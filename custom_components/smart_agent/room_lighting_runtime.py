"""HA provides observations and wakes the SA room controller; HA owns no target."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
from typing import Any
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later


async def reconcile_rooms(owner: Any, _now: Any = None, *, space_id: str = "") -> dict:
    if not owner._is_enabled() or getattr(owner, "_sensors_muted", False):
        return {}
    client = getattr(owner, "_addon_client", None)
    if client is None:
        return {}
    rooms = {}
    for entity in owner._managed_listener_entity_ids():
        info = (owner.device_info or {}).get(entity) or {}
        space = str(info.get("space_id") or "")
        if space and (not space_id or space_id == space) and owner._is_presence_listener_entity(entity, info):
            rooms.setdefault(space, entity)
    locks = getattr(owner, "_room_lighting_locks", None)
    if locks is None:
        locks = owner._room_lighting_locks = {}
    outcomes = {}
    for space, anchor in rooms.items():
        lock = locks.setdefault(space, asyncio.Lock())
        if lock.locked():
            continue
        async with lock:
            try:
                outcomes[space] = await _reconcile_room(owner, client, space, anchor, _now)
            except Exception as exc:
                owner._sys_log("WARNING", f"[RoomLighting] room={space} recheck_failed={type(exc).__name__}")
    return outcomes


async def _reconcile_room(owner: Any, client: Any, space: str, anchor: str, now: Any) -> dict:
    snapshot = owner._build_addon_fast_path_snapshot(anchor)
    snapshot.pop("causal_events", None)
    now = now if isinstance(now, datetime) else owner._ha_local_now()
    task = {"schema_version": "0.1", "job_id": "room_lighting", "scope_id": space,
            "scheduled_for_utc": now.astimezone(timezone.utc).isoformat(),
            "policy_revision": hashlib.sha256(b"room_lighting_v1").hexdigest()}
    snapshot["room_lighting_task"] = task
    current = owner.hass.states.get(anchor)
    request_id = owner._new_addon_fast_path_request_id(anchor, "", str(getattr(current, "state", "")))
    response = await client.run_decision_fast_path(entity_id=anchor,
        new_state=str(getattr(current, "state", "")), snapshot=snapshot, request_id=request_id)
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError("room_lighting_recheck_failed")
    schedule_room_check(owner, response)
    result = response.get("result") or {}
    from .confidence_arbitration_contract import validate_auto_execution_arbitration
    arbitration = validate_auto_execution_arbitration(response, context_snapshot=snapshot)
    if response.get("auto_execute") is True and result.get("actions") and arbitration.allowed:
        return await owner._execute_fast_path_decision_result(result, entity_id=anchor,
            source_label="房间灯控核对", transaction_id=response.get("transaction_id", ""),
            correlation_id=response.get("correlation_id", ""),
            world_snapshot_id=response.get("world_snapshot_id", ""),
            decision_trace=response.get("decision_trace"), trigger="room_lighting_reconciliation",
            active_ai_rollout=response.get("active_ai_rollout"))
    return response


def schedule_room_check(owner: Any, response: dict, *, schedule: Any = None) -> None:
    control = (response.get("result") or {}).get("room_lighting") or {}
    space, due = control.get("space_id"), control.get("vacancy_due_at")
    if not space:
        return
    timers = getattr(owner, "_room_lighting_timers", None)
    if timers is None:
        timers = owner._room_lighting_timers = {}
    previous = timers.pop(space, None)
    if callable(previous):
        previous()
    if not due:
        return
    seconds = (datetime.fromisoformat(due) - owner._ha_local_now()).total_seconds()
    handle = None
    @callback
    def wake(now: Any) -> None:
        if timers.get(space) is not handle:
            return
        timers.pop(space, None)
        owner.hass.async_create_task(reconcile_rooms(owner, now, space_id=space))
    handle = (schedule or async_call_later)(owner.hass, seconds if seconds > 0 else 20, wake)
    timers[space] = handle
