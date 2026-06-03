"""Регистрация и завершение активных сессий входа (таблица user_sessions)."""

from flask import session

from models import UserDevice, UserSession, db
from utils.datetime_utils import utc_now


def _device_label(device_info):
    browser = (device_info or {}).get('browser') or 'Браузер'
    os_name = (device_info or {}).get('os') or 'ОС'
    return f'{browser} · {os_name}'


def register_user_session(user, token, device_info):
    """Создать или обновить запись активной сессии после входа."""
    if not user or not token:
        return None

    now = utc_now()
    ip = (device_info or {}).get('ip')
    label = _device_label(device_info)

    row = UserSession.query.filter_by(user_id=user.id, token=token).first()
    if row:
        row.device_name = label
        row.ip_address = ip
        row.last_active = now
    else:
        row = UserSession(
            user_id=user.id,
            device_name=label,
            ip_address=ip,
            last_active=now,
            token=token,
        )
        db.session.add(row)
    db.session.flush()
    return row


def touch_user_session(user_id, token):
    if not user_id or not token:
        return
    row = UserSession.query.filter_by(user_id=user_id, token=token).first()
    if row:
        row.last_active = utc_now()
        db.session.flush()


def list_user_sessions(user_id):
    return (
        UserSession.query.filter_by(user_id=user_id)
        .order_by(UserSession.last_active.desc())
        .all()
    )


def terminate_other_login_sessions(user, keep_token=None):
    """Удалить все сессии пользователя, кроме текущего токена."""
    if keep_token is None:
        keep_token = session.get('session_token')

    q = UserSession.query.filter_by(user_id=user.id)
    if keep_token:
        q = q.filter(UserSession.token != keep_token)
    return q.delete(synchronize_session=False)


def terminate_login_sessions(user, session_ids=None, keep_token=None, *, commit=True):
    """
    Завершить чужие сессии: без session_ids — все кроме текущей;
    с session_ids — только перечисленные (не текущую).
    """
    if keep_token is None:
        keep_token = session.get('session_token')

    if not session_ids:
        deleted = terminate_other_login_sessions(user, keep_token=keep_token)
    else:
        ids = [int(i) for i in session_ids if i is not None]
        if not ids:
            deleted = 0
        else:
            q = UserSession.query.filter(
                UserSession.user_id == user.id,
                UserSession.id.in_(ids),
            )
            if keep_token:
                q = q.filter(UserSession.token != keep_token)
            deleted = q.delete(synchronize_session=False)

    if commit:
        db.session.commit()
    return deleted


def sessions_for_api(user_id, current_token):
    """Список сессий для API (с fallback на user_devices)."""
    rows = list_user_sessions(user_id)
    if rows:
        return [
            {
                'id': r.id,
                'device_name': r.device_name or 'Устройство',
                'ip_address': r.ip_address,
                'last_active': r.last_active.isoformat() if r.last_active else None,
                'token': r.token,
                'is_current': r.token == current_token,
            }
            for r in rows
        ]

    devices = (
        UserDevice.query.filter_by(user_id=user_id)
        .order_by(UserDevice.last_login.desc())
        .all()
    )
    return [
        {
            'id': d.id,
            'device_name': f'{(d.browser or "Браузер")} · {(d.os or "ОС")}',
            'ip_address': d.ip,
            'last_active': d.last_login.isoformat() if d.last_login else None,
            'token': None,
            'is_current': False,
            'is_legacy_device': True,
        }
        for d in devices
    ]
