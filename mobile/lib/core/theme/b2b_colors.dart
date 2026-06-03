import 'package:flutter/material.dart';

/// Design tokens из `templates/base.html` (:root, dark theme).
abstract final class B2bColors {
  // ——— Фоны (web --bg-*) ———
  static const Color bgPrimary = Color(0xFF0E1621);
  static const Color bgSecondary = Color(0xFF17212B);
  static const Color bgTertiary = Color(0xFF242F3D);

  // ——— Текст (web --text-*) ———
  static const Color textPrimary = Color(0xFFE4E6EB);
  static const Color textSecondary = Color(0xFF8E9EAE);
  static const Color textMuted = Color(0xFF5E6F8D);

  // ——— Акцент / бренд (web --accent-*) ———
  static const Color accent = Color(0xFF2B5278);
  static const Color accentHover = Color(0xFF2C6B98);
  static const Color accentLight = Color(0xFF3A6B99);
  static const Color gradientStart = Color(0xFF2B5278);
  static const Color gradientEnd = Color(0xFF2C6B98);

  // ——— Семантика ———
  static const Color success = Color(0xFF4CAF50);
  static const Color successHover = Color(0xFF43A047);
  static const Color warning = Color(0xFFF39C12);
  static const Color danger = Color(0xFFDC3545);

  // ——— Границы ———
  static const Color border = Color(0xFF242F3D);
  static const Color borderLight = Color(0xFF2A3645);

  // ——— Чат (web --message-mine / --bg-chat-theirs) ———
  static const Color messageMine = Color(0xFF2B5278);
  static const Color messageTheirs = Color(0xFF242F3D);
  static const Color textChatTheirs = Color(0xE6FFFFFF); // rgba(255,255,255,0.9)

  // ——— Статусы заявок ———
  static const Color statusRecruiting = Color(0xFFA855F7);
  static const Color statusInProgress = Color(0xFFF59E0B);
  static const Color statusDone = Color(0xFF22C55E);

  // ——— Радиусы (web --radius-*) ———
  static const double radiusSm = 8;
  static const double radiusMd = 12;
  static const double radiusLg = 16;

  // ——— Обратная совместимость со старыми именами ———
  static const Color darkScaffold = bgPrimary;
  static const Color darkCard = bgSecondary;
  static const Color darkBorder = borderLight;
  static const Color darkInputFill = bgTertiary;
  static const Color darkTextPrimary = textPrimary;
  static const Color darkTextSecondary = textSecondary;

  static const Color lightScaffold = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFF0F2F5);
  static const Color lightBorder = Color(0xFFDCE3EC);
  static const Color lightInputFill = Color(0xFFEEF2F6);
  static const Color lightTextPrimary = Color(0xFF1C1E21);
  static const Color lightTextSecondary = Color(0xFF65676B);

  static Color dropdownHoverDark() =>
      Color.alphaBlend(accent.withOpacity(0.2), bgTertiary);
}
