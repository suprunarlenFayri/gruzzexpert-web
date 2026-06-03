"""API контактов и чёрного списка."""

from flask import Blueprint, jsonify, request, url_for
from flask_login import current_user, login_required

from models import db
from utils.media_urls import avatar_url_for
from utils.social import (
    add_contact,
    is_blocked,
    is_contact,
    list_contacts,
    remove_contact,
    toggle_blacklist,
)

social_bp = Blueprint('social', __name__)


def _user_brief(user):
    return {
        'id': user.id,
        'name': user.name,
        'tag': user.tag,
        'username': getattr(user, 'username', None),
        'role': user.role,
        'avatar_url': avatar_url_for(user, lambda p: url_for('uploaded_file', filename=p)),
        'chat_url': f'/chat/create/private/{user.id}',
    }


@social_bp.route('/api/contacts/add', methods=['POST'])
@login_required
def contacts_add():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Укажите user_id'}), 400

    try:
        _, created = add_contact(current_user, user_id)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400

    return jsonify({
        'ok': True,
        'created': created,
        'is_contact': True,
        'message': 'Добавлено в контакты' if created else 'Уже в контактах',
    })


@social_bp.route('/api/contacts/remove', methods=['POST'])
@login_required
def contacts_remove():
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get('user_id'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Укажите user_id'}), 400

    removed = remove_contact(current_user, user_id)
    db.session.commit()
    return jsonify({'ok': True, 'removed': removed, 'is_contact': False})


@social_bp.route('/api/contacts', methods=['GET'])
@login_required
def contacts_list():
    users = list_contacts(current_user.id)
    return jsonify({
        'ok': True,
        'contacts': [_user_brief(u) for u in users],
    })


@social_bp.route('/api/blacklist', methods=['POST'])
@login_required
def blacklist_toggle():
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get('user_id'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Укажите user_id'}), 400

    action = (data.get('action') or 'add').strip().lower()
    block = action in ('add', 'block', 'true', '1')

    try:
        toggle_blacklist(current_user, user_id, block=block)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400

    return jsonify({
        'ok': True,
        'is_blocked': is_blocked(current_user.id, user_id),
        'is_contact': is_contact(current_user.id, user_id),
        'message': 'Пользователь заблокирован' if block else 'Пользователь разблокирован',
    })


@social_bp.route('/api/users/<int:user_id>/relation', methods=['GET'])
@login_required
def user_relation(user_id):
    return jsonify({
        'ok': True,
        'is_contact': is_contact(current_user.id, user_id),
        'is_blocked': is_blocked(current_user.id, user_id),
        'is_blocked_by': is_blocked(user_id, current_user.id),
    })
