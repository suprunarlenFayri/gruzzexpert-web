import uuid

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, Workspace
from utils.invite_utils import DEFAULT_WORKSPACE_ID, workspace_has_director
from utils.tags import normalize_tag, tag_is_available
from utils.creator_totp import (
    authenticate_creator,
    creator_email_requires_totp,
    create_platform_creator,
    is_creator_account,
)
from utils.sms_verification import (
    consume_verified_session,
    create_sms_verification,
    verify_sms_code,
)
from utils.device_security import (
    generate_mock_2fa_codes,
    needs_device_2fa,
    normalize_2fa_code,
    notify_login_attempt,
    parse_client_info,
    register_trusted_device,
    resolve_device_hash,
)

auth_bp = Blueprint('auth', __name__)


def get_device_type(user_agent_string):
    ua = user_agent_string.lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'mobile'
    return 'desktop'


def _establish_device_session(user):
    device_type = get_device_type(request.headers.get('User-Agent', ''))
    token = uuid.uuid4().hex
    if device_type == 'mobile':
        user.current_mobile_token = token
    else:
        user.current_desktop_token = token
    db.session.commit()
    session['session_token'] = token
    session['device_type'] = device_type


def _wants_json_response():
    if request.is_json:
        return True
    accept = request.headers.get('Accept', '')
    if 'application/json' in accept:
        return True
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _complete_login(user, device_hash, device_info):
    login_user(user)
    register_trusted_device(user, device_hash, device_info)
    _establish_device_session(user)
    from utils.user_login_sessions import register_user_session

    register_user_session(user, session.get('session_token'), device_info)
    db.session.commit()
    session.pop('login_2fa_pending', None)


def _start_login_2fa(user, device_hash, device_info):
    from utils.login_attempts import create_login_attempt

    codes = generate_mock_2fa_codes()
    attempt = create_login_attempt(
        user,
        device_hash,
        device_info,
        codes['sms_code'],
        codes['email_code'],
    )
    session['login_attempt_token'] = attempt.attempt_token
    session['login_2fa_pending'] = {
        'user_id': user.id,
        'device_hash': device_hash,
        'device_info': device_info,
        'attempt_token': attempt.attempt_token,
    }
    notify_login_attempt(user, device_info, attempt_token=attempt.attempt_token)
    return codes


def _resolve_registration_workspace_and_role(invite_key_raw):
    invite_key = (invite_key_raw or '').strip()

    if invite_key:
        workspace = Workspace.query.filter_by(invite_key=invite_key).first()
        if not workspace:
            return None, None, 'Неверный ключ приглашения директора'
        if workspace_has_director(workspace.id):
            return None, None, 'Этот ключ уже использован'
        return workspace.id, 'director', None

    invite_workspace_id = session.pop('invite_workspace_id', None)
    if invite_workspace_id:
        workspace = Workspace.query.get(invite_workspace_id)
        if not workspace:
            return None, None, 'Ссылка приглашения недействительна'
        return workspace.id, 'user', None

    return DEFAULT_WORKSPACE_ID, 'user', None


def _platform_is_empty():
    return User.query.count() == 0


def _register_platform_creator(name, email, tag):
    if not tag_is_available(tag):
        return None, 'Этот тег уже занят, придумайте другой', None
    if User.query.filter_by(email=email).first():
        return None, 'Email уже зарегистрирован', None

    user, secret, uri, qr_url, backup_plain = create_platform_creator(
        name, email, tag, print_instructions=False
    )
    setup_payload = {
        'secret': secret,
        'provisioning_uri': uri,
        'qr_url': qr_url,
        'backup_codes': backup_plain,
        'email': email,
    }
    return user, None, setup_payload


@auth_bp.route('/join/<string:token>')
def join_via_share_token(token):
    workspace = Workspace.query.filter_by(share_token=token).first()
    if not workspace:
        flash('Ссылка приглашения недействительна или устарела')
        return redirect(url_for('auth.register'))

    session['invite_workspace_id'] = workspace.id
    flash(f'Регистрация в компании «{workspace.name}»')
    return redirect(url_for('auth.register'))


@auth_bp.route('/api/users/check-tag')
def check_tag():
    tag = normalize_tag(request.args.get('tag'))
    if not tag:
        return jsonify({'available': False, 'error': 'invalid', 'tag': None}), 400
    exclude_id = request.args.get('exclude', type=int)
    available = tag_is_available(tag, exclude_user_id=exclude_id)
    return jsonify({'available': available, 'tag': tag, 'taken': not available})


@auth_bp.route('/api/auth/sms/send', methods=['POST'])
def sms_send():
    data = request.get_json(silent=True) or request.form
    phone = data.get('phone')
    purpose = data.get('purpose', 'login')
    session_token, err = create_sms_verification(phone, purpose)
    if err:
        return jsonify({'ok': False, 'error': err}), 400
    return jsonify({'ok': True, 'sms_session': session_token})


@auth_bp.route('/api/auth/sms/verify', methods=['POST'])
def sms_verify():
    data = request.get_json(silent=True) or request.form
    ok, err = verify_sms_code(
        data.get('sms_session') or '',
        data.get('code') or data.get('sms_code') or '',
        phone=data.get('phone'),
    )
    if not ok:
        return jsonify({'ok': False, 'error': err}), 403
    return jsonify({'ok': True, 'sms_session': data.get('sms_session')})


@auth_bp.route('/api/auth/creator-login-check')
def creator_login_check():
    email = (request.args.get('email') or '').strip().lower()
    if not email:
        return jsonify({'creator': False, 'totp_required': False})
    return jsonify({
        'creator': creator_email_requires_totp(email),
        'totp_required': creator_email_requires_totp(email),
    })


@auth_bp.route('/register/creator-totp-setup')
def creator_totp_setup():
    payload = session.pop('creator_totp_setup', None)
    if not payload:
        return redirect(url_for('auth.login', mode='creator'))
    return render_template(
        'creator_totp_setup.html',
        secret=payload.get('secret'),
        qr_url=payload.get('qr_url'),
        backup_codes=payload.get('backup_codes') or [],
    )


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    is_bootstrap = _platform_is_empty()

    invited_workspace = None
    invite_workspace_id = session.get('invite_workspace_id')
    if invite_workspace_id and not is_bootstrap:
        invited_workspace = Workspace.query.get(invite_workspace_id)

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        tag = normalize_tag(request.form.get('tag'))

        if is_bootstrap or _platform_is_empty():
            if not name or not email or not tag:
                flash('Укажите имя, уникальный тег и email')
                return redirect(url_for('auth.register'))
            user, err, totp_setup = _register_platform_creator(name, email, tag)
            if err:
                flash(err)
                return redirect(url_for('auth.register'))
            session['creator_totp_setup'] = totp_setup
            return redirect(url_for('auth.creator_totp_setup'))

        phone = request.form.get('phone')
        password = request.form.get('password')
        invite_key = request.form.get('invite_key')

        if not tag:
            flash('Укажите уникальный тег')
            return redirect(url_for('auth.register'))

        if not tag_is_available(tag):
            flash('Этот тег уже занят, придумайте другой')
            return redirect(url_for('auth.register'))

        if not email:
            email = None
        elif User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(phone=phone).first():
            flash('Телефон уже зарегистрирован')
            return redirect(url_for('auth.register'))

        workspace_id, role, reg_error = _resolve_registration_workspace_and_role(invite_key)
        if reg_error:
            flash(reg_error)
            return redirect(url_for('auth.register'))

        user = User(
            name=name,
            phone=phone,
            email=email,
            tag=tag,
            role=role,
            workspace_id=workspace_id,
            created_by_id=None,
        )
        user.set_password(password)

        if invite_key and role == 'director':
            workspace = Workspace.query.get(workspace_id)
            if workspace:
                workspace.invite_key = None

        db.session.add(user)
        db.session.commit()

        session.pop('invite_workspace_id', None)

        device_hash = resolve_device_hash(request)
        device_info = parse_client_info(request)
        _complete_login(user, device_hash, device_info)
        return redirect(url_for('tasks.tasks_list'))

    return render_template(
        'register.html',
        invited_workspace=invited_workspace,
        is_platform_bootstrap=is_bootstrap,
    )


def _creator_login():
    email = (request.form.get('email') or '').strip().lower()
    totp_code = request.form.get('totp_code') or request.form.get('authenticator_code') or ''
    backup_code = request.form.get('backup_code') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not is_creator_account(user):
        msg = 'Неверный email создателя'
        if _wants_json_response():
            return jsonify({'ok': False, 'error': msg}), 401
        flash(msg)
        return redirect(url_for('auth.login', mode='creator'))

    ok, err = authenticate_creator(user, totp_code=totp_code, backup_code=backup_code)
    if not ok:
        msg = err or 'Ошибка аутентификации'
        if _wants_json_response():
            return jsonify({'ok': False, 'error': msg}), 401
        flash(msg)
        return redirect(url_for('auth.login', mode='creator'))

    device_hash = resolve_device_hash(request)
    device_info = parse_client_info(request)
    _complete_login(user, device_hash, device_info)
    if _wants_json_response():
        return jsonify({'ok': True, 'redirect': url_for('tasks.tasks_list')})
    return redirect(url_for('tasks.tasks_list'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    step = request.args.get('step') or request.form.get('step')
    creator_mode = (
        request.args.get('mode') == 'creator'
        or request.form.get('login_mode') == 'creator'
    )

    if request.method == 'POST' and step != '2fa' and creator_mode:
        return _creator_login()

    if request.method == 'POST' and step == 'sms':
        pending = session.get('login_sms_pending') or {}
        phone = pending.get('phone') or request.form.get('phone')
        sms_session = request.form.get('sms_session') or pending.get('sms_session')
        sms_code = request.form.get('sms_code') or ''
        user = User.query.filter_by(phone=phone).first()
        if not user:
            flash('Сессия истекла. Войдите снова.')
            return redirect(url_for('auth.login'))
        ok, err = verify_sms_code(sms_session, sms_code, phone=phone)
        if not ok:
            flash(err or 'Неверный код')
            return redirect(url_for('auth.login', step='sms'))
        if not consume_verified_session(sms_session, phone, 'login'):
            flash('Подтвердите код из SMS')
            return redirect(url_for('auth.login', step='sms'))
        device_hash = pending.get('device_hash') or resolve_device_hash(request)
        device_info = pending.get('device_info') or parse_client_info(request)
        session.pop('login_sms_pending', None)
        if needs_device_2fa(user, device_hash):
            codes = _start_login_2fa(user, device_hash, device_info)
            flash('Обнаружен вход с нового устройства. Подтвердите коды 2FA.')
            return redirect(url_for('auth.login', step='2fa'))
        _complete_login(user, device_hash, device_info)
        return redirect(url_for('tasks.tasks_list'))

    if request.method == 'POST' and step != '2fa':
        phone = request.form.get('phone')
        password = request.form.get('password')

        user = User.query.filter_by(phone=phone).first()

        if user and user.check_password(password):
            if is_creator_account(user):
                flash('Для создателя используйте вход по email')
                return redirect(url_for('auth.login', mode='creator'))

            device_hash = resolve_device_hash(request)
            device_info = parse_client_info(request)

            sms_session, sms_err = create_sms_verification(phone, 'login')
            if sms_err:
                flash(sms_err)
                return redirect(url_for('auth.login'))
            session['login_sms_pending'] = {
                'phone': phone,
                'sms_session': sms_session,
                'device_hash': device_hash,
                'device_info': device_info,
            }
            flash('Введите код из SMS')
            return redirect(url_for('auth.login', step='sms'))

        if _wants_json_response():
            return jsonify({'ok': False, 'error': 'Неверный телефон или пароль'}), 401
        flash('Неверный телефон или пароль')

    pending = session.get('login_2fa_pending')
    sms_pending = session.get('login_sms_pending')
    show_2fa = step == '2fa' and pending
    show_sms = step == 'sms' and sms_pending
    mock_codes = None
    if show_2fa and pending:
        from utils.login_attempts import get_attempt_by_token
        attempt = get_attempt_by_token(pending.get('attempt_token'))
        if attempt:
            mock_codes = {
                'sms': attempt.sms_code,
                'email': attempt.email_code,
            }

    return render_template(
        'login.html',
        show_2fa=show_2fa,
        show_sms=show_sms,
        sms_pending=sms_pending,
        mock_codes=mock_codes,
        creator_mode=creator_mode,
    )


@auth_bp.route('/login/verify-2fa', methods=['POST'])
def verify_login_2fa():
    pending = session.get('login_2fa_pending')
    if not pending:
        if _wants_json_response():
            return jsonify({'ok': False, 'error': 'Сессия 2FA истекла'}), 400
        flash('Сессия подтверждения истекла. Войдите снова.')
        return redirect(url_for('auth.login'))

    from utils.login_attempts import complete_attempt, get_attempt_by_token

    attempt_token = pending.get('attempt_token') or session.get('login_attempt_token')
    attempt = get_attempt_by_token(attempt_token)
    if not attempt or attempt.status == 'blocked':
        session.pop('login_2fa_pending', None)
        session.pop('login_attempt_token', None)
        if _wants_json_response():
            return jsonify({'ok': False, 'error': 'Попытка входа заблокирована'}), 403
        flash('Попытка входа была заблокирована с другого устройства.')
        return redirect(url_for('auth.login'))

    payload = request.get_json(silent=True) or {}
    sms_code = normalize_2fa_code(payload.get('sms_code') or request.form.get('sms_code'))
    email_code = normalize_2fa_code(payload.get('email_code') or request.form.get('email_code'))

    expected_sms = normalize_2fa_code(attempt.sms_code)
    expected_email = normalize_2fa_code(attempt.email_code)

    if sms_code != expected_sms or email_code != expected_email:
        if _wants_json_response():
            return jsonify({'ok': False, 'error': 'Неверные коды подтверждения'}), 403
        flash('Неверные коды подтверждения')
        return redirect(url_for('auth.login', step='2fa'))

    user = User.query.get(pending.get('user_id'))
    if not user:
        session.pop('login_2fa_pending', None)
        if _wants_json_response():
            return jsonify({'ok': False, 'error': 'Пользователь не найден'}), 404
        flash('Пользователь не найден')
        return redirect(url_for('auth.login'))

    _complete_login(
        user,
        pending.get('device_hash'),
        pending.get('device_info') or {},
    )
    complete_attempt(attempt)
    session.pop('login_attempt_token', None)

    if _wants_json_response():
        return jsonify({'ok': True, 'redirect': url_for('tasks.tasks_list')})
    return redirect(url_for('tasks.tasks_list'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))
