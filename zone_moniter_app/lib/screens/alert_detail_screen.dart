import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:video_player/video_player.dart';
import '../models/alert_model.dart';
import '../services/api_service.dart';
import '../config/app_config.dart';

class AlertDetailScreen extends StatefulWidget {
  final String alertId;
  const AlertDetailScreen({super.key, required this.alertId});
  @override
  State<AlertDetailScreen> createState() => _AlertDetailScreenState();
}

class _AlertDetailScreenState extends State<AlertDetailScreen> {
  AlertModel? _alert;
  bool _isLoading = true;
  VideoPlayerController? _videoCtrl;

  @override
  void initState() { super.initState(); _loadDetail(); }

  Future<void> _loadDetail() async {
    try {
      final data = await ApiService.instance.getAlertDetails(widget.alertId);
      if (mounted) { setState(() { _alert = data; _isLoading = false; }); _initVideo(); }
    } catch (_) { if (mounted) setState(() => _isLoading = false); }
  }

  Future<void> _initVideo() async {
    if (_alert?.videoUrl == null) return;
    final url = _alert!.videoUrl!.startsWith('http') ? _alert!.videoUrl! : '${AppConfig.baseUrl}${_alert!.videoUrl}';
    _videoCtrl = VideoPlayerController.networkUrl(Uri.parse(url))..initialize().then((_) {
      if (mounted) { setState(() {}); _videoCtrl!.play(); _videoCtrl!.setLooping(true); }
    });
  }

  @override
  void dispose() { _videoCtrl?.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Chi tiết sự kiện')),
      body: _isLoading ? const Center(child: CircularProgressIndicator()) : _alert == null ? const Center(child: Text('Lỗi tải dữ liệu')) : SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity, height: 250, color: Colors.black,
              child: _videoCtrl != null && _videoCtrl!.value.isInitialized ? AspectRatio(aspectRatio: _videoCtrl!.value.aspectRatio, child: VideoPlayer(_videoCtrl!)) : _alert!.thumbnailUrl != null ? Image.network('${AppConfig.baseUrl}${_alert!.thumbnailUrl}', fit: BoxFit.contain) : const Center(child: Icon(Icons.image_not_supported, color: Colors.white24, size: 50)),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('THÔNG TIN XÂM NHẬP', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                  const SizedBox(height: 16),
                  _buildInfoRow(Icons.location_on, 'Vùng cấm', _alert!.zoneName),
                  const Divider(color: Colors.white10, height: 32),
                  _buildInfoRow(Icons.access_time, 'Thời gian', DateFormat('HH:mm:ss - dd/MM/yyyy').format(_alert!.detectedAt.toLocal())),
                  const Divider(color: Colors.white10, height: 32),
                  _buildInfoRow(Icons.person, 'Đối tượng', '${_alert!.objectCount} người'),
                ],
              ),
            )
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Row(children: [Icon(icon, color: Colors.white54, size: 28), const SizedBox(width: 16), Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: const TextStyle(color: Colors.white54, fontSize: 13)), Text(value, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600))])]);
  }
}