"""Portable add-on settings and listener synchronization for the HA coordinator."""
from __future__ import annotations

import logging
from typing import Any


_LOGGER = logging.getLogger(__name__)


def report_addon_sync_failure(owner: Any, operation: str, exception_type: str) -> bool:
    """Warn once per failed synchronization episode, without response or exception text."""
    failures = getattr(owner, "_addon_sync_failures", None)
    if failures is None:
        failures = owner._addon_sync_failures = {}
    count = failures.get(operation, 0)
    failures[operation] = count + 1
    if count == 0:
        _LOGGER.warning("[AddonSync] operation=%s outcome=failed exception_type=%s", operation, exception_type)
    return False


def report_addon_sync_recovery(owner: Any, operation: str) -> bool:
    count = getattr(owner, "_addon_sync_failures", {}).pop(operation, 0)
    if count:
        _LOGGER.info("[AddonSync] operation=%s outcome=recovered failed_attempts=%s", operation, count)
    return True


async def _fetch_addon_settings(owner: Any) -> dict[str, Any] | None:
    client = getattr(owner, "_addon_client", None)
    if client is None:
        report_addon_sync_failure(owner, "settings", "client_unavailable")
        return None
    try:
        payload = await client.get_system_settings()
    except Exception as exc:
        report_addon_sync_failure(owner, "settings", type(exc).__name__)
        return None
    if not isinstance(payload, dict) or payload.get("ok") is False or payload.get("__status", 200) != 200:
        report_addon_sync_failure(owner, "settings", "response_unavailable")
        return None
    return payload


async def sync_listener_resources(owner: Any, *, reason: str) -> bool:
    """Keep the existing sequence; device refresh returns changed, not success."""
    try:
        await owner._async_refresh_device_info_from_addon_devices(reason=reason)
        devices_ok = getattr(owner, "_last_addon_device_sync_status", {}).get("ok") is True
        if reason == "periodic_listener":
            await owner.async_refresh_device_areas()
        memory_ok = await owner._async_refresh_memory_assets_from_addon()
        if reason == "periodic_listener" and owner._refresh_listeners_if_entity_set_changed():
            _LOGGER.debug("[Listeners] refreshed subscriptions after managed entity set changed")
    except Exception as exc:
        return report_addon_sync_failure(owner, "listener_resources", type(exc).__name__)
    if devices_ok is not True or memory_ok is not True:
        return report_addon_sync_failure(owner, "listener_resources", "response_unavailable")
    return report_addon_sync_recovery(owner, "listener_resources")


def _changed(owner: Any, attribute: str, value: Any, applied: list[str], label: str) -> bool:
    if value == getattr(owner, attribute):
        return False
    setattr(owner, attribute, value)
    applied.append(label)
    return True


def _integer(payload: dict[str, Any], key: str, current: int) -> int:
    try:
        return int(float(payload.get(key)))
    except (TypeError, ValueError):
        return current


def _apply_inference_settings(
    owner: Any,
    payload: dict[str, Any],
    applied: list[str],
) -> None:
    if "engine" in payload:
        value = (
            "online"
            if str(payload.get("engine") or "").strip().lower() == "online"
            else "local"
        )
        _changed(owner, "engine", value, applied, f"engine={value}")
    if "ollama_url" in payload:
        value = str(payload.get("ollama_url") or "").strip() or "http://127.0.0.1:11434"
        _changed(owner, "ollama_url", value, applied, "ollama_url=updated")
    if "ollama_model" in payload:
        value = str(payload.get("ollama_model") or "").strip()
        if value:
            _changed(owner, "ollama_model", value, applied, f"ollama_model={value}")
    if "online_base_url" in payload:
        value = str(payload.get("online_base_url") or "").strip()
        if value:
            _changed(owner, "online_base_url", value, applied, "online_base_url=updated")
    if "online_model" in payload:
        value = str(payload.get("online_model") or "").strip()
        if value:
            _changed(owner, "online_model", value, applied, f"online_model={value}")
    if "online_api_key" in payload:
        value = str(payload.get("online_api_key") or "").strip()
        if value and set(value) != {"*"}:
            _changed(owner, "_online_api_key", value, applied, "online_api_key=updated")
    if "cloud_fallback" in payload:
        value = bool(payload.get("cloud_fallback"))
        _changed(owner, "_cloud_fallback", value, applied, f"cloud_fallback={value}")
    for key, attribute in (
        ("confidence_auto", "confidence_auto"),
        ("confidence_notify", "confidence_notify"),
        ("cooldown", "cooldown"),
    ):
        if key not in payload:
            continue
        value = _integer(payload, key, int(getattr(owner, attribute)))
        _changed(owner, attribute, value, applied, f"{key}={value}")


def _patrol_identifiers(payload: dict[str, Any], key: str) -> tuple[str, ...] | None:
    if key not in payload:
        return None
    raw_values = payload.get(key)
    if not isinstance(raw_values, (list, tuple, set)):
        return ()
    return tuple(
        dict.fromkeys(
            str(value or "").strip()
            for value in raw_values
            if str(value or "").strip()
        )
    )


def _patrol_hhmm(payload: dict[str, Any], key: str) -> str | None:
    if key not in payload:
        return None
    value = str(payload.get(key) or "").strip()
    if not value:
        return ""
    parts = value.split(":", 1)
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return ""
    hour, minute = (int(part) for part in parts)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return ""
    return f"{hour:02d}:{minute:02d}"


def _apply_patrol_settings(
    owner: Any,
    payload: dict[str, Any],
    applied: list[str],
) -> None:
    if "patrol_enabled" in payload:
        value = bool(payload.get("patrol_enabled"))
        _changed(owner, "_patrol_enabled", value, applied, f"patrol_enabled={value}")
    if "patrol_interval_minutes" in payload:
        current = int(getattr(owner, "_patrol_interval_minutes"))
        value = _integer(payload, "patrol_interval_minutes", current)
        if not 5 <= value <= 1440:
            value = current
        _changed(
            owner,
            "_patrol_interval_minutes",
            value,
            applied,
            f"patrol_interval_minutes={value}",
        )
    for key, attribute in (
        ("patrol_scope_space_ids", "_patrol_scope_space_ids"),
        ("patrol_excluded_space_ids", "_patrol_excluded_space_ids"),
        ("patrol_low_risk_entity_ids", "_patrol_low_risk_entity_ids"),
    ):
        value = _patrol_identifiers(payload, key)
        if value is not None:
            _changed(owner, attribute, value, applied, f"{key}={len(value)}")
    for key, attribute in (
        ("patrol_quiet_hours_start", "_patrol_quiet_hours_start"),
        ("patrol_quiet_hours_end", "_patrol_quiet_hours_end"),
    ):
        value = _patrol_hhmm(payload, key)
        if value is not None:
            _changed(owner, attribute, value, applied, f"{key}={bool(value)}")


def _apply_mode_and_learning_settings(
    owner: Any,
    payload: dict[str, Any],
    applied: list[str],
) -> None:
    if "mode" in payload:
        value = (
            "showroom"
            if str(payload.get("mode") or "").strip().lower() == "showroom"
            else "home"
        )
        _changed(owner, "_mode", value, applied, f"mode={value}")
    if "learning_mode" in payload:
        value = bool(payload.get("learning_mode"))
        _changed(owner, "_learning_mode", value, applied, f"learning_mode={value}")
    # Only a persisted SmartAgent setting owns the product mode.  The add-on
    # also returns a normalized ``shadow`` value for an empty settings row;
    # treating that default as authoritative would silently overwrite a
    # legacy engineering canary during migration.
    if (
        "active_ai_mode" in payload
        and str(payload.get("source") or "").strip() == "addon_local"
    ):
        value = str(payload.get("active_ai_mode") or "").strip().lower()
        if value == "on":
            value = "active"
        if value not in {"off", "shadow", "active"}:
            value = "shadow"
        _changed(owner, "_active_ai_mode", value, applied, f"active_ai_mode={value}")
    habit_value = payload.get("habit_proactive")
    if habit_value is not None:
        value = bool(habit_value)
        _changed(owner, "_habit_proactive", value, applied, f"habit_proactive={value}")


async def apply_addon_system_settings(
    owner: Any,
    *,
    apply_presence_timing: Any,
) -> bool:
    """Pull canonical settings and apply them without owning HA lifecycle setup."""
    payload = await _fetch_addon_settings(owner)
    if payload is None:
        return False
    if str(payload.get("source") or "").strip() == "addon_default":
        _LOGGER.debug("[AddonSettings] skip applying unpersisted addon_default payload over live runtime")
        return report_addon_sync_recovery(owner, "settings")

    applied: list[str] = []
    _apply_inference_settings(owner, payload, applied)
    apply_presence_timing(owner, payload, applied)
    _apply_mode_and_learning_settings(owner, payload, applied)
    _apply_patrol_settings(owner, payload, applied)
    if "vision_enabled" in payload:
        value = bool(payload.get("vision_enabled"))
        _changed(owner, "_vision_enabled", value, applied, f"vision_enabled={value}")

    frigate_runtime_action: str | None = None
    if "frigate_enabled" in payload:
        value = bool(payload.get("frigate_enabled"))
        if _changed(
            owner,
            "_frigate_enabled",
            value,
            applied,
            f"frigate_enabled={value}",
        ):
            frigate_runtime_action = "start" if value else "stop"
    if frigate_runtime_action == "start":
        await owner._async_start_frigate_mqtt()
    elif frigate_runtime_action == "stop":
        await owner._async_stop_frigate_mqtt()
    if applied:
        owner._sys_log(
            "INFO",
            "[AddonSettings] 已从 add-on 同步策略开关：" + ", ".join(applied),
        )
        owner.async_set_updated_data({})
    return report_addon_sync_recovery(owner, "settings")


__all__ = ["apply_addon_system_settings"]
