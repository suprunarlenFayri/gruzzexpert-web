"""Цели пересылки: контакты ∪ собеседники личных чатов."""
from flask import url_for
from sqlalchemy import inspect
from sqlalchemy.orm import aliased

from models import Chat, ChatParticipant, Contact, User, db
from utils.media_urls import avatar_url_for
from utils.social import is_blocked_either_way


def _contacts_table_exists():
    try:
        return inspect(db.engine).has_table('contacts')
    except Exception:
        return False


def get_forward_peer_user_ids(user_id):
    """UNION: ID из Contact + ID собеседников private-чатов."""
    cp_me = aliased(ChatParticipant)
    cp_other = aliased(ChatParticipant)

    direct_q = (
        db.session.query(cp_other.user_id.label('peer_id'))
        .join(Chat, Chat.id == cp_other.chat_id)
        .join(cp_me, (cp_me.chat_id == Chat.id) & (cp_me.user_id == user_id))
        .filter(
            Chat.type == 'private',
            Chat.is_group.is_(False),
            cp_other.user_id != user_id,
        )
    )

    queries = [direct_q]
    if _contacts_table_exists():
        contact_q = db.session.query(Contact.contact_user_id.label('peer_id')).filter(
            Contact.owner_id == user_id,
            Contact.contact_user_id != user_id,
        )
        queries.append(contact_q)

    if len(queries) == 1:
        union_q = queries[0]
    else:
        union_q = queries[0].union(*queries[1:])

    rows = db.session.query(union_q.subquery().c.peer_id).distinct().all()
    return {row[0] for row in rows if row[0]}


def get_forward_target_chats(user_id):
    """Личные чаты, куда разрешена пересылка (peer ∈ contacts ∪ direct)."""
    peer_ids = get_forward_peer_user_ids(user_id)
    if not peer_ids:
        return []

    cp_me = aliased(ChatParticipant)
    cp_other = aliased(ChatParticipant)

    return (
        Chat.query.join(cp_me, (cp_me.chat_id == Chat.id) & (cp_me.user_id == user_id))
        .join(
            cp_other,
            (cp_other.chat_id == Chat.id) & (cp_other.user_id.in_(peer_ids)),
        )
        .filter(Chat.type == 'private', Chat.is_group.is_(False))
        .order_by(Chat.created_at.desc())
        .all()
    )


def is_allowed_forward_chat(user_id, chat_id):
    from models import User

    viewer = User.query.get(user_id)
    chat = Chat.query.get(chat_id)
    if not viewer or not chat or chat.type != 'private' or chat.is_group:
        return False
    other = chat.get_other_participant(viewer)
    if not other:
        return False
    return other.id in get_forward_peer_user_ids(user_id)


def get_or_create_private_chat(user_id, peer_user_id):
    """Найти или создать личный чат между user_id и peer_user_id."""
    if not peer_user_id or peer_user_id == user_id:
        return None

    other_user = User.query.get(peer_user_id)
    if not other_user or is_blocked_either_way(user_id, peer_user_id):
        return None

    cp1 = aliased(ChatParticipant)
    cp2 = aliased(ChatParticipant)

    existing_chat = (
        Chat.query.filter(Chat.type == 'private', Chat.is_group.is_(False))
        .join(cp1, Chat.id == cp1.chat_id)
        .join(cp2, Chat.id == cp2.chat_id)
        .filter(cp1.user_id == user_id, cp2.user_id == peer_user_id)
        .first()
    )

    if existing_chat:
        my_part = ChatParticipant.query.filter_by(
            chat_id=existing_chat.id, user_id=user_id
        ).first()
        if my_part and my_part.is_hidden:
            my_part.is_hidden = False
        return existing_chat

    chat = Chat(
        type='private',
        name=f'Чат с {other_user.name}',
        workspace_id=None,
        is_group=False,
    )
    db.session.add(chat)
    db.session.flush()
    db.session.add(ChatParticipant(chat_id=chat.id, user_id=user_id))
    db.session.add(ChatParticipant(chat_id=chat.id, user_id=peer_user_id))
    return chat


def serialize_forward_targets(chats, viewer):
    """Список dict для window.ForwardTargetsList / API."""
    items = []
    for chat in chats:
        other = chat.get_other_participant(viewer)
        if not other:
            continue
        name = other.name or f'Чат #{chat.id}'
        avatar = ''
        if other.avatar:
            avatar = avatar_url_for(other, lambda p: url_for('uploaded_file', filename=p)) or ''
        initials = other.name[0].upper() if other.name else '💬'
        items.append({
            'id': chat.id,
            'user_id': other.id,
            'name': name,
            'avatar': avatar,
            'initials': initials,
        })
    return items
