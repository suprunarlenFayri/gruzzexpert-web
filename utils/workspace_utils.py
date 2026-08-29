"""Утилиты изоляции данных по рабочим пространствам."""

from utils.invite_utils import DEFAULT_WORKSPACE_ID

ADMIN_STAFF_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
CLIENT_ADMIN_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
USER_MANAGEMENT_ROLES = ('creator', 'director', 'senior_dispatcher')

# Лимит по умолчанию для новых клиентских пространств (не флагман)
DEFAULT_CLIENT_WORKSPACE_ADMIN_LIMIT = 5
MAX_WORKSPACE_ADMIN_LIMIT = 100
MIN_WORKSPACE_ADMIN_LIMIT = 1

# В БД хранится число (NOT NULL); для флагмана лимит не применяется в коде (id=1).
FLAGSHIP_ADMIN_LIMIT_DB = 9999


def is_platform_admin(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if (getattr(user, 'platform_role', None) or '') == 'super_admin':
        return True
    return (user.role or '') == 'creator'


def is_flagship_workspace(workspace_or_id):
    """Флагманское пространство GruzzExpert (id=1) — без лимита админов."""
    if workspace_or_id is None:
        return False
    wid = workspace_or_id if isinstance(workspace_or_id, int) else int(workspace_or_id.id)
    return wid == DEFAULT_WORKSPACE_ID


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


def effective_admin_limit(workspace):
    """
    Лимит из БД для клиентского пространства.
    Флагман (id=1): None — без ограничений.
    """
    from models import Workspace

    if workspace is None:
        return DEFAULT_CLIENT_WORKSPACE_ADMIN_LIMIT
    if isinstance(workspace, int):
        if is_flagship_workspace(workspace):
            return None
        workspace = Workspace.query.get(workspace)
    elif is_flagship_workspace(workspace):
        return None
    if not workspace:
        return DEFAULT_CLIENT_WORKSPACE_ADMIN_LIMIT
    if workspace.admin_limit is None:
        return DEFAULT_CLIENT_WORKSPACE_ADMIN_LIMIT
    return max(int(workspace.admin_limit), MIN_WORKSPACE_ADMIN_LIMIT)


def admin_limit_reached(workspace_id, exclude_user_id=None, acting_user=None):
    del acting_user  # лимит не зависит от того, кто назначает роль

    if is_flagship_workspace(int(workspace_id)):
        return False

    from models import Workspace

    ws = Workspace.query.get(workspace_id)
    if not ws:
        return False
    limit = effective_admin_limit(ws)
    return count_admin_staff(workspace_id, exclude_user_id=exclude_user_id) >= limit


def would_exceed_admin_limit(workspace_id, target_user, new_role, acting_user=None):
    del acting_user

    if new_role not in ADMIN_STAFF_ROLES:
        return False
    if target_user.role in ADMIN_STAFF_ROLES:
        return False
    if is_flagship_workspace(int(workspace_id)):
        return False
    return admin_limit_reached(workspace_id, exclude_user_id=target_user.id)


def normalize_admin_limit_value(raw, acting_user=None):
    """Парсинг лимита из формы. Создатель может задать любое разумное значение для клиентов."""
    del acting_user
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, 'Лимит администраторов должен быть числом'

    if value < MIN_WORKSPACE_ADMIN_LIMIT:
        return None, f'Лимит администраторов должен быть не менее {MIN_WORKSPACE_ADMIN_LIMIT}'

    if value > MAX_WORKSPACE_ADMIN_LIMIT:
        return None, f'Лимит администраторов не может превышать {MAX_WORKSPACE_ADMIN_LIMIT}'

    return value, None


def admin_limit_display(workspace):
    """Строка для UI: «без лимита» или число."""
    if is_flagship_workspace(workspace):
        return None
    from models import Workspace

    if isinstance(workspace, int):
        workspace = Workspace.query.get(workspace)
    if not workspace:
        return DEFAULT_CLIENT_WORKSPACE_ADMIN_LIMIT
    return workspace.admin_limit if workspace.admin_limit is not None else DEFAULT_CLIENT_WORKSPACE_ADMIN_LIMIT


def require_workspace(user):
    ws_id = resolve_workspace_id(user)
    if not ws_id:
        return None, 'Рабочее пространство не назначено'
    return ws_id, None
