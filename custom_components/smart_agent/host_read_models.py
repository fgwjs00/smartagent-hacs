"""HA host local read-model helpers for SmartAgent compatibility views."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import SmartAgentCoordinator
from .ha_adapter import (
    async_get_area_registry,
    async_get_state,
    get_device_info_snapshot,
    get_room_topology_cache_snapshot,
    list_binary_sensor_states,
)


def _presence_sensor_keywords(coord: SmartAgentCoordinator) -> tuple[str, ...]:
    defaults = (
        "occupancy", "presence", "motion", "pir", "ren_ti", "cun_zai", "you_ren",
        "radar", "mmwave", "frigate", "vision", "camera", "person_occupancy", "object_count",
        "contact", "door", "window", "opening", "men_chuang",
    )
    raw_keywords = getattr(coord, "_PRESENCE_KW", defaults)
    if not isinstance(raw_keywords, (list, tuple, set)):
        raw_keywords = defaults
    merged = [*defaults, *(str(item) for item in raw_keywords)]
    result: list[str] = []
    for item in merged:
        token = str(item or "").strip().lower()
        if token and token not in result:
            result.append(token)
    return tuple(result)


def _presence_sensor_domain(entity_id: str, info: dict[str, Any] | None = None) -> str:
    info = info if isinstance(info, dict) else {}
    domain = str(info.get("domain") or info.get("type") or "").strip()
    if not domain and "." in entity_id:
        domain = entity_id.split(".", 1)[0]
    return domain


def _presence_sensor_text(entity_id: str, info: dict[str, Any] | None = None) -> str:
    info = info if isinstance(info, dict) else {}
    parts: list[str] = [entity_id]
    for key in ("name", "friendly_name", "domain", "type", "sensor_type", "device_class"):
        value = info.get(key)
        if value:
            parts.append(str(value))
    roles = info.get("roles") or info.get("role") or ()
    if isinstance(roles, str):
        roles = [roles]
    if isinstance(roles, (list, tuple, set)):
        parts.extend(str(item) for item in roles if item)
    return " ".join(parts).lower()


def _is_presence_sensor_snapshot(
    entity_id: str,
    info: dict[str, Any] | None,
    keywords: tuple[str, ...],
) -> bool:
    domain = _presence_sensor_domain(entity_id, info)
    if domain not in {"binary_sensor", "sensor", "camera"}:
        return False
    text = _presence_sensor_text(entity_id, info)
    return any(token in text for token in keywords)


def build_presence_sensors_payload(hass: HomeAssistant, coord: SmartAgentCoordinator) -> dict[str, Any]:
    """Build the presence sensor editor payload shared by HTTP and HA WS UIs."""
    import json as _json

    _legacy_presence_kw = (
        "occupancy", "presence", "motion", "人体", "存在", "有人", "移动",
        "ren_ti", "cun_zai", "radar", "mmwave", "雷达",
        "person_occupancy", "object_count",
    )

    presence_kw = (*_legacy_presence_kw, *_presence_sensor_keywords(coord))

    sensors_by_id: dict[str, dict[str, Any]] = {}
    fusion_registry = getattr(coord, "_fusion_registry", None)
    device_info = get_device_info_snapshot(coord)

    for row in list_binary_sensor_states(hass):
        eid = str(row.get("entity_id", "") or "")
        attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        info = device_info.get(eid) if isinstance(device_info.get(eid), dict) else {}
        match_info = {**attrs, **info}
        friendly = attrs.get("friendly_name", eid)
        if not _is_presence_sensor_snapshot(eid, match_info, presence_kw):
            continue

        fusion_scope = None
        if fusion_registry is not None:
            scope = fusion_registry.get_scope_for_entity(eid)
            if scope is not None:
                fusion_scope = scope.display_name

        state_obj = async_get_state(hass, eid)
        runtime_state = getattr(state_obj, "state", None) if state_obj is not None else None
        sensors_by_id[eid] = {
            "entity_id": eid,
            "name": info.get("name") or friendly,
            "room": info.get("room", ""),
            "state": str(runtime_state if runtime_state is not None else (row.get("state", "") or "")),
            "sensor_type": info.get("sensor_type", ""),
            "in_sa": eid in device_info,
            "fusion_scope": fusion_scope,
        }

    for eid, raw_info in sorted(device_info.items(), key=lambda item: str(item[0])):
        entity_id = str(eid or "").strip()
        if not entity_id or entity_id in sensors_by_id:
            continue
        info = raw_info if isinstance(raw_info, dict) else {}
        if not _is_presence_sensor_snapshot(entity_id, info, presence_kw):
            continue
        fusion_scope = None
        if fusion_registry is not None:
            scope = fusion_registry.get_scope_for_entity(entity_id)
            if scope is not None:
                fusion_scope = scope.display_name
        state_obj = async_get_state(hass, entity_id)
        runtime_state = getattr(state_obj, "state", None) if state_obj is not None else None
        sensors_by_id[entity_id] = {
            "entity_id": entity_id,
            "name": info.get("name") or info.get("friendly_name") or entity_id,
            "room": info.get("room", ""),
            "state": str(runtime_state if runtime_state is not None else (info.get("state", "") or "")),
            "sensor_type": info.get("sensor_type", ""),
            "in_sa": True,
            "fusion_scope": fusion_scope,
        }

    entry = getattr(coord, "_entry", None)
    fusion_raw = ((entry.options or {}).get("presence_fusion", "[]") if entry else "[]") or "[]"
    try:
        fusion_config = _json.loads(fusion_raw)
        if not isinstance(fusion_config, list):
            fusion_config = []
    except Exception:
        fusion_config = []

    rooms = sorted({
        info.get("room", "")
        for info in device_info.values()
        if info.get("room", "")
    })

    return {
        "sensors": list(sensors_by_id.values()),
        "fusion_config": fusion_config,
        "rooms": rooms,
    }


def local_device_rows(coord: Any, hass: HomeAssistant | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    hass = hass or getattr(coord, "hass", None)
    for eid, info in get_device_info_snapshot(coord).items():
        if not isinstance(info, dict):
            continue
        entity_id = str(eid)
        row = {"entity_id": entity_id, "managed": True, "in_sa": True, **dict(info)}
        try:
            get_area = getattr(coord, "_get_entity_area", None)
            raw_ha_area = get_area(entity_id) if callable(get_area) else ""
            ha_area = str(raw_ha_area or "").strip()
        except Exception:
            ha_area = ""
        if ha_area:
            cached_room = str(row.get("room") or row.get("area") or "").strip()
            if cached_room and cached_room != ha_area:
                row["configured_room"] = cached_room
            row["room"] = ha_area
            row["area"] = ha_area
            row["area_source"] = "ha_registry"
        state_obj = None
        if hass is not None:
            try:
                state_obj = async_get_state(hass, entity_id)
            except Exception:
                state_obj = None
        if state_obj is not None:
            state = str(getattr(state_obj, "state", "") or "unknown")
            row["state"] = state
            row["available"] = state != "unavailable"
            for key in ("last_changed", "last_updated"):
                raw = getattr(state_obj, key, "")
                row[key] = raw.isoformat() if hasattr(raw, "isoformat") else str(raw or "")
        else:
            if row.get("state") is not None:
                row["state"] = str(row.get("state") or "unknown")
        rows.append(row)
    return rows


def local_ha_area_room_rows(hass: HomeAssistant | None) -> list[dict[str, Any]]:
    if hass is None:
        return []
    try:
        area_reg = async_get_area_registry(hass)
        raw_areas = getattr(area_reg, "areas", None)
        if isinstance(raw_areas, dict):
            area_items = list(raw_areas.values())
        elif hasattr(area_reg, "async_list_areas"):
            area_items = list(area_reg.async_list_areas())
        else:
            area_items = []
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for area in area_items:
        area_id = str(
            getattr(area, "id", "")
            or getattr(area, "area_id", "")
            or getattr(area, "slug", "")
            or ""
        ).strip()
        name = str(getattr(area, "name", "") or area_id).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append({
            "id": area_id or name,
            "name": name,
            "device_count": 0,
            "area_id": area_id,
            "source": "ha_area_registry",
        })
    return rows


def local_room_rows(coord: Any, hass: HomeAssistant | None = None) -> list[dict[str, Any]]:
    rooms: dict[str, dict[str, Any]] = {}
    room_aliases: dict[str, str] = {}
    for area_row in local_ha_area_room_rows(hass):
        area_key = str(area_row.get("id") or area_row.get("area_id") or area_row.get("name") or "").strip()
        name = str(area_row["name"])
        if not area_key:
            area_key = name
        rooms[area_key] = dict(area_row)
        room_aliases[name] = area_key
        room_aliases[area_key] = area_key
        area_id = str(area_row.get("area_id") or "").strip()
        if area_id:
            room_aliases[area_id] = area_key

    for info in get_device_info_snapshot(coord).values():
        if not isinstance(info, dict):
            continue
        room = str(info.get("room") or info.get("area") or "").strip()
        if not room:
            continue
        room_key = room_aliases.get(room)
        if not room_key:
            continue
        row = rooms.get(room_key)
        if row is None:
            continue
        row["device_count"] = int(row.get("device_count", 0)) + 1
    return sorted(rooms.values(), key=lambda row: str(row.get("name", "")))


def local_room_topology_rows(coord: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    db = getattr(coord, "_db", None)
    if db is not None and hasattr(db, "query"):
        try:
            raw_rows = db.query("SELECT room_a, room_b, relation FROM room_topology", ()) or []
        except Exception:
            raw_rows = []
        for row in raw_rows:
            if isinstance(row, dict):
                room_a = str(row.get("room_a") or "").strip()
                room_b = str(row.get("room_b") or "").strip()
                relation = str(row.get("relation") or "adjacent").strip() or "adjacent"
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                room_a = str(row[0] or "").strip()
                room_b = str(row[1] or "").strip()
                relation = str(row[2] if len(row) > 2 else "adjacent").strip() or "adjacent"
            else:
                continue
            if room_a and room_b:
                rows.append({"room_a": room_a, "room_b": room_b, "relation": relation})
        if rows:
            return rows

    topology = get_room_topology_cache_snapshot(coord)
    seen: set[tuple[str, str]] = set()
    for room_a, neighbors in topology.items():
        left = str(room_a or "").strip()
        if not left:
            continue
        for room_b in neighbors or set():
            right = str(room_b or "").strip()
            if not right:
                continue
            key = tuple(sorted((left, right)))
            if key in seen:
                continue
            seen.add(key)
            rows.append({"room_a": left, "room_b": right, "relation": "adjacent"})
    return sorted(rows, key=lambda row: (str(row.get("room_a", "")), str(row.get("room_b", ""))))


async def async_save_presence_sensor_type(
    hass: HomeAssistant,
    coord: SmartAgentCoordinator,
    entity_id: str,
    sensor_type: str,
) -> dict[str, Any]:
    """Persist a managed presence sensor's type classification."""
    eid = entity_id.strip()
    s_type = sensor_type.strip().lower()
    if not eid:
        return {"ok": False, "error": "entity_id required", "status": 400}
    if s_type not in ("", "pir", "mmwave", "frigate"):
        return {
            "ok": False,
            "error": "sensor_type must be '', 'pir', 'mmwave' or 'frigate'",
            "status": 400,
        }
    device_info_snapshot = get_device_info_snapshot(coord)
    if eid not in device_info_snapshot:
        return {"ok": False, "error": f"设备未纳管: {eid}", "status": 404}

    from datetime import datetime as _dt_s
    now_s = _dt_s.now().isoformat()

    enqueue = getattr(coord, "_enqueue_internal_event", None)
    if not callable(enqueue) or not enqueue(
        "device",
        {"action": "update_sensor_type", "entity_id": eid, "sensor_type": s_type, "updated": now_s},
        ts=now_s,
    ):
        return {"ok": False, "error": "保存 sensor_type 失败", "status": 500}

    coord.device_info[eid]["sensor_type"] = s_type
    return {"ok": True, "entity_id": eid, "sensor_type": s_type, "status": 200}


