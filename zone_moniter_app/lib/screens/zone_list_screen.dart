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
    // Gọi tải dữ liệu mỗi khi màn hình này được mở
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppProvider>().loadZones();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Quản lý Vùng Cấm', style: TextStyle(fontWeight: FontWeight.bold))),
      body: Consumer<AppProvider>(
        builder: (context, provider, child) {
          // Hiển thị loading nếu đang tải
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (provider.zones.isEmpty) {
            return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [const Icon(Icons.crop_free_rounded, size: 80, color: Colors.white24), const SizedBox(height: 16), const Text('Chưa có vùng cấm nào', style: TextStyle(color: Colors.white54, fontSize: 16))]));
          }

          return RefreshIndicator(
            onRefresh: provider.loadZones,
            child: ListView.separated(
              padding: const EdgeInsets.all(16), itemCount: provider.zones.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final zone = provider.zones[index];
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(zone.isActive ? Icons.shield : Icons.shield_outlined, color: zone.isActive ? Colors.red : Colors.grey), const SizedBox(width: 12),
                            Expanded(child: Text(zone.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white))),
                            Switch(value: zone.isActive, activeColor: Colors.red, onChanged: (val) => provider.toggleZone(zone.zoneId)),
                          ],
                        ),
                        const Divider(color: Colors.white10, height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Ngày tạo: ${DateFormat('dd/MM/yyyy').format(zone.createdAt.toLocal())}', style: const TextStyle(color: Colors.white54, fontSize: 12)), const SizedBox(height: 4), Text('Số điểm: ${zone.coordinates.length}', style: const TextStyle(color: Colors.white54, fontSize: 12))]),
                            IconButton(icon: const Icon(Icons.delete_outline, color: Colors.redAccent), onPressed: () => provider.deleteZone(zone.zoneId)),
                          ],
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