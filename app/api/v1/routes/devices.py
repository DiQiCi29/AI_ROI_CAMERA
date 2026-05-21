"""
Device Management & Control API
===============================

API để quản lý và điều khiển các thiết bị IoT (đèn, còi, relay, cảm biến) kết nối qua MQTT.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.device import Device, DeviceType
from app.models.user import User
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceCommand, DeviceResponse
from app.services.mqtt_client import mqtt_client  # ✅ Dùng mqtt_client thay vì MQTTService

router = APIRouter(prefix="/devices", tags=["IoT Devices"])


def device_to_dict(d: Device) -> dict:
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
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail={
            "code": "DEVICE_NOT_FOUND",
            "message": f"Device with ID {device_id} not found"
        })
    return device


@router.get("")
def list_devices(
    device_type: Optional[str] = Query(None),
    is_online: Optional[bool] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.get("/stats/summary")
def device_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(Device).count()
    online = db.query(Device).filter(Device.is_online == True).count()
    offline = total - online
    by_type = {}
    for dt in DeviceType:
        count = db.query(Device).filter(Device.device_type == dt).count()
        by_type[dt.value] = count
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


@router.get("/{device_id}")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = get_device_or_404(device_id, db)
    return {"success": True, "data": device_to_dict(device)}


@router.post("", status_code=201)
def create_device(
    body: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(Device).filter(
        (Device.name == body.name) | (Device.mqtt_topic == body.mqtt_topic)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail={
            "code": "DEVICE_ALREADY_EXISTS",
            "message": f"Device with name '{body.name}' or topic '{body.mqtt_topic}' already exists"
        })
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
    device = get_device_or_404(device_id, db)
    if body.name is not None:
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
    """Gửi lệnh on/off/toggle đến thiết bị qua MQTT."""
    device = get_device_or_404(device_id, db)

    if not device.is_online:
        print(f"[Devices] ⚠️ Device '{device.name}' is offline, command queued")

    valid_commands = ["on", "off", "toggle"]
    if body.command not in valid_commands:
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_COMMAND",
            "message": f"Invalid command '{body.command}'. Allowed: {', '.join(valid_commands)}"
        })

    # ✅ Build payload rồi publish qua mqtt_client
    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail={
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT service is not available. Command could not be sent."
        })

    # Build payload đúng theo device_type
   # Build payload đúng theo device_type
    device_type_value = device.device_type.value if hasattr(device.device_type, 'value') else str(device.device_type)

    if device_type_value == "siren":
        print(f"[Devices] 🚨 Triggering siren '{device.name}' with command '{body.command}'")
        payload = {
            "action": "alarm" if body.command == "on" else "stop",
            "duration": body.duration if body.duration is not None else 10
        }
    else:
        print(f"[Devices] 🕒 Controlling device '{device.name}' with command '{body.command}'")
        payload = {"power": body.command}
        if body.duration is not None:
            payload["duration"] = body.duration

    # ✅ Publish nằm ngoài if/else — chạy cho cả 2 loại
    topic = device.mqtt_topic
    success = mqtt_client.publish(topic=topic, payload=payload)

    if not success:
        raise HTTPException(status_code=503, detail={
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT service is not available. Command could not be sent."
        })

    # Cập nhật state trong DB
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


@router.post("/{device_id}/control")
def control_device(
    device_id: int,
    command: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gửi control command tùy ý tới device qua MQTT topic của device."""
    device = get_device_or_404(device_id, db)

    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT broker not connected")

    control_msg = {
        **command,
        "timestamp": datetime.now().isoformat(),
        "command_id": f"{device_id}_{int(datetime.now().timestamp() * 1000)}"
    }

    # ✅ Publish tới mqtt_topic của device (do người dùng cấu hình)
    success = mqtt_client.publish(topic=device.mqtt_topic, payload=control_msg)

    if success:
        return {
            "success": True,
            "data": {
                "device_id": device_id,
                "device_name": device.name,
                "command": command,
                "message": f"Command sent to {device.name}",
                "timestamp": datetime.now().isoformat()
            }
        }
    raise HTTPException(status_code=500, detail="Failed to publish control command")


@router.post("/{device_id}/toggle")
def toggle_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle device on/off."""
    device = get_device_or_404(device_id, db)

    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT broker not connected")

    current_state = device.state.get("power", "off") if device.state else "off"
    new_state = "off" if current_state == "on" else "on"

    control_msg = {"power": new_state, "timestamp": datetime.now().isoformat()}
    success = mqtt_client.publish(topic=device.mqtt_topic, payload=control_msg)

    if success:
        device.state = {**(device.state or {}), "power": new_state}
        db.commit()
        return {
            "success": True,
            "data": {
                "device_id": device_id,
                "device_name": device.name,
                "previous_state": current_state,
                "new_state": new_state,
                "timestamp": datetime.now().isoformat()
            }
        }
    raise HTTPException(status_code=500, detail="Failed to toggle device")


@router.post("/{device_id}/trigger-alarm")
def trigger_alarm(
    device_id: int,
    duration_seconds: int = Query(default=60, ge=1, le=3600),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger siren/alarm device."""
    device = get_device_or_404(device_id, db)

    device_type_value = device.device_type.value if hasattr(device.device_type, 'value') else str(device.device_type)
    if device_type_value != "siren":
        raise HTTPException(status_code=400, detail="Device is not a siren")

    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT broker not connected")

    alarm_cmd = {
        "action": "alarm",
        "duration": duration_seconds,
        "timestamp": datetime.now().isoformat()
    }
    success = mqtt_client.publish(topic=device.mqtt_topic, payload=alarm_cmd)

    if success:
        return {
            "success": True,
            "data": {
                "device_id": device_id,
                "device_name": device.name,
                "action": "alarm",
                "duration": duration_seconds,
                "message": f"Alarm triggered on {device.name} for {duration_seconds}s",
                "timestamp": datetime.now().isoformat()
            }
        }
    raise HTTPException(status_code=500, detail="Failed to trigger alarm")


@router.post("/{device_id}/sync")
def sync_device_status(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Yêu cầu thiết bị gửi lại trạng thái hiện tại."""
    device = get_device_or_404(device_id, db)

    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail={
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT service is not available"
        })

    topic = f"devices/{device.name}/command"
    success = mqtt_client.publish(topic=topic, payload={"command": "status"})

    if not success:
        raise HTTPException(status_code=503, detail={
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT service is not available"
        })

    return {"success": True, "message": f"Status request sent to '{device.name}'"}


@router.get("/{device_id}/status")
def get_device_status(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy status hiện tại của device."""
    device = get_device_or_404(device_id, db)
    return {
        "success": True,
        "data": {
            "device_id": device.id,
            "device_name": device.name,
            "online": device.is_online,
            "state": device.state,
            "last_seen": device.last_seen_at.isoformat() if device.last_seen_at else None,
            "location": device.location,
            "mqtt_topic": device.mqtt_topic
        }
    }