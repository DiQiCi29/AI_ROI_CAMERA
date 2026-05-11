from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class ZoneType(str, enum.Enum):
    polygon   = "polygon"
    rectangle = "rectangle"

class Zone(Base):
    __tablename__ = "zones"

    id          = Column(Integer, primary_key=True, index=True)
    camera_id   = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name        = Column(String(100), nullable=False)     # VD: "Vùng cấm cửa chính"
    zone_type   = Column(Enum(ZoneType), default=ZoneType.polygon)
    coordinates = Column(JSON, nullable=False)
    # VD polygon:   [{"x": 10, "y": 20}, {"x": 50, "y": 20}, ...]
    # VD rectangle: {"x": 10, "y": 20, "width": 100, "height": 80}
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())