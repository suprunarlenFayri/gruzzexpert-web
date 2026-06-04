from datetime import datetime
import os
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask import Flask, current_app, redirect, url_for, jsonify, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required, logout_user
from flask_socketio import emit, join_room, leave_room
from socketio_instance import socketio
from config import Config
from flask_cors import CORS
from models import db, User, PinnedItem, Chat, Task, ChatParticipant, Message
from flask import send_from_directory
from services.chat_service import ChatService
from utils.media_urls import avatar_url_for
from utils.datetime_utils import (
    chat_date_separator_label,
    format_local_date,
    format_local_datetime,
    format_local_time,
    local_date_key,
    utc_iso,
    utc_now,
)

load_dotenv()

login_manager = LoginManager()
#socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB (видео в чатах)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
    app.config['JSON_AS_ASCII'] = False

    cors_origins = os.getenv('CORS_ORIGINS', '*')
    if cors_origins.strip() == '*':
        CORS(app, resources={r'/api/*': {'origins': '*'}, r'/socket.io/*': {'origins': '*'}}, supports_credentials=True)
    else:
        origins = [o.strip() for o in cors_origins.split(',') if o.strip()]
        CORS(app, resources={r'/api/*': {'origins': origins}, r'/socket.io/*': {'origins': origins}}, supports_credentials=True)

    if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('postgresql'):
        engine_opts = dict(app.config.get('SQLALCHEMY_ENGINE_OPTIONS') or {})
        connect_args = dict(engine_opts.get('connect_args') or {})
        connect_args.setdefault('client_encoding', 'utf8')
        engine_opts['connect_args'] = connect_args
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_opts
    
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    socketio.init_app(app, async_mode=os.getenv('SOCKETIO_ASYNC_MODE', 'threading'))
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def authenticate_mobile_api_token():
        """Bearer / X-Session-Token для JSON API с веб-роутов (Flutter)."""
        if current_user.is_authenticated:
            return None
        path = request.path or ''
        if not (
            path.startswith('/api/mobile/')
            or path.startswith('/api/task')
            or path.startswith('/api/tasks/')
            or path.startswith('/chat/') and path.endswith('/messages')
        ):
            return None
        from utils.mobile_auth import resolve_mobile_user
        from flask_login import login_user

        user = resolve_mobile_user()
        if user:
            login_user(user)
        return None

    @app.before_request
    def validate_device_session():
        path = request.path or ''

        if path.startswith('/static/'):
            return None
        if '/socket.io/' in path:
            return None
        if path.startswith('/uploads/'):
            return None
        if path.startswith('/api/mobile/'):
            return None
        if path.startswith('/api/task') or path.startswith('/api/tasks/'):
            return None
        if request.endpoint in (
            'auth.login',
            'auth.register',
            'auth.logout',
            'auth.join_via_share_token',
            'auth.verify_login_2fa',
            'auth.check_tag',
            'auth.creator_totp_setup',
            'auth.creator_login_check',
            'auth.sms_send',
            'auth.sms_verify',
        ):
            return None

        if not current_user.is_authenticated:
            return None

        from utils.workspace_utils import is_platform_admin, resolve_workspace_id

        if is_platform_admin(current_user):
            resolve_workspace_id(current_user)

        session_token = session.get('session_token')
        device_type = session.get('device_type', 'desktop')
        db_token = (
            current_user.current_mobile_token
            if device_type == 'mobile'
            else current_user.current_desktop_token
        )

        if not session_token or db_token != session_token:
            logout_user()
            session.clear()
            flash('Вы вошли в аккаунт на другом устройстве этого типа. Сессия завершена')
            return redirect(url_for('auth.login'))

        return None
    
    @app.context_processor
    def inject_user_settings():
        from utils.user_settings import (
            DEFAULT_USER_SETTINGS,
            clear_expired_task_mute,
            get_user_settings,
            is_user_tasks_muted,
            is_worker_role,
            tasks_muted_until_iso,
        )
        from utils.user_profiles import header_role_label
        if current_user.is_authenticated:
            clear_expired_task_mute(current_user)
            return {
                'current_user_settings': get_user_settings(current_user),
                'current_user_is_worker': is_worker_role(current_user),
                'current_user_tasks_muted_until': tasks_muted_until_iso(current_user),
                'current_user_tasks_muted_active': is_user_tasks_muted(current_user),
                'current_user_header_role': header_role_label(current_user),
            }
        return {
            'current_user_settings': DEFAULT_USER_SETTINGS,
            'current_user_is_worker': False,
            'current_user_tasks_muted_until': None,
            'current_user_tasks_muted_active': False,
            'current_user_header_role': '',
        }
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('tasks.tasks_list'))
        return redirect(url_for('auth.login'))
    
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        norm = str(filename or '').replace('\\', '/').lstrip('/')
        if norm.startswith('verification/'):
            abort(403)
        return send_from_directory('uploads', filename)

    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/uploads/'):
            # Агрессивное кэширование на 1 год + immutable
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['Expires'] = 'Thu, 31 Dec 2030 23:59:59 GMT'
            response.headers['Vary'] = 'Accept-Encoding'
        return response
    
    # === ФИЛЬТР ДЛЯ НОРМАЛИЗАЦИИ ПУТЕЙ К ЗАГРУЖЕННЫМ ФАЙЛАМ ===
    # Предотвращает /uploads/uploads/ путем извлечения только имени файла
    @app.template_filter('normalize_upload')
    def normalize_upload_path(path):
        """Приводит путь к basename для использования с url_for('uploaded_file')"""
        if not path:
            return ''
        # Извлекаем только имя файла, убирая любые префиксы uploads/
        basename = os.path.basename(str(path))
        if basename.startswith('uploads/'):
            basename = basename[8:]
        return basename

    @app.template_filter('avatar_url')
    def avatar_url_filter(user):
        """Корректный URL аватарки: uploads/avatars/… через uploaded_file."""
        if user is None:
            return ''
        path = getattr(user, 'avatar', None) or getattr(user, 'avatar_url', None)
        if not path:
            return ''
        path = str(path).replace('\\', '/').strip()
        for prefix in ('/static/uploads/', 'static/uploads/', '/uploads/', 'uploads/'):
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        if '/' not in path:
            path = f'avatars/{path}'
        return url_for('uploaded_file', filename=path)

    @app.template_filter('format_local_time')
    def format_local_time_filter(value, fmt='%H:%M'):
        return format_local_time(value, fmt)

    @app.template_filter('format_local_datetime')
    def format_local_datetime_filter(value, fmt='%d.%m.%Y %H:%M'):
        return format_local_datetime(value, fmt)

    @app.template_filter('format_local_date')
    def format_local_date_filter(value, fmt='%d.%m.%Y'):
        return format_local_date(value, fmt)

    @app.template_filter('local_date_key')
    def local_date_key_filter(value):
        return local_date_key(value)

    @app.template_filter('chat_date_separator')
    def chat_date_separator_filter(value):
        return chat_date_separator_label(value)

    @app.template_filter('decrypt_field')
    def decrypt_field_filter(value):
        from utils.crypto import decrypt_data
        return decrypt_data(value)

    @app.template_global()
    def worker_task_tracking(task):
        from flask_login import current_user
        from routes.tasks import get_task_tracking_for_user
        if not current_user.is_authenticated:
            return None
        return get_task_tracking_for_user(task, current_user)
    
    @app.route('/pin/<type>/<int:id>', methods=['POST'])
    @login_required
    def toggle_pin(type, id):
        if type not in ['chat', 'task']:
            return jsonify({'error': 'Invalid type'}), 400
        
        existing = PinnedItem.query.filter_by(
            user_id=current_user.id,
            item_type=type,
            item_id=id
        ).first()
        
        if existing:
            db.session.delete(existing)
            is_pinned = False
        else:
            pin = PinnedItem(user_id=current_user.id, item_type=type, item_id=id)
            db.session.add(pin)
            is_pinned = True
        
        db.session.commit()
        return jsonify({'pinned': is_pinned}), 200
    
    @app.route('/unpin/<type>/<int:id>', methods=['POST'])
    @login_required
    def unpin_item(type, id):
        item = PinnedItem.query.filter_by(
            user_id=current_user.id,
            item_type=type,
            item_id=id
        ).first()
        if item:
            db.session.delete(item)
            db.session.commit()
        return '', 200
    
    @app.context_processor
    def inject_pinned():
        if current_user.is_authenticated:
            pinned_chats = []
            pinned_tasks = []
            pinned_tasks_ids = []
            
            pinned_items = PinnedItem.query.filter_by(user_id=current_user.id).all()
            for item in pinned_items:
                if item.item_type == 'chat':
                    chat = Chat.query.get(item.item_id)
                    if chat:
                        pinned_chats.append(chat)
                elif item.item_type == 'task':
                    task = Task.query.get(item.item_id)
                    if task:
                        pinned_tasks.append(task)
                        pinned_tasks_ids.append(task.id)
            
            return dict(pinned_chats=pinned_chats, pinned_tasks=pinned_tasks, pinned_tasks_ids=pinned_tasks_ids)
        return dict(pinned_chats=[], pinned_tasks=[], pinned_tasks_ids=[])

    @app.context_processor
    def inject_chat_contacts():
        if current_user.is_authenticated:
            return {
                'all_users': User.query.filter(User.id != current_user.id).order_by(User.name).all()
            }
        return {'all_users': []}
    
    # Регистрация blueprint'ов
    from routes.auth import auth_bp
    from routes.tasks import tasks_bp
    from routes.chats import chats_bp
    from routes.profile import profile_bp
    from routes.admin import admin_bp
    from routes.statistics import statistics_bp
    from routes.worker import worker_bp
    from routes.settings import settings_bp
    from routes.security import security_bp
    from routes.social import social_bp
    from routes.mobile_api import mobile_api_bp
    from routes.worker_api import worker_api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(mobile_api_bp)
    app.register_blueprint(worker_api_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(chats_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(social_bp)

    if not os.getenv('SKIP_BACKGROUND_WORKERS'):
        from services.chat_cleanup import start_chat_cleanup_worker, purge_expired_chats_once
        from services.task_timer_service import start_task_timer_worker
        purge_expired_chats_once(app)
        start_chat_cleanup_worker(app)
        start_task_timer_worker(app)

    with app.app_context():
        try:
            from utils.app_bootstrap import run_startup_bootstrap
            run_startup_bootstrap()
        except Exception:
            pass
        try:
            from utils.push_notifications import init_firebase
            init_firebase()
        except Exception:
            pass
    
    return app

# ===== SOCKET.IO СОБЫТИЯ =====

@socketio.on('connect')
def handle_connect(auth=None):
    """Пользователь подключился"""
    print(f'Client connected: {request.sid}')
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        if current_user.workspace_id:
            join_room(f'workspace_{current_user.workspace_id}')
        from routes.admin import join_user_moderation_rooms
        join_user_moderation_rooms(current_user, join_room)
        emit('connected', {'user': current_user.name})

@socketio.on('disconnect')
def handle_disconnect():
    """Пользователь отключился"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('join_chat')
def handle_join_chat(data):
    """Подключение к комнате чата"""
    chat_id = data.get('chat_id')
    if chat_id:
        room = f'chat_{chat_id}'
        join_room(room)
        print(f'User joined chat room: {room}')
        emit('user_joined', {'message': 'User joined the chat'}, room=room, include_self=False)

@socketio.on('leave_chat')
def handle_leave_chat(data):
    """Выход из комнаты чата"""
    chat_id = data.get('chat_id')
    if chat_id:
        room = f'chat_{chat_id}'
        leave_room(room)
        print(f'User left chat room: {room}')

@socketio.on('send_message')
def handle_send_message(data):
    """Отправка сообщения в реальном времени (текст + файлы)"""
    try:
        chat_id = data.get('chat_id')
        message_text = data.get('message', '').strip()
        attachments_data = data.get('attachments', [])  # Файлы в base64
        parent_id = data.get('parent_id')

        if parent_id in ['', 'null', 'None', None]:
            parent_id = None
        else:
            try:
                parent_id = int(parent_id)
            except (ValueError, TypeError):
                parent_id = None
        
        if not current_user.is_authenticated:
            emit('message_error', {'error': 'User not authenticated'}, room=request.sid)
            return

        if not chat_id:
            return
        
        message_dict = ChatService.send_message(
            chat_id=chat_id,
            sender_id=current_user.id,
            text=message_text,
            attachments=attachments_data,
            parent_id=parent_id,
        )

        if message_dict:
            room = f'chat_{chat_id}'
            emit_payload = {
                'id': message_dict['id'],
                'message': message_dict['text'],
                'author': current_user.name,
                'author_id': current_user.id,
                'sender_id': current_user.id,
                'author_name': current_user.name,
                'sender_name': current_user.name,
                'avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
                'sender_avatar': avatar_url_for(current_user, lambda p: url_for('uploaded_file', filename=p)),
                'attachments': message_dict['attachments'],
                'parent_id': parent_id,
                'created_at': message_dict['created_at'],
            }
            if parent_id:
                parent_msg = Message.query.get(parent_id)
                if parent_msg:
                    emit_payload['parent_author_name'] = parent_msg.sender.name if parent_msg.sender else 'Пользователь'
                    emit_payload['parent_text'] = parent_msg.plaintext_text

            emit('receive_message', emit_payload, room=room)

            from services.notification_service import notify_chat_message
            notify_chat_message(chat_id, current_user.id, emit_payload)
        
    except Exception as e:
        print(f'Error sending message: {e}')
        emit('message_error', {'error': str(e)}, room=request.sid)

# Добавляем событие для уведомления о новых файлах
@socketio.on('file_uploaded')
def handle_file_uploaded(data):
    """Уведомление о загрузке файлов"""
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    files = data.get('files', [])
    
    room = f'chat_{chat_id}'
    emit('new_attachments', {
        'message_id': message_id,
        'files': files,
        'author_id': current_user.id,
        'created_at': utc_iso(utc_now()),
    }, room=room)

@socketio.on('new_message')
def handle_new_message(data):
    """Отправка уведомления о новом сообщении"""
    chat_id = data.get('chat_id')
    message = data.get('message')
    author_name = data.get('author_name')
    
    room = f'chat_{chat_id}'
    emit('new_message', {
        'message': message,
        'author_name': author_name
    }, room=room, include_self=False)

@socketio.on('typing')
def handle_typing(data):
    """Пользователь печатает..."""
    if not current_user.is_authenticated:
        return

    from models import Chat

    chat_id = data.get('chat_id')
    is_typing = data.get('is_typing', False)

    if not chat_id:
        return

    payload = {
        'chat_id': chat_id,
        'user_id': current_user.id,
        'user_name': current_user.name,
        'is_typing': is_typing,
    }

    room = f'chat_{chat_id}'
    emit('user_typing', payload, room=room, include_self=False)

    chat = Chat.query.get(chat_id)
    if chat:
        for participant in chat.get_participants():
            if participant.id != current_user.id:
                emit('chat_typing', payload, room=f'user_{participant.id}')


@socketio.on('mark_as_read')
def handle_mark_as_read(data):
    """Входящие сообщения в чате помечены прочитанными текущим пользователем."""
    if not current_user.is_authenticated:
        return
    chat_id = data.get('chat_id')
    if not chat_id:
        return

    if ChatService.mark_messages_as_read(chat_id, current_user.id):
        room = f'chat_{chat_id}'
        emit(
            'messages_marked_read',
            {'chat_id': chat_id, 'reader_id': current_user.id},
            room=room,
        )


@socketio.on('join_task_room')
def handle_join_task_room(data):
    """Подключение к комнате заявки"""
    task_id = data.get('task_id')
    if task_id:
        room = f'task_{task_id}'
        join_room(room)
        print(f'User joined task room: {room}')

@socketio.on('task_taken')
def handle_task_taken(data):
    """Кто-то взял заявку"""
    task_id = data.get('task_id')
    if task_id:
        room = f'task_{task_id}'
        emit('task_status_update', {
            'task_id': task_id,
            'status': 'in_progress',
            'user': current_user.name
        }, room=room)

@socketio.on('task_completed')
def handle_task_completed(data):
    """Заявка завершена"""
    task_id = data.get('task_id')
    if task_id:
        room = f'task_{task_id}'
        emit('task_status_update', {
            'task_id': task_id,
            'status': 'done',
            'user': current_user.name
        }, room=room)

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Таблицы успешно созданы!")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)