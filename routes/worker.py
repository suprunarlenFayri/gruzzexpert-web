from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, VerificationRequest, City
from datetime import datetime, timezone
from utils.datetime_utils import utc_now
from utils.crypto import encrypt_data

worker_bp = Blueprint('worker', __name__)


def _legal_consent_accepted(form):
    raw = form.get('is_legal_agreed')
    return raw in ('1', 'true', 'on', 'yes', True, 1)


def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or ''


@worker_bp.route('/become-worker', methods=['GET', 'POST'])
@login_required
def become_worker():
    existing = VerificationRequest.query.filter_by(
        user_id=current_user.id,
        status='pending',
    ).first()
    if existing:
        flash('Ваша анкета уже на модерации. Ожидайте проверки.')
        return redirect(url_for('profile.profile'))

    if request.method == 'POST':
        if not _legal_consent_accepted(request.form):
            flash('Необходимо дать согласие на обработку персональных данных и b2b-условия')
            return redirect(url_for('worker.become_worker'))

        full_name = request.form.get('full_name')
        birth_date_str = request.form.get('birth_date')
        city_id = request.form.get('city_id')
        experience = request.form.get('experience')
        comment = request.form.get('comment')

        if not full_name or not birth_date_str or not city_id:
            flash('Заполните все обязательные поля')
            return redirect(url_for('worker.become_worker'))

        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        today = datetime.now(timezone.utc).date()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        if age < 18:
            cities = City.query.order_by(City.name).all()
            flash('Регистрация доступна только с 18 лет', 'error')
            return render_template('worker/become_worker.html', cities=cities), 400

        passport_photo = request.files.get('passport_photo')
        selfie_photo = request.files.get('selfie_photo')

        if not passport_photo or not selfie_photo:
            flash('Загрузите фото паспорта и селфи')
            return redirect(url_for('worker.become_worker'))

        from utils.secure_media import save_encrypted_verification_upload

        passport_path = save_encrypted_verification_upload(passport_photo, current_app)
        selfie_path = save_encrypted_verification_upload(selfie_photo, current_app)

        if not passport_path or not selfie_path:
            flash('Ошибка при загрузке фото. Разрешены: png, jpg, jpeg, gif, webp')
            return redirect(url_for('worker.become_worker'))

        verification = VerificationRequest(
            user_id=current_user.id,
            workspace_id=current_user.workspace_id or 1,
            full_name=encrypt_data(full_name.strip()),
            birth_date=birth_date,
            phone=encrypt_data(current_user.phone),
            city_id=int(city_id),
            experience=encrypt_data(experience) if experience else None,
            comment=encrypt_data(comment) if comment else None,
            passport_photo=passport_path,
            selfie_photo=selfie_path,
            status='pending',
            is_legal_agreed=True,
            agreed_at=utc_now(),
            agreed_from_ip=_client_ip(),
        )
        db.session.add(verification)
        db.session.commit()

        from socketio_instance import emit_new_profile_moderation
        emit_new_profile_moderation(verification.city_id, verification.workspace_id)

        flash('Анкета отправлена на модерацию. После проверки вы получите доступ к заявкам.')
        return redirect(url_for('profile.profile'))

    cities = City.query.order_by(City.name).all()
    return render_template('worker/become_worker.html', cities=cities)
