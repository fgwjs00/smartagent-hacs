"""Shared timezone lookup with the existing fixed-offset fallback."""
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def configured_timezone(configured_timezone: str):
    normalized_tz = configured_timezone.lower()
    fixed_offset_hours = {
        "asia/shanghai": 8,
        "asia/chongqing": 8,
        "asia/harbin": 8,
        "asia/hong_kong": 8,
        "hongkong": 8,
        "prc": 8,
        "utc": 0,
    }.get(normalized_tz)
    try:
        return ZoneInfo(configured_timezone)
    except ZoneInfoNotFoundError:
        if fixed_offset_hours is not None:
            return timezone(timedelta(hours=fixed_offset_hours), configured_timezone)
        raise
