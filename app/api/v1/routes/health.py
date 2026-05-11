from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

@router.get("/hello", tags=["System"])
async def hello_world():
    return {"message": "Hello from Smart Home Server!"}