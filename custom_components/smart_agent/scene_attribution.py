"""Helpers for preserving AI scene space attribution in the HA bridge."""
from __future__ import annotations

import json
from typing import Any


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _json_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed


def _iter_scene_items(*values: Any):
    for value in values:
        parsed = _json_value(value)
        if isinstance(parsed, dict):
            yield parsed
        elif isinstance(parsed, list):
            for item in parsed:
                yield item


def ai_scene_space_attribution(
    entities_json: Any,
    actions_json: Any,
    device_info: dict[str, Any] | None = None,
    *,
    source: str,
) -> tuple[str, str, dict[str, Any]]:
    """Infer scene space/room from explicit payload fields or HA device metadata."""
    devices = device_info if isinstance(device_info, dict) else {}
    entity_ids: list[str] = []
    explicit_space = ""
    explicit_room = ""

    for item in _iter_scene_items(entities_json, actions_json):
        if isinstance(item, str):
            entity_id = item.strip()
        elif isinstance(item, dict):
            entity_id = _first_text(item.get("entity_id"), item.get("id"), item.get("entity"))
            explicit_space = explicit_space or _first_text(item.get("space_id"), item.get("space"), item.get("room_id"))
            explicit_room = explicit_room or _first_text(
                item.get("room"),
                item.get("room_name"),
                item.get("display_room"),
                item.get("area"),
            )
        else:
            continue
        if entity_id and entity_id not in entity_ids:
            entity_ids.append(entity_id)

    space_id = explicit_space
    room = explicit_room
    for entity_id in entity_ids:
        info = devices.get(entity_id)
        if not isinstance(info, dict):
            continue
        space_id = space_id or _first_text(info.get("space_id"), info.get("space"), info.get("room"), info.get("area"))
        room = room or _first_text(info.get("room"), info.get("area"), info.get("room_name"), info.get("display_room"))
        if space_id and room:
            break

    if space_id and not room:
        room = space_id
    if room and not space_id:
        space_id = room

    explain_bundle = {
        "source": source,
        "entity_ids": entity_ids,
    }
    if space_id:
        explain_bundle["space_id"] = space_id
    if room:
        explain_bundle["room"] = room
    return space_id, room, explain_bundle
