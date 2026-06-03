import 'dart:convert';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../core/api/auth_api.dart';

const String kAndroidChannelId = 'gruzz_b2b_high';
const String kAndroidChannelName = 'GruzzExpert B2B';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  await NotificationService.instance.showFromRemoteMessage(message);
}

/// FCM + системные баннеры (foreground через local_notifications, background — FCM + local).
class NotificationService {
  NotificationService._();

  static final NotificationService instance = NotificationService._();

  /// Не обращаться к [FirebaseMessaging.instance] до успешного [Firebase.initializeApp].
  FirebaseMessaging? _messaging;
  final FlutterLocalNotificationsPlugin _local = FlutterLocalNotificationsPlugin();

  AuthApi? _authApi;
  bool _initialized = false;
  bool _firebaseReady = false;

  static bool _isFirebaseNoAppError(Object e) {
    final msg = e.toString();
    return msg.contains('[core/no-app]') || msg.contains('no-app');
  }

  FirebaseMessaging? _messagingIfReady() {
    if (!_firebaseReady) return null;
    try {
      return _messaging ??= FirebaseMessaging.instance;
    } catch (e) {
      if (_isFirebaseNoAppError(e)) {
        _firebaseReady = false;
        debugPrint('[FCM] FirebaseMessaging недоступен: $e');
        return null;
      }
      rethrow;
    }
  }

  /// FCM-токен или `null`, если Firebase не настроен (вход в приложение не блокируется).
  Future<String?> _safeGetFcmToken() async {
    final messaging = _messagingIfReady();
    if (messaging == null) return null;
    try {
      return await messaging.getToken().timeout(const Duration(seconds: 8));
    } catch (e) {
      if (_isFirebaseNoAppError(e)) {
        debugPrint('[FCM] getToken пропущен (нет google-services.json): $e');
      } else {
        debugPrint('[FCM] getToken failed: $e');
      }
      return null;
    }
  }

  void Function(Map<String, dynamic> data)? onNotificationTap;

  Future<void> initialize() async {
    if (_initialized) return;
    _initialized = true;

    try {
      await _initLocalNotifications().timeout(const Duration(seconds: 5));
    } catch (e) {
      debugPrint('[FCM] local notifications init failed: $e');
    }

    try {
      await _requestAndroidNotificationPermission()
          .timeout(const Duration(seconds: 5));
    } catch (e) {
      debugPrint('[FCM] android permission request failed: $e');
    }

    try {
      await Firebase.initializeApp().timeout(const Duration(seconds: 8));
      _firebaseReady = true;
    } catch (e) {
      debugPrint('[FCM] Firebase не настроен (добавьте google-services.json): $e');
      return;
    }

    try {
      final messaging = _messagingIfReady();
      if (messaging == null) return;

      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

      await _requestFcmPermission().timeout(const Duration(seconds: 5));

      FirebaseMessaging.onMessage.listen(_onForegroundMessage);
      FirebaseMessaging.onMessageOpenedApp.listen(_onOpenedApp);

      final initial = await messaging
          .getInitialMessage()
          .timeout(const Duration(seconds: 5));
      if (initial != null) {
        _dispatchTap(initial.data);
      }

      debugPrint('[FCM] Сервис уведомлений готов');
    } catch (e) {
      debugPrint('[FCM] Настройка FCM прервана: $e');
    }
  }

  Future<void> _requestFcmPermission() async {
    final messaging = _messagingIfReady();
    if (messaging == null) return;
    final settings = await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );
    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      debugPrint('[FCM] Разрешение на push отклонено');
    }
  }

  Future<void> _requestAndroidNotificationPermission() async {
    if (!Platform.isAndroid) return;
    final plugin = _local.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await plugin?.requestNotificationsPermission();
  }

  Future<void> _initLocalNotifications() async {
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings();
    await _local.initialize(
      const InitializationSettings(android: android, iOS: ios),
      onDidReceiveNotificationResponse: (details) {
        if (details.payload == null || details.payload!.isEmpty) return;
        try {
          final data = Map<String, dynamic>.from(
            jsonDecode(details.payload!) as Map,
          );
          _dispatchTap(data);
        } catch (_) {}
      },
    );

    final plugin = _local.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await plugin?.createNotificationChannel(
      const AndroidNotificationChannel(
        kAndroidChannelId,
        kAndroidChannelName,
        description: 'Новые сообщения в чатах и обновления заявок',
        importance: Importance.high,
        playSound: true,
        enableVibration: true,
      ),
    );
  }

  /// После успешного входа: FCM-токен → POST /api/mobile/fcm/register.
  /// Ошибки Firebase (в т.ч. [core/no-app]) не прерывают b2b-авторизацию.
  Future<void> bindAuth(AuthApi authApi) async {
    _authApi = authApi;
    try {
      await _requestAndroidNotificationPermission()
          .timeout(const Duration(seconds: 5));
    } catch (e) {
      debugPrint('[FCM] bindAuth: local permission failed: $e');
    }

    if (!_firebaseReady) {
      debugPrint('[FCM] bindAuth: Firebase не инициализирован, push пропущен');
      return;
    }

    try {
      await _requestFcmPermission().timeout(const Duration(seconds: 5));
    } catch (e) {
      if (_isFirebaseNoAppError(e)) {
        debugPrint('[FCM] bindAuth: FCM permission skipped (no Firebase app)');
        return;
      }
      debugPrint('[FCM] bindAuth: FCM permission failed: $e');
    }

    final token = await _safeGetFcmToken();
    if (token != null && token.isNotEmpty) {
      await _registerToken(token);
    } else {
      debugPrint('[FCM] Токен недоступен (no_token), вход без регистрации push');
    }

    try {
      _messagingIfReady()?.onTokenRefresh.listen(_registerToken);
    } catch (e) {
      debugPrint('[FCM] onTokenRefresh недоступен: $e');
    }
  }

  Future<void> _registerToken(String token) async {
    final api = _authApi;
    if (api == null) {
      debugPrint('[FCM] Регистрация пропущена: пользователь не авторизован');
      return;
    }
    try {
      await api.registerFcm(
        token,
        deviceName: Platform.isAndroid ? 'Android' : 'iOS',
      );
      debugPrint('[FCM] Токен отправлен на /api/mobile/fcm/register');
    } catch (e) {
      debugPrint('[FCM] Ошибка регистрации токена: $e');
    }
  }

  Future<void> _onForegroundMessage(RemoteMessage message) async {
    debugPrint('[FCM] Foreground: ${message.notification?.title}');
    await showFromRemoteMessage(message);
  }

  void _onOpenedApp(RemoteMessage message) {
    _dispatchTap(message.data);
  }

  void _dispatchTap(Map<String, dynamic> data) {
    onNotificationTap?.call(data);
  }

  Future<void> showFromRemoteMessage(RemoteMessage message) async {
    final notification = message.notification;
    final data = Map<String, dynamic>.from(message.data);

    final title = notification?.title ??
        data['title']?.toString() ??
        _titleForKind(data['kind']?.toString());
    final body = notification?.body ??
        data['body']?.toString() ??
        'Новое уведомление';

    if ((title == null || title.isEmpty) && (body == null || body.isEmpty)) {
      return;
    }

    final android = AndroidNotificationDetails(
      kAndroidChannelId,
      kAndroidChannelName,
      channelDescription: 'Сообщения и заявки',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
      enableVibration: true,
      playSound: true,
      ticker: title,
    );

    await _local.show(
      message.hashCode,
      title ?? 'GruzzExpert',
      body ?? '',
      NotificationDetails(
        android: android,
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
        ),
      ),
      payload: jsonEncode(data),
    );
  }

  String? _titleForKind(String? kind) {
    const map = {
      'chat_message': 'Новое сообщение',
      'new_message': 'Новое сообщение',
      'new_task': 'Новая заявка',
      'task_updated': 'Заявка обновлена',
      'task_reopened': 'Заявка снова доступна',
      'worker_status': 'Статус исполнителя',
      'task_cancelled': 'Заявка отменена',
      'route_reminder': 'Напоминание',
      'route_alarm': 'Срочно',
    };
    return kind != null ? map[kind] : null;
  }
}
