"""Initial action guards and their transaction receipts in the existing HA host."""

from __future__ import annotations
import json
from typing import Any
from .action_execution_context import ActionBatchContext, ActionPreparationState
from .action_normalization import action_domain, action_entity_id
from .execution_gate import evaluate_self_trigger_protection


def _remember_guard_result(
    host: Any,
    state: ActionPreparationState,
    action: Any,
    result: dict[str, Any],
    context: ActionBatchContext,
) -> None:
    result.update(context.receipt_metadata())
    state.collector.remember(state.collector.claim_position(action), result)
    entity_id = action_entity_id(action)
    if not isinstance(entity_id, str) or "." not in entity_id:
        return
    current = host.hass.states.get(entity_id)
    if current:
        state.guard_pre_states[entity_id] = current.state


def _isolation_details(host: Any, action: Any, trigger_room: str) -> tuple[str, str, str, bool]:
    entity_id = action_entity_id(action)
    if not entity_id:
        return "", "", "", False
    capability = host._get_action_device_capability(entity_id)
    room = (capability.get("room") or "").strip()
    if not room and hasattr(host, "_get_entity_area"):
        room = (host._get_entity_area(entity_id) or "").strip()
    capability = {**capability, "room": room}
    domain = action_domain(action)
    cross_zone = host._is_cross_zone_action(trigger_room, capability)
    control_spaces = host._resolve_action_control_spaces(capability)
    adjacent = any(
        hasattr(host, "_is_adjacent_room") and host._is_adjacent_room(trigger_room, space)
        for space in control_spaces
        if space
    )
    exempt = (
        (not room and not capability.get("control_zone"))
        or not cross_zone
        or domain in ("climate", "cover", "scene", "script", "vacuum")
        or action.get("is_global", False)
        or adjacent
    )
    return entity_id, domain, room, exempt


def _filter_isolated_actions(
    host: Any, state: ActionPreparationState, context: ActionBatchContext
) -> None:
    filtered = []
    for action in state.actions:
        entity_id, domain, room, exempt = _isolation_details(host, action, context.trigger_room)
        if not entity_id:
            continue
        if exempt:
            filtered.append(action)
            continue
        host._sys_log(
            "WARN",
            f"[区域隔离] 拦截跨区域操作: {entity_id}(属于{room})，本次触发于「{context.trigger_room}」",
        )
        message = f"cross_zone_isolation: {entity_id} belongs to {room or 'unknown'}; trigger_room={context.trigger_room}"
        result = {
            "domain": str(domain or ""),
            "service": str(
                action.get("service") or action.get("action") or action.get("command") or ""
            ).split(".", 1)[-1],
            "entity_id": str(entity_id or ""),
            "status": "blocked_cross_zone_isolation",
            "msg": message,
            "error": message,
            "error_type": "cross_zone_isolation",
        }
        _remember_guard_result(host, state, action, result, context)
    if len(filtered) < len(state.actions):
        host._sys_log(
            "INFO",
            f"[区域隔离] 动作集已精简: {len(state.actions)} -> {len(filtered)} (拦截了 {len(state.actions)-len(filtered)} 个跨区域动作)",
        )
        state.actions = filtered


def _filter_self_triggered_actions(
    host: Any, state: ActionPreparationState, context: ActionBatchContext
) -> None:
    filtered, blocked = [], []
    for action in state.actions:
        entity_id = action_entity_id(action)
        service = str(
            action.get("service") or action.get("action") or action.get("command") or ""
        ).split(".", 1)[-1]
        if not (
            entity_id and service == "turn_on" and entity_id in host._batch_trigger_controllable
        ):
            filtered.append(action)
            continue
        blocked.append(entity_id)
        domain = action_domain(action)
        guard = evaluate_self_trigger_protection(
            entity_id=entity_id,
            service=service,
            trigger_entities=host._batch_trigger_controllable,
        )
        message = (
            guard.msg
            or f"self_trigger_protection: {entity_id} triggered current inference; rejected {service}"
        )
        result = {
            "domain": domain,
            "service": str(service or ""),
            "entity_id": str(entity_id or ""),
            "status": guard.status or "blocked_self_trigger",
            "msg": message,
            "error": message,
            "error_type": guard.error_type or "self_trigger_protection",
        }
        _remember_guard_result(host, state, action, result, context)
    if blocked:
        host._sys_log(
            "INFO",
            f"[自触发预过滤] 移除 {len(blocked)} 个自触发设备的 turn_on 动作: {', '.join(blocked)}",
        )
        state.actions = filtered


async def _finish_guard_rejection(
    host: Any, state: ActionPreparationState, context: ActionBatchContext
) -> Any:
    results = state.collector.ordered_results()
    transaction_id = await host.hass.async_add_executor_job(
        host._begin_transaction_db,
        context.trigger_summary,
        context.scene_desc,
        context.confidence,
        len(state.original_actions),
        json.dumps(state.guard_pre_states, ensure_ascii=False),
        json.dumps(state.original_actions, ensure_ascii=False, default=str),
    )
    if not transaction_id:
        return host._action_execution_result(
            0,
            results=results,
            pre_states=state.guard_pre_states,
            correlation_id=context.correlation_id,
        )
    await host.hass.async_add_executor_job(
        host._complete_transaction_db,
        transaction_id,
        0,
        len(results),
        0,
        json.dumps(results, ensure_ascii=False),
    )
    return host._action_execution_result(
        0,
        transaction_id=transaction_id,
        results=results,
        pre_states=state.guard_pre_states,
        correlation_id=context.correlation_id,
    )


async def apply_initial_batch_guards(
    host: Any, state: ActionPreparationState, context: ActionBatchContext
) -> Any | None:
    should_isolate = bool(
        context.trigger_room
        and not context.is_global_cmd
        and context.cmd_source != "USER_EXPLICIT"
        and not any(kind in context.trigger_summary for kind in ("巡检", "位置变化", "视觉检测"))
    )
    if should_isolate:
        _filter_isolated_actions(host, state, context)
        if not state.actions:
            return await _finish_guard_rejection(host, state, context)
    if not state.actions:
        return host._action_execution_result(0, correlation_id=context.correlation_id)
    if host._batch_trigger_controllable:
        _filter_self_triggered_actions(host, state, context)
        if not state.actions:
            host._sys_log("INFO", "[自触发预过滤] 所有动作均为自触发设备，跳过执行")
            return await _finish_guard_rejection(host, state, context)
    return None
