"""
Device Control API Routes

Endpoints để quản lý và control IoT devices (ESP32, relays, sirens, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.device import Device
from app.services.mqtt_client import mqtt_client

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("")
async def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách tất cả devices (ESP32, relays, sensors, etc.)
    """
    devices = db.query(Device).all()
    
    return {
        "success": True,
        "data": {
            "devices": [
                {
                    "id": d.id,
                    "name": d.name,
                    "type": d.device_type,
                    "mqtt_topic": d.mqtt_topic,
                    "state": d.state,
                    "online": d.is_online,
                    "last_seen": d.last_seen_at.isoformat() if d.last_seen_at else None,
                    "location": d.location,
                    "created_at": d.created_at.isoformat() if d.created_at else None
                }
                for d in devices
            ],
            "count": len(devices)
        }
    }


@router.get("/{device_id}")
async def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin chi tiết 1 device
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {
        "success": True,
        "data": {
            "id": device.id,
            "name": device.name,
            "type": device.device_type,
            "mqtt_topic": device.mqtt_topic,
            "state": device.state,
            "online": device.is_online,
            "last_seen": device.last_seen_at.isoformat() if device.last_seen_at else None,
            "location": device.location,
            "created_at": device.created_at.isoformat() if device.created_at else None
        }
    }


@router.post("/{device_id}/control")
async def control_device(
    device_id: int,
    command: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Gửi control command tới device thông qua MQTT
    
    Example payload:
    {
        "power": "on",
        "brightness": 75,
        "color": "red"
    }
    
    Flow:
    1. Find device by ID
    2. Publish command to device.mqtt_topic
    3. Return success/fail
    4. Device receives command via MQTT subscription
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if not mqtt_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT broker not connected"
        )
    
    try:
        # Prepare control message
        control_msg = {
            **command,
            "timestamp": datetime.now().isoformat(),
            "command_id": f"{device_id}_{int(datetime.now().timestamp() * 1000)}"
        }
        
        # Publish to device MQTT topic
        success = mqtt_client.publish(
            topic=device.mqtt_topic,
            payload=control_msg,
            qos=1
        )
        
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
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to publish control command"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/{device_id}/toggle")
async def toggle_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Toggle device on/off (Relay, Light, Siren, etc.)
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get current state
    current_state = device.state.get("power", "off") if device.state else "off"
    new_state = "off" if current_state == "on" else "on"
    
    # Send toggle command
    command = {"power": new_state}
    
    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT broker not connected")
    
    try:
        control_msg = {
            "power": new_state,
            "timestamp": datetime.now().isoformat()
        }
        
        success = mqtt_client.publish(
            topic=device.mqtt_topic,
            payload=control_msg,
            qos=1
        )
        
        if success:
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
        else:
            raise HTTPException(status_code=500, detail="Failed to toggle device")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/{device_id}/trigger-alarm")
async def trigger_alarm(
    device_id: int,
    duration_seconds: int = Query(default=60, ge=1, le=3600),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger siren/alarm device
    
    Args:
        device_id: Device ID
        duration_seconds: Bao lâu siren reo (1-3600 seconds)
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.device_type != "siren":
        raise HTTPException(status_code=400, detail="Device is not a siren")
    
    if not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT broker not connected")
    
    try:
        alarm_cmd = {
            "action": "alarm",
            "duration": duration_seconds,
            "timestamp": datetime.now().isoformat()
        }
        
        success = mqtt_client.publish(
            topic=device.mqtt_topic,
            payload=alarm_cmd,
            qos=1
        )
        
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
        else:
            raise HTTPException(status_code=500, detail="Failed to trigger alarm")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/{device_id}/status")
async def get_device_status(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy status hiện tại của device (online/offline, state, last_seen)
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
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
