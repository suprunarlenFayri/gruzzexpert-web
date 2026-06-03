import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/api/auth_api.dart';
import '../../core/storage/secure_storage.dart';
import '../../services/notification_service.dart';
import '../../widgets/input_masks.dart';
import '../../widgets/totp_code_field.dart';
import '../home/home_shell.dart';

class CreatorLoginScreen extends StatefulWidget {
  const CreatorLoginScreen({super.key, required this.storage, required this.apiClient});

  final SecureStorage storage;
  final ApiClient apiClient;

  @override
  State<CreatorLoginScreen> createState() => _CreatorLoginScreenState();
}

class _CreatorLoginScreenState extends State<CreatorLoginScreen> {
  final _emailCtrl = TextEditingController();
  final _totpCtrl = TextEditingController();
  final _backupCtrl = TextEditingController();
  bool _totpRequired = false;
  bool _useBackup = false;
  bool _totpValid = false;
  bool _loading = false;
  String? _error;

  late final AuthApi _auth = AuthApi(widget.apiClient, widget.storage);

  Future<void> _checkEmail() async {
    final email = _emailCtrl.text.trim().toLowerCase();
    if (email.isEmpty) return;
    try {
      final data = await _auth.creatorCheck(email);
      setState(() => _totpRequired = data['totp_required'] == true || data['creator'] == true);
    } catch (_) {}
  }

  Future<void> _submit() async {
    if (!_useBackup && !TotpCodeMaskFormatter.isComplete(_totpCtrl.text)) {
      setState(() => _error = 'Введите 6 цифр TOTP');
      return;
    }
    if (_useBackup && _backupCtrl.text.trim().isEmpty) {
      setState(() => _error = 'Введите резервный код');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _auth.creatorLogin(
        email: _emailCtrl.text.trim().toLowerCase(),
        totpCode: _useBackup ? null : _totpCtrl.text.trim(),
        backupCode: _useBackup ? _backupCtrl.text.trim() : null,
      );
      if (data['ok'] == true) {
        await _auth.persistLoginResponse(data);
        try {
          await NotificationService.instance.bindAuth(_auth);
        } catch (e) {
          debugPrint('[CreatorLogin] FCM bindAuth пропущен: $e');
        }
        if (!mounted) return;
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(
            builder: (_) => HomeShell(
              storage: widget.storage,
              apiClient: widget.apiClient,
            ),
          ),
          (_) => false,
        );
        return;
      }
      setState(() => _error = data['error'] as String? ?? 'Ошибка входа');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final showTotp = _totpRequired || _emailCtrl.text.isNotEmpty;

    return Scaffold(
      appBar: AppBar(title: const Text('Вход создателя')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(
            controller: _emailCtrl,
            decoration: const InputDecoration(labelText: 'Email'),
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            onSubmitted: (_) => _checkEmail(),
            onEditingComplete: _checkEmail,
          ),
          if (showTotp) ...[
            const SizedBox(height: 12),
            if (!_useBackup)
              TotpCodeField(
                controller: _totpCtrl,
                autofocus: _totpRequired,
                onValidChanged: (v) => setState(() => _totpValid = v),
              )
            else
              TextField(
                controller: _backupCtrl,
                decoration: const InputDecoration(
                  labelText: 'Резервный код GRZ-XXXX-XXXX',
                ),
                textCapitalization: TextCapitalization.characters,
              ),
            TextButton(
              onPressed: () => setState(() => _useBackup = !_useBackup),
              child: Text(_useBackup ? 'Код из приложения' : 'Резервный код'),
            ),
          ],
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: (_loading || (!_useBackup && showTotp && !_totpValid))
                ? null
                : _submit,
            child: _loading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Войти'),
          ),
        ],
      ),
    );
  }
}
