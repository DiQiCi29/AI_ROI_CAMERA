from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class ZoneType(str, enum.Enum):
    polygon   = "polygon"
    rectangle = "rectangle"

class Zone(Base):
    __tablename__ = "zones"

    id                    = Column(Integer, primary_key=True, index=True)
    camera_id             = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name                  = Column(String(100), nullable=False)
    zone_type             = Column(Enum(ZoneType), default=ZoneType.polygon)
    coordinates           = Column(JSON, nullable=False)
    is_active             = Column(Boolean, default=True)
    alert_cooldown_seconds = Column(Integer, default=30)   # ← thêm dòng này
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    # updated_at            = Column(DateTime(timezone=True), onupdate=func.now())