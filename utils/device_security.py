"""Проверка устройств и 2FA при входе b2b-пользователей."""

import hashlib
import random
import re

from utils.datetime_utils import utc_now

B2B_LOGIN_ROLES = frozenset({
    'creator', 'director', 'senior_dispatcher', 'dispatcher', 'manager', 'brigadir',
})


def resolve_device_hash(request):
    """Хэш устройства из заголовка/формы или fallback по UA+IP."""
    payload = request.get_json(silent=True) or {}
    explicit = (
        request.headers.get('X-Device-Hash')
        or request.form.get('device_hash')
        or payload.get('device_hash')
    )
    if explicit:
        return str(explicit).strip()

    ua = request.headers.get('User-Agent', '')
    ip = request.remote_addr or ''
    raw = f'{ua}|{ip}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _detect_browser(user_agent):
    ua = (user_agent or '').lower()
    if 'edg/' in ua or 'edge/' in ua:
        return 'Edge'
    if 'chrome/' in ua and 'chromium' not in ua:
        return 'Chrome'
    if 'firefox/' in ua:
        return 'Firefox'
    if 'safari/' in ua and 'chrome' not in ua:
        return 'Safari'
    if 'opr/' in ua or 'opera' in ua:
        return 'Opera'
    return 'Браузер'


def _detect_os(user_agent):
    ua = (user_agent or '').lower()
    if 'windows' in ua:
        return 'Windows'
    if 'mac os' in ua or 'macintosh' in ua:
        return 'macOS'
    if 'android' in ua:
        return 'Android'
    if 'iphone' in ua or 'ipad' in ua or 'ios' in ua:
        return 'iOS'
    if 'linux' in ua:
        return 'Linux'
    return 'ОС'


def parse_client_info(request):
    ua = request.headers.get('User-Agent', '')
    return {
        'browser': _detect_browser(ua),
        'os': _detect_os(ua),
        'ip': request.remote_addr,
        'user_agent': ua[:255] if ua else None,
    }


def is_trusted_device(user_id, device_hash):
    from models import UserDevice

    if not user_id or not device_hash:
        return False
    return (
        UserDevice.query.filter_by(
            user_id=user_id,
            device_hash=device_hash,
            is_trusted=True,
        ).first()
        is not None
    )


def user_has_active_sessions(user):
    if not user:
        return False
    if user.current_desktop_token or user.current_mobile_token:
        return True

    from models import UserDevice

    return (
        UserDevice.query.filter_by(user_id=user.id, is_trusted=True).count() > 0
    )


def needs_device_2fa(user, device_hash):
    from utils.creator_auth import is_creator_account

    if not user or (user.role or '') not in B2B_LOGIN_ROLES:
        return False
    if is_creator_account(user):
        return False
    if is_trusted_device(user.id, device_hash):
        return False
    return user_has_active_sessions(user)


def generate_mock_2fa_codes():
    return {
        'sms_code': f'{random.randint(100000, 999999)}',
        'email_code': f'{random.randint(100000, 999999)}',
    }


def register_trusted_device(user, device_hash, device_info):
    from models import db, UserDevice

    if not user or not device_hash:
        return None

    device = UserDevice.query.filter_by(user_id=user.id, device_hash=device_hash).first()
    now = utc_now()
    if device:
        device.last_login = now
        device.browser = device_info.get('browser')
        device.os = device_info.get('os')
        device.ip = device_info.get('ip')
        device.is_trusted = True
    else:
        device = UserDevice(
            user_id=user.id,
            device_hash=device_hash,
            browser=device_info.get('browser'),
            os=device_info.get('os'),
            ip=device_info.get('ip'),
            last_login=now,
            is_trusted=True,
        )
        db.session.add(device)
    db.session.commit()
    return device


def notify_login_attempt(user, device_info, attempt_token=None):
    from socketio_instance import send_user_notification

    browser = device_info.get('browser') or 'Браузер'
    os_name = device_info.get('os') or 'ОС'
    ip = device_info.get('ip') or '—'

    send_user_notification(user.id, {
        'kind': 'login_attempt',
        'title': 'Внимание! Попытка входа с нового устройства',
        'body': f'{browser}, {os_name}, IP: {ip}. Это вы?',
        'message': f'Попытка входа: {browser} / {os_name} (IP: {ip})',
        'browser': browser,
        'os': os_name,
        'ip': ip,
        'attempt_id': attempt_token,
        'attempt_token': attempt_token,
        'actions': [
            {'id': 'block_session', 'label': 'Заблокировать сессию', 'attempt_id': attempt_token},
        ],
    })


def normalize_2fa_code(raw):
    if raw is None:
        return ''
    return re.sub(r'\D', '', str(raw).strip())
