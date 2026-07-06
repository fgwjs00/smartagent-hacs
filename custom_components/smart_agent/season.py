"""Season helpers used by the Home Assistant integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def ha_season_for_datetime(value: datetime) -> str:
    try:
        from core.season import season_for_datetime as _season_for_datetime  # type: ignore[import-not-found]

        season = str(_season_for_datetime(value) or "").strip()
        if season:
            return season
    except Exception:
        pass

    month = int(getattr(value, "month", 0) or 0)
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    if month in (12, 1, 2):
        return "winter"
    return ""


def normalize_ha_season(value: Any) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "春": "spring",
        "春季": "spring",
        "夏": "summer",
        "夏季": "summer",
        "秋": "autumn",
        "秋季": "autumn",
        "fall": "autumn",
        "冬": "winter",
        "冬季": "winter",
    }
    return aliases.get(raw, raw)
