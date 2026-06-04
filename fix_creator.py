#!/usr/bin/env python3
"""
Сид городов + привязка создателя платформы к флагманскому Workspace.

Запуск на Render Shell:
  python fix_creator.py
  CREATOR_NAME="Арлен" python fix_creator.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault('SKIP_BACKGROUND_WORKERS', '1')

from app import create_app
from models import City, db
from utils.app_bootstrap import ensure_platform_creator_setup, seed_cities_if_empty


def main():
    app = create_app()
    with app.app_context():
        added = seed_cities_if_empty()
        total = City.query.count()
        print(f'[cities] добавлено {added}, всего в БД: {total}')
        ok = ensure_platform_creator_setup()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
