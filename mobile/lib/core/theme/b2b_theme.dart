import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'b2b_colors.dart';

abstract final class B2bTheme {
  static const BorderRadius radius8 = BorderRadius.all(Radius.circular(B2bColors.radiusSm));
  static const BorderRadius radius12 = BorderRadius.all(Radius.circular(B2bColors.radiusMd));
  static const BorderRadius radius16 = BorderRadius.all(Radius.circular(B2bColors.radiusLg));

  static ThemeData light() => _build(Brightness.light);

  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;

    final scaffold = isDark ? B2bColors.bgPrimary : B2bColors.lightScaffold;
    final surface = isDark ? B2bColors.bgSecondary : B2bColors.lightCard;
    final card = isDark ? B2bColors.bgTertiary : B2bColors.lightInputFill;
    final border = isDark ? B2bColors.borderLight : B2bColors.lightBorder;
    final inputFill = isDark ? B2bColors.bgTertiary : B2bColors.lightInputFill;
    final textPrimary = isDark ? B2bColors.textPrimary : B2bColors.lightTextPrimary;
    final textSecondary =
        isDark ? B2bColors.textSecondary : B2bColors.lightTextSecondary;
    final accent = isDark ? B2bColors.accent : const Color(0xFF0088CC);

    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: accent,
      onPrimary: Colors.white,
      secondary: isDark ? B2bColors.accentHover : const Color(0xFF0099E6),
      onSecondary: Colors.white,
      surface: surface,
      onSurface: textPrimary,
      error: B2bColors.danger,
      onError: Colors.white,
      outline: border,
    );

    final borderSide = BorderSide(color: border, width: 1);

    final inputDecoration = InputDecorationTheme(
      filled: true,
      fillColor: inputFill,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(borderRadius: radius12, borderSide: borderSide),
      enabledBorder: OutlineInputBorder(borderRadius: radius12, borderSide: borderSide),
      focusedBorder: OutlineInputBorder(
        borderRadius: radius12,
        borderSide: BorderSide(color: accent, width: 1.5),
      ),
      hintStyle: TextStyle(color: textSecondary, fontSize: 14),
      labelStyle: TextStyle(color: textSecondary, fontSize: 13, fontWeight: FontWeight.w500),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      scaffoldBackgroundColor: scaffold,
      colorScheme: colorScheme,
      cardColor: card,
      dividerColor: border,
      fontFamily: 'Inter',
      textTheme: TextTheme(
        bodyLarge: TextStyle(color: textPrimary, fontSize: 16, height: 1.4),
        bodyMedium: TextStyle(color: textPrimary, fontSize: 14, height: 1.45),
        bodySmall: TextStyle(color: textSecondary, fontSize: 12),
        titleLarge: TextStyle(
          color: textPrimary,
          fontSize: 22,
          fontWeight: FontWeight.w800,
        ),
        titleMedium: TextStyle(
          color: textPrimary,
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
        labelSmall: TextStyle(
          color: textSecondary,
          fontSize: 11,
          fontWeight: FontWeight.w500,
          letterSpacing: 0.3,
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
        systemOverlayStyle: isDark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        indicatorColor: accent.withOpacity(0.22),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 12,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
            color: selected ? accent : textSecondary,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? accent : textSecondary,
            size: 24,
          );
        }),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: radius16,
          side: BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: inputDecoration,
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: const RoundedRectangleBorder(borderRadius: radius12),
          elevation: 0,
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          backgroundColor: card,
          minimumSize: const Size.fromHeight(48),
          side: borderSide,
          shape: const RoundedRectangleBorder(borderRadius: radius12),
        ),
      ),
      listTileTheme: const ListTileThemeData(
        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      ),
    );
  }
}
