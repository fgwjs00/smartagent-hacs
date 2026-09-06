"""Capture the callback transition before asynchronous snapshot reads."""
from __future__ import annotations

from typing import Any


def callback_cause(entity_id: str, old: Any, new: Any) -> dict[str, str]:
    observed = ""
    for key in ("last_updated", "last_changed"):
        value = getattr(new, key, None)
        if value:
            observed = value.isoformat() if hasattr(value, "isoformat") else str(value)
            break
    return {
        "entity_id": str(entity_id),
        "old_state": str(getattr(old, "state", "") or ""),
        "new_state": str(getattr(new, "state", "") or ""),
        "observed_at": observed,
        "quality": "good",
        "source_event_id": f"ha_state:{entity_id}:{observed}" if observed else "",
    }
