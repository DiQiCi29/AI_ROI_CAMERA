// lib/models/zone_model.dart

class ZonePoint {
  final double x; // % 0-100
  final double y; // % 0-100

  const ZonePoint({required this.x, required this.y});

  factory ZonePoint.fromJson(Map<String, dynamic> j) {
    double x = (j['x'] as num).toDouble();
    double y = (j['y'] as num).toDouble();
    // Tự động chuẩn hóa nếu dữ liệu là hệ 0-100 thay vì 0-1
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

  factory ZoneModel.fromJson(Map<String, dynamic> j) => ZoneModel(
    zoneId: j['zone_id'].toString(),
    name: j['name'],
    cameraId: j['camera_id'].toString(),
    zoneType: j['zone_type'] ?? 'polygon',
    coordinates: (j['coordinates'] as List).map((e) => ZonePoint.fromJson(e)).toList(),
    isActive: j['is_active'] ?? true,
    alertCooldownSeconds: j['alert_cooldown_seconds'] ?? 30,
    createdAt: DateTime.parse(j['created_at']),
    // updatedAt: DateTime.parse(j['updated_at'] ?? j['created_at']),
  );

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
