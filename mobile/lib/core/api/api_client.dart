import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../storage/secure_storage.dart';

class ApiClient {
  ApiClient(this._storage) {
    _dio = _buildDio(AppConfig.apiPrefix);
    _rootDio = _buildDio(AppConfig.apiBaseUrl);
  }

  final SecureStorage _storage;
  late final Dio _dio;
  late final Dio _rootDio;

  Dio _buildDio(String baseUrl) {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 20),
        receiveTimeout: const Duration(seconds: 30),
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-Device-Type': 'mobile',
        },
      ),
    );
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.getToken();
          if (token != null && token.isNotEmpty) {
            options.headers['X-Session-Token'] = token;
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
    return dio;
  }

  Dio get dio => _dio;

  Dio get rootDio => _rootDio;
}
