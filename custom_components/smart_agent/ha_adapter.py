"""HA adapter boundary for add-on command envelopes.

This module is allowed to touch Home Assistant runtime objects. Business
decision modules should stay in the add-on Core and call this boundary through a
plain command envelope.
"""
from __future__ import annotations

import time
from typing import Any
from homeassistant.core import HomeAssistant


def async_get_state(hass: HomeAssistant, entity_id: str) -> Any:
    """最小运行时读取：返回指定实体当前 state 对象。"""
    return hass.states.get(entity_id)


def _state_snapshot(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Serialize the pre-execution HA state needed for rollback/audit."""
    state_obj = async_get_state(hass, entity_id)
    if state_obj is None:
        return {
            "entity_id": entity_id,
            "available": False,
            "state": "",
            "attributes": {},
            "last_changed": "",
            "last_updated": "",
        }
    attrs = getattr(state_obj, "attributes", {})
    return {
        "entity_id": entity_id,
        "available": True,
        "state": str(getattr(state_obj, "state", "") or ""),
        "attributes": attrs if isinstance(attrs, dict) else {},
        "last_changed": str(getattr(state_obj, "last_changed", "") or ""),
        "last_updated": str(getattr(state_obj, "last_updated", "") or ""),
    }


def async_get_entity_registry(hass: HomeAssistant) -> Any:
    """最小运行时读取：返回实体 registry 快照对象。"""
    from homeassistant.helpers import entity_registry as er

    return er.async_get(hass)


def async_get_device_registry(hass: HomeAssistant) -> Any:
    """最小运行时读取：返回设备 registry 快照对象。"""
    from homeassistant.helpers import device_registry as dr

    return dr.async_get(hass)


def async_get_area_registry(hass: HomeAssistant) -> Any:
    """最小运行时读取：返回区域 registry 快照对象。"""
    from homeassistant.helpers import area_registry as ar

    return ar.async_get(hass)


def get_device_info_snapshot(coord: Any) -> dict[str, Any]:
    """最小只读读取面：返回 coord.device_info 的安全 dict 视图。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 该快照用于 presence payload 的组装（第二阶段最小下沉切口）。
    """
    device_info = getattr(coord, "device_info", None)
    if not isinstance(device_info, dict):
        return {}
    return dict(device_info)


def get_room_topology_cache_snapshot(coord: Any) -> dict[Any, set[Any]]:
    """最小只读读取面：返回 coord._room_topology_cache 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 该快照用于 diagnostics/UI 汇总，避免直接读取可变内存态。
    """
    cache = getattr(coord, "_room_topology_cache", None)
    if not isinstance(cache, dict) or not cache:
        return {}

    snapshot: dict[Any, set[Any]] = {}
    for key, raw_value in cache.items():
        if isinstance(raw_value, set):
            snapshot[key] = set(raw_value)
        elif isinstance(raw_value, (list, tuple)):
            snapshot[key] = set(raw_value)
        else:
            snapshot[key] = set()
    return snapshot


def get_transactions_cache_snapshot(coord: Any) -> list[dict[str, Any]]:
    """最小只读读取面：返回 coord._transactions_cache 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。
    """
    cache = getattr(coord, "_transactions_cache", None)
    if not isinstance(cache, list) or not cache:
        return []

    snapshot: list[dict[str, Any]] = []
    for item in cache:
        if isinstance(item, dict):
            snapshot.append(dict(item))
    return snapshot


def get_ai_scenes_cache_snapshot(coord: Any) -> list[dict[str, Any]]:
    """最小只读读取面：返回 coord._ai_scenes_cache 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。
    """
    cache = getattr(coord, "_ai_scenes_cache", None)
    if not isinstance(cache, list) or not cache:
        return []

    snapshot: list[dict[str, Any]] = []
    for item in cache:
        if isinstance(item, dict):
            snapshot.append(dict(item))
    return snapshot


def get_habits_snapshot(coord: Any) -> list[tuple[str, bool]]:
    """最小只读读取面：返回 coord._habits 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。

    兼容说明：
    - 历史上该 helper 命名为 get_habits_snapshot；新增的 get_habits_cache_snapshot 是等价别名，
      用于明确 "cache" 语义，便于未来统一收口。
    """
    habits = getattr(coord, "_habits", None)
    if not isinstance(habits, (list, tuple)) or not habits:
        return []

    snapshot: list[tuple[str, bool]] = []
    for item in habits:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        content, locked = item
        if not isinstance(content, str):
            continue
        snapshot.append((content, bool(locked)))
    return snapshot


def get_habits_cache_snapshot(coord: Any) -> list[tuple[str, bool]]:
    """最小只读读取面：返回 coord._habits 的安全副本（cache 语义别名）。

    说明：
    - 仅负责读取 + 最小形态保护 + 返回安全副本；不承载任何业务逻辑。
    - 与 get_habits_snapshot 等价，避免 WS/HTTP 层直接触碰 coord._habits。
    """
    return get_habits_snapshot(coord)


def get_rules_snapshot(coord: Any) -> list[tuple[str, bool]]:
    """最小只读读取面：返回 coord._rules 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。
    """
    rules = getattr(coord, "_rules", None)
    if not isinstance(rules, (list, tuple)) or not rules:
        return []

    snapshot: list[tuple[str, bool]] = []
    for item in rules:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        content, locked = item
        if not isinstance(content, str):
            continue
        snapshot.append((content, bool(locked)))
    return snapshot


async def async_call_service(
    hass: Any,
    domain: str,
    service: str,
    data: dict[str, Any] | None = None,
    *,
    blocking: bool = True,
) -> None:
    """统一 HA service 调用边界，供宿主桥接层复用。"""
    payload = data if isinstance(data, dict) else {}
    await hass.services.async_call(domain, service, payload, blocking=blocking)


def list_binary_sensor_states(hass: HomeAssistant) -> list[dict[str, Any]]:
    """返回 binary_sensor 的最小只读快照列表。"""
    rows: list[dict[str, Any]] = []
    for st in hass.states.async_all("binary_sensor"):
        attrs = st.attributes if isinstance(st.attributes, dict) else {}
        rows.append({
            "entity_id": st.entity_id,
            "state": st.state,
            "attributes": attrs,
        })
    return rows


async def async_run_in_executor(hass: HomeAssistant, func: Any, *args: Any) -> Any:
    """统一 executor 调用边界，供宿主桥接层复用。"""
    return await hass.async_add_executor_job(func, *args)


_ALLOWED_COMMAND_SERVICES: dict[str, set[str]] = {
    "light": {"turn_on", "turn_off", "toggle"},
    "switch": {"turn_on", "turn_off", "toggle"},
    "input_boolean": {"turn_on", "turn_off", "toggle"},
    "scene": {"turn_on"},
    "cover": {"open_cover", "close_cover", "stop_cover", "set_cover_position"},
    "fan": {"turn_on", "turn_off", "toggle", "set_percentage", "set_preset_mode", "oscillate"},
    "climate": {"turn_on", "turn_off", "set_temperature", "set_hvac_mode", "set_preset_mode"},
    "media_player": {
        "turn_on",
        "turn_off",
        "toggle",
        "media_play",
        "media_pause",
        "media_stop",
        "volume_mute",
        "volume_set",
    },
}


def _json_error(
    request_id: str,
    error: str,
    *,
    error_type: str = "execution_error",
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "request_id": request_id,
        "ok": False,
        "results": [],
        "error": error,
        "error_type": error_type,
        "retryable": retryable,
    }
    if details:
        payload["details"] = details
    return payload


def _envelope_safety_error(envelope: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    safety = envelope.get("safety") if isinstance(envelope, dict) else None
    safety = safety if isinstance(safety, dict) else {}
    risk_level = str(safety.get("risk_level") or "safe").strip().lower()
    requires_confirmation = bool(safety.get("requires_confirmation", False))
    reason = str(safety.get("reason") or "")

    if requires_confirmation:
        return (
            "confirmation_required",
            {
                "risk_level": risk_level,
                "requires_confirmation": True,
                "reason": reason,
            },
        )
    if risk_level != "safe":
        return (
            "unsafe_risk_level",
            {
                "risk_level": risk_level,
                "requires_confirmation": False,
                "reason": reason,
            },
        )
    return None


def _normalize_command(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("command must be an object")
    entity_id = str(raw.get("entity_id") or "").strip()
    domain = str(raw.get("domain") or "").strip()
    service = str(raw.get("service") or "").strip()
    data = raw.get("data", raw.get("params", {}))
    if not entity_id:
        raise ValueError("entity_id required")
    if "." not in entity_id:
        raise ValueError("entity_id must include domain prefix")
    inferred_domain = entity_id.split(".", 1)[0]
    if not domain:
        domain = inferred_domain
    if domain != inferred_domain:
        raise ValueError(f"domain mismatch: {domain} != {inferred_domain}")
    if not service:
        raise ValueError("service required")
    allowed_services = _ALLOWED_COMMAND_SERVICES.get(domain)
    if allowed_services is None or service not in allowed_services:
        raise ValueError(f"unsupported service: {domain}.{service}")
    return {
        "entity_id": entity_id,
        "domain": domain,
        "service": service,
        "data": data if isinstance(data, dict) else {},
    }


async def async_execute_command_envelope(hass: Any, envelope: dict[str, Any]) -> dict[str, Any]:
    """Execute a CommandEnvelope through HA services and return ExecutionResult."""
    request_id = str((envelope or {}).get("request_id") or "")
    if not request_id:
        request_id = "unknown"
    commands_raw = (envelope or {}).get("commands")
    if not isinstance(commands_raw, list) or not commands_raw:
        return _json_error(request_id, "commands_required", error_type="bad_request")
    safety_error = _envelope_safety_error(envelope if isinstance(envelope, dict) else {})
    if safety_error is not None:
        error, details = safety_error
        return _json_error(
            request_id,
            error,
            error_type="safety_blocked",
            retryable=False,
            details=details,
        )

    policy = (envelope or {}).get("execution_policy")
    policy = policy if isinstance(policy, dict) else {}
    stop_on_first_error = bool(policy.get("stop_on_first_error", True))
    results: list[dict[str, Any]] = []
    pre_state_snapshot: list[dict[str, Any]] = []
    stopped_after_error = False
    for raw in commands_raw:
        if stopped_after_error:
            entity_id = str(raw.get("entity_id", "") if isinstance(raw, dict) else "")
            domain = str(raw.get("domain", "") if isinstance(raw, dict) else "")
            service = str(raw.get("service", "") if isinstance(raw, dict) else "")
            results.append({
                "entity_id": entity_id,
                "domain": domain,
                "service": service,
                "ok": False,
                "status": "skipped",
                "error": "command_skipped_after_failure",
                "error_type": "execution_skipped",
                "retryable": False,
                "latency_ms": 0,
                "data": {},
            })
            continue
        started = time.monotonic()
        try:
            command = _normalize_command(raw)
        except ValueError as exc:
            results.append({
                "entity_id": str(raw.get("entity_id", "") if isinstance(raw, dict) else ""),
                "domain": "",
                "service": "",
                "ok": False,
                "error": str(exc),
                "error_type": "bad_request",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "data": {},
                "status": "failed",
            })
            if stop_on_first_error:
                stopped_after_error = True
            continue

        pre_state_snapshot.append(_state_snapshot(hass, command["entity_id"]))
        try:
            await hass.services.async_call(
                command["domain"],
                command["service"],
                {"entity_id": command["entity_id"], **command["data"]},
                blocking=True,
            )
            results.append({
                **command,
                "ok": True,
                "error": "",
                "error_type": "",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "status": "succeeded",
            })
        except Exception as exc:
            results.append({
                **command,
                "ok": False,
                "error": str(exc) or exc.__class__.__name__,
                "error_type": "ha_service_error",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "status": "failed",
            })
            if stop_on_first_error:
                stopped_after_error = True

    ok = bool(results) and all(bool(item.get("ok")) for item in results)
    first_error = next((item for item in results if not item.get("ok")), None)
    succeeded_count = sum(1 for item in results if bool(item.get("ok")))
    failed_count = sum(1 for item in results if not bool(item.get("ok")) and item.get("status") != "skipped")
    skipped_count = sum(1 for item in results if item.get("status") == "skipped")
    partial_success = succeeded_count > 0 and (failed_count > 0 or skipped_count > 0)
    rollback_available = bool(pre_state_snapshot)
    rollback_mode = "manual" if rollback_available else "not_supported"
    return {
        "request_id": request_id,
        "ok": ok,
        "results": results,
        "pre_state_snapshot": pre_state_snapshot,
        "partial_success": partial_success,
        "stop_on_first_error": stop_on_first_error,
        "command_status": {
            "succeeded": succeeded_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "partial_success": partial_success,
        },
        "rollback_available": rollback_available,
        "rollback_mode": rollback_mode,
        "rollback_intent": {
            "required": bool(pre_state_snapshot),
            "strategy": "restore_pre_state",
            "state_snapshot_captured": bool(pre_state_snapshot),
            "state_snapshot": pre_state_snapshot,
            "available": rollback_available,
            "mode": rollback_mode,
            "failure_policy": "stop_on_first_error" if stop_on_first_error else "continue_on_error",
        },
        "error": str(first_error.get("error", "") if first_error else ""),
        "error_type": str(first_error.get("error_type", "") if first_error else ""),
        "retryable": bool(first_error.get("retryable", False) if first_error else False),
    }
