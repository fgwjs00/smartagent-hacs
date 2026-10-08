"""Existing AI priority and manual-override decisions at the service boundary."""

from __future__ import annotations
from typing import Any
from .service_execution_context import ServiceCallContext
from .action_execution_context import delegates_night_priority_to_core
from .service_execution_errors import ServiceErrorRecorder
from .execution_gate import evaluate_proactive_priority_handoff, evaluate_manual_override_window


def _reentry_decision(host: Any, context: ServiceCallContext, now_ts: float) -> tuple[Any, Any]:
    call, batch = context.call, context.batch
    info = host.device_info.get(call.entity_id, {}) if isinstance(host.device_info, dict) else {}
    if not isinstance(info, dict):
        info = {}
    lineage = batch.decision_contract_lineage
    cycle = str(
        ((lineage or {}).get("occupancy_cycle_id") or "") if isinstance(lineage, dict) else ""
    ).strip()
    existing = (
        host._device_priority_map.get(call.entity_id)
        if isinstance(getattr(host, "_device_priority_map", None), dict)
        else None
    )
    decision = evaluate_proactive_priority_handoff(
        entity_id=call.entity_id,
        service=call.service,
        claim=context.priority_override_claim,
        existing=existing,
        active_space_id=batch.active_space_id,
        target_space_id=context.target_space_id,
        world_snapshot_id=batch.world_snapshot_id,
        decision_time=batch.decision_time,
        occupancy_cycle_id=cycle,
        now_ts=now_ts,
        is_lighting=(call.domain == "light" or str(info.get("capability") or "") == "lighting"),
        max_age_seconds=30,
    )
    return existing, decision


def _is_ai_cycle_record(existing: Any) -> bool:
    return bool(
        isinstance(existing, dict)
        and existing.get("priority") in {3, 4}
        and str(existing.get("source") or "").strip().lower() in {"ai_rule", "ai_infer"}
        and str(existing.get("occupancy_cycle_id") or "").strip()
    )


def _reverses_ai_cycle(host: Any, existing: Any, service: str) -> bool:
    if not _is_ai_cycle_record(existing):
        return False
    state = str(existing.get("state") or "").strip().lower()
    return (
        state in host._OFF_STATES
        and ("turn_on" in service or "open" in service)
        or state not in host._OFF_STATES
        and ("turn_off" in service or "close" in service)
    )


def _manual_override(
    host: Any, context: ServiceCallContext, now_ts: float, errors: ServiceErrorRecorder
) -> bool:
    call = context.call
    with host._user_overrides_lock:
        override = host._user_overrides.get(call.entity_id)
    guard = evaluate_manual_override_window(
        entity_id=call.entity_id,
        service=call.service,
        now_ts=now_ts,
        override=override,
        off_states=host._OFF_STATES,
        window_seconds=getattr(host, "_manual_override_protection_seconds", 0),
    )
    if not guard.allowed and not context.batch.authenticated_user_intent:
        host._sys_log("WARN", f"[manual override protection] {guard.msg}")
        return errors.before(
            guard.msg,
            error_type=guard.error_type or "user_override_protection",
            status=guard.status or "blocked",
        )
    if guard.clear_expired_override:
        with host._user_overrides_lock:
            current = host._user_overrides.get(call.entity_id)
            if current is override or current == override:
                host._user_overrides.pop(call.entity_id, None)
    return True


def evaluate_home_service_priority(
    host: Any,
    context: ServiceCallContext,
    now_ts: float,
    ai_source: str,
    errors: ServiceErrorRecorder,
) -> bool:
    call, batch = context.call, context.batch
    existing, reentry = _reentry_decision(host, context, now_ts)
    if batch.authenticated_user_intent:
        host._sys_log(
            "INFO",
            f"[priority] explicit user command bypassed AI anti-flap guard: {call.entity_id}.{call.service}",
        )
    elif batch.require_world_snapshot_guard and reentry.allowed:
        host._sys_log("INFO", f"[主动优先级交接] {call.entity_id} 使用 Core cycle claim 反向动作")
    elif delegates_night_priority_to_core(batch, call) and _is_ai_cycle_record(existing):
        # Core checks the exact successful night ON/OFF receipt and new activity.
        # Keep the independent human takeover check below for this path too.
        host._sys_log("INFO", f"[起夜优先级交接] {call.entity_id}.{call.service} 交由 Core 复核原动作出处")
    elif _reverses_ai_cycle(host, existing, call.service):
        return errors.before("priority_guard_active", error_type="priority_guard")
    else:
        allowed, reason = host._arbitrate(call.entity_id, ai_source, call.service, call.params)
        if not allowed:
            host._sys_log("WARN", reason)
            return errors.before(
                str(reason or "priority_guard_rejected"), error_type="priority_guard"
            )
    return _manual_override(host, context, now_ts, errors)
