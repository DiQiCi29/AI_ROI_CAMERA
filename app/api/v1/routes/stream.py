import httpx
import subprocess
import numpy as np
import cv2
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/stream", tags=["Camera Stream"])

MEDIAMTX_HOST = "localhost"
RTSP_URL = "rtsp://35639463:123@192.168.0.3:554/onvif1"
WIDTH, HEIGHT = 1280, 720


def open_ffmpeg_pipe():
    """Mở FFmpeg subprocess đọc RTSP bằng UDP, xuất raw frames"""
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "udp",       # Ép UDP — phù hợp với camera này
        "-i", RTSP_URL,
        "-vf", "scale=640:360",          # Resize nhỏ để tiết kiệm băng thông
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",             # Định dạng OpenCV đọc được
        "-r", "10",                      # Giới hạn 10 FPS cho mobile
        "-an",                           # Bỏ audio
        "pipe:1"                         # Xuất ra stdout
    ]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,       # Bỏ log FFmpeg
        bufsize=10**8
    )


def generate_mjpeg_frames():
    """Generator yield từng JPEG frame cho MJPEG stream"""
    proc = open_ffmpeg_pipe()
    frame_size = 640 * 360 * 3          # width * height * BGR channels

    try:
        while True:
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size:
                break

            frame = np.frombuffer(raw, dtype=np.uint8).reshape((360, 640, 3))
            _, buffer = cv2.imencode(
                ".jpg", frame,
                [cv2.IMWRITE_JPEG_QUALITY, 70]
            )
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )
    finally:
        proc.kill()


def capture_snapshot() -> bytes:
    """Chụp 1 frame từ camera bằng FFmpeg"""
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "udp",
        "-i", RTSP_URL,
        "-frames:v", "1",               # Chỉ lấy 1 frame
        "-f", "image2",
        "-vcodec", "mjpeg",
        "pipe:1"
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10
    )
    return proc.stdout


# ─────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────

@router.get("/video")
def stream_video(current_user: User = Depends(get_current_user)):
    return StreamingResponse(
        generate_mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/snapshot")
def get_snapshot(current_user: User = Depends(get_current_user)):
    try:
        data = capture_snapshot()
        if not data:
            raise ValueError("Empty frame")
    except Exception:
        raise HTTPException(status_code=503, detail={
            "code": "CAMERA_OFFLINE",
            "message": "Không thể lấy ảnh từ camera"
        })
    return Response(content=data, media_type="image/jpeg")


@router.get("/status")
async def stream_status(current_user: User = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"http://{MEDIAMTX_HOST}:9997/v3/paths/list", timeout=3
            )
            paths = r.json().get("items", [])
            cam = next((p for p in paths if p["name"] == "camera_01"), None)
            status = "online" if cam and cam.get("ready") else "offline"
    except Exception:
        status = "offline"
    return {"success": True, "data": {
        "camera_id": "cam_01", "status": status,
        "resolution": {"width": 1280, "height": 720}, "fps": 15,
    }}


@router.get("/urls")
async def get_stream_urls(current_user: User = Depends(get_current_user)):
    return {"success": True, "data": {
        "camera_id": "camera_01",
        "mjpeg": "http://SERVER_IP:8000/api/v1/stream/video",
        "rtsp":  f"rtsp://{MEDIAMTX_HOST}:8554/camera_01",
        "hls":   f"http://{MEDIAMTX_HOST}:8888/camera_01",
    }}