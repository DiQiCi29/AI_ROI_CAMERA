from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Float
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class CameraStatus(str, enum.Enum):
    online  = "online"
    offline = "offline"

class Camera(Base):
    __tablename__ = "cameras"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False)        # VD: "Camera Cổng"
    rtsp_url     = Column(String(255), nullable=False)        # VD: rtsp://192.168.1.10/stream
    location     = Column(String(100))                        # VD: "Sân trước"
    resolution   = Column(String(20), default="1920x1080")    # VD: "1280x720"
    status       = Column(Enum(CameraStatus), default=CameraStatus.offline)
    is_active    = Column(Boolean, default=True)
    last_seen_at = Column(DateTime(timezone=True))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())