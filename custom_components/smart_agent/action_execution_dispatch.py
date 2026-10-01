"""Immediate and timer registration paths, both using the original service host."""

from __future__ import annotations
from typing import Any
from .action_execution_accounting import pop_service_error
from .action_execution_context import (
    ActionBatchContext,
    ActionExecutionProgress,
    ActionItem,
    DelayedActionCallbacks,
    DelayedActionContext,
)
from .action_execution_delayed import make_delayed_callback
from .action_execution_diagnostics import action_failure_details


def _cancel_previous_timer(host: Any, entity_id: str) -> None:
    if entity_id in host._active_timers:
        host._active_timers[entity_id]()
        del host._active_timers[entity_id]


def _timer_failure_result(
    item: ActionItem, batch: ActionBatchContext, error: Exception, *, code: str
) -> dict[str, Any]:
    return {
        "status": "blocked_or_error", "msg": code, "error": code,
        "error_type": code, "ha_command_status": "not_dispatched",
        **action_failure_details(batch, item.action_seq, error, operation=code),
    }


def _schedule_action(
    host: Any,
    item: ActionItem,
    batch: ActionBatchContext,
    progress: ActionExecutionProgress,
    callbacks: DelayedActionCallbacks,
    *,
    schedule: Any,
    decorate: Any,
) -> None:
    call = item.call
    entry = {
        "entity_id": call.entity_id,
        "service": call.service,
        "status": "scheduled",
        "delay": item.delay,
    }
    entry.update(item.receipt)
    progress.results.append(entry)
    context = DelayedActionContext(
        domain=call.domain,
        service=call.service,
        entity_id=call.entity_id,
        params=call.params,
        reason=call.reason,
        action_seq=item.action_seq,
        target_space_id=item.target_space_id,
        priority_override_claim=item.priority_override_claim,
        batch=batch,
        result=entry,
    )
    callback = make_delayed_callback(host, context, callbacks, decorate=decorate)
    registration_complete = False

    @decorate
    def registered_callback(now: Any) -> None:
        if registration_complete:
            callback(now)

    try:
        cancel = schedule(host.hass, item.delay, registered_callback)
    except Exception as exc:
        entry.update(_timer_failure_result(item, batch, exc, code="action_timer_registration_failed"))
        progress.failed += 1
    else:
        host._active_timers[call.entity_id] = cancel
        registration_complete = True


async def _execute_immediate(
    host: Any,
    item: ActionItem,
    batch: ActionBatchContext,
    progress: ActionExecutionProgress,
    *,
    decision_linked_batch: bool,
) -> None:
    call = item.call
    outcome = await host._do_call_service(
        call.domain,
        call.service,
        call.entity_id,
        call.params,
        call.reason,
        batch.scene_desc,
        batch.trigger_summary,
        batch.transaction_id,
        item.action_seq,
        batch.parent_transaction_id,
        batch.world_snapshot_id,
        batch.correlation_id,
        active_space_id=batch.active_space_id,
        decision_time=batch.decision_time,
        target_space_id=item.target_space_id,
        cmd_source=batch.cmd_source,
        require_world_snapshot_guard=batch.require_world_snapshot_guard,
        priority_override_claim=item.priority_override_claim,
        decision_contract_lineage=batch.decision_contract_lineage,
        user_intent_authority=batch.user_intent_authority,
        prepare_only=decision_linked_batch,
    )
    if decision_linked_batch and isinstance(outcome, dict):
        progress.prepared_batch_calls.append(
            {
                **outcome,
                "original_position": item.original_position,
                "action_seq": item.action_seq,
                "reason": str(call.reason or ""),
                "target_space_id": str(item.target_space_id or "").strip(),
                "result_context": dict(item.receipt),
            }
        )
    elif outcome:
        progress.executed += 1
        progress.results.append({**item.receipt, "status": "ok"})
    else:
        error = pop_service_error(host, batch.transaction_id, item.action_seq, call.entity_id)
        if error.get("ha_command_status") == "skipped":
            progress.results.append({**item.receipt, **error, "status": "skip"})
        else:
            progress.record_failure(
                item.original_position, {**item.receipt, **error, "status": "blocked_or_error"}
            )


async def execute_or_schedule_action(
    host: Any,
    item: ActionItem,
    batch: ActionBatchContext,
    progress: ActionExecutionProgress,
    callbacks: DelayedActionCallbacks,
    *,
    decision_linked_batch: bool,
    schedule: Any,
    decorate: Any,
) -> None:
    try:
        _cancel_previous_timer(host, item.call.entity_id)
    except Exception as exc:
        progress.record_failure(item.original_position, {
            **item.receipt,
            **_timer_failure_result(item, batch, exc, code="previous_action_cancel_failed"),
        })
        return
    if item.delay > 0:
        _schedule_action(
            host, item, batch, progress, callbacks, schedule=schedule, decorate=decorate
        )
    else:
        await _execute_immediate(
            host, item, batch, progress, decision_linked_batch=decision_linked_batch
        )
