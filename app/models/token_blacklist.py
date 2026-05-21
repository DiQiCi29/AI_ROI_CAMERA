from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id          = Column(Integer, primary_key=True, index=True)
    token_jti   = Column(String(255), unique=True, nullable=False, index=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())