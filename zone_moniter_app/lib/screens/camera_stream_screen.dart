import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import 'package:http/http.dart' as http;
import '../providers/app_provider.dart';
import '../services/api_service.dart';
import '../config/app_config.dart';
import '../widgets/zone_painter.dart';
import '../services/websocket_service.dart';
import 'zone_draw_screen.dart';

enum StreamMode { webrtc, ai }

class CameraStreamScreen extends StatefulWidget {
  const CameraStreamScreen({super.key});
  @override
  State<CameraStreamScreen> createState() => _CameraStreamScreenState();
}

class _CameraStreamScreenState extends State<CameraStreamScreen> {
  late final WebViewController _webController;
  
  Uint8List? _currentAiFrame;
  StreamSubscription? _aiStreamSub;
  
  StreamMode _mode = StreamMode.ai; 
  bool _isLoading = true;
  bool _showZones = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initWebViewController();
    _setupWebSocket();
    _startStream();
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

  void _startStream() {
    if (_mode == StreamMode.webrtc) {
      _loadWebRTC();
      _stopAiStream();
    } else {
      _startAiStream();
    }
  }

  void _loadWebRTC() {
    setState(() => _isLoading = true);
    final cameraName = "camera_01"; 
    final url = AppConfig.webrtcPage(cameraName);
    debugPrint("Loading WebRTC URL: $url");
    _webController.loadRequest(Uri.parse(url));
  }

  Future<void> _startAiStream() async {
    _stopAiStream();
    setState(() { _isLoading = true; _error = null; });
    
    try {
      final token = await ApiService.getToken();
      final cameraId = context.read<AppProvider>().currentCameraId ?? "1";
      final url = "${AppConfig.aiStream}?camera_id=$cameraId";
      
      final request = http.Request('GET', Uri.parse(url));
      request.headers['Authorization'] = 'Bearer $token';

      final client = http.Client();
      final response = await client.send(request).timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        setState(() { _error = 'AI Stream Offline (HTTP ${response.statusCode})'; _isLoading = false; });
        return;
      }

      final List<int> buffer = [];
      _aiStreamSub = response.stream.listen(
        (chunk) {
          buffer.addAll(chunk);
          _extractAiFrames(buffer);
        },
        onError: (e) => _onAiError(e.toString()),
        onDone: () => _onAiError('AI Stream Closed'),
      );
      setState(() => _isLoading = false);
    } catch (e) {
      setState(() { _error = 'Không thể kết nối Backend (Port 8000): $e'; _isLoading = false; });
    }
  }

  void _extractAiFrames(List<int> buffer) {
    const jpegStart = [0xFF, 0xD8];
    const jpegEnd   = [0xFF, 0xD9];
    int lastEnd = -1;
    int lastStart = -1;

    for (int i = buffer.length - 2; i >= 0; i--) {
      if (lastEnd == -1 && buffer[i] == jpegEnd[0] && buffer[i + 1] == jpegEnd[1]) {
        lastEnd = i + 2;
      } else if (lastEnd != -1 && buffer[i] == jpegStart[0] && buffer[i + 1] == jpegStart[1]) {
        lastStart = i;
        break; 
      }
    }

    if (lastStart != -1 && lastEnd != -1) {
      final frame = Uint8List.fromList(buffer.sublist(lastStart, lastEnd));
      buffer.removeRange(0, lastEnd);
      if (mounted) setState(() => _currentAiFrame = frame);
    }

    if (buffer.length > 3 * 1024 * 1024) buffer.clear();
  }

  void _onAiError(String msg) {
    if (!mounted || _mode != StreamMode.ai) return;
    debugPrint("AI Stream Error: $msg");
    setState(() => _error = "Lỗi luồng AI. Đang thử lại...");
    Future.delayed(const Duration(seconds: 5), _startAiStream);
  }

  void _stopAiStream() {
    _aiStreamSub?.cancel();
    _aiStreamSub = null;
    _currentAiFrame = null;
  }

  @override
  void dispose() {
    _stopAiStream();
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
              setState(() => _isLoading = true);
              
              // Lấy camera_id từ provider
              final cameraIdStr = provider.currentCameraId ?? "1";
              final cameraIdInt = int.tryParse(cameraIdStr) ?? 1;

              // Ưu tiên dùng frame hiện tại nếu có, nếu không thì gọi API snapshot
              Uint8List? snapshot = _currentAiFrame;
              if (snapshot == null) {
                snapshot = await ApiService.instance.getSnapshot(cameraId: cameraIdInt);
              }
              
              if (!mounted) return;
              setState(() => _isLoading = false);

              if (snapshot == null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Lỗi: Không thể lấy ảnh snapshot từ server'))
                );
                return;
              }

              await Navigator.push(context, MaterialPageRoute(builder: (_) => ZoneDrawScreen(
                currentFrame: snapshot, 
                existingZones: zones,
                cameraId: cameraIdStr,
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
                      : _mode == StreamMode.webrtc 
                          ? WebViewWidget(controller: _webController)
                          : _currentAiFrame == null 
                              ? const CircularProgressIndicator()
                              : Image.memory(_currentAiFrame!, gaplessPlayback: true, fit: BoxFit.contain),
                ),
                
                if (_isLoading) const Center(child: CircularProgressIndicator()),

                // ROI Zones Overlay (Chỉ vẽ thủ công nếu ở mode WebRTC, MJPEG AI thường đã vẽ sẵn từ server)
                if (_showZones && _mode == StreamMode.webrtc) 
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

                Positioned(bottom: 12, right: 12, child: _buildModeSelector()),
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
            label: const Text('Thử lại AI View'), 
            onPressed: () => setState(() { _mode = StreamMode.ai; _error = null; _startStream(); })
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
          Text(_mode == StreamMode.webrtc ? 'WEBRTC (TỐC ĐỘ CAO)' : 'AI VIEW (VẼ KHUNG NHẬN DIỆN)', 
            style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold)
          )
        ]
      )
    );
  }

  Widget _buildModeSelector() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: Colors.black45, borderRadius: BorderRadius.circular(30)),
      child: Row(
        children: [
          _modeButton(StreamMode.ai, "AI View"),
          _modeButton(StreamMode.webrtc, "WebRTC"),
        ],
      ),
    );
  }

  Widget _modeButton(StreamMode mode, String label) {
    final isSelected = _mode == mode;
    return GestureDetector(
      onTap: () {
        if (isSelected) return;
        setState(() {
          _mode = mode;
          _error = null;
          _startStream();
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF1565C0) : Colors.transparent,
          borderRadius: BorderRadius.circular(25),
        ),
        child: Text(label, style: TextStyle(color: isSelected ? Colors.white : Colors.white60, fontSize: 12, fontWeight: FontWeight.bold)),
      ),
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
