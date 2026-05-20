from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.routes import health, stream, auth, zones, alerts, logs, media, websocket
from app.ai.detector import IntrusionDetector
import app.models

# Import exception handlers và FCM service
from app.core.exceptions import register_exception_handlers
from app.services.fcm_service import FCMService

# ── Alembic quản lý migration (chạy "alembic upgrade head" để cập nhật) ──
# create_all() vẫn giữ làm fallback cho lần chạy đầu tiên
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Khởi tạo AI detector và các service khác ──────────────────
@app.on_event("startup")
async def startup_event():
    app.state.detector = IntrusionDetector(
        model_path="app/ai/yolov8s.pt",
        confidence=0.5
    )
    # ROI mặc định = toàn bộ khung hình 1280x720
    app.state.detector.update_roi([
        (0, 0), (1280, 0), (1280, 720), (0, 720)
    ])
    print("[Server] AI Detector ready!")
    
    # Khởi tạo FCM service
    FCMService.initialize()
    print("Application startup complete")


# ── Đăng ký Exception Handlers ────────────────────────────────
register_exception_handlers(app)

# ── Routes ────────────────────────────────────────────────
prefix = "/api/v1"
app.include_router(health.router,     prefix=prefix)
app.include_router(auth.router,       prefix=prefix)
app.include_router(stream.router,     prefix=prefix)
app.include_router(zones.router,      prefix=prefix)
app.include_router(alerts.router,     prefix=prefix)
app.include_router(logs.router,       prefix=prefix)
app.include_router(media.router,      prefix=prefix)
app.include_router(websocket.router)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Smart Home Server is running 🚀"}