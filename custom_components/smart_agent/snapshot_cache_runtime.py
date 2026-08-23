"""Portable add-on snapshot fetch and normalization helpers.

This module deliberately owns no Home Assistant state and no cache lifecycle.
The coordinator supplies the add-on client and remains responsible for request
ordering, monotonic timestamps, and committing the normalized projections.
"""
from __future__ import annotations

import math
from typing import Any


_PRESENCE_SOURCE = "addon_presence_engine"
_PRESENCE_STATES = frozenset({"occupied", "vacant", "unknown"})
_TOPOLOGY_METADATA_KEYS = frozenset(
    {"ok", "error", "error_type", "retryable"}
)
_PRESENCE_EVIDENCE_FIELDS = (
    "entity_id",
    "sensor_type",
    "state",
    "use_for",
    "confidence",
    "freshness_ttl_secs",
    "battery_powered",
    "last_observed_at",
    "stale",
    "stale_reason",
)


def _is_error_payload(value: dict[str, Any]) -> bool:
    if value.get("ok") is False:
        return True
    try:
        return int(value.get("__status", 200) or 200) >= 400
    except (TypeError, ValueError):
        return True


def _unknown_room_payload(
    localized_spaces: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "state": "unknown",
        "confidence": 0.0,
        "reasons": [reason],
        "enter_qualified": False,
        "leave_qualified": False,
        "localized_spaces": localized_spaces,
        "blocked_actions": ["turn_off"],
        "occupied_evidence_ids": [],
        "vacant_evidence_ids": [],
        "evidence_ids": [],
        "metadata": {"presence_contract_source": _PRESENCE_SOURCE},
    }


def _localized_spaces(row: dict[str, Any], room_id: str) -> list[str]:
    localized_spaces: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)
            return
        text = str(value or "").strip()
        if text and text not in localized_spaces:
            localized_spaces.append(text)

    for key in (
        "id",
        "space_id",
        "room_id",
        "area_id",
        "room",
        "name",
        "localized_spaces",
    ):
        add(row.get(key))
    add(room_id)
    return localized_spaces


def _evidence_ids(row: dict[str, Any]) -> list[str]:
    raw = row.get("presence_evidence_ids")
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, (list, tuple, set)):
        values = list(raw)
    else:
        values = []
    result: list[str] = []
    for value in values:
        evidence_id = str(value or "").strip()
        if evidence_id and evidence_id not in result:
            result.append(evidence_id)
    return result


def _presence_evidence(row: dict[str, Any]) -> list[dict[str, Any]]:
    raw_rows = row.get("presence_evidence")
    if not isinstance(raw_rows, (list, tuple)):
        return []
    result: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        entity_id = str(raw.get("entity_id") or raw.get("id") or "").strip()
        if not entity_id:
            continue
        evidence = {
            key: raw.get(key)
            for key in _PRESENCE_EVIDENCE_FIELDS
            if key in raw
        }
        evidence["entity_id"] = entity_id
        use_for = evidence.get("use_for")
        if isinstance(use_for, (list, tuple, set)):
            evidence["use_for"] = [
                str(item or "").strip()
                for item in use_for
                if str(item or "").strip()
            ]
        elif isinstance(use_for, str):
            evidence["use_for"] = [
                item.strip() for item in use_for.split(",") if item.strip()
            ]
        else:
            evidence["use_for"] = []
        result.append(evidence)
    return result


def _normalized_presence_row(
    row: dict[str, Any],
    room_id: str,
    localized_spaces: list[str],
) -> dict[str, Any]:
    source = str(row.get("presence_source") or "").strip()
    state = str(
        row.get("presence_state") or row.get("occupancy_state") or ""
    ).strip().lower()
    canonical = source == _PRESENCE_SOURCE and state in _PRESENCE_STATES
    reason = str(row.get("presence_reason") or "").strip()
    evidence_ids = _evidence_ids(row)
    presence_evidence = _presence_evidence(row)
    confidence = 0.0
    if canonical:
        raw_confidence = (
            row.get("presence_confidence")
            if row.get("presence_confidence") is not None
            else row.get("occupancy_confidence", 0.0)
        )
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            canonical = False
        if (
            isinstance(raw_confidence, bool)
            or not math.isfinite(confidence)
            or not 0.0 <= confidence <= 1.0
        ):
            canonical = False

    if canonical:
        reason = reason or f"canonical_presence_{state}"
    else:
        state = "unknown"
        confidence = 0.0
        reason = "canonical_presence_contract_invalid"
        evidence_ids = []

    result: dict[str, Any] = {
        "state": state,
        "confidence": confidence,
        "reasons": [reason],
        "enter_qualified": False,
        "leave_qualified": False,
        "localized_spaces": localized_spaces,
        "blocked_actions": ["turn_off"] if state != "vacant" else [],
        "occupied_evidence_ids": evidence_ids if state == "occupied" else [],
        "vacant_evidence_ids": evidence_ids if state == "vacant" else [],
        "evidence_ids": evidence_ids,
        "metadata": {"presence_contract_source": _PRESENCE_SOURCE},
    }
    if canonical and presence_evidence:
        result["presence_evidence"] = presence_evidence
    return result


def normalize_presence_rows(rows: list[Any] | tuple[Any, ...]) -> dict[str, dict[str, Any]]:
    """Project add-on room rows into the fail-closed Presence cache contract."""
    normalized_rooms: dict[str, dict[str, Any]] = {}
    alias_owners: dict[str, set[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        room_id = str(
            row.get("id")
            or row.get("space_id")
            or row.get("room_id")
            or row.get("area_id")
            or row.get("name")
            or ""
        ).strip()
        if not room_id:
            continue
        localized_spaces = _localized_spaces(row, room_id)
        for localized in localized_spaces:
            alias_owners.setdefault(localized.casefold(), set()).add(room_id)
        room_payload = _normalized_presence_row(row, room_id, localized_spaces)
        previous = normalized_rooms.get(room_id)
        if previous is not None:
            merged_spaces: list[str] = []
            for values in (previous.get("localized_spaces", []), localized_spaces):
                if not isinstance(values, list):
                    continue
                for localized in values:
                    if localized and localized not in merged_spaces:
                        merged_spaces.append(localized)
            room_payload = _unknown_room_payload(
                merged_spaces,
                "canonical_presence_duplicate_room",
            )
        normalized_rooms[room_id] = room_payload

    conflicting_room_ids = {
        room_id
        for owners in alias_owners.values()
        if len(owners) > 1
        for room_id in owners
    }
    for room_id in conflicting_room_ids:
        payload = normalized_rooms.get(room_id)
        if not isinstance(payload, dict):
            continue
        localized_spaces = payload.get("localized_spaces")
        normalized_rooms[room_id] = _unknown_room_payload(
            list(localized_spaces)
            if isinstance(localized_spaces, list)
            else [room_id],
            "canonical_presence_room_alias_conflict",
        )
    return normalized_rooms


async def fetch_presence_snapshot(
    addon_client: Any,
) -> dict[str, dict[str, Any]] | None:
    """Fetch and normalize Presence rows without owning the caller's cache."""
    get_rooms = getattr(addon_client, "get_rooms", None)
    if not callable(get_rooms):
        return None
    try:
        payload = await get_rooms()
    except Exception:
        return None
    rows: Any = payload
    if isinstance(payload, dict):
        if _is_error_payload(payload):
            return None
        if isinstance(payload.get("data"), list):
            rows = payload.get("data")
        elif isinstance(payload.get("rooms"), list):
            rows = payload.get("rooms")
        else:
            return None
    if not isinstance(rows, (list, tuple)):
        return None
    return normalize_presence_rows(rows)


def normalize_room_topology(payload: Any) -> dict[str, set[str]] | None:
    """Normalize supported add-on topology shapes into symmetric edges."""
    topology: dict[str, set[str]] = {}

    def add_edge(left: Any, right: Any) -> None:
        room_a = str(left or "").strip()
        room_b = str(right or "").strip()
        if not room_a or not room_b or room_a == room_b:
            return
        topology.setdefault(room_a, set()).add(room_b)
        topology.setdefault(room_b, set()).add(room_a)

    rows = payload
    if isinstance(payload, dict) and _is_error_payload(payload):
        return None
    if isinstance(payload, dict) and isinstance(
        payload.get("topology"), (dict, list, tuple, set)
    ):
        rows = payload.get("topology")
    elif isinstance(payload, dict) and isinstance(
        payload.get("data"), (dict, list, tuple, set)
    ):
        rows = payload.get("data")

    if isinstance(rows, dict):
        if _is_error_payload(rows):
            return None
        for room, raw_neighbors in rows.items():
            if str(room).startswith("__") or room in _TOPOLOGY_METADATA_KEYS:
                continue
            if isinstance(raw_neighbors, (list, tuple, set)):
                for neighbor in raw_neighbors:
                    add_edge(room, neighbor)
            else:
                add_edge(room, raw_neighbors)
    elif isinstance(rows, (list, tuple, set)):
        for item in rows:
            if not isinstance(item, dict):
                continue
            room_a = (
                item.get("room_a")
                or item.get("room")
                or item.get("from")
                or item.get("source")
            )
            room_b = (
                item.get("room_b")
                or item.get("neighbor")
                or item.get("to")
                or item.get("target")
            )
            add_edge(room_a, room_b)
    elif rows is None:
        return None
    else:
        return None
    return topology


async def fetch_room_topology(addon_client: Any) -> dict[str, set[str]] | None:
    """Fetch and normalize topology without owning the caller's cache."""
    get_topology = getattr(addon_client, "get_rooms_topology", None)
    if not callable(get_topology):
        return None
    try:
        payload = await get_topology()
    except Exception:
        return None
    return normalize_room_topology(payload)


__all__ = [
    "fetch_presence_snapshot",
    "fetch_room_topology",
    "normalize_presence_rows",
    "normalize_room_topology",
]
