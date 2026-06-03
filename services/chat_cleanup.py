import threading
import time

from models import db
from services.task_chat_service import TaskChatService


def start_chat_cleanup_worker(app, interval_seconds=300):
    """Фоновый поток: каждые N секунд удаляет чаты с наступившим delete_at."""
    def worker():
        while True:
            time.sleep(interval_seconds)
            try:
                with app.app_context():
                    TaskChatService.purge_expired_chats()
            except Exception as exc:
                print(f'Chat cleanup error: {exc}')

    thread = threading.Thread(target=worker, daemon=True, name='chat-cleanup')
    thread.start()


def purge_expired_chats_once(app):
    with app.app_context():
        try:
            deleted = TaskChatService.purge_expired_chats()
            if deleted:
                print(f'Purged expired chats: {deleted}')
        except Exception as exc:
            print(f'Chat cleanup skipped (run migration): {exc}')
