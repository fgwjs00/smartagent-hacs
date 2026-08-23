"""Portable decision lineage and observe-only training projections.

This module deliberately owns no Home Assistant lifecycle, state, transport, or
execution authority.  The coordinator supplies the local time and season while
retaining responsibility for emitting and persisting the resulting records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def build_decision_trace_lineage(
    *,
    bundle: dict[str, Any],
    result: dict[str, Any],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project canonical source, plan, policy, and action lineage."""

    nested_result = result.get("result") if isinstance(result.get("result"), dict) else {}
    details = result.get("details") if isinstance(result.get("details"), dict) else {}
    source_context = (
        bundle.get("source_trace_context")
        if isinstance(bundle.get("source_trace_context"), dict)
        else {}
    )
    context_snapshot = (
        result.get("context_snapshot")
        if isinstance(result.get("context_snapshot"), dict)
        else nested_result.get("context_snapshot")
        if isinstance(nested_result.get("context_snapshot"), dict)
        else {}
    )
    llm_request = (
        result.get("llm_request")
        if isinstance(result.get("llm_request"), dict)
        else nested_result.get("llm_request")
        if isinstance(nested_result.get("llm_request"), dict)
        else details.get("llm_request")
        if isinstance(details.get("llm_request"), dict)
        else {}
    )

    raw_evidence_ids = (
        result.get("source_evidence_ids")
        or nested_result.get("source_evidence_ids")
        or context_snapshot.get("source_evidence_ids")
        or bundle.get("source_evidence_ids")
        or source_context.get("source_evidence_ids")
    )
    if isinstance(raw_evidence_ids, str):
        raw_evidence_ids = [raw_evidence_ids]
    source_evidence_ids: list[str] = []
    if isinstance(raw_evidence_ids, (list, tuple, set)):
        for item in raw_evidence_ids:
            evidence_id = str(item or "").strip()
            if evidence_id and evidence_id not in source_evidence_ids:
                source_evidence_ids.append(evidence_id)
    trigger_entity_id = str(bundle.get("trigger_entity_id") or "").strip()
    if not source_evidence_ids and trigger_entity_id:
        source_evidence_ids.append(trigger_entity_id)

    action_sequences: list[int] = []
    for index, action in enumerate(actions, start=1):
        raw_sequence = (
            action.get("sequence")
            or action.get("action_sequence")
            or action.get("sequence_id")
            or index
        )
        try:
            sequence = int(raw_sequence)
        except (TypeError, ValueError, OverflowError):
            sequence = index
        action_sequences.append(sequence)

    decision_request = (
        result.get("decision_request")
        if isinstance(result.get("decision_request"), dict)
        else nested_result.get("decision_request")
        if isinstance(nested_result.get("decision_request"), dict)
        else {}
    )
    plan_sketch = (
        result.get("plan_sketch")
        if isinstance(result.get("plan_sketch"), dict)
        else nested_result.get("plan_sketch")
        if isinstance(nested_result.get("plan_sketch"), dict)
        else {}
    )
    policy_evaluation = (
        result.get("policy_evaluation")
        if isinstance(result.get("policy_evaluation"), dict)
        else nested_result.get("policy_evaluation")
        if isinstance(nested_result.get("policy_evaluation"), dict)
        else {}
    )
    decision_event_claim_ids: list[str] = []
    causal_event_rows = decision_request.get("causal_events")
    if isinstance(causal_event_rows, list):
        for row in causal_event_rows:
            if not isinstance(row, dict):
                continue
            claim_id = str(row.get("claim_id") or "").strip()
            if claim_id and claim_id not in decision_event_claim_ids:
                decision_event_claim_ids.append(claim_id)

    lineage = {
        "world_snapshot_id": str(
            result.get("world_snapshot_id")
            or nested_result.get("world_snapshot_id")
            or context_snapshot.get("world_snapshot_id")
            or bundle.get("world_snapshot_id")
            or bundle.get("parent_world_snapshot_id")
            or "unknown"
        ).strip()
        or "unknown",
        "source_evidence_ids": source_evidence_ids,
        "parent_transaction_id": str(
            bundle.get("parent_transaction_id")
            or result.get("parent_transaction_id")
            or nested_result.get("parent_transaction_id")
            or ""
        ).strip(),
        "action_sequences": action_sequences,
        "llm_provider": str(
            result.get("llm_provider")
            or nested_result.get("llm_provider")
            or llm_request.get("provider")
            or ""
        ).strip(),
        "llm_model": str(
            result.get("llm_model")
            or nested_result.get("llm_model")
            or llm_request.get("model")
            or ""
        ).strip(),
    }
    contract_lineage = {
        "decision_transaction_id": str(
            result.get("transaction_id")
            or result.get("decision_id")
            or nested_result.get("transaction_id")
            or nested_result.get("decision_id")
            or ""
        ).strip(),
        "decision_event_claim_ids": decision_event_claim_ids,
        "parent_execution_transaction_id": str(
            bundle.get("parent_execution_transaction_id")
            or source_context.get("execution_transaction_id")
            or ""
        ).strip(),
        "decision_request_id": str(decision_request.get("request_id") or "").strip(),
        "plan_fingerprint": str(plan_sketch.get("semantic_fingerprint") or "").strip(),
        "policy_evaluation_id": str(policy_evaluation.get("evaluation_id") or "").strip(),
        "policy_evaluation_digest": str(
            policy_evaluation.get("evaluation_digest") or ""
        ).strip(),
        "policy_aggregate_decision": str(
            policy_evaluation.get("aggregate_decision") or ""
        ).strip().lower(),
    }
    lineage.update({key: value for key, value in contract_lineage.items() if value})
    return lineage


def build_training_sample_payload(
    *,
    bundle: dict[str, Any],
    actions: list[dict[str, Any]],
    confidence: int,
    final_outcome: str,
    now: datetime,
    season: str,
    default_confidence_auto: int,
    decision_id: str = "unknown",
    transaction_id: str = "unknown",
    execution_transaction_id: str = "unknown",
    world_snapshot_id: str = "unknown",
    planned_count: int | None = None,
    executed_count: int | None = None,
    action_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Project an observe-only training sample from a completed execution."""

    if final_outcome not in {"succeeded", "partial"} or not actions:
        return None

    planned = max(0, int(len(actions) if planned_count is None else planned_count))
    executed = max(
        0,
        int(
            planned
            if executed_count is None and final_outcome == "succeeded"
            else executed_count or 0
        ),
    )
    if executed == 0:
        return None

    sample_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        entity_id = str(action.get("entity_id") or action.get("entity") or "").strip()
        service = str(action.get("service") or "").strip()
        if not entity_id or not service:
            continue
        domain = str(action.get("domain") or entity_id.split(".", 1)[0]).strip()
        normalized_service = service.lower()
        if normalized_service == "turn_on":
            desired_state = "on"
        elif normalized_service == "turn_off":
            desired_state = "off"
        elif normalized_service in {"open_cover", "open"}:
            desired_state = "open"
        elif normalized_service in {"close_cover", "close"}:
            desired_state = "closed"
        else:
            params = action.get("params") if isinstance(action.get("params"), dict) else {}
            desired_state = str(
                params.get("hvac_mode")
                or params.get("temperature")
                or params.get("position")
                or normalized_service
            ).strip().lower()
        sample_actions.append(
            {
                "domain": domain,
                "service": service,
                "entity_id": entity_id,
                "desired_state": desired_state,
                "confidence": max(0.0, min(float(confidence or 0) / 100.0, 1.0)),
            }
        )
    if not sample_actions:
        return None

    trigger_entity = str(bundle.get("trigger_entity_id") or "").strip()
    trigger_domain = trigger_entity.split(".", 1)[0] if "." in trigger_entity else ""
    trigger_room = str(bundle.get("trigger_room") or "").strip()
    old_state = str(bundle.get("old_state") or "").strip().lower()
    new_state = str(bundle.get("new_state") or "").strip().lower()
    if trigger_domain == "binary_sensor" and old_state == "off" and new_state == "on":
        trigger_type = "arrival"
    elif trigger_domain == "binary_sensor" and old_state == "on" and new_state == "off":
        trigger_type = "departure"
    else:
        trigger_type = "state_change"
    presence_snapshot = (
        bundle.get("presence_snapshot")
        if isinstance(bundle.get("presence_snapshot"), dict)
        else {}
    )
    rooms = presence_snapshot.get("rooms") if isinstance(presence_snapshot, dict) else {}
    room_presence = (
        rooms.get(trigger_room)
        if isinstance(rooms, dict)
        and trigger_room
        and isinstance(rooms.get(trigger_room), dict)
        else {}
    )
    room_state = str(
        room_presence.get("state") or room_presence.get("presence") or ""
    ).strip().lower()
    room_person_count = 1 if room_state in {"occupied", "present", "on", "home"} else 0
    quality_score = max(0.0, min(float(confidence or 0) / 100.0, 1.0))
    confidence_auto = int(bundle.get("confidence_auto") or default_confidence_auto or 0)
    return {
        "source": "ha_slow_decision",
        "source_id": str(transaction_id or "unknown"),
        "feature_json": {
            "time_hour": now.hour,
            "is_weekend": now.weekday() >= 5,
            "trigger_domain": trigger_domain or "unknown",
            "space": trigger_room or "unknown",
            "trigger_room": trigger_room or "unknown",
            "trigger_type": trigger_type,
            "local_date": now.strftime("%Y-%m-%d"),
            "weekday": now.weekday(),
            "confidence_auto": confidence_auto,
            "room_person_count": room_person_count,
            "outdoor_temp": None,
            "season_encoding": season,
        },
        "decision_json": {"actions": sample_actions},
        "label": None,
        "preference_label": "unknown",
        "quality_score": quality_score,
        "is_verified": False,
        "lifecycle_state": "observe_only",
        "evidence": {
            "service_acknowledged": True,
            "post_state_verified": False,
            "stable_seconds": 0,
            "confidence": int(confidence or 0),
            "confidence_auto": confidence_auto,
            "world_snapshot_id": str(world_snapshot_id or "unknown"),
            "execution_transaction_id": str(execution_transaction_id or "unknown"),
            "partial_execution": final_outcome == "partial" or executed < planned,
            "planned_count": planned,
            "executed_count": executed,
            "action_results": [
                dict(item) for item in (action_results or []) if isinstance(item, dict)
            ],
        },
        "privacy_tier": "derived_private",
        "model_schema_version": "system1_v1",
        "origin": "smartagent",
        "actor": "smartagent:ha_slow_decision",
        "decision_id": str(decision_id or "unknown"),
        "transaction_id": str(transaction_id or "unknown"),
        "world_snapshot_id": str(world_snapshot_id or "unknown"),
    }


__all__ = ["build_decision_trace_lineage", "build_training_sample_payload"]
