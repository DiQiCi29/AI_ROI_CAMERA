import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../config/app_config.dart';
import '../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _serverCtrl = TextEditingController(text: AppConfig.baseUrl);

  void _saveServer() async {
    final newUrl = _serverCtrl.text.trim();
    if (newUrl.isEmpty) return;

    AppConfig.baseUrl = newUrl;
    ApiService.instance.updateBaseUrl(newUrl);
    await ApiService.saveBaseUrl(newUrl);
    
    // Reconnect WebSocket and reload data with new IP
    if (mounted) {
      context.read<AppProvider>().reconnectAll();
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã lưu và kết nối lại với máy chủ mới')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.read<AppProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Cài đặt', style: TextStyle(fontWeight: FontWeight.bold))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('HỆ THỐNG', style: TextStyle(color: Colors.white54, fontSize: 13, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Địa chỉ máy chủ (API)', style: TextStyle(color: Colors.white70, fontSize: 14)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _serverCtrl,
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    decoration: InputDecoration(
                      filled: true,
                      fillColor: Colors.black26,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.save, color: Colors.blue),
                        onPressed: _saveServer,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text('Ví dụ: http://192.168.1.100:8000/api/v1', 
                    style: TextStyle(color: Colors.white24, fontSize: 12)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          const Text('TÀI KHOẢN', style: TextStyle(color: Colors.white54, fontSize: 13, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                const ListTile(
                  leading: Icon(Icons.admin_panel_settings, color: Colors.white70), 
                  title: Text('Tài khoản quản trị', style: TextStyle(color: Colors.white)), 
                  subtitle: Text('admin', style: TextStyle(color: Colors.white38))
                ),
                const Divider(color: Colors.white10, height: 1),
                ListTile(
                  leading: const Icon(Icons.logout, color: Colors.redAccent),
                  title: const Text('Đăng xuất', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
                  onTap: () async {
                    final confirm = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('Đăng xuất'),
                        content: const Text('Bạn có chắc chắn muốn đăng xuất không?'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Hủy')),
                          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Đăng xuất')),
                        ],
                      ),
                    );
                    if (confirm == true) provider.logout();
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 40),
          const Center(child: Text('Zone Monitor v1.1.0', style: TextStyle(color: Colors.white24)))
        ],
      ),
    );
  }

  @override
  void dispose() {
    _serverCtrl.dispose();
    super.dispose();
  }
}
