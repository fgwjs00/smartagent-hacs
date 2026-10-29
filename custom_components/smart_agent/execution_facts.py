# Generated from contracts/python/execution_facts.py; do not edit.
"""Canonical execution fact interpretation; no dispatch or deletion authority.

Legacy planning compatibility stays narrow. Source clocks, receipt clocks and
judgment clocks remain distinct. Fact digests identify content, not event order.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any
from .fact_contract import FactJudgment, fact_version, utc_text

RULE_VERSION = "execution_evidence.v1"
LEGACY_PROFILE = "legacy_sql_json.v1"
RECEIPT_PROFILE = "action_receipts.v1"

LEGACY_NO_ACTION_REASONS = frozenset({
    "no_match", "daylight_auto_lighting_suppressed", "signal_manifest_quarantined",
    "non_presence_binary_sensor", "room_lighting_vacant", "room_lighting_vacancy_pending",
    "room_lighting_presence_unknown", "room_lighting_already_on", "room_lighting_retry_wait",
    "room_lighting_configuration_required", "room_lighting_manual_control",
    "room_lighting_repeated_manual_off", "illuminance_presence_unknown",
    "illuminance_presence_vacant", "illuminance_lighting_already_on",
    "illuminance_lighting_requires_planning", "arrival_preference_negative",
    "duplicate_occupancy_cycle", "duplicate_signal_event", "duplicate_task_occurrence",
    "guard_blocked", "decision_fast_path_failed",
})
def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _legacy_execution(row: dict) -> tuple[dict, bool]:
    """Decode the whole old copy; a raw response need not contain a status."""
    raw = row.get("trace_json", row.get("result_json"))
    try:
        value = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}, False
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return {"action_results": value}, True
    if not isinstance(value, dict):
        return {}, value is None
    execution = value.get("execution", {})
    if not isinstance(execution, dict):
        return {}, False
    return value, True


_NOT_EXECUTED = frozenset({"", "not_started", "not_dispatched", "no_actions"})


def _legacy_non_receipt_states(holder: dict, field: str, execution: bool) -> frozenset[str]:
    ignored = _NOT_EXECUTED - {"no_actions"} if execution or field.startswith("execution_") else _NOT_EXECUTED
    if not execution:
        ignored = ignored | {"matched"} if field in {"status", "final_outcome"} else ignored
        # The decision writer emits pending/no_actions before any receipt exists.
        # This exception applies to top-level planning only; independent raw
        # execution or action results still establish a fact below.
        planning = any(holder.get(name) == "matched" for name in ("status", "final_outcome", "decision_outcome"))
        if planning and field in {"execution_status", "execution_outcome"}:
            ignored = ignored | {"pending", "no_actions"}
    return ignored | LEGACY_NO_ACTION_REASONS if field == "final_outcome" else ignored


def _legacy_states(holder: dict, *, execution: bool = False) -> list[str]:
    states = []
    for field in ("status", "execution_status", "execution_outcome", "final_outcome"):
        if field not in holder:
            continue
        state = holder[field]
        if not isinstance(state, str):
            return ["unknown"]
        state = state.strip().lower()
        if state not in _legacy_non_receipt_states(holder, field, execution):
            states.append(state)
    return states


def _legacy_planning_response(row: dict, value: dict) -> bool:
    """Recognize the linked matched response written before HA execution.

    Its top-level ok describes planning, not an execution receipt. Independent
    receipt fields, both evidence copies and their clocks still need checking.
    """
    result, trace = value.get("result"), value.get("decision_trace")
    key = row.get("transaction_id")
    if not (key and row.get("status") == row.get("final_outcome") == "matched"
            and value.get("ok") is True and value.get("matched") is True
            and value.get("transaction_id") == key
            # The writer persists the response before setting available=True.
            # Both boolean values describe a trace link, never HA execution.
            and isinstance(trace, dict) and type(trace.get("available")) is bool
            and trace.get("transaction_id") == key
            and isinstance(result, dict) and isinstance(result.get("actions"), list)):
        return False
    receipt_fields = {"execution", "action_results", "results", "executed", "ok",
                      "transport_status", "effect_status", "workflow_status"}
    return not (receipt_fields.intersection(result) or _legacy_states(result) or result.get("error"))


def _legacy_fact_outcome(row: dict, value: dict) -> str | None:
    execution = value.get("execution", {})
    states = _legacy_states(execution, execution=True) + _legacy_states(value) + _legacy_states(row)
    if states:
        return states[0] if len(set(states)) == 1 else "unknown"
    # Only an empty or explicit not-started placeholder proves no execution.
    # Raw ok/error/results, future fields and conflicting receipts are facts too.
    if set(execution) - {"status", "updated_at"}:
        return "unknown"
    if "action_results" in value and value["action_results"] != []:
        return "unknown"
    if any(field in value for field in ("results", "executed", "transport_status", "effect_status", "workflow_status")) or value.get("error"):
        return "unknown"
    if "ok" in value and not _legacy_planning_response(row, value):
        return "unknown"
    return None


def _legacy_clocks(row: dict, value: dict) -> list[datetime] | None:
    # SQL clocks are mandatory; explicit JSON clocks must also be trustworthy.
    # Use the maximum, never prefer an older nested clock over a newer copy.
    raw_times = [row.get("updated_at")]
    for holder in (value, value.get("execution", {})):
        if "updated_at" in holder:
            raw_times.append(holder["updated_at"])
    instants = [_instant(raw) for raw in raw_times]
    return instants if all(at is not None for at in instants) else None


def legacy_planning_clocks(row: dict) -> list[datetime] | None:
    """Prove a linked legacy planning response has no independent receipt.

    Shared by receipt ordering and retention compatibility. This grants no
    execution authority and does not turn the SQL word 'matched' into a terminal.
    """
    value, valid = _legacy_execution(row)
    if not valid or not _legacy_planning_response(row, value) or _legacy_fact_outcome(row, value) is not None:
        return None
    return _legacy_clocks(row, value)


def legacy_settled_planning_pair(transaction: dict, trace: dict, trace_row: dict | None = None) -> bool:
    """Retention-only compatibility; SQL must cover every explicit receipt clock."""
    clocks = legacy_planning_clocks(transaction)
    value, valid = _legacy_execution(transaction)
    trace_clocks = _legacy_clocks(trace_row or trace, trace)
    settled_at = _instant((trace_row or trace).get('updated_at'))
    return bool(valid and clocks and trace_clocks and settled_at
                and min(trace_clocks) >= max(clocks) and max(trace_clocks) <= settled_at
                and transaction.get('transaction_id') == trace.get('transaction_id')
                and not value.get('authorization_contract')
                and not value.get('result', {}).get('authorization_contract'))


_RECEIPT_ENDED = frozenset({
    "ok", "success", "succeeded", "executed", "completed", "failed", "failure",
    "error", "not_executed", "blocked", "blocked_or_error", "verification_failed",
    "rolled_back", "cancelled", "canceled", "rejected", "skipped", "no_action",
    "no_actions", "observe_only",
})
_EFFECT_ENDED = frozenset({"verified_success", "verified_failed", "not_sent"})
_WORKFLOW_ENDED = _RECEIPT_ENDED | {"not_started", "not_dispatched"}


def _known(value, allowed) -> bool:
    return isinstance(value, str) and value.strip().lower() in allowed


def _unresolved_effect(holder: dict) -> bool:
    if holder.get("reconciliation_required") not in (None, False):
        return True
    if holder.get("unconfirmed_count") not in (None, 0):
        return True
    for field, allowed in (("effect_status", _EFFECT_ENDED), ("workflow_status", _WORKFLOW_ENDED)):
        value = holder.get(field)
        if value not in (None, "") and not _known(value, allowed):
            return True
    transport = holder.get("transport_status")
    if (transport not in (None, "") and not _known(transport, {"not_sent", "acknowledged"})
            and not _known(holder.get("effect_status"), _EFFECT_ENDED)):
        return True
    return False


def _receipt_ended(receipt) -> bool:
    if not isinstance(receipt, dict) or _unresolved_effect(receipt):
        return False
    states = [receipt[field] for field in (
        "status", "outcome", "final_outcome", "execution_status", "execution_outcome"
    ) if field in receipt]
    if not states and not _known(receipt.get("effect_status"), _EFFECT_ENDED):
        return False
    if any(not _known(value, _RECEIPT_ENDED) for value in states):
        return False
    # An explicit unknown execution boolean is not a negative receipt.
    if "executed" in receipt and type(receipt["executed"]) is not bool:
        return False
    return True


def unresolved_receipts(payload: dict) -> bool:
    """Inspect both persisted receipt copies, even when aggregate status ended.

    Missing receipt collections keep legacy compatibility. Present malformed or
    unrecognized rows remain protected; counts cannot manufacture a receipt.
    Transport history alone is not decisive: later verified effects can settle it.
    """
    execution = payload.get("execution")
    holders = (payload, execution) if isinstance(execution, dict) else (payload,)
    for holder in holders:
        if _unresolved_effect(holder):
            return True
        if "action_results" not in holder:
            continue
        rows = holder["action_results"]
        if not isinstance(rows, list) or any(not _receipt_ended(row) for row in rows):
            return True
    return False


@dataclass(frozen=True, slots=True)
class LegacyFact:
    judgment: FactJudgment
    payload_valid: bool
    outcome: str | None
    clocks: tuple[datetime, ...] | None


def inspect_legacy_row(row: dict, *, subject: str, source: str, checked_at: str) -> LegacyFact:
    """Interpret one original SQL/JSON copy without modifying or retaining it."""
    value, valid = _legacy_execution(row)
    outcome = _legacy_fact_outcome(row, value) if valid else None
    clocks = _legacy_clocks(row, value) if valid else None
    if not valid:
        conclusion, reason = "unknown", "legacy_payload_invalid"
    elif outcome is None:
        conclusion, reason = "no_execution_fact", "legacy_planning_or_empty"
    elif clocks is None:
        conclusion, reason = "unknown", "legacy_clock_invalid"
    else:
        conclusion, reason = "execution_fact", "legacy_execution_evidence"
    identity = {key: row.get(key) for key in
                ("transaction_id", "trace_json", "result_json", "updated_at", "status", "final_outcome")}
    judgment = FactJudgment(subject, source, fact_version(identity), RULE_VERSION,
                            LEGACY_PROFILE, utc_text(checked_at), conclusion, reason, None,
                            "newer_ordered_fact_or_explicit_reconciliation")
    return LegacyFact(judgment, valid, outcome, tuple(clocks) if clocks is not None else None)


def assess_receipts(payload, *, subject: str, source: str, checked_at: str,
                    profile: str = RECEIPT_PROFILE) -> FactJudgment:
    """Read-only explanation; absence of unresolved receipts is not authority.

    A missing receipt collection is explicitly 'absent', not proof of success.
    Retention additionally checks terminal parents, clocks, references and grants.
    """
    if profile != RECEIPT_PROFILE:
        conclusion, reason = "unknown", "unsupported_policy"
    elif not isinstance(payload, dict):
        conclusion, reason = "unknown", "receipt_payload_invalid"
    elif unresolved_receipts(payload):
        conclusion, reason = "unresolved", "receipt_unknown_or_unconfirmed"
    else:
        holders = [payload]
        if isinstance(payload.get("execution"), dict):
            holders.append(payload["execution"])
        present = any(bool(holder.get("action_results")) for holder in holders)
        conclusion = "settled_receipts" if present else "absent_receipts"
        reason = "known_receipts_only" if present else "no_receipt_collection"
    return FactJudgment(subject, source, fact_version(payload), RULE_VERSION,
                        profile, utc_text(checked_at), conclusion, reason, None,
                        "newer_ordered_fact_or_explicit_reconciliation")
