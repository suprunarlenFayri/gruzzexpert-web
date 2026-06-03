import 'package:flutter/foundation.dart';

/// Базовый URL Flask API.
///
/// Эмулятор: `http://10.0.2.2:5001` (если `python app.py` на порту 5001).
/// Реальное устройство (USB): LAN IP ПК, например:
/// `flutter run --dart-define=API_BASE_URL=http://192.168.1.10:5001`
///
/// Скрипт: `.\scripts\run_on_device.ps1`
class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:5001',
  );

  static void logConfig() {
    if (kDebugMode) {
      // ignore: avoid_print
      print('[AppConfig] API_BASE_URL=$apiBaseUrl');
    }
  }
  static String get apiPrefix => '$apiBaseUrl/api/mobile';

  static String get socketUrl => apiBaseUrl;

  /// Основной REST (take/status) — тот же хост, Bearer-токен.
  static String apiPath(String path) {
    final p = path.startsWith('/') ? path : '/$path';
    return '$apiBaseUrl$p';
  }
}
