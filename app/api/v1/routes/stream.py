import httpx
import subprocess
import numpy as np
import cv2
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.camera import Camera

router = APIRouter(prefix="/stream", tags=["Camera Stream"])


def get_camera_rtsp_url(camera_id: int, db: Session) -> str:
    """Fetch RTSP URL from database for the given camera"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail={
            "code": "CAMERA_NOT_FOUND",
            "message": f"Camera with ID {camera_id} not found"
        })
    if not camera.is_active:
        raise HTTPException(status_code=503, detail={
            "code": "CAMERA_OFFLINE",
            "message": f"Camera {camera.name} is not active"
        })
    return camera.rtsp_url


def open_ffmpeg_pipe(rtsp_url: str, width=640, height=360, fps=10):
    """Mở FFmpeg subprocess đọc RTSP bằng UDP"""
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "udp",
        "-i", rtsp_url,
        "-vf", f"scale={width}:{height}",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-an",
        "pipe:1"
    ]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10**8
    )


def generate_plain_frames(rtsp_url: str):
    """Stream thuần — không có AI"""
    proc = open_ffmpeg_pipe(rtsp_url)
    frame_size = 640 * 360 * 3
    try:
        while True:
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size:
                break
            frame = np.frombuffer(raw, dtype=np.uint8).reshape((360, 640, 3))
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )
    finally:
        proc.kill()


def generate_ai_frames(detector, rtsp_url: str):
    """Stream có AI — vẽ ROI + bounding box người xâm nhập"""
    proc = open_ffmpeg_pipe(rtsp_url, width=1280, height=720, fps=10)
    frame_size = 1280 * 720 * 3
    try:
        while True:
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size:
                break

            # Đọc frame gốc
            frame = np.frombuffer(raw, dtype=np.uint8).reshape((720, 1280, 3))

            # ── Chạy AI ──────────────────────────────────────
            output = detector.process_frame(frame)

            # ── Vẽ annotation lên frame ───────────────────────
            annotated = detector.draw_frame(frame, output)

            # ── Resize nhỏ lại trước khi gửi mobile ──────────
            annotated = cv2.resize(annotated, (640, 360))

            # ── Encode JPEG ───────────────────────────────────
            _, buffer = cv2.imencode(
                ".jpg", annotated,
                [cv2.IMWRITE_JPEG_QUALITY, 75]
            )
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )
    finally:
        proc.kill()


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/video")
def stream_video(camera_id: int = Query(1, ge=1, description="Camera ID"),
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Stream video thường (không AI)"""
    rtsp_url = get_camera_rtsp_url(camera_id, db)
    return StreamingResponse(
        generate_plain_frames(rtsp_url),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/video/ai")
def stream_video_ai(camera_id: int = Query(1, ge=1, description="Camera ID"),
                    request: Request = None,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Stream video có AI — vẽ ROI và bounding box người xâm nhập"""
    rtsp_url = get_camera_rtsp_url(camera_id, db)
    detector = request.app.state.detector
    return StreamingResponse(
        generate_ai_frames(detector, rtsp_url),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/snapshot")
def get_snapshot(camera_id: int = Query(1, ge=1, description="Camera ID"),
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Chụp 1 ảnh tĩnh từ camera"""
    rtsp_url = get_camera_rtsp_url(camera_id, db)
    cmd = [
        "ffmpeg", "-rtsp_transport", "udp",
        "-i", rtsp_url,
        "-frames:v", "1",
        "-f", "image2", "-vcodec", "mjpeg", "pipe:1"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, timeout=10)
    if not proc.stdout:
        raise HTTPException(status_code=503, detail={
            "code": "CAMERA_OFFLINE",
            "message": "Không thể lấy ảnh từ camera"
        })
    return Response(content=proc.stdout, media_type="image/jpeg")


@router.get("/status")
async def stream_status(camera_id: int = Query(1, ge=1, description="Camera ID"),
                       current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Check camera and MediaMTX status"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail={
            "code": "CAMERA_NOT_FOUND",
            "message": f"Camera with ID {camera_id} not found"
        })
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"http://{settings.MEDIAMTX_HOST}:{settings.MEDIAMTX_PORT}/v3/paths/list", 
                timeout=3)
            paths = r.json().get("items", [])
            cam = next((p for p in paths if p["name"] == f"camera_{camera_id}"), None)
            status = "online" if cam and cam.get("ready") else "offline"
    except Exception:
        status = "offline"
    
    return {"success": True, "data": {
        "camera_id": camera_id, 
        "camera_name": camera.name,
        "status": status,
        "resolution": camera.resolution or "1280x720", 
        "fps": 15,
    }}