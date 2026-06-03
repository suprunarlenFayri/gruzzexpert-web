"""Сортировка и фильтрация чатов для списка."""

from models import ChatParticipant, Message, PinnedItem
from models import db


def _last_message_ts(chat):
    last = getattr(chat, 'last_message', None)
    if last and last.created_at:
        return last.created_at
    return chat.created_at


def sort_chats_for_user(chats):
    """Закреплённые сверху, затем по времени последнего сообщения."""
    if not chats:
        return chats

    def sort_key(chat):
        pinned = bool(getattr(chat, 'is_pinned', False))
        ts = _last_message_ts(chat)
        return (0 if pinned else 1, -(ts.timestamp() if ts else 0))

    return sorted(chats, key=sort_key)


def _sync_legacy_pins(user_id, parts):
    """Перенос закреплений из pinned_items в chat_participants."""
    legacy_ids = {
        item.item_id
        for item in PinnedItem.query.filter_by(user_id=user_id, item_type='chat').all()
    }
    changed = False
    for chat_id, part in parts.items():
        if chat_id in legacy_ids and part and not part.is_pinned:
            part.is_pinned = True
            changed = True
    if changed:
        db.session.commit()


def attach_participant_flags(chats, user_id):
    """Проставить is_pinned / participant с записи chat_participants."""
    if not chats:
        return chats
    chat_ids = [c.id for c in chats]
    parts = {
        p.chat_id: p
        for p in ChatParticipant.query.filter(
            ChatParticipant.user_id == user_id,
            ChatParticipant.chat_id.in_(chat_ids),
        ).all()
    }
    _sync_legacy_pins(user_id, parts)
    for chat in chats:
        part = parts.get(chat.id)
        chat.is_pinned = bool(part.is_pinned) if part else False
        chat._my_participant = part
    return sort_chats_for_user(chats)
