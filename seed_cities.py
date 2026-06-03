#!/usr/bin/env python3
"""Заполнение справочника cities городами РФ (если ещё нет в БД)."""

import json
from pathlib import Path

from app import create_app
from models import City, db

DATA_FILE = Path(__file__).resolve().parent / 'data' / 'russian_cities.json'
REMOTE_URL = 'https://raw.githubusercontent.com/pensnarik/russian-cities/master/russian-cities.json'


def load_city_names():
    if DATA_FILE.exists():
        names = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        if isinstance(names, list) and names:
            return names

    import urllib.request

    raw = urllib.request.urlopen(REMOTE_URL, timeout=60).read().decode('utf-8')
    payload = json.loads(raw)
    names = sorted({item['name'].strip() for item in payload if item.get('name')})
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(names, ensure_ascii=False, indent=0), encoding='utf-8')
    return names


def seed_cities():
    names = load_city_names()
    app = create_app()
    with app.app_context():
        existing = {row[0] for row in db.session.query(City.name).all()}
        added = 0
        for name in names:
            name = (name or '').strip()
            if not name or name in existing:
                continue
            db.session.add(City(name=name))
            existing.add(name)
            added += 1
        db.session.commit()
        total = City.query.count()
        print(f'Готово: добавлено {added}, всего в БД {total} городов.')
        return added, total


if __name__ == '__main__':
    seed_cities()
