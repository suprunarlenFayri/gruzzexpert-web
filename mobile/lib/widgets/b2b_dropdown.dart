import 'package:flutter/material.dart';

import '../core/theme/b2b_colors.dart';
import '../core/theme/b2b_theme.dart';

/// Monolithic B2B dropdown — mirrors web `.b2b-select` (Density UI).
class B2bDropdownItem<T> {
  const B2bDropdownItem({required this.value, required this.label});

  final T value;
  final String label;
}

class B2bDropdown<T> extends StatefulWidget {
  const B2bDropdown({
    super.key,
    required this.items,
    this.value,
    this.onChanged,
    this.hint = 'Выберите…',
    this.enabled = true,
  });

  final List<B2bDropdownItem<T>> items;
  final T? value;
  final ValueChanged<T?>? onChanged;
  final String hint;
  final bool enabled;

  @override
  State<B2bDropdown<T>> createState() => _B2bDropdownState<T>();
}

class _B2bDropdownState<T> extends State<B2bDropdown<T>>
    with SingleTickerProviderStateMixin {
  static const _duration = Duration(milliseconds: 150);
  static const _curve = Curves.easeOutCubic;

  bool _open = false;
  late final AnimationController _controller;
  late final Animation<double> _expand;
  late final Animation<double> _arrowTurns;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: _duration);
    _expand = CurvedAnimation(parent: _controller, curve: _curve);
    _arrowTurns = Tween<double>(begin: 0, end: 0.5).animate(_expand);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  B2bDropdownItem<T>? get _selected {
    if (widget.value == null) return null;
    for (final item in widget.items) {
      if (item.value == widget.value) return item;
    }
    return null;
  }

  void _toggle() {
    if (!widget.enabled) return;
    setState(() => _open = !_open);
    if (_open) {
      _controller.forward();
    } else {
      _controller.reverse();
    }
  }

  void _close() {
    if (!_open) return;
    setState(() => _open = false);
    _controller.reverse();
  }

  void _select(B2bDropdownItem<T> item) {
    widget.onChanged?.call(item.value);
    _close();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final border = isDark ? B2bColors.darkBorder : B2bColors.lightBorder;
    final fill = isDark ? B2bColors.darkInputFill : B2bColors.lightInputFill;
    final hover = isDark
        ? B2bColors.dropdownHoverDark()
        : B2bColors.dropdownHoverLight();
    final textPrimary =
        isDark ? B2bColors.darkTextPrimary : B2bColors.lightTextPrimary;
    final selected = _selected;

    return RepaintBoundary(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: widget.enabled ? _toggle : null,
              borderRadius: _open
                  ? const BorderRadius.vertical(top: Radius.circular(8))
                  : B2bTheme.radius8,
              child: AnimatedContainer(
                duration: _duration,
                curve: _curve,
                height: 44,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(
                  color: fill,
                  borderRadius: _open
                      ? const BorderRadius.vertical(top: Radius.circular(8))
                      : B2bTheme.radius8,
                  border: Border(
                    top: BorderSide(color: border),
                    left: BorderSide(color: border),
                    right: BorderSide(color: border),
                    bottom: _open
                        ? BorderSide.none
                        : BorderSide(color: border),
                  ),
                  boxShadow: _open
                      ? [
                          BoxShadow(
                            color: B2bColors.accent.withOpacity(0.35),
                            blurRadius: 0,
                            spreadRadius: 2,
                          ),
                        ]
                      : null,
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        selected?.label ?? widget.hint,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: selected != null
                              ? textPrimary
                              : (isDark
                                  ? B2bColors.darkTextSecondary
                                  : B2bColors.lightTextSecondary),
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    RotationTransition(
                      turns: _arrowTurns,
                      child: Icon(
                        Icons.keyboard_arrow_down_rounded,
                        size: 22,
                        color: textPrimary.withOpacity(0.65),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          ClipRRect(
            borderRadius: const BorderRadius.vertical(
              bottom: Radius.circular(8),
            ),
            clipBehavior: Clip.antiAlias,
            child: SizeTransition(
              sizeFactor: _expand,
              axisAlignment: -1,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: fill,
                  border: Border(
                    left: BorderSide(color: border),
                    right: BorderSide(color: border),
                    bottom: BorderSide(color: border),
                  ),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (var i = 0; i < widget.items.length; i++)
                      _B2bDropdownOption<T>(
                        item: widget.items[i],
                        selected: widget.value == widget.items[i].value,
                        hoverColor: hover,
                        textColor: textPrimary,
                        onTap: widget.enabled
                            ? () => _select(widget.items[i])
                            : null,
                      ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _B2bDropdownOption<T> extends StatelessWidget {
  const _B2bDropdownOption({
    required this.item,
    required this.selected,
    required this.hoverColor,
    required this.textColor,
    this.onTap,
  });

  final B2bDropdownItem<T> item;
  final bool selected;
  final Color hoverColor;
  final Color textColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? hoverColor : Colors.transparent,
      child: InkWell(
        onTap: onTap,
        splashColor: hoverColor.withOpacity(0.4),
        highlightColor: hoverColor,
        child: Ink(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: selected ? hoverColor : null,
          ),
          child: Text(
            item.label,
            style: TextStyle(
              color: selected ? Colors.white : textColor,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }
}