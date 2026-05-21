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

  // Tránh vòng lặp reconnect vô hạn làm treo máy
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;

  Stream<Map<String, dynamic>> get events => _controller?.stream ?? const Stream.empty();

  Function(Map<String, dynamic>)? onIntrusionDetected;
  Function(Map<String, dynamic>)? onIntrusionEnded;
  Function(Map<String, dynamic>)? onCameraStatusChanged;
  Function(WsStatus)? onStatusChanged;
  Function(Map<String, dynamic>)? onConnected; // ADDED
  Function(Map<String, dynamic>)? onLiveBboxes;

  Future<void> connect() async {
    if (_status == WsStatus.connecting || _status == WsStatus.connected) return;

    _status = WsStatus.connecting;
    onStatusChanged?.call(_status);

    try {
      final token = await ApiService.getToken();
      if (token == null || token.isEmpty) {
        _status = WsStatus.disconnected;
        onStatusChanged?.call(_status);
        return;
      }

      _controller ??= StreamController<Map<String, dynamic>>.broadcast();

      final uri = Uri.parse(AppConfig.wsWithToken(token));
      _channel = WebSocketChannel.connect(uri);

      // We wait for the 'connected' event from server before setting status to connected
      // but usually WebSocketChannel.connect doesn't wait for server message.
      // So we set it to connected here or in _handleMessage 'connected' case.
      // Setting it here for now to allow _send to work.
      _status = WsStatus.connected; 
      _reconnectAttempts = 0; 
      onStatusChanged?.call(_status);

      _channel!.stream.listen(
            (message) => _handleMessage(message),
        onDone: _onDisconnect,
        onError: (e) {
          debugPrint('WebSocket error: $e');
          _onDisconnect();
        },
      );

      _startPing();
    } catch (e) {
      debugPrint('WebSocket connect exception: $e');
      _onDisconnect();
    }
  }

  void _handleMessage(dynamic raw) {
    if (raw is! String) return;

    try {
      final data = jsonDecode(raw) as Map<String, dynamic>;
      final event = data['event'] as String?;
      _controller?.add(data);

      switch (event) {
        case 'connected': // ADDED
          debugPrint('[WS] Connection confirmed by server');
          onConnected?.call(data['data'] ?? {});
          break;
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
          onLiveBboxes?.call(data['data']);
          break;
        case 'ping': // ADDED
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
      debugPrint('WS reconnect sau $delaySeconds giây... (Lần $_reconnectAttempts)');
      _reconnectTimer = Timer(Duration(seconds: delaySeconds), connect);
    }
  }

  void disconnect() {
    _pingTimer?.cancel();
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _status = WsStatus.disconnected;
    _reconnectAttempts = 0;
    onStatusChanged?.call(_status);
  }
}
