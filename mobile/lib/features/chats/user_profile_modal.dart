import 'package:flutter/material.dart';

import '../../core/theme/theme.dart';

/// Модальное окно профиля пользователя (как в веб-версии при клике на аватарку в чате)
class UserProfileModal extends StatelessWidget {
  const UserProfileModal({
    super.key,
    required this.userId,
    required this.name,
    this.phone,
    this.role,
    this.avatarUrl,
    this.tag,
  });

  final int userId;
  final String name;
  final String? phone;
  final String? role;
  final String? avatarUrl;
  final String? tag;

  static Future<void> show(
    BuildContext context, {
    required int userId,
    required String name,
    String? phone,
    String? role,
    String? avatarUrl,
    String? tag,
  }) {
    return showModalBottomSheet(
      context: context,
      backgroundColor: B2bColors.bgSecondary,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => UserProfileModal(
        userId: userId,
        name: name,
        phone: phone,
        role: role,
        avatarUrl: avatarUrl,
        tag: tag,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final initials = name.trim().isNotEmpty
        ? name.trim().split(RegExp(r'\s+')).map((e) => e[0]).take(2).join().toUpperCase()
        : '?';

    return Container(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: B2bColors.borderLight,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 20),

          // Аватар
          CircleAvatar(
            radius: 42,
            backgroundColor: B2bColors.bgTertiary,
            backgroundImage: avatarUrl != null ? NetworkImage(avatarUrl!) : null,
            child: avatarUrl == null
                ? Text(
                    initials,
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                      color: B2bColors.textPrimary,
                    ),
                  )
                : null,
          ),
          const SizedBox(height: 16),

          // Имя
          Text(
            name,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: B2bColors.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),

          // Тег
          if (tag != null && tag!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              '@$tag',
              style: const TextStyle(
                fontSize: 14,
                color: B2bColors.accentLight,
              ),
            ),
          ],

          const SizedBox(height: 20),

          // Информация
          _InfoRow(icon: Icons.badge_outlined, label: 'Роль', value: role ?? 'Пользователь'),
          if (phone != null && phone!.isNotEmpty)
            _InfoRow(icon: Icons.phone_outlined, label: 'Телефон', value: phone!),

          const SizedBox(height: 24),

          // Кнопка закрытия
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => Navigator.pop(context),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(B2bColors.radiusMd),
                ),
              ),
              child: const Text('Закрыть'),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
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
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: B2bColors.textSecondary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    color: B2bColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 15,
                    color: B2bColors.textPrimary,
                    fontWeight: FontWeight.w600,
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
