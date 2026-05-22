import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    force=True
)

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.v1.routes import health, stream, auth, zones, alerts, logs, media, websocket, devices, alarm
from app.ai.detector import IntrusionDetector
from app.services.mqtt_client import mqtt_client
from app.services.mqtt_listener import mqtt_listener
from app.api.v1.routes import monitoring
import app.models
import logging

logger = logging.getLogger(__name__)

from app.core.exceptions import register_exception_handlers
from app.services.fcm_service import FCMService
from app.models.zone import Zone
from app.models.camera import Camera
from app.services.ai_worker import AIWorker

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting AI_ROI_CAMERA Server...")

    # 1. Khởi tạo FCM
    try:
        FCMService.initialize()
        logger.info("✓ FCM Service initialized")
    except Exception as e:
        logger.error(f"✗ FCM initialization failed: {str(e)}")

    # 2. Kết nối MQTT broker TRƯỚC khi khởi tạo detector
    mqtt_connected = mqtt_client.connect()
    if mqtt_connected:
        logger.info("✓ MQTT broker connected")
        # Khởi động listener để nhận status từ ESP32 và alert từ AI
        await mqtt_listener.init_listeners()
    else:
        logger.warning("⚠️  MQTT broker không kết nối được — tiếp tục không có MQTT")

    # 3. Khởi tạo AI Detector — FIX: truyền mqtt_client vào
    try:
        app.state.detector = IntrusionDetector(
            model_path="app/ai/yolov8s.pt",
            confidence=0.5,
            mqtt_client=mqtt_client if mqtt_connected else None,  # FIX
        )
        app.state.monitoring_active = True
        logger.info("✓ AI Detector ready")
    except Exception as e:
        logger.error(f"✗ AI Detector initialization failed: {str(e)}")
        yield
        return

    # 4. Phục hồi zones + khởi động AI Worker
    db = SessionLocal()
    try:
        active_zones = db.query(Zone).filter(Zone.is_active == True).all()

        if active_zones:
            multi_rois_norm = []
            for zone in active_zones:
                coords_norm = [(float(c["x"]), float(c["y"])) for c in zone.coordinates]
                multi_rois_norm.append(coords_norm)
            app.state.detector.update_multi_roi(multi_rois_norm)
            logger.info(f"✓ Restored {len(multi_rois_norm)} active zones from DB")
        else:
            app.state.detector.update_multi_roi([
                [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
            ])
            logger.info("✓ Default ROI applied")

        camera = db.query(Camera).filter(Camera.is_active == True).first()
        cam_id = camera.id if camera else 1

        rtsp_url = "rtsp://127.0.0.1:8554/camera_01"

        app.state.ai_worker = AIWorker(
            detector=app.state.detector,
            rtsp_url=rtsp_url,
            camera_id=cam_id
        )
        app.state.ai_worker.start()
        logger.info(f"✓ AI Worker started for camera {cam_id}")

    except Exception as e:
        logger.error(f"⚠️ Failed to start AI Worker: {str(e)}")
    finally:
        db.close()

    yield  # ── SERVER ĐANG CHẠY ──

    # 5. Dọn dẹp
    logger.info("🛑 Shutting down...")
    if hasattr(app.state, 'ai_worker'):
        app.state.ai_worker.stop()
    mqtt_client.disconnect()


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

register_exception_handlers(app)

prefix = "/api/v1"
app.include_router(health.router,   prefix=prefix)
app.include_router(auth.router,     prefix=prefix)
app.include_router(stream.router,   prefix=prefix)
app.include_router(zones.router,    prefix=prefix)
app.include_router(alerts.router,   prefix=prefix)
app.include_router(logs.router,     prefix=prefix)
app.include_router(media.router,    prefix=prefix)
app.include_router(devices.router,  prefix=prefix)
app.include_router(alarm.router,    prefix=prefix)
app.include_router(monitoring.router, prefix=prefix)
app.include_router(websocket.router)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Smart Home Server is running 🚀"}