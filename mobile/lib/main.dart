import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';

/// WebView-оболочка GruzzExpert B2B с поддержкой выбора файлов (грузовик в чате).
/// Убираем SafeArea, чтобы не было пустоты сверху.
/// Добавляем onShowFileChooser, чтобы Android открывал галерею при клике на скрепку.
void main() {
  runApp(const GruzzWebViewApp());
}

class GruzzWebViewApp extends StatelessWidget {
  const GruzzWebViewApp({super.key});

  @override
  Widget build(BuildContext context) {
    const defaultUrl = 'http://192.168.31.137:5001';

    final url = const String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: defaultUrl,
    );

    return MaterialApp(
      title: 'GruzzExpert B2B',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: Scaffold(
        resizeToAvoidBottomInset: true,
        extendBodyBehindAppBar: true,
        body: InAppWebView(
          initialUrlRequest: URLRequest(url: Uri.parse(url)),
          initialSettings: InAppWebViewSettings(
            javaScriptEnabled: true,
            mediaPlaybackRequiresUserGesture: false,
            allowFileAccess: true,
            allowContentAccess: true,
          ),
          onWebViewCreated: (controller) {
            // Можно добавить JS-каналы при необходимости
          },
          onShowFileChooser: (controller, fileChooserParams) async {
            // Этот колбэк срабатывает при клике на input[type=file] в вебе (грузовик)
            // Возвращаем null — Android сам откроет системный выбор файла/галереи.
            // Если нужно кастомное поведение (image_picker), здесь можно вызвать нативный пикер.
            return null;
          },
        ),
      ),
    );
  }
}
