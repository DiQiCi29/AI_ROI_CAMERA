import httpx
import subprocess
import numpy as np
import cv2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/stream", tags=["Camera Stream"])

MEDIAMTX_HOST = "localhost"
RTSP_URL = "rtsp://35639463:123@192.168.0.3:554/onvif1"


def open_ffmpeg_pipe(width=640, height=360, fps=10):
    """Mở FFmpeg subprocess đọc RTSP bằng UDP"""
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "udp",
        "-i", RTSP_URL,
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


def generate_plain_frames():
    """Stream thuần — không có AI"""
    proc = open_ffmpeg_pipe()
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


def generate_ai_frames(detector):
    """Stream có AI — vẽ ROI + bounding box người xâm nhập"""
    proc = open_ffmpeg_pipe(width=1280, height=720, fps=10)
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
def stream_video(current_user: User = Depends(get_current_user)):
    """Stream video thường (không AI)"""
    return StreamingResponse(
        generate_plain_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/video/ai")
def stream_video_ai(request: Request,
                    current_user: User = Depends(get_current_user)):
    """Stream video có AI — vẽ ROI và bounding box người xâm nhập"""
    detector = request.app.state.detector
    return StreamingResponse(
        generate_ai_frames(detector),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/snapshot")
def get_snapshot(current_user: User = Depends(get_current_user)):
    """Chụp 1 ảnh tĩnh từ camera"""
    cmd = [
        "ffmpeg", "-rtsp_transport", "udp",
        "-i", RTSP_URL,
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
async def stream_status(current_user: User = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"http://{MEDIAMTX_HOST}:9997/v3/paths/list", timeout=3)
            paths = r.json().get("items", [])
            cam = next((p for p in paths if p["name"] == "camera_01"), None)
            status = "online" if cam and cam.get("ready") else "offline"
    except Exception:
        status = "offline"
    return {"success": True, "data": {
        "camera_id": "cam_01", "status": status,
        "resolution": {"width": 1280, "height": 720}, "fps": 15,
    }}