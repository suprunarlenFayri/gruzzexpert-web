"""SaaS-панель создателя: пространства, подписки, сессии админов."""

from models import Client, User, UserSession, Workspace, db
from utils.datetime_utils import format_local_datetime, utc_now
from utils.user_login_sessions import list_user_sessions, sessions_for_api
from utils.workspace_utils import ADMIN_STAFF_ROLES, count_admin_staff

WORKER_ROLES = ('worker', 'brigadir')


def _cyrillic_count(text):
    if not text:
        return 0
    return sum(1 for c in str(text) if '\u0400' <= c <= '\u04FF')


def try_repair_mojibake(name):
    """
    Восстановление UTF-8, ошибочно прочитанного как Latin-1/CP1252.
    НЕ трогает строки, где уже есть нормальная кириллица.
    """
    if not name:
        return name or ''
    text = str(name).strip()
    if not text:
        return text
    if isinstance(name, bytes):
        return name.decode('utf-8', errors='replace').strip()

    if _cyrillic_count(text) >= 2:
        return text

    attempts = (
        lambda t: t.encode('latin1').decode('utf-8'),
        lambda t: t.encode('cp1252').decode('utf-8'),
        lambda t: t.encode('utf-8').decode('cp1251'),
    )
    for attempt in attempts:
        try:
            candidate = attempt(text)
            if candidate and _cyrillic_count(candidate) >= 2:
                return candidate.strip()
        except (UnicodeDecodeError, UnicodeEncodeError, ValueError):
            continue
    return text


def display_workspace_name(name):
    """Безопасное имя для UI/API (без порчи валидного UTF-8)."""
    return try_repair_mojibake(name)


def normalize_workspace_name(raw):
    """Нормализация названия при создании — только UTF-8, без «ремонта»."""
    if raw is None:
        return ''
    if isinstance(raw, bytes):
        return raw.decode('utf-8', errors='replace').strip()
    return str(raw).strip()


def fix_corrupted_workspace_names(*, commit=False):
    """Перекодировать испорченные названия в БД. Возвращает список (id, old, new)."""
    changed = []
    for ws in Workspace.query.all():
        raw = ws.name or ''
        fixed = try_repair_mojibake(raw)
        if fixed and fixed != raw:
            ws.name = fixed
            changed.append({'id': ws.id, 'old': raw, 'new': fixed})
    if commit and changed:
        db.session.commit()
    return changed


def count_workspace_workers(workspace_id):
    return User.query.filter(
        User.workspace_id == workspace_id,
        User.role.in_(WORKER_ROLES),
    ).count()


def workspace_card_stats(workspace_id, admin_limit=5):
    return {
        'workers': count_workspace_workers(workspace_id),
        'clients': Client.query.filter_by(workspace_id=workspace_id).count(),
        'admins': count_admin_staff(workspace_id),
        'admin_limit': admin_limit or 5,
    }


def _session_platform_label(device_name):
    s = (device_name or '').lower()
    if any(x in s for x in ('android', 'iphone', 'ipad', 'mobile', 'ios')):
        return 'Мобилка'
    if any(x in s for x in ('electron', 'desktop app', 'приложение')):
        return 'Десктоп'
    if any(x in s for x in ('windows', 'macos', 'linux', 'win32', 'darwin')):
        return 'Десктоп'
    return 'Веб-браузер'


def _serialize_session(row):
    return {
        'id': row.id,
        'device_name': row.device_name or 'Устройство',
        'platform': _session_platform_label(row.device_name),
        'ip_address': row.ip_address,
        'location': row.ip_address,
        'last_active': format_local_datetime(row.last_active) if row.last_active else None,
        'last_active_iso': row.last_active.isoformat() if row.last_active else None,
    }


def _admin_users_for_workspace(workspace_id, avatar_url_fn):
    users = (
        User.query.filter(
            User.workspace_id == workspace_id,
            User.role.in_(ADMIN_STAFF_ROLES),
        )
        .order_by(User.name.asc())
        .all()
    )
    admins = []
    for user in users:
        sessions = list_user_sessions(user.id)
        if not sessions:
            legacy = sessions_for_api(user.id, None)
            session_items = [
                {
                    'id': item['id'],
                    'device_name': item.get('device_name') or 'Устройство',
                    'platform': _session_platform_label(item.get('device_name')),
                    'ip_address': item.get('ip_address'),
                    'location': item.get('ip_address'),
                    'last_active': item.get('last_active'),
                    'is_legacy_device': item.get('is_legacy_device', False),
                }
                for item in legacy
            ]
        else:
            session_items = [_serialize_session(s) for s in sessions]

        tag = user.tag or user.username
        admins.append({
            'id': user.id,
            'name': user.name,
            'tag': tag,
            'tag_display': f'@{tag}' if tag else None,
            'role': user.role,
            'avatar_url': avatar_url_fn(user) if avatar_url_fn else None,
            'sessions': session_items,
        })
    return admins


def serialize_workspace_detail(workspace, avatar_url_fn):
    name = display_workspace_name(workspace.name)
    stats = workspace_card_stats(workspace.id, workspace.admin_limit)
    expires_display = None
    expires_iso = None
    if workspace.expires_at:
        expires_display = workspace.expires_at.strftime('%d.%m.%Y')
        expires_iso = workspace.expires_at.strftime('%Y-%m-%d')

    return {
        'id': workspace.id,
        'name': name,
        'admin_limit': workspace.admin_limit or 5,
        'expires_at': expires_iso,
        'expires_at_display': expires_display,
        'invite_key': workspace.invite_key,
        'stats': stats,
        'admins': _admin_users_for_workspace(workspace.id, avatar_url_fn),
    }


def admin_terminate_session(user, session_id):
    """Завершить сеанс админа (SaaS-создатель)."""
    row = UserSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not row:
        return False
    token = row.token
    db.session.delete(row)
    if user.current_desktop_token == token:
        user.current_desktop_token = None
    if user.current_mobile_token == token:
        user.current_mobile_token = None
    db.session.commit()
    return True
