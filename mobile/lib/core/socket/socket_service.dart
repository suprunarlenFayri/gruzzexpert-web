import 'package:socket_io_client/socket_io_client.dart' as io;

import '../config/app_config.dart';

/// Socket.IO — синхронно с Flask-SocketIO (комнаты user_{id}, global_update).
class SocketService {
  io.Socket? _socket;

  void connect({
    required int userId,
    required String sessionToken,
    void Function(Map<String, dynamic> payload)? onGlobalUpdate,
    void Function(Map<String, dynamic> data)? onTaskNotification,
  }) {
    disconnect();
    _socket = io.io(
      AppConfig.socketUrl,
      io.OptionBuilder()
          .setTransports(['websocket', 'polling'])
          .enableAutoConnect()
          .setAuth({'token': sessionToken, 'user_id': userId})
          .build(),
    );

    _socket!.onConnect((_) {
      _socket!.emit('join', {'room': 'user_$userId'});
    });

    _socket!.on('global_update', (data) {
      if (data is Map && onGlobalUpdate != null) {
        onGlobalUpdate(Map<String, dynamic>.from(data));
      }
    });

    _socket!.on('task_notification', (data) {
      if (data is Map && onTaskNotification != null) {
        onTaskNotification(Map<String, dynamic>.from(data));
      }
    });
  }

  void disconnect() {
    _socket?.dispose();
    _socket = null;
  }
}
