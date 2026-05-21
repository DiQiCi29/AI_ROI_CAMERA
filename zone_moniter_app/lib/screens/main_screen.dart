// lib/screens/main_screen.dart

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import 'dashboard_screen.dart';
import 'camera_stream_screen.dart';
import 'zone_list_screen.dart';
import 'alert_list_screen.dart';
import 'settings_screen.dart';
import '../widgets/intrusion_overlay.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    DashboardScreen(),
    CameraStreamScreen(),
    ZoneListScreen(),
    AlertListScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, provider, child) {
        return Stack(
          children: [
            Scaffold(
              body: IndexedStack(
                index: _currentIndex,
                children: _screens,
              ),
              bottomNavigationBar: NavigationBar(
                selectedIndex: _currentIndex,
                backgroundColor: const Color(0xFF0D0D1A),
                indicatorColor: const Color(0xFF1565C0).withOpacity(0.3),
                onDestinationSelected: (i) =>
                    setState(() => _currentIndex = i),
                destinations: [
                  const NavigationDestination(
                    icon: Icon(Icons.dashboard_outlined),
                    selectedIcon: Icon(Icons.dashboard),
                    label: 'Dashboard',
                  ),
                  const NavigationDestination(
                    icon: Icon(Icons.videocam_outlined),
                    selectedIcon: Icon(Icons.videocam),
                    label: 'Camera',
                  ),
                  const NavigationDestination(
                    icon: Icon(Icons.crop_free_outlined),
                    selectedIcon: Icon(Icons.crop_free),
                    label: 'Vùng cấm',
                  ),
                  NavigationDestination(
                    icon: Badge(
                      isLabelVisible: provider.unreadCount > 0,
                      label: Text('${provider.unreadCount}'),
                      child: const Icon(Icons.notifications_outlined),
                    ),
                    selectedIcon: Badge(
                      isLabelVisible: provider.unreadCount > 0,
                      label: Text('${provider.unreadCount}'),
                      child: const Icon(Icons.notifications),
                    ),
                    label: 'Cảnh báo',
                  ),
                  const NavigationDestination(
                    icon: Icon(Icons.settings_outlined),
                    selectedIcon: Icon(Icons.settings),
                    label: 'Cài đặt',
                  ),
                ],
              ),
            ),

            // Intrusion alert overlay (hiện lên khi có xâm nhập)
            if (provider.hasActiveAlert)
              IntrusionOverlay(
                alertData: provider.activeAlert!,
                onDismiss: () => provider.dismissActiveAlert(),
                onViewDetail: () {
                  provider.dismissActiveAlert();
                  setState(() => _currentIndex = 3); // Chuyển sang tab Alerts
                },
              ),
          ],
        );
      },
    );
  }
}