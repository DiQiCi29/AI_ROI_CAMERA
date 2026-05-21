import httpx
import itertools
import logging
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


def open_ffmpeg_pipe(rtsp_url: str, width=640, height=360, fps=10, transport="udp", timeout_us=5000000):
    """Mở FFmpeg subprocess đọc RTSP bằng transport chỉ định."""
    cmd = [
        "ffmpeg",
        "-rtsp_transport", transport,
        "-stimeout", str(timeout_us),
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


def open_cv_capture(rtsp_url: str, width=640, height=360, fps=10):
    """Mở OpenCV VideoCapture với buffer tối thiểu cho low latency"""
    # Thử multiple RTSP transport protocols
    for protocol in ["udp", "tcp"]:
        try:
            # Build RTSP URL with transport protocol
            rtsp_url_with_transport = f"{rtsp_url}?transport={protocol}"
            cap = cv2.VideoCapture(rtsp_url_with_transport, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer for low latency
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
            
            # Test if capture is actually working
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"[OpenCV] Stream opened with {protocol}: {rtsp_url}, buffer_size=1")
                    return cap
                else:
                    cap.release()
        except Exception as e:
            print(f"[OpenCV] Failed with {protocol}: {e}")
            if 'cap' in locals():
                cap.release()
    
    # Fallback: try without explicit transport
    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        
        if cap.isOpened():
            print(f"[OpenCV] Stream opened (fallback): {rtsp_url}, buffer_size=1")
            return cap
    except Exception as e:
        print(f"[OpenCV] Fallback also failed: {e}")
    
    raise RuntimeError(f"Cannot open RTSP stream: {rtsp_url} with any protocol")


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


def generate_ai_frames(detector, rtsp_url: str, width=640, height=360, fps=10, transport="udp"):
    """Stream có AI — vẽ ROI + bounding box người xâm nhập"""
    proc = open_ffmpeg_pipe(rtsp_url, width=width, height=height, fps=fps, transport=transport)
    frame_size = width * height * 3
    try:
        while True:
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size:
                break

            frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
            output = detector.process_frame(frame)
            annotated = detector.draw_frame(frame, output)
            annotated = cv2.resize(annotated, (640, 360))
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


def generate_ai_frames_cv(detector, cap):
    """Stream AI với OpenCV direct capture cho low latency"""
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[OpenCV] Failed to read frame")
                break

            # ── Chạy AI với optimization ROI-based ───────────
            output = detector.process_frame(frame)

            # ── Vẽ annotation lên frame ───────────────────────
            annotated = detector.draw_frame(frame, output)

            # ── Resize cho mobile ────────────────────────────
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
        cap.release()


def get_ai_frame_generator(detector, rtsp_url: str):
    """Try OpenCV direct capture first; fallback to FFmpeg with transport fallback."""
    try:
        cap = open_cv_capture(rtsp_url, width=640, height=360, fps=10)
        return generate_ai_frames_cv(detector, cap)
    except RuntimeError as exc:
        logging.warning("OpenCV RTSP capture failed, falling back to FFmpeg AI stream: %s", exc)

    transports = ["tcp", "udp"]
    last_error = None
    for transport in transports:
        gen = generate_ai_frames(detector, rtsp_url, width=640, height=360, fps=10, transport=transport)
        try:
            first_chunk = next(gen)
            return itertools.chain([first_chunk], gen)
        except RuntimeError as exc:
            last_error = exc
            logging.warning("FFmpeg AI stream failed using transport=%s: %s", transport, exc)
            continue
    raise HTTPException(status_code=503, detail={
        "code": "CAMERA_STREAM_UNAVAILABLE",
        "message": "Không thể mở luồng AI từ camera. Vui lòng kiểm tra kết nối RTSP hoặc cấu hình camera."
    })


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
def stream_video_ai(request: Request,
                    camera_id: int = Query(1, ge=1, description="Camera ID"),
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Stream video có AI — vẽ ROI và bounding box người xâm nhập"""
    rtsp_url = get_camera_rtsp_url(camera_id, db)
    detector = request.app.state.detector
    generator = get_ai_frame_generator(detector, rtsp_url)
    return StreamingResponse(
        generator,
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
    
    # Query MediaMTX API để kiểm tra trạng thái
    status = "offline"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"http://{settings.MEDIAMTX_HOST}:{settings.MEDIAMTX_PORT}/v3/paths/list", 
                timeout=3)
            paths = r.json().get("items", [])
            # Duyệt tất cả paths, match linh hoạt camera_<id> (hỗ trợ cả camera_1, camera_01)
            cam = next((p for p in paths 
                       if p["name"] == f"camera_{camera_id}" 
                       or p["name"] == f"camera_{camera_id:02d}"), None)
            if cam and cam.get("ready"):
                status = "online"
    except Exception:
        pass
    
    # Nếu MediaMTX không có path nhưng camera đang active thì vẫn báo online
    if status == "offline" and camera.is_active and camera.rtsp_url:
        status = "connecting"
    
    return {"success": True, "data": {
        "camera_id": camera_id, 
        "camera_name": camera.name,
        "status": status,
        "resolution": camera.resolution or "1280x720", 
        "fps": 15,
        "stream_urls": {
            "hls": f"http://{settings.MEDIAMTX_HOST}:8888/camera_{camera_id:02d}/index.m3u8",
            "webrtc": f"http://{settings.MEDIAMTX_HOST}:8889/camera_{camera_id:02d}/whep",
            "rtsp": f"rtsp://{settings.MEDIAMTX_HOST}:8554/camera_{camera_id:02d}",
        }
    }}


@router.get("/urls")
def get_stream_urls(camera_id: int = Query(1, ge=1, description="Camera ID"),
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """
    Trả về HLS/WebRTC/RTSP URLs cho camera — app Android dùng HLS hoặc WebRTC
    để xem stream mượt mà, giảm độ trễ
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail={
            "code": "CAMERA_NOT_FOUND",
            "message": f"Camera with ID {camera_id} not found"
        })
    
    return {"success": True, "data": {
        "camera_id": camera_id,
        "camera_name": camera.name,
        "hls": f"http://{settings.MEDIAMTX_HOST}:8888/camera_{camera_id:02d}/index.m3u8",
        "webrtc": f"http://{settings.MEDIAMTX_HOST}:8889/camera_{camera_id:02d}/whep",
        "mjpeg": f"{settings.MEDIAMTX_HOST}:8889/camera_{camera_id:02d}/whep",
        "snapshot": f"/api/v1/stream/snapshot?camera_id={camera_id}",
    }}


@router.get("/list")
def list_cameras(current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Liệt kê tất cả camera kèm stream URLs"""
    cameras = db.query(Camera).filter(Camera.is_active == True).all()
    return {"success": True, "data": [
        {
            "camera_id": cam.id,
            "camera_name": cam.name,
            "location": cam.location,
            "status": "online" if cam.status.value == "online" else "offline",
            "resolution": cam.resolution or "1280x720",
            "stream_urls": {
                "hls": f"http://{settings.MEDIAMTX_HOST}:8888/camera_{cam.id:02d}/index.m3u8",
                "webrtc": f"http://{settings.MEDIAMTX_HOST}:8889/camera_{cam.id:02d}/whep",
            }
        }
        for cam in cameras
    ]}