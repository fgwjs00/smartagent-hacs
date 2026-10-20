"""HA provides observations and wakes the SA room controller; HA owns no target."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later


MAX_CONCURRENT_ROOM_CHECKS = 4


@dataclass(slots=True)
class _RecheckProgress:
    request_id: str = ""
    stage: str = "prepare"
    upstream_status: int | None = None

    def failure(self, space: str, anchor: str, exc: Exception) -> dict:
        # Transport/host failure does not prove whether the gateway or HA acted.
        # Keep local locators, never raw response bodies or exception messages.
        return {"ok": False, "error": "room_lighting_recheck_failed",
                "request_id": self.request_id, "execution_state": "unknown",
                "details": {"operation": "room_lighting.reconcile",
                            "failure_stage": self.stage, "space_id": space,
                            "entity_id": anchor, "exception_type": type(exc).__name__,
                            "upstream_status": self.upstream_status}}


async def reconcile_rooms(owner: Any, _now: Any = None, *, space_id: str = "") -> dict:
    if (getattr(owner, "_room_lighting_stopping", False)
            or not owner._is_enabled() or getattr(owner, "_sensors_muted", False)):
        return {}
    client = getattr(owner, "_addon_client", None)
    if client is None:
        return {}
    reserved = await _reserve_rooms(owner, space_id)
    if not reserved:
        return {}
    return await _run_room_checks(owner, client, reserved, _now)


async def _reserve_rooms(owner: Any, space_id: str) -> list:
    rooms = {}
    for entity in owner._managed_listener_entity_ids():
        info = (owner.device_info or {}).get(entity) or {}
        space = str(info.get("space_id") or "")
        if space and (not space_id or space_id == space) and owner._is_presence_listener_entity(entity, info):
            rooms.setdefault(space, entity)
    locks = getattr(owner, "_room_lighting_locks", None)
    if locks is None:
        locks = owner._room_lighting_locks = {}
    # Reserve before yielding so overlapping periodic/timer callbacks coalesce,
    # including rooms waiting for a worker. Do not enqueue one task per room.
    reserved = []
    for space, anchor in rooms.items():
        lock = locks.setdefault(space, asyncio.Lock())
        if not lock.locked():
            await lock.acquire()  # Uncontended acquisition does not yield.
            reserved.append((space, anchor, lock))
    return reserved


async def _run_room_checks(owner: Any, client: Any, reserved: list, now: Any) -> dict:
    gate = getattr(owner, "_room_lighting_gate", None)
    if gate is None:
        gate = owner._room_lighting_gate = asyncio.Semaphore(MAX_CONCURRENT_ROOM_CHECKS)
    tasks = getattr(owner, "_room_lighting_tasks", None)
    if tasks is None:
        tasks = owner._room_lighting_tasks = set()
    parent = asyncio.current_task()
    tasks.add(parent)
    outcomes = {}
    pending = iter(reserved)

    async def worker():
        for space, anchor, _lock in pending:
            async with gate:
                # Settings may have changed while another room was timing out.
                if (getattr(owner, "_room_lighting_stopping", False)
                        or not owner._is_enabled() or getattr(owner, "_sensors_muted", False)):
                    continue
                progress = _RecheckProgress()
                try:
                    outcomes[space] = await _reconcile_room(owner, client, space, anchor, now, progress)
                except Exception as exc:
                    outcomes[space] = progress.failure(space, anchor, exc)
                    owner._sys_log("WARNING", "[RoomLighting] operation=room_lighting.reconcile "
                        f"room={space} entity={anchor} request_id={progress.request_id} "
                        f"failure_stage={progress.stage} recheck_failed={type(exc).__name__} "
                        f"upstream_status={progress.upstream_status}")

    workers = []
    try:
        for _ in range(min(MAX_CONCURRENT_ROOM_CHECKS, len(reserved))):
            workers.append(asyncio.create_task(worker()))
        group = asyncio.gather(*workers)
        # Cancellation is handled once by our draining finally block. Repeated
        # caller cancellation must not interrupt a child's cleanup await.
        group.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        await asyncio.shield(group)
    finally:
        try:
            await _cancel_room_tasks(workers)
        finally:
            for _, _, lock in reserved:
                lock.release()
            tasks.discard(parent)
    return outcomes


async def stop_room_checks(owner: Any) -> None:
    """Drain checks before closing their client; no timer may revive this owner."""
    owner._room_lighting_stopping = True
    for cancel in getattr(owner, "_room_lighting_timers", {}).values():
        cancel()
    owner._room_lighting_timers = {}
    tasks = list(getattr(owner, "_room_lighting_tasks", ()))
    await _cancel_room_tasks(tasks)


async def _cancel_room_tasks(tasks) -> None:
    for task in tasks:
        if not task.done():
            task.cancel()
    drained = asyncio.gather(*tasks, return_exceptions=True)
    cancelled = None
    while not drained.done():
        try:
            await asyncio.shield(drained)
        except asyncio.CancelledError as exc:
            cancelled = exc
    if cancelled is not None:
        raise cancelled
    failures = [result for result in drained.result()
                if isinstance(result, Exception)]
    if failures:
        raise ExceptionGroup('room_lighting_shutdown_failed', failures)


async def _reconcile_room(
    owner: Any, client: Any, space: str, anchor: str, now: Any, progress: _RecheckProgress,
) -> dict:
    snapshot = owner._build_addon_fast_path_snapshot(anchor)
    snapshot.pop("causal_events", None)
    now = now if isinstance(now, datetime) else owner._ha_local_now()
    task = {"schema_version": "0.1", "job_id": "room_lighting", "scope_id": space,
            "scheduled_for_utc": now.astimezone(timezone.utc).isoformat(),
            "policy_revision": hashlib.sha256(b"room_lighting_v1").hexdigest()}
    snapshot["room_lighting_task"] = task
    current = owner.hass.states.get(anchor)
    request_id = owner._new_addon_fast_path_request_id(anchor, "", str(getattr(current, "state", "")))
    progress.request_id, progress.stage = request_id, "provider_request"
    response = await client.run_decision_fast_path(entity_id=anchor,
        new_state=str(getattr(current, "state", "")), snapshot=snapshot, request_id=request_id)
    progress.stage = "provider_response"
    status = response.get("__status") if isinstance(response, dict) else None
    if type(status) is int and 100 <= status <= 599:
        progress.upstream_status = status
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError("room_lighting_recheck_failed")
    progress.stage = "response_schedule"
    schedule_room_check(owner, response)
    progress.stage = "execution_validation"
    result = response.get("result") or {}
    from .confidence_arbitration_contract import validate_auto_execution_arbitration
    arbitration = validate_auto_execution_arbitration(response, context_snapshot=snapshot)
    if response.get("auto_execute") is True and result.get("actions") and arbitration.allowed:
        progress.stage = "execution"
        return await owner._execute_fast_path_decision_result(result, entity_id=anchor,
            source_label="房间灯控核对", transaction_id=response.get("transaction_id", ""),
            correlation_id=response.get("correlation_id", ""),
            world_snapshot_id=response.get("world_snapshot_id", ""),
            decision_trace=response.get("decision_trace"), trigger="room_lighting_reconciliation",
            active_ai_rollout=response.get("active_ai_rollout"))
    return response


def schedule_room_check(owner: Any, response: dict, *, schedule: Any = None) -> None:
    if getattr(owner, "_room_lighting_stopping", False):
        return
    control = (response.get("result") or {}).get("room_lighting") or {}
    space = control.get("space_id")
    deadlines = [datetime.fromisoformat(control[key]) for key in ("vacancy_due_at", "next_check_at")
                 if control.get(key)]
    due = min(deadlines) if deadlines else None
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
    seconds = (due - owner._ha_local_now()).total_seconds()
    if seconds <= 0:
        # An expired retry is ready now. Other stale deadlines (for example an
        # unresolved vacancy candidate) keep the normal cadence, avoiding a spin.
        seconds = 0 if control.get("reason") == "room_lighting_retry_wait" else 20
    handle = None
    @callback
    def wake(now: Any) -> None:
        if timers.get(space) is not handle:
            return
        timers.pop(space, None)
        owner.hass.async_create_task(reconcile_rooms(owner, now, space_id=space))
    handle = (schedule or async_call_later)(owner.hass, seconds, wake)
    timers[space] = handle
