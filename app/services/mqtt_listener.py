
import asyncio
import logging
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.alert import Alert
from app.models.device import Device
from app.services.mqtt_client import mqtt_client
from app.api.v1.routes.websocket import broadcast_event

logger = logging.getLogger(__name__)


class MqttListener:
    """Xử lý incoming MQTT messages"""
    
    def __init__(self):
        self.db_session = None
        self._loop = None  # ✅ Lưu event loop lúc init
    
    async def init_listeners(self):
        try:
            self._loop = asyncio.get_event_loop()
            mqtt_client.set_on_message_callback(self.on_mqtt_message)
            self._loop = asyncio.get_event_loop()
            
            # ✅ Kiểm tra connected
            if not mqtt_client.is_connected():
                logger.error("✗ MQTT: Client chưa kết nối, không thể subscribe")
                return
            
            mqtt_client.subscribe("alerts/+/intrusion", qos=1)
            mqtt_client.subscribe("home/sensors/+", qos=1)
            mqtt_client.subscribe("home/devices/+", qos=1)
            mqtt_client.subscribe("system/status", qos=1)
            
            logger.info("✓ MQTT Listeners initialized")
        except Exception as e:
            logger.error(f"✗ Error initializing MQTT listeners: {str(e)}")
    
    def on_mqtt_message(self, topic: str, payload: dict):
        """
        Callback khi nhận message từ MQTT
        
        Args:
            topic: MQTT topic
            payload: Dict đã parse từ JSON
        """
        try:
            # ✅ Vẫn match đúng vì topic thực tế từ ESP vẫn là alerts/camera_1/intrusion
            if topic.startswith("alerts/") and topic.endswith("/intrusion"):
                self._handle_detector_alert(topic, payload)
            elif topic.startswith("home/sensors/"):
                self._handle_sensor_update(topic, payload)
            elif topic.startswith("home/devices/"):
                self._handle_device_update(topic, payload)
            elif topic == "system/status":
                self._handle_system_status(topic, payload)
        except Exception as e:
            logger.error(f"✗ Error processing MQTT message: {str(e)}")
    
    def _handle_detector_alert(self, topic: str, payload: dict):
        try:
            camera_id = payload.get("camera_id")
            detected_at = payload.get("detected_at")
            intruders = payload.get("intruders", [])

            logger.info(f"🚨 INTRUSION ALERT: Camera {camera_id}, {len(intruders)} intruders")

            db = next(get_db())
    
            alert = Alert(
                camera_id=camera_id,
                zone_id=None,
                detected_at=detected_at,
                bounding_boxes=intruders,
                confidence=max(
                    [i.get("confidence", 0) for i in intruders],
                    default=0
                ),
                is_acknowledged=0
            )

            db.add(alert)
            db.commit()
            db.refresh(alert)
            logger.info(f"✓ Alert saved to DB (ID: {alert.id})")

            # ✅ Fix: dùng asyncio.run_coroutine_threadsafe thay vì create_task
            # import asyncio
            event_data = {
                "alert_id": str(alert.id),
                "camera_id": camera_id,
                "detected_at": detected_at,
                "intruder_count": len(intruders),
                "timestamp": datetime.now().isoformat()
            }

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        broadcast_event(event="intrusion_alert", data=event_data),
                        loop
                    )
                else:
                    logger.warning("⚠️ Event loop không chạy, bỏ qua broadcast")
            except Exception as ws_err:
                logger.warning(f"⚠️ Broadcast thất bại (không ảnh hưởng alert): {ws_err}")

            db.close()

        except Exception as e:
            logger.error(f"✗ Error handling detector alert: {str(e)}")
            
    def _handle_sensor_update(self, topic: str, payload: dict):
        """
        Xử lý cập nhật sensor từ ESP32
        Topic: home/sensors/{location} or home/sensors/{device_id}
        
        Payload example:
        {
            "temperature": 28.5,
            "humidity": 65,
            "motion": true,
            "timestamp": "2026-05-17T14:00:00"
        }
        """
        try:
            logger.debug(f"📊 Sensor Update: {topic}")
            
            db = next(get_db())
            
            # Find device by mqtt_topic
            device = db.query(Device).filter(
                Device.mqtt_topic == topic
            ).first()
            
            if device:
                # Update device state
                device.state = payload
                device.last_seen_at = datetime.now()
                device.is_online = True
                db.commit()
                
                logger.debug(f"✓ Device state updated: {device.name}")
                
                # Broadcast to WebSocket
                import asyncio
                asyncio.create_task(broadcast_event(
                    event="device_update",
                    data={
                        "device_id": device.id,
                        "device_name": device.name,
                        "state": device.state,
                        "timestamp": datetime.now().isoformat()
                    }
                ))
            else:
                logger.warning(f"⚠️  Device not found: {topic}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"✗ Error handling sensor update: {str(e)}")
    
    def _handle_device_update(self, topic: str, payload: dict):
        """
        Xử lý state update từ device (relay, siren, etc.)
        Topic: home/devices/{device_id} or home/devices/{type}/{id}
        
        Payload example:
        {
            "power": "on",
            "mode": "alarm",
            "timestamp": "2026-05-17T14:00:00"
        }
        """
        try:
            logger.debug(f"🔌 Device Update: {topic}")
            
            db = next(get_db())
            
            # Find device by mqtt_topic
            device = db.query(Device).filter(
                Device.mqtt_topic == topic
            ).first()
            
            if device:
                # Update device state
                device.state = payload
                device.last_seen_at = datetime.now()
                device.is_online = True
                db.commit()
                
                logger.info(f"✓ Device updated: {device.name} → {payload}")
                
                # Broadcast to WebSocket
                import asyncio
                asyncio.create_task(broadcast_event(
                    event="device_status",
                    data={
                        "device_id": device.id,
                        "device_type": device.device_type,
                        "state": device.state,
                        "online": True,
                        "timestamp": datetime.now().isoformat()
                    }
                ))
            else:
                logger.warning(f"⚠️  Device not found: {topic}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"✗ Error handling device update: {str(e)}")
    
    def _handle_system_status(self, topic: str, payload: dict):
        """
        Xử lý system status messages
        Topic: system/status
        
        Payload example:
        {
            "detector_running": true,
            "uptime": 3600,
            "alerts_today": 5
        }
        """
        try:
            logger.info(f"ℹ️  System Status: {payload}")
            
            # Could broadcast to WebSocket for admin dashboard
            import asyncio
            asyncio.create_task(broadcast_event(
                event="system_status",
                data=payload
            ))
            
        except Exception as e:
            logger.error(f"✗ Error handling system status: {str(e)}")


# Global instance
mqtt_listener = MqttListener()
