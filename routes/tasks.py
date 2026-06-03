from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from models import db, Task, City, User, TaskAssignment, PinnedItem, Client, Chat, ChatParticipant, Message
from datetime import datetime, timedelta, time
from socketio_instance import send_update
from services.task_chat_service import TaskChatService
from utils.crypto import encrypt_data
from services.notification_service import (
    get_eligible_workers,
    notify_chat_message,
    notify_dispatchers_worker_status,
    notify_new_task,
    notify_task_cancelled,
    notify_task_reopened,
    notify_task_updated,
)
from utils.datetime_nsk import parse_execution_date, format_execution_date
from utils.datetime_utils import (
    format_local_datetime,
    format_local_time,
    local_now,
    utc_iso,
    utc_now,
)
from utils.media_urls import avatar_url_for
from services.chat_service import ChatService
import re

tasks_bp = Blueprint('tasks', __name__)

ACTIVE_TASK_STATUSES = ['recruiting', 'in_progress', 'on_site', 'waiting_confirm']
ARCHIVED_TASK_STATUSES = ['done', 'failed']
PENDING_CONFIRM_STATUSES = ['on_site', 'waiting_confirm']
ACTIVE_ASSIGNMENT_STATUSES = ('assigned',)
TASK_DELETE_ROLES = ('dispatcher', 'senior_dispatcher', 'director', 'creator', 'manager')


def _user_workspace_id():
    if not current_user.is_authenticated:
        return None
    return current_user.workspace_id


def _scope_tasks(query):
    """Жёсткая изоляция: все роли (включая creator) видят только свой workspace."""
    ws_id = _user_workspace_id()
    if not ws_id:
        return query.filter(False)
    return query.filter(Task.workspace_id == ws_id)


def _get_scoped_task_or_404(task_id):
    return _scope_tasks(_task_query()).filter(Task.id == task_id).first_or_404()


def _workspace_id():
    return _user_workspace_id()


def _workspace_clients_query():
    ws_id = _workspace_id()
    if not ws_id:
        return Client.query.filter(False)
    return Client.query.filter(
        Client.workspace_id == ws_id,
        or_(Client.status == 'active', Client.status.is_(None)),
    )


def _parse_execution_time(value):
    if not value or not str(value).strip():
        return None
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(str(value).strip(), fmt).time()
        except ValueError:
            continue
    return None


def _task_query():
    """Запрос заявок с eager-load city/client/assignments — без N+1."""
    return Task.query.options(
        joinedload(Task.city),
        joinedload(Task.client),
        joinedload(
            Task.assignments.and_(TaskAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES))
        ).joinedload(TaskAssignment.user),
    )


def _task_ws_query():
    """Полная загрузка заявки для WebSocket-payload."""
    return Task.query.options(
        joinedload(Task.city),
        joinedload(
            Task.assignments.and_(TaskAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES))
        ).joinedload(TaskAssignment.user),
    )


def _reload_task_for_ws(task_or_id):
    task_id = task_or_id.id if isinstance(task_or_id, Task) else task_or_id
    return (
        _task_ws_query()
        .execution_options(populate_existing=True)
        .filter(Task.id == task_id)
        .first()
    )


def _resolve_task_city_name(task):
    city = task.city
    if not city and task.city_id:
        city = db.session.get(City, task.city_id)
    return city.name if city else 'Город не указан'


def _avatar_basename(user):
    if not user or not user.avatar:
        return ''
    path = str(user.avatar).replace('\\', '/').strip()
    for prefix in ('/static/uploads/', 'static/uploads/', '/uploads/', 'uploads/'):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    if '/' not in path:
        path = f'avatars/{path}'
    return path


def _task_assignments_payload(task):
    items = []
    for assignment in task.assignments:
        if assignment.status != 'assigned':
            continue
        user = assignment.user
        avatar = ''
        if user and user.avatar:
            avatar = url_for('uploaded_file', filename=_avatar_basename(user))
        items.append({
            'user_id': int(assignment.user_id),
            'user_name': str(user.name if user else 'Unknown'),
            'user_avatar': avatar,
            'worker_status': assignment.worker_status or 'assigned',
            'work_duration': _format_tracking_duration(
                assignment.started_working_at, assignment.finished_working_at
            ),
        })
    return items


def _new_task_ws_payload(task):
    """Готовые строки для мгновенного рендера карточки у исполнителя."""
    task = _reload_task_for_ws(task)
    if not task:
        return {}

    city_name = _resolve_task_city_name(task)
    return {
        'id': int(task.id),
        'title': str(task.title or 'Без названия'),
        'description': str(task.description or ''),
        'price': str(task.price or 0),
        'city': city_name,
        'city_name': city_name,
        'created_at': format_local_datetime(task.created_at),
        'workers': int(task.required_workers or 1),
        'required_workers': int(task.required_workers or 1),
        'assigned_count': 0,
        'status': str(task.status or 'recruiting'),
        'assignments': [],
        'address': task.address or '',
        'execution_date': format_execution_date(task.execution_date),
        'execution_time': task.execution_time.strftime('%H:%M') if task.execution_time else '08:00',
        'task_number': task.task_number or '',
        'workspace_id': int(task.workspace_id) if task.workspace_id else None,
    }


def _task_ws_payload(task):
    if not task:
        return {}
    city_name = _resolve_task_city_name(task)
    if city_name == 'Город не указан':
        city_name = ''
    return {
        'id': int(task.id),
        'title': str(task.title or 'Без названия'),
        'description': str(task.description or ''),
        'price': str(task.price or 0),
        'city': city_name,
        'city_name': city_name,
        'created_at': format_local_datetime(task.created_at),
        'required_workers': int(task.required_workers or 1),
        'workers': int(task.required_workers or 1),
        'assigned_count': len(task.get_assigned_workers()),
        'status': str(task.status or 'recruiting'),
        'assignments': _task_assignments_payload(task),
        'address': task.address or '',
        'execution_date': format_execution_date(task.execution_date),
        'execution_time': task.execution_time.strftime('%H:%M') if task.execution_time else '08:00',
        'task_number': task.task_number or '',
        'workspace_id': int(task.workspace_id) if task.workspace_id else None,
    }


def _emit_task_ws(event_type, task_or_id, actor_id=None):
    task = _reload_task_for_ws(task_or_id)
    if task:
        payload = _task_ws_payload(task)
        notify_task_updated(task, payload, actor_id=actor_id)


def _task_start_datetime(task):
    exec_time = task.execution_time or time(8, 0)
    if task.execution_date:
        base_date = task.execution_date
    elif task.created_at:
        base_date = task.created_at.date()
    else:
        base_date = local_now().date()
    return datetime.combine(base_date, exec_time)


def _can_start_en_route(task):
    start = _task_start_datetime(task)
    return local_now() >= start - timedelta(hours=2)


REJECT_MIN_HOURS_BEFORE_START = 2


def _can_worker_reject_assignment(task, assignment, user=None):
    """Исполнитель может отказаться до «На месте» и не позднее чем за N часов до старта."""
    user = user or current_user
    if not assignment or assignment.status != 'assigned':
        return False, 'Нет активного назначения'
    if assignment.user_id != user.id:
        return False, 'Недостаточно прав'
    ws = assignment.worker_status or 'assigned'
    if ws in ('on_site', 'completed'):
        return False, 'Слишком поздно для отказа, свяжитесь с диспетчером'
    start = _task_start_datetime(task)
    if local_now() >= start - timedelta(hours=REJECT_MIN_HOURS_BEFORE_START):
        return False, 'Слишком поздно для отказа, свяжитесь с диспетчером'
    return True, None


def _format_tracking_clock(dt):
    return format_local_time(dt, '%H:%M') if dt else '—'


def _format_tracking_duration(start, end):
    if not start or not end:
        return None
    delta = end - start
    if delta.total_seconds() < 0:
        return None
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f'{hours} ч. {minutes} мин.'


def _tracking_summary(assignment):
    en_route = _format_tracking_clock(assignment.en_route_at)
    on_site = _format_tracking_clock(assignment.started_working_at)
    finished = _format_tracking_clock(assignment.finished_working_at)
    total = _format_tracking_duration(assignment.started_working_at, assignment.finished_working_at)
    total_part = f' (Всего: {total})' if total else ''
    return f'В пути: {en_route} | На месте: {on_site} | Закончил: {finished}{total_part}'


def _user_tracking_payload(task, assignment):
    if not assignment:
        return None
    ws = assignment.worker_status or 'assigned'
    return {
        'worker_status': ws,
        'en_route_at': assignment.en_route_at.isoformat() if assignment.en_route_at else None,
        'started_working_at': assignment.started_working_at.isoformat() if assignment.started_working_at else None,
        'finished_working_at': assignment.finished_working_at.isoformat() if assignment.finished_working_at else None,
        'work_duration': _format_tracking_duration(
            assignment.started_working_at, assignment.finished_working_at
        ),
        'show_en_route': ws == 'assigned',
        'can_en_route': _can_start_en_route(task) and ws == 'assigned',
        'show_on_site': ws == 'en_route',
        'show_finish': ws == 'on_site',
        'is_finished': ws == 'completed',
        'can_submit_confirmation': (
            ws == 'completed'
            and task.status != 'waiting_confirm'
            and (
                task.status == 'on_site'
                or (task.status == 'in_progress' and _all_workers_finished(task))
            )
        ),
        'awaiting_confirmation': task.status == 'waiting_confirm',
    }


def _worker_tracking_payload(assignment):
    user = assignment.user
    duration = _format_tracking_duration(
        assignment.started_working_at, assignment.finished_working_at
    )
    return {
        'user_id': assignment.user_id,
        'user_name': user.name if user else 'Unknown',
        'worker_status': assignment.worker_status or 'assigned',
        'tracking_summary': _tracking_summary(assignment),
        'en_route_at': _format_tracking_clock(assignment.en_route_at),
        'started_working_at': _format_tracking_clock(assignment.started_working_at),
        'finished_working_at': _format_tracking_clock(assignment.finished_working_at),
        'work_duration': duration,
        'total_duration': duration,
    }


def _sync_task_assigned_to_id(task):
    """Синхронизирует legacy-поле assigned_to_id с реальными активными назначениями."""
    active = task.get_assigned_workers()
    task.assigned_to_id = active[0].id if active else None


def _can_delete_task(task):
    if current_user.id == task.created_by_id:
        return True
    return current_user.role in TASK_DELETE_ROLES


def _task_delete_label(task):
    if task.task_number:
        return f'№ {task.task_number}'
    if task.title:
        return str(task.title)
    return f'№{task.id}'


def _detach_task_references(task_id):
    """Снимает внешние ссылки на заявку перед DELETE (messages.task_id и др.)."""
    Message.query.filter_by(task_id=task_id).update(
        {Message.task_id: None},
        synchronize_session=False,
    )
    Chat.query.filter_by(task_id=task_id).update(
        {Chat.task_id: None},
        synchronize_session=False,
    )
    PinnedItem.query.filter_by(item_type='task', item_id=task_id).delete(
        synchronize_session=False,
    )


def _safe_notify_task_cancelled(worker_id, task_snapshot, message):
    try:
        notify_task_cancelled(worker_id, task_snapshot, message)
    except Exception as exc:
        current_app.logger.warning(
            'task_cancelled notify skipped for user %s: %s',
            worker_id,
            exc,
            exc_info=True,
        )


def _safe_send_update(event_type, data, user_ids=None):
    try:
        send_update(event_type, data, user_ids=user_ids)
    except Exception as exc:
        current_app.logger.warning(
            'socket emit %s failed: %s',
            event_type,
            exc,
            exc_info=True,
        )


def _is_task_manager(task):
    return (
        current_user.id == task.created_by_id
        or current_user.role in ['dispatcher', 'senior_dispatcher', 'director', 'creator', 'manager', 'brigadir']
    )


def _can_manage_assignments(task):
    return (
        current_user.id == task.created_by_id
        or current_user.role in ['dispatcher', 'senior_dispatcher', 'director', 'creator']
    )


def _sync_task_status_after_assignment_change(task):
    assigned = task.get_assigned_workers()
    if len(assigned) >= int(task.required_workers or 1):
        if task.status == 'recruiting':
            task.status = 'in_progress'
        _maybe_create_task_chat(task)
    elif task.status == 'in_progress':
        task.status = 'recruiting'
    _sync_task_assigned_to_id(task)


def _assign_worker_to_task(task, worker_id, assigned_by_id):
    if len(task.get_assigned_workers()) >= int(task.required_workers or 1):
        return False, 'Пул исполнителей заполнен'
    worker = User.query.get(worker_id)
    if not worker:
        return False, 'Исполнитель не найден'
    from services.notification_service import _worker_allowed_for_task
    if not _worker_allowed_for_task(worker, task):
        return False, 'Исполнитель недоступен для этой заявки'
    existing = TaskAssignment.query.filter_by(
        task_id=task.id, user_id=worker_id, status='assigned'
    ).first()
    if existing:
        return False, 'Уже назначен'
    prev = TaskAssignment.query.filter_by(task_id=task.id, user_id=worker_id).first()
    if prev and prev.status != 'assigned':
        prev.status = 'assigned'
        prev.worker_status = 'assigned'
        prev.assigned_by_id = assigned_by_id
        prev.assigned_at = utc_now()
        prev.route_reminder_stage = 0
        prev.route_deadline_at = None
    else:
        db.session.add(TaskAssignment(
            task_id=task.id,
            user_id=worker_id,
            assigned_by_id=assigned_by_id,
            status='assigned',
            worker_status='assigned',
            assigned_at=utc_now(),
        ))
    _sync_task_assigned_to_id(task)
    _sync_task_status_after_assignment_change(task)
    return True, None


def _remove_worker_from_task(task, user_id, penalty=False, final_status='removed'):
    assignment = TaskAssignment.query.filter_by(
        task_id=task.id, user_id=user_id, status='assigned'
    ).first()
    if not assignment:
        return False, 'Назначение не найдено'
    assignment.status = final_status
    assignment.route_reminder_stage = 0
    assignment.route_deadline_at = None
    worker = assignment.user
    if penalty and worker:
        worker.missed_tasks = int(worker.missed_tasks or 0) + 1
        worker.rating = max(0.0, float(worker.rating or 0) - 0.5)
    if len(task.get_assigned_workers()) < int(task.required_workers or 1):
        task.status = 'recruiting'
    _sync_task_status_after_assignment_change(task)
    return True, None


def _worker_reject_assignment(task, user=None):
    user = user or current_user
    assignment = TaskAssignment.query.filter_by(
        task_id=task.id, user_id=user.id, status='assigned'
    ).first()
    ok, err = _can_worker_reject_assignment(task, assignment, user=user)
    if not ok:
        return False, err
    return _remove_worker_from_task(task, user.id, penalty=False, final_status='rejected')


def _task_needs_confirmation(task):
    if task.status in PENDING_CONFIRM_STATUSES:
        return True
    if task.status == 'in_progress' and _all_workers_finished(task):
        return True
    return False


def _can_confirm_task(task):
    if not _task_needs_confirmation(task):
        return False
    return (
        current_user.id == task.created_by_id
        or current_user.role in ['creator', 'director', 'senior_dispatcher', 'dispatcher']
    )


def _sync_task_confirmation_status(task, commit=False):
    """Если все исполнители нажали «Закончил», переводим заявку в on_site."""
    if task.status == 'in_progress' and _all_workers_finished(task):
        task.status = 'on_site'
        if commit:
            db.session.commit()
        return True
    return False


def _active_assignments(task):
    return [a for a in task.assignments if a.status == 'assigned']


def _all_workers_finished(task):
    active = _active_assignments(task)
    return bool(active) and all((a.worker_status or 'assigned') == 'completed' for a in active)


def _maybe_mark_task_on_site(task):
    return _sync_task_confirmation_status(task, commit=False)


def _apply_worker_ratings(task):
    for assignment in _active_assignments(task):
        user = assignment.user
        if not user:
            continue
        if assignment.assigned_at and (utc_now() - assignment.assigned_at) > timedelta(hours=24):
            user.update_auto_rating(success=False)
        else:
            user.update_auto_rating(success=True)


def _finalize_task_completion(task):
    task.status = 'done'
    task.completed_at = utc_now()
    _apply_worker_ratings(task)
    for assignment in _active_assignments(task):
        assignment.status = 'completed'
        assignment.completed_at = utc_now()
    _sync_task_assigned_to_id(task)
    if task.chat_id:
        chat = db.session.get(Chat, task.chat_id)
        if chat:
            TaskChatService.schedule_chat_deletion(chat, hours=24)


def _can_view_archive():
    """Архив в списке заявок — только для диспетчеров и выше (не исполнители)."""
    return current_user.role in [
        'dispatcher', 'senior_dispatcher', 'director', 'creator', 'manager',
    ]


def _active_tasks_filter(query):
    """Исключает завершённые и проваленные заявки из активного списка."""
    return query.filter(Task.status.notin_(ARCHIVED_TASK_STATUSES))


def _archive_tasks_query():
    """Заявки архива: done/failed. Исполнители видят только свои."""
    query = _scope_tasks(
        _task_query().filter(Task.status.in_(ARCHIVED_TASK_STATUSES))
    )
    if current_user.role == 'worker':
        query = query.filter(Task.assignments.any(user_id=current_user.id))
    return query.order_by(Task.completed_at.desc(), Task.created_at.desc())


def _get_worker_assignment(task_id):
    return TaskAssignment.query.filter_by(
        task_id=task_id,
        user_id=current_user.id,
        status='assigned',
    ).first()


def get_task_tracking_for_user(task, user):
    """Данные линейного трекинга для карточки заявки (исполнитель)."""
    if not task or not user:
        return None
    if getattr(user, 'role', None) != 'worker' or not getattr(user, 'is_verified', False):
        return None
    assignment = None
    for a in task.assignments:
        if a.user_id == user.id and a.status == 'assigned':
            assignment = a
            break
    if not assignment:
        assignment = TaskAssignment.query.filter_by(
            task_id=task.id,
            user_id=user.id,
            status='assigned',
        ).first()
    if not assignment:
        return None
    return _user_tracking_payload(task, assignment)


def _handle_tracking_step(task_id, step):
    task = _get_scoped_task_or_404(task_id)
    assignment = _get_worker_assignment(task_id)

    if not assignment:
        return jsonify({'error': 'Вы не назначены на эту заявку'}), 403
    if current_user.role != 'worker' or not getattr(current_user, 'is_verified', False):
        return jsonify({'error': 'Доступ только для утверждённых исполнителей'}), 403

    now = utc_now()
    ws = assignment.worker_status or 'assigned'

    if step == 'en_route':
        if ws != 'assigned':
            return jsonify({'error': 'Статус «В пути» уже зафиксирован'}), 400
        if not _can_start_en_route(task):
            return jsonify({'error': 'Кнопка «В пути» доступна за 2 часа до начала'}), 400
        assignment.en_route_at = now
        assignment.worker_status = 'en_route'
        assignment.route_reminder_stage = 0
        assignment.route_deadline_at = None
    elif step == 'on_site':
        if ws != 'en_route':
            return jsonify({'error': 'Сначала отметьте «В пути»'}), 400
        assignment.started_working_at = now
        assignment.worker_status = 'on_site'
    elif step == 'finish':
        if ws != 'on_site':
            return jsonify({'error': 'Сначала отметьте «Я на месте»'}), 400
        assignment.finished_working_at = now
        assignment.worker_status = 'completed'
        _maybe_mark_task_on_site(task)
    else:
        return jsonify({'error': 'Неизвестное действие'}), 400

    db.session.commit()
    notify_dispatchers_worker_status(task, current_user, step, actor_id=current_user.id)
    _emit_task_ws('task_updated', task.id, actor_id=current_user.id)

    tracking = _user_tracking_payload(task, assignment)
    return jsonify({
        'ok': True,
        'worker_status': assignment.worker_status,
        'work_duration': tracking.get('work_duration'),
        'tracking': tracking,
        'payload': _task_ws_payload(task),
    })


def _archive_assignments_payload(task):
    items = []
    for assignment in task.assignments:
        user = assignment.user
        avatar = ''
        if user and user.avatar:
            avatar = url_for('uploaded_file', filename=_avatar_basename(user))
        items.append({
            'user_id': int(assignment.user_id),
            'user_name': str(user.name if user else 'Unknown'),
            'user_avatar': avatar,
        })
    return items


def _archive_task_payload(task):
    workers = []
    for assignment in task.assignments:
        workers.append(_worker_tracking_payload(assignment))

    return {
        'id': task.id,
        'task_number': task.task_number or '',
        'title': task.title,
        'price': task.price,
        'status': task.status,
        'city': task.city.name if task.city else '',
        'client': task.client.name if task.client else '',
        'created_at': format_local_datetime(task.created_at),
        'completed_at': format_local_datetime(task.completed_at),
        'execution_time': task.execution_time.strftime('%H:%M') if task.execution_time else '08:00',
        'execution_date': format_execution_date(task.execution_date),
        'address': task.address or '',
        'assignments': _archive_assignments_payload(task),
        'workers': workers,
    }


def _maybe_create_task_chat(task):
    """Создаёт групповой чат, если заявка укомплектована и включён auto_chat."""
    chat = TaskChatService.ensure_task_group_chat(task)
    if chat:
        participant_ids = {task.created_by_id}
        for worker in task.get_assigned_workers():
            participant_ids.add(worker.id)
        send_update('auto_chat_created', {
            'chat_id': chat.id,
            'task_id': task.id,
            'type': chat.type,
            'name': chat.name,
            'task_title': task.title,
            'participant_ids': list(participant_ids),
        })
    return chat


@tasks_bp.route('/tasks')
@login_required
def tasks_list():
    # 1. Проверка базового доступа: если роли нет в списке — отдаем пустую страницу
    allowed_roles = ['worker', 'dispatcher', 'senior_dispatcher', 'director', 'creator']
    if current_user.role not in allowed_roles:
        return render_template('tasks/list.html', tasks=[], cities=City.query.all(), 
                               share_chats=[],
                               my_in_progress=[], pinned_tasks=[], pinned_tasks_ids=[],
                               can_view_archive=False, archive_page=False, active_tab='tasks')

    # 2. Получаем ID заявок, которые текущий пользователь УЖЕ взял (чтобы не дублировать в общем списке)
    assigned_ids = [a.task_id for a in TaskAssignment.query.filter_by(
        user_id=current_user.id, status='assigned').all()]

    # 3. Только активные заявки (без архива)
    query = _scope_tasks(_active_tasks_filter(_task_query())).filter(
        ~Task.id.in_(assigned_ids) if assigned_ids else True
    )
    # --- ИСПРАВЛЕННЫЙ ПЛАН: ОГРАНИЧЕНИЕ ПО ГОРОДАМ ---
    if current_user.role == 'worker':
        import json
        locations = current_user.allowed_locations
        
        # Безопасно парсим локации
        if isinstance(locations, str):
            try:
                locations = json.loads(locations)
            except:
                locations = []
        
        # Если у работника ЕСТЬ привязанные города — фильтруем по ним
        if locations and isinstance(locations, list):
            query = query.filter(Task.city_id.in_(locations))
        else:
            # Если городов НЕТ — либо показываем ВСЁ (закомментируй filter), 
            # либо не показываем НИЧЕГО (оставь как есть)
            # Сейчас оставим "не показывать ничего", но БЕЗ мгновенного return
            from sqlalchemy import false
            query = query.filter(false())

    # 4. Мои заявки в работе (те, что отображаются отдельно)
    my_in_progress = _scope_tasks(_active_tasks_filter(_task_query())).filter(
        Task.assignments.any(user_id=current_user.id, status='assigned'),
    ).all()
    # 5. Закрепленные (pinned) заявки — только активные
    pinned_items = PinnedItem.query.filter_by(user_id=current_user.id, item_type='task').all()
    pinned_tasks_ids = [item.item_id for item in pinned_items]
    pinned_tasks = (
        _scope_tasks(_active_tasks_filter(_task_query())).filter(
            Task.id.in_(pinned_tasks_ids),
        ).all()
        if pinned_tasks_ids else []
    )
    # 6. Фильтры: поиск, город, дата выполнения, статус
    search_q = (request.args.get('search') or '').strip()
    city_filter = request.args.get('city_id', type=int)
    execution_date_raw = (request.args.get('execution_date') or '').strip()
    execution_date_filter = parse_execution_date(execution_date_raw) if execution_date_raw else None
    status_filter = (request.args.get('status') or '').strip()

    def _apply_worker_scope(task_query):
        if current_user.role != 'worker':
            return task_query
        import json
        locations = current_user.allowed_locations
        if isinstance(locations, str):
            try:
                locations = json.loads(locations)
            except Exception:
                locations = []
        if locations and isinstance(locations, list):
            return task_query.filter(Task.city_id.in_(locations))
        from sqlalchemy import false
        return task_query.filter(false())

    if status_filter in ARCHIVED_TASK_STATUSES:
        query = _scope_tasks(_task_query()).filter(Task.status == status_filter)
        if current_user.role == 'worker':
            query = query.filter(Task.assignments.any(user_id=current_user.id))
    elif status_filter == 'in_progress':
        query = _scope_tasks(_active_tasks_filter(_task_query())).filter(Task.status == 'in_progress')
        if assigned_ids:
            query = query.filter(~Task.id.in_(assigned_ids))
        query = _apply_worker_scope(query)
    else:
        if assigned_ids:
            query = query.filter(~Task.id.in_(assigned_ids))

    if search_q:
        like = f'%{search_q}%'
        query = query.filter(or_(Task.title.ilike(like), Task.task_number.ilike(like)))
    if city_filter:
        query = query.filter(Task.city_id == city_filter)
    if execution_date_filter:
        query = query.filter(Task.execution_date == execution_date_filter)
        
    # Формируем итоговый список
    tasks = query.order_by(Task.created_at.desc()).all()
    all_cities = City.query.order_by(City.name).all()

    return render_template('tasks/list.html', 
                           tasks=tasks, 
                           cities=all_cities, 
                           my_in_progress=my_in_progress,
                           pinned_tasks=pinned_tasks,
                           pinned_tasks_ids=pinned_tasks_ids,
                           can_view_archive=_can_view_archive(),
                           archive_page=False,
                           archive_tasks=[],
                           status_filter=status_filter,
                           share_chats=_user_chats_for_share(),
                           share_forward_targets=_share_forward_targets_json(),
                           active_tab='tasks')


@tasks_bp.route('/tasks/archive')
@login_required
def tasks_archive():
    if current_user.role in ['worker', 'brigadir']:
        return redirect(url_for('tasks.my_tasks'))

    allowed_roles = ['dispatcher', 'senior_dispatcher', 'director', 'creator', 'manager']
    if current_user.role not in allowed_roles and not _can_view_archive():
        flash('Недостаточно прав для просмотра архива')
        return redirect(url_for('tasks.tasks_list'))

    tasks = _archive_tasks_query().all()
    archive_payload = [_archive_task_payload(task) for task in tasks]
    all_cities = City.query.order_by(City.name).all()

    return render_template(
        'tasks/list.html',
        tasks=[],
        cities=all_cities,
        my_in_progress=[],
        pinned_tasks=[],
        pinned_tasks_ids=[],
        can_view_archive=_can_view_archive(),
        archive_page=True,
        archive_tasks=archive_payload,
        share_chats=_user_chats_for_share(),
        share_forward_targets=_share_forward_targets_json(),
        active_tab='tasks',
    )


@tasks_bp.route('/task/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if current_user.role not in ['dispatcher', 'senior_dispatcher', 'director', 'creator']:
        flash('Только диспетчеры и выше могут создавать заявки')
        return redirect(url_for('tasks.tasks_list'))
    
    if request.method == 'POST':
        ws_id = current_user.workspace_id
        if not ws_id:
            flash('Рабочее пространство не назначено. Обратитесь к администратору.')
            return redirect(url_for('tasks.tasks_list'))

        try:
            title = request.form.get('title')
            description = request.form.get('description')
            required_workers = request.form.get('required_workers', 1, type=int)
            
            # Цена
            price_raw = request.form.get('price_display', '0').strip()

            # Проверяем формат "цена/часы"
            import re
            hourly_match = re.match(r'^(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)$', price_raw)

            if hourly_match:
                hourly_rate = float(hourly_match.group(1))
                min_hours = float(hourly_match.group(2))
                price = int(hourly_rate * min_hours)
            else:
                # Обычное число
                price_cleaned = ''.join(filter(str.isdigit, price_raw))
                price = int(price_cleaned) if price_cleaned else 0
            
            # Город
            city_id_raw = request.form.get('city_id')
            city_id = int(city_id_raw) if city_id_raw and city_id_raw.isdigit() else None
            
            # Клиент (выбор из списка или ручной ввод)
            client_id_raw = request.form.get('client_id')
            client_name = request.form.get('client_name')
            
            client_id = None
            if client_id_raw and client_id_raw.isdigit():
                client_id = int(client_id_raw)
            elif client_name and client_name.strip():
                new_client = Client(
                    name=client_name.strip(),
                    workspace_id=ws_id,
                )
                db.session.add(new_client)
                db.session.commit()
                client_id = new_client.id
            
            # Дата выполнения, адрес и время
            execution_date = parse_execution_date(request.form.get('execution_date'))
            address = (request.form.get('address') or '').strip() or None

            execution_time = _parse_execution_time(request.form.get('execution_time'))
            auto_chat = request.form.get('auto_chat') == '1'
            
            task = Task(
                title=title,
                description=description,
                price=price,
                required_workers=required_workers,
                status='recruiting',
                city_id=city_id,
                client_id=client_id,
                address=address,
                execution_date=execution_date,
                execution_time=execution_time,
                auto_chat=auto_chat,
                workspace_id=ws_id,
                created_by_id=current_user.id,
                created_at=utc_now(),
            )
            task.workspace_id = ws_id
            
            db.session.add(task)
            db.session.commit()

            worker_ids = request.form.getlist('worker_ids')
            for wid in worker_ids:
                try:
                    _assign_worker_to_task(task, int(wid), current_user.id)
                except (TypeError, ValueError):
                    continue
            db.session.commit()

            notify_new_task(task, _new_task_ws_payload(task))

            flash('Заявка успешно создана!')
            return redirect(url_for('tasks.tasks_list'))            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка создания задачи: {e}")
            flash(f'Ошибка при создании заявки: {str(e)}')
            return redirect(url_for('tasks.create_task'))
    
    cities = City.query.order_by(City.name).all()
    clients = _workspace_clients_query().order_by(Client.name).all()
    ws_id = current_user.workspace_id
    available_workers = []
    if ws_id:
        from services.notification_service import _worker_allowed_for_task

        class _DummyTask:
            pass

        dummy = _DummyTask()
        dummy.workspace_id = ws_id
        dummy.city_id = None
        available_workers = [
            w for w in User.query.filter(
                User.workspace_id == ws_id,
                User.role.in_(['worker', 'brigadir']),
                User.is_verified.is_(True),
            ).order_by(User.name).all()
            if _worker_allowed_for_task(w, dummy)
        ]

    task = None
    copy_from = request.args.get('copy_from', type=int)
    if copy_from:
        task = _scope_tasks(_task_query()).filter(Task.id == copy_from).first_or_404()

    return render_template(
        'tasks/create.html',
        cities=cities,
        clients=clients,
        task=task,
        available_workers=available_workers,
        active_tab='tasks',
    )

def _take_task_for_current_user(task_id):
    """Взять заявку исполнителем. Возвращает (task, assignment, error, status_code)."""
    if current_user.role != 'worker':
        return None, None, 'Только исполнители могут брать заявки', 403

    task = _get_scoped_task_or_404(task_id)

    if task.status not in ['recruiting', 'in_progress']:
        return None, None, 'Заявка уже не доступна', 400

    active = TaskAssignment.query.filter_by(
        task_id=task.id, user_id=current_user.id, status='assigned'
    ).first()
    if active:
        return None, None, 'Вы уже взяли эту заявку', 400

    prev = TaskAssignment.query.filter_by(task_id=task.id, user_id=current_user.id).first()
    if prev:
        prev.status = 'assigned'
        prev.worker_status = 'assigned'
        prev.assigned_by_id = current_user.id
        prev.assigned_at = utc_now()
        prev.en_route_at = None
        prev.started_working_at = None
        prev.finished_working_at = None
        prev.route_reminder_stage = 0
        prev.route_deadline_at = None
        assignment = prev
    else:
        assignment = TaskAssignment(
            task_id=task.id,
            user_id=current_user.id,
            assigned_by_id=current_user.id,
            status='assigned',
            worker_status='assigned',
            assigned_at=utc_now(),
        )
        db.session.add(assignment)
    db.session.flush()
    _sync_task_assigned_to_id(task)

    message = None
    if task.is_fully_assigned():
        task.status = 'in_progress'
        _maybe_create_task_chat(task)
        message = f'Заявка полностью укомплектована ({task.required_workers} исполнителей)'
    else:
        needed = task.required_workers - len(task.get_assigned_workers())
        message = f'Вы взяли заявку. Осталось мест: {needed}'

    db.session.commit()
    _emit_task_ws('task_updated', task.id, actor_id=current_user.id)
    return task, assignment, message, 200


@tasks_bp.route('/task/take/<int:task_id>')
@login_required
def take_task(task_id):
    task, assignment, err, code = _take_task_for_current_user(task_id)
    if err:
        flash(err)
        return redirect(url_for('tasks.tasks_list'))
    flash(message or 'Заявка принята')
    return redirect(url_for('tasks.tasks_list'))


@tasks_bp.route('/api/tasks/<int:task_id>/take', methods=['POST'])
@login_required
def api_take_task(task_id):
    task, assignment, message, code = _take_task_for_current_user(task_id)
    if code != 200:
        return jsonify({'ok': False, 'error': message}), code

    tracking = _user_tracking_payload(task, assignment) if assignment else None
    return jsonify({
        'ok': True,
        'message': message,
        'task_id': task.id,
        'status': task.status,
        'tracking': tracking,
        'payload': _task_ws_payload(task),
    })


_TASK_STATUS_API_MAP = {
    'en_route': 'en_route',
    'on_way': 'en_route',
    'on_site': 'on_site',
    'arrived': 'on_site',
    'finish': 'finish',
    'completed': 'finish',
}


@tasks_bp.route('/api/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def api_task_status(task_id):
    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip().lower()

    if status in ('take', 'accept'):
        return api_take_task(task_id)

    if status == 'reject':
        return api_worker_reject_task(task_id)

    if status == 'submit' or status == 'submit_confirmation':
        return submit_confirmation(task_id)

    step = _TASK_STATUS_API_MAP.get(status)
    if not step:
        return jsonify({'ok': False, 'error': 'Неизвестный статус'}), 400
    return _handle_tracking_step(task_id, step)


@tasks_bp.route('/task/<int:task_id>/assign-workers', methods=['POST'])
@login_required
def assign_workers_to_task(task_id):
    task = _get_scoped_task_or_404(task_id)
    if not _can_manage_assignments(task):
        return jsonify({'error': 'Нет прав'}), 403

    data = request.get_json(silent=True) or {}
    raw_ids = data.get('worker_ids') or request.form.getlist('worker_ids') or []
    added = []
    errors = []
    for wid in raw_ids:
        try:
            ok, err = _assign_worker_to_task(task, int(wid), current_user.id)
            if ok:
                added.append(int(wid))
            elif err:
                errors.append(err)
        except (TypeError, ValueError):
            continue

    db.session.commit()
    payload = _task_ws_payload(task)
    _emit_task_ws('task_updated', task.id)
    if added:
        notify_new_task(task, payload)

    return jsonify({
        'ok': True,
        'added': added,
        'errors': errors,
        'assigned_count': len(task.get_assigned_workers()),
        'required_workers': task.required_workers,
        'assignments': _task_assignments_payload(task),
    })


def _api_remove_worker_response(task):
    db.session.commit()
    payload = _task_ws_payload(task)
    _emit_task_ws('task_updated', task.id, actor_id=current_user.id)
    if not task.is_fully_assigned():
        notify_task_reopened(task, payload)
    return jsonify({
        'ok': True,
        'status': task.status,
        'assigned_count': len(task.get_assigned_workers()),
        'required_workers': task.required_workers,
        'assignments': _task_assignments_payload(task),
        'payload': payload,
    })


@tasks_bp.route('/api/tasks/<int:task_id>/remove-worker', methods=['POST'])
@login_required
def api_remove_worker(task_id):
    task = _get_scoped_task_or_404(task_id)
    if not _can_manage_assignments(task):
        return jsonify({'ok': False, 'error': 'Нет прав'}), 403

    data = request.get_json(silent=True) or {}
    user_id = data.get('worker_id') or data.get('user_id')
    if not user_id:
        return jsonify({'ok': False, 'error': 'worker_id обязателен'}), 400

    ok, err = _remove_worker_from_task(task, int(user_id), penalty=False)
    if not ok:
        return jsonify({'ok': False, 'error': err}), 400

    return _api_remove_worker_response(task)


@tasks_bp.route('/task/<int:task_id>/remove-worker/<int:user_id>', methods=['POST'])
@login_required
def remove_worker_from_task(task_id, user_id):
    task = _get_scoped_task_or_404(task_id)
    if not _can_manage_assignments(task):
        return jsonify({'error': 'Нет прав'}), 403

    ok, err = _remove_worker_from_task(task, user_id, penalty=False)
    if not ok:
        return jsonify({'error': err}), 400

    return _api_remove_worker_response(task)


@tasks_bp.route('/api/tasks/<int:task_id>/reject', methods=['POST'])
@login_required
def api_worker_reject_task(task_id):
    task = _get_scoped_task_or_404(task_id)
    if current_user.role != 'worker' or not getattr(current_user, 'is_verified', False):
        return jsonify({'ok': False, 'error': 'Доступ только для утверждённых исполнителей'}), 403

    ok, err = _worker_reject_assignment(task)
    if not ok:
        return jsonify({'ok': False, 'error': err}), 400

    db.session.commit()
    payload = _task_ws_payload(task)
    _emit_task_ws('task_updated', task.id, actor_id=current_user.id)
    notify_task_reopened(task, payload)

    return jsonify({
        'ok': True,
        'status': task.status,
        'message': 'Вы отказались от заявки',
        'payload': payload,
    })


@tasks_bp.route('/task/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = _get_scoped_task_or_404(task_id)

    _sync_task_confirmation_status(task)
    if not _can_confirm_task(task):
        flash('Нет прав для подтверждения этой заявки')
        return redirect(url_for('tasks.tasks_list'))

    _maybe_mark_task_on_site(task)
    _finalize_task_completion(task)
    db.session.commit()

    _emit_task_ws('task_updated', task.id)

    flash('Заявка подтверждена и завершена!')
    return redirect(request.referrer or url_for('tasks.tasks_list'))


@tasks_bp.route('/task/reject/<int:task_id>', methods=['POST'])
@login_required
def reject_task_completion(task_id):
    task = _get_scoped_task_or_404(task_id)

    _sync_task_confirmation_status(task)
    if not _can_confirm_task(task):
        flash('Нет прав для отклонения этой заявки')
        return redirect(url_for('tasks.tasks_list'))

    task.status = 'in_progress'
    for assignment in _active_assignments(task):
        if (assignment.worker_status or 'assigned') == 'completed':
            assignment.worker_status = 'on_site'
            assignment.finished_working_at = None

    db.session.commit()
    _emit_task_ws('task_updated', task.id)

    flash('Заявка возвращена в работу')
    return redirect(request.referrer or url_for('tasks.tasks_list'))


@tasks_bp.route('/task/copy/<int:task_id>')
@login_required
def copy_task(task_id):
    if current_user.role not in ['dispatcher', 'senior_dispatcher', 'director', 'creator']:
        flash('Только диспетчеры и выше могут копировать заявки')
        return redirect(url_for('tasks.tasks_list'))
    
    _get_scoped_task_or_404(task_id)
    # Просто перенаправляем на создание с параметрами из оригинальной заявки
    return redirect(url_for('tasks.create_task', copy_from=task_id))

def _can_forward_to_chat(task):
    return current_user.role in ['creator', 'director', 'senior_dispatcher', 'dispatcher']


def _user_chats_for_share():
    from services.forward_targets import get_forward_target_chats

    return get_forward_target_chats(current_user.id)


def _share_forward_targets_json():
    from services.forward_targets import get_forward_target_chats, serialize_forward_targets

    chats = get_forward_target_chats(current_user.id)
    return serialize_forward_targets(chats, current_user)


@tasks_bp.route('/tasks/<int:task_id>/share-to-chat', methods=['POST'])
@login_required
def share_task_to_chat(task_id):
    task = _get_scoped_task_or_404(task_id)
    if not _can_forward_to_chat(task):
        return jsonify({'status': 'error', 'error': 'Нет прав'}), 403

    data = request.get_json(silent=True) or {}
    raw_ids = data.get('chat_ids')
    if raw_ids is None and data.get('target_chat_id'):
        raw_ids = [data.get('target_chat_id')]

    if not isinstance(raw_ids, list):
        return jsonify({'status': 'error', 'error': 'Некорректный список чатов'}), 400

    try:
        chat_ids = []
        seen = set()
        for cid in raw_ids:
            n = int(cid)
            if n not in seen:
                seen.add(n)
                chat_ids.append(n)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'error': 'Некорректный список чатов'}), 400

    if not chat_ids:
        return jsonify({'status': 'error', 'error': 'Выберите получателей'}), 400

    from services.forward_targets import is_allowed_forward_chat

    title = task.title or f'Заявка №{task.task_number or task.id}'
    plain_text = f'📋 {title}'
    processed = 0
    notify_queue = []

    for target_chat_id in chat_ids:
        target_chat = Chat.query.get(target_chat_id)
        if not target_chat:
            continue

        participant = ChatParticipant.query.filter_by(
            chat_id=target_chat.id,
            user_id=current_user.id,
        ).first()
        if not participant:
            continue

        if not is_allowed_forward_chat(current_user.id, target_chat.id):
            continue

        message = Message(
            chat_id=target_chat.id,
            sender_id=current_user.id,
            text=encrypt_data(plain_text),
            task_id=task.id,
            workspace_id=target_chat.workspace_id or task.workspace_id,
        )
        db.session.add(message)
        db.session.flush()
        notify_queue.append((target_chat, message.id))
        processed += 1

    if processed == 0:
        db.session.rollback()
        return jsonify({'status': 'error', 'error': 'Не удалось отправить ни в один чат'}), 400

    db.session.commit()

    for target_chat, message_id in notify_queue:
        message = db.session.get(Message, message_id)
        if not message:
            continue
        notify_chat_message(target_chat.id, current_user.id, {
            'chat_id': target_chat.id,
            'id': message.id,
            'message': plain_text,
            'text': plain_text,
            'sender_id': current_user.id,
            'author_id': current_user.id,
            'author_name': current_user.name,
            'sender_name': current_user.name,
            'sender_avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
            'avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
            'created_at': utc_iso(message.created_at),
            'is_read': False,
            'attachments': [],
            'task_id': task.id,
        })

    return jsonify({'status': 'success', 'processed': processed, 'success': True})


@tasks_bp.route('/task/detail/<int:task_id>')
@tasks_bp.route('/tasks/detail/<int:task_id>')
@login_required
def task_detail(task_id):
    task = _scope_tasks(_task_ws_query()).filter(Task.id == task_id).first_or_404()

    user_assignment = TaskAssignment.query.filter_by(
        task_id=task.id,
        user_id=current_user.id,
        status='assigned',
    ).first()

    is_verified_worker = (
        current_user.role == 'worker'
        and getattr(current_user, 'is_verified', False)
        and user_assignment is not None
    )
    is_manager = _is_task_manager(task)

    _sync_task_confirmation_status(task, commit=True)

    worker_tracking = []
    if is_manager:
        for assignment in task.assignments:
            if assignment.status != 'assigned':
                continue
            worker_tracking.append(_worker_tracking_payload(assignment))

    my_in_progress = _scope_tasks(_active_tasks_filter(_task_query())).filter(
        Task.assignments.any(user_id=current_user.id, status='assigned'),
    ).all()

    can_reject_assignment = False
    reject_block_reason = None
    if is_verified_worker and user_assignment:
        can_reject_assignment, reject_block_reason = _can_worker_reject_assignment(
            task, user_assignment
        )
        if can_reject_assignment:
            reject_block_reason = None

    all_tasks = _scope_tasks(_active_tasks_filter(_task_query())).order_by(Task.created_at.desc()).all()
    cities = City.query.order_by(City.name).all()
    embed_mode = request.args.get('embed') == 'chat'
    is_chat = request.args.get('is_chat') in ('1', 'true', 'True') or embed_mode
    can_manage_assignments = _can_manage_assignments(task)
    available_workers = get_eligible_workers(task) if can_manage_assignments else []
    assigned_workers = task.get_assigned_workers()
    return render_template(
        'tasks/detail.html',
        task=task,
        tasks=all_tasks,
        cities=cities,
        my_in_progress=my_in_progress,
        user_assignment=user_assignment,
        is_verified_worker=is_verified_worker,
        is_manager=is_manager,
        can_manage_assignments=can_manage_assignments,
        available_workers=available_workers,
        assigned_workers=assigned_workers,
        worker_tracking=worker_tracking,
        user_tracking=_user_tracking_payload(task, user_assignment) if is_verified_worker else None,
        can_reject_assignment=can_reject_assignment,
        reject_block_reason=reject_block_reason,
        can_en_route=_can_start_en_route(task),
        can_confirm_completion=_can_confirm_task(task),
        can_forward_to_chat=_can_forward_to_chat(task),
        is_chat=is_chat,
        active_tab='tasks',
    )


@tasks_bp.route('/task/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = _get_scoped_task_or_404(task_id)

    if current_user.id != task.created_by_id and current_user.role not in ['senior_dispatcher', 'director']:
        flash('Нет прав для редактирования')
        return redirect(url_for('tasks.tasks_list'))
    ws_id = current_user.workspace_id
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.city_id = request.form.get('city_id') or None
        task.address = (request.form.get('address') or '').strip() or None
        task.required_workers = request.form.get('required_workers', 1, type=int)
        
        # Клиент (выбор из списка или ручной ввод)
        client_id_raw = request.form.get('client_id')
        client_name = request.form.get('client_name')
        
        if client_id_raw and client_id_raw.isdigit():
            task.client_id = int(client_id_raw)
        elif client_name and client_name.strip():
            new_client = Client(
                name=client_name.strip(),
                workspace_id=ws_id,
            )
            db.session.add(new_client)
            db.session.commit()
            task.client_id = new_client.id
        else:
            task.client_id = None
        
        # Цена
        price_display = request.form.get('price_display', '')
        hourlyMatch = re.match(r'^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$', price_display.strip())
        if hourlyMatch:
            task.price = int(float(hourlyMatch.group(1)) * float(hourlyMatch.group(2)))
        elif price_display.strip().isdigit():
            task.price = int(price_display.strip())
        
        execution_date_str = request.form.get('execution_date')
        if execution_date_str:
            task.execution_date = parse_execution_date(execution_date_str)
        else:
            task.execution_date = None

        task.execution_time = _parse_execution_time(request.form.get('execution_time'))
        task.auto_chat = request.form.get('auto_chat') == '1'
        task.workspace_id = ws_id

        if task.is_fully_assigned() and task.status == 'recruiting':
            task.status = 'in_progress'
        _maybe_create_task_chat(task)
        
        db.session.commit()
        _emit_task_ws('task_updated', task.id)
        flash('Заявка обновлена')
        return redirect(url_for('tasks.tasks_list'))    
    cities = City.query.order_by(City.name).all()
    clients = _workspace_clients_query().order_by(Client.name).all()
    return render_template('tasks/edit.html', task=task, cities=cities, clients=clients, active_tab='tasks')

@tasks_bp.route('/task/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = _get_scoped_task_or_404(task_id)
    wants_json = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in (request.accept_mimetypes.values() or [])
    )

    if not _can_delete_task(task):
        msg = 'Нет прав для удаления этой заявки'
        if wants_json:
            return jsonify({'status': 'error', 'error': msg}), 403
        flash(msg)
        return redirect(url_for('tasks.tasks_list'))

    label = _task_delete_label(task)
    worker_ids = [w.id for w in task.get_assigned_workers()]
    cancel_message = f'Внимание! Заявка {label} отменена диспетчером.'
    task_snapshot = {
        'id': int(task.id),
        'task_id': int(task.id),
        'title': str(task.title or ''),
        'task_number': task.task_number or '',
        'workspace_id': int(task.workspace_id) if task.workspace_id else None,
        'message': cancel_message,
    }

    try:
        _detach_task_references(task.id)
        db.session.delete(task)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        current_app.logger.exception('delete_task failed for task_id=%s', task_id)
        msg = 'Не удалось удалить заявку: есть связанные данные'
        if wants_json:
            return jsonify({'status': 'error', 'error': msg}), 409
        flash(msg)
        return redirect(url_for('tasks.tasks_list'))
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('delete_task failed for task_id=%s', task_id)
        if wants_json:
            return jsonify({'status': 'error', 'error': 'Ошибка при удалении заявки'}), 500
        flash('Ошибка при удалении заявки')
        return redirect(url_for('tasks.tasks_list'))

    for uid in worker_ids:
        _safe_notify_task_cancelled(uid, task_snapshot, cancel_message)

    _safe_send_update('task_deleted', {'id': task_id, **task_snapshot})

    return jsonify({'status': 'success'}), 200

@tasks_bp.route('/api/task/<int:task_id>')
@login_required
def api_task_detail(task_id):
    task = _scope_tasks(_task_ws_query()).filter(Task.id == task_id).first_or_404()

    user_assignment = TaskAssignment.query.filter_by(
        task_id=task.id,
        user_id=current_user.id,
        status='assigned',
    ).first()

    is_verified_worker = (
        current_user.role == 'worker'
        and getattr(current_user, 'is_verified', False)
        and user_assignment is not None
    )
    is_manager = _is_task_manager(task)

    _sync_task_confirmation_status(task, commit=True)

    workers = []
    if is_manager:
        for assignment in task.assignments:
            workers.append(_worker_tracking_payload(assignment))

    start_dt = _task_start_datetime(task)
    payload = {
        'id': task.id,
        'title': task.title,
        'description': task.description or '',
        'price': task.price,
        'status': task.status,
        'is_archived': task.status == 'done',
        'required_workers': task.required_workers,
        'assigned_count': len(task.get_assigned_workers()) if task.status != 'done' else len(task.assignments),
        'city': task.city.name if task.city else None,
        'address': task.address or '',
        'client': task.client.name if task.client else None,
        'execution_date': format_execution_date(task.execution_date),
        'created_at': format_local_datetime(task.created_at),
        'completed_at': format_local_datetime(task.completed_at),
        'execution_time': task.execution_time.strftime('%H:%M') if task.execution_time else '08:00',
        'task_start_iso': start_dt.isoformat(),
        'chat_id': task.chat_id,
        'created_by_id': task.created_by_id,
        'current_user_id': current_user.id,
        'current_user_role': current_user.role,
        'is_verified_worker': is_verified_worker,
        'is_manager': is_manager,
        'can_take': (
            current_user.role == 'worker'
            and getattr(current_user, 'is_verified', False)
            and not user_assignment
            and task.status in ['recruiting', 'in_progress']
        ),
        'user_tracking': _user_tracking_payload(task, user_assignment) if is_verified_worker else None,
        'workers': workers,
        'can_confirm_completion': _can_confirm_task(task),
        'can_submit_confirmation': bool(
            is_verified_worker
            and user_assignment
            and _user_tracking_payload(task, user_assignment).get('can_submit_confirmation')
        ),
        'can_reject_assignment': bool(
            is_verified_worker
            and user_assignment
            and _can_worker_reject_assignment(task, user_assignment)[0]
        ),
        'reject_block_reason': (
            None
            if (is_verified_worker and user_assignment and _can_worker_reject_assignment(task, user_assignment)[0])
            else (
                _can_worker_reject_assignment(task, user_assignment)[1]
                if is_verified_worker and user_assignment
                else None
            )
        ),
    }
    if current_user.role != 'worker':
        payload['task_number'] = task.task_number
    return jsonify(payload)


@tasks_bp.route('/tasks/<int:task_id>/go_route', methods=['POST'])
@login_required
def go_route(task_id):
    return _handle_tracking_step(task_id, 'en_route')


@tasks_bp.route('/tasks/<int:task_id>/arrive_site', methods=['POST'])
@login_required
def arrive_site(task_id):
    return _handle_tracking_step(task_id, 'on_site')


@tasks_bp.route('/tasks/<int:task_id>/finish_work', methods=['POST'])
@login_required
def finish_work(task_id):
    return _handle_tracking_step(task_id, 'finish')


@tasks_bp.route('/tasks/<int:task_id>/submit_confirmation', methods=['POST'])
@login_required
def submit_confirmation(task_id):
    task = _get_scoped_task_or_404(task_id)
    assignment = _get_worker_assignment(task_id)

    if not assignment:
        return jsonify({'error': 'Вы не назначены на эту заявку'}), 403
    if current_user.role != 'worker' or not getattr(current_user, 'is_verified', False):
        return jsonify({'error': 'Доступ только для утверждённых исполнителей'}), 403
    if (assignment.worker_status or 'assigned') != 'completed':
        return jsonify({'error': 'Сначала отметьте «Закончил»'}), 400

    _maybe_mark_task_on_site(task)
    if task.status == 'waiting_confirm':
        return jsonify({'error': 'Заявка уже отправлена на подтверждение'}), 400
    if task.status not in PENDING_CONFIRM_STATUSES and not (
        task.status == 'in_progress' and _all_workers_finished(task)
    ):
        return jsonify({'error': 'Заявка ещё не готова к отправке на подтверждение'}), 400

    task.status = 'waiting_confirm'
    db.session.commit()
    _emit_task_ws('task_updated', task.id)

    tracking = _user_tracking_payload(task, assignment)
    return jsonify({
        'ok': True,
        'status': task.status,
        'tracking': tracking,
        'payload': _task_ws_payload(task),
    })


@tasks_bp.route('/api/task/<int:task_id>/tracking', methods=['POST'])
@login_required
def api_task_tracking(task_id):
    action_map = {
        'en_route': 'en_route',
        'on_site': 'on_site',
        'finish': 'finish',
    }
    action = (request.get_json(silent=True) or {}).get('action')
    step = action_map.get(action)
    if not step:
        return jsonify({'error': 'Неизвестное действие'}), 400
    return _handle_tracking_step(task_id, step)


@tasks_bp.route('/api/tasks/archive')
@login_required
def api_tasks_archive():
    if not _can_view_archive():
        return jsonify({'error': 'Недостаточно прав'}), 403

    tasks = _archive_tasks_query().all()
    return jsonify({
        'tasks': [_archive_task_payload(task) for task in tasks],
    })

@tasks_bp.route('/api/favorite-city/<int:city_id>', methods=['POST'])
@login_required
def toggle_favorite_city(city_id):
    favs = list(current_user.favorite_cities or [])
    
    if city_id in favs:
        favs.remove(city_id)
        status = 'removed'
    else:
        favs.append(city_id)
        status = 'added'
    
    current_user.favorite_cities = favs
    db.session.commit()
    return jsonify({'status': status, 'favs': favs})


@tasks_bp.route('/my-tasks')
@login_required
def my_tasks():
    in_progress = _scope_tasks(_task_query()).filter_by(
        assigned_to_id=current_user.id,
        status='in_progress'
    ).all()

    completed = _scope_tasks(_task_query()).filter_by(
        assigned_to_id=current_user.id,
        status='done'
    ).order_by(Task.completed_at.desc()).all()

    failed = _scope_tasks(_task_query()).filter_by(
        assigned_to_id=current_user.id,
        status='failed'
    ).order_by(Task.completed_at.desc()).all()

    return render_template(
        'tasks/my_tasks.html',
        in_progress=in_progress,
        completed=completed,
        failed=failed,
        pinned_tasks_ids=[],
        active_tab='tasks',
    )