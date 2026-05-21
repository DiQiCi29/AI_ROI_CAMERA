"""
MQTT Client Module - Giao tiếp với Mosquitto Broker

Mục đích:
  - Publish alerts từ AI Detector
  - Subscribe device status từ ESP32/IoT
  - Publish control commands tới devices
  - Handle reconnection & error recovery
"""

import paho.mqtt.client as mqtt
import json
import logging
from typing import Callable, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class MqttClient:
    """MQTT Client để kết nối tới Mosquitto broker"""
    
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.connected = False
        self.on_message_callback: Optional[Callable] = None
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
    
    def connect(self) -> bool:
        """
        Kết nối tới MQTT broker
        
        Returns:
            True nếu connect thành công, False nếu thất bại
        """
        try:
            # Set username/password
            self.client.username_pw_set(
                settings.MQTT_USERNAME,
                settings.MQTT_PASSWORD
            )
            
            # Connect to broker
            self.client.connect(
                settings.MQTT_HOST,
                settings.MQTT_PORT,
                keepalive=settings.MQTT_KEEPALIVE
            )
            
            # Start background thread để process network events
            self.client.loop_start()
            logger.info(f"✓ MQTT: Kết nối {settings.MQTT_HOST}:{settings.MQTT_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"✗ MQTT: Lỗi kết nối - {str(e)}")
            return False
    
    def disconnect(self):
        """Ngắt kết nối an toàn khỏi broker"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("✓ MQTT: Đã ngắt kết nối")
        except Exception as e:
            logger.error(f"✗ MQTT: Lỗi ngắt kết nối - {str(e)}")
    
    def publish(
        self,
        topic: str,
        payload: dict,
        qos: int = None,
        retain: bool = False
    ) -> bool:
        """
        Publish message tới topic
        
        Args:
            topic: MQTT topic (VD: alerts/camera_1/intrusion)
            payload: Dict sẽ convert sang JSON
            qos: Quality of Service (0/1/2, default từ config)
            retain: Giữ message trên broker cho subscriber mới
            
        Returns:
            True nếu publish thành công
        """
        try:
            if qos is None:
                qos = settings.MQTT_QOS
            
            # Convert dict to JSON
            message = json.dumps(payload, ensure_ascii=False)
            
            # Publish
            result = self.client.publish(
                topic,
                message,
                qos=qos,
                retain=retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"📤 MQTT Publish: {topic} (QoS {qos})")
                return True
            else:
                logger.warning(f"⚠️  MQTT Publish failed: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"✗ MQTT: Lỗi publish - {str(e)}")
            return False
    
    def subscribe(self, topic: str, qos: int = None) -> bool:
        """
        Subscribe tới topic
        
        Args:
            topic: MQTT topic pattern (VD: alerts/camera_+/intrusion)
            qos: Quality of Service
            
        Returns:
            True nếu subscribe thành công
        """
        try:
            if qos is None:
                qos = settings.MQTT_QOS
            
            result = self.client.subscribe(topic, qos=qos)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📥 MQTT Subscribe: {topic} (QoS {qos})")
                return True
            else:
                logger.warning(f"⚠️  MQTT Subscribe failed: {result[0]}")
                return False
                
        except Exception as e:
            logger.error(f"✗ MQTT: Lỗi subscribe - {str(e)}")
            return False
    
    def set_on_message_callback(self, callback: Callable):
        """Set custom callback khi nhận message"""
        self.on_message_callback = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback khi kết nối thành công"""
        if rc == 0:
            self.connected = True
            logger.info("✓ MQTT: Kết nối thành công (rc=0)")
        else:
            self.connected = False
            logger.error(f"✗ MQTT: Kết nối thất bại (rc={rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback khi ngắt kết nối"""
        self.connected = False
        if rc != 0:
            logger.warning(f"⚠️  MQTT: Ngắt kết nối không chủ ý (rc={rc})")
        else:
            logger.info("MQTT: Đã ngắt kết nối")
    
    def _on_message(self, client, userdata, msg):
        """Callback khi nhận message"""
        try:
            payload = json.loads(msg.payload.decode())
            logger.debug(f"📨 MQTT Message: {msg.topic} → {payload}")
            
            # Call custom callback nếu có
            if self.on_message_callback:
                self.on_message_callback(msg.topic, payload)
                
        except json.JSONDecodeError:
            logger.warning(f"⚠️  MQTT: Invalid JSON payload: {msg.payload}")
        except Exception as e:
            logger.error(f"✗ MQTT: Lỗi xử lý message - {str(e)}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback khi publish thành công"""
        logger.debug(f"✓ MQTT: Message published (mid={mid})")
    
    def is_connected(self) -> bool:
        """Check xem MQTT có đang kết nối không"""
        return self.connected


# Global instance - dùng ở toàn app
mqtt_client = MqttClient()
