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

def build_presence_sensors_payload(hass: HomeAssistant, coord: SmartAgentCoordinator) -> dict[str, Any]:
    """Build the presence sensor editor payload shared by HTTP and HA WS UIs."""
    import json as _json

    presence_kw = getattr(coord, "_PRESENCE_KW", (
        "occupancy", "presence", "motion", "人体", "存在", "有人", "移动",
        "ren_ti", "cun_zai", "radar", "mmwave", "雷达",
        "person_occupancy", "object_count",
    ))

    sensors: list[dict[str, Any]] = []
    fusion_registry = getattr(coord, "_fusion_registry", None)
    device_info = get_device_info_snapshot(coord)

    for row in list_binary_sensor_states(hass):
        eid = str(row.get("entity_id", "") or "")
        attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        friendly = attrs.get("friendly_name", eid)
        check_str = (friendly + eid).lower()
        if not any(str(kw).lower() in check_str for kw in presence_kw):
            continue

        info = device_info.get(eid) or {}
        fusion_scope = None
        if fusion_registry is not None:
            scope = fusion_registry.get_scope_for_entity(eid)
            if scope is not None:
                fusion_scope = scope.display_name

        state_obj = async_get_state(hass, eid)
        runtime_state = getattr(state_obj, "state", None) if state_obj is not None else None
        sensors.append({
            "entity_id": eid,
            "name": info.get("name") or friendly,
            "room": info.get("room", ""),
            "state": str(runtime_state if runtime_state is not None else (row.get("state", "") or "")),
            "sensor_type": info.get("sensor_type", ""),
            "in_sa": eid in device_info,
            "fusion_scope": fusion_scope,
        })

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
        "sensors": sensors,
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
        row = {"entity_id": entity_id, **dict(info)}
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
            "id": name,
            "name": name,
            "device_count": 0,
            "area_id": area_id,
        })
    return rows


def local_room_rows(coord: Any, hass: HomeAssistant | None = None) -> list[dict[str, Any]]:
    rooms: dict[str, dict[str, Any]] = {}
    room_aliases: dict[str, str] = {}
    for area_row in local_ha_area_room_rows(hass):
        name = str(area_row["name"])
        rooms[name] = dict(area_row)
        room_aliases[name] = name
        area_id = str(area_row.get("area_id") or "").strip()
        if area_id:
            room_aliases[area_id] = name

    for info in get_device_info_snapshot(coord).values():
        if not isinstance(info, dict):
            continue
        room = str(info.get("room") or info.get("area") or "").strip()
        if not room:
            continue
        room_key = room_aliases.get(room, room)
        row = rooms.setdefault(room_key, {"id": room_key, "name": room_key, "device_count": 0})
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

    def _db_update() -> bool:
        return bool(coord._db.execute(
            "UPDATE devices SET sensor_type=?, updated=? WHERE entity_id=?",
            (s_type, now_s, eid),
        ))

    db_ok = await hass.async_add_executor_job(_db_update)
    if not db_ok:
        return {"ok": False, "error": "保存 sensor_type 失败", "status": 500}

    coord.device_info[eid]["sensor_type"] = s_type
    return {"ok": True, "entity_id": eid, "sensor_type": s_type, "status": 200}


