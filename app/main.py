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

from app.core.exceptions import register_exception_handlers
from app.services.fcm_service import FCMService
# ❌ Bỏ import MQTTService — duplicate với mqtt_client, gây 2 connection

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events - startup & shutdown"""
    
    # ════ STARTUP ════════════════════════════════════════════════════════
    logger.info("🚀 Starting AI_ROI_CAMERA Server...")

    # ── AI Detector ───────────────────────────────────────────────────
    try:
        app.state.detector = IntrusionDetector(
            model_path="app/ai/yolov8s.pt",
            confidence=0.5
        )
        app.state.detector.update_roi([
            (0, 0), (1280, 0), (1280, 720), (0, 720)
        ])
        logger.info("✓ AI Detector ready")
    except Exception as e:
        logger.error(f"✗ AI Detector initialization failed: {str(e)}")

    # ── FCM ───────────────────────────────────────────────────────────
    try:
        FCMService.initialize()
        logger.info("✓ FCM Service initialized")
    except Exception as e:
        logger.error(f"✗ FCM initialization failed: {str(e)}")

    # ── MQTT ──────────────────────────────────────────────────────────
    # ✅ Connect trước, chờ connected (có timeout bên trong), rồi mới subscribe
    try:
        connected = mqtt_client.connect()
        if connected:
            await mqtt_listener.init_listeners()
            logger.info("✓ MQTT initialized successfully")
        else:
            logger.warning("⚠️  MQTT broker không khả dụng, bỏ qua listeners")
    except Exception as e:
        logger.error(f"✗ MQTT initialization failed: {str(e)}")

    yield  # ── Server running ──────────────────────────────────────────

    # ════ SHUTDOWN ═══════════════════════════════════════════════════════
    logger.info("🛑 Shutting down AI_ROI_CAMERA Server...")

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
    lifespan=lifespan  # ✅ Chỉ dùng lifespan, không dùng @on_event
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ────────────────────────────────────────
register_exception_handlers(app)

# ── Routes ────────────────────────────────────────────────────
prefix = "/api/v1"
app.include_router(health.router,    prefix=prefix)
app.include_router(auth.router,      prefix=prefix)
app.include_router(stream.router,    prefix=prefix)
app.include_router(zones.router,     prefix=prefix)
app.include_router(alerts.router,    prefix=prefix)
app.include_router(logs.router,      prefix=prefix)
app.include_router(media.router,     prefix=prefix)
app.include_router(devices.router,   prefix=prefix)
app.include_router(websocket.router)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Smart Home Server is running 🚀"}