# 🚀 Android Implementation Plan - Chi Tiết

**Hướng dẫn từng bước sửa dự án Flutter App**

---

## ⚡ Quick Start

**Thứ tự ưu tiên:**
1. Stream API update (CRITICAL)
2. Error handling (HIGH)
3. Add missing API methods (MEDIUM)
4. Data models (MEDIUM)
5. Package name fix (MEDIUM)

---

## 🔴 PHASE 1: CRITICAL FIXES

### 1.1 Update Stream Video Handling (MJPEG → RTSP/HLS)

**File**: `lib/config/app_config.dart`

```dart
// OLD (MJPEG)
const String videoStream = "$apiBaseUrl/stream/video";

// NEW (RTSP/HLS)
// We'll fetch URLs from endpoint instead of hardcoding
```

**File**: `lib/services/api_service.dart` (Add new method)

```dart
// Add this new method to fetch stream URLs
Future<Map<String, dynamic>> getStreamUrls() async {
  final response = await client.get(
    Uri.parse("$apiBaseUrl/stream/urls"),
    headers: {"Authorization": "Bearer $token"}
  );
  
  if (response.statusCode == 200) {
    final json = jsonDecode(response.body);
    if (json["success"] == true) {
      return json["data"];  // Returns {rtsp, hls, webrtc, camera_id}
    }
  }
  
  throw Exception("Failed to fetch stream URLs");
}
```

**File**: `lib/screens/stream_screen.dart` (Update existing)

```dart
import 'package:video_player/video_player.dart';

class StreamScreen extends StatefulWidget {
  @override
  State<StreamScreen> createState() => _StreamScreenState();
}

class _StreamScreenState extends State<StreamScreen> {
  late VideoPlayerController _controller;
  late Future<void> _initializeVideoPlayerFuture;
  String? _currentStreamUrl;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _initializeStream();
  }

  Future<void> _initializeStream() async {
    try {
      setState(() => _isLoading = true);
      
      // Fetch stream URLs from backend
      final urls = await ApiService.instance.getStreamUrls();
      
      // Use HLS URL (best compatibility for mobile)
      // Alternative: use RTSP for lower latency
      // _currentStreamUrl = urls['rtsp'];  // For RTSP
      _currentStreamUrl = urls['hls'];  // For HLS (recommended)
      
      print("Stream URL: $_currentStreamUrl");
      
      // Initialize video player
      _controller = VideoPlayerController.network(_currentStreamUrl!);
      
      _initializeVideoPlayerFuture = _controller.initialize().then((_) {
        // Play video when ready
        _controller.play();
        setState(() => _isLoading = false);
      }).catchError((error) {
        print("Error initializing video player: $error");
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Failed to load stream: $error"))
        );
        setState(() => _isLoading = false);
      });
      
    } catch (e) {
      print("Error fetching stream URLs: $e");
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error: $e"))
      );
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Camera Stream")),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : FutureBuilder<void>(
              future: _initializeVideoPlayerFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.done) {
                  return Column(
                    children: [
                      Expanded(
                        child: AspectRatio(
                          aspectRatio: _controller.value.aspectRatio,
                          child: VideoPlayer(_controller),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.all(8.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children: [
                            FloatingActionButton(
                              onPressed: () {
                                setState(() {
                                  if (_controller.value.isPlaying) {
                                    _controller.pause();
                                  } else {
                                    _controller.play();
                                  }
                                });
                              },
                              child: Icon(
                                _controller.value.isPlaying
                                    ? Icons.pause
                                    : Icons.play_arrow
                              ),
                            ),
                            FloatingActionButton(
                              onPressed: _initializeStream,
                              child: const Icon(Icons.refresh),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                } else if (snapshot.hasError) {
                  return Center(
                    child: Text("Error loading video: ${snapshot.error}")
                  );
                }
                return const Center(child: CircularProgressIndicator());
              },
            ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
```

**Update pubspec.yaml:**

```yaml
dependencies:
  video_player: ^2.4.0
  # Optional: for RTSP support
  flutter_vlc_player: ^7.3.0  # Only if RTSP needed
```

**Or just HLS (recommended):**
```yaml
dependencies:
  video_player: ^2.4.0  # Already supports HLS natively
```

**Add to AndroidManifest.xml** (if not already done):
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.LOCAL_NETWORK_PERMISSION" />
```

---

### 1.2 Fix Error Handling

**File**: `lib/services/api_service.dart`

```dart
import 'package:dio/dio.dart';

class ApiService {
  static final instance = ApiService._();
  
  ApiService._() {
    _initDio();
  }
  
  late Dio client;
  String token = "";
  
  void _initDio() {
    client = Dio(BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));
    
    // Add logging interceptor for debugging
    client.interceptors.add(LoggingInterceptor());
  }
  
  // NEW: Handle API errors with new format
  Map<String, dynamic> _handleResponse(Response response) {
    if (response.statusCode == 200 || response.statusCode == 201) {
      try {
        final json = jsonDecode(response.body);
        if (json["success"] == true) {
          return json["data"] ?? {};
        } else if (json["success"] == false) {
          // Handle new error format
          final error = json["error"] ?? {};
          throw ApiException(
            code: error["code"] ?? "UNKNOWN_ERROR",
            message: error["message"] ?? "Unknown error",
            httpStatus: error["http_status"] ?? response.statusCode,
          );
        }
      } catch (e) {
        throw ApiException(
          code: "PARSE_ERROR",
          message: "Failed to parse response: $e",
          httpStatus: response.statusCode,
        );
      }
    }
    
    // Handle error responses
    if (response.statusCode == 401) {
      throw ApiException(
        code: "UNAUTHORIZED",
        message: "Authentication failed. Please login again.",
        httpStatus: 401,
      );
    } else if (response.statusCode == 403) {
      throw ApiException(
        code: "FORBIDDEN",
        message: "You don't have permission to access this resource.",
        httpStatus: 403,
      );
    } else if (response.statusCode == 404) {
      throw ApiException(
        code: "NOT_FOUND",
        message: "Resource not found.",
        httpStatus: 404,
      );
    } else if (response.statusCode == 500) {
      throw ApiException(
        code: "SERVER_ERROR",
        message: "Server error. Please try again later.",
        httpStatus: 500,
      );
    } else {
      throw ApiException(
        code: "UNKNOWN_ERROR",
        message: "An unexpected error occurred.",
        httpStatus: response.statusCode ?? 0,
      );
    }
  }
  
  // Existing methods remain the same, but use _handleResponse
  
  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final response = await client.post(
        "/auth/login",
        data: {"username": username, "password": password},
        options: Options(
          headers: {"Content-Type": "application/json"}
        ),
      );
      
      final json = jsonDecode(response.body);
      if (json["success"] == true) {
        token = json["data"]["access_token"];
        return json["data"];
      } else if (json["success"] == false) {
        throw ApiException(
          code: json["error"]["code"],
          message: json["error"]["message"],
          httpStatus: response.statusCode ?? 401,
        );
      }
    } catch (e) {
      rethrow;
    }
  }
}

// NEW: Custom exception class for API errors
class ApiException implements Exception {
  final String code;
  final String message;
  final int httpStatus;
  
  ApiException({
    required this.code,
    required this.message,
    required this.httpStatus,
  });
  
  @override
  String toString() => "ApiException($code): $message [HTTP $httpStatus]";
}

// NEW: Error handler helper
class ApiErrorHandler {
  static String getErrorMessage(ApiException exception) {
    switch (exception.code) {
      case "UNAUTHORIZED":
        return "Please login again";
      case "FORBIDDEN":
        return "You don't have permission";
      case "NOT_FOUND":
        return "Resource not found";
      case "ZONE_NOT_FOUND":
        return "Zone not found";
      case "ALERT_NOT_FOUND":
        return "Alert not found";
      case "INVALID_REQUEST":
        return "Invalid request";
      case "SERVER_ERROR":
        return "Server error. Try again later";
      default:
        return exception.message;
    }
  }
  
  static void handleError(BuildContext context, ApiException exception) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(getErrorMessage(exception)),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 3),
      ),
    );
  }
}
```

**File**: `lib/screens/login_screen.dart` (Update to use new error handling)

```dart
Future<void> _handleLogin() async {
  try {
    // ... login code ...
    await ApiService.instance.login(username, password);
    // ... success handling ...
  } on ApiException catch (e) {
    ApiErrorHandler.handleError(context, e);
  } catch (e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text("Error: $e"))
    );
  }
}
```

---

## 🟠 HIGH PRIORITY - Add Missing API Methods

### 2.1 Add Missing CRUD Operations

**File**: `lib/services/api_service.dart` (Add these methods)

```dart
// ============== ZONE MANAGEMENT ==============

// GET /zones/{id} - Get zone details
Future<Map<String, dynamic>> getZoneDetails(int zoneId) async {
  try {
    final response = await client.get(
      Uri.parse("$apiBaseUrl/zones/$zoneId"),
      headers: {"Authorization": "Bearer $token"},
    );
    
    final json = jsonDecode(response.body);
    if (json["success"] == true) {
      return json["data"];
    } else {
      throw ApiException(
        code: json["error"]["code"],
        message: json["error"]["message"],
        httpStatus: response.statusCode ?? 404,
      );
    }
  } catch (e) {
    rethrow;
  }
}

// PUT /zones/{id} - Update zone
Future<Map<String, dynamic>> updateZone(
  int zoneId, {
  required String name,
  required List<Map<String, double>> coordinates,
  required bool isActive,
  required int alertCooldownSeconds,
}) async {
  try {
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
        "alert_cooldown_seconds": alertCooldownSeconds,
      }),
    );
    
    final json = jsonDecode(response.body);
    if (json["success"] == true) {
      return json["data"];
    } else {
      throw ApiException(
        code: json["error"]["code"],
        message: json["error"]["message"],
        httpStatus: response.statusCode ?? 400,
      );
    }
  } catch (e) {
    rethrow;
  }
}

// DELETE /media/alerts/{id} - Delete alert media
Future<void> deleteAlertMedia(int alertId) async {
  try {
    final response = await client.delete(
      Uri.parse("$apiBaseUrl/media/alerts/$alertId"),
      headers: {"Authorization": "Bearer $token"},
    );
    
    final json = jsonDecode(response.body);
    if (json["success"] != true) {
      throw ApiException(
        code: json["error"]["code"],
        message: json["error"]["message"],
        httpStatus: response.statusCode ?? 400,
      );
    }
  } catch (e) {
    rethrow;
  }
}

// ============== LOGS/HISTORY ==============

// GET /logs - Get intrusion logs (paginated)
Future<Map<String, dynamic>> getLogs({
  int page = 1,
  int limit = 20,
  int? zoneId,
  DateTime? fromDate,
  DateTime? toDate,
}) async {
  try {
    Map<String, String> params = {
      "page": page.toString(),
      "limit": limit.toString(),
    };
    
    if (zoneId != null) {
      params["zone_id"] = zoneId.toString();
    }
    if (fromDate != null) {
      params["from_date"] = fromDate.toIso8601String();
    }
    if (toDate != null) {
      params["to_date"] = toDate.toIso8601String();
    }
    
    final uri = Uri.parse("$apiBaseUrl/logs")
        .replace(queryParameters: params);
    
    final response = await client.get(
      uri,
      headers: {"Authorization": "Bearer $token"},
    );
    
    final json = jsonDecode(response.body);
    if (json["success"] == true) {
      return json["data"];
    } else {
      throw ApiException(
        code: json["error"]["code"],
        message: json["error"]["message"],
        httpStatus: response.statusCode ?? 400,
      );
    }
  } catch (e) {
    rethrow;
  }
}
```

**Effort: 3-4 hours**

---

## 🟡 MEDIUM PRIORITY

### 3.1 Update Data Models

**File**: `lib/models/zone_model.dart`

```dart
class Zone {
  final int id;
  final String name;
  final String cameraId;
  final String zoneType;
  final List<Coordinate> coordinates;
  final bool isActive;
  final int alertCooldownSeconds;
  final DateTime createdAt;
  final DateTime updatedAt;  // ADD THIS

  Zone({
    required this.id,
    required this.name,
    required this.cameraId,
    required this.zoneType,
    required this.coordinates,
    required this.isActive,
    required this.alertCooldownSeconds,
    required this.createdAt,
    required this.updatedAt,  // ADD THIS
  });

  factory Zone.fromJson(Map<String, dynamic> json) {
    return Zone(
      id: json['zone_id'] as int,
      name: json['name'] as String,
      cameraId: json['camera_id'] as String,
      zoneType: json['zone_type'] as String,
      coordinates: (json['coordinates'] as List)
          .map((c) => Coordinate.fromJson(c as Map<String, dynamic>))
          .toList(),
      isActive: json['is_active'] as bool,
      alertCooldownSeconds: json['alert_cooldown_seconds'] as int? ?? 30,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),  // ADD THIS
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'zone_id': id,
      'name': name,
      'camera_id': cameraId,
      'zone_type': zoneType,
      'coordinates': coordinates.map((c) => c.toJson()).toList(),
      'is_active': isActive,
      'alert_cooldown_seconds': alertCooldownSeconds,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),  // ADD THIS
    };
  }
}

class Coordinate {
  final double x;
  final double y;

  Coordinate({required this.x, required this.y});

  factory Coordinate.fromJson(Map<String, dynamic> json) {
    return Coordinate(
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {'x': x, 'y': y};
  }
}
```

**Effort: 30 minutes**

---

### 3.2 Handle WebSocket "Connected" Event

**File**: `lib/services/websocket_service.dart`

```dart
class WebSocketService {
  static final WebSocketService _instance = WebSocketService._();
  
  factory WebSocketService() => _instance;
  
  WebSocketService._() {
    // ...
  }
  
  // NEW: Handle all WebSocket events
  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(message);
      final event = data['event'] as String?;
      
      if (event == null) return;
      
      switch (event) {
        case 'connected':
          _handleConnected(data['data'] as Map<String, dynamic>?);
          break;
        case 'intrusion_detected':
          _handleIntrusionDetected(data['data'] as Map<String, dynamic>?);
          break;
        case 'intrusion_ended':
          _handleIntrusionEnded(data['data'] as Map<String, dynamic>?);
          break;
        case 'camera_status_changed':
          _handleCameraStatusChanged(data['data'] as Map<String, dynamic>?);
          break;
        case 'ping':
          _sendPong();
          break;
        default:
          print("[WS] Unknown event: $event");
      }
    } catch (e) {
      print("[WS] Error handling message: $e");
    }
  }
  
  // NEW: Handle connection confirmation
  void _handleConnected(Map<String, dynamic>? data) {
    print("[WS] Connected successfully");
    print("[WS] Message: ${data?['message']}");
    print("[WS] Timestamp: ${data?['timestamp']}");
    
    // Can trigger UI update to show "Connected" status
    _connectionStatusController.add(true);
  }
  
  void _handleIntrusionDetected(Map<String, dynamic>? data) {
    if (data == null) return;
    
    print("[WS] Intrusion detected");
    print("[WS] Zone: ${data['zone_name']} (${data['zone_id']})");
    print("[WS] Confidence: ${data['confidence']}");
    
    // Show notification, play alert, etc.
    _alertController.add(AlertEvent(
      alertId: data['alert_id'],
      zoneId: data['zone_id'],
      zoneName: data['zone_name'],
      cameraId: data['camera_id'],
      detectedAt: DateTime.parse(data['detected_at']),
      confidence: data['confidence'],
      thumbnailUrl: data['thumbnail_url'],
      boundingBoxes: data['bounding_boxes'] ?? [],
    ));
  }
  
  void _handleIntrusionEnded(Map<String, dynamic>? data) {
    if (data == null) return;
    
    print("[WS] Intrusion ended");
    print("[WS] Duration: ${data['duration_seconds']}s");
    
    // Can update UI to show intrusion ended
    _intrussionEndedController.add(IntrusionEndedEvent(
      alertId: data['alert_id'],
      durationSeconds: data['duration_seconds'],
      exitedAt: DateTime.parse(data['exited_at']),
    ));
  }
  
  void _handleCameraStatusChanged(Map<String, dynamic>? data) {
    if (data == null) return;
    
    final status = data['status'] as String;
    print("[WS] Camera status changed: ${data['camera_id']} -> $status");
    
    // Update camera status in UI
    _cameraStatusController.add(CameraStatusEvent(
      cameraId: data['camera_id'],
      status: status,
      timestamp: DateTime.parse(data['timestamp']),
    ));
  }
}

// NEW: Event models
class AlertEvent {
  final String alertId;
  final String zoneId;
  final String zoneName;
  final String? cameraId;
  final DateTime detectedAt;
  final double confidence;
  final String? thumbnailUrl;
  final List<dynamic> boundingBoxes;
  
  AlertEvent({
    required this.alertId,
    required this.zoneId,
    required this.zoneName,
    required this.cameraId,
    required this.detectedAt,
    required this.confidence,
    required this.thumbnailUrl,
    required this.boundingBoxes,
  });
}

class IntrusionEndedEvent {
  final String alertId;
  final int durationSeconds;
  final DateTime exitedAt;
  
  IntrusionEndedEvent({
    required this.alertId,
    required this.durationSeconds,
    required this.exitedAt,
  });
}

class CameraStatusEvent {
  final String cameraId;
  final String status;
  final DateTime timestamp;
  
  CameraStatusEvent({
    required this.cameraId,
    required this.status,
    required this.timestamp,
  });
}
```

**Effort: 30 minutes**

---

### 3.3 Fix Package Name

**Steps:**

1. **Rename package in Android:**
   ```bash
   # From project root
   flutter pub get
   
   # Manual rename:
   # Move: android/app/src/main/java/com/example/zone_moniter_app
   # To:   android/app/src/main/java/com/example/zone_monitor_app
   ```

2. **Update AndroidManifest.xml:**
   ```xml
   <!-- Change from -->
   <manifest package="com.example.zone_moniter_app">
   
   <!-- To -->
   <manifest package="com.example.zone_monitor_app">
   ```

3. **Update pubspec.yaml:**
   ```yaml
   flutter:
     uses-material-design: true
   ```

4. **Clean and rebuild:**
   ```bash
   flutter clean
   flutter pub get
   flutter run
   ```

**Effort: 1-2 hours**

---

### 3.4 Add Video Player Dependency

**File**: `pubspec.yaml`

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # ... existing dependencies ...
  
  # NEW: Video streaming
  video_player: ^2.4.0
  
  # Optional: for RTSP support (if needed)
  # flutter_vlc_player: ^7.3.0
```

**Effort: 30 minutes**

---

## 🧪 TESTING CHECKLIST

### Before Release
- [ ] Test login with correct/incorrect credentials
- [ ] Test stream video playback (HLS)
- [ ] Test real-time WebSocket alerts
- [ ] Test error handling (401, 404, 500)
- [ ] Test zone create/read/update/delete
- [ ] Test alert list with pagination
- [ ] Test logs/history view
- [ ] Test WebSocket connection status display
- [ ] Test alert notification (if FCM available)
- [ ] Test offline behavior
- [ ] Test network timeout handling
- [ ] Test package name is consistent

### Integration Tests
```dart
// test/integration_test/api_test.dart

void main() {
  group('API Integration Tests', () {
    
    test('Login and get token', () async {
      final result = await ApiService.instance.login('admin', 'password');
      expect(result['access_token'], isNotNull);
    });
    
    test('Fetch stream URLs', () async {
      final urls = await ApiService.instance.getStreamUrls();
      expect(urls['hls'], isNotNull);
      expect(urls['rtsp'], isNotNull);
    });
    
    test('Get zone details', () async {
      final zone = await ApiService.instance.getZoneDetails(1);
      expect(zone['zone_id'], isNotNull);
      expect(zone['zone_name'], isNotNull);
    });
    
    test('Handle 404 error', () async {
      expect(
        () => ApiService.instance.getZoneDetails(9999),
        throwsA(isA<ApiException>()),
      );
    });
  });
}
```

---

## 📋 Implementation Checklist

- [ ] Update stream handling to RTSP/HLS
- [ ] Add video_player dependency
- [ ] Update error handling with new API format
- [ ] Add missing API methods (CRUD zones, logs)
- [ ] Update ZoneModel with updated_at field
- [ ] Handle WebSocket "connected" event
- [ ] Fix package name consistency
- [ ] Update AndroidManifest.xml (if needed)
- [ ] Run flutter clean
- [ ] Run flutter pub get
- [ ] Test all features
- [ ] Run integration tests

---

## 📊 Summary of Changes

| Component | Change | Priority | Time |
|-----------|--------|----------|------|
| Stream | MJPEG → RTSP/HLS | 🔴 | 2-3h |
| Error Handling | Update format | 🟠 | 1-2h |
| API Methods | Add missing CRUD | 🟡 | 3-4h |
| Data Models | Add updated_at | 🟡 | 30min |
| WebSocket | Handle connected event | 🟡 | 30min |
| Package Name | Fix consistency | 🟡 | 1-2h |
| **TOTAL** | | | **8-12h** |

---

**Estimated Total Time: 9-13 hours**
