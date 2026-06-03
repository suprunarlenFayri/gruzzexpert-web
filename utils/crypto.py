"""Симметричное шифрование полей и файлов (Fernet / AES-256)."""

import base64
import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

ENCRYPTED_PREFIX = 'enc:'
FILE_ENCRYPTED_MAGIC = b'GRZENC1'


def _resolve_key_from_env():
    """Ключ только из .env: ENCRYPTION_KEY или FIELD_ENCRYPTION_KEY (legacy)."""
    key = (os.getenv('ENCRYPTION_KEY') or os.getenv('FIELD_ENCRYPTION_KEY') or '').strip()
    if not key:
        raise RuntimeError(
            'ENCRYPTION_KEY is not set in .env. '
            'Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    if isinstance(key, str):
        key = key.encode('utf-8')
    return key


def _load_key():
    from flask import current_app

    key = current_app.config.get('ENCRYPTION_KEY') or current_app.config.get('FIELD_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('ENCRYPTION_KEY is not configured in application')
    if isinstance(key, str):
        key = key.encode('utf-8')
    return key


@lru_cache(maxsize=1)
def _fernet_for_key(key_bytes):
    return Fernet(key_bytes)


def _fernet():
    return _fernet_for_key(_load_key())


def encrypt_data(text):
    """Шифрует строку для хранения в БД."""
    if text is None:
        return None
    value = str(text)
    if not value:
        return value
    if value.startswith(ENCRYPTED_PREFIX):
        return value
    token = _fernet().encrypt(value.encode('utf-8')).decode('ascii')
    return ENCRYPTED_PREFIX + token


def decrypt_data(cipher_text):
    """Расшифровывает строку; legacy plaintext возвращает как есть."""
    if cipher_text is None:
        return None
    value = str(cipher_text)
    if not value:
        return value
    if not value.startswith(ENCRYPTED_PREFIX):
        return value
    token = value[len(ENCRYPTED_PREFIX):].encode('ascii')
    try:
        return _fernet().decrypt(token).decode('utf-8')
    except InvalidToken:
        logger.warning('Failed to decrypt field value')
        return None


def is_encrypted(value):
    return bool(value) and str(value).startswith(ENCRYPTED_PREFIX)


def encrypt_file(file_bytes):
    """Шифрует бинарные данные (фото документов). Возвращает bytes с magic-header."""
    if file_bytes is None:
        return None
    if isinstance(file_bytes, str):
        file_bytes = file_bytes.encode('utf-8')
    payload = _fernet().encrypt(bytes(file_bytes))
    return FILE_ENCRYPTED_MAGIC + payload


def decrypt_file(blob):
    """Расшифровывает blob, сохранённый через encrypt_file."""
    if blob is None:
        return None
    data = bytes(blob)
    if data.startswith(FILE_ENCRYPTED_MAGIC):
        token = data[len(FILE_ENCRYPTED_MAGIC):]
        return _fernet().decrypt(token)
    try:
        return _fernet().decrypt(data)
    except InvalidToken:
        logger.warning('Failed to decrypt file blob')
        return None


def encrypt_file_base64(file_bytes):
    """Base64 для передачи в JSON (кратковременный просмотр)."""
    encrypted = encrypt_file(file_bytes)
    if encrypted is None:
        return None
    return base64.b64encode(encrypted).decode('ascii')


def decrypt_file_base64(encoded):
    if not encoded:
        return None
    return decrypt_file(base64.b64decode(encoded.encode('ascii')))
