"""Сериализация чатов и заявок для Flutter (/api/mobile/*)."""
import json

from flask import request, url_for

from models import Message, Task, TaskAssignment, User
from services.chat_service import ChatService
from utils.datetime_utils import format_execution_date, format_local_datetime, utc_iso
from utils.media_urls import avatar_url_for


def _abs_media_url(path):
    if not path:
        return None
    if path.startswith('http://') or path.startswith('https://'):
        return path
    base = request.host_url.rstrip('/')
    if path.startswith('/'):
        return f'{base}{path}'
    return f'{base}/{path}'


def _chat_title(chat, user):
    if chat.name:
        return chat.name
    if chat.type == 'task' and chat.task:
        return chat.task.title or f'Заявка #{chat.task_id}'
    other = chat.get_other_participant(user)
    if other:
        return other.name or 'Чат'
    return 'Чат'


def serialize_chat_summary(chat, user):
    last = chat.last_message
    preview = ''
    if last:
        preview = (last.plaintext_text or last.text or '').strip()
        if preview.startswith('enc:'):
            preview = 'Сообщение'
        preview = preview[:120]
    return {
        'id': chat.id,
        'title': _chat_title(chat, user),
        'type': chat.type or 'private',
        'is_group': bool(chat.is_group),
        'task_id': chat.task_id,
        'unread_count': int(getattr(chat, 'unread_count', 0) or 0),
        'last_message': preview,
        'last_message_at': utc_iso(last.created_at) if last and last.created_at else None,
    }


def serialize_task_card(task):
    city_name = task.city.name if task.city else ''
    return {
        'id': task.id,
        'title': task.title or 'Без названия',
        'description': task.description or '',
        'price': float(task.price or 0),
        'status': task.status or 'recruiting',
        'city': city_name,
        'address': task.address or '',
        'execution_date': format_execution_date(task.execution_date),
        'execution_time': task.execution_time.strftime('%H:%M') if task.execution_time else '08:00',
        'required_workers': int(task.required_workers or 1),
        'assigned_count': len(task.get_assigned_workers()),
        'task_number': task.task_number or '',
        'chat_id': task.chat_id,
    }


def worker_task_scope_filter(query, user):
    if user.role != 'worker':
        return query
    locations = user.allowed_locations
    if isinstance(locations, str):
        try:
            locations = json.loads(locations)
        except Exception:
            locations = []
    if locations and isinstance(locations, list):
        return query.filter(Task.city_id.in_(locations))
    from sqlalchemy import false
    return query.filter(false())
