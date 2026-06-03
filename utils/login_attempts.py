"""Серверное хранение попыток входа с нового устройства (для блокировки с активных сессий)."""

import secrets
import uuid
from datetime import timedelta

from utils.datetime_utils import utc_now

ATTEMPT_TTL_MINUTES = 15


def _expires_at():
    return utc_now() + timedelta(minutes=ATTEMPT_TTL_MINUTES)


def create_login_attempt(user, device_hash, device_info, sms_code, email_code):
    from models import db, PendingLoginAttempt

    attempt_token = secrets.token_urlsafe(24)
    attempt = PendingLoginAttempt(
        user_id=user.id,
        attempt_token=attempt_token,
        device_hash=device_hash or '',
        browser=(device_info or {}).get('browser'),
        os=(device_info or {}).get('os'),
        ip=(device_info or {}).get('ip'),
        sms_code=sms_code,
        email_code=email_code,
        status='pending',
        expires_at=_expires_at(),
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def get_attempt_by_token(token):
    from models import PendingLoginAttempt

    if not token:
        return None
    attempt = PendingLoginAttempt.query.filter_by(attempt_token=token).first()
    if not attempt:
        return None
    if attempt.expires_at and utc_now() > attempt.expires_at:
        if attempt.status == 'pending':
            attempt.status = 'expired'
            from models import db
            db.session.commit()
        return None
    return attempt


def block_attempt(user_id, attempt_token):
    from models import db, PendingLoginAttempt

    attempt = PendingLoginAttempt.query.filter_by(
        user_id=user_id,
        attempt_token=attempt_token,
    ).first()
    if not attempt or attempt.status != 'pending':
        return False
    attempt.status = 'blocked'
    db.session.commit()
    return True


def complete_attempt(attempt):
    from models import db

    if not attempt:
        return
    attempt.status = 'completed'
    db.session.commit()


def revoke_other_sessions(user, keep_device_hash=None):
    """Завершить все сессии, кроме текущего устройства."""
    from flask import session
    from models import db, UserDevice

    token = uuid.uuid4().hex
    device_type = session.get('device_type', 'desktop')

    if device_type == 'mobile':
        user.current_mobile_token = token
        user.current_desktop_token = None
    else:
        user.current_desktop_token = token
        user.current_mobile_token = None

    session['session_token'] = token

    q = UserDevice.query.filter_by(user_id=user.id, is_trusted=True)
    if keep_device_hash:
        q = q.filter(UserDevice.device_hash != keep_device_hash)
    q.update({'is_trusted': False}, synchronize_session=False)

    from utils.user_login_sessions import terminate_other_login_sessions

    terminate_other_login_sessions(user, keep_token=token)
    db.session.commit()
    return token
