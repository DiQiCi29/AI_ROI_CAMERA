from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.routes import health, stream, auth, zones, alerts, logs, media, websocket, devices
from app.ai.detector import IntrusionDetector
from app.services.mqtt_client import mqtt_client
from app.services.mqtt_listener import mqtt_listener
import app.models
import logging

logger = logging.getLogger(__name__)

# Import exception handlers và FCM service
from app.core.exceptions import register_exception_handlers
from app.services.fcm_service import FCMService
from app.services.mqtt_service import MQTTService

# ── Alembic quản lý migration (chạy "alembic upgrade head" để cập nhật) ──
# create_all() vẫn giữ làm fallback cho lần chạy đầu tiên
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events - startup & shutdown"""
    
    # ════ STARTUP ════════════════════════════════════════════════════════
    logger.info("🚀 Starting AI_ROI_CAMERA Server...")
    
    # Connect to MQTT Broker
    try:
        mqtt_client.connect()
        await mqtt_listener.init_listeners()
        logger.info("✓ MQTT initialized successfully")
    except Exception as e:
        logger.error(f"✗ MQTT initialization failed: {str(e)}")
    
    yield  # Server running
    
    # ════ SHUTDOWN ═══════════════════════════════════════════════════════
    logger.info("🛑 Shutting down AI_ROI_CAMERA Server...")
    
    # Disconnect from MQTT
    try:
        mqtt_client.disconnect()
        logger.info("✓ MQTT disconnected")
    except Exception as e:
        logger.error(f"✗ MQTT disconnection error: {str(e)}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
    
    # Khởi tạo MQTT service cho IoT devices (ESP32, Arduino)
    MQTTService.initialize()
    
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
app.include_router(devices.router,   prefix=prefix)  # NEW: Device control
app.include_router(websocket.router)  # Không có prefix, dùng /ws trực tiếp

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Smart Home Server is running 🚀"}