// lib/providers/app_provider.dart

import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../models/zone_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../services/notification_service.dart';
import '../config/app_config.dart';

class AppProvider extends ChangeNotifier {
  bool _isLoggedIn = false;
  String? _token;
  Uint8List? _cameraSnapshotBytes;
  int _unreadCount = 0;
  bool _cameraOnline = false;
  String? _currentCameraId;
  bool _isLoading = false;
  List<ZoneModel> _zones = [];

  // Trạng thái cảnh báo xâm nhập trực tiếp
  Map<String, dynamic>? _activeAlert;
  bool get hasActiveAlert => _activeAlert != null;
  Map<String, dynamic>? get activeAlert => _activeAlert;

  bool get isLoggedIn => _isLoggedIn;
  String? get token => _token;
  Uint8List? get cameraSnapshotBytes => _cameraSnapshotBytes;
  int get unreadCount => _unreadCount;
  bool get cameraOnline => _cameraOnline;
  bool get isLoading => _isLoading;
  String? get currentCameraId => _currentCameraId;
  List<ZoneModel> get zones => _zones;

  final WebSocketService _ws = WebSocketService();

  // ─── Auth ──────────────────────────────────────────────
  Future<void> loadSavedToken() async {
    // 1. Load saved Server URL first
    final savedUrl = await ApiService.getSavedBaseUrl();
    if (savedUrl != null && savedUrl.isNotEmpty) {
      AppConfig.baseUrl = savedUrl;
      ApiService.instance.updateBaseUrl(savedUrl);
    }

    final token = await ApiService.getToken();
    if (token != null && token.isNotEmpty) {
      _token = token;
      _isLoggedIn = true;
      notifyListeners();
      await _afterLogin();
    }
  }

  Future<bool> login(String username, String password) async {
    try {
      final res = await ApiService.instance.login(username, password);
      _token = res['access_token'];
      if (_token != null) {
        await ApiService.saveToken(_token!);
        // Save current server URL on successful login
        await ApiService.saveBaseUrl(AppConfig.baseUrl);
      }
      _isLoggedIn = true;
      notifyListeners();
      await _afterLogin();
      return true;
    } catch (e) {
      debugPrint('Lỗi đăng nhập: $e');
      rethrow;
    }
  }

  Future<void> _afterLogin() async {
    // Kết nối WebSocket
    _setupWebSocket();
    _ws.connect();

    // Đăng ký FCM token
    try {
      final fcmToken = await NotificationService.getFcmToken();
      if (fcmToken != null) {
        // Assume deviceId is required, can be generated or fetched
        await ApiService.instance.registerFcmToken(fcmToken, 'android_device_id');
      }
    } catch (e) {
      debugPrint('Chưa cấu hình Firebase hoặc lỗi FCM: $e');
    }

    // Load dữ liệu ban đầu
    try {
      // Refresh camera status first to get the correct camera ID
      await refreshCameraStatus();
      
      await Future.wait([
        loadZones(),
        refreshUnreadCount(),
      ]);
    } catch (e) {
      debugPrint('Lỗi tải dữ liệu ban đầu: $e');
    }
  }

  void _setupWebSocket() {
    _ws.onIntrusionDetected = (data) {
      _activeAlert = data;
      _unreadCount++;
      notifyListeners();
      NotificationService.triggerAlert(zoneName: data['zone_name']);
    };

    _ws.onIntrusionEnded = (data) {
      notifyListeners();
    };

    _ws.onCameraStatusChanged = (data) {
      _cameraOnline = data['status'] == 'online';
      notifyListeners();
    };
  }

  Future<void> logout() async {
    _ws.disconnect();
    
    // Clear state immediately for better UX
    _isLoggedIn = false;
    _token = null;
    _zones = [];
    _activeAlert = null;
    _unreadCount = 0;
    _cameraOnline = false;
    notifyListeners();

    // Fire and forget logout request, don't wait for it
    ApiService.instance.logout('android_device_id').catchError((e) {
      debugPrint('Logout error (ignored): $e');
    });
  }

  // ─── Zones ─────────────────────────────────────────────
  Future<void> loadZones() async {
    _isLoading = true;
    notifyListeners();

    try {
      final int? camId = int.tryParse(_currentCameraId ?? '');
      _zones = await ApiService.instance.getZones(cameraId: camId);
      debugPrint("✓ [Provider] Loaded ${_zones.length} zones successfully.");
    } catch (e) {
      debugPrint("✗ [Provider] Exception inside loadZones: $e");
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createZone(Map<String, dynamic> data) async {
    try {
      final zone = await ApiService.instance.createZone(data);
      _zones.add(zone);
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('Lỗi tạo Zone: $e');
      return false;
    }
  }

  Future<bool> deleteZone(String zoneId) async {
    try {
      final intId = int.tryParse(zoneId);
      if (intId != null) {
        await ApiService.instance.deleteZone(intId);
        _zones.removeWhere((z) => z.zoneId == zoneId);
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Lỗi xóa Zone: $e');
      return false;
    }
  }

  Future<void> toggleZone(String zoneId) async {
    try {
      final intId = int.tryParse(zoneId);
      if (intId != null) {
        final newState = await ApiService.instance.toggleZone(intId);
        final index = _zones.indexWhere((z) => z.zoneId == zoneId);
        if (index != -1) {
          _zones[index].isActive = newState;
          notifyListeners();
        }
      }
    } catch (e) {
      debugPrint('Lỗi bật/tắt Zone: $e');
    }
  }

  // ─── Alerts & Stats ────────────────────────────────────
  Future<void> refreshUnreadCount() async {
    try {
      _unreadCount = await ApiService.instance.getUnreadCount();
      notifyListeners();
    } catch (e) {
      debugPrint('Error refreshing unread count: $e');
    }
  }

  Future<void> refreshCameraStatus() async {
    try {
      final status = await ApiService.instance.getCameraStatus();
      _cameraOnline = status['status'] == 'online';
      _currentCameraId = status['camera_id']?.toString();
      notifyListeners();
    } catch (e) {
      debugPrint('Error refreshing camera status: $e');
      _cameraOnline = false;
      notifyListeners();
    }
  }

  void dismissActiveAlert() {
    _activeAlert = null;
    NotificationService.stopAlert();
    notifyListeners();
  }

  // Thêm hàm để kết nối lại khi đổi IP
  void reconnectAll() {
    _ws.disconnect();
    if (_isLoggedIn) {
      _ws.connect();
      loadZones();
      refreshCameraStatus();
    }
  }
  Future<bool> fetchCameraSnapshot() async {
    _isLoading = true;
    _cameraSnapshotBytes = null;
    notifyListeners();

    try {
      final int camId = int.tryParse(_currentCameraId ?? '') ?? 1;
      final Uint8List? bytes = await ApiService.getCameraSnapshotBytes(camId);

      if (bytes != null && bytes.isNotEmpty) {
        _cameraSnapshotBytes = bytes;
        return true;
      }
      return false;
    } catch (e) {
      debugPrint("✗ [Provider] Lỗi xử lý ảnh snapshot: $e");
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

