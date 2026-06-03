import 'package:dio/dio.dart';

import 'api_client.dart';

/// Быстрая проверка доступности API без блокировки UI.
class ServerHealth {
  static Future<bool> isReachable(
    ApiClient client, {
    Duration timeout = const Duration(seconds: 5),
  }) async {
    try {
      await client.dio.get(
        '/auth/creator-check',
        queryParameters: {'email': '_health@local'},
        options: Options(
          connectTimeout: timeout,
          receiveTimeout: timeout,
          sendTimeout: timeout,
          validateStatus: (status) => status != null && status < 500,
        ),
      );
      return true;
    } on DioException catch (e) {
      return e.type == DioExceptionType.badResponse && e.response != null;
    } catch (_) {
      return false;
    }
  }
}
