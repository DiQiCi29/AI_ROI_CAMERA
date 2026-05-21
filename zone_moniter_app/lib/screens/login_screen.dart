// lib/screens/login_screen.dart

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../config/app_config.dart';
import '../services/api_service.dart'; // Added

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameCtrl = TextEditingController(text: 'admin');
  final _passwordCtrl = TextEditingController();
  final _serverCtrl   = TextEditingController(text: AppConfig.baseUrl);
  bool _loading = false;
  bool _obscure = true;
  String? _error;

  Future<void> _login() async {
    setState(() { _loading = true; _error = null; });

    try {
      // Cập nhật server URL nếu người dùng thay đổi
      final newUrl = _serverCtrl.text.trim();
      AppConfig.baseUrl = newUrl;
      ApiService.instance.updateBaseUrl(newUrl); // Thêm dòng này

      await context.read<AppProvider>().login(
        _usernameCtrl.text.trim(),
        _passwordCtrl.text.trim(),
      );
    } catch (e) {
      if (mounted) {
        ApiErrorHandler.handleError(context, e);
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    } finally {
      if (mounted) {
        setState(() { _loading = false; });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo
                Container(
                  width: 80, height: 80,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1565C0),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Icon(Icons.videocam_rounded,
                      size: 44, color: Colors.white),
                ),
                const SizedBox(height: 24),
                Text('Zone Monitor',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    )),
                const SizedBox(height: 6),
                Text('Hệ thống giám sát vùng cấm',
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: Colors.white54)),
                const SizedBox(height: 40),

                // Server URL
                _buildField(
                  controller: _serverCtrl,
                  label: 'Server URL',
                  hint: '192.168.1.100:8000',
                  icon: Icons.dns_rounded,
                ),
                const SizedBox(height: 14),

                // Username
                _buildField(
                  controller: _usernameCtrl,
                  label: 'Tên đăng nhập',
                  hint: 'admin',
                  icon: Icons.person_rounded,
                ),
                const SizedBox(height: 14),

                // Password
                _buildField(
                  controller: _passwordCtrl,
                  label: 'Mật khẩu',
                  hint: '••••••••',
                  icon: Icons.lock_rounded,
                  obscure: _obscure,
                  suffixIcon: IconButton(
                    icon: Icon(
                        _obscure ? Icons.visibility_off : Icons.visibility,
                        color: Colors.white38),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),

                if (_error != null) ...[
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.red.withOpacity(0.3)),
                    ),
                    child: Row(children: [
                      const Icon(Icons.error_outline, color: Colors.red, size: 18),
                      const SizedBox(width: 8),
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                    ]),
                  ),
                ],

                const SizedBox(height: 28),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1565C0),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: _loading ? null : _login,
                    child: _loading
                        ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white))
                        : const Text('Đăng nhập',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w600)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    bool obscure = false,
    Widget? suffixIcon,
  }) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        hintStyle: const TextStyle(color: Colors.white24),
        labelStyle: const TextStyle(color: Colors.white54),
        prefixIcon: Icon(icon, color: Colors.white38),
        suffixIcon: suffixIcon,
        filled: true,
        fillColor: const Color(0xFF141420),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF252535)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF252535)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF1565C0)),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    _serverCtrl.dispose();
    super.dispose();
  }
}