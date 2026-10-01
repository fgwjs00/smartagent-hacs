"""Typed fast-path response facts; policy validation precedes any execution."""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Any
from .confidence_arbitration_contract import (
    AutoExecutionArbitrationValidation,
    validate_auto_execution_arbitration,
)
from .fast_path_request import FastPathRequest
from .fast_path_claim import FastPathClaim


@dataclass(frozen=True, slots=True)
class FastPathMessages:
    path_taken: str
    decision_reason: str
    arbitration_reason: str
    reason: str


@dataclass(frozen=True, slots=True)
class FastPathPolicy:
    validation: AutoExecutionArbitrationValidation
    fail_closed: bool
    confirm_required: bool
    confirm_suppressed_reason: str
    execution_suppressed_reason: str
    reason: str
    learning_mode: Any
    habit_proactive: Any
    confidence_auto: Any
    confidence_notify: Any
    threshold: Any
    arbitration_result: str


@dataclass(frozen=True, slots=True)
class FastPathLineage:
    transaction_id: str
    correlation_id: str
    world_snapshot_id: str
    decision_trace: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FastPathPlan:
    scene: str
    confidence: Any
    action_count: int
    actions: list[Any]
    lineage: FastPathLineage


@dataclass(frozen=True, slots=True)
class FastPathResponse:
    status: int
    result: Any
    matched: bool
    messages: FastPathMessages
    policy: FastPathPolicy
    plan: FastPathPlan
    claim: FastPathClaim


def _messages(response: dict[str, Any], result: Any, details: dict[str, Any]) -> FastPathMessages:
    path_taken = str(response.get("path_taken") or details.get("path_taken") or "none")
    result_payload = result if isinstance(result, dict) else {}
    decision_reason = str(
        response.get("decision_reason")
        or result_payload.get("decision_reason")
        or details.get("decision_reason")
        or ""
    )
    arbitration_reason = str(
        response.get("arbitration_reason")
        or result_payload.get("arbitration_reason")
        or details.get("arbitration_reason")
        or ""
    )
    reason = str(
        response.get("reason")
        or decision_reason
        or details.get("reason")
        or response.get("error")
        or ""
    )
    return FastPathMessages(path_taken, decision_reason, arbitration_reason, reason)


def _policy(
    response: dict[str, Any],
    details: dict[str, Any],
    matched: bool,
    arbitration_validation: AutoExecutionArbitrationValidation,
    arbitration_fail_closed: bool,
    reason: str,
) -> FastPathPolicy:
    confirm_required = (
        response.get("confirm_required") is True or details.get("confirm_required") is True
    )
    confirm_suppressed_reason = str(details.get("confirm_suppressed_reason") or "")
    addon_learning_mode = details.get("learning_mode")
    addon_habit_proactive = details.get("habit_proactive")
    execution_suppressed_reason = "learning_mode" if matched and addon_learning_mode is True else ""
    if matched and not arbitration_validation.allowed and not execution_suppressed_reason:
        execution_suppressed_reason = arbitration_validation.reason
    if arbitration_fail_closed:
        confirm_required = False
        reason = arbitration_validation.reason
        execution_suppressed_reason = arbitration_validation.reason
    if confirm_required and confirm_suppressed_reason:
        confirm_required = False
    confidence_auto = response.get("confidence_auto", details.get("confidence_auto"))
    confidence_notify = response.get("confidence_notify", details.get("confidence_notify"))
    threshold = response.get("threshold", details.get("threshold"))
    arbitration_result = str(
        response.get("arbitration_result") or details.get("arbitration_result") or ""
    )
    return FastPathPolicy(
        arbitration_validation,
        arbitration_fail_closed,
        confirm_required,
        confirm_suppressed_reason,
        execution_suppressed_reason,
        reason,
        addon_learning_mode,
        addon_habit_proactive,
        confidence_auto,
        confidence_notify,
        threshold,
        arbitration_result,
    )


def _lineage(response: dict[str, Any], details: dict[str, Any], request_id: str) -> FastPathLineage:
    decision_trace = (
        response.get("decision_trace") if isinstance(response.get("decision_trace"), dict) else {}
    )
    transaction_id = str(
        response.get("transaction_id")
        or details.get("transaction_id")
        or (decision_trace.get("transaction_id") if isinstance(decision_trace, dict) else "")
        or ""
    )
    correlation_id = str(
        response.get("correlation_id")
        or details.get("correlation_id")
        or response.get("request_id")
        or request_id
    )
    world_snapshot_id = str(
        response.get("world_snapshot_id") or details.get("world_snapshot_id") or ""
    )
    return FastPathLineage(transaction_id, correlation_id, world_snapshot_id, decision_trace)


def _plan(
    request: FastPathRequest, response: dict[str, Any], details: dict[str, Any], result: Any
) -> tuple[FastPathPlan, FastPathClaim]:
    request_id, entity_id = request.request_id, request.trigger.entity_id
    scene = ""
    confidence = response.get("confidence", details.get("confidence"))
    action_count = 0
    actions: list[Any] = []
    lineage = _lineage(response, details, request_id)
    transaction_id = lineage.transaction_id
    event_claim = (
        dict(response.get("event_claim")) if isinstance(response.get("event_claim"), dict) else {}
    )

    claim = FastPathClaim(request.host, request.client, entity_id, request_id, event_claim)

    if isinstance(result, dict):
        scene = str(result.get("scene") or result.get("source") or "")
        if confidence is None:
            confidence = result.get("confidence")
        raw_actions = result.get("actions")
        if isinstance(raw_actions, list):
            actions = raw_actions
            action_count = len(raw_actions)
        elif result.get("action"):
            action_count = 1
        transaction_id = transaction_id or str(
            result.get("transaction_id") or result.get("txn_id") or ""
        )
    plan = FastPathPlan(
        scene, confidence, action_count, actions, replace(lineage, transaction_id=transaction_id)
    )
    return plan, claim


def prepare_fast_path_response(
    request: FastPathRequest, response: dict[str, Any]
) -> FastPathResponse:
    host, snapshot = request.host, request.snapshot
    entity_id, old_state, new_state = (
        request.trigger.entity_id,
        request.trigger.old_state,
        request.trigger.new_state,
    )
    from .room_lighting_runtime import schedule_room_check

    schedule_room_check(host, response)
    status = int(response.get("__status") or 0)
    result = response.get("result")
    matched = response.get("matched") is True
    arbitration_validation = validate_auto_execution_arbitration(
        response,
        context_snapshot=snapshot,
    )
    arbitration_fail_closed = matched and arbitration_validation.reason in {
        "confidence_arbitration_missing",
        "confidence_arbitration_invalid",
    }
    details = response.get("details") if isinstance(response.get("details"), dict) else {}
    presence_details = details.get("presence") if isinstance(details.get("presence"), dict) else {}
    host._schedule_presence_temporal_recheck(
        entity_id,
        old_state=old_state,
        new_state=new_state,
        presence=presence_details,
        presence_hold_ref=response.get("presence_hold_ref"),
    )
    messages = _messages(response, result, details)
    policy = _policy(
        response, details, matched, arbitration_validation, arbitration_fail_closed, messages.reason
    )
    plan, claim = _plan(request, response, details, result)
    return FastPathResponse(status, result, matched, messages, policy, plan, claim)
