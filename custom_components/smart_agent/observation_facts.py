# Generated from contracts/python/observation_facts.py; do not edit.
"""Versioned report freshness interpretation shared by HA and Add-on.

Adapters own timestamp/TTL decoding. The two named compatibility profiles retain
their existing skew/no-TTL behavior. Neither freshness nor continuity authorizes
an action; the room policy, manual control and dispatch guards remain separate.
"""
from __future__ import annotations

from math import isfinite
from .fact_contract import FactJudgment, fact_version, utc_text

RULE_VERSION = "observation_freshness.v1"
HA_PROFILE = "ha_report_lease.v1"
CORE_PROFILE = "core_evidence_lease.v1"


def _number(value) -> bool:
    return type(value) in (float, int) and isfinite(value)


def _freshness(reported, ttl, now, profile, eligible, available) -> tuple[str, str]:
    if profile not in {HA_PROFILE, CORE_PROFILE}:
        return "unknown", "unsupported_policy"
    if not available or not eligible:
        return "unknown", "observation_unavailable_or_ineligible"
    if not _number(now) or not _number(ttl) or ttl < 0:
        return "unknown", "invalid_clock_or_ttl"
    # Historical HA no-TTL sources need no report clock. Core still rejects a
    # known future clock, including for no-TTL evidence.
    if ttl == 0 and profile == HA_PROFILE:
        return "fresh", "explicit_no_ttl"
    if _number(reported) and now - reported < (-60 if profile == HA_PROFILE else 0):
        return "unknown", "future_report"
    if ttl == 0:
        return "fresh", "explicit_no_ttl"
    if not _number(reported):
        return "unknown", "report_clock_missing"
    if now - reported > ttl:
        return "stale", "report_expired"
    return "fresh", "report_within_lease"


def assess_observation(*, subject: str, source: str, reported, ttl, now,
                       profile: str, eligible: bool = True, available: bool = True) -> FactJudgment:
    conclusion, reason = _freshness(reported, ttl, now, profile, eligible, available)
    version = fact_version([subject, source, reported, available])
    policy_version = profile + ":" + (fact_version([ttl, eligible]) or "invalid")
    until = reported + ttl if _number(reported) and _number(ttl) and ttl > 0 else None
    return FactJudgment(subject, source, version, RULE_VERSION, policy_version, utc_text(now),
                        conclusion, reason, utc_text(until),
                        "new_report_or_policy_change_or_lease_expiry")


def lease_overlaps(prior, current: tuple, now: float) -> bool:
    """A fresh replacement cannot repair a gap or a backwards report."""
    if not _number(now) or not isinstance(prior, (list, tuple)) or len(prior) != 2:
        return False
    if not isinstance(current, tuple) or len(current) != 2:
        return False
    if current == (None, None):
        return tuple(prior) == current
    if any(not _number(value) for value in (*prior, *current)):
        return False
    reported, until = current
    return (prior[0] <= reported <= prior[1] and until >= now
            and until - reported == prior[1] - prior[0])


def assess_continuity(previous, current: dict, now: float, *, subject: str = "") -> FactJudgment:
    """Explain full-member continuity; holding duration remains room-policy owned."""
    if not _number(now):
        reason = "invalid_judgment_clock"
    elif not isinstance(previous, dict) or not isinstance(current, dict) or not current:
        reason = "continuity_history_missing"
    elif previous.keys() != current.keys():
        reason = "required_members_changed"
    elif not all(lease_overlaps(previous[entity], window, now) for entity, window in current.items()):
        reason = "lease_gap_regression_or_policy_change"
    else:
        reason = "continuous_report_windows"
    conclusion = "continuous" if reason == "continuous_report_windows" else "interrupted"
    return FactJudgment(subject, "member_report_windows", fact_version([previous, current]),
                        "observation_continuity.v1", "full_member_overlap.v1", utc_text(now),
                        conclusion, reason, None, "each_report_or_member_or_policy_change")
