"""REST API профиля исполнителя для нативного Flutter-клиента."""
from flask import Blueprint, jsonify, request

from utils.media_urls import avatar_path_for_user
from utils.mobile_auth import (
    _weekly_earnings,
    _worker_availability,
    mobile_auth_required,
)
from utils.security_freeze import is_balance_frozen
from utils.user_profiles import is_worker_profile, resolve_full_name
from utils.worker_stats import get_worker_stats, resolve_stats_workspace_id

worker_api_bp = Blueprint('worker_api', __name__, url_prefix='/api/worker')


def _avatar_url(user, base_url: str | None) -> str | None:
    path = avatar_path_for_user(user)
    if not path or not base_url:
        return None
    return f'{base_url.rstrip("/")}/uploads/{path}'


def serialize_worker_me(user, *, base_url: str | None = None) -> dict:
    """Профиль воркера — те же поля, что нужны мобильному экрану профиля."""
    availability, availability_label = _worker_availability(user)
    ws_id = resolve_stats_workspace_id(user, user)
    stats = get_worker_stats(user.id, ws_id)

    display_name = resolve_full_name(user) if is_worker_profile(user) else user.name

    return {
        'id': user.id,
        'name': user.name,
        'full_name': display_name,
        'phone': user.phone,
        'email': user.email,
        'tag': user.tag or user.username,
        'role': user.role,
        'workspace_id': user.workspace_id,
        'avatar': user.avatar,
        'avatar_url': _avatar_url(user, base_url),
        'balance': float(user.balance or 0),
        'is_frozen': is_balance_frozen(user),
        'weekly_earnings': _weekly_earnings(user),
        'availability': availability,
        'availability_label': availability_label,
        'rating': stats['rating'],
        'completed_tasks': stats['completed_tasks'],
        'missed_tasks': stats['missed_tasks'],
        'is_verified': bool(user.is_verified),
    }


@worker_api_bp.route('/me', methods=['GET'])
@mobile_auth_required
def worker_me(user):
    base_url = request.url_root.rstrip('/')
    return jsonify({
        'ok': True,
        'user': serialize_worker_me(user, base_url=base_url),
    })
