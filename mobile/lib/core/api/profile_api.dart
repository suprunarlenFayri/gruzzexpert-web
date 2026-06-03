import 'dart:io';

import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';

import '../config/app_config.dart';
import 'api_client.dart';

class UserProfile {
  UserProfile({
    required this.id,
    required this.name,
    this.phone,
    this.email,
    this.tag,
    this.role,
    this.avatarUrl,
    this.balance = 0,
    this.weeklyEarnings = 0,
    this.availability = 'available',
    this.availabilityLabel = 'Доступен',
    this.rating = 0,
    this.completedTasks = 0,
    this.missedTasks = 0,
    this.isFrozen = false,
    this.isVerified = false,
  });

  final int id;
  final String name;
  final String? phone;
  final String? email;
  final String? tag;
  final String? role;
  final String? avatarUrl;
  final double balance;
  final double weeklyEarnings;
  final String availability;
  final String availabilityLabel;
  final double rating;
  final int completedTasks;
  final int missedTasks;
  final bool isFrozen;
  final bool isVerified;

  factory UserProfile.fromJson(Map<String, dynamic> j) => UserProfile(
        id: j['id'] as int,
        name: (j['full_name'] ?? j['name'] ?? 'Пользователь').toString(),
        phone: j['phone']?.toString(),
        email: j['email']?.toString(),
        tag: j['tag']?.toString(),
        role: j['role']?.toString(),
        avatarUrl: _resolveAvatarUrl(j),
        balance: (j['balance'] as num?)?.toDouble() ?? 0,
        weeklyEarnings: (j['weekly_earnings'] as num?)?.toDouble() ?? 0,
        availability: (j['availability'] ?? 'available').toString(),
        availabilityLabel: (j['availability_label'] ?? 'Доступен').toString(),
        rating: (j['rating'] as num?)?.toDouble() ?? 0,
        completedTasks: (j['completed_tasks'] as num?)?.toInt() ?? 0,
        missedTasks: (j['missed_tasks'] as num?)?.toInt() ?? 0,
        isFrozen: j['is_frozen'] == true,
        isVerified: j['is_verified'] == true,
      );

  static String? _resolveAvatarUrl(Map<String, dynamic> j) {
    final direct = j['avatar_url']?.toString();
    if (direct != null && direct.isNotEmpty) return direct;
    final path = j['avatar']?.toString();
    if (path == null || path.isEmpty) return null;
    final clean = path.replaceAll('\\', '/');
    if (clean.startsWith('http')) return clean;
    final base = AppConfig.apiBaseUrl.replaceAll(RegExp(r'/$'), '');
    final rel = clean.startsWith('uploads/') ? clean : 'uploads/$clean';
    return '$base/$rel';
  }

  String get initials {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty) return '?';
    if (parts.length == 1) {
      return parts.first.isNotEmpty ? parts.first[0].toUpperCase() : '?';
    }
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }
}

class ProfileApi {
  ProfileApi(this._client);

  final ApiClient _client;

  /// Профиль исполнителя — `GET /api/worker/me` (как в веб B2B).
  Future<UserProfile> fetchMe() async {
    final res = await _client.rootDio.get('/api/worker/me');
    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(
        requestOptions: res.requestOptions,
        message: data['error']?.toString() ?? 'Ошибка загрузки профиля',
      );
    }
    return UserProfile.fromJson(Map<String, dynamic>.from(data['user'] as Map));
  }

  /// Загрузка аватара (Multipart) — POST /api/worker/me/avatar
  Future<UserProfile> uploadAvatar(XFile file) async {
    final formData = FormData.fromMap({
      'avatar': await MultipartFile.fromFile(
        file.path,
        filename: file.name,
      ),
    });

    final res = await _client.rootDio.post(
      '/api/worker/me/avatar',
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );

    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(
        requestOptions: res.requestOptions,
        message: data['error']?.toString() ?? 'Ошибка загрузки аватара',
      );
    }
    return UserProfile.fromJson(Map<String, dynamic>.from(data['user'] as Map));
  }
}
