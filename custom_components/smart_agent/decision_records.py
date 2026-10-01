"""Typed construction of slow decision execution records, without owning dispatch."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionExecutionOutcome:
    planned_count: int
    actions: list[dict[str, Any]]
    authorized_actions: list[dict[str, Any]]
    action_results: list[dict[str, Any]]
    final_outcome: str
    arbitration_result: str
    reason: str
    rollout_blocked_actions: list[dict[str, Any]] = field(default_factory=list)
    executed_count: int = 0
    auto_execute: bool = False
    confirm_required: bool = False
    training_sample: dict[str, Any] | None = None
    source: str = "ha_slow_decision"
    execution_transaction_id: str | None = None
    parent_execution_transaction_id: str | None = None
    correlation_id: str | None = None
    rollout: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SlowDecisionRecords:
    result: dict[str, Any]
    transaction_id: str
    trigger: str
    scene: str
    confidence: int
    candidate_actions: list[dict[str, Any]]
    decision_id: str
    world_snapshot_id: str
    lineage: dict[str, Any]

    def payload(self, outcome: DecisionExecutionOutcome) -> dict[str, Any]:
        record = {
            "transaction_id": self.transaction_id,
            "trigger": str(self.trigger or ""),
            "scene": self.scene,
            "confidence": self.confidence,
            "confidence_auto": self.result.get("confidence_auto"),
            "confidence_notify": self.result.get("confidence_notify"),
            "threshold": self.result.get("threshold"),
            "auto_execute": outcome.auto_execute,
            "confirm_required": outcome.confirm_required,
            "arbitration_result": outcome.arbitration_result,
            "reason": outcome.reason,
            "planned_count": outcome.planned_count,
            "candidate_action_count": len(self.candidate_actions),
            "authorized_action_count": len(outcome.authorized_actions),
            "executed_count": outcome.executed_count,
            "final_outcome": outcome.final_outcome,
            "actions": outcome.actions,
            "candidate_actions": self.candidate_actions,
            "authorized_actions": outcome.authorized_actions,
            "rollout_blocked_actions": outcome.rollout_blocked_actions,
            "action_results": outcome.action_results,
            "training_sample": outcome.training_sample,
            "source": outcome.source,
            "origin": "smartagent",
            "actor": "smartagent:" + outcome.source,
            "decision_id": self.decision_id,
            "world_snapshot_id": self.world_snapshot_id,
            "lineage": self.lineage,
        }
        if outcome.execution_transaction_id is not None:
            record["execution_transaction_id"] = outcome.execution_transaction_id
        if outcome.parent_execution_transaction_id is not None:
            record["parent_execution_transaction_id"] = outcome.parent_execution_transaction_id
        if outcome.correlation_id is not None:
            record["correlation_id"] = outcome.correlation_id
        if outcome.rollout is not None:
            record["rollout"] = outcome.rollout
        return record
