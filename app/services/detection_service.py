import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.zone import Zone
from app.models.device import Device, DeviceType
from app.api.v1.routes.websocket import broadcast, broadcast_event
from agent.mqtt_service import MQTTService


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

        # ── Auto-trigger hardware devices on intrusion ─────────────────────
        try:
            # 1. Bật còi báo động (siren)
            siren = db.query(Device).filter(
                Device.device_type == DeviceType.siren,
                Device.is_online == True
            ).first()
            if siren:
                MQTTService.trigger_siren(siren.name, duration=30)
                print(f"[Auto-Action] 🔔 Siren '{siren.name}' triggered for 30s")

            # 2. Bật đèn cảnh báo (light) - tất cả đèn online
            lights = db.query(Device).filter(
                Device.device_type == DeviceType.light,
                Device.is_online == True
            ).all()
            for light in lights:
                MQTTService.turn_on_light(light.name)
                print(f"[Auto-Action] 💡 Light '{light.name}' turned on")

            # 3. Bật relay nếu có
            relays = db.query(Device).filter(
                Device.device_type == DeviceType.relay,
                Device.is_online == True
            ).all()
            for relay in relays:
                MQTTService.send_command(relay.name, "on")
                print(f"[Auto-Action] 🔄 Relay '{relay.name}' triggered")

        except Exception as hw_err:
            print(f"[Auto-Action] ❌ Failed to trigger hardware: {str(hw_err)}")

    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast intrusion_detected: {str(e)}")


async def on_intrusion_ended(alert: Alert, exited_at: datetime, db: Session):
    """Gọi khi xâm nhập kết thúc (đối tượng rời khỏi vùng)."""
    try:
        duration = int((exited_at - alert.detected_at).total_seconds()) if alert.detected_at else 0
        await broadcast_event("intrusion_ended", {
            "alert_id": str(alert.id),
            "zone_id": str(alert.zone_id) if alert.zone_id is not None else None,
            "exited_at": exited_at.isoformat(),
            "duration_seconds": duration,
            "video_url": f"/api/v1/media/alerts/{alert.id}/video" if alert.video_clip_path else None
        })
        print(f"[WebSocket] Broadcast intrusion_ended for alert {alert.id}")
    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast intrusion_ended: {str(e)}")


async def on_camera_status_changed(camera_id: str, status: str):
    """Gọi khi camera thay đổi trạng thái (online/offline)."""
    try:
        await broadcast_event("camera_status_changed", {
            "camera_id": camera_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"[WebSocket] Broadcast camera_status_changed: {camera_id} -> {status}")
    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast camera_status_changed: {str(e)}")
