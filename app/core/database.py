from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,        # In SQL ra terminal khi DEBUG=True
    pool_pre_ping=True,         # Tự kiểm tra kết nối trước mỗi query
    pool_recycle=3600,          # Tái sử dụng connection sau 1 giờ
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Dependency dùng trong FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()