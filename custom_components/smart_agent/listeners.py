"""
ListenersMixin — 事件监听层。
负责：HA 状态变化监听、存在传感器去抖、触发合并、冷却管理、快速通道。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .ha_adapter import async_call_service
from .active_ai_rollout import (
    ActiveAiRolloutConfig,
    DEFAULT_ACTIVE_AI_MODE,
    enrich_active_ai_action_spaces,
    evaluate_active_ai_execution_gate,
    normalize_active_ai_mode,
)
from .confidence_arbitration_contract import validate_auto_execution_arbitration
from .sensor_event_filter import EnvironmentTelemetryFilter, environment_sensor_kind
from .const import (
    FRIGATE_PERSON_COUNT_KW as _FRIGATE_PERSON_COUNT_KW,
    AI_ACTION_SKIP_WINDOW, URGENT_MERGE_WINDOW, NORMAL_MERGE_WINDOW,
    GLITCH_THRESHOLD, GLITCH_WINDOW, GLITCH_SUPPRESS_SECS,
    PRESENCE_OFF_DELAY, PRESENCE_ON_COOLDOWN, PRESENCE_ON_MIN_HOLD,
    PRESENCE_FLAP_WINDOW, PRESENCE_FLAP_THRESHOLD, PRESENCE_FLAP_SUPPRESS_SECS,
    FRIGATE_COUNT_ON_HOLD, FRIGATE_COUNT_CHANGE_HOLD,
    FRIGATE_COUNT_OFF_HOLD, FRIGATE_COUNT_COOLDOWN,
    SENSOR_DEADBAND_PCT,
    SOURCE_AUTOMATION, SOURCE_DASHBOARD, SOURCE_PHYSICAL, SOURCE_VOICE,
    DEVICE_VACANT_ACTIONS,
)

_LOGGER = logging.getLogger(__name__)
_CMD_SOURCE_SENSOR = "SENSOR"
_FAST_PATH_FIXED_TIMEZONE_OFFSETS = {
    "Asia/Shanghai": 8,
    "Asia/Chongqing": 8,
    "Asia/Harbin": 8,
}


def _fast_path_timezone(configured_timezone: str) -> Any | None:
    try:
        return ZoneInfo(configured_timezone)
    except ZoneInfoNotFoundError:
        offset = _FAST_PATH_FIXED_TIMEZONE_OFFSETS.get(configured_timezone)
        if offset is None:
            raise
        return timezone(timedelta(hours=offset))


class ListenersMixin:
    """Mixin: 事件监听 — 状态变化 / 去抖 / 触发调度 / 快速通道。"""

    # AI 操作后 N 秒内的同向状态变化视为 AI 自身引起，不再触发
    _AI_ACTION_SKIP_WINDOW = AI_ACTION_SKIP_WINDOW
    _ARRIVAL_CAUSAL_WINDOW_SECONDS = 30.0

    # 触发合并窗口
    _URGENT_MERGE_WINDOW = URGENT_MERGE_WINDOW    # binary_sensor 类触发：1 秒
    _NORMAL_MERGE_WINDOW = NORMAL_MERGE_WINDOW    # 其他：3 秒

    # 通信闪断累计抑制参数
    _GLITCH_THRESHOLD = GLITCH_THRESHOLD
    _GLITCH_WINDOW = GLITCH_WINDOW
    _GLITCH_SUPPRESS_SECS = GLITCH_SUPPRESS_SECS

    # 存在传感器去抖参数（binary_sensor.*）
    _PRESENCE_KW = ("occupancy", "presence", "motion", "人体", "存在", "有人", "移动",
                    "ren_ti", "cun_zai", "radar", "mmwave", "雷达",
                    "person_occupancy", "object_count")  # Frigate 生成的占用实体
    _ACTIONABLE_SENSOR_TYPES = frozenset(
        {
            "pir",
            "mmwave",
            "presence",
            "human_presence",
            "occupancy",
            "motion",
            "moving",
            "frigate",
            "radar",
            "person",
            "person_count",
            "object_count",
            "vision",
        }
    )
    _PRESENCE_DEVICE_CLASSES = frozenset({"motion", "moving", "occupancy", "presence"})
    _GENERIC_BINARY_CLASS_VALUES = frozenset({"", "binary_sensor", "sensor", "unknown"})
    _ACTIONABLE_CONTACT_SENSOR_TYPES = frozenset({"door", "window", "contact", "opening", "garage_door"})
    _ACTIONABLE_CONTACT_KW = ("door", "window", "contact", "opening", "men_chuang", "garage", "门", "窗", "门窗")
    _PRESENCE_OFF_DELAY = PRESENCE_OFF_DELAY
    _PRESENCE_ON_COOLDOWN = PRESENCE_ON_COOLDOWN
    _PRESENCE_ON_MIN_HOLD = PRESENCE_ON_MIN_HOLD
    _PRESENCE_FLAP_WINDOW = PRESENCE_FLAP_WINDOW
    _PRESENCE_FLAP_THRESHOLD = PRESENCE_FLAP_THRESHOLD
    _PRESENCE_FLAP_SUPPRESS_SECS = PRESENCE_FLAP_SUPPRESS_SECS

    # Frigate person_count sensor 触发阈值
    _PERSON_COUNT_KW = _FRIGATE_PERSON_COUNT_KW

    # Frigate 人数传感器防抖参数
    _FRIGATE_COUNT_ON_HOLD = FRIGATE_COUNT_ON_HOLD
    _FRIGATE_COUNT_CHANGE_HOLD = FRIGATE_COUNT_CHANGE_HOLD
    _FRIGATE_COUNT_OFF_HOLD = FRIGATE_COUNT_OFF_HOLD
    _FRIGATE_COUNT_COOLDOWN = FRIGATE_COUNT_COOLDOWN

    # 数值型传感器触发死区
    _SENSOR_DEADBAND_PCT: float = SENSOR_DEADBAND_PCT

    # 人工交互可作为无硬件房间的 enter-only 在场证据。
    _PRESENCE_INTERACTION_DOMAINS = frozenset({"light", "media_player", "climate"})
    _PRESENCE_INTERACTION_HUMAN_SOURCES = frozenset({SOURCE_PHYSICAL, SOURCE_DASHBOARD, SOURCE_VOICE})
    _PRESENCE_INTERACTION_AI_SELF_WINDOW = 15 * 60
    _DAYLIGHT_AUTO_LIGHTING_SUPPRESSED = "daylight_auto_lighting_suppressed"
    _DAYLIGHT_SUN_STATES = frozenset({"above_horizon", "day", "daylight"})
    _DARK_SUN_STATES = frozenset({"below_horizon", "night", "dark"})
    _DAYLIGHT_GUARD_LUX_THRESHOLD = 80.0
    _DAYLIGHT_FALLBACK_START_HOUR = 8
    _DAYLIGHT_FALLBACK_END_HOUR = 20
    _PROTECTED_NIGHT_START_HOUR = 22
    _PROTECTED_NIGHT_END_HOUR = 6
    _CORRECTION_SUPPRESSIONS_CACHE_TTL = 60.0
    _LISTENER_DOMAINS = frozenset(
        (
            "binary_sensor",
            "sensor",
            "device_tracker",
            "person",
            "light",
            "switch",
            "climate",
            "cover",
            "fan",
            "media_player",
        )
    )
    _CONTROL_EVENT_DOMAINS = frozenset({"light", "switch", "climate", "cover", "fan", "media_player"})

    # 按时段调整开灯亮度的参考表
    _BRIGHTNESS_TABLE = (
        (6, 8, 70),
        (8, 18, 100),
        (18, 21, 80),
        (21, 23, 60),
        (23, 24, 20),
        (0, 6, 20),
    )

    # ── 触发校验 ──────────────────────────────────────────────────────────────

    def _should_trigger(self, entity_id: str, old: str, new: str) -> bool:
        if not self._is_enabled():
            self._sys_log("WARN", f"触发被拒: AI 已暂停 | {entity_id}")
            return False
        elapsed = time.time() - self._startup_time
        if elapsed < self._startup_grace:
            remaining = int(self._startup_grace - elapsed)
            self._sys_log("INFO", f"启动冷却中({remaining}s 后就绪)，忽略触发: {entity_id} {old}→{new}")
            if remaining <= 3 and not getattr(self, "_startup_ready_notified", False):
                self._startup_ready_notified = True
                self._sys_log("INFO", "✅ 系统即将就绪，下次触发将开始 AI 推理")
            return False
        if not getattr(self, "_startup_ready_notified", False):
            self._startup_ready_notified = True
            self._sys_log("INFO", f"✅ 启动冷却已结束（{int(elapsed)}s），AI 推理已就绪")
        if new in ("unavailable", "unknown"):
            self._sys_log("INFO", f"[过滤] 设备状态变为 {new}，跳过: {entity_id}")
            return False
        if old in ("unavailable", "unknown"):
            self._sys_log("INFO", f"[过滤] 设备从 {old} 恢复为 {new}，跳过: {entity_id}")
            return False
        if entity_id not in self.device_info:
            self._sys_log("WARN", f"触发被拒: {entity_id} 不在已配置设备列表中（请在设备页面添加）")
            return False

        # 数值型传感器死区过滤（SYS-02）：
        # 仅针对 sensor.* 且 old/new 均可解析为浮点数的情况做变化量检查。
        # 非数值传感器（motion: on/off / door: open/closed）直接放行。
        if entity_id.split(".")[0] == "sensor":
            try:
                _old_v = float(old)
                _new_v = float(new)
                _base = max(abs(_old_v), abs(_new_v), 1.0)
                _change_pct = abs(_new_v - _old_v) / _base * 100
                if _change_pct < self._SENSOR_DEADBAND_PCT:
                    self._sys_log(
                        "INFO",
                        f"[死区过滤] {entity_id} {old}→{new} 变化 {_change_pct:.1f}% "
                        f"< 阈值 {self._SENSOR_DEADBAND_PCT}%，跳过推理",
                    )
                    return False
            except (ValueError, TypeError):
                pass  # 非数值型状态（on/off 等），直接放行

        last_ai = self._last_ai_actions.get(entity_id)
        if last_ai:
            age = time.time() - last_ai["time"]
            if age < self._AI_ACTION_SKIP_WINDOW and last_ai["state"] == new:
                self._sys_log("INFO", f"[过滤] AI 操作后 {int(age)}s 内同向变化，跳过: {entity_id} → {new}")
                return False
        return True

    def _effective_cooldown(self) -> int:
        """展厅模式使用更短冷却以便快速响应演示。"""
        return self._SHOWROOM_COOLDOWN if self._mode == "showroom" else self.cooldown

    def _slow_inference_cooldown_key(self, entity_id: str, new_state: str) -> str:
        """避免同一存在传感器的到达和离开互相吞掉慢脑调度。"""
        if self._is_presence_arrival_for_slow_inference(entity_id, new_state):
            return f"{entity_id}:presence_arrival"
        if self._is_presence_departure_for_slow_inference(entity_id, new_state):
            return f"{entity_id}:presence_departure"
        return entity_id

    def _is_presence_flap_suppressed(self, entity_id: str) -> tuple[bool, int]:
        """检查存在传感器是否处于抖动风暴抑制期。"""
        now_ts = time.time()
        suppressed = getattr(self, "_presence_flap_suppressed", None)
        if not isinstance(suppressed, dict):
            suppressed = {}
            self._presence_flap_suppressed = suppressed
        suppress_until = suppressed.get(entity_id, 0)
        if now_ts < suppress_until:
            return True, int(suppress_until - now_ts)
        if suppress_until:
            suppressed.pop(entity_id, None)
        return False, 0

    def _record_presence_flap(self, entity_id: str) -> None:
        """记录 on/off 反转并在高频抖动时进入抑制期。"""
        now_ts = time.time()
        history_map = getattr(self, "_presence_flap_history", None)
        if not isinstance(history_map, dict):
            history_map = {}
            self._presence_flap_history = history_map
        suppressed = getattr(self, "_presence_flap_suppressed", None)
        if not isinstance(suppressed, dict):
            suppressed = {}
            self._presence_flap_suppressed = suppressed
        history = history_map.setdefault(entity_id, [])
        history.append(now_ts)
        history_map[entity_id] = [
            t for t in history if now_ts - t <= self._PRESENCE_FLAP_WINDOW
        ]
        flap_count = len(history_map[entity_id])
        if flap_count < self._PRESENCE_FLAP_THRESHOLD:
            return

        suppress_until = now_ts + self._PRESENCE_FLAP_SUPPRESS_SECS
        suppressed[entity_id] = suppress_until
        history_map[entity_id] = []
        presence_on_start = getattr(self, "_presence_on_start", None)
        if isinstance(presence_on_start, dict):
            presence_on_start.pop(entity_id, None)
        presence_off_timers = getattr(self, "_presence_off_timers", None)
        old_off = presence_off_timers.pop(entity_id, None) if isinstance(presence_off_timers, dict) else None
        if old_off:
            try:
                old_off()
            except Exception as exc:
                _LOGGER.debug("[Listeners] 取消离开确认计时器失败 (flap): %s", exc)

        self._sys_log(
            "WARN",
            f"[存在去抖] {entity_id} 在 {self._PRESENCE_FLAP_WINDOW}s 内状态反转 {flap_count} 次，"
            f"判定抖动风暴，抑制 {self._PRESENCE_FLAP_SUPPRESS_SECS}s",
        )

    def _cancel_presence_temporal_recheck(self, entity_id: str) -> None:
        timers = getattr(self, "_presence_off_timers", None)
        if not isinstance(timers, dict):
            return
        cancel = timers.pop(entity_id, None)
        if callable(cancel):
            try:
                cancel()
            except Exception as exc:
                _LOGGER.debug("[PresenceTemporal] cancel recheck failed for %s: %s", entity_id, exc)

    @staticmethod
    def _presence_temporal_recheck_delay(presence: dict[str, Any]) -> float | None:
        if str(presence.get("temporal_status") or "") != "vacant_hold_pending":
            return None
        try:
            hold_secs = max(0.0, float(presence.get("hold_secs") or 0.0))
        except (TypeError, ValueError):
            return None
        if hold_secs <= 0:
            return None
        candidate_text = str(presence.get("candidate_since") or "").strip()
        if not candidate_text:
            return hold_secs
        if candidate_text.endswith("Z"):
            candidate_text = f"{candidate_text[:-1]}+00:00"
        try:
            candidate_since = datetime.fromisoformat(candidate_text)
        except ValueError:
            return hold_secs
        if candidate_since.tzinfo is None:
            candidate_since = candidate_since.replace(tzinfo=timezone.utc)
        elapsed = max(0.0, time.time() - candidate_since.timestamp())
        return max(1.0, hold_secs - elapsed)

    def _schedule_presence_temporal_recheck(
        self,
        entity_id: str,
        *,
        old_state: str,
        new_state: str,
        presence: dict[str, Any] | None,
    ) -> None:
        vacant_states = {"off", "closed", "not_home", "away", "idle", "clear", "empty", "vacant"}
        normalized_state = str(new_state or "").strip().lower()
        temporal = presence if isinstance(presence, dict) else {}
        delay = self._presence_temporal_recheck_delay(temporal)

        if normalized_state not in vacant_states:
            self._cancel_presence_temporal_recheck(entity_id)
            return
        if delay is None:
            if str(temporal.get("temporal_status") or "") in {
                "vacant_hold_satisfied",
                "vacant_confirmed",
            }:
                self._cancel_presence_temporal_recheck(entity_id)
            return

        self._cancel_presence_temporal_recheck(entity_id)
        timers = getattr(self, "_presence_off_timers", None)
        if not isinstance(timers, dict):
            timers = {}
            self._presence_off_timers = timers

        @callback
        def _recheck(_: datetime) -> None:
            timers.pop(entity_id, None)
            states = getattr(getattr(self, "hass", None), "states", None)
            get_state = getattr(states, "get", None)
            state_obj = get_state(entity_id) if callable(get_state) else None
            current_state = str(getattr(state_obj, "state", "") or "").strip().lower()
            if current_state not in vacant_states:
                return
            self._spawn_addon_fast_path_task(
                self._run_addon_fast_path_fail_closed(entity_id, current_state, old_state),
                entity_id=entity_id,
                old_state=old_state,
                new_state=current_state,
            )

        try:
            timers[entity_id] = async_call_later(self.hass, delay, _recheck)
        except Exception as exc:
            timers.pop(entity_id, None)
            _LOGGER.debug("[PresenceTemporal] schedule recheck failed for %s: %s", entity_id, exc)

    def _build_presence_snapshot_for_entity(
        self,
        entity_id: str,
        *,
        blocked_actions: list[str] | None = None,
        reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build a compatibility Presence Snapshot without local HA inference."""
        room = (self.device_info.get(entity_id, {}) or {}).get("room", "").strip()
        snapshot_fn = getattr(self, "get_presence_snapshot", None)
        if callable(snapshot_fn) and room:
            try:
                root_snapshot = snapshot_fn()
            except Exception as exc:
                _LOGGER.debug("[Listeners] get_presence_snapshot failed: %s", exc)
                root_snapshot = None
            rooms = root_snapshot.get("rooms") if isinstance(root_snapshot, dict) else None
            room_snapshot = rooms.get(room) if isinstance(rooms, dict) else None
            if isinstance(room_snapshot, dict):
                snap = dict(room_snapshot)
                if reasons:
                    snap["reasons"] = list(snap.get("reasons", [])) + list(reasons)
                if blocked_actions:
                    snap["blocked_actions"] = list(snap.get("blocked_actions", [])) + list(blocked_actions)
                localized_spaces = list(snap.get("localized_spaces") or [])
                if room not in localized_spaces:
                    localized_spaces.insert(0, room)
                snap["localized_spaces"] = localized_spaces
                return snap

        fallback_reasons = list(reasons or [])
        fallback_reasons.append("presence_decision_owned_by_addon")
        if not room:
            fallback_reasons.append("no_room")
        return {
            "state": "unknown",
            "confidence": 0.0,
            "reasons": fallback_reasons,
            "enter_qualified": False,
            "leave_qualified": False,
            "localized_spaces": [room] if room else [],
            "blocked_actions": list(blocked_actions or []),
        }

    def _is_presence_interaction_active(self, domain: str, state: str) -> bool:
        normalized = str(state or "").strip().lower()
        if domain == "light":
            return normalized == "on"
        if domain == "media_player":
            return normalized in {"on", "playing", "paused"}
        if domain == "climate":
            return normalized not in {"", "off", "unavailable", "unknown"}
        return False

    def _presence_interaction_source(self, entity_id: str, source_type: str) -> str:
        classifier = getattr(self, "_classify_source", None)
        if callable(classifier):
            try:
                return str(classifier(entity_id, source_type))
            except Exception as exc:
                _LOGGER.debug("[PresenceInference] classify interaction source failed: %s", exc)
        if source_type == "自动化/脚本":
            return SOURCE_AUTOMATION
        if source_type == "用户界面":
            return SOURCE_DASHBOARD
        if source_type == "语音":
            return SOURCE_VOICE
        return SOURCE_PHYSICAL

    def _record_presence_interaction_trace(
        self,
        entity_id: str,
        domain: str,
        new_state: str,
        source_type: str,
        *,
        source: str | None = None,
    ) -> bool:
        if domain not in self._PRESENCE_INTERACTION_DOMAINS:
            return False
        if not self._is_presence_interaction_active(domain, new_state):
            return False
        trace_source = str(source or self._presence_interaction_source(entity_id, source_type))
        inference = getattr(self, "_presence_inference", None)
        update_trace = getattr(inference, "update_device_trace", None)
        if not callable(update_trace):
            return False
        try:
            update_trace(entity_id, new_state, source=trace_source)
            return trace_source in self._PRESENCE_INTERACTION_HUMAN_SOURCES
        except Exception as exc:
            _LOGGER.debug("[PresenceInference] update_device_trace failed for %s: %s", entity_id, exc)
            return False

    # ── 触发调度与合并 ────────────────────────────────────────────────────────

    @callback
    def _schedule_inference(
        self,
        entity_id: str,
        trigger: str,
        new_state: str = "",
        one_off_prompt: str = "",
        *,
        _policy_synced: bool = False,
        _allow_learning_mode_inference: bool = False,
        source_trace_context: dict[str, Any] | None = None,
    ) -> None:

        # ── 门控检查（所有路径统一入口，包括 Frigate MQTT / 巡检 / HA 状态变化）──────
        # 1. AI 是否已暂停
        if not self._is_enabled():
            self._sys_log("WARN", f"触发被拒: AI 已暂停 | {entity_id}")
            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                new_state=new_state,
                filter_reason="ai_disabled",
                source_type="schedule_gate",
                trigger=trigger,
            )
            return
        # 2. 启动冷却（HA 重启后等待设备状态稳定）
        _startup_elapsed = time.time() - self._startup_time
        if _startup_elapsed < self._startup_grace:
            _remaining = int(self._startup_grace - _startup_elapsed)
            self._sys_log("INFO", f"启动冷却中({_remaining}s 后就绪)，忽略触发: {entity_id}")
            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                new_state=new_state,
                filter_reason="startup_cooldown",
                source_type="schedule_gate",
                trigger=trigger,
                cooldown_remaining=_remaining,
            )
            return
        # 3. 静默学习模式（记录与学习，抑制执行）
        if not _policy_synced:
            self._spawn_slow_inference_task(
                self._schedule_inference_after_addon_policy_sync(
                    entity_id,
                    trigger,
                    new_state,
                    one_off_prompt,
                    _allow_learning_mode_inference=_allow_learning_mode_inference,
                    source_trace_context=source_trace_context,
                ),
                trigger=trigger,
                entity_id=entity_id,
            )
            return
        if self._learning_mode and not _allow_learning_mode_inference:
            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                new_state=new_state,
                filter_reason="learning_mode",
                source_type="schedule_gate",
                trigger=trigger,
            )
            # 仅记录真实 HA 实体（entity_id 必须含"."，排除"展厅系统"等虚拟调度实体）
            _is_real_entity = "." in entity_id and not entity_id.startswith(".")
            if _is_real_entity:
                self._sys_log("INFO", f"[静默学习] {entity_id} {new_state}，记录与学习，抑制执行")
                self.hass.async_add_executor_job(
                    self._record_event, "Learning", trigger, entity_id, new_state
                )
            else:
                self._sys_log("INFO", f"[静默学习] {entity_id} {new_state}，记录与学习，抑制执行")
            return
        # ──────────────────────────────────────────────────────────────────────────

        now = time.time()
        cooldown = self._effective_cooldown()
        cooldown_key = self._slow_inference_cooldown_key(entity_id, new_state)
        elapsed = now - self._last_inference.get(cooldown_key, 0)
        if elapsed < cooldown:
            _remaining = int(cooldown - elapsed)
            self._sys_log("INFO", f"[冷却] {entity_id} 冷却中({_remaining}s 后可再触发)")
            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                new_state=new_state,
                filter_reason="cooldown",
                source_type="schedule_gate",
                trigger=trigger,
                cooldown_remaining=_remaining,
                cooldown_key=cooldown_key,
            )
            return
        self._last_inference[cooldown_key] = now
        with self._pending_triggers_lock:
            if len(self._pending_triggers) >= 50:
                _dropped = [t.get("entity_id", "?") for t in self._pending_triggers[:25]]
                self._sys_log("WARN", f"[事件溢出] 触发队列满，丢弃 25 个事件: {_dropped}")
                self._pending_triggers = self._pending_triggers[-25:]
            pending_trigger = {"text": trigger, "entity_id": entity_id, "one_off": one_off_prompt}
            if isinstance(source_trace_context, dict) and source_trace_context:
                pending_trigger["source_trace_context"] = dict(source_trace_context)
            self._pending_triggers.append(pending_trigger)

        domain = entity_id.split(".")[0]
        if domain in ("light", "switch", "fan", "cover", "climate", "media_player"):
            with self._pending_triggers_lock:
                self._pending_trigger_controllable[entity_id] = new_state
        is_urgent = domain in ("binary_sensor", "device_tracker", "person")
        window = self._URGENT_MERGE_WINDOW if is_urgent else self._NORMAL_MERGE_WINDOW

        if self._merge_timer_unsub is not None and is_urgent:
            try:
                self._merge_timer_unsub()
            except Exception as _e:
                _LOGGER.debug("[调度] 取消合并定时器异常（忽略）: %s", _e)
            self._merge_timer_unsub = None

        self._sys_log("INFO", f"[调度] 推理已加入队列，{window}s 后执行{'（紧急）' if is_urgent else ''}")
        if self._merge_timer_unsub is None:
            self._merge_timer_unsub = async_call_later(self.hass, window, self._flush_triggers)

    async def _schedule_inference_after_addon_policy_sync(
        self,
        entity_id: str,
        trigger: str,
        new_state: str = "",
        one_off_prompt: str = "",
        *,
        _allow_learning_mode_inference: bool = False,
        source_trace_context: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self._async_apply_addon_system_settings()
        except Exception as exc:
            _LOGGER.debug("[AddonSettings] pre-inference policy sync failed: %s", exc)
        self._schedule_inference(
            entity_id,
            trigger,
            new_state,
            one_off_prompt,
            _policy_synced=True,
            _allow_learning_mode_inference=_allow_learning_mode_inference,
            source_trace_context=source_trace_context,
        )

    def _emit_slow_inference_task_failure(
        self,
        *,
        trigger: str,
        entity_id: str,
        reason: str,
        scene: str,
        status: int,
        message: str = "",
    ) -> None:
        old_state = ""
        new_state = ""
        match = re.match(r"^\s*([^:]+):\s*(.*?)\s*->\s*(.*?)\s*$", str(trigger or ""))
        if match:
            entity_id = entity_id or match.group(1).strip()
            old_state = match.group(2).strip()
            new_state = match.group(3).strip()
        try:
            self.hass.bus.async_fire("smart_agent_decision_bubble", {
                "source": "ha_slow_decision",
                "entity_id": str(entity_id or ""),
                "trigger_entity_id": str(entity_id or ""),
                "old_state": old_state,
                "new_state": new_state,
                "trigger": str(trigger or ""),
                "status": status,
                "matched": False,
                "path_taken": "llm",
                "reason": reason,
                "scene": scene,
                "confidence": 0,
                "action_count": 0,
                "actions": [],
                "transaction_id": "",
                "executed": False,
                "executed_count": 0,
                "final_outcome": "failed",
                "fail_closed": True,
                "message": str(message or ""),
            })
        except Exception as exc:
            _LOGGER.debug("[SlowInference] failure bubble emit failed: %s", exc)
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if callable(enqueue):
            result_payload = {
                "source": "ha_slow_decision",
                "path_taken": "llm",
                "reason": reason,
                "scene": scene,
                "trigger": str(trigger or ""),
                "actions": [],
                "matched": False,
                "final_outcome": "failed",
                "fail_closed": True,
                "message": str(message or ""),
            }
            log_payload = {
                "trigger": str(trigger or ""),
                "scene": scene,
                "source": "ha_slow_decision",
                "path_taken": "llm",
                "confidence": 0,
                "matched": False,
                "action_count": 0,
                "reason": reason,
                "actions": [],
                "result": result_payload,
            }
            try:
                if not enqueue("decision_log", log_payload):
                    self._sys_log("WARN", f"[SlowInference] decision_log enqueue failed reason={reason}")
            except Exception as exc:
                _LOGGER.debug("[SlowInference] decision_log enqueue failed: %s", exc)

    def _handle_slow_inference_task_done(self, task: Any, *, trigger: str, entity_id: str) -> None:
        cancelled = False
        try:
            cancelled = bool(task.cancelled()) if hasattr(task, "cancelled") else False
        except Exception:
            cancelled = False
        if cancelled:
            self._sys_log("WARN", f"[决策] 线上大模型任务被取消: {entity_id}")
            self._emit_slow_inference_task_failure(
                trigger=trigger,
                entity_id=entity_id,
                reason="slow_inference_task_cancelled",
                scene="线上大模型任务已取消",
                status=499,
            )
            return
        try:
            exc = task.exception() if hasattr(task, "exception") else None
        except asyncio.CancelledError:
            self._sys_log("WARN", f"[决策] 线上大模型任务被取消: {entity_id}")
            self._emit_slow_inference_task_failure(
                trigger=trigger,
                entity_id=entity_id,
                reason="slow_inference_task_cancelled",
                scene="线上大模型任务已取消",
                status=499,
            )
            return
        except Exception as err:
            exc = err
        if exc is None:
            return
        self._sys_log("ERROR", f"[决策] 线上大模型任务异常: {entity_id} | {exc}")
        self._emit_slow_inference_task_failure(
            trigger=trigger,
            entity_id=entity_id,
            reason="slow_inference_task_failed",
            scene="线上大模型任务失败",
            status=500,
            message=str(exc),
        )

    def _spawn_slow_inference_task(self, coro: Any, *, trigger: str, entity_id: str) -> None:
        try:
            task = self.hass.async_create_task(coro)
        except Exception as exc:
            close = getattr(coro, "close", None)
            if callable(close):
                close()
            self._sys_log("ERROR", f"[决策] 创建线上大模型任务失败: {entity_id} | {exc}")
            self._emit_slow_inference_task_failure(
                trigger=trigger,
                entity_id=entity_id,
                reason="slow_inference_task_create_failed",
                scene="线上大模型任务创建失败",
                status=500,
                message=str(exc),
            )
            return
        add_done_callback = getattr(task, "add_done_callback", None)
        if callable(add_done_callback):
            add_done_callback(
                lambda finished: self._handle_slow_inference_task_done(
                    finished,
                    trigger=trigger,
                    entity_id=entity_id,
                )
            )

    @callback
    def _flush_triggers(self, _: datetime) -> None:
        self._merge_timer_unsub = None
        with self._pending_triggers_lock:
            if not self._pending_triggers:
                return

        # 每次 flush 时顺手清理 _user_manual_actions 过期键（超过 _USER_MANUAL_WINDOW）
        # 防止字典无限增长（随历史手动操作实体数线性增大）
        with self._user_manual_actions_lock:
            if self._user_manual_actions:
                _now_ts = time.time()
                _expired = [
                    eid for eid, v in self._user_manual_actions.items()
                    if (_now_ts - v.get("time", 0)) > self._USER_MANUAL_WINDOW
                ]
                for eid in _expired:
                    del self._user_manual_actions[eid]

        with self._pending_triggers_lock:
            triggers = self._pending_triggers.copy()
            self._pending_triggers.clear()
            controllable_snapshot = self._pending_trigger_controllable.copy()
            self._pending_trigger_controllable.clear()

        # 状态校验：合并窗口内检查可控设备当前状态是否与上报一致
        # 同时维护闪断累计计数，频繁闪断的设备进入抑制期，暂停触发推理
        # （_glitch_history / _glitch_suppressed 已在 coordinator.__init__ 中初始化）

        _now_glitch = time.time()
        glitched: list[str] = []
        for eid, reported in controllable_snapshot.items():
            if not reported:
                continue
            # 检查该设备是否处于闪断抑制期，若是则直接视为闪断跳过
            suppress_until = self._glitch_suppressed.get(eid, 0)
            if _now_glitch < suppress_until:
                glitched.append(eid)
                remain = int(suppress_until - _now_glitch)
                self._sys_log("INFO", f"[状态校验] {eid} 处于闪断抑制期，跳过触发（剩余{remain}s）")
                continue
            current = self.hass.states.get(eid)
            if current and current.state != reported:
                glitched.append(eid)
                name = self.get_device_name(eid)
                self._sys_log("WARN", f"[状态校验] {name}({eid}) 上报 {reported} 但刷新后为 {current.state}，判定为通信闪断，移除该触发")
                with self._user_overrides_lock:
                    self._user_overrides.pop(eid, None)
                # 累计闪断记录，清理超出时间窗口的旧记录
                history = self._glitch_history.setdefault(eid, [])
                history.append(_now_glitch)
                self._glitch_history[eid] = [t for t in history if _now_glitch - t < self._GLITCH_WINDOW]
                # 若在时间窗口内闪断次数达到阈值，进入抑制期
                if len(self._glitch_history[eid]) >= self._GLITCH_THRESHOLD:
                    self._glitch_suppressed[eid] = _now_glitch + self._GLITCH_SUPPRESS_SECS
                    self._sys_log("WARN",
                        f"[状态校验] {name}({eid}) {self._GLITCH_WINDOW}s内闪断{len(self._glitch_history[eid])}次，"
                        f"进入{self._GLITCH_SUPPRESS_SECS}s抑制期，暂停触发推理"
                    )
                    self._glitch_history[eid] = []  # 重置计数，等待抑制期结束

        if glitched:
            triggers = [t for t in triggers if t["entity_id"] not in glitched]
            for eid in glitched:
                controllable_snapshot.pop(eid, None)

        if not triggers:
            self._sys_log("INFO", "[状态校验] 所有触发均为通信闪断，取消本次推理")
            return

        self._batch_trigger_controllable = controllable_snapshot
        if self._batch_trigger_controllable:
            self._sys_log("INFO", f"[自触发保护] 本批次含可控设备触发: {', '.join(self._batch_trigger_controllable)}，AI 不可反向操作这些设备")
        
        contextual_triggers = [
            item
            for item in triggers
            if isinstance(item.get("source_trace_context"), dict)
            and item.get("source_trace_context")
        ]
        mergeable_triggers = [item for item in triggers if item not in contextual_triggers]
        inference_batches: list[dict[str, Any]] = []

        merged_batch: dict[str, Any] | None = None
        if mergeable_triggers:
            mergeable_texts = [item["text"] for item in mergeable_triggers]
            merged_trigger = (
                mergeable_texts[0]
                if len(mergeable_texts) == 1
                else self._compact_merged_trigger(mergeable_texts)
            )
            one_off_prompts = [
                item.get("one_off")
                for item in mergeable_triggers
                if item.get("one_off")
            ]
            merged_batch = {
                "trigger": merged_trigger,
                "entity_id": str(mergeable_triggers[0].get("entity_id") or ""),
                "one_off_prompt": one_off_prompts[0] if one_off_prompts else "",
                "source_trace_context": None,
                "trigger_count": len(mergeable_triggers),
                "public_summary": self._trigger_public_summary(mergeable_texts),
            }

        merged_batch_added = False
        for item in triggers:
            context = item.get("source_trace_context")
            if isinstance(context, dict) and context:
                inference_batches.append(
                    {
                        "trigger": item["text"],
                        "entity_id": str(item.get("entity_id") or ""),
                        "one_off_prompt": str(item.get("one_off") or ""),
                        "source_trace_context": dict(context),
                        "trigger_count": 1,
                        "public_summary": self._trigger_public_summary([item["text"]]),
                    }
                )
            elif merged_batch is not None and not merged_batch_added:
                inference_batches.append(merged_batch)
                merged_batch_added = True

        for batch in inference_batches:
            self._sys_log(
                "INFO",
                f"[合并] 合并 {batch['trigger_count']} 个触发，启动推理: {batch['public_summary']}",
            )
            try:
                trigger_text = str(batch["trigger"])
                self._spawn_slow_inference_task(
                    self._run_addon_decision(
                        trigger_text,
                        one_off_prompt=str(batch["one_off_prompt"]),
                        source_trace_context=batch["source_trace_context"],
                    ),
                    trigger=trigger_text,
                    entity_id=str(batch["entity_id"]),
                )
            except Exception as exc:
                self._sys_log("ERROR", f"[合并] 创建推理任务失败: {exc}")

    # ── 触发文本格式化 ────────────────────────────────────────────────────────

    _DOMAIN_ZH_MAP = {
        "light": "灯光", "switch": "开关", "climate": "空调",
        "cover": "窗帘", "fan": "风扇", "sensor": "数值传感器",
        "binary_sensor": "传感器", "media_player": "播放器",
        "device_tracker": "位置", "person": "人员",
    }

    # 仅存在感/二进制传感器使用"有人/无人"语义翻译
    _PRESENCE_STATE_ZH = {"on": "有人", "off": "无人"}
    # 可控设备（灯/开关/窗帘等）使用"开/关"
    _CTRL_STATE_ZH = {
        "on": "开", "off": "关",
        "open": "已开", "closed": "已关",
        "heat": "制热", "cool": "制冷", "dry": "除湿",
        "fan_only": "送风", "auto": "自动",
        "home": "回家", "not_home": "离家",
        "unavailable": "离线", "unknown": "未知",
    }
    # 存在感传感器关键词（与 _PRESENCE_KW 保持一致）
    _PRESENCE_DOMAINS = frozenset({"binary_sensor"})

    def _fmt_state(self, domain: str, entity_id: str, state: str) -> str:
        """根据设备类型返回语义准确的状态文字。"""
        if domain in self._PRESENCE_DOMAINS:
            eid_lower = entity_id.lower()
            is_presence = any(kw in eid_lower or kw in (
                self.device_info.get(entity_id, {}).get("name", "").lower()
            ) for kw in self._PRESENCE_KW)
            if is_presence:
                return self._PRESENCE_STATE_ZH.get(state, state)
        return self._CTRL_STATE_ZH.get(state, state)

    def _fmt_trigger(self, source: str, domain: str, name: str,
                     entity_id: str, old_s: str, new_s: str) -> str:
        """生成简洁的触发文本，供 AI Prompt 和日志使用。
        
        保留 entity_id 让 AI 可精确识别设备，状态按设备类型语义化翻译。
        """
        dz = self._DOMAIN_ZH_MAP.get(domain, domain)
        oz = self._fmt_state(domain, entity_id, old_s)
        nz = self._fmt_state(domain, entity_id, new_s)
        src_short = {"物理/自动": "物理", "自动化/脚本": "脚本", "用户界面": "用户"}.get(source, source)
        return f"[{src_short}] {dz}「{name}」{oz}→{nz}（{entity_id}）"

    def _trigger_public_summary(
        self,
        trigger: Any,
        *,
        entity_id: str = "",
        old_state: str = "",
        new_state: str = "",
    ) -> str:
        """Return a log-safe trigger summary without friendly names or raw text."""
        if isinstance(trigger, (list, tuple, set)):
            texts = [str(item or "").strip() for item in trigger if str(item or "").strip()]
        else:
            text = str(trigger or "").strip()
            texts = [text] if text else []

        def _summary_from_text(text: str) -> str:
            patterns = (
                re.compile(r"\[(?P<src>[^\]]+)\].*?」(?P<old>[^→（）\s]+)→(?P<new>[^（）\s]+)（(?P<eid>[^）]+)）"),
                re.compile(r"\[(?P<src>[^\]]+)\].*?\((?P<eid>[^)]+)\)\]\s+changed:\s+(?P<old>\S+)\s+->\s+(?P<new>\S+)"),
                re.compile(r"(?P<eid>[A-Za-z0-9_]+\.[A-Za-z0-9_.:-]+)\s*[:：]?\s*(?P<old>[^\s→-]+)\s*(?:→|->)\s*(?P<new>\S+)"),
            )
            for pattern in patterns:
                match = pattern.search(text)
                if not match:
                    continue
                src = str(match.groupdict().get("src") or "").strip()
                eid = str(match.group("eid") or "").strip()
                old_s = str(match.group("old") or "?").strip()
                new_s = str(match.group("new") or "?").strip()
                if eid:
                    prefix = f"[{src}] " if src else ""
                    return f"{prefix}{eid}:{old_s}->{new_s}"
            return ""

        summaries: list[str] = []
        seen: set[str] = set()
        for text in texts:
            summary = _summary_from_text(text)
            if summary and summary not in seen:
                summaries.append(summary)
                seen.add(summary)

        fallback_entity = str(entity_id or "").strip()
        if fallback_entity:
            old_s = str(old_state or "?").strip() or "?"
            new_s = str(new_state or "?").strip() or "?"
            fallback = f"{fallback_entity}:{old_s}->{new_s}"
            if fallback not in seen:
                summaries.append(fallback)

        if summaries:
            visible = summaries[:6]
            suffix = f"; +{len(summaries) - len(visible)} more" if len(summaries) > len(visible) else ""
            return ("; ".join(visible) + suffix)[:240]

        combined = "\n".join(texts)
        if not combined:
            return "-"
        digest = hashlib.sha256(combined.encode("utf-8", "ignore")).hexdigest()[:12]
        return f"trigger_hash={digest} len={len(combined)}"

    # ── 触发合并压缩 ──────────────────────────────────────────────────────────

    def _compact_merged_trigger(self, texts: list[str]) -> str:
        """将多条触发消息压缩为简洁的合并描述，节省字符，同时保留 AI 决策所需信息。

        优化策略：
        1. 相同变化方向（off→on / on→off）且同域的设备归为一组，仅列设备名
        2. 不同类型/方向的设备各自独立一行
        3. 整体长度控制在 200 字以内
        """
        import re as _re
        # 兼容新格式: [来源] 域「名称」旧→新（entity_id）
        # 兼容旧格式: [来源] domain [名称(entity_id)] changed: old -> new
        _pat_new = _re.compile(r"\[(.+?)\]\s+\S+「(.+?)」(\S+)→(\S+)（(\S+?)）")
        _pat_old = _re.compile(r"\[(.+?)\]\s+\S+\s+\[(.+?)\((.+?)\)\]\s+changed:\s+(\S+)\s+->\s+(\S+)")
        parsed = []
        unparsed = []
        for t in texts:
            m = _pat_new.search(t)
            if m:
                src, name, old_s, new_s, eid = m.groups()
                domain = eid.split(".")[0]
                parsed.append({"src": src, "name": name, "eid": eid,
                                "domain": domain, "old": old_s, "new": new_s})
                continue
            m = _pat_old.search(t)
            if m:
                src, name, eid, old_s, new_s = m.groups()
                domain = eid.split(".")[0]
                parsed.append({"src": src, "name": name, "eid": eid,
                                "domain": domain, "old": old_s, "new": new_s})
            else:
                unparsed.append(t)

        # 按 (src, domain, old→new) 分组，值存 (name, eid) 以便状态翻译时参考 eid
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for p in parsed:
            key = (p["src"], p["domain"], p["old"], p["new"])
            groups[key].append((p["name"], p["eid"]))

        lines = []
        for (src, domain, old_s, new_s), items in groups.items():
            # items 现在是 (name, eid) 的列表
            dz = self._DOMAIN_ZH_MAP.get(domain, domain)
            # 用第一个 eid 判断状态翻译策略（同组设备类型相同）
            rep_eid = items[0][1] if items and isinstance(items[0], tuple) else ""
            oz = self._fmt_state(domain, rep_eid, old_s)
            nz = self._fmt_state(domain, rep_eid, new_s)
            names = [it[0] if isinstance(it, tuple) else it for it in items]
            if len(names) == 1:
                lines.append(f"[{src}] {dz}「{names[0]}」{oz}→{nz}")
            else:
                # 多个设备同向变化：使用第一个设备名称带「」标记以保留房间信息，
                # 确保 inference.py 中 r"「\[(.*?)\]" 能正确提取 trigger_room，
                # 避免区域隔离和 per-room lock 因 trigger_room 为空而失效。
                first_name = names[0]
                rest_names = "、".join(names[1:3])
                suffix = f"等{len(names)}台" if len(names) > 2 else (f"、{rest_names}" if rest_names else "")
                lines.append(f"[{src}] {dz}「{first_name}」{suffix} {oz}→{nz}")

        lines.extend(unparsed)
        result = "同时发生：\n" + "\n".join(f"  · {l}" for l in lines)
        # 超 220 字则截取并提示
        if len(result) > 220:
            result = result[:218] + "…"
        return result

    # ── 快速通道 ──────────────────────────────────────────────────────────────

    def _get_time_brightness(self, hour: int) -> int:
        """Return appropriate brightness for the given hour, checking user rules first."""
        for content, locked in self._rules:
            m = self._TIME_RE.search(content)
            if not m:
                continue
            h1 = int(m.group(1))
            op = m.group(2) or ""
            h2 = int(m.group(3)) if m.group(3) else None
            applicable = False
            if op in ("以后", "之后", "后"):
                applicable = hour >= h1
            elif op in ("以前", "之前", "前"):
                applicable = hour < h1
            elif op in ("到", "至", "-") and h2 is not None:
                applicable = (h1 <= hour <= h2) if h1 <= h2 else (hour >= h1 or hour <= h2)
            if not applicable:
                continue
            bm = re.search(r'亮度[为到]?\s*(\d{1,3})\s*%?', content)
            if bm:
                return int(bm.group(1))
        for start, end, brightness in self._BRIGHTNESS_TABLE:
            if start <= hour < end:
                return brightness
        return 80

    def _find_room_lights(self, sensor_eid: str) -> list[str]:
        """Find light entities in the same room as the given sensor."""
        sensor_info = self.device_info.get(sensor_eid, {})
        sensor_room = sensor_info.get("room", "")
        if not sensor_room:
            sensor_room = self._get_entity_area(sensor_eid)
        lights = []
        for eid, info in self.device_info.items():
            if not eid.startswith("light."):
                continue
            dev_room = info.get("room", "")
            if not dev_room:
                dev_room = self._get_entity_area(eid)
            if sensor_room and dev_room and sensor_room == dev_room:
                lights.append(eid)
        return lights

    def _ha_local_now(self) -> datetime:
        config = getattr(getattr(self, "hass", None), "config", None)
        configured_timezone = str(getattr(config, "time_zone", "") or "").strip()
        if configured_timezone:
            try:
                return datetime.now(_fast_path_timezone(configured_timezone))
            except ZoneInfoNotFoundError:
                _LOGGER.debug("[Listeners] invalid HA timezone for local clock: %s", configured_timezone)
            except Exception as exc:
                _LOGGER.debug("[Listeners] HA timezone read failed for local clock: %s", exc)
        try:
            from homeassistant.util import dt as dt_util

            return dt_util.now()
        except Exception:
            return datetime.now(timezone.utc)

    def _listener_db_now_text(self) -> str:
        return self._ha_local_now().strftime("%Y-%m-%d %H:%M:%S")

    def _build_fast_path_environment_context(
        self,
        device_info: dict[str, Any],
        trigger_entity_id: str = "",
    ) -> dict[str, Any]:
        states = getattr(getattr(self, "hass", None), "states", None)
        get_state = getattr(states, "get", None)
        if not callable(get_state):
            return {}
        context: dict[str, Any] = {}
        local_hour_source = "ha_local_clock"
        local_timezone = ""
        config = getattr(getattr(self, "hass", None), "config", None)
        configured_timezone = str(getattr(config, "time_zone", "") or "").strip()
        if configured_timezone:
            try:
                local_now = datetime.now(_fast_path_timezone(configured_timezone))
                local_hour_source = "ha_config_timezone"
                local_timezone = configured_timezone
            except ZoneInfoNotFoundError:
                _LOGGER.debug("[Listeners] invalid HA timezone for fast-path snapshot: %s", configured_timezone)
                local_now = self._ha_local_now()
            except Exception as exc:
                _LOGGER.debug("[Listeners] HA timezone read failed for fast-path snapshot: %s", exc)
                local_now = self._ha_local_now()
        else:
            local_now = self._ha_local_now()
        context["local_hour"] = local_now.hour
        context["local_weekday"] = (local_now.weekday() + 1) % 7
        context["local_hour_source"] = local_hour_source
        if local_timezone:
            context["local_timezone"] = local_timezone
        try:
            sun = get_state("sun.sun")
        except Exception as exc:
            _LOGGER.debug("[Listeners] sun.sun read failed for fast-path snapshot: %s", exc)
            sun = None
        if sun is not None:
            sun_state = str(getattr(sun, "state", "") or "").strip().lower()
            if sun_state:
                context["sun_state"] = sun_state
                context["is_daylight"] = sun_state == "above_horizon"
                context["is_dark"] = sun_state == "below_horizon"
            attrs = getattr(sun, "attributes", None)
            if isinstance(attrs, dict):
                for key in ("elevation", "next_rising", "next_setting"):
                    value = attrs.get(key)
                    if value not in (None, ""):
                        context[f"sun_{key}"] = value

        def _entity_room(entity_id: str, info: dict[str, Any]) -> str:
            for key in ("space_id", "room", "area"):
                value = str((info or {}).get(key) or "").strip()
                if value:
                    return value
            area_getter = getattr(self, "_get_entity_area", None)
            if callable(area_getter):
                try:
                    return str(area_getter(entity_id) or "").strip()
                except Exception as exc:
                    _LOGGER.debug("[Listeners] area lookup failed for daylight context %s: %s", entity_id, exc)
            return ""

        trigger_info = device_info.get(trigger_entity_id, {}) if trigger_entity_id else {}
        if not isinstance(trigger_info, dict):
            trigger_info = {}
        trigger_room = _entity_room(trigger_entity_id, trigger_info) if trigger_entity_id else ""
        trigger_room_lux_values: list[tuple[float, str]] = []
        environment_device_info = getattr(self, "_environment_context_device_info", {}) or {}
        evidence_device_info = dict(device_info)
        if isinstance(environment_device_info, dict):
            evidence_device_info.update(environment_device_info)
        for eid, raw_info in evidence_device_info.items():
            entity_id = str(eid or "")
            if not entity_id.startswith("sensor."):
                continue
            info = raw_info if isinstance(raw_info, dict) else {}
            if environment_sensor_kind(entity_id, info) != "illuminance":
                continue
            if not trigger_room or _entity_room(entity_id, info) != trigger_room:
                continue
            try:
                state_obj = get_state(entity_id)
                lux = float(str(getattr(state_obj, "state", "") or "").strip())
                if isfinite(lux):
                    trigger_room_lux_values.append((lux, entity_id))
            except (TypeError, ValueError):
                continue
            except Exception as exc:
                _LOGGER.debug("[Listeners] illuminance read failed for %s: %s", entity_id, exc)
        if trigger_room_lux_values:
            min_lux = min(lux for lux, _entity_id in trigger_room_lux_values)
            min_lux_entities = [
                entity_id
                for lux, entity_id in trigger_room_lux_values
                if lux == min_lux
            ]
            context["illuminance_lux_min"] = min_lux
            context["illuminance_lux"] = min_lux
            context["illuminance_scope"] = "trigger_room"
            if min_lux_entities:
                context["illuminance_entity_id"] = min_lux_entities[0]
                context["illuminance_evidence_ids"] = min_lux_entities
                context["illuminance_source"] = "ha_state"
            if min_lux <= self._DAYLIGHT_GUARD_LUX_THRESHOLD:
                context["is_dark"] = True
                context["is_daylight"] = False
        return context

    def _is_ai_self_presence_interaction_evidence(self, item: dict[str, Any], now_ts: float) -> bool:
        entity_id = str(item.get("entity_id") or "").strip()
        if not entity_id:
            return False
        last_ai_actions = getattr(self, "_last_ai_actions", {})
        last_ai = last_ai_actions.get(entity_id) if isinstance(last_ai_actions, dict) else None
        if not isinstance(last_ai, dict):
            return False
        if str(last_ai.get("state") or "").strip().lower() != str(item.get("state") or "").strip().lower():
            return False
        try:
            age = now_ts - float(last_ai.get("time") or 0)
        except (TypeError, ValueError):
            return False
        return 0 <= age <= self._PRESENCE_INTERACTION_AI_SELF_WINDOW

    def _filtered_presence_interaction_evidence(self, evidence: list[Any], now_ts: float) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            if self._is_ai_self_presence_interaction_evidence(row, now_ts):
                continue
            rows.append(row)
        return rows

    # ── 状态变化处理器 ────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_correction_suppressions(rows: Any) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        suppressions: list[dict[str, Any]] = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            entity_id = str(raw.get("entity_id") or raw.get("target") or "").strip()
            service = str(raw.get("service") or raw.get("ai_service") or "").strip().lower()
            if "." in service:
                service = service.rsplit(".", 1)[-1]
            room = str(raw.get("room") or raw.get("space") or "").strip()
            presence = str(raw.get("presence") or raw.get("presence_context") or "any").strip().lower() or "any"
            if not entity_id or not service:
                continue
            try:
                count = int(raw.get("count") or raw.get("correction_count") or 1)
            except (TypeError, ValueError):
                count = 1
            try:
                score = float(raw.get("score") or raw.get("decay_score") or raw.get("confidence") or 1.0)
            except (TypeError, ValueError):
                score = 1.0
            suppressions.append(
                {
                    "entity_id": entity_id,
                    "service": service,
                    "room": room,
                    "presence": presence,
                    "suppress": bool(raw.get("suppress", True)),
                    "count": max(1, count),
                    "score": max(0.0, min(1.0, score)),
                }
            )
            if len(suppressions) >= 50:
                break
        return suppressions

    def _snapshot_correction_suppressions(self) -> list[dict[str, Any]]:
        for attr in ("_correction_suppressions_cache", "_corrections_cache"):
            cached = getattr(self, attr, None)
            suppressions = self._normalize_correction_suppressions(cached)
            if suppressions:
                return suppressions
        return []

    async def _refresh_correction_suppressions_cache(self, addon_client: Any) -> None:
        now_ts = time.time()
        next_refresh = getattr(self, "_correction_suppressions_cache_refresh_at", 0.0)
        try:
            if now_ts < float(next_refresh or 0.0) and isinstance(
                getattr(self, "_correction_suppressions_cache", None),
                list,
            ):
                return
        except (TypeError, ValueError):
            pass
        self._correction_suppressions_cache_refresh_at = now_ts + self._CORRECTION_SUPPRESSIONS_CACHE_TTL
        getter = getattr(addon_client, "get_corrections", None)
        if not callable(getter):
            return
        try:
            rows = await getter()
        except Exception as exc:
            _LOGGER.debug("[Listeners] refresh correction suppressions failed: %s", exc)
            return
        if not isinstance(rows, list):
            return
        self._correction_suppressions_cache = self._normalize_correction_suppressions(rows)

    def _build_addon_fast_path_snapshot(self, entity_id: str) -> dict[str, Any]:
        """Build the plain snapshot consumed by add-on Core fast-path decisions."""
        raw_device_info = getattr(self, "device_info", {}) or {}
        device_info = {
            str(entity_id): dict(info) if isinstance(info, dict) else {}
            for entity_id, info in raw_device_info.items()
        } if isinstance(raw_device_info, dict) else {}
        now_ts = time.time()
        observed_at = datetime.fromtimestamp(now_ts, timezone.utc).isoformat()
        states: dict[str, str] = {}
        state_observations: dict[str, dict[str, str]] = {}
        for eid in device_info.keys():
            if not eid:
                continue
            state = self.hass.states.get(eid)
            if state is not None:
                state_value = str(state.state or "")
                states[eid] = state_value
                observation = {"state": state_value}
                for timestamp_key in ("last_changed", "last_updated"):
                    timestamp = getattr(state, timestamp_key, None)
                    if timestamp in (None, ""):
                        continue
                    isoformat = getattr(timestamp, "isoformat", None)
                    observation[timestamp_key] = (
                        str(isoformat()) if callable(isoformat) else str(timestamp)
                    )
                state_observations[eid] = observation
                attributes = getattr(state, "attributes", None)
                if isinstance(attributes, dict):
                    device_class = str(attributes.get("device_class") or "").strip().lower()
                    if device_class and not device_info[eid].get("device_class"):
                        device_info[eid]["device_class"] = device_class

        topology: dict[str, list[str]] = {}
        for room, neighbors in (getattr(self, "_room_topology_cache", {}) or {}).items():
            if isinstance(neighbors, (set, list, tuple)):
                topology[str(room)] = sorted({str(item) for item in neighbors if str(item or "").strip()})

        snapshot: dict[str, Any] = {
            "device_info": device_info,
            "states": states,
            "state_observations": state_observations,
            "ai_scenes": list(getattr(self, "_ai_scenes_cache", []) or []),
            "room_topology": topology,
            "mode": str(getattr(self, "_mode", "") or ""),
            "presence_contract_source": "addon_presence_engine",
            "observed_at": observed_at,
            "created_at": observed_at,
        }
        environment_context = self._build_fast_path_environment_context(device_info, entity_id)
        if environment_context:
            snapshot["environment_context"] = environment_context
        correction_suppressions = self._snapshot_correction_suppressions()
        if correction_suppressions:
            snapshot["correction_suppressions"] = correction_suppressions

        occ_getter = getattr(self, "_get_room_occupancy_map", None)
        if callable(occ_getter):
            try:
                occ_map = occ_getter()
            except Exception as exc:
                _LOGGER.debug("[Listeners] _get_room_occupancy_map failed for add-on snapshot: %s", exc)
                occ_map = None
            if isinstance(occ_map, dict):
                snapshot["occ_map"] = occ_map
                snapshot["occ_map_contract"] = {
                    "compatibility_field": "occ_map",
                    "semantic_role": "legacy_evidence_only",
                    "canonical_source": "addon_presence_engine",
                    "fallback_consumer": "none",
                }

        rules_getter = getattr(self, "_build_locked_people_rules", None)
        if callable(rules_getter):
            try:
                locked_people_rules = rules_getter()
            except Exception as exc:
                _LOGGER.debug("[Listeners] _build_locked_people_rules failed for add-on snapshot: %s", exc)
                locked_people_rules = None
            if isinstance(locked_people_rules, list):
                snapshot["locked_people_rules"] = locked_people_rules

        manual_getter = getattr(self, "_get_recent_manual_actions_snapshot", None)
        manual_actions: Any = None
        if callable(manual_getter):
            try:
                manual_actions = manual_getter()
            except Exception as exc:
                _LOGGER.debug("[Listeners] _get_recent_manual_actions_snapshot failed for add-on snapshot: %s", exc)
                manual_actions = None
        elif isinstance(getattr(self, "_user_manual_actions", None), dict):
            lock = getattr(self, "_user_manual_actions_lock", None)
            if lock is not None:
                try:
                    with lock:
                        manual_actions = dict(getattr(self, "_user_manual_actions", {}) or {})
                except Exception as exc:
                    _LOGGER.debug("[Listeners] _user_manual_actions snapshot failed: %s", exc)
                    manual_actions = None
            else:
                manual_actions = dict(getattr(self, "_user_manual_actions", {}) or {})
        if isinstance(manual_actions, dict):
            snapshot["user_manual_actions"] = manual_actions
        trace_getter = getattr(getattr(self, "_presence_inference", None), "get_recent_device_trace_evidence", None)
        if callable(trace_getter):
            try:
                interaction_evidence = trace_getter()
            except Exception as exc:
                _LOGGER.debug("[Listeners] get_recent_device_trace_evidence failed for add-on snapshot: %s", exc)
                interaction_evidence = None
            if isinstance(interaction_evidence, list) and interaction_evidence:
                filtered_evidence = self._filtered_presence_interaction_evidence(interaction_evidence, now_ts)
                if filtered_evidence:
                    snapshot["presence_interaction_evidence"] = filtered_evidence
        priority_getter = getattr(self, "_get_priority_summary", None)
        if callable(priority_getter):
            try:
                priority_guards = priority_getter()
            except Exception as exc:
                _LOGGER.debug("[Listeners] _get_priority_summary failed for add-on snapshot: %s", exc)
                priority_guards = None
            if isinstance(priority_guards, list):
                snapshot["manual_action_summary"] = {
                    "priority_guards": [dict(item) for item in priority_guards if isinstance(item, dict)]
                }
        snapshot["now_ts"] = now_ts

        for key, getter_name in (
            ("space_snapshot", "get_space_runtime_snapshot"),
            ("device_capability_snapshot", "get_device_capability_snapshot"),
        ):
            getter = getattr(self, getter_name, None)
            if callable(getter):
                try:
                    value = getter()
                except Exception as exc:
                    _LOGGER.debug("[Listeners] %s failed for add-on snapshot: %s", getter_name, exc)
                    value = None
                if isinstance(value, dict):
                    snapshot[key] = value
        return snapshot

    @staticmethod
    def _new_addon_fast_path_request_id(
        entity_id: str,
        old_state: str,
        new_state: str,
    ) -> str:
        seed = "|".join(
            (
                str(entity_id or "").strip(),
                str(old_state or "").strip(),
                str(new_state or "").strip(),
                str(time.time_ns()),
            )
        )
        return f"ha-fast-path-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:20]}"

    async def _execute_fast_path_decision_result(
        self,
        result: dict[str, Any],
        *,
        entity_id: str,
        source_label: str,
        transaction_id: str = "",
        correlation_id: str = "",
        world_snapshot_id: str = "",
        decision_trace: dict[str, Any] | None = None,
        trigger: str = "",
        active_ai_rollout: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        actions = result.get("actions", [])
        scene = result.get("scene", source_label)
        confidence = result.get("confidence", 90)
        device_info = getattr(self, "device_info", {})
        if not isinstance(device_info, dict):
            device_info = {}
        room = result.get("trigger_room") or device_info.get(entity_id, {}).get("room", "")
        try:
            defer_seconds = int(result.get("defer_seconds", 0) or 0)
        except (TypeError, ValueError):
            defer_seconds = 0

        if defer_seconds > 0:
            await asyncio.sleep(defer_seconds)

        valid_actions = actions if isinstance(actions, list) else []
        rollout_actions = enrich_active_ai_action_spaces(valid_actions, device_info)
        trigger_info = device_info.get(entity_id, {})
        if not isinstance(trigger_info, dict):
            trigger_info = {}
        trigger_space_id = str(
            result.get("trigger_space_id")
            or trigger_info.get("space_id")
            or trigger_info.get("room_id")
            or trigger_info.get("area_id")
            or room
            or ""
        ).strip()
        rollout_payload = (
            active_ai_rollout if isinstance(active_ai_rollout, dict) else {}
        )
        execution_flags = (
            rollout_payload.get("execution_flags")
            if isinstance(rollout_payload.get("execution_flags"), dict)
            else {}
        )
        is_enabled = getattr(self, "_is_enabled", None)
        rollout_decision = evaluate_active_ai_execution_gate(
            ai_enabled=bool(is_enabled()) if callable(is_enabled) else False,
            config=ActiveAiRolloutConfig.from_mapping(rollout_payload),
            trigger_space_id=trigger_space_id,
            actions=rollout_actions,
            execution_flags=execution_flags,
        )
        trigger_summary = f"{source_label}[{scene}]"
        if trigger:
            trigger_summary = f"{trigger_summary} {trigger}"
        if not rollout_decision.allow_execution:
            self._sys_log(
                "INFO",
                f"[Add-on FastPath] rollout gate blocked execution "
                f"mode={rollout_decision.mode} reason={rollout_decision.reason} "
                f"transaction_id={transaction_id or '-'}",
            )
            return self._enqueue_fast_path_execution_audit(
                transaction_id=transaction_id,
                correlation_id=correlation_id,
                world_snapshot_id=world_snapshot_id,
                decision_trace=decision_trace,
                trigger=trigger or f"{entity_id}: state_changed",
                scene=str(scene),
                confidence=confidence,
                actions=valid_actions,
                execution_result=0,
                execution_suppressed_reason=rollout_decision.reason,
                rollout=rollout_decision.as_trace(),
            )
        execution_result = await self._execute_actions(
            valid_actions,
            trigger_summary=trigger_summary,
            scene_desc=str(scene),
            confidence=confidence,
            trigger_room=room,
            is_global_cmd=False,
            cmd_source=_CMD_SOURCE_SENSOR,
            parent_transaction_id=transaction_id,
            world_snapshot_id=world_snapshot_id,
            correlation_id=correlation_id,
            active_space_id=trigger_space_id,
            decision_time=datetime.now(timezone.utc).isoformat(),
            require_world_snapshot_guard=True,
        )
        return self._enqueue_fast_path_execution_audit(
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            world_snapshot_id=world_snapshot_id,
            decision_trace=decision_trace,
            trigger=trigger or f"{entity_id}: state_changed",
            scene=str(scene),
            confidence=confidence,
            actions=valid_actions,
            execution_result=execution_result,
        )

    def _enqueue_fast_path_execution_audit(
        self,
        *,
        transaction_id: str,
        correlation_id: str = "",
        world_snapshot_id: str = "",
        decision_trace: dict[str, Any] | None = None,
        trigger: str,
        scene: str,
        confidence: Any,
        actions: list[Any],
        execution_result: Any,
        execution_suppressed_reason: str = "",
        rollout: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        transaction_id = str(transaction_id or "").strip()
        if not transaction_id:
            return {}
        valid_actions = [dict(item) for item in actions if isinstance(item, dict)]
        try:
            executed = int(execution_result)
        except (TypeError, ValueError):
            executed = 0
        raw_action_results = getattr(execution_result, "action_results", None)
        action_results = list(raw_action_results) if isinstance(raw_action_results, list) else []
        raw_pre_states = getattr(execution_result, "pre_states", None)
        pre_states = {
            str(entity_id): str(state)
            for entity_id, state in raw_pre_states.items()
            if str(entity_id).strip()
        } if isinstance(raw_pre_states, dict) else {}
        execution_transaction_id = str(
            getattr(execution_result, "transaction_id", "") or ""
        ).strip()
        for index, action in enumerate(valid_actions):
            params = action.get("params")
            action_reason = str(action.get("reason") or "").strip()
            if index < len(action_results) and isinstance(action_results[index], dict):
                merged = {
                    **action_results[index],
                    "domain": str(action_results[index].get("domain") or action.get("domain") or ""),
                    "service": str(action_results[index].get("service") or action.get("service") or ""),
                    "entity_id": str(action_results[index].get("entity_id") or action.get("entity_id") or ""),
                }
                if isinstance(params, dict) and params and not isinstance(merged.get("params"), dict):
                    merged["params"] = dict(params)
                if action_reason and not str(merged.get("action_reason") or "").strip():
                    merged["action_reason"] = action_reason
                action_results[index] = merged
                continue
            fallback_result = {
                "domain": str(action.get("domain") or ""),
                "service": str(action.get("service") or ""),
                "entity_id": str(action.get("entity_id") or ""),
                "status": (
                    "executed"
                    if index < executed
                    else "blocked"
                    if execution_suppressed_reason
                    else "not_executed"
                ),
                "reason": (
                    execution_suppressed_reason
                    or "ha_fast_path_missing_structured_result"
                ),
            }
            if isinstance(params, dict) and params:
                fallback_result["params"] = dict(params)
            if action_reason:
                fallback_result["action_reason"] = action_reason
            action_results.append(fallback_result)
        final_outcome = (
            "observe_only"
            if execution_suppressed_reason == "active_ai_shadow"
            else "blocked"
            if execution_suppressed_reason
            else "succeeded"
            if valid_actions and executed >= len(valid_actions)
            else "partial"
            if executed > 0
            else "failed"
        )
        audit_context = {
            "source": "addon_fast_path_execution_audit",
            "transaction_id": transaction_id,
            "decision_id": transaction_id,
            "execution_transaction_id": execution_transaction_id,
            "correlation_id": str(correlation_id or "").strip(),
            "world_snapshot_id": str(world_snapshot_id or "").strip(),
            "decision_trace": dict(decision_trace) if isinstance(decision_trace, dict) else {},
            "trigger": str(trigger or ""),
            "scene": scene,
            "confidence": confidence,
            "planned_count": len(valid_actions),
            "executed_count": executed,
            "final_outcome": final_outcome,
            "actions": valid_actions,
            "action_results": action_results,
            "pre_states": pre_states,
        }
        if execution_suppressed_reason:
            audit_context["execution_suppressed_reason"] = execution_suppressed_reason
        if isinstance(rollout, dict):
            audit_context["rollout"] = dict(rollout)
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue):
            return audit_context
        ok = enqueue("decision_execution", audit_context)
        if not ok:
            self._sys_log(
                "WARN",
                f"[Add-on FastPath] decision_execution 回写入队失败 transaction_id={transaction_id}",
            )
        return audit_context

    def _fast_path_audit_action_is_low_risk(self, action: Any) -> bool:
        if not isinstance(action, dict):
            return False
        entity_id = str(action.get("entity_id") or "").strip()
        domain = str(action.get("domain") or "").strip().lower()
        if not domain and "." in entity_id:
            domain = entity_id.split(".", 1)[0].lower()
        service = str(action.get("service") or action.get("action") or "").strip().lower()
        service = service.rsplit(".", 1)[-1]
        return domain in {"light", "input_boolean"} and service in {"turn_on", "turn_off", "toggle"}

    def _fast_path_result_allows_slow_audit(self, actions: Any) -> bool:
        if not isinstance(actions, list) or not actions:
            return False
        return all(self._fast_path_audit_action_is_low_risk(action) for action in actions)

    def _fast_path_slow_audit_prompt(self) -> str:
        return (
            "[fast_path_audit]\n"
            "Fast path already executed a provisional low-risk action.\n"
            "Audit the action, do not repeat identical light actions, and return approve/adjust/observe_only."
        )

    def _addon_fast_path_snapshot_diagnostics(self, snapshot: dict[str, Any], entity_id: str) -> dict[str, Any]:
        device_info = snapshot.get("device_info") if isinstance(snapshot.get("device_info"), dict) else {}
        topology = snapshot.get("room_topology") if isinstance(snapshot.get("room_topology"), dict) else {}
        capabilities = snapshot.get("device_capability_snapshot")
        capability_rows = 0
        if isinstance(capabilities, dict):
            rows = capabilities.get("devices", capabilities.get("items", capabilities.get("data", capabilities)))
            capability_rows = len(rows) if isinstance(rows, (dict, list, tuple, set)) else 0
        elif isinstance(capabilities, (list, tuple, set)):
            capability_rows = len(capabilities)

        active_space = ""
        for key in ("active_space_id", "space_id", "trigger_room", "room", "area"):
            active_space = str(snapshot.get(key) or "").strip()
            if active_space:
                break
        if not active_space:
            info = device_info.get(entity_id)
            if isinstance(info, dict):
                active_space = str(info.get("space_id") or info.get("room") or info.get("area") or "").strip()

        return {
            "active_space": active_space,
            "capability_rows": capability_rows,
            "device_info_count": len(device_info),
            "topology_count": len(topology),
        }

    def _is_presence_arrival_for_slow_inference(self, entity_id: str, new_state: str) -> bool:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        state = str(new_state or "").strip().lower()
        if state not in {"on", "open", "home", "playing", "occupied", "present"}:
            return False
        if domain != "binary_sensor":
            return False
        return self._is_presence_listener_entity(entity_id)

    def _is_presence_departure_for_slow_inference(self, entity_id: str, new_state: str) -> bool:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        state = str(new_state or "").strip().lower()
        if state not in {"off", "closed", "not_home", "away", "idle", "clear", "empty", "vacant"}:
            return False
        if domain != "binary_sensor":
            return False
        return self._is_presence_listener_entity(entity_id)

    def _is_actionable_contact_arrival_for_slow_inference(self, entity_id: str, new_state: str) -> bool:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        state = str(new_state or "").strip().lower()
        if state not in {"on", "open"}:
            return False
        if domain != "binary_sensor":
            return False
        info = self._listener_entity_metadata(entity_id)
        sensor_type = str((info or {}).get("sensor_type") or "").strip().lower()
        device_class = str((info or {}).get("device_class") or "").strip().lower()
        if sensor_type in self._ACTIONABLE_CONTACT_SENSOR_TYPES or device_class in self._ACTIONABLE_CONTACT_SENSOR_TYPES:
            return True
        eid_lower = entity_id.lower()
        name_lower = str((info or {}).get("name") or "").lower()
        return any(kw in eid_lower or kw in name_lower for kw in self._ACTIONABLE_CONTACT_KW)

    def _is_managed_control_event_for_slow_inference(self, entity_id: str, new_state: str) -> bool:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain not in self._CONTROL_EVENT_DOMAINS:
            return False
        state = str(new_state or "").strip().lower()
        if not state or state in {"unknown", "unavailable"}:
            return False
        device_info = getattr(self, "device_info", {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        info = device_info.get(entity_id) if isinstance(device_info, dict) else None
        if not isinstance(info, dict):
            return False
        mode = str(info.get("control_mode") or info.get("policy") or "shared").strip().lower() or "shared"
        return mode in {"ai", "shared"}

    @staticmethod
    def _fast_path_context_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return None
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "daylight"}:
            return True
        if text in {"0", "false", "no", "off", "dark"}:
            return False
        return None

    @staticmethod
    def _fast_path_context_float(*values: Any) -> float | None:
        for value in values:
            if value in (None, ""):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _fast_path_context_hour(*values: Any) -> int | None:
        for value in values:
            if value in (None, ""):
                continue
            try:
                hour = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= hour <= 23:
                return hour
        return None

    def _fast_path_context_is_protected_night_hour(self, context: dict[str, Any]) -> bool:
        local_hour = self._fast_path_context_hour(
            context.get("local_hour"),
            context.get("now_hour"),
            context.get("hour"),
        )
        if local_hour is None:
            return False
        return local_hour >= self._PROTECTED_NIGHT_START_HOUR or local_hour < self._PROTECTED_NIGHT_END_HOUR

    def _fast_path_no_match_slow_inference_skip_reason(
        self,
        entity_id: str,
        new_state: str,
        snapshot: dict[str, Any] | None = None,
    ) -> str:
        if not self._is_presence_arrival_for_slow_inference(entity_id, new_state):
            return ""
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        context = snapshot.get("environment_context") if isinstance(snapshot.get("environment_context"), dict) else {}
        if not context:
            return ""
        is_dark = self._fast_path_context_bool(context.get("is_dark"))
        if is_dark is True:
            return ""
        lux = self._fast_path_context_float(
            context.get("illuminance_lux_min"),
            context.get("illuminance_lux"),
            context.get("lux"),
            context.get("ambient_lux"),
        )
        if lux is not None and lux <= self._DAYLIGHT_GUARD_LUX_THRESHOLD:
            return ""
        sun_state = str(context.get("sun_state") or "").strip().lower()
        if sun_state in self._DARK_SUN_STATES:
            return ""
        is_daylight = self._fast_path_context_bool(context.get("is_daylight"))
        if sun_state in self._DAYLIGHT_SUN_STATES or is_daylight is True:
            return self._DAYLIGHT_AUTO_LIGHTING_SUPPRESSED
        if is_daylight is False:
            return ""
        if lux is not None and lux > self._DAYLIGHT_GUARD_LUX_THRESHOLD:
            if self._fast_path_context_is_protected_night_hour(context):
                return ""
            return self._DAYLIGHT_AUTO_LIGHTING_SUPPRESSED
        local_hour = self._fast_path_context_hour(
            context.get("local_hour"),
            context.get("now_hour"),
            context.get("hour"),
        )
        if local_hour is not None and self._DAYLIGHT_FALLBACK_START_HOUR <= local_hour <= self._DAYLIGHT_FALLBACK_END_HOUR:
            return self._DAYLIGHT_AUTO_LIGHTING_SUPPRESSED
        return ""

    def _should_slow_infer_after_fast_path_no_match(
        self,
        entity_id: str,
        new_state: str,
        snapshot: dict[str, Any] | None = None,
    ) -> bool:
        """Allow slow inference for user-meaningful managed events after fast-path misses."""
        if self._fast_path_no_match_slow_inference_skip_reason(entity_id, new_state, snapshot):
            return False
        return (
            self._is_presence_arrival_for_slow_inference(entity_id, new_state)
            or self._is_presence_departure_for_slow_inference(entity_id, new_state)
            or self._is_actionable_contact_arrival_for_slow_inference(entity_id, new_state)
            or self._is_managed_control_event_for_slow_inference(entity_id, new_state)
        )

    def _schedule_arrival_baseline_sample(self, entity_id: str, old_state: str, new_state: str) -> None:
        """Sample room lights shortly after a presence arrival."""
        old_value = str(old_state or "").strip().lower()
        new_value = str(new_state or "").strip().lower()
        if old_value not in {"off", "closed", "not_home", "away", "idle", "clear", "empty", "vacant", "0", ""}:
            return
        if not self._is_presence_arrival_for_slow_inference(entity_id, new_value):
            return
        device_info = getattr(self, "device_info", {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        info = device_info.get(entity_id) if isinstance(device_info, dict) else {}
        room = str((info or {}).get("room") or (info or {}).get("area") or "").strip()
        if not room:
            area_getter = getattr(self, "_get_entity_area", None)
            if callable(area_getter):
                try:
                    room = str(area_getter(entity_id) or "").strip()
                except Exception:
                    room = ""
        if not room:
            return

        states = getattr(self.hass, "states", None)
        pre_light_states: dict[str, str | None] = {}
        for light_entity_id, light_info in device_info.items():
            if not str(light_entity_id).startswith("light.") or not isinstance(light_info, dict):
                continue
            light_room = str(light_info.get("room") or light_info.get("area") or "").strip()
            if light_room != room:
                continue
            light_state = states.get(light_entity_id) if states is not None and hasattr(states, "get") else None
            pre_light_states[light_entity_id] = getattr(light_state, "state", None) if light_state is not None else None
        sample_started_at = time.time()

        def _sample(_now: Any = None) -> None:
            try:
                states = getattr(self.hass, "states", None)
                state_obj = states.get(entity_id) if states is not None and hasattr(states, "get") else None
                if state_obj is not None and str(getattr(state_obj, "state", "") or "").strip().lower() not in {
                    "on",
                    "open",
                    "home",
                    "playing",
                    "occupied",
                    "present",
                }:
                    return
                recorder = getattr(self, "_record_arrival_snapshot", None)
                if callable(recorder):
                    sample_ended_at = time.time()
                    observed_light_states: dict[str, str | None] = {}
                    state_change_evidence: dict[str, dict[str, Any]] = {}
                    smartagent_actions: list[dict[str, Any]] = []
                    for light_entity_id in pre_light_states:
                        light_state = states.get(light_entity_id) if states is not None and hasattr(states, "get") else None
                        observed_light_states[light_entity_id] = (
                            getattr(light_state, "state", None) if light_state is not None else None
                        )
                        state_context = getattr(light_state, "context", None)
                        last_changed = getattr(light_state, "last_changed", None)
                        try:
                            changed_at = float(last_changed.timestamp())
                        except (AttributeError, TypeError, ValueError, OSError):
                            changed_at = 0.0
                        if sample_started_at <= changed_at <= sample_ended_at:
                            user_id = str(getattr(state_context, "user_id", None) or "").strip()
                            parent_id = str(getattr(state_context, "parent_id", None) or "").strip()
                            context_id = str(getattr(state_context, "id", None) or "").strip()
                            if user_id:
                                origin = "user_action"
                                actor = f"ha_user:{user_id}"
                            elif parent_id:
                                origin = "automation"
                                actor = "homeassistant:automation"
                            else:
                                origin = "unknown"
                                actor = "unknown"
                            state_change_evidence[light_entity_id] = {
                                "origin": origin,
                                "actor": actor,
                                "context_id": context_id or "not_applicable",
                                "time": changed_at,
                            }

                    causal_since = max(
                        sample_started_at,
                        sample_ended_at - self._ARRIVAL_CAUSAL_WINDOW_SECONDS,
                    )
                    recent_query = getattr(self, "_recent_ai_action_entities", None)
                    if callable(recent_query):
                        try:
                            recent_by_entity = recent_query(
                                since=causal_since,
                                until=sample_ended_at,
                                statuses={"executed"},
                            )
                        except Exception as exc:
                            _LOGGER.warning("[ArrivalBaseline] recent AI action query failed: %s", exc)
                            recent_by_entity = {}
                        if isinstance(recent_by_entity, dict):
                            for rows in recent_by_entity.values():
                                if isinstance(rows, list):
                                    smartagent_actions.extend(
                                        dict(item) for item in rows if isinstance(item, dict)
                                    )

                    last_ai_actions = getattr(self, "_last_ai_actions", {})
                    for action_entity_id, action in (
                        last_ai_actions.items() if isinstance(last_ai_actions, dict) else ()
                    ):
                        if not isinstance(action, dict):
                            continue
                        try:
                            action_time = float(action.get("time") or 0)
                        except (TypeError, ValueError):
                            continue
                        if causal_since <= action_time <= sample_ended_at:
                            smartagent_actions.append({"entity_id": str(action_entity_id), **dict(action)})
                    deduplicated_actions: list[dict[str, Any]] = []
                    seen_actions: set[tuple[str, str, int, float, str]] = set()
                    for action in smartagent_actions:
                        try:
                            action_time = float(action.get("time") or 0)
                        except (TypeError, ValueError):
                            action_time = 0.0
                        fingerprint = (
                            str(action.get("entity_id") or ""),
                            str(action.get("transaction_id") or ""),
                            int(action.get("action_seq") or 0),
                            action_time,
                            str(action.get("status") or ""),
                        )
                        if fingerprint in seen_actions:
                            continue
                        seen_actions.add(fingerprint)
                        deduplicated_actions.append(action)
                    recorder(
                        room,
                        entity_id,
                        observed_light_states,
                        pre_light_states=pre_light_states,
                        smartagent_actions=deduplicated_actions,
                        state_change_evidence=state_change_evidence,
                        sample_started_at=sample_started_at,
                        sample_ended_at=sample_ended_at,
                    )
            except Exception as exc:
                _LOGGER.debug("[ArrivalBaseline] delayed sample failed for %s: %s", entity_id, exc)

        try:
            delay = max(1, int(getattr(self, "_PRESENCE_ON_MIN_HOLD", 1) or 1))
            async_call_later(self.hass, delay, _sample)
        except Exception as exc:
            _LOGGER.debug("[ArrivalBaseline] sample scheduling failed for %s: %s", entity_id, exc)

    def _record_silent_learning_behavior_sample(
        self,
        entity_id: str,
        old_state: str,
        new_state: str,
        source_type: str,
        old_state_obj: Any = None,
        new_state_obj: Any = None,
    ) -> None:
        if not bool(getattr(self, "_learning_mode", False)):
            return
        device_info = getattr(self, "device_info", {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        info = device_info.get(entity_id) if isinstance(device_info, dict) else {}
        if not isinstance(info, dict):
            info = {}
        info_payload = dict(info)
        room = str(info.get("room") or info.get("area") or "").strip()
        if not room:
            area_getter = getattr(self, "_get_entity_area", None)
            if callable(area_getter):
                try:
                    room = str(area_getter(entity_id) or "").strip()
                except Exception:
                    room = ""
        if room and not str(info_payload.get("room") or info_payload.get("area") or "").strip():
            info_payload["room"] = room
        now = self._ha_local_now()
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue):
            return
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        old_attrs = getattr(old_state_obj, "attributes", None)
        new_attrs = getattr(new_state_obj, "attributes", None)
        state_context = getattr(new_state_obj, "context", None)
        user_id = str(getattr(state_context, "user_id", None) or "").strip()
        parent_id = str(getattr(state_context, "parent_id", None) or "").strip()
        context_id = str(getattr(state_context, "id", None) or "").strip()
        if user_id:
            origin = "user_action"
            actor = f"ha_user:{user_id}"
        elif parent_id:
            origin = "automation"
            actor = "homeassistant:automation"
        else:
            origin = "unknown"
            actor = "unknown"
        payload = {
            "action": "sample_state_transition",
            "entity_id": entity_id,
            "old_state": str(old_state or ""),
            "new_state": str(new_state or ""),
            "old_attributes": dict(old_attrs) if isinstance(old_attrs, dict) else {},
            "new_attributes": dict(new_attrs) if isinstance(new_attrs, dict) else {},
            "device_info": info_payload,
            "source_type": str(source_type or ""),
            "origin": origin,
            "actor": actor,
            "decision_id": "not_applicable",
            "transaction_id": context_id or "not_applicable",
            "world_snapshot_id": "not_applicable",
        }
        if enqueue("behavior", payload, ts=ts):
            self._sys_log("INFO", f"[SilentLearning] behavior sample forwarded: {entity_id}")

    def _emit_addon_fast_path_event(self, payload: dict[str, Any]) -> None:
        try:
            self.hass.bus.async_fire("smart_agent_decision_bubble", payload)
        except Exception as exc:
            _LOGGER.debug("[Listeners] smart_agent_decision_bubble emit failed: %s", exc)

    def _spawn_addon_fast_path_task(
        self,
        coro: Any,
        *,
        entity_id: str,
        old_state: str,
        new_state: str,
    ) -> None:
        try:
            task = self.hass.async_create_task(coro)
        except Exception as exc:
            close = getattr(coro, "close", None)
            if callable(close):
                close()
            exception_type = type(exc).__name__
            _LOGGER.warning(
                "[Listeners] add-on fast-path task create failed entity=%s old_state=%s new_state=%s: %s",
                entity_id,
                old_state,
                new_state,
                exc,
                exc_info=(type(exc), exc, getattr(exc, "__traceback__", None)),
            )
            self._sys_log(
                "ERROR",
                f"[Add-on FastPath] task create failed fail-closed | entity={entity_id} "
                f"reason=task_create_failed exception_type={exception_type}",
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
                    "reason": "task_create_failed",
                    "exception_type": exception_type,
                    "fail_closed": True,
                }
            )
            return
        add_done_callback = getattr(task, "add_done_callback", None)
        if callable(add_done_callback):
            add_done_callback(
                lambda done_task: self._handle_addon_fast_path_task_done(
                    done_task,
                    entity_id=entity_id,
                    old_state=old_state,
                    new_state=new_state,
                )
            )

    def _handle_addon_fast_path_task_done(
        self,
        task: Any,
        *,
        entity_id: str,
        old_state: str,
        new_state: str,
    ) -> None:
        cancelled = False
        try:
            cancelled = bool(task.cancelled()) if hasattr(task, "cancelled") else False
        except Exception:
            cancelled = False
        if cancelled:
            self._sys_log(
                "WARN",
                f"[Add-on FastPath] task cancelled fail-closed | entity={entity_id} reason=task_cancelled",
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
                    "reason": "task_cancelled",
                    "fail_closed": True,
                }
            )
            return
        try:
            exc = task.exception() if hasattr(task, "exception") else None
        except asyncio.CancelledError:
            self._sys_log(
                "WARN",
                f"[Add-on FastPath] task cancelled fail-closed | entity={entity_id} reason=task_cancelled",
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
                    "reason": "task_cancelled",
                    "fail_closed": True,
                }
            )
            return
        except Exception as err:
            exc = err
        if exc is None:
            return
        _LOGGER.warning(
            "[Listeners] add-on fast-path task failed entity=%s old_state=%s new_state=%s: %s",
            entity_id,
            old_state,
            new_state,
            exc,
            exc_info=(type(exc), exc, getattr(exc, "__traceback__", None)),
        )
        exception_type = type(exc).__name__
        self._sys_log(
            "ERROR",
            f"[Add-on FastPath] task failed fail-closed | entity={entity_id} "
            f"reason=task_exception exception_type={exception_type}",
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
                "reason": "task_exception",
                "exception_type": exception_type,
                "fail_closed": True,
            }
        )

    def _emit_listener_event(
        self,
        *,
        listener_action: str,
        entity_id: str,
        old_state: str = "",
        new_state: str = "",
        filter_reason: str = "",
        source_type: str = "",
        **extra: Any,
    ) -> None:
        try:
            now_ts = time.time()
            startup_elapsed = now_ts - float(getattr(self, "_startup_time", now_ts) or now_ts)
            startup_grace = int(getattr(self, "_startup_grace", 0) or 0)
            startup_remaining = max(0, int(startup_grace - startup_elapsed))
            payload: dict[str, Any] = {
                "listener_action": str(listener_action or "unknown"),
                "entity_id": str(entity_id or ""),
                "old_state": str(old_state or ""),
                "new_state": str(new_state or ""),
                "filter_reason": str(filter_reason or ""),
                "source_type": str(source_type or ""),
                "ai_enabled": bool(self._is_enabled()),
                "sensors_muted": bool(getattr(self, "_sensors_muted", False)),
                "startup_remaining": startup_remaining,
                "startup_cooldown": startup_remaining > 0,
                "mode": str(getattr(self, "_mode", "") or ""),
            }
            payload.update({key: value for key, value in extra.items() if value is not None})
            self._last_listener_event = payload
            if filter_reason:
                self._last_listener_filter_reason = str(filter_reason)
            enqueue = getattr(self, "_enqueue_internal_event", None)
            if callable(enqueue):
                try:
                    event_time = self._ha_local_now().isoformat()
                    info = {}
                    device_info = getattr(self, "device_info", {})
                    if isinstance(device_info, dict):
                        maybe_info = device_info.get(str(entity_id or ""))
                        if isinstance(maybe_info, dict):
                            info = maybe_info
                    area = str(info.get("room") or info.get("area") or "").strip()
                    if not area:
                        area_getter = getattr(self, "_get_entity_area", None)
                        if callable(area_getter):
                            try:
                                area = str(area_getter(str(entity_id or "")) or "").strip()
                            except Exception:
                                area = ""
                    enqueue(
                        "event",
                        {
                            "time": event_time,
                            "type": "smart_agent_listener_event",
                            "detail": json.dumps(payload, ensure_ascii=False, default=str),
                            "entity_id": str(entity_id or ""),
                            "state": str(new_state or old_state or ""),
                            "source": "ha_listener_runtime",
                            "area": area,
                            "confidence": 0,
                            "transaction_id": 0,
                            "action_seq": 0,
                        },
                        ts=event_time,
                    )
                except Exception as exc:
                    _LOGGER.debug("[Listeners] smart_agent_listener_event persist skipped: %s", exc)
            self.hass.bus.async_fire("smart_agent_listener_event", payload)
        except Exception as exc:
            _LOGGER.debug("[Listeners] smart_agent_listener_event emit failed: %s", exc)

    async def _run_addon_fast_path_fail_closed(
        self,
        entity_id: str,
        new_state: str,
        old_state: str,
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
                    arbitration_validation = validate_auto_execution_arbitration(response)
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
                    reason = str(response.get("reason") or details.get("reason") or response.get("error") or "")
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

                    def _fast_path_handoff_context(source: str) -> dict[str, Any]:
                        return {
                            "source": source,
                            "transaction_id": transaction_id,
                            "correlation_id": correlation_id,
                            "world_snapshot_id": world_snapshot_id,
                            "reason": reason or "",
                            "decision_trace": dict(decision_trace) if isinstance(decision_trace, dict) else {},
                        }

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
                    trigger_info = device_info.get(entity_id, {})
                    if not isinstance(trigger_info, dict):
                        trigger_info = {}
                    rollout_decision = evaluate_active_ai_execution_gate(
                        ai_enabled=bool(is_enabled()) if callable(is_enabled) else False,
                        config=ActiveAiRolloutConfig.from_mapping(rollout_payload),
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
                    audit_pending = bool(
                        matched
                        and arbitration_validation.allowed
                        and not execution_suppressed_reason
                        and self._fast_path_result_allows_slow_audit(actions)
                    )
                    self._sys_log(
                        "INFO",
                        "[Add-on FastPath] result "
                        f"status={status} matched={matched} path_taken={path_taken} "
                        f"reason={reason or '-'} scene={scene or '-'} "
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
                            "actions": actions,
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
                            self._sys_log(
                                "INFO",
                                f"[Add-on FastPath] execution suppressed | entity={entity_id} reason={execution_suppressed_reason}",
                            )
                            if execution_suppressed_reason.startswith("active_ai_"):
                                await self._execute_fast_path_decision_result(
                                    result,
                                    entity_id=entity_id,
                                    source_label="AddonFastPath",
                                    transaction_id=transaction_id,
                                    correlation_id=correlation_id,
                                    world_snapshot_id=world_snapshot_id,
                                    decision_trace=decision_trace,
                                    trigger=f"{entity_id}: {old_state} -> {new_state}",
                                    active_ai_rollout=rollout_payload,
                                )
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
                                result,
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
                            if self._should_slow_infer_after_fast_path_no_match(entity_id, new_state, snapshot):
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
                        if reason == "confidence_below_auto_threshold" and not confirm_required:
                            if action_count > 0 or self._should_slow_infer_after_fast_path_no_match(entity_id, new_state, snapshot):
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
                        if self._should_slow_infer_after_fast_path_no_match(entity_id, new_state, snapshot):
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
                                source_trace_context={
                                    "source": "addon_fast_path_409",
                                    "transaction_id": transaction_id,
                                    "correlation_id": correlation_id,
                                    "world_snapshot_id": world_snapshot_id,
                                    "reason": reason or "input_incomplete",
                                    "decision_trace": dict(decision_trace) if isinstance(decision_trace, dict) else {},
                                },
                            )
                        return
                    elif status > 0:
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

    def _make_state_handler(self):
        """Build the state-change callback."""
        @callback
        def _state_changed(ev) -> None:
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
            if entity_id not in device_info_snapshot:
                try:
                    if self._reconcile_device_info_entity_ids_from_ha_registry():
                        device_info_snapshot = getattr(self, "device_info", {}) or {}
                except Exception as exc:
                    _LOGGER.debug("[Listeners] state-handler reconciliation skipped for %s: %s", entity_id, exc)
            if entity_id not in device_info_snapshot:
                unmanaged_filter_reason = "unmanaged_entity"
                self._last_listener_filter_reason = unmanaged_filter_reason
                _LOGGER.debug(
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
                        _LOGGER.warning(message)
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason=unmanaged_filter_reason,
                    source_type=source_type,
                )
                return

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
                if environment_decision.tracked and not environment_decision.forward:
                    self._last_listener_filter_reason = (
                        f"environment_telemetry_{environment_decision.reason}"
                    )
                    _LOGGER.debug(
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

            _LOGGER.debug("[事件] %s: %s -> %s (来源: %s)", entity_id, old_s, new_s, source_type)
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

            if domain == "sensor" and old_s and new_s:
                try:
                    delta = abs(float(new_s) - float(old_s))
                    eid_lower = entity_id.lower()
                    # Frigate person_count：启用 Frigate 时降低触发阈值到 1（0→1 是关键事件）
                    frigate_on = getattr(self, "_frigate_enabled", False)
                    is_person_count = frigate_on and any(kw in eid_lower for kw in self._PERSON_COUNT_KW)
                    threshold = 1 if is_person_count else 5
                    if delta < threshold:
                        _LOGGER.debug(
                            "[ListenerFilter] numeric deadband entity=%s delta=%.3f threshold=%s",
                            entity_id,
                            delta,
                            threshold,
                        )
                        self._emit_listener_event(
                            listener_action="filtered",
                            entity_id=entity_id,
                            old_state=old_s,
                            new_state=new_s,
                            filter_reason="numeric_deadband",
                            source_type=source_type,
                            delta=delta,
                            threshold=threshold,
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

            self._record_silent_learning_behavior_sample(entity_id, old_s, new_s, source_type, old, new)
            self._record_presence_interaction_trace(entity_id, domain, new_s, source_type)

            if domain in self._CONTROL_EVENT_DOMAINS:
                self._last_listener_filter_reason = "controllable_state_feedback"
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="controllable_state_feedback",
                    source_type=source_type,
                )
                return

            info = device_info_snapshot.get(entity_id) if isinstance(device_info_snapshot, dict) else {}
            info = self._listener_entity_metadata(entity_id, info=info, state_obj=new)
            is_presence_sensor = self._is_presence_listener_entity(entity_id, info)
            if domain == "binary_sensor" and not is_presence_sensor:
                if self._is_actionable_contact_arrival_for_slow_inference(entity_id, new_s):
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

            self._schedule_arrival_baseline_sample(entity_id, old_s, new_s)
            self._emit_listener_event(
                listener_action="fast_path_scheduled",
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
                source_type=source_type,
            )
            self._spawn_addon_fast_path_task(
                self._run_addon_fast_path_fail_closed(entity_id, new_s, old_s),
                entity_id=entity_id,
                old_state=old_s,
                new_state=new_s,
            )
            return
        return _state_changed

    def _listener_entity_metadata(
        self,
        entity_id: str,
        *,
        info: dict[str, Any] | None = None,
        state_obj: Any | None = None,
    ) -> dict[str, Any]:
        row = dict(info) if isinstance(info, dict) else {}
        if not row:
            device_info = getattr(self, "device_info", {})
            stored = device_info.get(entity_id) if isinstance(device_info, dict) else None
            if isinstance(stored, dict):
                row.update(stored)
        if state_obj is None:
            states = getattr(getattr(self, "hass", None), "states", None)
            get_state = getattr(states, "get", None)
            state_obj = get_state(entity_id) if callable(get_state) else None
        attributes = getattr(state_obj, "attributes", None)
        if isinstance(attributes, dict):
            for key in ("device_class", "friendly_name", "entity_category"):
                if not row.get(key) and attributes.get(key) not in (None, ""):
                    row[key] = attributes.get(key)
        return row

    def _is_presence_listener_entity(self, entity_id: str, info: dict[str, Any] | None = None) -> bool:
        """Return True for managed entities that can represent human presence."""
        domain = str(entity_id or "").split(".", 1)[0]
        if domain != "binary_sensor":
            return False
        row = self._listener_entity_metadata(entity_id, info=info)
        sensor_type = str(row.get("sensor_type") or "").strip().lower()
        if sensor_type in self._ACTIONABLE_SENSOR_TYPES:
            return True
        if sensor_type and sensor_type not in self._GENERIC_BINARY_CLASS_VALUES:
            return False
        device_class = str(row.get("device_class") or row.get("ha_device_class") or "").strip().lower()
        capability = str(row.get("capability") or "").strip().lower()
        specific_class = device_class or (
            capability if capability not in self._GENERIC_BINARY_CLASS_VALUES else ""
        )
        if specific_class in self._PRESENCE_DEVICE_CLASSES:
            return True
        if specific_class:
            return False
        eid_lower = str(entity_id or "").lower()
        name_lower = str(row.get("name") or row.get("friendly_name") or "").lower()
        return any(kw in eid_lower or kw in name_lower for kw in self._PRESENCE_KW)

    def _reconcile_active_listener_states(self, entity_ids: list[str]) -> None:
        """Catch up active managed presence sensors that were already on before listener binding."""
        if not entity_ids:
            return
        states = getattr(getattr(self, "hass", None), "states", None)
        get_state = getattr(states, "get", None)
        if not callable(get_state):
            return
        reconciled = getattr(self, "_listener_active_state_reconciled", None)
        if not isinstance(reconciled, dict):
            reconciled = {}
            self._listener_active_state_reconciled = reconciled
        device_info = getattr(self, "device_info", {}) or {}
        if not isinstance(device_info, dict):
            device_info = {}

        for entity_id in entity_ids:
            raw_info = device_info.get(entity_id)
            info = raw_info if isinstance(raw_info, dict) else {}
            if not self._is_presence_listener_entity(entity_id, info):
                continue
            try:
                state_obj = get_state(entity_id)
            except Exception as exc:
                _LOGGER.debug("[Listeners] active state reconcile read failed for %s: %s", entity_id, exc)
                continue
            state = str(getattr(state_obj, "state", "") or "").strip().lower()
            if state != "on":
                reconciled.pop(entity_id, None)
                continue
            state_marker = str(
                getattr(state_obj, "last_changed", "")
                or getattr(state_obj, "last_updated", "")
                or state
            )
            reconcile_marker = f"{state}:{state_marker}"
            if reconciled.get(entity_id) == reconcile_marker:
                continue
            reconciled[entity_id] = reconcile_marker

            if not self._is_enabled():
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state="unknown",
                    new_state=state,
                    filter_reason="ai_disabled",
                    source_type="state_reconcile",
                    reconcile_reason="listener_refresh_active_state",
                )
                continue
            if getattr(self, "_sensors_muted", False):
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state="unknown",
                    new_state=state,
                    filter_reason="sensors_muted",
                    source_type="state_reconcile",
                    reconcile_reason="listener_refresh_active_state",
                )
                continue

            self._emit_listener_event(
                listener_action="filtered",
                entity_id=entity_id,
                old_state="unknown",
                new_state=state,
                filter_reason="state_recovery_unknown_unavailable",
                source_type="state_reconcile",
                reconcile_reason="listener_refresh_active_state",
            )

    async def _async_refresh_device_info_from_addon_devices(self, *, reason: str = "") -> bool:
        """Refresh runtime listener device_info from the add-on device projection."""
        status = {
            "ok": False,
            "source": "addon_devices",
            "reason": str(reason or "manual"),
            "count": 0,
        }
        client = getattr(self, "_addon_client", None)
        get_devices = getattr(client, "get_devices", None)
        if not callable(get_devices):
            status["reason"] = "addon_client_unavailable"
            self._last_addon_device_sync_status = status
            return False

        try:
            rows = await get_devices()
        except Exception as exc:
            status["reason"] = "addon_exception"
            status["error"] = str(exc)
            self._last_addon_device_sync_status = status
            return False

        if rows is None:
            status["reason"] = "addon_not_available"
            self._last_addon_device_sync_status = status
            return False
        if isinstance(rows, dict):
            status["reason"] = "addon_error"
            if rows.get("__status") is not None:
                status["status"] = rows.get("__status")
            if rows.get("error") is not None:
                status["error"] = str(rows.get("error"))
            self._last_addon_device_sync_status = status
            return False
        if not isinstance(rows, list):
            status["reason"] = "invalid_payload"
            status["payload_type"] = type(rows).__name__
            self._last_addon_device_sync_status = status
            return False

        next_device_info: dict[str, dict[str, Any]] = {}
        next_environment_context_info: dict[str, dict[str, Any]] = {}
        skipped = 0
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            mapped = self._managed_device_info_row_from_addon_device(row)
            if mapped is None:
                skipped += 1
                continue
            entity_id, info = mapped
            if self._is_listener_runtime_entity(entity_id, info):
                next_device_info[entity_id] = info
            else:
                skipped += 1
            if environment_sensor_kind(entity_id, info):
                next_environment_context_info[entity_id] = info

        current = getattr(self, "device_info", {}) or {}
        if not isinstance(current, dict):
            current = {}
        current_environment = getattr(self, "_environment_context_device_info", {}) or {}
        if not isinstance(current_environment, dict):
            current_environment = {}
        changed = current != next_device_info or current_environment != next_environment_context_info
        self.device_info = next_device_info
        self._environment_context_device_info = next_environment_context_info
        if changed:
            reconciled = getattr(self, "_listener_active_state_reconciled", None)
            if isinstance(reconciled, dict):
                for entity_id in list(reconciled):
                    if entity_id not in next_device_info:
                        reconciled.pop(entity_id, None)
            presence_inference = getattr(self, "_presence_inference", None)
            if presence_inference is not None and hasattr(presence_inference, "device_info"):
                try:
                    presence_inference.device_info = self.device_info
                except Exception:
                    pass
            updater = getattr(self, "async_set_updated_data", None)
            if callable(updater):
                try:
                    updater({})
                except Exception:
                    pass

        status.update(
            {
                "ok": True,
                "reason": str(reason or "manual"),
                "count": len(next_device_info),
                "environment_context_count": len(next_environment_context_info),
                "skipped": skipped,
                "changed": changed,
            }
        )
        self._device_info_source = "addon_devices"
        self._last_addon_device_sync_status = status
        return changed

    def _is_actionable_sensor_runtime_entity(self, entity_id: str, info: dict[str, Any]) -> bool:
        sensor_type = str((info or {}).get("sensor_type") or "").strip().lower()
        if sensor_type in self._ACTIONABLE_SENSOR_TYPES:
            return True
        text = " ".join(
            str((info or {}).get(key) or "")
            for key in ("name", "type", "capability", "device_class")
        ).lower()
        text = f"{entity_id.lower()} {text}"
        return any(str(kw).lower() in text for kw in (*self._PRESENCE_KW, *self._PERSON_COUNT_KW))

    def _is_listener_runtime_entity(self, entity_id: str, info: dict[str, Any]) -> bool:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain not in self._LISTENER_DOMAINS:
            return False
        if domain != "sensor":
            return True
        return self._is_actionable_sensor_runtime_entity(entity_id, info)

    def _managed_device_info_row_from_addon_device(
        self,
        row: dict[str, Any],
    ) -> tuple[str, dict[str, Any]] | None:
        if row.get("managed") is False or row.get("in_sa") is False:
            return None
        entity_id = str(row.get("entity_id") or row.get("id") or "").strip()
        if "." not in entity_id:
            return None
        ops = str(row.get("ops") or "").strip()
        if ops == "__smartagent_deleted__":
            return None
        domain = entity_id.split(".", 1)[0]
        if domain not in self._LISTENER_DOMAINS:
            return None

        mode = str(row.get("control_mode") or row.get("policy") or "shared").strip() or "shared"
        valid_modes = getattr(self, "_VALID_CONTROL_MODES", {"ai", "ha", "shared"})
        if mode not in valid_modes:
            mode = "shared"

        room = (
            row.get("room")
            or row.get("area")
            or row.get("space_id")
            or row.get("space")
            or ""
        )
        if isinstance(room, (list, tuple)):
            room = next((str(item).strip() for item in room if str(item).strip()), "")
        space_id = row.get("space_id") or row.get("space") or ""
        if isinstance(space_id, (list, tuple)):
            space_id = next((str(item).strip() for item in space_id if str(item).strip()), "")
        name = (
            row.get("name")
            or row.get("friendly_name")
            or row.get("display_name")
            or entity_id
        )
        dev_type = (
            row.get("type")
            or row.get("dev_type")
            or row.get("capability")
            or row.get("domain")
            or domain
        )
        vacant_action = str(row.get("vacant_action") or "preserve").strip().lower()
        if vacant_action not in DEVICE_VACANT_ACTIONS:
            vacant_action = "preserve"
        info = {
            "name": str(name or entity_id),
            "room": str(room or ""),
            "space_id": str(space_id or ""),
            "type": str(dev_type or domain),
            "ops": ops,
            "control_mode": mode,
            "managed": True,
            "vacant_action": vacant_action,
            "sensor_type": str(row.get("sensor_type") or ""),
            "device_class": str(row.get("device_class") or ""),
            "unit_of_measurement": str(row.get("unit_of_measurement") or row.get("unit") or ""),
            "ha_unique_id": str(row.get("ha_unique_id") or row.get("unique_id") or ""),
            "ha_device_id": str(row.get("ha_device_id") or row.get("device_id") or ""),
        }
        return entity_id, info

    def _device_info_row_from_addon_device(self, row: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        mapped = self._managed_device_info_row_from_addon_device(row)
        if mapped is None:
            return None
        entity_id, info = mapped
        if not self._is_listener_runtime_entity(entity_id, info):
            return None
        return entity_id, info

    def _managed_listener_entity_ids(self) -> list[str]:
        """Return managed entity ids that should receive HA state listeners."""
        try:
            self._reconcile_device_info_entity_ids_from_ha_registry()
        except Exception as exc:
            _LOGGER.debug("[Listeners] entity registry reconciliation failed: %s", exc)
        device_info = getattr(self, "device_info", {}) or {}
        if not isinstance(device_info, dict):
            return []
        return [
            eid
            for eid in device_info
            if isinstance(eid, str)
            and self._is_listener_runtime_entity(eid, device_info.get(eid) if isinstance(device_info.get(eid), dict) else {})
        ]

    def _reconcile_device_info_entity_ids_from_ha_registry(self) -> bool:
        """Migrate managed entity ids when HA's entity registry renamed them."""
        device_info = getattr(self, "device_info", {}) or {}
        if not isinstance(device_info, dict) or not device_info:
            return False

        hass = getattr(self, "hass", None)
        if hass is None:
            return False
        states = getattr(hass, "states", None)

        try:
            from homeassistant.helpers import entity_registry as er
            entity_reg = er.async_get(hass)
        except Exception as exc:
            _LOGGER.debug("[Listeners] entity registry unavailable for reconciliation: %s", exc)
            return False

        def _state_obj(entity_id: str) -> Any:
            getter = getattr(states, "get", None)
            if not callable(getter):
                return None
            try:
                return getter(entity_id)
            except Exception:
                return None

        def _entry_obj(entity_id: str) -> Any:
            getter = getattr(entity_reg, "async_get", None)
            if not callable(getter):
                return None
            try:
                return getter(entity_id)
            except Exception:
                return None

        raw_entries = getattr(entity_reg, "entities", {}) or {}
        if isinstance(raw_entries, dict):
            registry_entries = list(raw_entries.values())
        elif isinstance(raw_entries, (list, tuple, set)):
            registry_entries = list(raw_entries)
        else:
            registry_entries = []

        def _entry_entity_id(entry: Any) -> str:
            return str(getattr(entry, "entity_id", "") or "").strip()

        def _entry_unique_id(entry: Any) -> str:
            return str(getattr(entry, "unique_id", "") or "").strip()

        def _entry_device_id(entry: Any) -> str:
            return str(getattr(entry, "device_id", "") or "").strip()

        by_unique_id: dict[str, list[Any]] = {}
        for entry in registry_entries:
            unique_id = _entry_unique_id(entry)
            entity_id = _entry_entity_id(entry)
            if unique_id and entity_id:
                by_unique_id.setdefault(unique_id, []).append(entry)

        def _friendly_name(entity_id: str) -> str:
            state = _state_obj(entity_id)
            attrs = getattr(state, "attributes", None)
            if isinstance(attrs, dict):
                return str(attrs.get("friendly_name") or "").strip()
            return ""

        def _find_legacy_name_match(old_entity_id: str, info: dict[str, Any]) -> Any | None:
            old_domain = old_entity_id.split(".", 1)[0] if "." in old_entity_id else ""
            old_name = str(info.get("name") or info.get("friendly_name") or "").strip()
            if not old_domain or not old_name:
                return None
            matches: list[Any] = []
            for entry in registry_entries:
                new_entity_id = _entry_entity_id(entry)
                if not new_entity_id or new_entity_id == old_entity_id or new_entity_id in device_info:
                    continue
                if new_entity_id.split(".", 1)[0] != old_domain:
                    continue
                if _state_obj(new_entity_id) is None:
                    continue
                if _friendly_name(new_entity_id) == old_name:
                    matches.append(entry)
            return matches[0] if len(matches) == 1 else None

        changed = False
        for old_entity_id, raw_info in list(device_info.items()):
            if not isinstance(old_entity_id, str) or "." not in old_entity_id:
                continue
            info = raw_info if isinstance(raw_info, dict) else {}
            current_entry = _entry_obj(old_entity_id)
            if _state_obj(old_entity_id) is not None or current_entry is not None:
                self._persist_ha_registry_metadata(old_entity_id, info, current_entry)
                continue

            match_entry = None
            match_reason = ""
            unique_id = str(info.get("ha_unique_id") or info.get("unique_id") or "").strip()
            if unique_id:
                unique_matches = [
                    entry
                    for entry in by_unique_id.get(unique_id, [])
                    if _entry_entity_id(entry) and _entry_entity_id(entry) not in device_info
                ]
                if len(unique_matches) == 1:
                    match_entry = unique_matches[0]
                    match_reason = "unique_id"
            if match_entry is None:
                match_entry = _find_legacy_name_match(old_entity_id, info)
                if match_entry is not None:
                    match_reason = "legacy_name_match"
            if match_entry is None:
                continue

            new_entity_id = _entry_entity_id(match_entry)
            if not new_entity_id or new_entity_id in device_info:
                continue
            migrated = dict(info)
            migrated["entity_id"] = new_entity_id
            if _entry_unique_id(match_entry):
                migrated["ha_unique_id"] = _entry_unique_id(match_entry)
            if _entry_device_id(match_entry):
                migrated["ha_device_id"] = _entry_device_id(match_entry)
            device_info.pop(old_entity_id, None)
            device_info[new_entity_id] = migrated
            self._persist_device_entity_id_migration(old_entity_id, new_entity_id, migrated)
            changed = True
            log = getattr(self, "_sys_log", None)
            message = (
                f"[监听器] HA 实体 ID 已对账迁移: {old_entity_id} -> {new_entity_id} "
                f"({match_reason})"
            )
            if callable(log):
                log("WARN", message)
            else:
                _LOGGER.warning(message)
        if changed:
            updater = getattr(self, "async_set_updated_data", None)
            if callable(updater):
                try:
                    updater({})
                except Exception:
                    pass
        return changed

    def _persist_ha_registry_metadata(self, entity_id: str, info: dict[str, Any], entry: Any) -> None:
        """Remember HA registry identity metadata so future HA-side renames can be reconciled."""
        if not isinstance(info, dict) or entry is None:
            return
        unique_id = str(getattr(entry, "unique_id", "") or "").strip()
        device_id = str(getattr(entry, "device_id", "") or "").strip()
        if not unique_id and not device_id:
            return
        changed = False
        if unique_id and info.get("ha_unique_id") != unique_id:
            info["ha_unique_id"] = unique_id
            changed = True
        if device_id and info.get("ha_device_id") != device_id:
            info["ha_device_id"] = device_id
            changed = True
        if changed:
            self._persist_device_registry_metadata(entity_id, info)

    def _persist_device_registry_metadata(self, entity_id: str, info: dict[str, Any]) -> None:
        db = getattr(self, "_db", None)
        execute = getattr(db, "execute", None)
        if not callable(execute):
            return
        now = self._listener_db_now_text()
        try:
            execute(
                "UPDATE devices SET ha_unique_id=?, ha_device_id=?, updated=? WHERE entity_id=?",
                (
                    str(info.get("ha_unique_id") or ""),
                    str(info.get("ha_device_id") or ""),
                    now,
                    entity_id,
                ),
            )
        except Exception as exc:
            _LOGGER.debug("[Listeners] device registry metadata persist skipped for %s: %s", entity_id, exc)

    def _persist_device_entity_id_migration(self, old_entity_id: str, new_entity_id: str, info: dict[str, Any]) -> None:
        db = getattr(self, "_db", None)
        execute = getattr(db, "execute", None)
        if not callable(execute):
            return
        now = self._listener_db_now_text()
        try:
            execute(
                "UPDATE devices SET entity_id=?, updated=? WHERE entity_id=?",
                (new_entity_id, now, old_entity_id),
            )
        except Exception as exc:
            _LOGGER.warning("[Listeners] device entity_id migration persist failed %s -> %s: %s", old_entity_id, new_entity_id, exc)
            return
        try:
            execute(
                "UPDATE devices SET ha_unique_id=?, ha_device_id=?, updated=? WHERE entity_id=?",
                (
                    str(info.get("ha_unique_id") or ""),
                    str(info.get("ha_device_id") or ""),
                    now,
                    new_entity_id,
                ),
            )
        except Exception as exc:
            _LOGGER.debug("[Listeners] migrated registry metadata persist skipped for %s: %s", new_entity_id, exc)

    def _refresh_listeners_if_entity_set_changed(self) -> bool:
        """Refresh HA state listeners when the managed entity id set drifts."""
        next_ids = set(self._managed_listener_entity_ids())
        current_ids = set(getattr(self, "_listener_entity_ids", set()) or set())
        if next_ids == current_ids:
            self._reconcile_active_listener_states(sorted(next_ids))
            return False
        self._refresh_listeners()
        return True

    def _refresh_listeners(self) -> None:
        """Re-register state-change listeners after device list changes."""
        state_removers = getattr(self, "_state_listener_removers", None)
        if state_removers is None:
            state_removers = []
            self._state_listener_removers = state_removers
        for remove in state_removers:
            try:
                remove()
            except Exception:
                pass
        state_removers.clear()
        entity_ids = self._managed_listener_entity_ids()
        self._listener_entity_ids = set(entity_ids)
        if entity_ids:
            state_removers.append(
                async_track_state_change_event(self.hass, entity_ids, self._make_state_handler())
            )
            self._reconcile_active_listener_states(entity_ids)
            self._sys_log("INFO", f"监听器已刷新，监听 {len(entity_ids)} 个实体: {', '.join(entity_ids[:5])}{'...' if len(entity_ids)>5 else ''}")
        else:
            self._sys_log("WARN", "监听器刷新：无可监听设备，请先添加设备")
