import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Маска телефона: +7 (XXX) XXX-XX-XX
class RussianPhoneMaskFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    var digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    if (digits.startsWith('8') && digits.length > 1) {
      digits = '7${digits.substring(1)}';
    }
    if (digits.startsWith('7')) {
      digits = digits.substring(1);
    }
    if (digits.length > 10) {
      digits = digits.substring(0, 10);
    }

    final formatted = _formatDigits(digits);
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }

  static String _formatDigits(String d) {
    if (d.isEmpty) return '+7';
    final b = StringBuffer('+7 (');
    b.write(d.substring(0, d.length >= 3 ? 3 : d.length));
    if (d.length <= 3) {
      if (d.length < 3) return b.toString();
      return '$b)';
    }
    b.write(') ');
    final mid = d.substring(3, d.length >= 6 ? 6 : d.length);
    b.write(mid);
    if (d.length <= 6) return b.toString();
    b.write('-');
    final tail = d.substring(6, d.length >= 8 ? 8 : d.length);
    b.write(tail);
    if (d.length <= 8) return b.toString();
    b.write('-');
    b.write(d.substring(8));
    return b.toString();
  }

  /// Нормализация для API (+7XXXXXXXXXX).
  static String toApiPhone(String masked) {
    var digits = masked.replaceAll(RegExp(r'\D'), '');
    if (digits.startsWith('8')) digits = '7${digits.substring(1)}';
    if (!digits.startsWith('7') && digits.length == 10) {
      digits = '7$digits';
    }
    if (digits.startsWith('7')) return '+$digits';
    return masked.trim();
  }

  static bool isComplete(String masked) {
    final digits = masked.replaceAll(RegExp(r'\D'), '');
    if (digits.startsWith('7')) return digits.length == 11;
    return digits.length == 10;
  }
}

/// Ровно 4 цифры SMS.
class SmsCodeMaskFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    final trimmed = digits.length > 4 ? digits.substring(0, 4) : digits;
    return TextEditingValue(
      text: trimmed,
      selection: TextSelection.collapsed(offset: trimmed.length),
    );
  }

  static bool isComplete(String code) => code.replaceAll(RegExp(r'\D'), '').length == 4;
}

/// 6 цифр TOTP.
class TotpCodeMaskFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    final trimmed = digits.length > 6 ? digits.substring(0, 6) : digits;
    return TextEditingValue(
      text: trimmed,
      selection: TextSelection.collapsed(offset: trimmed.length),
    );
  }

  static bool isComplete(String code) => code.replaceAll(RegExp(r'\D'), '').length == 6;
}

InputDecoration phoneInputDecoration({String? error}) => InputDecoration(
      labelText: 'Телефон',
      hintText: '+7 (___) ___-__-__',
      errorText: error,
    );

InputDecoration smsCodeDecoration({String? error}) => InputDecoration(
      labelText: 'Код из SMS',
      hintText: '••••',
      counterText: '',
      errorText: error,
    );
