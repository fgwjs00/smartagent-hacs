"""Submit exact slow-decision actions and project existing structured receipts."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .decision_policy_outcomes import DecisionPolicyContext
from .decision_records import DecisionExecutionOutcome
from .execution_audit import project_execution_audit


@dataclass(frozen=True, slots=True)
class DecisionSubmission:
    executed: int
    transaction_id: str
    correlation_id: str
    final_outcome: str
    action_results: list[dict[str, Any]]


def _correlation_id(context: DecisionPolicyContext) -> str:
    result, bundle = context.records.result, context.emitter.bundle
    details = result.get("details") if isinstance(result.get("details"), dict) else {}
    return str(
        result.get("correlation_id")
        or details.get("correlation_id")
        or bundle.get("parent_correlation_id")
        or ""
    ).strip()


def _decision_time(result: dict[str, Any]) -> str:
    return str(
        result.get("decision_time")
        or (
            result.get("result", {}).get("decision_time")
            if isinstance(result.get("result"), dict)
            else ""
        )
        or ""
    ).strip()


async def _dispatch(
    context: DecisionPolicyContext,
    actions: list[dict[str, Any]],
    active_space_id: str,
    authority: Any,
    correlation_id: str,
) -> Any:
    records, bundle = context.records, context.emitter.bundle
    result = records.result
    # The exact Core-selected entity/service/parameters stay on the canonical path.
    return await context.emitter.host._execute_actions(
        actions,
        trigger_summary=str(records.trigger or ""),
        scene_desc=records.scene,
        confidence=records.confidence,
        trigger_room=str(bundle.get("trigger_room") or result.get("trigger_room") or ""),
        parent_transaction_id=records.transaction_id,
        cmd_source=str(bundle.get("cmd_source") or result.get("cmd_source") or ""),
        world_snapshot_id=records.world_snapshot_id,
        correlation_id=correlation_id,
        active_space_id=active_space_id,
        decision_time=_decision_time(result),
        require_world_snapshot_guard=True,
        direct_entity_only=True,
        decision_contract_lineage=records.lineage,
        user_intent_authority=authority,
    )


def _record_submission(
    context: DecisionPolicyContext,
    actions: list[dict[str, Any]],
    blocked_actions: list[dict[str, Any]],
    submission: DecisionSubmission,
    arbitration_result: str,
) -> None:
    records = context.records
    audit_results = [
        dict(item)
        for item in [*submission.action_results, *blocked_actions]
        if isinstance(item, dict)
    ]
    training_sample = context.emitter.host._build_training_sample_payload(
        bundle=context.emitter.bundle,
        actions=actions,
        confidence=records.confidence,
        final_outcome=submission.final_outcome,
        decision_id=records.decision_id,
        transaction_id=records.transaction_id,
        execution_transaction_id=submission.transaction_id,
        world_snapshot_id=records.world_snapshot_id,
        planned_count=len(actions),
        executed_count=submission.executed,
        action_results=submission.action_results,
    )
    context.enqueue(
        DecisionExecutionOutcome(
            auto_execute=True,
            arbitration_result=arbitration_result,
            reason=str(records.result.get("reason") or "confidence_threshold_met"),
            planned_count=len(actions),
            executed_count=submission.executed,
            final_outcome=submission.final_outcome,
            actions=actions,
            authorized_actions=actions,
            rollout_blocked_actions=blocked_actions,
            action_results=audit_results,
            training_sample=training_sample,
            execution_transaction_id=submission.transaction_id,
            correlation_id=submission.correlation_id,
        ),
        f"[决策] decision_execution 回写入队失败 transaction_id={records.transaction_id}",
    )


async def submit_slow_decision(
    context: DecisionPolicyContext,
    actions: list[dict[str, Any]],
    blocked_actions: list[dict[str, Any]],
    *,
    active_space_id: str,
    authority: Any,
    arbitration_result: str,
) -> DecisionSubmission:
    correlation = _correlation_id(context)
    execution_result = await _dispatch(context, actions, active_space_id, authority, correlation)
    audit = project_execution_audit(
        actions, execution_result, correlation_id=correlation,
        missing_reason="ha_execute_actions_missing_structured_result",
    )
    transaction_id = (
        str(getattr(execution_result, "transaction_id", "") or "unknown").strip() or "unknown"
    )
    result = context.records.result
    result["executed_count"] = audit.executed
    result["final_outcome"] = audit.final_outcome
    result["execution_status"] = audit.final_outcome
    if audit.integrity_reason:
        result["receipt_integrity_reason"] = audit.integrity_reason
        result["unconfirmed_count"] = audit.unconfirmed_count
        context.emitter.host._sys_log(
            "WARN", f"[决策] execution_receipt_unconfirmed transaction_id={transaction_id} "
            f"correlation_id={correlation} reason={audit.integrity_reason}",
        )
    submission = DecisionSubmission(
        audit.executed, transaction_id, correlation, audit.final_outcome, audit.action_results,
    )
    _record_submission(context, actions, blocked_actions, submission, arbitration_result)
    context.emitter.host._sys_log(
        "INFO", f"[决策] add-on 返回 {len(actions)} 个动作，回执确认执行 {audit.executed} 个，结果 {audit.final_outcome}"
    )
    return submission
