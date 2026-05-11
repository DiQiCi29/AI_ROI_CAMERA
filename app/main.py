from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.routes import health

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",       # Swagger UI tại đây
    redoc_url="/redoc",
)

# Đăng ký router
app.include_router(health.router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Server is running 🚀"}