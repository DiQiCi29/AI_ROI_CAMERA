import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/app_provider.dart';

class ZoneListScreen extends StatefulWidget {
  const ZoneListScreen({super.key});

  @override
  State<ZoneListScreen> createState() => _ZoneListScreenState();
}

class _ZoneListScreenState extends State<ZoneListScreen> {
  @override
  void initState() {
    super.initState();
    // Tự động đồng bộ gọi dữ liệu từ Database về khi mở trang
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppProvider>().loadZones();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Quản Lý Vùng Cấm', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: const Color(0xFF1A1A2E),
      ),
      body: Consumer<AppProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator(color: Colors.red));
          }

          if (provider.zones.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.shield_outlined, size: 64, color: Colors.white24),
                  const SizedBox(height: 16),
                  const Text('Không có vùng cấm nào trong Database', style: TextStyle(color: Colors.white54)),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => provider.loadZones(),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: provider.zones.length,
              itemBuilder: (context, index) {
                final zone = provider.zones[index];
                return Card(
                  color: const Color(0xFF161623),
                  margin: const EdgeInsets.only(bottom: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    leading: Icon(
                      zone.isActive ? Icons.shield : Icons.shield_outlined,
                      color: zone.isActive ? Colors.red : Colors.grey,
                      size: 28,
                    ),
                    title: Text(zone.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    subtitle: Text(
                      'Số điểm nút: ${zone.coordinates.length}\nNgày tạo: ${DateFormat('dd/MM/yyyy HH:mm').format(zone.createdAt.toLocal())}',
                      style: const TextStyle(color: Colors.white54, fontSize: 12),
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Switch(
                          value: zone.isActive,
                          activeColor: Colors.red,
                          onChanged: (value) => provider.toggleZone(zone.zoneId),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_sweep_outlined, color: Colors.redAccent),
                          onPressed: () => provider.deleteZone(zone.zoneId),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}