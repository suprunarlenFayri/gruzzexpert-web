"""Фоновые таймеры подтверждения «В пути» и напоминания исполнителям."""

import threading
import time
from datetime import timedelta

from models import Task, TaskAssignment, db
from services.notification_service import notify_task_reopened, notify_worker
from utils.datetime_utils import utc_now


def _task_start_datetime(task):
    from routes.tasks import _task_start_datetime as calc_start
    return calc_start(task)


def _process_assignment(app, assignment):
    from routes.tasks import _emit_task_ws, _task_ws_payload

    task = assignment.task
    if not task or task.status in ('done', 'failed', 'waiting_confirm'):
        return

    if assignment.status != 'assigned':
        return

    ws = assignment.worker_status or 'assigned'
    if ws != 'assigned':
        return

    start = _task_start_datetime(task)
    now = utc_now()
    worker = assignment.user
    if not worker:
        return

    two_hours_before = start - timedelta(hours=2)
    stage = assignment.route_reminder_stage or 0

    if stage == 0 and now >= two_hours_before:
        notify_worker(
            worker.id,
            'route_reminder',
            'Подтвердите статус «В пути»',
            task.title or f'Заявка №{task.task_number or task.id}',
            task_id=task.id,
        )
        assignment.route_reminder_stage = 1
        assignment.route_deadline_at = now + timedelta(minutes=10)
        db.session.commit()
        return

    if not assignment.route_deadline_at or now < assignment.route_deadline_at:
        return

    if stage == 1:
        notify_worker(
            worker.id,
            'route_nudge',
            'Повторное напоминание',
            'Нажмите «В пути» в течение 5 минут',
            task_id=task.id,
        )
        assignment.route_reminder_stage = 2
        assignment.route_deadline_at = now + timedelta(minutes=5)
        db.session.commit()
        return

    if stage == 2:
        notify_worker(
            worker.id,
            'route_alarm',
            'Срочно подтвердите «В пути»!',
            task.title or f'Заявка №{task.task_number or task.id}',
            task_id=task.id,
            alarm=True,
        )
        assignment.route_reminder_stage = 3
        assignment.route_deadline_at = now + timedelta(minutes=3)
        db.session.commit()
        return

    if stage == 3:
        assignment.status = 'removed'
        assignment.route_reminder_stage = 4
        assignment.route_deadline_at = None
        worker.missed_tasks = int(worker.missed_tasks or 0) + 1
        worker.rating = max(0.0, float(worker.rating or 0) - 0.5)

        active_count = sum(
            1 for a in task.assignments if a.status == 'assigned'
        )
        if active_count < int(task.required_workers or 1):
            task.status = 'recruiting'

        db.session.commit()
        payload = _task_ws_payload(task)
        from services.notification_service import notify_task_reopened, notify_task_updated
        notify_task_updated(task, payload)
        notify_task_reopened(task, payload)
        notify_worker(
            worker.id,
            'route_removed',
            'Вы сняты с заявки',
            'Не подтверждён статус «В пути». Рейтинг снижен.',
            task_id=task.id,
        )


def run_timer_tick(app):
    with app.app_context():
        try:
            assignments = (
                TaskAssignment.query.join(Task)
                .filter(
                    TaskAssignment.status == 'assigned',
                    TaskAssignment.worker_status == 'assigned',
                    TaskAssignment.route_reminder_stage < 4,
                    Task.status.notin_(['done', 'failed']),
                )
                .all()
            )
            for assignment in assignments:
                try:
                    _process_assignment(app, assignment)
                except Exception as exc:
                    db.session.rollback()
                    print(f'Timer assignment error: {exc}')
        except Exception as exc:
            print(f'Timer tick error: {exc}')


def start_task_timer_worker(app, interval_seconds=60):
    def worker():
        while True:
            time.sleep(interval_seconds)
            run_timer_tick(app)

    thread = threading.Thread(target=worker, daemon=True, name='task-timer')
    thread.start()
