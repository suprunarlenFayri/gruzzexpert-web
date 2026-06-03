#!/usr/bin/env python3
"""Одноразовое исправление названий workspaces в БД (UTF-8 / mojibake)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from utils.workspace_admin import fix_corrupted_workspace_names


def main():
    app = create_app()
    with app.app_context():
        changed = fix_corrupted_workspace_names(commit=True)
        if not changed:
            print('Нет названий для исправления.')
            return
        print(f'Исправлено записей: {len(changed)}')
        for item in changed:
            print(f"  #{item['id']}: {item['old']!r} -> {item['new']!r}")


if __name__ == '__main__':
    main()
