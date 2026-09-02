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

from .action_normalization import action_requires_presence_refresh
from .arrival_lighting_learning import arrival_lighting_entity_ids
from .ha_adapter import async_call_service
from .active_ai_rollout import (
    ActiveAiRolloutConfig,
    enrich_active_ai_action_spaces,
    evaluate_active_ai_execution_gate,
    scope_active_ai_canary_actions,
)
from .fast_path_listener import run_addon_fast_path_fail_closed
from .listener_trigger_projection import (
    compact_listener_triggers,
    format_listener_state,
    format_listener_trigger,
    listener_trigger_public_summary,
)
from .listener_trigger_runtime import (
    build_presence_snapshot_for_entity,
    cancel_presence_temporal_recheck,
    effective_cooldown,
    emit_slow_inference_task_failure,
    flush_triggers,
    handle_slow_inference_task_done,
    is_presence_flap_suppressed,
    is_presence_interaction_active,
    presence_interaction_source,
    presence_temporal_recheck_delay,
    record_presence_flap,
    record_presence_interaction_trace,
    schedule_inference,
    schedule_inference_after_addon_policy_sync,
    schedule_presence_temporal_recheck,
    should_trigger,
    slow_inference_cooldown_key,
    spawn_slow_inference_task,
)
from .listener_state_runtime import handle_listener_state_changed
from .listener_registry_runtime import (
    async_refresh_device_info_from_addon_devices,
    device_info_row_from_addon_device,
    get_live_presence_occupancy_map,
    is_actionable_sensor_runtime_entity,
    is_listener_runtime_entity,
    is_presence_listener_entity,
    listener_entity_metadata,
    managed_device_info_row_from_addon_device,
    managed_listener_entity_ids,
    persist_device_entity_id_migration,
    persist_device_registry_metadata,
    persist_ha_registry_metadata,
    reconcile_active_listener_states,
    reconcile_device_info_entity_ids_from_ha_registry,
    refresh_listeners_if_entity_set_changed,
)
from .presence_runtime import DEFAULT_COLD_START_RECHECK_SECONDS, advance_occupancy_cycle, async_restore_occupancy_cycles, cleanup_startup_reconciliation, learning_space_identity, occupancy_cycle_outcome, persist_occupancy_cycles, resolve_space_id, room_candidates, room_snapshot, schedule_arrival_baseline_sample, schedule_startup_presence_reconciliation
from .sensor_event_filter import EnvironmentTelemetryFilter, environment_sensor_kind
from .service_contracts import DISCOVERY_DOMAINS, STATEFUL_EXECUTION_DOMAINS
from .const import (
    FRIGATE_PERSON_COUNT_KW as _FRIGATE_PERSON_COUNT_KW,
    AI_ACTION_SKIP_WINDOW, URGENT_MERGE_WINDOW, NORMAL_MERGE_WINDOW,
    GLITCH_THRESHOLD, GLITCH_WINDOW, GLITCH_SUPPRESS_SECS,
    PRESENCE_OFF_DELAY, PRESENCE_ON_COOLDOWN, PRESENCE_ON_MIN_HOLD,
    PRESENCE_FLAP_WINDOW, PRESENCE_FLAP_THRESHOLD, PRESENCE_FLAP_SUPPRESS_SECS,
    CORRECTION_WINDOW_SECONDS,
    FRIGATE_COUNT_ON_HOLD, FRIGATE_COUNT_CHANGE_HOLD,
    FRIGATE_COUNT_OFF_HOLD, FRIGATE_COUNT_COOLDOWN,
    SENSOR_DEADBAND_PCT,
    SOURCE_AUTOMATION, SOURCE_DASHBOARD, SOURCE_PHYSICAL, SOURCE_VOICE,
    DEVICE_CONTROL_MODES,
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
    _ARRIVAL_LEARNING_LOOKBACK_SECONDS = 30.0
    # Arrival evidence is sampled after a short stable-presence window. The
    # separate 30-second product setting is reserved for departure debounce.
    _ARRIVAL_LEARNING_WINDOW_SECONDS = 5.0
    _ARRIVAL_MANUAL_EVIDENCE_RETENTION_SECONDS = 120.0
    _MANUAL_SERVICE_CONTEXT_RETENTION_SECONDS = 15 * 60.0
    _MANUAL_SCENE_SESSION_IDLE_SECONDS = 90.0
    _ARRIVAL_ACTIVE_STATES = frozenset(
        {"on", "open", "home", "playing", "occupied", "present"}
    )

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
    _ACTIONABLE_CONTACT_SENSOR_TYPES = frozenset({"door", "window", "contact", "opening", "garage_door"})
    _ACTIONABLE_CONTACT_KW = ("door", "window", "contact", "opening", "men_chuang", "garage", "门", "窗", "门窗")
    _PRESENCE_OFF_DELAY = PRESENCE_OFF_DELAY
    _PRESENCE_ON_COOLDOWN = PRESENCE_ON_COOLDOWN
    _PRESENCE_ON_MIN_HOLD = PRESENCE_ON_MIN_HOLD
    _PRESENCE_FLAP_WINDOW = PRESENCE_FLAP_WINDOW
    _PRESENCE_FLAP_THRESHOLD = PRESENCE_FLAP_THRESHOLD
    _PRESENCE_FLAP_SUPPRESS_SECS = PRESENCE_FLAP_SUPPRESS_SECS
    _CORRECTION_WINDOW_SECONDS = CORRECTION_WINDOW_SECONDS
    _STARTUP_PRESENCE_RECONCILE_HOLD_SECONDS = DEFAULT_COLD_START_RECHECK_SECONDS

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
    _LISTENER_DOMAINS = DISCOVERY_DOMAINS | frozenset({"person"})
    _CONTROL_EVENT_DOMAINS = STATEFUL_EXECUTION_DOMAINS

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

    _should_trigger = should_trigger
    _effective_cooldown = effective_cooldown
    _slow_inference_cooldown_key = slow_inference_cooldown_key
    _is_presence_flap_suppressed = is_presence_flap_suppressed
    _record_presence_flap = record_presence_flap
    _cancel_presence_temporal_recheck = cancel_presence_temporal_recheck
    _presence_temporal_recheck_delay = staticmethod(presence_temporal_recheck_delay)

    def _schedule_presence_temporal_recheck(
        self,
        entity_id: str,
        *,
        old_state: str,
        new_state: str,
        presence: dict[str, Any] | None,
    ) -> None:
        schedule_presence_temporal_recheck(
            self,
            entity_id,
            old_state=old_state,
            new_state=new_state,
            presence=presence,
            schedule=async_call_later,
        )

    _build_presence_snapshot_for_entity = build_presence_snapshot_for_entity
    _is_presence_interaction_active = is_presence_interaction_active
    _presence_interaction_source = presence_interaction_source
    _record_presence_interaction_trace = record_presence_interaction_trace

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
        causal_event: dict[str, Any] | None = None,
    ) -> None:
        schedule_inference(
            self,
            entity_id,
            trigger,
            new_state,
            one_off_prompt,
            _policy_synced=_policy_synced,
            _allow_learning_mode_inference=_allow_learning_mode_inference,
            source_trace_context=source_trace_context,
            causal_event=causal_event,
            schedule=async_call_later,
        )

    _schedule_inference_after_addon_policy_sync = schedule_inference_after_addon_policy_sync
    _emit_slow_inference_task_failure = emit_slow_inference_task_failure
    _handle_slow_inference_task_done = handle_slow_inference_task_done
    _spawn_slow_inference_task = spawn_slow_inference_task

    @callback
    def _flush_triggers(self, now: datetime) -> None:
        flush_triggers(self, now)

    def _fmt_state(self, domain: str, entity_id: str, state: str) -> str:
        """根据设备类型返回语义准确的状态文字。"""
        return format_listener_state(self, domain, entity_id, state)

    def _fmt_trigger(self, source: str, domain: str, name: str,
                     entity_id: str, old_s: str, new_s: str) -> str:
        """生成简洁的触发文本，供 AI Prompt 和日志使用。
        
        保留 entity_id 让 AI 可精确识别设备，状态按设备类型语义化翻译。
        """
        return format_listener_trigger(
            self,
            source,
            domain,
            name,
            entity_id,
            old_s,
            new_s,
        )

    def _trigger_public_summary(
        self,
        trigger: Any,
        *,
        entity_id: str = "",
        old_state: str = "",
        new_state: str = "",
    ) -> str:
        """Return a log-safe trigger summary without friendly names or raw text."""
        return listener_trigger_public_summary(
            trigger,
            entity_id=entity_id,
            old_state=old_state,
            new_state=new_state,
        )

    # ── 触发合并压缩 ──────────────────────────────────────────────────────────

    def _compact_merged_trigger(self, texts: list[str]) -> str:
        """将多条触发消息压缩为简洁的合并描述，节省字符，同时保留 AI 决策所需信息。

        优化策略：
        1. 相同变化方向（off→on / on→off）且同域的设备归为一组，仅列设备名
        2. 不同类型/方向的设备各自独立一行
        3. 整体长度控制在 200 字以内
        """
        return compact_listener_triggers(self, texts)

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

    def _is_inflight_smartagent_state_feedback(
        self, entity_id: str, state: str
    ) -> bool:
        """Return whether this state is feedback from a running SA command."""
        registry = getattr(self, "_inflight_smartagent_state_feedback", None)
        if not isinstance(registry, dict):
            return False
        request_ids = registry.get(
            (
                str(entity_id or "").strip(),
                str(state or "").strip().lower(),
            )
        )
        return isinstance(request_ids, set) and bool(request_ids)

    def _record_implicit_reverse_correction(
        self,
        *,
        entity_id: str,
        domain: str,
        old_state: str,
        new_state: str,
        new_state_obj: Any,
        source_type: str,
        device_info: dict[str, Any],
    ) -> bool:
        """Record a direct manual reversal of a recent successful AI lighting action."""
        capability = str(device_info.get("capability") or "").strip().lower()
        if domain != "light" and not (domain == "switch" and capability == "lighting"):
            return False

        context = getattr(new_state_obj, "context", None)
        if context is not None and getattr(context, "parent_id", None):
            return False

        last_ai_actions = getattr(self, "_last_ai_actions", {})
        last_ai = last_ai_actions.get(entity_id) if isinstance(last_ai_actions, dict) else None
        if not isinstance(last_ai, dict):
            return False

        ai_state = str(last_ai.get("state") or "").strip().lower()
        old_value = str(old_state or "").strip().lower()
        user_state = str(new_state or "").strip().lower()
        opposite = {"on": "off", "off": "on"}.get(ai_state)
        if not opposite or old_value != ai_state or user_state != opposite:
            return False

        ai_service = str(last_ai.get("service") or "").strip().lower()
        expected_service = f"{domain}.turn_{ai_state}"
        if ai_service != expected_service:
            return False
        try:
            age = time.time() - float(last_ai.get("time") or 0)
        except (TypeError, ValueError):
            return False
        if age < 0 or age > self._CORRECTION_WINDOW_SECONDS:
            return False

        room = str(device_info.get("space_id") or device_info.get("room") or "").strip()
        presence_context = "occupied" if ai_state == "on" else "vacant"
        transaction_id = str(last_ai.get("transaction_id") or "").strip()
        parent_transaction_id = str(last_ai.get("parent_transaction_id") or "").strip()
        context_user_id = str(getattr(context, "user_id", None) or "").strip()
        actor = f"ha_user:{context_user_id}" if context_user_id else "ha_user:physical_control"
        payload: dict[str, Any] = {
            "action": "record",
            "outcome": "rejected",
            "entity_id": entity_id,
            "ai_service": ai_service,
            "ai_state": ai_state,
            "user_state": user_state,
            "user_service": f"{domain}.turn_{user_state}",
            "room": room,
            "room_aliases": room_candidates(device_info),
            "scene_desc": str(last_ai.get("scene") or ""),
            "trigger_text": str(last_ai.get("trigger") or ""),
            "presence_context": presence_context,
            "context": "implicit_reverse_after_ai",
            "reason": "用户在 AI 操作后直接反向操作设备",
            "correction_source": "implicit_reverse_after_ai",
            "source_type": source_type,
            "ai_action_age_seconds": round(age, 3),
            "origin": "user_correction",
            "actor": actor,
            "decision_id": str(last_ai.get("decision_id") or transaction_id or "unknown"),
            "transaction_id": transaction_id or "unknown",
            "world_snapshot_id": str(last_ai.get("world_snapshot_id") or "unknown"),
        }
        execution_transaction_id = str(last_ai.get("execution_transaction_id") or "").strip()
        if execution_transaction_id:
            payload["execution_transaction_id"] = execution_transaction_id
        if parent_transaction_id:
            payload["parent_transaction_id"] = parent_transaction_id

        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue) or not enqueue("correction", payload):
            _LOGGER.warning("[Correction] implicit correction enqueue failed: %s", entity_id)
            return False

        suppressions = self._snapshot_correction_suppressions()
        suppression_key = (entity_id, ai_service.rsplit(".", 1)[-1], room, presence_context)
        updated_suppressions: list[dict[str, Any]] = []
        matched_suppression = False
        for row in suppressions:
            row_key = (
                row.get("entity_id"),
                row.get("service"),
                row.get("room"),
                row.get("presence"),
            )
            if row_key != suppression_key:
                updated_suppressions.append(row)
                continue
            matched_suppression = True
            updated_suppressions.append(
                {
                    **row,
                    "suppress": True,
                    "count": int(row.get("count") or 0) + 1,
                    "score": 1.0,
                }
            )
        if not matched_suppression:
            updated_suppressions.insert(
                0,
                {
                    "entity_id": entity_id,
                    "service": ai_service.rsplit(".", 1)[-1],
                    "room": room,
                    "presence": presence_context,
                    "suppress": True,
                    "count": 1,
                    "score": 1.0,
                },
            )
        self._correction_suppressions_cache = updated_suppressions
        self._correction_suppressions_cache_refresh_at = (
            time.time() + self._CORRECTION_SUPPRESSIONS_CACHE_TTL
        )
        user_overrides = getattr(self, "_user_overrides", None)
        user_overrides_lock = getattr(self, "_user_overrides_lock", None)
        if isinstance(user_overrides, dict) and user_overrides_lock is not None:
            with user_overrides_lock:
                user_overrides[entity_id] = {
                    "time": time.time(),
                    "state": user_state,
                    "source": "implicit_reverse_correction",
                }
        last_ai_actions.pop(entity_id, None)
        self._sys_log(
            "WARN",
            f"[纠错学习] 已记录人工反向操作: {entity_id} "
            f"{ai_state}->{user_state}（AI 操作后 {int(age)}s）",
        )
        return True

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

    def _build_addon_fast_path_snapshot(
        self,
        entity_id: str,
        *,
        include_environment_devices: bool = False,
    ) -> dict[str, Any]:
        """Build the plain snapshot consumed by add-on Core fast-path decisions."""
        raw_device_info = getattr(self, "device_info", {}) or {}
        environment_device_info = (
            getattr(self, "_environment_context_device_info", {}) or {}
        )
        include_environment_devices = bool(include_environment_devices) or (
            isinstance(environment_device_info, dict)
            and str(entity_id or "") in environment_device_info
        )
        if (
            include_environment_devices
            and isinstance(raw_device_info, dict)
            and isinstance(environment_device_info, dict)
        ):
            raw_device_info = {
                **raw_device_info,
                **environment_device_info,
            }
        device_info: dict[str, dict[str, Any]] = {}
        if isinstance(raw_device_info, dict):
            for snapshot_entity_id, raw_info in raw_device_info.items():
                projected_info = dict(raw_info) if isinstance(raw_info, dict) else {}
                # The server-issued sampling contract is consumed only by the HA
                # collection gate.  It is not machine evidence and must not be
                # echoed back into the decision snapshot/model input.
                projected_info.pop("signal_sampling_contract", None)
                device_info[str(snapshot_entity_id)] = projected_info
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
                observation = {
                    "state": state_value,
                    "quality": (
                        "invalid"
                        if state_value.strip().lower() in {"", "unknown", "unavailable"}
                        else "good"
                    ),
                }
                for timestamp_key in ("last_changed", "last_updated"):
                    timestamp = getattr(state, timestamp_key, None)
                    if timestamp in (None, ""):
                        continue
                    isoformat = getattr(timestamp, "isoformat", None)
                    observation[timestamp_key] = (
                        str(isoformat()) if callable(isoformat) else str(timestamp)
                    )
                observed_at_value = str(
                    observation.get("last_updated")
                    or observation.get("last_changed")
                    or ""
                ).strip()
                if observed_at_value:
                    observation["observed_at"] = observed_at_value
                    observation["source_event_id"] = f"ha_state:{eid}:{observed_at_value}"
                state_observations[eid] = observation
                attributes = getattr(state, "attributes", None)
                if isinstance(attributes, dict):
                    device_class = str(attributes.get("device_class") or "").strip().lower()
                    if device_class and not device_info[eid].get("device_class"):
                        device_info[eid]["device_class"] = device_class
                    unit = str(attributes.get("unit_of_measurement") or "").strip()
                    if unit and not device_info[eid].get("unit_of_measurement"):
                        device_info[eid]["unit_of_measurement"] = unit

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

        presence_getter = getattr(self, "get_presence_snapshot", None)
        if callable(presence_getter):
            try:
                presence_snapshot = presence_getter()
            except Exception as exc:
                _LOGGER.debug("[Listeners] get_presence_snapshot failed for add-on snapshot: %s", exc)
                presence_snapshot = None
            if isinstance(presence_snapshot, dict):
                snapshot["presence_snapshot"] = presence_snapshot

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
                priority_guards = priority_getter(include_lineage=True)
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
        decision_request = (
            result.get("decision_request")
            if isinstance(result.get("decision_request"), dict)
            else {}
        )
        plan_sketch = (
            result.get("plan_sketch")
            if isinstance(result.get("plan_sketch"), dict)
            else {}
        )
        policy_evaluation = (
            result.get("policy_evaluation")
            if isinstance(result.get("policy_evaluation"), dict)
            else {}
        )
        decision_event_claim_ids: list[str] = []
        causal_event_rows = decision_request.get("causal_events")
        if isinstance(causal_event_rows, list):
            for row in causal_event_rows:
                if not isinstance(row, dict):
                    continue
                claim_id = str(row.get("claim_id") or "").strip()
                if claim_id and claim_id not in decision_event_claim_ids:
                    decision_event_claim_ids.append(claim_id)
        decision_contract_lineage = {
            "decision_transaction_id": str(transaction_id or "").strip(),
            "decision_request_id": str(
                decision_request.get("request_id") or ""
            ).strip(),
            "plan_fingerprint": str(
                plan_sketch.get("semantic_fingerprint") or ""
            ).strip(),
            "policy_evaluation_id": str(
                policy_evaluation.get("evaluation_id") or ""
            ).strip(),
            "policy_evaluation_digest": str(
                policy_evaluation.get("evaluation_digest") or ""
            ).strip(),
            "policy_aggregate_decision": str(
                policy_evaluation.get("aggregate_decision") or ""
            ).strip().lower(),
            "decision_event_claim_ids": decision_event_claim_ids,
            "occupancy_cycle_id": str(
                result.get("occupancy_cycle_id")
                or (
                    decision_trace.get("context_snapshot", {}).get("occupancy_cycle_id")
                    if isinstance(decision_trace, dict)
                    and isinstance(decision_trace.get("context_snapshot"), dict)
                    else ""
                )
                or ""
            ).strip(),
        }
        decision_contract_lineage = {
            key: value
            for key, value in decision_contract_lineage.items()
            if value
        }
        nested_result = (
            result.get("result")
            if isinstance(result.get("result"), dict)
            else {}
        )
        daylight_evidence = (
            result.get("daylight_evidence")
            if isinstance(result.get("daylight_evidence"), dict)
            else nested_result.get("daylight_evidence")
            if isinstance(nested_result.get("daylight_evidence"), dict)
            else {}
        )
        if daylight_evidence:
            decision_contract_lineage["daylight_evidence"] = dict(
                daylight_evidence
            )
            decision_contract_lineage["policy_evaluation"] = dict(
                policy_evaluation
            )
            bound_snapshot_id = str(world_snapshot_id or "").strip()
            if bound_snapshot_id:
                decision_contract_lineage["world_snapshot_id"] = (
                    bound_snapshot_id
                )
            bound_decision_time = str(
                result.get("decision_time")
                or nested_result.get("decision_time")
                or ""
            ).strip()
            if bound_decision_time:
                decision_contract_lineage["decision_time"] = (
                    bound_decision_time
                )
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
        if not valid_actions:
            selection_confirmation = result.get("selection_confirmation")
            pending_selection = (
                isinstance(selection_confirmation, dict)
                and selection_confirmation.get("required") is True
            )
            return self._enqueue_fast_path_execution_audit(
                transaction_id=transaction_id,
                correlation_id=correlation_id,
                world_snapshot_id=world_snapshot_id,
                decision_trace=decision_trace,
                trigger=trigger or f"{entity_id}: state_changed",
                scene=str(scene),
                confidence=confidence,
                actions=[],
                candidate_actions=[],
                execution_result=0,
                execution_suppressed_reason=(
                    "pending_selection_confirmation"
                    if pending_selection
                    else "no_actions"
                ),
                decision_contract_lineage=decision_contract_lineage,
            )
        candidate_actions = (
            result.get("rollout_original_actions")
            if isinstance(result.get("rollout_original_actions"), list)
            else valid_actions
        )
        candidate_actions = [
            dict(item) for item in candidate_actions if isinstance(item, dict)
        ]
        rollout_actions = enrich_active_ai_action_spaces(
            candidate_actions,
            device_info,
        )
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
        rollout_config = ActiveAiRolloutConfig.from_mapping(rollout_payload)
        scoped_actions = scope_active_ai_canary_actions(
            candidate_actions,
            rollout_config,
        )
        if not scoped_actions.entity_missing:
            valid_actions = list(scoped_actions.actions)
            rollout_actions = enrich_active_ai_action_spaces(
                valid_actions,
                device_info,
            )
        rollout_blocked_actions = (
            [
                dict(item)
                for item in result.get("rollout_blocked_actions", [])
                if isinstance(item, dict)
            ]
            if isinstance(result.get("rollout_blocked_actions"), list)
            else []
        )
        if not rollout_blocked_actions and scoped_actions.blocked_entity_ids:
            blocked_entity_ids = set(scoped_actions.blocked_entity_ids)
            for action in candidate_actions:
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
        execution_flags = (
            rollout_payload.get("execution_flags")
            if isinstance(rollout_payload.get("execution_flags"), dict)
            else {}
        )
        is_enabled = getattr(self, "_is_enabled", None)
        rollout_decision = evaluate_active_ai_execution_gate(
            ai_enabled=bool(is_enabled()) if callable(is_enabled) else False,
            config=rollout_config,
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
                candidate_actions=candidate_actions,
                rollout_blocked_actions=rollout_blocked_actions,
                execution_result=0,
                execution_suppressed_reason=rollout_decision.reason,
                rollout=rollout_decision.as_trace(),
                decision_contract_lineage=decision_contract_lineage,
            )
        if any(action_requires_presence_refresh(action) for action in valid_actions):
            refresh_presence = getattr(self, "_async_refresh_presence_snapshot_cache", None)
            refreshed = False
            if callable(refresh_presence):
                try:
                    refreshed = await refresh_presence() is True
                except Exception as exc:
                    _LOGGER.warning(
                        "[Add-on FastPath] presence refresh before turn_off failed: %s",
                        exc.__class__.__name__,
                    )
            if not refreshed:
                self._sys_log(
                    "WARN",
                    f"[Add-on FastPath] blocked turn_off because authoritative "
                    f"Presence refresh failed transaction_id={transaction_id or '-'}",
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
                    candidate_actions=candidate_actions,
                    rollout_blocked_actions=rollout_blocked_actions,
                    execution_result=0,
                    execution_suppressed_reason="presence_refresh_failed",
                    rollout=rollout_decision.as_trace(),
                    decision_contract_lineage=decision_contract_lineage,
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
            decision_time=str(result.get("decision_time") or "").strip(),
            require_world_snapshot_guard=True,
            # The fast-path result is already a canonical Core command.  Keep
            # HA as the exact transport/effect adapter instead of routing by
            # entity names to a legacy scene or script.
            direct_entity_only=True,
            decision_contract_lineage=decision_contract_lineage,
        )
        audit_context = self._enqueue_fast_path_execution_audit(
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            world_snapshot_id=world_snapshot_id,
            decision_trace=decision_trace,
            trigger=trigger or f"{entity_id}: state_changed",
            scene=str(scene),
            confidence=confidence,
            actions=valid_actions,
            candidate_actions=candidate_actions,
            rollout_blocked_actions=rollout_blocked_actions,
            execution_result=execution_result,
            enqueue_event=False,
            decision_contract_lineage=decision_contract_lineage,
        )
        return await self._persist_fast_path_execution_audit(audit_context)

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
        candidate_actions: list[Any] | None = None,
        rollout_blocked_actions: list[Any] | None = None,
        execution_suppressed_reason: str = "",
        rollout: dict[str, Any] | None = None,
        enqueue_event: bool = True,
        decision_contract_lineage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        transaction_id = str(transaction_id or "").strip()
        if not transaction_id:
            return {}
        valid_actions = [dict(item) for item in actions if isinstance(item, dict)]
        candidate_action_rows = [
            dict(item)
            for item in (
                candidate_actions
                if isinstance(candidate_actions, list)
                else valid_actions
            )
            if isinstance(item, dict)
        ]
        blocked_action_rows = [
            dict(item)
            for item in (
                rollout_blocked_actions
                if isinstance(rollout_blocked_actions, list)
                else []
            )
            if isinstance(item, dict)
        ]
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
        action_results.extend(blocked_action_rows)
        final_outcome = (
            "observe_only"
            if execution_suppressed_reason == "active_ai_shadow"
            else "no_action"
            if execution_suppressed_reason
            in {"pending_selection_confirmation", "no_actions"}
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
            "candidate_action_count": len(candidate_action_rows),
            "authorized_action_count": len(valid_actions),
            "executed_count": executed,
            "final_outcome": final_outcome,
            "actions": valid_actions,
            "candidate_actions": candidate_action_rows,
            "authorized_actions": valid_actions,
            "rollout_blocked_actions": blocked_action_rows,
            "action_results": action_results,
            "pre_states": pre_states,
        }
        if isinstance(decision_contract_lineage, dict) and decision_contract_lineage:
            audit_context["lineage"] = {
                str(key): str(value)[:512]
                for key, value in decision_contract_lineage.items()
                if str(key).strip() and str(value).strip()
            }
        if execution_suppressed_reason:
            audit_context["execution_suppressed_reason"] = execution_suppressed_reason
        if isinstance(rollout, dict):
            audit_context["rollout"] = dict(rollout)
        if not enqueue_event:
            return audit_context
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

    async def _persist_fast_path_execution_audit(
        self,
        audit_context: dict[str, Any],
    ) -> dict[str, Any]:
        context = dict(audit_context) if isinstance(audit_context, dict) else {}
        transaction_id = str(context.get("transaction_id") or "").strip()
        if not transaction_id:
            return context

        confirmed_post = getattr(
            self,
            "_post_internal_event_confirmed_async",
            None,
        )
        receipt: dict[str, Any] = {}
        if callable(confirmed_post):
            try:
                raw_receipt = await asyncio.wait_for(
                    confirmed_post("decision_execution", context),
                    timeout=5.0,
                )
                if isinstance(raw_receipt, dict):
                    receipt = dict(raw_receipt)
            except asyncio.TimeoutError:
                receipt = {
                    "ok": False,
                    "status": 504,
                    "error": "decision_execution_persistence_timeout",
                }
            except Exception as exc:
                receipt = {
                    "ok": False,
                    "status": 502,
                    "error": (
                        "decision_execution_persistence_failed:"
                        f"{exc.__class__.__name__}"
                    ),
                }
            if (
                receipt.get("ok") is True
                and receipt.get("persistence_confirmed") is True
            ):
                return context

        enqueue = getattr(self, "_enqueue_internal_event", None)
        queued = bool(enqueue("decision_execution", context)) if callable(enqueue) else False
        if not queued:
            sys_log = getattr(self, "_sys_log", None)
            if callable(sys_log):
                sys_log(
                    "WARN",
                    "[Add-on FastPath] execution receipt persistence failed "
                    f"transaction_id={transaction_id}",
                )
        return context


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

    def _prune_manual_service_contexts(self, now: float | None = None) -> dict[str, dict[str, Any]]:
        current = time.time() if now is None else float(now)
        cache = getattr(self, "_trusted_manual_service_contexts", None)
        if not isinstance(cache, dict):
            cache = {}
            self._trusted_manual_service_contexts = cache
        cutoff = current - float(self._MANUAL_SERVICE_CONTEXT_RETENTION_SECONDS)
        for context_id in list(cache):
            row = cache.get(context_id)
            try:
                occurred_at = float((row or {}).get("time") or 0)
            except (AttributeError, TypeError, ValueError):
                occurred_at = 0.0
            if occurred_at < cutoff:
                cache.pop(context_id, None)
        return cache

    @staticmethod
    def _is_user_scene_script_service(domain: str, service: str) -> bool:
        normalized_domain = str(domain or "").strip().lower()
        normalized_service = str(service or "").strip().lower()
        if normalized_domain == "scene":
            return normalized_service in {"turn_on", "apply"}
        if normalized_domain == "script":
            return normalized_service not in {"", "reload", "turn_off"}
        return False

    def _trusted_registered_ha_sources(self) -> dict[str, str]:
        """Return owner-approved HA behavior sources keyed by entity id."""
        result: dict[str, str] = {}
        expected_domains = {
            "ha_automation": "automation",
            "ha_script": "script",
            "ha_scene": "scene",
        }
        assets = getattr(self, "_habit_assets", None)
        if not isinstance(assets, list):
            return result
        for row in assets:
            if not isinstance(row, dict):
                continue
            source_type = str(row.get("source_type") or "").strip().lower()
            domain = expected_domains.get(source_type)
            source_id = str(row.get("source_id") or "").strip()
            if (
                not domain
                or not source_id.startswith(f"{domain}.")
                or source_id.count(".") != 1
                or str(row.get("trust_state") or "").strip().lower() != "verified"
                or str(row.get("origin") or "").strip().lower() != "explicit_user_approval"
                or str(row.get("lifecycle_state") or "active").strip().lower() != "active"
            ):
                continue
            result[source_id] = source_type
        return result

    @staticmethod
    def _ha_service_source_id(
        domain: str,
        service: str,
        service_data: dict[str, Any],
    ) -> str:
        normalized_domain = str(domain or "").strip().lower()
        normalized_service = str(service or "").strip().lower()
        raw_entity_id = service_data.get("entity_id")
        if isinstance(raw_entity_id, str):
            candidates = [item.strip() for item in raw_entity_id.split(",") if item.strip()]
        elif isinstance(raw_entity_id, (list, tuple, set)):
            candidates = [str(item or "").strip() for item in raw_entity_id if str(item or "").strip()]
        else:
            candidates = []
        expected_prefix = f"{normalized_domain}."
        for entity_id in candidates:
            if entity_id.startswith(expected_prefix):
                return entity_id
        if (
            normalized_domain == "script"
            and normalized_service not in {"", "reload", "turn_off", "turn_on", "toggle"}
        ):
            return f"script.{normalized_service}"
        return ""

    def _make_call_service_handler(self):
        """Track owner-started scene/script context lineage for child device actions."""

        @callback
        def _call_service(event: Any) -> None:
            data = getattr(event, "data", None)
            if not isinstance(data, dict):
                return
            context = getattr(event, "context", None)
            context_id = str(getattr(context, "id", None) or "").strip()
            if not context_id:
                return

            now = time.time()
            cache = self._prune_manual_service_contexts(now)
            domain = str(data.get("domain") or "").strip().lower()
            service = str(data.get("service") or "").strip().lower()
            user_id = str(getattr(context, "user_id", None) or "").strip()
            parent_id = str(getattr(context, "parent_id", None) or "").strip()
            attribution: dict[str, Any] | None = None

            if user_id and self._is_user_scene_script_service(domain, service):
                attribution = {
                    "origin": "user_scene_script_action",
                    "actor": f"ha_user:{user_id}",
                    "context_id": context_id,
                    "root_context_id": context_id,
                    "manual_service_domain": domain,
                    "manual_service": service,
                    "time": now,
                }
            elif parent_id and isinstance(cache.get(parent_id), dict):
                attribution = dict(cache[parent_id])
                attribution["time"] = now
            elif self._is_user_scene_script_service(domain, service):
                service_data = data.get("service_data")
                if not isinstance(service_data, dict):
                    service_data = {}
                source_id = self._ha_service_source_id(domain, service, service_data)
                source_type = self._trusted_registered_ha_sources().get(source_id)
                if source_type:
                    attribution = {
                        "origin": "automation",
                        "actor": f"homeassistant:{source_id}",
                        "context_id": context_id,
                        "root_context_id": context_id,
                        "manual_service_domain": domain,
                        "manual_service": service,
                        "registered_source_id": source_id,
                        "registered_source_type": source_type,
                        "owner_registered": True,
                        "trusted_automation_source": True,
                        "time": now,
                    }

            if attribution is not None:
                cache[context_id] = attribution

        return _call_service

    def _manual_action_attribution(
        self,
        state_obj: Any,
        *,
        entity_id: str = "",
    ) -> dict[str, Any]:
        context = getattr(state_obj, "context", None)
        context_id = str(getattr(context, "id", None) or "").strip()
        user_id = str(getattr(context, "user_id", None) or "").strip()
        parent_id = str(getattr(context, "parent_id", None) or "").strip()
        if user_id:
            return {
                "origin": "user_action",
                "actor": f"ha_user:{user_id}",
                "context_id": context_id or "not_applicable",
            }

        cache = self._prune_manual_service_contexts()
        lineage = cache.get(parent_id) if parent_id else None
        if not isinstance(lineage, dict) and context_id:
            lineage = cache.get(context_id)
        if isinstance(lineage, dict):
            root_context_id = str(
                lineage.get("root_context_id")
                or lineage.get("context_id")
                or context_id
                or "not_applicable"
            )
            result = {
                "origin": str(lineage.get("origin") or "user_scene_script_action"),
                "actor": str(lineage.get("actor") or "ha_user:scene_script"),
                "context_id": root_context_id,
            }
            for key in (
                "manual_service_domain",
                "manual_service",
                "registered_source_id",
                "registered_source_type",
                "owner_registered",
                "trusted_automation_source",
            ):
                value = lineage.get(key)
                if value not in (None, ""):
                    result[key] = value
            return result

        if parent_id:
            result = {
                "origin": "automation",
                "actor": "homeassistant:automation",
                "context_id": context_id or parent_id,
            }
            managed = getattr(self, "_automation_managed_device_entities", None)
            candidate_ids = (
                set(managed.get(entity_id) or set())
                if isinstance(managed, dict) and entity_id
                else set()
            )
            trusted_sources = self._trusted_registered_ha_sources()
            if candidate_ids and all(
                trusted_sources.get(source_id) == "ha_automation"
                for source_id in candidate_ids
            ):
                source_ids = sorted(candidate_ids)
                result.update(
                    {
                        "actor": "homeassistant:" + ",".join(source_ids),
                        "registered_source_id": source_ids[0],
                        "registered_source_ids": source_ids,
                        "registered_source_type": "ha_automation",
                        "owner_registered": True,
                        "trusted_automation_source": True,
                    }
                )
            return result
        return {
            "origin": "physical_action",
            "actor": "ha_user:physical_control",
            "context_id": context_id or "not_applicable",
        }

    def _record_arrival_manual_action_evidence(
        self,
        *,
        entity_id: str,
        old_state: str,
        new_state: str,
        new_state_obj: Any,
        source_type: str,
        device_info: dict[str, Any],
    ) -> bool:
        """暂存到达照明学习所需的业主直接操作证据。"""
        domain = str(entity_id or "").split(".", 1)[0]
        capability = str(device_info.get("capability") or "").strip().lower()
        managed = any(
            value is True
            or str(value or "").strip().lower() in {"1", "true", "yes", "on"}
            for value in (
                device_info.get("managed"),
                device_info.get("in_sa"),
                device_info.get("in_smartagent"),
            )
        )
        if (
            domain not in {"light", "switch"}
            or capability != "lighting"
            or not managed
        ):
            return False

        before = str(old_state or "").strip().lower()
        after = str(new_state or "").strip().lower()
        if before == after or before not in {"on", "off"} or after not in {"on", "off"}:
            return False

        attribution = self._manual_action_attribution(new_state_obj, entity_id=entity_id)
        trusted_registered_source = bool(
            attribution.get("owner_registered")
            and attribution.get("trusted_automation_source")
        )
        if attribution["origin"] not in {
            "user_action",
            "physical_action",
            "user_scene_script_action",
        } and not trusted_registered_source:
            return False

        room = str(
            device_info.get("space_id")
            or device_info.get("room")
            or device_info.get("area")
            or ""
        ).strip()
        if not room:
            return False

        occurred_at = time.time()
        retention = max(
            float(self._ARRIVAL_MANUAL_EVIDENCE_RETENTION_SECONDS),
            float(self._ARRIVAL_LEARNING_LOOKBACK_SECONDS)
            + float(self._ARRIVAL_LEARNING_WINDOW_SECONDS),
        )
        cutoff = occurred_at - retention
        cache = getattr(self, "_arrival_manual_action_evidence", None)
        if not isinstance(cache, dict):
            cache = {}
            self._arrival_manual_action_evidence = cache
        for cached_entity_id in list(cache):
            rows = cache.get(cached_entity_id)
            if not isinstance(rows, list):
                cache.pop(cached_entity_id, None)
                continue
            kept: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                try:
                    row_time = float(row.get("time") or 0)
                except (TypeError, ValueError):
                    continue
                if row_time >= cutoff:
                    kept.append(row)
            if kept:
                cache[cached_entity_id] = kept[-16:]
            else:
                cache.pop(cached_entity_id, None)

        evidence = {
            **attribution,
            "time": occurred_at,
            "room": room,
            "old_state": before,
            "new_state": after,
            "source_type": source_type,
        }
        cache.setdefault(entity_id, []).append(evidence)
        cache[entity_id] = cache[entity_id][-16:]
        return True

    def _arrival_manual_action_rows(
        self,
        *,
        room: str,
        since: float,
        until: float,
    ) -> dict[str, list[dict[str, Any]]]:
        cache = getattr(self, "_arrival_manual_action_evidence", None)
        if not isinstance(cache, dict):
            return {}
        selected: dict[str, list[dict[str, Any]]] = {}
        for entity_id, raw_rows in cache.items():
            if not isinstance(raw_rows, list):
                continue
            rows: list[dict[str, Any]] = []
            for raw in raw_rows:
                if not isinstance(raw, dict):
                    continue
                try:
                    occurred_at = float(raw.get("time") or 0)
                except (TypeError, ValueError):
                    continue
                if (
                    since <= occurred_at <= until
                    and str(raw.get("room") or "").strip() == room
                ):
                    rows.append(dict(raw))
            if rows:
                rows.sort(key=lambda row: float(row.get("time") or 0))
                selected[str(entity_id)] = rows
        return selected

    def _arrival_room_has_active_presence(self, room: str, states: Any) -> bool:
        device_info = (
            getattr(self, "device_info", {})
            if isinstance(getattr(self, "device_info", None), dict)
            else {}
        )
        if states is None or not hasattr(states, "get"):
            return False
        for presence_entity_id, raw_info in device_info.items():
            if not isinstance(raw_info, dict):
                continue
            presence_room = str(
                raw_info.get("space_id")
                or raw_info.get("room")
                or raw_info.get("area")
                or ""
            ).strip()
            if presence_room != room:
                continue
            if not self._is_presence_listener_entity(presence_entity_id, raw_info):
                continue
            state_obj = states.get(presence_entity_id)
            state = str(getattr(state_obj, "state", "") or "").strip().lower()
            if state in self._ARRIVAL_ACTIVE_STATES:
                return True
        return False

    @staticmethod
    def _presence_cycle_observation_is_fresh(
        raw_info: dict[str, Any],
        state_obj: Any,
    ) -> bool:
        if raw_info.get("presence_eligible") is False or raw_info.get("stale") is True:
            return False
        eligible_text = str(raw_info.get("presence_eligible") or "").strip().lower()
        if eligible_text in {"0", "false", "no", "off"}:
            return False

        if "use_for" in raw_info:
            raw_use_for = raw_info.get("use_for")
            if isinstance(raw_use_for, str):
                use_for = {
                    item.strip()
                    for item in raw_use_for.split(",")
                    if item.strip()
                }
            elif isinstance(raw_use_for, (list, tuple, set)):
                use_for = {
                    str(item or "").strip()
                    for item in raw_use_for
                    if str(item or "").strip()
                }
            else:
                use_for = set()
            if not use_for.intersection({"turn_on", "occupied_or", "guard"}):
                return False

        raw_ttl = raw_info.get("freshness_ttl_secs")
        if raw_ttl in (None, ""):
            return True
        try:
            freshness_ttl_secs = float(raw_ttl)
        except (TypeError, ValueError):
            return False
        if not isfinite(freshness_ttl_secs) or freshness_ttl_secs < 0:
            return False
        if freshness_ttl_secs == 0:
            return True

        observed_value = (
            raw_info.get("last_observed_at")
            or raw_info.get("observed_at")
            or getattr(state_obj, "last_updated", None)
            or getattr(state_obj, "last_changed", None)
        )
        if isinstance(observed_value, datetime):
            observed_at = observed_value
        else:
            observed_text = str(observed_value or "").strip()
            try:
                observed_at = datetime.fromisoformat(
                    observed_text.replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                return False
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        age_secs = (
            datetime.now(timezone.utc) - observed_at.astimezone(timezone.utc)
        ).total_seconds()
        return -60 <= age_secs <= freshness_ttl_secs


    def _arrival_occupancy_cycle_for_edge(
        self,
        entity_id: str,
        old_state: str,
        new_state: str,
    ) -> tuple[str, bool, bool]:
        """Return the stable cycle id plus first-arrival/final-departure edges."""
        device_info = (
            getattr(self, "device_info", {})
            if isinstance(getattr(self, "device_info", None), dict)
            else {}
        )
        info = device_info.get(entity_id) if isinstance(device_info, dict) else {}
        room = str(
            (info or {}).get("space_id")
            or (info or {}).get("room")
            or (info or {}).get("area")
            or ""
        ).strip()
        if not room:
            return "", False, False

        states = getattr(getattr(self, "hass", None), "states", None)
        other_active = False
        for presence_entity_id, raw_info in device_info.items():
            if presence_entity_id == entity_id or not isinstance(raw_info, dict):
                continue
            presence_room = str(
                raw_info.get("space_id")
                or raw_info.get("room")
                or raw_info.get("area")
                or ""
            ).strip()
            if presence_room != room or not self._is_presence_listener_entity(
                presence_entity_id,
                raw_info,
            ):
                continue
            state_obj = states.get(presence_entity_id) if hasattr(states, "get") else None
            if not self._presence_cycle_observation_is_fresh(raw_info, state_obj):
                continue
            state = str(getattr(state_obj, "state", "") or "").strip().lower()
            if state in self._ARRIVAL_ACTIVE_STATES:
                other_active = True
                break

        cycles = getattr(self, "_arrival_occupancy_cycles", None)
        if not isinstance(cycles, dict):
            cycles = {}
            self._arrival_occupancy_cycles = cycles
        outcome = advance_occupancy_cycle(
            cycles, room=room, new_state=new_state, other_active=other_active,
            active_states=self._ARRIVAL_ACTIVE_STATES,
            departure_debounce_seconds=max(0.0, float(getattr(self, "_PRESENCE_OFF_DELAY", PRESENCE_OFF_DELAY) or 0.0)),
        )
        persist_occupancy_cycles(self)
        return outcome
    def _schedule_arrival_baseline_sample(
        self,
        entity_id: str,
        old_state: str,
        new_state: str,
        *,
        occupancy_cycle_id: str = "",
    ) -> None:
        """先确认到达，再在独立的较宽时间窗中采集业主照明选择。"""
        old_value = str(old_state or "").strip().lower()
        new_value = str(new_state or "").strip().lower()
        if old_value not in {"off", "closed", "not_home", "away", "idle", "clear", "empty", "vacant", "0", ""}:
            return
        if not self._is_presence_arrival_for_slow_inference(entity_id, new_value):
            return
        device_info = getattr(self, "device_info", {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        info = device_info.get(entity_id) if isinstance(device_info, dict) else {}
        room = resolve_space_id(
            info or {}, entity_id=entity_id,
            area_getter=getattr(self, "_get_entity_area", None),
        )
        if not room:
            return

        states = getattr(self.hass, "states", None)
        lighting_entity_ids = arrival_lighting_entity_ids(
            device_info,
            room,
            entity_states=states,
        )
        environment_builder = getattr(
            self,
            "_build_fast_path_environment_context",
            None,
        )
        raw_environment_context = (
            environment_builder(device_info, entity_id)
            if callable(environment_builder)
            else None
        )
        environment_context = (
            dict(raw_environment_context)
            if isinstance(raw_environment_context, dict)
            else {}
        )
        pre_light_states_at_arrival: dict[str, str | None] = {
            lighting_entity_id: (
                getattr(states.get(lighting_entity_id), "state", None)
                if states is not None and hasattr(states, "get")
                else None
            )
            for lighting_entity_id in lighting_entity_ids
        }
        arrival_detected_at = time.time()
        sample_started_at = (
            arrival_detected_at
            - max(0.0, float(self._ARRIVAL_LEARNING_LOOKBACK_SECONDS))
        )

        def _sample(_now: Any = None) -> None:
            try:
                states = getattr(self.hass, "states", None)
                recorder = getattr(self, "_record_arrival_snapshot", None)
                if callable(recorder):
                    sample_ended_at = time.time()
                    manual_rows = self._arrival_manual_action_rows(
                        room=room,
                        since=sample_started_at,
                        until=sample_ended_at,
                    )
                    room_still_occupied = self._arrival_room_has_active_presence(
                        room,
                        states,
                    )
                    if not room_still_occupied and not manual_rows:
                        return

                    pre_light_states = dict(pre_light_states_at_arrival)
                    for light_entity_id, rows in manual_rows.items():
                        pre_arrival_rows = [
                            row
                            for row in rows
                            if float(row.get("time") or 0) <= arrival_detected_at
                        ]
                        if pre_arrival_rows:
                            pre_light_states[light_entity_id] = pre_arrival_rows[0].get(
                                "old_state"
                            )

                    observed_light_states: dict[str, str | None] = {}
                    state_change_evidence: dict[str, dict[str, Any]] = {}
                    smartagent_actions: list[dict[str, Any]] = []
                    for light_entity_id in pre_light_states:
                        if not room_still_occupied and light_entity_id not in manual_rows:
                            continue
                        light_state = states.get(light_entity_id) if states is not None and hasattr(states, "get") else None
                        observed_light_states[light_entity_id] = (
                            getattr(light_state, "state", None) if light_state is not None else None
                        )
                        rows = manual_rows.get(light_entity_id) or []
                        if rows:
                            state_change_evidence[light_entity_id] = dict(rows[-1])
                            state_change_evidence[light_entity_id].pop(
                                "source_type",
                                None,
                            )
                            continue
                        state_context = getattr(light_state, "context", None)
                        last_changed = getattr(light_state, "last_changed", None)
                        try:
                            changed_at = float(last_changed.timestamp())
                        except (AttributeError, TypeError, ValueError, OSError):
                            changed_at = 0.0
                        if sample_started_at <= changed_at <= sample_ended_at:
                            attribution = self._manual_action_attribution(light_state, entity_id=light_entity_id)
                            state_change_evidence[light_entity_id] = {
                                **attribution,
                                "time": changed_at,
                            }

                    causal_since = sample_started_at
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
                        pre_light_states={
                            light_entity_id: pre_light_states.get(light_entity_id)
                            for light_entity_id in observed_light_states
                        },
                        smartagent_actions=deduplicated_actions,
                        state_change_evidence=state_change_evidence,
                        sample_started_at=sample_started_at,
                        sample_ended_at=sample_ended_at,
                        environment_context=environment_context,
                        occupancy_cycle_id=occupancy_cycle_id,
                    )
            except Exception as exc:
                _LOGGER.debug("[ArrivalBaseline] delayed sample failed for %s: %s", entity_id, exc)

        def _confirm_presence(_now: Any = None) -> None:
            try:
                states = getattr(self.hass, "states", None)
                state_obj = (
                    states.get(entity_id)
                    if states is not None and hasattr(states, "get")
                    else None
                )
                state = str(
                    getattr(state_obj, "state", "") or ""
                ).strip().lower()
                if state_obj is not None and state not in self._ARRIVAL_ACTIVE_STATES:
                    return
                hold_seconds = max(
                    1.0,
                    float(getattr(self, "_PRESENCE_ON_MIN_HOLD", 1) or 1),
                )
                learning_window = max(
                    hold_seconds,
                    float(self._ARRIVAL_LEARNING_WINDOW_SECONDS),
                )
                remaining = learning_window - hold_seconds
                if remaining <= 0:
                    _sample(_now)
                else:
                    async_call_later(self.hass, remaining, _sample)
            except Exception as exc:
                _LOGGER.debug(
                    "[ArrivalBaseline] presence confirmation failed for %s: %s",
                    entity_id,
                    exc,
                )

        try:
            delay = max(1, int(getattr(self, "_PRESENCE_ON_MIN_HOLD", 1) or 1))
            async_call_later(self.hass, delay, _confirm_presence)
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
        device_info = getattr(self, "device_info", {}) if isinstance(getattr(self, "device_info", None), dict) else {}
        info = device_info.get(entity_id) if isinstance(device_info, dict) else {}
        if not isinstance(info, dict):
            info = {}
        info_payload, space_id, room = learning_space_identity(
            info, entity_id=entity_id,
            area_getter=getattr(self, "_get_entity_area", None),
        )
        now = self._ha_local_now()
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue):
            return
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        old_attrs = getattr(old_state_obj, "attributes", None)
        new_attrs = getattr(new_state_obj, "attributes", None)
        attribution = self._manual_action_attribution(new_state_obj, entity_id=entity_id)
        origin = str(attribution.get("origin") or "unknown")
        trusted_manual = origin in {
            "user_action",
            "physical_action",
            "user_scene_script_action",
        }
        trusted_registered_source = bool(
            attribution.get("owner_registered")
            and attribution.get("trusted_automation_source")
        )
        learning_mode = bool(getattr(self, "_learning_mode", False))
        domain = str(entity_id or "").split(".", 1)[0]
        if not learning_mode and (
            (not trusted_manual and not trusted_registered_source)
            or domain not in self._CONTROL_EVENT_DOMAINS
        ):
            return
        if origin in {"user_action", "user_scene_script_action"}:
            learning_source_type = "user_interface"
        elif origin == "physical_action":
            learning_source_type = "manual_action"
        elif trusted_registered_source:
            learning_source_type = str(
                attribution.get("registered_source_type") or "ha_automation"
            )
        else:
            learning_source_type = str(source_type or "")
        manual_session = self._manual_scene_learning_session(
            attribution=attribution,
            space_id=space_id,
            room=str(
                info_payload.get("room_name")
                or info_payload.get("area_name")
                or room
            ).strip(),
            source_type=learning_source_type,
            now=now,
        )
        payload = {
            "action": "sample_state_transition",
            "entity_id": entity_id,
            "old_state": str(old_state or ""),
            "new_state": str(new_state or ""),
            "old_attributes": dict(old_attrs) if isinstance(old_attrs, dict) else {},
            "new_attributes": dict(new_attrs) if isinstance(new_attrs, dict) else {},
            "device_info": info_payload,
            "source_type": learning_source_type,
            "observed_source_type": str(source_type or ""),
            **manual_session,
            **attribution,
            "decision_id": "not_applicable",
            "transaction_id": str(
                attribution.get("context_id") or "not_applicable"
            ),
            "world_snapshot_id": "not_applicable",
        }
        if enqueue("behavior", payload, ts=ts):
            self._sys_log("INFO", f"[SilentLearning] behavior sample forwarded: {entity_id}")

    def _manual_scene_learning_session(
        self,
        *,
        attribution: dict[str, Any],
        space_id: str,
        room: str,
        source_type: str,
        now: datetime,
    ) -> dict[str, Any]:
        origin = str(attribution.get("origin") or "").strip()
        actor = str(attribution.get("actor") or "").strip()
        context_id = str(attribution.get("context_id") or "").strip()
        trusted_registered_source = bool(
            attribution.get("owner_registered")
            and attribution.get("trusted_automation_source")
        )
        if not space_id or (
            origin not in {
                "user_action",
                "physical_action",
                "user_scene_script_action",
            }
            and not trusted_registered_source
        ):
            return {}

        explicit_lineage = bool(
            context_id
            and (
                origin == "user_scene_script_action"
                or trusted_registered_source
            )
        )
        session_scope = (
            f"explicit|{actor}|{context_id}"
            if explicit_lineage
            else f"direct|{actor}|{space_id}"
        )
        sessions = getattr(self, "_manual_scene_learning_sessions", None)
        if not isinstance(sessions, dict):
            sessions = {}
            self._manual_scene_learning_sessions = sessions
        timers = getattr(self, "_manual_scene_learning_timers", None)
        if not isinstance(timers, dict):
            timers = {}
            self._manual_scene_learning_timers = timers

        current_time = time.time()
        current = sessions.get(session_scope)
        if not isinstance(current, dict) or (
            not explicit_lineage
            and current_time - float(current.get("last_event_time") or 0)
            > float(self._MANUAL_SCENE_SESSION_IDLE_SECONDS)
        ):
            seed = f"{session_scope}|{current_time:.6f}"
            session_id = "manual-session-" + hashlib.sha256(
                seed.encode("utf-8")
            ).hexdigest()[:24]
            current = {
                "session_id": session_id,
                "started_at": now.isoformat(),
                "generation": 0,
            }
            sessions[session_scope] = current

        current["last_event_time"] = current_time
        current["generation"] = int(current.get("generation") or 0) + 1
        generation = int(current["generation"])
        session_id = str(current["session_id"])
        started_at = str(current["started_at"])
        previous_timer = timers.pop(session_scope, None)
        if callable(previous_timer):
            try:
                previous_timer()
            except Exception:
                pass

        def _finalize(_now: Any = None) -> None:
            active = sessions.get(session_scope)
            if (
                not isinstance(active, dict)
                or int(active.get("generation") or 0) != generation
            ):
                return
            enqueue = getattr(self, "_enqueue_internal_event", None)
            if callable(enqueue):
                ended_at = self._ha_local_now()
                enqueue(
                    "behavior",
                    {
                        "action": "finalize_manual_scene_session",
                        "manual_session_id": session_id,
                        "manual_session_started_at": started_at,
                        "space_id": space_id,
                        "room": room or space_id,
                        "origin": origin,
                        "actor": actor,
                        "source_type": source_type,
                        "transaction_id": context_id or "not_applicable",
                    },
                    ts=ended_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            sessions.pop(session_scope, None)
            timers.pop(session_scope, None)

        try:
            timers[session_scope] = async_call_later(
                self.hass,
                float(self._MANUAL_SCENE_SESSION_IDLE_SECONDS),
                _finalize,
            )
        except Exception as exc:
            _LOGGER.warning(
                "[ManualSceneLearning] finalize scheduling failed session_id=%s error=%s",
                session_id,
                exc.__class__.__name__,
            )

        return {
            "manual_session_id": session_id,
            "manual_session_started_at": started_at,
            "space_id": space_id,
            "room": room or space_id,
        }

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
        *,
        occupancy_cycle_id: str = "",
        trigger_context: dict[str, Any] | None = None,
        suppress_slow_fallback: bool = False,
    ) -> None:
        await run_addon_fast_path_fail_closed(
            self,
            entity_id,
            new_state,
            old_state,
            occupancy_cycle_id=occupancy_cycle_id,
            trigger_context=trigger_context,
            suppress_slow_fallback=suppress_slow_fallback,
        )

    def _make_state_handler(self):
        """Build the state-change callback."""

        @callback
        def _state_changed(ev) -> None:
            handle_listener_state_changed(self, ev, logger=_LOGGER)

        return _state_changed

    _listener_entity_metadata = listener_entity_metadata
    _is_presence_listener_entity = is_presence_listener_entity
    _get_live_presence_occupancy_map = get_live_presence_occupancy_map
    def _reconcile_active_listener_states(self, entity_ids: list[str]) -> None:
        reconcile_active_listener_states(
            self,
            entity_ids,
            schedule=async_call_later,
        )
    _async_refresh_device_info_from_addon_devices = async_refresh_device_info_from_addon_devices
    _is_actionable_sensor_runtime_entity = is_actionable_sensor_runtime_entity
    _is_listener_runtime_entity = is_listener_runtime_entity
    _managed_device_info_row_from_addon_device = managed_device_info_row_from_addon_device
    _device_info_row_from_addon_device = device_info_row_from_addon_device
    _managed_listener_entity_ids = managed_listener_entity_ids
    _reconcile_device_info_entity_ids_from_ha_registry = reconcile_device_info_entity_ids_from_ha_registry
    _persist_ha_registry_metadata = persist_ha_registry_metadata
    _persist_device_registry_metadata = persist_device_registry_metadata
    _persist_device_entity_id_migration = persist_device_entity_id_migration
    _refresh_listeners_if_entity_set_changed = refresh_listeners_if_entity_set_changed

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
        cleanup_startup_reconciliation(self, entity_ids)
        if entity_ids:
            state_removers.append(
                async_track_state_change_event(self.hass, entity_ids, self._make_state_handler())
            )
            self._reconcile_active_listener_states(entity_ids)
            self._sys_log("INFO", f"监听器已刷新，监听 {len(entity_ids)} 个实体: {', '.join(entity_ids[:5])}{'...' if len(entity_ids)>5 else ''}")
        else:
            self._sys_log("WARN", "监听器刷新：无可监听设备，请先添加设备")
