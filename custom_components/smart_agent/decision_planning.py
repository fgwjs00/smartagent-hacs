"""Prepare slow-decision candidates and immutable request metadata before admission."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .decision_records import SlowDecisionRecords
from .decision_presentation import decision_transaction_id


@dataclass(frozen=True, slots=True)
class PreparedSlowDecision:
    records: SlowDecisionRecords
    actions: list[dict[str, Any]]
    patrol_blocked_actions: list[dict[str, Any]]


def _select_actions(
    host: Any, bundle: dict[str, Any], result: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    actions = result.get("actions") if isinstance(result.get("actions"), list) else []
    valid_actions = [item for item in actions if isinstance(item, dict)]
    candidate_actions = [dict(item) for item in valid_actions]
    patrol_policy_blocked_actions: list[dict[str, Any]] = []
    if isinstance(bundle.get("patrol_execution_policy"), dict) and bundle.get(
        "patrol_execution_policy"
    ):
        valid_actions, patrol_policy_blocked_actions = host._filter_patrol_reconciliation_actions(
            valid_actions,
            bundle,
        )
        result["candidate_action_count"] = len(candidate_actions)
        result["authorized_action_count"] = len(valid_actions)
        result["authorized_actions"] = list(valid_actions)
        result["patrol_policy_blocked_actions"] = list(patrol_policy_blocked_actions)
        result["execution_authorized"] = bool(valid_actions)
        if patrol_policy_blocked_actions and not valid_actions:
            result["execution_suppressed_reason"] = "patrol_policy"
            result["reason"] = "patrol_policy_blocked"
            result["auto_execute"] = False
            result["confirm_required"] = False
            result["arbitration_result"] = "blocked_by_patrol_policy"
    return valid_actions, candidate_actions, patrol_policy_blocked_actions


def _decision_records(
    host: Any,
    *,
    bundle: dict[str, Any],
    result: dict[str, Any],
    trigger: str,
    valid_actions: list[dict[str, Any]],
    candidate_actions: list[dict[str, Any]],
) -> SlowDecisionRecords:
    scene = str(result.get("scene") or "")
    transaction_id = decision_transaction_id(result)
    decision_id = str(result.get("decision_id") or transaction_id or "unknown").strip() or "unknown"
    nested_result = result.get("result") if isinstance(result.get("result"), dict) else {}
    world_snapshot_id = (
        str(
            result.get("world_snapshot_id") or nested_result.get("world_snapshot_id") or "unknown"
        ).strip()
        or "unknown"
    )
    decision_lineage = host._build_decision_trace_lineage(
        bundle=bundle,
        result=result,
        actions=valid_actions,
    )
    try:
        confidence = int(float(result.get("confidence") or 0))
    except (TypeError, ValueError, OverflowError):
        confidence = 0
    records = SlowDecisionRecords(
        result=result,
        transaction_id=transaction_id,
        trigger=trigger,
        scene=scene,
        confidence=confidence,
        candidate_actions=candidate_actions,
        decision_id=decision_id,
        world_snapshot_id=world_snapshot_id,
        lineage=decision_lineage,
    )
    return records


def prepare_slow_decision(
    host: Any, *, bundle: dict[str, Any], result: dict[str, Any], trigger: str
) -> PreparedSlowDecision:
    actions, candidates, blocked = _select_actions(host, bundle, result)
    records = _decision_records(
        host,
        bundle=bundle,
        result=result,
        trigger=trigger,
        valid_actions=actions,
        candidate_actions=candidates,
    )
    return PreparedSlowDecision(records, actions, blocked)
