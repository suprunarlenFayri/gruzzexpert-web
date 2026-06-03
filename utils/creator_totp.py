"""TOTP и резервные коды для входа создателя платформы."""

import re
import secrets
from urllib.parse import quote

import pyotp
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, User, UserBackupCode
from utils.crypto import decrypt_data, encrypt_data
from utils.datetime_utils import utc_now

TOTP_ISSUER = 'GruzzExpert'
BACKUP_CODE_PATTERN = re.compile(r'^GRZ-[A-Z0-9]{4}-[A-Z0-9]{4}$')
BACKUP_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def is_creator_account(user):
    if not user:
        return False
    if (user.phone or '').strip():
        return False
    return (
        getattr(user, 'platform_role', None) == 'super_admin'
        or (user.role or '') == 'creator'
    )


def creator_email_requires_totp(email):
    if not email:
        return False
    user = User.query.filter_by(email=email.strip().lower()).first()
    return bool(user and is_creator_account(user) and user.totp_secret)


def generate_backup_code():
    part = lambda: ''.join(secrets.choice(BACKUP_ALPHABET) for _ in range(4))
    return f'GRZ-{part()}-{part()}'


def normalize_backup_code(raw):
    if not raw:
        return ''
    code = str(raw).strip().upper().replace(' ', '')
    return code


def normalize_totp_code(raw):
    if raw is None:
        return ''
    return re.sub(r'\D', '', str(raw).strip())


def build_provisioning_uri(email, secret):
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def build_qr_code_url(provisioning_uri):
    return (
        'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data='
        + quote(provisioning_uri, safe='')
    )


def get_user_totp_secret(user):
    if not user or not user.totp_secret:
        return None
    return decrypt_data(user.totp_secret)


def setup_creator_totp(user, *, print_instructions=True):
    """
    Генерирует TOTP-секрет и 5 резервных кодов для создателя.
    Возвращает (secret_plain, provisioning_uri, qr_url, backup_codes_plain).
    """
    secret = pyotp.random_base32()
    user.totp_secret = encrypt_data(secret)

    UserBackupCode.query.filter_by(user_id=user.id).delete()

    backup_plain = []
    for _ in range(5):
        plain = generate_backup_code()
        backup_plain.append(plain)
        db.session.add(
            UserBackupCode(
                user_id=user.id,
                code_hash=generate_password_hash(plain),
            )
        )
    db.session.commit()

    uri = build_provisioning_uri(user.email or 'creator', secret)
    qr_url = build_qr_code_url(uri)

    if print_instructions:
        print_totp_setup_instructions(user.email, secret, uri, qr_url, backup_plain)

    return secret, uri, qr_url, backup_plain


def print_totp_setup_instructions(email, secret, provisioning_uri, qr_url, backup_codes):
    print('\n' + '=' * 60)
    print('  TOTP — настройка входа создателя (Google Authenticator / Яндекс.Ключ)')
    print('=' * 60)
    print(f'  Email:        {email}')
    print(f'  Секрет TOTP:  {secret}')
    print(f'  OTPAuth URI:  {provisioning_uri}')
    print(f'\n  QR-код (откройте в браузере и отсканируйте):\n  {qr_url}\n')
    print('  Резервные коды (сохраните в надёжном месте, каждый — один раз):')
    for code in backup_codes:
        print(f'    {code}')
    print('=' * 60 + '\n')


def verify_totp_code(user, code):
    secret = get_user_totp_secret(user)
    if not secret:
        return False
    digits = normalize_totp_code(code)
    if len(digits) != 6:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(digits, valid_window=1)


def verify_and_consume_backup_code(user, raw_code):
    code = normalize_backup_code(raw_code)
    if not BACKUP_CODE_PATTERN.match(code):
        return False

    rows = (
        UserBackupCode.query.filter_by(user_id=user.id)
        .filter(UserBackupCode.used_at.is_(None))
        .all()
    )
    for row in rows:
        if check_password_hash(row.code_hash, code):
            row.used_at = utc_now()
            db.session.commit()
            return True
    return False


def authenticate_creator(user, totp_code=None, backup_code=None):
    """Проверяет TOTP или резервный код. Возвращает (ok, error_message)."""
    if not user.totp_secret:
        return False, 'TOTP не настроен для этого аккаунта'

    backup_raw = (backup_code or '').strip()
    if backup_raw:
        if verify_and_consume_backup_code(user, backup_raw):
            return True, None
        return False, 'Неверный или уже использованный резервный код'

    if verify_totp_code(user, totp_code):
        return True, None

    return False, 'Неверный код аутентификатора'


def create_platform_creator(name, email, tag, *, print_instructions=True):
    from werkzeug.security import generate_password_hash as gph

    email = email.strip().lower()
    user = User(
        name=name.strip(),
        phone=None,
        email=email,
        tag=tag,
        role='creator',
        platform_role='super_admin',
        workspace_id=None,
        created_by_id=None,
    )
    user.password_hash = gph(secrets.token_urlsafe(48))
    db.session.add(user)
    db.session.flush()
    secret, uri, qr_url, backup_plain = setup_creator_totp(user, print_instructions=print_instructions)
    return user, secret, uri, qr_url, backup_plain
