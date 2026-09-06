"""
ActionsMixin — 动作执行层。
负责：动作标准化、实体模糊匹配、Action Router（脚本/场景路由）、
      服务调用保护、动作验证与自动重试。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime
from math import isfinite
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import ServiceNotFound

from .action_execution_runtime import ActionExecutionRuntimeMixin
from .action_receipts import (
    ActionExecutionResult,
    ActionResultCollector,
    action_execution_result,
    active_ai_authorization_ref,
    canonical_active_ai_receipt_dispositions,
    decision_action_result_from_ha_result,
)
from .action_normalization import (
    action_domain,
    action_entity_id,
    action_requires_presence_refresh,
)
from .const import (
    ACTION_PARAM_KEYS_COLOR,
    ACTION_PARAM_KEYS_LIGHT_SCENE,
    ACTION_PARAM_KEYS_USELESS_WHEN_OFF,
    DEVICE_CONTROL_MODES,
    DEVICE_CAP_KEY_COVERAGE_SPACES,
    DEVICE_CAP_KEY_SHARED_FIXTURE,
    MODE_SHOWROOM,
)
from .execution_gate import (
    evaluate_automation_conflict_window,
    evaluate_color_temp_mireds_param,
    evaluate_proactive_priority_handoff,
    evaluate_global_suppress_window,
    evaluate_manual_override_window,
    evaluate_self_trigger_protection,
    evaluate_thin_execution_gate,
)

_LOGGER = logging.getLogger(__name__)


class ActionsMixin(ActionExecutionRuntimeMixin):
    """Mixin: 动作执行 — 路由 / 保护 / 验证 / 重试。"""

    def _get_showroom_light_tier_v2(self, entity_id: str) -> str:
        """Return the neutral tier after HA-local showroom preference storage removal."""
        return "core"

    _ActionExecutionResult = ActionExecutionResult

    # 合法的设备管辖域值（DatabaseMixin 也定义了此常量，MRO 取第一个即可）
    _VALID_CONTROL_MODES = DEVICE_CONTROL_MODES

    # 设备管辖域标签（用于日志）
    _CONTROL_MODE_LABELS = {"ai": "AI全权", "ha": "HA优先", "shared": "共享"}

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
    _DAYLIGHT_EVIDENCE_SCHEMA_VERSION = "smartagent.daylight_evidence.v2"
    _DAYLIGHT_EVIDENCE_REF_PREFIX = "daylight_evidence:"
    _DAYLIGHT_EVIDENCE_MAX_AGE_SECONDS = 30
    _DAYLIGHT_EVIDENCE_FIELDS = frozenset(
        {
            "schema_version",
            "guard",
            "provenance",
            "world_snapshot_id",
            "decision_time",
            "observed_at",
            "active_space_id",
            "environment_bucket",
            "illuminance_lux",
            "threshold_lux",
            "source_entity_id",
            "source_space_id",
            "source_event_id",
            "source_signal_kind",
            "source_unit",
            "source",
            "freshness_max_age_seconds",
            "plan_fingerprint",
            "commands_digest",
            "target_bindings",
            "reason_code",
            "evidence_digest",
        }
    )
    _DAYLIGHT_FALLBACK_START_HOUR = 8
    _DAYLIGHT_FALLBACK_END_HOUR = 20
    _PROTECTED_NIGHT_START_HOUR = 22

    _active_ai_authorization_ref = staticmethod(active_ai_authorization_ref)
    _PROTECTED_NIGHT_END_HOUR = 6
    _DAYLIGHT_SUN_STATES = frozenset({"above_horizon", "day", "daylight"})
    _DARK_SUN_STATES = frozenset({"below_horizon", "night", "dark"})

    @classmethod
    def _action_requires_presence_refresh(cls, action: Any) -> bool:
        """Match the action shapes that will use the Presence turn-off guard."""
        return action_requires_presence_refresh(
            action,
            dim_to_off_brightness_pct=cls._DIM_TO_OFF_BRIGHTNESS_PCT,
        )

    _action_execution_result = staticmethod(action_execution_result)
    _decision_action_result_from_ha_result = staticmethod(decision_action_result_from_ha_result)

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

    def _daylight_auto_lighting_execution_evaluation(
        self,
        entity_id: str,
        domain: str,
        service: str,
        *,
        actions: list[dict[str, Any]],
        require_world_snapshot_guard: bool,
        decision_contract_lineage: dict[str, Any] | None,
        world_snapshot_id: str,
        active_space_id: str,
        decision_time: str,
    ) -> dict[str, Any]:
        """Validate the planning daylight fact without rebuilding HA state."""

        if not require_world_snapshot_guard:
            reason = self._daylight_auto_lighting_suppressed_reason(entity_id)
            return {
                "guard": "daylight_auto_lighting",
                "allowed": not bool(reason),
                "reason_code": reason or "legacy_runtime_not_daylight",
                "evidence_source": "legacy_ha_runtime",
            }

        lineage = (
            decision_contract_lineage
            if isinstance(decision_contract_lineage, dict)
            else {}
        )
        evidence = (
            lineage.get("daylight_evidence")
            if isinstance(lineage.get("daylight_evidence"), dict)
            else {}
        )
        policy = (
            lineage.get("policy_evaluation")
            if isinstance(lineage.get("policy_evaluation"), dict)
            else {}
        )
        freshness: dict[str, Any] = {
            "observed_at": str(evidence.get("observed_at") or "").strip(),
            "decision_time": str(evidence.get("decision_time") or "").strip(),
            "max_age_seconds": evidence.get("freshness_max_age_seconds"),
            "age_seconds": None,
        }
        evaluation: dict[str, Any] = {
            "guard": "daylight_auto_lighting",
            "allowed": False,
            "reason_code": "daylight_evidence_missing",
            "evidence_source": "sealed_planning_evidence",
            "provenance": str(evidence.get("provenance") or "").strip(),
            "illuminance_lux": evidence.get("illuminance_lux"),
            "threshold_lux": evidence.get("threshold_lux"),
            "source_entity_id": str(evidence.get("source_entity_id") or "").strip(),
            "source_space_id": str(evidence.get("source_space_id") or "").strip(),
            "target_entity_id": str(entity_id or "").strip(),
            "target_space_id": "",
            "freshness": freshness,
            "world_snapshot_id": str(
                evidence.get("world_snapshot_id") or world_snapshot_id or ""
            ).strip(),
            "evidence_digest": str(evidence.get("evidence_digest") or "").strip().lower(),
            "policy_evaluation_id": str(policy.get("evaluation_id") or "").strip(),
        }

        def _reject(reason_code: str) -> dict[str, Any]:
            evaluation["reason_code"] = reason_code
            return evaluation

        def _canonical(value: Any, *, depth: int = 0) -> Any:
            if depth > 6:
                raise ValueError("canonical depth exceeded")
            if value is None or isinstance(value, (bool, int)):
                return value
            if isinstance(value, float):
                if not isfinite(value):
                    raise ValueError("non-finite value")
                return int(value) if value.is_integer() else value
            if isinstance(value, str):
                text = value.strip()
                if len(text) > 512 or any(
                    ord(char) < 32 or ord(char) == 127 for char in text
                ):
                    raise ValueError("invalid text")
                return text
            if isinstance(value, dict):
                if len(value) > 128:
                    raise ValueError("object too large")
                return {
                    str(key): _canonical(item, depth=depth + 1)
                    for key, item in sorted(
                        value.items(), key=lambda item: str(item[0])
                    )
                }
            if isinstance(value, (list, tuple)):
                if len(value) > 128:
                    raise ValueError("array too large")
                return [_canonical(item, depth=depth + 1) for item in value]
            raise ValueError("unsupported canonical type")

        def _digest(value: Any, *, ensure_ascii: bool) -> str:
            encoded = json.dumps(
                _canonical(value),
                ensure_ascii=ensure_ascii,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

        def _action_command(action: dict[str, Any]) -> dict[str, Any] | None:
            target = action.get("target") if isinstance(action.get("target"), dict) else {}
            action_entity = str(
                action.get("entity_id")
                or action.get("entity")
                or target.get("entity_id")
                or ""
            ).strip()
            service_raw = str(
                action.get("service")
                or action.get("action")
                or action.get("command")
                or ""
            ).strip()
            action_domain = str(action.get("domain") or "").strip().lower()
            action_service = service_raw
            if "." in service_raw:
                service_domain, action_service = service_raw.split(".", 1)
                if not action_domain:
                    action_domain = service_domain.strip().lower()
            if not action_domain and "." in action_entity:
                action_domain = action_entity.split(".", 1)[0].lower()
            params = action.get("params")
            if not isinstance(params, dict):
                params = action.get("data")
            if not isinstance(params, dict):
                params = action.get("service_data")
            if not isinstance(params, dict):
                params = {}
            if not action_entity or not action_domain or not action_service:
                return None
            return {
                "entity_id": action_entity,
                "domain": action_domain,
                "service": action_service.strip(),
                "data": _canonical(params),
            }

        def _entity_space(bound_entity_id: str, info: Any = None) -> str:
            if info is None:
                info = self.device_info.get(bound_entity_id)
            if not isinstance(info, dict):
                info = {}
            for key in ("space_id", "room", "area", "control_zone"):
                value = str(info.get(key) or "").strip()
                if value:
                    return value
            if hasattr(self, "_get_entity_area"):
                return str(self._get_entity_area(bound_entity_id) or "").strip()
            return ""

        if not evidence:
            return evaluation
        if (
            frozenset(evidence) != self._DAYLIGHT_EVIDENCE_FIELDS
            or evidence.get("schema_version") != self._DAYLIGHT_EVIDENCE_SCHEMA_VERSION
        ):
            return _reject("daylight_evidence_schema_invalid")
        if (
            evidence.get("guard") != "daylight_auto_lighting"
            or evidence.get("provenance") != "server_planning_state_observation"
            or evidence.get("source") != "ha_state"
            or evidence.get("environment_bucket") != "dark"
            or evidence.get("reason_code") != "sealed_dark_lux_evidence"
        ):
            return _reject("daylight_evidence_provenance_invalid")
        supplied_digest = str(evidence.get("evidence_digest") or "").strip().lower()
        if len(supplied_digest) != 64 or any(
            char not in "0123456789abcdef" for char in supplied_digest
        ):
            return _reject("daylight_evidence_digest_invalid")
        try:
            expected_digest = _digest(
                {key: value for key, value in evidence.items() if key != "evidence_digest"},
                ensure_ascii=True,
            )
        except (TypeError, ValueError):
            return _reject("daylight_evidence_digest_invalid")
        if expected_digest != supplied_digest:
            return _reject("daylight_evidence_digest_mismatch")

        policy_digest = str(policy.get("evaluation_digest") or "").strip().lower()
        policy_id = str(policy.get("evaluation_id") or "").strip()
        if not policy or len(policy_digest) != 64:
            return _reject("daylight_policy_evaluation_missing")
        try:
            expected_policy_digest = _digest(
                {
                    key: value
                    for key, value in policy.items()
                    if key not in {"evaluation_id", "evaluation_digest"}
                },
                ensure_ascii=True,
            )
        except (TypeError, ValueError):
            return _reject("daylight_policy_evaluation_invalid")
        if (
            expected_policy_digest != policy_digest
            or policy_id != f"policy-eval-{policy_digest[:24]}"
            or str(lineage.get("policy_evaluation_id") or "").strip() != policy_id
            or str(lineage.get("policy_evaluation_digest") or "").strip().lower()
            != policy_digest
        ):
            return _reject("daylight_policy_evaluation_digest_mismatch")
        if (
            str(policy.get("request_id") or "").strip()
            != str(lineage.get("decision_request_id") or "").strip()
            or str(policy.get("aggregate_decision") or "").strip().lower()
            != str(lineage.get("policy_aggregate_decision") or "").strip().lower()
        ):
            return _reject("daylight_policy_evaluation_lineage_mismatch")
        policy_refs = policy.get("evidence_refs")
        evidence_ref = f"{self._DAYLIGHT_EVIDENCE_REF_PREFIX}{supplied_digest}"
        if not isinstance(policy_refs, list) or evidence_ref not in policy_refs:
            return _reject("daylight_evidence_policy_binding_missing")

        snapshot_id = str(world_snapshot_id or "").strip()
        fingerprint = str(lineage.get("plan_fingerprint") or "").strip().lower()
        normalized_decision_time = str(decision_time or "").strip()
        normalized_active_space = str(active_space_id or "").strip()
        if (
            not snapshot_id
            or snapshot_id == "unknown"
            or str(evidence.get("world_snapshot_id") or "").strip() != snapshot_id
            or str(lineage.get("world_snapshot_id") or "").strip() != snapshot_id
            or str(policy.get("world_snapshot_id") or "").strip() != snapshot_id
        ):
            return _reject("daylight_evidence_snapshot_mismatch")
        if (
            not normalized_decision_time
            or str(evidence.get("decision_time") or "").strip()
            != normalized_decision_time
            or str(lineage.get("decision_time") or "").strip()
            != normalized_decision_time
        ):
            return _reject("daylight_evidence_decision_time_mismatch")
        if (
            len(fingerprint) != 64
            or str(evidence.get("plan_fingerprint") or "").strip().lower()
            != fingerprint
            or str(policy.get("plan_fingerprint") or "").strip().lower()
            != fingerprint
        ):
            return _reject("daylight_evidence_plan_mismatch")
        if (
            not normalized_active_space
            or str(evidence.get("active_space_id") or "").strip()
            != normalized_active_space
        ):
            return _reject("daylight_evidence_active_space_mismatch")

        source_entity_id = str(evidence.get("source_entity_id") or "").strip()
        source_space_id = str(evidence.get("source_space_id") or "").strip()
        source_event_id = str(evidence.get("source_event_id") or "").strip()
        source_info = self.device_info.get(source_entity_id)
        if not isinstance(source_info, dict):
            source_info = (getattr(self, "_environment_context_device_info", {}) or {}).get(source_entity_id)
        if not isinstance(source_info, dict):
            source_info = {}
        source_kind = str(
            source_info.get("device_class")
            or source_info.get("signal_kind")
            or source_info.get("capability")
            or ""
        ).strip().lower()
        source_unit = str(
            source_info.get("unit_of_measurement")
            or source_info.get("canonical_unit")
            or ""
        ).strip().lower()
        if (
            not source_entity_id.startswith("sensor.")
            or evidence.get("source_signal_kind") != "illuminance"
            or evidence.get("source_unit") not in {"lx", "lux"}
            or (source_kind and source_kind not in {"illuminance", "lux"})
            or (source_unit and source_unit not in {"lx", "lux"})
            or source_space_id != normalized_active_space
            or _entity_space(source_entity_id, source_info) != source_space_id
            or source_event_id
            != f"ha_state:{source_entity_id}:{str(evidence.get('observed_at') or '').strip()}"
        ):
            return _reject("daylight_evidence_source_binding_mismatch")

        target_bindings = evidence.get("target_bindings")
        if not isinstance(target_bindings, list):
            return _reject("daylight_evidence_target_binding_missing")
        matching_targets = [
            row
            for row in target_bindings
            if isinstance(row, dict)
            and str(row.get("entity_id") or "").strip() == entity_id
            and str(row.get("domain") or "").strip() == domain
            and str(row.get("service") or "").strip() == service
        ]
        actual_target_space = _entity_space(entity_id)
        evaluation["target_space_id"] = actual_target_space
        if (
            len(matching_targets) != 1
            or not actual_target_space
            or actual_target_space != normalized_active_space
            or str(matching_targets[0].get("space_id") or "").strip()
            != actual_target_space
        ):
            return _reject("daylight_evidence_target_binding_mismatch")

        commands: list[dict[str, Any]] = []
        try:
            for action in actions:
                command = _action_command(action)
                if command is None:
                    return _reject("daylight_evidence_commands_invalid")
                commands.append(command)
            expected_commands_digest = _digest(commands, ensure_ascii=False)
        except (TypeError, ValueError):
            return _reject("daylight_evidence_commands_invalid")
        if (
            not commands
            or str(evidence.get("commands_digest") or "").strip().lower()
            != expected_commands_digest
        ):
            return _reject("daylight_evidence_commands_mismatch")

        raw_lux = evidence.get("illuminance_lux")
        raw_threshold = evidence.get("threshold_lux")
        if (
            isinstance(raw_lux, bool)
            or isinstance(raw_threshold, bool)
            or not isinstance(raw_lux, (int, float))
            or not isinstance(raw_threshold, (int, float))
        ):
            return _reject("daylight_evidence_lux_invalid")
        lux = float(raw_lux)
        threshold = float(raw_threshold)
        if not isfinite(lux) or threshold != self._DAYLIGHT_GUARD_LUX_THRESHOLD:
            return _reject("daylight_evidence_lux_invalid")
        max_age = evidence.get("freshness_max_age_seconds")
        if type(max_age) is not int or max_age != self._DAYLIGHT_EVIDENCE_MAX_AGE_SECONDS:
            return _reject("daylight_evidence_freshness_invalid")
        try:
            observed = datetime.fromisoformat(
                str(evidence.get("observed_at") or "").strip().replace("Z", "+00:00")
            )
            planned = datetime.fromisoformat(
                normalized_decision_time.replace("Z", "+00:00")
            )
            if observed.tzinfo is None or planned.tzinfo is None:
                raise ValueError("timezone required")
            age_seconds = planned.timestamp() - observed.timestamp()
        except (TypeError, ValueError, OverflowError):
            return _reject("daylight_evidence_freshness_invalid")
        freshness["age_seconds"] = round(age_seconds, 3)
        if age_seconds < 0 or age_seconds > max_age:
            return _reject("daylight_evidence_expired")
        if lux > threshold:
            return _reject(self._DAYLIGHT_AUTO_LIGHTING_SUPPRESSED)
        if (
            policy.get("schema_version") != "0.1"
            or policy.get("stage") != "planning"
            or policy.get("aggregate_decision") != "allow"
            or policy.get("actor_class") != "autonomous_agent"
            or policy.get("execution_intent") != "autonomous"
        ):
            return _reject("daylight_policy_evaluation_not_authorizing")

        evaluation["allowed"] = True
        evaluation["reason_code"] = "sealed_dark_lux_evidence"
        return evaluation

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
        live_getter = getattr(self, "_get_live_presence_occupancy_map", None)
        getter = live_getter
        uses_live_projection = callable(live_getter)
        if not callable(getter):
            getter = getattr(self, "_get_room_occupancy_map", None)
        if not callable(getter):
            return []
        if uses_live_projection:
            self._last_live_presence_guard_status = {"ok": True, "reason": ""}
        try:
            occ_map = getter()
        except Exception:
            if uses_live_projection:
                self._last_live_presence_guard_status = {
                    "ok": False,
                    "reason": "presence_live_projection_failed",
                }
            return []
        if not isinstance(occ_map, dict):
            if uses_live_projection:
                self._last_live_presence_guard_status = {
                    "ok": False,
                    "reason": "presence_live_projection_invalid",
                }
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
        if not legacy:
            return [], ""
        live_getter = getattr(self, "_get_live_presence_occupancy_map", None)
        return legacy, "ha_live_presence_state" if callable(live_getter) else "legacy_occupancy_map"

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
        canonical = self._canonical_room_occupancy_entries(room, room_candidates)
        live = self._legacy_room_occupancy_entries_for_candidates(room, room_candidates)
        live_getter = getattr(self, "_get_live_presence_occupancy_map", None)
        live_source = "ha_live_presence_state" if callable(live_getter) else "legacy_occupancy_map"
        live_status = getattr(self, "_last_live_presence_guard_status", {})
        if (
            callable(live_getter)
            and isinstance(live_status, dict)
            and live_status.get("ok") is False
            and room
        ):
            live = [*live, ("presence.live_guard", "unknown")]
        if canonical and self._presence_entries_conflict(canonical, live):
            self._record_presence_guard_conflict(room, canonical, live)
        else:
            self._last_presence_guard_conflict = {}
        if not room or (not canonical and not live):
            self._last_turnoff_presence_guard_detail = {
                "presence_source": "none",
                "presence_reason": "presence_guard_not_applicable",
                "presence_room": room,
                "presence_evidence_ids": [],
                "presence_states": [],
            }
            return False, ""

        canonical_blocked = [
            (eid, state)
            for eid, state in canonical
            if state == "on" or state in ("unknown", "unavailable")
        ]
        live_blocked = [
            (eid, state)
            for eid, state in live
            if state == "on" or state in ("unknown", "unavailable")
        ]
        blocked_entries: list[tuple[str, str]] = []
        for entry in (*canonical_blocked, *live_blocked):
            if entry not in blocked_entries:
                blocked_entries.append(entry)

        source_parts: list[str] = []
        if canonical_blocked:
            source_parts.append("canonical_presence_snapshot")
        if live_blocked:
            source_parts.append(live_source)
        if not blocked_entries:
            clear_entries: list[tuple[str, str]] = []
            for entry in (*canonical, *live):
                if entry not in clear_entries:
                    clear_entries.append(entry)
            if canonical:
                source_parts.append("canonical_presence_snapshot")
            if live:
                source_parts.append(live_source)
            self._last_turnoff_presence_guard_detail = {
                "presence_source": "+".join(source_parts) or "unknown",
                "presence_reason": "presence_clear",
                "presence_room": room,
                "presence_evidence_ids": [
                    eid for eid, _state in clear_entries if str(eid or "").strip()
                ],
                "presence_states": [
                    {"entity_id": eid, "state": state}
                    for eid, state in clear_entries
                    if str(eid or "").strip()
                ],
            }
            return False, ""
        sensor_str = ", ".join(f"{eid}={state}" for eid, state in blocked_entries[:3])
        projection_conflict = bool(canonical) and bool(live_blocked) and not canonical_blocked
        detail: dict[str, Any] = {
            "presence_source": "+".join(source_parts) or "unknown",
            "presence_reason": (
                "presence_projection_conflict"
                if projection_conflict
                else "presence_not_clear"
            ),
            "presence_room": room,
            "presence_evidence_ids": [
                eid for eid, _state in blocked_entries if str(eid or "").strip()
            ],
            "presence_states": [
                {"entity_id": eid, "state": state}
                for eid, state in blocked_entries
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

    def _normalize_action(
        self,
        action: dict,
        *,
        allow_fuzzy_entity_match: bool = True,
    ) -> dict:
        """Normalize an action while preserving canonical entity identity.

        Legacy callers may still opt into the historical name-to-entity
        compatibility match.  A canonical action must instead retain its
        exact supplied entity id so the execution gate can reject an invalid
        target before any HA I/O.
        """
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
            if not allow_fuzzy_entity_match:
                self._sys_log(
                    "ERROR",
                    f"[动作修正] canonical action returned invalid entity_id「{entity_id}」; "
                    "refusing host-side fuzzy remap",
                )
            else:
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

        priority_override_claim = action.get("priority_override_claim")
        return {"entity_id": entity_id, "domain": domain, "service": service,
                "params": params, "reason": action.get("reason", ""),
                "delay_seconds": action.get("delay_seconds", 0),
                "runtime_hints": action.get("runtime_hints") or {},
                "priority_override_claim": (
                    dict(priority_override_claim)
                    if isinstance(priority_override_claim, dict)
                    else {}
                )}

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

    @staticmethod
    def _smartagent_state_feedback_key(
        command: dict[str, Any],
    ) -> tuple[str, str] | None:
        """Return the state-feedback identity for one SmartAgent light command."""
        entity_id = str(command.get("entity_id") or "").strip()
        domain = str(command.get("domain") or "").strip().lower()
        service = str(command.get("service") or "").strip().lower()
        if not entity_id or domain not in {"light", "switch"}:
            return None
        target_state = {"turn_on": "on", "turn_off": "off"}.get(service)
        return (entity_id, target_state) if target_state else None

    def _begin_smartagent_state_feedback(
        self,
        commands: list[dict[str, Any]],
        *,
        request_id: str,
    ) -> list[tuple[str, str]]:
        """Mark transitions attributable to this in-flight SmartAgent dispatch."""
        registry = getattr(self, "_inflight_smartagent_state_feedback", None)
        if not isinstance(registry, dict):
            registry = {}
            self._inflight_smartagent_state_feedback = registry
        keys: list[tuple[str, str]] = []
        for command in commands:
            key = self._smartagent_state_feedback_key(command)
            if key is None:
                continue
            request_ids = registry.setdefault(key, set())
            if not isinstance(request_ids, set):
                request_ids = set()
                registry[key] = request_ids
            request_ids.add(request_id)
            keys.append(key)
        return keys

    def _end_smartagent_state_feedback(
        self,
        keys: list[tuple[str, str]],
        *,
        request_id: str,
    ) -> None:
        """Release only markers owned by the completed dispatch."""
        registry = getattr(self, "_inflight_smartagent_state_feedback", None)
        if not isinstance(registry, dict):
            return
        for key in keys:
            request_ids = registry.get(key)
            if not isinstance(request_ids, set):
                registry.pop(key, None)
                continue
            request_ids.discard(request_id)
            if not request_ids:
                registry.pop(key, None)

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
        cmd_source: str = "",
        require_world_snapshot_guard: bool = False,
        decision_contract_lineage: dict[str, Any] | None = None,
        user_intent_authority: Any | None = None,
        commands_override: list[dict[str, Any]] | None = None,
        target_space_ids_override: list[str] | None = None,
        return_failed_result: bool = False,
        correlation_id_override: str = "",
    ) -> dict[str, Any]:
        """Execute one canonical command envelope and preserve failure detail.

        ``commands_override`` is reserved for a decision-linked batch whose
        complete ordered command set has already passed every HA-host guard.
        The add-on then authorizes and dispatches that exact set under one
        durable decision grant.  Ordinary callers continue to use the
        single-command projection below.
        """
        from .ha_adapter import async_execute_command_envelope

        payload = call_params if isinstance(call_params, dict) else {}
        is_user_explicit = str(cmd_source or "").strip().upper() == "USER_EXPLICIT"
        active_correlations = getattr(self, "_active_service_correlation_ids", {})
        active_correlation_id = (
            active_correlations.get(asyncio.current_task(), "")
            if isinstance(active_correlations, dict)
            else ""
        )
        normalized_correlation_id = str(
            correlation_id_override or active_correlation_id or ""
        ).strip()
        request_id = (
            f"{normalized_correlation_id}:action:{transaction_id}:{action_seq}:{time.time_ns()}"
            if normalized_correlation_id
            else f"legacy-action:{transaction_id}:{action_seq}:{entity_id}"
        )
        if commands_override is None:
            commands = [{
                "entity_id": entity_id,
                "domain": domain,
                "service": service,
                "data": payload,
            }]
        else:
            if type(commands_override) is not list or not commands_override or any(
                type(command) is not dict for command in commands_override
            ):
                raise RuntimeError("decision_linked_batch_commands_invalid")
            commands = []
            for command in commands_override:
                command_data = command.get("data")
                if type(command_data) is not dict:
                    raise RuntimeError("decision_linked_batch_command_data_invalid")
                normalized_command = {
                    "entity_id": str(command.get("entity_id") or "").strip(),
                    "domain": str(command.get("domain") or "").strip(),
                    "service": str(command.get("service") or "").strip(),
                    "data": dict(command_data),
                }
                if (
                    not normalized_command["entity_id"]
                    or not normalized_command["domain"]
                    or not normalized_command["service"]
                ):
                    raise RuntimeError("decision_linked_batch_command_invalid")
                commands.append(normalized_command)
        if target_space_ids_override is None:
            target_space_ids = (
                [str(target_space_id or "").strip()]
                if str(target_space_id or "").strip()
                else []
            )
        else:
            if type(target_space_ids_override) is not list:
                raise RuntimeError("decision_linked_batch_target_spaces_invalid")
            target_space_ids = []
            for raw_space_id in target_space_ids_override:
                if type(raw_space_id) is not str or not raw_space_id.strip():
                    raise RuntimeError("decision_linked_batch_target_space_invalid")
                normalized_space_id = raw_space_id.strip()
                if normalized_space_id not in target_space_ids:
                    target_space_ids.append(normalized_space_id)
        authorization_ref = self._active_ai_authorization_ref(
            decision_contract_lineage,
            commands,
        ) if require_world_snapshot_guard else None
        envelope = {
            "request_id": request_id,
            "source": (
                "smartagent_user_explicit"
                if is_user_explicit
                else "smartagent_active_ai"
                if require_world_snapshot_guard
                else "smartagent_ha_host"
            ),
            "scope": "home_control",
            "commands": commands,
            "execution_policy": {"stop_on_first_error": True},
            "safety": {
                "risk_level": "safe",
                "requires_confirmation": False,
                "reason": reason,
                "context": {
                    **(
                        {"correlation_id": normalized_correlation_id}
                        if normalized_correlation_id
                        else {}
                    ),
                    **(
                        {
                            "active_ai_managed": not is_user_explicit,
                            **(
                                {
                                    "execution_intent": "user_explicit",
                                    "actor_class": "authenticated_gateway_operator",
                                }
                                if is_user_explicit
                                else {}
                            ),
                            "world_snapshot_id": str(world_snapshot_id or "").strip(),
                            "active_space_id": str(active_space_id or "").strip(),
                            "cmd_source": str(cmd_source or "").strip(),
                            "decision_time": str(decision_time or "").strip(),
                            "target_space_ids": target_space_ids,
                        }
                        if require_world_snapshot_guard
                        else {}
                    )
                },
            },
        }
        if authorization_ref is not None:
            envelope["authorization_ref"] = authorization_ref

        async def _dispatch_with_state_feedback(dispatch: Any) -> Any:
            feedback_keys = (
                []
                if is_user_explicit
                else self._begin_smartagent_state_feedback(
                    commands,
                    request_id=request_id,
                )
            )
            try:
                return await dispatch()
            finally:
                self._end_smartagent_state_feedback(
                    feedback_keys,
                    request_id=request_id,
                )

        result: dict[str, Any] | None
        if require_world_snapshot_guard:
            is_enabled = getattr(self, "_is_enabled", None)
            ai_enabled = (
                bool(is_enabled())
                if callable(is_enabled)
                else bool(getattr(self, "_enabled", False))
            )
            if not ai_enabled and not is_user_explicit:
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
            elif not target_space_ids:
                result = {
                    "ok": False,
                    "error": "active_ai_action_space_missing",
                    "error_type": "policy_rejected",
                    "status": "blocked",
                }
            elif authorization_ref is None:
                result = {
                    "ok": False,
                    "error": "active_ai_authorization_ref_missing",
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
                    if is_user_explicit:
                        from .admin_actor import AuthenticatedOwnerSession

                    if is_user_explicit and type(user_intent_authority) is not AuthenticatedOwnerSession:
                        result = {
                            "ok": False,
                            "error": "household_owner_session_invalid",
                            "error_type": "policy_rejected",
                            "status": "blocked",
                        }
                    else:
                        result = await _dispatch_with_state_feedback(
                            lambda: execute(envelope)
                        )
                    if not isinstance(result, dict):
                        result = {
                            "ok": False,
                            "error": "active_ai_execute_provider_unavailable",
                            "error_type": "upstream_unavailable",
                            "status": "failed",
                        }
        else:
            result = await _dispatch_with_state_feedback(
                lambda: async_execute_command_envelope(self.hass, envelope)
            )
        if (
            require_world_snapshot_guard
            and not is_user_explicit
            and isinstance(result, dict)
            and authorization_ref is not None
        ):
            dispositions = canonical_active_ai_receipt_dispositions(
                result,
                request_id=request_id,
                commands=commands,
                authorization_ref=authorization_ref,
            )
            if dispositions is None:
                result = {
                    "ok": False,
                    "executed": False,
                    "error": "ha_execution_receipt_unverified",
                    "error_type": "ha_service_unverified_success",
                    "status": "failed",
                    "effect_status": "effect_unknown",
                    "workflow_status": "reconciliation_required",
                    "reconciliation_required": True,
                    "results": (
                        list(result.get("results") or [])
                        if isinstance(result.get("results"), list)
                        else []
                    ),
                }
            else:
                result["_smartagent_receipt_dispositions"] = dispositions
        if isinstance(result, dict) and result.get("ok"):
            self._clear_service_call_error(transaction_id, action_seq, entity_id)
            return result
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
        if return_failed_result and isinstance(result, dict):
            return result
        raise RuntimeError(msg)

    async def _record_prepared_service_success(
        self,
        *,
        domain: str,
        service: str,
        entity_id: str,
        params: dict[str, Any],
        reason: str,
        scene_desc: str,
        trigger_text: str,
        transaction_id: int,
        action_seq: int,
        parent_transaction_id: str,
        world_snapshot_id: str,
        correlation_id: str,
        now_ts: float,
        ai_source: str,
        ai_new_state: str,
        occupancy_cycle_id: str = "",
    ) -> None:
        """Apply post-dispatch bookkeeping for one verified batch receipt."""
        self._last_inference[entity_id] = now_ts
        if domain in ("scene", "script") and service == "turn_on":
            self._scene_last_exec[entity_id] = time.time()
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
        with self._user_overrides_lock:
            self._user_overrides.pop(entity_id, None)
        if occupancy_cycle_id:
            self._record_device_operation(
                entity_id,
                ai_source,
                ai_new_state,
                params,
                occupancy_cycle_id=occupancy_cycle_id,
            )
        else:
            self._record_device_operation(entity_id, ai_source, ai_new_state, params)
        normalized_parent_transaction_id = str(parent_transaction_id or "").strip()
        event_detail = f"{entity_id} -> {service}"
        event_metadata: dict[str, Any] = {
            "detail": event_detail,
            "domain": domain,
            "service": service,
            "entity_id": entity_id,
        }
        if params:
            event_metadata["params"] = dict(params)
        if reason:
            event_metadata["reason"] = reason
        if scene_desc:
            event_metadata["scene_desc"] = scene_desc
        if trigger_text:
            event_metadata["trigger_summary"] = trigger_text
        if transaction_id:
            event_metadata["execution_transaction_id"] = int(transaction_id)
        if normalized_parent_transaction_id:
            event_metadata["parent_transaction_id"] = normalized_parent_transaction_id
            event_metadata["decision_trace"] = {
                "available": True,
                "transaction_id": normalized_parent_transaction_id,
                "url": f"/decision-trace/{normalized_parent_transaction_id}",
            }
        if correlation_id:
            event_metadata["correlation_id"] = correlation_id
        self.hass.async_add_executor_job(
            self._record_event,
            "AI_Action",
            event_detail,
            entity_id,
            "on" if "turn_on" in service else "off",
            "ai",
            None,
            transaction_id,
            action_seq,
            event_metadata,
        )
        if service == "turn_off" and trigger_text:
            trigger_lower = trigger_text.lower()
            if any(
                keyword in trigger_lower
                for keyword in ("离开", "departure", "无人", "empty", "人员离开")
            ):
                room = (self.device_info.get(entity_id) or {}).get("room", "")
                if room and hasattr(self, "_last_departure_turnoff_time"):
                    self._last_departure_turnoff_time[room] = time.time()
        await self._async_update_status(
            "运行中",
            f"{self.get_device_name(entity_id)} -> {service} ({reason[:30]})",
        )
        expected = "on" if ("turn_on" in service or "open" in service) else "off"
        if len(self._pending_verifications) < self._VERIFY_QUEUE_MAX:
            self._pending_verifications.append({
                "entity_id": entity_id,
                "domain": domain,
                "service": service,
                "expected_state": expected,
                "reason": reason,
                "fire_time": time.time(),
                "retry": 0,
                "transaction_id": transaction_id,
                "action_seq": action_seq,
                "parent_transaction_id": str(parent_transaction_id or "unknown"),
                "world_snapshot_id": str(world_snapshot_id or "unknown"),
                "correlation_id": correlation_id,
            })
        if domain == "climate" and "turn_on" in service:
            await self._register_env_feedback(entity_id)

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
        cmd_source: str = "",
        require_world_snapshot_guard: bool = False,
        priority_override_claim: dict[str, Any] | None = None,
        decision_contract_lineage: dict[str, Any] | None = None,
        user_intent_authority: Any | None = None,
        prepare_only: bool = False,
    ) -> bool | dict[str, Any]:
        """Call HA service and record AI action for override detection. Returns True if executed.

        Args:
            scene_desc:   本次推理的场景描述，写入 _last_ai_actions 供纠错 UI 展示。
                          并发推理时通过参数传递，避免多房间竞争 self._current_scene_desc。
            trigger_text: 本次推理的触发文本，同上。
        """
        correlation_id = str(correlation_id or "").strip()
        is_user_explicit = str(cmd_source or "").strip().upper() == "USER_EXPLICIT"
        # Host-side AI guards may be bypassed only for the already-authenticated
        # canonical user path.  A raw command-source string is not authority.
        authenticated_user_explicit = False
        if is_user_explicit and require_world_snapshot_guard:
            from .admin_actor import AuthenticatedOwnerSession

            authenticated_user_explicit = (
                type(user_intent_authority) is AuthenticatedOwnerSession
            )
        state = self.hass.states.get(entity_id)
        is_presence_departure_turnoff = (
            service == "turn_off"
            and self._looks_like_presence_departure_turnoff(
                reason=str(reason or ""),
                scene_desc=str(scene_desc or ""),
                trigger_summary=str(trigger_text or ""),
            )
        )
        self._clear_service_call_error(transaction_id, action_seq, entity_id)
        if state and service == "turn_off" and state.state == "off" and not is_presence_departure_turnoff:
            self._remember_service_call_error(
                transaction_id,
                action_seq,
                entity_id,
                msg="already_in_target_state",
                status="skipped",
            )
            return False

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
        if not self_trigger_guard.allowed and not authenticated_user_explicit:
            self._sys_log("WARN", f"[自触发保护] {entity_id} 触发了本次推理，拒绝 AI 操作该设备 → {service}（防止死循环）")
            return _fail_before_service(
                self_trigger_guard.msg,
                error_type=self_trigger_guard.error_type or "self_trigger_protection",
                status=self_trigger_guard.status or "blocked_self_trigger",
            )
        now_ts = time.time()
        # ── 自动化冲突硬拦截：若设备被 HA 自动化管辖且自动化近期执行过，拒绝 AI 操作 ──
        auto_names = self._automation_managed_devices.get(entity_id)
        if auto_names and not authenticated_user_explicit:
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
            target_info = self.device_info.get(entity_id, {}) if isinstance(self.device_info, dict) else {}
            if not isinstance(target_info, dict):
                target_info = {}
            current_cycle_id = str(
                ((decision_contract_lineage or {}).get("occupancy_cycle_id") or "")
                if isinstance(decision_contract_lineage, dict)
                else ""
            ).strip()
            existing_priority_record = (
                self._device_priority_map.get(entity_id)
                if isinstance(getattr(self, "_device_priority_map", None), dict)
                else None
            )
            reentry_override = evaluate_proactive_priority_handoff(
                entity_id=entity_id,
                service=service,
                claim=priority_override_claim,
                existing=existing_priority_record,
                active_space_id=active_space_id,
                target_space_id=target_space_id,
                world_snapshot_id=world_snapshot_id,
                decision_time=decision_time,
                occupancy_cycle_id=current_cycle_id,
                now_ts=now_ts,
                is_lighting=(
                    domain == "light"
                    or str(target_info.get("capability") or "") == "lighting"
                ),
                max_age_seconds=30,
            )
            if authenticated_user_explicit:
                self._sys_log(
                    "INFO",
                    f"[priority] explicit user command bypassed AI anti-flap guard: {entity_id}.{service}",
                )
            elif require_world_snapshot_guard and reentry_override.allowed:
                self._sys_log(
                    "INFO",
                    f"[主动优先级交接] {entity_id} 使用 Core cycle claim 反向动作",
                )
            elif (
                isinstance(existing_priority_record, dict)
                and existing_priority_record.get("priority") in {3, 4}
                and str(existing_priority_record.get("source") or "").strip().lower()
                in {"ai_rule", "ai_infer"}
                and str(existing_priority_record.get("occupancy_cycle_id") or "").strip()
                and (
                    (
                        str(existing_priority_record.get("state") or "").strip().lower()
                        in self._OFF_STATES
                        and ("turn_on" in service or "open" in service)
                    )
                    or (
                        str(existing_priority_record.get("state") or "").strip().lower()
                        not in self._OFF_STATES
                        and ("turn_off" in service or "close" in service)
                    )
                )
            ):
                return _fail_before_service(
                    "priority_guard_active",
                    error_type="priority_guard",
                )
            else:
                allowed, arb_reason = self._arbitrate(entity_id, ai_source, service, params)
                if not allowed:
                    self._sys_log("WARN", arb_reason)
                    return _fail_before_service(
                        str(arb_reason or "priority_guard_rejected"),
                        error_type="priority_guard",
                    )
            # 人工 override 是唯一可配置的时间保护；未配置即禁用。
            with self._user_overrides_lock:
                override = self._user_overrides.get(entity_id)
            manual_guard = evaluate_manual_override_window(
                entity_id=entity_id,
                service=service,
                now_ts=now_ts,
                override=override,
                off_states=self._OFF_STATES,
                window_seconds=getattr(
                    self, "_manual_override_protection_seconds", 0
                ),
            )
            if not manual_guard.allowed and not authenticated_user_explicit:
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
        canonical_service = str(service or "").strip().lower().split(".", 1)[-1]
        ai_new_state = (
            "on" if canonical_service in {"turn_on", "open_cover"} else "off"
        )
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

        if prepare_only:
            return {
                "domain": str(domain or "").strip(),
                "service": str(service or "").strip(),
                "entity_id": str(entity_id or "").strip(),
                "data": dict(safe_params),
                "now_ts": float(now_ts),
                "ai_source": str(ai_source or ""),
                "ai_new_state": str(ai_new_state or ""),
            }

        self._last_inference[entity_id] = now_ts

        def _is_param_rejection(exc: Exception | str) -> bool:
            text = str(exc).lower()
            return "extra keys" in text or "not allowed" in text or "unexpected" in text

        async def _call_enveloped_service(call_data: dict[str, Any]) -> dict[str, Any]:
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
                        "cmd_source": cmd_source,
                        "require_world_snapshot_guard": True,
                        "decision_contract_lineage": decision_contract_lineage,
                        "user_intent_authority": user_intent_authority,
                    }
                    if require_world_snapshot_guard
                    else {}
                )
                return await self._execute_enveloped_service(
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

        envelope_result: dict[str, Any] = {}
        try:
            envelope_result = await _call_enveloped_service(safe_params)
        except Exception as call_err:
            # Canonical active-AI commands are already admitted against an
            # exact command envelope.  Retrying with stripped parameters
            # would change the approved physical effect after admission.
            # Preserve the first failure; only the legacy host path below may
            # retain its historical compatibility fallback.
            if require_world_snapshot_guard:
                if _is_service_missing_error(call_err):
                    self._sys_log("ERROR", f"[动作] {domain}.{service}({entity_id}) 实体/服务不存在，跳过。"
                                  f"请检查设备是否在线或名称是否正确。原始错误: {call_err}")
                    return _fail_after_service(str(call_err), error_type="service_missing")
                self._sys_log("ERROR", f"[动作] {entity_id} canonical 服务调用失败: {call_err}")
                return _fail_after_service(str(call_err))
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
                        envelope_result = await _call_enveloped_service(non_color_params)
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
                            envelope_result = await _call_enveloped_service({})
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
                        envelope_result = await _call_enveloped_service({})
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
        envelope_rows = envelope_result.get("results")
        receipt = (
            envelope_rows[0]
            if isinstance(envelope_rows, list)
            and len(envelope_rows) == 1
            and isinstance(envelope_rows[0], dict)
            else None
        )
        receipt_dispositions = envelope_result.get(
            "_smartagent_receipt_dispositions"
        )
        receipt_disposition = (
            str(receipt_dispositions[0])
            if isinstance(receipt_dispositions, list)
            and len(receipt_dispositions) == 1
            else ""
        )
        if isinstance(receipt, dict) and receipt.get("ok") is True:
            receipt_status = str(receipt.get("status") or "").strip().lower()
            strict_active_ai_receipt = (
                require_world_snapshot_guard and not is_user_explicit
            )
            if (
                receipt.get("executed") is False or receipt_status == "skipped"
            ) and (
                receipt_disposition == "noop" or not strict_active_ai_receipt
            ):
                noop_reason = str(
                    receipt.get("reason") or receipt.get("status") or "already_in_target_state"
                ).strip()
                self._remember_service_call_error(
                    transaction_id,
                    action_seq,
                    entity_id,
                    msg=noop_reason,
                    status="skipped",
                )
                return False
            if (
                receipt.get("executed") is not True
                or (
                    require_world_snapshot_guard
                    and not is_user_explicit
                    and receipt_disposition != "verified_success"
                )
            ):
                return _fail_after_service(
                    "ha_execution_receipt_unverified",
                    error_type="ha_service_unverified_success",
                    status="failed",
                    overwrite_stale=True,
                )
        else:
            return _fail_after_service(
                "ha_execution_receipt_unverified",
                error_type="ha_service_unverified_success",
                status="failed",
                overwrite_stale=True,
            )
        if domain in ("scene", "script") and service == "turn_on":
            self._scene_last_exec[entity_id] = time.time()
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
        occupancy_cycle_id = str(
            ((decision_contract_lineage or {}).get("occupancy_cycle_id") or "")
            if isinstance(decision_contract_lineage, dict)
            else ""
        ).strip()
        if occupancy_cycle_id and not is_user_explicit:
            self._record_device_operation(
                entity_id,
                ai_source,
                ai_new_state,
                params,
                occupancy_cycle_id=occupancy_cycle_id,
            )
        else:
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
                # Verification failure is new world evidence, not authority to
                # replay the old command. The next reconciliation/patrol run
                # must re-read state and obtain a fresh Decision/Policy grant.
                self._sys_log(
                    "ERROR",
                    f"[验证✗] {eid} 期望={expected} 实际={actual}，禁止直接自动重试，等待重新规划",
                )
        self._pending_verifications = remaining
