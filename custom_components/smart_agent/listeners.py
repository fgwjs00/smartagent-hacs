"""
ListenersMixin — 事件监听层。
负责：HA 状态变化监听、存在传感器去抖、触发合并、冷却管理、快速通道。
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .ha_adapter import async_call_service
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
)

_LOGGER = logging.getLogger(__name__)
_CMD_SOURCE_SENSOR = "SENSOR"


class ListenersMixin:
    """Mixin: 事件监听 — 状态变化 / 去抖 / 触发调度 / 快速通道。"""

    # AI 操作后 N 秒内的同向状态变化视为 AI 自身引起，不再触发
    _AI_ACTION_SKIP_WINDOW = AI_ACTION_SKIP_WINDOW

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
        if old in ("unavailable", "unknown") and new not in ("on", "open", "home", "playing"):
            self._sys_log("INFO", f"[过滤] 设备从 {old} 恢复为 {new}（非激活状态），跳过: {entity_id}")
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
        elapsed = now - self._last_inference.get(entity_id, 0)
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
            )
            return
        self._last_inference[entity_id] = now
        with self._pending_triggers_lock:
            if len(self._pending_triggers) >= 50:
                _dropped = [t.get("entity_id", "?") for t in self._pending_triggers[:25]]
                self._sys_log("WARN", f"[事件溢出] 触发队列满，丢弃 25 个事件: {_dropped}")
                self._pending_triggers = self._pending_triggers[-25:]
            self._pending_triggers.append({"text": trigger, "entity_id": entity_id, "one_off": one_off_prompt})

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
        
        # 提取一客制化 Prompt（主要用于展示模式的一次性指令）
        one_off_prompts = [t.get("one_off") for t in triggers if t.get("one_off")]
        final_one_off = one_off_prompts[0] if one_off_prompts else ""
        
        texts = [t["text"] for t in triggers]
        if len(texts) == 1:
            merged = texts[0]
        else:
            merged = self._compact_merged_trigger(texts)
        self._sys_log("INFO", f"[合并] 合并 {len(triggers)} 个触发，启动推理: {merged[:80]}")
        try:
            self._spawn_slow_inference_task(
                self._run_addon_decision(merged, one_off_prompt=final_one_off),
                trigger=merged,
                entity_id=str(triggers[0].get("entity_id") or ""),
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

    # ── 状态变化处理器 ────────────────────────────────────────────────────────

    def _build_addon_fast_path_snapshot(self, entity_id: str) -> dict[str, Any]:
        """Build the plain snapshot consumed by add-on Core fast-path decisions."""
        raw_device_info = getattr(self, "device_info", {}) or {}
        device_info = dict(raw_device_info) if isinstance(raw_device_info, dict) else {}
        states: dict[str, str] = {}
        for eid in device_info.keys():
            if not eid:
                continue
            state = self.hass.states.get(eid)
            if state is not None:
                states[eid] = str(state.state or "")

        topology: dict[str, list[str]] = {}
        for room, neighbors in (getattr(self, "_room_topology_cache", {}) or {}).items():
            if isinstance(neighbors, (set, list, tuple)):
                topology[str(room)] = sorted({str(item) for item in neighbors if str(item or "").strip()})

        snapshot: dict[str, Any] = {
            "device_info": device_info,
            "states": states,
            "ai_scenes": list(getattr(self, "_ai_scenes_cache", []) or []),
            "room_topology": topology,
            "mode": str(getattr(self, "_mode", "") or ""),
            "presence_contract_source": "addon_presence_engine",
        }

        occ_getter = getattr(self, "_get_room_occupancy_map", None)
        if callable(occ_getter):
            try:
                occ_map = occ_getter()
            except Exception as exc:
                _LOGGER.debug("[Listeners] _get_room_occupancy_map failed for add-on snapshot: %s", exc)
                occ_map = None
            if isinstance(occ_map, dict):
                snapshot["occ_map"] = occ_map

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
                snapshot["presence_interaction_evidence"] = [
                    dict(item) for item in interaction_evidence if isinstance(item, dict)
                ]
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
        snapshot["now_ts"] = time.time()

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

    async def _execute_fast_path_decision_result(
        self,
        result: dict[str, Any],
        *,
        entity_id: str,
        source_label: str,
    ) -> None:
        actions = result.get("actions", [])
        scene = result.get("scene", source_label)
        confidence = result.get("confidence", 90)
        room = result.get("trigger_room") or self.device_info.get(entity_id, {}).get("room", "")
        try:
            defer_seconds = int(result.get("defer_seconds", 0) or 0)
        except (TypeError, ValueError):
            defer_seconds = 0

        if defer_seconds > 0:
            await asyncio.sleep(defer_seconds)

        await self._execute_actions(
            actions if isinstance(actions, list) else [],
            trigger_summary=f"{source_label}[{scene}]",
            scene_desc=str(scene),
            confidence=confidence,
            trigger_room=room,
            is_global_cmd=False,
            cmd_source=_CMD_SOURCE_SENSOR,
        )

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
        info = self.device_info.get(entity_id, {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        sensor_type = str((info or {}).get("sensor_type") or "").strip().lower()
        if sensor_type in {"pir", "mmwave", "presence", "occupancy", "motion", "frigate"}:
            return True
        eid_lower = entity_id.lower()
        name_lower = str((info or {}).get("name") or "").lower()
        return any(kw in eid_lower or kw in name_lower for kw in self._PRESENCE_KW)

    def _is_actionable_contact_arrival_for_slow_inference(self, entity_id: str, new_state: str) -> bool:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        state = str(new_state or "").strip().lower()
        if state not in {"on", "open"}:
            return False
        if domain != "binary_sensor":
            return False
        info = self.device_info.get(entity_id, {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        sensor_type = str((info or {}).get("sensor_type") or "").strip().lower()
        if sensor_type in self._ACTIONABLE_CONTACT_SENSOR_TYPES:
            return True
        eid_lower = entity_id.lower()
        name_lower = str((info or {}).get("name") or "").lower()
        return any(kw in eid_lower or kw in name_lower for kw in self._ACTIONABLE_CONTACT_KW)

    def _should_slow_infer_after_fast_path_no_match(self, entity_id: str, new_state: str) -> bool:
        """Allow slow inference for presence arrivals and actionable contact openings."""
        return (
            self._is_presence_arrival_for_slow_inference(entity_id, new_state)
            or self._is_actionable_contact_arrival_for_slow_inference(entity_id, new_state)
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
                    recorder(room, entity_id)
            except Exception as exc:
                _LOGGER.debug("[ArrivalBaseline] delayed sample failed for %s: %s", entity_id, exc)

        try:
            delay = max(1, int(getattr(self, "_PRESENCE_ON_MIN_HOLD", 1) or 1))
            async_call_later(self.hass, delay, _sample)
        except Exception as exc:
            _LOGGER.debug("[ArrivalBaseline] sample scheduling failed for %s: %s", entity_id, exc)

    def _silent_learning_expected_state(self, entity_id: str, state: str) -> str:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        value = str(state or "").strip().lower()
        if domain in {"light", "switch", "fan", "input_boolean"}:
            return value if value in {"on", "off"} else ""
        if domain == "cover":
            if value in {"open", "opening"}:
                return "open"
            if value in {"closed", "closing"}:
                return "closed"
            return ""
        if domain == "media_player":
            if value == "playing":
                return "on"
            if value in {"off", "idle", "paused", "standby"}:
                return "off"
        return ""

    @staticmethod
    def _silent_learning_truthy(value: Any, default: bool = True) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return value != 0
        text = str(value).strip().lower()
        if text in {"0", "false", "no", "n", "off", "disabled"}:
            return False
        if text in {"1", "true", "yes", "y", "on", "enabled"}:
            return True
        return default

    @staticmethod
    def _silent_learning_clean_states(value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            return (value.strip().lower(),) if value.strip() else ()
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item).strip().lower() for item in value if str(item).strip())
        return ()

    @staticmethod
    def _silent_learning_range(value: Any) -> tuple[float, float] | None:
        if isinstance(value, str):
            parts = [part.strip() for part in value.replace("..", "-").split("-") if part.strip()]
        elif isinstance(value, (list, tuple)):
            parts = list(value[:2])
        else:
            parts = []
        if len(parts) < 2:
            return None
        try:
            return (float(parts[0]), float(parts[1]))
        except (TypeError, ValueError):
            return None

    def _silent_learning_default_behavior_dims(self, entity_id: str) -> list[dict[str, Any]]:
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain == "light":
            return [
                {"key": "power", "kind": "discrete", "states": ("on", "off"), "active_when": "on"},
                {"key": "brightness", "kind": "position", "range": (0, 100), "unit": "percent"},
            ]
        if domain in {"switch", "input_boolean"}:
            return [{"key": "power", "kind": "discrete", "states": ("on", "off"), "active_when": "on"}]
        if domain == "fan":
            return [
                {"key": "power", "kind": "discrete", "states": ("on", "off"), "active_when": "on"},
                {"key": "speed", "kind": "enum", "states": ("low", "medium", "high")},
            ]
        if domain == "cover":
            return [
                {"key": "power", "kind": "discrete", "states": ("open", "closed"), "active_when": "open"},
                {"key": "position", "kind": "position", "range": (0, 100), "unit": "percent"},
            ]
        if domain == "climate":
            return [
                {"key": "hvac_mode", "kind": "enum", "states": ("cool", "heat", "auto", "off"), "active_when": "cool"},
                {"key": "target_temp", "kind": "continuous", "range": (16, 30), "unit": "c"},
            ]
        if domain == "media_player":
            return [{"key": "power", "kind": "discrete", "states": ("on", "off"), "active_when": "on"}]
        return []

    def _silent_learning_behavior_dims(self, entity_id: str, info: dict[str, Any]) -> list[dict[str, Any]]:
        if not self._silent_learning_truthy(info.get("learnable"), True):
            return []
        raw_dims = info.get("behavior_dims") or info.get("behavior_dimensions")
        dims: list[dict[str, Any]] = []
        if isinstance(raw_dims, (list, tuple)):
            for raw_dim in raw_dims:
                if not isinstance(raw_dim, dict):
                    continue
                key = str(raw_dim.get("key") or raw_dim.get("name") or "").strip().lower()
                kind = str(raw_dim.get("kind") or raw_dim.get("type") or "").strip().lower()
                if not key or not kind:
                    continue
                dim = {"key": key, "kind": kind}
                states = self._silent_learning_clean_states(raw_dim.get("states") or raw_dim.get("values"))
                if states:
                    dim["states"] = states
                value_range = self._silent_learning_range(raw_dim.get("range") or raw_dim.get("value_range"))
                if value_range is not None:
                    dim["range"] = value_range
                unit = str(raw_dim.get("unit") or "").strip()
                if unit:
                    dim["unit"] = unit
                dims.append(dim)
        return dims or self._silent_learning_default_behavior_dims(entity_id)

    @staticmethod
    def _silent_learning_attributes(state_obj: Any) -> dict[str, Any]:
        attrs = getattr(state_obj, "attributes", None)
        return dict(attrs) if isinstance(attrs, dict) else {}

    @staticmethod
    def _silent_learning_number_text(value: float) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:g}"

    def _silent_learning_numeric_value(
        self,
        entity_id: str,
        dim_key: str,
        attrs: dict[str, Any],
    ) -> str:
        candidates_by_key = {
            "brightness": ("brightness_pct", "brightness"),
            "position": ("current_position", "position", "current_cover_position"),
            "target_temp": ("target_temp", "target_temperature", "temperature"),
        }
        candidates = candidates_by_key.get(dim_key, (dim_key,))
        raw_value: Any = None
        raw_key = ""
        for key in candidates:
            if key in attrs and attrs.get(key) is not None:
                raw_key = key
                raw_value = attrs.get(key)
                break
        if raw_value is None:
            return ""
        try:
            number = float(raw_value)
        except (TypeError, ValueError):
            return ""
        if dim_key == "brightness" and raw_key == "brightness":
            number = round(max(0.0, min(255.0, number)) * 100 / 255)
        return self._silent_learning_number_text(number)

    def _silent_learning_dimension_value(
        self,
        entity_id: str,
        state: str,
        state_obj: Any,
        dim: dict[str, Any],
    ) -> str:
        dim_key = str(dim.get("key") or "").strip().lower()
        kind = str(dim.get("kind") or "").strip().lower()
        raw_state = str(state or "").strip().lower()
        attrs = self._silent_learning_attributes(state_obj)
        if kind in {"position", "continuous"}:
            value = self._silent_learning_numeric_value(entity_id, dim_key, attrs)
            if not value:
                return ""
            value_range = dim.get("range")
            if isinstance(value_range, tuple) and len(value_range) >= 2:
                try:
                    numeric = float(value)
                    if numeric < float(value_range[0]) or numeric > float(value_range[1]):
                        return ""
                except (TypeError, ValueError):
                    return ""
            return value

        if dim_key == "power":
            value = self._silent_learning_expected_state(entity_id, raw_state)
        else:
            raw_value = attrs.get(dim_key)
            value = str(raw_value if raw_value is not None else raw_state).strip().lower()
        states = self._silent_learning_clean_states(dim.get("states"))
        if states and value not in states:
            return ""
        return value

    @staticmethod
    def _silent_learning_season(now: datetime) -> str:
        month = int(now.month)
        if month in {12, 1, 2}:
            return "winter"
        if month in {3, 4, 5}:
            return "spring"
        if month in {6, 7, 8}:
            return "summer"
        return "autumn"

    def _silent_learning_source_allowed(self, source_type: str) -> bool:
        normalized = str(source_type or "").strip().lower()
        if not normalized:
            return True
        blocked_tokens = ("自动化", "脚本", "automation", "script")
        return not any(token in normalized for token in blocked_tokens)

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
        if not self._silent_learning_source_allowed(source_type):
            self._sys_log("INFO", f"[SilentLearning] behavior sample skipped for automation/script source: {entity_id}")
            return
        old_value = str(old_state or "").strip().lower()
        new_value = str(new_state or "").strip().lower()
        if not new_value:
            return
        device_info = getattr(self, "device_info", {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        info = device_info.get(entity_id) if isinstance(device_info, dict) else {}
        if not isinstance(info, dict):
            info = {}
        dims = self._silent_learning_behavior_dims(entity_id, info)
        if not dims:
            return
        room = str(info.get("room") or info.get("area") or "").strip()
        if not room:
            area_getter = getattr(self, "_get_entity_area", None)
            if callable(area_getter):
                try:
                    room = str(area_getter(entity_id) or "").strip()
                except Exception:
                    room = ""
        now = datetime.now()
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue):
            return
        recorded: list[str] = []
        season_sensitive = self._silent_learning_truthy(info.get("season_sensitive"), False)
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        for dim in dims:
            dim_key = str(dim.get("key") or "").strip().lower()
            if not dim_key:
                continue
            expected_value = self._silent_learning_dimension_value(entity_id, new_value, new_state_obj, dim)
            if not expected_value:
                continue
            previous_value = self._silent_learning_dimension_value(entity_id, old_value, old_state_obj, dim)
            if previous_value and previous_value == expected_value:
                continue
            season = self._silent_learning_season(now) if season_sensitive or str(dim.get("kind") or "") == "continuous" else ""
            payload = {
                "action": "upsert",
                "entity_id": entity_id,
                "expected_state": expected_value,
                "dim_key": dim_key,
                "expected_value": expected_value,
                "season": season,
                "room": room,
                "hour_start": (now.hour - 1) % 24,
                "hour_end": (now.hour + 1) % 24,
                "weekday_mask": str(now.strftime("%w")),
                "confidence": 62,
                "hit_count": 1,
                "lifecycle_state": "active",
                "source": "silent_learning",
                "source_type": str(source_type or ""),
            }
            if enqueue("behavior", payload, ts=ts):
                recorded.append(f"{dim_key}={expected_value}")
        if recorded:
            self._sys_log("INFO", f"[SilentLearning] behavior sample recorded: {entity_id} -> {', '.join(recorded)}")

    def _emit_addon_fast_path_event(self, payload: dict[str, Any]) -> None:
        try:
            self.hass.bus.async_fire("smart_agent_decision_bubble", payload)
        except Exception as exc:
            _LOGGER.debug("[Listeners] smart_agent_decision_bubble emit failed: %s", exc)

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
        addon_client = getattr(self, "_addon_client", None)
        snapshot = self._build_addon_fast_path_snapshot(entity_id)
        snapshot_diag = self._addon_fast_path_snapshot_diagnostics(snapshot, entity_id)
        self._sys_log(
            "INFO",
            "[Add-on FastPath] request "
            f"entity={entity_id} old={old_state} new={new_state} "
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
                )
            except Exception as exc:
                response = None
                _LOGGER.debug("[Listeners] add-on fast-path decision failed: %s", exc)
                self._sys_log(
                    "ERROR",
                    f"[Add-on FastPath] addon_unreachable fail-closed | entity={entity_id} "
                    f"reason=exception exception_type={type(exc).__name__}",
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
                    details = response.get("details") if isinstance(response.get("details"), dict) else {}
                    path_taken = str(response.get("path_taken") or details.get("path_taken") or "none")
                    reason = str(response.get("reason") or details.get("reason") or response.get("error") or "")
                    confirm_required = response.get("confirm_required") is True or details.get("confirm_required") is True
                    confirm_suppressed_reason = str(details.get("confirm_suppressed_reason") or "")
                    addon_learning_mode = details.get("learning_mode")
                    addon_habit_proactive = details.get("habit_proactive")
                    execution_suppressed_reason = (
                        "learning_mode" if matched and addon_learning_mode is True else ""
                    )
                    if confirm_required and confirm_suppressed_reason:
                        confirm_required = False
                    confidence_auto = details.get("confidence_auto")
                    confidence_notify = details.get("confidence_notify")
                    scene = ""
                    confidence = details.get("confidence")
                    action_count = 0
                    actions: list[Any] = []
                    transaction_id = ""
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
                        transaction_id = str(result.get("transaction_id") or result.get("txn_id") or "")
                    audit_pending = bool(matched and self._fast_path_result_allows_slow_audit(actions))
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
                        f"action_count={action_count} entity={entity_id}",
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
                            "confirm_required": confirm_required,
                            "confirm_suppressed_reason": confirm_suppressed_reason,
                            "action_count": action_count,
                            "actions": actions,
                            "transaction_id": transaction_id,
                            "executed": matched and not execution_suppressed_reason,
                            "provisional_execution": audit_pending,
                            "audit_pending": audit_pending,
                            "rollback_allowed": audit_pending,
                            "execution_suppressed_reason": execution_suppressed_reason,
                            "fail_closed": not (200 <= status < 300),
                            "snapshot": snapshot_diag,
                        }
                    )
                    if 200 <= status < 300 and not matched and confirm_required and isinstance(result, dict):
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
                                f"[Add-on FastPath] execution suppressed | entity={entity_id} policy=learning_mode reason={execution_suppressed_reason}",
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
                            await self._execute_fast_path_decision_result(
                                result,
                                entity_id=entity_id,
                                source_label="AddonFastPath",
                            )
                        finally:
                            self._batch_trigger_controllable = previous_batch_trigger_controllable
                        if audit_pending:
                            self._schedule_inference(
                                entity_id,
                                f"{entity_id}: {old_state} -> {new_state}",
                                new_state,
                                one_off_prompt=self._fast_path_slow_audit_prompt(),
                                _allow_learning_mode_inference=True,
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
                            )
                            return
                        if reason == "no_match":
                            if self._should_slow_infer_after_fast_path_no_match(entity_id, new_state):
                                self._sys_log(
                                    "INFO",
                                    f"[Add-on FastPath] no_match; scheduling slow inference | entity={entity_id} "
                                    f"active_space={snapshot_diag.get('active_space') or '-'}",
                                )
                                self._schedule_inference(
                                    entity_id,
                                    f"{entity_id}: {old_state} -> {new_state}",
                                    new_state,
                                )
                                return
                            info = self.device_info.get(entity_id, {}) if isinstance(getattr(self, "device_info", None), dict) else {}
                            if not isinstance(info, dict):
                                info = {}
                            self._sys_log(
                                "INFO",
                                f"[Add-on FastPath] no_match; slow inference not scheduled | "
                                f"reason=not_presence_arrival entity={entity_id} state={new_state} "
                                f"sensor_type={info.get('sensor_type') or '-'} name={info.get('name') or '-'}",
                            )
                        if reason == "confidence_below_auto_threshold" and not confirm_required:
                            if action_count > 0 or self._should_slow_infer_after_fast_path_no_match(entity_id, new_state):
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

            self._sys_log("INFO", f"[事件] {entity_id}: {old_s} → {new_s} (来源: {source_type})")
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
                        self._sys_log("INFO", f"[过滤] 传感器变化 {delta:.1f} < {threshold}，跳过: {entity_id}")
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

            if old_s in ("unavailable", "unknown") and new_s not in ("on", "open", "home", "playing"):
                self._sys_log(
                    "INFO",
                    f"[过滤] 设备从 {old_s} 恢复为非激活状态 {new_s}，跳过 add-on 快路: {entity_id}",
                )
                self._emit_listener_event(
                    listener_action="filtered",
                    entity_id=entity_id,
                    old_state=old_s,
                    new_state=new_s,
                    filter_reason="state_recovery_inactive",
                    source_type=source_type,
                )
                return

            last_ai_actions = getattr(self, "_last_ai_actions", {})
            last_ai = last_ai_actions.get(entity_id) if isinstance(last_ai_actions, dict) else None
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

            info = device_info_snapshot.get(entity_id) if isinstance(device_info_snapshot, dict) else {}
            sensor_type = str((info or {}).get("sensor_type") or "").strip().lower()
            eid_lower = entity_id.lower()
            name_lower = str((info or {}).get("name") or "").lower()
            is_presence_sensor = (
                domain == "binary_sensor"
                and (
                    sensor_type in {"pir", "mmwave", "presence", "occupancy", "motion", "frigate"}
                    or any(kw in eid_lower or kw in name_lower for kw in self._PRESENCE_KW)
                )
            )
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
            self.hass.async_create_task(
                self._run_addon_fast_path_fail_closed(
                    entity_id,
                    new_s,
                    old_s,
                )
            )
            return
        return _state_changed

    def _is_presence_listener_entity(self, entity_id: str, info: dict[str, Any] | None = None) -> bool:
        """Return True for managed entities that can represent human presence."""
        domain = str(entity_id or "").split(".", 1)[0]
        if domain != "binary_sensor":
            return False
        row = info if isinstance(info, dict) else {}
        sensor_type = str(row.get("sensor_type") or "").strip().lower()
        if sensor_type in {"pir", "mmwave", "presence", "occupancy", "motion", "frigate"}:
            return True
        eid_lower = str(entity_id or "").lower()
        name_lower = str(row.get("name") or "").lower()
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
                listener_action="state_reconciled",
                entity_id=entity_id,
                old_state="unknown",
                new_state=state,
                source_type="state_reconcile",
                reconcile_reason="listener_refresh_active_state",
            )
            self.hass.async_create_task(
                self._run_addon_fast_path_fail_closed(
                    entity_id,
                    state,
                    "unknown",
                )
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
        skipped = 0
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            mapped = self._device_info_row_from_addon_device(row)
            if mapped is None:
                skipped += 1
                continue
            entity_id, info = mapped
            next_device_info[entity_id] = info

        current = getattr(self, "device_info", {}) or {}
        if not isinstance(current, dict):
            current = {}
        changed = current != next_device_info
        if changed:
            self.device_info = next_device_info
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
                "skipped": skipped,
                "changed": changed,
            }
        )
        self._device_info_source = "addon_devices"
        self._last_addon_device_sync_status = status
        return changed

    def _device_info_row_from_addon_device(self, row: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
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
        return entity_id, {
            "name": str(name or entity_id),
            "room": str(room or ""),
            "type": str(dev_type or domain),
            "ops": ops,
            "control_mode": mode,
            "sensor_type": str(row.get("sensor_type") or ""),
            "ha_unique_id": str(row.get("ha_unique_id") or row.get("unique_id") or ""),
            "ha_device_id": str(row.get("ha_device_id") or row.get("device_id") or ""),
        }

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
            if isinstance(eid, str) and eid.split(".", 1)[0] in self._LISTENER_DOMAINS
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
        try:
            execute(
                "UPDATE devices SET ha_unique_id=?, ha_device_id=?, updated=? WHERE entity_id=?",
                (
                    str(info.get("ha_unique_id") or ""),
                    str(info.get("ha_device_id") or ""),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
