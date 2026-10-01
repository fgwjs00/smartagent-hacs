"""Confidence admission and non-executing confirmation outcomes for slow decisions."""

from __future__ import annotations
from dataclasses import dataclass
import logging
from typing import Any
from .execution_gate import ThinExecutionGateResult, evaluate_slow_brain_confidence_gate
from .confidence_arbitration_contract import (
    AutoExecutionArbitrationValidation,
    apply_arrival_lighting_confirmation_gate,
    pending_confirmation_allowed,
    validate_auto_execution_arbitration,
)
from .decision_policy_outcomes import DecisionPolicyContext, rejected_action_results
from .decision_records import DecisionExecutionOutcome

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DecisionConfidence:
    arbitration_result: str
    gate: ThinExecutionGateResult
    validation: AutoExecutionArbitrationValidation
    confirm_required: bool

    @property
    def local_block(self) -> bool:
        return not self.gate.allowed

    @property
    def auto_execute(self) -> bool:
        return self.validation.allowed and self.gate.allowed

    @property
    def fail_closed(self) -> bool:
        return (
            self.gate.log_code == "confidence_invalid"
            if self.local_block
            else self.validation.reason
            in {"confidence_arbitration_missing", "confidence_arbitration_invalid"}
        )


@dataclass(frozen=True, slots=True)
class ConfidenceRejection:
    reason: str
    public_reason: str
    final_outcome: str
    arbitration_result: str


def prepare_decision_confidence(
    context: DecisionPolicyContext, actions: list[dict[str, Any]]
) -> DecisionConfidence:
    result, bundle = context.records.result, context.emitter.bundle
    apply_arrival_lighting_confirmation_gate(result, actions=actions, context_snapshot=bundle)
    arbitration = str(result.get("arbitration_result") or "").strip()
    gate = evaluate_slow_brain_confidence_gate(
        confidence=result.get("confidence"), threshold=context.emitter.host.confidence_auto
    )
    validation = validate_auto_execution_arbitration(
        result if gate.log_code != "confidence_invalid" else {}, context_snapshot=bundle
    )
    confirm_required = pending_confirmation_allowed(
        validation.reason, local_confidence_block=not gate.allowed, payload=result
    )
    return DecisionConfidence(arbitration, gate, validation, confirm_required)


def _rejection_reason(result: dict[str, Any], admission: DecisionConfidence) -> str:
    decision_reason = str(result.get("reason") or "").strip()
    if admission.local_block:
        return admission.gate.log_code or "confidence_invalid"
    if admission.validation.reason in {
        "confidence_arbitration_missing",
        "confidence_arbitration_invalid",
    }:
        reason = admission.validation.reason
        if decision_reason and decision_reason != reason:
            result.setdefault("decision_reason", decision_reason)
        return reason
    return admission.validation.reason


def _apply_rejection(
    context: DecisionPolicyContext, admission: DecisionConfidence
) -> ConfidenceRejection:
    result = context.records.result
    reason = _rejection_reason(result, admission)
    public_reason = "置信度未达到自动执行阈值" if admission.local_block else reason
    if admission.local_block:
        outcome = "blocked"
    elif admission.confirm_required:
        outcome = "pending_confirmation"
    else:
        outcome = "observe_only"
    result["matched"] = True
    result["executed_count"] = 0
    result["execution_suppressed_reason"] = public_reason
    result["final_outcome"] = outcome
    result["execution_status"] = outcome
    arbitration = admission.arbitration_result
    if admission.local_block:
        result["confidence_auto"] = context.emitter.host.confidence_auto
        result["threshold"] = context.emitter.host.confidence_auto
        result["auto_execute"] = False
        result["confirm_required"] = False
        result["arbitration_result"] = "blocked"
        result["reason"] = public_reason
        arbitration = "blocked"
    return ConfidenceRejection(reason, public_reason, outcome, arbitration)


def _emit_confirmation(
    context: DecisionPolicyContext, rejection: ConfidenceRejection, actions: list[dict[str, Any]]
) -> None:
    result, records = context.records.result, context.records
    try:
        context.emitter.host.hass.bus.async_fire(
            "smart_agent_confirm_required",
            {
                "source": "ha_slow_decision",
                "trigger": context.emitter.trigger_public_summary,
                "scene": records.scene,
                "confidence": records.confidence,
                "confidence_auto": result.get("confidence_auto"),
                "confidence_notify": result.get("confidence_notify"),
                "threshold": result.get("threshold"),
                "arbitration_result": rejection.arbitration_result,
                "confirm_required": True,
                "reason": rejection.reason,
                "actions": actions,
                "action_count": len(actions),
                "transaction_id": records.transaction_id,
                "result": result,
            },
        )
    except Exception as exc:
        _LOGGER.debug("[Coordinator] slow confirmation emit failed: %s", exc)


def _set_confirmation_reply(
    context: DecisionPolicyContext, admission: DecisionConfidence, rejection: ConfidenceRejection
) -> None:
    result, bundle = context.records.result, context.emitter.bundle
    nested = result.get("result") if isinstance(result.get("result"), dict) else {}
    if admission.local_block:
        result["reply"] = (
            context.policy_unauthorized_speech
            if bundle.get("is_voice")
            else rejection.public_reason
        )
        if bundle.get("is_voice"):
            result["speak"] = context.policy_unauthorized_speech
    else:
        result.setdefault(
            "reply",
            nested.get("reply")
            or ("等待用户确认" if admission.confirm_required else "置信度不足，仅记录未执行"),
        )
    result.setdefault("status", "ok")


def _schedule_remainder(context: DecisionPolicyContext) -> None:
    result, bundle = context.records.result, context.emitter.bundle
    if isinstance(result.get("room_remainder_ref"), dict):
        from .room_remainder_runtime import schedule_room_remainder

        schedule_room_remainder(
            context.emitter.host,
            result,
            entity_id=str(bundle.get("trigger_entity_id") or ""),
            trigger=context.records.trigger,
            new_state=str(bundle.get("trigger_new_state") or ""),
        )


def report_confidence_rejection(
    context: DecisionPolicyContext,
    admission: DecisionConfidence,
    actions: list[dict[str, Any]],
    blocked_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    rejection = _apply_rejection(context, admission)
    action_results = rejected_action_results(
        actions,
        status="blocked" if admission.local_block else "not_executed",
        reason=rejection.reason,
    )
    context.enqueue(
        DecisionExecutionOutcome(
            confirm_required=admission.confirm_required,
            arbitration_result=rejection.arbitration_result or "missing",
            reason=rejection.reason,
            planned_count=len(actions),
            final_outcome=rejection.final_outcome,
            actions=actions,
            authorized_actions=actions,
            rollout_blocked_actions=blocked_actions,
            action_results=[*action_results, *blocked_actions],
        ),
        f"[Decision] decision_execution enqueue failed transaction_id={context.records.transaction_id}",
    )
    if admission.confirm_required:
        _emit_confirmation(context, rejection, actions)
    context.emitter.host._sys_log(
        "INFO",
        f"[决策] 置信度仲裁禁止自动执行 result={rejection.arbitration_result or 'missing'} "
        f"confidence={context.records.confidence} threshold={context.records.result.get('threshold')} reason={rejection.reason}",
    )
    context.emit(
        actions,
        reason=rejection.public_reason,
        final_outcome=rejection.final_outcome,
        fail_closed=admission.fail_closed,
    )
    _set_confirmation_reply(context, admission, rejection)
    _schedule_remainder(context)
    return context.records.result
