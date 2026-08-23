"""Fail-closed add-on fast-path response orchestration.

This module owns the transport response, arbitration, rollout, and slow-fallback
policy for one already-admitted listener event. HA subscriptions stay in
`listeners.py`; physical execution remains delegated to the coordinator.
"""
from __future__ import annotations

import logging
from typing import Any

from .active_ai_rollout import (
    ActiveAiRolloutConfig,
    DEFAULT_ACTIVE_AI_MODE,
    enrich_active_ai_action_spaces,
    evaluate_active_ai_execution_gate,
    normalize_active_ai_mode,
    scope_active_ai_canary_actions,
)
from .confidence_arbitration_contract import validate_auto_execution_arbitration
from .presence_runtime import (
    attach_occupancy_cycle,
    enrich_fast_path_presence_timing,
    slow_fallback_allowed,
)

_LOGGER = logging.getLogger(__name__)


async def run_addon_fast_path_fail_closed(
    self,
    entity_id: str,
    new_state: str,
    old_state: str,
    *,
    occupancy_cycle_id: str = "",
    trigger_context: dict[str, Any] | None = None,
    suppress_slow_fallback: bool = False,
) -> None:
    should_fail_closed = True
    if normalize_active_ai_mode(
        getattr(self, "_active_ai_mode", DEFAULT_ACTIVE_AI_MODE)
    ) == "off":
        self._sys_log(
            "INFO",
            f"[Add-on FastPath] active_ai_off | entity={entity_id}",
        )
        self._emit_addon_fast_path_event(
            {
                "source": "addon_fast_path",
                "entity_id": entity_id,
                "old_state": old_state,
                "new_state": new_state,
                "status": 200,
                "matched": False,
                "path_taken": "active_ai_rollout_gate",
                "reason": "active_ai_off",
                "executed": False,
                "fail_closed": True,
            }
        )
        return
    if str(new_state or "").strip().lower() in {
        "on",
        "open",
        "home",
        "occupied",
        "present",
        "detected",
        "motion",
        "person",
    }:
        self._cancel_presence_temporal_recheck(entity_id)
    addon_client = getattr(self, "_addon_client", None)
    if addon_client is not None:
        await self._refresh_correction_suppressions_cache(addon_client)
    snapshot = self._build_addon_fast_path_snapshot(entity_id)
    observations = snapshot.get("state_observations")
    if isinstance(observations, dict):
        trigger_observation = observations.get(entity_id)
        if isinstance(trigger_observation, dict):
            # Bind the transition to the same HA state observation used by
            # the typed signal gate. The add-on must not trust the HTTP
            # old_state/new_state pair as an independent evidence source.
            trigger_observation["previous_state"] = str(old_state or "")
            trigger_observation["event_current_state"] = str(new_state or "")
    enrich_fast_path_presence_timing(self, snapshot, trigger_context)
    snapshot["occupancy_cycle_id"] = str(occupancy_cycle_id).strip()
    request_id = self._new_addon_fast_path_request_id(entity_id, old_state, new_state)
    snapshot["request_id"] = request_id
    snapshot_diag = self._addon_fast_path_snapshot_diagnostics(snapshot, entity_id)
    self._sys_log(
        "INFO",
        "[Add-on FastPath] request "
        f"entity={entity_id} old={old_state} new={new_state} "
        f"request_id={request_id} "
        f"active_space={snapshot_diag.get('active_space') or '-'} "
        f"capability_rows={snapshot_diag.get('capability_rows', 0)} "
        f"device_info_count={snapshot_diag.get('device_info_count', 0)} "
        f"topology_count={snapshot_diag.get('topology_count', 0)}",
    )
    if addon_client is not None:
        try:
            response = await addon_client.run_decision_fast_path(
                entity_id=entity_id,
                new_state=new_state,
                old_state=old_state,
                snapshot=snapshot,
                request_id=request_id,
            )
        except Exception as exc:
            response = None
            _LOGGER.debug("[Listeners] add-on fast-path decision failed: %s", exc)
            self._sys_log(
                "ERROR",
                f"[Add-on FastPath] addon_unreachable fail-closed | entity={entity_id} "
                f"reason=exception exception_type={type(exc).__name__} request_id={request_id}",
            )
            self._emit_addon_fast_path_event(
                {
                    "source": "addon_fast_path",
                    "entity_id": entity_id,
                    "old_state": old_state,
                    "new_state": new_state,
                    "status": 0,
                    "matched": False,
                    "path_taken": "none",
                    "reason": "exception",
                    "exception_type": type(exc).__name__,
                    "correlation_id": request_id,
                    "fail_closed": True,
                    "snapshot": snapshot_diag,
                }
            )
            return
        else:
            if isinstance(response, dict):
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
                self._schedule_presence_temporal_recheck(
                    entity_id,
                    old_state=old_state,
                    new_state=new_state,
                    presence=presence_details,
                )
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
                confirm_required = response.get("confirm_required") is True or details.get("confirm_required") is True
                confirm_suppressed_reason = str(details.get("confirm_suppressed_reason") or "")
                addon_learning_mode = details.get("learning_mode")
                addon_habit_proactive = details.get("habit_proactive")
                execution_suppressed_reason = (
                    "learning_mode" if matched and addon_learning_mode is True else ""
                )
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
                    response.get("arbitration_result")
                    or details.get("arbitration_result")
                    or ""
                )
                scene = ""
                confidence = response.get("confidence", details.get("confidence"))
                action_count = 0
                actions: list[Any] = []
                decision_trace = response.get("decision_trace") if isinstance(response.get("decision_trace"), dict) else {}
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
                world_snapshot_id = str(response.get("world_snapshot_id") or details.get("world_snapshot_id") or "")
                event_claim = (
                    dict(response.get("event_claim"))
                    if isinstance(response.get("event_claim"), dict)
                    else {}
                )

                async def _finalize_fast_path_claim(
                    outcome: str,
                    *,
                    required_for_action: bool = False,
                ) -> bool:
                    nonlocal event_claim
                    if not event_claim:
                        if required_for_action:
                            self._sys_log(
                                "ERROR",
                                "[Add-on FastPath] action blocked; terminal event claim is missing "
                                f"| entity={entity_id} request_id={request_id}",
                            )
                            return False
                        return True
                    finalizer = getattr(
                        addon_client,
                        "finalize_decision_fast_path_claim",
                        None,
                    )
                    if not callable(finalizer):
                        self._sys_log(
                            "ERROR",
                            "[Add-on FastPath] terminal claim endpoint unavailable "
                            f"| entity={entity_id} claim_id={event_claim.get('claim_id') or '-'}",
                        )
                        return False
                    try:
                        terminal = await finalizer(
                            event_claim=dict(event_claim),
                            attempt_id=request_id,
                            outcome=outcome,
                        )
                    except Exception as exc:
                        _LOGGER.debug(
                            "[Listeners] fast-path event claim finalize failed: %s",
                            exc,
                        )
                        terminal = None
                    terminal_status = (
                        int(terminal.get("__status") or 0)
                        if isinstance(terminal, dict)
                        else 0
                    )
                    terminal_claim = (
                        terminal.get("event_claim")
                        if isinstance(terminal, dict)
                        and isinstance(terminal.get("event_claim"), dict)
                        else {}
                    )
                    if (
                        not isinstance(terminal, dict)
                        or terminal.get("ok") is not True
                        or not (200 <= terminal_status < 300)
                        or terminal_claim.get("state") != "finalized"
                        or terminal_claim.get("current_stage") != "terminal"
                        or terminal_claim.get("continuation_token")
                    ):
                        self._sys_log(
                            "ERROR",
                            "[Add-on FastPath] terminal claim rejected; action delivery remains blocked "
                            f"| entity={entity_id} claim_id={event_claim.get('claim_id') or '-'} "
                            f"status={terminal_status}",
                        )
                        return False
                    event_claim = dict(terminal_claim)
                    return True

                def _fast_path_handoff_context(source: str) -> dict[str, Any]:
                    context = {
                        "source": source,
                        "transaction_id": transaction_id,
                        "correlation_id": correlation_id,
                        "world_snapshot_id": world_snapshot_id,
                        "reason": reason or "",
                        "decision_trace": dict(decision_trace) if isinstance(decision_trace, dict) else {},
                    }
                    if event_claim:
                        context["event_claim"] = dict(event_claim)
                    attach_occupancy_cycle(context, snapshot)
                    if decision_reason:
                        context["decision_reason"] = decision_reason
                    if arbitration_reason:
                        context["arbitration_reason"] = arbitration_reason
                    return context

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
                    transaction_id = transaction_id or str(result.get("transaction_id") or result.get("txn_id") or "")
                rollout_payload = (
                    response.get("active_ai_rollout")
                    if isinstance(response.get("active_ai_rollout"), dict)
                    else {}
                )
                rollout_flags = (
                    rollout_payload.get("execution_flags")
                    if isinstance(rollout_payload.get("execution_flags"), dict)
                    else {}
                )
                device_info = getattr(self, "device_info", {})
                if not isinstance(device_info, dict):
                    device_info = {}
                is_enabled = getattr(self, "_is_enabled", None)
                rollout_actions = enrich_active_ai_action_spaces(actions, device_info)
                original_actions = list(actions)
                rollout_config = ActiveAiRolloutConfig.from_mapping(
                    rollout_payload
                )
                scoped_actions = scope_active_ai_canary_actions(
                    original_actions,
                    rollout_config,
                )
                rollout_scope_filtered_entity_ids = list(
                    scoped_actions.blocked_entity_ids
                )
                authorized_actions = list(actions)
                if not scoped_actions.entity_missing:
                    authorized_actions = list(scoped_actions.actions)
                    rollout_actions = enrich_active_ai_action_spaces(
                        authorized_actions,
                        device_info,
                    )
                blocked_entity_ids = set(rollout_scope_filtered_entity_ids)
                rollout_blocked_actions = []
                for action in original_actions:
                    if not isinstance(action, dict):
                        continue
                    action_entity_id = str(
                        action.get("entity_id")
                        or action.get("entity")
                        or (
                            action.get("target", {}).get("entity_id")
                            if isinstance(action.get("target"), dict)
                            else ""
                        )
                        or ""
                    ).strip().lower()
                    if action_entity_id not in blocked_entity_ids:
                        continue
                    rollout_blocked_actions.append(
                        {
                            **action,
                            "status": "blocked_by_rollout",
                            "reason": "active_ai_canary_entity_not_allowed",
                        }
                    )
                trigger_info = device_info.get(entity_id, {})
                if not isinstance(trigger_info, dict):
                    trigger_info = {}
                rollout_decision = evaluate_active_ai_execution_gate(
                    ai_enabled=bool(is_enabled()) if callable(is_enabled) else False,
                    config=rollout_config,
                    trigger_space_id=str(
                        (result.get("trigger_space_id") if isinstance(result, dict) else "")
                        or trigger_info.get("space_id")
                        or trigger_info.get("room_id")
                        or trigger_info.get("area_id")
                        or (result.get("trigger_room") if isinstance(result, dict) else "")
                        or device_info.get(entity_id, {}).get("room", "")
                    ),
                    actions=rollout_actions,
                    execution_flags=rollout_flags,
                )
                if matched and not rollout_decision.allow_execution and not execution_suppressed_reason:
                    execution_suppressed_reason = rollout_decision.reason
                rollout_trace = rollout_decision.as_trace()
                execution_result_payload = (
                    dict(result) if isinstance(result, dict) else {}
                )
                execution_result_payload["actions"] = authorized_actions
                if rollout_blocked_actions:
                    execution_result_payload["rollout_original_actions"] = (
                        original_actions
                    )
                    execution_result_payload["rollout_blocked_actions"] = (
                        rollout_blocked_actions
                    )
                audit_pending = bool(
                    matched
                    and arbitration_validation.allowed
                    and not execution_suppressed_reason
                    and self._fast_path_result_allows_slow_audit(
                        authorized_actions
                    )
                )
                self._sys_log(
                    "INFO",
                    "[Add-on FastPath] result "
                    f"status={status} matched={matched} path_taken={path_taken} "
                    f"reason={reason or '-'} scene={scene or '-'} "
                    f"decision_reason={decision_reason or '-'} "
                    f"arbitration_reason={arbitration_reason or '-'} "
                    f"confidence={confidence if confidence is not None else '-'} "
                    f"confidence_auto={confidence_auto if confidence_auto is not None else '-'} "
                    f"confidence_notify={confidence_notify if confidence_notify is not None else '-'} "
                    f"confirm_required={confirm_required} "
                    f"confirm_suppressed_reason={confirm_suppressed_reason or '-'} "
                    f"learning_mode={addon_learning_mode if addon_learning_mode is not None else '-'} "
                    f"habit_proactive={addon_habit_proactive if addon_habit_proactive is not None else '-'} "
                    f"action_count={action_count} entity={entity_id} correlation_id={correlation_id}",
                )
                self._emit_addon_fast_path_event(
                    {
                        "source": "addon_fast_path",
                        "entity_id": entity_id,
                        "old_state": old_state,
                        "new_state": new_state,
                        "status": status,
                        "matched": matched,
                        "path_taken": path_taken,
                        "reason": reason,
                        "decision_reason": decision_reason,
                        "arbitration_reason": arbitration_reason,
                        "scene": scene,
                        "confidence": confidence,
                        "confidence_auto": confidence_auto,
                        "confidence_notify": confidence_notify,
                        "threshold": threshold,
                        "auto_execute": arbitration_validation.allowed,
                        "arbitration_result": arbitration_result,
                        "confirm_required": confirm_required,
                        "confirm_suppressed_reason": confirm_suppressed_reason,
                        "action_count": action_count,
                        "actions": original_actions,
                        "authorized_action_count": len(authorized_actions),
                        "authorized_actions": authorized_actions,
                        "rollout_blocked_actions": rollout_blocked_actions,
                        "transaction_id": transaction_id,
                        "decision_trace": decision_trace,
                        "correlation_id": correlation_id,
                        "world_snapshot_id": world_snapshot_id,
                        "executed": False,
                        "execution_status": "pending" if audit_pending else "not_started",
                        "provisional_execution": audit_pending,
                        "audit_pending": audit_pending,
                        "rollback_allowed": audit_pending,
                        "execution_suppressed_reason": execution_suppressed_reason,
                        "rollout": rollout_trace,
                        "rollout_scope_filtered_entity_ids": (
                            rollout_scope_filtered_entity_ids
                        ),
                        "fail_closed": arbitration_fail_closed or not (200 <= status < 300),
                        "snapshot": snapshot_diag,
                    }
                )
                if 200 <= status < 300 and matched and confirm_required and isinstance(result, dict):
                    confirm_payload = {
                        "source": "addon_fast_path",
                        "entity_id": entity_id,
                        "old_state": old_state,
                        "new_state": new_state,
                        "scene": scene,
                        "confidence": confidence,
                        "confidence_auto": confidence_auto,
                        "confidence_notify": confidence_notify,
                        "action_count": action_count,
                        "actions": actions,
                        "trigger": f"{entity_id}: {old_state} -> {new_state}",
                        "reply": "AI 已命中候选动作，但置信度低于自动执行阈值，等待用户确认。",
                        "reason": reason,
                        "decision_reason": decision_reason,
                        "arbitration_reason": arbitration_reason,
                        "path_taken": path_taken,
                        "result": result,
                        "txn_id": transaction_id or None,
                    }
                    try:
                        self.hass.bus.async_fire("smart_agent_confirm_required", confirm_payload)
                    except Exception as exc:
                        _LOGGER.debug("[Listeners] smart_agent_confirm_required emit failed: %s", exc)
                    self._sys_log(
                        "INFO",
                        f"[Add-on FastPath] confirm_required | entity={entity_id} "
                        f"confidence={confidence if confidence is not None else '-'} "
                        f"confidence_auto={confidence_auto if confidence_auto is not None else '-'} "
                        f"confidence_notify={confidence_notify if confidence_notify is not None else '-'} "
                        f"actions={action_count}",
                    )
                if 200 <= status < 300 and matched and isinstance(result, dict):
                    if execution_suppressed_reason:
                        if not await _finalize_fast_path_claim(
                            "fast_path_execution_suppressed",
                            required_for_action=False,
                        ):
                            return
                        self._sys_log(
                            "INFO",
                            f"[Add-on FastPath] execution suppressed | entity={entity_id} reason={execution_suppressed_reason}",
                        )
                        if execution_suppressed_reason.startswith("active_ai_"):
                            await self._execute_fast_path_decision_result(
                                execution_result_payload,
                                entity_id=entity_id,
                                source_label="AddonFastPath",
                                transaction_id=transaction_id,
                                correlation_id=correlation_id,
                                world_snapshot_id=world_snapshot_id,
                                decision_trace=decision_trace,
                                trigger=f"{entity_id}: {old_state} -> {new_state}",
                                active_ai_rollout=rollout_payload,
                            )
                        else:
                            self._enqueue_fast_path_execution_audit(
                                transaction_id=transaction_id,
                                correlation_id=correlation_id,
                                world_snapshot_id=world_snapshot_id,
                                decision_trace=decision_trace,
                                trigger=f"{entity_id}: {old_state} -> {new_state}",
                                scene=scene,
                                confidence=confidence,
                                actions=actions,
                                execution_result=0,
                                execution_suppressed_reason=execution_suppressed_reason,
                                rollout=rollout_trace,
                            )
                        return
                    if not audit_pending and not await _finalize_fast_path_claim(
                        "fast_path_completed",
                        required_for_action=True,
                    ):
                        return
                    self._sys_log("INFO", f"[Add-on FastPath] 命中规则: {result.get('scene', 'FastPath')}")
                    previous_batch_trigger_controllable = getattr(
                        self,
                        "_batch_trigger_controllable",
                        set(),
                    )
                    domain = entity_id.split(".")[0]
                    if domain in ("light", "switch", "fan", "cover", "climate", "media_player"):
                        self._batch_trigger_controllable = {entity_id}
                        self._sys_log(
                            "INFO",
                            f"[自触发保护] FastPath 可控设备触发: {entity_id}，AI 不可反向操作该设备",
                        )
                    try:
                        execution_audit_context = await self._execute_fast_path_decision_result(
                            execution_result_payload,
                            entity_id=entity_id,
                            source_label="AddonFastPath",
                            transaction_id=transaction_id,
                            correlation_id=correlation_id,
                            world_snapshot_id=world_snapshot_id,
                            decision_trace=decision_trace,
                            trigger=f"{entity_id}: {old_state} -> {new_state}",
                            active_ai_rollout=rollout_payload,
                        )
                    finally:
                        self._batch_trigger_controllable = previous_batch_trigger_controllable
                    if event_claim:
                        execution_audit_context["event_claim"] = dict(event_claim)
                    if (
                        audit_pending
                        and execution_audit_context.get("final_outcome") == "succeeded"
                    ):
                        self._schedule_inference(
                            entity_id,
                            f"{entity_id}: {old_state} -> {new_state}",
                            new_state,
                            one_off_prompt=self._fast_path_slow_audit_prompt(),
                            _allow_learning_mode_inference=True,
                            source_trace_context=execution_audit_context,
                        )
                    elif audit_pending:
                        await _finalize_fast_path_claim(
                            "fast_path_execution_failed",
                            required_for_action=False,
                        )
                    return
                if 200 <= status < 300:
                    should_fail_closed = False
                    if reason == "local_fast_brain_disabled" or response.get("fast_path_disabled") is True:
                        self._sys_log(
                            "INFO",
                            f"[Add-on FastPath] disabled; scheduling slow inference | entity={entity_id}",
                        )
                        self._schedule_inference(
                            entity_id,
                            f"{entity_id}: {old_state} -> {new_state}",
                            new_state,
                            source_trace_context=_fast_path_handoff_context("addon_fast_path_disabled"),
                        )
                        return
                    if reason == "no_match":
                        if slow_fallback_allowed(suppress_slow_fallback, self._should_slow_infer_after_fast_path_no_match(entity_id, new_state, snapshot)):
                            self._sys_log(
                                "INFO",
                                f"[Add-on FastPath] no_match; scheduling slow inference | entity={entity_id} "
                                f"active_space={snapshot_diag.get('active_space') or '-'}",
                            )
                            self._schedule_inference(
                                entity_id,
                                f"{entity_id}: {old_state} -> {new_state}",
                                new_state,
                                source_trace_context=_fast_path_handoff_context("addon_fast_path_no_match"),
                            )
                            return
                        info = self.device_info.get(entity_id, {}) if isinstance(getattr(self, "device_info", None), dict) else {}
                        if not isinstance(info, dict):
                            info = {}
                        skip_reason = self._fast_path_no_match_slow_inference_skip_reason(
                            entity_id,
                            new_state,
                            snapshot,
                        )
                        self._sys_log(
                            "INFO",
                            f"[Add-on FastPath] no_match; slow inference not scheduled | "
                            f"reason={skip_reason or 'not_presence_arrival'} entity={entity_id} state={new_state} "
                            f"sensor_type={info.get('sensor_type') or '-'} name={info.get('name') or '-'}",
                        )
                        await _finalize_fast_path_claim(
                            "fast_path_no_fallback",
                            required_for_action=False,
                        )
                    if reason == "confidence_below_auto_threshold" and not confirm_required:
                        if slow_fallback_allowed(suppress_slow_fallback, (
                            action_count > 0
                            or self._should_slow_infer_after_fast_path_no_match(entity_id, new_state, snapshot)
                        )):
                            self._sys_log(
                                "INFO",
                                f"[Add-on FastPath] confidence_below_auto_threshold; scheduling slow inference | "
                                f"entity={entity_id} confidence={confidence if confidence is not None else '-'} "
                                f"confidence_auto={confidence_auto if confidence_auto is not None else '-'} "
                                f"confidence_notify={confidence_notify if confidence_notify is not None else '-'} "
                                f"actions={action_count} "
                                f"confirm_suppressed_reason={confirm_suppressed_reason or '-'} "
                                f"active_space={snapshot_diag.get('active_space') or '-'}",
                            )
                            self._schedule_inference(
                                entity_id,
                                f"{entity_id}: {old_state} -> {new_state}",
                                new_state,
                                _allow_learning_mode_inference=(confirm_suppressed_reason == "learning_mode"),
                                source_trace_context=_fast_path_handoff_context("addon_fast_path_low_confidence"),
                            )
                            return
                        info = self.device_info.get(entity_id, {}) if isinstance(getattr(self, "device_info", None), dict) else {}
                        if not isinstance(info, dict):
                            info = {}
                        self._sys_log(
                            "INFO",
                            f"[Add-on FastPath] confidence_below_auto_threshold; slow inference not scheduled | "
                            f"reason=no_action_candidate_or_not_presence_arrival entity={entity_id} state={new_state} "
                            f"sensor_type={info.get('sensor_type') or '-'} name={info.get('name') or '-'}",
                        )
                        await _finalize_fast_path_claim(
                            "fast_path_no_fallback",
                            required_for_action=False,
                        )
                    if reason not in {"no_match", "confidence_below_auto_threshold"}:
                        await _finalize_fast_path_claim(
                            "fast_path_filtered",
                            required_for_action=False,
                        )
                    self._sys_log(
                        "INFO",
                        f"[Add-on FastPath] not matched; HA local decision skipped | status={status} matched={response.get('matched')}",
                    )
                elif status == 409:
                    self._sys_log(
                        "WARN",
                        f"[Add-on FastPath] addon_fast_path_input_incomplete fail-closed | "
                        f"status={status} reason={reason or 'input_incomplete'} entity={entity_id}",
                    )
                    if slow_fallback_allowed(suppress_slow_fallback, self._should_slow_infer_after_fast_path_no_match(entity_id, new_state, snapshot)):
                        self._sys_log(
                            "INFO",
                            f"[Add-on FastPath] 409 input incomplete; scheduling slow inference | "
                            f"entity={entity_id} reason={reason or 'input_incomplete'} "
                            f"active_space={snapshot_diag.get('active_space') or '-'}",
                        )
                        self._schedule_inference(
                            entity_id,
                            f"{entity_id}: {old_state} -> {new_state}",
                            new_state,
                            source_trace_context=_fast_path_handoff_context(
                                "addon_fast_path_409"
                            ),
                        )
                    else:
                        await _finalize_fast_path_claim(
                            "fast_path_input_incomplete",
                            required_for_action=False,
                        )
                    return
                elif status > 0:
                    await _finalize_fast_path_claim(
                        "fast_path_execution_failed",
                        required_for_action=False,
                    )
                    self._sys_log(
                        "INFO",
                        f"[Add-on FastPath] addon_unreachable fail-closed | "
                        f"status={status} matched={response.get('matched')} reason={reason or '-'}",
                    )
                    return

    if should_fail_closed:
        self._sys_log(
            "ERROR",
            f"[Add-on FastPath] addon_unreachable fail-closed | entity={entity_id} reason=unreachable",
        )
        self._emit_addon_fast_path_event(
            {
                "source": "addon_fast_path",
                "entity_id": entity_id,
                "old_state": old_state,
                "new_state": new_state,
                "status": 0,
                "matched": False,
                "path_taken": "none",
                "reason": "unreachable",
                "fail_closed": True,
                "snapshot": snapshot_diag,
            }
        )
    return

__all__ = ["run_addon_fast_path_fail_closed"]
