"""Токен-сессии для нативного клиента (заголовок X-Session-Token)."""
import uuid

from flask import jsonify, request
from flask_login import login_user
from functools import wraps

from models import User, db


def extract_session_token():
    auth = request.headers.get('Authorization', '')
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return (request.headers.get('X-Session-Token') or '').strip()


def resolve_mobile_user():
    token = extract_session_token()
    if not token:
        return None
    return User.query.filter_by(current_mobile_token=token).first()


def issue_mobile_token(user) -> str:
    token = uuid.uuid4().hex
    user.current_mobile_token = token
    db.session.commit()
    return token


def mobile_auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = resolve_mobile_user()
        if not user:
            return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
        login_user(user)
        return fn(user, *args, **kwargs)

    return wrapper


def _worker_availability(user):
    """available | on_shift | busy — для экрана профиля в приложении."""
    from models import Task, TaskAssignment

    active = (
        TaskAssignment.query.join(Task, TaskAssignment.task_id == Task.id)
        .filter(
            TaskAssignment.user_id == user.id,
            TaskAssignment.status == 'assigned',
            Task.status.in_(('recruiting', 'in_progress')),
        )
        .all()
    )
    if not active:
        return 'available', 'Доступен'
    for assignment in active:
        ws = assignment.worker_status or 'assigned'
        if ws in ('en_route', 'on_site'):
            return 'on_shift', 'На смене'
    return 'busy', 'Занят'


def _weekly_earnings(user):
    from datetime import timedelta

    from sqlalchemy import func

    from models import Task, TaskAssignment
    from utils.datetime_utils import utc_now

    since = utc_now() - timedelta(days=7)
    total = (
        db.session.query(func.coalesce(func.sum(Task.price), 0.0))
        .join(TaskAssignment, TaskAssignment.task_id == Task.id)
        .filter(
            TaskAssignment.user_id == user.id,
            TaskAssignment.status == 'completed',
            TaskAssignment.completed_at.isnot(None),
            TaskAssignment.completed_at >= since,
        )
        .scalar()
    )
    return float(total or 0)


def user_mobile_json(user, *, base_url=None):
    from utils.media_urls import avatar_path_for_user
    from utils.security_freeze import is_balance_frozen

    availability, availability_label = _worker_availability(user)
    payload = {
        'id': user.id,
        'name': user.name,
        'phone': user.phone,
        'email': user.email,
        'tag': user.tag or user.username,
        'role': user.role,
        'workspace_id': user.workspace_id,
        'platform_role': user.platform_role,
        'avatar': user.avatar,
        'balance': float(user.balance or 0),
        'is_frozen': is_balance_frozen(user),
        'rating': float(user.rating or 0),
        'completed_tasks': int(user.completed_tasks or 0),
        'availability': availability,
        'availability_label': availability_label,
        'weekly_earnings': _weekly_earnings(user),
    }
    path = avatar_path_for_user(user)
    if path and base_url:
        root = base_url.rstrip('/')
        payload['avatar_url'] = f'{root}/uploads/{path}'
    return payload
