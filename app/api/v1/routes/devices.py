"""
Device Management API
======================
API để quản lý và điều khiển các thiết bị IoT (đèn, còi, relay, cảm biến)
kết nối qua MQTT.

Các thiết bị giao tiếp với server qua MQTT:
  - Server ──topic: devices/{name}/command──► ESP32 (gửi lệnh)
  - ESP32  ──topic: devices/{name}/status──► Server (gửi trạng thái)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.device import Device, DeviceType
from app.models.user import User
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceCommand, DeviceResponse
from app.services.mqtt_service import MQTTService

router = APIRouter(prefix="/devices", tags=["IoT Devices"])


def device_to_dict(d: Device) -> dict:
    """Convert Device model to dict response"""
    return {
        "id": d.id,
        "name": d.name,
        "device_type": d.device_type.value if hasattr(d.device_type, 'value') else str(d.device_type),
        "mqtt_topic": d.mqtt_topic,
        "location": d.location,
        "state": d.state or {},
        "is_online": d.is_online,
        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def get_device_or_404(device_id: int, db: Session) -> Device:
    """Helper: lấy device hoặc raise 404"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail={
            "code": "DEVICE_NOT_FOUND",
            "message": f"Device with ID {device_id} not found"
        })
    return device


@router.get("")
def list_devices(
    device_type: Optional[str] = Query(None, description="Filter by type: light, siren, relay, sensor"),
    is_online: Optional[bool] = Query(None, description="Filter by online status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy danh sách tất cả thiết bị IoT.
    Có thể lọc theo device_type, is_online, location.
    """
    q = db.query(Device)
    
    if device_type:
        try:
            dt = DeviceType(device_type)
            q = q.filter(Device.device_type == dt)
        except ValueError:
            raise HTTPException(status_code=400, detail={
                "code": "INVALID_DEVICE_TYPE",
                "message": f"Invalid device type: {device_type}. Allowed: light, siren, relay, sensor"
            })
    
    if is_online is not None:
        q = q.filter(Device.is_online == is_online)
    
    if location:
        q = q.filter(Device.location.ilike(f"%{location}%"))
    
    devices = q.order_by(Device.device_type, Device.name).all()
    
    return {"success": True, "data": [device_to_dict(d) for d in devices]}


@router.get("/{device_id}")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết của 1 thiết bị."""
    device = get_device_or_404(device_id, db)
    return {"success": True, "data": device_to_dict(device)}


@router.post("", status_code=201)
def create_device(
    body: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Thêm thiết bị IoT mới vào hệ thống.
    Yêu cầu quyền admin.
    
    MQTT topic convention:
      - Command: devices/{name}/command (server → ESP)
      - Status:  devices/{name}/status  (ESP → server)
    """
    # Kiểm tra trùng lặp
    existing = db.query(Device).filter(
        (Device.name == body.name) | (Device.mqtt_topic == body.mqtt_topic)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail={
            "code": "DEVICE_ALREADY_EXISTS",
            "message": f"Device with name '{body.name}' or topic '{body.mqtt_topic}' already exists"
        })

    # Validate device_type
    try:
        device_type = DeviceType(body.device_type)
    except ValueError:
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_DEVICE_TYPE",
            "message": f"Invalid device type: {body.device_type}"
        })

    device = Device(
        name=body.name,
        device_type=device_type,
        mqtt_topic=body.mqtt_topic,
        location=body.location,
        state={"power": "off"},
        is_online=False,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    
    return {"success": True, "data": device_to_dict(device)}


@router.put("/{device_id}")
def update_device(
    device_id: int,
    body: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Cập nhật thông tin thiết bị (admin)."""
    device = get_device_or_404(device_id, db)
    
    if body.name is not None:
        # Check name conflict
        conflict = db.query(Device).filter(
            Device.name == body.name, Device.id != device_id
        ).first()
        if conflict:
            raise HTTPException(status_code=409, detail={
                "code": "DEVICE_ALREADY_EXISTS",
                "message": f"Device name '{body.name}' already in use"
            })
        device.name = body.name
    
    if body.location is not None:
        device.location = body.location
    
    if body.is_online is not None:
        device.is_online = body.is_online
        if body.is_online:
            device.last_seen_at = datetime.utcnow()
    
    if body.state is not None:
        current_state = device.state or {}
        current_state.update(body.state)
        device.state = current_state
    
    db.commit()
    db.refresh(device)
    
    return {"success": True, "data": device_to_dict(device)}


@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Xóa thiết bị khỏi hệ thống (admin)."""
    device = get_device_or_404(device_id, db)
    db.delete(device)
    db.commit()
    
    return {"success": True, "message": f"Device '{device.name}' deleted successfully"}


@router.post("/{device_id}/command")
def send_command(
    device_id: int,
    body: DeviceCommand,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gửi lệnh điều khiển đến thiết bị IoT qua MQTT.
    
    Commands:
      - "on":    Bật thiết bị
      - "off":   Tắt thiết bị
      - "toggle": Chuyển đổi on/off
    
    Với siren, có thể thêm duration (giây) để tự động tắt sau.
    
    Ví dụ:
      {"command": "on"}              → Bật đèn
      {"command": "off"}             → Tắt đèn
      {"command": "on", "duration": 30} → Bật còi 30 giây
      {"command": "toggle"}          → Chuyển đổi trạng thái
    """
    device = get_device_or_404(device_id, db)
    
    if not device.is_online:
        # Vẫn cho phép gửi lệnh, ESP sẽ nhận khi kết nối lại
        print(f"[Devices] ⚠️ Device '{device.name}' is offline, command queued")
    
    # Validate command
    valid_commands = ["on", "off", "toggle"]
    if body.command not in valid_commands:
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_COMMAND",
            "message": f"Invalid command '{body.command}'. Allowed: {', '.join(valid_commands)}"
        })
    
    # Gửi lệnh qua MQTT
    success = MQTTService.send_command(
        device_name=device.name,
        command=body.command,
        duration=body.duration,
    )
    
    if not success:
        raise HTTPException(status_code=503, detail={
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT service is not available. Command could not be sent."
        })
    
    # Cập nhật state trong database
    if body.command == "on":
        device.state = {**(device.state or {}), "power": "on"}
    elif body.command == "off":
        device.state = {**(device.state or {}), "power": "off"}
    elif body.command == "toggle":
        current_power = (device.state or {}).get("power", "off")
        device.state = {**(device.state or {}), "power": "on" if current_power == "off" else "off"}
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Command '{body.command}' sent to '{device.name}'",
        "data": device_to_dict(device)
    }


@router.post("/{device_id}/sync")
def sync_device_status(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Yêu cầu thiết bị gửi lại trạng thái hiện tại.
    Server gửi lệnh "status" xuống ESP, ESP sẽ reply với status hiện tại.
    """
    device = get_device_or_404(device_id, db)
    
    success = MQTTService.send_command(device.name, "status")
    if not success:
        raise HTTPException(status_code=503, detail={
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT service is not available"
        })
    
    return {"success": True, "message": f"Status request sent to '{device.name}'"}


@router.get("/stats/summary")
def device_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Thống kê tổng quan về các thiết bị IoT."""
    total = db.query(Device).count()
    online = db.query(Device).filter(Device.is_online == True).count()
    offline = total - online
    
    # Count by type
    by_type = {}
    for dt in DeviceType:
        count = db.query(Device).filter(Device.device_type == dt).count()
        by_type[dt.value] = count
    
    # Count by location
    by_location = {}
    locations = db.query(Device.location).distinct().all()
    for (loc,) in locations:
        if loc:
            count = db.query(Device).filter(Device.location == loc).count()
            by_location[loc] = count
    
    return {
        "success": True,
        "data": {
            "total_devices": total,
            "online": online,
            "offline": offline,
            "by_type": by_type,
            "by_location": by_location,
        }
    }