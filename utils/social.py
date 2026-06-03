"""Контакты и чёрный список."""

from sqlalchemy.orm import aliased

from models import BlacklistEntry, Chat, ChatParticipant, Contact, User, db


def is_contact(owner_id, contact_user_id):
    if not owner_id or not contact_user_id or owner_id == contact_user_id:
        return False
    return (
        Contact.query.filter_by(owner_id=owner_id, contact_user_id=contact_user_id).first()
        is not None
    )


def is_blocked(owner_id, other_user_id):
    if not owner_id or not other_user_id:
        return False
    return (
        BlacklistEntry.query.filter_by(owner_id=owner_id, blocked_user_id=other_user_id).first()
        is not None
    )


def is_blocked_either_way(user_a_id, user_b_id):
    return is_blocked(user_a_id, user_b_id) or is_blocked(user_b_id, user_a_id)


def add_contact(owner, contact_user_id):
    if owner.id == contact_user_id:
        raise ValueError('Нельзя добавить себя в контакты')
    target = User.query.get(contact_user_id)
    if not target:
        raise ValueError('Пользователь не найден')
    if is_blocked_either_way(owner.id, contact_user_id):
        raise ValueError('Пользователь в чёрном списке')
    existing = Contact.query.filter_by(owner_id=owner.id, contact_user_id=contact_user_id).first()
    if existing:
        return existing, False
    row = Contact(owner_id=owner.id, contact_user_id=contact_user_id)
    db.session.add(row)
    return row, True


def remove_contact(owner, contact_user_id):
    row = Contact.query.filter_by(owner_id=owner.id, contact_user_id=contact_user_id).first()
    if not row:
        return False
    db.session.delete(row)
    return True


def hide_private_chat_for_user(user_id, peer_id):
    cp1 = aliased(ChatParticipant)
    cp2 = aliased(ChatParticipant)
    chat = (
        Chat.query.filter(Chat.type == 'private')
        .join(cp1, Chat.id == cp1.chat_id)
        .join(cp2, Chat.id == cp2.chat_id)
        .filter(cp1.user_id == user_id, cp2.user_id == peer_id)
        .first()
    )
    if not chat:
        return False
    part = ChatParticipant.query.filter_by(chat_id=chat.id, user_id=user_id).first()
    if not part:
        return False
    part.is_hidden = True
    part.is_pinned = False
    return True


def toggle_blacklist(owner, blocked_user_id, *, block=True):
    if owner.id == blocked_user_id:
        raise ValueError('Нельзя заблокировать себя')
    target = User.query.get(blocked_user_id)
    if not target:
        raise ValueError('Пользователь не найден')

    row = BlacklistEntry.query.filter_by(owner_id=owner.id, blocked_user_id=blocked_user_id).first()
    if block:
        if row:
            return row, False
        row = BlacklistEntry(owner_id=owner.id, blocked_user_id=blocked_user_id)
        db.session.add(row)
        remove_contact(owner, blocked_user_id)
        hide_private_chat_for_user(owner.id, blocked_user_id)
        return row, True

    if not row:
        return None, False
    db.session.delete(row)
    return None, True


def list_contacts(owner_id):
    rows = (
        Contact.query.filter_by(owner_id=owner_id)
        .join(User, Contact.contact_user_id == User.id)
        .order_by(User.name.asc())
        .all()
    )
    return [c.contact_user for c in rows if c.contact_user]
