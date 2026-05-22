import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class IntrusionOverlay extends StatefulWidget {
  final Map<String, dynamic> alertData;
  final VoidCallback onDismiss;
  final VoidCallback onViewDetail;

  const IntrusionOverlay({super.key, required this.alertData, required this.onDismiss, required this.onViewDetail});

  @override
  State<IntrusionOverlay> createState() => _IntrusionOverlayState();
}

class _IntrusionOverlayState extends State<IntrusionOverlay> with SingleTickerProviderStateMixin {
  late AnimationController _pulseCtrl;
  late Animation<double> _pulseAnim;
  Timer? _autoTimer;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 600))..repeat(reverse: true);
    _pulseAnim = Tween<double>(begin: 0.6, end: 1.0).animate(_pulseCtrl);
    _autoTimer = Timer(const Duration(seconds: 30), widget.onDismiss);
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _autoTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final zoneName = widget.alertData['zone_name'] ?? 'Vùng cấm';
    final detectedAt = widget.alertData['detected_at'] != null
        ? DateFormat('HH:mm:ss dd/MM/yyyy').format(DateTime.parse(widget.alertData['detected_at']).toLocal())
        : '--';

    return Material(
      color: Colors.transparent,
      child: AnimatedBuilder(
        animation: _pulseAnim,
        builder: (_, __) {
          return Container(
            color: Colors.red.withOpacity(0.15 * _pulseAnim.value),
            child: Container(
              decoration: BoxDecoration(border: Border.all(color: Colors.red.withOpacity(_pulseAnim.value), width: 3)),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: double.infinity, color: Colors.red.withOpacity(0.85), padding: const EdgeInsets.symmetric(vertical: 20),
                    child: const Column(
                      children: [
                        Icon(Icons.warning_amber_rounded, color: Colors.white, size: 48),
                        SizedBox(height: 8),
                        Text('⚠ PHÁT HIỆN XÂM NHẬP!', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                      ],
                    ),
                  ),
                  Container(
                    width: double.infinity, color: const Color(0xFF1A0000), padding: const EdgeInsets.all(24),
                    child: Column(
                      children: [
                        _infoRow(Icons.location_on_rounded, 'Vùng cấm', zoneName, Colors.redAccent),
                        const SizedBox(height: 16),
                        _infoRow(Icons.access_time_rounded, 'Thời gian', detectedAt, Colors.orange),
                        const SizedBox(height: 16),
                        _infoRow(Icons.people_rounded, 'Đối tượng', '${widget.alertData['object_count'] ?? 1} người phát hiện', Colors.yellow),
                      ],
                    ),
                  ),
                  Container(
                    color: const Color(0xFF0D0000), padding: const EdgeInsets.all(20),
                    child: Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.white30), foregroundColor: Colors.white70, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                            icon: const Icon(Icons.close), label: const Text('Bỏ qua'), onPressed: widget.onDismiss,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                            icon: const Icon(Icons.remove_red_eye_rounded), label: const Text('Xem ngay'), onPressed: widget.onViewDetail,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _infoRow(IconData icon, String label, String value, Color iconColor) {
    return Row(
      children: [
        Icon(icon, color: iconColor, size: 24), const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12)),
            Text(value, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
          ],
        ),
      ],
    );
  }
}