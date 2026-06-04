"""Утилиты изоляции данных по рабочим пространствам."""

ADMIN_STAFF_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
CLIENT_ADMIN_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
USER_MANAGEMENT_ROLES = ('creator', 'director', 'senior_dispatcher')

DEFAULT_WORKSPACE_ADMIN_LIMIT = 50
MAX_WORKSPACE_ADMIN_LIMIT = 100
MIN_WORKSPACE_ADMIN_LIMIT = 1
PLATFORM_ADMIN_SOFT_LIMIT = 9999


def is_platform_admin(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if (getattr(user, 'platform_role', None) or '') == 'super_admin':
        return True
    return (user.role or '') == 'creator'


def _session_workspace_id():
    try:
        from flask import session
        return session.get('workspace_id')
    except RuntimeError:
        return None


def _set_session_workspace_id(ws_id):
    if ws_id is None:
        return
    try:
        from flask import session
        session['workspace_id'] = int(ws_id)
    except RuntimeError:
        pass


def resolve_workspace_id(user, *, persist=True):
    """
    workspace_id из User, иначе session, иначе первый Workspace для creator/super_admin.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return None

    if user.workspace_id:
        _set_session_workspace_id(user.workspace_id)
        return int(user.workspace_id)

    session_ws = _session_workspace_id()
    if session_ws:
        return int(session_ws)

    if is_platform_admin(user):
        from models import Workspace, db

        ws = Workspace.query.order_by(Workspace.id.asc()).first()
        if ws:
            ws_id = int(ws.id)
            _set_session_workspace_id(ws_id)
            if persist and user.workspace_id != ws_id:
                user.workspace_id = ws_id
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            return ws_id

    return None


def get_workspace_id(user):
    return resolve_workspace_id(user)


def scope_query(query, model, user):
    """Фильтрует запрос по workspace_id текущего пользователя."""
    ws_id = get_workspace_id(user)
    if ws_id is None:
        return query.filter(False)
    return query.filter(model.workspace_id == ws_id)


def count_admin_staff(workspace_id, exclude_user_id=None):
    from models import User

    q = User.query.filter(
        User.workspace_id == workspace_id,
        User.role.in_(ADMIN_STAFF_ROLES),
    )
    if exclude_user_id:
        q = q.filter(User.id != exclude_user_id)
    return q.count()


def effective_admin_limit(workspace, acting_user=None):
    """Лимит админ-состава; для создателя платформы — без жёсткого потолка."""
    from models import Workspace

    if acting_user and is_platform_admin(acting_user):
        return PLATFORM_ADMIN_SOFT_LIMIT
    if workspace is None:
        ws = None
    elif isinstance(workspace, Workspace):
        ws = workspace
    else:
        ws = Workspace.query.get(int(workspace))
    if not ws:
        return DEFAULT_WORKSPACE_ADMIN_LIMIT
    return max(int(ws.admin_limit or DEFAULT_WORKSPACE_ADMIN_LIMIT), MIN_WORKSPACE_ADMIN_LIMIT)


def admin_limit_reached(workspace_id, exclude_user_id=None, acting_user=None):
    from models import Workspace

    if acting_user and is_platform_admin(acting_user):
        return False

    ws = Workspace.query.get(workspace_id)
    if not ws:
        return False
    limit = effective_admin_limit(ws, acting_user)
    return count_admin_staff(workspace_id, exclude_user_id=exclude_user_id) >= limit


def would_exceed_admin_limit(workspace_id, target_user, new_role, acting_user=None):
    if new_role not in ADMIN_STAFF_ROLES:
        return False
    if target_user.role in ADMIN_STAFF_ROLES:
        return False
    return admin_limit_reached(workspace_id, exclude_user_id=target_user.id, acting_user=acting_user)


def normalize_admin_limit_value(raw, acting_user=None):
    """Парсинг лимита из формы с учётом роли."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, 'Лимит администраторов должен быть числом'

    if value < MIN_WORKSPACE_ADMIN_LIMIT:
        return None, f'Лимит администраторов должен быть не менее {MIN_WORKSPACE_ADMIN_LIMIT}'

    if acting_user and is_platform_admin(acting_user):
        return value, None

    if value > MAX_WORKSPACE_ADMIN_LIMIT:
        return None, f'Лимит администраторов не может превышать {MAX_WORKSPACE_ADMIN_LIMIT}'

    return value, None


def require_workspace(user):
    ws_id = resolve_workspace_id(user)
    if not ws_id:
        return None, 'Рабочее пространство не назначено'
    return ws_id, None
