# 🔧 Hướng Dẫn Sửa Backend Để Khớp Với Thiết Kế

**Cách sửa dự án AI_ROI_CAMERA để tuân thủ API_DESIGN.md**

---

## 🎯 Priority 1: CRITICAL - WebSocket Real-time Events

### Vấn đề:
- Thiếu `intrusion_detected` event → App không nhận real-time alerts
- Thiếu `intrusion_ended` event → Không biết khi nào xâm nhập kết thúc
- Thiếu `camera_status_changed` event → Không detect camera offline

### Giải pháp:

#### Bước 1: Tạo Alert Detection Service
Tạo file `app/services/detection_service.py`:

```python
from app.services.websocket import broadcast_event
from datetime import datetime
import asyncio

async def handle_intrusion_detected(alert):
    """Gửi event intrusion_detected qua WebSocket"""
    await broadcast_event("intrusion_detected", {
        "alert_id": str(alert.id),
        "zone_id": str(alert.zone_id) if alert.zone_id else None,
        "camera_id": str(alert.camera_id) if alert.camera_id else None,
        "detected_at": alert.detected_at.isoformat(),
        "object_count": len(alert.bounding_boxes) if alert.bounding_boxes else 1,
        "confidence": float(alert.confidence),
        "thumbnail_url": f"/api/v1/media/alerts/{alert.id}/thumbnail" if alert.thumbnail_path else None,
        "bounding_boxes": alert.bounding_boxes or []
    })

async def handle_intrusion_ended(alert, exited_at):
    """Gửi event intrusion_ended qua WebSocket"""
    duration = (exited_at - alert.detected_at).total_seconds()
    await broadcast_event("intrusion_ended", {
        "alert_id": str(alert.id),
        "zone_id": str(alert.zone_id) if alert.zone_id else None,
        "exited_at": exited_at.isoformat(),
        "duration_seconds": int(duration),
        "video_url": f"/api/v1/media/alerts/{alert.id}/video" if alert.video_clip_path else None
    })

async def handle_camera_status_changed(camera_id, status):
    """Gửi event camera_status_changed qua WebSocket"""
    await broadcast_event("camera_status_changed", {
        "camera_id": camera_id,
        "status": status,  # "online" | "offline"
        "timestamp": datetime.utcnow().isoformat()
    })
```

#### Bước 2: Cập nhật WebSocket để hỗ trợ ACK
File `app/api/v1/routes/websocket.py`:

```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    connected_clients.append(websocket)

    # Send connection confirmation
    await websocket.send_json({
        "event": "connected",
        "data": {
            "message": "WebSocket connected successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            event = msg.get("event")

            if event == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                })
            
            elif event == "subscribe_camera":
                # Store subscription info if needed
                await websocket.send_json({
                    "event": "subscribe_camera_ack",
                    "data": msg.get("data", {})
                })
            
            elif event == "unsubscribe_camera":
                await websocket.send_json({
                    "event": "unsubscribe_camera_ack",
                    "data": msg.get("data", {})
                })
                
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
```

---

## 🎯 Priority 2: HIGH - Stream API

### Vấn đề:
Thiết kế yêu cầu `/stream/video` (MJPEG), nhưng backend thay thế bằng `/stream/urls`

### Lựa chọn Giải pháp:

**Option A: Giữ nguyên (Khuyến nghị)** ✅
- Lý do: RTSP/HLS tốt hơn MJPEG cho mobile (hỗ trợ adaptive bitrate, hardware decoding)
- Cách: Cập nhật Flutter app để parse `/stream/urls` thay vì stream `/stream/video`
- Không cần sửa backend

**Option B: Thêm MJPEG support**
- Nếu cần, thêm endpoint mới:

```python
@router.get("/stream/video", tags=["Camera Stream"])
async def stream_mjpeg(current_user: User = Depends(get_current_user)):
    """Stream MJPEG từ MediaMTX"""
    async def generate():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET", 
                    "http://localhost:8888/camera_01.mjpeg"  # HLS → MJPEG
                ) as response:
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        yield chunk
        except Exception as e:
            yield b"Error streaming"
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/stream/snapshot", tags=["Camera Stream"])
async def stream_snapshot(current_user: User = Depends(get_current_user)):
    """Lấy snapshot hiện tại từ camera"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8888/camera_01.jpg")
            return Response(content=response.content, media_type="image/jpeg")
    except Exception:
        raise HTTPException(status_code=503, detail="Camera offline")
```

---

## 🎯 Priority 3: MEDIUM - Error Response Format

### Vấn đề:
- Thiết kế: `{"success": false, "error": {"code": "...", "message": "...", "http_status": 404}}`
- Thực tế: `{"detail": {"code": "...", "message": "..."}}`

### Giải pháp:

**Option A: Tạo Exception Handler tùy chỉnh**

File `app/core/exceptions.py`:

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

class APIException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "http_status": exc.status_code
            }
        }
    )

# Usage example:
# raise APIException(404, "ZONE_NOT_FOUND", "Zone with ID 123 not found")
```

**Option B: Tạo Response wrapper** (Đơn giản hơn)

File `app/core/response.py`:

```python
def error_response(status_code: int, code: str, message: str):
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "http_status": status_code
        }
    }

# Usage in routes:
@router.get("/zones/{zone_id}")
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=error_response(404, "ZONE_NOT_FOUND", "Zone not found")
        )
    return {"success": True, "data": zone_to_dict(zone)}
```

---

## 🎯 Priority 4: MEDIUM - Alert Response Enrichment

### Vấn đề:
- Thiếu `zone_name` (cần join từ Zone table)
- `object_count` hardcoded = 1

### Giải pháp:

File `app/api/v1/routes/alerts.py`:

```python
def alert_to_dict(a: Alert, db: Session = None, include_bbox=False) -> dict:
    # Fetch zone name if db is provided
    zone_name = None
    if db and a.zone_id:
        zone = db.query(Zone).filter(Zone.id == a.zone_id).first()
        zone_name = zone.name if zone else None
    
    base = {
        "alert_id": str(a.id),
        "zone_id": str(a.zone_id) if a.zone_id else None,
        "zone_name": zone_name,  # ADD THIS
        "camera_id": str(a.camera_id) if a.camera_id else None,
        "detected_at": a.detected_at,
        "is_read": bool(a.is_acknowledged),
        "thumbnail_url": f"/api/v1/media/alerts/{a.id}/thumbnail" if a.thumbnail_path else None,
        "video_url": f"/api/v1/media/alerts/{a.id}/video" if a.video_clip_path else None,
        # FIXED: Calculate actual object count from bounding boxes
        "object_count": len(a.bounding_boxes) if a.bounding_boxes else 1,
        "confidence": a.confidence,
    }
    if include_bbox:
        base["bounding_boxes"] = a.bounding_boxes or []
    return base

# Update routes to pass db parameter:
@router.get("")
def list_alerts(..., db: Session = Depends(get_db), ...):
    # ... existing code ...
    return {"success": True, "data": {
        "items": [alert_to_dict(a, db=db) for a in items],  # Pass db!
        "pagination": {...}
    }}

@router.get("/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db), ...):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(...)
    return {"success": True, "data": alert_to_dict(a, db=db, include_bbox=True)}
```

---

## 🎯 Priority 5: MEDIUM - Logs Stats Enhancement

### Vấn đề:
Thiếu: `intrusions_this_week`, `most_active_zone`, `peak_hour`, `by_zone`

### Giải pháp:

File `app/api/v1/routes/logs.py`:

```python
from datetime import datetime, timedelta
from sqlalchemy import func, extract

@router.get("/stats")
def get_stats(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(IntrusionLog)
    if from_date:
        q = q.filter(IntrusionLog.entered_at >= from_date)
    if to_date:
        q = q.filter(IntrusionLog.entered_at <= to_date)

    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    total = q.count()
    today_count = q.filter(func.date(IntrusionLog.entered_at) == today).count()
    week_count = q.filter(
        func.date(IntrusionLog.entered_at) >= week_ago,
        func.date(IntrusionLog.entered_at) <= today
    ).count()
    
    # Get most active zone
    zone_stats = db.query(
        Zone.id,
        Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(
        IntrusionLog, Zone.id == IntrusionLog.zone_id
    ).group_by(Zone.id).order_by(func.count(IntrusionLog.id).desc()).first()
    
    most_active = {
        "zone_id": str(zone_stats[0]),
        "zone_name": zone_stats[1],
        "count": zone_stats[2] or 0
    } if zone_stats else None
    
    # Get by_zone breakdown
    by_zone_data = db.query(
        Zone.id,
        Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(
        IntrusionLog, Zone.id == IntrusionLog.zone_id
    ).group_by(Zone.id).all()
    
    by_zone = [
        {"zone_id": str(z[0]), "zone_name": z[1], "count": z[2] or 0}
        for z in by_zone_data
    ]
    
    # Get peak hour (optional)
    peak_hour_data = db.query(
        extract('hour', IntrusionLog.entered_at).label('hour'),
        func.count(IntrusionLog.id).label('count')
    ).group_by('hour').order_by(func.count(IntrusionLog.id).desc()).first()
    
    peak_hour = int(peak_hour_data[0]) if peak_hour_data else None

    return {"success": True, "data": {
        "total_intrusions": total,
        "intrusions_today": today_count,
        "intrusions_this_week": week_count,
        "most_active_zone": most_active,
        "peak_hour": peak_hour,
        "by_zone": by_zone
    }}
```

---

## 📋 Bảng Kiểm Tra Sửa Lỗi

### WebSocket Events ✅
- [ ] Tạo `app/services/detection_service.py`
- [ ] Cập nhật `websocket.py` hỗ trợ `subscribe_camera_ack`, `unsubscribe_camera_ack`
- [ ] Gọi `broadcast_event("intrusion_detected", ...)` khi detection engine phát hiện
- [ ] Gọi `broadcast_event("intrusion_ended", ...)` khi xâm nhập kết thúc
- [ ] Gọi `broadcast_event("camera_status_changed", ...)` khi camera online/offline

### Stream API ✅
- [ ] Option A: Giữ nguyên `/stream/urls`, update Flutter (KHUYẾN NGHỊ)
- [ ] Option B: Thêm `/stream/video` endpoint nếu cần

### Error Response ✅
- [ ] Tạo custom exception handler hoặc response wrapper
- [ ] Cập nhật tất cả errors để trả về format: `{"success": false, "error": {...}}`
- [ ] Thêm `http_status` field trong error response

### Alert Response ✅
- [ ] Cập nhật `alert_to_dict()` thêm `zone_name`
- [ ] Cập nhật `object_count` từ `bounding_boxes` thay vì hardcoded = 1
- [ ] Pass `db` parameter trong tất cả `alert_to_dict()` calls

### Logs Stats ✅
- [ ] Thêm query `intrusions_this_week`
- [ ] Thêm query `most_active_zone`
- [ ] Thêm query `peak_hour`
- [ ] Thêm query `by_zone` breakdown

---

## 🧪 Testing

Sau khi sửa, test các endpoint:

```bash
# Test WebSocket connection
wscat -c "ws://localhost:8000/ws?token=<your-token>"

# Test stream URLs
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/stream/urls

# Test alert list
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/alerts

# Test logs stats
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/logs/stats
```

---

**Priority Queue:**
1. 🔴 WebSocket Events (CRITICAL)
2. 🟠 Stream API (HIGH)
3. 🟡 Error Format (MEDIUM)
4. 🟡 Alert Response (MEDIUM)
5. 🟡 Logs Stats (MEDIUM)
