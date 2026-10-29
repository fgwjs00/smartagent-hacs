# Generated from contracts/python/fact_contract.py; do not edit.
"""Small immutable explanations, never an execution or reclamation permit."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json


def fact_version(value) -> str | None:
    """Content identity only: a digest has no chronological ordering semantics."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(encoded.encode()).hexdigest()


def utc_text(value) -> str | None:
    """Canonical judgment-clock text; invalid/naive time stays explicitly absent."""
    try:
        if type(value) in (int, float):
            parsed = datetime.fromtimestamp(value, timezone.utc)
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value if isinstance(value, datetime) else None
        return parsed.astimezone(timezone.utc).isoformat() if parsed is not None and parsed.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


@dataclass(frozen=True, slots=True)
class FactJudgment:
    subject: str
    source: str
    fact_version: str | None
    rule_version: str
    policy_version: str
    checked_at: str | None
    conclusion: str
    reason: str
    valid_until: str | None
    recheck_condition: str

    def to_dict(self) -> dict:
        return asdict(self)
