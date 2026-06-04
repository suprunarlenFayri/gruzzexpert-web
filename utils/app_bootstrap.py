"""Сид справочников и привязка создателя платформы при старте приложения."""
from __future__ import annotations

import logging
import os

from models import City, User, Workspace, WorkspaceMember, db
from utils.invite_utils import DEFAULT_WORKSPACE_ID, generate_invite_key

logger = logging.getLogger(__name__)

CREATOR_NAME = (os.getenv('CREATOR_NAME') or 'Арлен').strip()
FLAGSHIP_NAME = (os.getenv('FLAGSHIP_WORKSPACE_NAME') or 'GruzzExpert — флагман').strip()


def _dedupe_names(names):
    seen = set()
    out = []
    for raw in names:
        name = (raw or '').strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def seed_cities_if_empty() -> int:
    """Заполняет cities из City.get_defaults(), если таблица пуста."""
    try:
        if City.query.count() > 0:
            return 0
    except Exception as exc:
        logger.warning('seed_cities_if_empty: skip (%s)', exc)
        return 0

    names = _dedupe_names(City.get_defaults())
    priority = ['Новосибирск', 'Москва', 'Санкт-Петербург', 'Екатеринбург', 'Казань']
    ordered = _dedupe_names(priority + names)

    added = 0
    for name in ordered:
        if City.query.filter_by(name=name).first():
            continue
        db.session.add(City(name=name))
        added += 1

    if added:
        db.session.commit()
        logger.info('Bootstrap: добавлено %d городов, всего %d', added, City.query.count())
    return added


def _find_creator_user():
    if CREATOR_NAME:
        user = User.query.filter(User.name.ilike(CREATOR_NAME)).first()
        if user:
            return user
        user = User.query.filter(User.name.ilike(f'%{CREATOR_NAME}%')).first()
        if user:
            return user
    return User.query.filter_by(role='creator').order_by(User.id.asc()).first()


def _ensure_flagship_workspace(creator: User) -> Workspace | None:
    ws = Workspace.query.get(DEFAULT_WORKSPACE_ID)
    if ws:
        return ws

    ws = Workspace.query.order_by(Workspace.id.asc()).first()
    if ws:
        return ws

    ws = Workspace.query.filter(Workspace.name.ilike('%флагман%')).first()
    if ws:
        return ws

    ws = Workspace(
        name=FLAGSHIP_NAME,
        admin_limit=50,
        invite_key=generate_invite_key(),
        created_by_id=creator.id,
    )
    db.session.add(ws)
    db.session.flush()
    return ws


def _ensure_workspace_member(creator: User, workspace: Workspace) -> None:
    member = WorkspaceMember.query.filter_by(
        user_id=creator.id,
        workspace_id=workspace.id,
    ).first()
    if member:
        if member.role != 'creator':
            member.role = 'creator'
        return
    db.session.add(
        WorkspaceMember(
            user_id=creator.id,
            workspace_id=workspace.id,
            role='creator',
        )
    )


def ensure_platform_creator_setup() -> bool:
    """Роль creator/super_admin + workspace_id для создателя платформы."""
    try:
        user = _find_creator_user()
        if not user:
            logger.info('Bootstrap: создатель «%s» не найден — пропуск', CREATOR_NAME)
            return False

        workspace = _ensure_flagship_workspace(user)
        if not workspace:
            logger.warning('Bootstrap: не удалось создать workspace')
            return False

        changed = False
        if user.role != 'creator':
            user.role = 'creator'
            changed = True
        if (user.platform_role or '') != 'super_admin':
            user.platform_role = 'super_admin'
            changed = True
        if user.workspace_id != workspace.id:
            user.workspace_id = workspace.id
            changed = True

        _ensure_workspace_member(user, workspace)
        db.session.commit()

        if changed:
            logger.info(
                'Bootstrap: создатель id=%s привязан к workspace_id=%s (%s)',
                user.id,
                workspace.id,
                workspace.name,
            )
        return True
    except Exception as exc:
        db.session.rollback()
        logger.warning('ensure_platform_creator_setup failed: %s', exc, exc_info=True)
        return False


def run_startup_bootstrap() -> None:
    """Идемпотентная инициализация БД при старте воркера."""
    print('[bootstrap] run_startup_bootstrap: start', flush=True)
    try:
        added = seed_cities_if_empty()
        print(f'[bootstrap] cities seed: added={added}, total={City.query.count()}', flush=True)
        ok = ensure_platform_creator_setup()
        print(f'[bootstrap] creator setup: ok={ok}', flush=True)
    except Exception as exc:
        print(f'[bootstrap] run_startup_bootstrap failed: {exc}', flush=True)
        logger.warning('run_startup_bootstrap failed: %s', exc, exc_info=True)
    print('[bootstrap] run_startup_bootstrap: done', flush=True)
