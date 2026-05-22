// lib/models/zone_model.dart
import 'dart:convert';

class ZonePoint {
  final double x;
  final double y;

  const ZonePoint({required this.x, required this.y});

  factory ZonePoint.fromJson(Map<String, dynamic> j) {
    double x = (j['x'] as num).toDouble();
    double y = (j['y'] as num).toDouble();
    if (x > 1.0 || y > 1.0) {
      x /= 100.0;
      y /= 100.0;
    }
    return ZonePoint(x: x, y: y);
  }

  Map<String, dynamic> toJson() => {'x': x, 'y': y};
}

class ZoneModel {
  final String zoneId;
  final String name;
  final String cameraId;
  final String zoneType;
  final List<ZonePoint> coordinates;
  bool isActive;
  final int alertCooldownSeconds;
  final DateTime createdAt;
  // final DateTime updatedAt; // Removed as per database change

  ZoneModel({
    required this.zoneId,
    required this.name,
    required this.cameraId,
    required this.zoneType,
    required this.coordinates,
    required this.isActive,
    required this.alertCooldownSeconds,
    required this.createdAt,
    // required this.updatedAt,
  });

  factory ZoneModel.fromJson(Map<String, dynamic> j) {
    // 1. Xử lý ID linh hoạt (bắt cả 'zone_id' hoặc 'id')
    final String parsedZoneId = (j['zone_id'] ?? j['id'] ?? '').toString();

    // 2. Xử lý mảng tọa độ (Coordinates) chống lỗi String JSON
    dynamic coordsRaw = j['coordinates'];
    List<dynamic> coordsList = [];

    if (coordsRaw != null) {
      if (coordsRaw is String) {
        try {
          coordsList = jsonDecode(coordsRaw);
        } catch (e) {
          print('Lỗi parse coordinates JSON string: $e');
        }
      } else if (coordsRaw is List) {
        coordsList = coordsRaw;
      }
    }

    return ZoneModel(
      zoneId: parsedZoneId,
      name: j['name'] ?? 'Vùng cấm',
      cameraId: (j['camera_id'] ?? '').toString(),
      zoneType: j['zone_type'] ?? 'polygon',
      // Xử lý tọa độ thông qua mảng đã được làm sạch ở trên
      coordinates: coordsList.map((e) => ZonePoint.fromJson(e)).toList(),
      isActive: j['is_active'] ?? true,
      alertCooldownSeconds: j['alert_cooldown_seconds'] ?? 30,
      createdAt: j['created_at'] != null ? DateTime.parse(j['created_at']) : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
    'name': name,
    'camera_id': cameraId,
    'zone_type': zoneType,
    'coordinates': coordinates.map((c) => c.toJson()).toList(),
    'is_active': isActive,
    'alert_cooldown_seconds': alertCooldownSeconds,
    'created_at': createdAt.toIso8601String(),
    // 'updated_at': updatedAt.toIso8601String(),
  };
}
