"""Portable state-event orchestration for the HA listener callback.

The listener mixin retains HA subscription ownership and passes the event plus
its existing helper surface into this module. This runtime does not register
listeners, call HA services, persist data directly, or own execution authority.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .const import SOURCE_AUTOMATION, SOURCE_DASHBOARD
from .presence_runtime import occupancy_cycle_outcome, schedule_arrival_baseline_sample
from .sensor_event_filter import EnvironmentTelemetryFilter


def handle_listener_state_changed(
    self: Any,
    ev: Any,
    *,
    logger: logging.Logger,
) -> None:
    """Process one already-subscribed HA state-change event."""
    data = ev.data
    entity_id = data.get("entity_id")
    if not entity_id:
        return
    new = data.get("new_state")
    old = data.get("old_state")
    new_s = new.state if new else ""
    old_s = old.state if old else ""

    source_type = "物理/自动"
    if new and new.context:
        if new.context.user_id:
            source_type = "用户界面"
        elif new.context.parent_id:
            source_type = "自动化/脚本"

    domain = entity_id.split(".")[0]
    device_info_snapshot = getattr(self, "device_info", {}) or {}
    if not isinstance(device_info_snapshot, dict):
        device_info_snapshot = {}
    environment_device_info = (
        getattr(self, "_environment_context_device_info", {}) or {}
    )
    if isinstance(environment_device_info, dict):
        device_info_snapshot = {
            **device_info_snapshot,
            **environment_device_info,
        }
    if entity_id not in device_info_snapshot:
        try:
            if self._reconcile_device_info_entity_ids_from_ha_registry():
                device_info_snapshot = getattr(self, "device_info", {}) or {}
                environment_device_info = (
                    getattr(
                        self,
                        "_environment_context_device_info",
                        {},
                    )
                    or {}
                )
                if isinstance(environment_device_info, dict):
                    device_info_snapshot = {
                        **device_info_snapshot,
                        **environment_device_info,
                    }
        except Exception as exc:
            logger.debug("[Listeners] state-handler reconciliation skipped for %s: %s", entity_id, exc)
    if entity_id not in device_info_snapshot:
        unmanaged_filter_reason = "unmanaged_entity"
        self._last_listener_filter_reason = unmanaged_filter_reason
        logger.debug(
            "[ListenerFilter] managed=false filter_reason=unmanaged_entity "
            "path=state_handler entity=%s old_state=%s new_state=%s source_type=%s reason=%s",
            entity_id,
            old_s,
            new_s,
            source_type,
            unmanaged_filter_reason,
        )
        warned = getattr(self, "_unmanaged_listener_entity_warned", set())
        if not isinstance(warned, set):
            warned = set()
        if entity_id not in warned:
            warned.add(entity_id)
            self._unmanaged_listener_entity_warned = warned
            log = getattr(self, "_sys_log", None)
            message = (
                "[监听器] 收到未纳管实体状态变化，未触发 AI 决策: "
                f"{entity_id} {old_s}->{new_s}。请在设备页纳管该实体，或检查 HA 实体 ID 是否已改名。"
            )
            if callable(log):
                log("WARN", message)
            else:
                logger.warning(message)
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason=unmanaged_filter_reason,
            source_type=source_type,
        )
        return

    environment_telemetry_tracked = False
    if domain == "sensor":
        environment_metadata = self._listener_entity_metadata(
            entity_id,
            info=device_info_snapshot.get(entity_id),
            state_obj=new,
        )
        environment_filter = getattr(self, "_environment_telemetry_event_filter", None)
        if not isinstance(environment_filter, EnvironmentTelemetryFilter):
            environment_filter = EnvironmentTelemetryFilter()
            self._environment_telemetry_event_filter = environment_filter
        environment_decision = environment_filter.evaluate(
            entity_id,
            old_s,
            new_s,
            metadata=environment_metadata,
            now=time.monotonic(),
        )
        environment_telemetry_tracked = environment_decision.tracked
        if environment_decision.tracked and not environment_decision.forward:
            self._last_listener_filter_reason = (
                f"environment_telemetry_{environment_decision.reason}"
            )
            logger.debug(
                "[ListenerFilter] environment telemetry sampled entity=%s kind=%s "
                "reason=%s delta=%s threshold=%s elapsed=%s",
                entity_id,
                environment_decision.sensor_kind,
                environment_decision.reason,
                environment_decision.delta,
                environment_decision.threshold,
                environment_decision.elapsed,
            )
            return

    logger.debug("[事件] %s: %s -> %s (来源: %s)", entity_id, old_s, new_s, source_type)
    self._emit_listener_event(
        listener_action="received",
        entity_id=entity_id,
        old_state=old_s,
        new_state=new_s,
        source_type=source_type,
    )

    # ── 传感器静默 ──
    if self._sensors_muted and domain in ("binary_sensor", "sensor"):
        self._sys_log("INFO", f"[传感器静默] {entity_id} {old_s}→{new_s}，静默中跳过")
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason="sensors_muted",
            source_type=source_type,
        )
        return

    if (
        domain == "sensor"
        and old_s
        and new_s
        and not environment_telemetry_tracked
    ):
        try:
            delta = abs(float(new_s) - float(old_s))
            eid_lower = entity_id.lower()
            # Presence person_count retains its dimension-specific step.
            # Every other numeric signal must be described by a SignalManifest;
            # never fall back to one cross-dimension numeric threshold.
            frigate_on = getattr(self, "_frigate_enabled", False)
            is_person_count = frigate_on and any(kw in eid_lower for kw in self._PERSON_COUNT_KW)
            if is_person_count and delta < 1:
                logger.debug(
                    "[ListenerFilter] person_count deadband entity=%s delta=%.3f threshold=1",
                    entity_id,
                    delta,
                )
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="person_count_deadband",
                    source_type=source_type,
                    delta=delta,
                    threshold=1,
                )
                return
            if not is_person_count:
                self._last_listener_filter_reason = "untyped_numeric_signal_quarantine"
                logger.warning(
                    "[ListenerFilter] untyped numeric signal quarantined entity=%s delta=%.3f",
                    entity_id,
                    delta,
                )
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="untyped_numeric_signal_quarantine",
                    source_type=source_type,
                    delta=delta,
                )
                return
        except (ValueError, TypeError):
            pass

    # P0修复：AI 主开关检查必须先于 add-on 快路，
    # 否则关闭 AI 仍会执行设备控制动作。
    if not self._is_enabled():
        self._sys_log("INFO", f"[过滤] AI 已暂停，跳过 add-on 快路: {entity_id}")
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason="ai_disabled",
            source_type=source_type,
        )
        return
    # 启动冷却保护：系统初始化期间也不执行快路
    _startup_elapsed = time.time() - self._startup_time
    if _startup_elapsed < self._startup_grace:
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason="startup_cooldown",
            source_type=source_type,
            startup_remaining=max(0, int(self._startup_grace - _startup_elapsed)),
        )
        return

    if new_s in ("unavailable", "unknown"):
        self._sys_log("INFO", f"[过滤] 设备状态变为 {new_s}，跳过 add-on 快路: {entity_id}")
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason="state_unavailable_unknown",
            source_type=source_type,
        )
        return

    if old_s in ("unavailable", "unknown"):
        self._sys_log(
            "INFO",
            f"[过滤] 设备从 {old_s} 恢复为 {new_s}，跳过 add-on 快路: {entity_id}",
        )
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason="state_recovery_unknown_unavailable",
            source_type=source_type,
        )
        return

    last_ai_actions = getattr(self, "_last_ai_actions", {})
    last_ai = last_ai_actions.get(entity_id) if isinstance(last_ai_actions, dict) else None
    if isinstance(last_ai, dict):
        expected_ai_state = str(last_ai.get("state") or "").strip().lower()
        try:
            stability_deadline = float(last_ai.get("learning_stability_deadline") or 0)
        except (TypeError, ValueError):
            stability_deadline = 0
        if (
            expected_ai_state
            and new_s != expected_ai_state
            and time.time() <= stability_deadline
        ):
            last_ai["reverse_user_action"] = True
            last_ai["reverse_user_action_state"] = new_s
            last_ai["reverse_user_action_source"] = source_type
    if isinstance(last_ai, dict) and str(last_ai.get("state") or "") == new_s:
        try:
            ai_action_age = time.time() - float(last_ai.get("time") or 0)
        except (TypeError, ValueError):
            ai_action_age = self._AI_ACTION_SKIP_WINDOW + 1
        if 0 <= ai_action_age < self._AI_ACTION_SKIP_WINDOW:
            self._record_presence_interaction_trace(
                entity_id,
                domain,
                new_s,
                source_type,
                source=SOURCE_AUTOMATION,
            )
            self._sys_log(
                "INFO",
                f"[过滤] AI 操作后 {int(ai_action_age)}s 内同向变化，跳过 add-on 快路: {entity_id} -> {new_s}",
            )
            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
                filter_reason="ai_self_action",
                source_type=source_type,
                ai_action_age=int(ai_action_age),
            )
            return

    self._record_arrival_manual_action_evidence(
        entity_id=entity_id,
        old_state=old_s,
        new_state=new_s,
        new_state_obj=new,
        source_type=source_type,
        device_info=dict(device_info_snapshot.get(entity_id) or {}),
    )

    if new and new.context and new.context.user_id:
        record_operation = getattr(self, "_record_device_operation", None)
        if callable(record_operation):
            record_operation(entity_id, SOURCE_DASHBOARD, new_s)

        user_overrides = getattr(self, "_user_overrides", None)
        user_overrides_lock = getattr(self, "_user_overrides_lock", None)
        if isinstance(user_overrides, dict) and user_overrides_lock is not None:
            with user_overrides_lock:
                user_overrides[entity_id] = {
                    "state": new_s,
                    "time": time.time(),
                }

        user_manual_actions = getattr(self, "_user_manual_actions", None)
        user_manual_actions_lock = getattr(self, "_user_manual_actions_lock", None)
        if isinstance(user_manual_actions, dict) and user_manual_actions_lock is not None:
            with user_manual_actions_lock:
                user_manual_actions[entity_id] = {
                    "state": new_s,
                    "time": time.time(),
                }

    implicit_correction_recorded = self._record_implicit_reverse_correction(
        entity_id=entity_id,
        domain=domain,
        old_state=old_s,
        new_state=new_s,
        new_state_obj=new,
        source_type=source_type,
        device_info=dict(device_info_snapshot.get(entity_id) or {}),
    )
    self._record_silent_learning_behavior_sample(entity_id, old_s, new_s, source_type, old, new)
    self._record_presence_interaction_trace(entity_id, domain, new_s, source_type)

    if domain in self._CONTROL_EVENT_DOMAINS:
        filter_reason = (
            "implicit_reverse_correction"
            if implicit_correction_recorded
            else "controllable_state_feedback"
        )
        self._last_listener_filter_reason = filter_reason
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason=filter_reason,
            source_type=source_type,
        )
        return

    info = device_info_snapshot.get(entity_id) if isinstance(device_info_snapshot, dict) else {}
    info = self._listener_entity_metadata(entity_id, info=info, state_obj=new)
    is_presence_sensor = self._is_presence_listener_entity(entity_id, info)
    if domain == "binary_sensor" and not is_presence_sensor:
        if self._is_actionable_contact_arrival_for_slow_inference(entity_id, new_s):
            causal_observed_at = ""
            for timestamp_key in ("last_updated", "last_changed"):
                timestamp = getattr(new, timestamp_key, None)
                isoformat = getattr(timestamp, "isoformat", None)
                if callable(isoformat):
                    causal_observed_at = str(isoformat() or "").strip()
                elif timestamp not in (None, ""):
                    causal_observed_at = str(timestamp).strip()
                if causal_observed_at:
                    break
            causal_event = {
                "entity_id": entity_id,
                "old_state": old_s,
                "new_state": new_s,
                "observed_at": causal_observed_at,
                "source_event_id": (
                    f"ha_state:{entity_id}:{causal_observed_at}"
                    if causal_observed_at
                    else ""
                ),
                "quality": "good",
            }
            self._last_listener_filter_reason = "contact_slow_path_only"
            self._emit_listener_event(
                listener_action="slow_path_scheduled",
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
                filter_reason="contact_not_presence",
                source_type=source_type,
            )
            self._schedule_inference(
                entity_id,
                f"{entity_id}: {old_s} -> {new_s}",
                new_s,
                causal_event=causal_event,
            )
        else:
            self._last_listener_filter_reason = "non_presence_binary_sensor"
            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
                filter_reason="non_presence_binary_sensor",
                source_type=source_type,
                device_class=str(info.get("device_class") or ""),
                sensor_type=str(info.get("sensor_type") or ""),
            )
        return
    old_presence_state = str(old_s or "").strip().lower()
    new_presence_state = str(new_s or "").strip().lower()
    if (
        is_presence_sensor
        and old_presence_state != new_presence_state
        and old_presence_state in {"on", "off"}
        and new_presence_state in {"on", "off"}
    ):
        suppressed, remaining = self._is_presence_flap_suppressed(entity_id)
        if suppressed:
            self._sys_log("INFO", f"[存在去抖] {entity_id} 抖动抑制中，剩余 {remaining}s，跳过 add-on 快路")
            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
                filter_reason="presence_flap_suppressed",
                source_type=source_type,
                suppress_remaining=remaining,
            )
            return
        self._record_presence_flap(entity_id)

    occupancy_cycle_id, arrival_started, duplicate_arrival, learning_cycle_status = occupancy_cycle_outcome(
        self, entity_id, old_s, new_s,
        is_presence_sensor=is_presence_sensor,
        old_presence_state=old_presence_state,
        new_presence_state=new_presence_state,
    )

    if is_presence_sensor and duplicate_arrival:
        self._cancel_presence_temporal_recheck(entity_id)
        self._emit_listener_event(
            listener_action="filtered",
            entity_id=entity_id,
            old_state=old_s,
            new_state=new_s,
            filter_reason="duplicate_occupancy_cycle",
            source_type=source_type,
            occupancy_cycle_id=occupancy_cycle_id,
            learning_cycle_status=learning_cycle_status,
        )
        return

    schedule_arrival_baseline_sample(
        self, entity_id, old_s, new_s,
        is_presence_sensor=is_presence_sensor,
        arrival_started=arrival_started,
        occupancy_cycle_id=occupancy_cycle_id,
    )
    self._emit_listener_event(
        listener_action="fast_path_scheduled",
        entity_id=entity_id,
        old_state=old_s,
        new_state=new_s,
        source_type=source_type,
        occupancy_cycle_id=occupancy_cycle_id,
        learning_cycle_status=learning_cycle_status,
    )
    try:
        fast_path_coro = self._run_addon_fast_path_fail_closed(
            entity_id,
            new_s,
            old_s,
            occupancy_cycle_id=occupancy_cycle_id,
        )
    except TypeError as exc:
        if "occupancy_cycle_id" not in str(exc):
            raise
        fast_path_coro = self._run_addon_fast_path_fail_closed(
            entity_id,
            new_s,
            old_s,
        )
    self._spawn_addon_fast_path_task(
        fast_path_coro,
        entity_id=entity_id,
        old_state=old_s,
        new_state=new_s,
    )
    return


__all__ = ["handle_listener_state_changed"]
