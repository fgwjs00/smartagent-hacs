"""Ordered action guards, before and after the existing target router."""

from __future__ import annotations
from typing import Any
from .action_execution_context import ActionGuardContext, ActionGuardOutcome, ShowroomBatchEvidence
from .action_execution_lighting_guards import (
    already_at_target,
    evaluate_daylight_guard,
    evaluate_turnon_presence,
    evaluate_turnoff_presence,
    evaluate_lighting_classification,
)
from .action_execution_scene_guards import evaluate_scene_guards
from .action_execution_showroom import evaluate_people_rule, evaluate_showroom_tier


def evaluate_before_router(host: Any, context: ActionGuardContext) -> ActionGuardOutcome | None:
    automatic, failure = evaluate_lighting_classification(host, context)
    if failure is not None:
        return failure
    if automatic:
        return evaluate_daylight_guard(host, context, before_router=True)
    return None


async def evaluate_after_router(
    host: Any, context: ActionGuardContext, evidence: ShowroomBatchEvidence
) -> ActionGuardOutcome | None:
    call = context.call
    outcome = evaluate_scene_guards(host, call)
    if outcome is not None:
        return outcome
    host._sys_log(
        "INFO",
        f"[动作] 准备执行: {call.domain}.{call.service}({call.entity_id}) params={call.params} reason={call.reason}",
    )
    automatic, failure = evaluate_lighting_classification(host, context)
    if failure is not None:
        return failure
    outcome = already_at_target(host, context, automatic_lighting=automatic)
    if outcome is not None:
        return outcome
    outcome = await evaluate_turnon_presence(host, context)
    if outcome is not None:
        return outcome
    if call.service == "turn_on" and automatic:
        outcome = evaluate_daylight_guard(host, context, before_router=False)
        if outcome is not None:
            return outcome
    outcome = evaluate_people_rule(host, context, evidence)
    if outcome is not None:
        return outcome
    outcome = await evaluate_showroom_tier(host, context, evidence)
    if outcome is not None:
        return outcome
    return await evaluate_turnoff_presence(host, context)
