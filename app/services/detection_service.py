import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.zone import Zone
from app.models.device import Device, DeviceType
from app.api.v1.routes.websocket import broadcast, broadcast_event
from app.services.mqtt_client import mqtt_client  # FIX: dùng mqtt_client thay MQTTService


async def on_intrusion_detected(alert: Alert, db: Session):
    """Gọi khi detection engine phát hiện xâm nhập."""
    try:
        zone_name = None
        if alert.zone_id is not None:
            zone = db.query(Zone).filter(Zone.id == alert.zone_id).first()
            zone_name = zone.name if zone else f"Zone {alert.zone_id}"

        boxes = []
        if alert.bounding_boxes:
            if isinstance(alert.bounding_boxes, str):
                try:
                    boxes = json.loads(alert.bounding_boxes)
                except Exception:
                    boxes = []
            else:
                boxes = alert.bounding_boxes

        object_count = len(boxes) if boxes else 1

        await broadcast("intrusion_detected", {
            "alert_id": str(alert.id),
            "zone_id": str(alert.zone_id) if alert.zone_id is not None else None,
            "zone_name": zone_name,
            "camera_id": str(alert.camera_id) if alert.camera_id is not None else None,
            "detected_at": alert.detected_at.isoformat() if alert.detected_at else None,
            "object_count": object_count,
            "confidence": float(alert.confidence) if alert.confidence is not None else 0.0,
            "thumbnail_url": f"/api/v1/media/alerts/{alert.id}/thumbnail" if alert.thumbnail_path else None,
            "bounding_boxes": boxes,
            "video_url": f"/api/v1/media/alerts/{alert.id}/video" if alert.video_clip_path else None
        })
        print(f"[WebSocket] Broadcast intrusion_detected for alert {alert.id}")

        # FIX: Kích hoạt thiết bị phần cứng qua mqtt_client thay vì MQTTService
        if mqtt_client.is_connected():
            _trigger_hardware_devices(alert, db)

    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast intrusion_detected: {str(e)}")


def _trigger_hardware_devices(alert: Alert, db: Session):
    """Bật siren/đèn khi có xâm nhập."""
    try:
        # Bật còi báo động (siren) - 30 giây
        siren = db.query(Device).filter(
            Device.device_type == DeviceType.siren,
            Device.is_online == True
        ).first()
        if siren:
            topic = f"devices/{siren.name}/command"
            mqtt_client.publish(topic, {"command": "on", "duration": 30})
            print(f"[Auto-Action] 🔔 Siren '{siren.name}' triggered")

        # Bật đèn cảnh báo
        lights = db.query(Device).filter(
            Device.device_type == DeviceType.light,
            Device.is_online == True
        ).all()
        for light in lights:
            topic = f"devices/{light.name}/command"
            mqtt_client.publish(topic, {"command": "on"})
            print(f"[Auto-Action] 💡 Light '{light.name}' turned on")

    except Exception as hw_err:
        print(f"[Auto-Action] ❌ Failed to trigger hardware: {str(hw_err)}")


async def on_intrusion_ended(alert: Alert, exited_at: datetime, db: Session):
    """Gọi khi xâm nhập kết thúc."""
    try:
        duration = int((exited_at - alert.detected_at).total_seconds()) if alert.detected_at else 0
        await broadcast_event("intrusion_ended", {
            "alert_id": str(alert.id),
            "zone_id": str(alert.zone_id) if alert.zone_id is not None else None,
            "exited_at": exited_at.isoformat(),
            "duration_seconds": duration,
            "video_url": f"/api/v1/media/alerts/{alert.id}/video" if alert.video_clip_path else None
        })
    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast intrusion_ended: {str(e)}")


async def on_camera_status_changed(camera_id: str, status: str):
    """Gọi khi camera thay đổi trạng thái."""
    try:
        await broadcast_event("camera_status_changed", {
            "camera_id": camera_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast camera_status_changed: {str(e)}")