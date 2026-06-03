import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import '../../core/api/auth_api.dart';
import '../../core/storage/secure_storage.dart';
import '../../services/notification_service.dart';
import '../../widgets/input_masks.dart';
import '../home/home_shell.dart';
import 'creator_login_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.storage, required this.apiClient});

  final SecureStorage storage;
  final ApiClient apiClient;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phoneCtrl = TextEditingController(text: '+7');
  final _passCtrl = TextEditingController();
  final _smsCtrl = TextEditingController();
  String? _smsSession;
  bool _loading = false;
  String? _error;
  String? _phoneError;
  String? _smsError;

  late final AuthApi _auth = AuthApi(widget.apiClient, widget.storage);

  bool _isConnectionError(DioException e) {
    return e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout;
  }

  Future<void> _submit() async {
    final phone = RussianPhoneMaskFormatter.toApiPhone(_phoneCtrl.text);
    if (!RussianPhoneMaskFormatter.isComplete(_phoneCtrl.text)) {
      setState(() => _phoneError = 'Введите номер полностью');
      return;
    }
    if (_smsSession != null && !SmsCodeMaskFormatter.isComplete(_smsCtrl.text)) {
      setState(() => _smsError = 'Нужно 4 цифры');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _phoneError = null;
      _smsError = null;
    });
    try {
      final data = await _auth.login(
        phone: phone,
        password: _passCtrl.text,
        smsSession: _smsSession,
        smsCode: _smsSession != null ? _smsCtrl.text.trim() : null,
      );

      if (data['require_sms'] == true ||
          (data['sms_session'] != null && data['ok'] != true)) {
        setState(() {
          _smsSession = data['sms_session'] as String?;
          _error = data['message'] as String? ?? 'Введите код из SMS';
        });
        return;
      }

      if (data['ok'] == true) {
        await _auth.persistLoginResponse(data);
        try {
          await NotificationService.instance.bindAuth(_auth);
        } catch (e) {
          debugPrint('[Login] FCM bindAuth пропущен, вход продолжается: $e');
        }
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => HomeShell(
              storage: widget.storage,
              apiClient: widget.apiClient,
            ),
          ),
        );
        return;
      }

      setState(() => _error = data['error'] as String? ?? 'Ошибка входа');
    } on DioException catch (e) {
      if (_isConnectionError(e)) {
        setState(() => _error = 'Нет связи с сервером');
        return;
      }
      final body = e.response?.data;
      if (body is Map) {
        final data = Map<String, dynamic>.from(body);
        if (data['require_sms'] == true || data['sms_session'] != null) {
          setState(() {
            _smsSession = data['sms_session'] as String?;
            _error = data['message'] as String? ?? 'Введите код из SMS';
          });
          return;
        }
        setState(() => _error = data['error'] as String? ?? e.message);
      } else {
        setState(() => _error = e.message);
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Вход')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(
            controller: _phoneCtrl,
            decoration: phoneInputDecoration(error: _phoneError),
            keyboardType: TextInputType.phone,
            inputFormatters: [RussianPhoneMaskFormatter()],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _passCtrl,
            decoration: const InputDecoration(labelText: 'Пароль'),
            obscureText: true,
          ),
          if (_smsSession != null) ...[
            const SizedBox(height: 16),
            TextField(
              controller: _smsCtrl,
              decoration: smsCodeDecoration(error: _smsError),
              keyboardType: TextInputType.number,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                SmsCodeMaskFormatter(),
              ],
              autofocus: true,
              maxLength: 4,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 28, letterSpacing: 14),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(_smsSession == null ? 'Продолжить' : 'Подтвердить код'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => CreatorLoginScreen(
                    storage: widget.storage,
                    apiClient: widget.apiClient,
                  ),
                ),
              );
            },
            child: const Text('Вход создателя (email + TOTP)'),
          ),
        ],
      ),
    );
  }
}
