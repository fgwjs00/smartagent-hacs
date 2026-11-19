"""Shared timezone lookup and HA local clock helper."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import logging
from typing import Any
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


def ha_local_now(
    hass: Any,
    *,
    fallback_now: Callable[[], datetime],
    now_cls: type[datetime] = datetime,
    logger: logging.Logger | None = None,
    source: str = "",
) -> datetime:
    config = getattr(hass, "config", None)
    tz_name = str(getattr(config, "time_zone", "") or "").strip()
    if tz_name:
        try:
            return now_cls.now(configured_timezone(tz_name))
        except ZoneInfoNotFoundError:
            if logger is not None:
                logger.debug("[%s] invalid HA timezone for local clock: %s", source or "SmartAgent", tz_name)
    return fallback_now()
