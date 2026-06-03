"""
Исправление workspace_id у заявок с неверной изоляцией.

Запуск из корня проекта:
    python scripts/fix_task_workspace_isolation.py

SQL (PostgreSQL) для заявки «Привет» директора ООО «Отмена»:
    UPDATE tasks
    SET workspace_id = (
        SELECT u.workspace_id
        FROM users u
        WHERE u.id = tasks.created_by_id
    )
    WHERE id = 27
       OR (title ILIKE 'Привет' AND created_by_id IN (
            SELECT id FROM users WHERE role = 'director'
       ));
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Task, User, Workspace


def fix_misassigned_tasks(dry_run=True):
    app = create_app()
    with app.app_context():
        fixes = []

        privet_tasks = Task.query.filter(Task.title.ilike('%Привет%')).all()
        for task in privet_tasks:
            creator = User.query.get(task.created_by_id) if task.created_by_id else None
            target_ws = creator.workspace_id if creator else None
            if target_ws and task.workspace_id != target_ws:
                fixes.append((task.id, task.title, task.workspace_id, target_ws))

        orphan_tasks = Task.query.filter(Task.workspace_id.is_(None)).all()
        for task in orphan_tasks:
            creator = User.query.get(task.created_by_id) if task.created_by_id else None
            target_ws = creator.workspace_id if creator else 1
            fixes.append((task.id, task.title, task.workspace_id, target_ws))

        cross_ws = (
            db.session.query(Task, User)
            .join(User, Task.created_by_id == User.id)
            .filter(Task.workspace_id != User.workspace_id)
            .filter(User.workspace_id.isnot(None))
            .all()
        )
        for task, creator in cross_ws:
            if (task.id, task.title, task.workspace_id, creator.workspace_id) not in fixes:
                fixes.append((task.id, task.title, task.workspace_id, creator.workspace_id))

        if not fixes:
            print('Нет заявок с неверным workspace_id.')
            return

        print('Будут исправлены:')
        for task_id, title, old_ws, new_ws in fixes:
            ws_name = Workspace.query.get(new_ws).name if new_ws else '?'
            print(f'  task #{task_id} «{title}»: {old_ws} -> {new_ws} ({ws_name})')

        if dry_run:
            print('\nDry-run. Для записи: python scripts/fix_task_workspace_isolation.py --apply')
            return

        for task_id, _, _, new_ws in fixes:
            task = Task.query.get(task_id)
            if task:
                task.workspace_id = new_ws
        db.session.commit()
        print(f'\nИсправлено заявок: {len(fixes)}')


if __name__ == '__main__':
    import sys
    apply = '--apply' in sys.argv
    fix_misassigned_tasks(dry_run=not apply)
