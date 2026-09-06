"""Queue a server-produced room remainder after the lighting path returns."""
from __future__ import annotations

from typing import Any


def schedule_room_remainder(owner: Any, payload: dict[str, Any], *,
                            entity_id: str, trigger: str, new_state: str = "") -> bool:
    reference = payload.get("room_remainder_ref")
    if not isinstance(reference, dict) or reference.get("schema_version") != "0.1":
        return False
    owner._schedule_inference(
        entity_id, trigger, new_state,
        source_trace_context={
            "source": "addon_room_remainder",
            "transaction_id": reference.get("parent_transaction_id", ""),
            "reason": "lighting_scope_evaluated",
            "room_remainder_ref": dict(reference),
        },
    )
    return True
