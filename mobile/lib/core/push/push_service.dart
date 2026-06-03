import '../api/auth_api.dart';
import '../../services/notification_service.dart';

/// Совместимость: делегирует в [NotificationService].
class PushService {
  PushService(AuthApi authApi) : _auth = authApi;

  final AuthApi _auth;

  Future<void> init() => NotificationService.instance.bindAuth(_auth);
}
