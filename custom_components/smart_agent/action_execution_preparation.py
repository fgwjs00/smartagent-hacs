"""Normalization and transaction initialization before the existing HA dispatch."""

from __future__ import annotations
import json
from typing import Any
from .action_normalization import InvalidActionDelay, action_delay_seconds
from .action_execution_context import (
    ActionBatchContext,
    ActionPreparationState,
    ActionTransactionStart,
)


def _normalize_batch(host: Any, state: ActionPreparationState, context: ActionBatchContext) -> None:
    state.pre_states = dict(state.guard_pre_states)
    for raw in state.actions:
        action = host._normalize_action(
            raw, allow_fuzzy_entity_match=not context.require_world_snapshot_guard
        )
        state.normalized_actions.append((state.collector.claim_position(raw), raw, action))
        entity_id = action.get("entity_id", "")
        if entity_id and isinstance(entity_id, str) and "." in entity_id:
            current = host.hass.states.get(entity_id)
            if current:
                state.pre_states[entity_id] = current.state


def _has_delayed_node(state: ActionPreparationState) -> bool:
    # Validate every value before short-circuiting, so a later invalid node cannot be hidden.
    delays = [action_delay_seconds(action, action_seq=position + 1)
              for position, _raw, action in state.normalized_actions]
    return any(delay > 0 for delay in delays)


def _record_batch_rejection(
    state: ActionPreparationState, decision_transaction_id: str, *, reason: str, status: str,
    invalid_action_seq: int | None = None,
) -> None:
    for position, _raw, action in state.normalized_actions:
        params = action.get("params")
        result = {
            "domain": str(action.get("domain") or ""),
            "service": str(action.get("service") or ""),
            "entity_id": str(action.get("entity_id") or ""),
            "status": status,
            "msg": reason,
            "error": reason,
            "error_type": reason,
            "ha_command_status": "not_dispatched",
            "decision_trace": {"decision_transaction_id": decision_transaction_id},
        }
        if isinstance(params, dict) and params:
            result["params"] = dict(params)
        if invalid_action_seq is not None:
            result["invalid_action_seq"] = invalid_action_seq
        state.collector.remember(position, result)


def _record_transaction_start_failure(
    state: ActionPreparationState, context: ActionBatchContext
) -> None:
    for position, _raw, action in state.normalized_actions:
        params = action.get("params")
        result = {
            "domain": str(action.get("domain") or ""),
            "service": str(action.get("service") or ""),
            "entity_id": str(action.get("entity_id") or ""),
            "status": "blocked_or_error",
            "msg": "transaction_start_failed",
            "error": "transaction_start_failed",
            "error_type": "transaction_start_failed",
            "ha_command_status": "not_dispatched",
        }
        if isinstance(params, dict) and params:
            result["params"] = dict(params)
        reason = str(action.get("reason") or "").strip()
        if reason:
            result["reason"] = reason
        result.update(context.receipt_metadata())
        state.collector.remember(position, result)


async def prepare_action_transaction(
    host: Any,
    state: ActionPreparationState,
    context: ActionBatchContext,
    *,
    decision_linked_batch: bool,
    decision_transaction_id: str,
) -> ActionTransactionStart:
    _normalize_batch(host, state, context)
    invalid_delay = False
    invalid_action_seq = None
    try:
        delayed = _has_delayed_node(state)
    except InvalidActionDelay as exc:
        invalid_delay, delayed = True, False
        invalid_action_seq = exc.action_seq
    if invalid_delay or (decision_linked_batch and delayed):
        _record_batch_rejection(
            state, decision_transaction_id,
            reason="action_delay_seconds_invalid" if invalid_delay else "decision_linked_batch_delayed_node_not_authorized",
            status="blocked_invalid_action_delay" if invalid_delay else "blocked_decision_linked_batch_delayed_node",
            invalid_action_seq=invalid_action_seq,
        )
        return ActionTransactionStart(
            0,
            host._action_execution_result(
                0,
                results=state.collector.ordered_results(),
                pre_states=state.pre_states,
                correlation_id=context.correlation_id,
            ),
        )
    transaction_id = await host.hass.async_add_executor_job(
        host._begin_transaction_db,
        context.trigger_summary,
        context.scene_desc,
        context.confidence,
        len(state.original_actions),
        json.dumps(state.pre_states, ensure_ascii=False),
        json.dumps(state.original_actions, ensure_ascii=False, default=str),
    )
    if not transaction_id:
        host._sys_log(
            "WARN", "[事务] 事务记录写入失败（DB锁/磁盘等），已中止动作执行以保持审计一致性"
        )
        _record_transaction_start_failure(state, context)
        return ActionTransactionStart(
            0,
            host._action_execution_result(
                0,
                results=state.collector.ordered_results(),
                pre_states=state.pre_states,
                correlation_id=context.correlation_id,
            ),
        )
    return ActionTransactionStart(transaction_id)
