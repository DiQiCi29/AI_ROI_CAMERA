// lib/screens/camera_stream_screen.dart

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../providers/app_provider.dart';
import '../widgets/zone_painter.dart';
import 'zone_draw_screen.dart';
import '../widgets/live_bbox_overlay.dart';

class CameraStreamScreen extends StatefulWidget {
  const CameraStreamScreen({super.key});
  @override
  State<CameraStreamScreen> createState() => _CameraStreamScreenState();
}

class _CameraStreamScreenState extends State<CameraStreamScreen> {
  late final WebViewController _webController;
  bool _isLoading = true;
  bool _showZones = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initWebViewController();
    _loadWebRTC();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppProvider>().loadZones();
    });
  }

  void _initWebViewController() {
    _webController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.black)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) => setState(() => _isLoading = true),
          onPageFinished: (_) => setState(() => _isLoading = false),
          onWebResourceError: (err) {
            debugPrint("WebView Error: ${err.description}");
            setState(() {
              _error = "Không thể kết nối luồng WebRTC Proxy";
              _isLoading = false;
            });
          },
        ),
      );
  }

  void _loadWebRTC() {
    final provider = context.read<AppProvider>();
    final camId = provider.currentCameraId ?? "1";
    final webrtcUrl = "http://127.0.0.1:8889/camera_${camId.padLeft(2, '0')}/whep";

    _webController.loadHtmlString('''
      <!DOCTYPE html>
      <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
          body, html { margin: 0; padding: 0; width: 100%; height: 100%; background: black; overflow: hidden; }
          whep-video { width: 100%; height: 100%; object-fit: contain; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/@livekit/whep-video@1.0.1/dist/index.js"></script>
      </head>
      <body>
        <video id="video" autoplay muted playsinline></video>
        <script>
          const videoElement = document.getElementById('video');
          navigator.mediaDevices.getUserMedia({ video: true }).then(() => {
             const peerConnection = new RTCPeerConnection();
             peerConnection.ontrack = (event) => {
               if (videoElement.srcObject !== event.streams[0]) {
                 videoElement.srcObject = event.streams[0];
               }
             };
             peerConnection.addTransceiver('video', { direction: 'recvonly' });
             fetch('$webrtcUrl', {
               method: 'POST',
               body: peerConnection.localDescription.sdp,
               headers: { 'Content-Type': 'application/sdp' }
             }).then(res => res.text()).then(sdp => {
               peerConnection.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: sdp }));
             });
          });
        </script>
      </body>
      </html>
    ''');
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    final zones = provider.zones;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Giám sát Camera', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        actions: [
          IconButton(
              icon: Icon(_showZones ? Icons.layers : Icons.layers_clear),
              onPressed: () => setState(() => _showZones = !_showZones)
          ),
          IconButton(
              icon: const Icon(Icons.add_location_alt_rounded),
              onPressed: () async {
                final success = await provider.fetchCameraSnapshot();

                if (!mounted) return;

                if (!success || provider.cameraSnapshotBytes == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Không thể lấy ảnh để vẽ zone!'))
                  );
                  return;
                }

                await Navigator.push(context, MaterialPageRoute(builder: (_) => ZoneDrawScreen(
                  currentFrame: provider.cameraSnapshotBytes!,
                  existingZones: provider.zones,
                  cameraId: provider.currentCameraId?.toString() ?? "1",
                )));

                provider.loadZones();
              }
          ),
        ],
      ),
      backgroundColor: Colors.black,
      body: Column(
        children: [
          Expanded(
            child: Center(
              // Đưa toàn bộ khu vực stream vào AspectRatio cố định tỷ lệ 16:9
              child: AspectRatio(
                aspectRatio: 16 / 9,
                child: Stack(
                  children: [
                    Center(
                      child: _error != null
                          ? Text(_error!, style: const TextStyle(color: Colors.white54))
                          : WebViewWidget(controller: _webController),
                    ),

                    if (_isLoading) const Center(child: CircularProgressIndicator()),

                    if (_showZones && zones.isNotEmpty)
                      Positioned.fill(
                        child: IgnorePointer(
                          child: LayoutBuilder(builder: (_, constraints) {
                            return CustomPaint(
                                painter: ZoneOverlayPainter(
                                    zones: zones,
                                    frameSize: Size(constraints.maxWidth, constraints.maxHeight)
                                )
                            );
                          }),
                        ),
                      ),

                    // Lớp trên cùng: Vẽ BBox thời gian thực
                    if (provider.hasActiveAlert)
                      Positioned.fill(
                        child: IgnorePointer(
                          child: LayoutBuilder(builder: (_, constraints) {
                            final intruders = provider.activeAlert?['intruders'] as List? ?? [];
                            return CustomPaint(
                              painter: LiveBboxPainter(
                                intruders: intruders,
                                frameSize: Size(constraints.maxWidth, constraints.maxHeight),
                              ),
                            );
                          }),
                        ),
                      ),

                    Positioned(top: 12, left: 12, child: _buildStatusBadge()),
                  ],
                ),
              ),
            ),
          ),
          _buildZoneFooter(zones),
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    final online = context.select<AppProvider, bool>((p) => p.cameraOnline);
    return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(15)),
        child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(width: 8, height: 8, decoration: BoxDecoration(color: online ? Colors.green : Colors.red, shape: BoxShape.circle)),
              const SizedBox(width: 6),
              Text(online ? 'LIVE - WEBRTC' : 'OFFLINE', style: TextStyle(color: online ? Colors.green : Colors.red, fontSize: 11, fontWeight: FontWeight.bold))
            ]
        )
    );
  }

  Widget _buildZoneFooter(List zones) {
    return Container(
      height: 90, color: const Color(0xFF0D0D1A),
      child: zones.isEmpty ? const Center(child: Text('Chưa có vùng cấm', style: TextStyle(color: Colors.white38))) : ListView.builder(
        scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(12), itemCount: zones.length,
        itemBuilder: (_, i) => Container(
          margin: const EdgeInsets.only(right: 8), padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(color: zones[i].isActive ? Colors.red.withOpacity(0.15) : Colors.grey.withOpacity(0.1), borderRadius: BorderRadius.circular(20), border: Border.all(color: zones[i].isActive ? Colors.red.withOpacity(0.4) : Colors.grey.withOpacity(0.3))),
          child: Column(mainAxisSize: MainAxisSize.min, children: [Icon(zones[i].isActive ? Icons.shield : Icons.shield_outlined, color: zones[i].isActive ? Colors.red : Colors.grey, size: 18), const SizedBox(height: 4), Text(zones[i].name, style: TextStyle(color: zones[i].isActive ? Colors.white : Colors.white38, fontSize: 12))]),
        ),
      ),
    );
  }
}