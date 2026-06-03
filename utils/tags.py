"""Нормализация и проверка уникальности тегов (@username)."""

from models import User


def normalize_tag(raw):
    if raw is None:
        return None
    tag = str(raw).strip()
    if not tag:
        return None
    if tag.startswith('@'):
        tag = tag[1:].strip()
    return tag or None


def tag_is_available(tag, exclude_user_id=None):
    if not tag:
        return False
    query = User.query.filter(User.tag == tag)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is None
