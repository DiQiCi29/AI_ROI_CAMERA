// lib/config/app_config.dart

class AppConfig {
  static String baseUrl = 'http://192.168.0.4:8000/api/v1';

  static String get wsUrl {
    try {
      Uri uri = Uri.parse(baseUrl);
      String scheme = uri.scheme == 'https' ? 'wss' : 'ws';
      return '$scheme://${uri.host}:${uri.port}/ws';
    } catch (e) {
      return 'ws://192.168.0.4:8000/ws';
    }
  }

  static String get webrtcBaseUrl {
    try {
      Uri uri = Uri.parse(baseUrl);
      // MediaMTX WebRTC UI port
      return 'http://${uri.host}:8889';
    } catch (e) {
      return 'http://192.168.1.100:8889';
    }
  }

  // Auth
  static String get login             => '$baseUrl/auth/login';
  static String get registerFcm       => '$baseUrl/auth/register-fcm-token';
  static String get logout            => '$baseUrl/auth/logout';

  // Camera Stream
  static String get aiStream          => '$baseUrl/stream/video/ai'; 
  static String get snapshot          => '$baseUrl/stream/snapshot';
  static String get cameraStatus      => '$baseUrl/stream/status';
  
  // WebRTC URL cho WebView: http://host:8889/<camera_name>
  // MediaMTX sẽ tự động phục vụ một trang HTML player tại đây.
  static String webrtcPage(String cameraName) => '$webrtcBaseUrl/$cameraName';

  // Zones
  static String get zones             => '$baseUrl/zones';
  static String zone(String id)       => '$baseUrl/zones/$id';
  static String zoneToggle(String id) => '$baseUrl/zones/$id/toggle';

  // Alerts
  static String get alerts            => '$baseUrl/alerts';
  static String alert(String id)      => '$baseUrl/alerts/$id';
  static String alertRead(String id)  => '$baseUrl/alerts/$id/read';
  static String get readAllAlerts     => '$baseUrl/alerts/read-all';
  static String get unreadCount       => '$baseUrl/alerts/unread-count';

  // Logs
  static String get logs              => '$baseUrl/logs';
  static String get logStats          => '$baseUrl/logs/stats';

  // Media
  static String mediaThumbnail(String alertId) =>
      '$baseUrl/media/alerts/$alertId/thumbnail';
  static String mediaVideo(String alertId) =>
      '$baseUrl/media/alerts/$alertId/video';

  static String wsWithToken(String token) => '$wsUrl?token=$token';
}
