"""
Полная очистка тестовых данных перед чистым B2B-запуском.

Использование:
  python scripts/clear_production_db.py --confirm

Создание создателя с TOTP и резервными кодами:
  python scripts/clear_production_db.py --confirm \\
    --bootstrap-creator --name "Арлен" --email creator@gruzz.local --tag arlen
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from models import db
from utils.tags import normalize_tag, tag_is_available
from utils.creator_totp import create_platform_creator

TABLES_TO_PURGE = [
    'message_hidden',
    'blacklist',
    'contacts',
    'pinned_items',
    'forwarded_messages',
    'attachments',
    'messages',
    'chat_participants',
    'chats',
    'task_assignments',
    'tasks',
    'worker_accesses',
    'work_sites',
    'clients',
    'verification_requests',
    'workspace_members',
    'invites',
    'pending_login_attempts',
    'user_sessions',
    'user_devices',
    'phone_recovery_tickets',
    'user_backup_codes',
    'users',
    'workspaces',
]

OPTIONAL_TABLES = ['cities']


def purge_table(table_name):
    from sqlalchemy import text

    bind = db.session.get_bind()
    dialect = bind.dialect.name
    if dialect == 'postgresql':
        db.session.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
    else:
        db.session.execute(text(f'DELETE FROM {table_name}'))
    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description='Очистка БД для чистого B2B-теста')
    parser.add_argument('--confirm', action='store_true', help='Подтвердить удаление всех данных')
    parser.add_argument('--keep-cities', action='store_true', help='Не трогать таблицу cities')
    parser.add_argument('--bootstrap-creator', action='store_true', help='Создать аккаунт создателя с TOTP')
    parser.add_argument('--name', help='Имя создателя (с --bootstrap-creator)')
    parser.add_argument('--email', help='Email создателя (с --bootstrap-creator)')
    parser.add_argument('--tag', help='Уникальный тег создателя (с --bootstrap-creator)')
    args = parser.parse_args()

    if not args.confirm:
        print('ВНИМАНИЕ: будут удалены пользователи, пространства, заявки, чаты и клиенты.')
        print('Для выполнения:  python scripts/clear_production_db.py --confirm')
        print('С создателем:    python scripts/clear_production_db.py --confirm --bootstrap-creator \\')
        print('                   --name "Имя" --email you@corp.ru --tag username')
        return 1

    if args.bootstrap_creator and not all([args.name, args.email, args.tag]):
        print('Для --bootstrap-creator укажите --name, --email и --tag')
        return 1

    app = create_app()
    with app.app_context():
        tables = list(TABLES_TO_PURGE)
        if not args.keep_cities:
            tables.extend(OPTIONAL_TABLES)

        for name in tables:
            try:
                purge_table(name)
                print(f'  OK  {name}')
            except Exception as exc:
                db.session.rollback()
                print(f'  SKIP {name}: {exc}')

        if args.bootstrap_creator:
            tag = normalize_tag(args.tag)
            email = args.email.strip().lower()
            if not tag_is_available(tag):
                print('Ошибка: тег уже занят')
                return 1
            create_platform_creator(args.name, email, tag, print_instructions=True)
            print('Создатель создан. Вход: /login?mode=creator — email + код из приложения или резервный код.')

        print('\nБаза очищена.')
        if not args.bootstrap_creator:
            print('  Вариант A: /register — первый аккаунт станет создателем (на экране — QR и backup-коды).')
            print('  Вариант B: повторите скрипт с --bootstrap-creator --name ... --email ... --tag ...')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
