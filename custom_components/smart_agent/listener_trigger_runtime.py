"""Trigger admission, temporal recheck, and slow-inference queue runtime.

HA callback registration remains in ``ListenersMixin``. The mixin injects the
HA scheduler into the two scheduling entrypoints; this module owns no device
service call, command envelope, provider transport, or execution authority.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from .const import SOURCE_AUTOMATION, SOURCE_DASHBOARD, SOURCE_PHYSICAL, SOURCE_VOICE
from .presence_runtime import room_candidates, room_snapshot


_LOGGER = logging.getLogger(__name__)

def should_trigger(self, entity_id: str, old: str, new: str) -> bool:
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

def effective_cooldown(self) -> int:
    """展厅模式使用更短冷却以便快速响应演示。"""
    return self._SHOWROOM_COOLDOWN if self._mode == "showroom" else self.cooldown

def slow_inference_cooldown_key(self, entity_id: str, new_state: str) -> str:
    """避免同一存在传感器的到达和离开互相吞掉慢脑调度。"""
    if self._is_presence_arrival_for_slow_inference(entity_id, new_state):
        return f"{entity_id}:presence_arrival"
    if self._is_presence_departure_for_slow_inference(entity_id, new_state):
        return f"{entity_id}:presence_departure"
    return entity_id

def is_presence_flap_suppressed(self, entity_id: str) -> tuple[bool, int]:
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

def record_presence_flap(self, entity_id: str) -> None:
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

def cancel_presence_temporal_recheck(self, entity_id: str) -> None:
    timers = getattr(self, "_presence_off_timers", None)
    if not isinstance(timers, dict):
        return
    cancel = timers.pop(entity_id, None)
    if callable(cancel):
        try:
            cancel()
        except Exception as exc:
            _LOGGER.debug("[PresenceTemporal] cancel recheck failed for %s: %s", entity_id, exc)

def presence_temporal_recheck_delay(presence: dict[str, Any]) -> float | None:
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

def schedule_presence_temporal_recheck(
    self,
    entity_id: str,
    *,
    old_state: str,
    new_state: str,
    presence: dict[str, Any] | None,
    schedule: Any = async_call_later,
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
        timers[entity_id] = schedule(self.hass, delay, _recheck)
    except Exception as exc:
        timers.pop(entity_id, None)
        _LOGGER.debug("[PresenceTemporal] schedule recheck failed for %s: %s", entity_id, exc)

def build_presence_snapshot_for_entity(
    self,
    entity_id: str,
    *,
    blocked_actions: list[str] | None = None,
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Build a compatibility Presence Snapshot without local HA inference."""
    candidates = room_candidates(self.device_info.get(entity_id, {}) or {})
    room = candidates[0] if candidates else ""
    snapshot_fn = getattr(self, "get_presence_snapshot", None)
    if callable(snapshot_fn) and room:
        try:
            root_snapshot = snapshot_fn()
        except Exception as exc:
            _LOGGER.debug("[Listeners] get_presence_snapshot failed: %s", exc)
            root_snapshot = None
        rooms = root_snapshot.get("rooms") if isinstance(root_snapshot, dict) else None
        selected_snapshot = room_snapshot(rooms, candidates)
        if isinstance(selected_snapshot, dict):
            snap = dict(selected_snapshot)
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

def is_presence_interaction_active(self, domain: str, state: str) -> bool:
    normalized = str(state or "").strip().lower()
    if domain == "light":
        return normalized == "on"
    if domain == "media_player":
        return normalized in {"on", "playing", "paused"}
    if domain == "climate":
        return normalized not in {"", "off", "unavailable", "unknown"}
    return False

def presence_interaction_source(self, entity_id: str, source_type: str) -> str:
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

def record_presence_interaction_trace(
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

def schedule_inference(
    self,
    entity_id: str,
    trigger: str,
    new_state: str = "",
    one_off_prompt: str = "",
    *,
    _policy_synced: bool = False,
    _allow_learning_mode_inference: bool = False,
    source_trace_context: dict[str, Any] | None = None,
    causal_event: dict[str, Any] | None = None,
    schedule: Any = async_call_later,
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
                causal_event=causal_event,
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
        if isinstance(causal_event, dict) and causal_event:
            pending_trigger["causal_event"] = dict(causal_event)
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
        self._merge_timer_unsub = schedule(self.hass, window, self._flush_triggers)

async def schedule_inference_after_addon_policy_sync(
    self,
    entity_id: str,
    trigger: str,
    new_state: str = "",
    one_off_prompt: str = "",
    *,
    _allow_learning_mode_inference: bool = False,
    source_trace_context: dict[str, Any] | None = None,
    causal_event: dict[str, Any] | None = None,
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
        causal_event=causal_event,
    )

def emit_slow_inference_task_failure(
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

def handle_slow_inference_task_done(self, task: Any, *, trigger: str, entity_id: str) -> None:
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

def spawn_slow_inference_task(self, coro: Any, *, trigger: str, entity_id: str) -> None:
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

def flush_triggers(self, _: datetime) -> None:
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
            "causal_events": [
                dict(item["causal_event"])
                for item in mergeable_triggers
                if isinstance(item.get("causal_event"), dict)
                and item.get("causal_event")
            ],
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
                    "causal_events": (
                        [dict(item["causal_event"])]
                        if isinstance(item.get("causal_event"), dict)
                        and item.get("causal_event")
                        else []
                    ),
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
            decision_kwargs: dict[str, Any] = {
                "one_off_prompt": str(batch["one_off_prompt"]),
                "source_trace_context": batch["source_trace_context"],
            }
            if batch.get("causal_events"):
                decision_kwargs["causal_events"] = list(batch["causal_events"])
            self._spawn_slow_inference_task(
                self._run_addon_decision(
                    trigger_text,
                    **decision_kwargs,
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


__all__ = [
    "should_trigger",
    "effective_cooldown",
    "slow_inference_cooldown_key",
    "is_presence_flap_suppressed",
    "record_presence_flap",
    "cancel_presence_temporal_recheck",
    "presence_temporal_recheck_delay",
    "schedule_presence_temporal_recheck",
    "build_presence_snapshot_for_entity",
    "is_presence_interaction_active",
    "presence_interaction_source",
    "record_presence_interaction_trace",
    "schedule_inference",
    "schedule_inference_after_addon_policy_sync",
    "emit_slow_inference_task_failure",
    "handle_slow_inference_task_done",
    "spawn_slow_inference_task",
    "flush_triggers",
]
