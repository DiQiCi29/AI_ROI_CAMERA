# 🎯 Phương Án Chỉnh Sửa Toàn Diện - Backend vs Android App

**Tổng hợp sự sai khác và đề xuất giải pháp để cả 2 dự án đồng nhất**

---

## 📊 Bảng So Sánh Tổng Quan

```
API_DESIGN.md (Thiết Kế Ban Đầu)
    ↓
    ├─→ Backend (AI_ROI_CAMERA) - 70% đúng
    │   └─ 5 vấn đề cần sửa
    │
    ├─→ Android App (Flutter) - 65% đúng  
    │   └─ 6 vấn đề cần sửa
    │
    └─ MỤC TIÊU: Đồng nhất cả 2 để chạy optimal
```

---

## 🔴 CRITICAL ISSUES

### Issue 1: WebSocket Real-Time Alerts Không Hoạt Động

#### Hiện Trạng:
- **Backend**: Không gửi `intrusion_detected`, `intrusion_ended` events
- **Android**: Có code lắng nghe events nhưng backend không gửi
- **Result**: ❌ Real-time alerts MẤT

#### Thiết Kế Yêu Cầu:
```json
// Server gửi
{
  "event": "intrusion_detected",
  "data": {
    "alert_id": "alert_xyz789",
    "zone_id": "zone_abc123",
    "zone_name": "Vùng cấm cửa chính",
    "camera_id": "cam_01",
    "detected_at": "2024-01-15T10:35:00Z",
    "object_count": 1,
    "confidence": 0.95,
    "thumbnail_url": "/media/alerts/alert_xyz789/thumbnail.jpg",
    "bounding_boxes": [...]
  }
}
```

#### Giải Pháp:

**Backend Fix** (Priority 1 - URGENT):
```python
# app/services/detection_service.py
from app.services.websocket import broadcast_event

async def handle_intrusion_detected(alert):
    """Được gọi khi detection engine phát hiện xâm nhập"""
    zone = db.query(Zone).filter(Zone.id == alert.zone_id).first()
    
    await broadcast_event("intrusion_detected", {
        "alert_id": str(alert.id),
        "zone_id": str(alert.zone_id),
        "zone_name": zone.name if zone else None,
        "camera_id": str(alert.camera_id),
        "detected_at": alert.detected_at.isoformat(),
        "object_count": len(alert.bounding_boxes) if alert.bounding_boxes else 1,
        "confidence": float(alert.confidence),
        "thumbnail_url": f"/api/v1/media/alerts/{alert.id}/thumbnail",
        "bounding_boxes": alert.bounding_boxes or []
    })

async def handle_intrusion_ended(alert, exited_at):
    """Được gọi khi xâm nhập kết thúc"""
    duration = (exited_at - alert.detected_at).total_seconds()
    
    await broadcast_event("intrusion_ended", {
        "alert_id": str(alert.id),
        "zone_id": str(alert.zone_id),
        "exited_at": exited_at.isoformat(),
        "duration_seconds": int(duration),
        "video_url": f"/api/v1/media/alerts/{alert.id}/video"
    })
```

**Android No Changes Needed** ✅
- Code đã sẵn sàng lắng nghe events

#### Impact:
- ✅ App nhận real-time alerts
- ✅ Hiển thị notification ngay lập tức
- ✅ Không cần polling

**Ước tính công việc:**
- Backend: 2-3 giờ
- Android: 0 giờ (No changes)

---

### Issue 2: Stream API - MJPEG vs RTSP/HLS

#### Hiện Trạng:
- **Thiết Kế**: `/stream/video` (MJPEG) + `/stream/snapshot`
- **Backend**: Chỉ có `/stream/urls` (RTSP/HLS/WebRTC)
- **Android**: Được viết để stream MJPEG từ `/stream/video`
- **Result**: ❌ Stream không hoạt động

#### Giải Pháp - HAI LỰA CHỌN:

##### **Option A: Giữ RTSP/HLS, Cập Nhật Android** ✅ KHUYẾN NGHỊ

**Lý do:**
- RTSP/HLS là chuẩn quốc tế
- Mobile player hỗ trợ tốt hơn
- Adaptive bitrate, tiết kiệm bandwidth
- Dễ scale

**Backend** (0 giờ - không cần thay đổi):
```python
# Current implementation is perfect
@router.get("/stream/urls")
async def get_stream_urls(current_user: User = Depends(get_current_user)):
    return {"success": True, "data": {
        "camera_id": "camera_01",
        "rtsp": f"rtsp://localhost:8554/camera_01",
        "hls": f"http://localhost:8888/camera_01",
        "webrtc": f"http://localhost:8889/camera_01",
    }}
```

**Android** (Thay đổi cần thiết):
```dart
// OLD (MJPEG)
const String videoStream = "$apiBaseUrl/stream/video";

// NEW (RTSP/HLS)
// Fetch URLs từ /stream/urls endpoint
Future<void> fetchStreamUrls() async {
  final response = await client.get(
    Uri.parse("$apiBaseUrl/stream/urls"),
    headers: {"Authorization": "Bearer $token"}
  );
  
  final data = jsonDecode(response.body);
  final streamUrls = data["data"];
  
  // Sử dụng HLS URL (best compatibility)
  String hlsUrl = streamUrls["hls"]; // "http://localhost:8888/camera_01"
  
  // Plugin: flutter_vlc_player hoặc video_player
  // video_player hỗ trợ HLS natively
  _videoPlayerController = VideoPlayerController.network(hlsUrl);
}
```

**Packages cần thêm** (Android):
```yaml
dependencies:
  video_player: ^2.4.0
  flutter_vlc_player: ^7.3.0  # Nếu cần RTSP
```

**Effort:**
- Backend: 0 giờ ✅
- Android: 2-3 giờ (update player logic)

---

##### **Option B: Thêm MJPEG Support** (Nếu cần)

**Backend** (2-3 giờ):
```python
@router.get("/stream/video", tags=["Camera Stream"])
async def stream_mjpeg(current_user: User = Depends(get_current_user)):
    """Stream MJPEG từ MediaMTX"""
    async def generate():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET", 
                    "http://localhost:8888/camera_01.mjpeg"
                ) as response:
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        yield chunk
        except Exception as e:
            yield b"Error"
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/stream/snapshot", tags=["Camera Stream"])
async def stream_snapshot(current_user: User = Depends(get_current_user)):
    """Snapshot từ camera"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8888/camera_01.jpg")
        return Response(content=response.content, media_type="image/jpeg")
```

**Android** (0 giờ - No changes):
- Existing code already supports MJPEG

**Effort:**
- Backend: 2-3 giờ
- Android: 0 giờ

---

**RECOMMENDATION: Option A** (Better for mobile)
- Simpler, more efficient
- Modern streaming protocol
- Better user experience

---

## 🟠 HIGH PRIORITY ISSUES

### Issue 3: Error Response Format Khác

#### Hiện Trạng:
- **Thiết Kế**: `{"success": false, "error": {"code": "...", "message": "...", "http_status": 404}}`
- **Backend**: `{"detail": {"code": "...", "message": "..."}}`
- **Android**: Dự tính parse `response.error.code`
- **Result**: ⚠️ Error handling bị gãy

#### Backend Fix (1-2 giờ):

```python
# app/core/exceptions.py
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    # Parse detail if it's a dict
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": detail.get("code", "UNKNOWN_ERROR"),
                "message": detail.get("message", str(exc.detail)),
                "http_status": exc.status_code
            }
        }
    )

# Usage in routes:
raise HTTPException(
    status_code=404,
    detail={
        "code": "ZONE_NOT_FOUND",
        "message": "Zone with ID 123 not found"
    }
)
```

#### Android Fix (1-2 giờ):

```dart
// OLD
catch (e) {
  if (e.response?.statusCode == 401) {
    // Handle 401
  }
}

// NEW
void handleApiError(dynamic error) {
  if (error is DioException) {
    final data = error.response?.data;
    
    if (data is Map && data["error"] != null) {
      final errorData = data["error"];
      final code = errorData["code"]; // ZONE_NOT_FOUND
      final message = errorData["message"];
      final httpStatus = errorData["http_status"]; // 404
      
      switch (code) {
        case "UNAUTHORIZED":
          // Handle auth error
          break;
        case "ZONE_NOT_FOUND":
          // Handle zone not found
          break;
        case "ALERT_NOT_FOUND":
          // Handle alert not found
          break;
      }
    }
  }
}
```

**Effort:**
- Backend: 1-2 giờ
- Android: 1-2 giờ

---

### Issue 4: Response Format Inconsistency - `zone_name` Missing

#### Hiện Trạng:
- **Thiết Kế**: Alerts trả về `zone_name`
- **Backend**: Không trả về `zone_name`, chỉ `zone_id`
- **Android**: Dự tính hiển thị zone name trên alert list
- **Result**: ⚠️ UI display thiếu thông tin

#### Backend Fix (1-2 giờ):

```python
# app/api/v1/routes/alerts.py
def alert_to_dict(a: Alert, db: Session = None, include_bbox=False) -> dict:
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
        "object_count": len(a.bounding_boxes) if a.bounding_boxes else 1,  # FIX THIS TOO
        "confidence": a.confidence,
    }
    if include_bbox:
        base["bounding_boxes"] = a.bounding_boxes or []
    return base

# Update all calls to pass db
@router.get("")
def list_alerts(..., db: Session = Depends(get_db), ...):
    # ...
    return {"success": True, "data": {
        "items": [alert_to_dict(a, db=db) for a in items],  # Pass db!
        "pagination": {...}
    }}
```

#### Android No Changes ✅
- Code đã dự tính có `zone_name` trong response

**Effort:**
- Backend: 1-2 giờ
- Android: 0 giờ

---

## 🟡 MEDIUM PRIORITY ISSUES

### Issue 5: Missing API Endpoints in Android

#### Hiện Trạng:
- **Backend**: Có endpoint
- **Android**: Chưa implement
- **Result**: Các tính năng bị thiếu

| Endpoint | Backend | Android | Fix Time |
|----------|---------|---------|----------|
| `GET /zones/{id}` | ✅ | ❌ | 1h |
| `PUT /zones/{id}` | ✅ | ❌ | 1-2h |
| `DELETE /media/alerts/{id}` | ✅ | ❌ | 1h |
| `GET /logs` (list) | ✅ | ❌ | 1-2h |

#### Android Fix:

**ApiService.dart - Add Missing Methods:**
```dart
// GET /zones/{id}
Future<Map<String, dynamic>> getZoneDetails(int zoneId) async {
  final response = await client.get(
    Uri.parse("$apiBaseUrl/zones/$zoneId"),
    headers: {"Authorization": "Bearer $token"}
  );
  return _handleResponse(response);
}

// PUT /zones/{id}
Future<Map<String, dynamic>> updateZone(
  int zoneId,
  String name,
  List<Map<String, double>> coordinates,
  bool isActive,
  int cooldownSeconds,
) async {
  final response = await client.put(
    Uri.parse("$apiBaseUrl/zones/$zoneId"),
    headers: {
      "Authorization": "Bearer $token",
      "Content-Type": "application/json"
    },
    body: jsonEncode({
      "name": name,
      "coordinates": coordinates,
      "is_active": isActive,
      "alert_cooldown_seconds": cooldownSeconds
    })
  );
  return _handleResponse(response);
}

// DELETE /media/alerts/{id}
Future<void> deleteAlertMedia(int alertId) async {
  final response = await client.delete(
    Uri.parse("$apiBaseUrl/media/alerts/$alertId"),
    headers: {"Authorization": "Bearer $token"}
  );
  _handleResponse(response);
}

// GET /logs (list with pagination)
Future<Map<String, dynamic>> getLogs({
  int page = 1,
  int limit = 20,
  int? zoneId,
  DateTime? fromDate,
  DateTime? toDate,
}) async {
  Map<String, String> params = {
    "page": page.toString(),
    "limit": limit.toString(),
  };
  if (zoneId != null) params["zone_id"] = zoneId.toString();
  if (fromDate != null) params["from_date"] = fromDate.toIso8601String();
  if (toDate != null) params["to_date"] = toDate.toIso8601String();
  
  final response = await client.get(
    Uri.parse("$apiBaseUrl/logs").replace(queryParameters: params),
    headers: {"Authorization": "Bearer $token"}
  );
  return _handleResponse(response);
}
```

**Backend**: No changes ✅

**Effort:**
- Backend: 0 giờ
- Android: 3-4 giờ

---

### Issue 6: Data Model Updates

#### ZoneModel Missing `updated_at`

**Android Fix (30 min):**
```dart
// OLD
class Zone {
  final int id;
  final String name;
  final String cameraId;
  final List<Coordinate> coordinates;
  final bool isActive;
  final int alertCooldownSeconds;
  final DateTime createdAt;
  // updated_at: MISSING
}

// NEW
class Zone {
  final int id;
  final String name;
  final String cameraId;
  final List<Coordinate> coordinates;
  final bool isActive;
  final int alertCooldownSeconds;
  final DateTime createdAt;
  final DateTime updatedAt;  // ADD THIS
  
  Zone({
    required this.id,
    required this.name,
    required this.cameraId,
    required this.coordinates,
    required this.isActive,
    required this.alertCooldownSeconds,
    required this.createdAt,
    required this.updatedAt,
  });
  
  factory Zone.fromJson(Map<String, dynamic> json) {
    return Zone(
      id: json['zone_id'],
      name: json['name'],
      cameraId: json['camera_id'],
      coordinates: (json['coordinates'] as List)
          .map((c) => Coordinate.fromJson(c))
          .toList(),
      isActive: json['is_active'],
      alertCooldownSeconds: json['alert_cooldown_seconds'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),  // ADD THIS
    );
  }
}
```

**Backend**: Already implemented ✅

**Effort:**
- Backend: 0 giờ
- Android: 30 min

---

### Issue 7: Logs Stats Data Enrichment

#### Hiện Trạng:
- **Thiết Kế**: Stats có `intrusions_this_week`, `most_active_zone`, `peak_hour`, `by_zone`
- **Backend**: Chỉ có `total_intrusions`, `intrusions_today`
- **Android**: Dự tính hiển thị tất cả stats

#### Backend Fix (2-3 giờ):

```python
# app/api/v1/routes/logs.py
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
    
    # Most active zone
    zone_stats = db.query(
        Zone.id, Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(IntrusionLog, Zone.id == IntrusionLog.zone_id)\
     .group_by(Zone.id)\
     .order_by(func.count(IntrusionLog.id).desc())\
     .first()
    
    most_active = {
        "zone_id": str(zone_stats[0]),
        "zone_name": zone_stats[1],
        "count": zone_stats[2] or 0
    } if zone_stats else None
    
    # By zone breakdown
    by_zone_data = db.query(
        Zone.id, Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(IntrusionLog, Zone.id == IntrusionLog.zone_id)\
     .group_by(Zone.id).all()
    
    by_zone = [{
        "zone_id": str(z[0]),
        "zone_name": z[1],
        "count": z[2] or 0
    } for z in by_zone_data]
    
    # Peak hour
    peak_hour_data = db.query(
        extract('hour', IntrusionLog.entered_at).label('hour'),
        func.count(IntrusionLog.id).label('count')
    ).group_by('hour')\
     .order_by(func.count(IntrusionLog.id).desc())\
     .first()
    
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

#### Android No Changes ✅

**Effort:**
- Backend: 2-3 giờ
- Android: 0 giờ

---

### Issue 8: WebSocket Connection Handling

#### Thiết Kế:
- Server gửi `{"event": "connected", ...}` khi kết nối
- App nên xử lý event này

#### Hiện Trạng:
- **Backend**: Gửi đúng
- **Android**: Code hiện tại bỏ qua event này
- **Result**: ⚠️ Không xác nhận connection thành công

#### Android Fix (30 min):

```dart
// OLD
void _handleWebSocketMessage(dynamic message) {
  Map<String, dynamic> data = jsonDecode(message);
  String event = data['event'];
  
  if (event == 'intrusion_detected') {
    _handleIntrusionDetected(data['data']);
  } else if (event == 'intrusion_ended') {
    _handleIntrusionEnded(data['data']);
  }
  // Bỏ qua "connected" event
}

// NEW
void _handleWebSocketMessage(dynamic message) {
  Map<String, dynamic> data = jsonDecode(message);
  String event = data['event'];
  
  switch (event) {
    case 'connected':
      _handleConnected(data['data']);
      break;
    case 'intrusion_detected':
      _handleIntrusionDetected(data['data']);
      break;
    case 'intrusion_ended':
      _handleIntrusionEnded(data['data']);
      break;
    case 'camera_status_changed':
      _handleCameraStatusChanged(data['data']);
      break;
  }
}

void _handleConnected(Map<String, dynamic> data) {
  print("WebSocket connected: ${data['message']}");
  // Có thể show notification rằng app đã kết nối thành công
  _isWebSocketConnected = true;
}
```

**Backend**: No changes ✅

**Effort:**
- Backend: 0 giờ
- Android: 30 min

---

### Issue 9: Package Name Consistency

#### Hiện Trạng:
- **Config**: `com.example.zone_monitor_app`
- **Code folder**: `com.example.zone_moniter_app` (typo: **moniter** thay vì **monitor**)
- **Result**: ⚠️ Package name mismatch

#### Android Fix (1-2 giờ):

```bash
# Đổi tên package
flutter pub get  # Cập nhật pubspec.lock
flutter clean
flutter pub get

# Hoặc rename thủ công:
# android/app/src/main/java/com/example/zone_monitor_app/
# Rename từ zone_moniter_app → zone_monitor_app
```

**Backend**: No changes ✅

**Effort:**
- Backend: 0 giờ
- Android: 1-2 giờ

---

### Issue 10: FCM Notification Payload Alignment

#### Thiết Kế:
```json
{
  "notification": {
    "title": "⚠️ Cảnh báo xâm nhập!",
    "body": "Phát hiện người tại: Vùng cấm cửa chính"
  },
  "data": {
    "type": "intrusion_alert",
    "alert_id": "alert_xyz789",
    "zone_id": "zone_abc123",
    "zone_name": "Vùng cấm cửa chính",
    "detected_at": "2024-01-15T10:35:00Z",
    "thumbnail_url": "/media/alerts/alert_xyz789/thumbnail.jpg"
  }
}
```

#### Hiện Trạng:
- **Backend**: Không implement FCM
- **Android**: Có code xử lý FCM nhưng backend không gửi
- **Result**: ⚠️ Push notification không hoạt động

#### Backend Fix (3-4 giờ):

```python
# app/services/fcm_service.py
import firebase_admin
from firebase_admin import credentials, messaging

# Initialize (gọi 1 lần ở main.py)
if not firebase_admin._apps:
    cred = credentials.Certificate("path/to/firebase-adminsdk.json")
    firebase_admin.initialize_app(cred)

async def send_intrusion_alert(alert, zone_name):
    """Gửi FCM notification khi phát hiện xâm nhập"""
    # Lấy tất cả FCM tokens của user
    tokens = db.query(FCMToken).filter(
        FCMToken.is_active == True
    ).all()
    
    if not tokens:
        return
    
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
            "camera_id": str(alert.camera_id)
        },
        tokens=[token.token for token in tokens],
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="intrusion_alert_channel",
                sound="alert_sound",
                vibrate_timings=[0, 500, 1000, 500],  # ms
                icon="ic_launcher_foreground"
            )
        )
    )
    
    # Gửi
    response = messaging.send_multicast(message)
    print(f"FCM sent: {response.success} successful, {response.failure} failed")
```

#### Android Code Already Ready ✅
- Firebase setup done
- Notification handler implemented
- Just need backend to send

**Effort:**
- Backend: 3-4 giờ (setup Firebase Admin SDK, implement sending)
- Android: 0 giờ

---

## 📋 TỔNG HỢP CÔNG VIỆC CẦN LÀM

### Backend (AI_ROI_CAMERA)

| # | Task | Priority | Thời gian | Status |
|----|------|----------|----------|--------|
| 1 | Implement WebSocket events (intrusion_detected, etc.) | 🔴 CRITICAL | 2-3h | TODO |
| 2 | Fix Error Response Format | 🟠 HIGH | 1-2h | TODO |
| 3 | Add `zone_name` to Alert response | 🟠 HIGH | 1-2h | TODO |
| 4 | Enhance Logs Stats (week, peak_hour, etc.) | 🟡 MEDIUM | 2-3h | TODO |
| 5 | Optional: Add MJPEG stream endpoints | 🟡 MEDIUM | 2-3h | Optional |
| 6 | Implement FCM sending service | 🟡 MEDIUM | 3-4h | TODO |
| **TOTAL** | | | **11-17h** | |

---

### Android (Flutter App)

| # | Task | Priority | Thời gian | Status |
|----|------|----------|----------|--------|
| 1 | Add missing API methods (getZoneDetails, updateZone, etc.) | 🟡 MEDIUM | 3-4h | TODO |
| 2 | Update Stream handling (MJPEG → RTSP/HLS) | 🟠 HIGH | 2-3h | TODO |
| 3 | Fix Error handling to match new format | 🟠 HIGH | 1-2h | TODO |
| 4 | Add `updated_at` to ZoneModel | 🟡 MEDIUM | 30min | TODO |
| 5 | Handle WebSocket "connected" event | 🟡 MEDIUM | 30min | TODO |
| 6 | Fix Package name consistency | 🟡 MEDIUM | 1-2h | TODO |
| 7 | Add missing video_player dependency | 🟡 MEDIUM | 30min | TODO |
| **TOTAL** | | | **8-12h** | |

---

## 🎯 PHƯƠNG ÁN THỰC HIỆN

### Phase 1: CRITICAL (1-2 ngày)
**Backend:**
1. ✅ WebSocket events (2-3h)
2. ✅ Error format (1-2h)
3. ✅ zone_name in alerts (1-2h)

**Android:**
1. ✅ Stream handling (2-3h)
2. ✅ Error handling (1-2h)
3. ✅ API methods (3-4h)

**Mục tiêu**: Ứng dụng hoạt động chính, real-time alerts, stream video

---

### Phase 2: IMPORTANT (1-2 ngày)
**Backend:**
1. ✅ Logs stats enhancement (2-3h)
2. ✅ FCM service (3-4h)

**Android:**
1. ✅ Data models (30min)
2. ✅ WebSocket connection handling (30min)
3. ✅ Package name fix (1-2h)

**Mục tiêu**: Push notifications, dashboard stats, data consistency

---

### Phase 3: OPTIONAL
**Backend:**
1. MJPEG stream endpoints (2-3h) - if needed for legacy support

**Android:**
1. UI enhancements
2. Performance optimization

---

## ✅ TESTING CHECKLIST

### Backend
- [ ] WebSocket connection test
- [ ] Intrusion event broadcasting test
- [ ] Error response format test
- [ ] Stats query performance test
- [ ] FCM delivery test

### Android
- [ ] Login and get token
- [ ] Stream video playback
- [ ] WebSocket real-time alerts
- [ ] Zone management (create, update, delete)
- [ ] Alert list with pagination
- [ ] Push notification receive
- [ ] Error handling (404, 401, etc.)
- [ ] Offline behavior

---

## 📞 SUMMARY

**Current Status:**
- Backend: 70% complete, 5 major issues
- Android: 65% complete, 6 major issues
- **Misalignment**: Significant

**After Implementation:**
- Both systems will be **95%+ aligned** with API_DESIGN.md
- Real-time alerts functional
- Stream video working
- Push notifications working
- Dashboard stats complete

**Total Effort:**
- Backend: 11-17 hours
- Android: 8-12 hours
- **Total: ~25-29 hours** (assuming ~2 developers working in parallel)

**Timeline:**
- Phase 1 (Critical): 1-2 days (parallel work)
- Phase 2 (Important): 1-2 days
- Phase 3 (Optional): As needed

---

**Document Version:** 1.0  
**Created:** May 17, 2026  
**Status:** Ready for implementation
