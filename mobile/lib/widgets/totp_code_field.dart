import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme/b2b_colors.dart';
import 'input_masks.dart';

/// 6 ячеек TOTP (Google Authenticator): автофокус, валидация на лету.
class TotpCodeField extends StatefulWidget {
  const TotpCodeField({
    super.key,
    required this.controller,
    this.autofocus = false,
    this.onValidChanged,
  });

  final TextEditingController controller;
  final bool autofocus;
  final ValueChanged<bool>? onValidChanged;

  @override
  State<TotpCodeField> createState() => _TotpCodeFieldState();
}

class _TotpCodeFieldState extends State<TotpCodeField> {
  final _focus = FocusNode();
  final _hidden = TextEditingController();
  bool _touched = false;

  @override
  void initState() {
    super.initState();
    _hidden.text = widget.controller.text;
    _hidden.addListener(_syncFromHidden);
    widget.controller.addListener(_syncToHidden);
    if (widget.autofocus) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _focus.requestFocus();
      });
    }
  }

  void _syncFromHidden() {
    final digits = _hidden.text.replaceAll(RegExp(r'\D'), '');
    final trimmed = digits.length > 6 ? digits.substring(0, 6) : digits;
    if (widget.controller.text != trimmed) {
      widget.controller.text = trimmed;
    }
    widget.onValidChanged?.call(TotpCodeMaskFormatter.isComplete(trimmed));
    if (mounted) setState(() {});
  }

  void _syncToHidden() {
    if (_hidden.text != widget.controller.text) {
      _hidden.text = widget.controller.text;
      _hidden.selection = TextSelection.collapsed(offset: _hidden.text.length);
    }
  }

  @override
  void dispose() {
    _hidden.removeListener(_syncFromHidden);
    widget.controller.removeListener(_syncToHidden);
    _hidden.dispose();
    _focus.dispose();
    super.dispose();
  }

  String? get _error {
    if (!_touched) return null;
    final len = widget.controller.text.length;
    if (len == 0) return 'Введите 6 цифр из приложения';
    if (len < 6) return 'Осталось ${6 - len}';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final code = widget.controller.text;
    final valid = TotpCodeMaskFormatter.isComplete(code);
    final focused = _focus.hasFocus;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Код из Google Authenticator',
          style: TextStyle(fontSize: 13, color: B2bColors.darkTextSecondary),
        ),
        const SizedBox(height: 12),
        GestureDetector(
          onTap: () => _focus.requestFocus(),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: List.generate(6, (i) {
                  final char = i < code.length ? code[i] : '';
                  final filled = char.isNotEmpty;
                  final active = focused && i == code.length;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    width: 46,
                    height: 52,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: B2bColors.darkInputFill,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: active
                            ? B2bColors.accentLight
                            : filled
                                ? B2bColors.accent.withOpacity(0.5)
                                : B2bColors.darkBorder,
                        width: active ? 2 : 1,
                      ),
                      boxShadow: active
                          ? [
                              BoxShadow(
                                color: B2bColors.accentLight.withOpacity(0.25),
                                blurRadius: 8,
                              ),
                            ]
                          : null,
                    ),
                    child: Text(
                      char,
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0,
                      ),
                    ),
                  );
                }),
              ),
              Opacity(
                opacity: 0.01,
                child: TextField(
                  controller: _hidden,
                  focusNode: _focus,
                  autofocus: widget.autofocus,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    TotpCodeMaskFormatter(),
                  ],
                  onTap: () => setState(() => _touched = true),
                  onChanged: (_) => setState(() => _touched = true),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            if (valid)
              const Icon(Icons.check_circle, color: Colors.greenAccent, size: 18),
            if (valid) const SizedBox(width: 6),
            Expanded(
              child: Text(
                valid ? 'Код принят' : (_error ?? '6 цифр'),
                style: TextStyle(
                  fontSize: 12,
                  color: _error != null
                      ? Theme.of(context).colorScheme.error
                      : B2bColors.darkTextSecondary,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
