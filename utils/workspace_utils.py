"""Утилиты изоляции данных по рабочим пространствам."""

ADMIN_STAFF_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
CLIENT_ADMIN_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
USER_MANAGEMENT_ROLES = ('creator', 'director', 'senior_dispatcher')


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
    ws_id = resolve_workspace_id(user)
    if not ws_id:
        return None, 'Рабочее пространство не назначено'
    return ws_id, None
