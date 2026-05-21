import 'package:flutter/material.dart';
import '../models/zone_model.dart';

class ZoneOverlayPainter extends CustomPainter {
  final List<ZoneModel> zones;
  final List<ZonePoint>? drawingPoints;
  final Size frameSize;

  ZoneOverlayPainter({
    required this.zones,
    this.drawingPoints,
    required this.frameSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    for (final zone in zones) {
      if (zone.coordinates.length < 3) continue;
      _drawZone(canvas, size, zone.coordinates,
          color: zone.isActive ? Colors.red : Colors.grey,
          isActive: zone.isActive,
          label: zone.name);
    }

    if (drawingPoints != null && drawingPoints!.isNotEmpty) {
      _drawZone(canvas, size, drawingPoints!,
          color: Colors.yellow, isActive: false, label: '');
    }
  }

  void _drawZone(
      Canvas canvas, Size size, List<ZonePoint> points, {
        required Color color, required bool isActive, required String label,
      }) {
    if (points.isEmpty) return;

    final fillPaint = Paint()..color = color.withOpacity(0.15)..style = PaintingStyle.fill;
    final strokePaint = Paint()..color = color.withOpacity(0.8)..style = PaintingStyle.stroke..strokeWidth = 2.0;

    final path = Path();
    final first = _toPixel(points.first, size);
    path.moveTo(first.dx, first.dy);

    for (int i = 1; i < points.length; i++) {
      final p = _toPixel(points[i], size);
      path.lineTo(p.dx, p.dy);
    }
    path.close();

    canvas.drawPath(path, fillPaint);
    canvas.drawPath(path, strokePaint);

    for (final pt in points) {
      final p = _toPixel(pt, size);
      canvas.drawCircle(p, 5, Paint()..color = color..style = PaintingStyle.fill);
    }

    if (label.isNotEmpty && points.isNotEmpty) {
      final center = _centerOf(points, size);
      final textPainter = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            color: color, fontSize: 13, fontWeight: FontWeight.bold,
            shadows: const [Shadow(color: Colors.black, blurRadius: 4, offset: Offset(1, 1))],
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      textPainter.paint(canvas, center - Offset(textPainter.width / 2, textPainter.height / 2));
    }
  }

  Offset _toPixel(ZonePoint p, Size size) => Offset(p.x * size.width, p.y * size.height);

  Offset _centerOf(List<ZonePoint> points, Size size) {
    double sumX = 0, sumY = 0;
    for (final p in points) { sumX += p.x; sumY += p.y; }
    return _toPixel(ZonePoint(x: sumX / points.length, y: sumY / points.length), size);
  }

  @override
  bool shouldRepaint(ZoneOverlayPainter oldDelegate) => true;
}