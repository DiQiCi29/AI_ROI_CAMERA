from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

db = SessionLocal()
admin = User(
    username="admin",
    email="admin@example.com",
    hashed_password=hash_password("123456"),
    role="admin",
    is_active=True
)
db.add(admin)
db.commit()
print("✅ Admin created: admin / 123456")
db.close()