"""Сериализация профилей: мессенджер (публичный) и рабочая карточка исполнителя."""

from datetime import date, datetime

from models import ChatParticipant, User, VerificationRequest, db
from utils.crypto import decrypt_data
from utils.user_settings import can_view_private_field
from utils.worker_stats import get_worker_stats, resolve_stats_workspace_id

ROLE_LABELS = {
    'creator': 'Создатель',
    'director': 'Директор',
    'senior_dispatcher': 'Ст. диспетчер',
    'dispatcher': 'Диспетчер',
    'manager': 'Менеджер',
    'brigadir': 'Бригадир',
    'worker': 'Исполнитель',
    'client': 'Клиент',
    'user': 'Пользователь',
}

WORKER_PROFILE_ROLES = frozenset({'worker', 'brigadir'})

WORKER_CARD_VIEWER_ROLES = frozenset({
    'creator', 'director', 'senior_dispatcher', 'dispatcher', 'manager', 'brigadir',
})


def role_label(role):
    return ROLE_LABELS.get(role or '', role or 'Пользователь')


def header_role_label(user):
    """Подпись роли в шапке: исполнитель только после одобрения анкеты."""
    if not user or not getattr(user, 'is_authenticated', False):
        return ''

    role = user.role or 'user'

    staff_labels = {
        'creator': 'Создатель',
        'director': 'Директор',
        'senior_dispatcher': 'Ст. диспетчер',
        'dispatcher': 'Диспетчер',
        'manager': 'Менеджер',
    }
    if role in staff_labels:
        return staff_labels[role]

    if role in WORKER_PROFILE_ROLES:
        if getattr(user, 'is_verified', False):
            return role_label(role)
        return 'Пользователь'

    if role == 'client':
        return 'Клиент'

    return 'Пользователь'


def is_worker_profile(user):
    return (user.role or '') in WORKER_PROFILE_ROLES


def _approved_verification(user):
    return (
        VerificationRequest.query.filter_by(user_id=user.id, status='approved')
        .order_by(VerificationRequest.moderated_at.desc())
        .first()
    )


def resolve_birth_date(user):
    if user.birth_date:
        return user.birth_date
    req = _approved_verification(user)
    return req.birth_date if req else None


def format_birth_date_display(birth):
    """Дата рождения для UI: date/datetime или legacy-строка из БД."""
    if birth is None:
        return None
    if isinstance(birth, datetime):
        return birth.date().strftime('%d.%m.%Y')
    if isinstance(birth, date):
        return birth.strftime('%d.%m.%Y')
    if isinstance(birth, str):
        raw = birth.strip()
        if not raw:
            return None
        if len(raw) >= 10 and raw[2] == '.' and raw[5] == '.':
            return raw[:10]
        for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
            try:
                parsed = datetime.strptime(raw[:10], fmt).date()
                return parsed.strftime('%d.%m.%Y')
            except ValueError:
                continue
        return raw
    return str(birth)


def resolve_full_name(user):
    req = _approved_verification(user)
    if req and req.full_name:
        return decrypt_data(req.full_name)
    return user.name


def can_view_user_profile(viewer, target):
    if not viewer.is_authenticated:
        return False
    if viewer.id == target.id:
        return True
    if viewer.role == 'creator' and not viewer.workspace_id:
        return True
    if viewer.workspace_id and target.workspace_id:
        return viewer.workspace_id == target.workspace_id
    viewer_chat_ids = (
        db.session.query(ChatParticipant.chat_id)
        .filter(ChatParticipant.user_id == viewer.id)
        .subquery()
    )
    return (
        ChatParticipant.query.filter(
            ChatParticipant.chat_id.in_(viewer_chat_ids),
            ChatParticipant.user_id == target.id,
        ).first()
        is not None
    )


def can_view_worker_card(viewer, target):
    """Полная рабочая карточка — только заявки, статистика, админка."""
    if not viewer.is_authenticated:
        return False
    if viewer.id == target.id and is_worker_profile(target):
        return True
    if viewer.role == 'creator' and not viewer.workspace_id:
        return True
    if (viewer.role or '') not in WORKER_CARD_VIEWER_ROLES:
        return False
    if viewer.workspace_id and target.workspace_id:
        return viewer.workspace_id == target.workspace_id
    return False


def serialize_messenger_profile(user, viewer, avatar_url_fn):
    """Публичный профиль для чатов (Telegram-style)."""
    birth_date_display = format_birth_date_display(resolve_birth_date(user))
    tag_display = f'@{user.tag}' if user.tag else None

    show_phone = can_view_private_field(viewer, user, 'phone', task_context=False)
    show_birth = can_view_private_field(viewer, user, 'birth', task_context=False)

    username = getattr(user, 'username', None) or None
    username_display = f'@{username}' if username else None

    return {
        'id': user.id,
        'context': 'messenger',
        'profile_type': 'messenger',
        'name': user.name,
        'phone': user.phone if show_phone else None,
        'birth_date': birth_date_display if show_birth else None,
        'tag': tag_display,
        'username': username_display,
        'role': user.role,
        'role_label': role_label(user.role),
        'avatar_url': avatar_url_fn(user),
    }


def serialize_worker_card(user, viewer, avatar_url_fn):
    """Полная рабочая карточка исполнителя."""
    if not is_worker_profile(user):
        data = serialize_messenger_profile(user, viewer, avatar_url_fn)
        data['context'] = 'worker'
        return data

    birth_date_display = format_birth_date_display(resolve_birth_date(user))
    display_name = resolve_full_name(user)

    show_phone = can_view_private_field(viewer, user, 'phone', task_context=True)
    show_birth = can_view_private_field(viewer, user, 'birth', task_context=True)

    ws_id = resolve_stats_workspace_id(viewer, user)
    stats = get_worker_stats(user.id, ws_id)

    is_self = viewer.id == user.id
    staff_view = can_view_worker_card(viewer, user) and not is_self

    return {
        'id': user.id,
        'context': 'worker',
        'profile_type': 'worker',
        'name': user.name,
        'full_name': display_name,
        'phone': user.phone if show_phone else None,
        'birth_date': birth_date_display if show_birth else None,
        'role': user.role,
        'role_label': role_label(user.role),
        'avatar_url': avatar_url_fn(user),
        'is_verified': bool(user.is_verified),
        'is_self': is_self,
        'can_edit_bank_card': is_self,
        'can_open_chat': staff_view,
        'can_view_documents': staff_view,
        'bank_card': decrypt_data(user.bank_card) if user.bank_card else '',
        'rating': stats['rating'],
        'completed_tasks': stats['completed_tasks'],
        'missed_tasks': stats['missed_tasks'],
    }


def serialize_user_profile(user, viewer, avatar_url_fn, *, context='messenger', task_context=False):
    """Обратная совместимость: context=messenger|worker."""
    if context == 'worker':
        return serialize_worker_card(user, viewer, avatar_url_fn)
    return serialize_messenger_profile(user, viewer, avatar_url_fn)
