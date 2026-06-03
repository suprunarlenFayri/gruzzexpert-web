import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _resolve_encryption_key():
    from utils.crypto import _resolve_key_from_env
    return _resolve_key_from_env()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENCRYPTION_KEY = _resolve_encryption_key()
    FIELD_ENCRYPTION_KEY = ENCRYPTION_KEY