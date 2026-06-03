import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/api/chats_api.dart';
import '../../core/theme/theme.dart';
import 'chat_room_screen.dart';

class ChatsListScreen extends StatefulWidget {
  const ChatsListScreen({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<ChatsListScreen> createState() => _ChatsListScreenState();
}

class _ChatsListScreenState extends State<ChatsListScreen> {
  late final ChatsApi _api = ChatsApi(widget.apiClient);
  List<ChatSummary> _chats = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final chats = await _api.fetchChats();
      if (!mounted) return;
      setState(() {
        _chats = chats;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  IconData _iconFor(ChatSummary chat) {
    if (chat.isGroup) return Icons.groups_rounded; // Группа — иконка компании
    if (chat.type == 'task') return Icons.assignment_outlined;
    return Icons.person_outline; // Личный чат
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Повторить')),
            ],
          ),
        ),
      );
    }
    if (_chats.isEmpty) {
      return const Center(
        child: Text(
          'Нет чатов',
          style: TextStyle(color: B2bColors.darkTextSecondary),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      color: B2bColors.accentLight,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(vertical: 6),
        itemCount: _chats.length,
        itemBuilder: (context, i) => _ChatListTile(
          chat: _chats[i],
          icon: _iconFor(_chats[i]),
          onTap: () {
            Navigator.of(context)
                .push(
                  MaterialPageRoute(
                    builder: (_) => ChatRoomScreen(
                      apiClient: widget.apiClient,
                      chatId: _chats[i].id,
                      title: _chats[i].title,
                    ),
                  ),
                )
                .then((_) => _load());
          },
        ),
      ),
    );
  }
}

class _ChatListTile extends StatelessWidget {
  const _ChatListTile({
    required this.chat,
    required this.icon,
    required this.onTap,
  });

  final ChatSummary chat;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final preview = (chat.lastMessage ?? '').trim();
    // Показываем автора последнего сообщения в формате "Имя: текст" (как в веб-версии)
    final subtitle = preview.isEmpty ? 'Нет сообщений' : preview;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Row(
            children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: B2bColors.accent.withOpacity(0.18),
                child: Icon(icon, color: B2bColors.accentLight, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            chat.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                              color: B2bColors.textPrimary,
                            ),
                          ),
                        ),
                        if (chat.unreadCount > 0)
                          Container(
                            margin: const EdgeInsets.only(left: 8),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 7,
                              vertical: 3,
                            ),
                            decoration: BoxDecoration(
                              color: B2bColors.accent,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              chat.unreadCount > 99 ? '99+' : '${chat.unreadCount}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13,
                        color: chat.unreadCount > 0
                            ? B2bColors.textPrimary.withOpacity(0.85)
                            : B2bColors.textSecondary,
                        fontWeight:
                            chat.unreadCount > 0 ? FontWeight.w500 : FontWeight.normal,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
