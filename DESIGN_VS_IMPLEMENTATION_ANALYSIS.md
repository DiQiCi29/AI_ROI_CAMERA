# 🔍 Phân Tích Sự Khác Biệt Giữa Thiết Kế API và Dự Án Thực Tế

**So sánh API_DESIGN.md (bản thiết kế) với AI_ROI_CAMERA (implementation)**

---

## 📊 Tóm Tắt Nhanh

| Khía cạnh | Thiết Kế | Thực Tế | Trạng Thái |
|-----------|----------|--------|-----------|
| Stream API | MJPEG + Snapshot | RTSP/HLS/WebRTC URLs | ⚠️ KHÁC |
| Error Format | `error` + `http_status` | Chỉ `detail` | ⚠️ KHÁC |
| WebSocket Events | 5 events cụ thể | 3 events cơ bản | ⚠️ THIẾU |
| Alert Response | Có `zone_name`, `object_count` | Thiếu `zone_name` | ⚠️ THIẾU |
| Error Response | `{success: false, error: {...}}` | `{detail: {...}}` | ⚠️ KHÁC |
| Zone Coordinates | % (0-100) | % (0-100) | ✅ GIỐNG |
| Auth Flow | Đầy đủ (FCM + logout) | Đầy đủ | ✅ OK |
| Media API | Đầy đủ | Đầy đủ | ✅ OK |
| Logs API | Đầy đủ | Đầy đủ | ✅ OK |

---

## 🔴 KHÁC BIỆT CHI TIẾT

### 1. ⚠️ STREAM API - THIẾT KẾ VS THỰC TẾ

#### Thiết Kế (API_DESIGN.md):
```
GET /stream/video → MJPEG stream (multipart/x-mixed-replace)
GET /stream/snapshot → Single JPEG image
GET /stream/status → Camera status
```

#### Thực Tế (AI_ROI_CAMERA):
```
GET /stream/status → Camera status (matches)
GET /stream/urls → Returns stream URLs (RTSP, HLS, WebRTC)
```

**Các vấn đề:**
- ❌ Thiếu `/stream/video` (MJPEG stream endpoint)
- ❌ Thiếu `/stream/snapshot` (snapshot JPEG endpoint)
- ✅ Có `/stream/urls` (thay thế, nhưng khác thiết kế)

**Impact lên Flutter App:**
- Flutter app được thiết kế để stream MJPEG từ `/stream/video`
- Nhưng backend trả về URLs (RTSP/HLS/WebRTC)
- Flutter cần thay đổi để support RTSP/HLS streams thay vì MJPEG

**MediaMTX Configuration (thực tế):**
```python
MEDIAMTX_HOST = "localhost"
CAMERA_RTSP = "rtsp://35639463:123@192.168.0.2:554/onvif1"

# Returns:
# rtsp://localhost:8554/camera_01
# http://localhost:8888/camera_01 (HLS)
# http://localhost:8889/camera_01 (WebRTC)
```

---

### 2. ⚠️ ERROR RESPONSE FORMAT - KHÁC BIỆT

#### Thiết Kế (API_DESIGN.md):
```json
{
  "success": false,
  "error": {
    "code": "ZONE_NOT_FOUND",
    "message": "Zone with ID zone_abc123 not found",
    "http_status": 404
  }
}
```

#### Thực Tế (AI_ROI_CAMERA):
```json
{
  "detail": {
    "code": "ZONE_NOT_FOUND",
    "message": "Not found"
  }
}
```

**Các vấn đề:**
- ❌ Thiếu field `success: false`
- ❌ Thiếu field `http_status` (HTTP status code trong response body)
- ❌ Không có wrapper `error`, thay vào đó là `detail`

**Impact lên Flutter App:**
- Flutter app dự tính parse `response.error.code`
- Nhưng thực tế là `response.detail.code`
- Cần cập nhật error handling logic

---

### 3. ⚠️ WEBSOCKET EVENTS - THIẾU CÁC EVENT QUAN TRỌNG

#### Thiết Kế (API_DESIGN.md):
```javascript
// Server → App events:
"intrusion_detected"     // ← CHÍNH: Cảnh báo xâm nhập
"intrusion_ended"        // ← CHÍNH: Xâm nhập kết thúc
"camera_status_changed"  // ← Important: Camera online/offline

// App → Server events:
"subscribe_camera"
"unsubscribe_camera"
"ping" / "pong"
```

#### Thực Tế (AI_ROI_CAMERA):
```javascript
// Server → App events:
"connected"              // Connection ack
(không có intrusion_detected)
(không có intrusion_ended)
(không có camera_status_changed)

// App → Server events:
"subscribe_camera"       // Có ✓
"unsubscribe_camera"     // Có ✓
"ping" / "pong"          // Có ✓
```

**Các vấn đề:**
- ❌ Không có `intrusion_detected` - **CỰC KỲ QUAN TRỌNG** cho real-time alerts
- ❌ Không có `intrusion_ended` - để biết khi nào xâm nhập kết thúc
- ❌ Không có `camera_status_changed` - để detect camera online/offline

**Impact lên Flutter App:**
- App được thiết kế để lắng nghe `intrusion_detected` events
- Nhưng backend không gửi event này → App không nhận real-time alerts via WebSocket
- App phải poll `/alerts` endpoint liên tục (không tối ưu)
- **Mất tính năng real-time alert quan trọng**

**Note**: Có hàm `broadcast_event()` trong websocket.py nhưng không ai gọi nó!

---

### 4. ⚠️ ALERT RESPONSE - THIẾU FIELDS

#### Thiết Kế (API_DESIGN.md) - List alerts:
```json
{
  "alert_id": "alert_xyz789",
  "zone_id": "zone_abc123",
  "zone_name": "Vùng cấm cửa chính",        // ← THIẾU trong thực tế
  "camera_id": "cam_01",
  "detected_at": "2024-01-15T10:35:00Z",
  "is_read": false,
  "thumbnail_url": "/media/alerts/alert_xyz789/thumbnail.jpg",
  "video_url": "/media/alerts/alert_xyz789/clip.mp4",
  "object_count": 1,                        // ← THIẾU trong thực tế
  "confidence": 0.95
}
```

#### Thực Tế (AI_ROI_CAMERA):
```json
{
  "alert_id": "1",
  "zone_id": "1",
  // zone_name: MISSING
  "camera_id": "cam_01",
  "detected_at": "2024-01-01T12:00:00",
  "is_read": false,
  "thumbnail_url": "/api/v1/media/alerts/1/thumbnail",
  "video_url": "/api/v1/media/alerts/1/video",
  // object_count: MISSING (sử dụng hardcoded = 1)
  "confidence": 0.95
}
```

**Các vấn đề:**
- ❌ Thiếu `zone_name` - phải join từ Zone table hoặc trả trong response
- ❌ `object_count` hardcoded = 1 - không chính xác

**Current code** (alerts.py):
```python
def alert_to_dict(a: Alert, include_bbox=False) -> dict:
    base = {
        "alert_id": str(a.id),
        "zone_id": str(a.zone_id) if a.zone_id else None,
        # "zone_name": Missing!
        "camera_id": str(a.camera_id) if a.camera_id else None,
        "detected_at": a.detected_at,
        "is_read": bool(a.is_acknowledged),
        "thumbnail_url": f"/api/v1/media/alerts/{a.id}/thumbnail" if a.thumbnail_path else None,
        "video_url": f"/api/v1/media/alerts/{a.id}/video" if a.video_clip_path else None,
        "object_count": 1,  # ← Hardcoded!
        "confidence": a.confidence,
    }
```

**Impact lên Flutter App:**
- App dự định hiển thị zone name trên alert item
- Nhưng backend không trả → cần gọi API zone riêng hoặc cấu trúc lại logic
- Không lý tưởng

---

### 5. ⚠️ LOGS STATS RESPONSE - THIẾU FIELDS

#### Thiết Kế (API_DESIGN.md):
```json
{
  "total_intrusions": 45,
  "intrusions_today": 3,
  "intrusions_this_week": 12,           // ← THIẾU trong thực tế
  "most_active_zone": {                 // ← THIẾU trong thực tế
    "zone_id": "zone_abc123",
    "zone_name": "Vùng cấm cửa chính",
    "count": 30
  },
  "peak_hour": 14,                      // ← THIẾU trong thực tế
  "by_zone": [...]                      // ← THIẾU trong thực tế
}
```

#### Thực Tế (AI_ROI_CAMERA):
```json
{
  "total_intrusions": 42,
  "intrusions_today": 5
  // Missing: intrusions_this_week, most_active_zone, peak_hour, by_zone
}
```

**Current code** (logs.py):
```python
@router.get("/stats")
def get_stats(...):
    return {"success": True, "data": {
        "total_intrusions": total,
        "intrusions_today": today_count,
        # Thiếu insights khác
    }}
```

**Impact lên Flutter App:**
- Dashboard stats screen sẽ thiếu data để hiển thị
- Không thể show peak hour, most active zone, weekly stats

---

### 6. ✅ RESPONSE FORMAT SUCCESS - GIỐNG

#### Thiết Kế & Thực Tế:
```json
{
  "success": true,
  "data": { /* ... */ }
}
```

**Status:** ✅ Matching

---

### 7. ✅ ZONE COORDINATES - GIỐNG

#### Thiết Kế:
```json
"coordinates": [
  { "x": 10.5, "y": 20.0 },      // % (0-100)
  { "x": 60.0, "y": 20.0 }
]
```

#### Thực Tế:
```json
"coordinates": [
  { "x": 10.5, "y": 20.0 },      // % (0-100)
  { "x": 60.0, "y": 20.0 }
]
```

**Status:** ✅ Matching

---

## 📋 TỔNG HỢP DANH SÁCH KHÁC BIỆT

### 🔴 CRITICAL (Ảnh hưởng lớn đến Flutter App):

1. **WebSocket Events Thiếu** 
   - ❌ `intrusion_detected` - Mất real-time alerts
   - ❌ `intrusion_ended`
   - ❌ `camera_status_changed`
   - **Mức độ**: **CRITICAL** - App không thể nhận real-time alerts via WS

2. **Stream API Khác**
   - ❌ Thiếu `/stream/video` (MJPEG)
   - ❌ Thiếu `/stream/snapshot`
   - ✅ Thêm `/stream/urls` (RTSP/HLS/WebRTC)
   - **Mức độ**: **HIGH** - Streaming architecture khác hoàn toàn

3. **Error Response Format**
   - ❌ `{detail: {...}}` thay vì `{success: false, error: {...}}`
   - ❌ Thiếu `http_status` field
   - **Mức độ**: **MEDIUM** - Error handling cần cập nhật

### 🟡 IMPORTANT (Ảnh hưởng trung bình):

4. **Alert Response Thiếu Fields**
   - ❌ Thiếu `zone_name`
   - ❌ `object_count` hardcoded = 1
   - **Mức độ**: **MEDIUM** - UI display không hoàn hảo

5. **Logs Stats Thiếu Data**
   - ❌ Thiếu `intrusions_this_week`
   - ❌ Thiếu `most_active_zone`
   - ❌ Thiếu `peak_hour`
   - ❌ Thiếu `by_zone` breakdown
   - **Mức độ**: **MEDIUM** - Dashboard stats không đầy đủ

---

## 🔧 KHUYẾN NGHỊ SỬA LỖI

### Priority 1: CRITICAL

**Fix WebSocket Events:**
```python
# In websocket.py or alert detection service
async def broadcast_event(event: str, data: dict):
    # Already exists! But needs to be called from detection logic
    
# When intrusion detected, send:
await broadcast_event("intrusion_detected", {
    "alert_id": str(alert.id),
    "zone_id": str(alert.zone_id),
    "camera_id": alert.camera_id,
    "detected_at": alert.detected_at.isoformat(),
    "confidence": alert.confidence,
    "thumbnail_url": f"/api/v1/media/alerts/{alert.id}/thumbnail",
    "bounding_boxes": alert.bounding_boxes
})

# When intrusion ends:
await broadcast_event("intrusion_ended", {
    "alert_id": str(alert.id),
    "zone_id": str(alert.zone_id),
    "exited_at": datetime.utcnow().isoformat(),
    "duration_seconds": (exited_at - entered_at).total_seconds()
})
```

**Add MJPEG Stream Endpoint (Alternative):**
```python
# Option 1: Keep MJPEG support
@router.get("/stream/video", tags=["Camera Stream"])
async def stream_mjpeg(current_user: User = Depends(get_current_user)):
    # Return MJPEG stream from MediaMTX
    pass

# Option 2: Keep current design, update Flutter to use RTSP/HLS
# (Current /stream/urls approach is actually better for scalability)
```

---

### Priority 2: HIGH

**Fix Error Response Format:**
```python
# Current: HTTPException automatically returns {"detail": {...}}
# Option 1: Create custom exception handler
from fastapi.exceptions import RequestValidationError

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "success": False,
        "error": {
            "code": exc.detail.get("code"),
            "message": exc.detail.get("message"),
            "http_status": exc.status_code
        }
    }
```

---

### Priority 3: MEDIUM

**Enrich Alert Response:**
```python
def alert_to_dict(a: Alert, db: Session, include_bbox=False) -> dict:
    zone = db.query(Zone).filter(Zone.id == a.zone_id).first()
    return {
        "alert_id": str(a.id),
        "zone_id": str(a.zone_id) if a.zone_id else None,
        "zone_name": zone.name if zone else None,  # ADD THIS
        "camera_id": str(a.camera_id) if a.camera_id else None,
        "detected_at": a.detected_at,
        "is_read": bool(a.is_acknowledged),
        "thumbnail_url": f"/api/v1/media/alerts/{a.id}/thumbnail",
        "video_url": f"/api/v1/media/alerts/{a.id}/video",
        "object_count": a.bounding_boxes.__len__() if a.bounding_boxes else 1,  # FIX THIS
        "confidence": a.confidence,
    }
```

**Enhance Logs Stats:**
```python
@router.get("/logs/stats")
def get_stats(from_date, to_date, db: Session):
    q = db.query(IntrusionLog)
    if from_date: q = q.filter(IntrusionLog.entered_at >= from_date)
    if to_date: q = q.filter(IntrusionLog.entered_at <= to_date)

    total = q.count()
    today_count = q.filter(func.date(IntrusionLog.entered_at) == date.today()).count()
    
    # ADD MISSING STATS:
    week_count = q.filter(IntrusionLog.entered_at >= date.today() - timedelta(days=7)).count()
    
    by_zone = db.query(Zone.name, func.count(IntrusionLog.id))\
        .join(IntrusionLog, Zone.id == IntrusionLog.zone_id)\
        .group_by(Zone.id).all()
    
    return {"success": True, "data": {
        "total_intrusions": total,
        "intrusions_today": today_count,
        "intrusions_this_week": week_count,
        "by_zone": [{"zone_name": z[0], "count": z[1]} for z in by_zone],
        # Thêm peak_hour nếu cần
    }}
```

---

## 📝 KẾT LUẬN

| Mục | Tình Trạng | Khuyến Nghị |
|-----|-----------|------------|
| **Stream** | Thay đổi hoàn toàn từ MJPEG → RTSP/HLS/WebRTC | Giữ nguyên `/stream/urls`, update Flutter |
| **WebSocket** | Thiếu 3 events quan trọng | **CẦN SỬA ngay** |
| **Error Format** | Khác với thiết kế | Có thể cập nhật hoặc giữ nguyên (tùy) |
| **Alert Fields** | Thiếu `zone_name` + `object_count` | Nên sửa cho consistency |
| **Logs Stats** | Thiếu 4 fields | Nên thêm vào |

---

**Tệp tài liệu này sẽ giúp:**
1. Backend dev biết cần sửa gì
2. Flutter dev biết cần adapt code như thế nào
3. Giảm thiểu lỗi kết nối & integration issues

---

**Cập nhật lần cuối:** May 17, 2026
