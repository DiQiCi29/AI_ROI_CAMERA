# 🏗️ AI_ROI_CAMERA Backend - Complete Design Document

**Version**: 1.0.0  
**Last Updated**: May 17, 2026  
**Status**: Production Ready

---

## 📋 Executive Summary

This document provides a comprehensive design specification for the AI_ROI_CAMERA backend system. It covers architecture, API design, database schema, security protocols, and deployment guidelines.

**Key Features**:
- ✅ Real-time camera streaming with RTSP support
- ✅ YOLOv8s-based AI detection (person & objects)
- ✅ Multi-zone intrusion detection with configurable cooldown
- ✅ WebSocket real-time event broadcasting
- ✅ Firebase Cloud Messaging (FCM) push notifications
- ✅ JWT-based authentication with role-based access control
- ✅ MySQL database with ORM (SQLAlchemy)
- ✅ RESTful API following industry standards
- ✅ Comprehensive analytics dashboard

---

## 🏛️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Android/Web Client                        │
├─────────────────────────────────────────────────────────────┤
│          HTTP REST API + WebSocket Connection               │
├─────────────────────────────────────────────────────────────┤
│         FastAPI Server (Python)                             │
│  ┌──────────┬──────────┬──────────┬──────────────────┐    │
│  │  Routes  │ Services │ Business │ Core Infrastructure│
│  │          │          │  Logic   │                 │    │
│  └──────────┴──────────┴──────────┴──────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│         Subsystems                                          │
│  ┌──────────┬──────────┬──────────┬──────────────────┐    │
│  │   YOLOv8 │ MediaMTX │ Firebase │    MySQL DB     │    │
│  │   AI     │  RTSP    │   FCM    │                 │    │
│  │ Detection│ Server   │ Messaging│                 │    │
│  └──────────┴──────────┴──────────┴──────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│         External Systems                                    │
│  ┌──────────┬──────────┐                                    │
│  │  RTSP    │ Firebase │                                    │
│  │ Cameras  │  Backend │                                    │
│  └──────────┴──────────┘                                    │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI | Modern async web framework |
| **Language** | Python 3.9+ | High productivity, ML support |
| **Database** | MySQL | Relational data persistence |
| **ORM** | SQLAlchemy | Database abstraction |
| **Auth** | JWT (HS256) | Stateless authentication |
| **AI** | YOLOv8s | Object detection (person/items) |
| **Streaming** | FFmpeg + MediaMTX | RTSP stream processing |
| **Real-time** | WebSocket | Bidirectional event channel |
| **Notifications** | Firebase Admin SDK | Push notifications |
| **Deployment** | Docker + Docker Compose | Container orchestration |

---

## 📊 Database Schema

### Database Diagram

```
users
├── id (PK)
├── username (UNIQUE)
├── email (UNIQUE)
├── hashed_password
├── role (admin|viewer)
├── is_active
├── created_at
└── updated_at

cameras
├── id (PK)
├── name
├── rtsp_url
├── location
├── resolution
├── status (online|offline)
├── is_active
├── last_seen_at
└── created_at

zones (FK: camera_id)
├── id (PK)
├── name
├── camera_id
├── zone_type (polygon|rectangle)
├── coordinates (JSON)
├── is_active
├── alert_cooldown_seconds
├── created_at
└── updated_at

alerts (FK: camera_id, zone_id)
├── id (PK)
├── camera_id
├── zone_id
├── bounding_boxes (JSON)
├── confidence
├── detected_at (INDEXED)
├── thumbnail_path
├── video_clip_path
├── is_acknowledged
└── created_at

intrusion_logs (FK: alert_id, camera_id, zone_id)
├── id (PK)
├── alert_id (ON DELETE CASCADE)
├── camera_id
├── zone_id
├── entered_at
├── exited_at
├── duration_seconds
└── created_at

fcm_tokens (FK: user_id)
├── id (PK)
├── user_id
├── token (UNIQUE)
├── device_name
├── is_active
├── created_at
└── last_used_at

notification_logs (FK: user_id, alert_id)
├── id (PK)
├── user_id
├── alert_id
├── title
├── body
├── is_success
├── error_msg
└── sent_at

devices (IoT)
├── id (PK)
├── name
├── device_type (light|siren|relay|sensor)
├── mqtt_topic (UNIQUE)
├── location
├── state (JSON)
├── is_online
└── last_seen_at
```

### Key Constraints

- **Cascading Deletes**: `alerts` → `intrusion_logs`, `fcm_tokens` → related tokens
- **Indexing**: 
  - `alerts.detected_at` for time-range queries
  - `zones.camera_id`, `zones.is_active` for zone filtering
  - `fcm_tokens.user_id`, `fcm_tokens.is_active` for push notification lookups

---

## 🔐 Security Architecture

### Authentication Flow

```
┌─────────────────────────────────────────┐
│  1. Client Submits Credentials          │
│     POST /auth/login                    │
│     {"username": "admin", ...}          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. Server Validates Password           │
│     Verify against bcrypt hash          │
│     Lookup user in database             │
└──────────────┬──────────────────────────┘
               │
         ┌─────┴─────┐
         │           │
         ▼           ▼
      Valid      Invalid
         │           │
         ▼           ▼
    Create JWT   401 Error
         │
         ▼
┌─────────────────────────────────────────┐
│  3. Return Token to Client              │
│     {access_token, expires_in: 86400}   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. Client Stores Token Securely        │
│     EncryptedSharedPreferences (Android)│
└─────────────────────────────────────────┘
```

### Token Structure

**JWT Payload**:
```json
{
  "sub": "1",              // User ID
  "role": "admin",         // User role
  "exp": 1726234800,       // Expiry timestamp
  "iat": 1726148400        // Issued at
}
```

**Generation**:
```python
token = jwt.encode(
    {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(minutes=1440)
    },
    settings.JWT_SECRET_KEY,
    algorithm=settings.JWT_ALGORITHM
)
```

### Password Security

- **Hashing**: Bcrypt with automatic salt
- **Verification**: Constant-time comparison
- **Minimum Requirements**:
  - Recommended: 12+ characters
  - Mix of uppercase, lowercase, numbers, special chars

### Role-Based Access Control (RBAC)

| Endpoint | Admin | Viewer | Public |
|----------|-------|--------|--------|
| `/auth/login` | ✓ | ✓ | ✓ |
| `/stream/*` | ✓ | ✓ | ✗ |
| `/zones/*` (POST/PUT/DELETE) | ✓ | ✗ | ✗ |
| `/zones/*` (GET) | ✓ | ✓ | ✗ |
| `/alerts/*` (POST/PATCH) | ✓ | ✓ | ✗ |
| `/alerts/*` (GET) | ✓ | ✓ | ✗ |
| `/media/*` (DELETE) | ✓ | ✗ | ✗ |
| `/media/*` (GET) | ✓ | ✓ | ✗ |

---

## 🎯 API Specification

### Request/Response Standard

**Success Response**:
```json
{
  "success": true,
  "data": {
    // Endpoint-specific data
  }
}
```

**Error Response**:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "http_status": 400
  }
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET/PATCH |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input validation |
| 401 | Unauthorized | Missing/invalid JWT token |
| 403 | Forbidden | Insufficient permissions (role-based) |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists (uniqueness) |
| 429 | Too Many Requests | Rate limit exceeded (future) |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Camera offline, external service down |

### Request Validation

All request bodies validated using Pydantic schemas with:
- Type checking
- Range validation (0-1 for confidence, 0-1280 for x-coordinate)
- Required/optional fields
- Custom validators for domain logic

---

## 🎬 Streaming Architecture

### RTSP Processing Pipeline

```
RTSP Camera Stream
       │
       ▼
┌──────────────────┐
│ FFmpeg Subprocess│
│ UDP Transport    │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────┐
│ Raw Video Frames (BGR24) │
│ 1280x720 @ 10 FPS        │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ YOLOv8s AI Detection     │
│ - Person detection       │
│ - Bounding boxes         │
│ - Confidence scores      │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ ROI Filtering            │
│ Check if bbox in zone    │
│ Apply cooldown logic     │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Annotation & Drawing     │
│ - Draw ROI polygon       │
│ - Draw bounding boxes    │
│ - Add confidence text    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Resize for Mobile        │
│ 1280x720 → 640x360       │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ JPEG Encoding            │
│ Quality: 70-75           │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ MJPEG Stream (multipart) │
│ ~100KB/frame @ 10 fps    │
│ ~10 Mbps bandwidth       │
└──────────────────────────┘
```

### Camera Configuration

**Per-Camera Settings**:
- `rtsp_url`: RTSP source (stored in database)
- `resolution`: Video resolution (default: 1280x720)
- `is_active`: Enable/disable camera
- `status`: Online/offline (updated by monitoring)

**Example Configuration**:
```python
{
    "id": 1,
    "name": "Cánh cổng chính",
    "rtsp_url": "rtsp://admin:pass@192.168.0.3:554/onvif1",
    "resolution": "1280x720",
    "is_active": True,
    "status": "online"
}
```

---

## 🤖 AI Detection System

### YOLOv8s Model

**Model Details**:
- **Architecture**: YOLOv8 small variant
- **Input**: 1280×720 frames
- **Output**: Bounding boxes with confidence
- **Classes**: COCO80 (includes 'person' as primary detection target)
- **Inference Speed**: ~50-100ms per frame @ 10 FPS
- **Model Size**: ~11.2 MB

### Detection Parameters

```python
YOLO_CONFIDENCE_THRESHOLD = 0.5      # Only boxes with confidence > 0.5
YOLO_NMS_THRESHOLD = 0.45            # NMS IOU threshold
YOLO_MODEL_PATH = "./app/ai/yolov8s.pt"
```

### ROI (Region of Interest) System

**Zone Types**:
1. **Polygon**: Custom multi-point region
2. **Rectangle**: Simple rectangular area

**Coordinate System**:
- Stored as percentages: 0-100% of frame
- Converted to pixels: (percentage/100) × frame_dimension
- Example: Zone at x=50%, y=50%, w=30%, h=40%
  - Pixels: x=640, y=360, w=384, h=288

**Bounding Box Filtering Logic**:
```python
def is_detection_in_zone(bbox, zone_coords):
    """
    Check if bounding box center is inside zone
    """
    bbox_center_x = bbox.x + bbox.w / 2
    bbox_center_y = bbox.y + bbox.h / 2
    
    return point_in_polygon(
        (bbox_center_x, bbox_center_y),
        zone_coords
    )
```

---

## 📡 Real-time Communication

### WebSocket Event Architecture

**Connection Lifecycle**:
```
1. Client connects with JWT token
   ws://server:8000/ws?token=<JWT>
   
2. Server validates token
   ├─ Valid: Accept connection
   └─ Invalid: Reject with 401

3. Server sends connection confirmation
   { "event": "connected", "data": {...} }

4. Client can subscribe to specific cameras
   { "event": "subscribe_camera", "data": { "camera_id": 1 } }

5. Server pushes events to subscribed clients
   { "event": "intrusion_detected", "data": {...} }

6. Client keeps connection alive with ping/pong
   { "event": "ping" } / { "event": "pong" }

7. Connection closes
   Connection.close(code=1000, reason="...")
```

### Event Types

| Event | Direction | Trigger | Purpose |
|-------|-----------|---------|---------|
| `connected` | Server → Client | On connection | Confirm connection |
| `intrusion_detected` | Server → Client | AI detects person | Alert users immediately |
| `intrusion_ended` | Server → Client | No detections for cooldown | Log session end |
| `camera_status_changed` | Server → Client | Camera goes online/offline | Notify user of camera status |
| `ping` | Client → Server | Every 30s | Keep connection alive |
| `pong` | Server → Client | Response to ping | Acknowledge keepalive |
| `subscribe_camera` | Client → Server | User subscribes | Start receiving camera events |
| `unsubscribe_camera` | Client → Server | User unsubscribes | Stop receiving camera events |

---

## 📨 Firebase Cloud Messaging (FCM)

### Notification Flow

```
Intrusion Detected
       │
       ▼
Alert Service
       │
       ▼
Query Active FCM Tokens
       │
       ▼
Build Notification Payload
{
  "title": "⚠️ Cảnh báo xâm nhập!",
  "body": "Vùng cổng chính",
  "sound": "alert_sound",
  "priority": "high",
  "color": "#FF0000"
}
       │
       ▼
Firebase Admin SDK
       │
       ▼
Send Multicast to Devices
       │
       ▼
Log Notification Results
       │
       ▼
Clients Receive Push Notification
```

### FCM Configuration

**Setup Steps**:
1. Create Firebase project
2. Download service account key (JSON)
3. Store path in `FIREBASE_CREDENTIALS_PATH`
4. Initialize Firebase Admin SDK

**Notification Format**:
```python
message = messaging.MulticastMessage(
    notification=messaging.Notification(
        title="⚠️ Cảnh báo xâm nhập!",
        body=zone_name,
    ),
    android=messaging.AndroidConfig(
        priority="high",
        notification=messaging.AndroidNotification(
            sound="alert_sound",
            color="#FF0000",
            click_action="com.airoicamera.ACTION_ALERT",
            tag=str(alert_id),
        ),
    ),
    tokens=token_list,
)
```

---

## 📊 Analytics Engine

### Metrics Calculated

```python
def calculate_stats(from_date=None, to_date=None):
    return {
        "total_intrusions": COUNT(alerts),
        "intrusions_today": COUNT(alerts WHERE date = TODAY),
        "intrusions_this_week": COUNT(alerts WHERE date >= WEEK_START),
        "most_active_zone": MODE(zone_id),
        "peak_hour": MODE(HOUR(detected_at)),
        "by_zone": {
            "zone_name": COUNT(alerts WHERE zone_id = X),
            ...
        }
    }
```

### Time-Series Data

**Available Aggregations**:
- Per hour: `GROUP BY DATE_TRUNC('hour', detected_at)`
- Per day: `GROUP BY DATE(detected_at)`
- Per week: `GROUP BY WEEK(detected_at)`
- Per month: `GROUP BY MONTH(detected_at)`

---

## 🔧 Configuration Management

### Environment Variables (.env)

```bash
# Application
APP_NAME=AI_ROI_CAMERA
APP_VERSION=1.0.0
DEBUG=False  # Set to True only in development

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secure_password
DB_NAME=ai_roi_camera

# Security
JWT_SECRET_KEY=generate_with_secrets.token_urlsafe(32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-adminsdk.json

# Streaming
MEDIAMTX_HOST=localhost
MEDIAMTX_PORT=9997

# AI
YOLO_MODEL_SIZE=small
YOLO_MODEL_PATH=./app/ai/yolov8s.pt
YOLO_CONFIDENCE_THRESHOLD=0.5
YOLO_NMS_THRESHOLD=0.45
```

### Runtime Configuration

Loaded via `app/core/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # All config values read from environment
    # with defaults if not set
    
    class Config:
        env_file = ".env"
```

---

## 🚀 Deployment Architecture

### Docker Compose Stack

```yaml
services:
  backend:
    image: ai-roi-camera:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - MEDIAMTX_HOST=mediamtx
    depends_on:
      - db
      - mediamtx
    volumes:
      - ./alerts:/app/alerts
      - ./firebase-adminsdk.json:/app/firebase-adminsdk.json

  db:
    image: mysql:8.0
    ports:
      - "3306:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=ai_roi_camera
    volumes:
      - mysql_data:/var/lib/mysql

  mediamtx:
    image: bluenviron/mediamtx:latest
    ports:
      - "8554:8554"    # RTSP
      - "9997:9997"    # API
    volumes:
      - ./mediamtx.yml:/etc/mediamtx/mediamtx.yml

volumes:
  mysql_data:
```

### Startup Process

```
1. Docker Compose brings up all services
   docker-compose up -d

2. MySQL starts and initializes database
   
3. Backend container starts FastAPI app
   - Connects to MySQL
   - Creates tables via SQLAlchemy
   - Loads YOLOv8s model
   - Initializes Firebase Admin SDK
   
4. MediaMTX starts RTSP server
   - Listens on port 8554

5. Backend ready to accept connections
   http://localhost:8000/docs (Swagger UI)
   ws://localhost:8000/ws (WebSocket)
```

---

## 🧪 Testing & QA

### Unit Tests

```python
# Test authentication
def test_login_success():
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "password"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]

# Test zone creation
def test_create_zone_requires_admin():
    response = client.post("/zones", headers={
        "Authorization": "Bearer viewer_token"
    }, json={...})
    assert response.status_code == 403
```

### Integration Tests

```python
# Full alert workflow
def test_alert_workflow():
    # 1. Create zone
    zone = create_zone(...)
    
    # 2. Create alert
    alert = create_alert(..., zone_id=zone.id)
    
    # 3. Verify alert in list
    alerts = get_alerts()
    assert alert.id in [a.id for a in alerts]
    
    # 4. Mark as read
    mark_as_read(alert.id)
    
    # 5. Verify read status
    updated = get_alert(alert.id)
    assert updated.is_read == True
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# Using Locust
locust -f locustfile.py --host http://localhost:8000
```

---

## 📋 Checklist for Production Deployment

- [ ] Change JWT_SECRET_KEY to strong random value
- [ ] Set DEBUG=False
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up MySQL backups (daily)
- [ ] Configure Firebase credentials
- [ ] Set up logging and monitoring
- [ ] Configure RTSP camera URLs in database
- [ ] Test FCM push notifications
- [ ] Load test streaming endpoints
- [ ] Set up rate limiting
- [ ] Configure CORS for production domain
- [ ] Enable database connection pooling
- [ ] Set up audit logging
- [ ] Configure media file storage (S3/NFS)
- [ ] Test disaster recovery/failover
- [ ] Document operational procedures

---

## 🐛 Troubleshooting Guide

### Camera Not Connecting

**Symptoms**: `CAMERA_OFFLINE` error

**Diagnosis**:
1. Check camera power and network
2. Verify RTSP URL: `ffmpeg -rtsp_transport udp -i rtsp://... -frames 1 -f null -`
3. Check firewall rules on camera port

**Solution**:
```bash
# Test RTSP connection
ffmpeg -rtsp_transport udp -i rtsp://camera:554/stream -f null -
```

### High Latency on Stream

**Symptoms**: Real-time stream has 5+ second delay

**Causes**:
1. RTSP camera buffering
2. Network bandwidth issues
3. AI inference slow (CPU-bound)

**Solution**:
```python
# Reduce resolution or FPS
def open_ffmpeg_pipe(width=480, height=270, fps=5):  # Reduced
    ...
```

### FCM Notifications Not Arriving

**Symptoms**: Push notifications don't reach device

**Diagnosis**:
1. Verify FCM token is registered: `SELECT * FROM fcm_tokens WHERE user_id = X`
2. Check Firebase console for errors
3. Verify Firebase credentials file

**Solution**:
```bash
# Re-register FCM token on client
POST /auth/register-fcm-token
```

---

## 📝 API Versioning

**Current Version**: v1 (`/api/v1/*`)

**Versioning Strategy**:
- Major version for breaking changes (v2, v3)
- Minor version for backward-compatible features
- Use header: `API-Version: 1.0.0` (optional)

**Deprecation Policy**:
- Notify clients 3 months in advance
- Maintain old version for 6 months overlap
- Provide migration guide

---

## 📚 Related Documentation

- [Android Integration Guide](./ANDROID_API_GUIDE.md)
- [API Architecture](./API_ARCHITECTURE.md)
- [Implementation Timeline](./IMPLEMENTATION_TIMELINE.md)
- [Getting Started](./GETTING_STARTED.md)

---

**Document Version**: 1.0.0  
**Last Updated**: May 17, 2026  
**Maintained by**: AI_ROI_CAMERA Development Team

---

## Fixes Applied ✅

This document reflects the following improvements made to the backend:

1. ✅ **JWT Secret**: Moved from hardcode to environment configuration
2. ✅ **RTSP URL**: Made configurable per-camera from database
3. ✅ **Role-Based Access Control**: Implemented admin/viewer role enforcement
4. ✅ **Input Validation**: Added comprehensive validation to bounding box coordinates
5. ✅ **Service Layer**: Implemented AuthService, AlertService, StreamService
6. ✅ **Configuration**: Created .env.example template with all settings
7. ✅ **Security**: Enhanced security dependencies with role checking functions
