import 'package:web_socket_channel/web_socket_channel.dart';

/// Заготовка для raw WebSocket (если появятся отдельные WS-endpoint'ы).
class RawWsClient {
  WebSocketChannel? _channel;

  void connect(Uri uri) {
    _channel = WebSocketChannel.connect(uri);
  }

  Stream<dynamic>? get stream => _channel?.stream;

  void send(String data) => _channel?.sink.add(data);

  void close() => _channel?.sink.close();
}
