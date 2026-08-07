"""Presence timing, cold-start reconciliation, and occupancy-cycle helpers."""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from typing import Any, Callable

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

_LOGGER = logging.getLogger(__name__)


DEFAULT_COLD_START_RECHECK_SECONDS = 5
DEFAULT_DEPARTURE_DEBOUNCE_SECONDS = 30
_OCCUPANCY_CYCLE_STORE_VERSION = 1
_OCCUPANCY_CYCLE_STORE_KEY = "smart_agent.occupancy_cycles"


def _serializable_occupancy_cycles(owner: Any) -> dict[str, dict[str, Any]]:
    cycles = getattr(owner, "_arrival_occupancy_cycles", None)
    if not isinstance(cycles, dict):
        return {}
    serialized: dict[str, dict[str, Any]] = {}
    for room, raw in cycles.items():
        if not str(room or "").strip() or not isinstance(raw, dict):
            continue
        cycle_id = str(raw.get("cycle_id") or "").strip()
        if not cycle_id:
            continue
        serialized[str(room)] = {
            "cycle_id": cycle_id,
            "active": raw.get("active") is True,
            "generation": max(0, int(raw.get("generation") or 0)),
            **(
                {"vacant_candidate_at": float(raw.get("vacant_candidate_at"))}
                if raw.get("vacant_candidate_at") not in (None, "")
                else {}
            ),
        }
    return serialized


async def async_restore_occupancy_cycles(owner: Any) -> None:
    """Restore occupancy-cycle identity before listeners reconcile active states."""
    owner._arrival_occupancy_cycles = {}
    try:
        from homeassistant.helpers.storage import Store

        entry_id = str(getattr(getattr(owner, "_entry", None), "entry_id", "") or "default")
        store = Store(
            owner.hass,
            _OCCUPANCY_CYCLE_STORE_VERSION,
            f"{_OCCUPANCY_CYCLE_STORE_KEY}.{entry_id}",
        )
        payload = await store.async_load()
    except Exception as exc:
        _LOGGER.debug("[PresenceCycle] restore unavailable: %s", exc)
        return
    raw_cycles = payload.get("cycles") if isinstance(payload, dict) else None
    if isinstance(raw_cycles, dict):
        owner._arrival_occupancy_cycles = {
            str(room): dict(cycle)
            for room, cycle in raw_cycles.items()
            if str(room or "").strip()
            and isinstance(cycle, dict)
            and str(cycle.get("cycle_id") or "").strip()
        }
    owner._arrival_occupancy_cycle_store = store


def persist_occupancy_cycles(owner: Any) -> None:
    """Schedule a durable write so integration/HA restarts cannot mint a new cycle."""
    store = getattr(owner, "_arrival_occupancy_cycle_store", None)
    delay_save = getattr(store, "async_delay_save", None)
    if not callable(delay_save):
        return
    try:
        delay_save(
            lambda: {"cycles": _serializable_occupancy_cycles(owner)},
            0,
        )
    except Exception as exc:
        _LOGGER.debug("[PresenceCycle] persistence schedule failed: %s", exc)


def _bounded_seconds(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if minimum <= parsed <= maximum else default


def apply_presence_timing_settings(
    owner: Any,
    payload: dict[str, Any],
    applied: list[str],
) -> None:
    fields = (
        (
            "presence_cold_start_recheck_seconds",
            "_STARTUP_PRESENCE_RECONCILE_HOLD_SECONDS",
            DEFAULT_COLD_START_RECHECK_SECONDS,
            1,
            30,
        ),
        (
            "presence_departure_debounce_seconds",
            "_PRESENCE_OFF_DELAY",
            DEFAULT_DEPARTURE_DEBOUNCE_SECONDS,
            5,
            300,
        ),
    )
    for field, attribute, default, minimum, maximum in fields:
        if field not in payload:
            continue
        current = int(getattr(owner, attribute, default) or default)
        value = _bounded_seconds(
            payload.get(field),
            default=current,
            minimum=minimum,
            maximum=maximum,
        )
        if value != current:
            setattr(owner, attribute, value)
            applied.append(f"{field}={value}")


def room_candidates(info: dict[str, Any]) -> list[str]:
    values = (
        info.get("space_id"),
        info.get("room_id"),
        info.get("area_id"),
        info.get("room"),
        info.get("area"),
    )
    return list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))


def room_snapshot(rooms: Any, candidates: list[str]) -> dict[str, Any] | None:
    if not isinstance(rooms, dict):
        return None
    for candidate in candidates:
        snapshot = rooms.get(candidate)
        if isinstance(snapshot, dict):
            return snapshot
    return None


def resolve_space_id(
    info: dict[str, Any],
    *,
    entity_id: str,
    area_getter: Callable[[str], Any] | None = None,
) -> str:
    candidates = room_candidates(info)
    if candidates:
        return candidates[0]
    if callable(area_getter):
        try:
            return str(area_getter(entity_id) or "").strip()
        except Exception:
            return ""
    return ""


def learning_space_identity(
    info: dict[str, Any],
    *,
    entity_id: str,
    area_getter: Callable[[str], Any] | None = None,
) -> tuple[dict[str, Any], str, str]:
    payload = dict(info)
    space_id = resolve_space_id(info, entity_id=entity_id, area_getter=area_getter)
    room = str(
        info.get("room_name")
        or info.get("area_name")
        or info.get("room")
        or info.get("area")
        or space_id
    ).strip()
    if space_id and not str(payload.get("space_id") or "").strip():
        payload["space_id"] = space_id
    if room and not str(payload.get("room") or payload.get("area") or "").strip():
        payload["room"] = room
    return payload, space_id, room


def advance_occupancy_cycle(
    cycles: dict[str, Any],
    *,
    room: str,
    new_state: str,
    other_active: bool,
    active_states: set[str] | tuple[str, ...],
    departure_debounce_seconds: float,
) -> tuple[str, bool, bool]:
    cycle = cycles.get(room) if isinstance(cycles.get(room), dict) else {}
    now = time.time()
    if str(new_state or "").strip().lower() in active_states:
        vacant_at = float(cycle.get("vacant_candidate_at") or 0.0)
        if cycle.get("active") is True and vacant_at > 0 and now - vacant_at >= departure_debounce_seconds:
            cycle["active"] = False
            cycle.pop("vacant_candidate_at", None)
        if cycle.get("active") is True or other_active:
            cycle.pop("vacant_candidate_at", None)
            if not cycle.get("cycle_id"):
                _replace_cycle(cycles, cycle, room)
            return str(cycles.get(room, cycle).get("cycle_id") or ""), False, False
        cycle = _replace_cycle(cycles, cycle, room)
        return str(cycle["cycle_id"]), True, False
    if other_active:
        cycle.pop("vacant_candidate_at", None)
    elif cycle.get("active") is True:
        cycle.setdefault("vacant_candidate_at", now)
    return str(cycle.get("cycle_id") or ""), False, False


def _replace_cycle(cycles: dict[str, Any], prior: dict[str, Any], room: str) -> dict[str, Any]:
    generation = int(prior.get("generation") or 0) + 1
    digest = hashlib.sha256(f"{room}|{generation}|{time.time_ns()}".encode()).hexdigest()[:20]
    cycle = {"cycle_id": f"occ-{digest}", "active": True, "generation": generation}
    cycles[room] = cycle
    return cycle


def slow_fallback_allowed(suppressed: bool, candidate: Any) -> bool:
    return not suppressed and bool(candidate)


def enrich_fast_path_presence_timing(
    owner: Any,
    snapshot: dict[str, Any],
    trigger_context: dict[str, Any] | None,
) -> None:
    snapshot["departure_confirm_delay"] = int(
        getattr(owner, "_PRESENCE_OFF_DELAY", DEFAULT_DEPARTURE_DEBOUNCE_SECONDS)
        or DEFAULT_DEPARTURE_DEBOUNCE_SECONDS
    )
    if isinstance(trigger_context, dict) and trigger_context:
        snapshot["trigger_context"] = dict(trigger_context)


def attach_occupancy_cycle(context: dict[str, Any], snapshot: dict[str, Any]) -> None:
    cycle_id = str(snapshot.get("occupancy_cycle_id", "")).strip()
    if cycle_id:
        context["occupancy_cycle_id"] = cycle_id


def schedule_arrival_baseline_sample(
    owner: Any,
    entity_id: str,
    old_state: str,
    new_state: str,
    *,
    is_presence_sensor: bool,
    arrival_started: bool,
    occupancy_cycle_id: str,
) -> None:
    if is_presence_sensor and not arrival_started and occupancy_cycle_id:
        return
    try:
        owner._schedule_arrival_baseline_sample(
            entity_id, old_state, new_state, occupancy_cycle_id=occupancy_cycle_id
        )
    except TypeError as exc:
        if "occupancy_cycle_id" not in str(exc):
            raise
        owner._schedule_arrival_baseline_sample(entity_id, old_state, new_state)


def occupancy_cycle_outcome(
    owner: Any,
    entity_id: str,
    old_state: str,
    new_state: str,
    *,
    is_presence_sensor: bool,
    old_presence_state: str,
    new_presence_state: str,
) -> tuple[str, bool, bool, str]:
    if not is_presence_sensor or old_presence_state == new_presence_state:
        return "", False, False, ""
    cycle_id, arrival_started, departure_completed = owner._arrival_occupancy_cycle_for_edge(
        entity_id, old_state, new_state
    )
    duplicate_arrival = new_presence_state == "on" and not arrival_started
    incomplete_departure = new_presence_state == "off" and not departure_completed
    status = (
        "duplicate_occupancy_cycle"
        if duplicate_arrival
        else "occupancy_cycle_still_active" if incomplete_departure else ""
    )
    return cycle_id, arrival_started, duplicate_arrival, status


def schedule_startup_presence_reconciliation(
    owner: Any,
    entity_id: str,
    *,
    reconcile_marker: str,
    schedule: Callable[[Any, float, Callable[[datetime], None]], Any] = async_call_later,
) -> None:
    timers = getattr(owner, "_startup_presence_reconcile_timers", None)
    if not isinstance(timers, dict):
        timers = {}
        owner._startup_presence_reconcile_timers = timers
    existing = timers.pop(entity_id, None)
    if callable(existing):
        existing()
    hold_seconds = max(
        1,
        int(getattr(owner, "_STARTUP_PRESENCE_RECONCILE_HOLD_SECONDS", DEFAULT_COLD_START_RECHECK_SECONDS) or DEFAULT_COLD_START_RECHECK_SECONDS),
    )

    @callback
    def _reconcile(_: datetime) -> None:
        timers.pop(entity_id, None)
        reconciled = getattr(owner, "_listener_active_state_reconciled", {})
        if not isinstance(reconciled, dict) or reconciled.get(entity_id) != reconcile_marker:
            return
        states = getattr(getattr(owner, "hass", None), "states", None)
        get_state = getattr(states, "get", None)
        state_obj = get_state(entity_id) if callable(get_state) else None
        current_state = str(getattr(state_obj, "state", "") or "").strip().lower()
        if current_state != "on" or not owner._is_enabled() or getattr(owner, "_sensors_muted", False):
            return
        device_info = getattr(owner, "device_info", {})
        raw_info = device_info.get(entity_id) if isinstance(device_info, dict) else {}
        info = raw_info if isinstance(raw_info, dict) else {}
        room = resolve_space_id(
            info,
            entity_id=entity_id,
            area_getter=getattr(owner, "_get_entity_area", None),
        )
        cycles = getattr(owner, "_arrival_occupancy_cycles", None)
        if not isinstance(cycles, dict):
            cycles = {}
            owner._arrival_occupancy_cycles = cycles
        cycle = cycles.get(room) if room and isinstance(cycles.get(room), dict) else {}
        occupancy_cycle_id = str(cycle.get("cycle_id") or "").strip()
        if not occupancy_cycle_id:
            digest = hashlib.sha256(
                f"{room}|{entity_id}|{reconcile_marker}".encode()
            ).hexdigest()[:20]
            occupancy_cycle_id = f"startup-{digest}"
            if room:
                cycles[room] = {
                    "cycle_id": occupancy_cycle_id,
                    "active": True,
                    "generation": max(1, int(cycle.get("generation") or 0) + 1),
                }
        persist_occupancy_cycles(owner)
        owner._emit_listener_event(
            listener_action="fast_path_scheduled",
            entity_id=entity_id,
            old_state="off",
            new_state="on",
            source_type="startup_reconciliation",
            occupancy_cycle_id=occupancy_cycle_id,
            reconcile_reason="stable_recovered_occupancy",
        )
        owner._spawn_addon_fast_path_task(
            owner._run_addon_fast_path_fail_closed(
                entity_id,
                "on",
                "off",
                occupancy_cycle_id=occupancy_cycle_id,
                trigger_context={
                    "kind": "startup_reconciliation",
                    "stable_presence_seconds": hold_seconds,
                    "verified_preference_required": True,
                },
                suppress_slow_fallback=True,
            ),
            entity_id=entity_id,
            old_state="off",
            new_state="on",
        )

    try:
        timers[entity_id] = schedule(owner.hass, hold_seconds, _reconcile)
    except Exception as exc:
        timers.pop(entity_id, None)
        _LOGGER.debug(
            "[Listeners] startup presence reconciliation schedule failed for %s: %s",
            entity_id,
            exc,
        )


def cleanup_startup_reconciliation(owner: Any, entity_ids: list[str]) -> None:
    current = set(entity_ids)
    reconciled = getattr(owner, "_listener_active_state_reconciled", None)
    if isinstance(reconciled, dict):
        for stale_entity_id in set(reconciled) - current:
            reconciled.pop(stale_entity_id, None)
    timers = getattr(owner, "_startup_presence_reconcile_timers", None)
    if not isinstance(timers, dict):
        return
    for stale_entity_id in set(timers) - current:
        cancel = timers.pop(stale_entity_id, None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                pass
