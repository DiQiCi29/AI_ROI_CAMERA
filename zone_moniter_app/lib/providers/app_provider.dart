// lib/providers/app_provider.dart

import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../models/zone_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../services/notification_service.dart';
import '../config/app_config.dart';
import '../main.dart';

class AppProvider extends ChangeNotifier {
  bool _isLoggedIn = false;
  String? _token;
  Uint8List? _cameraSnapshotBytes;
  int _unreadCount = 0;
  bool _cameraOnline = false;
  String? _currentCameraId;
  bool _isLoading = false;
  List<ZoneModel> _zones = [];

  Map<String, dynamic>? _activeAlert;

  // FIX: Cooldown sau khi người dùng bấm dismiss
  DateTime? _alertSuppressedUntil;
  static const _alertCooldownSeconds = 60;

  // FIX: Chỉ hiện overlay khi alert = true VÀ không trong cooldown
  bool get hasActiveAlert =>
      _activeAlert != null &&
          _activeAlert!['alert'] == true &&
          (_alertSuppressedUntil == null ||
              DateTime.now().isAfter(_alertSuppressedUntil!));

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

  AppProvider() {
    ApiService.instance.onTokenExpired = () {
      if (_isLoggedIn) {
        rootScaffoldMessengerKey.currentState?.showSnackBar(
          const SnackBar(
            content: Text('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại!'),
            backgroundColor: Colors.red,
            duration: Duration(seconds: 4),
          ),
        );
        logout();
      }
    };
  }

  Future<void> loadSavedToken() async {
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
    _setupWebSocket();
    _ws.connect();

    try {
      final fcmToken = await NotificationService.getFcmToken();
      if (fcmToken != null) {
        await ApiService.instance.registerFcmToken(fcmToken, 'android_device_id');
      }
    } catch (e) {
      debugPrint('Chưa cấu hình Firebase hoặc lỗi FCM: $e');
    }

    try {
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
    // FIX: Tách biệt live bbox (hiển thị khung) vs intrusion_detected (pop-up cảnh báo)
    _ws.onLiveBboxes = (data) {
      // Trong cooldown → chỉ cập nhật bbox để vẽ khung, KHÔNG trigger overlay
      final bool inCooldown = _alertSuppressedUntil != null &&
          DateTime.now().isBefore(_alertSuppressedUntil!);

      final String incomingCamId = data['camera_id'].toString();
      final String currentCamId = (_currentCameraId ?? '1').toString();

      if (incomingCamId == currentCamId) {
        if (inCooldown) {
          // Vẫn cập nhật để vẽ bbox nhưng không kích hoạt overlay
          _activeAlert = {...data, 'alert': false};
        } else {
          _activeAlert = data;
        }
        notifyListeners();
      }
    };

    // Event intrusion_detected: cập nhật unread count + âm thanh
    _ws.onIntrusionDetected = (data) {
      _unreadCount++;
      // FIX: Chỉ phát âm thanh nếu không trong cooldown
      final bool inCooldown = _alertSuppressedUntil != null &&
          DateTime.now().isBefore(_alertSuppressedUntil!);
      if (!inCooldown) {
        NotificationService.triggerAlert(zoneName: data['zone_name']);
      }
      notifyListeners();
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
    _isLoggedIn = false;
    _token = null;
    _zones = [];
    _activeAlert = null;
    _alertSuppressedUntil = null;
    _unreadCount = 0;
    _cameraOnline = false;
    notifyListeners();

    ApiService.instance.logout('android_device_id').catchError((e) {
      debugPrint('Logout error (ignored): $e');
    });
  }

  Future<void> loadZones() async {
    _isLoading = true;
    notifyListeners();

    try {
      final int? camId = int.tryParse(_currentCameraId ?? '');
      _zones = await ApiService.instance.getZones(cameraId: camId);
    } catch (e) {
      debugPrint("✗ Lỗi loadZones: $e");
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

  // FIX: Dismiss với cooldown 60 giây
  void dismissActiveAlert() {
    _alertSuppressedUntil =
        DateTime.now().add(const Duration(seconds: _alertCooldownSeconds));
    _activeAlert = null;
    NotificationService.stopAlert();
    notifyListeners();
  }

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