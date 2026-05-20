# 📱 AI_ROI_CAMERA - Android Integration Guide

**Version**: 1.0.0  
**Last Updated**: May 17, 2026  
**API Base URL**: `http://your-server-ip:8000/api/v1`

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [WebSocket Real-time Events](#websocket-real-time-events)
5. [Error Handling](#error-handling)
6. [Data Models](#data-models)
7. [Code Examples](#code-examples)
8. [Best Practices](#best-practices)

---

## 🚀 Getting Started

### Prerequisites
- Android API Level 24+
- Retrofit 2 for HTTP requests
- OkHttp for HTTP client
- Gson for JSON serialization
- Scarlet or OkHttp3 WebSocket for real-time events
- Firebase Cloud Messaging (FCM) for push notifications

### Setup Dependencies

```gradle
dependencies {
    // HTTP Client
    implementation 'com.squareup.retrofit2:retrofit:2.10.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.10.0'
    implementation 'com.squareup.okhttp3:okhttp:4.11.0'
    implementation 'com.squareup.okhttp3:logging-interceptor:4.11.0'
    
    // WebSocket
    implementation 'com.tinder.scarlet:scarlet:0.1.12'
    implementation 'com.tinder.scarlet:lifecycle-android:0.1.12'
    
    // JWT
    implementation 'io.jsonwebtoken:jjwt-api:0.12.3'
    
    // Firebase
    implementation 'com.google.firebase:firebase-messaging:23.2.1'
}
```

---

## 🔐 Authentication

### 1. Login to Get JWT Token

**Endpoint**: `POST /auth/login`

**Request**:
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

### 2. Token Storage & Expiry

- Store token in **SharedPreferences** (encrypted if using EncryptedSharedPreferences)
- Token expires in **24 hours**
- Implement automatic token refresh on login screen
- Handle 401 errors by redirecting to login

### 3. Register Firebase Token for Push Notifications

**Endpoint**: `POST /auth/register-fcm-token`  
**Auth**: ✅ Required (Bearer Token)

**Request**:
```json
{
  "fcm_token": "eJx7JbvDkYUow5GEkYU5w5GEmYUlw4mEmYURQxaXjIUlw5mEmYU1w5GEmYURQx6Xlp...",
  "device_id": "device_123_samsung_s22",
  "platform": "android"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "FCM token registered successfully"
}
```

### 4. Logout

**Endpoint**: `DELETE /auth/logout`  
**Auth**: ✅ Required

**Request**:
```json
{
  "device_id": "device_123_samsung_s22"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 📡 API Endpoints

### Health Check (No Auth Required)

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "ok"
}
```

---

### 🎥 Camera Streaming

#### Get Live Video Stream (Plain)

**Endpoint**: `GET /stream/video?camera_id=1`  
**Auth**: ✅ Required  
**Returns**: MJPEG stream (multipart/x-mixed-replace)

**Usage**:
```kotlin
// Using ExoPlayer or standard ImageView with background thread
val client = OkHttpClient()
val request = Request.Builder()
    .url("$BASE_URL/stream/video?camera_id=1")
    .header("Authorization", "Bearer $token")
    .build()

val call = client.newCall(request)
val response = call.execute()
val inputStream = response.body?.byteStream()
// Decode MJPEG frames...
```

#### Get AI-Processed Video Stream

**Endpoint**: `GET /stream/video/ai?camera_id=1`  
**Auth**: ✅ Required  
**Returns**: MJPEG stream with ROI + bounding boxes

#### Get Single Frame Snapshot

**Endpoint**: `GET /stream/snapshot?camera_id=1`  
**Auth**: ✅ Required  
**Returns**: JPEG image

**Response Headers**:
```
Content-Type: image/jpeg
Content-Length: 15234
```

#### Get Camera Status

**Endpoint**: `GET /stream/status?camera_id=1`  
**Auth**: ✅ Required

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "camera_id": 1,
    "camera_name": "Cánh cổng chính",
    "status": "online",
    "resolution": "1280x720",
    "fps": 15
  }
}
```

**Status Values**: `online`, `offline`

---

### 🚨 Alerts & Intrusion Detection

#### Create Alert

**Endpoint**: `POST /alerts`  
**Auth**: ✅ Required

**Request**:
```json
{
  "camera_id": 1,
  "zone_id": 1,
  "bounding_boxes": [
    {
      "x": 320,
      "y": 180,
      "w": 150,
      "h": 250,
      "label": "person",
      "confidence": 0.95
    }
  ],
  "confidence": 0.95,
  "thumbnail_path": "/alerts/thumb_20260517_143022.jpg",
  "video_clip_path": "/alerts/video_20260517_143022.mp4"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "alert_id": "12345",
    "camera_id": "1",
    "zone_id": "1",
    "zone_name": "Vùng cổng chính",
    "detected_at": "2026-05-17T14:30:22Z",
    "is_read": false,
    "confidence": 0.95,
    "object_count": 1,
    "thumbnail_url": "/api/v1/media/alerts/12345/thumbnail",
    "video_url": "/api/v1/media/alerts/12345/video"
  }
}
```

#### List Alerts (with Pagination & Filters)

**Endpoint**: `GET /alerts?page=1&limit=20&zone_id=1&is_read=false&from_date=2026-05-10T00:00:00Z&to_date=2026-05-17T23:59:59Z`  
**Auth**: ✅ Required

**Query Parameters**:
- `page` (int, default 1): Page number for pagination
- `limit` (int, default 20, max 100): Items per page
- `zone_id` (int, optional): Filter by zone
- `is_read` (boolean, optional): Filter by read status
- `from_date` (ISO 8601): Filter from date
- `to_date` (ISO 8601): Filter to date

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "alert_id": "12345",
        "camera_id": "1",
        "zone_id": "1",
        "zone_name": "Vùng cổng chính",
        "detected_at": "2026-05-17T14:30:22Z",
        "is_read": false,
        "confidence": 0.95,
        "object_count": 1,
        "thumbnail_url": "/api/v1/media/alerts/12345/thumbnail",
        "video_url": "/api/v1/media/alerts/12345/video"
      }
    ],
    "total": 156,
    "page": 1,
    "limit": 20,
    "total_pages": 8
  }
}
```

#### Get Alert Details

**Endpoint**: `GET /alerts/{alert_id}`  
**Auth**: ✅ Required

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "alert_id": "12345",
    "camera_id": "1",
    "zone_id": "1",
    "zone_name": "Vùng cổng chính",
    "detected_at": "2026-05-17T14:30:22Z",
    "is_read": false,
    "confidence": 0.95,
    "object_count": 1,
    "thumbnail_url": "/api/v1/media/alerts/12345/thumbnail",
    "video_url": "/api/v1/media/alerts/12345/video",
    "bounding_boxes": [
      {
        "x": 320,
        "y": 180,
        "w": 150,
        "h": 250,
        "label": "person",
        "confidence": 0.95
      }
    ]
  }
}
```

#### Mark Alert as Read

**Endpoint**: `PATCH /alerts/{alert_id}/read`  
**Auth**: ✅ Required

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Alert marked as read"
}
```

#### Mark All Alerts as Read

**Endpoint**: `PATCH /alerts/read-all`  
**Auth**: ✅ Required

**Response** (200 OK):
```json
{
  "success": true,
  "message": "All alerts marked as read"
}
```

#### Get Unread Alert Count

**Endpoint**: `GET /alerts/unread-count`  
**Auth**: ✅ Required

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "unread_count": 5
  }
}
```

---

### 📍 Zones Management

#### Create Detection Zone

**Endpoint**: `POST /zones`  
**Auth**: ✅ Required (Admin only)

**Request**:
```json
{
  "name": "Vùng cổng chính",
  "camera_id": "1",
  "zone_type": "polygon",
  "coordinates": [
    {"x": 10, "y": 10},
    {"x": 90, "y": 10},
    {"x": 90, "y": 80},
    {"x": 10, "y": 80}
  ],
  "is_active": true,
  "alert_cooldown_seconds": 30
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "zone_id": 1,
    "name": "Vùng cổng chính",
    "camera_id": "1",
    "zone_type": "polygon",
    "coordinates": [
      {"x": 10, "y": 10},
      {"x": 90, "y": 10},
      {"x": 90, "y": 80},
      {"x": 10, "y": 80}
    ],
    "is_active": true,
    "alert_cooldown_seconds": 30,
    "created_at": "2026-05-17T14:00:00Z",
    "updated_at": "2026-05-17T14:00:00Z"
  }
}
```

#### List All Zones

**Endpoint**: `GET /zones?camera_id=1&is_active=true`  
**Auth**: ✅ Required

**Query Parameters**:
- `camera_id` (int, optional): Filter by camera
- `is_active` (boolean, optional): Filter by active status

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "zones": [
      {
        "zone_id": 1,
        "name": "Vùng cổng chính",
        "camera_id": "1",
        "zone_type": "polygon",
        "coordinates": [...],
        "is_active": true,
        "alert_cooldown_seconds": 30,
        "created_at": "2026-05-17T14:00:00Z"
      }
    ]
  }
}
```

#### Get Zone Details

**Endpoint**: `GET /zones/{zone_id}`  
**Auth**: ✅ Required

#### Update Zone

**Endpoint**: `PUT /zones/{zone_id}`  
**Auth**: ✅ Required (Admin only)

**Request** (partial update):
```json
{
  "name": "Vùng cổng chính (cập nhật)",
  "coordinates": [
    {"x": 15, "y": 15},
    {"x": 85, "y": 15},
    {"x": 85, "y": 75},
    {"x": 15, "y": 75}
  ],
  "is_active": true,
  "alert_cooldown_seconds": 60
}
```

#### Delete Zone

**Endpoint**: `DELETE /zones/{zone_id}`  
**Auth**: ✅ Required (Admin only)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Zone deleted successfully"
}
```

#### Toggle Zone Active Status

**Endpoint**: `PATCH /zones/{zone_id}/toggle`  
**Auth**: ✅ Required (Admin only)

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "zone_id": 1,
    "is_active": false
  }
}
```

---

### 📊 Logs & Analytics

#### Get Intrusion Logs

**Endpoint**: `GET /logs?page=1&limit=20&zone_id=1&from_date=2026-05-10T00:00:00Z&to_date=2026-05-17T23:59:59Z`  
**Auth**: ✅ Required

**Query Parameters**:
- `page` (int, default 1): Page number
- `limit` (int, default 20): Items per page
- `zone_id` (int, optional): Filter by zone
- `from_date` (ISO 8601, optional): Filter from date
- `to_date` (ISO 8601, optional): Filter to date

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "log_id": 1,
        "alert_id": "12345",
        "camera_id": "1",
        "zone_id": "1",
        "zone_name": "Vùng cổng chính",
        "entered_at": "2026-05-17T14:30:22Z",
        "exited_at": "2026-05-17T14:32:15Z",
        "duration_seconds": 113,
        "thumbnail_url": "/api/v1/media/alerts/12345/thumbnail",
        "video_url": "/api/v1/media/alerts/12345/video"
      }
    ],
    "total": 45,
    "page": 1
  }
}
```

#### Get Analytics Dashboard

**Endpoint**: `GET /logs/stats?from_date=2026-05-10T00:00:00Z&to_date=2026-05-17T23:59:59Z`  
**Auth**: ✅ Required

**Query Parameters**:
- `from_date` (ISO 8601, optional): Filter from date
- `to_date` (ISO 8601, optional): Filter to date

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "total_intrusions": 156,
    "intrusions_today": 12,
    "intrusions_this_week": 67,
    "most_active_zone": "Vùng cổng chính",
    "peak_hour": 14,
    "by_zone": {
      "Vùng cổng chính": 45,
      "Vùng sân phía sau": 23,
      "Vùng tầng 2": 88
    }
  }
}
```

---

### 🎬 Media Download

#### Download Alert Thumbnail

**Endpoint**: `GET /media/alerts/{alert_id}/thumbnail`  
**Auth**: ✅ Required  
**Returns**: JPEG image

#### Download Alert Video

**Endpoint**: `GET /media/alerts/{alert_id}/video`  
**Auth**: ✅ Required  
**Returns**: MP4 video (supports range requests for seeking)

**Response Headers**:
```
Content-Type: video/mp4
Accept-Ranges: bytes
Content-Length: 1024000
```

#### Delete Alert Media

**Endpoint**: `DELETE /media/alerts/{alert_id}`  
**Auth**: ✅ Required (Admin only)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Media deleted successfully"
}
```

---

## 🔌 WebSocket Real-time Events

### Connection Setup

**URL**: `ws://your-server-ip:8000/ws?token=<JWT_TOKEN>`

**Connection Flow**:
1. Client establishes WebSocket connection with JWT token
2. Server validates token
3. Server sends connection confirmation
4. Client can subscribe/unsubscribe to events
5. Server pushes real-time events

### Client Messages

#### Ping/Pong (Keep-Alive)
```json
{
  "event": "ping"
}
```

**Server Response**:
```json
{
  "event": "pong",
  "data": {
    "timestamp": "2026-05-17T14:30:22Z"
  }
}
```

#### Subscribe to Camera Events
```json
{
  "event": "subscribe_camera",
  "data": {
    "camera_id": 1
  }
}
```

**Server Response**:
```json
{
  "event": "subscribed",
  "data": {
    "camera_id": 1,
    "status": "success"
  }
}
```

#### Unsubscribe from Camera Events
```json
{
  "event": "unsubscribe_camera",
  "data": {
    "camera_id": 1
  }
}
```

### Server-Pushed Events

#### Intrusion Detected
```json
{
  "event": "intrusion_detected",
  "data": {
    "alert_id": 12345,
    "camera_id": 1,
    "zone_id": 1,
    "zone_name": "Vùng cổng chính",
    "confidence": 0.95,
    "object_count": 1,
    "bounding_boxes": [
      {
        "x": 320,
        "y": 180,
        "w": 150,
        "h": 250,
        "label": "person",
        "confidence": 0.95
      }
    ],
    "timestamp": "2026-05-17T14:30:22Z"
  }
}
```

#### Intrusion Ended
```json
{
  "event": "intrusion_ended",
  "data": {
    "alert_id": 12345,
    "camera_id": 1,
    "zone_id": 1,
    "duration_seconds": 113,
    "timestamp": "2026-05-17T14:32:15Z"
  }
}
```

#### Camera Status Changed
```json
{
  "event": "camera_status_changed",
  "data": {
    "camera_id": 1,
    "camera_name": "Cánh cổng chính",
    "status": "online",
    "timestamp": "2026-05-17T14:30:22Z"
  }
}
```

---

## ❌ Error Handling

### HTTP Error Codes

| Status | Code | Message | Description |
|--------|------|---------|-------------|
| 400 | `INVALID_REQUEST` | Invalid request parameters | Validation error |
| 401 | `UNAUTHORIZED` | Invalid or missing token | Authentication failed |
| 401 | `TOKEN_EXPIRED` | Token has expired | Need re-login |
| 403 | `FORBIDDEN` | Admin access required | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found | Entity doesn't exist |
| 503 | `CAMERA_OFFLINE` | Camera is not responding | Camera connection failed |
| 500 | `INTERNAL_ERROR` | Server error | Unexpected error |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Token expired or invalid",
    "http_status": 401
  }
}
```

### Handling in Android

```kotlin
retrofit2.Call<AlertResponse> call = apiService.getAlerts(page, limit);
call.enqueue(new Callback<AlertResponse>() {
    @Override
    public void onResponse(Call<AlertResponse> call, Response<AlertResponse> response) {
        if (response.isSuccessful()) {
            AlertResponse data = response.body();
            // Handle success
        } else {
            // Parse error response
            try {
                String errorBody = response.errorBody().string();
                JsonObject errorJson = JsonParser.parseString(errorBody).getAsJsonObject();
                String errorCode = errorJson.getAsJsonObject("error").get("code").getAsString();
                
                if (errorCode.equals("TOKEN_EXPIRED")) {
                    // Redirect to login
                    redirectToLogin();
                } else if (errorCode.equals("UNAUTHORIZED")) {
                    // Show error message
                    showError("Unauthorized access");
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }
    
    @Override
    public void onFailure(Call<AlertResponse> call, Throwable t) {
        // Handle network error
        showError("Network error: " + t.getMessage());
    }
});
```

---

## 📦 Data Models

### User Model
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-05-17T10:00:00Z",
  "updated_at": "2026-05-17T14:00:00Z"
}
```

### Camera Model
```json
{
  "id": 1,
  "name": "Cánh cổng chính",
  "rtsp_url": "rtsp://192.168.0.3:554/onvif1",
  "location": "Sân trước",
  "resolution": "1280x720",
  "status": "online",
  "is_active": true,
  "last_seen_at": "2026-05-17T14:30:22Z",
  "created_at": "2026-05-17T10:00:00Z"
}
```

### Zone Model
```json
{
  "zone_id": 1,
  "name": "Vùng cổng chính",
  "camera_id": "1",
  "zone_type": "polygon",
  "coordinates": [
    {"x": 10, "y": 10},
    {"x": 90, "y": 10},
    {"x": 90, "y": 80},
    {"x": 10, "y": 80}
  ],
  "is_active": true,
  "alert_cooldown_seconds": 30,
  "created_at": "2026-05-17T14:00:00Z",
  "updated_at": "2026-05-17T14:00:00Z"
}
```

### Alert Model
```json
{
  "alert_id": "12345",
  "camera_id": "1",
  "zone_id": "1",
  "zone_name": "Vùng cổng chính",
  "detected_at": "2026-05-17T14:30:22Z",
  "is_read": false,
  "confidence": 0.95,
  "object_count": 1,
  "thumbnail_url": "/api/v1/media/alerts/12345/thumbnail",
  "video_url": "/api/v1/media/alerts/12345/video",
  "bounding_boxes": [
    {
      "x": 320,
      "y": 180,
      "w": 150,
      "h": 250,
      "label": "person",
      "confidence": 0.95
    }
  ]
}
```

### BoundingBox Model
```json
{
  "x": 320,
  "y": 180,
  "w": 150,
  "h": 250,
  "label": "person",
  "confidence": 0.95
}
```

**Coordinate System**:
- `x`, `y`: Top-left corner of bounding box (in pixels, 0-1280 for x, 0-720 for y)
- `w`, `h`: Width and height of bounding box (in pixels)
- `label`: Object class name (e.g., "person", "backpack")
- `confidence`: Detection confidence (0-1, higher is better)

---

## 📝 Code Examples

### 1. Retrofit Setup with Interceptor

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor

class ApiClient {
    companion object {
        private const val BASE_URL = "http://192.168.1.100:8000/api/v1/"
        private var retrofit: Retrofit? = null
        private var token: String? = null

        fun setToken(authToken: String) {
            token = authToken
            retrofit = null // Reset to recreate with new token
        }

        fun getClient(): Retrofit {
            if (retrofit == null) {
                val logging = HttpLoggingInterceptor()
                logging.setLevel(HttpLoggingInterceptor.Level.BODY)

                val httpClient = OkHttpClient.Builder()
                    .addInterceptor(logging)
                    .addInterceptor { chain ->
                        val original = chain.request()
                        val requestBuilder = original.newBuilder()
                        
                        // Add Authorization header if token exists
                        if (token != null) {
                            requestBuilder.header("Authorization", "Bearer $token")
                        }
                        
                        val request = requestBuilder.build()
                        chain.proceed(request)
                    }
                    .build()

                retrofit = Retrofit.Builder()
                    .baseUrl(BASE_URL)
                    .addConverterFactory(GsonConverterFactory.create())
                    .client(httpClient)
                    .build()
            }
            return retrofit!!
        }

        fun getApiService(): ApiService {
            return getClient().create(ApiService::class.java)
        }
    }
}
```

### 2. API Service Interface

```kotlin
import retrofit2.Call
import retrofit2.http.*

interface ApiService {
    // Auth
    @POST("auth/login")
    fun login(@Body request: LoginRequest): Call<LoginResponse>

    @POST("auth/register-fcm-token")
    fun registerFcmToken(@Body request: FCMTokenRequest): Call<SuccessResponse>

    @DELETE("auth/logout")
    fun logout(@Body request: LogoutRequest): Call<SuccessResponse>

    // Stream
    @GET("stream/video")
    fun getVideoStream(
        @Query("camera_id") cameraId: Int = 1
    ): Call<ResponseBody>

    @GET("stream/video/ai")
    fun getAIVideoStream(
        @Query("camera_id") cameraId: Int = 1
    ): Call<ResponseBody>

    @GET("stream/snapshot")
    fun getSnapshot(
        @Query("camera_id") cameraId: Int = 1
    ): Call<ResponseBody>

    @GET("stream/status")
    fun getStreamStatus(
        @Query("camera_id") cameraId: Int = 1
    ): Call<ApiResponse<StreamStatusData>>

    // Alerts
    @POST("alerts")
    fun createAlert(@Body request: AlertCreateRequest): Call<ApiResponse<AlertData>>

    @GET("alerts")
    fun getAlerts(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
        @Query("zone_id") zoneId: Int? = null,
        @Query("is_read") isRead: Boolean? = null
    ): Call<ApiResponse<AlertListData>>

    @GET("alerts/{alert_id}")
    fun getAlertDetails(@Path("alert_id") alertId: String): Call<ApiResponse<AlertData>>

    @PATCH("alerts/{alert_id}/read")
    fun markAlertAsRead(@Path("alert_id") alertId: String): Call<SuccessResponse>

    @PATCH("alerts/read-all")
    fun markAllAlertsAsRead(): Call<SuccessResponse>

    @GET("alerts/unread-count")
    fun getUnreadCount(): Call<ApiResponse<UnreadCountData>>

    // Zones
    @GET("zones")
    fun getZones(
        @Query("camera_id") cameraId: Int? = null,
        @Query("is_active") isActive: Boolean? = null
    ): Call<ApiResponse<ZoneListData>>

    @GET("zones/{zone_id}")
    fun getZoneDetails(@Path("zone_id") zoneId: Int): Call<ApiResponse<ZoneData>>

    @POST("zones")
    fun createZone(@Body request: ZoneCreateRequest): Call<ApiResponse<ZoneData>>

    @PUT("zones/{zone_id}")
    fun updateZone(
        @Path("zone_id") zoneId: Int,
        @Body request: ZoneUpdateRequest
    ): Call<ApiResponse<ZoneData>>

    @DELETE("zones/{zone_id}")
    fun deleteZone(@Path("zone_id") zoneId: Int): Call<SuccessResponse>

    @PATCH("zones/{zone_id}/toggle")
    fun toggleZone(@Path("zone_id") zoneId: Int): Call<ApiResponse<ZoneToggleData>>

    // Logs
    @GET("logs")
    fun getLogs(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
        @Query("zone_id") zoneId: Int? = null
    ): Call<ApiResponse<LogListData>>

    @GET("logs/stats")
    fun getStats(): Call<ApiResponse<StatsData>>

    // Media
    @GET("media/alerts/{alert_id}/thumbnail")
    fun getThumbnail(@Path("alert_id") alertId: String): Call<ResponseBody>

    @GET("media/alerts/{alert_id}/video")
    fun getVideo(@Path("alert_id") alertId: String): Call<ResponseBody>

    @DELETE("media/alerts/{alert_id}")
    fun deleteMedia(@Path("alert_id") alertId: String): Call<SuccessResponse>
}
```

### 3. WebSocket Setup

```kotlin
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import com.google.gson.JsonObject
import com.google.gson.JsonParser

class WebSocketManager(private val token: String) : WebSocketListener() {
    companion object {
        private const val WS_URL = "ws://192.168.1.100:8000/ws"
    }

    private lateinit var webSocket: WebSocket
    private var listener: WebSocketEventListener? = null

    interface WebSocketEventListener {
        fun onIntrusionDetected(alert: AlertData)
        fun onIntrusionEnded(endData: IntrustionEndData)
        fun onCameraStatusChanged(statusData: CameraStatusData)
        fun onError(error: String)
        fun onConnected()
    }

    fun connect(listener: WebSocketEventListener) {
        this.listener = listener
        
        val request = Request.Builder()
            .url("$WS_URL?token=$token")
            .build()

        val client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .build()

        webSocket = client.newWebSocket(request, this)
    }

    override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
        listener?.onConnected()
        
        // Send ping to keep connection alive
        sendPing()
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        try {
            val json = JsonParser.parseString(text).asJsonObject
            val event = json.get("event").asString
            val data = json.getAsJsonObject("data")

            when (event) {
                "intrusion_detected" -> {
                    val alert = parseAlertData(data)
                    listener?.onIntrusionDetected(alert)
                }
                "intrusion_ended" -> {
                    val endData = parseIntrustionEndData(data)
                    listener?.onIntrusionEnded(endData)
                }
                "camera_status_changed" -> {
                    val statusData = parseCameraStatusData(data)
                    listener?.onCameraStatusChanged(statusData)
                }
                "pong" -> {
                    // Keep-alive pong
                    schedulePing()
                }
            }
        } catch (e: Exception) {
            listener?.onError("Failed to parse WebSocket message: ${e.message}")
        }
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
        listener?.onError("WebSocket failure: ${t.message}")
    }

    override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
        listener?.onError("WebSocket closed: $reason")
    }

    fun sendPing() {
        val pingJson = JsonObject().apply {
            addProperty("event", "ping")
        }
        webSocket.send(pingJson.toString())
    }

    private fun schedulePing() {
        Handler(Looper.getMainLooper()).postDelayed({
            sendPing()
        }, 30000) // Ping every 30 seconds
    }

    fun subscribeToCamera(cameraId: Int) {
        val subscribeJson = JsonObject().apply {
            addProperty("event", "subscribe_camera")
            add("data", JsonObject().apply {
                addProperty("camera_id", cameraId)
            })
        }
        webSocket.send(subscribeJson.toString())
    }

    fun disconnect() {
        webSocket.close(1000, "User initiated disconnect")
    }

    // Helper parsing functions...
}
```

### 4. Login Activity Example

```kotlin
class LoginActivity : AppCompatActivity() {
    private lateinit var apiService: ApiService
    private lateinit var usernameInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var loginButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        apiService = ApiClient.getApiService()
        usernameInput = findViewById(R.id.username_input)
        passwordInput = findViewById(R.id.password_input)
        loginButton = findViewById(R.id.login_button)

        loginButton.setOnClickListener {
            performLogin()
        }
    }

    private fun performLogin() {
        val username = usernameInput.text.toString().trim()
        val password = passwordInput.text.toString()

        if (username.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Please enter username and password", Toast.LENGTH_SHORT).show()
            return
        }

        val loginRequest = LoginRequest(username, password)
        apiService.login(loginRequest).enqueue(object : Callback<LoginResponse> {
            override fun onResponse(call: Call<LoginResponse>, response: Response<LoginResponse>) {
                if (response.isSuccessful) {
                    val loginResponse = response.body()
                    val token = loginResponse?.data?.access_token

                    // Save token securely
                    saveToken(token!!)

                    // Register FCM token
                    registerFcmToken(token)

                    // Navigate to main activity
                    startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                    finish()
                } else {
                    Toast.makeText(
                        this@LoginActivity,
                        "Login failed: Invalid credentials",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }

            override fun onFailure(call: Call<LoginResponse>, t: Throwable) {
                Toast.makeText(
                    this@LoginActivity,
                    "Network error: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }

    private fun saveToken(token: String) {
        val sharedPref = EncryptedSharedPreferences.create(
            this,
            "auth_prefs",
            MasterKey.Builder(this).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
        sharedPref.edit().putString("auth_token", token).apply()

        // Set token in API client
        ApiClient.setToken(token)
    }

    private fun registerFcmToken(authToken: String) {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val fcmToken = task.result
                val deviceId = Settings.Secure.getString(
                    contentResolver,
                    Settings.Secure.ANDROID_ID
                )

                val fcmRequest = FCMTokenRequest(
                    fcm_token = fcmToken,
                    device_id = deviceId,
                    platform = "android"
                )

                apiService.registerFcmToken(fcmRequest).enqueue(object : Callback<SuccessResponse> {
                    override fun onResponse(
                        call: Call<SuccessResponse>,
                        response: Response<SuccessResponse>
                    ) {
                        Log.d("FCM", "Token registered successfully")
                    }

                    override fun onFailure(call: Call<SuccessResponse>, t: Throwable) {
                        Log.e("FCM", "Failed to register token: ${t.message}")
                    }
                })
            }
        }
    }
}
```

### 5. Alerts List Fragment

```kotlin
class AlertsFragment : Fragment() {
    private lateinit var apiService: ApiService
    private lateinit var alertAdapter: AlertAdapter
    private var currentPage = 1
    private var isLoading = false

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_alerts, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        apiService = ApiClient.getApiService()
        alertAdapter = AlertAdapter()

        val recyclerView: RecyclerView = view.findViewById(R.id.alerts_recycler)
        recyclerView.apply {
            adapter = alertAdapter
            layoutManager = LinearLayoutManager(requireContext())
            addOnScrollListener(object : RecyclerView.OnScrollListener() {
                override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                    val layoutManager = recyclerView.layoutManager as LinearLayoutManager
                    val totalItemCount = layoutManager.itemCount
                    val lastVisibleItem = layoutManager.findLastVisibleItemPosition()

                    if (lastVisibleItem + 5 >= totalItemCount && !isLoading) {
                        currentPage++
                        loadAlerts()
                    }
                }
            })
        }

        loadAlerts()
    }

    private fun loadAlerts() {
        isLoading = true
        apiService.getAlerts(page = currentPage, limit = 20).enqueue(object : Callback<ApiResponse<AlertListData>> {
            override fun onResponse(
                call: Call<ApiResponse<AlertListData>>,
                response: Response<ApiResponse<AlertListData>>
            ) {
                isLoading = false
                if (response.isSuccessful) {
                    val alerts = response.body()?.data?.alerts ?: emptyList()
                    alertAdapter.addItems(alerts)
                }
            }

            override fun onFailure(call: Call<ApiResponse<AlertListData>>, t: Throwable) {
                isLoading = false
                Toast.makeText(
                    requireContext(),
                    "Failed to load alerts: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }
}
```

---

## ✅ Best Practices

### 1. Token Management
- Store token in **EncryptedSharedPreferences**
- Check token expiry before making requests
- Implement automatic re-login on 401 errors
- Clear token on logout

### 2. Error Handling
- Always handle 401/403 errors with user feedback
- Implement exponential backoff for retries
- Log all API errors for debugging
- Show user-friendly error messages

### 3. Performance
- Use pagination for list endpoints (default limit 20)
- Cache responses where appropriate
- Implement request throttling for WebSocket
- Use Glide/Picasso for image caching

### 4. Security
- Never log sensitive data (tokens, passwords)
- Use HTTPS in production
- Validate all user inputs
- Implement certificate pinning

### 5. Connectivity
- Check network availability before requests
- Implement offline mode for critical features
- Use WebSocket for real-time updates
- Handle WebSocket reconnection gracefully

### 6. UI/UX
- Show loading indicators during network requests
- Implement pull-to-refresh for lists
- Display network error messages prominently
- Keep WebSocket connection alive with ping/pong

### 7. Testing
- Mock API responses using Mockito
- Test error scenarios thoroughly
- Verify token refresh logic
- Test WebSocket message handling

---

## 📞 Support & Troubleshooting

### Common Issues

**Q: 401 Unauthorized Error**  
A: Token has expired or is invalid. Redirect user to login screen and re-authenticate.

**Q: WebSocket Connection Failed**  
A: Check internet connectivity, verify token validity, ensure server is running.

**Q: Images Not Loading**  
A: Verify thumbnail URLs are accessible, check network permissions in AndroidManifest.xml.

**Q: Slow Streaming**  
A: Check server RTSP source, reduce stream resolution, verify network bandwidth.

---

**Last Updated**: May 17, 2026  
**API Version**: v1.0.0  
**Maintained by**: AI_ROI_CAMERA Development Team
