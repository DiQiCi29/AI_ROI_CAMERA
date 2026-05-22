// lib/widgets/live_bbox_overlay.dart

import 'package:flutter/material.dart';

class LiveBboxPainter extends CustomPainter {
  final List<dynamic> intruders;     // Người trong ROI → vẽ đỏ
  final List<dynamic> allPeople;     // Tất cả người detect được
  final Size frameSize;

  LiveBboxPainter({
    required this.intruders,
    required this.frameSize,
    this.allPeople = const [],
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Vẽ TẤT CẢ người detect được (màu xanh)
    for (var person in allPeople) {
      final bbox = person['bbox'] as List<dynamic>;
      if (bbox.length < 4) continue;

      final double x1 = bbox[0] * frameSize.width;
      final double y1 = bbox[1] * frameSize.height;
      final double x2 = bbox[2] * frameSize.width;
      final double y2 = bbox[3] * frameSize.height;

      // Kiểm tra xem người này có trong intruders (ROI) không
      final bool isInRoi = _isPersonInIntruders(person);
      if (isInRoi) continue; // Bỏ qua, sẽ vẽ đỏ sau

      // Màu xanh cho người ngoài ROI
      final greenPaint = Paint()
        ..color = Colors.green
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2;

      final greenBgPaint = Paint()
        ..color = Colors.green.withOpacity(0.8)
        ..style = PaintingStyle.fill;

      final rect = Rect.fromLTRB(x1, y1, x2, y2);
      final rrect = RRect.fromRectAndRadius(rect, const Radius.circular(8));
      canvas.drawRRect(rrect, greenPaint);

      // Điểm chân màu xanh
      final footX = (x1 + x2) / 2;
      final footY = y2;
      canvas.drawCircle(Offset(footX, footY), 4, Paint()..color = Colors.green..style = PaintingStyle.fill);

      final double confidence = person['confidence'] ?? 0.0;
      final String labelText = "PERSON ${(confidence * 100).toStringAsFixed(0)}%";

      final textPainter = TextPainter(
        text: TextSpan(
          text: labelText,
          style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();

      final backgroundRect = Rect.fromLTWH(
        x1, y1 - textPainter.height - 4,
        textPainter.width + 8, textPainter.height + 4,
      );
      canvas.drawRect(backgroundRect, greenBgPaint);
      textPainter.paint(canvas, Offset(x1 + 4, y1 - textPainter.height - 2));
    }

    // 2. Vẽ người trong ROI (màu đỏ)
    if (intruders.isEmpty) return;

    final redPaint = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final redBgPaint = Paint()
      ..color = Colors.red.withOpacity(0.8)
      ..style = PaintingStyle.fill;

    for (var intruder in intruders) {
      final bbox = intruder['bbox'] as List<dynamic>;
      if (bbox.length < 4) continue;

      final double x1 = bbox[0] * frameSize.width;
      final double y1 = bbox[1] * frameSize.height;
      final double x2 = bbox[2] * frameSize.width;
      final double y2 = bbox[3] * frameSize.height;

      final rect = Rect.fromLTRB(x1, y1, x2, y2);
      final rrect = RRect.fromRectAndRadius(rect, const Radius.circular(8));
      canvas.drawRRect(rrect, redPaint);

      // Điểm chân màu đỏ
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
        x1, y1 - textPainter.height - 4,
        textPainter.width + 8, textPainter.height + 4,
      );
      canvas.drawRect(backgroundRect, redBgPaint);
      textPainter.paint(canvas, Offset(x1 + 4, y1 - textPainter.height - 2));
    }
  }

  bool _isPersonInIntruders(Map<String, dynamic> person) {
    if (intruders.isEmpty) return false;
    // So sánh bằng bbox coordinates
    final personBbox = person['bbox'] as List<dynamic>;
    for (var intruder in intruders) {
      final intruderBbox = intruder['bbox'] as List<dynamic>;
      if (personBbox[0] == intruderBbox[0] &&
          personBbox[1] == intruderBbox[1] &&
          personBbox[2] == intruderBbox[2] &&
          personBbox[3] == intruderBbox[3]) {
        return true;
      }
    }
    return false;
  }

  @override
  bool shouldRepaint(covariant LiveBboxPainter oldDelegate) {
    return oldDelegate.intruders != intruders ||
        oldDelegate.allPeople != allPeople ||
        oldDelegate.frameSize != frameSize;
  }
}