from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from models import db
from utils.security_freeze import is_balance_frozen
from utils.user_settings import (
    clear_expired_task_mute,
    get_user_settings,
    is_user_tasks_muted,
    is_worker_role,
    set_user_setting,
    tasks_muted_until_iso,
)

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
@login_required
def settings_page():
    clear_expired_task_mute(current_user)
    db.session.commit()
    return render_template(
        'settings.html',
        settings=get_user_settings(current_user),
        is_worker=is_worker_role(current_user),
        tasks_muted_active=is_user_tasks_muted(current_user),
        tasks_muted_until=tasks_muted_until_iso(current_user),
        is_balance_frozen=is_balance_frozen(current_user),
        frozen_until=current_user.frozen_until,
        active_tab='settings',
    )


@settings_bp.route('/api/save-settings', methods=['POST'])
@login_required
def save_settings():
    data = request.get_json(silent=True) or {}
    key = data.get('key')
    value = data.get('value')

    if not key:
        return jsonify({'ok': False, 'error': 'Не указан ключ настройки'}), 400

    try:
        clear_expired_task_mute(current_user)
        updated, tasks_muted_until = set_user_setting(current_user, key, value)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'ok': False, 'error': 'Ошибка сохранения'}), 500

    return jsonify({
        'ok': True,
        'settings': updated,
        'tasks_muted_until': tasks_muted_until or tasks_muted_until_iso(current_user),
        'tasks_muted_active': is_user_tasks_muted(current_user),
    })


@settings_bp.route('/api/settings')
@login_required
def get_settings_api():
    clear_expired_task_mute(current_user)
    db.session.commit()
    return jsonify({
        'ok': True,
        'settings': get_user_settings(current_user),
        'tasks_muted_until': tasks_muted_until_iso(current_user),
        'tasks_muted_active': is_user_tasks_muted(current_user),
        'is_worker': is_worker_role(current_user),
    })
