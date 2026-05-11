from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    alert_id   = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)
    title      = Column(String(150), nullable=False)
    body       = Column(Text)
    is_success = Column(Boolean, default=True)   # FCM gửi thành công hay thất bại
    error_msg  = Column(String(255))             # Lý do nếu thất bại
    sent_at    = Column(DateTime(timezone=True), server_default=func.now())