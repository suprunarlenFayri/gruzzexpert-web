import os
from datetime import datetime, timedelta

from models import db, Chat, ChatParticipant, Message, Task, PinnedItem, ForwardedMessage, Attachment


class TaskChatService:
    UPLOAD_FOLDER = 'uploads'

    @classmethod
    def ensure_task_group_chat(cls, task):
        """Создаёт групповой чат по заявке, если набор закрыт и включён auto_chat."""
        if not task or not task.auto_chat or not task.is_fully_assigned():
            return None

        if task.chat_id:
            chat = db.session.get(Chat, task.chat_id)
            if chat:
                cls._sync_participants(task, chat)
                return chat

        chat = Chat(
            type='task',
            name=f"Заявка: {task.title}",
            task_id=task.id,
            workspace_id=task.workspace_id,
        )
        db.session.add(chat)
        db.session.flush()

        cls._sync_participants(task, chat)
        task.chat_id = chat.id
        return chat

    @classmethod
    def _sync_participants(cls, task, chat):
        participant_ids = {task.created_by_id}
        for worker in task.get_assigned_workers():
            participant_ids.add(worker.id)

        existing_ids = {
            p.user_id for p in ChatParticipant.query.filter_by(chat_id=chat.id).all()
        }

        for user_id in participant_ids:
            if user_id not in existing_ids:
                db.session.add(ChatParticipant(chat_id=chat.id, user_id=user_id))

    @classmethod
    def schedule_chat_deletion(cls, chat, hours=24):
        """Планирует полное удаление чата через указанное количество часов."""
        if not chat:
            return None
        if chat.delete_at and chat.delete_at > datetime.utcnow():
            return chat

        chat.delete_at = datetime.utcnow() + timedelta(hours=hours)
        return chat

    @classmethod
    def purge_expired_chats(cls):
        """Удаляет все чаты, у которых наступило время delete_at."""
        expired = Chat.query.filter(
            Chat.delete_at.isnot(None),
            Chat.delete_at <= datetime.utcnow(),
        ).all()

        deleted_ids = []
        for chat in expired:
            if cls.delete_chat_completely(chat.id):
                deleted_ids.append(chat.id)

        if deleted_ids:
            db.session.commit()

        return deleted_ids

    @classmethod
    def delete_chat_completely(cls, chat_id):
        """Полностью удаляет чат, сообщения, вложения и связи."""
        chat = db.session.get(Chat, chat_id)
        if not chat:
            return False

        messages = Message.query.filter_by(chat_id=chat_id).all()
        message_ids = [message.id for message in messages]

        for message in messages:
            for attachment in message.attachments:
                cls._remove_attachment_files(attachment)

        if message_ids:
            ForwardedMessage.query.filter(
                (ForwardedMessage.original_message_id.in_(message_ids))
                | (ForwardedMessage.new_message_id.in_(message_ids))
            ).delete(synchronize_session=False)

        Message.query.filter_by(chat_id=chat_id).delete(synchronize_session=False)
        ChatParticipant.query.filter_by(chat_id=chat_id).delete(synchronize_session=False)
        PinnedItem.query.filter_by(item_type='chat', item_id=chat_id).delete(synchronize_session=False)

        for task in Task.query.filter_by(chat_id=chat_id).all():
            task.chat_id = None

        db.session.delete(chat)
        return True

    @classmethod
    def _remove_attachment_files(cls, attachment):
        for path in (attachment.file_path, attachment.thumbnail_path, attachment.optimized_path):
            if not path:
                continue
            full_path = os.path.join(cls.UPLOAD_FOLDER, os.path.basename(str(path)))
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError:
                    pass
