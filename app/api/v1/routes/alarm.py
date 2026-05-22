"""
Alarm API - Kích hoạt cảnh báo thủ công
========================================
Publish MQTT tới ESP32 V2:
  Topic: alerts/camera_1/intrusion
  Payload: {"camera_id": 1, "detected_at": "...", "intruder_count": 2, "intruders": []}

ESP32 nhận → LED nhấp nháy + Buzzer kêu + LCD hiển thị "CANH BAO"
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.alert_trigger import AlertTriggerRequest
from app.services.mqtt_client import mqtt_client

router = APIRouter(prefix="/alarm", tags=["Alarm"])

ALERT_TOPIC = "alerts/camera_1/intrusion"


def _check_mqtt():
    """Helper: kiểm tra MQTT connected, raise 503 nếu không"""
    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail={
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT broker không khả dụng"
        })


@router.post("/trigger")
def trigger_alarm(
    body: AlertTriggerRequest,
    # current_user: User = Depends(get_current_user),
):
    """
    Kích hoạt cảnh báo thủ công.
    ESP32 nhận → LED nhấp nháy + Buzzer kêu + LCD: CANH BAO / KHONG AN TOAN!
    """
    _check_mqtt()

    payload = {
        "camera_id": body.camera_id,
        "detected_at": datetime.now().isoformat(),
        "intruder_count": body.intruder_count,
        "intruders": [],
        "note": body.message or "Manual trigger"
    }

    success = mqtt_client.publish(topic=ALERT_TOPIC, payload=payload, qos=1)

    if not success:
        raise HTTPException(status_code=500, detail={
            "code": "PUBLISH_FAILED",
            "message": "Không thể gửi cảnh báo tới ESP32"
        })

    return {
        "success": True,
        "message": f"Đã kích hoạt cảnh báo: {body.intruder_count} người xâm nhập",
        "data": {
            "topic": ALERT_TOPIC,
            "payload": payload,
            # "triggered_by": current_user.username,
            "triggered_at": datetime.now().isoformat()
        }
    }


@router.post("/stop")
def stop_alarm(
    # current_user: User = Depends(get_current_user),
):
    """
    Gửi lệnh dừng cảnh báo (intruder_count=0).
    Lưu ý: ESP32 V2 dừng hoàn toàn qua nút vật lý hoặc hết 30s timer.
    Muốn dừng từ xa qua MQTT cần thêm handler trong .ino.
    """
    _check_mqtt()

    payload = {
        "camera_id": 1,
        "detected_at": datetime.now().isoformat(),
        "intruder_count": 0,
        "intruders": [],
        "note": "Stop trigger"
    }

    success = mqtt_client.publish(topic=ALERT_TOPIC, payload=payload, qos=1)

    if not success:
        raise HTTPException(status_code=500, detail={
            "code": "PUBLISH_FAILED",
            "message": "Không thể gửi lệnh dừng tới ESP32"
        })

    return {
        "success": True,
        "message": "Đã gửi lệnh dừng cảnh báo",
        "data": {
            # "triggered_by": current_user.username,
            "stopped_at": datetime.now().isoformat()
        }
    }


@router.get("/status")
def alarm_status(
    # current_user: User = Depends(get_current_user),
):
    """Kiểm tra trạng thái kết nối MQTT và topic cảnh báo."""
    return {
        "success": True,
        "data": {
            # "mqtt_connected": mqtt_client.is_connected(),
            "alert_topic": ALERT_TOPIC
        }
    }