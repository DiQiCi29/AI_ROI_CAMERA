"""
Script: Cập nhật camera vào MediaMTX qua API
Chạy script này sau khi thêm camera mới vào database.

Sử dụng MediaMTX API (port 9997) để add/update path động,
thay vì sửa file mediamtx.yml thủ công.

Cách dùng:
    python mediamtx/setup_camera.py          # Đồng bộ tất cả camera từ DB lên MediaMTX
    python mediamtx/setup_camera.py --id 1   # Chỉ đồng bộ camera ID=1
"""
import os
import sys
import json
import httpx

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.camera import Camera

MEDIAMTX_API = f"http://{settings.MEDIAMTX_HOST}:{settings.MEDIAMTX_PORT}"

def sync_camera_to_mediamtx(camera_id: int, rtsp_url: str):
    """Gửi request tới MediaMTX API để tạo path cho camera"""
    path_name = f"camera_{camera_id:02d}"
    
    payload = {
        "name": path_name,
        "source": rtsp_url,
        "sourceOnDemand": True,
        "sourceOnDemandStartTimeout": "15s",
        "sourceOnDemandCloseAfter": "60s",
    }
    
    try:
        r = httpx.post(
            f"{MEDIAMTX_API}/v3/config/paths/replace/{path_name}",
            json=payload,
            timeout=5
        )
        if r.status_code in (200, 201):
            print(f"  ✅ Camera {camera_id}: path '{path_name}' created/updated")
            return
        print(f"  ⚠️  Camera {camera_id}: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"  ❌ Camera {camera_id}: API error - {e}")

def sync_all():
    """Đồng bộ tất cả camera active từ DB lên MediaMTX"""
    db = SessionLocal()
    try:
        cameras = db.query(Camera).filter(Camera.is_active == True).all()
        if not cameras:
            print("Không có camera nào trong database.")
            return
        print(f"Đồng bộ {len(cameras)} camera lên MediaMTX...")
        for cam in cameras:
            sync_camera_to_mediamtx(cam.id, cam.rtsp_url)
    finally:
        db.close()

def sync_one(camera_id: int):
    """Đồng bộ 1 camera"""
    db = SessionLocal()
    try:
        cam = db.query(Camera).filter(Camera.id == camera_id).first()
        if not cam:
            print(f"Camera ID {camera_id} không tồn tại.")
            return
        sync_camera_to_mediamtx(cam.id, cam.rtsp_url)
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--id":
        sync_one(int(sys.argv[2]))
    else:
        sync_all()