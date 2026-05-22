// lib/widgets/live_bbox_overlay.dart

import 'package:flutter/material.dart';

class LiveBboxPainter extends CustomPainter {
  final List<dynamic> intruders;
  final Size frameSize;

  LiveBboxPainter({
    required this.intruders,
    required this.frameSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (intruders.isEmpty) return;

    final paint = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final textBgPaint = Paint()
      ..color = Colors.red.withOpacity(0.8)
      ..style = PaintingStyle.fill;

    for (var intruder in intruders) {
      final bbox = intruder['bbox'] as List<dynamic>;
      if (bbox.length < 4) continue;

      // Chuyển đổi từ chuẩn hóa (0.0 - 1.0) ra pixel thực của Widget AspectRatio
      final double x1 = bbox[0] * frameSize.width;
      final double y1 = bbox[1] * frameSize.height;
      final double x2 = bbox[2] * frameSize.width;
      final double y2 = bbox[3] * frameSize.height;

      final rect = Rect.fromLTRB(x1, y1, x2, y2);

      final rrect = RRect.fromRectAndRadius(rect, const Radius.circular(8));
      canvas.drawRRect(rrect, paint);

      // Điểm chấm ở chân
      final footX = (x1 + x2) / 2;
      final footY = y2;
      canvas.drawCircle(Offset(footX, footY), 5, Paint()..color = Colors.red..style = PaintingStyle.fill);

      final double confidence = intruder['confidence'] ?? 0.0;
      final String labelText = "INTRUDER ${(confidence * 100).toStringAsFixed(0)}%";

      final textPainter = TextPainter(
        text: TextSpan(
          text: labelText,
          style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();

      final backgroundRect = Rect.fromLTWH(
        x1,
        y1 - textPainter.height - 4,
        textPainter.width + 8,
        textPainter.height + 4,
      );
      canvas.drawRect(backgroundRect, textBgPaint);

      textPainter.paint(canvas, Offset(x1 + 4, y1 - textPainter.height - 2));
    }
  }

  @override
  bool shouldRepaint(covariant LiveBboxPainter oldDelegate) {
    // Ép buộc vẽ lại khi tọa độ người hoặc khung hình thiết bị thay đổi
    return oldDelegate.intruders != intruders || oldDelegate.frameSize != frameSize;
  }
}