"""Pure execution receipt projections for the HA action host."""
from __future__ import annotations

import hashlib
import json
from typing import Any


class ActionExecutionResult(int):
    """Int-compatible execution summary with per-action trace results."""

    def __new__(
        cls,
        executed_count: int = 0,
        *,
        action_results: list[dict[str, Any]] | None = None,
        transaction_id: int = 0,
        raw_results: list[dict[str, Any]] | None = None,
        pre_states: dict[str, str] | None = None,
    ):
        value = max(0, int(executed_count or 0))
        obj = int.__new__(cls, value)
        obj.executed_count = value
        obj.action_results = list(action_results or [])
        obj.transaction_id = int(transaction_id or 0)
        obj.raw_results = list(raw_results or [])
        obj.pre_states = dict(pre_states or {})
        return obj


def active_ai_authorization_ref(
    decision_contract_lineage: dict[str, Any] | None,
    commands: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Bind server-produced decision lineage to the exact HA command."""

    lineage = (
        dict(decision_contract_lineage)
        if isinstance(decision_contract_lineage, dict)
        else {}
    )
    required = (
        "decision_transaction_id",
        "decision_request_id",
        "plan_fingerprint",
        "policy_evaluation_id",
        "policy_evaluation_digest",
    )
    normalized = {key: str(lineage.get(key) or "").strip() for key in required}
    if any(not normalized[key] for key in required):
        return None
    policy_digest = normalized["policy_evaluation_digest"].lower()
    if len(policy_digest) != 64 or any(char not in "0123456789abcdef" for char in policy_digest):
        return None
    raw_claim_ids = (
        lineage.get("decision_event_claim_ids")
        if isinstance(lineage.get("decision_event_claim_ids"), (list, tuple))
        else lineage.get("claim_ids")
    )
    claim_ids: list[str] = []
    if isinstance(raw_claim_ids, (list, tuple)):
        for item in raw_claim_ids[:50]:
            claim_id = str(item or "").strip()
            if claim_id and claim_id not in claim_ids:
                claim_ids.append(claim_id)
    try:
        canonical = json.dumps(
            commands,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return None
    authorization_ref = {
        "version": "0.1",
        "claim_ids": claim_ids,
        **normalized,
        "policy_evaluation_digest": policy_digest,
        "commands_digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    aggregate = str(lineage.get("policy_aggregate_decision") or "").strip().lower()
    if aggregate:
        authorization_ref["policy_aggregate_decision"] = aggregate
    return authorization_ref


def decision_action_result_from_ha_result(item: dict[str, Any]) -> dict[str, Any]:
    ha_status = str(item.get("status") or "").strip()
    if ha_status == "ok":
        status = "executed"
        reason = "ha_service_call_ok"
    elif ha_status == "scheduled":
        status = "scheduled"
        reason = "delayed_action_scheduled"
    elif ha_status == "skip":
        status = "skipped"
        reason = str(item.get("msg") or "already_in_target_state")
    elif ha_status == "blocked_or_error":
        status = "failed"
        reason = str(item.get("msg") or "ha_service_returned_false")
    elif ha_status.startswith("blocked"):
        status = "blocked"
        reason = str(item.get("msg") or ha_status)
    else:
        status = "unknown"
        reason = str(item.get("msg") or ha_status or "unknown_action_result")
    entity_id = str(item.get("entity_id") or "")
    result = {
        "domain": str(item.get("domain") or (entity_id.split(".", 1)[0] if "." in entity_id else "")),
        "service": str(item.get("service") or ""),
        "entity_id": entity_id,
        "status": status,
        "reason": reason,
        "ha_status": ha_status,
    }
    if isinstance(item.get("params"), dict) and item.get("params"):
        result["params"] = dict(item.get("params") or {})
    for source_key, target_key in (
        ("error", "error"),
        ("error_type", "error_type"),
        ("reason", "action_reason"),
        ("scene_desc", "scene_desc"),
        ("trigger_summary", "trigger_summary"),
    ):
        value = str(item.get(source_key) or "").strip()
        if value:
            result[target_key] = value
    execution_transaction_id = item.get("execution_transaction_id")
    if execution_transaction_id not in (None, ""):
        result["execution_transaction_id"] = execution_transaction_id
    for key in ("parent_transaction_id", "correlation_id"):
        value = str(item.get(key) or "").strip()
        if value:
            result[key] = value
    decision_trace = item.get("decision_trace")
    if isinstance(decision_trace, dict) and decision_trace:
        result["decision_trace"] = dict(decision_trace)
    for key in ("presence_source", "presence_reason", "presence_room"):
        value = str(item.get(key) or "").strip()
        if value:
            result[key] = value
    presence_evidence_ids = item.get("presence_evidence_ids")
    if isinstance(presence_evidence_ids, list):
        result["presence_evidence_ids"] = [
            str(eid or "") for eid in presence_evidence_ids if str(eid or "").strip()
        ]
    presence_states = item.get("presence_states")
    if isinstance(presence_states, list):
        result["presence_states"] = [dict(row) for row in presence_states if isinstance(row, dict)]
    presence_conflict = item.get("presence_conflict")
    if isinstance(presence_conflict, dict) and presence_conflict:
        result["presence_conflict"] = dict(presence_conflict)
    return result


def action_execution_result(
    executed_count: int = 0,
    *,
    transaction_id: int = 0,
    results: list[dict[str, Any]] | None = None,
    pre_states: dict[str, str] | None = None,
    correlation_id: str = "",
) -> ActionExecutionResult:
    normalized_correlation_id = str(correlation_id or "").strip()
    raw_results = [
        {
            **dict(item),
            **({"correlation_id": normalized_correlation_id} if normalized_correlation_id else {}),
        }
        for item in results or []
        if isinstance(item, dict)
    ]
    action_results = [decision_action_result_from_ha_result(item) for item in raw_results]
    return ActionExecutionResult(
        executed_count,
        action_results=action_results,
        transaction_id=transaction_id,
        raw_results=raw_results,
        pre_states=pre_states,
    )


class ActionResultCollector:
    """Preserve caller action order while gates and dispatch append results."""

    def __init__(self, actions: list[Any], *, correlation_id: str = "") -> None:
        self._actions = list(actions)
        self._correlation_id = str(correlation_id or "").strip()
        self._positions: dict[int, list[int]] = {}
        for index, action in enumerate(self._actions):
            self._positions.setdefault(id(action), []).append(index)
        self._claimed: set[int] = set()
        self._results: dict[int, dict[str, Any]] = {}

    def claim_position(self, action: Any) -> int:
        for position in self._positions.get(id(action), []):
            if position not in self._claimed:
                self._claimed.add(position)
                return position
        for position in range(len(self._actions)):
            if position not in self._claimed:
                self._claimed.add(position)
                return position
        return len(self._actions) + len(self._claimed)

    def remember(self, position: int, result: dict[str, Any]) -> None:
        if self._correlation_id:
            result["correlation_id"] = self._correlation_id
        self._results[position] = result

    def ordered_results(self) -> list[dict[str, Any]]:
        return [self._results[position] for position in sorted(self._results)]


__all__ = [
    "ActionExecutionResult",
    "ActionResultCollector",
    "action_execution_result",
    "active_ai_authorization_ref",
    "decision_action_result_from_ha_result",
]
