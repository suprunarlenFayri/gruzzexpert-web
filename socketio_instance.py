import logging

from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")
logger = logging.getLogger(__name__)


def send_update(event_type, data, user_ids=None):
    payload = {'type': event_type, 'payload': data}
    try:
        if user_ids:
            for uid in user_ids:
                if uid is not None:
                    socketio.emit('global_update', payload, room=f'user_{int(uid)}')
            return
        socketio.emit('global_update', payload)
    except Exception as exc:
        logger.warning('send_update %s failed: %s', event_type, exc, exc_info=True)


def emit_task_notification(workspace_id, data, user_id=None, user_ids=None):
    """Push по заявкам: комната workspace или личные комнаты без workspace."""
    try:
        if workspace_id:
            socketio.emit('task_notification', data, room=f'workspace_{int(workspace_id)}')
            return
        targets = set()
        if user_id is not None:
            targets.add(int(user_id))
        if user_ids:
            targets.update(int(uid) for uid in user_ids if uid is not None)
        for uid in targets:
            socketio.emit('task_notification', data, room=f'user_{uid}')
    except Exception as exc:
        logger.warning('emit_task_notification failed: %s', exc, exc_info=True)


def send_user_notification(user_id, notification):
    socketio.emit('user_notification', notification, room=f'user_{int(user_id)}')


def emit_new_profile_moderation(city_id, workspace_id=None):
    """Уведомление диспетчеров о новой анкете на модерации в городе."""
    if not city_id:
        return
    payload = {'city_id': int(city_id)}
    socketio.emit('new_profile_moderation', payload, room=f'moderation_city_{int(city_id)}')
    if workspace_id:
        socketio.emit('new_profile_moderation', payload, room=f'workspace_{int(workspace_id)}')
