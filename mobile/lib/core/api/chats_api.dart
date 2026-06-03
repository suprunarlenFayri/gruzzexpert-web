import 'package:dio/dio.dart';

import '../config/app_config.dart';
import 'api_client.dart';

class ChatSummary {
  ChatSummary({
    required this.id,
    required this.title,
    required this.type,
    required this.unreadCount,
    this.lastMessage,
    this.lastMessageAt,
    this.isGroup = false,
    this.taskId,
  });

  final int id;
  final String title;
  final String type;
  final int unreadCount;
  final String? lastMessage;
  final String? lastMessageAt;
  final bool isGroup;
  final int? taskId;

  factory ChatSummary.fromJson(Map<String, dynamic> j) => ChatSummary(
        id: j['id'] as int,
        title: (j['title'] ?? 'Чат').toString(),
        type: (j['type'] ?? 'private').toString(),
        unreadCount: (j['unread_count'] as num?)?.toInt() ?? 0,
        lastMessage: j['last_message']?.toString(),
        lastMessageAt: j['last_message_at']?.toString(),
        isGroup: j['is_group'] == true,
        taskId: (j['task_id'] as num?)?.toInt(),
      );
}

class ChatMessage {
  ChatMessage({
    required this.id,
    required this.text,
    required this.authorName,
    required this.isMine,
    this.senderId,
    this.senderAvatar,
    this.createdAt,
    this.hasAttachments = false,
    this.deletedForAll = false,
  });

  final int id;
  final String text;
  final String authorName;
  final bool isMine;
  final int? senderId;
  final String? senderAvatar;
  final String? createdAt;
  final bool hasAttachments;
  final bool deletedForAll;

  bool get isRenderable {
    if (deletedForAll) return true;
    final t = text.trim();
    if (t.isNotEmpty) return true;
    return hasAttachments;
  }

  String get displayText {
    final t = text.trim();
    if (t.isNotEmpty) return t;
    if (hasAttachments) return 'Вложение';
    if (deletedForAll) return 'Сообщение удалено';
    return '';
  }

  factory ChatMessage.fromJson(Map<String, dynamic> j) {
    final attachments = j['attachments'] as List<dynamic>? ?? [];
    return ChatMessage(
      id: j['id'] as int,
      text: (j['message'] ?? j['text'] ?? '').toString(),
      authorName: (j['author_name'] ?? j['sender_name'] ?? '—').toString(),
      isMine: j['isMyMessage'] == true,
      senderId: (j['sender_id'] ?? j['author_id']) as int?,
      senderAvatar: j['sender_avatar']?.toString() ?? j['avatar']?.toString(),
      createdAt: j['created_at']?.toString(),
      hasAttachments: attachments.isNotEmpty,
      deletedForAll: j['deleted_for_all'] == true,
    );
  }
}

class ChatsApi {
  ChatsApi(this._client);

  final ApiClient _client;

  Future<List<ChatSummary>> fetchChats() async {
    final res = await _client.dio.get('/chats');
    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(requestOptions: res.requestOptions, message: data['error']?.toString());
    }
    final list = data['chats'] as List<dynamic>? ?? [];
    return list.map((e) => ChatSummary.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<List<ChatMessage>> fetchMessages(int chatId, {int? beforeId}) async {
    final res = await _client.dio.get(
      '/chats/$chatId/messages',
      queryParameters: beforeId != null ? {'before_id': beforeId, 'limit': 40} : {'limit': 40},
    );
    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(requestOptions: res.requestOptions, message: data['error']?.toString());
    }
    final list = data['messages'] as List<dynamic>? ?? [];
    return list.map((e) => ChatMessage.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<void> sendMessage(int chatId, String text) async {
    final res = await _client.dio.post('/chats/$chatId/send', data: {'text': text});
    final data = res.data as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw DioException(requestOptions: res.requestOptions, message: data['error']?.toString());
    }
  }
}
