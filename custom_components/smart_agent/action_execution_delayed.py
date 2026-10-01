"""Delayed stages of the existing action executor; transport remains on the host."""

from __future__ import annotations
from collections.abc import Callable
from datetime import datetime
from typing import Any
from .action_execution_context import DelayedActionCallbacks, DelayedActionContext
from .action_execution_diagnostics import action_failure_details, presence_refresh_failure
from .const import MODE_SHOWROOM

def _delayed_action_already_off(host: Any, action: DelayedActionContext) -> bool:
    batch, result = action.batch, action.result
    state = host.hass.states.get(action.entity_id)
    if (
        state
        and action.service == "turn_off"
        and getattr(state, "state", None) == "off"
        and not host._looks_like_presence_departure_turnoff(
            reason=str(action.reason or ""),
            scene_desc=str(batch.scene_desc or ""),
            trigger_summary=str(batch.trigger_summary or ""),
        )
    ):
        result.update(
            {"status": "skip", "msg": "already off", "ha_command_status": "not_dispatched"}
        )
        return True
    return False


async def _delayed_action_is_blocked(host: Any, action: DelayedActionContext) -> bool:
    if _delayed_action_already_off(host, action):
        return True
    result = action.result
    if (
        action.domain not in ("light", "switch")
        or action.service != "turn_off"
        or host._mode == MODE_SHOWROOM
    ):
        return False
    refresh_presence = getattr(host, "_async_refresh_presence_snapshot_cache", None)
    if callable(refresh_presence):
        try:
            presence_refreshed = bool(await refresh_presence())
        except Exception as exc:
            result.update(presence_refresh_failure(
                action.batch, action.action_seq, exc, operation="delayed_presence_refresh"
            ))
            return True
        if not presence_refreshed:
            result.update(
                {
                    "status": "blocked_person",
                    "msg": "presence_refresh_failed",
                    "ha_command_status": "not_dispatched",
                    "presence_source": "addon_presence_engine",
                    "presence_reason": "presence_refresh_failed",
                    "presence_evidence_ids": [],
                    "presence_states": [],
                }
            )
            return True
    off_blocked, off_reason = host._turnoff_presence_guard(action.entity_id, action.service)
    presence_detail = getattr(host, "_last_turnoff_presence_guard_detail", {})
    if isinstance(presence_detail, dict):
        result.update(presence_detail)
    if off_blocked:
        result.update(
            {"status": "blocked_person", "msg": off_reason, "ha_command_status": "not_dispatched"}
        )
        return True
    return False


async def _dispatch_delayed_action(host: Any, action: DelayedActionContext) -> Any:
    batch = action.batch
    return await host._do_call_service(
        action.domain,
        action.service,
        action.entity_id,
        action.params,
        action.reason,
        batch.scene_desc,
        batch.trigger_summary,
        batch.transaction_id,
        action.action_seq,
        batch.parent_transaction_id,
        batch.world_snapshot_id,
        batch.correlation_id,
        active_space_id=batch.active_space_id,
        decision_time=batch.decision_time,
        target_space_id=action.target_space_id,
        cmd_source=batch.cmd_source,
        require_world_snapshot_guard=batch.require_world_snapshot_guard,
        priority_override_claim=action.priority_override_claim,
        decision_contract_lineage=batch.decision_contract_lineage,
        user_intent_authority=batch.user_intent_authority,
    )


async def _refresh_delayed_receipt(
    action: DelayedActionContext, callbacks: DelayedActionCallbacks
) -> None:
    try:
        await callbacks.refresh_transaction()
    except Exception as exc:
        action_failure_details(
            action.batch, action.action_seq, exc, operation="delayed_receipt_refresh"
        )


async def run_delayed_action(
    host: Any,
    action: DelayedActionContext,
    callbacks: DelayedActionCallbacks,
) -> None:
    dispatch_started = False
    try:
        if not await _delayed_action_is_blocked(host, action):
            dispatch_started = True
            ok = await _dispatch_delayed_action(host, action)
            if ok:
                action.result["status"] = "ok"
            else:
                service_error = callbacks.pop_service_error(
                    action.batch.transaction_id, action.action_seq, action.entity_id
                )
                action.result.update(service_error)
                action.result["status"] = (
                    "skip" if service_error.get("ha_command_status") == "skipped" else "blocked_or_error"
                )
    except Exception as exc:
        action.result.update(
            status="blocked_or_error", msg="delayed_action_failed",
            error="delayed_action_failed", error_type="delayed_action_failed",
            ha_command_status="effect_unknown" if dispatch_started else "not_dispatched",
            **action_failure_details(
                action.batch, action.action_seq, exc,
                operation="delayed_action_dispatch" if dispatch_started else "delayed_action_guard",
            ),
        )
    # Receipt failure is separate from the service outcome and must never retry the write.
    await _refresh_delayed_receipt(action, callbacks)


def make_delayed_callback(
    host: Any,
    action: DelayedActionContext,
    callbacks: DelayedActionCallbacks,
    *,
    decorate: Callable[[Callable[..., None]], Callable[..., None]],
) -> Callable[[datetime], None]:
    @decorate
    def delayed(_now: datetime) -> None:
        coro = run_delayed_action(host, action, callbacks)
        try:
            host.hass.async_create_task(coro)
        except BaseException as exc:
            coro.close()
            if not isinstance(exc, Exception):
                raise
            action.result.update(
                {
                    "status": "blocked_or_error",
                    "msg": "task_create_failed",
                    "error": "task_create_failed",
                    "error_type": "task_create_failed",
                    "ha_command_status": "not_dispatched",
                    **action_failure_details(
                        action.batch, action.action_seq, exc, operation="delayed_task_create"
                    ),
                }
            )
            try:
                callbacks.refresh_transaction_sync()
            except Exception as refresh_exc:
                action_failure_details(
                    action.batch, action.action_seq, refresh_exc,
                    operation="delayed_task_failure_receipt_refresh",
                )

    return delayed
