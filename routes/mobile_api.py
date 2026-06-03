"""REST API для нативного Flutter-клиента."""
from flask import Blueprint, jsonify, request
from flask_login import login_user
from models import Task, TaskAssignment, User, UserFcmToken, db
from utils.mobile_feed import serialize_chat_summary
from utils.datetime_utils import format_local_datetime, utc_now
from utils.creator_totp import authenticate_creator, creator_email_requires_totp, is_creator_account
from utils.device_security import (
    needs_device_2fa,
    parse_client_info,
    register_trusted_device,
    resolve_device_hash,
)
from utils.invite_utils import DEFAULT_WORKSPACE_ID
from utils.mobile_auth import (
    issue_mobile_token,
    mobile_auth_required,
    user_mobile_json,
)
from utils.sms import normalize_phone
from utils.sms_verification import (
    consume_verified_session,
    create_sms_verification,
    verify_sms_code,
)
from utils.tags import normalize_tag, tag_is_available

mobile_api_bp = Blueprint('mobile_api', __name__, url_prefix='/api/mobile')


def _json_error(message, status=400):
    return jsonify({'ok': False, 'error': message}), status


def _phone_from_payload(data) -> str | None:
    phone = data.get('phone')
    if not isinstance(phone, str):
        return None
    phone = phone.strip()
    return phone or None


@mobile_api_bp.route('/auth/sms/send', methods=['POST'])
def sms_send():
    data = request.get_json(silent=True) or {}
    phone = _phone_from_payload(data)
    if not phone:
        return _json_error('Укажите телефон')
    purpose = data.get('purpose', 'login')
    session_token, err = create_sms_verification(phone, purpose)
    if err:
        return _json_error(err, 400)
    return jsonify({
        'ok': True,
        'sms_session': session_token,
        'message': 'Код отправлен по SMS',
    })


@mobile_api_bp.route('/auth/sms/verify', methods=['POST'])
def sms_verify():
    data = request.get_json(silent=True) or {}
    session_token = (data.get('sms_session') or '').strip()
    code = data.get('code') or ''
    phone = data.get('phone')
    ok, err = verify_sms_code(session_token, code, phone=phone)
    if not ok:
        return _json_error(err or 'Неверный код', 403)
    return jsonify({'ok': True, 'sms_session': session_token})


@mobile_api_bp.route('/auth/login', methods=['POST'])
def mobile_login():
    data = request.get_json(silent=True) or {}
    phone = _phone_from_payload(data)
    password = data.get('password')
    sms_session = (data.get('sms_session') or '').strip()
    sms_code = data.get('sms_code') or ''

    if not phone:
        return _json_error('Укажите телефон', 401)

    user = User.query.filter_by(phone=phone).first()
    if not user or not user.check_password(password):
        return _json_error('Неверный телефон или пароль', 401)

    if is_creator_account(user):
        return _json_error('Для создателя используйте вход по email и TOTP', 400)

    if not sms_session:
        token, err = create_sms_verification(phone, 'login')
        if err:
            return _json_error(err, 400)
        return jsonify({
            'ok': False,
            'require_sms': True,
            'sms_session': token,
            'message': 'Введите код из SMS',
        }), 403

    ok, err = verify_sms_code(sms_session, sms_code, phone=phone)
    if not ok:
        return _json_error(err or 'Неверный код', 403)

    if not consume_verified_session(sms_session, phone, 'login'):
        return _json_error('Подтвердите SMS-код', 403)

    device_hash = resolve_device_hash(request)
    device_info = parse_client_info(request)
    if needs_device_2fa(user, device_hash):
        return jsonify({
            'ok': False,
            'require_device_2fa': True,
            'message': 'Новое устройство — подтвердите вход в веб-версии',
        }), 403

    register_trusted_device(user, device_hash, device_info)
    token = issue_mobile_token(user)
    login_user(user)
    base_url = request.url_root.rstrip('/')
    return jsonify({
        'ok': True,
        'token': token,
        'user': user_mobile_json(user, base_url=base_url),
    })


@mobile_api_bp.route('/auth/creator-login', methods=['POST'])
def mobile_creator_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    totp_code = data.get('totp_code') or data.get('code') or ''
    backup_code = data.get('backup_code') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not is_creator_account(user):
        return _json_error('Неверный email создателя', 401)

    ok, err = authenticate_creator(user, totp_code=totp_code, backup_code=backup_code)
    if not ok:
        return _json_error(err or 'Ошибка TOTP', 401)

    token = issue_mobile_token(user)
    login_user(user)
    base_url = request.url_root.rstrip('/')
    return jsonify({
        'ok': True,
        'token': token,
        'user': user_mobile_json(user, base_url=base_url),
    })


@mobile_api_bp.route('/auth/creator-check', methods=['GET'])
def mobile_creator_check():
    email = (request.args.get('email') or '').strip().lower()
    return jsonify({
        'creator': creator_email_requires_totp(email),
        'totp_required': creator_email_requires_totp(email),
    })


@mobile_api_bp.route('/auth/register', methods=['POST'])
def mobile_register():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    phone = _phone_from_payload(data)
    password = data.get('password')
    tag = normalize_tag(data.get('tag'))
    sms_session = (data.get('sms_session') or '').strip()
    sms_code = data.get('sms_code') or ''

    if not name or not phone or not password or not tag:
        return _json_error('Заполните имя, телефон, пароль и тег')

    if not tag_is_available(tag):
        return _json_error('Этот тег уже занят')

    if User.query.filter_by(phone=phone).first():
        return _json_error('Телефон уже зарегистрирован')

    if not sms_session:
        token, err = create_sms_verification(phone, 'register')
        if err:
            return _json_error(err, 400)
        return jsonify({
            'ok': False,
            'require_sms': True,
            'sms_session': token,
        }), 403

    ok, err = verify_sms_code(sms_session, sms_code, phone=phone)
    if not ok:
        return _json_error(err or 'Неверный код', 403)
    if not consume_verified_session(sms_session, phone, 'register'):
        return _json_error('Подтвердите SMS', 403)

    user = User()
    user.name = name
    user.phone = normalize_phone(phone)
    user.tag = tag
    user.role = 'user'
    user.workspace_id = DEFAULT_WORKSPACE_ID
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = issue_mobile_token(user)
    login_user(user)
    base_url = request.url_root.rstrip('/')
    return jsonify({
        'ok': True,
        'token': token,
        'user': user_mobile_json(user, base_url=base_url),
    })


@mobile_api_bp.route('/fcm/register', methods=['POST'])
@mobile_auth_required
def fcm_register(user):
    data = request.get_json(silent=True) or {}
    fcm_token = (data.get('token') or data.get('fcm_token') or '').strip()
    if not fcm_token:
        return _json_error('token required')

    platform = (data.get('platform') or 'android').strip().lower()
    device_name = (data.get('device_name') or '')[:120] or None

    row = UserFcmToken.query.filter_by(token=fcm_token).first()
    if row and row.user_id != user.id:
        db.session.delete(row)
        db.session.flush()

    if not row:
        row = UserFcmToken()
        row.user_id = user.id
        row.token = fcm_token
        db.session.add(row)

    row.user_id = user.id
    row.platform = platform
    row.device_name = device_name
    db.session.commit()

    return jsonify({'ok': True})


@mobile_api_bp.route('/me', methods=['GET'])
@mobile_auth_required
def mobile_me(user):
    base_url = request.url_root.rstrip('/')
    return jsonify({'ok': True, 'user': user_mobile_json(user, base_url=base_url)})


@mobile_api_bp.route('/chats', methods=['GET'])
@mobile_auth_required
def mobile_chats_list(user):
    from routes.chats import _get_user_chats

    chats = _get_user_chats(user.id)
    return jsonify({
        'ok': True,
        'chats': [serialize_chat_summary(c, user) for c in chats],
    })


@mobile_api_bp.route('/chats/<int:chat_id>/messages', methods=['GET'])
@mobile_auth_required
def mobile_chat_messages(user, chat_id):
    from routes.chats import (
        CHAT_HISTORY_LIMIT,
        _hidden_message_ids,
        _message_query_options,
        _serialize_chat_message,
    )
    from models import Chat, ChatParticipant, Message

    chat = Chat.query.get_or_404(chat_id)
    participant = ChatParticipant.query.filter_by(
        chat_id=chat_id, user_id=user.id
    ).first()
    if not participant:
        return _json_error('Нет доступа к чату', 403)

    before_id = request.args.get('before_id', type=int)
    limit = request.args.get('limit', CHAT_HISTORY_LIMIT, type=int)
    limit = max(1, min(limit, 50))

    query = Message.query.filter_by(chat_id=chat_id).options(*_message_query_options())
    if before_id:
        anchor = Message.query.filter_by(id=before_id, chat_id=chat_id).first()
        if not anchor:
            return _json_error('Сообщение не найдено', 404)
        query = query.filter(Message.created_at < anchor.created_at)

    batch = query.order_by(Message.created_at.desc()).limit(limit).all()
    batch = list(reversed(batch))
    hidden_ids = _hidden_message_ids(user.id)
    messages = [
        payload
        for m in batch
        if (payload := _serialize_chat_message(m, user.id, hidden_ids=hidden_ids))
    ]

    participant.last_read_at = utc_now()
    db.session.commit()

    return jsonify({
        'ok': True,
        'chat_id': chat_id,
        'messages': messages,
        'has_more': len(batch) >= limit,
    })


@mobile_api_bp.route('/chats/<int:chat_id>/send', methods=['POST'])
@mobile_auth_required
def mobile_chat_send(user, chat_id):
    from services.chat_service import ChatService
    from models import ChatParticipant

    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return _json_error('Пустое сообщение')

    participant = ChatParticipant.query.filter_by(
        chat_id=chat_id, user_id=user.id
    ).first()
    if not participant:
        return _json_error('Нет доступа', 403)

    message_dict = ChatService.send_message(
        chat_id=chat_id,
        sender_id=user.id,
        text=text,
        attachments=[],
        parent_id=data.get('parent_id'),
    )
    if not message_dict:
        return _json_error('Не удалось отправить', 500)

    return jsonify({'ok': True, 'message': message_dict})


@mobile_api_bp.route('/tasks', methods=['GET'])
@mobile_auth_required
def mobile_tasks_list(user):
    from routes.tasks import _active_tasks_filter, _scope_tasks, _task_query
    from utils.mobile_feed import serialize_task_card, worker_task_scope_filter

    allowed_roles = ['worker', 'dispatcher', 'senior_dispatcher', 'director', 'creator']
    if user.role not in allowed_roles:
        return jsonify({'ok': True, 'tasks': [], 'my_tasks': []})

    assigned_ids = [
        a.task_id
        for a in TaskAssignment.query.filter_by(user_id=user.id, status='assigned').all()
    ]

    query = _scope_tasks(_active_tasks_filter(_task_query()))
    if assigned_ids:
        query = query.filter(~Task.id.in_(assigned_ids))
    query = worker_task_scope_filter(query, user)
    pool = query.order_by(Task.created_at.desc()).limit(80).all()

    my_query = _scope_tasks(_active_tasks_filter(_task_query())).filter(
        Task.assignments.any(user_id=user.id, status='assigned'),
    )
    my_tasks = my_query.order_by(Task.created_at.desc()).all()

    return jsonify({
        'ok': True,
        'tasks': [serialize_task_card(t) for t in pool],
        'my_tasks': [serialize_task_card(t) for t in my_tasks],
    })


@mobile_api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@mobile_auth_required
def mobile_task_detail(user, task_id):
    from routes.tasks import (
        _can_worker_reject_assignment,
        _get_scoped_task_or_404,
        _is_task_manager,
        _sync_task_confirmation_status,
        _task_start_datetime,
        _user_tracking_payload,
        _worker_tracking_payload,
    )

    task = _get_scoped_task_or_404(task_id)
    user_assignment = TaskAssignment.query.filter_by(
        task_id=task.id, user_id=user.id, status='assigned'
    ).first()
    is_verified_worker = (
        user.role == 'worker'
        and getattr(user, 'is_verified', False)
        and user_assignment is not None
    )
    is_manager = _is_task_manager(task)
    _sync_task_confirmation_status(task, commit=True)

    can_reject = False
    reject_reason = None
    if is_verified_worker and user_assignment:
        can_reject, reject_reason = _can_worker_reject_assignment(task, user_assignment)
        if can_reject:
            reject_reason = None

    workers = []
    if is_manager:
        for assignment in task.assignments:
            if assignment.status == 'assigned':
                workers.append(_worker_tracking_payload(assignment))

    start_dt = _task_start_datetime(task)
    from utils.mobile_feed import serialize_task_card

    payload = serialize_task_card(task)
    payload.update({
        'created_at': format_local_datetime(task.created_at),
        'task_start_iso': start_dt.isoformat(),
        'created_by_id': task.created_by_id,
        'is_verified_worker': is_verified_worker,
        'is_manager': is_manager,
        'can_take': (
            user.role == 'worker'
            and getattr(user, 'is_verified', False)
            and not user_assignment
            and task.status in ['recruiting', 'in_progress']
        ),
        'user_tracking': _user_tracking_payload(task, user_assignment) if is_verified_worker else None,
        'workers': workers,
        'can_reject_assignment': can_reject,
        'reject_block_reason': reject_reason,
    })
    return jsonify({'ok': True, 'task': payload})
