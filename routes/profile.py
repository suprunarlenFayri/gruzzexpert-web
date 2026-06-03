from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required, current_user
from models import db, User
from utils.security_freeze import apply_security_freeze
from utils.crypto import encrypt_data, decrypt_data
from utils.media_urls import avatar_url_for
from utils.user_profiles import (
    can_view_user_profile,
    can_view_worker_card,
    is_worker_profile,
    serialize_messenger_profile,
    serialize_worker_card,
)
from utils.tags import normalize_tag as _normalize_tag, tag_is_available
import os
from werkzeug.utils import secure_filename

profile_bp = Blueprint('profile', __name__)

UPLOAD_FOLDER = 'static/uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _tag_is_taken(tag, user_id):
    return not tag_is_available(tag, exclude_user_id=user_id)


@profile_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', active_tab='profile')


@profile_bp.route('/profile/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return redirect(request.referrer)

    file = request.files['avatar']
    if file and file.filename != '':
        filename = User.generate_uuid_filename(file.filename)
        upload_path = os.path.join(current_app.root_path, 'uploads', 'avatars')
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, filename))
        current_user.avatar = f"avatars/{filename}"
        db.session.commit()
        flash('Аватар обновлён')
    else:
        flash('Файл не выбран')

    return redirect(url_for('profile.profile'))


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update():
    name = request.form.get('name')
    tag = _normalize_tag(request.form.get('tag'))

    if name:
        current_user.name = name.strip()

    email = (request.form.get('email') or '').strip()
    new_email = email or None
    if new_email != (current_user.email or None):
        current_user.email = new_email
        apply_security_freeze(current_user, 'email')

    if is_worker_profile(current_user):
        bank_card = (request.form.get('bank_card') or '').strip() or None
        current_plain = decrypt_data(current_user.bank_card) if current_user.bank_card else None
        if bank_card != current_plain:
            current_user.bank_card = encrypt_data(bank_card) if bank_card else None
            apply_security_freeze(current_user, 'bank_card')

    if tag:
        if _tag_is_taken(tag, current_user.id):
            flash('Этот тег уже занят')
            return redirect(url_for('profile.profile'))
        current_user.tag = tag
    else:
        current_user.tag = None

    db.session.commit()
    flash('Профиль обновлён')
    return redirect(url_for('profile.profile'))


@profile_bp.route('/profile/rate/<int:user_id>', methods=['POST'])
@login_required
def rate(user_id):
    if current_user.id == user_id:
        flash('Нельзя оценить себя')
        return redirect(request.referrer or url_for('profile.profile'))

    user = User.query.get_or_404(user_id)
    score = int(request.form.get('score', 0))

    if score < 1 or score > 5:
        flash('Оценка должна быть от 1 до 5')
        return redirect(request.referrer or url_for('profile.profile'))

    flash(f'Вы оценили {user.name} на {score} ⭐')
    return redirect(request.referrer or url_for('profile.profile'))


def _avatar_url(user):
    return avatar_url_for(user, lambda p: url_for('uploaded_file', filename=p))


@profile_bp.route('/api/users/<int:user_id>/profile')
@login_required
def user_profile_api(user_id):
    user = User.query.get_or_404(user_id)
    context = (request.args.get('context') or 'messenger').strip().lower()
    if context not in ('messenger', 'worker'):
        context = 'messenger'

    if context == 'worker':
        if not can_view_worker_card(current_user, user):
            return jsonify({'error': 'Нет доступа к рабочей карточке'}), 403
        payload = serialize_worker_card(user, current_user, _avatar_url)
    else:
        if not can_view_user_profile(current_user, user):
            return jsonify({'error': 'Нет доступа'}), 403
        payload = serialize_messenger_profile(user, current_user, _avatar_url)
        from utils.social import is_blocked, is_contact

        payload['is_self'] = current_user.id == user.id
        payload['is_contact'] = is_contact(current_user.id, user.id)
        payload['is_blocked'] = is_blocked(current_user.id, user.id)
        payload['is_blocked_by'] = is_blocked(user.id, current_user.id)

    payload['ok'] = True
    return jsonify(payload)


@profile_bp.route('/profile/update-bank-card', methods=['POST'])
@login_required
def update_bank_card():
    if not is_worker_profile(current_user):
        return jsonify({'error': 'Доступно только исполнителям'}), 403

    data = request.get_json(silent=True) or {}
    bank_card = (data.get('bank_card') if data else None) or request.form.get('bank_card') or ''
    bank_card = bank_card.strip() or None
    current_plain = decrypt_data(current_user.bank_card) if current_user.bank_card else None
    if bank_card != current_plain:
        current_user.bank_card = encrypt_data(bank_card) if bank_card else None
        apply_security_freeze(current_user, 'bank_card')
    else:
        current_user.bank_card = encrypt_data(bank_card) if bank_card else None
    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'bank_card': decrypt_data(current_user.bank_card) or ''})

    flash('Номер карты сохранён')
    return redirect(url_for('profile.profile'))
