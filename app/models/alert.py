from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id              = Column(Integer, primary_key=True, index=True)
    camera_id       = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    zone_id         = Column(Integer, ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    thumbnail_path  = Column(String(255))       # Đường dẫn ảnh chụp đối tượng
    video_clip_path = Column(String(255))       # Đường dẫn video clip ngắn
    bounding_boxes  = Column(JSON)
    # VD: [{"x":10,"y":20,"w":50,"h":80,"label":"person","confidence":0.95}]
    confidence      = Column(Float)             # Score cao nhất trong frame
    detected_at     = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_acknowledged = Column(Integer, default=0) # 0=chưa xem, 1=đã xem