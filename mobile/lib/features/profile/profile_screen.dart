import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api_client.dart';
import '../../core/api/profile_api.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/theme.dart';
import '../../widgets/b2b_widgets.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    super.key,
    required this.storage,
    required this.apiClient,
    required this.onLogout,
  });

  final SecureStorage storage;
  final ApiClient apiClient;
  final Future<void> Function() onLogout;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final ProfileApi _api = ProfileApi(widget.apiClient);
  final _picker = ImagePicker();

  UserProfile? _profile;
  bool _loading = true;
  bool _uploadingAvatar = false;
  bool _loggingOut = false;

  // Настройки (локальные + синхронизация с бэкендом в будущем)
  bool _pushEnabled = true;
  bool _soundEnabled = true;
  bool _availableForTasks = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final fresh = await _api.fetchMe();
      await widget.storage.saveUserProfile(_profileToCache(fresh));
      if (!mounted) return;
      setState(() {
        _profile = fresh;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка загрузки профиля: $e')),
      );
    }
  }

  Map<String, dynamic> _profileToCache(UserProfile p) => {
        'id': p.id,
        'name': p.name,
        'full_name': p.name,
        'phone': p.phone,
        'tag': p.tag,
        'role': p.role,
        'avatar_url': p.avatarUrl,
        'balance': p.balance,
        'weekly_earnings': p.weeklyEarnings,
        'availability': p.availability,
        'availability_label': p.availabilityLabel,
        'rating': p.rating,
        'completed_tasks': p.completedTasks,
        'missed_tasks': p.missedTasks,
        'is_frozen': p.isFrozen,
        'is_verified': p.isVerified,
      };

  // =====================================================
  // СМЕНА АВАТАРА (image_picker + multipart)
  // =====================================================
  Future<void> _changeAvatar() async {
    final xfile = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 85,
      maxWidth: 1024,
    );
    if (xfile == null) return;

    setState(() => _uploadingAvatar = true);
    try {
      final updated = await _api.uploadAvatar(xfile);
      await widget.storage.saveUserProfile(_profileToCache(updated));
      if (!mounted) return;
      setState(() => _profile = updated);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Аватар обновлён')),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка загрузки аватара: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _uploadingAvatar = false);
    }
  }

  // =====================================================
  // ВЫХОД ИЗ АККАУНТА
  // =====================================================
  Future<void> _logout() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: B2bColors.bgSecondary,
        title: const Text('Выйти из аккаунта?'),
        content: const Text('Потребуется повторный вход по телефону и SMS.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: B2bColors.danger),
            child: const Text('Выйти'),
          ),
        ],
      ),
    );
    if (ok != true) return;

    setState(() => _loggingOut = true);
    await widget.onLogout();
    if (mounted) setState(() => _loggingOut = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _profile == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final p = _profile;
    if (p == null) {
      return Center(
        child: FilledButton(onPressed: _load, child: const Text('Обновить')),
      );
    }

    final statusColor = availabilityColor(p.availability);
    final phoneFmt = _formatPhone(p.phone);

    return RefreshIndicator(
      onRefresh: _load,
      color: B2bColors.accentLight,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 40),
        children: [
          // === АВАТАР + ИМЯ ===
          B2bDetailCard(
            child: Column(
              children: [
                GestureDetector(
                  onTap: _uploadingAvatar ? null : _changeAvatar,
                  child: Stack(
                    alignment: Alignment.bottomRight,
                    children: [
                      CircleAvatar(
                        radius: 48,
                        backgroundColor: B2bColors.bgTertiary,
                        backgroundImage: p.avatarUrl != null ? NetworkImage(p.avatarUrl!) : null,
                        child: p.avatarUrl == null
                            ? Text(p.initials, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700))
                            : null,
                      ),
                      if (_uploadingAvatar)
                        const CircleAvatar(
                          radius: 48,
                          backgroundColor: Colors.black54,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      else
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: B2bColors.accent,
                            shape: BoxShape.circle,
                            border: Border.all(color: B2bColors.bgSecondary, width: 2),
                          ),
                          child: const Icon(Icons.camera_alt, size: 18, color: Colors.white),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Text(p.name, style: Theme.of(context).textTheme.titleLarge),
                if (phoneFmt != null) ...[
                  const SizedBox(height: 4),
                  Text(phoneFmt, style: const TextStyle(color: B2bColors.textSecondary)),
                ],
                if (p.tag != null && p.tag!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text('@${p.tag}', style: const TextStyle(color: B2bColors.accentLight)),
                ],
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: statusColor.withOpacity(0.4)),
                  ),
                  child: Text(
                    p.availabilityLabel,
                    style: TextStyle(color: statusColor, fontWeight: FontWeight.w700, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 12),

          // === ФИНАНСЫ ===
          B2bDetailCard(
            headerIcon: Icons.account_balance_wallet_outlined,
            headerTitle: 'Финансы',
            child: Row(
              children: [
                Expanded(child: _MoneyTile(label: 'Баланс', amount: p.balance, highlight: true)),
                const SizedBox(width: 12),
                Expanded(child: _MoneyTile(label: 'За 7 дней', amount: p.weeklyEarnings)),
              ],
            ),
          ),

          if (p.isFrozen)
            Padding(
              padding: const EdgeInsets.only(top: 8, bottom: 4),
              child: Text(
                'Вывод средств временно заморожен',
                style: TextStyle(fontSize: 12, color: B2bColors.warning),
              ),
            ),

          const SizedBox(height: 12),

          // === РЕЙТИНГ ===
          B2bDetailCard(
            headerIcon: Icons.star_outline,
            headerTitle: 'Рейтинг',
            child: Row(
              children: [
                const Icon(Icons.star_rounded, color: Color(0xFFC9A227), size: 28),
                const SizedBox(width: 8),
                Text(
                  p.rating.toStringAsFixed(1),
                  style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w800, color: B2bColors.accent),
                ),
                const Spacer(),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('${p.completedTasks} выполнено', style: const TextStyle(fontWeight: FontWeight.w600)),
                    if (p.missedTasks > 0)
                      Text('${p.missedTasks} пропущено', style: const TextStyle(fontSize: 12, color: B2bColors.textSecondary)),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // === НАСТРОЙКИ ===
          B2bDetailCard(
            headerIcon: Icons.settings_outlined,
            headerTitle: 'Настройки',
            child: Column(
              children: [
                _SettingSwitch(
                  icon: Icons.notifications_active_outlined,
                  title: 'Пуш-уведомления',
                  value: _pushEnabled,
                  onChanged: (v) => setState(() => _pushEnabled = v),
                ),
                const Divider(height: 1, color: B2bColors.borderLight),
                _SettingSwitch(
                  icon: Icons.volume_up_outlined,
                  title: 'Звук при новых заявках',
                  value: _soundEnabled,
                  onChanged: (v) => setState(() => _soundEnabled = v),
                ),
                const Divider(height: 1, color: B2bColors.borderLight),
                _SettingSwitch(
                  icon: Icons.work_outline,
                  title: 'Доступен для заказов',
                  value: _availableForTasks,
                  onChanged: (v) => setState(() => _availableForTasks = v),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // === ВЫХОД ===
          OutlinedButton.icon(
            onPressed: _loggingOut ? null : _logout,
            icon: const Icon(Icons.logout_rounded),
            label: _loggingOut
                ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Выйти из аккаунта'),
            style: OutlinedButton.styleFrom(
              foregroundColor: B2bColors.danger,
              side: const BorderSide(color: B2bColors.danger),
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(B2bColors.radiusMd)),
            ),
          ),
        ],
      ),
    );
  }

  String? _formatPhone(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    final d = raw.replaceAll(RegExp(r'\D'), '');
    if (d.length == 11 && d.startsWith('7')) {
      return '+7 (${d.substring(1, 4)}) ${d.substring(4, 7)}-${d.substring(7, 9)}-${d.substring(9)}';
    }
    return raw;
  }
}

// =====================================================
// Вспомогательные виджеты
// =====================================================

class _MoneyTile extends StatelessWidget {
  const _MoneyTile({required this.label, required this.amount, this.highlight = false});

  final String label;
  final double amount;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: highlight ? B2bColors.accent.withOpacity(0.1) : B2bColors.bgSecondary,
        borderRadius: BorderRadius.circular(B2bColors.radiusMd),
        border: Border.all(color: highlight ? B2bColors.accent.withOpacity(0.3) : B2bColors.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: B2bColors.textSecondary)),
          const SizedBox(height: 6),
          Text(
            formatRub(amount),
            style: TextStyle(
              fontSize: highlight ? 20 : 17,
              fontWeight: FontWeight.w800,
              color: B2bColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingSwitch extends StatelessWidget {
  const _SettingSwitch({
    required this.icon,
    required this.title,
    required this.value,
    required this.onChanged,
  });

  final IconData icon;
  final String title;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return SwitchListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      secondary: Icon(icon, color: B2bColors.textSecondary),
      title: Text(title, style: const TextStyle(color: B2bColors.textPrimary)),
      value: value,
      onChanged: onChanged,
      activeColor: B2bColors.accent,
    );
  }
}
