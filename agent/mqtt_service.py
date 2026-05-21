"""
MQTT Service for IoT device communication
==========================================
Giao tiếp với ESP32/Arduino qua MQTT protocol.
Sử dụng Mosquitto broker (docker-compose.yml).

Cách dùng:
    # Trong startup event của server
    MQTTService.initialize()
    
    # Gửi lệnh xuống ESP
    MQTTService.publish("devices/siren_01/command", {"command": "on", "duration": 30})
    
    # ESP sẽ nhận và thực thi
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Callable, Optional
import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.device import Device
from app.core.config import settings


class MQTTService:
    """
    Singleton service quản lý kết nối MQTT với ESP32/Arduino.
    - Tự động kết nối/reconnect đến MQTT broker
    - Lắng nghe topic "devices/+/status" để cập nhật trạng thái thiết bị
    - Gửi lệnh xuống thiết bị qua topic "devices/{device_name}/command"
    """

    _instance = None
    _client: Optional[mqtt.Client] = None
    _initialized = False
    _on_message_callback: Optional[Callable] = None

    # MQTT broker config
    MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
    MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
    MQTT_KEEPALIVE = 60

    # Topics
    STATUS_TOPIC = "devices/#"               # Subscribe tất cả dưới devices/       # ESP gửi status lên
    COMMAND_TOPIC_PREFIX = "devices/{}/command"  # Server gửi lệnh xuống

    @classmethod
    def initialize(cls, host: str = None, port: int = None):
        """
        Khởi tạo MQTT client và kết nối đến broker.
        Gọi 1 lần duy nhất khi server start.

        Args:
            host: MQTT broker hostname/IP (default: localhost)
            port: MQTT broker port (default: 1883)
        """
        if cls._initialized:
            print("[MQTT] Already initialized, skipping")
            return

        cls.MQTT_HOST = host or cls.MQTT_HOST
        cls.MQTT_PORT = port or cls.MQTT_PORT

        try:
            cls._client = mqtt.Client(client_id="ai_roi_camera_server", protocol=mqtt.MQTTv311)
            cls._client.on_connect = cls._on_connect
            cls._client.on_disconnect = cls._on_disconnect
            cls._client.on_message = cls._on_message

            # Enable automatic reconnect
            cls._client.connect_async(cls.MQTT_HOST, cls.MQTT_PORT, cls.MQTT_KEEPALIVE)
            cls._client.loop_start()

            cls._initialized = True
            print(f"[MQTT] Connecting to {cls.MQTT_HOST}:{cls.MQTT_PORT}...")

        except Exception as e:
            print(f"[MQTT] Failed to initialize: {str(e)}")
            print("[MQTT] MQTT service will be disabled")
            cls._initialized = False

    @classmethod
    def _on_connect(cls, client, userdata, flags, rc):
        """Callback khi kết nối MQTT thành công."""
        if rc == 0:
            print(f"[MQTT] ✅ Connected to broker at {cls.MQTT_HOST}:{cls.MQTT_PORT}")
            # Subscribe để nhận status từ ESP
            client.subscribe(cls.STATUS_TOPIC, qos=1)
            print(f"[MQTT] Subscribed to {cls.STATUS_TOPIC}")
        elif rc == 1:
            print("[MQTT] ❌ Connection refused - incorrect protocol version")
        elif rc == 2:
            print("[MQTT] ❌ Connection refused - invalid client identifier")
        elif rc == 3:
            print("[MQTT] ❌ Connection refused - server unavailable")
        elif rc == 4:
            print("[MQTT] ❌ Connection refused - bad username or password")
        elif rc == 5:
            print("[MQTT] ❌ Connection refused - not authorised")
        else:
            print(f"[MQTT] ❌ Connection failed with code {rc}")

    @classmethod
    def _on_disconnect(cls, client, userdata, rc):
        """Callback khi mất kết nối MQTT."""
        if rc != 0:
            print(f"[MQTT] ⚠️ Unexpected disconnect (rc={rc}), will auto-reconnect...")
        else:
            print("[MQTT] Disconnected")

    @classmethod
    def _on_message(cls, client, userdata, msg):
        """
        Callback khi nhận được message từ ESP.
        
        ESP gửi lên theo format:
            Topic: "devices/{device_name}/status"
            Payload: {"power": "on", "temperature": 30.5, ...}
        
        Server tự động cập nhật state + last_seen_at trong database.
        """
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            
            print(f"[MQTT] 📩 Received: {topic} -> {payload}")

            # Parse device name từ topic: "devices/{name}/status"
            parts = topic.split("/")
            if len(parts) >= 2:
                device_name = parts[1]

                # Cập nhật database
                db: Session = SessionLocal()
                try:
                    device = db.query(Device).filter(Device.name == device_name).first()
                    if device:
                        device.state = payload
                        device.is_online = True
                        device.last_seen_at = datetime.utcnow()
                        db.commit()
                        print(f"[MQTT] ✅ Updated device '{device_name}' state: {payload}")
                    else:
                        print(f"[MQTT] ⚠️ Device '{device_name}' not found in database")
                except Exception as e:
                    print(f"[MQTT] ❌ Database error: {str(e)}")
                finally:
                    db.close()

            # Gọi callback nếu có (cho xử lý mở rộng)
            if cls._on_message_callback:
                cls._on_message_callback(topic, payload)

        except json.JSONDecodeError:
            print(f"[MQTT] ❌ Invalid JSON from ESP: {msg.payload}")
        except Exception as e:
            print(f"[MQTT] ❌ Error processing message: {str(e)}")

    @classmethod
    def set_message_callback(cls, callback: Callable[[str, dict], None]):
        """
        Đặt callback tùy chỉnh cho message từ ESP.
        Dùng để mở rộng xử lý (ví dụ: tự động gửi WebSocket event).
        """
        cls._on_message_callback = callback

    @classmethod
    def publish(cls, topic: str, payload: dict, qos: int = 1) -> bool:
        """
        Gửi lệnh JSON xuống ESP/Arduino qua MQTT.

        Args:
            topic: MQTT topic (VD: "devices/siren_01/command")
            payload: Dict dữ liệu (VD: {"command": "on", "duration": 30})
            qos: Quality of Service (0, 1, hoặc 2)

        Returns:
            True nếu gửi thành công, False nếu thất bại
        """
        if not cls._initialized or cls._client is None:
            print("[MQTT] ❌ Service not initialized")
            return False

        if not cls._client.is_connected():
            print("[MQTT] ⚠️ Not connected to broker, cannot publish")
            return False

        try:
            result = cls._client.publish(topic, json.dumps(payload), qos=qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] 📤 Published to {topic}: {payload}")
                return True
            else:
                print(f"[MQTT] ❌ Publish failed with code {result.rc}")
                return False
        except Exception as e:
            print(f"[MQTT] ❌ Publish error: {str(e)}")
            return False

    @classmethod
    def send_command(cls, device_name: str, command: str, duration: int = None) -> bool:
        """
        Gửi lệnh đến thiết bị cụ thể.

        Args:
            device_name: Tên thiết bị (VD: "siren_01")
            command: Lệnh ("on", "off", "toggle")
            duration: Thời gian bật (giây) - chỉ dùng cho siren

        Returns:
            True nếu gửi thành công
        """
        topic = cls.COMMAND_TOPIC_PREFIX.format(device_name)
        payload = {"command": command}
        if duration is not None:
            payload["duration"] = duration
        return cls.publish(topic, payload)

    @classmethod
    def trigger_siren(cls, device_name: str = "siren_01", duration: int = 30) -> bool:
        """Bật còi báo động trong duration giây."""
        return cls.send_command(device_name, "on", duration)

    @classmethod
    def turn_on_light(cls, device_name: str) -> bool:
        """Bật đèn."""
        return cls.send_command(device_name, "on")

    @classmethod
    def turn_off_light(cls, device_name: str) -> bool:
        """Tắt đèn."""
        return cls.send_command(device_name, "off")

    @classmethod
    def toggle_device(cls, device_name: str) -> bool:
        """Chuyển đổi trạng thái on/off."""
        return cls.send_command(device_name, "toggle")

    @classmethod
    def get_connection_status(cls) -> dict:
        """Kiểm tra trạng thái kết nối MQTT."""
        if not cls._initialized or cls._client is None:
            return {"connected": False, "initialized": False}
        return {
            "connected": cls._client.is_connected(),
            "initialized": True,
            "host": cls.MQTT_HOST,
            "port": cls.MQTT_PORT,
        }

    @classmethod
    def shutdown(cls):
        """Ngắt kết nối MQTT (gọi khi server shutdown)."""
        if cls._client:
            cls._client.loop_stop()
            cls._client.disconnect()
            cls._initialized = False
            print("[MQTT] Shutdown complete")