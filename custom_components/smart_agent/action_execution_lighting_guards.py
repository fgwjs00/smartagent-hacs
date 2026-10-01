"""Live presence and daylight checks around routing, preserving their order."""

from __future__ import annotations
from typing import Any
from .action_execution_context import ActionGuardContext, ActionGuardOutcome
from .action_execution_diagnostics import action_failure_details, action_predispatch_failure, presence_refresh_failure
from .const import MODE_SHOWROOM


def is_automatic_presence_lighting(host: Any, context: ActionGuardContext) -> bool:
    call, batch = context.call, context.batch
    return (
        call.service == "turn_on"
        and host._entity_looks_like_lighting(
            call.entity_id,
            call.domain,
            reason=str(call.reason or ""),
            scene_desc=str(batch.scene_desc or ""),
            trigger_summary=str(batch.trigger_summary or ""),
        )
        and host._looks_like_automatic_presence_lighting(
            reason=str(call.reason or ""),
            scene_desc=str(batch.scene_desc or ""),
            trigger_summary=str(batch.trigger_summary or ""),
            cmd_source=str(batch.cmd_source or ""),
        )
    )


def evaluate_lighting_classification(
    host: Any, context: ActionGuardContext,
) -> tuple[bool, ActionGuardOutcome | None]:
    """Keep a failed metadata read distinct from a known non-lighting target."""
    try:
        return is_automatic_presence_lighting(host, context), None
    except Exception as exc:
        return False, action_predispatch_failure(
            context, exc, operation="action_lighting_classification",
            code="lighting_classification_failed",
        )


def evaluate_daylight_guard(
    host: Any, context: ActionGuardContext, *, before_router: bool
) -> ActionGuardOutcome | None:
    call, batch = context.call, context.batch
    if context.daylight_evaluation is None:
        context.daylight_evaluation = host._daylight_auto_lighting_execution_evaluation(
            call.entity_id,
            call.domain,
            call.service,
            actions=context.original_actions,
            require_world_snapshot_guard=batch.require_world_snapshot_guard,
            decision_contract_lineage=batch.decision_contract_lineage,
            world_snapshot_id=batch.world_snapshot_id,
            active_space_id=batch.active_space_id,
            decision_time=batch.decision_time,
        )
        context.receipt["daylight_guard_evaluation"] = dict(context.daylight_evaluation)
    reason = str(context.daylight_evaluation.get("reason_code") or "").strip()
    if context.daylight_evaluation.get("allowed") is not True:
        if before_router:
            host._sys_log(
                "WARN",
                f"[DaylightGuard] blocked daytime automatic presence lighting {call.domain}.turn_on({call.entity_id}): {reason}",
            )
        else:
            host._sys_log(
                "WARN",
                f"[日照守卫] 拒绝白天自动开灯 {call.domain}.turn_on({call.entity_id})：{reason}",
            )
        return ActionGuardOutcome(
            {
                **context.receipt,
                "status": "blocked_daylight_auto_lighting",
                "msg": reason,
                "ha_command_status": "not_dispatched",
            },
            blocked=1,
        )
    return None


def already_at_target(
    host: Any, context: ActionGuardContext, *, automatic_lighting: bool
) -> ActionGuardOutcome | None:
    call, batch = context.call, context.batch
    departure_off = call.service == "turn_off" and host._looks_like_presence_departure_turnoff(
        reason=str(call.reason or ""),
        scene_desc=str(batch.scene_desc or ""),
        trigger_summary=str(batch.trigger_summary or ""),
        cmd_source=str(batch.cmd_source or ""),
    )
    state = host.hass.states.get(call.entity_id)
    if state:
        if call.service == "turn_off" and state.state == "off" and not departure_off:
            host._sys_log("INFO", f"[动作] 跳过(已是off): {call.entity_id}")
            return ActionGuardOutcome(
                {
                    **context.receipt,
                    "status": "skip",
                    "msg": "already off",
                    "ha_command_status": "not_dispatched",
                }
            )
        if (
            call.service == "turn_on"
            and state.state == "on"
            and (not call.params or automatic_lighting)
        ):
            host._sys_log("INFO", f"[动作] 跳过(已是on): {call.entity_id}")
            return ActionGuardOutcome({**context.receipt, "status": "skip", "msg": "already on"})
    return None


async def _refresh_presence_guard(
    host: Any, context: ActionGuardContext
) -> ActionGuardOutcome | None:
    refresh = getattr(host, "_async_refresh_presence_snapshot_cache", None)
    if callable(refresh):
        try:
            refreshed = bool(await refresh())
        except Exception as exc:
            return ActionGuardOutcome(
                {**context.receipt, **presence_refresh_failure(
                    context.batch, context.action_seq, exc, operation="action_presence_refresh"
                )},
                failed=1,
            )
        if not refreshed:
            return ActionGuardOutcome(
                {
                    **context.receipt,
                    "status": "blocked_person",
                    "msg": "presence_refresh_failed",
                    "ha_command_status": "not_dispatched",
                    "presence_source": "addon_presence_engine",
                    "presence_reason": "presence_refresh_failed",
                    "presence_evidence_ids": [],
                    "presence_states": [],
                },
                blocked=1,
            )
    return None


def _presence_read_failure(context: ActionGuardContext, error: Exception) -> ActionGuardOutcome:
    return ActionGuardOutcome(
        {
            **context.receipt,
            **action_failure_details(context.batch, context.action_seq, error,
                operation=f"action_{context.call.service}_presence_read"),
            "status": "blocked_or_error",
            "msg": "presence_state_read_failed",
            "error": "presence_state_read_failed",
            "error_type": "presence_state_read_failed",
            "ha_command_status": "not_dispatched",
        },
        failed=1,
    )


async def evaluate_turnon_presence(
    host: Any, context: ActionGuardContext
) -> ActionGuardOutcome | None:
    call, batch = context.call, context.batch
    authenticated_turnon = batch.authenticated_user_intent and call.service == "turn_on"
    if (
        call.domain in ("light", "switch")
        and host._mode != MODE_SHOWROOM
        and not authenticated_turnon
    ):
        if call.service == "turn_on":
            outcome = await _refresh_presence_guard(host, context)
            if outcome is not None:
                return outcome
        try:
            blocked, reason = host._occupancy_guard_check(call.entity_id, call.service)
        except Exception as exc:
            return _presence_read_failure(context, exc)
        if blocked:
            host._sys_log(
                "WARN",
                f"[人员守卫] 拒绝 {call.domain}.turn_on({call.entity_id})：{reason}（无人区域禁止开灯）",
            )
            return ActionGuardOutcome(
                {
                    "entity_id": call.entity_id,
                    "service": call.service,
                    "status": "blocked",
                    "msg": reason,
                },
                blocked=1,
            )
    return None


async def evaluate_turnoff_presence(
    host: Any, context: ActionGuardContext
) -> ActionGuardOutcome | None:
    call, batch = context.call, context.batch
    if (
        call.domain in ("light", "switch")
        and host._mode != MODE_SHOWROOM
        and batch.cmd_source != "USER_EXPLICIT"
    ):
        if call.service == "turn_off":
            outcome = await _refresh_presence_guard(host, context)
            if outcome is not None:
                return outcome
        try:
            blocked, reason = host._turnoff_presence_guard(call.entity_id, call.service)
        except Exception as exc:
            return _presence_read_failure(context, exc)
        detail = getattr(host, "_last_turnoff_presence_guard_detail", {})
        if not isinstance(detail, dict):
            detail = {}
        if blocked:
            host._sys_log(
                "WARN", f"[关灯守卫] 阻止 {call.domain}.turn_off({call.entity_id})：{reason}"
            )
            return ActionGuardOutcome(
                {
                    "entity_id": call.entity_id,
                    "service": call.service,
                    "status": "blocked_person",
                    "msg": reason,
                    **detail,
                },
                blocked=1,
            )
        if detail:
            context.receipt.update(detail)
    return None
