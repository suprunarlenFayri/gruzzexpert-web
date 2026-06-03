from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import uuid
from sqlalchemy import inspect, JSON, Index, select, event

from utils.datetime_utils import utc_iso, utc_now

db = SQLAlchemy()

class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utc_now, index=True)

    def to_dict(self):
        """
        Converts a SQLAlchemy model instance to a dictionary.
        Handles datetime objects (to ISO format) and JSON fields.
        """
        data = {}
        mapper = inspect(self.__class__)
        assert mapper is not None
        for column in mapper.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                data[column.name] = utc_iso(value)
            # Handle JSON fields explicitly if they are SQLAlchemy's JSON type
            elif isinstance(column.type, JSON):
                data[column.name] = value
            else:
                data[column.name] = value
        return data

# ========== ГЛОБАЛЬНЫЙ УРОВЕНЬ ==========

class User(BaseModel, UserMixin):
    __tablename__ = 'users'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    role = db.Column(db.String(20), default='user')
    email = db.Column(db.String(100), unique=True, nullable=True)
    tag = db.Column(db.String(50), unique=True, nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=True, index=True)
    send_by_enter = db.Column(db.Boolean, default=True, nullable=False)
    phone_privacy = db.Column(db.String(20), default='contacts', nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    favorite_cities = db.Column(db.JSON, default=list)  # Храним список ID городов

    # Список ID городов, к которым есть доступ (например: [1, 12, 45])
    # Если список пустой, исполнитель не видит ничего (или всё, как решишь)
    allowed_locations = db.Column(db.JSON, default=[])

    # Дополнительно: можно добавить поле для объектов/клиентов, если они в разных таблицах
    allowed_clients = db.Column(db.JSON, default=[])
    
    # Глобальная роль платформы (super_admin / user)
    platform_role = db.Column(db.String(20), default='user')

    current_desktop_token = db.Column(db.String(100), nullable=True)
    current_mobile_token = db.Column(db.String(100), nullable=True)
    
    # Статус верификации (галочка)
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True)  # ✅ ДОБАВЛЕНО: дата верификации
    
    # Рейтинг
    rating = db.Column(db.Float, default=0.0)  

    completed_tasks = db.Column(db.Integer, default=0)
    missed_tasks = db.Column(db.Integer, default=0)
    rating_auto = db.Column(db.Float, default=0.0)

    birth_date = db.Column(db.Date, nullable=True)
    bank_card = db.Column(db.String(512), nullable=True)
    settings = db.Column(db.JSON, nullable=True)
    tasks_muted_until = db.Column(db.DateTime, nullable=True)

    balance = db.Column(db.Float, default=0.0)
    is_frozen = db.Column(db.Boolean, default=False, nullable=False)
    frozen_until = db.Column(db.DateTime, nullable=True)

    # TOTP (Google Authenticator / Яндекс.Ключ) для входа создателя
    totp_secret = db.Column(db.String(512), nullable=True)

    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_assign_role(self, target_role):
        """Проверяет, может ли текущий пользователь назначать указанную роль"""
        role_hierarchy = {
            'creator': ['director', 'senior_dispatcher', 'dispatcher', 'manager', 'brigadir', 'worker', 'client'],
            'director': ['senior_dispatcher', 'dispatcher', 'manager', 'brigadir', 'worker', 'client'],
            'senior_dispatcher': ['dispatcher', 'manager', 'worker'],
            'dispatcher': ['worker'],
            'manager': ['worker'],
            'brigadir': ['worker'],
            'worker': [],
            'client': []
        }
        return target_role in role_hierarchy.get(self.role, [])

    @staticmethod
    def generate_uuid_filename(filename):
        """Генерирует уникальное имя файла на основе UUID, сохраняя расширение"""
        import uuid
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

    def update_auto_rating(self, success=True):
        """
        Пересчет автоматического рейтинга исполнителя после завершения заявки.
        Пока работает как безопасная заглушка, чтобы не блокировать флоу.
        В будущем здесь будет логика расчета на основе отзывов и выполненных задач.
        """
        pass

    def set_manual_rating(self, value):
        """Ручная установка рейтинга (0–10)."""
        self.rating = max(0.0, min(10.0, float(value)))


class UserBackupCode(BaseModel):
    """Одноразовые резервные коды входа создателя (GRZ-XXXX-XXXX)."""
    __tablename__ = 'user_backup_codes'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('backup_codes', lazy='dynamic'))


class UserDevice(BaseModel):
    """Запоминание доверенных устройств для b2b-ролей."""
    __tablename__ = 'user_devices'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    device_hash = db.Column(db.String(128), nullable=False, index=True)
    browser = db.Column(db.String(120), nullable=True)
    os = db.Column(db.String(120), nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    last_login = db.Column(db.DateTime, default=utc_now, nullable=True)
    is_trusted = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User', backref=db.backref('devices', lazy='dynamic'))


class UserSession(BaseModel):
    """Активные входы пользователя (устройства и токены сессии)."""
    __tablename__ = 'user_sessions'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    device_name = db.Column(db.String(200), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    last_active = db.Column(db.DateTime, default=utc_now, nullable=True)
    token = db.Column(db.String(100), nullable=False, index=True)

    user = db.relationship('User', backref=db.backref('login_sessions', lazy='dynamic'))


class PendingLoginAttempt(BaseModel):
    """Попытка входа с нового устройства (ожидает 2FA или заблокирована)."""
    __tablename__ = 'pending_login_attempts'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    attempt_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    device_hash = db.Column(db.String(128), nullable=False)
    browser = db.Column(db.String(120), nullable=True)
    os = db.Column(db.String(120), nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    sms_code = db.Column(db.String(10), nullable=True)
    email_code = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('login_attempts', lazy='dynamic'))


class SmsVerificationCode(BaseModel):
    """Временные SMS-коды (4 цифры) для входа и регистрации."""
    __tablename__ = 'sms_verification_codes'

    phone = db.Column(db.String(20), nullable=False, index=True)
    purpose = db.Column(db.String(20), nullable=False, index=True)
    session_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    consumed_at = db.Column(db.DateTime, nullable=True)


class UserFcmToken(BaseModel):
    """FCM-токены устройств для push-уведомлений."""
    __tablename__ = 'user_fcm_tokens'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = db.Column(db.String(512), unique=True, nullable=False, index=True)
    platform = db.Column(db.String(20), nullable=True)
    device_name = db.Column(db.String(120), nullable=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=True)

    user = db.relationship('User', backref=db.backref('fcm_tokens', lazy='dynamic'))


class PhoneRecoveryTicket(BaseModel):
    """Заявка на смену номера без доступа к старому телефону."""
    __tablename__ = 'phone_recovery_tickets'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    old_phone = db.Column(db.String(20), nullable=True)
    new_phone = db.Column(db.String(20), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True, index=True)

    user = db.relationship('User', foreign_keys=[user_id])


# ========== WORKSPACE (РАБОЧЕЕ ПРОСТРАНСТВО) ==========

class Workspace(BaseModel):
    __tablename__ = 'workspaces'
    
    name = db.Column(db.String(100), nullable=False)
    admin_limit = db.Column(db.Integer, default=5)
    expires_at = db.Column(db.DateTime, nullable=True)
    invite_key = db.Column(db.String(23), unique=True, nullable=True)
    share_token = db.Column(db.String(50), unique=True, nullable=True)
    invite_token = db.Column(db.String(100), unique=True, default=lambda: secrets.token_urlsafe(32))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    settings = db.Column(db.JSON, nullable=True)
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])


class WorkspaceMember(BaseModel):
    __tablename__ = 'workspace_members'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    role = db.Column(db.String(50), default='worker')  # owner / admin / dispatcher / brigadir / manager / sales_manager / worker / client
    joined_at = db.Column(db.DateTime, default=utc_now)
    
    user = db.relationship('User', foreign_keys=[user_id])
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'workspace_id', name='unique_user_workspace'),
    )
    

# ========== ВЕРИФИКАЦИЯ (АНКЕТА ИСПОЛНИТЕЛЯ) ==========

class VerificationRequest(BaseModel):
    __tablename__ = 'verification_requests'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    
    # Данные анкеты
    full_name = db.Column(db.String(512), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(512), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=True)
    experience = db.Column(db.Text, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    
    # Фото (хранятся под UUID именами)
    passport_photo = db.Column(db.String(512), nullable=False)
    selfie_photo = db.Column(db.String(512), nullable=False)
    
    # Статус модерации
    status = db.Column(db.String(20), default='pending', index=True)  # pending / approved / rejected
    moderated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    moderated_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Юридическое согласие при подаче анкеты
    is_legal_agreed = db.Column(db.Boolean, default=False, nullable=False)
    agreed_at = db.Column(db.DateTime, nullable=True)
    agreed_from_ip = db.Column(db.String(45), nullable=True)
    
    user = db.relationship('User', foreign_keys=[user_id])
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    city = db.relationship('City', foreign_keys=[city_id])
    moderated_by = db.relationship('User', foreign_keys=[moderated_by_id])

# ========== КЛИЕНТЫ И ОБЪЕКТЫ ==========

class Client(BaseModel):
    __tablename__ = 'clients'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(512), nullable=True)
    address = db.Column(db.Text, nullable=True)
    inn = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])

class WorkSite(BaseModel):
    __tablename__ = 'work_sites'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    client = db.relationship('Client', foreign_keys=[client_id])

class WorkerAccess(BaseModel):
    __tablename__ = 'worker_accesses'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True, index=True)
    worksite_id = db.Column(db.Integer, db.ForeignKey('work_sites.id'), nullable=True, index=True)
    granted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    worker = db.relationship('User', foreign_keys=[worker_id])
    client = db.relationship('Client', foreign_keys=[client_id])
    worksite = db.relationship('WorkSite', foreign_keys=[worksite_id])
    granted_by = db.relationship('User', foreign_keys=[granted_by_id])
    
    __table_args__ = (
        db.UniqueConstraint('worker_id', 'client_id', 'worksite_id', name='unique_worker_access'),
    )

# ========== ЗАЯВКИ ==========

class Task(BaseModel):
    __tablename__ = 'tasks'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True, index=True)
    worksite_id = db.Column(db.Integer, db.ForeignKey('work_sites.id'), nullable=True, index=True)
    
    task_number = db.Column(db.String(11), unique=True, nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='open', index=True)  # open / in_progress / done / cancelled
    required_workers = db.Column(db.Integer, default=1)
    
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    execution_date = db.Column(db.Date, nullable=True)
    execution_time = db.Column(db.Time, nullable=True)
    auto_chat = db.Column(db.Boolean, default=False)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=True)
    
    completed_at = db.Column(db.DateTime, nullable=True)
    
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    client = db.relationship('Client', foreign_keys=[client_id])
    worksite = db.relationship('WorkSite', foreign_keys=[worksite_id])
    city = db.relationship('City', foreign_keys=[city_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])
    assignments = db.relationship('TaskAssignment', back_populates='task', cascade='all, delete-orphan')
    
    def get_assigned_workers(self):
        """Исполнители, реально занявшие слот (не отклики/снятия/архив)."""
        active_statuses = {'assigned'}
        workers = []
        seen = set()
        for a in TaskAssignment.query.filter_by(task_id=self.id).all():
            if a.status not in active_statuses or not a.user:
                continue
            if a.user_id in seen:
                continue
            seen.add(a.user_id)
            workers.append(a.user)
        return workers
    
    def is_fully_assigned(self):
        return len(self.get_assigned_workers()) >= self.required_workers

    @property
    def creator_id(self):
        return self.created_by_id

    @classmethod
    def generate_task_number(cls, connection=None):
        """Генерирует уникальный 11-значный номер заявки."""
        for _ in range(100):
            number = ''.join(secrets.choice('0123456789') for _ in range(11))
            if connection is not None:
                mapper = inspect(cls)
                assert mapper is not None
                task_number_col = mapper.local_table.c.task_number
                exists = connection.execute(
                    select(task_number_col).where(task_number_col == number)
                ).first()
            else:
                exists = cls.query.filter_by(task_number=number).first()
            if not exists:
                return number
        raise RuntimeError('Не удалось сгенерировать уникальный номер заявки')


@event.listens_for(Task, 'before_insert')
def _assign_task_number(mapper, connection, target):
    if not target.task_number:
        target.task_number = Task.generate_task_number(connection)


class TaskAssignment(BaseModel):
    __tablename__ = 'task_assignments'
    
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), default='assigned', index=True)
    worker_status = db.Column(db.String(20), default='assigned', index=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_at = db.Column(db.DateTime, default=utc_now)
    completed_at = db.Column(db.DateTime, nullable=True)
    en_route_at = db.Column(db.DateTime, nullable=True)
    started_working_at = db.Column(db.DateTime, nullable=True)
    finished_working_at = db.Column(db.DateTime, nullable=True)
    route_reminder_stage = db.Column(db.Integer, default=0)
    route_deadline_at = db.Column(db.DateTime, nullable=True)
    
    task = db.relationship('Task', back_populates='assignments', foreign_keys=[task_id])
    user = db.relationship('User', foreign_keys=[user_id])
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])
    
    __table_args__ = (
        db.UniqueConstraint('task_id', 'user_id', name='unique_task_user'),
        db.Index('idx_task_assignments_task', 'task_id'),
        db.Index('idx_task_assignments_user', 'user_id'),
    )


# ========== ЧАТЫ ==========

class Chat(BaseModel):
    __tablename__ = 'chats'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True, index=True)  # ✅ nullable=True
    type = db.Column(db.String(20), default='private', index=True)  # private / group / task
    name = db.Column(db.String(100), nullable=True)
    is_group = db.Column(db.Boolean, default=False, nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    delete_at = db.Column(db.DateTime, nullable=True, index=True)
    
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    task = db.relationship('Task', foreign_keys=[task_id], backref='chat', uselist=False)
    
    @property
    def last_message(self):
        return Message.query.filter_by(chat_id=self.id).order_by(Message.created_at.desc()).first()
    
    def get_participants(self):
        return User.query.join(ChatParticipant).filter(ChatParticipant.chat_id == self.id).all()
    
    def get_other_participant(self, user):
        participants = self.get_participants()
        for p in participants:
            if p.id != user.id:
                return p
        return None

class ChatParticipant(BaseModel):
    __tablename__ = 'chat_participants'
    
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role = db.Column('role_in_chat', db.String(20), default='member')  # creator / admin / member
    last_read_at = db.Column(db.DateTime, default=utc_now)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    pinned_at = db.Column(db.DateTime, nullable=True)
    
    chat = db.relationship('Chat', backref='participants')
    user = db.relationship('User', backref='chat_participants')
    
    __table_args__ = (
        db.UniqueConstraint('chat_id', 'user_id', name='unique_chat_user'),
    )

    def is_admin(self):
        return self.role in ('creator', 'admin')


class Message(BaseModel):
    __tablename__ = 'messages'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True, index=True)  # ✅ nullable=True
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    text = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True, index=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    pinned_at = db.Column(db.DateTime, nullable=True)
    deleted_for_all = db.Column(db.Boolean, default=False, nullable=False)
    
    __table_args__ = (
        db.Index('idx_message_chat_created_at', 'chat_id', 'created_at'),
    )
    
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    chat = db.relationship('Chat', backref='messages')
    sender = db.relationship('User', backref='messages')
    parent = db.relationship('Message', remote_side='Message.id', foreign_keys=[parent_id])
    task = db.relationship('Task', foreign_keys=[task_id])

    def to_dict(self):
        data = super().to_dict()
        if data.get('text') is not None:
            from utils.crypto import decrypt_data
            data['text'] = decrypt_data(data['text'])
        return data

    @property
    def plaintext_text(self):
        from utils.crypto import decrypt_data
        return decrypt_data(self.text)

class Attachment(BaseModel):
    __tablename__ = 'attachments'
    
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    thumbnail_path = db.Column(db.String(500), nullable=True) 
    optimized_path = db.Column(db.String(500), nullable=True)
    
    message = db.relationship('Message', backref='attachments')

class ForwardedMessage(BaseModel):
    __tablename__ = 'forwarded_messages'
    
    original_message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False, index=True)
    new_message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False, index=True)
    comment = db.Column(db.Text, nullable=True)
    forwarded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    original_message = db.relationship('Message', foreign_keys=[original_message_id])
    new_message = db.relationship('Message', foreign_keys=[new_message_id])
    forwarded_by = db.relationship('User', foreign_keys=[forwarded_by_id])


# ========== ПРИГЛАШЕНИЯ ==========

class Invite(BaseModel):
    __tablename__ = 'invites'
    
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    email = db.Column(db.String(100), nullable=False)
    token = db.Column(db.String(100), unique=True, default=lambda: secrets.token_urlsafe(32))
    role = db.Column(db.String(50), default='worker')
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: utc_now() + timedelta(days=7))
    
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    
    def is_valid(self):
        return utc_now() < self.expires_at


# ========== КОНТАКТЫ ==========

class Contact(BaseModel):
    """Контакты пользователя (адресная книга для чатов и пересылки)."""
    __tablename__ = 'contacts'

    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    contact_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    owner = db.relationship('User', foreign_keys=[owner_id], backref='contacts_owned')
    contact_user = db.relationship('User', foreign_keys=[contact_user_id])

    __table_args__ = (
        db.UniqueConstraint('owner_id', 'contact_user_id', name='unique_user_contact'),
    )


class BlacklistEntry(BaseModel):
    """Чёрный список пользователя."""
    __tablename__ = 'blacklist'

    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    blocked_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    owner = db.relationship('User', foreign_keys=[owner_id], backref='blacklist_owned')
    blocked_user = db.relationship('User', foreign_keys=[blocked_user_id])

    __table_args__ = (
        db.UniqueConstraint('owner_id', 'blocked_user_id', name='unique_blacklist_entry'),
    )


class MessageHidden(BaseModel):
    """Сообщение скрыто только для конкретного пользователя."""
    __tablename__ = 'message_hidden'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)

    user = db.relationship('User', backref='hidden_messages')
    message = db.relationship('Message', backref='hidden_for_users')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'message_id', name='unique_message_hidden'),
    )


# ========== ЗАКРЕПЛЁННЫЕ ЭЛЕМЕНТЫ ==========

class PinnedItem(BaseModel):
    __tablename__ = 'pinned_items'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    item_type = db.Column(db.String(20), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    
    user = db.relationship('User', backref='pinned_items')
    workspace = db.relationship('Workspace', foreign_keys=[workspace_id])
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_type', 'item_id', name='unique_user_pin'),
    )


# ========== ГОРОДА (справочник) ==========

class City(BaseModel):
    __tablename__ = 'cities'
    
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    
    @staticmethod
    def get_defaults():
        """Возвращает полный список городов РФ (85+ городов)"""
        return [
            # Города федерального значения
            'Москва', 'Санкт-Петербург', 'Севастополь',
            
            # Центральный федеральный округ
            'Белгород', 'Брянск', 'Владимир', 'Воронеж', 'Иваново', 'Калуга',
            'Кострома', 'Курск', 'Липецк', 'Москва', 'Орёл', 'Рязань',
            'Смоленск', 'Тамбов', 'Тверь', 'Тула', 'Ярославль',
            
            # Северо-Западный федеральный округ
            'Архангельск', 'Вологда', 'Калининград', 'Петрозаводск',
            'Сыктывкар', 'Великий Новгород', 'Псков', 'Санкт-Петербург',
            'Мурманск', 'Северодвинск', 'Череповец',
            
            # Южный федеральный округ
            'Астрахань', 'Волгоград', 'Краснодар', 'Ростов-на-Дону',
            'Элиста', 'Майкоп', 'Нальчик', 'Владикавказ', 'Грозный',
            'Махачкала', 'Назрань', 'Черкесск', 'Ставрополь', 'Сочи',
            'Новороссийск', 'Таганрог', 'Шахты', 'Волжский', 'Батайск',
            
            # Приволжский федеральный округ
            'Уфа', 'Киров', 'Йошкар-Ола', 'Саранск', 'Нижний Новгород',
            'Оренбург', 'Пенза', 'Пермь', 'Самара', 'Саратов', 'Казань',
            'Ижевск', 'Ульяновск', 'Чебоксары', 'Тольятти', 'Набережные Челны',
            'Сызрань', 'Энгельс', 'Дзержинск', 'Орск', 'Стерлитамак',
            
            # Уральский федеральный округ
            'Курган', 'Екатеринбург', 'Тюмень', 'Ханты-Мансийск',
            'Челябинск', 'Магнитогорск', 'Нижний Тагил', 'Каменск-Уральский',
            'Златоуст', 'Миасс', 'Копейск', 'Сургут', 'Нижневартовск',
            'Нефтеюганск', 'Новый Уренгой', 'Ноябрьск',
            
            # Сибирский федеральный округ
            'Горно-Алтайск', 'Барнаул', 'Улан-Удэ', 'Чита', 'Иркутск',
            'Кемерово', 'Новокузнецк', 'Красноярск', 'Новосибирск', 'Омск',
            'Томск', 'Кызыл', 'Абакан', 'Прокопьевск', 'Бийск', 'Ангарск',
            'Братск', 'Норильск', 'Канск', 'Бердск', 'Искитим', 'Ленинск-Кузнецкий',
            'Междуреченск', 'Киселёвск', 'Юрга', 'Ачинск', 'Рубцовск',
            
            # Дальневосточный федеральный округ
            'Биробиджан', 'Благовещенск', 'Владивосток', 'Магадан',
            'Хабаровск', 'Южно-Сахалинск', 'Петропавловск-Камчатский',
            'Якутск', 'Уссурийск', 'Находка', 'Комсомольск-на-Амуре',
            'Артём', 'Арсеньев', 'Свободный', 'Дальнегорск', 'Большой Камень'
        ]