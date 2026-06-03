"""Статистика исполнителя в рамках одного рабочего пространства (SQL-изоляция)."""

from sqlalchemy import func

from models import Task, TaskAssignment, db


def resolve_stats_workspace_id(viewer, target=None):
    """Workspace для фильтрации статистики: сначала сессия зрителя, иначе workspace цели."""
    ws_id = getattr(viewer, 'workspace_id', None) if viewer else None
    if ws_id:
        return ws_id
    if target is not None:
        return getattr(target, 'workspace_id', None)
    return None


def count_worker_completed(workspace_id, user_id):
    if not workspace_id or not user_id:
        return 0
    return (
        TaskAssignment.query.join(Task, TaskAssignment.task_id == Task.id)
        .filter(
            Task.workspace_id == workspace_id,
            TaskAssignment.user_id == user_id,
            TaskAssignment.status == 'completed',
            Task.status == 'done',
        )
        .count()
    )


def count_worker_missed(workspace_id, user_id):
    if not workspace_id or not user_id:
        return 0
    base = (
        TaskAssignment.query.join(Task, TaskAssignment.task_id == Task.id)
        .filter(
            Task.workspace_id == workspace_id,
            TaskAssignment.user_id == user_id,
        )
    )
    timer_penalty = base.filter(
        TaskAssignment.status == 'removed',
        TaskAssignment.route_reminder_stage >= 4,
    ).count()
    failed_tasks = base.filter(Task.status == 'failed').count()
    return timer_penalty + failed_tasks


def compute_worker_rating(completed, missed):
    total = completed + missed
    if total <= 0:
        return 0.0
    return round(max(0.0, min(10.0, (completed / total) * 10.0)), 1)


def get_worker_stats(user_id, workspace_id):
    completed = count_worker_completed(workspace_id, user_id)
    missed = count_worker_missed(workspace_id, user_id)
    return {
        'completed_tasks': completed,
        'missed_tasks': missed,
        'rating': compute_worker_rating(completed, missed),
    }


def get_workers_stats_batch(workspace_id, user_ids):
    """Пакетный подсчёт для списков исполнителей."""
    ids = list(user_ids or [])
    empty = {
        'completed_tasks': 0,
        'missed_tasks': 0,
        'rating': 0.0,
    }
    if not workspace_id or not ids:
        return {uid: dict(empty) for uid in ids}

    completed_rows = (
        db.session.query(TaskAssignment.user_id, func.count(TaskAssignment.id))
        .join(Task, TaskAssignment.task_id == Task.id)
        .filter(
            Task.workspace_id == workspace_id,
            TaskAssignment.user_id.in_(ids),
            TaskAssignment.status == 'completed',
            Task.status == 'done',
        )
        .group_by(TaskAssignment.user_id)
        .all()
    )
    missed_timer_rows = (
        db.session.query(TaskAssignment.user_id, func.count(TaskAssignment.id))
        .join(Task, TaskAssignment.task_id == Task.id)
        .filter(
            Task.workspace_id == workspace_id,
            TaskAssignment.user_id.in_(ids),
            TaskAssignment.status == 'removed',
            TaskAssignment.route_reminder_stage >= 4,
        )
        .group_by(TaskAssignment.user_id)
        .all()
    )
    missed_failed_rows = (
        db.session.query(TaskAssignment.user_id, func.count(TaskAssignment.id))
        .join(Task, TaskAssignment.task_id == Task.id)
        .filter(
            Task.workspace_id == workspace_id,
            TaskAssignment.user_id.in_(ids),
            Task.status == 'failed',
        )
        .group_by(TaskAssignment.user_id)
        .all()
    )

    completed_map = {uid: cnt for uid, cnt in completed_rows}
    missed_map = {}
    for uid, cnt in missed_timer_rows:
        missed_map[uid] = missed_map.get(uid, 0) + cnt
    for uid, cnt in missed_failed_rows:
        missed_map[uid] = missed_map.get(uid, 0) + cnt

    result = {}
    for uid in ids:
        completed = completed_map.get(uid, 0)
        missed = missed_map.get(uid, 0)
        result[uid] = {
            'completed_tasks': completed,
            'missed_tasks': missed,
            'rating': compute_worker_rating(completed, missed),
        }
    return result
