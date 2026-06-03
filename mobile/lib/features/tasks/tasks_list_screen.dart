import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/api/tasks_api.dart';
import '../../core/theme/theme.dart';
import 'task_detail_screen.dart';

class TasksListScreen extends StatefulWidget {
  const TasksListScreen({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<TasksListScreen> createState() => _TasksListScreenState();
}

class _TasksListScreenState extends State<TasksListScreen> {
  late final TasksApi _api = TasksApi(widget.apiClient);
  List<TaskCard> _pool = [];
  List<TaskCard> _my = [];
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
      final data = await _api.fetchLists();
      if (!mounted) return;
      setState(() {
        _pool = data.pool;
        _my = data.my;
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

  String _statusLabel(String s) {
    const map = {
      'recruiting': 'Набор',
      'in_progress': 'В работе',
      'on_site': 'На проверке',
      'waiting_confirm': 'Ожидает подтверждения',
      'done': 'Завершена',
      'failed': 'Провалена',
    };
    return map[s] ?? s;
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('Повторить')),
          ],
        ),
      );
    }

    final priceFmt = NumberFormat('#,###', 'ru_RU');

    Widget buildSection(String title, List<TaskCard> items) {
      if (items.isEmpty) return const SizedBox.shrink();
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Text(
              title,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: B2bColors.darkTextSecondary,
              ),
            ),
          ),
          ...items.map((t) => _TaskTile(
                task: t,
                price: priceFmt.format(t.price),
                status: _statusLabel(t.status),
                onTap: () {
                  Navigator.of(context)
                      .push(
                        MaterialPageRoute(
                          builder: (_) => TaskDetailScreen(
                            apiClient: widget.apiClient,
                            taskId: t.id,
                          ),
                        ),
                      )
                      .then((_) => _load());
                },
              )),
        ],
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        children: [
          buildSection('Мои заявки', _my),
          buildSection('Доступные', _pool),
          if (_my.isEmpty && _pool.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: Text('Нет активных заявок')),
            ),
        ],
      ),
    );
  }
}

class _TaskTile extends StatelessWidget {
  const _TaskTile({
    required this.task,
    required this.price,
    required this.status,
    required this.onTap,
  });

  final TaskCard task;
  final String price;
  final String status;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      color: B2bColors.darkCard,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(B2bColors.radiusMd),
        side: const BorderSide(color: B2bColors.darkBorder),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(B2bColors.radiusMd),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      task.title,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                    ),
                    if (task.city != null && task.city!.isNotEmpty)
                      Text(task.city!, style: const TextStyle(color: B2bColors.darkTextSecondary)),
                    Text(
                      '${task.executionDate ?? ''} ${task.executionTime ?? ''}'.trim(),
                      style: const TextStyle(fontSize: 12, color: B2bColors.darkTextSecondary),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('$price ₽', style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: B2bColors.accent.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(status, style: const TextStyle(fontSize: 11)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
