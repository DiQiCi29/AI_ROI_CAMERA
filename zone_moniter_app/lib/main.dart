// lib/main.dart

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';
import 'providers/app_provider.dart';
import 'screens/login_screen.dart';
import 'screens/main_screen.dart';
import 'services/notification_service.dart';

final GlobalKey<ScaffoldMessengerState> rootScaffoldMessengerKey =
GlobalKey<ScaffoldMessengerState>();

class AppTheme {
  static const Color primaryColor = Color(0xFF0D47A1);
  static const Color bgColor = Color(0xFF0A0A0F);
  static const Color cardColor = Color(0xFF141420);
  static const Color borderColor = Color(0xFF252535);

  static ThemeData get darkTheme {
    return ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryColor,
        brightness: Brightness.dark,
      ),
      useMaterial3: true,
      scaffoldBackgroundColor: bgColor,
      cardTheme: CardThemeData(
        color: cardColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: borderColor, width: 0.5),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: bgColor,
        elevation: 0,
        centerTitle: false,
      ),
    );
  }
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // FIX: Bỏ comment — khởi tạo Firebase + Notification
  try {
    await Firebase.initializeApp();
    await NotificationService.initialize();
  } catch (e) {
    // Vẫn chạy app nếu Firebase lỗi (thiếu google-services.json)
    debugPrint('⚠️ Firebase init failed: $e');
  }

  runApp(const ZoneMonitorApp());
}

class ZoneMonitorApp extends StatelessWidget {
  const ZoneMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppProvider(),
      child: MaterialApp(
        title: 'Zone Monitor',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        scaffoldMessengerKey: rootScaffoldMessengerKey,
        home: const _AuthGate(),
      ),
    );
  }
}

class _AuthGate extends StatefulWidget {
  const _AuthGate();

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    try {
      await context.read<AppProvider>().loadSavedToken();
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(color: AppTheme.primaryColor),
        ),
      );
    }

    return Consumer<AppProvider>(
      builder: (context, provider, _) {
        return AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: provider.isLoggedIn
              ? const MainScreen(key: ValueKey('main'))
              : const LoginScreen(key: ValueKey('login')),
        );
      },
    );
  }
}