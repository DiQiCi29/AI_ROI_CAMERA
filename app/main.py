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
    logger.info("🚀 Starting AI_ROI_CAMERA Server...")

    # 1. Khởi tạo FCM Service
    try:
        FCMService.initialize()
        logger.info("✓ FCM Service initialized")
    except Exception as e:
        logger.error(f"✗ FCM initialization failed: {str(e)}")

    # 2. Khởi tạo AI Detector
    try:
        app.state.detector = IntrusionDetector(
            model_path="app/ai/yolov8s.pt",
            confidence=0.5
        )
        logger.info("✓ AI Detector ready")
    except Exception as e:
        logger.error(f"✗ AI Detector initialization failed: {str(e)}")
        yield
        return

    # 3. Phục hồi TẤT CẢ vùng Zone đang active từ DB & Bật AI Worker
    db = SessionLocal()
    try:
        active_zones = db.query(Zone).filter(Zone.is_active == True).all()
        
        if active_zones:
            multi_rois_norm = []
            for zone in active_zones:
                coords_norm = [(float(c["x"]), float(c["y"])) for c in zone.coordinates]
                multi_rois_norm.append(coords_norm)
            
            # GỌI ĐÚNG HÀM MỚI VÀ TRUYỀN VÀO MẢNG 2 CHIỀU (Danh sách các Zone)
            app.state.detector.update_multi_roi(multi_rois_norm)
            logger.info(f"✓ Restored {len(multi_rois_norm)} active zones from DB")
        else:
            # Gửi 1 Zone bao phủ toàn màn hình làm mặc định
            app.state.detector.update_multi_roi([ [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)] ])
            logger.info("✓ Default ROI applied")

        # Khởi tạo AI Worker
        camera = db.query(Camera).filter(Camera.is_active == True).first()
        cam_id = camera.id if camera else 1
        
        rtsp_url = "rtsp://127.0.0.1:8554/camera_01"
        
        app.state.ai_worker = AIWorker(
            detector=app.state.detector,
            rtsp_url=rtsp_url,
            camera_id=cam_id
        )
        app.state.ai_worker.start()
        logger.info(f"✓ AI Worker started successfully for camera {cam_id}!")

    except Exception as e:
        logger.error(f"⚠️ [Server] Failed to start AI Worker: {str(e)}")
    finally:
        db.close()

    yield  # ─── SERVER ĐANG CHẠY ───

    # 4. Dọn dẹp khi tắt server
    logger.info("🛑 Shutting down AI_ROI_CAMERA Server...")
    
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