import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/api/auth_api.dart';
import '../../core/push/push_service.dart';
import '../../core/socket/socket_service.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/theme.dart';
import '../../services/notification_service.dart';
import '../auth/login_screen.dart';
import '../chats/chats_list_screen.dart';
import '../profile/profile_screen.dart';
import '../tasks/tasks_list_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.storage, required this.apiClient});

  final SecureStorage storage;
  final ApiClient apiClient;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _socket = SocketService();
  int _tab = 0;

  static const _titles = ['Заявки', 'Чаты', 'Профиль'];

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final token = await widget.storage.getToken();
    final userId = await widget.storage.getUserId();
    if (token == null || userId == null) return;

    final auth = AuthApi(widget.apiClient, widget.storage);
    unawaited(PushService(auth).init());

    NotificationService.instance.onNotificationTap = (data) {
      if (!mounted) return;
      final kind = data['kind']?.toString();
      if (kind == 'chat_message' || data['chat_id'] != null) {
        setState(() => _tab = 1);
      } else if (kind != null && kind.contains('task')) {
        setState(() => _tab = 0);
      }
    };

    _socket.connect(
      userId: userId,
      sessionToken: token,
      onGlobalUpdate: (_) {},
      onTaskNotification: (_) {
        if (_tab == 0 && mounted) setState(() {});
      },
    );
  }

  @override
  void dispose() {
    _socket.disconnect();
    super.dispose();
  }

  Future<void> _logout() async {
    await widget.storage.clear();
    _socket.disconnect();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => LoginScreen(
          storage: widget.storage,
          apiClient: widget.apiClient,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      TasksListScreen(apiClient: widget.apiClient),
      ChatsListScreen(apiClient: widget.apiClient),
      ProfileScreen(
        storage: widget.storage,
        apiClient: widget.apiClient,
        onLogout: _logout,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_tab]),
        centerTitle: false,
      ),
      body: IndexedStack(
        index: _tab,
        children: pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        backgroundColor: B2bColors.bgSecondary,
        indicatorColor: B2bColors.accent.withOpacity(0.22),
        surfaceTintColor: Colors.transparent,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment),
            label: 'Заявки',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: 'Чаты',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Профиль',
          ),
        ],
      ),
    );
  }
}
