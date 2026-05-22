// lib/screens/camera_stream_screen.dart

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:video_player/video_player.dart';
import '../providers/app_provider.dart';
import '../widgets/zone_painter.dart';
import 'zone_draw_screen.dart';
import '../widgets/live_bbox_overlay.dart';
import '../config/app_config.dart';

class CameraStreamScreen extends StatefulWidget {
  const CameraStreamScreen({super.key});
  @override
  State<CameraStreamScreen> createState() => _CameraStreamScreenState();
}

class _CameraStreamScreenState extends State<CameraStreamScreen> {
  // WebRTC (primary)
  WebViewController? _webController;
  // HLS (fallback)
  VideoPlayerController? _videoCtrl;
  bool _isLoading = true;
  bool _showZones = true;
  String? _error;
  String? _streamMode; // "WEBRTC" or "HLS"
  Timer? _webrtcTimeout;

  @override
  void initState() {
    super.initState();
    _tryWebRTCFirst();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppProvider>().loadZones();
    });
  }

  void _tryWebRTCFirst() {
    final provider = context.read<AppProvider>();
    final camId = provider.currentCameraId ?? "1";
    final webrtcBase = AppConfig.webrtcBaseUrl;
    final webrtcUrl = "$webrtcBase/camera_${camId.padLeft(2, '0')}/whep";

    debugPrint("[STREAM] ▶️ Trying WebRTC: $webrtcUrl");

    _webController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.black)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) => _isLoading = true,
          onPageFinished: (_) {
            // WebRTC page loaded, wait 10s for video to start
            _webrtcTimeout = Timer(const Duration(seconds: 10), () {
              _webController?.runJavaScriptReturningResult('document.title').then((result) {
                final title = result.toString().replaceAll('"', '');
                if (title == 'WEBRTC_FAILED' || title == 'WEBRTC_STALLED') {
                  debugPrint("[STREAM] ⚠️ WebRTC failed/stalled → FALLBACK to HLS");
                  _fallbackToHls();
                } else {
                  // WebRTC seems OK
                  setState(() {
                    _isLoading = false;
                    _streamMode = "WEBRTC";
                  });
                  debugPrint("[STREAM] ✅ WebRTC connected");
                }
              }).catchError((_) { 
                _fallbackToHls(); 
              });
            });
          },
          onWebResourceError: (err) {
            debugPrint("[STREAM] ⚠️ WebRTC resource error: ${err.description} → FALLBACK to HLS");
            _fallbackToHls();
          },
        ),
      );

    _webController!.loadHtmlString('''
      <!DOCTYPE html>
      <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
          body, html { margin: 0; padding: 0; width: 100%; height: 100%; background: black; overflow: hidden; }
          video { width: 100%; height: 100%; object-fit: contain; }
        </style>
      </head>
      <body>
        <video id="video" autoplay muted playsinline></video>
        <script>
          async function startWebRTC() {
            try {
              const pc = new RTCPeerConnection();
              pc.ontrack = (event) => {
                const video = document.getElementById('video');
                if (video.srcObject !== event.streams[0]) {
                  video.srcObject = event.streams[0];
                }
              };
              pc.addTransceiver('video', { direction: 'recvonly' });
              await pc.setLocalDescription(await pc.createOffer());
              const res = await fetch('$webrtcUrl', {
                method: 'POST',
                body: pc.localDescription.sdp,
                headers: { 'Content-Type': 'application/sdp' }
              });
              if (!res.ok) throw new Error('WHEP response: ' + res.status);
              const sdp = await res.text();
              await pc.setRemoteDescription({ type: 'answer', sdp: sdp });
            } catch(e) {
              console.error('WebRTC error:', e);
              document.title = 'WEBRTC_FAILED';
            }
          }
          startWebRTC();
          setInterval(() => {
            const video = document.getElementById('video');
            if (video && video.readyState < 2 && document.title !== 'WEBRTC_FAILED') {
              document.title = 'WEBRTC_STALLED';
            }
          }, 5000);
        </script>
      </body>
      </html>
    ''');
  }

  void _fallbackToHls() {
    _webrtcTimeout?.cancel();
    _webController = null; // release WebRTC

    debugPrint("[STREAM] ▶️ FALLBACK to HLS...");

    final provider = context.read<AppProvider>();
    final camId = provider.currentCameraId ?? "1";
    final host = Uri.parse(AppConfig.baseUrl).host;
    final hlsUrl = "http://$host:8888/camera_${camId.padLeft(2, '0')}/index.m3u8";

    debugPrint("[STREAM] 🔄 FALLBACK to HLS: $hlsUrl");

    _videoCtrl = VideoPlayerController.networkUrl(Uri.parse(hlsUrl));
    _videoCtrl!.initialize().then((_) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _streamMode = "HLS";
      });
      _videoCtrl!.setLooping(true);
      _videoCtrl!.setVolume(0);
      _videoCtrl!.play();
      debugPrint("[STREAM] ✅ FALLBACK HLS connected");
    }).catchError((err) {
      debugPrint("[STREAM] ❌ HLS also failed: $err");
      if (!mounted) return;
      setState(() {
        _error = "Không thể kết nối luồng video";
        _isLoading = false;
      });
    });
  }

  @override
  void dispose() {
    _webrtcTimeout?.cancel();
    _webController = null;
    _videoCtrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    final zones = provider.zones;
    final isHlsReady = _videoCtrl != null && _videoCtrl!.value.isInitialized;
    final useWebRtc = _webController != null && _streamMode == "WEBRTC";

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
                if (!mounted || !context.mounted) return;
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
              child: AspectRatio(
                aspectRatio: 16 / 9,
                child: Stack(
                  children: [
                    Center(
                      child: _error != null
                          ? Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.videocam_off, color: Colors.white38, size: 48),
                          const SizedBox(height: 8),
                          Text(_error!, style: const TextStyle(color: Colors.white54)),
                          const SizedBox(height: 8),
                          Text(Uri.parse(AppConfig.baseUrl).host, style: const TextStyle(color: Colors.white24, fontSize: 11)),
                        ],
                      )
                          : useWebRtc
                              ? WebViewWidget(controller: _webController!)
                              : isHlsReady
                                  ? VideoPlayer(_videoCtrl!)
                                  : const Center(child: CircularProgressIndicator()),
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
                    if (provider.hasActiveBbox || provider.detectedAllPeople.isNotEmpty)
                      Positioned.fill(
                        child: IgnorePointer(
                          child: LayoutBuilder(builder: (_, constraints) {
                            final intruders = provider.activeAlert?['intruders'] as List? ?? [];
                            final allPeople = provider.detectedAllPeople;
                            return CustomPaint(
                              painter: LiveBboxPainter(
                                intruders: intruders,
                                allPeople: allPeople,
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
    final mode = _streamMode ?? "CONNECTING";
    return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(15)),
        child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(width: 8, height: 8, decoration: BoxDecoration(color: online ? Colors.green : Colors.red, shape: BoxShape.circle)),
              const SizedBox(width: 6),
              Text('LIVE - $mode', style: TextStyle(color: online ? Colors.green : Colors.red, fontSize: 11, fontWeight: FontWeight.bold))
            ]
        )
    );
  }

  Widget _buildZoneFooter(List zones) {
    return Container(
      height: 90, color: const Color(0xFF0D0D1A),
      child: zones.isEmpty
          ? const Center(child: Text('Chưa có vùng cấm', style: TextStyle(color: Colors.white38)))
          : ListView.builder(
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