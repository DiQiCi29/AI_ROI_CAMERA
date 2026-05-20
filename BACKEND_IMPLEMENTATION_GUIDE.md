# 🔧 Backend Implementation Plan - Chi Tiết

**Hướng dẫn từng bước sửa dự án AI_ROI_CAMERA**

---

## ⚡ Quick Start

**Thứ tự ưu tiên:**
1. WebSocket Events (CRITICAL)
2. Error Response Format (HIGH)
3. Alert Response enrichment (HIGH)
4. Logs Stats (MEDIUM)
5. FCM Service (MEDIUM)

---

## 🔴 PHASE 1: CRITICAL FIXES

### 1.1 WebSocket Real-Time Events

**File**: `app/services/detection_service.py` (Tạo mới)

```python
"""
Service để xử lý detection events và broadcast qua WebSocket
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.zone import Zone
from app.api.v1.routes.websocket import broadcast_event


async def on_intrusion_detected(alert: Alert, db: Session):
    """
    Gọi khi detection engine phát hiện xâm nhập.
    Gửi event qua WebSocket đến tất cả clients.
    """
    try:
        # Lấy thông tin zone
        zone = db.query(Zone).filter(Zone.id == alert.zone_id).first()
        zone_name = zone.name if zone else f"Zone {alert.zone_id}"
        
        # Broadcast event
        await broadcast_event("intrusion_detected", {
            "alert_id": str(alert.id),
            "zone_id": str(alert.zone_id) if alert.zone_id else None,
            "zone_name": zone_name,
            "camera_id": str(alert.camera_id) if alert.camera_id else None,
            "detected_at": alert.detected_at.isoformat(),
            "object_count": len(alert.bounding_boxes) if alert.bounding_boxes else 1,
            "confidence": float(alert.confidence) if alert.confidence else 0.0,
            "thumbnail_url": f"/api/v1/media/alerts/{alert.id}/thumbnail" if alert.thumbnail_path else None,
            "bounding_boxes": alert.bounding_boxes or [],
            "video_url": f"/api/v1/media/alerts/{alert.id}/video" if alert.video_clip_path else None
        })
        
        print(f"[WebSocket] Broadcast intrusion_detected for alert {alert.id}")
        
    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast intrusion_detected: {str(e)}")


async def on_intrusion_ended(alert: Alert, exited_at: datetime, db: Session):
    """
    Gọi khi xâm nhập kết thúc (đối tượng rời khỏi vùng).
    """
    try:
        # Tính duration
        duration = (exited_at - alert.detected_at).total_seconds()
        
        # Broadcast event
        await broadcast_event("intrusion_ended", {
            "alert_id": str(alert.id),
            "zone_id": str(alert.zone_id) if alert.zone_id else None,
            "exited_at": exited_at.isoformat(),
            "duration_seconds": int(duration),
            "video_url": f"/api/v1/media/alerts/{alert.id}/video" if alert.video_clip_path else None
        })
        
        print(f"[WebSocket] Broadcast intrusion_ended for alert {alert.id}")
        
    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast intrusion_ended: {str(e)}")


async def on_camera_status_changed(camera_id: str, status: str):
    """
    Gọi khi camera thay đổi trạng thái (online/offline).
    """
    try:
        # Broadcast event
        await broadcast_event("camera_status_changed", {
            "camera_id": camera_id,
            "status": status,  # "online" | "offline"
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"[WebSocket] Broadcast camera_status_changed: {camera_id} -> {status}")
        
    except Exception as e:
        print(f"[WebSocket Error] Failed to broadcast camera_status_changed: {str(e)}")
```

**Where to Call:**
- `on_intrusion_detected()` - Gọi từ AI detection service khi phát hiện
- `on_intrusion_ended()` - Gọi từ tracking service khi object rời zone
- `on_camera_status_changed()` - Gọi từ stream status monitor

**Integration Point:**
```python
# Ví dụ: app/api/v1/routes/alerts.py
from app.services.detection_service import on_intrusion_detected, on_intrusion_ended

@router.post("", status_code=201)
def create_alert(body: AlertCreate, db: Session = Depends(get_db), ...):
    alert = Alert(...)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # Gửi WebSocket event
    import asyncio
    asyncio.create_task(on_intrusion_detected(alert, db))
    
    return {"success": True, "data": alert_to_dict(alert, db=db)}
```

---

### 1.2 Update WebSocket Handler

**File**: `app/api/v1/routes/websocket.py`

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError
from app.core.security import decode_token
from datetime import datetime
import json

router = APIRouter(tags=["WebSocket"])

# Lưu danh sách clients đang kết nối
connected_clients: list[WebSocket] = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Xác thực JWT
    try:
        decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    connected_clients.append(websocket)

    # Gửi connection confirmation
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
                # Có thể lưu subscription state nếu cần
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
        print(f"Client disconnected. Active connections: {len(connected_clients)}")


async def broadcast_event(event: str, data: dict):
    """
    Gửi event tới tất cả clients đang kết nối.
    Gọi từ detection_service hoặc các service khác.
    """
    dead_clients = []
    
    for client in connected_clients:
        try:
            await client.send_json({
                "event": event,
                "data": data,
                "sent_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"[WebSocket] Error sending to client: {str(e)}")
            dead_clients.append(client)
    
    # Xóa clients đã disconnect
    for client in dead_clients:
        if client in connected_clients:
            connected_clients.remove(client)
    
    print(f"[WebSocket] Broadcast '{event}' to {len(connected_clients)} clients")
```

**Test:**
```bash
# Sử dụng wscat để test
wscat -c "ws://localhost:8000/ws?token=YOUR_JWT_TOKEN"

# Gửi ping
> {"event": "ping"}
< {"event": "pong", "data": {"timestamp": "2024-01-15T10:30:00"}}

# Sẽ nhận broadcast events từ server
< {"event": "intrusion_detected", "data": {...}}
```

---

### 1.3 Error Response Handler

**File**: `app/core/exceptions.py` (Tạo mới)

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


def create_api_exception(status_code: int, code: str, message: str) -> HTTPException:
    """Helper function để tạo API exception với format chuẩn"""
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message
        }
    )


# Gọi ở main.py để đăng ký handler
def register_exception_handlers(app):
    """Đăng ký tất cả exception handlers"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Format lại HTTPException theo chuẩn API_DESIGN.md
        """
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": detail.get("code", "INTERNAL_ERROR"),
                    "message": detail.get("message", str(exc.detail)),
                    "http_status": exc.status_code
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Format validation errors
        """
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "http_status": 400
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        Catch-all handler cho lỗi không lường trước
        """
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "http_status": 500
                }
            }
        )
```

**File**: `app/main.py` (Update)

```python
from fastapi import FastAPI
from app.core.exceptions import register_exception_handlers

app = FastAPI(...)

# ... existing middleware ...

# Đăng ký exception handlers
register_exception_handlers(app)

# ... existing routes ...
```

**Update Existing Routes** - Example:

```python
# OLD
@router.get("/{zone_id}")
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={
            "code": "ZONE_NOT_FOUND", "message": f"Zone {zone_id} not found"
        })
    return {"success": True, "data": zone_to_dict(zone)}

# Giờ sẽ tự động format response thành:
# {
#   "success": false,
#   "error": {
#     "code": "ZONE_NOT_FOUND",
#     "message": "Zone 123 not found",
#     "http_status": 404
#   }
# }
```

---

### 1.4 Enrich Alert Response with Zone Name

**File**: `app/api/v1/routes/alerts.py`

```python
def alert_to_dict(a: Alert, db: Session = None, include_bbox=False) -> dict:
    """
    Convert Alert model to dict, include zone_name nếu db session cung cấp
    """
    zone_name = None
    object_count = 1
    
    if db and a.zone_id:
        zone = db.query(Zone).filter(Zone.id == a.zone_id).first()
        zone_name = zone.name if zone else None
    
    # Calculate object_count từ bounding_boxes
    if a.bounding_boxes:
        try:
            import json
            boxes = json.loads(a.bounding_boxes) if isinstance(a.bounding_boxes, str) else a.bounding_boxes
            object_count = len(boxes)
        except:
            object_count = 1
    
    base = {
        "alert_id": str(a.id),
        "zone_id": str(a.zone_id) if a.zone_id else None,
        "zone_name": zone_name,  # ADD THIS
        "camera_id": str(a.camera_id) if a.camera_id else None,
        "detected_at": a.detected_at,
        "is_read": bool(a.is_acknowledged),
        "thumbnail_url": f"/api/v1/media/alerts/{a.id}/thumbnail" if a.thumbnail_path else None,
        "video_url": f"/api/v1/media/alerts/{a.id}/video" if a.video_clip_path else None,
        "object_count": object_count,  # FIXED
        "confidence": a.confidence,
    }
    
    if include_bbox:
        base["bounding_boxes"] = a.bounding_boxes or []
    
    return base


# UPDATE: Pass db parameter tới alert_to_dict()
@router.get("")
def list_alerts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    zone_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Alert)
    if zone_id: q = q.filter(Alert.zone_id == zone_id)
    if is_read is not None: q = q.filter(Alert.is_acknowledged == (1 if is_read else 0))
    if from_date: q = q.filter(Alert.detected_at >= from_date)
    if to_date: q = q.filter(Alert.detected_at <= to_date)
    total = q.count()
    items = q.order_by(Alert.detected_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {"success": True, "data": {
        "items": [alert_to_dict(a, db=db) for a in items],  # Pass db!
        "pagination": {"page": page, "limit": limit, "total": total,
                       "total_pages": math.ceil(total / limit)}
    }}

@router.get("/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "Not found"})
    return {"success": True, "data": alert_to_dict(a, db=db, include_bbox=True)}  # Pass db!
```

---

## 🟡 PHASE 2: MEDIUM PRIORITY

### 2.1 Enhance Logs Stats API

**File**: `app/api/v1/routes/logs.py`

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
    """
    Thống kê xâm nhập với đầy đủ dữ liệu analytics
    """
    q = db.query(IntrusionLog)
    if from_date:
        q = q.filter(IntrusionLog.entered_at >= from_date)
    if to_date:
        q = q.filter(IntrusionLog.entered_at <= to_date)

    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    # Basic counts
    total = q.count()
    today_count = q.filter(func.date(IntrusionLog.entered_at) == today).count()
    week_count = q.filter(
        func.date(IntrusionLog.entered_at) >= week_ago,
        func.date(IntrusionLog.entered_at) <= today
    ).count()
    
    # Most active zone
    most_active_query = db.query(
        Zone.id,
        Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(
        IntrusionLog, Zone.id == IntrusionLog.zone_id
    ).group_by(Zone.id).order_by(func.count(IntrusionLog.id).desc()).first()
    
    most_active = None
    if most_active_query:
        most_active = {
            "zone_id": str(most_active_query[0]),
            "zone_name": most_active_query[1],
            "count": most_active_query[2] or 0
        }
    
    # By zone breakdown
    by_zone_query = db.query(
        Zone.id,
        Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(
        IntrusionLog, Zone.id == IntrusionLog.zone_id
    ).group_by(Zone.id).all()
    
    by_zone = [
        {
            "zone_id": str(z[0]),
            "zone_name": z[1],
            "count": z[2] or 0
        }
        for z in by_zone_query
    ]
    
    # Peak hour (hour with most intrusions)
    peak_hour_query = db.query(
        extract('hour', IntrusionLog.entered_at).label('hour'),
        func.count(IntrusionLog.id).label('count')
    ).group_by('hour').order_by(func.count(IntrusionLog.id).desc()).first()
    
    peak_hour = None
    if peak_hour_query:
        peak_hour = int(peak_hour_query[0])

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

### 2.2 FCM Push Notification Service

**File**: `app/services/fcm_service.py` (Tạo mới)

```python
"""
Firebase Cloud Messaging service để gửi push notifications
"""
import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session
from app.models.fcm_token import FCMToken
from app.models.alert import Alert
from app.models.zone import Zone
import os


class FCMService:
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK (gọi 1 lần ở startup)"""
        if cls._initialized:
            return
        
        # Tìm firebase credentials file
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-adminsdk.json")
        
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            cls._initialized = True
            print("[FCM] Firebase initialized successfully")
        except FileNotFoundError:
            print(f"[FCM] Firebase credentials not found at {cred_path}")
            print("[FCM] FCM service will be disabled")
    
    @classmethod
    async def send_intrusion_alert(
        cls,
        alert: Alert,
        zone_name: str,
        db: Session
    ):
        """
        Gửi push notification khi phát hiện xâm nhập
        """
        if not cls._initialized:
            print("[FCM] Service not initialized, skipping notification")
            return
        
        # Lấy tất cả active FCM tokens
        tokens_query = db.query(FCMToken).filter(
            FCMToken.is_active == True
        ).all()
        
        if not tokens_query:
            print("[FCM] No active FCM tokens found")
            return
        
        token_list = [token.token for token in tokens_query]
        
        try:
            # Tạo message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title="⚠️ Cảnh báo xâm nhập!",
                    body=f"Phát hiện người tại: {zone_name}"
                ),
                data={
                    "type": "intrusion_alert",
                    "alert_id": str(alert.id),
                    "zone_id": str(alert.zone_id),
                    "zone_name": zone_name,
                    "detected_at": alert.detected_at.isoformat(),
                    "thumbnail_url": f"/api/v1/media/alerts/{alert.id}/thumbnail",
                    "camera_id": str(alert.camera_id),
                    "confidence": str(alert.confidence)
                },
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="intrusion_alert_channel",
                        sound="alert_sound",
                        color="#FF0000",
                        icon="ic_launcher_foreground",
                        vibrate_timings=[0, 500, 1000, 500]
                    )
                )
            )
            
            # Gửi
            response = messaging.send_multicast(message)
            
            print(f"[FCM] Sent to {response.success} devices, {response.failure} failed")
            print(f"[FCM] Alert ID: {alert.id}, Zone: {zone_name}")
            
            return response
            
        except Exception as e:
            print(f"[FCM] Error sending notification: {str(e)}")
            return None
```

**File**: `app/main.py` (Update)

```python
from app.services.fcm_service import FCMService

app = FastAPI(...)

# Initialize FCM on startup
@app.on_event("startup")
async def startup_event():
    FCMService.initialize()
    print("Application startup complete")
```

**File**: `app/api/v1/routes/alerts.py` (Update - khi create alert)

```python
from app.services.detection_service import on_intrusion_detected
from app.services.fcm_service import FCMService

@router.post("", status_code=201)
def create_alert(body: AlertCreate, db: Session = Depends(get_db), ...):
    alert = Alert(...)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # Get zone name
    zone = db.query(Zone).filter(Zone.id == body.zone_id).first()
    zone_name = zone.name if zone else f"Zone {body.zone_id}"
    
    # Send WebSocket event
    import asyncio
    asyncio.create_task(on_intrusion_detected(alert, db))
    
    # Send FCM notification
    asyncio.create_task(FCMService.send_intrusion_alert(alert, zone_name, db))
    
    return {"success": True, "data": alert_to_dict(alert, db=db)}
```

---

### 2.3 Setup Firebase Credentials

**Steps:**
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create project or use existing
3. Generate Service Account key:
   - Settings → Service Accounts → Generate New Private Key
   - Save as `firebase-adminsdk.json` in project root
4. Add to `.env`:
   ```
   FIREBASE_CREDENTIALS_PATH=./firebase-adminsdk.json
   ```
5. Ensure `google-cloud-firestore` in requirements

---

## ✅ TESTING

### Test WebSocket Events:
```bash
# Terminal 1: Start server
python -m uvicorn app.main:app --reload

# Terminal 2: Connect WebSocket
wscat -c "ws://localhost:8000/ws?token=YOUR_TOKEN"

# Terminal 3: Create alert (trigger event)
curl -X POST http://localhost:8000/api/v1/alerts/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{...}'

# Should see in Terminal 2:
# < {"event": "intrusion_detected", "data": {...}}
```

### Test Error Format:
```bash
curl http://localhost:8000/api/v1/zones/999 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return:
# {"success": false, "error": {"code": "ZONE_NOT_FOUND", "message": "...", "http_status": 404}}
```

### Test Alert with Zone Name:
```bash
curl "http://localhost:8000/api/v1/alerts?page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should include zone_name in response
```

### Test Stats:
```bash
curl "http://localhost:8000/api/v1/logs/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return all stats: week, most_active_zone, peak_hour, by_zone
```

---

## 📋 Implementation Checklist

- [ ] Create `app/services/detection_service.py`
- [ ] Update `app/api/v1/routes/websocket.py`
- [ ] Create `app/core/exceptions.py`
- [ ] Update `app/main.py` with exception handlers
- [ ] Update `app/api/v1/routes/alerts.py` - add zone_name
- [ ] Update `app/api/v1/routes/logs.py` - add stats
- [ ] Create `app/services/fcm_service.py`
- [ ] Setup Firebase credentials
- [ ] Update requirements.txt with new dependencies
- [ ] Test all endpoints
- [ ] Test WebSocket events
- [ ] Test error handling

---

**Estimated Total Time: 10-12 hours**
