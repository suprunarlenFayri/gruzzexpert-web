"""Утилиты изоляции данных по рабочим пространствам."""

ADMIN_STAFF_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
CLIENT_ADMIN_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
USER_MANAGEMENT_ROLES = ('creator', 'director', 'senior_dispatcher')


def get_workspace_id(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'workspace_id', None)


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


def admin_limit_reached(workspace_id, exclude_user_id=None):
    from models import Workspace

    ws = Workspace.query.get(workspace_id)
    if not ws:
        return False
    limit = ws.admin_limit or 5
    return count_admin_staff(workspace_id, exclude_user_id=exclude_user_id) >= limit


def would_exceed_admin_limit(workspace_id, target_user, new_role):
    if new_role not in ADMIN_STAFF_ROLES:
        return False
    if target_user.role in ADMIN_STAFF_ROLES:
        return False
    return admin_limit_reached(workspace_id, exclude_user_id=target_user.id)


def require_workspace(user):
    ws_id = get_workspace_id(user)
    if not ws_id:
        return None, 'Рабочее пространство не назначено'
    return ws_id, None
