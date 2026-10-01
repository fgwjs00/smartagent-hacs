"""Ordered single-service preflight without introducing another execution engine."""

from __future__ import annotations
import math
import time
from datetime import datetime
from typing import Any
from .const import MODE_HOME, SOURCE_AI_INFER, SOURCE_AI_RULE
from .execution_gate import (
    evaluate_self_trigger_protection,
    evaluate_automation_conflict_window,
    evaluate_global_suppress_window,
    evaluate_color_temp_mireds_param,
)
from .service_execution_context import ServiceCallContext, PreparedServiceState
from .service_execution_errors import ServiceErrorRecorder
from .service_execution_priority import evaluate_home_service_priority
from .action_execution_diagnostics import action_failure_details


def _already_off(host: Any, context: ServiceCallContext) -> bool:
    call, batch = context.call, context.batch
    state = host.hass.states.get(call.entity_id)
    departure = call.service == "turn_off" and host._looks_like_presence_departure_turnoff(
        reason=str(call.reason or ""),
        scene_desc=str(batch.scene_desc or ""),
        trigger_summary=str(batch.trigger_summary or ""),
    )
    host._clear_service_call_error(batch.transaction_id, context.action_seq, call.entity_id)
    if state and call.service == "turn_off" and state.state == "off" and not departure:
        host._remember_service_call_error(
            batch.transaction_id,
            context.action_seq,
            call.entity_id,
            msg="already_in_target_state",
            status="skipped",
        )
        return True
    return False


def _self_trigger(host: Any, context: ServiceCallContext, errors: ServiceErrorRecorder) -> bool:
    call = context.call
    guard = evaluate_self_trigger_protection(
        entity_id=call.entity_id,
        service=call.service,
        trigger_entities=host._batch_trigger_controllable,
    )
    if not guard.allowed and not context.batch.authenticated_user_intent:
        host._sys_log(
            "WARN",
            f"[自触发保护] {call.entity_id} 触发了本次推理，拒绝 AI 操作该设备 → {call.service}（防止死循环）",
        )
        return errors.before(
            guard.msg,
            error_type=guard.error_type or "self_trigger_protection",
            status=guard.status or "blocked_self_trigger",
        )
    return True


def _automation_records(host: Any, names: Any) -> list[dict[str, Any]]:
    records = []
    for state in host.hass.states.async_all("automation"):
        name = state.attributes.get("friendly_name", "")
        if name not in names:
            continue
        triggered = state.attributes.get("last_triggered")
        if triggered is not None and triggered != "":
            timestamp = (
                triggered.timestamp()
                if hasattr(triggered, "timestamp")
                else datetime.fromisoformat(str(triggered).replace("Z", "+00:00")).timestamp()
            )
            if not math.isfinite(timestamp):
                raise ValueError("automation_trigger_time_invalid")
            records.append({"name": name, "last_triggered_ts": timestamp})
    return records


def _automation_conflict(
    host: Any, context: ServiceCallContext, now_ts: float, errors: ServiceErrorRecorder
) -> bool:
    call = context.call
    names = host._automation_managed_devices.get(call.entity_id)
    if names and not context.batch.authenticated_user_intent:
        try:
            records = _automation_records(host, names)
        except Exception as exc:
            return errors.before(
                "automation_state_read_failed", error_type="automation_state_read_failed",
                status="not_dispatched", failure_details=action_failure_details(
                    context.batch, context.action_seq, exc, operation="automation_state_read"
                ),
            )
        guard = evaluate_automation_conflict_window(
            entity_id=call.entity_id,
            service=call.service,
            managed_automation_names=names,
            automation_records=records,
            now_ts=now_ts,
            window_seconds=host._AUTOMATION_EXEC_WINDOW,
        )
        if not guard.allowed:
            host._sys_log(
                "WARN",
                f"[自动化避让] {call.entity_id} 被自动化「{guard.automation_name}」管辖，"
                f"该自动化 {guard.age_seconds}s 前刚触发，AI 退让 → {call.service}（{host._AUTOMATION_EXEC_WINDOW}s 窗口）",
            )
            return errors.before(
                guard.msg,
                error_type=guard.error_type or "automation_conflict",
                status=guard.status or "blocked",
            )
    return True


def _global_suppress(
    host: Any, context: ServiceCallContext, now_ts: float, errors: ServiceErrorRecorder
) -> bool:
    call = context.call
    guard = evaluate_global_suppress_window(
        entity_id=call.entity_id,
        service=call.service,
        now_ts=now_ts,
        suppress_until=host._global_suppress_until,
        suppress_reason=host._global_suppress_reason,
    )
    if not guard.allowed:
        host._sys_log(
            "WARN",
            f"[P0 全局抑制] {host._global_suppress_reason}"
            f"（剩余 {guard.remaining_seconds}s）→ 拒绝 {call.entity_id}.{call.service}",
        )
        return errors.before(
            guard.msg,
            error_type=guard.error_type or "global_suppress",
            status=guard.status or "blocked",
        )
    return True


def _service_params(
    host: Any, context: ServiceCallContext, errors: ServiceErrorRecorder
) -> dict[str, Any] | None:
    call = context.call
    params = {key: value for key, value in call.params.items() if key != "entity_id"}
    guard = evaluate_color_temp_mireds_param(
        entity_id=call.entity_id, service=call.service, params=params
    )
    if not guard.allowed:
        value = str(guard.msg).split(":", 1)[1] if ":" in guard.msg else ""
        host._sys_log("ERROR", f"[动作] {call.entity_id} color_temp({value}) 非法，拒绝执行")
        errors.before(
            guard.msg,
            error_type=guard.error_type or "invalid_action_param",
            status=guard.status or "blocked_invalid_params",
        )
        return None
    if guard.normalized_params is not None:
        params = dict(guard.normalized_params)
    if guard.color_temp_kelvin:
        host._sys_log(
            "INFO",
            f"[动作] {call.entity_id} color_temp({guard.color_temp_mireds}mireds)"
            f" → color_temp_kelvin({guard.color_temp_kelvin}K) 自动转换",
        )
    return params


def prepare_service(
    host: Any, context: ServiceCallContext, errors: ServiceErrorRecorder
) -> PreparedServiceState | None:
    if _already_off(host, context) or not _self_trigger(host, context, errors):
        return None
    now_ts = time.time()
    if not _automation_conflict(host, context, now_ts, errors):
        return None
    ai_source = SOURCE_AI_INFER
    if "🔒" in context.call.reason or "锁定" in context.call.reason:
        ai_source = SOURCE_AI_RULE
    if not _global_suppress(host, context, now_ts, errors):
        return None
    if host._mode == MODE_HOME and not evaluate_home_service_priority(
        host, context, now_ts, ai_source, errors
    ):
        return None
    canonical_service = str(context.call.service or "").strip().lower().split(".", 1)[-1]
    new_state = "on" if canonical_service in {"turn_on", "open_cover"} else "off"
    params = _service_params(host, context, errors)
    if params is None:
        return None
    host._clear_service_call_error(
        context.batch.transaction_id, context.action_seq, context.call.entity_id
    )
    return PreparedServiceState(now_ts, ai_source, new_state, params)
