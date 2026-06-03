from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import and_, or_

from models import Task, User, City
from utils.worker_stats import get_workers_stats_batch
from utils.workspace_utils import get_workspace_id

statistics_bp = Blueprint('statistics', __name__)


def _user_timezone():
    user_tz_name = request.cookies.get('user_timezone', 'UTC')
    try:
        return ZoneInfo(user_tz_name)
    except Exception:
        return ZoneInfo('UTC')


def _to_utc_naive(dt):
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _scope_tasks_query(query):
    """Жёсткая изоляция статистики по workspace_id сессии."""
    ws_id = get_workspace_id(current_user)
    if not ws_id:
        return query.filter(False)
    return query.filter(Task.workspace_id == ws_id)


def _count_tasks_in_range(utc_start, utc_end, workspace_id):
    """Считает заявки в интервале: всего (по created_at), выполненные и пропущенные."""
    if not workspace_id:
        return 0, 0, 0

    base = Task.query.filter(Task.workspace_id == workspace_id)

    total = base.filter(
        Task.created_at >= utc_start,
        Task.created_at < utc_end,
    ).count()

    completed = base.filter(
        Task.status == 'done',
        or_(
            and_(Task.completed_at.isnot(None), Task.completed_at >= utc_start, Task.completed_at < utc_end),
            and_(Task.completed_at.is_(None), Task.created_at >= utc_start, Task.created_at < utc_end),
        ),
    ).count()

    missed = base.filter(
        Task.status == 'failed',
        or_(
            and_(Task.completed_at.isnot(None), Task.completed_at >= utc_start, Task.completed_at < utc_end),
            and_(Task.completed_at.is_(None), Task.created_at >= utc_start, Task.created_at < utc_end),
        ),
    ).count()

    return total, completed, missed


def _build_activity_buckets(period, workspace_id):
    user_tz = _user_timezone()
    now_user = datetime.now(user_tz)
    buckets = []

    if period == 'day':
        for i in range(13, -1, -1):
            local_start = datetime.combine(
                now_user.date() - timedelta(days=i),
                datetime.min.time(),
                tzinfo=user_tz,
            )
            local_end = local_start + timedelta(days=1)
            buckets.append((local_start, local_end, local_start.strftime('%d.%m')))
    elif period == 'month':
        year = now_user.year
        month = now_user.month
        for i in range(11, -1, -1):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            local_start = datetime(y, m, 1, tzinfo=user_tz)
            if m == 12:
                local_end = datetime(y + 1, 1, 1, tzinfo=user_tz)
            else:
                local_end = datetime(y, m + 1, 1, tzinfo=user_tz)
            buckets.append((local_start, local_end, local_start.strftime('%m.%Y')))
    else:
        for i in range(4, -1, -1):
            y = now_user.year - i
            local_start = datetime(y, 1, 1, tzinfo=user_tz)
            local_end = datetime(y + 1, 1, 1, tzinfo=user_tz)
            buckets.append((local_start, local_end, str(y)))

    result = []
    for local_start, local_end, label in buckets:
        utc_start = _to_utc_naive(local_start)
        utc_end = _to_utc_naive(local_end)
        total, completed, missed = _count_tasks_in_range(utc_start, utc_end, workspace_id)
        result.append({
            'label': label,
            'total': total,
            'completed': completed,
            'missed': missed,
        })
    return result


def _build_activity_chart_data(workspace_id):
    return {
        'day': _build_activity_buckets('day', workspace_id),
        'month': _build_activity_buckets('month', workspace_id),
        'year': _build_activity_buckets('year', workspace_id),
    }


@statistics_bp.route('/statistics')
@login_required
def statistics():
    if current_user.role not in ['creator', 'director', 'senior_dispatcher', 'manager']:
        flash('Нет доступа к статистике')
        return redirect(url_for('tasks.tasks_list'))

    ws_id = get_workspace_id(current_user)

    total_tasks = _scope_tasks_query(Task.query).count()
    completed_tasks = _scope_tasks_query(Task.query).filter_by(status='done').count()
    in_progress_tasks = _scope_tasks_query(Task.query).filter_by(status='in_progress').count()
    missed_tasks = _scope_tasks_query(Task.query).filter_by(status='failed').count()

    workers_query = User.query.filter(User.role.in_(['worker', 'brigadir']))
    if ws_id:
        workers_query = workers_query.filter(User.workspace_id == ws_id)
    else:
        workers_query = workers_query.filter(False)
    workers = workers_query.order_by(User.id.desc()).all()

    city_map = {c.id: c.name for c in City.query.all()}
    stats_by_user = get_workers_stats_batch(ws_id, [w.id for w in workers])

    worker_stats = []
    for worker in workers:
        ws_stats = stats_by_user.get(worker.id, {})
        completed = ws_stats.get('completed_tasks', 0)
        missed = ws_stats.get('missed_tasks', 0)
        city_ids = worker.allowed_locations or []
        worker_stats.append({
            'user': worker,
            'name': worker.name,
            'rating': ws_stats.get('rating', 0.0),
            'completed': completed,
            'missed': missed,
            'total': completed + missed,
            'cities': [city_map[cid] for cid in city_ids if cid in city_map],
        })

    worker_stats.sort(key=lambda item: (-item['rating'], -item['completed']))

    activity_chart_data = _build_activity_chart_data(ws_id)

    return render_template(
        'statistics.html',
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        missed_tasks=missed_tasks,
        worker_stats=worker_stats,
        activity_chart_data=activity_chart_data,
        active_tab='statistics',
    )
