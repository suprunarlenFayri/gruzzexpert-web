import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorage {
  SecureStorage() : _store = const FlutterSecureStorage();

  final FlutterSecureStorage _store;

  static const _keyToken = 'session_token';
  static const _keyUserId = 'user_id';
  static const _keyUserJson = 'user_profile_json';

  Future<void> saveSession({
    required String token,
    required int userId,
    Map<String, dynamic>? user,
  }) async {
    await _store.write(key: _keyToken, value: token);
    await _store.write(key: _keyUserId, value: userId.toString());
    if (user != null) {
      await saveUserProfile(user);
    }
  }

  Future<void> saveUserProfile(Map<String, dynamic> user) async {
    await _store.write(key: _keyUserJson, value: jsonEncode(user));
  }

  Future<Map<String, dynamic>?> getUserProfile() async {
    final raw = await _store.read(key: _keyUserJson);
    if (raw == null || raw.isEmpty) return null;
    try {
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return null;
    }
  }

  Future<String?> getToken() => _store.read(key: _keyToken);

  Future<int?> getUserId() async {
    final v = await _store.read(key: _keyUserId);
    return v == null ? null : int.tryParse(v);
  }

  Future<void> clear() async {
    await _store.delete(key: _keyToken);
    await _store.delete(key: _keyUserId);
    await _store.delete(key: _keyUserJson);
  }
}
