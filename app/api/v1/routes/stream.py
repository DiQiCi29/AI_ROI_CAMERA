from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from app.core.dependencies import get_current_user
from app.models.user import User
import httpx, asyncio

router = APIRouter(prefix="/stream", tags=["Camera Stream"])

MEDIAMTX_HOST = "localhost"
CAMERA_RTSP = "rtsp://35639463:123@192.168.0.2:554/onvif1"

@router.get("/status")
async def stream_status(current_user: User = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"http://{MEDIAMTX_HOST}:9997/v3/paths/list", timeout=3)
            paths = r.json().get("items", [])
            cam = next((p for p in paths if p["name"] == "camera_01"), None)
            status = "online" if cam and cam.get("ready") else "offline"
    except Exception:
        status = "offline"
    return {"success": True, "data": {
        "camera_id": "cam_01", "status": status,
        "resolution": {"width": 1920, "height": 1080}, "fps": 15,
    }}

@router.get("/urls")
async def get_stream_urls(current_user: User = Depends(get_current_user)):
    return {"success": True, "data": {
        "camera_id": "camera_01",
        "rtsp": f"rtsp://{MEDIAMTX_HOST}:8554/camera_01",
        "hls": f"http://{MEDIAMTX_HOST}:8888/camera_01",
        "webrtc": f"http://{MEDIAMTX_HOST}:8889/camera_01",
    }}