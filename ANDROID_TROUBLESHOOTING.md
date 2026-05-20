# Android App Connection Troubleshooting Guide

## Current Server Status

### Server Information
- **Framework**: FastAPI (Python)
- **Default Port**: 8000
- **API Base URL**: `http://<server-ip>:8000/api/v1`
- **Database**: MySQL on port 3306
- **CORS**: Fully enabled (allows all origins)

---

## Common Android Connection Problems & Solutions

### Problem 1: "Unable to Connect to Server" or "Connection Refused"

#### Checklist:
1. **Is the server running?**
   - Test endpoint: `curl http://127.0.0.1:8000/api/v1/health`
   - Should return: `{"status":"ok","app":"AI_ROI_CAMERA","version":"1.0.0"}`

2. **Are you using the correct server address?**
   - ❌ WRONG: `http://localhost:8000` (on Android device)
   - ❌ WRONG: `http://127.0.0.1:8000` (on Android device)
   - ✅ CORRECT: `http://<actual-server-ip>:8000` (e.g., `http://192.168.1.100:8000`)
   - ✅ CORRECT (Emulator): `http://10.0.2.2:8000` (to access host machine)

3. **Is the port correct?**
   - FastAPI is running on port 8000
   - Verify: `netstat -ano | findstr :8000` (Windows)
   - Or: `sudo netstat -tulpn | grep :8000` (Linux)

4. **Is firewall blocking the port?**
   - Windows Firewall: Allow port 8000 in Windows Defender Firewall
   - Linux: `sudo ufw allow 8000`
   - Check if port is listening:
     ```bash
     # Windows
     netstat -ano | findstr :8000
     
     # Linux
     lsof -i :8000
     ```

5. **Is Android device on same network?**
   - WiFi: Both server and device must be on same WiFi
   - Check device IP: Settings > WiFi > Network details
   - Check server IP: `ipconfig` (Windows) or `ifconfig` (Linux)
   - They should be on same subnet (e.g., 192.168.1.x)

---

### Problem 2: "Connection Timeout"

**Cause**: Network connectivity issue
**Solutions**:
1. Increase connection timeout in Android client (if configurable)
2. Check internet connectivity: Ping server from device
   ```bash
   # From Android device terminal/ADB
   ping 192.168.1.100
   ```
3. Check for network latency issues
4. Verify server isn't overloaded

---

### Problem 3: "401 Unauthorized" or "Invalid Credentials"

**Cause**: Login failed
**Solutions**:
1. Verify username and password are correct
2. Ensure user exists in database
3. Check password is not changed
4. Verify character encoding (special characters?)

**Debug**:
```bash
# Test login with curl
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

---

### Problem 4: "Bearer Token" or "Authentication" Errors

**Cause**: Incorrect token usage
**Solutions**:
1. Ensure Authorization header format is exactly:
   ```
   Authorization: Bearer <token>
   ```
   - NOT: `Bearer: <token>`
   - NOT: `Authorization: <token>`
   - NOT: `Authorization: Bearer<token>` (missing space)

2. Token is expired (24-hour limit)
   - Solution: Re-login to get fresh token

3. Token is invalid/corrupted
   - Verify token wasn't modified
   - Re-login to get new token

---

### Problem 5: "CORS Error" (Browser/WebView)

**Typical Error**:
```
Access to XMLHttpRequest at 'http://...' from origin 'null' has been blocked by CORS policy
```

**Status**: CORS is already enabled on server
- If still getting this error, it's likely not a server CORS issue
- Possible causes:
  1. Making request from file:// protocol (use server properly)
  2. WebView not allowing local network access (Android 12+)
  3. Incorrect request headers

**Android 12+ Fix** (if using WebView):
- Add to `AndroidManifest.xml`:
  ```xml
  <uses-permission android:name="android.permission.INTERNET" />
  <uses-permission android:name="android.permission.LOCAL_NETWORK_PERMISSION" />
  <uses-permission android:name="android.permission.CHANGE_NETWORK_STATE" />
  ```

---

### Problem 6: "SSL Certificate" Errors (HTTPS only)

**Current Status**: Server is running HTTP (not HTTPS)
- Mobile app should use `http://` NOT `https://`

**If implementing HTTPS in future**:
1. Use proper SSL certificate
2. Or use self-signed certificate and accept it in app
3. Don't trust all certificates in production

---

### Problem 7: "Response is Empty" or "JSON Parse Error"

**Causes**:
1. Server endpoint is returning HTML error page
2. Response is not valid JSON
3. Character encoding issue

**Debug**:
```bash
# Check raw response
curl -v http://localhost:8000/api/v1/health

# Should show response body starting with: {"status":"ok"...}
```

---

### Problem 8: "Stream URLs Not Working"

**Current Configuration**:
- MediaMTX Host: `localhost`
- Streams: RTSP (8554), HLS (8888), WebRTC (8889)

**For Android to access streams**:
1. Replace `localhost` with actual server IP
2. Use correct protocol:
   - RTSP: `rtsp://<server-ip>:8554/camera_01`
   - HLS: `http://<server-ip>:8888/camera_01`
   - WebRTC: `http://<server-ip>:8889/camera_01`

**Android Player Recommendation**:
- RTSP: Use VLC or ExoPlayer with RTSP extension
- HLS: Use ExoPlayer (built-in support)
- WebRTC: Use custom implementation or library

---

## Network Setup Verification Script

Run these tests to verify connectivity:

```bash
# Test 1: Check if server is running
curl http://127.0.0.1:8000/api/v1/health

# Test 2: Get your server IP
# Windows
ipconfig

# Test 3: Verify port is listening
# Windows
netstat -ano | findstr :8000
# Linux
lsof -i :8000

# Test 4: Test from another machine
# Replace 192.168.1.100 with your server IP
curl http://192.168.1.100:8000/api/v1/health

# Test 5: Test login endpoint
curl -X POST http://192.168.1.100:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

---

## Android App Implementation Checklist

### Network Configuration
- [ ] Use correct server IP (not localhost)
- [ ] Verify port is 8000
- [ ] Use `http://` (not `https://`)
- [ ] Full URL: `http://<server-ip>:8000/api/v1`

### Authentication Flow
- [ ] POST to `/auth/login` with username/password
- [ ] Extract `access_token` from response
- [ ] Store token securely (SharedPreferences/Keystore)
- [ ] Include in all requests: `Authorization: Bearer <token>`

### Request Headers (Required)
```
Content-Type: application/json
Authorization: Bearer <access_token>
Accept: application/json
```

### Handling Common Responses

**Success Response**:
```json
{
  "success": true,
  "data": {...}
}
```

**Error Response**:
```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

### Recommended Libraries (Android)
- **HTTP Client**: OkHttp, Retrofit, or Volley
- **WebSocket**: OkHttp with WebSocket support
- **JSON**: Gson or Moshi
- **Async**: Coroutines, RxJava, or LiveData

---

## Quick Diagnostic Commands

### Check Server Status
```bash
# Is server running?
curl http://192.168.1.100:8000/api/v1/health

# Check response time
curl -w "Time: %{time_total}s\n" http://192.168.1.100:8000/api/v1/health
```

### Verify Network Connectivity
```bash
# From Android device (via ADB)
adb shell ping 192.168.1.100

# Check DNS resolution
adb shell getprop net.hostname
```

### Test Full API Flow
```bash
# 1. Login
TOKEN=$(curl -s -X POST http://192.168.1.100:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.data.access_token')

# 2. Get zones with token
curl -H "Authorization: Bearer $TOKEN" \
  http://192.168.1.100:8000/api/v1/zones
```

---

## If Connection Still Fails

### Step-by-Step Debugging

1. **Test server directly** (on server machine)
   ```bash
   curl http://127.0.0.1:8000/api/v1/health
   ```
   If this fails → Server not running

2. **Test from same network** (another computer)
   ```bash
   curl http://<server-ip>:8000/api/v1/health
   ```
   If this fails → Network/firewall issue

3. **Test from Android emulator**
   ```bash
   # Using ADB
   adb shell curl http://10.0.2.2:8000/api/v1/health
   ```

4. **Test WebSocket connection** (Optional, for real-time)
   ```bash
   # Need wscat tool
   npm install -g wscat
   wscat -c "ws://192.168.1.100:8000/ws?token=<your-token>"
   ```

5. **Check logs** (if running with logging)
   - Look for connection attempts
   - Check for errors in FastAPI output

---

## Production Considerations

For production deployment:
1. Use domain name instead of IP
2. Implement HTTPS with proper certificates
3. Change default SECRET_KEY in security.py
4. Use environment variables for configuration
5. Add request rate limiting
6. Implement proper error logging
7. Set CORS to specific origins instead of "*"
8. Add request/response validation

---

## Environment Variables (For .env file)

```env
# Server
DEBUG=false
APP_NAME=AI_ROI_CAMERA
APP_VERSION=1.0.0

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_secure_password
DB_NAME=AI_ROI_CAMERA

# Security
SECRET_KEY=your-secure-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# MediaMTX
MEDIAMTX_HOST=localhost
RTSP_SOURCE_URL=rtsp://camera-ip:554/path
```

---

## Support Information

### Useful Endpoints for Testing
- Health Check: `GET /api/v1/health`
- Login: `POST /api/v1/auth/login`
- List Zones: `GET /api/v1/zones`
- List Alerts: `GET /api/v1/alerts`
- Stream Status: `GET /api/v1/stream/status`

### Documentation Files
- Full API Documentation: `API_ARCHITECTURE.md`
- Server Config: `app/core/config.py`
- Security Config: `app/core/security.py`

---

**Last Updated**: May 17, 2026  
**Database**: MySQL 8.0  
**Framework**: FastAPI 0.104+
