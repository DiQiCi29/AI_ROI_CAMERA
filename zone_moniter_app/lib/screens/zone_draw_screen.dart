import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/zone_model.dart';
import '../widgets/zone_painter.dart';

class ZoneDrawScreen extends StatefulWidget {
  final Uint8List currentFrame;
  final List<ZoneModel>? existingZones;
  final String? cameraId;
  const ZoneDrawScreen({super.key, required this.currentFrame, this.existingZones, this.cameraId});
  @override
  State<ZoneDrawScreen> createState() => _ZoneDrawScreenState();
}

class _ZoneDrawScreenState extends State<ZoneDrawScreen> {
  final List<ZonePoint> _points = [];
  final _nameCtrl = TextEditingController();
  bool _isSaving = false;
  ui.Image? _imageInfo;

  @override
  void initState() {
    super.initState();
    _loadImageInfo();
  }

  Future<void> _loadImageInfo() async {
    try {
      final codec = await ui.instantiateImageCodec(widget.currentFrame);
      final frame = await codec.getNextFrame();
      if (mounted) {
        setState(() {
          _imageInfo = frame.image;
        });
      }
    } catch (e) {
      debugPrint("✗ [ZoneDraw] Lỗi decode ảnh: $e");
    }
  }

  void _handleTap(TapUpDetails details, BoxConstraints constraints) {
    // Với AspectRatio, constraints sẽ khớp với vùng hiển thị ảnh
    // Đã bỏ phép nhân * 100, giữ giá trị từ 0.0 -> 1.0
    final x = (details.localPosition.dx / constraints.maxWidth);
    final y = (details.localPosition.dy / constraints.maxHeight);
    setState(() => _points.add(ZonePoint(x: x, y: y)));
  }

  Future<void> _saveZone() async {
    if (_points.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Cần ít nhất 3 điểm để tạo vùng cấm!')));
      return;
    }

    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A24),
        title: const Text('Lưu vùng cấm', style: TextStyle(color: Colors.white)),
        content: TextField(controller: _nameCtrl, style: const TextStyle(color: Colors.white), decoration: const InputDecoration(hintText: 'Nhập tên vùng cấm...', hintStyle: TextStyle(color: Colors.white38)), autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy', style: TextStyle(color: Colors.white54))),
          ElevatedButton(onPressed: () { if (_nameCtrl.text.trim().isNotEmpty) Navigator.pop(ctx, _nameCtrl.text.trim()); }, child: const Text('Lưu')),
        ],
      ),
    );

    if (name == null || !mounted) return;

    setState(() => _isSaving = true);
    final cameraId = int.tryParse(widget.cameraId ?? "1") ?? 1;

    final data = { 
      "name": name, 
      "camera_id": cameraId,
      "zone_type": "polygon", 
      "coordinates": _points.map((p) => {"x": p.x, "y": p.y}).toList(), 
      "is_active": true, 
      "alert_cooldown_seconds": 30 
    };

    final success = await context.read<AppProvider>().createZone(data);
    setState(() => _isSaving = false);

    if (success && mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vẽ Vùng Cấm', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          if (_points.isNotEmpty) IconButton(icon: const Icon(Icons.undo), onPressed: () => setState(() => _points.removeLast())),
          if (_points.length >= 3) IconButton(icon: _isSaving ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.check, color: Colors.greenAccent), onPressed: _isSaving ? null : _saveZone),
        ],
      ),
      body: Column(
        children: [
          Container(padding: const EdgeInsets.all(12), color: const Color(0xFF1565C0).withOpacity(0.2), width: double.infinity, child: const Text('Chạm để khoanh vùng. Toạ độ tính theo % khung hình ảnh.', textAlign: TextAlign.center, style: TextStyle(color: Colors.white70, fontSize: 13))),
          Expanded(
            child: Center(
              child: _imageInfo == null 
                  ? const CircularProgressIndicator() 
                  : LayoutBuilder(builder: (context, constraints) {
                      // Tính toán tỷ lệ khung hình của ảnh
                      final imageAspectRatio = _imageInfo!.width / _imageInfo!.height;
                      
                      return AspectRatio(
                        aspectRatio: imageAspectRatio,
                        child: LayoutBuilder(builder: (context, innerConstraints) {
                          return GestureDetector(
                            onTapUp: (details) => _handleTap(details, innerConstraints),
                            child: Stack(children: [
                              Image.memory(widget.currentFrame, width: innerConstraints.maxWidth, height: innerConstraints.maxHeight, fit: BoxFit.fill),
                              Positioned.fill(
                                child: IgnorePointer(
                                  child: CustomPaint(
                                    painter: ZoneOverlayPainter(
                                      zones: widget.existingZones ?? [], 
                                      drawingPoints: _points, 
                                      frameSize: Size(innerConstraints.maxWidth, innerConstraints.maxHeight)
                                    )
                                  ),
                                )
                              ),
                            ]),
                          );
                        }),
                      );
                    }),
            ),
          ),
        ],
      ),
    );
  }
}