import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/app_provider.dart';
import '../services/api_service.dart';
import '../models/alert_model.dart';
import '../config/app_config.dart';
import 'alert_detail_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _stats;
  List<AlertModel> _recentAlerts = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final provider = context.read<AppProvider>();
    try {
      await Future.wait([
        ApiService.instance.getStats().then((data) => _stats = data),
        ApiService.instance.getAlerts(limit: 5).then((data) {
          _recentAlerts = (data['alerts'] as List).map((e) => AlertModel.fromJson(e)).toList();
        }),
        provider.refreshCameraStatus(),
        provider.loadZones(),
      ]);

      if (mounted) {
        setState(() { _loading = false; });
      }
    } catch (e) {
      debugPrint('Dashboard load error: $e');
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () {
              setState(() => _loading = true);
              _loadData();
              provider.refreshCameraStatus();
            },
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. CARD HIỂN THỊ CAMERA STATUS
              _CameraStatusCard(isOnline: provider.cameraOnline),
              const SizedBox(height: 12),

              // 2. CARD ĐIỀU KHIỂN TRẠNG THÁI GIÁM SÁT (MONITORING SWITCH)
              Card(
                color: provider.isMonitoring ? Colors.blueGrey.withOpacity(0.2) : Colors.amber.withOpacity(0.1),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: BorderSide(color: provider.isMonitoring ? Colors.blue.withOpacity(0.3) : Colors.amber.withOpacity(0.4))
                ),
                child: SwitchListTile(
                  title: Text(
                    provider.isMonitoring ? 'Chế độ giám sát: ĐANG BẬT' : 'Chế độ giám sát: TẠM DỪNG',
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: provider.isMonitoring ? Colors.greenAccent : Colors.amberAccent
                    ),
                  ),
                  subtitle: Text(
                    provider.isMonitoring
                        ? 'Hệ thống đang bảo vệ vùng cấm, sẵn sàng kích hoạt còi báo động.'
                        : 'AI vẫn vẽ khung nhưng còi đèn, thông báo đẩy FCM đã bị vô hiệu hóa.',
                    style: const TextStyle(fontSize: 12, color: Colors.white60),
                  ),
                  value: provider.isMonitoring,
                  activeColor: Colors.greenAccent,
                  onChanged: provider.isLoading ? null : (bool value) {
                    provider.toggleMonitoringMode();
                  },
                  secondary: Icon(
                    provider.isMonitoring ? Icons.gpp_good_rounded : Icons.gpp_maybe_rounded,
                    color: provider.isMonitoring ? Colors.greenAccent : Colors.amberAccent,
                    size: 30,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // 3. THỐNG KÊ SỐ LIỆU (Trả lại phần bị lỗi cú pháp trước đó)
              if (_stats != null) ...[
                const Text('Thống kê hôm nay', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white70)),
                const SizedBox(height: 10),
                  GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 1.4,
                  children: [
                    _StatCard(icon: Icons.warning_amber_rounded, label: 'Tổng xâm nhập', value: '${_stats!['total_intrusions'] ?? 0}', color: Colors.orange),
                    _StatCard(icon: Icons.today_rounded, label: 'Hôm nay', value: '${_stats!['intrusions_today'] ?? 0}', color: Colors.redAccent),
                    _StatCard(icon: Icons.date_range_rounded, label: 'Tuần này', value: '${_stats!['intrusions_this_week'] ?? 0}', color: Colors.blue),

                    // ĐÃ THAY THẾ: Thẻ chưa đọc cũ bị lỗi hiển thị số lượng được thay bằng thẻ trạng thái hoạt động AI
                    _StatCard(
                        icon: provider.isMonitoring ? Icons.shield_rounded : Icons.shield_outlined,
                        label: 'Trạng thái AI',
                        value: provider.isMonitoring ? 'ON' : 'OFF',
                        color: provider.isMonitoring ? Colors.greenAccent : Colors.amber
                    ),
                  ],
                ),
                const SizedBox(height: 16),
              ],

              // 4. DANH SÁCH VÙNG CẤM ĐANG HOẠT ĐỘNG
              const Text('Vùng cấm đang hoạt động', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white70)),
              const SizedBox(height: 10),
              ...provider.zones.where((z) => z.isActive).map((z) => _ZoneChip(name: z.name)),
              if (provider.zones.where((z) => z.isActive).isEmpty)
                const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('Chưa có vùng cấm nào được kích hoạt', style: TextStyle(color: Colors.white38))),
              const SizedBox(height: 16),

              // 5. CẢNH BÁO GẦN ĐÂY
              const Text('Cảnh báo gần đây', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white70)),
              const SizedBox(height: 10),
              if (_recentAlerts.isEmpty)
                const Center(child: Padding(padding: EdgeInsets.all(20), child: Text('Chưa có cảnh báo nào', style: TextStyle(color: Colors.white38))))
              else
                ..._recentAlerts.map((a) => Card(
                  child: ListTile(
                    leading: Container(
                      width: 44, height: 44, decoration: BoxDecoration(color: Colors.red.withOpacity(0.15), borderRadius: BorderRadius.circular(10)),
                      child: a.thumbnailUrl != null
                          ? ClipRRect(borderRadius: BorderRadius.circular(10), child: Image.network('${AppConfig.baseUrl}${a.thumbnailUrl}', fit: BoxFit.cover, errorBuilder: (_, __, ___) => const Icon(Icons.person_rounded, color: Colors.red)))
                          : const Icon(Icons.person_rounded, color: Colors.red),
                    ),
                    title: Text(a.zoneName, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500)),
                    subtitle: Text(DateFormat('HH:mm - dd/MM/yyyy').format(a.detectedAt.toLocal()), style: const TextStyle(color: Colors.white38, fontSize: 12)),
                    trailing: a.isRead ? null : const CircleAvatar(radius: 4, backgroundColor: Colors.redAccent),
                    onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => AlertDetailScreen(alertId: a.alertId))),
                  ),
                )),
            ],
          ),
        ),
      ),
    );
  }
}

class _CameraStatusCard extends StatelessWidget {
  final bool isOnline;
  const _CameraStatusCard({required this.isOnline});
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(children: [
          Container(width: 48, height: 48, decoration: BoxDecoration(color: (isOnline ? Colors.green : Colors.red).withOpacity(0.1), shape: BoxShape.circle), child: Icon(isOnline ? Icons.videocam_rounded : Icons.videocam_off_rounded, color: isOnline ? Colors.green : Colors.red)),
          const SizedBox(width: 14),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Camera', style: TextStyle(color: Colors.white54)),
            Text(isOnline ? 'Đang hoạt động' : 'Offline', style: TextStyle(color: isOnline ? Colors.green : Colors.red, fontWeight: FontWeight.bold, fontSize: 16)),
          ]),
          const Spacer(),
          Container(width: 10, height: 10, decoration: BoxDecoration(color: isOnline ? Colors.green : Colors.red, shape: BoxShape.circle, boxShadow: [BoxShadow(color: (isOnline ? Colors.green : Colors.red).withOpacity(0.5), blurRadius: 6)])),
        ]),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon; final String label; final String value; final Color color;
  const _StatCard({required this.icon, required this.label, required this.value, required this.color});
  @override
  Widget build(BuildContext context) {
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(icon, color: color, size: 28), const Spacer(), Text(value, style: TextStyle(color: color, fontSize: 28, fontWeight: FontWeight.bold)), Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12))])));
  }
}

class _ZoneChip extends StatelessWidget {
  final String name; const _ZoneChip({required this.name});
  @override
  Widget build(BuildContext context) {
    return Container(margin: const EdgeInsets.only(bottom: 6), padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), decoration: BoxDecoration(color: Colors.green.withOpacity(0.1), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.green.withOpacity(0.3))), child: Row(children: [const Icon(Icons.shield_rounded, color: Colors.green, size: 16), const SizedBox(width: 8), Text(name, style: const TextStyle(color: Colors.green))]));
  }
}