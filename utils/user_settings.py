"""Пользовательские настройки: defaults, privacy, sleep mode."""

import re
from copy import deepcopy
from datetime import timedelta

from models import ChatParticipant, User, db
from utils.datetime_utils import utc_iso, utc_now

STAFF_ROLES = frozenset({'creator', 'director', 'senior_dispatcher', 'dispatcher'})
ADMIN_PRIVACY_OVERRIDE_ROLES = frozenset({
    'creator', 'director', 'senior_dispatcher', 'dispatcher', 'manager', 'brigadir',
})
WORKER_ROLES = frozenset({'worker', 'brigadir'})
PRIVACY_LEVELS = frozenset({'everyone', 'contacts', 'nobody'})
PHONE_PRIVACY_LEVELS = frozenset({'all', 'contacts', 'none'})
PRIVACY_SETTING_KEYS = frozenset({
    'privacy_phone_visibility',
    'privacy_phone_search',
    'privacy_birth_visibility',
})
WORKER_NOTIFY_KEYS = frozenset({'notify_new_tasks', 'notify_status_changes', 'notify_system_alerts'})
PROFILE_COLUMN_KEYS = frozenset({'username', 'send_by_enter', 'phone_privacy'})

DEFAULT_USER_SETTINGS = {
    'privacy_phone_visibility': 'everyone',
    'privacy_phone_search': 'everyone',
    'privacy_birth_visibility': 'everyone',
    'phone_privacy': 'contacts',
    'chat_sound_enabled': True,
    'chat_send_on_enter': True,
    'send_by_enter': True,
    'notify_new_tasks': True,
    'notify_status_changes': True,
    'notify_system_alerts': True,
}

SETTING_KEYS = frozenset(DEFAULT_USER_SETTINGS.keys()) | PROFILE_COLUMN_KEYS


def _phone_privacy_to_visibility(level):
    mapping = {'all': 'everyone', 'contacts': 'contacts', 'none': 'nobody'}
    return mapping.get(level, 'everyone')


def _visibility_to_phone_privacy(level):
    mapping = {'everyone': 'all', 'contacts': 'contacts', 'nobody': 'none', 'staff': 'contacts'}
    return mapping.get(level, 'contacts')


def is_worker_role(user):
    return (getattr(user, 'role', None) or '') in WORKER_ROLES


def privacy_admin_override(viewer):
    """Диспетчеры и руководство всегда видят данные исполнителей."""
    return (getattr(viewer, 'role', None) or '') in ADMIN_PRIVACY_OVERRIDE_ROLES


def is_staff_role(user):
    return (getattr(user, 'role', None) or '') in STAFF_ROLES


def _normalize_privacy_level(value):
    if value == 'staff':
        return 'contacts'
    if value in PRIVACY_LEVELS:
        return value
    return 'everyone'


def _normalize_phone_privacy(value):
    if value in PHONE_PRIVACY_LEVELS:
        return value
    legacy = _visibility_to_phone_privacy(_normalize_privacy_level(value))
    return legacy if legacy in PHONE_PRIVACY_LEVELS else 'contacts'


def _normalize_username(raw):
    if raw is None:
        return None
    name = str(raw).strip().lower()
    if not name:
        return None
    if name.startswith('@'):
        name = name[1:].strip()
    if not name:
        return None
    if not re.match(r'^[a-z0-9_]{3,32}$', name):
        raise ValueError('Юзернейм: 3–32 символа, латиница, цифры и _')
    return name


def _normalize_settings(raw):
    if not raw or not isinstance(raw, dict):
        return {}
    normalized = {}
    for key, value in raw.items():
        if key not in SETTING_KEYS:
            continue
        if key in PRIVACY_SETTING_KEYS:
            normalized[key] = _normalize_privacy_level(value)
        else:
            normalized[key] = value
    return normalized


def _sync_phone_privacy_column(user, phone_privacy):
    user.phone_privacy = phone_privacy
    current = _normalize_settings(getattr(user, 'settings', None))
    current['privacy_phone_visibility'] = _phone_privacy_to_visibility(phone_privacy)
    user.settings = current


def _sync_send_by_enter_column(user, enabled):
    user.send_by_enter = bool(enabled)
    current = _normalize_settings(getattr(user, 'settings', None))
    current['chat_send_on_enter'] = bool(enabled)
    user.settings = current


def _are_contacts(user_a, user_b):
    if not user_a or not user_b or user_a.id == user_b.id:
        return user_a and user_b and user_a.id == user_b.id
    chat_ids_a = (
        db.session.query(ChatParticipant.chat_id)
        .filter(ChatParticipant.user_id == user_a.id)
        .subquery()
    )
    return (
        ChatParticipant.query.filter(
            ChatParticipant.chat_id.in_(chat_ids_a),
            ChatParticipant.user_id == user_b.id,
        ).first()
        is not None
    )


def clear_expired_task_mute(user):
    until = getattr(user, 'tasks_muted_until', None)
    if until and utc_now() >= until:
        user.tasks_muted_until = None
        return True
    return False


def is_user_tasks_muted(user):
    if not user:
        return False
    clear_expired_task_mute(user)
    until = getattr(user, 'tasks_muted_until', None)
    return bool(until and utc_now() < until)


def tasks_muted_until_iso(user):
    clear_expired_task_mute(user)
    until = getattr(user, 'tasks_muted_until', None)
    if until and utc_now() < until:
        return utc_iso(until)
    return None


def set_tasks_sleep_mode(user, enabled):
    if not is_worker_role(user):
        raise ValueError('Sleep mode доступен только исполнителям')
    if enabled:
        user.tasks_muted_until = utc_now() + timedelta(hours=24)
    else:
        user.tasks_muted_until = None
    return tasks_muted_until_iso(user)


def should_receive_task_notification(user):
    if is_worker_role(user) and is_user_tasks_muted(user):
        return False
    return True


def get_user_settings(user):
    merged = deepcopy(DEFAULT_USER_SETTINGS)
    merged.update(_normalize_settings(getattr(user, 'settings', None)))

    phone_privacy = getattr(user, 'phone_privacy', None)
    if phone_privacy:
        merged['phone_privacy'] = _normalize_phone_privacy(phone_privacy)
        merged['privacy_phone_visibility'] = _phone_privacy_to_visibility(merged['phone_privacy'])
    elif merged.get('privacy_phone_visibility'):
        merged['phone_privacy'] = _visibility_to_phone_privacy(merged['privacy_phone_visibility'])

    if getattr(user, 'send_by_enter', None) is not None:
        merged['send_by_enter'] = bool(user.send_by_enter)
        merged['chat_send_on_enter'] = merged['send_by_enter']
    else:
        merged['send_by_enter'] = merged.get('chat_send_on_enter', True) is not False

    merged['username'] = getattr(user, 'username', None) or ''
    return merged


def set_user_setting(user, key, value):
    if key == 'tasks_sleep_mode':
        until_iso = set_tasks_sleep_mode(user, bool(value))
        return get_user_settings(user), until_iso

    if key == 'username':
        normalized = _normalize_username(value)
        if normalized:
            taken = User.query.filter(User.username == normalized, User.id != user.id).first()
            if taken:
                raise ValueError('Этот юзернейм уже занят')
        user.username = normalized
        return get_user_settings(user), None

    if key == 'send_by_enter':
        _sync_send_by_enter_column(user, bool(value))
        return get_user_settings(user), None

    if key == 'phone_privacy':
        level = _normalize_phone_privacy(value)
        if level not in PHONE_PRIVACY_LEVELS:
            raise ValueError('Недопустимый уровень приватности телефона')
        _sync_phone_privacy_column(user, level)
        return get_user_settings(user), None

    if key not in SETTING_KEYS:
        raise ValueError(f'Unknown setting: {key}')

    if is_worker_role(user) and key in WORKER_NOTIFY_KEYS:
        raise ValueError('Используйте режим «Отключить на 24 часа»')

    if key == 'privacy_phone_visibility':
        level = _normalize_privacy_level(value)
        if level not in PRIVACY_LEVELS:
            raise ValueError('Invalid privacy level')
        _sync_phone_privacy_column(user, _visibility_to_phone_privacy(level))
        return get_user_settings(user), None

    if key in PRIVACY_SETTING_KEYS:
        value = _normalize_privacy_level(value)
        if value not in PRIVACY_LEVELS:
            raise ValueError('Invalid privacy level')
    elif key in (
        'chat_sound_enabled',
        'chat_send_on_enter',
        'notify_new_tasks',
        'notify_status_changes',
        'notify_system_alerts',
    ):
        value = bool(value)
        if key == 'chat_send_on_enter':
            _sync_send_by_enter_column(user, value)
            return get_user_settings(user), None
    else:
        raise ValueError(f'Unsupported setting: {key}')

    current = _normalize_settings(getattr(user, 'settings', None))
    current[key] = value
    user.settings = current
    return get_user_settings(user), None


def _privacy_allows(viewer, target, setting_key):
    from utils.user_profiles import is_worker_profile

    if not viewer or not getattr(viewer, 'is_authenticated', False):
        return False
    if viewer.id == target.id:
        return True

    if is_worker_profile(target) and privacy_admin_override(viewer):
        return True

    if setting_key == 'privacy_phone_visibility' and getattr(target, 'phone_privacy', None):
        level = _phone_privacy_to_visibility(_normalize_phone_privacy(target.phone_privacy))
    else:
        level = get_user_settings(target).get(setting_key, 'everyone')

    if level == 'everyone':
        return True
    if level == 'nobody':
        return False
    if level == 'contacts':
        return _are_contacts(viewer, target)
    return False


def can_view_private_field(viewer, target, field, *, task_context=False):
    """Видимость phone / birth в профиле."""
    setting_key = f'privacy_{field}_visibility'
    return _privacy_allows(viewer, target, setting_key)


def can_find_user_by_phone(viewer, target):
    """Поиск пользователя по номеру телефона."""
    return _privacy_allows(viewer, target, 'privacy_phone_search')
