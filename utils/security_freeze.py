"""Заморозка баланса и алерты при смене критических данных."""

from datetime import timedelta

from utils.datetime_utils import utc_now

FREEZE_HOURS = 48
DISPATCHER_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher', 'manager')

CHANGE_LABELS = {
    'phone': 'изменение номера телефона',
    'tag': 'изменение системного тега',
    'email': 'изменение email',
    'bank_card': 'изменение банковской карты',
}


def is_balance_frozen(user):
    if not user:
        return False
    if not getattr(user, 'is_frozen', False):
        return False
    frozen_until = getattr(user, 'frozen_until', None)
    if frozen_until and utc_now() >= frozen_until:
        return False
    return True


def apply_security_freeze(user, change_type, *, commit=False):
    """Заморозка вывода средств на 48 часов."""
    from models import db

    if not user:
        return None

    now = utc_now()
    user.is_frozen = True
    user.frozen_until = now + timedelta(hours=FREEZE_HOURS)

    if commit:
        db.session.commit()

    notify_dispatchers_security_alert(user, change_type)
    return user.frozen_until


def notify_dispatchers_security_alert(user, change_type):
    from models import User
    from socketio_instance import send_user_notification

    label = CHANGE_LABELS.get(change_type, change_type)
    title = 'Смена критических данных'
    body = f'{user.name}: {label}. Баланс заморожен на {FREEZE_HOURS} ч.'

    payload = {
        'kind': 'security_alert',
        'title': title,
        'body': body,
        'message': body,
        'change_type': change_type,
        'user_id': user.id,
        'user_name': user.name,
        'workspace_id': user.workspace_id,
    }

    query = User.query.filter(User.role.in_(DISPATCHER_ROLES))
    if user.workspace_id:
        query = query.filter(User.workspace_id == user.workspace_id)

    for dispatcher in query.all():
        if dispatcher.id == user.id:
            continue
        send_user_notification(dispatcher.id, payload)
