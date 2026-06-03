"""Целевые WebSocket-уведомления для чатов и заявок."""

import logging

from models import Chat, Task, User
from socketio_instance import emit_task_notification, send_update

logger = logging.getLogger(__name__)
from utils.user_settings import should_receive_task_notification

DISPATCHER_ROLES = ('creator', 'director', 'senior_dispatcher', 'dispatcher')
WORKER_ROLES = ('worker', 'brigadir')

STATUS_LABELS = {
    'en_route': 'В пути',
    'on_site': 'На месте',
    'finish': 'Закончил',
}

KIND_TITLES = {
    'new_task': 'Новая заявка',
    'task_updated': 'Заявка обновлена',
    'task_cancelled': 'Заявка отменена',
    'worker_status': 'Статус исполнителя',
    'route_reminder': 'Напоминание',
    'route_nudge': 'Повторное напоминание',
    'route_alarm': 'Срочно!',
    'route_removed': 'Снят с заявки',
    'task_reopened': 'Заявка снова доступна',
}


def _chat_recipient_ids(chat_id, exclude_user_id=None):
    chat = Chat.query.get(chat_id)
    if not chat:
        return []
    ids = []
    for user in chat.get_participants():
        if exclude_user_id and user.id == exclude_user_id:
            continue
        ids.append(user.id)
    return ids


def notify_chat_message(chat_id, sender_id, payload):
    recipient_ids = _chat_recipient_ids(chat_id, exclude_user_id=sender_id)
    if recipient_ids:
        send_update('new_message', payload, user_ids=recipient_ids)
        _push_chat_message(recipient_ids, payload)


def _push_chat_message(recipient_ids, payload):
    try:
        from utils.push_notifications import send_push_notification
    except ImportError:
        return

    sender_name = (payload or {}).get('sender_name') or 'Новое сообщение'
    text = (payload or {}).get('text') or (payload or {}).get('preview') or 'Сообщение'
    chat_id = (payload or {}).get('chat_id')
    data = {'kind': 'chat_message', 'chat_id': str(chat_id or '')}

    for uid in recipient_ids:
        send_push_notification(
            uid,
            title=sender_name,
            body=text[:120] if text else 'Новое сообщение',
            data=data,
        )


def _worker_allowed_for_task(worker, task):
    if worker.role not in WORKER_ROLES or not worker.is_verified:
        return False
    if task.workspace_id and worker.workspace_id != task.workspace_id:
        return False
    locations = worker.allowed_locations or []
    if isinstance(locations, str):
        import json
        try:
            locations = json.loads(locations)
        except Exception:
            locations = []
    if task.city_id and locations:
        return task.city_id in locations
    if task.city_id and not locations:
        return False
    return True


def get_eligible_workers(task):
    query = User.query.filter(
        User.role.in_(WORKER_ROLES),
        User.is_verified.is_(True),
    )
    if task.workspace_id:
        query = query.filter(User.workspace_id == task.workspace_id)
    workers = query.order_by(User.name).all()
    return [w for w in workers if _worker_allowed_for_task(w, task)]


def get_task_notification_recipients(task):
    assigned_ids = {
        a.user_id for a in task.assignments if a.status == 'assigned'
    }
    required = int(task.required_workers or 1)
    if len(assigned_ids) >= required:
        return list(assigned_ids)
    eligible = get_eligible_workers(task)
    free_ids = {w.id for w in eligible if w.id not in assigned_ids}
    return list(assigned_ids | free_ids)


def _base_task_notification(task, kind, title=None, body=None, payload=None, **extra):
    return {
        'kind': kind,
        'title': title or KIND_TITLES.get(kind, 'Заявка'),
        'body': body or (task.title if task else ''),
        'task_id': task.id if task else None,
        'workspace_id': task.workspace_id if task else None,
        'payload': payload,
        **extra,
    }


def _emit_task_to_recipients(data, user_ids):
    """Точечная отправка с учётом sleep mode исполнителей."""
    if not user_ids:
        return
    seen = set()
    for uid in user_ids:
        if uid is None or uid in seen:
            continue
        seen.add(uid)
        user = User.query.get(uid)
        if user and not should_receive_task_notification(user):
            continue
        emit_task_notification(None, data, user_id=uid)


def _recipients_for_task_event(task, kind):
    ids = set(_dispatcher_ids_for_task(task))
    if kind in ('new_task', 'task_reopened'):
        ids.update(get_task_notification_recipients(task))
    elif kind == 'task_updated':
        ids.update(
            a.user_id for a in task.assignments if a.status == 'assigned'
        )
    elif kind == 'worker_status':
        return list(_dispatcher_ids_for_task(task))
    return list(ids)


def broadcast_task_event(task, kind, payload=None, actor_id=None, **extra):
    """Push по заявкам: точечно, без пуша исполнителям в sleep mode."""
    title = extra.pop('title', None) or KIND_TITLES.get(kind, 'Заявка')
    body = extra.pop('body', None) or (payload or {}).get('title') or (task.title if task else '')
    data = _base_task_notification(
        task, kind, title=title, body=body, payload=payload,
        actor_id=actor_id, **extra,
    )
    recipient_ids = _recipients_for_task_event(task, kind)
    _emit_task_to_recipients(data, recipient_ids)
    _push_task_event(recipient_ids, data, task)


def _push_task_event(recipient_ids, data, task):
    try:
        from utils.push_notifications import send_push_notification
    except ImportError:
        return

    title = data.get('title') or 'Заявка'
    body = data.get('body') or (task.title if task else '')
    push_data = {
        'kind': data.get('kind') or 'task',
        'task_id': str(data.get('task_id') or ''),
    }
    for uid in recipient_ids:
        if uid is None:
            continue
        send_push_notification(uid, title=title, body=body, data=push_data)


def notify_new_task(task, payload):
    broadcast_task_event(task, 'new_task', payload=payload)


def notify_task_reopened(task, payload):
    broadcast_task_event(
        task, 'task_reopened', payload=payload,
        title='Заявка снова доступна',
        body=(payload or {}).get('title') or task.title,
    )


def notify_task_updated(task, payload, actor_id=None):
    broadcast_task_event(task, 'task_updated', payload=payload, actor_id=actor_id)


def _dispatcher_ids_for_task(task):
    ids = set()
    if task.created_by_id:
        ids.add(task.created_by_id)
    if task.workspace_id:
        staff = User.query.filter(
            User.workspace_id == task.workspace_id,
            User.role.in_(DISPATCHER_ROLES),
        ).all()
        ids.update(u.id for u in staff)
    return list(ids)


def notify_dispatchers_worker_status(task, worker, step, actor_id=None):
    label = STATUS_LABELS.get(step, step)
    worker_name = worker.name if worker else 'Исполнитель'
    task_title = task.title or f'Заявка №{task.task_number or task.id}'
    data = _base_task_notification(
        task,
        'worker_status',
        title=f'{worker_name}: {label}',
        body=task_title,
        worker_id=worker.id if worker else None,
        step=step,
        actor_id=actor_id or (worker.id if worker else None),
    )
    recipient_ids = _dispatcher_ids_for_task(task) if task.workspace_id else []
    if task.created_by_id and task.created_by_id not in recipient_ids:
        recipient_ids = list(set(recipient_ids) | {task.created_by_id})
    if recipient_ids:
        _emit_task_to_recipients(data, recipient_ids)
        _push_task_event(recipient_ids, data, task)


def notify_task_cancelled(worker_id, task_snapshot, message):
    """Уведомление исполнителю об отмене заявки диспетчером."""
    snapshot = task_snapshot or {}
    task_id = snapshot.get('id')
    data = _base_task_notification(
        None,
        'task_cancelled',
        title='Заявка отменена',
        body=message,
        payload=snapshot,
        alarm=True,
    )
    if task_id is not None:
        data['task_id'] = int(task_id)
    if snapshot.get('workspace_id') is not None:
        data['workspace_id'] = snapshot.get('workspace_id')
    try:
        emit_task_notification(None, data, user_id=worker_id)
    except Exception as exc:
        logger.warning(
            'emit_task_notification task_cancelled failed for user %s: %s',
            worker_id,
            exc,
            exc_info=True,
        )
    try:
        send_update('task_cancelled', snapshot, user_ids=[worker_id])
    except Exception as exc:
        logger.warning(
            'send_update task_cancelled failed for user %s: %s',
            worker_id,
            exc,
            exc_info=True,
        )


def notify_worker(user_id, kind, title, body, task_id=None, alarm=False):
    user = User.query.get(user_id)
    if user and not should_receive_task_notification(user):
        return
    task = Task.query.get(task_id) if task_id else None
    data = _base_task_notification(
        task,
        kind,
        title=title,
        body=body,
        alarm=alarm,
    )
    emit_task_notification(None, data, user_id=user_id)
