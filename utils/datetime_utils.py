"""UTC storage and per-user local display for datetimes."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None

    class ZoneInfoNotFoundError(Exception):
        pass


UTC = timezone.utc
DEFAULT_TZ = 'UTC'

_RU_MONTHS_GENITIVE = (
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
)


def utc_now() -> datetime:
    """Naive UTC datetime for DB writes."""
    return datetime.utcnow()


def resolve_timezone(tz_name: Optional[str] = None):
    name = (tz_name or DEFAULT_TZ).strip() or DEFAULT_TZ
    if ZoneInfo is None:
        return UTC
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        try:
            return ZoneInfo(DEFAULT_TZ)
        except ZoneInfoNotFoundError:
            return UTC


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_local(dt: Optional[datetime], tz_name: Optional[str] = None) -> Optional[datetime]:
    if dt is None:
        return None
    utc_dt = ensure_utc(dt)
    local_tz = resolve_timezone(tz_name or get_user_timezone_from_request())
    return utc_dt.astimezone(local_tz).replace(tzinfo=None)


def get_user_timezone_from_request(request_obj=None) -> str:
    try:
        from flask import has_request_context, request

        req = request_obj or (request if has_request_context() else None)
        if req is not None:
            tz = (req.cookies.get('user_timezone') or '').strip()
            if tz:
                return tz
    except Exception:
        pass
    return DEFAULT_TZ


def local_now(tz_name: Optional[str] = None) -> datetime:
    return to_local(utc_now(), tz_name or get_user_timezone_from_request())


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    normalized = ensure_utc(dt)
    return normalized.isoformat().replace('+00:00', 'Z')


def format_local_time(dt, fmt: str = '%H:%M', tz_name: Optional[str] = None) -> str:
    local = to_local(dt, tz_name)
    return local.strftime(fmt) if local else ''


def format_local_datetime(dt, fmt: str = '%d.%m.%Y %H:%M', tz_name: Optional[str] = None) -> str:
    return format_local_time(dt, fmt, tz_name)


def format_local_date(dt, fmt: str = '%d.%m.%Y', tz_name: Optional[str] = None) -> str:
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime(fmt)
    local = to_local(dt, tz_name)
    return local.strftime(fmt) if local else ''


def local_date_key(dt, tz_name: Optional[str] = None) -> str:
    return format_local_time(dt, '%Y-%m-%d', tz_name)


def chat_date_separator_label(dt, tz_name: Optional[str] = None) -> str:
    local = to_local(dt, tz_name)
    if not local:
        return ''
    return f'{local.day} {_RU_MONTHS_GENITIVE[local.month - 1]} {local.year} г.'


def parse_execution_date(value):
    """Parses YYYY-MM-DD into date or returns None."""
    if not value or not str(value).strip():
        return None
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def format_execution_date(d, fmt: str = '%d.%m.%Y'):
    if not d:
        return None
    if isinstance(d, datetime):
        return d.strftime(fmt)
    if isinstance(d, date):
        return d.strftime(fmt)
    return str(d)
