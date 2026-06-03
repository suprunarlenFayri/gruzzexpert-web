"""Backward-compatible imports; all storage is UTC, display is user-local."""
from utils.datetime_utils import (
    chat_date_separator_label,
    format_execution_date,
    format_local_datetime,
    format_local_time,
    local_now,
    parse_execution_date,
    utc_now,
)

# Legacy names — do not use NSK wall clock for DB writes.
nsk_now = utc_now
nsk_today = lambda: utc_now().date()
format_nsk_datetime = format_local_datetime
