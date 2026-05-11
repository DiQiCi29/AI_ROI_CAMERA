from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class DeviceType(str, enum.Enum):
    light  = "light"
    siren  = "siren"
    relay  = "relay"
    sensor = "sensor"

class Device(Base):
    __tablename__ = "devices"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)      # VD: "Đèn phòng khách"
    device_type = Column(Enum(DeviceType), nullable=False)
    mqtt_topic  = Column(String(150), unique=True, nullable=False)
    # VD: "home/livingroom/light"
    location    = Column(String(100))
    state       = Column(JSON, default={"power": "off"})   # Trạng thái hiện tại
    is_online   = Column(Boolean, default=False)
    last_seen_at = Column(DateTime(timezone=True))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())