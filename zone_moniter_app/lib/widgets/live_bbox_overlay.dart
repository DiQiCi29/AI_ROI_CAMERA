import 'package:flutter/material.dart';

class LiveBboxPainter extends CustomPainter {
  final List<dynamic> intruders; // Format: [{"bbox": [x1, y1, x2, y2], "confidence": 0.9}, ...]

  LiveBboxPainter({required this.intruders});

  @override
  void paint(Canvas canvas, Size size) {
    if (intruders.isEmpty) return;

    final boxPaint = Paint()
      ..color = Colors.redAccent
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final bgPaint = Paint()
      ..color = Colors.redAccent.withOpacity(0.2)
      ..style = PaintingStyle.fill;

    for (var intruder in intruders) {
      final bbox = intruder['bbox'] as List; // [x1, y1, x2, y2] từ 0.0 -> 1.0

      // Nhân với kích thước thực tế của khung video
      final left = bbox[0] * size.width;
      final top = bbox[1] * size.height;
      final right = bbox[2] * size.width;
      final bottom = bbox[3] * size.height;

      final rect = Rect.fromLTRB(left, top, right, bottom);
      final rRect = RRect.fromRectAndRadius(rect, const Radius.circular(8));

      canvas.drawRRect(rRect, bgPaint);
      canvas.drawRRect(rRect, boxPaint);

      // (Tùy chọn) Vẽ chấm tròn ở chân kẻ xâm nhập
      final footPoint = Offset((left + right) / 2, bottom);
      canvas.drawCircle(footPoint, 4, Paint()..color = Colors.red);
    }
  }

  @override
  bool shouldRepaint(covariant LiveBboxPainter oldDelegate) => true;
}