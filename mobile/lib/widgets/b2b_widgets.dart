import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/theme/b2b_colors.dart';

String formatRub(num amount) =>
    '${NumberFormat('#,###', 'ru_RU').format(amount)} ₽';

Color availabilityColor(String code) {
  switch (code) {
    case 'on_shift':
      return B2bColors.success;
    case 'busy':
      return B2bColors.warning;
    default:
      return B2bColors.accentLight;
  }
}

/// Карточка заявки как `.detail-card` в вебе.
class B2bDetailCard extends StatelessWidget {
  const B2bDetailCard({
    super.key,
    this.headerIcon,
    this.headerTitle,
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  final IconData? headerIcon;
  final String? headerTitle;
  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: B2bColors.bgTertiary,
        borderRadius: BorderRadius.circular(B2bColors.radiusLg),
        border: Border.all(color: B2bColors.borderLight),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (headerTitle != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: const BoxDecoration(
                color: B2bColors.bgSecondary,
                border: Border(
                  bottom: BorderSide(color: B2bColors.borderLight),
                ),
              ),
              child: Row(
                children: [
                  if (headerIcon != null) ...[
                    Icon(headerIcon, size: 18, color: B2bColors.textSecondary),
                    const SizedBox(width: 8),
                  ],
                  Text(
                    headerTitle!.toUpperCase(),
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: B2bColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ),
          Padding(padding: padding, child: child),
        ],
      ),
    );
  }
}

/// Строка метаданных как `.worker-meta-row` в вебе.
class B2bWorkerMetaRow extends StatelessWidget {
  const B2bWorkerMetaRow({
    super.key,
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
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: B2bColors.accent),
          const SizedBox(width: 8),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(
                  fontSize: 14,
                  height: 1.5,
                  color: B2bColors.textPrimary,
                ),
                children: [
                  TextSpan(
                    text: '$label: ',
                    style: const TextStyle(
                      color: B2bColors.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  TextSpan(text: value),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Ценник `.detail-price-large` (зелёный success).
class B2bDetailPrice extends StatelessWidget {
  const B2bDetailPrice({super.key, required this.amount});

  final double amount;

  @override
  Widget build(BuildContext context) {
    return Text(
      formatRub(amount),
      textAlign: TextAlign.center,
      style: const TextStyle(
        fontSize: 28,
        fontWeight: FontWeight.w800,
        color: B2bColors.success,
      ),
    );
  }
}

class B2bPrimaryCta extends StatelessWidget {
  const B2bPrimaryCta({
    super.key,
    required this.label,
    required this.onPressed,
    this.loading = false,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: loading ? null : onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: B2bColors.accent,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(B2bColors.radiusMd),
          ),
          elevation: 0,
        ),
        child: loading
            ? const SizedBox(
                height: 22,
                width: 22,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (icon != null) ...[
                    Icon(icon, size: 22),
                    const SizedBox(width: 10),
                  ],
                  Text(
                    label,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
      ),
    );
  }
}

class B2bSectionCard extends StatelessWidget {
  const B2bSectionCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return B2bDetailCard(child: child, padding: padding);
  }
}
