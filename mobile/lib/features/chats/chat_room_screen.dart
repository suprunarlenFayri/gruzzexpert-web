import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/api/chats_api.dart';
import '../../core/theme/theme.dart';
import 'user_profile_modal.dart';

/// Полноценный экран чата с переносом всей логики веб-версии
class ChatRoomScreen extends StatefulWidget {
  const ChatRoomScreen({
    super.key,
    required this.apiClient,
    required this.chatId,
    required this.title,
  });

  final ApiClient apiClient;
  final int chatId;
  final String title;

  @override
  State<ChatRoomScreen> createState() => _ChatRoomScreenState();
}

class _ChatRoomScreenState extends State<ChatRoomScreen> {
  late final ChatsApi _api = ChatsApi(widget.apiClient);
  final _input = TextEditingController();
  final _scroll = ScrollController();
  List<ChatMessage> _messages = [];
  bool _loading = true;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final msgs = await _api.fetchMessages(widget.chatId);
      if (!mounted) return;
      setState(() {
        _messages = msgs.where((m) => m.isRenderable).toList();
        _loading = false;
      });
      _scrollToEnd();
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      await _api.sendMessage(widget.chatId, text);
      _input.clear();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  /// Показывает профиль пользователя при тапе на аватарку
  void _showUserProfile(ChatMessage message) {
    if (message.senderId == null) return;

    UserProfileModal.show(
      context,
      userId: message.senderId!,
      name: message.authorName,
      avatarUrl: message.senderAvatar,
      // phone и role можно подгрузить дополнительно через API
    );
  }

  /// Логика группировки имён (как в веб-версии)
  /// Имя показывается ТОЛЬКО над первым сообщением в серии от одного автора
  bool _showAuthorHeader(int index) {
    final cur = _messages[index];
    if (cur.isMine) return false;
    if (index == 0) return true;
    final prev = _messages[index - 1];
    return prev.isMine || prev.authorName != cur.authorName;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: B2bColors.bgPrimary,
      appBar: AppBar(
        title: Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis),
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? const Center(
                        child: Text(
                          'Нет сообщений',
                          style: TextStyle(color: B2bColors.textSecondary),
                        ),
                      )
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                        itemCount: _messages.length,
                        itemBuilder: (context, i) => _MessageRow(
                          message: _messages[i],
                          showAuthorName: _showAuthorHeader(i),
                          onAvatarTap: _showUserProfile,
                        ),
                      ),
          ),
          _Composer(
            controller: _input,
            sending: _sending,
            onSend: _send,
            onAttach: _showAttachOptions,
          ),
        ],
      ),
    );
  }

  /// Заглушка для кнопки прикрепления файлов (ЭТАП 2)
  /// В ЭТАПЕ 3/4 будет полноценная интеграция image_picker / file_picker
  void _showAttachOptions() {
    showModalBottomSheet(
      context: context,
      backgroundColor: B2bColors.bgSecondary,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Сделать фото'),
              onTap: () {
                Navigator.pop(ctx);
                // TODO: image_picker - камера
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Камера: будет реализовано в следующем этапе')),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Выбрать из галереи'),
              onTap: () {
                Navigator.pop(ctx);
                // TODO: image_picker - галерея
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Галерея: будет реализовано в следующем этапе')),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.attach_file_outlined),
              title: const Text('Прикрепить документ'),
              onTap: () {
                Navigator.pop(ctx);
                // TODO: file_picker
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Файл: будет реализовано в следующем этапе')),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Строка сообщения с аватаркой и бабблом
class _MessageRow extends StatelessWidget {
  const _MessageRow({
    required this.message,
    required this.showAuthorName,
    required this.onAvatarTap,
  });

  final ChatMessage message;
  final bool showAuthorName;
  final void Function(ChatMessage) onAvatarTap;

  @override
  Widget build(BuildContext context) {
    final isMine = message.isMine;
    final maxW = MediaQuery.sizeOf(context).width * 0.72;

    return Padding(
      padding: EdgeInsets.only(
        bottom: 4,
        top: showAuthorName ? 12 : 2,
      ),
      child: Row(
        mainAxisAlignment: isMine ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // Аватарка (только для чужих сообщений)
          if (!isMine) ...[
            GestureDetector(
              onTap: () => onAvatarTap(message),
              child: CircleAvatar(
                radius: 16,
                backgroundColor: B2bColors.bgTertiary,
                backgroundImage: message.senderAvatar != null
                    ? NetworkImage(message.senderAvatar!)
                    : null,
                child: message.senderAvatar == null
                    ? Text(
                        message.authorName.isNotEmpty
                            ? message.authorName[0].toUpperCase()
                            : '?',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                      )
                    : null,
              ),
            ),
            const SizedBox(width: 8),
          ],

          Flexible(
            child: Column(
              crossAxisAlignment: isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                // Имя автора (только над первым сообщением в группе)
                if (showAuthorName)
                  Padding(
                    padding: const EdgeInsets.only(left: 4, bottom: 4),
                    child: Text(
                      message.authorName,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: B2bColors.textSecondary,
                      ),
                    ),
                  ),

                // Баббл сообщения
                Container(
                  constraints: BoxConstraints(maxWidth: maxW),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: isMine ? B2bColors.messageMine : B2bColors.messageTheirs,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(18),
                      topRight: const Radius.circular(18),
                      bottomLeft: Radius.circular(isMine ? 18 : 4),
                      bottomRight: Radius.circular(isMine ? 4 : 18),
                    ),
                    border: isMine ? null : Border.all(color: B2bColors.border),
                    boxShadow: isMine
                        ? null
                        : [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.12),
                              blurRadius: 3,
                              offset: const Offset(0, 1),
                            ),
                          ],
                  ),
                  child: Text(
                    message.displayText,
                    style: TextStyle(
                      fontSize: 15,
                      height: 1.35,
                      color: isMine
                          ? Colors.white.withOpacity(0.94)
                          : B2bColors.textChatTheirs,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Поле ввода сообщения с кнопкой прикрепления
class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
    required this.onAttach,
  });

  final TextEditingController controller;
  final bool sending;
  final VoidCallback onSend;
  final VoidCallback onAttach;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [B2bColors.bgPrimary, B2bColors.bgPrimary.withOpacity(0)],
          stops: const [0.6, 1],
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              // Кнопка прикрепления файлов
              Material(
                color: B2bColors.bgTertiary,
                borderRadius: BorderRadius.circular(22),
                child: InkWell(
                  onTap: onAttach,
                  borderRadius: BorderRadius.circular(22),
                  child: const SizedBox(
                    width: 44,
                    height: 44,
                    child: Icon(Icons.attach_file_rounded, color: B2bColors.textSecondary),
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // Поле ввода
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(
                    color: B2bColors.bgTertiary,
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(color: B2bColors.border),
                  ),
                  child: TextField(
                    controller: controller,
                    style: const TextStyle(color: B2bColors.textPrimary),
                    decoration: const InputDecoration(
                      hintText: 'Сообщение…',
                      hintStyle: TextStyle(color: B2bColors.textSecondary),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    ),
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => onSend(),
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // Кнопка отправки
              Material(
                color: B2bColors.accent,
                borderRadius: BorderRadius.circular(22),
                child: InkWell(
                  onTap: sending ? null : onSend,
                  borderRadius: BorderRadius.circular(22),
                  child: SizedBox(
                    width: 44,
                    height: 44,
                    child: sending
                        ? const Padding(
                            padding: EdgeInsets.all(10),
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
