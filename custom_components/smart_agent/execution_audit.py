"""Project execution evidence without inventing receipts from aggregate counts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionAudit:
    action_results: list[dict[str, Any]]
    executed: int
    final_outcome: str
    unconfirmed_count: int
    integrity_reason: str


def _reported_count(value: Any) -> int | None:
    try:
        count = int(value)
    except (TypeError, ValueError, OverflowError):
        # No number is an unknown receipt, never a successful zero-action run.
        return None
    return count if count >= 0 else None


def _receipt_matches(action: dict, receipt: dict) -> bool:
    return all(
        not receipt.get(key) or str(receipt[key]) == str(action.get(key) or "")
        for key in ("domain", "service", "entity_id")
    )


def _action_receipt(
    action: dict, raw: Any, *, correlation_id: str, missing_reason: str,
    suppressed_reason: str,
) -> dict:
    known_statuses = {"executed", "failed", "blocked", "scheduled", "skipped", "not_executed", "blocked_or_error"}
    if isinstance(raw, dict) and _receipt_matches(action, raw) and isinstance(raw.get("status"), str) and raw["status"] in known_statuses:
        result = dict(raw)
    else:
        result = {
            "status": "blocked" if suppressed_reason else "unknown",
            "reason": suppressed_reason or missing_reason,
        }
    for key in ("domain", "service", "entity_id"):
        result[key] = str(result.get(key) or action.get(key) or "")
    params = action.get("params")
    if isinstance(params, dict) and params and not isinstance(result.get("params"), dict):
        result["params"] = dict(params)
    if action.get("reason") and not result.get("action_reason"):
        result["action_reason"] = str(action["reason"]).strip()
    if correlation_id:
        result["correlation_id"] = correlation_id
    return result


def project_execution_audit(
    actions: list[dict], execution_result: Any, *,
    missing_reason: str, correlation_id: str = "", suppressed_reason: str = "",
) -> ExecutionAudit:
    raw = getattr(execution_result, "action_results", None)
    raw = raw if isinstance(raw, list) else []
    results = [
        _action_receipt(
            action, raw[index] if index < len(raw) else None,
            correlation_id=correlation_id, missing_reason=missing_reason,
            suppressed_reason=suppressed_reason,
        )
        for index, action in enumerate(actions)
    ]
    executed = sum(row["status"] == "executed" for row in results)
    unconfirmed = sum(row["status"] == "unknown" for row in results)
    integrity = (
        "missing_or_invalid_action_receipt" if unconfirmed
        else "unexpected_action_receipt" if len(raw) > len(actions)
        else "execution_count_mismatch" if _reported_count(execution_result) != executed
        else ""
    )
    if suppressed_reason:
        outcome = (
            "observe_only" if suppressed_reason == "active_ai_shadow"
            else "no_action" if suppressed_reason in {"pending_selection_confirmation", "no_actions"}
            else "blocked"
        )
        integrity = ""
    elif integrity:
        outcome = "unknown"
    else:
        outcome = "succeeded" if actions and executed == len(actions) else "partial" if executed else "failed"
    return ExecutionAudit(results, executed, outcome, unconfirmed, integrity)
