import json
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.zone import Zone
from app.models.device import Device, DeviceType
from app.api.v1.routes.websocket import broadcast, broadcast_event
from app.services.mqtt_client import mqtt_client  # FIX: dùng mqtt_client thay MQTTService
from app.services.fcm_service import FCMService  # Import để gọi thẳng FCM dịch vụ của bạn


async def on_intrusion_detected_fast(camera_id: int, intruders: list, zone_name: str = "Vùng bảo vệ"):
    """
    HÀM XỬ LÝ NHANH CẤP TỐC: Bỏ qua việc ghi nhận/đọc tạo bản ghi DB rườm rà.
    Tập trung đẩy WebSocket thời gian thực, bắn thông báo FCM, và gọi /alarm/trigger.
    """
    try:
        object_count = len(intruders)
        detected_time = datetime.now().isoformat()

        # 0. GỌI /alarm/trigger ĐỂ BẬT ESP32 (MQTT tới Buzzer + LED + LCD)
        try:
            async with httpx.AsyncClient() as client:
                alarm_payload = {
                    "camera_id": camera_id,
                    "intruder_count": object_count,
                    "message": f"AI detected {object_count} intruders at {zone_name}"
                }
                response = await client.post(
                    "http://localhost:8000/api/v1/alarm/trigger",
                    json=alarm_payload,
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"✓ [Alarm Trigger] ESP32 alert activated ({object_count} intruders)")
                else:
                    print(f"✗ [Alarm Trigger] Failed: {response.status_code}")
        except Exception as alarm_err:
            print(f"✗ [Alarm Trigger Error] {str(alarm_err)}")

        # 1. PHÁT TRUYỀN WEBSOCKET ĐỂ HIỂN THỊ OVERLAY ĐỎ CHỚP TRÊN APP NGAY LẬP TỨC
        await broadcast("intrusion_detected", {
            "alert_id": "fast_trigger",
            "zone_id": "1",
            "zone_name": zone_name,
            "camera_id": str(camera_id),
            "detected_at": detected_time,
            "object_count": object_count,
            "confidence": 0.85,
            "thumbnail_url": None,  # Không tốn tài nguyên render ảnh thumbnail
            "bounding_boxes": [item["bbox"] for item in intruders],
            "video_url": None
        })
        print(f"🚀 [Fast Logic] Broadcast WebSocket intrusion_detected to application.")

        # 2. KIỂM TRA & BẮN THÔNG BÁO ĐẨY HỎA TỐC QUA FIREBASE (FCM)
        try:
            # Gửi tin nhắn Cloud Messaging không qua hàng đợi
            # Payload đơn giản hóa tối đa để điện thoại nhận được trong <1 giây
            FCMService.send_to_all(
                title="🚨 CẢNH BÁO XÂM NHẬP KHẨN CẤP",
                body=f"Phát hiện {object_count} đối tượng lạ xuất hiện tại khu vực {zone_name}!",
                data={
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "camera_id": str(camera_id),
                    "type": "intrusion"
                }
            )
            print("✓ [FCM Check] Khởi phát lệnh đẩy Firebase Cloud Messaging thành công.")
        except Exception as fcm_err:
            print(f"✗ [FCM Check Error] Thiết lập Firebase bị lỗi hoặc chưa có token: {str(fcm_err)}")

    except Exception as e:
        print(f"[Fast Logic Error] Gặp sự cố truyền phát tín hiệu khẩn cấp: {str(e)}")


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