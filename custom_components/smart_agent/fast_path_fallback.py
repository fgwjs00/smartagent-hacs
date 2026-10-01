"""Slow inference handoff and terminal outcomes for an unmatched fast path."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .fast_path_request import FastPathRequest, schedule_fast_path_remainder
from .fast_path_response import FastPathResponse
from .presence_runtime import attach_occupancy_cycle, slow_fallback_allowed

_PLANNING_REASONS = frozenset(
    {
        "no_match",
        "arrival_lighting_requires_planning",
        "illuminance_lighting_requires_planning",
    }
)


@dataclass(frozen=True, slots=True)
class FastPathFallback:
    request: FastPathRequest
    response: dict
    decision: FastPathResponse
    suppress_slow_fallback: bool
    causal_event: dict[str, Any] | None

    def handoff_context(self, source: str) -> dict[str, Any]:
        lineage = self.decision.plan.lineage
        context = {
            "source": source,
            "transaction_id": lineage.transaction_id,
            "correlation_id": lineage.correlation_id,
            "world_snapshot_id": lineage.world_snapshot_id,
            "reason": self.decision.policy.reason or "",
            "decision_trace": (
                dict(lineage.decision_trace) if isinstance(lineage.decision_trace, dict) else {}
            ),
        }
        if self.decision.claim.current:
            context["event_claim"] = dict(self.decision.claim.current)
        attach_occupancy_cycle(context, self.request.snapshot)
        if self.decision.messages.decision_reason:
            context["decision_reason"] = self.decision.messages.decision_reason
        if self.decision.messages.arbitration_reason:
            context["arbitration_reason"] = self.decision.messages.arbitration_reason
        return context

    def schedule(self, source: str, *, allow_learning: bool | None = None) -> None:
        trigger = self.request.trigger
        kwargs = {
            "causal_event": self.causal_event,
            "source_trace_context": self.handoff_context(source),
        }
        if allow_learning is not None:
            kwargs["_allow_learning_mode_inference"] = allow_learning
        self.request.host._schedule_inference(
            trigger.entity_id,
            trigger.summary,
            trigger.new_state,
            **kwargs,
        )


def _planning_eligible(context: FastPathFallback) -> bool:
    request, reason = context.request, context.decision.policy.reason
    # The gateway's current room lux must not be vetoed by an older sun-only summary.
    if reason == "illuminance_lighting_requires_planning":
        return True
    if reason == "arrival_lighting_requires_planning":
        return request.host._is_presence_arrival_for_slow_inference(
            request.trigger.entity_id,
            request.trigger.new_state,
        )
    return request.host._should_slow_infer_after_fast_path_no_match(
        request.trigger.entity_id,
        request.trigger.new_state,
        request.snapshot,
    )


def _log_not_scheduled(context: FastPathFallback, *, low_confidence: bool = False) -> None:
    request = context.request
    host, entity_id, new_state = request.host, request.trigger.entity_id, request.trigger.new_state
    info = (
        host.device_info.get(entity_id, {})
        if isinstance(getattr(host, "device_info", None), dict)
        else {}
    )
    if not isinstance(info, dict):
        info = {}
    if low_confidence:
        reason = "no_action_candidate_or_not_presence_arrival"
        prefix = "confidence_below_auto_threshold"
    else:
        reason = (
            host._fast_path_no_match_slow_inference_skip_reason(
                entity_id, new_state, request.snapshot
            )
            or "not_presence_arrival"
        )
        prefix = "no_match"
    host._sys_log(
        "INFO",
        f"[Add-on FastPath] {prefix}; slow inference not scheduled | "
        f"reason={reason} entity={entity_id} state={new_state} "
        f"sensor_type={info.get('sensor_type') or '-'} name={info.get('name') or '-'}",
    )


async def _planning_fallback(context: FastPathFallback) -> bool:
    request, reason = context.request, context.decision.policy.reason
    if slow_fallback_allowed(context.suppress_slow_fallback, _planning_eligible(context)):
        request.host._sys_log(
            "INFO",
            f"[Add-on FastPath] {reason}; scheduling slow inference | entity={request.trigger.entity_id} "
            f"active_space={request.diagnostics.get('active_space') or '-'}",
        )
        source = (
            "addon_fast_path_illuminance"
            if reason == "illuminance_lighting_requires_planning"
            else (
                "addon_fast_path_arrival_lighting"
                if reason == "arrival_lighting_requires_planning"
                else "addon_fast_path_no_match"
            )
        )
        context.schedule(source)
        return True
    _log_not_scheduled(context)
    await context.decision.claim.finalize("fast_path_no_fallback", required_for_action=False)
    schedule_fast_path_remainder(request, context.response)
    return False


def _log_low_confidence_handoff(context: FastPathFallback) -> None:
    request, policy, plan = context.request, context.decision.policy, context.decision.plan
    request.host._sys_log(
        "INFO",
        "[Add-on FastPath] confidence_below_auto_threshold; scheduling slow inference | "
        f"entity={request.trigger.entity_id} confidence={plan.confidence if plan.confidence is not None else '-'} "
        f"confidence_auto={policy.confidence_auto if policy.confidence_auto is not None else '-'} "
        f"confidence_notify={policy.confidence_notify if policy.confidence_notify is not None else '-'} "
        f"actions={plan.action_count} "
        f"confirm_suppressed_reason={policy.confirm_suppressed_reason or '-'} "
        f"active_space={request.diagnostics.get('active_space') or '-'}",
    )


async def _low_confidence_fallback(context: FastPathFallback) -> bool:
    request = context.request
    eligible = (
        context.decision.plan.action_count > 0
        or request.host._should_slow_infer_after_fast_path_no_match(
            request.trigger.entity_id,
            request.trigger.new_state,
            request.snapshot,
        )
    )
    if slow_fallback_allowed(context.suppress_slow_fallback, eligible):
        _log_low_confidence_handoff(context)
        context.schedule(
            "addon_fast_path_low_confidence",
            allow_learning=context.decision.policy.confirm_suppressed_reason == "learning_mode",
        )
        return True
    _log_not_scheduled(context, low_confidence=True)
    await context.decision.claim.finalize("fast_path_no_fallback", required_for_action=False)
    return False


async def _unmatched_success(context: FastPathFallback) -> None:
    request, decision = context.request, context.decision
    reason = decision.policy.reason
    if reason == "local_fast_brain_disabled" or context.response.get("fast_path_disabled") is True:
        request.host._sys_log(
            "INFO",
            f"[Add-on FastPath] disabled; scheduling slow inference | entity={request.trigger.entity_id}",
        )
        context.schedule("addon_fast_path_disabled")
        return
    if reason in _PLANNING_REASONS and await _planning_fallback(context):
        return
    if reason == "confidence_below_auto_threshold" and not decision.policy.confirm_required:
        if await _low_confidence_fallback(context):
            return
    if reason not in _PLANNING_REASONS and reason != "confidence_below_auto_threshold":
        await decision.claim.finalize("fast_path_filtered", required_for_action=False)
        if isinstance(context.response.get("room_remainder_ref"), dict):
            schedule_fast_path_remainder(request, context.response)
    request.host._sys_log(
        "INFO",
        f"[Add-on FastPath] not matched; HA local decision skipped | "
        f"status={decision.status} matched={context.response.get('matched')}",
    )


async def _input_incomplete(context: FastPathFallback) -> None:
    request, reason = context.request, context.decision.policy.reason
    entity_id, new_state = request.trigger.entity_id, request.trigger.new_state
    request.host._sys_log(
        "WARN",
        "[Add-on FastPath] addon_fast_path_input_incomplete fail-closed | "
        f"status={context.decision.status} reason={reason or 'input_incomplete'} entity={entity_id}",
    )
    if slow_fallback_allowed(
        context.suppress_slow_fallback,
        request.host._should_slow_infer_after_fast_path_no_match(
            entity_id, new_state, request.snapshot
        ),
    ):
        request.host._sys_log(
            "INFO",
            "[Add-on FastPath] 409 input incomplete; scheduling slow inference | "
            f"entity={entity_id} reason={reason or 'input_incomplete'} "
            f"active_space={request.diagnostics.get('active_space') or '-'}",
        )
        context.schedule("addon_fast_path_409")
    else:
        await context.decision.claim.finalize(
            "fast_path_input_incomplete", required_for_action=False
        )


async def finish_fast_path_without_match(context: FastPathFallback) -> bool:
    status = context.decision.status
    if 200 <= status < 300:
        await _unmatched_success(context)
    elif status == 409:
        await _input_incomplete(context)
    elif status > 0:
        await context.decision.claim.finalize(
            "fast_path_execution_failed", required_for_action=False
        )
        context.request.host._sys_log(
            "INFO",
            "[Add-on FastPath] addon_unreachable fail-closed | "
            f"status={status} matched={context.response.get('matched')} reason={context.decision.policy.reason or '-'}",
        )
    else:
        return False
    return True
