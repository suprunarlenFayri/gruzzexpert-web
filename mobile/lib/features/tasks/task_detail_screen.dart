import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/api/tasks_api.dart';
import '../../core/theme/theme.dart';
import '../../widgets/b2b_widgets.dart'; // содержит formatRub

class TaskDetailScreen extends StatefulWidget {
  const TaskDetailScreen({
    super.key,
    required this.apiClient,
    required this.taskId,
  });

  final ApiClient apiClient;
  final int taskId;

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  late final TasksApi _api = TasksApi(widget.apiClient);
  TaskDetail? _task;
  bool _loading = true;
  bool _acting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final t = await _api.fetchDetail(widget.taskId);
      if (!mounted) return;
      setState(() {
        _task = t;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _take() async {
    setState(() => _acting = true);
    try {
      await _api.takeTask(widget.taskId);
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _reject() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: B2bColors.bgSecondary,
        title: const Text('Отказаться?'),
        content: const Text('Заявка снова станет доступна другим исполнителям.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Отказаться')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _acting = true);
    try {
      await _api.rejectTask(widget.taskId);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _step(String status) async {
    setState(() => _acting = true);
    try {
      await _api.postStatus(widget.taskId, status);
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acting = false);
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

  String _formatDate(String? raw) {
    if (raw == null || raw.isEmpty) return '';
    try {
      final d = DateTime.parse(raw);
      return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
    } catch (_) {
      return raw;
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = _task;
    return Scaffold(
      backgroundColor: B2bColors.bgPrimary,
      appBar: AppBar(
        title: Text(
          t?.title ?? 'Заявка',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : t == null
              ? const Center(child: Text('Не найдено'))
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                  children: [
                    // === ГЛАВНАЯ КАРТОЧКА ЗАЯВКИ (как в веб-версии) ===
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: B2bColors.bgSecondary,
                        borderRadius: BorderRadius.circular(B2bColors.radiusLg),
                        border: Border.all(color: B2bColors.borderLight),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // КРУПНАЯ ЦЕНА (как .detail-price-large)
                          Text(
                            formatRub(t.price),
                            style: const TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.w800,
                              color: B2bColors.success,
                              height: 1.1,
                            ),
                          ),
                          const SizedBox(height: 12),

                          // Название
                          Text(
                            t.title,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                              color: B2bColors.textPrimary,
                            ),
                          ),
                          if (t.description != null && t.description!.trim().isNotEmpty) ...[
                            const SizedBox(height: 10),
                            Text(
                              t.description!.trim(),
                              style: const TextStyle(
                                fontSize: 14,
                                height: 1.45,
                                color: B2bColors.textPrimary,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),

                    const SizedBox(height: 12),

                    // === ДЕТАЛИ (Город, Адрес, Дата, Время, Исполнители) ===
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: B2bColors.bgSecondary,
                        borderRadius: BorderRadius.circular(B2bColors.radiusLg),
                        border: Border.all(color: B2bColors.borderLight),
                      ),
                      child: Column(
                        children: [
                          if (_has(t.city))
                            _DetailRow(
                              icon: Icons.location_city_outlined,
                              label: 'Город',
                              value: t.city!,
                            ),
                          if (_has(t.address))
                            _DetailRow(
                              icon: Icons.place_outlined,
                              label: 'Точный адрес',
                              value: t.address!,
                            ),
                          if (_has(t.executionDate))
                            _DetailRow(
                              icon: Icons.calendar_today_outlined,
                              label: 'Дата',
                              value: _formatDate(t.executionDate),
                            ),
                          if (_has(t.executionTime))
                            _DetailRow(
                              icon: Icons.schedule_outlined,
                              label: 'Время',
                              value: t.executionTime!,
                            ),
                          _DetailRow(
                            icon: Icons.engineering_outlined,
                            label: 'Исполнители',
                            value: '${t.assignedCount} / ${t.requiredWorkers}',
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 12),

                    // Статус заявки
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: B2bColors.bgSecondary,
                        borderRadius: BorderRadius.circular(B2bColors.radiusLg),
                        border: Border.all(color: B2bColors.borderLight),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.info_outline, color: B2bColors.textSecondary, size: 20),
                          const SizedBox(width: 10),
                          Text(
                            'Статус заявки:',
                            style: const TextStyle(color: B2bColors.textSecondary),
                          ),
                          const Spacer(),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                            decoration: BoxDecoration(
                              color: B2bColors.accent.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              _statusLabel(t.status),
                              style: const TextStyle(
                                color: B2bColors.textPrimary,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 20),

                    // === ЦЕПОЧКА B2B-СТАТУСОВ ===
                    _buildWorkerActionChain(t),
                  ],
                ),
    );
  }

  // =====================================================
  // ЭТАП 3: ПОЛНАЯ ЦЕПОЧКА B2B-СТАТУСОВ (как в веб-версии)
  // =====================================================
  Widget _buildWorkerActionChain(TaskDetail t) {
    final tracking = t.userTracking;
    final ws = tracking?['worker_status']?.toString() ?? 'assigned';

    // === 1. ЗАЯВКА ДОСТУПНА ДЛЯ ВЗЯТИЯ ===
    if (t.canTake) {
      return B2bPrimaryCta(
        label: 'Взять в работу',
        icon: Icons.local_shipping_outlined,
        loading: _acting,
        onPressed: _take,
      );
    }

    // === 2. ЗАЯВКА ВЗЯТА ИЛИ В РАБОТЕ ===
    if (tracking != null) {
      // Кнопка ОТКАЗА (только для assigned / en_route)
      final canRejectNow = t.canReject || ws == 'assigned' || ws == 'en_route';

      return Column(
        children: [
          // === ГЛАВНАЯ ИНТЕРАКТИВНАЯ КНОПКА СТАТУСА ===
          if (ws == 'assigned')
            B2bPrimaryCta(
              label: 'Выехал на объект',
              icon: Icons.directions_car_outlined,
              loading: _acting,
              onPressed: () => _step('en_route'),
            )
          else if (ws == 'en_route')
            B2bPrimaryCta(
              label: 'На месте / Начать работу',
              icon: Icons.place_outlined,
              loading: _acting,
              onPressed: () => _step('on_site'),
            )
          else if (ws == 'on_site')
            B2bPrimaryCta(
              label: 'Завершить работу',
              icon: Icons.check_circle_outline,
              loading: _acting,
              onPressed: () => _step('completed'),
            )
          else if (ws == 'completed')
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 18),
              decoration: BoxDecoration(
                color: B2bColors.success.withOpacity(0.12),
                borderRadius: BorderRadius.circular(B2bColors.radiusLg),
                border: Border.all(color: B2bColors.success.withOpacity(0.4)),
              ),
              child: const Center(
                child: Text(
                  'Работа выполнена',
                  style: TextStyle(
                    color: B2bColors.success,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),

          // === КНОПКА ОТКАЗА (B2bColors.danger) ===
          if (canRejectNow) ...[
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: _acting ? null : _reject,
              style: OutlinedButton.styleFrom(
                foregroundColor: B2bColors.danger,
                side: const BorderSide(color: B2bColors.danger),
                minimumSize: const Size.fromHeight(50),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(B2bColors.radiusMd),
                ),
              ),
              child: const Text('Отказаться от заявки'),
            ),
          ],
        ],
      );
    }

    // === 3. Если нет доступа ===
    return const SizedBox.shrink();
  }

  bool _has(String? v) => v != null && v.trim().isNotEmpty;
}

// =====================================================
// Вспомогательный виджет строки с иконкой
// =====================================================
class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        children: [
          Icon(icon, size: 20, color: B2bColors.textSecondary),
          const SizedBox(width: 12),
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: const TextStyle(
                color: B2bColors.textSecondary,
                fontSize: 14,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: B2bColors.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
