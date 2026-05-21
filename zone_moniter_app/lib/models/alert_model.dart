// lib/models/alert_model.dart

class BoundingBox {
  final double x, y, w, h; // Updated to w, h as per ANDROID_API_GUIDE.md
  final String label;
  final double confidence;

  const BoundingBox({
    required this.x,
    required this.y,
    required this.w,
    required this.h,
    required this.label,
    required this.confidence,
  });

  factory BoundingBox.fromJson(Map<String, dynamic> j) => BoundingBox(
    x: (j['x'] as num).toDouble(),
    y: (j['y'] as num).toDouble(),
    w: (j['w'] as num).toDouble(),
    h: (j['h'] as num).toDouble(),
    label: j['label'] ?? '',
    confidence: (j['confidence'] as num?)?.toDouble() ?? 0.0,
  );
}

class AlertModel {
  final String alertId;
  final String? cameraId; // Made optional or added as per guide
  final String zoneId;
  final String zoneName;
  final DateTime detectedAt;
  bool isRead;
  final String? thumbnailUrl;
  final String? videoUrl;
  final List<BoundingBox> boundingBoxes;
  final int objectCount;
  final double confidence;

  AlertModel({
    required this.alertId,
    this.cameraId,
    required this.zoneId,
    required this.zoneName,
    required this.detectedAt,
    required this.isRead,
    this.thumbnailUrl,
    this.videoUrl,
    required this.boundingBoxes,
    required this.objectCount,
    required this.confidence,
  });

  factory AlertModel.fromJson(Map<String, dynamic> j) => AlertModel(
    alertId: j['alert_id'].toString(),
    cameraId: j['camera_id']?.toString(),
    zoneId: j['zone_id'].toString(),
    zoneName: j['zone_name'] ?? '',
    detectedAt: DateTime.parse(j['detected_at']),
    isRead: j['is_read'] ?? false,
    thumbnailUrl: j['thumbnail_url'],
    videoUrl: j['video_url'],
    boundingBoxes: (j['bounding_boxes'] as List? ?? [])
        .map((e) => BoundingBox.fromJson(e))
        .toList(),
    objectCount: j['object_count'] ?? 1,
    confidence: (j['confidence'] as num?)?.toDouble() ?? 0.0,
  );
}
