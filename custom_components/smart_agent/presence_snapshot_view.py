"""Pure projection for the coordinator's cached Presence snapshot."""

from __future__ import annotations

from typing import Any


PRESENCE_SNAPSHOT_CACHE_TTL_SECONDS = 15.0


def build_presence_snapshot(
    *,
    cache_record: Any,
    fallback_cache: Any,
    fallback_updated_at: Any,
    device_info: Any,
    now_monotonic: float,
) -> dict[str, Any]:
    """Project cached Presence facts without performing I/O."""

    if (
        isinstance(cache_record, tuple)
        and len(cache_record) == 2
        and isinstance(cache_record[0], dict)
    ):
        cached = cache_record[0]
        updated_at_raw = cache_record[1]
    else:
        cached = fallback_cache or {}
        updated_at_raw = fallback_updated_at
    if not isinstance(cached, dict):
        cached = {}
    try:
        updated_at = float(updated_at_raw or 0.0)
    except (TypeError, ValueError):
        updated_at = 0.0
    cache_age = now_monotonic - updated_at if updated_at > 0 else None
    cache_fresh = (
        cache_age is not None
        and cache_age >= 0.0
        and cache_age <= PRESENCE_SNAPSHOT_CACHE_TTL_SECONDS
    )

    known_rooms = {
        str(room or "").strip()
        for room in cached
        if str(room or "").strip()
    }
    if isinstance(device_info, dict):
        for info in device_info.values():
            if not isinstance(info, dict):
                continue
            room = str(
                info.get("space_id")
                or info.get("room")
                or info.get("area")
                or ""
            ).strip()
            if room:
                known_rooms.add(room)

    def _unknown_payload(room: str, reason: str) -> dict[str, Any]:
        return {
            "state": "unknown",
            "confidence": 0.0,
            "reasons": [reason],
            "enter_qualified": False,
            "leave_qualified": False,
            "localized_spaces": [room],
            "blocked_actions": ["turn_off"],
            "occupied_evidence_ids": [],
            "vacant_evidence_ids": [],
            "evidence_ids": [f"presence.{room}"],
            "metadata": {"presence_contract_source": "addon_presence_engine"},
        }

    def _copy_payload(payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        copied = dict(payload)
        for key in (
            "reasons",
            "localized_spaces",
            "blocked_actions",
            "occupied_evidence_ids",
            "vacant_evidence_ids",
            "evidence_ids",
        ):
            value = copied.get(key)
            if isinstance(value, (list, tuple, set)):
                copied[key] = list(value)
        evidence_rows = copied.get("presence_evidence")
        if isinstance(evidence_rows, (list, tuple)):
            copied["presence_evidence"] = [
                {
                    key: list(value)
                    if isinstance(value, (list, tuple, set))
                    else value
                    for key, value in row.items()
                }
                for row in evidence_rows
                if isinstance(row, dict)
            ]
        metadata = copied.get("metadata")
        if isinstance(metadata, dict):
            copied["metadata"] = dict(metadata)
        return copied

    rooms: dict[str, dict[str, Any]] = {}
    if cache_fresh:
        for room in sorted(known_rooms):
            payload = _copy_payload(cached.get(room))
            rooms[room] = payload or _unknown_payload(
                room,
                "canonical_presence_room_missing",
            )
        source = "addon_presence_engine"
        reason = "canonical_presence_snapshot_fresh"
    else:
        reason = (
            "canonical_presence_snapshot_stale"
            if updated_at > 0
            else "canonical_presence_snapshot_unavailable"
        )
        rooms = {
            room: _unknown_payload(room, reason)
            for room in sorted(known_rooms)
        }
        source = "ha_presence_snapshot_fail_closed"

    return {
        "version": "1.0",
        "source": source,
        "rooms": rooms,
        "metadata": {
            "presence_contract_source": "addon_presence_engine",
            "reason": reason,
            "cache_fresh": cache_fresh,
            "cache_age_secs": round(cache_age, 3) if cache_age is not None else None,
            "cache_ttl_secs": PRESENCE_SNAPSHOT_CACHE_TTL_SECONDS,
        },
    }


__all__ = ["build_presence_snapshot"]
