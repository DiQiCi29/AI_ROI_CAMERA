// lib/services/api_service.dart

import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';
import '../models/zone_model.dart';
import '../models/alert_model.dart';

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

class ApiErrorHandler {
  static String getErrorMessage(ApiException exception) {
    switch (exception.code) {
      case "UNAUTHORIZED":
        return "Vui lòng đăng nhập lại";
      case "TOKEN_EXPIRED":
        return "Phiên đăng nhập đã hết hạn";
      case "FORBIDDEN":
        return "Bạn không có quyền truy cập";
      case "NOT_FOUND":
        return "Không tìm thấy tài nguyên";
      case "CAMERA_OFFLINE":
        return "Camera hiện đang ngoại tuyến";
      case "INTERNAL_ERROR":
        return "Lỗi hệ thống từ máy chủ";
      default:
        return exception.message;
    }
  }
  
  static void handleError(BuildContext context, dynamic error) {
    String message = "Đã có lỗi xảy ra";
    if (error is ApiException) {
      message = getErrorMessage(error);
    } else if (error is DioException) {
      message = "Lỗi kết nối mạng";
    } else {
      message = error.toString();
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 3),
      ),
    );
  }
}

class ApiService {
  static final ApiService instance = ApiService._();
  late Dio _dio;

  ApiService._() {
    _initDio();
  }

  void updateBaseUrl(String newUrl) {
    _dio.options.baseUrl = newUrl;
    debugPrint('Đã cập nhật ApiService BaseURL: $newUrl');
  }

  void _initDio() {
    _dio = Dio(BaseOptions(
      baseUrl: AppConfig.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));
    
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await getToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (DioException e, handler) {
        if (e.response != null) {
          final data = e.response!.data;
          if (data is Map && data.containsKey('error')) {
            final error = data['error'];
            throw ApiException(
              code: error['code'] ?? "UNKNOWN_ERROR",
              message: error['message'] ?? "Unknown error",
              httpStatus: error['http_status'] ?? e.response!.statusCode ?? 0,
            );
          }
        }
        return handler.next(e);
      },
    ));
  }

  // ─── Token & Config management ────────────────────────────────
  static Future<String?> getToken() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString('auth_token');
    } catch (e) {
      return null;
    }
  }

  static Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('auth_token', token);
  }

  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
  }

  static Future<void> saveBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', url);
  }

  static Future<String?> getSavedBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('server_url');
  }

  Map<String, dynamic> _handleResponse(Response response) {
    final data = response.data;
    if (data["success"] == true) {
      return data["data"] ?? {};
    }
    throw ApiException(
      code: "API_ERROR",
      message: "Operation failed",
      httpStatus: response.statusCode ?? 0,
    );
  }

  // Auth
  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await _dio.post('/auth/login', data: {
      'username': username,
      'password': password,
    });
    return _handleResponse(response);
  }

  Future<void> registerFcmToken(String fcmToken, String deviceId) async {
    await _dio.post('/auth/register-fcm-token', data: {
      'fcm_token': fcmToken,
      'device_id': deviceId,
      'platform': 'android',
    });
  }

  Future<void> logout(String deviceId) async {
    try {
      await _dio.delete('/auth/logout', data: {'device_id': deviceId});
    } finally {
      await clearToken();
    }
  }

  // Stream
  Future<Map<String, dynamic>> getStreamUrls({int cameraId = 1}) async {
    final response = await _dio.get('/stream/urls', queryParameters: {'camera_id': cameraId});
    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> getCameraStatus({int cameraId = 1}) async {
    final response = await _dio.get('/stream/status', queryParameters: {'camera_id': cameraId});
    return _handleResponse(response);
  }

  static Future<Uint8List?> getCameraSnapshotBytes(int cameraId) async {
    try {
      final token = await getToken();
      final response = await http.get(
        Uri.parse('${AppConfig.snapshot}?camera_id=$cameraId'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        return response.bodyBytes; // Trả về mảng byte nguyên bản
      }
      return null;
    } catch (e) {
      debugPrint("✗ Lỗi ApiService getSnapshot: $e");
      return null;
    }
  }

  // Zones
  Future<List<ZoneModel>> getZones({int? cameraId, bool? isActive}) async {
    final response = await _dio.get('/zones', queryParameters: {
      if (cameraId != null) 'camera_id': cameraId,
      if (isActive != null) 'is_active': isActive,
    });
    // data là List trực tiếp
    final raw = _handleResponse(response);
    final List<dynamic> tempList;
    if (raw is List) {
      tempList = raw as List<dynamic>;
    } else {
      tempList = (raw['zones'] as List?) ?? [];
    }
    return tempList.map((e) => ZoneModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<ZoneModel> createZone(Map<String, dynamic> data) async {
    final response = await _dio.post('/zones', data: data);
    return ZoneModel.fromJson(_handleResponse(response));
  }

  Future<ZoneModel> updateZone(int zoneId, Map<String, dynamic> data) async {
    final response = await _dio.put('/zones/$zoneId', data: data);
    return ZoneModel.fromJson(_handleResponse(response));
  }

  Future<void> deleteZone(int zoneId) async {
    await _dio.delete('/zones/$zoneId');
  }

  Future<bool> toggleZone(int zoneId) async {
    final response = await _dio.patch('/zones/$zoneId/toggle');
    return _handleResponse(response)['is_active'];
  }

  // Alerts
  Future<Map<String, dynamic>> getAlerts({
    int page = 1,
    int limit = 20,
    int? zoneId,
    bool? isRead,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    final response = await _dio.get('/alerts', queryParameters: {
      'page': page,
      'limit': limit,
      if (zoneId != null) 'zone_id': zoneId,
      if (isRead != null) 'is_read': isRead,
      if (fromDate != null) 'from_date': fromDate.toIso8601String(),
      if (toDate != null) 'to_date': toDate.toIso8601String(),
    });
    return _handleResponse(response);
  }

  Future<AlertModel> getAlertDetails(String alertId) async {
    final response = await _dio.get('/alerts/$alertId');
    return AlertModel.fromJson(_handleResponse(response));
  }

  Future<void> markAlertAsRead(String alertId) async {
    await _dio.patch('/alerts/$alertId/read');
  }

  Future<void> markAllAlertsAsRead() async {
    await _dio.patch('/alerts/read-all');
  }

  Future<int> getUnreadCount() async {
    final response = await _dio.get('/alerts/unread-count');
    return _handleResponse(response)['unread_count'] ?? 0;
  }

  // Logs & Analytics
  Future<Map<String, dynamic>> getLogs({int page = 1, int limit = 20, int? zoneId}) async {
    final response = await _dio.get('/logs', queryParameters: {
      'page': page,
      'limit': limit,
      if (zoneId != null) 'zone_id': zoneId,
    });
    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> getStats() async {
    final response = await _dio.get('/logs/stats');
    return _handleResponse(response);
  }

  // Media
  Future<void> deleteMedia(String alertId) async {
    await _dio.delete('/media/alerts/$alertId');
  }
}
