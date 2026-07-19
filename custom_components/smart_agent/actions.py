"""
ActionsMixin — 动作执行层。
负责：动作标准化、实体模糊匹配、Action Router（脚本/场景路由）、
      服务调用保护、动作验证与自动重试。
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import ServiceNotFound

from .const import (
    ACTION_PARAM_KEYS_COLOR,
    ACTION_PARAM_KEYS_LIGHT_SCENE,
    ACTION_PARAM_KEYS_USELESS_WHEN_OFF,
    DEVICE_CAP_KEY_COVERAGE_SPACES,
    DEVICE_CAP_KEY_SHARED_FIXTURE,
    MODE_SHOWROOM,
)
from .execution_gate import (
    ALLOWED_DOMAINS as THIN_GATE_ALLOWED_DOMAINS,
    BLOCKED_SERVICES as THIN_GATE_BLOCKED_SERVICES,
    STATELESS_DOMAINS as THIN_GATE_STATELESS_DOMAINS,
    evaluate_automation_conflict_window,
    evaluate_color_temp_mireds_param,
    evaluate_global_suppress_window,
    evaluate_manual_override_window,
    evaluate_self_trigger_protection,
    evaluate_thin_execution_gate,
)

_LOGGER = logging.getLogger(__name__)


class ActionsMixin:
    """Mixin: 动作执行 — 路由 / 保护 / 验证 / 重试。"""

    def _get_showroom_light_tier_v2(self, entity_id: str) -> str:
        """Return the neutral tier after HA-local showroom preference storage removal."""
        return "core"

    class _ActionExecutionResult(int):
        """Int-compatible execution summary with per-action trace results."""

        def __new__(
            cls,
            executed_count: int = 0,
            *,
            action_results: list[dict[str, Any]] | None = None,
            transaction_id: int = 0,
            raw_results: list[dict[str, Any]] | None = None,
            pre_states: dict[str, str] | None = None,
        ):
            value = max(0, int(executed_count or 0))
            obj = int.__new__(cls, value)
            obj.executed_count = value
            obj.action_results = list(action_results or [])
            obj.transaction_id = int(transaction_id or 0)
            obj.raw_results = list(raw_results or [])
            obj.pre_states = dict(pre_states or {})
            return obj

    # 合法的设备管辖域值（DatabaseMixin 也定义了此常量，MRO 取第一个即可）
    _VALID_CONTROL_MODES = frozenset({"ai", "ha", "shared"})

    # 设备管辖域标签（用于日志）
    _CONTROL_MODE_LABELS = {"ai": "AI全权", "ha": "HA优先", "shared": "共享"}

    # 安全白名单：AI 允许操作的 HA 域和禁止调用的危险服务
    _ALLOWED_DOMAINS = THIN_GATE_ALLOWED_DOMAINS
    _BLOCKED_SERVICES = THIN_GATE_BLOCKED_SERVICES

    # 动作验证参数
    _ACTION_VERIFY_DELAY = 5    # 执行后 N 秒回查状态
    _ACTION_RETRY_MAX = 1       # 最大自动重试次数
    _VERIFY_QUEUE_MAX = 50      # 待验证队列上限
    _VERIFY_EXPIRE_SEC = 120    # 超过 N 秒未验证完成的条目强制丢弃

    # 场景/脚本重复执行冷却
    _SCENE_COOLDOWN = 60        # 同一场景/脚本 N 秒内不重复执行
    _DIM_TO_OFF_BRIGHTNESS_PCT = 5
    _DAYLIGHT_AUTO_LIGHTING_SUPPRESSED = "daylight_auto_lighting_suppressed"
    _DAYLIGHT_GUARD_LUX_THRESHOLD = 80.0
    _DAYLIGHT_FALLBACK_START_HOUR = 8
    _DAYLIGHT_FALLBACK_END_HOUR = 20
    _PROTECTED_NIGHT_START_HOUR = 22
    _PROTECTED_NIGHT_END_HOUR = 6
    _DAYLIGHT_SUN_STATES = frozenset({"above_horizon", "day", "daylight"})
    _DARK_SUN_STATES = frozenset({"below_horizon", "night", "dark"})

    @classmethod
    def _action_execution_result(
        cls,
        executed_count: int = 0,
        *,
        transaction_id: int = 0,
        results: list[dict[str, Any]] | None = None,
        pre_states: dict[str, str] | None = None,
        correlation_id: str = "",
    ) -> int:
        normalized_correlation_id = str(correlation_id or "").strip()
        raw_results = [
            {
                **dict(item),
                **({"correlation_id": normalized_correlation_id} if normalized_correlation_id else {}),
            }
            for item in results or []
            if isinstance(item, dict)
        ]
        action_results = [
            cls._decision_action_result_from_ha_result(item)
            for item in raw_results
        ]
        return cls._ActionExecutionResult(
            executed_count,
            action_results=action_results,
            transaction_id=transaction_id,
            raw_results=raw_results,
            pre_states=pre_states,
        )

    @staticmethod
    def _decision_action_result_from_ha_result(item: dict[str, Any]) -> dict[str, Any]:
        ha_status = str(item.get("status") or "").strip()
        if ha_status == "ok":
            status = "executed"
            reason = "ha_service_call_ok"
        elif ha_status == "scheduled":
            status = "scheduled"
            reason = "delayed_action_scheduled"
        elif ha_status == "skip":
            status = "skipped"
            reason = str(item.get("msg") or "already_in_target_state")
        elif ha_status == "blocked_or_error":
            status = "failed"
            reason = str(item.get("msg") or "ha_service_returned_false")
        elif ha_status.startswith("blocked"):
            status = "blocked"
            reason = str(item.get("msg") or ha_status)
        else:
            status = "unknown"
            reason = str(item.get("msg") or ha_status or "unknown_action_result")
        entity_id = str(item.get("entity_id") or "")
        result = {
            "domain": str(item.get("domain") or (entity_id.split(".", 1)[0] if "." in entity_id else "")),
            "service": str(item.get("service") or ""),
            "entity_id": entity_id,
            "status": status,
            "reason": reason,
            "ha_status": ha_status,
        }
        if isinstance(item.get("params"), dict) and item.get("params"):
            result["params"] = dict(item.get("params") or {})
        error = str(item.get("error") or "").strip()
        if error:
            result["error"] = error
        error_type = str(item.get("error_type") or "").strip()
        if error_type:
            result["error_type"] = error_type
        action_reason = str(item.get("reason") or "").strip()
        if action_reason:
            result["action_reason"] = action_reason
        scene_desc = str(item.get("scene_desc") or "").strip()
        if scene_desc:
            result["scene_desc"] = scene_desc
        trigger_summary = str(item.get("trigger_summary") or "").strip()
        if trigger_summary:
            result["trigger_summary"] = trigger_summary
        execution_transaction_id = item.get("execution_transaction_id")
        if execution_transaction_id not in (None, ""):
            result["execution_transaction_id"] = execution_transaction_id
        parent_transaction_id = str(item.get("parent_transaction_id") or "").strip()
        if parent_transaction_id:
            result["parent_transaction_id"] = parent_transaction_id
        correlation_id = str(item.get("correlation_id") or "").strip()
        if correlation_id:
            result["correlation_id"] = correlation_id
        decision_trace = item.get("decision_trace")
        if isinstance(decision_trace, dict) and decision_trace:
            result["decision_trace"] = dict(decision_trace)
        presence_source = str(item.get("presence_source") or "").strip()
        if presence_source:
            result["presence_source"] = presence_source
        presence_reason = str(item.get("presence_reason") or "").strip()
        if presence_reason:
            result["presence_reason"] = presence_reason
        presence_room = str(item.get("presence_room") or "").strip()
        if presence_room:
            result["presence_room"] = presence_room
        presence_evidence_ids = item.get("presence_evidence_ids")
        if isinstance(presence_evidence_ids, list):
            result["presence_evidence_ids"] = [
                str(eid or "") for eid in presence_evidence_ids if str(eid or "").strip()
            ]
        presence_states = item.get("presence_states")
        if isinstance(presence_states, list):
            result["presence_states"] = [
                dict(row) for row in presence_states if isinstance(row, dict)
            ]
        presence_conflict = item.get("presence_conflict")
        if isinstance(presence_conflict, dict) and presence_conflict:
            result["presence_conflict"] = dict(presence_conflict)
        return result

    @staticmethod
    def _service_call_error_key(transaction_id: int, action_seq: int, entity_id: str) -> str:
        return f"{int(transaction_id or 0)}:{int(action_seq or 0)}:{str(entity_id or '')}"

    def _remember_service_call_error(
        self,
        transaction_id: int,
        action_seq: int,
        entity_id: str,
        *,
        msg: str,
        error: str = "",
        error_type: str = "",
        status: str = "",
    ) -> None:
        key = self._service_call_error_key(transaction_id, action_seq, entity_id)
        store = getattr(self, "_service_call_errors", None)
        if not isinstance(store, dict):
            store = {}
            self._service_call_errors = store
        detail: dict[str, Any] = {"msg": str(msg or error or status or "ha_service_call_failed")}
        if error:
            detail["error"] = str(error)
        if error_type:
            detail["error_type"] = str(error_type)
        if status:
            detail["ha_command_status"] = str(status)
        store[key] = detail

    def _clear_service_call_error(self, transaction_id: int, action_seq: int, entity_id: str) -> None:
        store = getattr(self, "_service_call_errors", None)
        if isinstance(store, dict):
            store.pop(self._service_call_error_key(transaction_id, action_seq, entity_id), None)

    def _pop_service_call_error(self, transaction_id: int, action_seq: int, entity_id: str) -> dict[str, Any]:
        store = getattr(self, "_service_call_errors", None)
        if not isinstance(store, dict):
            return {}
        detail = store.pop(self._service_call_error_key(transaction_id, action_seq, entity_id), None)
        return dict(detail) if isinstance(detail, dict) else {}

    def _is_light_blocked_by_people_rule(
        self,
        *,
        entity_id: str,
        room: str,
        person_count: int,
        parsed_rules: list[dict[str, Any]] | None,
    ) -> tuple[bool, str]:
        """Check P1 people-count rules for automatic light turn_on."""
        if not parsed_rules:
            return False, ""
        entity_id = str(entity_id or "")
        room = str(room or "").strip()
        try:
            people = int(person_count or 0)
        except (TypeError, ValueError):
            people = 0
        dev_name = str((self.device_info.get(entity_id) or {}).get("name") or "")
        text = f"{dev_name} {entity_id}".lower()

        for rule in parsed_rules:
            if not isinstance(rule, dict):
                continue
            rule_room = str(rule.get("room") or "").strip()
            if rule_room and room and rule_room != room:
                continue

            keywords = [
                str(item).strip().lower()
                for item in (rule.get("keywords") or [])
                if str(item).strip()
            ]
            if keywords and not any(keyword in text for keyword in keywords):
                continue

            try:
                threshold = int(rule.get("threshold", 0) or 0)
            except (TypeError, ValueError):
                threshold = 0
            op = str(rule.get("operator") or ">=").strip()
            allowed = people > threshold if op == ">" else people >= threshold
            if not allowed:
                return True, f"P1 people rule: need {op}{threshold}, current {people}"

        return False, ""

    def _is_night_time(self) -> bool:
        """夜间窗口判定（保守）：22:00-06:00。"""
        h = self._daylight_fallback_hour()
        if h is None:
            return False
        return h >= 22 or h < 6

    @staticmethod
    def _room_looks_like_bedroom(room: str) -> bool:
        """基于房间语义做卧室判定。"""
        room_l = str(room or "").lower()
        return any(k in room_l for k in ("卧", "bedroom", "主卧", "次卧", "儿童房", "master", "guest"))

    def _apply_sleep_reentry_low_disturbance(
        self,
        entity_id: str,
        domain: str,
        service: str,
        params: dict,
        runtime_hints: dict,
    ) -> tuple[str, dict]:
        """夜间卧室二次进入时，锁定低扰动灯参数。"""
        if domain != "light" or service != "turn_on":
            return service, params
        if not runtime_hints.get("sleep_reentry"):
            return service, params

        room = (self.device_info.get(entity_id) or {}).get("room", "")
        if not (self._room_looks_like_bedroom(room) and self._is_night_time()):
            return service, params

        out = dict(params or {})
        bri = out.get("brightness_pct")
        if bri is None and "brightness" in out:
            try:
                bri = float(out.get("brightness")) / 255 * 100
            except (TypeError, ValueError, ZeroDivisionError):
                bri = None
        if bri is None:
            out["brightness_pct"] = 20
        else:
            try:
                out["brightness_pct"] = min(float(bri), 30)
            except (TypeError, ValueError):
                out["brightness_pct"] = 20

        if "color_temp_kelvin" in out:
            try:
                out["color_temp_kelvin"] = min(float(out["color_temp_kelvin"]), 3200)
            except (TypeError, ValueError):
                out["color_temp_kelvin"] = 3000
        elif "color_temp" in out:
            try:
                _k = 1_000_000 / float(out["color_temp"])
                out["color_temp_kelvin"] = min(_k, 3200)
                out.pop("color_temp", None)
            except (TypeError, ValueError, ZeroDivisionError):
                out["color_temp_kelvin"] = 3000
        else:
            out["color_temp_kelvin"] = 3000

        self._sys_log("INFO", f"[SleepGuard] 夜间卧室二次进入低扰动锁定: {entity_id} -> {out}")
        return service, out

    def _action_entity_room(self, entity_id: str) -> str:
        info = {}
        try:
            info = self.device_info.get(entity_id, {}) or {}
        except Exception:
            info = {}
        room = str(info.get("room") or "").strip() if isinstance(info, dict) else ""
        if not room and hasattr(self, "_get_entity_area"):
            try:
                room = str(self._get_entity_area(entity_id) or "").strip()
            except Exception:
                room = ""
        return room

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _looks_like_illuminance_sensor(sensor_id: str, sensor_info: Any, state: Any) -> bool:
        info = sensor_info if isinstance(sensor_info, dict) else {}
        attrs = getattr(state, "attributes", None)
        attrs = attrs if isinstance(attrs, dict) else {}
        device_class = str(info.get("device_class") or attrs.get("device_class") or "").strip().lower()
        if device_class == "illuminance":
            return True
        unit = str(
            info.get("unit_of_measurement")
            or attrs.get("unit_of_measurement")
            or attrs.get("unit")
            or ""
        ).strip().lower()
        if unit in {"lx", "lux"}:
            return True
        label = f"{sensor_id} {info.get('name') or ''}".lower()
        return any(key in label for key in ("illuminance", "lux", "light_level", "照度", "光照"))

    def _same_room_illuminance_lux(self, entity_id: str) -> float | None:
        room = self._action_entity_room(entity_id)
        if not room:
            return None
        for sensor_id, sensor_info in self.device_info.items():
            if not str(sensor_id or "").startswith("sensor."):
                continue
            sensor_room = self._action_entity_room(sensor_id)
            if sensor_room != room:
                continue
            state = self.hass.states.get(sensor_id)
            if not self._looks_like_illuminance_sensor(sensor_id, sensor_info, state):
                continue
            lux = self._float_or_none(getattr(state, "state", None))
            if lux is not None:
                return lux
        return None

    def _ha_local_now(self):
        configured_timezone = str(
            getattr(getattr(getattr(self, "hass", None), "config", None), "time_zone", "") or ""
        ).strip()
        if configured_timezone:
            normalized_tz = configured_timezone.lower()
            fixed_offset_hours = {
                "asia/shanghai": 8,
                "asia/chongqing": 8,
                "asia/harbin": 8,
                "asia/hong_kong": 8,
                "hongkong": 8,
                "prc": 8,
                "utc": 0,
            }.get(normalized_tz)
            try:
                from zoneinfo import ZoneInfo

                return datetime.now(ZoneInfo(configured_timezone))
            except Exception:
                if fixed_offset_hours is not None:
                    try:
                        from datetime import timedelta, timezone

                        tz = timezone(timedelta(hours=fixed_offset_hours), configured_timezone)
                        return datetime.now(tz)
                    except Exception:
                        pass
        try:
            from homeassistant.util import dt as dt_util
            return dt_util.now()
        except Exception:
            try:
                from datetime import timezone
                return datetime.now(timezone.utc)
            except Exception:
                return None

    def _daylight_fallback_hour(self) -> int | None:
        try:
            now = self._ha_local_now()
            return int(now.hour) if now is not None else None
        except (TypeError, ValueError):
            return None

    def _ha_local_minute_of_day(self) -> int | None:
        try:
            now = self._ha_local_now()
            if now is None:
                return None
            return int(now.hour) * 60 + int(now.minute)
        except (TypeError, ValueError):
            return None

    def _is_protected_night_hour(self) -> bool:
        hour = self._daylight_fallback_hour()
        if hour is None:
            return False
        return hour >= self._PROTECTED_NIGHT_START_HOUR or hour < self._PROTECTED_NIGHT_END_HOUR

    def _daylight_auto_lighting_suppressed_reason(self, entity_id: str) -> str:
        lux = self._same_room_illuminance_lux(entity_id)
        if lux is not None and lux <= self._DAYLIGHT_GUARD_LUX_THRESHOLD:
            return ""

        sun = self.hass.states.get("sun.sun")
        sun_state = str(getattr(sun, "state", "") or "").strip().lower()
        if self._is_protected_night_hour() and sun_state in self._DAYLIGHT_SUN_STATES:
            return ""
        if sun_state in self._DAYLIGHT_SUN_STATES:
            return self._DAYLIGHT_AUTO_LIGHTING_SUPPRESSED

        if lux is not None and lux > self._DAYLIGHT_GUARD_LUX_THRESHOLD:
            if self._is_protected_night_hour():
                return ""
            return self._DAYLIGHT_AUTO_LIGHTING_SUPPRESSED

        hour = self._daylight_fallback_hour()
        if hour is not None and self._DAYLIGHT_FALLBACK_START_HOUR <= hour <= self._DAYLIGHT_FALLBACK_END_HOUR:
            return self._DAYLIGHT_AUTO_LIGHTING_SUPPRESSED
        if sun_state in self._DARK_SUN_STATES:
            return ""
        return ""

    @staticmethod
    def _looks_like_automatic_presence_lighting(
        *,
        reason: str,
        scene_desc: str,
        trigger_summary: str,
        cmd_source: str,
    ) -> bool:
        if str(cmd_source or "").strip() == "USER_EXPLICIT":
            return False
        text = f"{reason} {scene_desc} {trigger_summary}".lower()
        if "lighting_capability_fallback" in text and any(
            marker in text
            for marker in ("occupancy", "presence", "arrival", "有人", "人体", "存在")
        ):
            return True
        if "low_risk_presence_lighting_fallback" in text:
            return True

        if "fastbrain:habit" in text and any(marker in text for marker in ("occupancy", "presence", "arrival")):
            return True

        binary_arrival = "binary_sensor." in text and any(
            marker in text for marker in ("off -> on", "off->on", "to on")
        )
        arrival_source_markers = (
            "occupancy",
            "presence",
            "motion",
            "arrival",
            "ren_ti",
            "cun_zai",
            "you_ren",
            "door",
            "contact",
            "entry",
            "enter",
            "reentry",
            "men_chuang",
            "men_ci",
            "chuan_gan_qi_men",
            "有人",
            "人体",
            "存在",
            "检测到人",
            "有人活动",
            "门磁",
            "门窗",
            "开门",
            "门打开",
            "进入",
            "进门",
            "进房",
            "回房",
        )
        if binary_arrival and any(marker in text for marker in arrival_source_markers):
            return True

        presence_markers = (
            "occupancy",
            "presence",
            "有人",
            "人体",
            "存在",
            "检测到人",
            "门磁",
            "门窗",
            "开门",
            "门打开",
            "进入",
            "进门",
            "进房",
            "回房",
        )
        arrival_markers = (
            "off -> on",
            "off->on",
            "arrival",
            "entry",
            "enter",
            "检测到有人",
            "检测到人",
            "有人活动",
            "门打开",
            "开门",
            "进入",
            "进门",
            "进房",
            "回房",
        )
        lighting_markers = ("turn_on", "开灯", "开启", "射灯", "照明", "补光", "light.")
        return (
            any(marker in text for marker in presence_markers)
            and any(marker in text for marker in arrival_markers)
            and any(marker in text for marker in lighting_markers)
        )

    @staticmethod
    def _looks_like_presence_departure_turnoff(
        *,
        reason: str,
        scene_desc: str,
        trigger_summary: str,
        cmd_source: str = "",
    ) -> bool:
        if str(cmd_source or "").strip() == "USER_EXPLICIT":
            return False
        text = f"{reason} {scene_desc} {trigger_summary}".lower()
        if "departureplanner" in text or "confirmed vacant" in text:
            return True
        if "departure" in text or "vacant" in text or "leave" in text:
            return True
        binary_departure = "binary_sensor." in text and any(
            marker in text for marker in ("on -> off", "on->off", "to off")
        )
        presence_markers = (
            "occupancy",
            "presence",
            "motion",
            "ren_ti",
            "cun_zai",
            "you_ren",
        )
        return binary_departure and any(marker in text for marker in presence_markers)

    @staticmethod
    def _json_list_or_empty(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip():
            try:
                import json as _json

                parsed = _json.loads(value)
            except Exception:
                return []
            return parsed if isinstance(parsed, list) else []
        return []

    @staticmethod
    def _scene_cache_entity_ids(scene: dict[str, Any]) -> list[str]:
        entity_ids: list[str] = []
        for key in ("entities", "entities_json"):
            for item in ActionsMixin._json_list_or_empty(scene.get(key)):
                if isinstance(item, dict):
                    entity_id = str(item.get("entity_id") or item.get("entity") or "").strip()
                else:
                    entity_id = str(item or "").strip()
                if entity_id:
                    entity_ids.append(entity_id)
        for key in ("actions", "actions_json"):
            for item in ActionsMixin._json_list_or_empty(scene.get(key)):
                if not isinstance(item, dict):
                    continue
                entity_id = str(item.get("entity_id") or item.get("entity") or "").strip()
                if entity_id:
                    entity_ids.append(entity_id)
        return entity_ids

    @staticmethod
    def _scene_cache_has_light_turn_on(scene: dict[str, Any]) -> bool:
        if any(entity_id.startswith("light.") for entity_id in ActionsMixin._scene_cache_entity_ids(scene)):
            return True
        for key in ("actions", "actions_json"):
            for item in ActionsMixin._json_list_or_empty(scene.get(key)):
                if not isinstance(item, dict):
                    continue
                entity_id = str(item.get("entity_id") or item.get("entity") or "").strip()
                domain = str(item.get("domain") or (entity_id.split(".", 1)[0] if "." in entity_id else "")).strip()
                service = str(item.get("service") or "").strip()
                if domain == "light" and service in {"turn_on", "light.turn_on"}:
                    return True
        return False

    def _ai_scene_cache_row_for_entity(self, entity_id: str) -> dict[str, Any] | None:
        target = str(entity_id or "").strip()
        local_id = target.split(".", 1)[-1] if "." in target else target
        numeric_id = local_id[3:] if local_id.startswith("ai_") else ""
        for scene in getattr(self, "_ai_scenes_cache", []) or []:
            if not isinstance(scene, dict):
                continue
            scene_ids = {
                str(scene.get("id") or "").strip(),
                str(scene.get("source_id") or "").strip(),
                str(scene.get("entity_id") or "").strip(),
                str(scene.get("ha_entity_id") or "").strip(),
                str(scene.get("scene_entity_id") or "").strip(),
            }
            if target in scene_ids or local_id in scene_ids or (numeric_id and numeric_id in scene_ids):
                return scene
        return None

    def _scene_or_script_looks_like_lighting(
        self,
        entity_id: str,
        *,
        reason: str,
        scene_desc: str,
        trigger_summary: str,
    ) -> bool:
        scene = self._ai_scene_cache_row_for_entity(entity_id)
        if scene is not None and self._scene_cache_has_light_turn_on(scene):
            return True
        text = f"{entity_id} {reason} {scene_desc} {trigger_summary}".lower()
        if scene is None:
            # Unknown scene/script bodies may hide light.turn_on; automatic
            # presence-triggered daylight AI scenes fail closed.
            local_id = str(entity_id or "").split(".", 1)[-1]
            if local_id.startswith("ai_") or "[scene path]" in text or "ai_scene" in text:
                return True

        return any(
            marker in text
            for marker in (
                "light",
                "lighting",
                "lamp",
                "turn_on",
                "开灯",
                "灯",
                "照明",
                "补光",
            )
        )

    @staticmethod
    def _append_lighting_metadata(parts: list[str], value: Any) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for nested in value.values():
                ActionsMixin._append_lighting_metadata(parts, nested)
            return
        if isinstance(value, (list, tuple, set)):
            for nested in value:
                ActionsMixin._append_lighting_metadata(parts, nested)
            return
        parts.append(str(value))

    def _entity_looks_like_lighting(
        self,
        entity_id: str,
        domain: str,
        *,
        reason: str,
        scene_desc: str,
        trigger_summary: str,
    ) -> bool:
        if domain == "light":
            return True
        if domain in ("scene", "script"):
            return self._scene_or_script_looks_like_lighting(
                entity_id,
                reason=reason,
                scene_desc=scene_desc,
                trigger_summary=trigger_summary,
            )
        if domain != "switch":
            return False

        info = {}
        try:
            info = (getattr(self, "device_info", {}) or {}).get(entity_id, {}) or {}
        except Exception:
            info = {}

        parts: list[str] = [entity_id]
        if isinstance(info, dict):
            for key in (
                "name",
                "friendly_name",
                "role",
                "device_role",
                "device_type",
                "fixture_type",
                "device_class",
                "capability",
                "capabilities",
                "roles",
                "fixture_roles",
                "tags",
            ):
                self._append_lighting_metadata(parts, info.get(key))

        text = (
            " ".join(parts)
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
            .replace(".", "_")
            .replace("/", "_")
        )
        tokens = {token for token in text.split("_") if token}
        token_markers = {
            "light",
            "lighting",
            "lamp",
            "led",
            "bulb",
            "fixture",
            "deng",
            "zhaoming",
        }
        if tokens & token_markers:
            return True
        return any(
            marker in text
            for marker in (
                "wall_lamp",
                "ceiling_light",
                "spotlight",
                "downlight",
                "shedeng",
                "tongdeng",
                "bideng",
                "qiangdeng",
                "deng_guang",
                "zhao_ming",
                "she_deng",
                "tong_deng",
                "bi_deng",
                "qiang_deng",
                "灯",
                "灯光",
                "照明",
                "射灯",
                "筒灯",
                "壁灯",
                "顶灯",
            )
        )

    def _normalize_room_occupancy_entries(self, entries: Any) -> list[tuple[str, str]]:
        normalized: list[tuple[str, str]] = []
        for item in entries or []:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            normalized.append((str(item[0]), str(item[1]).lower()))
        return normalized

    def _legacy_room_occupancy_entries(self, room: str) -> list[tuple[str, str]]:
        if not room or not hasattr(self, "_get_room_occupancy_map"):
            return []
        try:
            occ_map = self._get_room_occupancy_map()
        except Exception:
            return []
        if not isinstance(occ_map, dict):
            return []
        entries = occ_map.get(room) or []
        return self._normalize_room_occupancy_entries(entries)

    @staticmethod
    def _space_candidate_values(*values: Any) -> list[str]:
        candidates: list[str] = []
        for value in values:
            if isinstance(value, dict):
                nested = (
                    value.get("id"),
                    value.get("space_id"),
                    value.get("room_id"),
                    value.get("room"),
                    value.get("space"),
                    value.get("area"),
                    value.get("name"),
                    value.get("display_name"),
                    value.get("label"),
                    value.get("localized_space"),
                    value.get("localized_spaces"),
                    value.get("aliases"),
                )
                for item in ActionsMixin._space_candidate_values(*nested):
                    if item not in candidates:
                        candidates.append(item)
                continue
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    for candidate in ActionsMixin._space_candidate_values(item):
                        if candidate not in candidates:
                            candidates.append(candidate)
                continue
            candidate = str(value or "").strip()
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        return candidates

    def _action_entity_space_candidates(self, entity_id: str) -> list[str]:
        info = self.device_info.get(entity_id, {}) if isinstance(getattr(self, "device_info", {}), dict) else {}
        if not isinstance(info, dict):
            info = {}
        candidates = self._space_candidate_values(
            info.get("space_id"),
            info.get("room_id"),
            info.get("room"),
            info.get("area"),
            info.get("control_zone"),
            info.get("control_space_id"),
            info.get(DEVICE_CAP_KEY_COVERAGE_SPACES),
            info.get("coverage_space_ids"),
        )
        if hasattr(self, "_get_entity_area"):
            try:
                area = str(self._get_entity_area(entity_id) or "").strip()
            except Exception:
                area = ""
            if area and area not in candidates:
                candidates.append(area)
        return candidates

    def _legacy_room_occupancy_entries_for_candidates(
        self,
        room: str,
        room_candidates: list[str] | None = None,
    ) -> list[tuple[str, str]]:
        if not hasattr(self, "_get_room_occupancy_map"):
            return []
        try:
            occ_map = self._get_room_occupancy_map()
        except Exception:
            return []
        if not isinstance(occ_map, dict):
            return []
        for candidate in self._space_candidate_values(room, room_candidates or []):
            entries = occ_map.get(candidate) or []
            if entries:
                return self._normalize_room_occupancy_entries(entries)
        return []

    def _presence_snapshot_room_payload(
        self,
        snapshot: Any,
        room: str,
        room_candidates: list[str] | None = None,
    ) -> Any:
        if not isinstance(snapshot, dict) or not room:
            return None
        candidate_keys = {
            candidate.casefold()
            for candidate in self._space_candidate_values(room, room_candidates or [])
        }

        def _matches(raw_room: Any, payload: Any) -> bool:
            values = self._space_candidate_values(raw_room, payload if isinstance(payload, dict) else {})
            return bool(candidate_keys.intersection(value.casefold() for value in values))

        rooms = snapshot.get("rooms")
        if isinstance(rooms, dict):
            for raw_room, payload in rooms.items():
                if _matches(raw_room, payload):
                    return payload
        elif isinstance(rooms, list):
            for payload in rooms:
                if not isinstance(payload, dict):
                    continue
                raw_room = payload.get("room") or payload.get("space") or payload.get("space_id") or ""
                if _matches(raw_room, payload):
                    return payload
        raw_room = snapshot.get("room") or snapshot.get("space") or snapshot.get("space_id") or ""
        if raw_room and _matches(raw_room, snapshot):
            return snapshot
        return None

    def _canonical_room_occupancy_entries(
        self,
        room: str,
        room_candidates: list[str] | None = None,
    ) -> list[tuple[str, str]]:
        getter = getattr(self, "get_presence_snapshot", None)
        if not room or not callable(getter):
            return []
        try:
            snapshot = getter()
        except Exception:
            return []
        payload = self._presence_snapshot_room_payload(snapshot, room, room_candidates)
        if isinstance(payload, str):
            payload = {"state": payload}
        if not isinstance(payload, dict):
            return []
        raw_state = payload.get("state") or payload.get("presence") or payload.get("occupancy") or ""
        state = str(raw_state).strip().lower()
        if state in {"occupied", "present", "on", "home", "motion", "person"}:
            mapped_state = "on"
            evidence_ids = (
                payload.get("occupied_evidence_ids")
                or payload.get("evidence_ids")
                or payload.get("source_evidence_ids")
                or ()
            )
        elif state in {"vacant", "clear", "off", "away", "none", "idle", "empty"}:
            mapped_state = "off"
            evidence_ids = (
                payload.get("vacant_evidence_ids")
                or payload.get("evidence_ids")
                or payload.get("source_evidence_ids")
                or ()
            )
        else:
            mapped_state = "unknown"
            evidence_ids = (
                payload.get("evidence_ids")
                or payload.get("source_evidence_ids")
                or payload.get("occupied_evidence_ids")
                or payload.get("vacant_evidence_ids")
                or ()
            )
        if isinstance(evidence_ids, str):
            evidence = [evidence_ids]
        else:
            evidence = [str(eid or "") for eid in evidence_ids or () if str(eid or "").strip()]
        if not evidence:
            evidence = [f"presence.{room}"]
        return [(eid, mapped_state) for eid in evidence]

    def _presence_entries_conflict(
        self,
        canonical: list[tuple[str, str]],
        legacy: list[tuple[str, str]],
    ) -> bool:
        if not canonical or not legacy:
            return False
        canonical_states = {state for _, state in canonical}
        legacy_states = {state for _, state in legacy}
        return canonical_states != legacy_states

    def _record_presence_guard_conflict(
        self,
        room: str,
        canonical: list[tuple[str, str]],
        legacy: list[tuple[str, str]],
    ) -> None:
        conflict = {
            "reason": "canonical_presence_conflict",
            "room": room,
            "canonical": [{"entity_id": eid, "state": state} for eid, state in canonical],
            "legacy": [{"entity_id": eid, "state": state} for eid, state in legacy],
        }
        self._last_presence_guard_conflict = conflict
        logger = getattr(self, "_sys_log", None)
        if callable(logger):
            canonical_str = ", ".join(f"{eid}={state}" for eid, state in canonical[:3])
            legacy_str = ", ".join(f"{eid}={state}" for eid, state in legacy[:3])
            logger(
                "INFO",
                f"[PresenceGuard] canonical_presence_conflict room={room} canonical=({canonical_str}) legacy=({legacy_str})",
            )

    def _room_occupancy_entries_with_source(
        self,
        room: str,
        room_candidates: list[str] | None = None,
    ) -> tuple[list[tuple[str, str]], str]:
        canonical = self._canonical_room_occupancy_entries(room, room_candidates)
        legacy = self._legacy_room_occupancy_entries_for_candidates(room, room_candidates)
        if canonical:
            if self._presence_entries_conflict(canonical, legacy):
                self._record_presence_guard_conflict(room, canonical, legacy)
            else:
                self._last_presence_guard_conflict = {}
            return canonical, "canonical_presence_snapshot"
        self._last_presence_guard_conflict = {}
        return legacy, "legacy_occupancy_map" if legacy else ""

    def _room_occupancy_entries(self, room: str, room_candidates: list[str] | None = None) -> list[tuple[str, str]]:
        entries, _source = self._room_occupancy_entries_with_source(room, room_candidates)
        return entries

    def _occupancy_guard_check(self, entity_id: str, service: str) -> tuple[bool, str]:
        if service != "turn_on":
            return False, ""
        room = self._action_entity_room(entity_id)
        room_candidates = self._action_entity_space_candidates(entity_id)
        if not room and room_candidates:
            room = room_candidates[0]
        sensors = self._room_occupancy_entries(room, room_candidates)
        if not room or not sensors:
            return False, ""
        occupied = any(state == "on" for _, state in sensors)
        uncertain = any(state in ("unknown", "unavailable") for _, state in sensors)
        if occupied or uncertain:
            return False, ""
        sensor_str = ", ".join(f"{eid}={state}" for eid, state in sensors[:3])
        return True, f"{room} no occupied sensor evidence ({sensor_str})"

    def _turnoff_presence_guard(self, entity_id: str, service: str) -> tuple[bool, str]:
        self._last_turnoff_presence_guard_detail = {}
        if service != "turn_off":
            return False, ""
        room = self._action_entity_room(entity_id)
        room_candidates = self._action_entity_space_candidates(entity_id)
        if not room and room_candidates:
            room = room_candidates[0]
        sensors, presence_source = self._room_occupancy_entries_with_source(room, room_candidates)
        if not room or not sensors:
            return False, ""
        occupied = [(eid, state) for eid, state in sensors if state == "on"]
        uncertain = [(eid, state) for eid, state in sensors if state in ("unknown", "unavailable")]
        if not occupied and not uncertain:
            return False, ""
        blocked = occupied or uncertain
        sensor_str = ", ".join(f"{eid}={state}" for eid, state in blocked[:3])
        detail: dict[str, Any] = {
            "presence_source": presence_source or "unknown",
            "presence_reason": "presence_not_clear",
            "presence_room": room,
            "presence_evidence_ids": [eid for eid, _state in blocked if str(eid or "").strip()],
            "presence_states": [
                {"entity_id": eid, "state": state}
                for eid, state in blocked
                if str(eid or "").strip()
            ],
        }
        conflict = getattr(self, "_last_presence_guard_conflict", None)
        if isinstance(conflict, dict) and conflict:
            detail["presence_conflict"] = dict(conflict)
        self._last_turnoff_presence_guard_detail = detail
        return True, f"{room} presence not clear ({sensor_str})"

    def _get_action_device_capability(self, entity_id: str) -> dict[str, Any]:
        """统一动作层设备能力读取面（Wave 1B）。"""
        if hasattr(self, "get_device_capability"):
            try:
                cap = self.get_device_capability(entity_id)
                if isinstance(cap, dict):
                    return cap
            except Exception:
                pass
        info = self.device_info.get(entity_id, {}) or {}
        room = (info.get("room") or "").strip()
        return {
            "entity_id": entity_id,
            "control_mode": info.get("control_mode", "shared"),
            "role": info.get("role", ""),
            "control_zone": info.get("control_zone", room),
            "disturbance_level": info.get("disturbance_level", ""),
            "room": room,
        }

    @staticmethod
    def _is_truthy_shared_fixture(value: Any) -> bool:
        """统一 shared_fixture 真值判定（与设备能力快照语义对齐）。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on", "explicit"}
        return False

    @staticmethod
    def _normalize_coverage_spaces(value: Any) -> list[str]:
        """规范化 coverage_spaces，过滤空值并去重保序。"""
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            space = str(item or "").strip()
            if space and space not in normalized:
                normalized.append(space)
        return normalized

    def _resolve_action_control_spaces(self, capability: dict[str, Any]) -> set[str]:
        """统一动作层控制空间集合解析（shared_fixture + coverage_spaces）。"""
        room = str((capability.get("room") or "")).strip()
        control_zone = str((capability.get("control_zone") or "")).strip()
        coverage_spaces = self._normalize_coverage_spaces(
            capability.get(DEVICE_CAP_KEY_COVERAGE_SPACES)
        )
        shared_fixture = self._is_truthy_shared_fixture(
            capability.get(DEVICE_CAP_KEY_SHARED_FIXTURE)
        )

        spaces = {s for s in (room, control_zone) if s}
        if shared_fixture and coverage_spaces:
            spaces.update(coverage_spaces)
        return spaces

    def _is_cross_zone_action(self, trigger_room: str, capability: dict[str, Any]) -> bool:
        """最小跨区判定入口：供执行期裁决复用，不改变现有判定结论。"""
        if not trigger_room:
            return False
        control_spaces = self._resolve_action_control_spaces(capability)
        if not control_spaces:
            return False
        return trigger_room not in control_spaces

    # ── 动作标准化 ────────────────────────────────────────────────────────────

    def _normalize_action(self, action: dict) -> dict:
        """Normalize AI action dict to canonical field names."""
        _target = action.get("target")
        _target_eid = _target.get("entity_id", "") if isinstance(_target, dict) else ""
        entity_id = action.get("entity_id") or action.get("entity") or _target_eid
        service_raw = action.get("service") or action.get("action") or action.get("command") or ""
        # Support "light.turn_on" format
        if "." in service_raw and not action.get("domain"):
            parts = service_raw.split(".", 1)
            domain = parts[0]
            service = parts[1]
        else:
            domain = action.get("domain") or (entity_id.split(".")[0] if entity_id else "")
            service = service_raw
        params = action.get("params") or action.get("data") or action.get("service_data") or {}

        # entity_id 校验与修正：AI 有时返回设备名而非合法 entity_id
        if entity_id and not self.hass.states.get(entity_id):
            matched = self._fuzzy_match_entity(entity_id, domain)
            if matched:
                self._sys_log("WARN", f"[动作修正] AI 返回无效 entity_id「{entity_id}」→ 修正为「{matched}」")
                entity_id = matched
                domain = entity_id.split(".")[0]
            else:
                # 保留原始（疑似幻觉）entity_id，交由执行层防幻觉硬闸显式拒绝并记入 rejected，
                # 以便 AI 决策页能呈现“为什么没动”，而不是在此静默置空丢弃。
                self._sys_log("ERROR", f"[动作修正] AI 返回无效 entity_id「{entity_id}」且无法匹配到已知设备，交由执行层硬闸拒绝")

        # 极低亮度的 turn_on 等同于关灯，规范化为 turn_off 以统一走守卫逻辑。
        # AI 有时用此手段绕过 Product Rule P1 "禁止 turn_off 展厅灯" 的限制，必须在此拦截。
        brightness_pct = None
        if service == "turn_on" and domain == "light" and isinstance(params, dict) and "brightness_pct" in params:
            try:
                brightness_pct = int(float(params.get("brightness_pct")))
            except (TypeError, ValueError):
                brightness_pct = None
        if (
            service == "turn_on"
            and domain == "light"
            and brightness_pct is not None
            and 0 <= brightness_pct <= self._DIM_TO_OFF_BRIGHTNESS_PCT
        ):
            self._sys_log("WARN",
                f"[动作规范化] {entity_id} turn_on(brightness_pct={brightness_pct}) 等效关灯，转换为 turn_off"
                "（防止绕过 Product Rule P1 保护）")
            service = "turn_off"
            params = {}

        # turn_off / close 时清理无意义的亮度/温度参数
        if service in ("turn_off", "close_cover", "lock") and params:
            cleaned = {k: v for k, v in params.items() if k not in ACTION_PARAM_KEYS_USELESS_WHEN_OFF}
            if len(cleaned) != len(params):
                self._sys_log("INFO", f"[动作清理] {service} 移除无效参数: "
                              f"{set(params.keys()) - set(cleaned.keys())}")
            params = cleaned

        return {"entity_id": entity_id, "domain": domain, "service": service,
                "params": params, "reason": action.get("reason", ""),
                "delay_seconds": action.get("delay_seconds", 0),
                "runtime_hints": action.get("runtime_hints") or {}}

    def _fuzzy_match_entity(self, bad_id: str, domain_hint: str) -> str | None:
        """Try to match a bad entity_id (device name) to a real entity_id."""
        bad_lower = bad_id.lower().replace("（", "(").replace("）", ")")
        # 先按空格/括号拆分，再按 . 和 _ 进一步拆分（支持 light.zhan_ting_zhong_jian → zhong, jian 等片段）
        raw_parts = bad_lower.replace("[", " ").replace("]", " ").replace("(", " ").replace(")", " ").split()
        keywords: list[str] = []
        for part in raw_parts:
            # 按 . 和 _ 拆分，取 长度≥2 的片段
            sub = [s for s in part.replace(".", "_").split("_") if len(s) >= 2]
            keywords.extend(sub if sub else [part])
        # 剔除 domain 结构前缀（如 light/switch/scene）：每个该域实体 eid 都含此前缀，
        # 若保留它会让任意幻觉实体（如 light.玄关）凭域名前缀命中真实设备并被错误“修正”。
        _domain_token = (domain_hint or "").strip().lower()
        keywords = [kw for kw in dict.fromkeys(keywords) if kw and kw != _domain_token]
        best_match = ""
        best_score = 0
        for eid, info in self.device_info.items():
            if domain_hint and not eid.startswith(domain_hint + "."):
                continue
            name = info.get("name", "").lower()
            score = sum(1 for kw in keywords if kw in name or kw in eid.lower())
            if score > best_score:
                best_score = score
                best_match = eid
        # script/scene 不在 device_info 中，需额外搜索 HA 状态
        if not best_match and domain_hint in ("script", "scene"):
            for state in self.hass.states.async_all(domain_hint):
                name = (state.attributes.get("friendly_name") or "").lower()
                score = sum(1 for kw in keywords if kw in name or kw in state.entity_id.lower())
                if score > best_score:
                    best_score = score
                    best_match = state.entity_id
        return best_match if best_score > 0 else None

    # ── Action Router ─────────────────────────────────────────────────────────

    def _find_associated_script(self, entity_id: str, service: str) -> str | None:
        """Action Router: 根据设备 entity_id 和 service 查找最匹配的 HA 脚本/场景。

        优先级：
          1. 激活的 AI 场景（包含此设备 + 当前时段匹配）→ 直接路由至 scene.ai_<id>
          2. 人工 HA 脚本/场景（名称模糊匹配）
        """
        import json as _json
        from .const import AI_SCENE_STATUS_ACTIVE, ai_scene_matches_now

        is_on = "turn_on" in service or "open" in service

        # ── 1. 检查激活的 AI 场景（时段匹配 + 包含此设备 + 方向一致）────────
        # 使用 ai_scene_matches_now() 统一星期格式（SQLite %w，0=日），
        # 修复之前直接用 Python weekday（0=Mon）导致工作日匹配失效的 Bug。
        if is_on:
            _now = self._ha_local_now()
            for sc in getattr(self, "_ai_scenes_cache", []):
                if sc.get("status") != AI_SCENE_STATUS_ACTIVE:
                    continue
                if not ai_scene_matches_now(sc, _now.hour, _now.weekday()):
                    continue
                # 包含目标设备检查
                try:
                    ents = _json.loads(sc.get("entities_json", "[]"))
                except Exception:
                    continue
                if not any(e.get("entity_id") == entity_id for e in ents):
                    continue
                # 确认对应 HA 场景实体存在
                ha_eid = f"scene.ai_{sc['id']}"
                if self.hass.states.get(ha_eid) is not None:
                    self._sys_log(
                        "INFO",
                        f"[Action Router] {entity_id} → 匹配激活 AI 场景 {sc['name']} → {ha_eid}"
                    )
                    return ha_eid

        # ── 2. 搜索 HA 脚本和人工场景（原有逻辑）────────────────────────────
        dev = self.device_info.get(entity_id, {})
        dev_name = dev.get("name", "").lower()
        dev_room = dev.get("room", "").lower()
        domain = entity_id.split(".")[0]
        is_off = "turn_off" in service or "close" in service
        on_kw = ("开", "turn_on", "open", "亮", "_on")
        off_kw = ("关", "turn_off", "close", "暗", "_off")
        candidates = self._ha_scripts + self._ha_scenes
        best: str | None = None
        best_score = 0
        for cand in candidates:
            ceid = cand["entity_id"]
            cname = cand["name"].lower()
            score = 0
            # 脚本/场景名含设备名 → 强匹配（设备名至少 2 字符才视为有效匹配）
            if dev_name and len(dev_name) >= 2 and dev_name in cname:
                score += 10
            # 脚本/场景名含房间名 → 中等匹配（房间名至少 2 字符）
            elif dev_room and len(dev_room) >= 2 and dev_room in cname:
                score += 5
            # 方向匹配（开/关）
            if is_on and any(k in cname for k in on_kw):
                score += 3
            elif is_off and any(k in cname for k in off_kw):
                score += 3
            # 域名匹配
            if domain in cname or (domain == "light" and "灯" in cname):
                score += 2
            if score >= 8 and score > best_score:
                best_score = score
                best = ceid
        return best

    # ── 动作执行主入口 ────────────────────────────────────────────────────────

    async def _execute_actions(
        self,
        actions: list,
        trigger_summary: str = "",
        scene_desc: str = "",
        confidence: int = 0,
        trigger_room: str = "",
        is_global_cmd: bool = False,
        cmd_source: str = "",
        parent_transaction_id: str = "",
        world_snapshot_id: str = "",
        correlation_id: str = "",
        active_space_id: str = "",
        decision_time: str = "",
        require_world_snapshot_guard: bool = False,
    ) -> int:
        """Execute a list of AI actions with transaction tracking."""
        import json as _json

        correlation_id = str(correlation_id or "").strip()

        if not actions:
            return self._action_execution_result(0, correlation_id=correlation_id)

        original_actions = list(actions)
        action_positions: dict[int, list[int]] = {}
        for original_index, original_action in enumerate(original_actions):
            action_positions.setdefault(id(original_action), []).append(original_index)
        claimed_positions: set[int] = set()
        ordered_result_slots: dict[int, dict[str, Any]] = {}
        guard_pre_states: dict[str, str] = {}

        def _claim_action_position(action: Any) -> int:
            for position in action_positions.get(id(action), []):
                if position not in claimed_positions:
                    claimed_positions.add(position)
                    return position
            for position in range(len(original_actions)):
                if position not in claimed_positions:
                    claimed_positions.add(position)
                    return position
            return len(original_actions) + len(claimed_positions)

        def _remember_result(position: int, result: dict[str, Any]) -> None:
            if correlation_id:
                result["correlation_id"] = correlation_id
            ordered_result_slots[position] = result

        def _ordered_results() -> list[dict[str, Any]]:
            return [
                ordered_result_slots[position]
                for position in sorted(ordered_result_slots)
            ]

        def _remember_guard_pre_state(action: dict[str, Any]) -> None:
            entity_id = action.get("entity_id") or action.get("entity")
            if not isinstance(entity_id, str) or "." not in entity_id:
                return
            state = self.hass.states.get(entity_id)
            if state:
                guard_pre_states[entity_id] = state.state

        # ── 区域隔离守卫校验 (AI-03) ──
        # 若有明确触发区域且非全局指令，过滤掉不属于该区域且非全局属性的动作
        # 允许的例外：巡检、位置变化、Frigate视觉触发（通常涉及多区域）
        # USER_EXPLICIT（用户主动指令/一次性场景/语音）豁免区域隔离，与 IntentVerifier 保持一致
        _SKIP_ISOLATION = ("巡检", "位置变化", "视觉检测")
        _USER_EXPLICIT = "USER_EXPLICIT"
        _is_user_explicit = (cmd_source == _USER_EXPLICIT)
        should_isolate = bool(
            trigger_room
            and not is_global_cmd
            and not _is_user_explicit
            and not any(k in trigger_summary for k in _SKIP_ISOLATION)
        )
        
        if should_isolate:
            filtered_actions = []
            for a in actions:
                eid = a.get("entity_id") or a.get("entity")
                if not eid: continue
                cap = self._get_action_device_capability(eid)
                dev_room = (cap.get("room") or "").strip()
                if not dev_room and hasattr(self, "_get_entity_area"):
                    dev_room = (self._get_entity_area(eid) or "").strip()
                cap = {**cap, "room": dev_room}

                # 隔离规则（与 IntentVerifier._stage1_semantic_check 保持完全一致）：
                # 1. 设备所在房间匹配触发房间 -> 放行
                # 2. 豁免域 (climate/cover/scene/script/vacuum) -> 放行
                # 3. action 本身标记了 is_global (LLM 合法跨区指令) -> 放行
                # 4. 房间信息经 device_info + Registry 双重查找后仍为空 -> 放行（全局设备）
                #    注意：仅靠 device_info 为空就豁免是不安全的，已在 _get_entity_area 回退后才豁免
                _domain = (a.get("domain") or eid.split(".")[0]) if isinstance(eid, str) else ""
                is_cross_zone = self._is_cross_zone_action(trigger_room, cap)
                control_spaces = self._resolve_action_control_spaces(cap)
                has_adjacent_space = any(
                    hasattr(self, "_is_adjacent_room") and self._is_adjacent_room(trigger_room, space)
                    for space in control_spaces
                    if space
                )
                is_exempt = (
                    (not dev_room and not cap.get("control_zone"))
                    or not is_cross_zone
                    or _domain in ("climate", "cover", "scene", "script", "vacuum")
                    or a.get("is_global", False)
                    or has_adjacent_space
                )

                if is_exempt:
                    filtered_actions.append(a)
                else:
                    self._sys_log("WARN", f"[区域隔离] 拦截跨区域操作: {eid}(属于{dev_room})，本次触发于「{trigger_room}」")
                    _msg = f"cross_zone_isolation: {eid} belongs to {dev_room or 'unknown'}; trigger_room={trigger_room}"
                    _result = {
                        "domain": str(_domain or ""),
                        "service": str(a.get("service") or ""),
                        "entity_id": str(eid or ""),
                        "status": "blocked_cross_zone_isolation",
                        "msg": _msg,
                        "error": _msg,
                        "error_type": "cross_zone_isolation",
                    }
                    if scene_desc:
                        _result["scene_desc"] = scene_desc
                    if trigger_summary:
                        _result["trigger_summary"] = trigger_summary
                    _remember_result(_claim_action_position(a), _result)
                    _remember_guard_pre_state(a)
            
            if len(filtered_actions) < len(actions):
                self._sys_log("INFO", f"[区域隔离] 动作集已精简: {len(actions)} -> {len(filtered_actions)} (拦截了 {len(actions)-len(filtered_actions)} 个跨区域动作)")
                actions = filtered_actions
                if not actions:
                    ordered_guard_results = _ordered_results()
                    txn_id: int = await self.hass.async_add_executor_job(
                        self._begin_transaction_db,
                        trigger_summary,
                        scene_desc,
                        confidence,
                        len(original_actions),
                        _json.dumps(guard_pre_states, ensure_ascii=False),
                        _json.dumps(original_actions, ensure_ascii=False, default=str),
                    )
                    if not txn_id:
                        return self._action_execution_result(
                            0,
                            results=ordered_guard_results,
                            pre_states=guard_pre_states,
                            correlation_id=correlation_id,
                        )
                    await self.hass.async_add_executor_job(
                        self._complete_transaction_db,
                        txn_id,
                        0,
                        len(ordered_guard_results),
                        0,
                        _json.dumps(ordered_guard_results, ensure_ascii=False),
                    )
                    return self._action_execution_result(
                        0,
                        transaction_id=txn_id,
                        results=ordered_guard_results,
                        pre_states=guard_pre_states,
                        correlation_id=correlation_id,
                    )

        if not actions:
            return self._action_execution_result(0, correlation_id=correlation_id)

        # ── 自触发保护快速预过滤 ────────────────────────────────────────────────
        # 在动作执行前提前过滤掉触发了本次推理的可控设备，避免浪费完整 LLM 推理后才在
        # _do_call_service 逐设备拦截（该拦截仍保留作最后一道防线）。
        # 注意：仅过滤 turn_on（防止触发灯被 AI 原地开回）；turn_off 通常是合理的关灯指令。
        if self._batch_trigger_controllable:
            _pre_filtered = []
            _pre_blocked = []
            for _a in actions:
                _eid = _a.get("entity_id") or _a.get("entity")
                _svc = _a.get("service", "")
                if _eid and _svc == "turn_on" and _eid in self._batch_trigger_controllable:
                    _pre_blocked.append(_eid)
                    _domain = str(_a.get("domain") or (_eid.split(".", 1)[0] if isinstance(_eid, str) and "." in _eid else ""))
                    _guard = evaluate_self_trigger_protection(
                        entity_id=_eid,
                        service=_svc,
                        trigger_entities=self._batch_trigger_controllable,
                    )
                    _msg = _guard.msg or f"self_trigger_protection: {_eid} triggered current inference; rejected {_svc}"
                    _result = {
                        "domain": _domain,
                        "service": str(_svc or ""),
                        "entity_id": str(_eid or ""),
                        "status": _guard.status or "blocked_self_trigger",
                        "msg": _msg,
                        "error": _msg,
                        "error_type": _guard.error_type or "self_trigger_protection",
                    }
                    if scene_desc:
                        _result["scene_desc"] = scene_desc
                    if trigger_summary:
                        _result["trigger_summary"] = trigger_summary
                    _remember_result(_claim_action_position(_a), _result)
                    _remember_guard_pre_state(_a)
                else:
                    _pre_filtered.append(_a)
            if _pre_blocked:
                self._sys_log("INFO",
                    f"[自触发预过滤] 移除 {len(_pre_blocked)} 个自触发设备的 turn_on 动作: "
                    f"{', '.join(_pre_blocked)}"
                )
                actions = _pre_filtered
            if not actions:
                self._sys_log("INFO", "[自触发预过滤] 所有动作均为自触发设备，跳过执行")
                ordered_guard_results = _ordered_results()
                _txn_id: int = await self.hass.async_add_executor_job(
                    self._begin_transaction_db,
                    trigger_summary,
                    scene_desc,
                    confidence,
                    len(original_actions),
                    _json.dumps(guard_pre_states, ensure_ascii=False),
                    _json.dumps(original_actions, ensure_ascii=False, default=str),
                )
                if not _txn_id:
                    return self._action_execution_result(
                        0,
                        results=ordered_guard_results,
                        pre_states=guard_pre_states,
                        correlation_id=correlation_id,
                    )
                await self.hass.async_add_executor_job(
                    self._complete_transaction_db,
                    _txn_id,
                    0,
                    len(ordered_guard_results),
                    0,
                    _json.dumps(ordered_guard_results, ensure_ascii=False),
                )
                return self._action_execution_result(
                    0,
                    transaction_id=_txn_id,
                    results=ordered_guard_results,
                    pre_states=guard_pre_states,
                    correlation_id=correlation_id,
                )

        # ── 1. 执行前：快照目标设备当前状态 ─────────────────────────────────
        pre_states: dict[str, str] = dict(guard_pre_states)
        normalized_actions: list[tuple[int, dict, dict]] = []
        for raw in actions:
            action = self._normalize_action(raw)
            normalized_actions.append((_claim_action_position(raw), raw, action))
            eid = action.get("entity_id", "")
            if eid and isinstance(eid, str) and "." in eid:
                st = self.hass.states.get(eid)
                if st:
                    pre_states[eid] = st.state

        # ── 2. 写入事务记录（pending）────────────────────────────────────────
        txn_id: int = await self.hass.async_add_executor_job(
            self._begin_transaction_db,
            trigger_summary,
            scene_desc,
            confidence,
            len(original_actions),
            _json.dumps(pre_states, ensure_ascii=False),
            _json.dumps(original_actions, ensure_ascii=False, default=str),
        )
        if not txn_id:
            self._sys_log("WARN", "[事务] 事务记录写入失败（DB锁/磁盘等），已中止动作执行以保持审计一致性")
            for _position, _raw_action, _action in normalized_actions:
                _entity_id = str(_action.get("entity_id") or "")
                _params = _action.get("params")
                _result = {
                    "domain": str(_action.get("domain") or ""),
                    "service": str(_action.get("service") or ""),
                    "entity_id": _entity_id,
                    "status": "blocked_or_error",
                    "msg": "transaction_start_failed",
                    "error": "transaction_start_failed",
                    "error_type": "transaction_start_failed",
                    "ha_command_status": "not_dispatched",
                }
                if isinstance(_params, dict) and _params:
                    _result["params"] = dict(_params)
                _reason = str(_action.get("reason") or "").strip()
                if _reason:
                    _result["reason"] = _reason
                if scene_desc:
                    _result["scene_desc"] = scene_desc
                if trigger_summary:
                    _result["trigger_summary"] = trigger_summary
                _remember_result(_position, _result)
            ordered_failure_results = _ordered_results()
            return self._action_execution_result(
                0,
                results=ordered_failure_results,
                pre_states=pre_states,
                correlation_id=correlation_id,
            )

        # ── 3. 执行所有动作，收集结果 ────────────────────────────────────────
        executed = 0
        blocked_count = len(ordered_result_slots)
        failed_count = 0
        guard_result_count = len(ordered_result_slots)
        results: list[dict] = _ordered_results()
        parent_transaction_id = str(parent_transaction_id or "").strip()
        parent_decision_trace: dict[str, Any] = {}
        if parent_transaction_id:
            parent_decision_trace = {
                "available": True,
                "transaction_id": parent_transaction_id,
                "url": f"/decision-trace/{parent_transaction_id}",
            }

        # Product Rule P1 优化：提前获取展厅兼容在场证据、灯光层级与人数锁定规则，避免循环内重复调用
        # Contract: legacy_presence_evidence_only; canonical presence guards use _room_occupancy_entries().
        legacy_occ_map = self._get_room_occupancy_map()
        people_counts_by_room = self._get_room_person_counts() if hasattr(self, "_get_room_person_counts") else {}
        parsed_people_rules = self._build_locked_people_rules() if hasattr(self, "_build_locked_people_rules") else []

        _now_min = self._ha_local_minute_of_day()
        is_working_hour = (
            _now_min is not None
            and self.showroom_biz_start_min <= _now_min < self.showroom_biz_end_min
        )
        
        # 预取展厅有人状态
        is_showroom_occupied = False
        showroom_light_tiers = {}
        if self._mode == MODE_SHOWROOM:
            _showroom_area = self.showroom_area_name
            showroom_sensors = legacy_occ_map.get(_showroom_area, []) if _showroom_area else []
            if not showroom_sensors:
                is_showroom_occupied = True
            else:
                is_showroom_occupied = any(s == "on" for _, s in showroom_sensors)
                if not is_showroom_occupied and all(s in ("unknown", "unavailable") for _, s in showroom_sensors):
                    is_showroom_occupied = True

            # 预取所有展厅灯的层级信息（v2：优先使用基线分数）
            for eid, info in self.device_info.items():
                if not eid.startswith("light."):
                    continue
                _room = info.get("room", "")
                if _showroom_area and _room == _showroom_area and _room not in self.showroom_excluded_subareas:
                    showroom_light_tiers[eid] = await self.hass.async_add_executor_job(self._get_showroom_light_tier_v2, eid)

        # ── Product Rule P2: 动作节拍控制 (Action Pacing) ──
        # 若动作数较多，每个动作之间加入微小延迟，缓解 Zigbee 拥塞
        _is_bulk = len(actions) > 5
        _pacing_delay = 0.2 if _is_bulk else 0.0

        def _result_counts_from_current_results() -> tuple[int, int, int]:
            dispatched_now = sum(1 for item in results if item.get("status") == "ok")
            blocked_now = sum(
                1
                for item in results
                if str(item.get("status") or "").startswith("blocked")
                and item.get("status") != "blocked_or_error"
            )
            failed_now = sum(1 for item in results if item.get("status") == "blocked_or_error")
            return dispatched_now, blocked_now, failed_now

        async def _refresh_transaction_from_results() -> None:
            dispatched_now, blocked_now, failed_now = _result_counts_from_current_results()
            await self.hass.async_add_executor_job(
                self._complete_transaction_db,
                txn_id,
                dispatched_now,
                blocked_now,
                failed_now,
                _json.dumps(results, ensure_ascii=False),
            )

        def _refresh_transaction_from_results_sync() -> None:
            dispatched_now, blocked_now, failed_now = _result_counts_from_current_results()
            self._complete_transaction_db(
                txn_id,
                dispatched_now,
                blocked_now,
                failed_now,
                _json.dumps(results, ensure_ascii=False),
            )

        def _pop_service_call_error_or_unknown(txid: int, aseq: int, eid: str) -> dict[str, Any]:
            detail = self._pop_service_call_error(txid, aseq, eid)
            if detail:
                return detail
            return {
                "msg": "ha_service_returned_false",
                "error": "ha_service_returned_false",
                "error_type": "ha_service_unknown_failure",
                "ha_command_status": "failed",
            }

        for idx, (original_position, raw_action, action) in enumerate(normalized_actions):
            action_seq = original_position + 1
            if idx > 0 and _pacing_delay > 0:
                await asyncio.sleep(_pacing_delay)

            domain = action.get("domain")
            service = action.get("service")
            entity_id = action.get("entity_id")
            params = action.get("params", {})
            reason = action.get("reason", "")
            target_info = self.device_info.get(entity_id, {}) if isinstance(self.device_info, dict) else {}
            if not isinstance(target_info, dict):
                target_info = {}
            target_space_id = str(
                action.get("target_space_id")
                or action.get("space_id")
                or target_info.get("space_id")
                or target_info.get("room_id")
                or target_info.get("area_id")
                or target_info.get("room")
                or target_info.get("area")
                or ""
            ).strip()
            action_result_context = {
                "domain": domain,
                "service": service,
                "entity_id": entity_id,
            }
            if correlation_id:
                action_result_context["correlation_id"] = correlation_id
            if parent_transaction_id:
                action_result_context["execution_transaction_id"] = txn_id
                action_result_context["parent_transaction_id"] = parent_transaction_id
                action_result_context["decision_trace"] = dict(parent_decision_trace)
            if isinstance(params, dict) and params:
                action_result_context["params"] = dict(params)
            if scene_desc:
                action_result_context["scene_desc"] = scene_desc
            if trigger_summary:
                action_result_context["trigger_summary"] = trigger_summary
            if reason:
                action_result_context["reason"] = reason
            raw_target = raw_action.get("target") if isinstance(raw_action, dict) else None
            raw_entity_id = (
                raw_action.get("entity_id")
                or raw_action.get("entity")
                or (raw_target.get("entity_id") if isinstance(raw_target, dict) else None)
            )
            try:
                delay = max(0, int(action.get("delay_seconds", 0)))
            except (ValueError, TypeError):
                delay = 0
            raw_entity_exists = True
            if (
                isinstance(raw_entity_id, str)
                and "." in raw_entity_id
                and domain not in THIN_GATE_STATELESS_DOMAINS
            ):
                raw_entity_exists = self.hass.states.get(raw_entity_id) is not None
            entity_exists = True
            if isinstance(entity_id, str) and domain not in THIN_GATE_STATELESS_DOMAINS:
                entity_exists = self.hass.states.get(entity_id) is not None
            thin_gate = evaluate_thin_execution_gate(
                domain=domain,
                service=service,
                entity_id=entity_id,
                raw_entity_id=raw_entity_id,
                entity_exists=entity_exists,
                raw_entity_exists=raw_entity_exists,
            )
            if not thin_gate.allowed:
                blocked_count += 1
                results.append(thin_gate.to_action_result())
                if thin_gate.log_code == "missing_required_action_fields":
                    self._sys_log("WARN", f"[动作] 字段缺失，跳过: {raw_action} → 标准化后: {action}")
                elif thin_gate.log_code == "domain_not_allowed":
                    self._sys_log("WARN", f"[安全] 拒绝 AI 操作不在白名单中的域: {domain}.{service}({entity_id})")
                elif thin_gate.log_code == "service_blocked":
                    self._sys_log("WARN", f"[安全] 拒绝 AI 执行危险服务: {domain}.{service}({entity_id})")
                elif thin_gate.log_code == "raw_entity_not_found":
                    self._sys_log("WARN", f"[安全] 拒绝原始动作中不存在的实体（防幻觉）: {domain}.{service}({raw_entity_id})")
                elif thin_gate.log_code == "entity_not_found":
                    self._sys_log("WARN", f"[安全] 拒绝操作不存在的实体（防幻觉）: {domain}.{service}({entity_id})")
                continue
            # ─── 设备管辖域 (Action Router) ───────────────────────────────────
            # Run daylight guard before Action Router can rewrite a simple
            # light.turn_on into scene.turn_on/script.turn_on. The guard must
            # evaluate the original light entity and its room context.
            pre_router_auto_presence_lighting = (
                service == "turn_on"
                and self._entity_looks_like_lighting(
                    entity_id,
                    domain,
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                )
                and self._looks_like_automatic_presence_lighting(
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                    cmd_source=str(cmd_source or ""),
                )
            )
            if pre_router_auto_presence_lighting:
                daylight_reason = self._daylight_auto_lighting_suppressed_reason(entity_id)
                if daylight_reason:
                    self._sys_log(
                        "WARN",
                        f"[DaylightGuard] blocked daytime automatic presence lighting {domain}.turn_on({entity_id}): {daylight_reason}",
                    )
                    blocked_count += 1
                    results.append({
                        **action_result_context,
                        "status": "blocked_daylight_auto_lighting",
                        "msg": daylight_reason,
                    })
                    continue
            if domain not in ("script", "scene"):
                ctrl_mode = self.device_info.get(entity_id, {}).get("control_mode", "shared")
                if ctrl_mode == "ha":
                    results.append({
                        "entity_id": entity_id,
                        "service": service,
                        "status": "skip",
                        "msg": "ha_control_mode",
                    })
                    # HA 优先模式：AI 不直接操作，仅记录建议
                    self._sys_log("INFO", f"[管辖域] {entity_id} 为 HA优先模式，AI 跳过直接操作（建议: {service}）")
                    continue
                elif ctrl_mode in ("ai", "shared"):
                    # AI全权 或 共享模式：shared 时尝试关联脚本/场景。
                    # 若是灯光精细参数（亮度/色温/颜色），优先直控设备，避免语义被场景路由吞掉。
                    _is_simple_off_with_params = (
                        service in ("turn_off", "close") and params
                    )
                    _has_precise_light_params = (
                        domain == "light" and service == "turn_on" and any(
                            k in params
                            for k in (
                                "brightness_pct", "brightness", "color_temp", "color_temp_kelvin",
                                "rgb_color", "hs_color", "xy_color", "effect",
                            )
                        )
                    )
                    if ctrl_mode == "shared" and domain in ("light", "switch", "cover", "fan", "climate") \
                            and service in ("turn_on", "turn_off", "open", "close", "toggle") \
                            and not _is_simple_off_with_params and not _has_precise_light_params:
                        assoc_script = self._find_associated_script(entity_id, service)
                        if assoc_script:
                            # 安全检查：若 AI 意图是 turn_off 且关联脚本名称含"关"/"turn_off"/"guan"，
                            # 该类脚本通常会关闭一批设备（全关脚本）；
                            # 仅当当前设备与脚本高度对应时才路由，否则跳过 Action Router 直接控制设备，
                            # 避免"降低亮度"等精细操作被全关脚本覆盖。
                            _script_local = assoc_script.split(".", 1)[-1].lower()
                            _IS_TURNOFF_SCRIPT = any(kw in _script_local for kw in
                                                     ("turn_off", "guan_deng", "guan_bi", "all_off", "quan_guan"))
                            if service == "turn_off" and _IS_TURNOFF_SCRIPT:
                                # 只路由当前设备唯一对应该脚本时才放行（脚本名称本地部分包含 entity_id 本地部分）
                                _eid_local = entity_id.split(".", 1)[-1].lower()
                                _script_parts = set(_script_local.replace("turn_off_", "").replace("_lights", "").split("_"))
                                _eid_parts = set(_eid_local.split("_"))
                                _overlap_ratio = len(_script_parts & _eid_parts) / max(len(_eid_parts), 1)
                                if _overlap_ratio < 0.8:
                                    self._sys_log("INFO",
                                        f"[Action Router] 跳过路由 {entity_id} → {assoc_script}"
                                        f"（turn_off 全关脚本保护，重叠率={_overlap_ratio:.0%} < 80%，直接控制单个设备）")
                                    assoc_script = None

                            if assoc_script:
                                assoc_domain = assoc_script.split(".")[0]
                                _had_params = bool(params)
                                _keep_precise = (assoc_domain == "scene" and domain == "light" and service == "turn_on")
                                self._sys_log("INFO",
                                    f"[Action Router] {entity_id} → 路由至 {assoc_domain}: {assoc_script}"
                                    f"（优先使用脚本/场景"
                                    f"{', 保留灯光精细参数' if (_had_params and _keep_precise) else (', 丢弃 AI params' if _had_params else '')}）")
                                orig_domain = domain
                                orig_service = service
                                domain = assoc_domain
                                entity_id = assoc_script
                                service = "turn_on"
                                params = {
                                    k: v
                                    for k, v in params.items()
                                    if k in ACTION_PARAM_KEYS_LIGHT_SCENE
                                } if (assoc_domain == "scene" and orig_domain == "light" and orig_service == "turn_on") else {}
            # ─────────────────────────────────────────────────────────────────

            runtime_hints = action.get("runtime_hints") or {}
            service, params = self._apply_sleep_reentry_low_disturbance(
                entity_id, domain, service, params, runtime_hints
            )

            # script / scene pass the pre-guards here, then continue through
            # _do_call_service so service errors and action trace stay unified.
            if domain in ("script", "scene"):
                # 拦截全局场景：entity_id 的本地部分（domain 后）以全局关键词开头才拦截
                # 例如 scene.quan_bu_off / scene.all_off → 拦截
                # 例如 scene.yi_lou_zhan_ting_suo_you_deng_guang_0_scene_0 → 放行（含房间前缀）
                _eid_local = entity_id.split(".", 1)[-1].lower()
                _GLOBAL_KW = ("turn_all", "all_on", "all_off", "quan_bu", "suo_you", "全部", "所有")
                if any(_eid_local == kw or _eid_local.startswith(kw + "_") for kw in _GLOBAL_KW):
                    blocked_count += 1
                    results.append({
                        "entity_id": entity_id,
                        "service": service,
                        "status": "blocked_global_scene",
                        "msg": "global_scene_blocked",
                    })
                    self._sys_log("WARN", f"[全局场景拦截] 拒绝执行 {entity_id}（以全局关键词开头），请使用区域场景替代")
                    continue
                # 场景/脚本人员在场守卫（家庭模式）
                if self._mode != MODE_SHOWROOM:
                    scene_room = self._guess_scene_room(entity_id)
                    if scene_room:
                        sensors = self._room_occupancy_entries(scene_room)
                        if sensors:
                            occupied = any(s == "on" for _, s in sensors)
                            uncertain = any(s in ("unknown", "unavailable") for _, s in sensors)
                            if not occupied and not uncertain:
                                blocked_count += 1
                                results.append({
                                    "entity_id": entity_id,
                                    "service": service,
                                    "status": "blocked_scene_vacant",
                                    "msg": f"scene_room_vacant:{scene_room}",
                                })
                                sensor_str = ", ".join(f"{eid}={s}" for eid, s in sensors[:2])
                                self._sys_log("WARN", f"[场景守卫] 拒绝 {domain}.turn_on({entity_id})：区域「{scene_room}」无人（{sensor_str}）")
                                continue
                # 场景/脚本重复执行冷却
                now_ts = time.time()
                last_exec = self._scene_last_exec.get(entity_id, 0)
                if now_ts - last_exec < self._SCENE_COOLDOWN:
                    results.append({
                        "entity_id": entity_id,
                        "service": service,
                        "status": "skip",
                        "msg": "scene_cooldown",
                    })
                    remain = int(self._SCENE_COOLDOWN - (now_ts - last_exec))
                    self._sys_log("INFO", f"[场景冷却] {entity_id} 距上次执行 {int(now_ts - last_exec)}s < {self._SCENE_COOLDOWN}s，跳过（{remain}s 后可再执行）")
                    continue
                self._sys_log("INFO", f"[动作] 场景/脚本通过前置守卫，转交统一保护链: {domain}.{service}({entity_id})")

            self._sys_log("INFO", f"[动作] 准备执行: {domain}.{service}({entity_id}) params={params} reason={reason}")
            is_automatic_presence_lighting = (
                service == "turn_on"
                and self._entity_looks_like_lighting(
                    entity_id,
                    domain,
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                )
                and self._looks_like_automatic_presence_lighting(
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                    cmd_source=str(cmd_source or ""),
                )
            )
            is_presence_departure_turnoff = (
                service == "turn_off"
                and self._looks_like_presence_departure_turnoff(
                    reason=str(reason or ""),
                    scene_desc=str(scene_desc or ""),
                    trigger_summary=str(trigger_summary or ""),
                    cmd_source=str(cmd_source or ""),
                )
            )
            state = self.hass.states.get(entity_id)
            if state:
                if service == "turn_off" and state.state == "off" and not is_presence_departure_turnoff:
                    self._sys_log("INFO", f"[动作] 跳过(已是off): {entity_id}")
                    results.append({
                        **action_result_context,
                        "status": "skip",
                        "msg": "already off",
                        "ha_command_status": "not_dispatched",
                    })
                    continue
                if service == "turn_on" and state.state == "on" and (not params or is_automatic_presence_lighting):
                    self._sys_log("INFO", f"[动作] 跳过(已是on): {entity_id}")
                    results.append({**action_result_context, "status": "skip", "msg": "already on"})
                    continue
            # 人员在场守卫：light/switch turn_on 前确认区域有人（仅家庭模式）
            if domain in ("light", "switch") and self._mode != MODE_SHOWROOM:
                guard_blocked, guard_reason = self._occupancy_guard_check(entity_id, service)
                if guard_blocked:
                    self._sys_log("WARN", f"[人员守卫] 拒绝 {domain}.turn_on({entity_id})：{guard_reason}（无人区域禁止开灯）")
                    blocked_count += 1
                    results.append({"entity_id": entity_id, "service": service, "status": "blocked", "msg": guard_reason})
                    continue

            if (
                service == "turn_on"
                and is_automatic_presence_lighting
            ):
                daylight_reason = self._daylight_auto_lighting_suppressed_reason(entity_id)
                if daylight_reason:
                    self._sys_log(
                        "WARN",
                        f"[日照守卫] 拒绝白天自动开灯 {domain}.turn_on({entity_id})：{daylight_reason}",
                    )
                    blocked_count += 1
                    results.append({
                        **action_result_context,
                        "status": "blocked_daylight_auto_lighting",
                        "msg": daylight_reason,
                    })
                    continue

            # 展厅模式人数阈值锁定规则（统一执行层）：
            # 无论动作来自反射弧/快脑/慢脑，只要命中“>N人才能开X”锁定规则，
            # 且当前人数不满足阈值，就阻止自动 turn_on。
            if (
                domain == "light"
                and service == "turn_on"
                and not _is_user_explicit
            ):
                _room = ((self.device_info.get(entity_id) or {}).get("room") or "").strip()
                if not _room and hasattr(self, "_get_entity_area"):
                    _room = (self._get_entity_area(entity_id) or "").strip()
                if _room:
                    _person_count = int((people_counts_by_room or {}).get(_room, 0) or 0)
                    _blocked_by_rule, _rule_text = self._is_light_blocked_by_people_rule(
                        entity_id=entity_id,
                        room=_room,
                        person_count=_person_count,
                        parsed_rules=parsed_people_rules,
                    )
                    if _blocked_by_rule:
                        self._sys_log(
                            "WARN",
                            f"[P1人数阈值] 阻止 turn_on({entity_id})：{_room} 当前人数={_person_count}，未满足锁定规则({_rule_text}人)",
                        )
                        blocked_count += 1
                        results.append({
                            "entity_id": entity_id,
                            "service": service,
                            "status": "blocked_p1_people",
                            "msg": f"{_room}人数{_person_count}未满足锁定阈值",
                        })
                        continue
            # 展厅代码层硬保护：展厅模式下上班时间实施分层保护。
            # 这是确定性执行守卫，不是交给 LLM 遵守的 Product Rule P1 运行时规则。
            # 有人时全保，无人时按学习到的层级（Core/Display/Auxiliary）进行差异化保护。
            if self._mode == MODE_SHOWROOM and domain == "light":
                _info = self.device_info.get(entity_id, {})
                _room = (_info.get("room") or "").strip()
                _showroom_area = self.showroom_area_name
                # 完全基于 HA Area Registry 中的 room 字段判断，不依赖实体 ID 拼音
                _is_showroom_light = (
                    bool(_showroom_area)
                    and _room == _showroom_area
                    and _room not in self.showroom_excluded_subareas
                )

                if _is_showroom_light:
                    # B. 获取设备层级（优先从基线分数，兜底旧 tier 表）
                    tier = showroom_light_tiers.get(entity_id) or await self.hass.async_add_executor_job(self._get_showroom_light_tier_v2, entity_id)

                    # C. 分层保护逻辑
                    from .const import (
                        SHOWROOM_DISPLAY_DIM_PCT, SHOWROOM_OCCUPIED_PCT, SHOWROOM_CORE_MIN_PCT,
                    )
                    if is_showroom_occupied:
                        # 【有人状态】Core/Display 层：禁止关闭；AI turn_off → 转换为有人亮度
                        if service == "turn_off":
                            if tier in ("core", "display"):
                                self._sys_log("INFO",
                                    f"[展厅P1] {entity_id}({tier}) 展厅有人，turn_off 转为 turn_on {SHOWROOM_OCCUPIED_PCT}%")
                                service = "turn_on"
                                params = {"brightness_pct": SHOWROOM_OCCUPIED_PCT}
                            # Auxiliary 层有人时也不应随意关灯，但允许 AI 决定
                        elif service == "turn_on":
                            bri = params.get("brightness_pct")
                            if tier == "core" and bri is not None and bri < SHOWROOM_CORE_MIN_PCT:
                                # Core 层：有人时不得低于最低亮度
                                self._sys_log("INFO",
                                    f"[展厅P1] {entity_id}(core) 亮度下限保护：{bri}% → {SHOWROOM_CORE_MIN_PCT}%")
                                params["brightness_pct"] = SHOWROOM_CORE_MIN_PCT
                            elif bri is None:
                                # 无亮度参数时注入有人默认亮度
                                params["brightness_pct"] = SHOWROOM_OCCUPIED_PCT
                    elif is_working_hour:
                        # 【营业时间 + 无人状态】根据层级差异化节能
                        if tier == "core":
                            # 🟢 Core（常用灯）：即便无人也不关闭，维持最低展示亮度
                            if service == "turn_off":
                                self._sys_log("WARN",
                                    f"[展厅P1] 阻止 turn_off({entity_id})：Core 层在营业时间内禁止关闭")
                                blocked_count += 1
                                results.append({"entity_id": entity_id, "service": service, "status": "blocked_p1", "msg": "P1 core"})
                                continue
                            if service == "turn_on" and params.get("brightness_pct") is not None and params["brightness_pct"] < SHOWROOM_CORE_MIN_PCT:
                                self._sys_log("INFO",
                                    f"[展厅P1] {entity_id}(core) 无人亮度下限：{params['brightness_pct']}% → {SHOWROOM_CORE_MIN_PCT}%")
                                params["brightness_pct"] = SHOWROOM_CORE_MIN_PCT

                        elif tier == "display":
                            # 🟡 Display（展示灯）：无人时调暗至 DIM_PCT，不允许彻底关闭
                            if service == "turn_off":
                                self._sys_log("INFO",
                                    f"[展厅分层] {entity_id}(display) 无人节能：turn_off → turn_on {SHOWROOM_DISPLAY_DIM_PCT}%")
                                service = "turn_on"
                                params = {"brightness_pct": SHOWROOM_DISPLAY_DIM_PCT}
                            elif service == "turn_on" and params.get("brightness_pct") is not None and params["brightness_pct"] < SHOWROOM_DISPLAY_DIM_PCT:
                                self._sys_log("INFO",
                                    f"[展厅分层] {entity_id}(display) 无人节能：亮度限制至 {SHOWROOM_DISPLAY_DIM_PCT}%")
                                params["brightness_pct"] = SHOWROOM_DISPLAY_DIM_PCT

                        # 🔴 Auxiliary（辅助灯）：无人时允许 AI 自由执行 turn_off，不予拦截
                    else:
                        # 【非营业时间 + 无人状态】完全释放 Product Rule P1 保护，允许 AI 关闭所有灯光
                        self._sys_log("INFO", f"[展厅下班] 非营业时间且无人，放行对 {entity_id} 的操作")

            # 关灯安全守卫：light/switch turn_off 前双重确认区域无人
            # 因 Frigate 存在漏检，优先以物理人体传感器为准；任意一路检测到有人则阻止关灯
            if domain in ("light", "switch") and self._mode != MODE_SHOWROOM:
                off_blocked, off_reason = self._turnoff_presence_guard(entity_id, service)
                if off_blocked:
                    self._sys_log("WARN",
                        f"[关灯守卫] 阻止 {domain}.turn_off({entity_id})：{off_reason}")
                    blocked_count += 1
                    presence_detail = getattr(self, "_last_turnoff_presence_guard_detail", {})
                    if not isinstance(presence_detail, dict):
                        presence_detail = {}
                    results.append({"entity_id": entity_id, "service": service,
                                    "status": "blocked_person", "msg": off_reason,
                                    **presence_detail})
                    continue
            if entity_id in self._active_timers:
                try:
                    self._active_timers[entity_id]()
                except Exception as exc:
                    _LOGGER.debug("[Actions] 取消定时任务失败 %s: %s", entity_id, exc)
                del self._active_timers[entity_id]
            if delay > 0:
                # 在闭包中捕获 scene_desc/trigger_summary，保证延迟执行时仍用正确的上下文
                # 避免并发推理时 self._current_scene_desc 被其他房间的推理覆盖
                result_entry = {
                    "entity_id": entity_id,
                    "service": service,
                    "status": "scheduled",
                    "delay": delay,
                }
                if reason:
                    result_entry.update(action_result_context)
                results.append(result_entry)

                async def _run_delayed(
                    d: str, s: str, eid: str, p: dict, r: str,
                    sc: str, trig: str, txid: int, aseq: int, parent_txid: str,
                    corr_id: str, target_sid: str, result: dict,
                ) -> None:
                    try:
                        state = self.hass.states.get(eid)
                        if (
                            state
                            and s == "turn_off"
                            and getattr(state, "state", None) == "off"
                            and not self._looks_like_presence_departure_turnoff(
                                reason=str(r or ""),
                                scene_desc=str(sc or ""),
                                trigger_summary=str(trig or ""),
                            )
                        ):
                            result.update({
                                "status": "skip",
                                "msg": "already off",
                                "ha_command_status": "not_dispatched",
                            })
                            await _refresh_transaction_from_results()
                            return
                        ok = await self._do_call_service(
                            d,
                            s,
                            eid,
                            p,
                            r,
                            sc,
                            trig,
                            txid,
                            aseq,
                            parent_txid,
                            world_snapshot_id,
                            corr_id,
                            active_space_id=active_space_id,
                            decision_time=decision_time,
                            target_space_id=target_sid,
                            require_world_snapshot_guard=require_world_snapshot_guard,
                        )
                    except Exception as exc:
                        _LOGGER.debug("[Actions] 延迟动作执行失败 %s.%s(%s): %s", d, s, eid, exc)
                        ok = False
                    if ok:
                        result["status"] = "ok"
                    else:
                        result.update(_pop_service_call_error_or_unknown(txid, aseq, eid))
                        result["status"] = "blocked_or_error"
                    try:
                        await _refresh_transaction_from_results()
                    except Exception as exc:
                        _LOGGER.warning(
                            "[Actions] delayed action transaction refresh failed %s.%s(%s): %s",
                            d,
                            s,
                            eid,
                            exc,
                            exc_info=True,
                        )

                def _delayed(
                    d: str, s: str, eid: str, p: dict, r: str,
                    sc: str, trig: str, txid: int, aseq: int, parent_txid: str,
                    corr_id: str, target_sid: str, result: dict, _: datetime,
                ) -> None:
                    coro = _run_delayed(
                        d, s, eid, p, r, sc, trig, txid, aseq, parent_txid,
                        corr_id, target_sid, result,
                    )
                    try:
                        self.hass.async_create_task(coro)
                    except Exception as exc:
                        close = getattr(coro, "close", None)
                        if callable(close):
                            close()
                        _LOGGER.warning(
                            "[Actions] delayed action task create failed %s.%s(%s): %s",
                            d,
                            s,
                            eid,
                            exc,
                            exc_info=True,
                        )
                        result.update(
                            {
                                "status": "blocked_or_error",
                                "msg": f"task_create_failed: {exc}",
                                "error": "task_create_failed",
                                "error_type": "task_create_failed",
                                "ha_command_status": "not_dispatched",
                                "exception_type": type(exc).__name__,
                            }
                        )
                        try:
                            _refresh_transaction_from_results_sync()
                        except Exception as refresh_exc:
                            _LOGGER.warning(
                                "[Actions] delayed action task create failure transaction refresh failed %s.%s(%s): %s",
                                d,
                                s,
                                eid,
                                refresh_exc,
                                exc_info=True,
                            )

                handle = async_call_later(
                    self.hass, delay,
                    lambda dt, d=domain, s=service, e=entity_id, p=params, r=reason,
                           sc=scene_desc, trig=trigger_summary, txid=txn_id, aseq=action_seq,
                           parent_txid=parent_transaction_id,
                           corr_id=correlation_id,
                           target_sid=target_space_id,
                           result=result_entry:
                        _delayed(
                            d, s, e, p, r, sc, trig, txid, aseq, parent_txid,
                            corr_id, target_sid, result, dt,
                        ),
                )
                self._active_timers[entity_id] = handle
            else:
                ok = await self._do_call_service(
                    domain, service, entity_id, params, reason, scene_desc, trigger_summary, txn_id, action_seq,
                    parent_transaction_id, world_snapshot_id, correlation_id,
                    active_space_id=active_space_id,
                    decision_time=decision_time,
                    target_space_id=target_space_id,
                    require_world_snapshot_guard=require_world_snapshot_guard,
                )
                if ok:
                    executed += 1
                    results.append({**action_result_context, "status": "ok"})
                else:
                    failed_count += 1
                    service_error = _pop_service_call_error_or_unknown(txn_id, action_seq, entity_id)
                    results.append({**action_result_context, **service_error, "status": "blocked_or_error"})

        for (original_position, _raw_action, _action), result in zip(
            normalized_actions,
            results[guard_result_count:],
        ):
            _remember_result(original_position, result)
        results[:] = _ordered_results()
        if correlation_id:
            results[:] = [{**item, "correlation_id": correlation_id} for item in results]

        # ── 4. 提交事务结果 ────────────────────────────────────────────────────
        if txn_id:
            await self.hass.async_add_executor_job(
                self._complete_transaction_db,
                txn_id,
                executed,
                blocked_count,
                failed_count,
                _json.dumps(results, ensure_ascii=False),
            )
        return self._action_execution_result(
            executed,
            transaction_id=txn_id,
            results=results,
            pre_states=pre_states,
            correlation_id=correlation_id,
        )

    # ── 服务调用 + 保护机制 ───────────────────────────────────────────────────

    async def _execute_enveloped_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        call_params: dict[str, Any] | None,
        reason: str,
        transaction_id: int = 0,
        action_seq: int = 0,
        *,
        world_snapshot_id: str = "",
        active_space_id: str = "",
        decision_time: str = "",
        target_space_id: str = "",
        require_world_snapshot_guard: bool = False,
    ) -> None:
        """Execute one HA command envelope and preserve structured failure detail."""
        from .ha_adapter import async_execute_command_envelope

        payload = call_params if isinstance(call_params, dict) else {}
        active_correlations = getattr(self, "_active_service_correlation_ids", {})
        active_correlation_id = (
            active_correlations.get(asyncio.current_task(), "")
            if isinstance(active_correlations, dict)
            else ""
        )
        request_id = str(active_correlation_id or "").strip() or f"legacy-action:{transaction_id}:{action_seq}:{entity_id}"
        envelope = {
            "request_id": request_id,
            "source": "smartagent_active_ai" if require_world_snapshot_guard else "smartagent_ha_host",
            "scope": "home_control",
            "commands": [{
                "entity_id": entity_id,
                "domain": domain,
                "service": service,
                "data": payload,
            }],
            "execution_policy": {"stop_on_first_error": True},
            "safety": {
                "risk_level": "safe",
                "requires_confirmation": False,
                "reason": reason,
                "context": {
                    **(
                        {
                            "active_ai_managed": True,
                            "world_snapshot_id": str(world_snapshot_id or "").strip(),
                            "active_space_id": str(active_space_id or "").strip(),
                            "decision_time": str(decision_time or "").strip(),
                            "target_space_ids": [str(target_space_id or "").strip()]
                            if str(target_space_id or "").strip()
                            else [],
                        }
                        if require_world_snapshot_guard
                        else {}
                    )
                },
            },
        }
        result: dict[str, Any] | None
        if require_world_snapshot_guard:
            is_enabled = getattr(self, "_is_enabled", None)
            ai_enabled = (
                bool(is_enabled())
                if callable(is_enabled)
                else bool(getattr(self, "_enabled", False))
            )
            if not ai_enabled:
                result = {
                    "ok": False,
                    "error": "active_ai_global_disabled",
                    "error_type": "policy_rejected",
                    "status": "blocked",
                }
            elif not str(world_snapshot_id or "").strip() or str(world_snapshot_id).strip() == "unknown":
                result = {
                    "ok": False,
                    "error": "world_snapshot_id_missing",
                    "error_type": "policy_rejected",
                    "status": "blocked",
                }
            elif not str(active_space_id or "").strip():
                result = {
                    "ok": False,
                    "error": "world_snapshot_space_mismatch",
                    "error_type": "policy_rejected",
                    "status": "blocked",
                }
            elif not str(decision_time or "").strip():
                result = {
                    "ok": False,
                    "error": "world_snapshot_stale",
                    "error_type": "policy_rejected",
                    "status": "blocked",
                }
            elif not str(target_space_id or "").strip():
                result = {
                    "ok": False,
                    "error": "active_ai_action_space_missing",
                    "error_type": "policy_rejected",
                    "status": "blocked",
                }
            else:
                addon_client = getattr(self, "_addon_client", None)
                execute = getattr(addon_client, "execute_command_envelope", None)
                if not callable(execute):
                    result = {
                        "ok": False,
                        "error": "active_ai_execute_provider_unavailable",
                        "error_type": "upstream_unavailable",
                        "status": "failed",
                    }
                else:
                    result = await execute(envelope)
                    if not isinstance(result, dict):
                        result = {
                            "ok": False,
                            "error": "active_ai_execute_provider_unavailable",
                            "error_type": "upstream_unavailable",
                            "status": "failed",
                        }
        else:
            result = await async_execute_command_envelope(self.hass, envelope)
        if isinstance(result, dict) and result.get("ok"):
            self._clear_service_call_error(transaction_id, action_seq, entity_id)
            return
        failed = None
        if isinstance(result, dict):
            failed = next((item for item in result.get("results", []) if not item.get("ok")), None)
        error = ""
        error_type = ""
        status = ""
        if isinstance(failed, dict):
            error = str(failed.get("error") or failed.get("status") or "")
            error_type = str(failed.get("error_type") or "")
            status = str(failed.get("status") or "")
        if not error and isinstance(result, dict):
            error = str(result.get("error") or result.get("error_type") or "")
            error_type = str(result.get("error_type") or "")
            status = str(result.get("status") or "")
        msg = error or status or "command_envelope_failed"
        self._remember_service_call_error(
            transaction_id,
            action_seq,
            entity_id,
            msg=msg,
            error=error,
            error_type=error_type,
            status=status,
        )
        raise RuntimeError(msg)

    async def _do_call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        params: dict,
        reason: str,
        scene_desc: str = "",
        trigger_text: str = "",
        transaction_id: int = 0,
        action_seq: int = 0,
        parent_transaction_id: str = "",
        world_snapshot_id: str = "",
        correlation_id: str = "",
        *,
        active_space_id: str = "",
        decision_time: str = "",
        target_space_id: str = "",
        require_world_snapshot_guard: bool = False,
    ) -> bool:
        """Call HA service and record AI action for override detection. Returns True if executed.

        Args:
            scene_desc:   本次推理的场景描述，写入 _last_ai_actions 供纠错 UI 展示。
                          并发推理时通过参数传递，避免多房间竞争 self._current_scene_desc。
            trigger_text: 本次推理的触发文本，同上。
        """
        correlation_id = str(correlation_id or "").strip()
        state = self.hass.states.get(entity_id)
        is_presence_departure_turnoff = (
            service == "turn_off"
            and self._looks_like_presence_departure_turnoff(
                reason=str(reason or ""),
                scene_desc=str(scene_desc or ""),
                trigger_summary=str(trigger_text or ""),
            )
        )
        if state and service == "turn_off" and state.state == "off" and not is_presence_departure_turnoff:
            return True
        self._clear_service_call_error(transaction_id, action_seq, entity_id)

        def _fail_before_service(msg: str, *, error_type: str = "ha_service_guard", status: str = "blocked") -> bool:
            self._remember_service_call_error(
                transaction_id,
                action_seq,
                entity_id,
                msg=msg,
                error=msg,
                error_type=error_type,
                status=status,
            )
            return False

        def _is_service_missing_error(error: Exception | str) -> bool:
            text = str(error).lower()
            return "not found" in text or "unknown" in text or "does not exist" in text

        def _service_failure_error_type(error: Exception | str) -> str:
            return "service_missing" if _is_service_missing_error(error) else "ha_service_error"

        def _fail_after_service(
            msg: str,
            *,
            error_type: str = "ha_service_error",
            status: str = "failed",
            overwrite_stale: bool = False,
        ) -> bool:
            store = getattr(self, "_service_call_errors", None)
            key = self._service_call_error_key(transaction_id, action_seq, entity_id)
            existing = store.get(key) if isinstance(store, dict) else None
            if isinstance(existing, dict):
                existing_msg = str(existing.get("msg") or existing.get("error") or "")
                existing_type = str(existing.get("error_type") or "")
                existing_status = str(existing.get("ha_command_status") or "")
                if existing_msg == str(msg or ""):
                    should_upgrade_type = (
                        bool(error_type)
                        and (
                            not existing_type
                            or (existing_type == "ha_service_error" and error_type == "service_missing")
                        )
                    )
                    if should_upgrade_type or (status and not existing_status):
                        self._remember_service_call_error(
                            transaction_id,
                            action_seq,
                            entity_id,
                            msg=msg,
                            error=str(existing.get("error") or msg),
                            error_type=error_type if should_upgrade_type else existing_type,
                            status=existing_status or status,
                        )
                    return False
                if not overwrite_stale:
                    current_is_generic = not error_type or error_type == "ha_service_error"
                    existing_is_specific = bool(existing_type) and existing_type != "ha_service_error"
                    if existing_is_specific and current_is_generic:
                        return False
            else:
                self._remember_service_call_error(
                    transaction_id,
                    action_seq,
                    entity_id,
                    msg=msg,
                    error=msg,
                    error_type=error_type,
                    status=status,
                )
                return False
            self._remember_service_call_error(
                transaction_id,
                action_seq,
                entity_id,
                msg=msg,
                error=msg,
                error_type=error_type,
                status=status,
            )
            return False

        self_trigger_guard = evaluate_self_trigger_protection(
            entity_id=entity_id,
            service=service,
            trigger_entities=self._batch_trigger_controllable,
        )
        if not self_trigger_guard.allowed:
            self._sys_log("WARN", f"[自触发保护] {entity_id} 触发了本次推理，拒绝 AI 操作该设备 → {service}（防止死循环）")
            return _fail_before_service(
                self_trigger_guard.msg,
                error_type=self_trigger_guard.error_type or "self_trigger_protection",
                status=self_trigger_guard.status or "blocked_self_trigger",
            )
        now_ts = time.time()
        # ── 自动化冲突硬拦截：若设备被 HA 自动化管辖且自动化近期执行过，拒绝 AI 操作 ──
        auto_names = self._automation_managed_devices.get(entity_id)
        if auto_names:
            automation_records: list[dict[str, Any]] = []
            for a_state in self.hass.states.async_all("automation"):
                a_name = a_state.attributes.get("friendly_name", "")
                if a_name not in auto_names:
                    continue
                last_triggered = a_state.attributes.get("last_triggered")
                if last_triggered:
                    try:
                        if hasattr(last_triggered, "timestamp"):
                            lt_ts = last_triggered.timestamp()
                        else:
                            from datetime import datetime as _dt
                            lt_ts = _dt.fromisoformat(str(last_triggered).replace("Z", "+00:00")).timestamp()
                        automation_records.append({
                            "name": a_name,
                            "last_triggered_ts": lt_ts,
                        })
                    except Exception as exc:
                        _LOGGER.debug("[Actions] 自动化避让时间解析失败: %s", exc)
            automation_guard = evaluate_automation_conflict_window(
                entity_id=entity_id,
                service=service,
                managed_automation_names=auto_names,
                automation_records=automation_records,
                now_ts=now_ts,
                window_seconds=self._AUTOMATION_EXEC_WINDOW,
            )
            if not automation_guard.allowed:
                self._sys_log("WARN", f"[自动化避让] {entity_id} 被自动化「{automation_guard.automation_name}」管辖，"
                              f"该自动化 {automation_guard.age_seconds}s 前刚触发，AI 退让 → {service}（{self._AUTOMATION_EXEC_WINDOW}s 窗口）")
                return _fail_before_service(
                    automation_guard.msg,
                    error_type=automation_guard.error_type or "automation_conflict",
                    status=automation_guard.status or "blocked",
                )
        # ── 优先级仲裁（Product Rule P0-P4 分级控制）──
        from .const import MODE_HOME, SOURCE_AI_INFER, SOURCE_AI_RULE
        ai_source = SOURCE_AI_INFER
        if "🔒" in reason or "锁定" in reason:
            ai_source = SOURCE_AI_RULE

        global_suppress_guard = evaluate_global_suppress_window(
            entity_id=entity_id,
            service=service,
            now_ts=now_ts,
            suppress_until=self._global_suppress_until,
            suppress_reason=self._global_suppress_reason,
        )
        if not global_suppress_guard.allowed:
            self._sys_log(
                "WARN",
                f"[P0 全局抑制] {self._global_suppress_reason}"
                f"（剩余 {global_suppress_guard.remaining_seconds}s）→ 拒绝 {entity_id}.{service}",
            )
            return _fail_before_service(
                global_suppress_guard.msg,
                error_type=global_suppress_guard.error_type or "global_suppress",
                status=global_suppress_guard.status or "blocked",
            )

        if self._mode == MODE_HOME:
            allowed, arb_reason = self._arbitrate(entity_id, ai_source, service, params)
            if not allowed:
                self._sys_log("WARN", arb_reason)
                return _fail_before_service(
                    str(arb_reason or "priority_guard_rejected"),
                    error_type="priority_guard",
                )

            # 兼容旧的用户覆盖保护（对未接入优先级系统的边界情况兜底）
            with self._user_overrides_lock:
                override = self._user_overrides.get(entity_id)
            manual_guard = evaluate_manual_override_window(
                entity_id=entity_id,
                service=service,
                now_ts=now_ts,
                override=override,
                off_states=self._OFF_STATES,
                window_seconds=self._USER_OVERRIDE_PROTECTION,
            )
            if not manual_guard.allowed:
                self._sys_log("WARN", f"[manual override protection] {manual_guard.msg}")
                return _fail_before_service(
                    manual_guard.msg,
                    error_type=manual_guard.error_type or "user_override_protection",
                    status=manual_guard.status or "blocked",
                )
            if manual_guard.clear_expired_override:
                with self._user_overrides_lock:
                    current_override = self._user_overrides.get(entity_id)
                    if current_override is override or current_override == override:
                        self._user_overrides.pop(entity_id, None)
        self._last_inference[entity_id] = now_ts
        ai_new_state = "on" if "turn_on" in service else "off"
        safe_params = {k: v for k, v in params.items() if k != "entity_id"}
        # HA 2024+ 已废弃 color_temp(mireds)，统一改为 color_temp_kelvin(Kelvin)
        # 若 AI 仍输出旧格式，自动转换以避免 schema 报错
        color_temp_guard = evaluate_color_temp_mireds_param(
            entity_id=entity_id,
            service=service,
            params=safe_params,
        )
        if not color_temp_guard.allowed:
            mired_val = str(color_temp_guard.msg).split(":", 1)[1] if ":" in color_temp_guard.msg else ""
            self._sys_log("ERROR", f"[动作] {entity_id} color_temp({mired_val}) 非法，拒绝执行")
            return _fail_before_service(
                color_temp_guard.msg,
                error_type=color_temp_guard.error_type or "invalid_action_param",
                status=color_temp_guard.status or "blocked_invalid_params",
            )
        if color_temp_guard.normalized_params is not None:
            safe_params = dict(color_temp_guard.normalized_params)
        if color_temp_guard.color_temp_kelvin:
            self._sys_log("INFO", f"[动作] {entity_id} color_temp({color_temp_guard.color_temp_mireds}mireds)"
                          f" → color_temp_kelvin({color_temp_guard.color_temp_kelvin}K) 自动转换")
        self._clear_service_call_error(transaction_id, action_seq, entity_id)

        def _is_param_rejection(exc: Exception | str) -> bool:
            text = str(exc).lower()
            return "extra keys" in text or "not allowed" in text or "unexpected" in text

        async def _call_enveloped_service(call_data: dict[str, Any]) -> None:
            active_correlations = getattr(self, "_active_service_correlation_ids", None)
            if not isinstance(active_correlations, dict):
                active_correlations = {}
                self._active_service_correlation_ids = active_correlations
            task = asyncio.current_task()
            previous = active_correlations.get(task)
            if correlation_id:
                active_correlations[task] = correlation_id
            try:
                active_execution_kwargs = (
                    {
                        "world_snapshot_id": world_snapshot_id,
                        "active_space_id": active_space_id,
                        "decision_time": decision_time,
                        "target_space_id": target_space_id,
                        "require_world_snapshot_guard": True,
                    }
                    if require_world_snapshot_guard
                    else {}
                )
                await self._execute_enveloped_service(
                    domain,
                    service,
                    entity_id,
                    call_data,
                    reason,
                    transaction_id,
                    action_seq,
                    **active_execution_kwargs,
                )
            finally:
                if previous:
                    active_correlations[task] = previous
                else:
                    active_correlations.pop(task, None)

        try:
            await _call_enveloped_service(safe_params)
            if domain in ("scene", "script") and service == "turn_on":
                self._scene_last_exec[entity_id] = time.time()
        except Exception as call_err:
            err_str = str(call_err).lower()
            # 部分设备不支持某些扩展参数，尝试智能降级：
            # 优先仅剔除色温参数保留亮度，若仍失败再去除全部扩展参数
            extra_keys = [k for k in safe_params]
            if extra_keys and _is_param_rejection(err_str):
                color_keys_present = [k for k in extra_keys if k in ACTION_PARAM_KEYS_COLOR]
                non_color_params = {k: v for k, v in safe_params.items() if k not in ACTION_PARAM_KEYS_COLOR}
                if color_keys_present and non_color_params:
                    # 先尝试：去掉色温，保留亮度等其他参数
                    self._sys_log("WARN", f"[动作] {entity_id} 不支持色温参数 {color_keys_present}，"
                                  f"保留亮度重试: {non_color_params}")
                    try:
                        await _call_enveloped_service(non_color_params)
                    except ServiceNotFound:
                        raise
                    except Exception as retry_err:
                        if not _is_param_rejection(retry_err):
                            self._sys_log("ERROR", f"[动作] {entity_id} 保留亮度重试失败: {retry_err}")
                            return _fail_after_service(
                                str(retry_err),
                                error_type=_service_failure_error_type(retry_err),
                                overwrite_stale=True,
                            )
                        # 再退一步：去除全部扩展参数
                        self._sys_log("WARN", f"[动作] {entity_id} 亮度参数也失败，去除全部扩展参数重试")
                        try:
                            await _call_enveloped_service({})
                        except ServiceNotFound:
                            raise
                        except Exception as bare_retry_err:
                            self._sys_log("ERROR", f"[动作] {entity_id} 服务调用重试失败: {bare_retry_err}")
                            return _fail_after_service(
                                str(bare_retry_err),
                                error_type=_service_failure_error_type(bare_retry_err),
                                overwrite_stale=True,
                            )
                else:
                    # 没有可保留的参数，直接裸调用
                    self._sys_log("WARN", f"[动作] {entity_id} 不支持参数 {extra_keys}，去除后重试")
                    try:
                        await _call_enveloped_service({})
                    except ServiceNotFound:
                        raise
                    except Exception as retry_err:
                        self._sys_log("ERROR", f"[动作] {entity_id} 服务调用重试失败: {retry_err}")
                        return _fail_after_service(
                            str(retry_err),
                            error_type=_service_failure_error_type(retry_err),
                            overwrite_stale=True,
                        )
            elif _is_service_missing_error(call_err):
                self._sys_log("ERROR", f"[动作] {domain}.{service}({entity_id}) 实体/服务不存在，跳过。"
                              f"请检查设备是否在线或名称是否正确。原始错误: {call_err}")
                return _fail_after_service(str(call_err), error_type="service_missing")
            else:
                self._sys_log("ERROR", f"[动作] {entity_id} 服务调用失败: {call_err}")
                return _fail_after_service(str(call_err))
        self._last_ai_actions[entity_id] = {
            "state": ai_new_state,
            "time": now_ts,
            "service": f"{domain}.{service}",
            "scene": scene_desc,
            "trigger": trigger_text,
            "origin": "smartagent",
            "actor": "smartagent:execution",
            "decision_id": str(parent_transaction_id or "unknown"),
            "transaction_id": str(parent_transaction_id or "unknown"),
            "execution_transaction_id": str(transaction_id or "unknown"),
            "world_snapshot_id": str(world_snapshot_id or "unknown"),
            "correlation_id": correlation_id,
        }
        # AI 成功执行时清除该设备的用户覆盖记录，并记录后续仲裁状态。
        with self._user_overrides_lock:
            self._user_overrides.pop(entity_id, None)
        self._record_device_operation(entity_id, ai_source, ai_new_state, params)
        parent_transaction_id = str(parent_transaction_id or "").strip()
        event_detail = f"{entity_id} -> {service}"
        event_metadata: dict[str, Any] = {
            "detail": event_detail,
            "domain": domain,
            "service": service,
            "entity_id": entity_id,
        }
        if isinstance(params, dict) and params:
            event_metadata["params"] = dict(params)
        if reason:
            event_metadata["reason"] = reason
        if scene_desc:
            event_metadata["scene_desc"] = scene_desc
        if trigger_text:
            event_metadata["trigger_summary"] = trigger_text
        if transaction_id:
            event_metadata["execution_transaction_id"] = int(transaction_id)
        if parent_transaction_id:
            event_metadata["parent_transaction_id"] = parent_transaction_id
            event_metadata["decision_trace"] = {
                "available": True,
                "transaction_id": parent_transaction_id,
                "url": f"/decision-trace/{parent_transaction_id}",
            }
        if correlation_id:
            event_metadata["correlation_id"] = correlation_id
        self.hass.async_add_executor_job(
            self._record_event, "AI_Action", event_detail,
            entity_id, "on" if "turn_on" in service else "off", "ai", None,
            transaction_id, action_seq, event_metadata,
        )
        # Phase 11.3: 若为 turn_off 且触发文本包含离开/departure，记录该房间冷却时间戳
        # 巡检将在冷却期（5分钟）内跳过对该房间的推理，防止巡检覆盖离开决策
        if service == "turn_off" and trigger_text:
            _trig_lower = trigger_text.lower()
            if any(kw in _trig_lower for kw in ("离开", "departure", "无人", "empty", "人员离开")):
                _room = (self.device_info.get(entity_id) or {}).get("room", "")
                if _room and hasattr(self, "_last_departure_turnoff_time"):
                    self._last_departure_turnoff_time[_room] = time.time()
                    self._sys_log("INFO",
                        f"[冷却保护] {_room} 检测到离开关灯，设置5分钟巡检冷却窗口")
        await self._async_update_status("运行中", f"{self.get_device_name(entity_id)} → {service}（{reason[:30]}）")
        # ── 注册延迟状态验证 ──
        expected = "on" if ("turn_on" in service or "open" in service) else "off"
        if len(self._pending_verifications) < self._VERIFY_QUEUE_MAX:
            self._pending_verifications.append({
                "entity_id": entity_id, "domain": domain, "service": service,
                "expected_state": expected, "reason": reason,
                "fire_time": time.time(), "retry": 0,
                "transaction_id": transaction_id,
                "action_seq": action_seq,
                "parent_transaction_id": str(parent_transaction_id or "unknown"),
                "world_snapshot_id": str(world_snapshot_id or "unknown"),
                "correlation_id": correlation_id,
            })

        # ── 注册环境效果反馈检查（climate 设备：10 分钟后检验温度变化）──
        if domain == "climate" and "turn_on" in service:
            await self._register_env_feedback(entity_id)

        return True

    async def _register_env_feedback(self, entity_id: str, check_after_secs: int = 600) -> None:
        """为 climate 设备注册一次环境效果反馈检查任务。

        尝试通过房间名称匹配找出相关温湿度传感器：
        - climate.living_room_ac → sensor.*living_room*temp*
        - 兜底：遍历 device_info 中的 sensor 实体，选名称/ID 含同一房间关键词的
        """

        # 取当前设备状态（基准值）
        dev_state = self.hass.states.get(entity_id)
        if not dev_state:
            return

        base_temp: float | None = None
        target_temp: float | None = None
        try:
            base_temp = float(dev_state.attributes.get("current_temperature", 0) or 0) or None
            target_temp = float(dev_state.attributes.get("temperature", 0) or 0) or None
        except (TypeError, ValueError):
            pass

        # 通过房间关键词匹配相关传感器
        room_kw = self._guess_room_from_entity(entity_id)
        temp_sensor = ""
        humi_sensor = ""
        base_humi: float | None = None

        for eid in self.device_info:
            if not eid.startswith("sensor."):
                continue
            eid_lower = eid.lower()
            if room_kw and room_kw not in eid_lower:
                continue
            if any(k in eid_lower for k in ("temp", "temperature", "温度")):
                if not temp_sensor:
                    st = self.hass.states.get(eid)
                    if st and st.state not in ("unavailable", "unknown"):
                        try:
                            base_temp = float(st.state)
                            temp_sensor = eid
                        except (ValueError, TypeError):
                            pass
            elif any(k in eid_lower for k in ("humid", "humidity", "湿度")):
                if not humi_sensor:
                    st = self.hass.states.get(eid)
                    if st and st.state not in ("unavailable", "unknown"):
                        try:
                            base_humi = float(st.state)
                            humi_sensor = eid
                        except (ValueError, TypeError):
                            pass

        new_task = {
            "entity_id": entity_id,
            "action": "on",
            "base_temp": base_temp,
            "target_temp": target_temp,
            "temp_sensor": temp_sensor,
            "base_humi": base_humi,
            "humi_sensor": humi_sensor,
            "check_at": time.time() + check_after_secs,
            "check_after": check_after_secs,
            "checked": False,
        }
        async with self._env_feedback_lock:
            self._env_feedback_tasks.append(new_task)
        self._sys_log("INFO",
                      f"[反馈] 已为 {entity_id} 注册环境效果检查（{check_after_secs // 60} 分钟后）"
                      + (f"，关联传感器: {temp_sensor}" if temp_sensor else "，未找到温度传感器"))

    def _guess_room_from_entity(self, entity_id: str) -> str:
        """从实体 ID 中提取房间关键词（小写），用于传感器匹配。"""
        _ROOM_KW = (
            "living", "bedroom", "kitchen", "bathroom", "toilet", "study",
            "office", "hall", "balcony", "garage", "basement",
            "客厅", "卧室", "厨房", "浴室", "书房", "走廊", "阳台", "茶室",
        )
        eid_lower = entity_id.lower().replace(".", "_")
        for kw in _ROOM_KW:
            if kw in eid_lower:
                return kw
        # 取 domain 后第一个 _ 分隔词
        parts = entity_id.split(".")[-1].split("_")
        if parts:
            return parts[0].lower()
        return ""

    # ── 动作验证与重试 ────────────────────────────────────────────────────────

    # ── 动作验证与重试 ────────────────────────────────────────────────────────

    async def _verify_pending_actions(self) -> None:
        """回查已执行动作的设备状态，确认是否生效。由巡检循环定期调用。"""
        if not self._pending_verifications:
            return
        now = time.time()
        # 过期清理
        self._pending_verifications = [
            v for v in self._pending_verifications
            if now - v["fire_time"] < self._VERIFY_EXPIRE_SEC
        ]
        remaining: list[dict] = []
        snapshot = list(self._pending_verifications)
        for item in snapshot:
            elapsed = now - item["fire_time"]
            if elapsed < self._ACTION_VERIFY_DELAY:
                remaining.append(item)
                continue
            eid = item["entity_id"]
            expected = item["expected_state"]
            state_obj = self.hass.states.get(eid)
            actual = state_obj.state if state_obj else "unknown"
            # unavailable/unknown 视为验证不可判定 — 跳过本次，等下一轮
            if actual in ("unavailable", "unknown"):
                if now - item["fire_time"] < self._VERIFY_EXPIRE_SEC:
                    remaining.append(item)
                continue
            ok = (expected == "on" and actual not in self._OFF_STATES) or \
                 (expected == "off" and actual in self._OFF_STATES)
            latency = int(elapsed * 1000)
            # 记录到 DB
            self.hass.async_add_executor_job(
                self._record_action_result,
                eid, item["domain"], item["service"], expected, actual,
                1 if ok else 0, item["retry"], latency, item["reason"],
                item.get("transaction_id", 0), item.get("action_seq", 0),
            )
            if ok:
                self._sys_log("INFO", f"[验证✓] {eid} 期望={expected} 实际={actual}（{latency}ms）")
                record_learning_verification = getattr(
                    self,
                    "_record_learning_post_state_verification",
                    None,
                )
                if callable(record_learning_verification):
                    record_learning_verification(item, actual)
            else:
                if item["retry"] < self._ACTION_RETRY_MAX:
                    self._sys_log("WARN", f"[验证✗] {eid} 期望={expected} 实际={actual}，自动重试第 {item['retry']+1} 次")
                    try:
                        # 临时记住队列长度，_do_call_service 会追加新验证条目，需在调用后删除
                        q_len_before = len(self._pending_verifications)
                        ok_retry = await self._do_call_service(
                            item["domain"], item["service"], eid, {}, f"验证重试({expected})",
                            transaction_id=item.get("transaction_id", 0),
                            action_seq=item.get("action_seq", 0),
                            parent_transaction_id=item.get("parent_transaction_id", ""),
                            world_snapshot_id=item.get("world_snapshot_id", ""),
                            correlation_id=item.get("correlation_id", ""),
                        )
                        # 删除 _do_call_service 追加的重复验证条目
                        if len(self._pending_verifications) > q_len_before:
                            self._pending_verifications = self._pending_verifications[:q_len_before]
                        if ok_retry:
                            item["retry"] += 1
                            item["fire_time"] = time.time()
                            remaining.append(item)
                        else:
                            self._sys_log("WARN", f"[验证重试] {eid} 被保护机制拦截，放弃重试")
                    except Exception as e:
                        self._sys_log("ERROR", f"[验证重试] {eid} 重试失败: {e}")
                else:
                    self._sys_log("ERROR", f"[验证✗] {eid} 期望={expected} 实际={actual}，已达最大重试次数")
        self._pending_verifications = remaining
