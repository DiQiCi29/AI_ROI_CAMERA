// lib/services/websocket_service.dart

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/app_config.dart';
import '../services/api_service.dart';

enum WsStatus { disconnected, connecting, connected }

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  StreamController<Map<String, dynamic>>? _controller;
  Timer? _pingTimer;
  Timer? _reconnectTimer;

  WsStatus _status = WsStatus.disconnected;
  WsStatus get status => _status;

  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;

  Stream<Map<String, dynamic>> get events => _controller?.stream ?? const Stream.empty();

  Function(Map<String, dynamic>)? onIntrusionDetected;
  Function(Map<String, dynamic>)? onIntrusionEnded;
  Function(Map<String, dynamic>)? onCameraStatusChanged;
  Function(WsStatus)? onStatusChanged;
  Function(Map<String, dynamic>)? onConnected;
  Function(Map<String, dynamic>)? onLiveBboxes; // Cổng nhận luồng tọa độ trực tiếp

  void connect() async {
    if (_status == WsStatus.connected || _status == WsStatus.connecting) return;
    _status = WsStatus.connecting;
    onStatusChanged?.call(_status);

    final token = await ApiService.getToken();

    // ĐÃ SỬA: Gọi đúng thuộc tính wsUrl từ AppConfig và tự động nối thêm Token
    final baseWsUrl = AppConfig.wsUrl;
    final wsUrl = (token != null && token.isNotEmpty)
        ? '$baseWsUrl?token=$token'
        : baseWsUrl;

    debugPrint('[WS] Connecting to: $wsUrl');

    try {
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _status = WsStatus.connected;
      _reconnectAttempts = 0;
      onStatusChanged?.call(_status);
      _startPing();

      _channel!.stream.listen(
            (message) => _handleMessage(message),
        onError: (err) {
          debugPrint('[WS] Error: $err');
          _onDisconnect();
        },
        onDone: () {
          debugPrint('[WS] Connection closed by server');
          _onDisconnect();
        },
      );
    } catch (e) {
      debugPrint('[WS] Connection failed: $e');
      _onDisconnect();
    }
  }

  void disconnect() {
    _pingTimer?.cancel();
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _onDisconnect();
  }

  void _handleMessage(dynamic message) {
    if (message is! String) return;

    try {
      final data = jsonDecode(message);
      final event = data['event'];

      switch (event) {
        case 'intrusion_detected':
          onIntrusionDetected?.call(data['data']);
          break;
        case 'intrusion_ended':
          onIntrusionEnded?.call(data['data']);
          break;
        case 'camera_status_changed':
          onCameraStatusChanged?.call(data['data']);
          break;
        case 'live_intrusion_boxes':
        // Kích hoạt truyền dữ liệu sang Provider
          if (onLiveBboxes != null) {
            onLiveBboxes!(data['data']);
          }
          break;
        case 'ping':
          _send({'event': 'pong'});
          break;
      }
    } catch (e) {
      debugPrint('Lỗi parse WebSocket data: $e');
    }
  }

  void _startPing() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _send({'event': 'ping'});
    });
  }

  void _send(Map<String, dynamic> data) {
    if (_status != WsStatus.connected) return;
    try {
      _channel?.sink.add(jsonEncode(data));
    } catch (e) {
      debugPrint('Lỗi khi gửi WS: $e');
    }
  }

  void _onDisconnect() {
    _pingTimer?.cancel();
    _status = WsStatus.disconnected;
    onStatusChanged?.call(_status);

    _reconnectTimer?.cancel();
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _reconnectAttempts++;
      final delaySeconds = 2 * _reconnectAttempts;
      _reconnectTimer = Timer(Duration(seconds: delaySeconds), () => connect());
    }
  }
}