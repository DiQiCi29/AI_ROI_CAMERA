import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../models/alert_model.dart';
import '../services/api_service.dart';
import '../config/app_config.dart';
import '../providers/app_provider.dart';
import 'alert_detail_screen.dart';

class AlertListScreen extends StatefulWidget {
  const AlertListScreen({super.key});
  @override
  State<AlertListScreen> createState() => _AlertListScreenState();
}

class _AlertListScreenState extends State<AlertListScreen> {
  List<AlertModel> _alerts = [];
  bool _isLoading = true;

  @override
  void initState() { super.initState(); _fetchAlerts(); }

  Future<void> _fetchAlerts() async {
    setState(() => _isLoading = true);
    try {
      final data = await ApiService.instance.getAlerts(limit: 50);
      final items = (data['alerts'] as List).map((e) => AlertModel.fromJson(e)).toList();
      if (mounted) { setState(() { _alerts = items; _isLoading = false; }); context.read<AppProvider>().refreshUnreadCount(); }
    } catch (_) { if (mounted) setState(() => _isLoading = false); }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Lịch Sử Cảnh Báo', style: TextStyle(fontWeight: FontWeight.bold))),
      body: _isLoading ? const Center(child: CircularProgressIndicator()) : RefreshIndicator(
        onRefresh: _fetchAlerts,
        child: ListView.separated(
          padding: const EdgeInsets.all(12), itemCount: _alerts.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final alert = _alerts[index];
            return Card(
              color: alert.isRead ? const Color(0xFF141420) : const Color(0xFF2A1A1A),
              child: ListTile(
                leading: Container(width: 60, height: 60, color: Colors.black26, child: alert.thumbnailUrl != null ? Image.network('${AppConfig.baseUrl}${alert.thumbnailUrl}', fit: BoxFit.cover, errorBuilder: (_,__,___) => const Icon(Icons.broken_image)) : const Icon(Icons.warning, color: Colors.red)),
                title: Text(alert.zoneName, style: TextStyle(fontWeight: alert.isRead ? FontWeight.normal : FontWeight.bold, color: Colors.white)),
                subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const SizedBox(height: 4), Text(DateFormat('HH:mm:ss - dd/MM/yyyy').format(alert.detectedAt.toLocal()), style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 12))]),
                trailing: alert.isRead ? null : const CircleAvatar(radius: 5, backgroundColor: Colors.red),
                onTap: () async {
                  if (!alert.isRead) await ApiService.instance.markAlertAsRead(alert.alertId);
                  if (mounted) await Navigator.push(context, MaterialPageRoute(builder: (_) => AlertDetailScreen(alertId: alert.alertId)));
                  _fetchAlerts();
                },
              ),
            );
          },
        ),
      ),
    );
  }
}