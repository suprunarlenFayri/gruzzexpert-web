"""Отправка SMS через SMS.ru (или mock в dev без SMS_API_KEY)."""
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

_SMS_RU_URL = 'https://sms.ru/sms/send'
_DEV_SMS_CODE = '0000'
_PLACEHOLDER_KEYS = frozenset({
    '',
    'none',
    'null',
    'changeme',
    'change-me',
    'your_sms_api_key',
    'sms_api_key',
    'xxx',
    'test',
    'stub',
    'placeholder',
})


def is_sms_api_configured() -> bool:
    """True, если задан реальный ключ SMS.ru (не пустой и не заглушка)."""
    key = (os.getenv('SMS_API_KEY') or '').strip().lower()
    return bool(key) and key not in _PLACEHOLDER_KEYS


def dev_sms_bypass_code() -> str:
    return _DEV_SMS_CODE


def normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone or '')
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    if len(digits) == 10:
        digits = '7' + digits
    return digits


def send_sms(phone: str, text: str) -> bool:
    """
    Отправка SMS. При отсутствии SMS_API_KEY — логирует код (dev).
    """
    phone_norm = normalize_phone(phone)
    if not phone_norm:
        logger.warning('send_sms: invalid phone %r', phone)
        return False

    if not is_sms_api_configured():
        # print — всегда видно в консоли python app.py (logger.info часто скрыт)
        print(f'[DEV SMS] {phone_norm} -> {text} (байпас: введите {_DEV_SMS_CODE})', flush=True)
        logger.warning('[DEV SMS] %s -> %s (bypass code: %s)', phone_norm, text, _DEV_SMS_CODE)
        return True

    api_key = (os.getenv('SMS_API_KEY') or '').strip()
    try:
        resp = requests.get(
            _SMS_RU_URL,
            params={
                'api_id': api_key,
                'to': phone_norm,
                'msg': text,
                'json': 1,
            },
            timeout=12,
        )
        data = resp.json()
        if data.get('status') == 'OK':
            return True
        logger.warning('SMS.ru error: %s', data)
        return False
    except Exception as exc:
        logger.exception('send_sms failed: %s', exc)
        return False
