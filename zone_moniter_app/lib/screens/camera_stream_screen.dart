import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import '../providers/app_provider.dart';
import '../config/app_config.dart';
import '../widgets/zone_painter.dart';
import '../services/websocket_service.dart';
import 'zone_draw_screen.dart';

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
    _setupWebSocket();
    _loadWebRTC();
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
              _error = "WebRTC không phản hồi. Kiểm tra Firewall cổng 8889.";
              _isLoading = false;
            });
          },
        ),
      );
    
    if (_webController.platform is AndroidWebViewController) {
      (_webController.platform as AndroidWebViewController).setMediaPlaybackRequiresUserGesture(false);
    }
  }

  void _setupWebSocket() {
    WebSocketService().onCameraStatusChanged = (data) {
      if (mounted) {
        context.read<AppProvider>().refreshCameraStatus();
      }
    };
  }

  void _loadWebRTC() {
    setState(() => _isLoading = true);
    final cameraName = "camera_01"; 
    final url = AppConfig.webrtcPage(cameraName);
    debugPrint("Loading WebRTC URL: $url");
    _webController.loadRequest(Uri.parse(url));
  }

  @override
  void dispose() {
    WebSocketService().onCameraStatusChanged = null;
    super.dispose();
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
                final provider = context.read<AppProvider>();
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
            child: Stack(
              children: [
                Center(
                  child: _error != null
                      ? _buildErrorWidget()
                      : WebViewWidget(controller: _webController),
                ),
                
                if (_isLoading) const Center(child: CircularProgressIndicator()),

                // ROI Zones Overlay vẽ từ tọa độ WebSocket
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
                  
                Positioned(top: 12, left: 12, child: _buildStatusBadge()),
              ],
            ),
          ),
          _buildZoneFooter(zones),
        ],
      ),
    );
  }

  Widget _buildErrorWidget() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center, 
        children: [
          const Icon(Icons.videocam_off_rounded, color: Colors.white38, size: 64), 
          const SizedBox(height: 16), 
          Text(_error!, style: const TextStyle(color: Colors.white54), textAlign: TextAlign.center), 
          const SizedBox(height: 24), 
          ElevatedButton.icon(
            icon: const Icon(Icons.refresh), 
            label: const Text('Thử lại WebRTC'), 
            onPressed: () => setState(() { _error = null; _isLoading = true; _loadWebRTC(); })
          )
        ]
      ),
    );
  }

  Widget _buildStatusBadge() {
    final isLive = _error == null && !_isLoading;
    final color = isLive ? Colors.green : Colors.red;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5), 
      decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(20), border: Border.all(color: color, width: 1)), 
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)), 
          const SizedBox(width: 6), 
          const Text('WEBRTC (TỐC ĐỘ CAO)', 
            style: TextStyle(color: Colors.green, fontSize: 11, fontWeight: FontWeight.bold)
          )
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
          child: Column(mainAxisSize: MainAxisSize.min, children: [Icon(zones[i].isActive ? Icons.shield : Icons.shield_outlined, color: zones[i].isActive ? Colors.red : Colors.grey, size: 18), const SizedBox(height: 2), Text(zones[i].name, style: TextStyle(color: zones[i].isActive ? Colors.red : Colors.grey, fontSize: 10))]),
        ),
      ),
    );
  }
}