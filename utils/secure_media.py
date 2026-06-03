"""Зашифрованное хранение и безопасная выдача документов анкет."""

import logging
import mimetypes
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from utils.crypto import decrypt_data, decrypt_file, encrypt_data, encrypt_file, is_encrypted

logger = logging.getLogger(__name__)

VERIFICATION_DIR = 'verification'
MEDIA_GRANT_SESSION_KEY = 'verification_media_grants'
MEDIA_GRANT_TTL = timedelta(minutes=15)
MEDIA_TOKEN_SALT = 'gruzz-verification-media-v1'

MIME_BY_EXT = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
}


def _upload_root(app):
    return os.path.join(app.root_path, 'uploads', VERIFICATION_DIR)


def _media_token_serializer(app=None):
    app = app or current_app
    return URLSafeTimedSerializer(
        app.config['SECRET_KEY'],
        salt=MEDIA_TOKEN_SALT,
    )


def _guess_mime(path, data=None):
    ext = (path or '').rsplit('.', 1)[-1].lower().replace('enc', 'jpg')
    if ext in MIME_BY_EXT:
        return MIME_BY_EXT[ext]
    if data:
        if data[:3] == b'\xff\xd8\xff':
            return 'image/jpeg'
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
    guessed, _ = mimetypes.guess_type(path or '')
    return guessed or 'application/octet-stream'


def save_encrypted_verification_upload(file_storage, app):
    """
    Принимает FileStorage, шифрует содержимое, пишет на диск как .enc.
    В БД сохраняется encrypt_data(относительный путь).
    """
    if not file_storage or not file_storage.filename:
        return None
    raw_name = secure_filename(file_storage.filename)
    ext = raw_name.rsplit('.', 1)[-1].lower() if '.' in raw_name else 'jpg'
    if ext not in MIME_BY_EXT:
        return None
    file_bytes = file_storage.read()
    if not file_bytes:
        return None
    encrypted = encrypt_file(file_bytes)
    if not encrypted:
        return None
    os.makedirs(_upload_root(app), exist_ok=True)
    filename = f'{uuid.uuid4().hex}.enc'
    abs_path = os.path.join(_upload_root(app), filename)
    with open(abs_path, 'wb') as fh:
        fh.write(encrypted)
    relative = f'{VERIFICATION_DIR}/{filename}'
    return encrypt_data(relative)


def _resolve_storage_path(stored_value):
    if not stored_value:
        return None
    if is_encrypted(stored_value):
        return decrypt_data(stored_value)
    return str(stored_value)


def _normalize_relative_upload_path(relative):
    if not relative:
        return None
    rel = str(relative).replace('\\', '/').strip().lstrip('/')
    if rel.startswith('uploads/'):
        rel = rel[len('uploads/'):]
    if '..' in rel:
        return None
    return rel


def _candidate_abs_paths(relative, app):
    rel = _normalize_relative_upload_path(relative)
    if not rel:
        return []
    basename = os.path.basename(rel)
    candidates = [
        os.path.join(app.root_path, 'uploads', rel),
        os.path.join(app.root_path, 'uploads', VERIFICATION_DIR, basename),
        os.path.join(_upload_root(app), basename),
    ]
    seen = set()
    unique = []
    for path in candidates:
        norm = os.path.normpath(path)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique


_INVALID_STORED_NAMES = frozenset({
    '', '.', '..', 'null', 'none', 'undefined', 'passport.jpg', 'selfie.jpg',
})


def _is_meaningful_stored_path(stored_value):
    if stored_value is None:
        return False
    raw = str(stored_value).strip()
    if not raw or raw.lower() in _INVALID_STORED_NAMES:
        return False
    relative = _resolve_storage_path(stored_value)
    if not relative:
        return False
    rel = _normalize_relative_upload_path(relative)
    if not rel or rel.lower() in ('verification', 'verification/'):
        return False
    basename = os.path.basename(rel)
    if not basename or basename.lower() in _INVALID_STORED_NAMES:
        return False
    return True


def verification_file_exists(stored_path_value, app):
    """Проверяет, что файл анкеты реально есть на диске (legacy .jpg и .enc)."""
    if not _is_meaningful_stored_path(stored_path_value):
        return False
    relative = _resolve_storage_path(stored_path_value)
    for candidate in _candidate_abs_paths(relative, app):
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            return True
    return False


def find_verification_documents(user_id, app):
    """
    Ищет последнюю анкету с читаемыми файлами.
    Возвращает (VerificationRequest|None, list[dict]) с type/field/label.
    """
    from models import VerificationRequest

    reqs = (
        VerificationRequest.query.filter_by(user_id=int(user_id))
        .order_by(VerificationRequest.id.desc())
        .all()
    )
    doc_specs = (
        ('passport', 'passport_photo', 'Паспорт'),
        ('selfie', 'selfie_photo', 'Селфи'),
    )
    for req in reqs:
        found = []
        for doc_type, field, label in doc_specs:
            stored = getattr(req, field, None)
            if verification_file_exists(stored, app):
                found.append({'type': doc_type, 'field': field, 'label': label})
        if found:
            return req, found
    return None, []


def build_worker_verification_documents_payload(user_id, viewer_id, app, media_url_builder):
    """
    media_url_builder(req_id, doc_type) -> str
    """
    req, doc_items = find_verification_documents(user_id, app)
    if not req or not doc_items:
        return {
            'ok': True,
            'has_documents': False,
            'documents': [],
            'message': 'Документы не загружены',
        }

    documents = []
    for item in doc_items:
        token = issue_verification_media_token(viewer_id, req.id, item['type'], app)
        documents.append({
            'type': item['type'],
            'label': item['label'],
            'url': media_url_builder(token),
        })

    return {
        'ok': True,
        'has_documents': True,
        'documents': documents,
        'req_id': req.id,
    }


def read_verification_document(stored_path_value, app, debug_out=None):
    """Читает и расшифровывает документ. Возвращает (bytes, mime) или (None, None)."""
    relative = _resolve_storage_path(stored_path_value)
    if not relative:
        if debug_out is not None:
            debug_out['reason'] = 'empty_storage_path'
        return None, None

    checked_paths = _candidate_abs_paths(relative, app)
    if debug_out is not None:
        debug_out['relative'] = relative
        debug_out['checked_paths'] = checked_paths

    abs_path = None
    for candidate in checked_paths:
        if os.path.isfile(candidate):
            abs_path = candidate
            break

    if not abs_path:
        for candidate in checked_paths:
            if not os.path.exists(candidate):
                print('Файл не найден по пути:', candidate)
        if debug_out is not None:
            debug_out['reason'] = 'file_not_found'
            debug_out['exists'] = {p: os.path.exists(p) for p in checked_paths}
        return None, None

    if debug_out is not None:
        debug_out['resolved_path'] = abs_path
        debug_out['file_exists'] = True

    with open(abs_path, 'rb') as fh:
        raw = fh.read()

    if relative.endswith('.enc') or raw.startswith(b'GRZENC1'):
        plain = decrypt_file(raw)
        if plain is None:
            if debug_out is not None:
                debug_out['reason'] = 'decrypt_failed'
            return None, None
        return plain, _guess_mime(relative, plain)

    return raw, _guess_mime(relative, raw)


def _utc_timestamp():
    return datetime.utcnow().timestamp()


def _prune_expired_grants(grants):
    now = _utc_timestamp()
    cleaned = {}
    for token, grant in (grants or {}).items():
        raw_exp = grant.get('expires_at')
        if isinstance(raw_exp, (int, float)) and raw_exp < now:
            continue
        if isinstance(raw_exp, datetime):
            exp_ts = (
                raw_exp.astimezone(timezone.utc).timestamp()
                if raw_exp.tzinfo
                else raw_exp.timestamp()
            )
            if exp_ts < now:
                continue
        cleaned[token] = grant
    return cleaned


def issue_verification_media_token(user_id, req_id, doc_type, app=None):
    """Подписанный токен + дублирование в session для <img src>."""
    app = app or current_app
    payload = {
        'uid': int(user_id),
        'req_id': int(req_id),
        'doc': str(doc_type),
    }
    token = _media_token_serializer(app).dumps(payload)
    grants = _prune_expired_grants(session.get(MEDIA_GRANT_SESSION_KEY) or {})
    grants[token] = {
        **payload,
        'expires_at': _utc_timestamp() + MEDIA_GRANT_TTL.total_seconds(),
    }
    session[MEDIA_GRANT_SESSION_KEY] = grants
    session.modified = True
    return token


def _validate_session_media_grant(token, user_id):
    """Legacy: токен в server-side session (до подписанных URL)."""
    grants = session.get(MEDIA_GRANT_SESSION_KEY) or {}
    grant = grants.get(token)
    if not grant or int(grant.get('uid', 0)) != int(user_id):
        return None
    raw_exp = grant.get('expires_at')
    if isinstance(raw_exp, (int, float)) and raw_exp < datetime.utcnow().timestamp():
        return None
    if isinstance(raw_exp, datetime):
        exp_ts = (
            raw_exp.astimezone(timezone.utc).timestamp()
            if raw_exp.tzinfo
            else raw_exp.timestamp()
        )
        if exp_ts < datetime.utcnow().timestamp():
            return None
    return {
        'uid': int(grant.get('uid', 0)),
        'req_id': int(grant.get('req_id', 0)),
        'doc': grant.get('doc'),
    }


def validate_verification_media_grant(token, user_id, app=None):
    """Подписанный токен; fallback — session[MEDIA_GRANT_SESSION_KEY]."""
    app = app or current_app
    if not token:
        return None
    token = str(token).strip()
    try:
        data = _media_token_serializer(app).loads(
            token,
            max_age=int(MEDIA_GRANT_TTL.total_seconds()),
        )
        if int(data.get('uid', 0)) != int(user_id):
            return None
        return data
    except SignatureExpired:
        logger.warning('Verification media token expired')
    except BadSignature:
        pass
    return _validate_session_media_grant(token, user_id)


def clear_verification_media_grants_for_user(user_id):
    """Очистка media-токенов пользователя в session."""
    grants = _prune_expired_grants(session.get(MEDIA_GRANT_SESSION_KEY) or {})
    session[MEDIA_GRANT_SESSION_KEY] = {
        t: g for t, g in grants.items() if int(g.get('uid', 0)) != int(user_id)
    }
    session.modified = True


def debug_media_404(reason, **context):
    """Временная отладка в терминал перед отдачей 404."""
    print(f'[verification_media] 404: {reason}', file=sys.stderr)
    for key, value in context.items():
        print(f'  {key}: {value}', file=sys.stderr)


def migrate_plain_verification_files(app, verification_query):
    """Шифрует legacy-файлы на диске (.jpg и т.д.)."""
    from models import db

    changed = 0
    for req in verification_query:
        for field in ('passport_photo', 'selfie_photo'):
            stored = getattr(req, field, None)
            if not stored:
                continue
            relative = _resolve_storage_path(stored)
            if not relative or relative.endswith('.enc'):
                continue
            abs_path = None
            for candidate in _candidate_abs_paths(relative, app):
                if os.path.isfile(candidate):
                    abs_path = candidate
                    break
            if not abs_path:
                continue
            with open(abs_path, 'rb') as fh:
                raw = fh.read()
            if raw.startswith(b'GRZENC1'):
                continue
            encrypted = encrypt_file(raw)
            enc_name = f'{uuid.uuid4().hex}.enc'
            enc_path = os.path.join(_upload_root(app), enc_name)
            with open(enc_path, 'wb') as fh:
                fh.write(encrypted)
            try:
                os.remove(abs_path)
            except OSError:
                pass
            setattr(req, field, encrypt_data(f'{VERIFICATION_DIR}/{enc_name}'))
            changed += 1
    if changed:
        db.session.commit()
    return changed
