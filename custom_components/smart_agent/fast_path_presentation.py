"""Fast-path diagnostic events and confirmation display never own device dispatch."""

from __future__ import annotations
from typing import Any
import logging
from .fast_path_request import FastPathRequest
from .fast_path_response import FastPathResponse
from .fast_path_rollout import FastPathRollout

_LOGGER = logging.getLogger("custom_components.smart_agent.fast_path_listener")


def _log_field(value: Any) -> Any:
    return "-" if value is None else value


def _log_response(request: FastPathRequest, decision: FastPathResponse) -> None:
    message, policy, plan = decision.messages, decision.policy, decision.plan
    request.host._sys_log(
        "INFO",
        f"[Add-on FastPath] result status={decision.status} matched={decision.matched} "
        f"path_taken={message.path_taken} reason={policy.reason or '-'} scene={plan.scene or '-'} "
        f"decision_reason={message.decision_reason or '-'} "
        f"arbitration_reason={message.arbitration_reason or '-'} "
        f"confidence={_log_field(plan.confidence)} "
        f"confidence_auto={_log_field(policy.confidence_auto)} "
        f"confidence_notify={_log_field(policy.confidence_notify)} "
        f"confirm_required={policy.confirm_required} "
        f"confirm_suppressed_reason={policy.confirm_suppressed_reason or '-'} "
        f"learning_mode={_log_field(policy.learning_mode)} "
        f"habit_proactive={_log_field(policy.habit_proactive)} "
        f"action_count={plan.action_count} entity={request.trigger.entity_id} "
        f"correlation_id={plan.lineage.correlation_id}",
    )


def _response_event(
    request: FastPathRequest,
    decision: FastPathResponse,
    rollout: FastPathRollout,
    trace: dict[str, Any],
    *,
    execution_suppressed_reason: str,
    audit_pending: bool,
) -> dict[str, Any]:
    return {
        "source": "addon_fast_path",
        "entity_id": request.trigger.entity_id,
        "old_state": request.trigger.old_state,
        "new_state": request.trigger.new_state,
        "status": decision.status,
        "matched": decision.matched,
        "path_taken": decision.messages.path_taken,
        "reason": decision.policy.reason,
        "decision_reason": decision.messages.decision_reason,
        "arbitration_reason": decision.messages.arbitration_reason,
        "scene": decision.plan.scene,
        "confidence": decision.plan.confidence,
        "confidence_auto": decision.policy.confidence_auto,
        "confidence_notify": decision.policy.confidence_notify,
        "threshold": decision.policy.threshold,
        "auto_execute": decision.policy.validation.allowed,
        "arbitration_result": decision.policy.arbitration_result,
        "confirm_required": decision.policy.confirm_required,
        "confirm_suppressed_reason": decision.policy.confirm_suppressed_reason,
        "action_count": decision.plan.action_count,
        "actions": rollout.selection.original_actions,
        "authorized_action_count": len(rollout.selection.actions),
        "authorized_actions": rollout.selection.actions,
        "rollout_blocked_actions": rollout.selection.blocked_actions,
        "transaction_id": decision.plan.lineage.transaction_id,
        "decision_trace": decision.plan.lineage.decision_trace,
        "correlation_id": decision.plan.lineage.correlation_id,
        "world_snapshot_id": decision.plan.lineage.world_snapshot_id,
        "executed": False,
        "execution_status": "pending" if audit_pending else "not_started",
        "provisional_execution": audit_pending,
        "audit_pending": audit_pending,
        "rollback_allowed": audit_pending,
        "execution_suppressed_reason": execution_suppressed_reason,
        "rollout": trace,
        "rollout_scope_filtered_entity_ids": rollout.selection.blocked_entity_ids,
        "fail_closed": decision.policy.fail_closed or not 200 <= decision.status < 300,
        "snapshot": request.diagnostics,
    }


def emit_fast_path_response(
    request: FastPathRequest,
    decision: FastPathResponse,
    rollout: FastPathRollout,
    trace: dict[str, Any],
    *,
    execution_suppressed_reason: str,
    audit_pending: bool,
) -> None:
    _log_response(request, decision)
    request.host._emit_addon_fast_path_event(
        _response_event(
            request,
            decision,
            rollout,
            trace,
            execution_suppressed_reason=execution_suppressed_reason,
            audit_pending=audit_pending,
        )
    )


def emit_fast_path_confirmation(request: FastPathRequest, decision: FastPathResponse) -> None:
    if (
        200 <= decision.status < 300
        and decision.matched
        and decision.policy.confirm_required
        and isinstance(decision.result, dict)
    ):
        confirm_payload = {
            "source": "addon_fast_path",
            "entity_id": request.trigger.entity_id,
            "old_state": request.trigger.old_state,
            "new_state": request.trigger.new_state,
            "scene": decision.plan.scene,
            "confidence": decision.plan.confidence,
            "confidence_auto": decision.policy.confidence_auto,
            "confidence_notify": decision.policy.confidence_notify,
            "action_count": decision.plan.action_count,
            "actions": decision.plan.actions,
            "trigger": f"{request.trigger.entity_id}: {request.trigger.old_state} -> {request.trigger.new_state}",
            "reply": "AI 已命中候选动作，但置信度低于自动执行阈值，等待用户确认。",
            "reason": decision.policy.reason,
            "decision_reason": decision.messages.decision_reason,
            "arbitration_reason": decision.messages.arbitration_reason,
            "path_taken": decision.messages.path_taken,
            "result": decision.result,
            "txn_id": decision.plan.lineage.transaction_id or None,
        }
        try:
            request.host.hass.bus.async_fire("smart_agent_confirm_required", confirm_payload)
        except Exception as exc:
            _LOGGER.debug("[Listeners] smart_agent_confirm_required emit failed: %s", exc)
        request.host._sys_log(
            "INFO",
            f"[Add-on FastPath] confirm_required | entity={request.trigger.entity_id} "
            f"confidence={_log_field(decision.plan.confidence)} "
            f"confidence_auto={_log_field(decision.policy.confidence_auto)} "
            f"confidence_notify={_log_field(decision.policy.confidence_notify)} "
            f"actions={decision.plan.action_count}",
        )
