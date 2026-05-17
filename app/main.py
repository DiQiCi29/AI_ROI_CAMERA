from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.routes import health, stream, auth, zones, alerts, logs, media, websocket
import app.models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS cho Flutter app
app.add_middleware(
    CORSMiddleware,
    
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký tất cả routes
prefix = "/api/v1"
app.include_router(health.router,     prefix=prefix)
app.include_router(auth.router,       prefix=prefix)
app.include_router(stream.router,     prefix=prefix)
app.include_router(zones.router,      prefix=prefix)
app.include_router(alerts.router,     prefix=prefix)
app.include_router(logs.router,       prefix=prefix)
app.include_router(media.router,      prefix=prefix)
app.include_router(websocket.router)  # Không có prefix, dùng /ws trực tiếp

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Smart Home Server is running 🚀"}