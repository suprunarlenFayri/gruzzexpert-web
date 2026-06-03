"""Firebase Cloud Messaging — push на мобильные устройства."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_firebase_app = None
_init_attempted = False


def _credentials_path() -> Path | None:
    raw = (os.getenv('FIREBASE_CREDENTIALS_PATH') or 'firebase_credentials.json').strip()
    path = Path(raw)
    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    return path if path.is_file() else None


def init_firebase():
    global _firebase_app, _init_attempted
    if _init_attempted:
        return _firebase_app is not None
    _init_attempted = True

    cred_path = _credentials_path()
    if not cred_path:
        logger.info('Firebase credentials not found — push disabled')
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            return True

        cred = credentials.Certificate(str(cred_path))
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info('Firebase Admin initialized')
        return True
    except Exception as exc:
        logger.warning('Firebase init failed: %s', exc)
        return False


def is_user_socket_online(user_id: int) -> bool:
    """Грубая проверка: есть ли активные Socket.IO подключения в комнате user_{id}."""
    try:
        from socketio_instance import socketio

        if not socketio.server:
            return False
        namespace = '/'
        room = f'user_{int(user_id)}'
        manager = socketio.server.manager
        if hasattr(manager, 'get_participants'):
            participants = manager.get_participants(namespace, room)
            return bool(list(participants))
        return False
    except Exception:
        return False


def send_push_notification(user_id, title, body, data=None):
    """
    Отправка FCM всем токенам пользователя.
    data — dict[str, str] для deep link (chat_id, task_id, kind, …).
    """
    from models import UserFcmToken

    if not init_firebase():
        return 0

    if is_user_socket_online(user_id):
        return 0

    tokens = [
        t.token
        for t in UserFcmToken.query.filter_by(user_id=int(user_id)).all()
        if t.token
    ]
    if not tokens:
        return 0

    try:
        from firebase_admin import messaging

        payload_data = {str(k): str(v) for k, v in (data or {}).items()}
        sent = 0
        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=str(title or 'GruzzExpert'),
                        body=str(body or ''),
                    ),
                    data=payload_data,
                    token=token,
                )
                messaging.send(message)
                sent += 1
            except Exception as exc:
                logger.warning('FCM send failed for user %s: %s', user_id, exc)
        return sent
    except Exception as exc:
        logger.exception('send_push_notification: %s', exc)
        return 0
