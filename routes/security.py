"""B2B-безопасность: смена телефона, сессии, блокировка входа."""

import random
import re

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required

from models import PhoneRecoveryTicket, User, db
from utils.device_security import normalize_2fa_code, parse_client_info, resolve_device_hash
from utils.login_attempts import block_attempt, revoke_other_sessions
from utils.user_login_sessions import sessions_for_api, terminate_login_sessions
from utils.security_freeze import apply_security_freeze, is_balance_frozen

security_bp = Blueprint('security', __name__)


def _generate_code():
    return f'{random.randint(100000, 999999)}'


def _normalize_tag(raw):
    if raw is None:
        return None
    tag = str(raw).strip()
    if not tag:
        return None
    if tag.startswith('@'):
        tag = tag[1:].strip()
    return tag or None


def _normalize_phone(raw):
    if not raw:
        return None
    digits = re.sub(r'\D', '', str(raw).strip())
    if len(digits) < 10:
        return None
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    if not digits.startswith('7') and len(digits) == 10:
        digits = '7' + digits
    return '+' + digits if not str(raw).strip().startswith('+') else str(raw).strip()


@security_bp.route('/api/request-phone-change', methods=['POST'])
@login_required
def request_phone_change():
    data = request.get_json(silent=True) or {}
    action = (data.get('action') or 'init').strip().lower()

    if action == 'recovery':
        new_phone = _normalize_phone(data.get('new_phone'))
        if not new_phone:
            return jsonify({'status': 'error', 'error': 'Укажите новый номер телефона'}), 400
        ticket = PhoneRecoveryTicket(
            user_id=current_user.id,
            old_phone=current_user.phone,
            new_phone=new_phone,
            comment=(data.get('comment') or '').strip() or None,
            status='pending',
            workspace_id=current_user.workspace_id,
        )
        db.session.add(ticket)
        db.session.commit()
        return jsonify({
            'status': 'ticket_created',
            'message': 'Заявка на восстановление отправлена диспетчеру',
        })

    if action == 'send_email':
        pending = session.get('phone_change_pending')
        if not pending:
            return jsonify({'status': 'error', 'error': 'Сначала запросите коды'}), 400
        email_code = _generate_code()
        pending['email_code'] = email_code
        pending['email_sent'] = True
        session['phone_change_pending'] = pending
        return jsonify({
            'status': 'email_sent',
            'message': 'Код отправлен на привязанную почту (режим разработки)',
            'mock_codes': {'email': email_code},
        })

    if action == 'init':
        new_phone = _normalize_phone(data.get('new_phone'))
        if not new_phone:
            return jsonify({'status': 'error', 'error': 'Укажите корректный новый номер'}), 400
        if new_phone == current_user.phone:
            return jsonify({'status': 'error', 'error': 'Новый номер совпадает с текущим'}), 400
        if User.query.filter(User.phone == new_phone, User.id != current_user.id).first():
            return jsonify({'status': 'error', 'error': 'Этот номер уже используется'}), 400

        codes = {
            'old_sms_code': _generate_code(),
            'new_sms_code': _generate_code(),
            'email_code': _generate_code(),
        }
        session['phone_change_pending'] = {
            'new_phone': new_phone,
            'email_sent': True,
            **codes,
        }
        return jsonify({
            'status': 'codes_sent',
            'message': 'Коды отправлены (режим разработки)',
            'mock_codes': {
                'old_sms': codes['old_sms_code'],
                'new_sms': codes['new_sms_code'],
                'email': codes['email_code'],
            },
        })

    if action == 'confirm':
        pending = session.get('phone_change_pending')
        if not pending:
            return jsonify({'status': 'error', 'error': 'Сессия смены номера истекла'}), 400

        old_code = normalize_2fa_code(data.get('old_sms_code'))
        new_code = normalize_2fa_code(data.get('new_sms_code'))
        email_code = normalize_2fa_code(data.get('email_code'))

        if not old_code or not new_code or not email_code:
            return jsonify({'status': 'error', 'error': 'Заполните все три кода'}), 400

        if old_code != normalize_2fa_code(pending.get('old_sms_code')):
            return jsonify({'status': 'error', 'error': 'Неверный код со старого номера'}), 403
        if new_code != normalize_2fa_code(pending.get('new_sms_code')):
            return jsonify({'status': 'error', 'error': 'Неверный код с нового номера'}), 403
        if email_code != normalize_2fa_code(pending.get('email_code')):
            return jsonify({'status': 'error', 'error': 'Неверный email-код'}), 403

        new_phone = pending.get('new_phone')
        if not new_phone:
            return jsonify({'status': 'error', 'error': 'Новый номер не найден в сессии'}), 400

        current_user.phone = new_phone
        apply_security_freeze(current_user, 'phone')
        db.session.commit()
        session.pop('phone_change_pending', None)

        return jsonify({'status': 'success', 'phone': new_phone})

    return jsonify({'status': 'error', 'error': 'Неизвестное действие'}), 400


@security_bp.route('/api/request-tag-change', methods=['POST'])
@login_required
def request_tag_change():
    data = request.get_json(silent=True) or {}
    action = (data.get('action') or 'init').strip().lower()

    if action == 'recovery':
        new_tag = _normalize_tag(data.get('new_tag'))
        if not new_tag:
            return jsonify({'status': 'error', 'error': 'Укажите новый тег'}), 400
        ticket = PhoneRecoveryTicket(
            user_id=current_user.id,
            old_phone=current_user.phone,
            new_phone=current_user.phone,
            comment=f'Запрос смены тега на @{new_tag}',
            status='pending',
            workspace_id=current_user.workspace_id,
        )
        db.session.add(ticket)
        db.session.commit()
        return jsonify({
            'status': 'ticket_created',
            'message': 'Заявка на восстановление отправлена диспетчеру',
        })

    if action == 'send_email':
        pending = session.get('tag_change_pending')
        if not pending:
            return jsonify({'status': 'error', 'error': 'Сначала запросите коды'}), 400
        email_code = _generate_code()
        pending['email_code'] = email_code
        pending['email_sent'] = True
        session['tag_change_pending'] = pending
        return jsonify({
            'status': 'email_sent',
            'message': 'Код отправлен на привязанную почту (режим разработки)',
            'mock_codes': {'email': email_code},
        })

    if action == 'init':
        new_tag = _normalize_tag(data.get('new_tag'))
        if not new_tag:
            return jsonify({'status': 'error', 'error': 'Укажите корректный новый тег'}), 400
        if new_tag == (current_user.tag or ''):
            return jsonify({'status': 'error', 'error': 'Новый тег совпадает с текущим'}), 400
        if User.query.filter(User.tag == new_tag, User.id != current_user.id).first():
            return jsonify({'status': 'error', 'error': 'Этот тег уже занят, придумайте другой'}), 400

        codes = {
            'old_sms_code': _generate_code(),
            'new_sms_code': _generate_code(),
            'email_code': _generate_code(),
        }
        session['tag_change_pending'] = {
            'new_tag': new_tag,
            'email_sent': True,
            **codes,
        }
        return jsonify({
            'status': 'codes_sent',
            'message': 'Коды отправлены (режим разработки)',
            'mock_codes': {
                'old_sms': codes['old_sms_code'],
                'new_sms': codes['new_sms_code'],
                'email': codes['email_code'],
            },
        })

    if action == 'confirm':
        pending = session.get('tag_change_pending')
        if not pending:
            return jsonify({'status': 'error', 'error': 'Сессия смены тега истекла'}), 400

        old_code = normalize_2fa_code(data.get('old_sms_code'))
        new_code = normalize_2fa_code(data.get('new_sms_code'))
        email_code = normalize_2fa_code(data.get('email_code'))

        if not old_code or not new_code or not email_code:
            return jsonify({'status': 'error', 'error': 'Заполните все три кода'}), 400

        if old_code != normalize_2fa_code(pending.get('old_sms_code')):
            return jsonify({'status': 'error', 'error': 'Неверный код со старого номера'}), 403
        if new_code != normalize_2fa_code(pending.get('new_sms_code')):
            return jsonify({'status': 'error', 'error': 'Неверный код с нового номера'}), 403
        if email_code != normalize_2fa_code(pending.get('email_code')):
            return jsonify({'status': 'error', 'error': 'Неверный email-код'}), 403

        new_tag = pending.get('new_tag')
        if not new_tag:
            return jsonify({'status': 'error', 'error': 'Новый тег не найден в сессии'}), 400

        current_user.tag = new_tag
        apply_security_freeze(current_user, 'tag')
        db.session.commit()
        session.pop('tag_change_pending', None)

        return jsonify({'status': 'success', 'tag': new_tag})

    return jsonify({'status': 'error', 'error': 'Неизвестное действие'}), 400


@security_bp.route('/api/security/block-login-attempt', methods=['POST'])
@login_required
def block_login_attempt_api():
    data = request.get_json(silent=True) or {}
    attempt_token = (data.get('attempt_id') or data.get('attempt_token') or '').strip()
    if not attempt_token:
        return jsonify({'ok': False, 'error': 'Не указана попытка входа'}), 400

    if not block_attempt(current_user.id, attempt_token):
        return jsonify({'ok': False, 'error': 'Попытка не найдена или уже обработана'}), 404

    return jsonify({'ok': True, 'message': 'Попытка входа заблокирована'})


@security_bp.route('/api/sessions', methods=['GET'])
@login_required
def list_sessions():
    current_token = session.get('session_token')
    items = sessions_for_api(current_user.id, current_token)
    return jsonify({
        'ok': True,
        'sessions': items,
        'is_frozen': is_balance_frozen(current_user),
        'frozen_until': current_user.frozen_until.isoformat() if current_user.frozen_until else None,
        'balance': float(current_user.balance or 0),
    })


@security_bp.route('/api/sessions/terminate', methods=['POST'])
@login_required
def terminate_sessions_api():
    data = request.get_json(silent=True) or {}
    session_ids = data.get('session_ids')
    device_hash = resolve_device_hash(request)
    current_token = session.get('session_token')

    if session_ids:
        terminate_login_sessions(
            current_user,
            session_ids=session_ids,
            keep_token=current_token,
        )
    else:
        terminate_login_sessions(current_user, keep_token=current_token)
        revoke_other_sessions(current_user, keep_device_hash=device_hash)

    return jsonify({'ok': True, 'message': 'Сессии завершены'})


@security_bp.route('/api/sessions/revoke-others', methods=['POST'])
@login_required
def revoke_other_sessions_api():
    """Обратная совместимость: делегирует в terminate."""
    return terminate_sessions_api()
