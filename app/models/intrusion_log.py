from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class IntrusionLog(Base):
    __tablename__ = "intrusion_logs"

    id               = Column(Integer, primary_key=True, index=True)
    alert_id         = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    camera_id        = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    entered_at       = Column(DateTime(timezone=True), nullable=False)
    exited_at        = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)          # Tính khi exited_at được cập nhật
    created_at       = Column(DateTime(timezone=True), server_default=func.now())