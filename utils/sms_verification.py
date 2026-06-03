"""4-значные SMS-коды: генерация, хэш, проверка."""
import random
import secrets
from datetime import timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from models import db
from models import SmsVerificationCode
from utils.datetime_utils import utc_now
from utils.sms import dev_sms_bypass_code, is_sms_api_configured, normalize_phone, send_sms

CODE_TTL_MINUTES = 10
MAX_ATTEMPTS = 5


def _generate_code() -> str:
    return f'{random.randint(1000, 9999)}'


def create_sms_verification(phone: str, purpose: str) -> tuple[str | None, str | None]:
    """
    Создаёт запись, отправляет SMS. Возвращает (session_token, error).
    """
    phone_norm = normalize_phone(phone)
    if len(phone_norm) < 11:
        return None, 'Некорректный номер телефона'

    purpose = (purpose or 'login').strip().lower()
    if purpose not in ('login', 'register'):
        return None, 'Неверный тип верификации'

    code = _generate_code()
    session_token = secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(minutes=CODE_TTL_MINUTES)

    row = SmsVerificationCode(
        phone=phone_norm,
        purpose=purpose,
        session_token=session_token,
        code_hash=generate_password_hash(code),
        expires_at=expires_at,
        attempts=0,
    )
    db.session.add(row)
    db.session.commit()

    text = f'GruzzExpert: код {code}. Никому не сообщайте.'
    if not is_sms_api_configured():
        print(
            f'[DEV SMS] login/register phone={phone_norm} code={code} '
            f'(или введите {dev_sms_bypass_code()})',
            flush=True,
        )
    if not send_sms(phone_norm, text):
        db.session.delete(row)
        db.session.commit()
        return None, 'Не удалось отправить SMS. Попробуйте позже.'

    return session_token, None


def verify_sms_code(session_token: str, code: str, phone: str | None = None) -> tuple[bool, str | None]:
    row = SmsVerificationCode.query.filter_by(session_token=session_token).first()
    if not row:
        return False, 'Сессия верификации не найдена'
    if row.expires_at and row.expires_at < utc_now():
        return False, 'Код истёк. Запросите новый.'
    if row.attempts >= MAX_ATTEMPTS:
        return False, 'Превышено число попыток'

    row.attempts += 1
    db.session.commit()

    if phone:
        phone_norm = normalize_phone(phone)
        if phone_norm != row.phone:
            return False, 'Номер не совпадает с верификацией'

    code_clean = ''.join(c for c in (code or '') if c.isdigit())
    if len(code_clean) != 4:
        return False, 'Введите 4 цифры кода'

    # Локальный байпас: без SMS_API_KEY всегда принимаем 0000
    if not is_sms_api_configured() and code_clean == dev_sms_bypass_code():
        row.verified_at = utc_now()
        db.session.commit()
        print(f'[DEV SMS] bypass accepted for {row.phone} (code 0000)', flush=True)
        return True, None

    if not check_password_hash(row.code_hash, code_clean):
        return False, 'Неверный код'

    row.verified_at = utc_now()
    db.session.commit()
    return True, None


def consume_verified_session(session_token: str, phone: str, purpose: str) -> bool:
    """Проверяет, что сессия уже подтверждена (для завершения login/register)."""
    phone_norm = normalize_phone(phone)
    row = SmsVerificationCode.query.filter_by(
        session_token=session_token,
        phone=phone_norm,
        purpose=purpose,
    ).first()
    if not row or not row.verified_at:
        return False
    if row.expires_at and row.expires_at < utc_now():
        return False
    if row.consumed_at:
        return False
    row.consumed_at = utc_now()
    db.session.commit()
    return True
