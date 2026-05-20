# Android App - Quick Reference Guide

## Server Connection Setup

### Step 1: Determine Server IP Address

**On Windows (Server Machine)**:
```bash
ipconfig
```
Look for IPv4 Address (e.g., 192.168.1.100)

**On Linux (Server Machine)**:
```bash
hostname -I
```

### Step 2: Configure Base URL in Android App

```kotlin
// NOT: http://localhost:8000/api/v1
// NOT: http://127.0.0.1:8000/api/v1
// CORRECT:
const val BASE_URL = "http://192.168.1.100:8000/api/v1"

// For Android Emulator only:
const val BASE_URL = "http://10.0.2.2:8000/api/v1"
```

### Step 3: Test Connection Before Login

```kotlin
// Test health endpoint (no authentication needed)
GET http://192.168.1.100:8000/api/v1/health

// Expected response:
{
  "status": "ok",
  "app": "AI_ROI_CAMERA",
  "version": "1.0.0"
}
```

---

## Authentication Flow

### 1. Login

```kotlin
// Request
POST /auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}

// Response
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 86400  // seconds (24 hours)
  }
}
```

### 2. Store Token Securely

```kotlin
// Use Android Keystore or Encrypted SharedPreferences
val sharedPref = context.getSharedPreferences("auth", Context.MODE_PRIVATE)
sharedPref.edit().putString("access_token", token).apply()
```

### 3. Use Token in Requests

```kotlin
// ALL requests (except health check) need this header:
Authorization: Bearer <access_token>

// Example with Retrofit:
@Headers("Authorization: Bearer ${getToken()}")
@GET("/zones")
fun getZones(): Call<ZonesResponse>
```

---

## Most Common Endpoints for Android

### 1. Health Check (No Auth)
```
GET /health
Response: {"status": "ok", "app": "AI_ROI_CAMERA", "version": "1.0.0"}
```

### 2. Login
```
POST /auth/login
Body: {"username": "...", "password": "..."}
Response: {"success": true, "data": {"access_token": "...", "token_type": "Bearer", "expires_in": 86400}}
```

### 3. Get Zones
```
GET /zones
Headers: Authorization: Bearer <token>
Response: {"success": true, "data": [{zone_id, name, camera_id, ...}]}
```

### 4. Get Alerts
```
GET /alerts?page=1&limit=20
Headers: Authorization: Bearer <token>
Response: {"success": true, "data": {"items": [...], "pagination": {...}}}
```

### 5. Get Stream URLs
```
GET /stream/urls
Headers: Authorization: Bearer <token>
Response: {"success": true, "data": {"camera_id": "...", "rtsp": "...", "hls": "...", "webrtc": "..."}}
```

### 6. WebSocket (Real-time Alerts)
```
ws://<server-ip>:8000/ws?token=<access_token>

Send: {"event": "ping"}
Receive: {"event": "pong", "data": {"timestamp": "..."}}
```

---

## Connection Troubleshooting Checklist

### Before Implementing:
- [ ] Server is running on port 8000
- [ ] You know the server's IP address (not localhost)
- [ ] Android device is on same WiFi network as server
- [ ] Port 8000 is not blocked by firewall

### Test Commands:
```bash
# On your server machine
curl http://127.0.0.1:8000/api/v1/health

# From another computer on same network
curl http://192.168.1.100:8000/api/v1/health  # Replace with your IP

# From Android device (via ADB)
adb shell curl http://10.0.2.2:8000/api/v1/health  # For emulator
# Or: adb shell curl http://192.168.1.100:8000/api/v1/health  # For real device
```

### If Connection Fails:
1. **Check server is running**
   - Should see FastAPI startup message in terminal
   - Command: `python -m uvicorn app.main:app --reload`

2. **Check port is listening**
   - Windows: `netstat -ano | findstr :8000`
   - Linux: `lsof -i :8000`

3. **Check firewall**
   - Windows: Allow port 8000 in Windows Defender Firewall
   - Linux: `sudo ufw allow 8000`

4. **Check IP address**
   - Server: `ipconfig` (Windows) or `hostname -I` (Linux)
   - Device: Should be on same subnet (192.168.1.x)

---

## Request/Response Examples

### Example 1: Login
```bash
curl -X POST http://192.168.1.100:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

Response:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzA0NzQyNDAwfQ.xxx",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

### Example 2: Get Zones
```bash
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
curl -H "Authorization: Bearer $TOKEN" \
  http://192.168.1.100:8000/api/v1/zones
```

Response:
```json
{
  "success": true,
  "data": [
    {
      "zone_id": "1",
      "name": "Front Door",
      "camera_id": "cam_01",
      "zone_type": "entry",
      "coordinates": [{"x": 100, "y": 100}, {"x": 200, "y": 200}],
      "is_active": true,
      "alert_cooldown_seconds": 30,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

### Example 3: Get Alerts
```bash
TOKEN="..."
curl "http://192.168.1.100:8000/api/v1/alerts?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "alert_id": "1",
        "zone_id": "1",
        "camera_id": "cam_01",
        "detected_at": "2024-01-15T14:30:00",
        "is_read": false,
        "thumbnail_url": "/api/v1/media/alerts/1/thumbnail",
        "video_url": "/api/v1/media/alerts/1/video",
        "object_count": 1,
        "confidence": 0.95
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 42,
      "total_pages": 5
    }
  }
}
```

---

## Android Code Snippets

### Using Retrofit
```kotlin
interface ApiService {
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>
    
    @GET("zones")
    suspend fun getZones(): Response<ZonesResponse>
    
    @GET("alerts")
    suspend fun getAlerts(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20
    ): Response<AlertsResponse>
}

// Create instance with correct base URL
val retrofit = Retrofit.Builder()
    .baseUrl("http://192.168.1.100:8000/api/v1/")  // Don't forget trailing slash
    .addConverterFactory(GsonConverterFactory.create())
    .build()

val apiService = retrofit.create(ApiService::class.java)
```

### Adding Bearer Token
```kotlin
class AuthInterceptor(private val token: String) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val requestBuilder = original.newBuilder()
            .addHeader("Authorization", "Bearer $token")
        return chain.proceed(requestBuilder.build())
    }
}

// Use in OkHttpClient
val client = OkHttpClient.Builder()
    .addInterceptor(AuthInterceptor(token))
    .build()
```

### WebSocket Connection
```kotlin
val webSocket = OkHttpClient()
    .newWebSocket(
        Request.Builder()
            .url("ws://192.168.1.100:8000/ws?token=$token")
            .build(),
        object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("WS", "Connected")
            }
            
            override fun onMessage(webSocket: WebSocket, text: String) {
                val json = JSONObject(text)
                val event = json.getString("event")
                when(event) {
                    "alert_detected" -> handleAlert(json)
                    "connected" -> Log.d("WS", "Ready")
                }
            }
        }
    )
```

---

## Important Notes

### Token Expiration
- Tokens expire after 24 hours
- Implement refresh mechanism or re-login when needed
- Check response status 401 → Need to re-login

### URL Format
- Always use: `http://` (NOT `https://`)
- Always include trailing slash in base URL: `http://ip:8000/api/v1/`
- Full URL examples:
  - Health: `http://192.168.1.100:8000/api/v1/health`
  - Login: `http://192.168.1.100:8000/api/v1/auth/login`
  - Zones: `http://192.168.1.100:8000/api/v1/zones`

### Content-Type
- Always send: `Content-Type: application/json`
- Always send: `Accept: application/json`

### Emulator vs Real Device
- **Emulator**: Use `http://10.0.2.2:8000` to access host machine
- **Real Device**: Use actual server IP `http://192.168.1.100:8000`

---

## Debugging Tips

### Enable Logging
```kotlin
val logging = HttpLoggingInterceptor()
logging.level = HttpLoggingInterceptor.Level.BODY

val client = OkHttpClient.Builder()
    .addInterceptor(logging)
    .addInterceptor(AuthInterceptor(token))
    .build()
```

### Check Request/Response
```bash
# Use curl to test before coding
curl -v http://192.168.1.100:8000/api/v1/health

# Use jsoncrack.com to visualize response format
# Use Postman to test endpoints
```

### Common Errors
- **Connection refused**: Server not running or wrong port
- **401 Unauthorized**: Wrong token or token expired
- **404 Not Found**: Wrong endpoint path
- **500 Internal Server Error**: Check server logs

---

## Files Reference

- **Full API Docs**: `API_ARCHITECTURE.md`
- **Connection Help**: `ANDROID_TROUBLESHOOTING.md`
- **Server Config**: `app/core/config.py`
- **Security**: `app/core/security.py`

---

**Last Updated**: May 17, 2026
