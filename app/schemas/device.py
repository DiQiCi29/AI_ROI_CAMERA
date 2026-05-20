from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime


class DeviceCreate(BaseModel):
    """Schema for creating a new IoT device"""
    name: str
    device_type: str  # "light", "siren", "relay", "sensor"
    mqtt_topic: str
    location: Optional[str] = None

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v):
        allowed = ["light", "siren", "relay", "sensor"]
        if v not in allowed:
            raise ValueError(f"device_type must be one of: {', '.join(allowed)}")
        return v

    @field_validator("mqtt_topic")
    @classmethod
    def validate_mqtt_topic(cls, v):
        if not v or len(v) < 3:
            raise ValueError("mqtt_topic must be at least 3 characters")
        return v


class DeviceCommand(BaseModel):
    """Schema for sending command to a device"""
    command: str  # "on", "off", "toggle"
    duration: Optional[int] = None  # seconds (for siren)


class DeviceUpdate(BaseModel):
    """Schema for updating device info"""
    name: Optional[str] = None
    location: Optional[str] = None
    is_online: Optional[bool] = None
    state: Optional[dict] = None


class DeviceResponse(BaseModel):
    """Schema for device response"""
    id: int
    name: str
    device_type: str
    mqtt_topic: str
    location: Optional[str] = None
    state: Optional[Any] = None
    is_online: bool
    last_seen_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True