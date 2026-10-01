"""Fail-closed add-on fast-path response orchestration.

This module owns the transport response, arbitration, rollout, and slow-fallback
policy for one already-admitted listener event. HA subscriptions stay in
`listeners.py`; physical execution remains delegated to the coordinator.
"""

from __future__ import annotations

from typing import Any

from .fast_path_fallback import FastPathFallback, finish_fast_path_without_match
from .fast_path_submission import prepare_fast_path_execution, submit_fast_path
from .fast_path_response import prepare_fast_path_response
from .fast_path_presentation import emit_fast_path_response, emit_fast_path_confirmation
from .fast_path_request import (
    FastPathTrigger,
    fast_path_disabled,
    prepare_fast_path_request,
    report_fast_path_unavailable,
)
from .fast_path_rollout import prepare_fast_path_rollout


async def run_addon_fast_path_fail_closed(
    self,
    entity_id: str,
    new_state: str,
    old_state: str,
    *,
    occupancy_cycle_id: str = "",
    causal_event: dict[str, Any] | None = None,
    trigger_context: dict[str, Any] | None = None,
    suppress_slow_fallback: bool = False,
) -> None:
    trigger_event = FastPathTrigger(entity_id, new_state, old_state)
    if fast_path_disabled(self, trigger_event):
        return
    request = await prepare_fast_path_request(
        self,
        trigger_event,
        occupancy_cycle_id=occupancy_cycle_id,
        causal_event=causal_event,
        trigger_context=trigger_context,
    )
    provider_response = await request.fetch()
    if provider_response.failed:
        return
    response = provider_response.payload
    if isinstance(response, dict):
        decision = prepare_fast_path_response(request, response)
        status, result, matched = decision.status, decision.result, decision.matched
        rollout = prepare_fast_path_rollout(
            self, response, result, decision.plan.actions, entity_id
        )
        execution = prepare_fast_path_execution(request, response, decision, rollout)
        rollout_trace = execution.trace
        execution_suppressed_reason, audit_pending = (
            execution.suppressed_reason,
            execution.audit_pending,
        )
        emit_fast_path_response(
            request,
            decision,
            rollout,
            rollout_trace,
            execution_suppressed_reason=execution_suppressed_reason,
            audit_pending=audit_pending,
        )
        emit_fast_path_confirmation(request, decision)
        if 200 <= status < 300 and matched and isinstance(result, dict):
            await submit_fast_path(execution, causal_event)
            return
        fallback = FastPathFallback(
            request, response, decision, suppress_slow_fallback, causal_event
        )
        if await finish_fast_path_without_match(fallback):
            return
    report_fast_path_unavailable(request)


__all__ = ["run_addon_fast_path_fail_closed"]
