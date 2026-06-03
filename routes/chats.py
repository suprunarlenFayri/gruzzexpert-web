from flask import Blueprint, jsonify, render_template, redirect, url_for, request, flash, send_from_directory
from flask_login import login_required, current_user
from models import (
    Attachment,
    Message,
    MessageHidden,
    db,
    Chat,
    ChatParticipant,
    User,
    PinnedItem,
    ForwardedMessage,
)
from datetime import datetime
import os
from sqlalchemy.orm import aliased, joinedload
from services.notification_service import notify_chat_message
from socketio_instance import socketio
from services.chat_service import ChatService
from services.task_chat_service import TaskChatService
from services.forward_targets import (
    get_forward_peer_user_ids,
    get_forward_target_chats,
    get_or_create_private_chat,
    serialize_forward_targets,
)

from utils.media_urls import avatar_url_for
from utils.datetime_utils import utc_iso, utc_now
from utils.chat_list import attach_participant_flags, sort_chats_for_user
from utils.messages import DELETED_MESSAGE_PLACEHOLDER
from utils.crypto import encrypt_data
from utils.social import is_blocked_either_way

chats_bp = Blueprint('chats', __name__)

CHAT_HISTORY_LIMIT = 40

# Совпадает с messageDateSeparatorLabel в static/js/chat.js (разделитель дат)
UPLOAD_FOLDER = 'uploads'


def _message_query_options():
    return (
        joinedload(Message.sender),
        joinedload(Message.attachments),
        joinedload(Message.task),
        joinedload(Message.parent).joinedload(Message.sender),
    )


def _attachment_payload(att):
    fp = att.file_path or ''
    return {
        'id': att.id,
        'filename': att.filename,
        'file_path': fp,
        'path': fp,
        'file_type': att.file_type,
        'file_size': att.file_size,
        'thumbnail_path': att.thumbnail_path,
        'optimized_path': att.optimized_path,
    }


def _hidden_message_ids(user_id):
    return {
        row.message_id
        for row in MessageHidden.query.filter_by(user_id=user_id).all()
    }


def _visible_message_text(msg):
    if msg.deleted_for_all:
        return DELETED_MESSAGE_PLACEHOLDER
    return msg.plaintext_text or ''


def _serialize_chat_message(msg, current_user_id, *, hidden_ids=None):
    if hidden_ids is None:
        hidden_ids = _hidden_message_ids(current_user_id)
    if msg.id in hidden_ids:
        return None

    sender = msg.sender
    text = _visible_message_text(msg)
    payload = {
        'id': msg.id,
        'message': text,
        'text': text,
        'sender_id': msg.sender_id,
        'author_id': msg.sender_id,
        'author_name': sender.name if sender else 'Пользователь',
        'sender_name': sender.name if sender else 'Пользователь',
        'sender_avatar': avatar_url_for(sender, lambda p: url_for('uploaded_file', filename=p)) if sender else None,
        'avatar': avatar_url_for(sender, lambda p: url_for('uploaded_file', filename=p)) if sender else None,
        'created_at': utc_iso(msg.created_at) if msg.created_at else None,
        'is_read': bool(msg.is_read),
        'isMyMessage': msg.sender_id == current_user_id,
        'parent_id': msg.parent_id,
        'task_id': msg.task_id,
        'is_pinned': bool(msg.is_pinned),
        'deleted_for_all': bool(msg.deleted_for_all),
        'attachments': [] if msg.deleted_for_all else [_attachment_payload(a) for a in (msg.attachments or [])],
    }
    if msg.parent_id and msg.parent:
        payload['parent_author_name'] = (
            msg.parent.sender.name if msg.parent.sender else 'Пользователь'
        )
        parent_plain = (msg.parent.plaintext_text or '').strip()
        payload['parent_text'] = parent_plain if parent_plain and not parent_plain.startswith('enc:') else 'Вложение...'
    if msg.task:
        payload['task'] = {
            'id': msg.task.id,
            'address': msg.task.address,
            'price': float(msg.task.price or 0),
        }
    return payload


def _get_user_chats(user_id):
    chats = (
        Chat.query.join(ChatParticipant)
        .filter(
            ChatParticipant.user_id == user_id,
            ChatParticipant.is_hidden.is_(False),
        )
        .all()
    )
    ChatService.attach_unread_counts(chats, user_id)
    return attach_participant_flags(chats, user_id)


def _split_chats_by_type(chats):
    private_chats = [chat for chat in chats if not chat.is_group and chat.type == 'private']
    group_chats = [chat for chat in chats if chat.is_group or chat.type == 'group']
    task_chats = [chat for chat in chats if chat.type == 'task']
    return private_chats, group_chats, task_chats


def _get_all_users_except_current():
    return User.query.filter(User.id != current_user.id).order_by(User.name).all()


def _get_chat_participant(chat_id, user_id):
    return ChatParticipant.query.filter_by(chat_id=chat_id, user_id=user_id).first()


def _is_group_chat(chat):
    return bool(chat.is_group or chat.type == 'group')


def _promote_group_successor(chat_id, leaving_user_id):
    others = (
        ChatParticipant.query.filter(
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.user_id != leaving_user_id,
        )
        .order_by(ChatParticipant.created_at.asc())
        .all()
    )
    if not others:
        return None
    successor = next((p for p in others if p.role == 'admin'), others[0])
    successor.role = 'creator'
    return successor


def _member_avatar_url(user):
    return avatar_url_for(user, lambda p: url_for('uploaded_file', filename=p))


def _emit_group_membership_changed(chat_id, affected_user_ids=None):
    room = f'chat_{chat_id}'
    socketio.emit('group_updated', {'chat_id': chat_id}, room=room)
    socketio.emit('group_updated', {'chat_id': chat_id})

    for uid in affected_user_ids or []:
        socketio.emit('force_reload_chats', {'user_id': uid}, room=f'user_{uid}')


def _get_group_members(chat_id):
    return (
        db.session.query(User, ChatParticipant.role)
        .join(ChatParticipant, ChatParticipant.user_id == User.id)
        .filter(ChatParticipant.chat_id == chat_id)
        .order_by(User.name)
        .all()
    )


@chats_bp.route('/chats', endpoint='list')
@login_required
def chat_list():
    chats = _get_user_chats(current_user.id)
    private_chats, group_chats, task_chats = _split_chats_by_type(chats)

    return render_template(
        'chats/list.html',
        chats=chats,
        private_chats=private_chats,
        group_chats=group_chats,
        task_chats=task_chats,
        all_users=_get_all_users_except_current(),
        active_tab='chats',
    )

@chats_bp.route('/chat/<int:chat_id>')
@login_required
def view(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    
    # Проверка доступа
    participant = ChatParticipant.query.filter_by(
        chat_id=chat_id, user_id=current_user.id
    ).first()
    if not participant:
        flash('У вас нет доступа к этому чату')
        return redirect(url_for('chats.list'))
    
    participant.last_read_at = utc_now()
    db.session.commit()

    base_query = Message.query.filter_by(chat_id=chat_id)
    total_count = base_query.count()
    messages = (
        base_query.options(*_message_query_options())
        .order_by(Message.created_at.desc())
        .limit(CHAT_HISTORY_LIMIT)
        .all()
    )
    messages = list(reversed(messages))
    hidden_ids = _hidden_message_ids(current_user.id)
    messages = [m for m in messages if m.id not in hidden_ids]
    chat_has_more_older = total_count > len(messages)
    oldest_message_id = messages[0].id if messages else None
    participants = chat.get_participants()
    
    all_chats = _get_user_chats(current_user.id)
    private_chats, group_chats, task_chats = _split_chats_by_type(all_chats)
    
    group_members = []
    users_available_to_add = []
    current_user_chat_role = 'member'
    can_manage_group = False

    if _is_group_chat(chat):
        group_members = _get_group_members(chat_id)
        participant_ids = {user.id for user, _role in group_members}
        users_available_to_add = [
            user for user in _get_all_users_except_current()
            if user.id not in participant_ids
        ]
        current_user_chat_role = participant.role if participant else 'member'
        can_manage_group = participant.is_admin() if participant else False

    forward_target_chats = get_forward_target_chats(current_user.id)
    forward_targets = serialize_forward_targets(forward_target_chats, current_user)
    
    return render_template('chats/chat.html', 
                         chat=chat, 
                         messages=messages,
                         chat_has_more_older=chat_has_more_older,
                         oldest_message_id=oldest_message_id,
                         chat_history_limit=CHAT_HISTORY_LIMIT,
                         forward_targets=forward_targets,
                         participants=participants,
                         chats=all_chats,
                         private_chats=private_chats,
                         group_chats=group_chats,
                         task_chats=task_chats,
                         all_users=_get_all_users_except_current(),
                         group_members=group_members,
                         users_available_to_add=users_available_to_add,
                         current_user_chat_role=current_user_chat_role,
                         can_manage_group=can_manage_group,
                         active_tab='chats')

@chats_bp.route('/chat/<int:chat_id>/messages', methods=['GET'])
@login_required
def chat_messages_page(chat_id):
    """Пагинация истории: последние N сообщений или порция старше before_id."""
    chat = Chat.query.get_or_404(chat_id)
    participant = ChatParticipant.query.filter_by(
        chat_id=chat_id, user_id=current_user.id
    ).first()
    if not participant:
        return jsonify({'success': False, 'error': 'Нет доступа к чату'}), 403

    before_id = request.args.get('before_id', type=int)
    limit = request.args.get('limit', CHAT_HISTORY_LIMIT, type=int)
    limit = max(1, min(limit, 50))

    query = Message.query.filter_by(chat_id=chat_id).options(*_message_query_options())

    if before_id:
        anchor = Message.query.filter_by(id=before_id, chat_id=chat_id).first()
        if not anchor:
            return jsonify({'success': False, 'error': 'Сообщение не найдено'}), 404
        query = query.filter(Message.created_at < anchor.created_at)

    batch = query.order_by(Message.created_at.desc()).limit(limit).all()
    batch = list(reversed(batch))

    has_more = False
    if batch:
        oldest = batch[0]
        has_more = (
            Message.query.filter(
                Message.chat_id == chat_id,
                Message.created_at < oldest.created_at,
            ).first()
            is not None
        )

    hidden_ids = _hidden_message_ids(current_user.id)
    serialized = [
        payload
        for m in batch
        if (payload := _serialize_chat_message(m, current_user.id, hidden_ids=hidden_ids))
    ]

    return jsonify({
        'success': True,
        'messages': serialized,
        'has_more': has_more,
        'oldest_id': batch[0].id if batch else None,
    })


@chats_bp.route('/chat/forward-targets', methods=['GET'])
@login_required
def forward_targets_api():
    """Личные чаты для модалки «Переслать» (контакты ∪ direct)."""
    chats = get_forward_target_chats(current_user.id)
    return jsonify({
        'success': True,
        'targets': serialize_forward_targets(chats, current_user),
    })


@chats_bp.route('/chat/send/<int:chat_id>', methods=['POST'])
@login_required
def send(chat_id):
    # Гарантируем наличие колонки в PostgreSQL
    try:
        db.session.execute(db.text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES messages(id) ON DELETE SET NULL;"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    text = request.form.get('text', '').strip()
    parent_id = request.form.get('parent_id')

    if parent_id in ['', 'null', 'None', None]:
        parent_id = None
    else:
        try:
            parent_id = int(parent_id)
        except ValueError:
            parent_id = None

    chat = Chat.query.get_or_404(chat_id)

    files = request.files.getlist('files')
    attachments_data = []

    if files and any(f.filename for f in files):
        for file in files:
            if not file or not file.filename:
                continue
            if not ChatService.allowed_file(file.filename, file.mimetype):
                continue
            file_content = file.read()
            if not file_content:
                continue
            file_type = ChatService.resolve_file_type(file.filename, file.mimetype)
            attachments_data.append({
                'data': file_content,
                'filename': file.filename,
                'file_type': file_type,
                'mimetype': file.mimetype,
            })

    message_dict = ChatService.send_message(
        chat_id=chat_id,
        sender_id=current_user.id,
        text=text,
        attachments=attachments_data,
        parent_id=parent_id
    )

    if files and any(f.filename for f in files) and not attachments_data:
        err = 'Файлы не приняты. Проверьте формат (изображения, видео MP4/MOV) и размер до 200 МБ.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': err}), 400
        flash(err)
        return redirect(url_for('chats.view', chat_id=chat_id))

    if not message_dict:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Failed to send message'}), 500
        return redirect(url_for('chats.view', chat_id=chat_id))

    message = db.session.get(Message, message_dict['id'])
    if parent_id and message and hasattr(message, 'parent_id'):
        message.parent_id = parent_id
        db.session.commit()

    send_update_payload = {
        'chat_id': chat_id,
        'id': message_dict['id'],
        'message': message_dict['text'],
        'sender_id': current_user.id,
        'author_id': current_user.id,
        'author_name': current_user.name,
        'sender_name': current_user.name,
        'sender_avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
        'avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
        'created_at': message_dict['created_at'],
        'is_read': message_dict['is_read'],
        'attachments': message_dict['attachments'],
        'parent_id': parent_id,
    }
    if parent_id:
        parent_msg = db.session.get(Message, parent_id)
        if parent_msg:
            send_update_payload['parent_author_name'] = parent_msg.sender.name if parent_msg.sender else 'Пользователь'
            send_update_payload['parent_text'] = parent_msg.plaintext_text

    notify_chat_message(chat_id, current_user.id, send_update_payload)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        msg_data = {
            'id': message_dict['id'],
            'text': message_dict['text'],
            'created_at': message_dict['created_at'],
            'is_read': message_dict['is_read'],
            'attachments': message_dict['attachments'],
            'parent_id': parent_id,
        }

        if parent_id:
            parent_msg = db.session.get(Message, parent_id)
            if parent_msg:
                msg_data['parent_author_name'] = parent_msg.sender.name if parent_msg.sender else 'Пользователь'
                msg_data['parent_text'] = parent_msg.plaintext_text

        return jsonify({'success': True, 'message': msg_data})

    return redirect(url_for('chats.view', chat_id=chat_id))

@chats_bp.route('/chat/create/private/<int:user_id>')
@login_required
def create_private(user_id):
    other_user = User.query.get_or_404(user_id)
    if is_blocked_either_way(current_user.id, other_user.id):
        flash('Нельзя начать диалог: пользователь в чёрном списке')
        return redirect(url_for('chats.list'))

    # Создаём два псевдонима для таблицы участников
    cp1 = aliased(ChatParticipant)
    cp2 = aliased(ChatParticipant)
    
    # Ищем приватный чат, где есть и текущий пользователь, и собеседник
    existing_chat = Chat.query.filter(Chat.type == 'private')\
        .join(cp1, Chat.id == cp1.chat_id)\
        .join(cp2, Chat.id == cp2.chat_id)\
        .filter(cp1.user_id == current_user.id)\
        .filter(cp2.user_id == other_user.id)\
        .first()
    
    if existing_chat:
        my_part = ChatParticipant.query.filter_by(
            chat_id=existing_chat.id, user_id=current_user.id
        ).first()
        if my_part and my_part.is_hidden:
            my_part.is_hidden = False
            db.session.commit()
        return redirect(url_for('chats.view', chat_id=existing_chat.id))
    
    # Создаём новый чат
    chat = Chat(
        type='private',
        name=f"Чат с {other_user.name}",
        workspace_id=None
    )
    db.session.add(chat)
    db.session.flush()
    
    # Добавляем участников
    participant1 = ChatParticipant(chat_id=chat.id, user_id=current_user.id)
    participant2 = ChatParticipant(chat_id=chat.id, user_id=other_user.id)
    db.session.add(participant1)
    db.session.add(participant2)
    
    db.session.commit()
    
    return redirect(url_for('chats.view', chat_id=chat.id))

@chats_bp.route('/chat/create/task/<int:task_id>')
@login_required
def create_task_chat(task_id):
    from models import Task
    task = Task.query.get_or_404(task_id)
    
    if task.chat_id:
        return redirect(url_for('chats.view', chat_id=task.chat_id))
    
    chat = TaskChatService.ensure_task_group_chat(task)
    if not chat:
        flash('Групповой чат будет создан после полного набора исполнителей')
        return redirect(url_for('tasks.task_detail', task_id=task.id))

    db.session.commit()
    return redirect(url_for('chats.view', chat_id=chat.id))

@chats_bp.route('/chats/create_group', methods=['POST'])
@login_required
def create_group():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    user_ids = data.get('user_ids') or []

    if not name or not user_ids:
        return jsonify({'success': False, 'error': 'Некорректные данные'}), 400

    member_ids = set()
    for raw_id in user_ids:
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if uid != current_user.id and User.query.get(uid):
            member_ids.add(uid)

    if not member_ids:
        return jsonify({'success': False, 'error': 'Выберите хотя бы одного участника'}), 400

    new_chat = Chat(
        is_group=True,
        type='group',
        name=name,
        workspace_id=current_user.workspace_id,
    )
    db.session.add(new_chat)
    db.session.flush()

    db.session.add(ChatParticipant(chat_id=new_chat.id, user_id=current_user.id, role='creator'))
    for uid in member_ids:
        db.session.add(ChatParticipant(chat_id=new_chat.id, user_id=uid, role='member'))

    db.session.commit()
    return jsonify({'success': True, 'chat_id': new_chat.id})


@chats_bp.route('/chats/<int:chat_id>/info', methods=['GET'])
@login_required
def chat_info(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    if not _is_group_chat(chat):
        return jsonify({'success': False, 'error': 'Информация доступна только для групповых чатов'}), 400

    participant = _get_chat_participant(chat_id, current_user.id)
    if not participant:
        return jsonify({'success': False, 'error': 'Нет доступа к этому чату'}), 403

    is_admin = participant.is_admin()
    members = []
    member_ids = set()
    for user, role in _get_group_members(chat_id):
        member_ids.add(user.id)
        members.append({
            'id': user.id,
            'name': user.name,
            'role': role,
            'avatar': _member_avatar_url(user),
        })

    available_users = []
    if is_admin:
        for user in _get_all_users_except_current():
            if user.id not in member_ids:
                available_users.append({
                    'id': user.id,
                    'name': user.name,
                    'avatar': _member_avatar_url(user),
                })

    return jsonify({
        'success': True,
        'name': chat.name or 'Группа',
        'is_admin': is_admin,
        'current_user_role': participant.role,
        'members': members,
        'available_users': available_users,
    })


@chats_bp.route('/chats/<int:chat_id>/leave', methods=['POST'])
@login_required
def leave_group(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    if not _is_group_chat(chat):
        return jsonify({'success': False, 'error': 'Выход доступен только для групповых чатов'}), 400

    participant = _get_chat_participant(chat_id, current_user.id)
    if not participant:
        return jsonify({'success': False, 'error': 'Вы не состоите в этом чате'}), 403

    if participant.role == 'creator':
        others_count = ChatParticipant.query.filter(
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.user_id != current_user.id,
        ).count()
        if others_count == 0:
            db.session.delete(chat)
            db.session.commit()
            _emit_group_membership_changed(chat_id, [current_user.id])
            return jsonify({'success': True, 'redirect': url_for('chats.list')})
        _promote_group_successor(chat_id, current_user.id)
        db.session.delete(participant)
    else:
        db.session.delete(participant)

    db.session.commit()
    _emit_group_membership_changed(chat_id, [current_user.id])
    return jsonify({'success': True, 'redirect': url_for('chats.list')})


@chats_bp.route('/chats/<int:chat_id>/add_members', methods=['POST'])
@login_required
def add_group_members(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    if not _is_group_chat(chat):
        return jsonify({'success': False, 'error': 'Добавление участников доступно только в группах'}), 400

    actor = _get_chat_participant(chat_id, current_user.id)
    if not actor or not actor.is_admin():
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    data = request.get_json(silent=True) or {}
    user_ids = data.get('user_ids') or []
    added = []

    for raw_id in user_ids:
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if uid == current_user.id or not User.query.get(uid):
            continue
        if _get_chat_participant(chat_id, uid):
            continue
        db.session.add(ChatParticipant(chat_id=chat_id, user_id=uid, role='member'))
        added.append(uid)

    if not added:
        return jsonify({'success': False, 'error': 'Нет новых участников для добавления'}), 400

    db.session.commit()
    _emit_group_membership_changed(chat_id, added)
    return jsonify({'success': True, 'added_user_ids': added})


@chats_bp.route('/chats/<int:chat_id>/kick/<int:user_id>', methods=['POST'])
@login_required
def kick_group_member(chat_id, user_id):
    chat = Chat.query.get_or_404(chat_id)
    if not _is_group_chat(chat):
        return jsonify({'success': False, 'error': 'Исключение доступно только в группах'}), 400

    actor = _get_chat_participant(chat_id, current_user.id)
    if not actor or not actor.is_admin():
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Используйте выход из группы'}), 400

    target = _get_chat_participant(chat_id, user_id)
    if not target:
        return jsonify({'success': False, 'error': 'Пользователь не найден в чате'}), 404

    if target.role == 'creator':
        return jsonify({'success': False, 'error': 'Нельзя исключить создателя группы'}), 403

    if actor.role == 'admin' and target.role == 'admin':
        return jsonify({'success': False, 'error': 'Админ не может исключить другого админа'}), 403

    db.session.delete(target)
    db.session.commit()
    _emit_group_membership_changed(chat_id, [user_id])
    return jsonify({'success': True, 'kicked_user_id': user_id})

@chats_bp.route('/search-users')
@login_required
def search_users():
    from utils.user_profiles import can_view_user_profile
    from utils.user_settings import can_find_user_by_phone, can_view_private_field

    query = (request.args.get('q') or '').strip()
    results = []
    if query:
        q_lower = query.lower().lstrip('@')
        candidates = User.query.filter(
            (User.name.contains(query)) |
            (User.phone.contains(query)) |
            (User.tag.contains(query)) |
            (User.username.contains(query))
        ).limit(40).all()

        for user in candidates:
            if user.id == current_user.id:
                continue
            if not can_view_user_profile(current_user, user):
                continue

            name_match = q_lower in (user.name or '').lower()
            tag_match = user.tag and q_lower in user.tag.lower()
            phone_match = user.phone and query.replace(' ', '') in user.phone.replace(' ', '')

            if phone_match and not name_match and not tag_match:
                if not can_find_user_by_phone(current_user, user):
                    continue
            elif not (name_match or tag_match or phone_match):
                continue

            results.append({
                'user': user,
                'show_phone': can_view_private_field(current_user, user, 'phone'),
            })

    return render_template(
        'chats/search_users.html',
        users=results,
        query=query,
        active_tab='chats',
    )

@chats_bp.route('/attachment/delete/<int:attachment_id>', methods=['POST'])
@login_required
def delete_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    # Проверяем, что пользователь владелец сообщения
    if attachment.message.sender_id != current_user.id:
        return '', 403
    
    # Удаляем файл
    file_path = os.path.join(UPLOAD_FOLDER, attachment.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.session.delete(attachment)
    db.session.commit()
    
    return '', 200

@chats_bp.route('/attachment/caption/<int:attachment_id>', methods=['POST'])
@login_required
def add_attachment_caption(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    if attachment.message.sender_id != current_user.id:
        return '', 403
    
    data = request.get_json()
    caption = data.get('caption', '')
    # Здесь можно добавить поле caption в модель Attachment
    # attachment.caption = caption
    db.session.commit()
    
    return '', 200

@chats_bp.route('/attachment/download/<int:attachment_id>')
@login_required
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    # Проверяем, что пользователь участник чата
    chat = attachment.message.chat
    participant = ChatParticipant.query.filter_by(
        chat_id=chat.id, user_id=current_user.id
    ).first()
    if not participant:
        return '', 403
    
    file_path = os.path.join(UPLOAD_FOLDER, attachment.file_path)
    if not os.path.exists(file_path):
        return '', 404
    
    return send_from_directory(
        UPLOAD_FOLDER,
        os.path.basename(attachment.file_path),
        as_attachment=True,
        download_name=attachment.filename
    )

# ===== ДОБАВЛЯЕМ МАРШРУТ ДЛЯ ЗАКРЕПЛЕНИЯ ЧАТА =====
@chats_bp.route('/pin/chat/<int:chat_id>', methods=['POST'])
@login_required
def pin_chat(chat_id):
    participant = _get_chat_participant(chat_id, current_user.id)
    if not participant:
        return jsonify({'ok': False, 'error': 'Нет доступа к чату'}), 403

    participant.is_pinned = not bool(participant.is_pinned)
    participant.pinned_at = utc_now() if participant.is_pinned else None

    legacy = PinnedItem.query.filter_by(
        user_id=current_user.id, item_type='chat', item_id=chat_id
    ).first()
    if participant.is_pinned and not legacy:
        db.session.add(PinnedItem(
            user_id=current_user.id,
            workspace_id=current_user.workspace_id or 1,
            item_type='chat',
            item_id=chat_id,
        ))
    elif not participant.is_pinned and legacy:
        db.session.delete(legacy)

    db.session.commit()
    return jsonify({'ok': True, 'pinned': participant.is_pinned}), 200


@chats_bp.route('/api/chats/<int:chat_id>/hide', methods=['POST'])
@login_required
def hide_chat(chat_id):
    participant = _get_chat_participant(chat_id, current_user.id)
    if not participant:
        return jsonify({'ok': False, 'error': 'Нет доступа к чату'}), 403

    participant.is_hidden = True
    participant.is_pinned = False
    participant.pinned_at = None
    legacy = PinnedItem.query.filter_by(
        user_id=current_user.id, item_type='chat', item_id=chat_id
    ).first()
    if legacy:
        db.session.delete(legacy)
    db.session.commit()
    return jsonify({'ok': True, 'hidden': True}), 200


@chats_bp.route('/chat/<int:chat_id>/pinned-message', methods=['GET'])
@login_required
def get_pinned_message(chat_id):
    participant = _get_chat_participant(chat_id, current_user.id)
    if not participant:
        return jsonify({'ok': False, 'error': 'Нет доступа'}), 403

    msg = (
        Message.query.filter_by(chat_id=chat_id, is_pinned=True)
        .options(joinedload(Message.sender))
        .order_by(Message.pinned_at.desc())
        .first()
    )
    if not msg:
        return jsonify({'ok': True, 'pinned': None})

    hidden_ids = _hidden_message_ids(current_user.id)
    payload = _serialize_chat_message(msg, current_user.id, hidden_ids=hidden_ids)
    return jsonify({'ok': True, 'pinned': payload})


@chats_bp.route('/chat/message/<int:message_id>/pin', methods=['POST'])
@login_required
def pin_message(message_id):
    msg = Message.query.get_or_404(message_id)
    participant = _get_chat_participant(msg.chat_id, current_user.id)
    if not participant:
        return jsonify({'ok': False, 'error': 'Нет доступа'}), 403

    if msg.is_pinned:
        msg.is_pinned = False
        msg.pinned_at = None
        pinned = False
    else:
        Message.query.filter_by(chat_id=msg.chat_id, is_pinned=True).update(
            {'is_pinned': False, 'pinned_at': None}, synchronize_session=False
        )
        msg.is_pinned = True
        msg.pinned_at = utc_now()
        pinned = True

    db.session.commit()
    hidden_ids = _hidden_message_ids(current_user.id)
    payload = _serialize_chat_message(msg, current_user.id, hidden_ids=hidden_ids)
    room = f'chat_{msg.chat_id}'
    if pinned:
        socketio.emit('chat_pinned_message', {
            'chat_id': msg.chat_id,
            'pinned': payload,
        }, room=room)
    else:
        socketio.emit('message_unpinned', {
            'chat_id': msg.chat_id,
            'message_id': msg.id,
        }, room=room)
        socketio.emit('chat_pinned_message', {
            'chat_id': msg.chat_id,
            'pinned': None,
        }, room=room)
    return jsonify({'ok': True, 'pinned': pinned, 'message': payload})


@chats_bp.route('/chat/message/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    msg = Message.query.get_or_404(message_id)
    participant = _get_chat_participant(msg.chat_id, current_user.id)
    if not participant:
        return jsonify({'ok': False, 'error': 'Нет доступа'}), 403

    data = request.get_json(silent=True) or {}
    scope = (data.get('scope') or 'me').strip().lower()

    if scope == 'all':
        if msg.sender_id != current_user.id:
            return jsonify({'ok': False, 'error': 'Можно удалить только свои сообщения для всех'}), 403
        msg.text = encrypt_data(DELETED_MESSAGE_PLACEHOLDER)
        msg.deleted_for_all = True
        msg.is_pinned = False
        msg.pinned_at = None
        for att in msg.attachments or []:
            db.session.delete(att)
    else:
        existing = MessageHidden.query.filter_by(
            user_id=current_user.id, message_id=msg.id
        ).first()
        if not existing:
            db.session.add(MessageHidden(user_id=current_user.id, message_id=msg.id))

    db.session.commit()
    socketio.emit('message_deleted', {
        'chat_id': msg.chat_id,
        'message_id': msg.id,
        'scope': scope,
        'user_id': current_user.id,
        'deleted_for_all': bool(msg.deleted_for_all),
    }, room=f'chat_{msg.chat_id}')
    return jsonify({
        'ok': True,
        'message_id': msg.id,
        'scope': scope,
        'deleted_for_all': bool(msg.deleted_for_all),
    }), 200

# ===== ДОБАВЛЯЕМ МАРШРУТ ДЛЯ ОЧИСТКИ ИСТОРИИ ЧАТА =====
@chats_bp.route('/chat/clear/<int:chat_id>', methods=['POST'])
@login_required
def clear_chat_history(chat_id):
    # Проверяем доступ
    participant = ChatParticipant.query.filter_by(
        chat_id=chat_id, user_id=current_user.id
    ).first()
    if not participant:
        return '', 403
    
    # Удаляем все сообщения чата
    Message.query.filter_by(chat_id=chat_id).delete()
    db.session.commit()

    return '', 200

def _build_forward_socket_payload(target_chat, new_msg):
    return {
        'chat_id': target_chat.id,
        'id': new_msg.id,
        'message': new_msg.plaintext_text,
        'sender_id': current_user.id,
        'author_id': current_user.id,
        'author_name': current_user.name,
        'sender_name': current_user.name,
        'sender_avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
        'avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
        'is_read': False,
        'attachments': [
            {
                'id': a.id,
                'file_path': a.file_path,
                'filename': a.filename,
                'file_type': a.file_type,
                'optimized_path': a.optimized_path,
                'thumbnail_path': a.thumbnail_path,
            }
            for a in new_msg.attachments
        ],
        'created_at': utc_iso(new_msg.created_at),
    }


@chats_bp.route('/chat/forward/<int:message_id>', methods=['POST'])
@login_required
def forward_message(message_id):
    data = request.get_json(silent=True) or {}
    raw_ids = data.get('user_ids', [])

    if not isinstance(raw_ids, list):
        return jsonify({'status': 'error', 'error': 'Некорректный список получателей'}), 400

    try:
        user_ids = []
        seen = set()
        for uid in raw_ids:
            n = int(uid)
            if n not in seen:
                seen.add(n)
                user_ids.append(n)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'error': 'Некорректный список получателей'}), 400

    if not user_ids:
        return jsonify({'status': 'error', 'error': 'Выберите получателей'}), 400

    orig_msg = Message.query.get_or_404(message_id)
    if not _get_chat_participant(orig_msg.chat_id, current_user.id):
        return jsonify({'status': 'error', 'error': 'Нет доступа к сообщению'}), 403

    allowed_peers = get_forward_peer_user_ids(current_user.id)
    processed = 0
    notify_queue = []

    for target_user_id in user_ids:
        if target_user_id == current_user.id:
            continue
        if target_user_id not in allowed_peers:
            continue

        target_chat = get_or_create_private_chat(current_user.id, target_user_id)
        if not target_chat:
            continue

        new_msg = Message(
            chat_id=target_chat.id,
            sender_id=current_user.id,
            text=orig_msg.text,
            workspace_id=target_chat.workspace_id,
        )
        db.session.add(new_msg)
        db.session.flush()

        for att in orig_msg.attachments or []:
            db.session.add(
                Attachment(
                    message_id=new_msg.id,
                    filename=att.filename,
                    file_path=att.file_path,
                    file_type=att.file_type,
                    file_size=att.file_size,
                    thumbnail_path=att.thumbnail_path,
                    optimized_path=att.optimized_path,
                )
            )

        db.session.add(
            ForwardedMessage(
                original_message_id=orig_msg.id,
                new_message_id=new_msg.id,
                forwarded_by_id=current_user.id,
            )
        )
        notify_queue.append((target_chat, new_msg.id))
        processed += 1

    if processed == 0:
        db.session.rollback()
        return jsonify({'status': 'error', 'error': 'Не удалось переслать ни одному получателю'}), 400

    db.session.commit()

    for target_chat, new_msg_id in notify_queue:
        new_msg = db.session.get(Message, new_msg_id)
        if new_msg:
            notify_chat_message(
                target_chat.id,
                current_user.id,
                _build_forward_socket_payload(target_chat, new_msg),
            )

    return jsonify({'status': 'success', 'processed': processed}), 200