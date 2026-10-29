"""Report leases for HA visit identity; no action or learning authority."""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any
from .observation_facts import HA_PROFILE, assess_observation, assess_continuity, lease_overlaps


def report_window(info: dict, state: Any, now: float) -> tuple | None:
    """None is untrusted; (None, None) is the explicit no-TTL contract."""
    ttl = _lease_ttl(info)
    result = observation_judgment(info, state, now)
    if result.conclusion != "fresh":
        return None
    if ttl == 0:
        return (None, None)
    reported = _report_instant(info, state)
    return (reported, reported + ttl)


def observation_judgment(info: dict, state: Any, now: float):
    """Explain the same lease used by the actual HA callback, without authority."""
    entity = str(getattr(state, "entity_id", "") or info.get("entity_id") or "")
    return assess_observation(subject=entity, source="ha_state_report",
        reported=_report_instant(info, state), ttl=_lease_ttl(info), now=now,
        profile=HA_PROFILE, available=state is not None)


def _lease_ttl(info: dict) -> float | None:
    eligible = str(info.get("presence_eligible", "")).strip().lower()
    if info.get("stale") is True or eligible in {"0", "false", "no", "off"}:
        return None
    raw_ttl = info.get("freshness_ttl_secs")
    if raw_ttl in (None, ""):
        return 0
    try:
        ttl = float(raw_ttl)
    except (TypeError, ValueError):
        return None
    if not isfinite(ttl) or ttl < 0:
        return None
    return ttl


def window_matches_policy(info: dict, window: tuple) -> bool:
    ttl = _lease_ttl(info)
    if ttl is None:
        return False
    if tuple(window) == (None, None):
        return ttl == 0
    return (all(type(value) in (int, float) and isfinite(value) for value in window)
            and window[1] - window[0] == ttl)


def _report_instant(info: dict, state: Any) -> float | None:
    raw = (getattr(state, "last_reported", None) or info.get("last_observed_at")
           or info.get("observed_at") or getattr(state, "last_updated", None)
           or getattr(state, "last_changed", None))
    try:
        at = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return (at if at.tzinfo is not None else at.replace(tzinfo=timezone.utc)).timestamp()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _overlaps(prior: Any, window: tuple, now: float) -> bool:
    return lease_overlaps(prior, window, now)


def continuous_members(previous: Any, current: dict, now: float) -> bool:
    """Every required source must overlap its previous lease, including the trigger.

    An unchanged fresh report is fine. A replacement arriving after expiry, a
    regressed report, a changed TTL/member set, or a missing proof restarts hold.
    """
    return assess_continuity(previous, current, now).conclusion == "continuous"
