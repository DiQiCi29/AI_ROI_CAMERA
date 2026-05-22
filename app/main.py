import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── CẤU HÌNH LOGGING ÉP BUỘC (TẮT RÁC SQL) ────────────────────
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    force=True
)
# ─────────────────────────────────────────────────────────────

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.v1.routes import health, stream, auth, zones, alerts, logs, media, websocket, devices,alarm
from app.ai.detector import IntrusionDetector
from app.services.mqtt_client import mqtt_client
from app.services.mqtt_listener import mqtt_listener
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
    """Quản lý các tiến trình khởi động và tắt server"""
    print("🚀 Starting AI_ROI_CAMERA Server...")
    
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
    # try:
    #     connected = mqtt_client.connect()
    #     if connected:
    #         await mqtt_listener.init_listeners()
    #         print("✓ MQTT initialized successfully")
    #     else:
    #         logger.warning("⚠️  MQTT broker không khả dụng, bỏ qua listeners")
    # except Exception as e:
    #     print(f"✗ MQTT initialization failed: {str(e)}")

    # 2. Khởi tạo FCM & Hardware Services
    FCMService.initialize()
    # MQTTService.initialize()

    # 3. Khởi tạo AI Detector
    app.state.detector = IntrusionDetector(
        model_path="app/ai/yolov8s.pt",
        confidence=0.5
    )
    print("✓ AI Detector ready!")

    # 4. Phục hồi vùng Zone & Bật AI Worker chạy ngầm
    db = SessionLocal()
    try:
        active_zone = db.query(Zone).filter(Zone.is_active == True).order_by(Zone.id.desc()).first()
        if active_zone:
            coords_norm = [(float(c["x"]), float(c["y"])) for c in active_zone.coordinates]
            app.state.detector.update_roi(coords_norm)
            print(f"✓ Restored ROI from DB: {active_zone.name}")
        else:
            app.state.detector.update_roi([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
            print("✓ Default ROI applied")

        camera = db.query(Camera).filter(Camera.is_active == True).first()
        cam_id = camera.id if camera else 1
        
        # THAY ĐỔI Ở ĐÂY: 
        # Bắt OpenCV phải đọc từ MediaMTX (localhost:8554) thay vì đọc từ Camera.
        # Dựa vào file mediamtx.yml của bạn, luồng được đặt tên là "camera_01"
        rtsp_url = "rtsp://127.0.0.1:8554/camera_01"
        
        # BẬT AI WORKER
        app.state.ai_worker = AIWorker(
            detector=app.state.detector,
            rtsp_url=rtsp_url, # AI bây giờ đọc từ localhost
            camera_id=cam_id
        )
        app.state.ai_worker.start()
        print(f"✓ AI Worker started successfully for camera {cam_id}!")

    except Exception as e:
        print(f"⚠️ [Server] Failed to start AI Worker: {str(e)}")
    finally:
        db.close()

    yield  # ─── SERVER ĐANG CHẠY ───

    # 5. Dọn dẹp khi tắt server
    print("🛑 Shutting down AI_ROI_CAMERA Server...")
    # try:
    #     mqtt_client.disconnect()
    # except Exception:
    #     pass
    
    if hasattr(app.state, 'ai_worker'):
        app.state.ai_worker.stop()

# Khởi tạo App với lifespan
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

# Routes────
prefix = "/api/v1"
app.include_router(health.router,    prefix=prefix)
app.include_router(auth.router,      prefix=prefix)
app.include_router(stream.router,    prefix=prefix)
app.include_router(zones.router,     prefix=prefix)
app.include_router(alerts.router,    prefix=prefix)
app.include_router(logs.router,      prefix=prefix)
app.include_router(media.router,     prefix=prefix)
app.include_router(devices.router,   prefix=prefix)
app.include_router(alarm.router, prefix=prefix)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Smart Home Server is running 🚀"}