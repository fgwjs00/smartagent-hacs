"""Non-executing decision outcomes share explicit event and receipt contracts."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .decision_records import SlowDecisionRecords, DecisionExecutionOutcome
from .decision_presentation import SlowDecisionEmitter, rollout_public_reason
from .decision_rollout import DecisionRollout


@dataclass(frozen=True, slots=True)
class DecisionPolicyContext:
    records: SlowDecisionRecords
    emitter: SlowDecisionEmitter
    status: int
    policy_unauthorized_speech: str

    def enqueue(self, outcome: DecisionExecutionOutcome, failure_message: str) -> None:
        if not self.records.transaction_id:
            return
        host = self.emitter.host
        if not host._enqueue_internal_event("decision_execution", self.records.payload(outcome)):
            host._sys_log("WARN", failure_message)

    def emit(
        self, actions: list[dict[str, Any]], *, reason: str, final_outcome: str, fail_closed: bool
    ) -> None:
        self.emitter.emit(
            result_payload=self.records.result,
            status_code=self.status,
            matched=True,
            reason=reason,
            scene_desc=self.records.scene,
            confidence_value=self.records.confidence,
            actions_payload=actions,
            transaction_id_value=self.records.transaction_id,
            executed_count=0,
            final_outcome_value=final_outcome,
            fail_closed=fail_closed,
            record_decision_log=not bool(self.records.transaction_id),
        )


def rejected_action_results(
    actions: list[dict[str, Any]], *, status: str, reason: str
) -> list[dict[str, Any]]:
    return [
        {
            "domain": str(action.get("domain") or ""),
            "service": str(action.get("service") or ""),
            "entity_id": str(action.get("entity_id") or ""),
            "status": status,
            "reason": reason,
        }
        for action in actions
        if isinstance(action, dict)
    ]


def report_rollout_rejection(
    context: DecisionPolicyContext, rollout: DecisionRollout
) -> dict[str, Any]:
    host = context.emitter.host
    bundle = context.emitter.bundle
    result = context.records.result
    transaction_id = context.records.transaction_id
    policy_unauthorized_speech = context.policy_unauthorized_speech
    valid_actions = rollout.selection.actions
    rollout_blocked_actions = rollout.selection.blocked_actions
    rollout_reason, rollout_config, rollout_trace = rollout.reason, rollout.config, rollout.trace
    is_shadow = rollout_reason in {"active_ai_shadow", "proactive_execution_not_permitted"}
    final_outcome = "observe_only" if is_shadow else "blocked"
    action_status = "not_executed" if is_shadow else "blocked"
    public_reason = rollout_public_reason(rollout_reason)
    result["matched"] = True
    result["executed_count"] = 0
    result["auto_execute"] = False
    result["confirm_required"] = False
    result["arbitration_result"] = "blocked_by_rollout"
    result["execution_suppressed_reason"] = public_reason
    result["final_outcome"] = final_outcome
    result["execution_status"] = final_outcome
    action_results = rejected_action_results(
        valid_actions, status=action_status, reason=rollout_reason
    )
    context.enqueue(
        DecisionExecutionOutcome(
            arbitration_result="blocked_by_rollout",
            reason=rollout_reason,
            planned_count=len(valid_actions),
            final_outcome=final_outcome,
            actions=valid_actions,
            authorized_actions=valid_actions,
            rollout_blocked_actions=rollout_blocked_actions,
            action_results=[*action_results, *rollout_blocked_actions],
            rollout=rollout_trace,
        ),
        f"[Decision] rollout decision_execution enqueue failed transaction_id={transaction_id}",
    )
    host._sys_log(
        "INFO",
        f"[Decision] active-AI rollout blocked execution mode={rollout_config.mode} reason={rollout_reason} transaction_id={transaction_id or '-'}",
    )
    context.emit(
        valid_actions, reason=public_reason, final_outcome=final_outcome, fail_closed=not is_shadow
    )
    nested = result.get("result") if isinstance(result.get("result"), dict) else {}
    if bundle.get("is_voice"):
        result["reply"] = policy_unauthorized_speech
        result["speak"] = policy_unauthorized_speech
    else:
        result.setdefault("reply", nested.get("reply") or public_reason)
    result.setdefault("status", "ok")
    return result


def report_learning_observation(
    context: DecisionPolicyContext,
    valid_actions: list[dict[str, Any]],
    rollout_blocked_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    host = context.emitter.host
    result = context.records.result
    transaction_id = context.records.transaction_id
    result["matched"] = True
    result["executed_count"] = 0
    result["execution_suppressed_reason"] = "learning_mode"
    result.setdefault("reason", "learning_mode_observe_only")
    final_outcome = "observe_only"
    result["final_outcome"] = final_outcome
    result["execution_status"] = final_outcome
    action_results = rejected_action_results(
        valid_actions, status="not_executed", reason="learning_mode_observe_only"
    )
    context.enqueue(
        DecisionExecutionOutcome(
            arbitration_result="observe_only",
            reason="learning_mode_observe_only",
            planned_count=len(valid_actions),
            final_outcome=final_outcome,
            actions=valid_actions,
            authorized_actions=valid_actions,
            rollout_blocked_actions=rollout_blocked_actions,
            action_results=[*action_results, *rollout_blocked_actions],
        ),
        f"[Decision] decision_execution enqueue failed transaction_id={transaction_id}",
    )
    host._sys_log(
        "INFO",
        f"[Decision] learning observe-only: received {len(valid_actions)} action(s), executed 0",
    )
    context.emit(
        valid_actions,
        reason=str(result.get("reason") or "learning_mode_observe_only"),
        final_outcome=final_outcome,
        fail_closed=False,
    )
    nested = result.get("result") if isinstance(result.get("result"), dict) else {}
    result.setdefault("reply", nested.get("reply") or "learning_mode_observe_only")
    result.setdefault("status", "ok")
    return result


def observe_committed_fast_path(context: DecisionPolicyContext) -> bool:
    bundle = context.emitter.bundle
    result = context.records.result
    records = context.records
    candidate_actions = records.candidate_actions
    transaction_id = records.transaction_id
    fast_path_execution_audit = (
        bundle.get("fast_path_execution_audit")
        if isinstance(bundle.get("fast_path_execution_audit"), dict)
        else {}
    )
    fast_path_audit_observe_only = bool(
        fast_path_execution_audit
        and str(fast_path_execution_audit.get("final_outcome") or "").strip() == "succeeded"
    )
    if not fast_path_audit_observe_only:
        return False
    # The fast path already crossed the physical-effect boundary.
    # System 2 is an auditor for this occurrence, never a second
    # executor.  Any correction must start from a fresh snapshot as
    # a new decision occurrence instead of replaying this handoff.
    audit_candidates = [dict(item) for item in candidate_actions]
    final_outcome = "observe_only"
    result["matched"] = bool(audit_candidates)
    result["executed_count"] = 0
    result["candidate_action_count"] = len(audit_candidates)
    result["authorized_action_count"] = 0
    result["authorized_actions"] = []
    result["auto_execute"] = False
    result["confirm_required"] = False
    result["arbitration_result"] = "observe_only"
    result["execution_audit_pending"] = False
    result["execution_suppressed_reason"] = "fast_path_execution_already_committed"
    result["reason"] = "fast_path_execution_already_committed"
    result["final_outcome"] = final_outcome
    result["execution_status"] = final_outcome
    context.enqueue(
        DecisionExecutionOutcome(
            arbitration_result="observe_only",
            reason="fast_path_execution_already_committed",
            planned_count=len(candidate_actions),
            final_outcome=final_outcome,
            actions=[],
            authorized_actions=[],
            rollout_blocked_actions=[],
            action_results=[],
            source="ha_slow_fast_path_audit",
            execution_transaction_id="",
            parent_execution_transaction_id=str(
                bundle.get("parent_execution_transaction_id") or ""
            ),
        ),
        "[Decision] fast-path audit decision_execution enqueue failed "
        f"transaction_id={transaction_id}",
    )
    return True
