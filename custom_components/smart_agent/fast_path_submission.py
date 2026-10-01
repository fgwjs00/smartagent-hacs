"""Fast-path submission through the existing execution and audit boundaries."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .fast_path_request import FastPathRequest, schedule_fast_path_remainder
from .fast_path_response import FastPathResponse
from .fast_path_rollout import FastPathRollout
from .service_contracts import STATEFUL_EXECUTION_DOMAINS


@dataclass(frozen=True, slots=True)
class FastPathExecution:
    request: FastPathRequest
    response: dict
    decision: FastPathResponse
    rollout: FastPathRollout
    trace: dict
    result_payload: dict
    suppressed_reason: str
    audit_pending: bool


def prepare_fast_path_execution(
    request: FastPathRequest,
    response: dict,
    decision: FastPathResponse,
    rollout: FastPathRollout,
) -> FastPathExecution:
    reason = decision.policy.execution_suppressed_reason
    if decision.matched and not rollout.decision.allow_execution and not reason:
        reason = rollout.decision.reason
    trace = rollout.decision.as_trace()
    payload = dict(decision.result) if isinstance(decision.result, dict) else {}
    payload["actions"] = rollout.selection.actions
    if rollout.selection.blocked_actions:
        payload["rollout_original_actions"] = rollout.selection.original_actions
        payload["rollout_blocked_actions"] = rollout.selection.blocked_actions
    raw_result = decision.result if isinstance(decision.result, dict) else {}
    audit_pending = bool(
        decision.matched
        and raw_result.get("source") != "room_lighting"
        and decision.policy.validation.allowed
        and not reason
        and request.host._fast_path_result_allows_slow_audit(rollout.selection.actions)
    )
    return FastPathExecution(
        request, response, decision, rollout, trace, payload, reason, audit_pending
    )


async def _dispatch(context: FastPathExecution) -> dict[str, Any]:
    request, lineage = context.request, context.decision.plan.lineage
    return await request.host._execute_fast_path_decision_result(
        context.result_payload,
        entity_id=request.trigger.entity_id,
        source_label="AddonFastPath",
        transaction_id=lineage.transaction_id,
        correlation_id=lineage.correlation_id,
        world_snapshot_id=lineage.world_snapshot_id,
        decision_trace=lineage.decision_trace,
        trigger=request.trigger.summary,
        active_ai_rollout=context.rollout.payload,
    )


def _record_suppressed(context: FastPathExecution) -> None:
    request, plan = context.request, context.decision.plan
    lineage = plan.lineage
    request.host._enqueue_fast_path_execution_audit(
        transaction_id=lineage.transaction_id,
        correlation_id=lineage.correlation_id,
        world_snapshot_id=lineage.world_snapshot_id,
        decision_trace=lineage.decision_trace,
        trigger=request.trigger.summary,
        scene=plan.scene,
        confidence=plan.confidence,
        actions=plan.actions,
        execution_result=0,
        execution_suppressed_reason=context.suppressed_reason,
        rollout=context.trace,
    )


async def _report_suppressed(context: FastPathExecution) -> None:
    request = context.request
    if not await context.decision.claim.finalize(
        "fast_path_execution_suppressed",
        required_for_action=False,
    ):
        return
    request.host._sys_log(
        "INFO",
        f"[Add-on FastPath] execution suppressed | entity={request.trigger.entity_id} "
        f"reason={context.suppressed_reason}",
    )
    if context.suppressed_reason.startswith("active_ai_"):
        await _dispatch(context)
    else:
        _record_suppressed(context)
    schedule_fast_path_remainder(request, context.response)


async def _execute_protected(context: FastPathExecution) -> dict[str, Any]:
    host, entity_id = context.request.host, context.request.trigger.entity_id
    previous = getattr(host, "_batch_trigger_controllable", set())
    domain = entity_id.split(".")[0]
    if domain in STATEFUL_EXECUTION_DOMAINS:
        host._batch_trigger_controllable = {entity_id}
        host._sys_log(
            "INFO",
            f"[自触发保护] FastPath 可控设备触发: {entity_id}，AI 不可反向操作该设备",
        )
    try:
        return await _dispatch(context)
    finally:
        host._batch_trigger_controllable = previous


async def _handoff_audit(
    context: FastPathExecution,
    execution_audit: dict[str, Any],
    causal_event: dict | None,
) -> None:
    request, claim = context.request, context.decision.claim
    if claim.current:
        execution_audit["event_claim"] = dict(claim.current)
    if context.audit_pending and execution_audit.get("final_outcome") == "succeeded":
        request.host._schedule_inference(
            request.trigger.entity_id,
            request.trigger.summary,
            request.trigger.new_state,
            one_off_prompt=request.host._fast_path_slow_audit_prompt(),
            _allow_learning_mode_inference=True,
            causal_event=causal_event,
            source_trace_context=execution_audit,
        )
    elif context.audit_pending:
        await claim.finalize("fast_path_execution_failed", required_for_action=False)


async def submit_fast_path(context: FastPathExecution, causal_event: dict | None) -> None:
    if context.suppressed_reason:
        await _report_suppressed(context)
        return
    if not context.audit_pending and not await context.decision.claim.finalize(
        "fast_path_completed",
        required_for_action=True,
    ):
        return
    context.request.host._sys_log(
        "INFO",
        f"[Add-on FastPath] 命中规则: {context.decision.result.get('scene', 'FastPath')}",
    )
    execution_audit = await _execute_protected(context)
    await _handoff_audit(context, execution_audit, causal_event)
    schedule_fast_path_remainder(context.request, context.response)
