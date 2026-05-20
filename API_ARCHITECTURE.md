# API Architecture Documentation
**AI ROI Camera Smart Home System**

---

## 1. Server Configuration

### Framework
- **Framework**: FastAPI (Python)
- **API Version**: v1
- **App Name**: AI_ROI_CAMERA
- **API Base URL**: `http://<server-host>:<port>/api/v1`
- **WebSocket URL**: `ws://<server-host>:<port>/ws`

### Port Configuration
- **FastAPI App**: `8000` (default, change in .env if needed)
- **MySQL Database**: `3306`
- **MQTT**: `1883`
- **MediaMTX RTSP/HLS**: 
  - HTTP API: `9997`
  - RTSP: `8554`
  - HLS: `8888`
  - WebRTC: `8889`

### Database
- **Type**: MySQL 8.0
- **Host**: `localhost` or `127.0.0.1` (in docker: `mysql` service name)
- **Port**: `3306`
- **Database Name**: `AI_ROI_CAMERA`
- **User**: `root`
- **Password**: `258463` (should be moved to .env for production)

### CORS Settings
- **Allow Origins**: `*` (any origin allowed)
- **Allow Credentials**: `true`
- **Allow Methods**: All (`*`)
- **Allow Headers**: All (`*`)

---

## 2. Authentication

### JWT Authentication
- **Algorithm**: HS256
- **Secret Key**: `your-super-secret-key-change-this` ⚠️ (Must be changed in production)
- **Token Expiration**: 24 hours (1440 minutes)
- **Token Type**: Bearer

### Login Endpoint
```
POST /api/v1/auth/login
Content-Type: application/json

Request:
{
  "username": "string",
  "password": "string"
}

Response Success (200):
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}

Response Error (401):
{
  "detail": {
    "code": "UNAUTHORIZED",
    "message": "Sai tên đăng nhập hoặc mật khẩu"
  }
}
```

### Token Usage
All protected endpoints require the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## 3. API Endpoints

### 3.1 Health Check (No Authentication Required)
```
GET /api/v1/health
GET /api/v1/hello

Response (200):
{
  "status": "ok",
  "app": "AI_ROI_CAMERA",
  "version": "1.0.0"
}
```

### 3.2 Authentication (auth.py)
**Prefix**: `/api/v1/auth`

#### Login
```
POST /api/v1/auth/login
```
- **No Auth Required**: No
- **Input**: LoginRequest (username, password)
- **Output**: Access token with 24-hour expiry

#### Register FCM Token
```
POST /api/v1/auth/register-fcm-token
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "fcm_token": "string",
  "device_id": "string"
}

Response (200):
{
  "success": true,
  "message": "FCM token registered successfully"
}
```

#### Logout
```
DELETE /api/v1/auth/logout
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "device_id": "string"
}

Response (200):
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

### 3.3 Stream Management (stream.py)
**Prefix**: `/api/v1/stream`

#### Get Stream Status
```
GET /api/v1/stream/status
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "data": {
    "camera_id": "cam_01",
    "status": "online|offline",
    "resolution": {"width": 1920, "height": 1080},
    "fps": 15
  }
}
```

#### Get Stream URLs
```
GET /api/v1/stream/urls
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "data": {
    "camera_id": "camera_01",
    "rtsp": "rtsp://localhost:8554/camera_01",
    "hls": "http://localhost:8888/camera_01",
    "webrtc": "http://localhost:8889/camera_01"
  }
}
```

**MediaMTX Configuration**:
- RTSP Source: `rtsp://35639463:123@192.168.0.2:554/onvif1`
- Camera Name: `camera_01`
- Host: `localhost` (default)

---

### 3.4 Zone Management (zones.py)
**Prefix**: `/api/v1/zones`

#### Create Zone
```
POST /api/v1/zones
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "name": "string",
  "camera_id": "string",
  "zone_type": "string",
  "coordinates": [
    {"x": number, "y": number},
    {"x": number, "y": number}
  ],
  "is_active": boolean,
  "alert_cooldown_seconds": number (optional, default: 30)
}

Response (201):
{
  "success": true,
  "data": {
    "zone_id": "string",
    "name": "string",
    "camera_id": "string",
    "zone_type": "string",
    "coordinates": [...],
    "is_active": boolean,
    "alert_cooldown_seconds": 30,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

#### List Zones
```
GET /api/v1/zones?camera_id=cam_01&is_active=true
Authorization: Bearer <token>

Query Parameters:
- camera_id (optional)
- is_active (optional): true|false

Response (200):
{
  "success": true,
  "data": [
    {
      "zone_id": "1",
      "name": "Zone A",
      "camera_id": "cam_01",
      ...
    }
  ]
}
```

#### Get Zone by ID
```
GET /api/v1/zones/{zone_id}
Authorization: Bearer <token>

Response (200): Zone object
```

#### Update Zone
```
PUT /api/v1/zones/{zone_id}
Authorization: Bearer <token>

Request: Partial ZoneUpdate object (all fields optional)
```

#### Delete Zone
```
DELETE /api/v1/zones/{zone_id}
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "message": "Zone deleted successfully"
}
```

#### Toggle Zone Active Status
```
PATCH /api/v1/zones/{zone_id}/toggle
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "data": {...zone_data...}
}
```

---

### 3.5 Alerts (alerts.py)
**Prefix**: `/api/v1/alerts`

#### Get Unread Count
```
GET /api/v1/alerts/unread-count
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "data": {"unread_count": 5}
}
```

#### Mark All as Read
```
PATCH /api/v1/alerts/read-all
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "message": "All alerts marked as read"
}
```

#### List Alerts (Paginated)
```
GET /api/v1/alerts?page=1&limit=20&zone_id=1&is_read=false
Authorization: Bearer <token>

Query Parameters:
- page (default: 1, min: 1)
- limit (default: 20, min: 1, max: 100)
- zone_id (optional)
- is_read (optional): true|false
- from_date (optional): ISO datetime
- to_date (optional): ISO datetime

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {
        "alert_id": "1",
        "zone_id": "1",
        "camera_id": "cam_01",
        "detected_at": "2024-01-01T12:00:00",
        "is_read": false,
        "thumbnail_url": "/api/v1/media/alerts/1/thumbnail",
        "video_url": "/api/v1/media/alerts/1/video",
        "object_count": 1,
        "confidence": 0.95
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```

#### Get Alert by ID
```
GET /api/v1/alerts/{alert_id}
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "data": {
    "alert_id": "1",
    "zone_id": "1",
    "camera_id": "cam_01",
    "detected_at": "2024-01-01T12:00:00",
    "is_read": false,
    "thumbnail_url": "/api/v1/media/alerts/1/thumbnail",
    "video_url": "/api/v1/media/alerts/1/video",
    "object_count": 1,
    "confidence": 0.95,
    "bounding_boxes": [...]
  }
}
```

#### Mark Alert as Read
```
PATCH /api/v1/alerts/{alert_id}/read
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "data": {
    "alert_id": "1",
    "is_read": true
  }
}
```

---

### 3.6 Intrusion Logs (logs.py)
**Prefix**: `/api/v1/logs`

#### List Logs (Paginated)
```
GET /api/v1/logs?page=1&limit=20&zone_id=1
Authorization: Bearer <token>

Query Parameters:
- page (default: 1)
- limit (default: 20, max: 100)
- zone_id (optional)
- from_date (optional): ISO datetime
- to_date (optional): ISO datetime

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {
        "log_id": "1",
        "alert_id": "1",
        "camera_id": "cam_01",
        "entered_at": "2024-01-01T12:00:00",
        "exited_at": "2024-01-01T12:05:00",
        "duration_seconds": 300,
        "thumbnail_url": "/api/v1/media/alerts/1/thumbnail",
        "video_url": "/api/v1/media/alerts/1/video"
      }
    ],
    "pagination": {...}
  }
}
```

#### Get Statistics
```
GET /api/v1/logs/stats?from_date=2024-01-01T00:00:00
Authorization: Bearer <token>

Query Parameters:
- from_date (optional)
- to_date (optional)

Response (200):
{
  "success": true,
  "data": {
    "total_intrusions": 42,
    "intrusions_today": 5
  }
}
```

---

### 3.7 Media (media.py)
**Prefix**: `/api/v1/media`

#### Get Alert Thumbnail
```
GET /api/v1/media/alerts/{alert_id}/thumbnail
Authorization: Bearer <token>

Response: JPEG image file
```

#### Get Alert Video Clip
```
GET /api/v1/media/alerts/{alert_id}/video
Authorization: Bearer <token>

Response: MP4 video file
```

#### Delete Media
```
DELETE /api/v1/media/alerts/{alert_id}
Authorization: Bearer <token>

Response (200):
{
  "success": true,
  "message": "Media deleted successfully"
}
```

---

### 3.8 WebSocket (websocket.py)
**URL**: `ws://localhost:8000/ws?token=<access_token>`

#### Connection
- **Query Parameter**: `token` (required, JWT token)
- **Authentication**: JWT verification on connect
- **Default Message**: 
```json
{
  "event": "connected",
  "data": {
    "message": "WebSocket connected successfully",
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

#### Client Events

**Ping/Pong**:
```json
// Send
{"event": "ping"}

// Receive
{"event": "pong", "data": {"timestamp": "..."}}
```

**Subscribe to Camera**:
```json
// Send
{"event": "subscribe_camera", "data": {"camera_id": "cam_01"}}

// Receive
{"event": "subscribe_camera_ack", "data": {...}}
```

**Unsubscribe from Camera**:
```json
// Send
{"event": "unsubscribe_camera", "data": {"camera_id": "cam_01"}}

// Receive
{"event": "unsubscribe_camera_ack", "data": {...}}
```

#### Server Events (Broadcast)
Alert events from AI detection:
```json
{
  "event": "alert_detected",
  "data": {
    "alert_id": "1",
    "zone_id": "1",
    "camera_id": "cam_01",
    "confidence": 0.95,
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

---

## 4. Common Issues & Troubleshooting

### 4.1 Connection Issues (Most Common for Android)

#### Issue: "Connection Refused" or "Unable to connect to server"
**Solutions**:
1. **Check Server URL**: Ensure Android app is using correct IP/domain and port
   - Local testing: `http://127.0.0.1:8000` or `http://localhost:8000`
   - Network: `http://<server-ip>:8000` (not localhost)
   - Production: Use domain name with proper SSL

2. **Verify Server is Running**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
   Should return: `{"status": "ok", "app": "AI_ROI_CAMERA", "version": "1.0.0"}`

3. **Check Firewall**: Ensure port 8000 is not blocked
   - Windows: `netstat -ano | findstr :8000`
   - Linux: `sudo netstat -tulpn | grep :8000`

4. **Check Network**: Android emulator/device must be on same network
   - Emulator: Use `10.0.2.2:8000` to access host machine
   - Real device: Must use actual server IP (not localhost)

#### Issue: "CORS Error" in Android client
**Solution**: CORS is already enabled in server (allow_origins=["*"])
- If still getting CORS errors, verify:
  - Request includes proper Content-Type header
  - Check browser console for actual error message

#### Issue: "Authentication Failed" or "401 Unauthorized"
**Solutions**:
1. Verify credentials are correct (username/password)
2. Check token expiration (24-hour limit)
3. Ensure Authorization header format: `Authorization: Bearer <token>`
4. Check Secret Key hasn't changed (currently: `your-super-secret-key-change-this`)

### 4.2 Database Connection Issues
**Error**: `Connection refused` to MySQL
**Solutions**:
1. Verify MySQL is running: `mysql -u root -p258463`
2. Check credentials in config: `app/core/config.py`
3. For Docker: Use service name `mysql` instead of `localhost`

### 4.3 JWT Token Issues
**Expired Token**:
- Tokens expire after 24 hours
- Solution: Implement refresh token mechanism or re-login

**Invalid Token**:
- Verify Secret Key matches
- Check token hasn't been modified
- Current Secret Key: `your-super-secret-key-change-this`

---

## 5. Response Format

### Success Response
```json
{
  "success": true,
  "data": {...}
}
```

### Error Response
```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

### Common Error Codes
- `UNAUTHORIZED`: Authentication failed or token invalid
- `TOKEN_EXPIRED`: Token has expired
- `ZONE_NOT_FOUND`: Zone ID doesn't exist
- `ALERT_NOT_FOUND`: Alert ID doesn't exist
- `ZONE_ALREADY_EXISTS`: Zone name already exists

---

## 6. Data Models Summary

### User
- `id`: int
- `username`: string (unique)
- `hashed_password`: string
- `role`: string
- `is_active`: boolean

### Zone
- `id`: int
- `name`: string
- `camera_id`: string
- `zone_type`: string
- `coordinates`: JSON (polygon points)
- `is_active`: boolean
- `alert_cooldown_seconds`: int (default: 30)
- `created_at`: datetime
- `updated_at`: datetime

### Alert
- `id`: int
- `zone_id`: int (optional)
- `camera_id`: string
- `detected_at`: datetime
- `is_acknowledged`: boolean
- `confidence`: float (0-1)
- `thumbnail_path`: string (optional)
- `video_clip_path`: string (optional)
- `bounding_boxes`: JSON array
- `created_at`: datetime

### IntrusionLog
- `id`: int
- `alert_id`: int
- `camera_id`: string
- `entered_at`: datetime
- `exited_at`: datetime (optional)
- `duration_seconds`: int
- `created_at`: datetime

### FCMToken
- `id`: int
- `user_id`: int
- `token`: string
- `device_name`: string
- `is_active`: boolean
- `created_at`: datetime

---

## 7. Quick Start for Android App

### 1. Login
```
POST http://<server-ip>:8000/api/v1/auth/login
{
  "username": "your_username",
  "password": "your_password"
}
```
Save the `access_token` from response.

### 2. Check Server Health
```
GET http://<server-ip>:8000/api/v1/health
```

### 3. Get Zones
```
GET http://<server-ip>:8000/api/v1/zones
Headers: Authorization: Bearer <access_token>
```

### 4. List Alerts
```
GET http://<server-ip>:8000/api/v1/alerts?page=1&limit=20
Headers: Authorization: Bearer <access_token>
```

### 5. Connect to WebSocket (Real-time updates)
```
ws://<server-ip>:8000/ws?token=<access_token>
```

---

## 8. Production Deployment Checklist

- [ ] Change SECRET_KEY in `app/core/security.py`
- [ ] Change database password from `258463` to secure password
- [ ] Move credentials to `.env` file
- [ ] Set DEBUG=False in config
- [ ] Configure HTTPS/SSL certificates
- [ ] Change CORS allow_origins from "*" to specific domains
- [ ] Set up proper firewall rules
- [ ] Enable database backups
- [ ] Configure logging system
- [ ] Set up monitoring and alerting

---

**Document Version**: 1.0  
**Last Updated**: May 17, 2026  
**Server Framework**: FastAPI 0.104+  
**Database**: MySQL 8.0
