import os
import base64
from datetime import datetime
from flask import current_app
from utils.crypto import encrypt_data
from utils.datetime_utils import utc_now
from models import db, Message, Attachment, ChatParticipant, User
from socketio_instance import send_update
from PIL import Image  # pyright: ignore[reportMissingImports]
from io import BytesIO

class ChatService:
    IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif', 'gif', 'webp'}
    VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm', 'm4v', 'mkv', 'mpeg', 'mpg', '3gp'}
    ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS).union(
        {'pdf', 'doc', 'docx', 'xls', 'xlsx'}
    )
    UPLOAD_FOLDER = 'uploads' # Определяем здесь для удобства

    @staticmethod
    def allowed_file(filename, mimetype=None):
        if filename and '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            if ext in ChatService.ALLOWED_EXTENSIONS:
                return True
        if mimetype:
            mt = mimetype.lower()
            if mt.startswith('image/') or mt.startswith('video/'):
                return True
        return False

    @staticmethod
    def resolve_file_type(filename, mimetype=None, hinted_type=None):
        if hinted_type in ('image', 'video', 'file'):
            return hinted_type
        ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else ''
        if ext in ChatService.IMAGE_EXTENSIONS or (mimetype and mimetype.startswith('image/')):
            return 'image'
        if ext in ChatService.VIDEO_EXTENSIONS or (mimetype and mimetype.startswith('video/')):
            return 'video'
        return 'file'

    @staticmethod
    def _process_image(file_data, unique_filename, upload_path):
        """
        Обрабатывает изображение: создает миниатюру и оптимизированную версию.
        Возвращает пути к миниатюре, оптимизированной версии и оригиналу (относительно UPLOAD_FOLDER).
        """
        try:
            img = Image.open(BytesIO(file_data))
            original_ext = unique_filename.rsplit('.', 1)[1].lower()

            # Пути для сохранения
            base_name = unique_filename.rsplit('.', 1)[0]
            # Для jfif/jpeg/jpg генерируем производные в .jpg для совместимости Pillow
            derived_ext = 'jpg' if original_ext in {'jpg', 'jpeg', 'jfif'} else original_ext
            thumbnail_filename = f"{base_name}_thumb.{derived_ext}"
            optimized_filename = f"{base_name}_opt.{derived_ext}"
            
            original_full_path = os.path.join(upload_path, unique_filename)
            thumb_full_path = os.path.join(upload_path, thumbnail_filename)
            opt_full_path = os.path.join(upload_path, optimized_filename)

            # Сохраняем оригинал байтово, чтобы не падать на специфичных форматах
            with open(original_full_path, 'wb') as f:
                f.write(file_data)

            # Для JPEG/JFIF режим должен быть RGB
            if derived_ext == 'jpg' and img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            save_kwargs = {'quality': 85}
            if derived_ext == 'jpg':
                save_kwargs['format'] = 'JPEG'

            # Создание миниатюры (макс. 400px по ширине, качество 75%)
            thumb_width = 400
            thumb_img = img.copy()
            if thumb_img.width > thumb_width:
                thumb_img.thumbnail((thumb_width, int((thumb_width / thumb_img.width) * thumb_img.height)), Image.Resampling.LANCZOS)
            thumb_kwargs = dict(save_kwargs)
            thumb_kwargs['quality'] = 75
            thumb_img.save(thumb_full_path, **thumb_kwargs)
            
            # Создание оптимизированной версии (если оригинал > 1600px, качество 85%)
            optimized_width = 1600
            opt_img = img.copy()
            if opt_img.width > optimized_width:
                opt_img.thumbnail((optimized_width, int((optimized_width / opt_img.width) * opt_img.height)), Image.Resampling.LANCZOS)
            opt_img.save(opt_full_path, **save_kwargs)

            return (
                f"{thumbnail_filename}",
                f"{optimized_filename}",
                f"{unique_filename}"
            )
        except Exception as e:
            print(f"Error processing image: {e}")
            return None, None, None

    @staticmethod
    def send_message(chat_id, sender_id, text, attachments=None, parent_id=None):
        return ChatService.save_message(
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            attachments_data=attachments,
            parent_id=parent_id,
        )

    @staticmethod
    def save_message(chat_id, sender_id, text, attachments_data=None, parent_id=None):
        if attachments_data is None:
            attachments_data = []

        if not text and not attachments_data:
            return None

        message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            text=encrypt_data(text) if text else text,
            parent_id=parent_id,
        )
        db.session.add(message)
        db.session.flush()

        saved_attachments = []
        
        upload_path = os.path.join(current_app.root_path, ChatService.UPLOAD_FOLDER)
        os.makedirs(upload_path, exist_ok=True)

        for att in attachments_data:
            raw = att.get('data')
            if isinstance(raw, (bytes, bytearray)):
                file_data = bytes(raw)
            else:
                file_data = base64.b64decode(raw)
            filename = att['filename']
            file_type = ChatService.resolve_file_type(
                filename,
                att.get('mimetype'),
                att.get('file_type'),
            )

            if '.' in filename:
                name_parts = filename.rsplit('.', 1)
                unique_filename = f"{datetime.utcnow().timestamp()}_{name_parts[0]}.{name_parts[1]}"
            else:
                unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"
            
            thumbnail_path = None
            optimized_path = None
            original_file_path = f"{unique_filename}"

            if file_type == 'image':
                thumb_p, opt_p, orig_p = ChatService._process_image(file_data, unique_filename, upload_path)
                if thumb_p and opt_p and orig_p:
                    thumbnail_path = thumb_p
                    optimized_path = opt_p
                    original_file_path = orig_p
                else:
                    # Если обработка изображения не удалась, сохраняем оригинал как есть
                    with open(os.path.join(upload_path, unique_filename), 'wb') as f:
                        f.write(file_data)
            else:
                # Для не-изображений сохраняем файл как есть
                with open(os.path.join(upload_path, unique_filename), 'wb') as f:
                    f.write(file_data)
            
            attachment = Attachment(
                message_id=message.id,
                filename=filename,
                file_path=original_file_path,
                file_type=file_type,
                file_size=len(file_data),
                thumbnail_path=thumbnail_path,
                optimized_path=optimized_path
            )
            db.session.add(attachment)
            saved_attachments.append(attachment.to_dict())

        db.session.commit()
        
        sender = User.query.get(sender_id)
        message_dict = message.to_dict()
        message_dict['sender_name'] = sender.name if sender else 'Unknown'
        message_dict['attachments'] = saved_attachments

        return message_dict

    @staticmethod
    def get_unread_count(chat_id, user_id):
        participant = ChatParticipant.query.filter_by(
            chat_id=chat_id,
            user_id=user_id,
        ).first()
        if not participant:
            return 0

        query = Message.query.filter(
            Message.chat_id == chat_id,
            Message.sender_id != user_id,
        )
        if participant.last_read_at:
            query = query.filter(Message.created_at > participant.last_read_at)
        return query.count()

    @staticmethod
    def attach_unread_counts(chats, user_id):
        if not chats:
            return chats
        for chat in chats:
            chat.unread_count = ChatService.get_unread_count(chat.id, user_id)
        return chats

    @staticmethod
    def mark_messages_as_read(chat_id, user_id):
        messages_to_mark = Message.query.filter(
            Message.chat_id == chat_id,
            Message.sender_id != user_id,
            Message.is_read == False
        )
        for msg in messages_to_mark:
            msg.is_read = True

        participant = ChatParticipant.query.filter_by(
            chat_id=chat_id,
            user_id=user_id,
        ).first()
        if participant:
            participant.last_read_at = utc_now()

        db.session.commit()
        return True
