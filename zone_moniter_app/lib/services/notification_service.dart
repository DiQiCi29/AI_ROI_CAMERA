// lib/services/notification_service.dart

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:torch_light/torch_light.dart';

// FIX: Background handler cần gọi Firebase.initializeApp() + init local notif plugin
@pragma('vm:entry-point')
Future<void> _firebaseBackgroundHandler(RemoteMessage message) async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();

  const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
  const initSettings = InitializationSettings(android: androidInit);
  await FlutterLocalNotificationsPlugin().initialize(initSettings);

  NotificationService._showLocalNotification(
    title: message.notification?.title ?? '⚠️ Cảnh báo xâm nhập!',
    body: message.notification?.body ?? 'Phát hiện đối tượng!',
    payload: message.data['alert_id'],
  );
}

class NotificationService {
  static final FlutterLocalNotificationsPlugin _localNotif = FlutterLocalNotificationsPlugin();
  static final AudioPlayer _audioPlayer = AudioPlayer();

  static const String _channelId = 'intrusion_alert_channel';
  static const String _channelName = 'Cảnh báo xâm nhập';

  static Function(String? alertId)? onNotificationTap;

  static Future<void> initialize() async {
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidInit);

    await _localNotif.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (details) {
        onNotificationTap?.call(details.payload);
      },
    );

    // Yêu cầu quyền thông báo trên Android 13+
    await _localNotif.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    const channel = AndroidNotificationChannel(
      _channelId,
      _channelName,
      description: 'Cảnh báo khi phát hiện đối tượng xâm nhập',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
    );

    await _localNotif.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()?.createNotificationChannel(channel);

    FirebaseMessaging.onBackgroundMessage(_firebaseBackgroundHandler);
    FirebaseMessaging.onMessage.listen((message) {
      _showLocalNotification(
        title: message.notification?.title ?? '⚠️ Cảnh báo!',
        body: message.notification?.body ?? '',
        payload: message.data['alert_id'],
      );
    });
  }

  static Future<String?> getFcmToken() async {
    try {
      return await FirebaseMessaging.instance.getToken();
    } catch (e) {
      debugPrint('Lỗi lấy FCM Token: $e');
      return null;
    }
  }

  static Future<void> _showLocalNotification({required String title, required String body, String? payload}) async {
    const androidDetails = AndroidNotificationDetails(
      _channelId, _channelName,
      channelDescription: 'Cảnh báo xâm nhập vùng cấm',
      importance: Importance.max,
      priority: Priority.high,
      fullScreenIntent: true,
    );
    await _localNotif.show(DateTime.now().millisecondsSinceEpoch ~/ 1000, title, body, const NotificationDetails(android: androidDetails), payload: payload);
  }

  static Future<void> triggerAlert({String? zoneName}) async {
    await Future.wait([_playAlertSound(), _flashTorch()]);
  }

  static Future<void> _playAlertSound() async {
    try {
      await _audioPlayer.stop();
      await _audioPlayer.setVolume(1.0);
      await _audioPlayer.play(AssetSource('sounds/alert.mp3'));
    } catch (e) {
      debugPrint('Lỗi phát âm thanh: $e');
    }
  }

  static Future<void> _flashTorch() async {
    try {
      for (int i = 0; i < 5; i++) {
        await TorchLight.enableTorch();
        await Future.delayed(const Duration(milliseconds: 200));
        await TorchLight.disableTorch();
        await Future.delayed(const Duration(milliseconds: 200));
      }
    } catch (e) {
      // Bỏ qua nếu thiết bị không có đèn flash
    }
  }

  static Future<void> stopAlert() async {
    await _audioPlayer.stop();
    try {
      await TorchLight.disableTorch();
    } catch (_) {}
  }
}