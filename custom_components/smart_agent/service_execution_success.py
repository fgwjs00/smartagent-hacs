"""Shared post-success effects with the existing batch/immediate presentation."""

from __future__ import annotations
import time
from typing import Any
from .service_execution_context import ServiceCallContext, PreparedServiceState


def _remember_action_state(
    host: Any, context: ServiceCallContext, prepared: PreparedServiceState
) -> None:
    call, batch = context.call, context.batch
    if call.domain in ("scene", "script") and call.service == "turn_on":
        host._scene_last_exec[call.entity_id] = time.time()
    host._last_ai_actions[call.entity_id] = {
        "state": prepared.ai_new_state,
        "time": prepared.now_ts,
        "service": f"{call.domain}.{call.service}",
        "scene": batch.scene_desc,
        "trigger": batch.trigger_summary,
        "origin": "smartagent",
        "actor": "smartagent:execution",
        "decision_id": str(batch.parent_transaction_id or "unknown"),
        "transaction_id": str(batch.parent_transaction_id or "unknown"),
        "execution_transaction_id": str(batch.transaction_id or "unknown"),
        "world_snapshot_id": str(batch.world_snapshot_id or "unknown"),
        "correlation_id": batch.correlation_id,
    }


def _event_metadata(context: ServiceCallContext, *, prepared_batch: bool) -> dict[str, Any]:
    call, batch = context.call, context.batch
    result = {
        "detail": f"{call.entity_id} -> {call.service}",
        "domain": call.domain,
        "service": call.service,
        "entity_id": call.entity_id,
    }
    include_params = (
        bool(call.params) if prepared_batch else isinstance(call.params, dict) and bool(call.params)
    )
    if include_params:
        result["params"] = dict(call.params)
    if call.reason:
        result["reason"] = call.reason
    result.update(batch.receipt_metadata())
    if batch.transaction_id:
        result["execution_transaction_id"] = int(batch.transaction_id)
    parent = str(batch.parent_transaction_id or "").strip()
    if parent:
        result["parent_transaction_id"] = parent
        result["decision_trace"] = {
            "available": True,
            "transaction_id": parent,
            "url": f"/decision-trace/{parent}",
        }
    if batch.correlation_id:
        result["correlation_id"] = batch.correlation_id
    return result


def _record_event(host: Any, context: ServiceCallContext, *, prepared_batch: bool) -> None:
    call, batch = context.call, context.batch
    metadata = _event_metadata(context, prepared_batch=prepared_batch)
    host.hass.async_add_executor_job(
        host._record_event,
        "AI_Action",
        metadata["detail"],
        call.entity_id,
        "on" if "turn_on" in call.service else "off",
        "ai",
        None,
        batch.transaction_id,
        context.action_seq,
        metadata,
    )


def _departure_cooldown(host: Any, context: ServiceCallContext, *, prepared_batch: bool) -> None:
    call, batch = context.call, context.batch
    if call.service == "turn_off" and batch.trigger_summary:
        text = batch.trigger_summary.lower()
        if any(key in text for key in ("离开", "departure", "无人", "empty", "人员离开")):
            room = (host.device_info.get(call.entity_id) or {}).get("room", "")
            if room and hasattr(host, "_last_departure_turnoff_time"):
                host._last_departure_turnoff_time[room] = time.time()
                if not prepared_batch:
                    host._sys_log(
                        "INFO", f"[冷却保护] {room} 检测到离开关灯，设置5分钟巡检冷却窗口"
                    )


def _queue_verification(host: Any, context: ServiceCallContext, *, prepared_batch: bool) -> None:
    call, batch = context.call, context.batch
    expected = "on" if ("turn_on" in call.service or "open" in call.service) else "off"
    if len(host._pending_verifications) < host._VERIFY_QUEUE_MAX:
        parent = (
            batch.parent_transaction_id
            if prepared_batch
            else str(batch.parent_transaction_id or "").strip()
        )
        host._pending_verifications.append(
            {
                "entity_id": call.entity_id,
                "domain": call.domain,
                "service": call.service,
                "expected_state": expected,
                "reason": call.reason,
                "fire_time": time.time(),
                "retry": 0,
                "transaction_id": batch.transaction_id,
                "action_seq": context.action_seq,
                "parent_transaction_id": str(parent or "unknown"),
                "world_snapshot_id": str(batch.world_snapshot_id or "unknown"),
                "correlation_id": batch.correlation_id,
            }
        )


async def record_service_success(
    host: Any,
    context: ServiceCallContext,
    prepared: PreparedServiceState,
    *,
    occupancy_cycle_id: str,
    prepared_batch: bool,
) -> None:
    call, batch = context.call, context.batch
    if prepared_batch:
        host._last_inference[call.entity_id] = prepared.now_ts
    _remember_action_state(host, context, prepared)
    with host._user_overrides_lock:
        host._user_overrides.pop(call.entity_id, None)
    if occupancy_cycle_id:
        host._record_device_operation(
            call.entity_id,
            prepared.ai_source,
            prepared.ai_new_state,
            call.params,
            occupancy_cycle_id=occupancy_cycle_id,
        )
    else:
        host._record_device_operation(
            call.entity_id, prepared.ai_source, prepared.ai_new_state, call.params
        )
    _record_event(host, context, prepared_batch=prepared_batch)
    _departure_cooldown(host, context, prepared_batch=prepared_batch)
    if prepared_batch:
        status = f"{host.get_device_name(call.entity_id)} -> {call.service} ({call.reason[:30]})"
    else:
        status = f"{host.get_device_name(call.entity_id)} → {call.service}（{call.reason[:30]}）"
    await host._async_update_status("运行中", status)
    _queue_verification(host, context, prepared_batch=prepared_batch)
    if call.domain == "climate" and "turn_on" in call.service:
        await host._register_env_feedback(call.entity_id)
