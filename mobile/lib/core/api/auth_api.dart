import 'package:dio/dio.dart';

import '../storage/secure_storage.dart';
import 'api_client.dart';

class AuthApi {
  AuthApi(this._client, this._storage);

  final ApiClient _client;
  final SecureStorage _storage;

  Dio get _dio => _client.dio;

  Future<Map<String, dynamic>> login({
    required String phone,
    required String password,
    String? smsSession,
    String? smsCode,
  }) async {
    final res = await _dio.post('/auth/login', data: {
      'phone': phone,
      'password': password,
      if (smsSession != null) 'sms_session': smsSession,
      if (smsCode != null) 'sms_code': smsCode,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> creatorCheck(String email) async {
    final res = await _dio.get('/auth/creator-check', queryParameters: {'email': email});
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> creatorLogin({
    required String email,
    String? totpCode,
    String? backupCode,
  }) async {
    final res = await _dio.post('/auth/creator-login', data: {
      'email': email,
      if (totpCode != null) 'totp_code': totpCode,
      if (backupCode != null) 'backup_code': backupCode,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> persistLoginResponse(Map<String, dynamic> data) async {
    if (data['ok'] != true) return;
    final token = data['token'] as String?;
    final user = data['user'] as Map?;
    if (token != null && user != null) {
      await _storage.saveSession(
        token: token,
        userId: user['id'] as int,
        user: Map<String, dynamic>.from(user),
      );
    }
  }

  Future<void> registerFcm(
    String fcmToken, {
    String platform = 'android',
    String? deviceName,
  }) async {
    await _dio.post('/fcm/register', data: {
      'token': fcmToken,
      'fcm_token': fcmToken,
      'platform': platform,
      if (deviceName != null) 'device_name': deviceName,
    });
  }
}
