"""RBAC для раздела «Рабочие пространства» (3 уровня доступа)."""

from utils.invite_utils import DEFAULT_WORKSPACE_ID


def is_platform_creator(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'platform_role', None) == 'super_admin':
        return True
    return (user.role or '') == 'creator'


def is_flagship_director(user):
    """Директор флагманского пространства (workspace_id = 1)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return (
        (user.role or '') == 'director'
        and int(user.workspace_id or 0) == DEFAULT_WORKSPACE_ID
    )


def is_external_director(user):
    """Директор стороннего пространства (workspace_id != 1)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    ws_id = int(user.workspace_id or 0)
    return (user.role or '') == 'director' and ws_id and ws_id != DEFAULT_WORKSPACE_ID


def workspaces_access_level(user):
    """
    1 — создатель / супер-админ платформы
    2 — директор флагманского пространства (id=1)
    3 — директор стороннего пространства
    """
    if is_platform_creator(user):
        return 1
    if is_flagship_director(user):
        return 2
    if is_external_director(user):
        return 3
    return None


def can_access_workspaces_page(user):
    return workspaces_access_level(user) is not None


def can_create_workspace(user):
    return is_platform_creator(user)


def workspaces_list_query(user):
    from models import Workspace

    level = workspaces_access_level(user)
    if level in (1, 2):
        return Workspace.query.order_by(Workspace.created_at.desc())
    if level == 3:
        return Workspace.query.filter_by(id=int(user.workspace_id))
    return Workspace.query.filter(False)


def can_view_workspace(user, workspace):
    level = workspaces_access_level(user)
    if level in (1, 2):
        return workspace is not None
    if level == 3:
        return workspace is not None and int(workspace.id) == int(user.workspace_id)
    return False


def can_extend_workspace_subscription(user, workspace):
    if not can_view_workspace(user, workspace):
        return False
    return workspaces_access_level(user) in (1, 2)


def can_terminate_workspace_admin_sessions(user, workspace):
    if not can_view_workspace(user, workspace):
        return False
    return workspaces_access_level(user) in (1, 2)


def workspace_panel_permissions(user, workspace=None):
    level = workspaces_access_level(user)
    readonly = level == 3
    return {
        'access_level': level,
        'can_create_workspace': can_create_workspace(user),
        'can_extend_subscription': (
            not readonly and workspace is not None and can_extend_workspace_subscription(user, workspace)
        ),
        'can_terminate_sessions': (
            not readonly and workspace is not None and can_terminate_workspace_admin_sessions(user, workspace)
        ),
        'is_readonly_panel': readonly,
    }


def workspace_admin_context_for_template(user):
    level = workspaces_access_level(user)
    return {
        'workspace_access_level': level,
        'can_create_workspace': can_create_workspace(user),
        'is_flagship_director': level == 2,
        'is_external_director': level == 3,
        'is_readonly_workspace_panel': level == 3,
        'show_employee_invite_panel': level == 3,
        'workspace_admin_perms': workspace_panel_permissions(user),
    }
