# app/api/v1/routes/monitoring.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.camera import Camera # Sử dụng bảng Camera sẵn có để giữ trạng thái bảo vệ
from app.services.mqtt_client import mqtt_client
from datetime import datetime

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])
ALERT_TOPIC = "alerts/camera_1/intrusion"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/status")
def get_monitoring_status(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Đọc trạng thái camera đầu tiên từ DB, dùng trường is_active để đại diện trạng thái giám sát toàn hệ thống
    camera = db.query(Camera).first()
    status = camera.is_active if camera else True
    
    # Đồng bộ ngược lại bộ nhớ đệm RAM để AI Worker đọc nhanh không cần query DB liên tục
    request.app.state.monitoring_active = status
    
    return {
        "success": True,
        "data": {
            "monitoring_active": status
        }
    }

@router.post("/toggle")
def toggle_monitoring_status(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    camera = db.query(Camera).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Không tìm thấy cấu hình Camera")
        
    # Đảo trạng thái hiện tại trong DB
    new_status = not camera.is_active
    camera.is_active = new_status
    db.commit()
    
    # Ghi đè vào bộ nhớ RAM cho AI Core đọc trực tiếp
    request.app.state.monitoring_active = new_status
    
    # Nếu tắt chế độ bảo vệ (OFF) -> Phát lệnh MQTT dập còi đèn ngay lập tức
    if not new_status:
        if mqtt_client.is_connected():
            payload = {
                "camera_id": 1,
                "detected_at": datetime.now().isoformat(),
                "intruder_count": 0,
                "intruders": [],
                "note": "Stopped by App monitoring disable"
            }
            mqtt_client.publish(topic=ALERT_TOPIC, payload=payload, qos=1)

    return {
        "success": True,
        "data": {
            "monitoring_active": new_status
        }
    }