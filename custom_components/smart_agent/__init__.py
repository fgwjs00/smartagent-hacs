"""
AI SmartAgent - Home Assistant Custom Integration.
Proactive smart home AI: device triggers -> LLM inference -> actions.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import voluptuous as vol
import aiohttp
from aiohttp import web
from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.auth import models as auth_models
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, MODE_HOME, MODE_SHOWROOM
from .coordinator import SmartAgentCoordinator
from .host_read_models import (
    async_save_presence_sensor_type as _async_save_presence_sensor_type,
    build_presence_sensors_payload as _build_presence_sensors_payload,
    local_device_rows as _local_device_rows,
    local_room_rows as _local_room_rows,
)
from .ha_adapter import (
    async_call_service,
    async_execute_command_envelope,
    get_ai_scenes_cache_snapshot,
    get_room_topology_cache_snapshot,
    get_transactions_cache_snapshot,
)
from .service_registration import register_smart_agent_services, remove_smart_agent_services, ServiceRegistration
from .websocket_handlers import build_smart_agent_websocket_commands
from .websocket_registration import register_smart_agent_websocket_commands
from .view_registration import register_host_views


# AI Scene snake_case/legacy 仅作为迁移兼容入口，统一集中管理。
AI_SCENE_LIST_MIGRATION_COMPAT_URLS = [
    "/api/v1/ai_scenes",
]
AI_SCENE_ACTION_MIGRATION_COMPAT_URLS = [
    "/api/v1/ai_scenes/approve",
    "/api/v1/ai_scenes/reject",
]
AI_SCENE_TRIGGER_MIGRATION_COMPAT_URLS = [
    "/api/v1/ai_scenes/trigger",
]

_AI_SCENE_LEGACY_COMPAT_PATHS = {
    *AI_SCENE_LIST_MIGRATION_COMPAT_URLS,
    *AI_SCENE_ACTION_MIGRATION_COMPAT_URLS,
    *AI_SCENE_TRIGGER_MIGRATION_COMPAT_URLS,
}
def _env_flag(name: str, default: bool = True) -> bool:
    raw = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _env_csv_set(name: str) -> set[str]:
    raw = str(os.getenv(name, "") or "")
    items = [item.strip().lower() for item in raw.split(",")]
    return {item for item in items if item}


_ACCEPT_LEGACY_AI_SCENE_SNAKE_WRITE = _env_flag("SA_ACCEPT_LEGACY_AI_SCENE_SNAKE_WRITE", True)
_LEGACY_DRYOFF_ENABLED = _env_flag("SA_LEGACY_DRYOFF_ENABLED", False)
_LEGACY_DRYOFF_TARGETS = _env_csv_set("SA_LEGACY_DRYOFF_TARGETS")
_LEGACY_DRYOFF_SUPPORTED_TARGETS = {"ai_scene_snake_write"}
_LEGACY_DRYOFF_DEFAULT_TARGETS: set[str] = set(_LEGACY_DRYOFF_SUPPORTED_TARGETS)
_ACCEPT_LEGACY_ROOT_BASE_LOGS_EXPORT = False
_LEGACY_DRYOFF_SESSION_BOOT_TS = float(time.time())

# HA 面板降级控制：迁移阶段默认进入降级（不作为主入口）。
_HA_PANEL_DEGRADED_MODE = _env_flag("SA_HA_PANEL_DEGRADED_MODE", True)
_HA_PANEL_REGISTER_ENABLED = _env_flag("SA_HA_PANEL_REGISTER_ENABLED", not _HA_PANEL_DEGRADED_MODE)
_HA_PANEL_STATIC_EXPOSED = _env_flag("SA_HA_PANEL_STATIC_EXPOSED", not _HA_PANEL_DEGRADED_MODE)
_HA_SCREEN_STATIC_EXPOSED = _env_flag("SA_HA_SCREEN_STATIC_EXPOSED", True)
_SYSTEM_CPU_SNAPSHOT: tuple[int, int] | None = None


def _clamp_percent(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric != numeric or numeric < 0:
        return 0.0
    if numeric > 100:
        return 100.0
    return round(numeric, 1)


def _read_proc_cpu_snapshot() -> tuple[int, int] | None:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as fp:
            line = fp.readline()
    except OSError:
        return None

    parts = line.split()
    if not parts or parts[0] != "cpu":
        return None
    try:
        values = [int(item) for item in parts[1:]]
    except ValueError:
        return None
    if len(values) < 4:
        return None

    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return sum(values), idle


def _cpu_percent_between(before: tuple[int, int], after: tuple[int, int]) -> float | None:
    total_delta = after[0] - before[0]
    idle_delta = after[1] - before[1]
    if total_delta <= 0 or idle_delta < 0:
        return None
    busy_delta = max(0, total_delta - idle_delta)
    return _clamp_percent((busy_delta * 100.0) / total_delta)


def _read_proc_cpu_percent() -> float | None:
    global _SYSTEM_CPU_SNAPSHOT

    current = _read_proc_cpu_snapshot()
    if current is None:
        return None

    previous = _SYSTEM_CPU_SNAPSHOT
    if previous is None:
        time.sleep(0.05)
        sampled = _read_proc_cpu_snapshot()
        _SYSTEM_CPU_SNAPSHOT = sampled or current
        if sampled is None:
            return None
        return _cpu_percent_between(current, sampled)

    _SYSTEM_CPU_SNAPSHOT = current
    return _cpu_percent_between(previous, current)


def _read_proc_memory_percent() -> float | None:
    fields: dict[str, float] = {}
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as fp:
            for line in fp:
                if ":" not in line:
                    continue
                key, raw_value = line.split(":", 1)
                parts = raw_value.strip().split()
                if not parts:
                    continue
                try:
                    fields[key] = float(parts[0])
                except ValueError:
                    continue
    except OSError:
        return None

    total = fields.get("MemTotal", 0.0)
    available = fields.get("MemAvailable")
    if available is None:
        available = fields.get("MemFree", 0.0) + fields.get("Buffers", 0.0) + fields.get("Cached", 0.0)
    if total <= 0 or available is None:
        return None
    return _clamp_percent(((total - available) * 100.0) / total)


def _collect_system_resource_metrics() -> dict[str, Any]:
    cpu: float | None = None
    memory: float | None = None
    source = "unavailable"

    try:
        import psutil  # type: ignore[import-not-found]

        cpu = _clamp_percent(psutil.cpu_percent(interval=0.05))
        memory = _clamp_percent(psutil.virtual_memory().percent)
        source = "psutil"
    except Exception:
        cpu = _read_proc_cpu_percent()
        memory = _read_proc_memory_percent()
        if cpu is not None or memory is not None:
            source = "procfs"

    return {
        "cpu": cpu if cpu is not None else 0.0,
        "memory": memory if memory is not None else 0.0,
        "resource_metrics": {
            "source": source,
            "cpu_available": cpu is not None,
            "memory_available": memory is not None,
            "sampled_at": datetime.now().isoformat(),
        },
    }


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, str(default)) or str(default)))
    except ValueError:
        return int(default)


def _parse_iso_timestamp(raw: str) -> float | None:
    text = str(raw or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).timestamp()
    return dt.timestamp()


_LEGACY_DRYOFF_SESSION_ENABLED = _env_flag("SA_LEGACY_DRYOFF_SESSION_ENABLED", False)
_LEGACY_DRYOFF_SESSION_DURATION_RAW = str(os.getenv("SA_LEGACY_DRYOFF_SESSION_DURATION_SECONDS", "") or "").strip()
_LEGACY_DRYOFF_SESSION_DURATION_SECONDS = max(
    1,
    _env_int("SA_LEGACY_DRYOFF_SESSION_DURATION_SECONDS", 900),
)
_LEGACY_DRYOFF_SESSION_PRESET = "15m_default" if not _LEGACY_DRYOFF_SESSION_DURATION_RAW else "custom"
_LEGACY_DRYOFF_SESSION_START_AT_TS = _parse_iso_timestamp(
    str(os.getenv("SA_LEGACY_DRYOFF_SESSION_START_AT", "") or "")
)
if _LEGACY_DRYOFF_SESSION_START_AT_TS is None:
    _LEGACY_DRYOFF_SESSION_START_AT_TS = _LEGACY_DRYOFF_SESSION_BOOT_TS

try:
    _LEGACY_DRYOFF_GUARD_WINDOW_SECONDS = max(
        60,
        int(str(os.getenv("SA_LEGACY_DRYOFF_GUARD_WINDOW_SECONDS", "300") or "300")),
    )
except ValueError:
    _LEGACY_DRYOFF_GUARD_WINDOW_SECONDS = 300
try:
    _LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD = max(
        1,
        int(str(os.getenv("SA_LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD", "10") or "10")),
    )
except ValueError:
    _LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD = 10
try:
    _LEGACY_DRYOFF_GUARD_BYPASS_SECONDS = max(
        60,
        int(str(os.getenv("SA_LEGACY_DRYOFF_GUARD_BYPASS_SECONDS", "600") or "600")),
    )
except ValueError:
    _LEGACY_DRYOFF_GUARD_BYPASS_SECONDS = 600

try:
    _LEGACY_ROUTE_WARN_THRESHOLD = max(1, int(str(os.getenv("SA_LEGACY_ROUTE_WARN_THRESHOLD", "50") or "50")))
except ValueError:
    _LEGACY_ROUTE_WARN_THRESHOLD = 50
try:
    _LEGACY_ROUTE_NOISY_MULTIPLIER = max(
        2,
        int(str(os.getenv("SA_LEGACY_ROUTE_NOISY_MULTIPLIER", "3") or "3")),
    )
except ValueError:
    _LEGACY_ROUTE_NOISY_MULTIPLIER = 3
try:
    _LEGACY_ROUTE_EVENT_MAX_PER_ROUTE = max(
        100,
        int(str(os.getenv("SA_LEGACY_ROUTE_EVENT_MAX_PER_ROUTE", "5000") or "5000")),
    )
except ValueError:
    _LEGACY_ROUTE_EVENT_MAX_PER_ROUTE = 5000
_LEGACY_ROUTE_24H_SECONDS = 24 * 60 * 60
_LEGACY_ROUTE_7D_SECONDS = 7 * _LEGACY_ROUTE_24H_SECONDS


def _compact_legacy_route_events(events: list[float], *, now_ts: float) -> list[float]:
    """清理 7d 之外的事件并控制列表上限。"""
    cutoff_7d = now_ts - _LEGACY_ROUTE_7D_SECONDS
    trimmed = [float(ts) for ts in events if float(ts) >= cutoff_7d]
    if len(trimmed) > _LEGACY_ROUTE_EVENT_MAX_PER_ROUTE:
        trimmed = trimmed[-_LEGACY_ROUTE_EVENT_MAX_PER_ROUTE :]
    return trimmed


def _count_legacy_hits_for_window(events: list[float], *, cutoff_ts: float) -> int:
    return sum(1 for ts in events if float(ts) >= cutoff_ts)


def _legacy_hit_window_bounds_iso(events: list[float], *, cutoff_ts: float) -> tuple[str | None, str | None]:
    window_hits = [float(ts) for ts in events if float(ts) >= cutoff_ts]
    if not window_hits:
        return None, None
    first_ts = min(window_hits)
    last_ts = max(window_hits)
    return datetime.fromtimestamp(first_ts).isoformat(), datetime.fromtimestamp(last_ts).isoformat()


def _calc_compat_risk_level(*, any_exceeded: bool, noisy_routes_count: int, hits_24h_total: int, warn_threshold: int) -> str:
    high_hits_threshold = max(1, int(warn_threshold or 1)) * 8
    medium_hits_threshold = max(1, int(warn_threshold or 1)) * 3
    if any_exceeded or noisy_routes_count >= 3 or hits_24h_total >= high_hits_threshold:
        return "high"
    if noisy_routes_count >= 1 or hits_24h_total >= medium_hits_threshold:
        return "medium"
    return "low"


def _build_route_readiness_fields(
    *,
    hits_24h: int,
    hits_7d: int,
    threshold_exceeded: bool,
    noisy: bool,
    warn_threshold: int,
) -> dict[str, Any]:
    medium_hits_threshold = max(1, int(warn_threshold or 1))
    if threshold_exceeded or noisy:
        risk = "high"
    elif hits_24h >= medium_hits_threshold or hits_7d > 0:
        risk = "medium"
    else:
        risk = "low"

    if risk == "low" and hits_7d == 0:
        readiness_status = "deprecate_ready"
        reason = "risk=low 且近 7d 无命中，可进入候选下线"
    elif risk == "high":
        readiness_status = "blocked"
        reason = "存在高风险命中（超阈值或噪声），当前不建议下线"
    else:
        readiness_status = "observe"
        reason = "近 7d 仍有命中或存在中风险，继续观察"

    return {
        "risk": risk,
        "candidate_deprecate": readiness_status == "deprecate_ready",
        "readiness_status": readiness_status,
        "reason": reason,
    }


def _build_deprecation_readiness_payload(hass: HomeAssistant) -> dict[str, Any]:
    stats = _build_legacy_compat_stats_payload(hass)
    routes = stats.get("routes") if isinstance(stats.get("routes"), dict) else {}

    grouped: dict[str, list[dict[str, Any]]] = {
        "deprecate_ready": [],
        "observe": [],
        "blocked": [],
    }

    for path, route_info in routes.items():
        if not isinstance(route_info, dict):
            continue
        item = {
            "path": str(path or ""),
            "route": str(path or ""),
            "route_type": str(route_info.get("route_type") or "unknown"),
            "risk": str(route_info.get("risk") or "low"),
            "hits_24h": int(route_info.get("hits_24h", 0) or 0),
            "hits_7d": int(route_info.get("hits_7d", 0) or 0),
            "reason": str(route_info.get("reason") or ""),
            "candidate_deprecate": bool(route_info.get("candidate_deprecate", False)),
            "readiness_status": str(route_info.get("readiness_status") or "observe"),
        }
        readiness_status = item["readiness_status"]
        if readiness_status not in grouped:
            readiness_status = "observe"
            item["readiness_status"] = readiness_status
        grouped[readiness_status].append(item)

    for key in grouped:
        grouped[key].sort(key=lambda x: (x["risk"], x["hits_7d"], x["path"]))

    return {
        "ok": True,
        "deprecate_ready": grouped["deprecate_ready"],
        "observe": grouped["observe"],
        "blocked": grouped["blocked"],
        "summary": {
            "route_count": int(stats.get("route_count", 0) or 0),
            "hits_24h_total": int(stats.get("hits_24h_total", 0) or 0),
            "hits_7d_total": int(stats.get("hits_7d_total", 0) or 0),
            "compat_risk_level": _build_compat_summary_payload(hass).get("compat_risk_level", "low"),
            "rollout_switches": _build_legacy_rollout_and_dryoff_payload(hass),
        },
    }


def _record_legacy_route_hit(hass: HomeAssistant, *, route_path: str, route_type: str) -> None:
    """记录迁移兼容入口命中次数并在超阈值后告警。"""
    obs_key = f"{DOMAIN}_legacy_route_observability"
    obs = hass.data.setdefault(obs_key, {"counts": {}, "warned": set(), "route_types": {}, "events": {}})
    counts = obs.setdefault("counts", {})
    warned = obs.setdefault("warned", set())
    route_types = obs.setdefault("route_types", {})
    events_by_route = obs.setdefault("events", {})

    count = int(counts.get(route_path, 0)) + 1
    counts[route_path] = count
    route_types[route_path] = str(route_type or "unknown")

    now_ts = time.time()
    route_events = events_by_route.get(route_path)
    route_events_list = route_events if isinstance(route_events, list) else []
    route_events_list.append(now_ts)
    events_by_route[route_path] = _compact_legacy_route_events(route_events_list, now_ts=now_ts)

    if count > _LEGACY_ROUTE_WARN_THRESHOLD and (
        count == _LEGACY_ROUTE_WARN_THRESHOLD + 1 or count % _LEGACY_ROUTE_WARN_THRESHOLD == 0
    ):
        warn_key = f"{route_type}:{route_path}"
        warned.add(warn_key)
        obs["last_warn_at"] = datetime.now().isoformat()
        _LOGGER.warning(
            "[LegacyCompatObs] route_type=%s path=%s hit_count=%s threshold=%s",
            route_type,
            route_path,
            count,
            _LEGACY_ROUTE_WARN_THRESHOLD,
        )


def _record_legacy_route_hit_if_needed(hass: HomeAssistant, request: web.Request) -> None:
    path = str(request.path or "").lower()
    if path in _AI_SCENE_LEGACY_COMPAT_PATHS:
        _record_legacy_route_hit(hass, route_path=path, route_type="ai_scene_snake_case")


def _legacy_reject_payload(*, legacy_group: str, env_name: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "legacy_route_disabled",
        "error_type": "gone",
        "retryable": False,
        "details": {
            "legacy_group": str(legacy_group or "legacy"),
            "switch_env": str(env_name or ""),
            "reason": "legacy compatibility route disabled by rollout switch",
        },
    }


def _legacy_dryoff_target_tags_for_request(request: web.Request) -> set[str]:
    tags: set[str] = set()
    if _is_ai_scene_legacy_write_path(request) and request.method.upper() != "GET":
        tags.add("ai_scene_snake_write")
    return tags


def _legacy_dryoff_active_targets() -> set[str]:
    configured = {
        tag for tag in _LEGACY_DRYOFF_TARGETS if tag in _LEGACY_DRYOFF_SUPPORTED_TARGETS
    }
    if configured:
        return configured
    if _LEGACY_DRYOFF_ENABLED or _LEGACY_DRYOFF_SESSION_ENABLED:
        return {
            tag for tag in _LEGACY_DRYOFF_DEFAULT_TARGETS if tag in _LEGACY_DRYOFF_SUPPORTED_TARGETS
        }
    return set()


def _legacy_dryoff_session_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    obs_key = f"{DOMAIN}_legacy_route_observability"
    raw = hass.data.get(obs_key)
    obs = raw if isinstance(raw, dict) else {}
    now_ts = time.time()

    start_ts = float(_LEGACY_DRYOFF_SESSION_START_AT_TS or _LEGACY_DRYOFF_SESSION_BOOT_TS)
    duration = int(max(1, _LEGACY_DRYOFF_SESSION_DURATION_SECONDS))
    end_ts = start_ts + duration

    session_enabled = bool(_LEGACY_DRYOFF_SESSION_ENABLED)
    session_active = bool(session_enabled and start_ts <= now_ts <= end_ts)
    if session_active:
        remaining = max(0, int(end_ts - now_ts))
    else:
        remaining = 0

    if session_enabled:
        session_block_count = int(obs.get("dryoff_session_block_count", 0) or 0)
        session_last_block_at = obs.get("dryoff_session_last_block_at")
    else:
        session_block_count = 0
        session_last_block_at = None

    return {
        "session_enabled": session_enabled,
        "session_active": session_active,
        "session_preset": _LEGACY_DRYOFF_SESSION_PRESET,
        "session_duration_seconds": int(duration),
        "session_start_at": datetime.fromtimestamp(start_ts).isoformat(),
        "session_end_at": datetime.fromtimestamp(end_ts).isoformat(),
        "session_remaining_seconds": int(remaining),
        "session_block_count": int(session_block_count),
        "session_last_block_at": session_last_block_at,
        "block_count": int(session_block_count),
    }


def _legacy_dryoff_is_effective(hass: HomeAssistant) -> bool:
    if bool(_LEGACY_DRYOFF_ENABLED):
        return True
    session = _legacy_dryoff_session_snapshot(hass)
    return bool(session.get("session_active", False))


def _legacy_dryoff_record_session_block(hass: HomeAssistant, *, now_iso: str) -> None:
    if not _LEGACY_DRYOFF_SESSION_ENABLED:
        return
    session = _legacy_dryoff_session_snapshot(hass)
    if not bool(session.get("session_active", False)):
        return

    obs_key = f"{DOMAIN}_legacy_route_observability"
    raw = hass.data.get(obs_key)
    obs = raw if isinstance(raw, dict) else {}
    obs["dryoff_session_block_count"] = int(obs.get("dryoff_session_block_count", 0) or 0) + 1
    obs["dryoff_session_last_block_at"] = now_iso
    hass.data[obs_key] = obs


def _legacy_dryoff_rehearsal_summary(
    *,
    session_snapshot: dict[str, Any],
    guard_snapshot: dict[str, Any],
) -> dict[str, Any]:
    block_count = int(session_snapshot.get("session_block_count", session_snapshot.get("block_count", 0)) or 0)
    safe_block_max = max(0, int(_LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD) - 1)
    auto_guard_triggered = bool(int(guard_snapshot.get("guard_trigger_count", 0) or 0) > 0)

    if not bool(session_snapshot.get("session_enabled", False)):
        rehearsal_status = "pending"
        rehearsal_result = "unknown"
        rehearsal_reason = "dryoff session not enabled"
    elif bool(session_snapshot.get("session_active", False)):
        rehearsal_status = "active"
        rehearsal_result = "unknown"
        rehearsal_reason = "dryoff session still active; waiting for completion"
    else:
        rehearsal_status = "completed"
        if auto_guard_triggered:
            rehearsal_result = "fail"
            rehearsal_reason = "auto_guard triggered during rehearsal"
        elif block_count > safe_block_max:
            rehearsal_result = "fail"
            rehearsal_reason = f"block_count={block_count} exceeds safe range <= {safe_block_max}"
        else:
            rehearsal_result = "pass"
            rehearsal_reason = f"block_count={block_count} within safe range <= {safe_block_max} and auto_guard not triggered"

    return {
        "rehearsal_status": rehearsal_status,
        "rehearsal_result": rehearsal_result,
        "rehearsal_reason": rehearsal_reason,
        "auto_guard_triggered": auto_guard_triggered,
        "rehearsal_safe_block_max": int(safe_block_max),
    }


def _legacy_dryoff_report_payload(hass: HomeAssistant) -> dict[str, Any]:
    session_snapshot = _legacy_dryoff_session_snapshot(hass)
    guard_snapshot = _legacy_dryoff_guard_snapshot(hass)
    rehearsal = _legacy_dryoff_rehearsal_summary(
        session_snapshot=session_snapshot,
        guard_snapshot=guard_snapshot,
    )
    payload = dict(session_snapshot)
    payload.update(
        {
            "dryoff_guard": guard_snapshot,
            "rehearsal_status": rehearsal.get("rehearsal_status", "pending"),
            "rehearsal_result": rehearsal.get("rehearsal_result", "unknown"),
            "rehearsal_reason": rehearsal.get("rehearsal_reason", ""),
            "auto_guard_triggered": bool(rehearsal.get("auto_guard_triggered", False)),
            "rehearsal_safe_block_max": int(rehearsal.get("rehearsal_safe_block_max", 0) or 0),
        }
    )
    return payload


def _legacy_dryoff_guard_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    obs_key = f"{DOMAIN}_legacy_route_observability"
    raw = hass.data.get(obs_key)
    obs = raw if isinstance(raw, dict) else {}
    now_ts = time.time()
    cutoff_window = now_ts - _LEGACY_DRYOFF_GUARD_WINDOW_SECONDS
    raw_events = obs.get("dryoff_block_events") if isinstance(obs.get("dryoff_block_events"), list) else []
    events = [float(ts) for ts in raw_events if float(ts) >= cutoff_window]
    obs["dryoff_block_events"] = events

    bypass_until_ts = float(obs.get("dryoff_guard_bypass_until_ts", 0.0) or 0.0)
    bypass_active = bypass_until_ts > now_ts
    if bypass_active:
        remaining = max(0, int(bypass_until_ts - now_ts))
    else:
        remaining = 0
        obs["dryoff_guard_bypass_until_ts"] = 0.0

    block_count_window = len(events)
    trigger_count = int(obs.get("dryoff_guard_trigger_count", 0) or 0)
    if (not bypass_active) and block_count_window >= _LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD:
        bypass_until_ts = now_ts + _LEGACY_DRYOFF_GUARD_BYPASS_SECONDS
        obs["dryoff_guard_bypass_until_ts"] = bypass_until_ts
        obs["dryoff_guard_last_trigger_at"] = datetime.now().isoformat()
        trigger_count += 1
        obs["dryoff_guard_trigger_count"] = trigger_count
        bypass_active = True
        remaining = _LEGACY_DRYOFF_GUARD_BYPASS_SECONDS
        _LOGGER.warning(
            "[LegacyDryoffGuard] triggered bypass window=%ss threshold=%s bypass=%ss hits=%s",
            _LEGACY_DRYOFF_GUARD_WINDOW_SECONDS,
            _LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD,
            _LEGACY_DRYOFF_GUARD_BYPASS_SECONDS,
            block_count_window,
        )

    hass.data[obs_key] = obs
    return {
        "guard_enabled": True,
        "guard_window_seconds": int(_LEGACY_DRYOFF_GUARD_WINDOW_SECONDS),
        "guard_block_threshold": int(_LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD),
        "guard_bypass_seconds": int(_LEGACY_DRYOFF_GUARD_BYPASS_SECONDS),
        "guard_block_count_window": int(block_count_window),
        "guard_bypass_active": bool(bypass_active),
        "guard_bypass_until": datetime.fromtimestamp(bypass_until_ts).isoformat() if bypass_until_ts > 0 else None,
        "guard_bypass_remaining_seconds": int(remaining),
        "guard_trigger_count": int(trigger_count),
        "guard_last_trigger_at": obs.get("dryoff_guard_last_trigger_at"),
    }


def _legacy_dryoff_should_bypass(hass: HomeAssistant) -> tuple[bool, dict[str, Any]]:
    snapshot = _legacy_dryoff_guard_snapshot(hass)
    return bool(snapshot.get("guard_bypass_active", False)), snapshot


def _legacy_dryoff_audit_context(
    hass: HomeAssistant,
    request: web.Request,
    *,
    target_tag: str,
    guard_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if guard_snapshot is None:
        _, guard_snapshot = _legacy_dryoff_should_bypass(hass)
    return {
        "route": str(request.path or "").lower(),
        "path": str(request.path or "").lower(),
        "target_tag": str(target_tag or ""),
        "timestamp": datetime.now().isoformat(),
        "env": {
            "SA_LEGACY_DRYOFF_ENABLED": bool(_LEGACY_DRYOFF_ENABLED),
            "SA_LEGACY_DRYOFF_TARGETS": sorted(_legacy_dryoff_active_targets()),
            "SA_LEGACY_DRYOFF_GUARD_WINDOW_SECONDS": int(_LEGACY_DRYOFF_GUARD_WINDOW_SECONDS),
            "SA_LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD": int(_LEGACY_DRYOFF_GUARD_BLOCK_THRESHOLD),
            "SA_LEGACY_DRYOFF_GUARD_BYPASS_SECONDS": int(_LEGACY_DRYOFF_GUARD_BYPASS_SECONDS),
            "SA_LEGACY_DRYOFF_SESSION_ENABLED": bool(_LEGACY_DRYOFF_SESSION_ENABLED),
            "SA_LEGACY_DRYOFF_SESSION_DURATION_SECONDS": int(_LEGACY_DRYOFF_SESSION_DURATION_SECONDS),
            "SA_LEGACY_DRYOFF_SESSION_START_AT": datetime.fromtimestamp(
                float(_LEGACY_DRYOFF_SESSION_START_AT_TS or _LEGACY_DRYOFF_SESSION_BOOT_TS)
            ).isoformat(),
        },
        "guard": guard_snapshot,
    }


def _record_legacy_dryoff_block(hass: HomeAssistant, request: web.Request, *, target_tag: str) -> dict[str, Any]:
    obs_key = f"{DOMAIN}_legacy_route_observability"
    raw = hass.data.get(obs_key)
    obs = raw if isinstance(raw, dict) else {}
    now_ts = time.time()
    now_iso = datetime.now().isoformat()
    obs["dryoff_block_count_24h"] = int(obs.get("dryoff_block_count_24h", 0) or 0) + 1
    obs["dryoff_last_block_at"] = now_iso
    obs["dryoff_last_hit_path"] = str(request.path or "").lower()
    obs["dryoff_last_target"] = str(target_tag or "")
    block_events = obs.get("dryoff_block_events") if isinstance(obs.get("dryoff_block_events"), list) else []
    block_events.append(now_ts)
    obs["dryoff_block_events"] = block_events
    hass.data[obs_key] = obs
    _legacy_dryoff_record_session_block(hass, now_iso=now_iso)
    _, guard_snapshot = _legacy_dryoff_should_bypass(hass)
    audit = _legacy_dryoff_audit_context(
        hass,
        request,
        target_tag=target_tag,
        guard_snapshot=guard_snapshot,
    )
    _LOGGER.warning(
        "[LegacyDryoffBlock] route=%s target_tag=%s env=%s timestamp=%s",
        audit.get("route"),
        audit.get("target_tag"),
        audit.get("env"),
        audit.get("timestamp"),
    )
    return audit


def _legacy_dryoff_reject_payload(*, legacy_group: str, target_tag: str, audit: dict[str, Any] | None = None) -> dict[str, Any]:
    details = {
        "legacy_group": str(legacy_group or "legacy"),
        "target_tag": str(target_tag or ""),
        "switch_env": "SA_LEGACY_DRYOFF_ENABLED",
        "targets_env": "SA_LEGACY_DRYOFF_TARGETS",
        "sunset_phase": "dryoff",
        "reason": "legacy compatibility route blocked by dryoff drill",
    }
    if audit:
        details["audit"] = audit
    return {
        "ok": False,
        "error": "legacy_route_dryoff_blocked",
        "error_type": "gone",
        "retryable": False,
        "details": details,
    }


def _legacy_dryoff_hit_target(hass: HomeAssistant, request: web.Request) -> tuple[str | None, dict[str, Any]]:
    guard_bypass, guard_snapshot = _legacy_dryoff_should_bypass(hass)
    active_targets = _legacy_dryoff_active_targets()
    if (not _legacy_dryoff_is_effective(hass)) or not active_targets:
        return None, guard_snapshot
    matched = _legacy_dryoff_target_tags_for_request(request)
    hit = sorted(matched & active_targets) if matched else []
    if guard_bypass and hit:
        _LOGGER.warning(
            "[LegacyDryoffGuardBypass] route=%s target_tag=%s bypass_remaining=%ss",
            str(request.path or "").lower(),
            hit[0],
            int(guard_snapshot.get("guard_bypass_remaining_seconds", 0) or 0),
        )
        return None, guard_snapshot
    return (hit[0] if hit else None), guard_snapshot


def _legacy_dryoff_status_payload(hass: HomeAssistant) -> dict[str, Any]:
    obs_key = f"{DOMAIN}_legacy_route_observability"
    raw = hass.data.get(obs_key)
    obs = raw if isinstance(raw, dict) else {}
    active_targets = sorted(_legacy_dryoff_active_targets())
    guard_snapshot = _legacy_dryoff_guard_snapshot(hass)
    session_snapshot = _legacy_dryoff_session_snapshot(hass)
    cutoff_24h = time.time() - _LEGACY_ROUTE_24H_SECONDS
    block_events = obs.get("dryoff_block_events") if isinstance(obs.get("dryoff_block_events"), list) else []
    compacted = [float(ts) for ts in block_events if float(ts) >= cutoff_24h]
    obs["dryoff_block_events"] = compacted
    hass.data[obs_key] = obs
    return {
        "dryoff_enabled": bool(_legacy_dryoff_is_effective(hass)),
        "dryoff_targets": active_targets,
        "dryoff_default_targets": sorted(_LEGACY_DRYOFF_DEFAULT_TARGETS),
        "dryoff_block_count_24h": int(len(compacted)),
        "dryoff_last_block_at": obs.get("dryoff_last_block_at"),
        "dryoff_last_hit_path": obs.get("dryoff_last_hit_path"),
        "dryoff_last_target": obs.get("dryoff_last_target"),
        "dryoff_guard": guard_snapshot,
        "dryoff_session": session_snapshot,
    }


def _is_ai_scene_legacy_write_path(request: web.Request) -> bool:
    path = str(request.path or "").lower()
    return bool(path.startswith("/api/v1/ai_scenes/") or path in AI_SCENE_ACTION_MIGRATION_COMPAT_URLS or path in AI_SCENE_TRIGGER_MIGRATION_COMPAT_URLS)


def _legacy_rollout_switches_payload() -> dict[str, Any]:
    return {
        "accept_legacy_ai_scene_snake_write": _ACCEPT_LEGACY_AI_SCENE_SNAKE_WRITE,
        "switch_env": {
            "accept_legacy_ai_scene_snake_write": "SA_ACCEPT_LEGACY_AI_SCENE_SNAKE_WRITE",
        },
        "default_mode": "compatible",
    }


def _build_legacy_rollout_and_dryoff_payload(hass: HomeAssistant) -> dict[str, Any]:
    payload = _legacy_rollout_switches_payload()
    payload.update(_legacy_dryoff_status_payload(hass))
    return payload


def _build_legacy_compat_stats_payload(hass: HomeAssistant) -> dict[str, Any]:
    obs_key = f"{DOMAIN}_legacy_route_observability"
    raw = hass.data.get(obs_key)
    obs = raw if isinstance(raw, dict) else {}
    counts = obs.get("counts") if isinstance(obs.get("counts"), dict) else {}
    warned = obs.get("warned") if isinstance(obs.get("warned"), set) else set()
    route_types = obs.get("route_types") if isinstance(obs.get("route_types"), dict) else {}
    events_by_route = obs.get("events") if isinstance(obs.get("events"), dict) else {}

    now_ts = time.time()
    cutoff_24h = now_ts - _LEGACY_ROUTE_24H_SECONDS
    cutoff_7d = now_ts - _LEGACY_ROUTE_7D_SECONDS

    routes: dict[str, dict[str, Any]] = {}
    any_threshold_exceeded = False
    any_noisy = False
    noisy_routes_count = 0
    hits_24h_total = 0
    hits_7d_total = 0
    for path, count in counts.items():
        p = str(path or "")
        c = int(count or 0)
        exceeded = c > _LEGACY_ROUTE_WARN_THRESHOLD
        route_type = str(route_types.get(p, "unknown") or "unknown")
        warn_key = f"{route_type}:{p}"

        raw_events = events_by_route.get(p)
        route_events = raw_events if isinstance(raw_events, list) else []
        compacted_events = _compact_legacy_route_events(route_events, now_ts=now_ts)
        events_by_route[p] = compacted_events
        hits_24h = _count_legacy_hits_for_window(compacted_events, cutoff_ts=cutoff_24h)
        hits_7d = _count_legacy_hits_for_window(compacted_events, cutoff_ts=cutoff_7d)
        first_hit_at_24h, last_hit_at_24h = _legacy_hit_window_bounds_iso(compacted_events, cutoff_ts=cutoff_24h)
        noisy_threshold = _LEGACY_ROUTE_WARN_THRESHOLD * _LEGACY_ROUTE_NOISY_MULTIPLIER
        noisy = hits_24h > noisy_threshold

        readiness = _build_route_readiness_fields(
            hits_24h=hits_24h,
            hits_7d=hits_7d,
            threshold_exceeded=exceeded,
            noisy=noisy,
            warn_threshold=_LEGACY_ROUTE_WARN_THRESHOLD,
        )

        routes[p] = {
            "route_type": route_type,
            "hit_count": c,
            "hits_24h": hits_24h,
            "hits_7d": hits_7d,
            "first_hit_at_24h": first_hit_at_24h,
            "last_hit_at_24h": last_hit_at_24h,
            "threshold": _LEGACY_ROUTE_WARN_THRESHOLD,
            "threshold_exceeded": exceeded,
            "warned": warn_key in warned,
            "noisy": noisy,
            "noisy_rule": f"hits_24h > warn_threshold * {_LEGACY_ROUTE_NOISY_MULTIPLIER}",
            "noisy_threshold": noisy_threshold,
            "risk": readiness["risk"],
            "candidate_deprecate": readiness["candidate_deprecate"],
            "readiness_status": readiness["readiness_status"],
            "reason": readiness["reason"],
        }
        any_threshold_exceeded = any_threshold_exceeded or exceeded
        any_noisy = any_noisy or noisy
        if noisy:
            noisy_routes_count += 1
        hits_24h_total += hits_24h
        hits_7d_total += hits_7d

    return {
        "ok": True,
        "threshold": {
            "warn_threshold": _LEGACY_ROUTE_WARN_THRESHOLD,
            "any_exceeded": any_threshold_exceeded,
            "noisy_multiplier_24h": _LEGACY_ROUTE_NOISY_MULTIPLIER,
            "any_noisy": any_noisy,
            "noise_rule": f"hits_24h > warn_threshold * {_LEGACY_ROUTE_NOISY_MULTIPLIER}",
        },
        "route_count": len(routes),
        "hits_24h_total": hits_24h_total,
        "hits_7d_total": hits_7d_total,
        "noisy_routes_count": noisy_routes_count,
        "routes": routes,
        "last_warn_at": obs.get("last_warn_at"),
        "rollout_switches": _build_legacy_rollout_and_dryoff_payload(hass),
    }


def _build_compat_summary_payload(hass: HomeAssistant) -> dict[str, Any]:
    stats = _build_legacy_compat_stats_payload(hass)
    threshold = stats.get("threshold") if isinstance(stats.get("threshold"), dict) else {}
    any_exceeded = bool(threshold.get("any_exceeded", False))
    hits_24h_total = int(stats.get("hits_24h_total", 0) or 0)
    noisy_routes_count = int(stats.get("noisy_routes_count", 0) or 0)
    compat_risk_level = _calc_compat_risk_level(
        any_exceeded=any_exceeded,
        noisy_routes_count=noisy_routes_count,
        hits_24h_total=hits_24h_total,
        warn_threshold=_LEGACY_ROUTE_WARN_THRESHOLD,
    )
    dryoff = _legacy_dryoff_status_payload(hass)
    session = dryoff.get("dryoff_session") if isinstance(dryoff.get("dryoff_session"), dict) else {}
    guard_snapshot = dryoff.get("dryoff_guard") if isinstance(dryoff.get("dryoff_guard"), dict) else {}
    rehearsal = _legacy_dryoff_rehearsal_summary(
        session_snapshot=session,
        guard_snapshot=guard_snapshot,
    )
    session_summary = {
        "session_enabled": bool(session.get("session_enabled", False)),
        "session_active": bool(session.get("session_active", False)),
        "session_preset": session.get("session_preset"),
        "session_duration_seconds": int(session.get("session_duration_seconds", 0) or 0),
        "session_start_at": session.get("session_start_at"),
        "session_end_at": session.get("session_end_at"),
        "session_remaining_seconds": int(session.get("session_remaining_seconds", 0) or 0),
        "session_block_count": int(session.get("session_block_count", 0) or 0),
        "session_last_block_at": session.get("session_last_block_at"),
        "block_count": int(session.get("session_block_count", session.get("block_count", 0)) or 0),
        "rehearsal_status": rehearsal.get("rehearsal_status", "pending"),
        "rehearsal_result": rehearsal.get("rehearsal_result", "unknown"),
        "rehearsal_reason": rehearsal.get("rehearsal_reason", ""),
        "auto_guard_triggered": bool(rehearsal.get("auto_guard_triggered", False)),
        "rehearsal_safe_block_max": int(rehearsal.get("rehearsal_safe_block_max", 0) or 0),
    }
    return {
        "any_exceeded": any_exceeded,
        "hits_24h_total": hits_24h_total,
        "hits_7d_total": int(stats.get("hits_7d_total", 0) or 0),
        "noisy_routes_count": noisy_routes_count,
        "compat_risk_level": compat_risk_level,
        "dryoff_enabled": bool(dryoff.get("dryoff_enabled", False)),
        "dryoff_targets": list(dryoff.get("dryoff_targets", [])),
        "dryoff_default_targets": list(dryoff.get("dryoff_default_targets", [])),
        "dryoff_block_count_24h": int(dryoff.get("dryoff_block_count_24h", 0) or 0),
        "dryoff_guard": dryoff.get("dryoff_guard", {}),
        "session_enabled": session_summary["session_enabled"],
        "session_active": session_summary["session_active"],
        "session_start_at": session_summary["session_start_at"],
        "session_end_at": session_summary["session_end_at"],
        "session_remaining_seconds": session_summary["session_remaining_seconds"],
        "session_block_count": session_summary["session_block_count"],
        "session_last_block_at": session_summary["session_last_block_at"],
        "session": session_summary,
        "rollout_switches": _build_legacy_rollout_and_dryoff_payload(hass),
    }


def _view_admin_check(request: web.Request):
    """P1修复：HTTP 视图管理员校验。返回 403 Response 或 None（通过）。
    需要认证（requires_auth=True）的视图中使用，在实际业务逻辑前调用。"""
    user = request.get("hass_user")
    if user is not None and not user.is_admin:
        payload = _json_error_payload(
            error="forbidden_admin_required",
            error_type="auth_failed",
            retryable=False,
        )
        return web.json_response(payload, status=403)
    return None


def _extract_bearer_token(request: web.Request) -> str:
    auth_header = str(request.headers.get("Authorization", "") or "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return ""


def _is_addon_proxy_request(request: web.Request) -> bool:
    return str(request.headers.get("X-SA-Proxy-From", "") or "").strip().lower() == "addon"


def _is_addon_internal_execute_request(request: web.Request) -> bool:
    return (
        _is_addon_proxy_request(request)
        and str(request.headers.get("X-SA-Internal-Execute", "") or "").strip().lower()
        in {"1", "true", "yes", "on"}
    )


def _ha_log_window_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _ha_log_line_matches_level(line: str, level: str) -> bool:
    if level == "all":
        return True
    lowered = line.lower()
    if level == "error":
        return "error" in lowered or "exception" in lowered or "traceback" in lowered
    if level == "warning":
        return "warn" in lowered or "warning" in lowered
    if level == "info":
        return "info" in lowered
    return True


def _ha_log_content_window(content: str, query: Any) -> tuple[str, dict[str, Any]]:
    q = query if hasattr(query, "get") else {}
    level = str(q.get("level") or "all").strip().lower()
    if level not in {"all", "error", "warning", "info"}:
        level = "all"
    keyword = str(q.get("keyword") or "").strip()
    keyword_lower = keyword.lower()
    max_bytes = _ha_log_window_int(q.get("max_bytes"), default=128 * 1024, minimum=1, maximum=512 * 1024)
    tail_lines = _ha_log_window_int(q.get("tail_lines"), default=800, minimum=1, maximum=3000)

    lines = str(content or "").splitlines()
    filtered_lines = [
        line
        for line in lines
        if _ha_log_line_matches_level(line, level)
        and (not keyword_lower or keyword_lower in line.lower())
    ]
    tail_truncated = len(filtered_lines) > tail_lines
    window_lines = filtered_lines[-tail_lines:]
    window_content = "\n".join(window_lines)
    if str(content or "").endswith("\n") and window_content:
        window_content += "\n"
    encoded = window_content.encode("utf-8")
    byte_truncated = len(encoded) > max_bytes
    if byte_truncated:
        window_content = encoded[-max_bytes:].decode("utf-8", errors="ignore")

    active = (
        level != "all"
        or bool(keyword)
        or "max_bytes" in q
        or "tail_lines" in q
    )
    window = {
        "active": active,
        "level": level,
        "keyword": keyword,
        "max_bytes": max_bytes,
        "tail_lines": tail_lines,
        "filtered": level != "all" or bool(keyword),
        "total_lines": len(lines),
        "matched_lines": len(filtered_lines),
        "returned_lines": len(window_content.splitlines()),
        "original_byte_count": len(str(content or "").encode("utf-8")),
        "returned_byte_count": len(window_content.encode("utf-8")),
        "tail_truncated": tail_truncated,
        "byte_truncated": byte_truncated,
    }
    window["truncated"] = bool(tail_truncated or byte_truncated)
    return window_content, window


def _json_error_payload(error: str, error_type: str, retryable: bool, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": str(error or "unknown_error"),
        "error_type": str(error_type or "internal_error"),
        "retryable": bool(retryable),
    }
    payload.update({k: v for k, v in extra.items() if v is not None})
    return payload


def _normalize_addon_diagnostics(raw: Any) -> dict[str, Any]:
    """统一把 addon_diagnostics 归一化为 dict，避免出现 null 类型漂移。"""
    if isinstance(raw, dict):
        return raw
    return {}


def _default_wave_semantics_payload(mode: str = "unknown") -> dict[str, Any]:
    return {
        "schema": "wave4a_v1",
        "snapshot_observability": {
            "presence_fusion_summary": False,
            "topology_summary": False,
            "status_source": "system_diagnostics",
        },
        "capability_observability": {
            "addon_capabilities": False,
            "bridge_mode": "local_first_with_fallback",
            "ha_adapter_bridge": True,
        },
        "context_layer_observability": {
            "contracts_summary": False,
            "compat_summary": True,
            "ha_adapter_bridge": True,
            "core_mode": str(mode or "unknown"),
        },
    }


def _status_error_type(status: int, fallback: str = "upstream_rejected") -> str:
    mapping = {
        400: "bad_request",
        401: "auth_failed",
        403: "auth_failed",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "unprocessable_entity",
        429: "rate_limited",
        500: "internal_error",
        502: "dependency_unreachable",
        503: "service_unavailable",
        504: "timeout",
    }
    return mapping.get(int(status), fallback)


def _is_retryable_status(status: int) -> bool:
    return int(status) in (429, 500, 502, 503, 504)


def _json_from_addon_result(proxied: dict[str, Any]) -> tuple[dict[str, Any], int]:
    body = dict(proxied or {})
    status = int(body.pop("__status", 200) or 200)
    if status >= 400:
        body["ok"] = False
        body.setdefault("error", "upstream_request_failed")
        body.setdefault("error_type", _status_error_type(status))
        body.setdefault("retryable", _is_retryable_status(status))
    else:
        body.setdefault("ok", True)
    return body, status


def _json_from_addon_http_result(result: dict[str, Any] | None) -> tuple[dict[str, Any], int] | None:
    """把 add-on request_json 结果转换为统一状态码感知透传结构。"""
    if not isinstance(result, dict):
        return None
    status = int(result.get("status_code", 0) or 0)
    if status <= 0:
        return None
    raw_body = result.get("body")
    if isinstance(raw_body, dict):
        proxied: dict[str, Any] = dict(raw_body)
    elif isinstance(raw_body, list):
        proxied = {"ok": 200 <= status < 300, "data": raw_body}
    else:
        proxied = {"ok": 200 <= status < 300}
    proxied["__status"] = status
    return _json_from_addon_result(proxied)


def _addon_result_payload_status(result: dict[str, Any] | None) -> tuple[dict[str, Any], int] | None:
    """统一识别 add-on 返回中的状态码结构。"""
    normalized = _json_from_addon_http_result(result)
    if normalized is not None:
        return normalized
    if isinstance(result, dict) and "__status" in result:
        return _json_from_addon_result(result)
    return None


def _addon_result_list_body(result: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    """抽取 add-on 列表结果，兼容 data 容器。"""
    if not isinstance(result, dict):
        return None
    raw_body = result.get("body")
    if isinstance(raw_body, list):
        return [x for x in raw_body if isinstance(x, dict)]
    if isinstance(raw_body, dict) and isinstance(raw_body.get("data"), list):
        return [x for x in raw_body.get("data", []) if isinstance(x, dict)]
    return None


def _addon_unreachable_payload(scope: str) -> dict[str, Any]:
    return _json_error_payload(
        error="addon_unreachable",
        error_type="dependency_unreachable",
        retryable=True,
        scope=scope,
    )


def _addon_endpoint_missing_payload(scope: str) -> dict[str, Any]:
    return _json_error_payload(
        error="addon_endpoint_missing",
        error_type="not_found",
        retryable=False,
        scope=scope,
    )


def _legacy_memory_rows_snapshot(
    rows: Any,
    *,
    source: str,
    defaults: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return result
    defaults = defaults if isinstance(defaults, dict) else {}
    for index, item in enumerate(rows):
        if isinstance(item, dict):
            row = dict(item)
            row.setdefault("id", index)
            row.setdefault("content", str(row.get("content") or row.get("text") or ""))
            row.setdefault("locked", bool(row.get("locked", False)))
        elif isinstance(item, (list, tuple)) and item:
            row = {
                "id": index,
                "content": str(item[0] or ""),
                "locked": bool(item[1]) if len(item) > 1 else False,
            }
        else:
            row = {"id": index, "content": str(item or ""), "locked": False}
        if str(row.get("content") or "").strip():
            for key, value in defaults.items():
                row.setdefault(key, value)
            row["source"] = source
            result.append(row)
    return result


def _legacy_memory_profiles_snapshot(coord: Any) -> list[dict[str, Any]]:
    return _legacy_memory_rows_snapshot(
        getattr(coord, "_rules", []),
        source="ha_legacy_rules_export",
        defaults={"weight": 0},
    )


def _legacy_memory_habits_snapshot(coord: Any) -> list[dict[str, Any]]:
    return _legacy_memory_rows_snapshot(
        getattr(coord, "_habits", []),
        source="ha_legacy_habits_export",
        defaults={"score": 0},
    )


def _legacy_corrections_snapshot(coord: Any) -> list[dict[str, Any]]:
    db = getattr(coord, "_db", None)
    query = getattr(db, "query", None)
    if not callable(query):
        return []
    try:
        raw_rows = query("SELECT * FROM corrections ORDER BY time DESC LIMIT 200")
    except Exception as exc:
        _LOGGER.debug("[Corrections] legacy snapshot read failed: %s", exc)
        return []
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(raw_rows or [], start=1):
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row.setdefault("id", index)
        row.setdefault("scene", row.get("scene_desc") or "")
        row.setdefault("action", row.get("ai_service") or row.get("service") or "")
        row.setdefault("created_at", row.get("time") or row.get("timestamp") or "")
        row.setdefault("source", "ha_legacy_corrections_export")
        row.setdefault("lifecycle_state", "active")
        row.setdefault("content", str(row.get("action") or row.get("entity_id") or ""))
        rows.append(row)
    return rows


def _ha_local_log_error_payload(
    scope: str,
    error: str,
    error_type: str = "dependency_error",
    exc: Exception | None = None,
) -> dict[str, Any]:
    return _json_error_payload(
        error=error,
        error_type=error_type,
        retryable=True,
        scope=scope,
        source="ha_host_local_logs",
        exception_type=exc.__class__.__name__ if exc is not None else None,
    )


def _patrol_trigger_plan_only_payload(reason: str = "controlled_provider_pending") -> dict[str, Any]:
    return {
        "ok": False,
        "error": "operation_plan_only",
        "error_type": "plan_only",
        "retryable": False,
        "source": "ha_host_patrol_plan_only_fallback",
        "contract_version": "1.1",
        "domain": "patrol",
        "action": "trigger",
        "dry_run": True,
        "executed": False,
        "provider_status": "pending_deepening",
        "plan": {
            "domain": "patrol",
            "action": "trigger",
            "status": "plan_only",
            "execution": "blocked",
            "reason": reason,
            "rollback": {
                "supported": False,
                "strategy": "not_supported_for_diagnostic_trigger",
            },
        },
        "warnings": [
            "patrol trigger remains plan-only until a controlled execution provider exists"
        ],
    }


def _default_capability_dry_run_payload() -> dict[str, Any]:
    """capability dry-run 最小安全骨架：默认仅给建议，不执行真实动作。"""
    return {
        "ok": True,
        "capability": "unknown",
        "dry_run": True,
        "suggested_actions": [],
        "risk_level": "high",
        "reject_reasons": ["dry_run_only"],
    }


def _addon_list_read_strict_response(
    rows: Any,
    *,
    scope: str,
) -> tuple[dict[str, Any] | list[dict[str, Any]], int]:
    proxied = _addon_result_payload_status(rows if isinstance(rows, dict) else None)
    if proxied is not None:
        payload, status = proxied
        if status in (404, 405):
            return _addon_endpoint_missing_payload(scope), status
        return payload, status

    if isinstance(rows, list):
        return rows, 200
    if isinstance(rows, dict):
        items = _addon_result_list_body(rows)
        if items is not None:
            return items, 200

    return _addon_unreachable_payload(scope), 502


async def _addon_probe_list_result(
    addon_client: Any,
    method: str,
    paths: tuple[str, ...],
    body: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]] | None, tuple[dict[str, Any], int] | None]:
    """通过 request_json 探测列表端点，透传非 404/405 错误。"""
    request_json = getattr(addon_client, "request_json", None)
    if not callable(request_json):
        return None, None

    req_method = str(method or "GET").upper()
    for path in paths:
        result = await request_json(req_method, path, body=body)
        if not isinstance(result, dict):
            return None, None

        converted = _addon_result_payload_status(result)
        if converted is None:
            continue
        payload, status = converted

        if status in (404, 405):
            return None, (_addon_endpoint_missing_payload(paths[0].lstrip("/").replace("/", "_")), status)
        if status >= 400:
            return None, (payload, status)

        rows = _addon_result_list_body(result)
        if rows is not None:
            return rows, None
        return None, None

    return None, None


async def _save_rooms_topology_via_addon(
    addon_client: Any,
    body: dict[str, Any],
) -> tuple[dict[str, Any], int] | None:
    payload = body if isinstance(body, dict) else {}
    save_rooms_topology = getattr(addon_client, "save_rooms_topology", None)
    if callable(save_rooms_topology):
        result = await save_rooms_topology(payload)
        if isinstance(result, dict):
            normalized = _json_from_addon_http_result(result)
            if normalized is not None:
                return normalized
            return _json_from_addon_result(result)
        return None

    request_json = getattr(addon_client, "request_json", None)
    if callable(request_json):
        result = await request_json("POST", "/rooms/topology", body=payload)
        if isinstance(result, dict):
            normalized = _json_from_addon_http_result(result)
            if normalized is not None:
                return normalized
            return _json_from_addon_result(result)
    return None


async def _refresh_coord_room_topology_cache(coord: Any) -> None:
    refresh_async = getattr(coord, "_async_refresh_room_topology_cache", None)
    if callable(refresh_async):
        result = refresh_async()
        if hasattr(result, "__await__"):
            await result
        return

    refresh_sync = getattr(coord, "_refresh_room_topology_cache", None)
    if callable(refresh_sync):
        result = refresh_sync()
        if hasattr(result, "__await__"):
            await result


async def _resolve_user_from_token(hass: HomeAssistant, token: str):
    token = str(token or "").strip()
    if not token:
        return None
    try:
        refresh_token = await hass.auth.async_validate_access_token(token)
    except Exception:
        return None
    if refresh_token is None:
        return None

    uid = getattr(getattr(refresh_token, "user", None), "id", None) or getattr(refresh_token, "user_id", None)
    if not uid:
        return None

    try:
        return await hass.auth.async_get_user(uid)
    except Exception:
        return None


async def _resolve_request_user(request: web.Request):
    """解析请求用户：优先 HA 会话，其次会话 token，再回退 HA token。"""
    user = request.get("hass_user")
    if user is not None:
        return user

    token = _extract_bearer_token(request)
    if not token:
        token = str(request.query.get("token", "") or "").strip()
    if not token:
        return None

    hass = request.app["hass"]
    session_user = await _resolve_user_by_auth_session(hass, token)
    if session_user is not None:
        return session_user
    return await _resolve_user_from_token(hass, token)


class SmartAgentLogDatesView(HomeAssistantView):
    """API endpoint to list available log dates."""

    url = "/api/v1/logs/dates"
    name = "api:smart_agent:log_dates"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]

        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("logs_dates"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            get_dates = getattr(coord, "get_log_dates", None)
            if not callable(get_dates):
                return self.json(
                    _ha_local_log_error_payload(
                        "logs_dates",
                        "ha_local_logs_dates_reader_missing",
                        "dependency_unreachable",
                    ),
                    status_code=502,
                )
            try:
                dates = await hass.async_add_executor_job(get_dates)
            except Exception as exc:
                _LOGGER.warning("[LogDates] local add-on proxy read failed: %s", exc)
                return self.json(
                    _ha_local_log_error_payload(
                        "logs_dates",
                        "ha_local_logs_dates_read_failed",
                        exc=exc,
                    ),
                    status_code=502,
                )
            if isinstance(dates, list):
                return self.json(dates)
            return self.json(
                _ha_local_log_error_payload(
                    "logs_dates",
                    "ha_local_logs_dates_invalid_payload",
                    "invalid_payload",
                ),
                status_code=502,
            )
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("logs_dates"), status_code=502)

        try:
            dates = await _addon_client.get_log_dates()
            if isinstance(dates, list):
                return self.json(dates)
            proxied = _addon_result_payload_status(dates if isinstance(dates, dict) else None)
            if proxied is not None:
                payload, status = proxied
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("logs_dates"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("logs_dates"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[LogDates] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("logs_dates"), status_code=502)


class SmartAgentLogContentView(HomeAssistantView):
    """API endpoint to read log content by date."""

    url = "/api/v1/logs/content"
    name = "api:smart_agent:log_content"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        date = request.query.get("date", "")
        if not date:
            return self.json(
                _json_error_payload(
                    error="date_parameter_required",
                    error_type="bad_request",
                    retryable=False,
                ),
                status_code=400,
            )
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            return self.json(
                _json_error_payload(
                    error="invalid_date_format_expected_yyyy_mm_dd",
                    error_type="bad_request",
                    retryable=False,
                ),
                status_code=400,
            )

        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("logs_content"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            read_file = getattr(coord, "read_log_file", None)
            if not callable(read_file):
                return self.json(
                    _ha_local_log_error_payload(
                        "logs_content",
                        "ha_local_logs_content_reader_missing",
                        "dependency_unreachable",
                    ),
                    status_code=502,
                )
            try:
                content = await hass.async_add_executor_job(read_file, str(date))
                windowed_content, window = _ha_log_content_window(str(content or ""), request.query)
                payload = {"date": str(date), "content": windowed_content}
                if bool(window.get("active")):
                    payload["window"] = {k: v for k, v in window.items() if k != "active"}
                return self.json(payload)
            except Exception as exc:
                _LOGGER.warning("[LogContent] local add-on proxy read failed: %s", exc)
                return self.json(
                    _ha_local_log_error_payload(
                        "logs_content",
                        "ha_local_logs_content_read_failed",
                        exc=exc,
                    ),
                    status_code=502,
                )
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("logs_content"), status_code=502)

        try:
            content = await _addon_client.get_log_content(
                str(date),
                level=request.query.get("level"),
                keyword=request.query.get("keyword"),
                max_bytes=request.query.get("max_bytes"),
                tail_lines=request.query.get("tail_lines"),
                raw=str(request.query.get("raw") or "").strip().lower() in {"1", "true", "yes", "on"},
            )
            if isinstance(content, dict):
                payload, status = _json_from_addon_result(content)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("logs_content"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("logs_content"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[LogContent] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("logs_content"), status_code=502)


class SmartAgentLogInfoView(HomeAssistantView):
    """API endpoint to get log file metadata (size, line counts, error counts)."""

    url = "/api/v1/logs/info"
    name = "api:smart_agent:log_info"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]

        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("logs_info"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            get_info = getattr(coord, "get_log_info", None)
            if not callable(get_info):
                return self.json(
                    _ha_local_log_error_payload(
                        "logs_info",
                        "ha_local_logs_info_reader_missing",
                        "dependency_unreachable",
                    ),
                    status_code=502,
                )
            try:
                info = await hass.async_add_executor_job(get_info)
            except Exception as exc:
                _LOGGER.warning("[LogInfo] local add-on proxy read failed: %s", exc)
                return self.json(
                    _ha_local_log_error_payload(
                        "logs_info",
                        "ha_local_logs_info_read_failed",
                        exc=exc,
                    ),
                    status_code=502,
                )
            if isinstance(info, (list, dict)):
                return self.json(info)
            return self.json(
                _ha_local_log_error_payload(
                    "logs_info",
                    "ha_local_logs_info_invalid_payload",
                    "invalid_payload",
                ),
                status_code=502,
            )
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("logs_info"), status_code=502)

        try:
            info = await _addon_client.get_log_info()
            if isinstance(info, dict):
                payload, status = _json_from_addon_result(info)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("logs_info"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("logs_info"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[LogInfo] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("logs_info"), status_code=502)


class SmartAgentSceneExportView(HomeAssistantView):
    """AI 场景 YAML 导出接口。

    GET  /api/v1/scenes/export-yaml?scene_id=N
         返回该场景的 YAML 字符串，供前端展示。

    POST /api/v1/scenes/export-yaml
         Body: {"scene_id": N}
         只代理到 add-on 场景导出 provider，HA host 不再写本地配置文件。
    """

    url = "/api/v1/scenes/export-yaml"
    name = "api:smart_agent:export_scene_yaml"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """GET: 返回场景 YAML 字符串。"""
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        scene_id_str = request.query.get("scene_id", "")
        if not scene_id_str:
            return self.json(
                _json_error_payload(
                    error="scene_id_required",
                    error_type="bad_request",
                    retryable=False,
                ),
                status_code=400,
            )
        try:
            scene_id = int(scene_id_str)
        except ValueError:
            return self.json(
                _json_error_payload(
                    error="invalid_scene_id",
                    error_type="bad_request",
                    retryable=False,
                ),
                status_code=400,
            )

        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload(
                    error="coordinator_not_found",
                    error_type="not_found",
                    retryable=False,
                ),
                status_code=404,
            )

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("scene_yaml_export"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("scene_yaml_export"), status_code=502)

        try:
            exported = await _addon_client.get_scene_yaml_export(scene_id)
            if isinstance(exported, dict):
                payload, status = _json_from_addon_result(exported)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("scene_yaml_export"), status_code=status)
                return self.json(payload, status_code=status)
            else:
                return self.json(_addon_unreachable_payload("scene_yaml_export"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[SceneExportGet] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("scene_yaml_export"), status_code=502)

    async def post(self, request: web.Request) -> web.Response:
        """POST: 将场景导出写操作代理给 add-on。"""
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        try:
            body = await request.json()
        except Exception:
            return self.json(
                _json_error_payload(
                    error="invalid_json_body",
                    error_type="bad_request",
                    retryable=False,
                ),
                status_code=400,
            )

        scene_id_str = body.get("scene_id")
        if not scene_id_str:
            return self.json(
                _json_error_payload(
                    error="scene_id_required",
                    error_type="bad_request",
                    retryable=False,
                ),
                status_code=400,
            )
        try:
            scene_id = int(scene_id_str)
        except (TypeError, ValueError):
            return self.json(
                _json_error_payload(
                    error="invalid_scene_id",
                    error_type="bad_request",
                    retryable=False,
                ),
                status_code=400,
            )

        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload(
                    error="coordinator_not_found",
                    error_type="not_found",
                    retryable=False,
                ),
                status_code=404,
            )

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("scene_yaml_export"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("scene_yaml_export"), status_code=502)

        try:
            proxied = await _addon_client.post_scene_yaml_export(body if isinstance(body, dict) else {})
            if isinstance(proxied, dict):
                payload, status = _json_from_addon_result(proxied)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("scene_yaml_export"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("scene_yaml_export"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[SceneExportPost] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("scene_yaml_export"), status_code=502)

_LOGGER = logging.getLogger(__name__)


def _get_first_coordinator(hass: HomeAssistant) -> SmartAgentCoordinator | None:
    """获取当前集成实例（单实例部署取第一个）。"""
    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, SmartAgentCoordinator):
            return value
    return None


class SmartAgentDevicesView(HomeAssistantView):
    """设备列表与批量新增接口（/api/v1/devices*）。"""

    url = "/api/v1/devices"
    name = "api:smart_agent:v1:devices"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("devices"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_local_device_rows(coord, hass))

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("devices"), status_code=502)

        try:
            rows, proxied_error = await _addon_probe_list_result(_addon_client, "GET", ("/devices",))
            if proxied_error is not None:
                payload, status = proxied_error
                return self.json(payload, status_code=status)
            if rows is not None:
                return self.json(rows)

            devices = await _addon_client.get_devices()
            rows = _addon_result_list_body(devices if isinstance(devices, dict) else None)
            if rows is not None:
                return self.json(rows)
            strict = _addon_list_read_strict_response(devices, scope="devices")
            payload, status = strict
            if status >= 400:
                return self.json(payload, status_code=status)
            if isinstance(payload, list):
                return self.json(payload)
            return self.json(_addon_unreachable_payload("devices"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[Devices] add-on devices proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("devices"), status_code=502)


class SmartAgentDevicesDiscoverView(HomeAssistantView):
    """设备发现接口。"""

    url = "/api/v1/devices/discover"
    name = "api:smart_agent:v1:devices:discover"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("devices_discover"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            try:
                rows = await coord._async_discover_devices()
                return self.json([row for row in (rows or []) if isinstance(row, dict)])
            except Exception as exc:
                _LOGGER.debug("[DevicesDiscover] local HA discovery failed: %s", exc)
                return self.json(_addon_unreachable_payload("devices_discover"), status_code=502)

        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                probe = await _addon_client.request_json("POST", "/devices/discover", body={})
                if isinstance(probe, dict):
                    raw_body = probe.get("body")
                    if isinstance(raw_body, list):
                        return self.json([x for x in raw_body if isinstance(x, dict)])
                    normalized = _json_from_addon_http_result(probe)
                    if normalized is not None:
                        payload, status = normalized
                        if status in (404, 405):
                            return self.json(_addon_endpoint_missing_payload("devices_discover"), status_code=status)
                        return self.json(payload, status_code=status)
                    else:
                        return self.json(_addon_unreachable_payload("devices_discover"), status_code=502)
                else:
                    return self.json(_addon_unreachable_payload("devices_discover"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[DevicesDiscover] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("devices_discover"), status_code=502)

        return self.json(_addon_unreachable_payload("devices_discover"), status_code=502)


class SmartAgentDevicesBatchAddView(HomeAssistantView):
    """批量纳管设备接口。"""

    url = "/api/v1/devices/batch-add"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:devices:batch_add"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("devices_batch_add"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid JSON"}, status_code=400)

        raw_entities = body.get("entities", [])
        if isinstance(raw_entities, str):
            entities = [e.strip() for e in raw_entities.split(",") if e.strip()]
        elif isinstance(raw_entities, list):
            entities = [str(e).strip() for e in raw_entities if str(e).strip()]
        else:
            entities = []

        if not entities:
            return self.json({"ok": False, "error": "entities required"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            try:
                added = await coord.async_batch_add_devices(entities)
                return self.json({"ok": True, "added": int(added or 0), "count": int(added or 0)})
            except Exception as exc:
                _LOGGER.debug("[DevicesBatchAdd] local HA batch add failed: %s", exc)
                return self.json(_addon_unreachable_payload("devices_batch_add"), status_code=502)

        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("POST", "/devices/batch-add", body={"entities": entities})
                if isinstance(proxied, dict):
                    normalized = _json_from_addon_http_result(proxied)
                    if normalized is not None:
                        payload, status = normalized
                        if status in (404, 405):
                            return self.json(_addon_endpoint_missing_payload("devices_batch_add"), status_code=status)
                        return self.json(payload, status_code=status)
                    else:
                        return self.json(_addon_unreachable_payload("devices_batch_add"), status_code=502)
                else:
                    return self.json(_addon_unreachable_payload("devices_batch_add"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[DevicesBatchAdd] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("devices_batch_add"), status_code=502)

        return self.json(_addon_unreachable_payload("devices_batch_add"), status_code=502)


class SmartAgentDeviceDetailView(HomeAssistantView):
    """单设备修改/删除接口。"""

    url = "/api/v1/devices/{entity_id}"
    name = "api:smart_agent:v1:devices:detail"
    requires_auth = True

    async def patch(self, request: web.Request, entity_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("device_patch"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid JSON"}, status_code=400)

        eid = entity_id.strip()
        if not eid:
            return self.json({"ok": False, "error": "entity_id required"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            patch_body = body if isinstance(body, dict) else {}
            room = str(patch_body.get("room") or patch_body.get("area") or "").strip()
            if not room:
                sync_payload = {
                    "ok": True,
                    "entity_id": eid,
                    "skipped": True,
                    "reason": "room_not_provided",
                    "source": "ha_area_registry_mirror",
                }
                return self.json(
                    {
                        "ok": True,
                        "entity_id": eid,
                        "source": "ha_area_registry_mirror",
                        "ha_area_sync": sync_payload,
                    }
                )
            sync_device_room = getattr(coord, "async_sync_device_room_to_ha", None)
            if sync_device_room is None:
                return self.json(_addon_endpoint_missing_payload("device_patch"), status_code=404)
            try:
                result = await sync_device_room(eid, room)
                sync_payload = result if isinstance(result, dict) else {"ok": True, "result": result}
                sync_payload.setdefault("ok", True)
                sync_payload.setdefault("entity_id", eid)
                sync_payload.setdefault("room", room)
                sync_payload.setdefault("source", "ha_area_registry_mirror")
                sync_ok = bool(sync_payload.get("ok"))
                return self.json(
                    {
                        "ok": sync_ok,
                        "entity_id": eid,
                        "room": room,
                        "area": room,
                        "source": "ha_area_registry_mirror",
                        "ha_area_sync": sync_payload,
                    },
                    status_code=200 if sync_ok else 502,
                )
            except Exception as exc:
                _LOGGER.debug("[DevicePatch] local HA area mirror failed: %s", exc)
                return self.json(_addon_unreachable_payload("device_patch"), status_code=502)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("device_patch"), status_code=502)

        try:
            proxied = await _addon_client.request_json("PATCH", f"/devices/{eid}", body=body if isinstance(body, dict) else {})
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                return self.json(_addon_unreachable_payload("device_patch"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("device_patch"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[DevicePatch] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("device_patch"), status_code=502)

    async def delete(self, request: web.Request, entity_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("device_delete"), status_code=502)

        eid = entity_id.strip()
        if not eid:
            return self.json({"ok": False, "error": "entity_id required"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("device_delete"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("device_delete"), status_code=502)

        try:
            proxied = await _addon_client.request_json("DELETE", f"/devices/{eid}")
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                return self.json(_addon_unreachable_payload("device_delete"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("device_delete"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[DeviceDelete] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("device_delete"), status_code=502)


class SmartAgentDeviceControlView(HomeAssistantView):
    """单设备快捷控制接口。"""

    url = "/api/v1/devices/{entity_id}/control"
    name = "api:smart_agent:v1:devices:control"
    requires_auth = True

    async def post(self, request: web.Request, entity_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("device_control"), status_code=502)

        eid = entity_id.strip()
        if not eid:
            return self.json({"ok": False, "error": "entity_id required"}, status_code=400)

        try:
            body = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid JSON"}, status_code=400)

        service = str((body or {}).get("service", "") or "").strip().lower()
        params = (body or {}).get("params")
        params = params if isinstance(params, dict) else {}

        allowed_services = {"turn_on", "turn_off", "toggle", "open_cover", "close_cover"}
        if service not in allowed_services:
            return self.json({"ok": False, "error": f"unsupported service: {service}"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("device_control"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("device_control"), status_code=502)

        try:
            proxied = await _addon_client.request_json(
                "POST",
                f"/devices/{eid}/control",
                body={"service": service, "params": params},
            )
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("device_control"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("device_control"), status_code=502)
            return self.json(_addon_unreachable_payload("device_control"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[DeviceControl] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("device_control"), status_code=502)


class SmartAgentPresenceSensorsView(HomeAssistantView):
    """存在传感器类型与融合域编辑器数据接口。"""

    url = "/api/v1/presence/sensors"
    name = "api:smart_agent:v1:presence:sensors"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("presence_sensors"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_build_presence_sensors_payload(hass, coord))

        addon_client = getattr(coord, "_addon_client", None)
        if addon_client is None:
            return self.json(_addon_unreachable_payload("presence_sensors"), status_code=502)

        try:
            proxied = await addon_client.request_json("GET", "/presence/sensors")
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("presence_sensors"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("presence_sensors"), status_code=502)
            return self.json(_addon_unreachable_payload("presence_sensors"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[PresenceSensors] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("presence_sensors"), status_code=502)


class SmartAgentPresenceSensorTypeView(HomeAssistantView):
    """保存存在传感器类型分类。"""

    url = "/api/v1/presence/sensors/type"
    name = "api:smart_agent:v1:presence:sensors:type"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("JSON body must be object")
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False),
                status_code=400,
            )

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            result = await _async_save_presence_sensor_type(
                hass,
                coord,
                str(body.get("entity_id") or ""),
                str(body.get("sensor_type") or ""),
            )
            status = int(result.get("status", 200) or 200)
            return self.json(result, status_code=status)

        addon_client = getattr(coord, "_addon_client", None)
        if addon_client is None:
            return self.json(_addon_unreachable_payload("presence_sensor_type"), status_code=502)

        try:
            proxied = await addon_client.request_json("POST", "/presence/sensors/type", body=body)
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("presence_sensor_type"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("presence_sensor_type"), status_code=502)
            return self.json(_addon_unreachable_payload("presence_sensor_type"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[PresenceSensorType] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("presence_sensor_type"), status_code=502)


class SmartAgentRoomsView(HomeAssistantView):
    """房间统计接口。"""

    url = "/api/v1/rooms"
    name = "api:smart_agent:v1:rooms"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("rooms"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_local_room_rows(coord, hass))

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("rooms"), status_code=502)

        try:
            rows, proxied_error = await _addon_probe_list_result(_addon_client, "GET", ("/rooms",))
            if proxied_error is not None:
                payload, status = proxied_error
                return self.json(payload, status_code=status)
            if rows is not None:
                return self.json(rows)

            rooms = await _addon_client.get_rooms()
            rows = _addon_result_list_body(rooms if isinstance(rooms, dict) else None)
            if rows is not None:
                return self.json(rows)
            strict = _addon_list_read_strict_response(rooms, scope="rooms")
            payload, status = strict
            if status >= 400:
                return self.json(payload, status_code=status)
            if isinstance(payload, list):
                return self.json(payload)
            return self.json(_addon_unreachable_payload("rooms"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[Rooms] add-on rooms proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("rooms"), status_code=502)


class SmartAgentRoomsSyncView(HomeAssistantView):
    """将 SmartAgent 房间同步到 HA Area。"""

    url = "/api/v1/rooms/sync"
    name = "api:smart_agent:v1:rooms:sync"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("rooms_sync"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            try:
                result = await coord.async_sync_rooms_to_ha()
                payload = {"ok": True}
                if isinstance(result, dict):
                    payload.update(result)
                return self.json(payload)
            except Exception as exc:
                _LOGGER.debug("[RoomsSync] local HA rooms sync failed: %s", exc)
                return self.json(_addon_unreachable_payload("rooms_sync"), status_code=502)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("rooms_sync"), status_code=502)

        try:
            proxied = await _addon_client.request_json("POST", "/rooms/sync", body={})
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("rooms_sync"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("rooms_sync"), status_code=502)
            return self.json(_addon_unreachable_payload("rooms_sync"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[RoomsSync] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("rooms_sync"), status_code=502)


class SmartAgentRoomsTopologyView(HomeAssistantView):
    """房间拓扑查询接口。"""

    url = "/api/v1/rooms/topology"
    name = "api:smart_agent:v1:rooms:topology"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("rooms_topology"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("rooms_topology"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("rooms_topology"), status_code=502)

        try:
            rows, proxied_error = await _addon_probe_list_result(
                _addon_client,
                "GET",
                ("/rooms/topology",),
            )
            if proxied_error is not None:
                payload, status = proxied_error
                return self.json(payload, status_code=status)
            if rows is not None:
                return self.json(rows)
            topo = await _addon_client.get_rooms_topology()
            payload, status = _addon_list_read_strict_response(topo, scope="rooms_topology")
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[RoomsTopology] add-on topology list proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("rooms_topology"), status_code=502)

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json({"ok": False, "error": "coordinator not found"}, status_code=404)

        try:
            body = await request.json()
        except Exception:
            body = {}

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("rooms_topology"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("rooms_topology"), status_code=502)

        try:
            normalized = await _save_rooms_topology_via_addon(
                _addon_client,
                body if isinstance(body, dict) else {},
            )
            if normalized is not None:
                payload, status = normalized
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("rooms_topology"), status_code=status)
                if status < 400:
                    await _refresh_coord_room_topology_cache(coord)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("rooms_topology"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[RoomsTopology] add-on topology save proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("rooms_topology"), status_code=502)

class SmartAgentAiScenesView(HomeAssistantView):
    """AI 场景列表接口（canonical + 迁移兼容入口）。"""

    url = "/api/v1/ai-scenes"
    extra_urls = AI_SCENE_LIST_MIGRATION_COMPAT_URLS
    name = "api:smart_agent:v1:ai_scenes"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        _record_legacy_route_hit_if_needed(hass, request)
        coord = _get_first_coordinator(hass)
        if coord is None or isinstance(coord, bool):
            return self.json(_addon_unreachable_payload("ai_scenes"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            rows = get_ai_scenes_cache_snapshot(coord)
            status = str(request.query.get("status", "") or "").strip().lower()
            if status:
                rows = [row for row in rows if str(row.get("status") or "").strip().lower() == status]
            return self.json(rows)

        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                rows, proxied_error = await _addon_probe_list_result(
                    _addon_client,
                    "GET",
                    ("/ai-scenes",),
                )
                if proxied_error is not None:
                    payload, status = proxied_error
                    return self.json(payload, status_code=status)
                if rows is not None:
                    return self.json(rows)

                # probe 未返回 rows 且无结构化透传错误时，统一视为 add-on 不可达；
                # 不再调用 legacy get_ai_scenes() 二次兜底，保持单入口代理语义。
                return self.json(_addon_unreachable_payload("ai_scenes"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[AiScenes] add-on scenes proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("ai_scenes"), status_code=502)

        return self.json(_addon_unreachable_payload("ai_scenes"), status_code=502)


class SmartAgentAiSceneActionView(HomeAssistantView):
    """AI 场景审批/拒绝接口（canonical）。"""

    url = "/api/v1/ai-scenes/approve"
    extra_urls = [
        "/api/v1/ai-scenes/reject",
    ]
    name = "api:smart_agent:v1:ai_scenes:action"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        _record_legacy_route_hit_if_needed(hass, request)
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("ai_scene_action"), status_code=502)

        path = request.path.lower()
        act = "reject" if "reject" in path else "approve"

        try:
            body = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid JSON"}, status_code=400)

        sid_raw = body.get("id")
        try:
            sid = int(sid_raw)
        except (TypeError, ValueError):
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)
        if sid <= 0:
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("ai_scene_action"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("ai_scene_action"), status_code=502)

        try:
            result = await _addon_client.post_ai_scene_action(act, sid)
            if isinstance(result, dict):
                payload, status = _json_from_addon_result(result)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("ai_scene_action"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("ai_scene_action"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[AiSceneAction] add-on action proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("ai_scene_action"), status_code=502)



class SmartAgentAiSceneTriggerView(HomeAssistantView):
    """AI 场景触发接口（canonical）。"""

    url = "/api/v1/ai-scenes/{scene_id}/trigger"
    name = "api:smart_agent:v1:ai_scenes:trigger"
    requires_auth = True

    async def post(self, request: web.Request, scene_id: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        _record_legacy_route_hit_if_needed(hass, request)
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("ai_scene_trigger"), status_code=502)

        sid_raw = scene_id
        if not sid_raw:
            try:
                body = await request.json()
            except Exception:
                body = {}
            sid_raw = body.get("id")

        try:
            sid = int(sid_raw)
        except (TypeError, ValueError):
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)
        if sid <= 0:
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("ai_scene_trigger"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("ai_scene_trigger"), status_code=502)

        try:
            result = await _addon_client.trigger_ai_scene(sid)
            if isinstance(result, dict):
                payload, status = _json_from_addon_result(result)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("ai_scene_trigger"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("ai_scene_trigger"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[AiSceneTrigger] add-on trigger proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("ai_scene_trigger"), status_code=502)



class SmartAgentSystemStatusView(HomeAssistantView):
    """系统状态接口。"""

    url = "/api/v1/system/status"
    name = "api:smart_agent:v1:system:status"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        user = request.get("hass_user")
        if user is None:
            user = await _resolve_request_user(request)
        if user is None:
            return self.json(
                _json_error_payload("unauthorized", "auth_failed", False),
                status_code=401,
            )
        if not bool(getattr(user, "is_admin", False)):
            return self.json(
                _json_error_payload("forbidden", "auth_failed", False),
                status_code=403,
            )
        hass = request.app["hass"]

        resource_metrics_cache = None

        async def _resource_metrics():
            nonlocal resource_metrics_cache
            if resource_metrics_cache is None:
                metrics_fn = globals().get("_collect_system_resource_metrics")
                if callable(metrics_fn):
                    executor = getattr(hass, "async_add_executor_job", None)
                    resource_metrics_cache = await executor(metrics_fn) if callable(executor) else metrics_fn()
                else:
                    resource_metrics_cache = {
                        "cpu": 0.0,
                        "memory": 0.0,
                        "resource_metrics": {},
                    }
            return resource_metrics_cache

        def _has_real_metric(value: Any) -> bool:
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return False
            return 0 < numeric <= 100

        coord = _get_first_coordinator(hass)
        is_addon_proxy = _is_addon_proxy_request(request)

        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if not is_addon_proxy:
            if _addon_client is None:
                return self.json(_addon_unreachable_payload("system_status"), status_code=502)
            try:
                proxied = await _addon_client.request_json("GET", "/system/status")
                converted = _json_from_addon_http_result(proxied)
                if converted is None:
                    return self.json(_addon_unreachable_payload("system_status"), status_code=502)
                payload, status = converted
                if isinstance(payload, dict):
                    payload["addon_diagnostics"] = _normalize_addon_diagnostics(payload.get("addon_diagnostics"))
                if status < 400:
                    if isinstance(payload, dict):
                        payload.setdefault("wave_semantics", _default_wave_semantics_payload(payload.get("mode", "unknown")))
                    payload.setdefault("ha", "online")
                    payload.setdefault("gateway", "online")
                    payload.setdefault("core", "online")
                    resource_metrics = await _resource_metrics()
                    if not _has_real_metric(payload.get("cpu")):
                        payload["cpu"] = resource_metrics.get("cpu", 0.0)
                    if not _has_real_metric(payload.get("memory")):
                        payload["memory"] = resource_metrics.get("memory", 0.0)
                    payload.setdefault("resource_metrics", resource_metrics.get("resource_metrics", {}))
                    payload.setdefault("compat_summary", _build_compat_summary_payload(hass))
                return self.json(payload, status_code=status)
            except Exception as exc:
                _LOGGER.debug("[SystemStatus] add-on status proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("system_status"), status_code=502)

        return self.json(_addon_endpoint_missing_payload("system_status"), status_code=404)


class SmartAgentCompatStatsView(HomeAssistantView):
    """legacy 兼容路由命中统计接口。"""

    url = "/api/v1/system/compat-stats"
    name = "api:smart_agent:v1:system:compat_stats"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("GET", "/system/compat-stats")
                converted = _json_from_addon_http_result(proxied)
                if converted is not None:
                    payload, status = converted
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("system_compat_stats"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("system_compat_stats"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[CompatStats] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("system_compat_stats"), status_code=502)

        return self.json(_build_legacy_compat_stats_payload(hass))


class SmartAgentDeprecationReadinessView(HomeAssistantView):
    """迁移兼容路由下线 readiness 只读分组接口。"""

    url = "/api/v1/system/deprecation-readiness"
    name = "api:smart_agent:v1:system:deprecation_readiness"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("GET", "/system/deprecation-readiness")
                converted = _json_from_addon_http_result(proxied)
                if converted is not None:
                    payload, status = converted
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("system_deprecation_readiness"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("system_deprecation_readiness"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[DeprecationReadiness] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("system_deprecation_readiness"), status_code=502)

        return self.json(_build_deprecation_readiness_payload(hass))


class SmartAgentDryoffSessionReportView(HomeAssistantView):
    """dryoff 短时会话只读报告接口。"""

    url = "/api/v1/system/dryoff-session-report"
    name = "api:smart_agent:v1:system:dryoff_session_report"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("GET", "/system/dryoff-session-report")
                converted = _json_from_addon_http_result(proxied)
                if converted is not None:
                    payload, status = converted
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("system_dryoff_session_report"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("system_dryoff_session_report"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[DryoffSessionReport] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("system_dryoff_session_report"), status_code=502)

        return self.json(_legacy_dryoff_report_payload(hass))


class SmartAgentDashboardSummaryView(HomeAssistantView):
    """仪表盘摘要接口。"""

    url = "/api/v1/dashboard/summary"
    name = "api:smart_agent:v1:dashboard:summary"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("GET", "/dashboard/summary")
                converted = _json_from_addon_http_result(proxied)
                if converted is not None:
                    payload, status = converted
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("dashboard_summary"), status_code=status)
                    if status >= 400:
                        return self.json(payload, status_code=status)
                    if not isinstance(payload, dict):
                        return self.json(_addon_unreachable_payload("dashboard_summary"), status_code=502)
                    payload["addon_diagnostics"] = _normalize_addon_diagnostics(payload.get("addon_diagnostics"))
                    payload.setdefault("decisions_today", 0)
                    payload.setdefault("corrections_today", 0)
                    payload.setdefault("action_total_7d", 0)
                    payload.setdefault("action_success_rate_7d", 0.0)
                    try:
                        caps = await _addon_client.get_capabilities()
                        if isinstance(caps, dict) and caps:
                            payload["addon_capabilities"] = caps
                    except Exception:
                        pass
                    try:
                        core_status = await _addon_client.get_core_status()
                        if isinstance(core_status, dict) and core_status:
                            payload["addon_core_status"] = core_status
                    except Exception:
                        pass
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("dashboard_summary"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[DashboardSummary] add-on summary proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("dashboard_summary"), status_code=502)

        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("dashboard_summary"), status_code=404)
        return self.json(_addon_unreachable_payload("dashboard_summary"), status_code=502)


def _build_presence_fusion_summary(coord) -> list[dict]:
    """汇总 PresenceFusion 域状态，供 diagnostics/UI 使用。"""
    fusion = getattr(coord, "_fusion_registry", None)
    if fusion is None or not hasattr(fusion, "get_summary"):
        return []
    try:
        summary = fusion.get_summary()
        return summary if isinstance(summary, list) else []
    except Exception as exc:
        _LOGGER.debug("[Diagnostics] build presence_fusion_summary failed: %s", exc)
        return []


def _build_topology_summary(coord) -> dict[str, Any]:
    """汇总 room topology 统计，供 diagnostics/UI 使用。"""
    try:
        topo_cache = get_room_topology_cache_snapshot(coord)
        if topo_cache:
            rooms = sorted(str(r) for r in topo_cache.keys())
            edge_count = int(sum(len(v or set()) for v in topo_cache.values()) / 2)
            isolated = [r for r, v in topo_cache.items() if not v]
            return {
                "configured_rooms": len(rooms),
                "edge_count": edge_count,
                "isolated_rooms": sorted(str(r) for r in isolated),
            }

        if hasattr(coord, "_db"):
            rows = coord._db.query(
                "SELECT room_a, room_b, relation FROM room_topology",
                (),
            ) or []
            rooms_set: set[str] = set()
            edges: set[tuple[str, str]] = set()
            for row in rows:
                a = str(row.get("room_a", "") or "")
                b = str(row.get("room_b", "") or "")
                if not a or not b:
                    continue
                rooms_set.add(a)
                rooms_set.add(b)
                edge = tuple(sorted((a, b)))
                edges.add(edge)
            return {
                "configured_rooms": len(rooms_set),
                "edge_count": len(edges),
                "isolated_rooms": [],
            }
    except Exception as exc:
        _LOGGER.debug("[Diagnostics] build topology_summary failed: %s", exc)

    return {
        "configured_rooms": 0,
        "edge_count": 0,
        "isolated_rooms": [],
    }


class SmartAgentDiagnosticsView(HomeAssistantView):
    """系统诊断接口（聚合 Add-on 诊断）。"""

    url = "/api/v1/system/diagnostics"
    extra_urls = ["/api/v1/diagnostics"]
    name = "api:smart_agent:v1:system:diagnostics"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        is_addon_proxy = _is_addon_proxy_request(request)

        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("system_diagnostics"), status_code=404)

        if _addon_client is None:
            return self.json(_addon_unreachable_payload("system_diagnostics"), status_code=502)
        try:
            proxied = await _addon_client.request_json("GET", "/system/diagnostics")
            if isinstance(proxied, dict) and int(proxied.get("status_code", 0) or 0) in (404, 405):
                proxied = await _addon_client.request_json("GET", "/diagnostics")
            converted = _json_from_addon_http_result(proxied)
            if converted is None:
                return self.json(_addon_unreachable_payload("system_diagnostics"), status_code=502)
            payload, status = converted
            if isinstance(payload, dict):
                payload["addon_diagnostics"] = _normalize_addon_diagnostics(payload.get("addon_diagnostics"))
            if status < 400 and isinstance(payload, dict):
                payload.setdefault("wave_semantics", _default_wave_semantics_payload(payload.get("mode", "unknown")))
                payload.setdefault("compat_summary", _build_compat_summary_payload(hass))
                payload.setdefault("presence_fusion_summary", _build_presence_fusion_summary(coord))
                payload.setdefault("topology_summary", _build_topology_summary(coord))
                try:
                    caps = await _addon_client.get_capabilities()
                    if isinstance(caps, dict) and caps:
                        payload["addon_capabilities"] = caps
                except Exception:
                    pass
                try:
                    core_status = await _addon_client.get_core_status()
                    if isinstance(core_status, dict) and core_status:
                        payload["addon_core_status"] = core_status
                except Exception:
                    pass
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[Diagnostics] add-on diagnostics failed: %s", exc)
            return self.json(_addon_unreachable_payload("system_diagnostics"), status_code=502)



class SmartAgentSystemSettingsView(HomeAssistantView):
    """系统设置读取/写入接口。"""

    url = "/api/v1/settings/system"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:settings:system"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("settings_system_get"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            # 收口决定（2026-05-12）：系统设置的唯一真源是 add-on core_configs。
            # HA 侧不再作为 fallback 真源，避免"写 A 读 B"：add-on 回读时
            # 返回 404 让 add-on 走本地存储路径。
            return self.json(_addon_endpoint_missing_payload("settings_system_get"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("settings_system_get"), status_code=502)

        try:
            settings = await _addon_client.get_system_settings()
            if isinstance(settings, dict):
                normalized = _json_from_addon_http_result(settings)
                if normalized is not None:
                    payload, status = normalized
                else:
                    payload, status = _json_from_addon_result(settings)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("settings_system_get"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("settings_system_get"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[SystemSettingsGet] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("settings_system_get"), status_code=502)

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("JSON body must be object")
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False),
                status_code=400,
            )

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            # 收口决定（2026-05-12）：系统设置的唯一真源是 add-on core_configs。
            # 此前此分支在 HA coordinator 和 config entry 上做本地双写，导致
            # "add-on 以为写自己实际写 HA"的典型"写 A 读 B"错位。
            # 现统一返回 404，让 add-on 走自己的本地存储 + entry persist 链。
            return self.json(_addon_endpoint_missing_payload("settings_system_post"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("settings_system_post"), status_code=502)

        try:
            proxied = await _addon_client.post_system_settings(body)
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                else:
                    payload, status = _json_from_addon_result(proxied)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("settings_system_post"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("settings_system_post"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[SystemSettingsPost] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("settings_system_post"), status_code=502)


class SmartAgentAuthLoginView(HomeAssistantView):
    """迁移期登录接口：校验来源 token 后签发管理端会话 token。"""

    url = "/api/v1/auth/login"
    name = "api:smart_agent:v1:auth:login"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        try:
            body = await request.json()
            if not isinstance(body, dict):
                body = {}
        except Exception:
            body = {}

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.post_auth_login(body)
                if isinstance(proxied, dict):
                    payload, status = _json_from_addon_result(proxied)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("auth_login"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[AuthLogin] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("auth_login"), status_code=502)

        user = request.get("hass_user")
        source_token = ""

        if user is None:
            source_token = str((body or {}).get("token", "") or "").strip()
            if not source_token:
                source_token = _extract_bearer_token(request)
            if not source_token:
                return self.json(
                    _json_error_payload("token_required", "auth_failed", False),
                    status_code=401,
                )
            user = await _resolve_user_from_token(hass, source_token)
            if user is None:
                return self.json(
                    _json_error_payload("invalid_token", "auth_failed", False),
                    status_code=401,
                )

        if not bool(getattr(user, "is_admin", False)):
            return self.json(
                _json_error_payload("forbidden", "auth_failed", False),
                status_code=403,
            )

        session_token = await _issue_auth_session(hass, user, source_token)
        return self.json({
            "ok": True,
            "token": session_token,
            "auth_mode": "gateway_session",
            "expires_in": _AUTH_SESSION_TTL,
            "user": {
                "id": getattr(user, "id", "") or "",
                "name": getattr(user, "name", "") or "",
                "is_admin": bool(getattr(user, "is_admin", False)),
                "is_owner": bool(getattr(user, "is_owner", False)),
            },
        })

class SmartAgentAuthMeView(HomeAssistantView):
    """当前会话用户信息接口。"""

    url = "/api/v1/auth/me"
    name = "api:smart_agent:v1:auth:me"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        session_token = _extract_bearer_token(request)
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.get_auth_me(session_token)
                if isinstance(proxied, dict):
                    payload, status = _json_from_addon_result(proxied)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("auth_me"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[AuthMe] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("auth_me"), status_code=502)

        user = await _resolve_user_by_auth_session(hass, session_token) if session_token else None
        auth_mode = "gateway_session"

        if user is None:
            user = await _resolve_request_user(request)
            auth_mode = "ha_session"
        if user is None:
            return self.json(
                _json_error_payload("unauthorized", "auth_failed", False),
                status_code=401,
            )
        return self.json({
            "ok": True,
            "id": getattr(user, "id", "") or "",
            "name": getattr(user, "name", "") or "",
            "is_admin": bool(getattr(user, "is_admin", False)),
            "is_owner": bool(getattr(user, "is_owner", False)),
            "auth_mode": auth_mode,
        })

class SmartAgentAuthLogoutView(HomeAssistantView):
    """迁移期登出接口（清理前端会话用）。"""

    url = "/api/v1/auth/logout"
    name = "api:smart_agent:v1:auth:logout"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        session_token = _extract_bearer_token(request)
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.post_auth_logout(session_token)
                if isinstance(proxied, dict):
                    payload, status = _json_from_addon_result(proxied)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("auth_logout"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[AuthLogout] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("auth_logout"), status_code=502)

        if session_token:
            sessions = _get_auth_sessions(hass)
            if session_token in sessions:
                sessions.pop(session_token, None)
                return self.json({"ok": True})

        user = await _resolve_request_user(request)
        if user is None:
            return self.json(
                _json_error_payload("unauthorized", "auth_failed", False),
                status_code=401,
            )
        return self.json({"ok": True})

class SmartAgentSystemBrandView(HomeAssistantView):
    """品牌信息接口。"""

    url = "/api/v1/system/brand"
    name = "api:smart_agent:v1:system:brand"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        user = request.get("hass_user")
        if user is None:
            user = await _resolve_request_user(request)
        if user is None:
            return self.json(
                _json_error_payload("unauthorized", "auth_failed", False),
                status_code=401,
            )
        if not bool(getattr(user, "is_admin", False)):
            return self.json(
                _json_error_payload("forbidden", "auth_failed", False),
                status_code=403,
            )
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json({"name": "SmartAgent", "color": "#6750A4", "logoUrl": "", "deployName": ""})

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                brand = await _addon_client.get_system_brand()
                if isinstance(brand, dict):
                    normalized = _json_from_addon_http_result(brand)
                    if normalized is not None:
                        payload, status = normalized
                    else:
                        payload, status = _json_from_addon_result(brand)
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("system_brand"), status_code=status)
                    return self.json(payload, status_code=status)
                else:
                    return self.json(_addon_unreachable_payload("system_brand"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[SystemBrand] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("system_brand"), status_code=502)

        return self.json({
            "name": getattr(coord, "brand_name", "SmartAgent") or "SmartAgent",
            "color": getattr(coord, "brand_primary_color", "#6750A4") or "#6750A4",
            "logoUrl": getattr(coord, "brand_logo_url", "") or "",
            "deployName": getattr(coord, "deploy_name", "") or "",
        })


class SmartAgentEventsWSView(HomeAssistantView):
    """最小可用事件流端点（迁移期）。"""

    url = "/api/v1/events"
    name = "api:smart_agent:v1:events"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                session = await _addon_client.get_http_session()
                upstream = await session.ws_connect(
                    _addon_client.ws_url("/events"),
                    params=dict(request.query),
                    headers=_addon_client.auth_headers,
                    heartbeat=30,
                    timeout=20,
                )
            except aiohttp.WSServerHandshakeError as exc:
                status = int(getattr(exc, "status", 0) or 0)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("events_ws"), status_code=status)
                elif status > 0:
                    error = "upstream_request_failed"
                    if status == 401:
                        error = "unauthorized"
                    elif status == 403:
                        error = "forbidden"
                    return self.json(
                        _json_error_payload(error, _status_error_type(status), _is_retryable_status(status)),
                        status_code=status,
                    )
                else:
                    return self.json(_addon_unreachable_payload("events_ws"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[EventsWS] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("events_ws"), status_code=502)
            else:
                ws = web.WebSocketResponse(heartbeat=30)
                await ws.prepare(request)
                try:
                    async def _up_to_client() -> None:
                        async for msg in upstream:
                            if msg.type == web.WSMsgType.TEXT:
                                await ws.send_str(str(msg.data))
                            elif msg.type == web.WSMsgType.BINARY:
                                await ws.send_bytes(msg.data)
                            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                                break

                    async def _client_to_up() -> None:
                        async for msg in ws:
                            if msg.type == web.WSMsgType.TEXT:
                                await upstream.send_str(str(msg.data))
                            elif msg.type == web.WSMsgType.BINARY:
                                await upstream.send_bytes(msg.data)
                            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                                break

                    up_task = asyncio.create_task(_up_to_client())
                    client_task = asyncio.create_task(_client_to_up())
                    done, pending = await asyncio.wait(
                        {up_task, client_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    for task in done:
                        task.result()
                except asyncio.TimeoutError:
                    _LOGGER.warning("[EventsWS] proxy relay timeout after handshake")
                except Exception as exc:
                    _LOGGER.warning("[EventsWS] proxy relay error after handshake: %s", exc)
                finally:
                    try:
                        await upstream.close()
                    except Exception:
                        pass
                    try:
                        await ws.close()
                    except Exception:
                        pass
                return ws

        user = await _resolve_request_user(request)
        if user is None:
            return self.json(_json_error_payload("unauthorized", "auth_failed", False), status_code=401)
        if not user.is_admin:
            return self.json(_json_error_payload("forbidden", "auth_failed", False), status_code=403)

        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        await ws.send_json({"type": "system.status.updated", "data": {"status": "connected"}})

        forward_events = {
            "smart_agent_confirm_required",
            "smart_agent_decision_bubble",
            "smart_agent_scene_created",
            "smart_agent_pairing_event",
            "smart_agent_voice_command",
            "smart_agent_listener_event",
            "state_changed",
        }
        state_changed_domains = (
            "sensor.",
            "binary_sensor.",
            "light.",
            "switch.",
            "climate.",
            "cover.",
            "fan.",
            "media_player.",
            "scene.",
            "automation.",
        )

        def _state_obj_to_jsonable(value):
            if value is None:
                return None
            as_dict = getattr(value, "as_dict", None)
            if callable(as_dict):
                return as_dict()
            if isinstance(value, dict):
                return value
            return {}

        def _event_int(value, default: int = 0) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        async def _forward(event):
            evt_type = getattr(event, "event_type", "")
            if evt_type not in forward_events:
                return
            event_data = dict(getattr(event, "data", {}) or {})
            if evt_type == "state_changed":
                old_state = _state_obj_to_jsonable(event_data.get("old_state"))
                new_state = _state_obj_to_jsonable(event_data.get("new_state"))
                entity_id = str(
                    event_data.get("entity_id")
                    or (new_state or {}).get("entity_id")
                    or (old_state or {}).get("entity_id")
                    or ""
                )
                if not entity_id.startswith(state_changed_domains):
                    return
                event_data = {
                    "entity_id": entity_id,
                    "old_state": old_state,
                    "new_state": new_state,
                }
            elif evt_type == "smart_agent_listener_event":
                event_data = {
                    "listener_action": str(event_data.get("listener_action") or ""),
                    "entity_id": str(event_data.get("entity_id") or ""),
                    "old_state": str(event_data.get("old_state") or ""),
                    "new_state": str(event_data.get("new_state") or ""),
                    "filter_reason": str(event_data.get("filter_reason") or ""),
                    "source_type": str(event_data.get("source_type") or ""),
                    "ai_enabled": bool(event_data.get("ai_enabled", False)),
                    "sensors_muted": bool(event_data.get("sensors_muted", False)),
                    "startup_remaining": _event_int(event_data.get("startup_remaining")),
                    "startup_cooldown": bool(event_data.get("startup_cooldown", False)),
                    "mode": str(event_data.get("mode") or ""),
                }
            payload = {
                "type": evt_type,
                "event_type": evt_type,
                "event": {
                    "event_type": evt_type,
                    "data": event_data,
                },
                "data": event_data,
            }
            try:
                await ws.send_json(payload)
            except Exception:
                pass

        unsubscribers = [hass.bus.async_listen(evt, _forward) for evt in forward_events]

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    if msg.data == "ping":
                        await ws.send_str("pong")
                elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.ERROR):
                    break
        finally:
            for unsub in unsubscribers:
                try:
                    unsub()
                except Exception:
                    pass

        return ws


class SmartAgentMemoryProfilesView(HomeAssistantView):
    """画像/规则读写接口（迁移期映射到 rules）。"""

    url = "/api/v1/memory/profiles"
    name = "api:smart_agent:v1:memory:profiles"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("memory_profiles"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_legacy_memory_profiles_snapshot(coord))

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("memory_profiles"), status_code=502)

        try:
            rows, proxied_error = await _addon_probe_list_result(
                _addon_client,
                "GET",
                ("/memory/profiles",),
            )
            if proxied_error is not None:
                payload, status = proxied_error
                return self.json(payload, status_code=status)
            if rows is not None:
                return self.json(rows)

            rows = await _addon_client.get_memory_profiles()
            payload, status = _addon_list_read_strict_response(rows, scope="memory_profiles")
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[MemoryProfiles] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("memory_profiles"), status_code=502)


class SmartAgentMemoryHabitsView(HomeAssistantView):
    """习惯读写接口。"""

    url = "/api/v1/memory/habits"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:memory:habits"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("memory_habits"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_legacy_memory_habits_snapshot(coord))

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("memory_habits"), status_code=502)

        try:
            rows = await _addon_client.get_memory_habits()
            payload, status = _addon_list_read_strict_response(rows, scope="memory_habits")
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[MemoryHabits] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("memory_habits"), status_code=502)


class SmartAgentLearningStatsView(HomeAssistantView):
    """学习统计接口。"""

    url = "/api/v1/learning/stats"
    name = "api:smart_agent:v1:learning:stats"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("learning_stats"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("learning_stats"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("learning_stats"), status_code=502)
        try:
            stats = await _addon_client.get_learning_stats()
            proxied = _addon_result_payload_status(stats if isinstance(stats, dict) else None)
            if proxied is not None:
                payload, status = proxied
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("learning_stats"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("learning_stats"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[LearningStats] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("learning_stats"), status_code=502)


class SmartAgentProfileActionView(HomeAssistantView):
    """画像（规则）写操作。"""

    url = "/api/v1/memory/profiles/{action}"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:profiles:action"
    requires_auth = True

    async def post(self, request: web.Request, action: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("profile_action"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid JSON"}, status_code=400)

        act = (action or "").strip().lower()
        if not act and request.path.endswith("toggle-lock"):
            act = "toggle-lock"

        content = str(body.get("content", "") or "").strip()
        if not content:
            return self.json({"ok": False, "error": "content required"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("profile_action"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("profile_action"), status_code=502)

        try:
            proxied = await _addon_client.post_profile_action(act, content)
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                normalized = _json_from_addon_result(proxied) if isinstance(proxied, dict) and "__status" in proxied else None
            if normalized is None:
                return self.json(_addon_unreachable_payload("profile_action"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("profile_action"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[ProfileAction] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("profile_action"), status_code=502)


class SmartAgentHabitActionView(HomeAssistantView):
    """习惯写操作（canonical：/api/v1/memory/habits/{action}）。"""

    url = "/api/v1/memory/habits/{action}"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:habits:action"
    requires_auth = True

    async def post(self, request: web.Request, action: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("habit_action"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid JSON"}, status_code=400)

        act = (action or "").strip().lower()
        if not act and request.path.endswith("toggle-lock"):
            act = "toggle-lock"

        content = str(body.get("content", "") or "").strip()
        if not content:
            return self.json({"ok": False, "error": "content required"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("habit_action"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("habit_action"), status_code=502)

        try:
            proxied = await _addon_client.post_habit_action(act, content)
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                normalized = _json_from_addon_result(proxied) if isinstance(proxied, dict) and "__status" in proxied else None
            if normalized is None:
                return self.json(_addon_unreachable_payload("habit_action"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("habit_action"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[HabitAction] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("habit_action"), status_code=502)


class SmartAgentCorrectionsView(HomeAssistantView):
    """纠错记录查询。"""

    url = "/api/v1/corrections"
    name = "api:smart_agent:v1:corrections"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("corrections"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_legacy_corrections_snapshot(coord))

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("corrections"), status_code=502)

        try:
            proxied = await _addon_client.request_json("GET", "/corrections")
            if not isinstance(proxied, dict):
                return self.json(_addon_unreachable_payload("corrections"), status_code=502)

            rows = _addon_result_list_body(proxied)
            if rows is not None:
                return self.json(rows)

            normalized = _json_from_addon_http_result(proxied)
            if normalized is not None:
                payload, status = normalized
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("corrections"), status_code=status)
                if status >= 400:
                    return self.json(payload, status_code=status)

            return self.json(_addon_unreachable_payload("corrections"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[Corrections] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("corrections"), status_code=502)


class SmartAgentCorrectionActionView(HomeAssistantView):
    """纠错动作接口（迁移期最小实现）。"""

    url = "/api/v1/corrections/{action}"
    extra_urls = []
    name = "api:smart_agent:v1:corrections:action"
    requires_auth = True

    async def post(self, request: web.Request, action: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        act = (action or "").strip().lower()

        try:
            body = await request.json()
        except Exception:
            body = {}

        entity_id = str((body or {}).get("entity_id", "") or "").strip()

        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("correction_action"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("correction_action"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("correction_action"), status_code=502)

        if act == "dismiss":
            try:
                proxied = await _addon_client.post_correction_action("dismiss", entity_id or None)
                normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
                if normalized is None:
                    return self.json(_addon_unreachable_payload("correction_action"), status_code=502)
                payload, status = normalized
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("correction_action"), status_code=status)
                return self.json(payload, status_code=status)
            except Exception as exc:
                _LOGGER.debug("[CorrectionAction] add-on dismiss proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("correction_action"), status_code=502)

        if act == "report":
            if not entity_id:
                return self.json({"ok": False, "error": "entity_id required"}, status_code=400)
            try:
                proxied = await _addon_client.post_correction_action("report", entity_id)
                normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
                if normalized is None:
                    return self.json(_addon_unreachable_payload("correction_action"), status_code=502)
                payload, status = normalized
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("correction_action"), status_code=status)
                return self.json(payload, status_code=status)
            except Exception as exc:
                _LOGGER.debug("[CorrectionAction] add-on report proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("correction_action"), status_code=502)

        return self.json({"ok": False, "error": f"unsupported action: {act}"}, status_code=400)


class SmartAgentTransactionsView(HomeAssistantView):
    """事务查询接口。"""

    url = "/api/v1/transactions"
    name = "api:smart_agent:v1:transactions"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("transactions"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(get_transactions_cache_snapshot(coord))

        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("GET", "/transactions")
                if not isinstance(proxied, dict):
                    return self.json(_addon_unreachable_payload("transactions"), status_code=502)

                normalized = _json_from_addon_http_result(proxied)
                if normalized is None:
                    return self.json(_addon_unreachable_payload("transactions"), status_code=502)
                payload, status = normalized

                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("transactions"), status_code=status)

                if 200 <= status < 300:
                    raw_body = proxied.get("body")
                    if isinstance(raw_body, list):
                        return self.json(raw_body, status_code=status)
                    if isinstance(raw_body, dict) and isinstance(raw_body.get("data"), list):
                        return self.json(raw_body, status_code=status)
                    return self.json(_addon_unreachable_payload("transactions"), status_code=502)

                return self.json(payload, status_code=status)
            except Exception as exc:
                _LOGGER.debug("[Transactions] add-on transactions proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("transactions"), status_code=502)

        return self.json(_addon_unreachable_payload("transactions"), status_code=502)


class SmartAgentTransactionDetailView(HomeAssistantView):
    """事务详情接口。"""

    url = "/api/v1/transactions/{txn_id}"
    name = "api:smart_agent:v1:transactions:detail"
    requires_auth = True

    async def get(self, request: web.Request, txn_id: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        tid = str(txn_id or "").strip()
        if not tid:
            return self.json(
                _json_error_payload("invalid_transaction_id", "bad_request", False),
                status_code=400,
            )
        encoded_tid = quote(tid, safe="")

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("GET", f"/transactions/{encoded_tid}")
                if isinstance(proxied, dict):
                    normalized = _json_from_addon_http_result(proxied)
                    if normalized is not None:
                        payload, status = normalized
                        if status in (404, 405):
                            return self.json(_addon_endpoint_missing_payload("transactions_detail"), status_code=status)
                        return self.json(payload, status_code=status)
                    else:
                        return self.json(_addon_unreachable_payload("transactions_detail"), status_code=502)
                else:
                    return self.json(_addon_unreachable_payload("transactions_detail"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[TransactionsDetail] add-on detail proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("transactions_detail"), status_code=502)

        return self.json(_addon_unreachable_payload("transactions_detail"), status_code=502)


class SmartAgentDecisionTraceView(HomeAssistantView):
    """统一 Decision Trace 读取接口（最小聚合视图）。"""

    url = "/api/v1/decision-trace/{txn_id}"
    name = "api:smart_agent:v1:decision-trace:detail"
    requires_auth = True

    async def get(self, request: web.Request, txn_id: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        tid = str(txn_id or "").strip()
        if not tid:
            return self.json(
                _json_error_payload("invalid_transaction_id", "bad_request", False),
                status_code=400,
            )
        encoded_tid = quote(tid, safe="")

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                get_trace = getattr(_addon_client, "get_decision_trace_detail", None)
                if callable(get_trace):
                    proxied = await get_trace(tid)
                else:
                    proxied = await _addon_client.request_json("GET", f"/decision-trace/{encoded_tid}")
                if isinstance(proxied, dict):
                    normalized = _json_from_addon_http_result(proxied)
                    if normalized is not None:
                        payload, status = normalized
                        if status in (404, 405):
                            return self.json(_addon_endpoint_missing_payload("decision_trace_detail"), status_code=status)
                        return self.json(payload, status_code=status)
                    else:
                        return self.json(_addon_unreachable_payload("decision_trace_detail"), status_code=502)
                return self.json(_addon_unreachable_payload("decision_trace_detail"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[DecisionTrace] add-on detail proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("decision_trace_detail"), status_code=502)

        if not is_addon_proxy:
            return self.json(_addon_unreachable_payload("decision_trace_detail"), status_code=502)

        # Phase C: the add-on proxy path must not synthesize Decision Trace from
        # HA local transaction/action_results tables. The add-on owns this read model.
        return self.json(_addon_endpoint_missing_payload("decision_trace_detail"), status_code=404)

        txns = coord._transactions_cache if isinstance(coord._transactions_cache, list) else []
        raw_detail = next(
            (
                t
                for t in txns
                if isinstance(t, dict)
                and str(t.get("transaction_id") or t.get("id") or "").strip() == tid
            ),
            None,
        )
        if raw_detail is None:
            return self.json(
                _json_error_payload("trace_not_found", "not_found", False),
                status_code=404,
            )
        detail = {k: v for k, v in raw_detail.items() if k != "pre_states_json"}

        def _decode_json_list(*values: Any) -> list[Any]:
            import json as _json

            for value in values:
                if value in (None, ""):
                    continue
                parsed = value
                if isinstance(value, str):
                    try:
                        parsed = _json.loads(value)
                    except Exception:
                        continue
                if isinstance(parsed, list):
                    return list(parsed)
            return []

        def _decode_json_object(value: Any) -> dict[str, Any]:
            import json as _json

            if isinstance(value, dict):
                return dict(value)
            if not isinstance(value, str) or not value:
                return {}
            try:
                parsed = _json.loads(value)
            except Exception:
                return {}
            return dict(parsed) if isinstance(parsed, dict) else {}

        def _query_legacy_trace_rows(sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
            db = getattr(coord, "_db", None)
            query = getattr(db, "query", None)
            if not callable(query):
                return []
            try:
                rows = query(sql, params)
            except TypeError:
                try:
                    rows = query(sql, params, max_rows=100)
                except Exception:
                    return []
            except Exception:
                return []
            if not isinstance(rows, list):
                return []
            normalized: list[dict[str, Any]] = []
            for row in rows:
                try:
                    item = dict(row)
                except Exception:
                    continue
                normalized.append(item)
            return normalized

        legacy_events = [
            row
            for row in _query_legacy_trace_rows(
                "SELECT time, type, detail, entity, state, source, area, confidence, transaction_id, action_seq "
                "FROM events WHERE CAST(transaction_id AS TEXT)=? ORDER BY action_seq ASC, time ASC",
                (tid,),
            )
            if row.get("type") or row.get("detail") or row.get("entity")
        ]
        legacy_action_results = [
            row
            for row in _query_legacy_trace_rows(
                "SELECT time, entity_id, domain, service, expected_state, actual_state, verified, success, "
                "retry_count, latency_ms, reason, transaction_id, action_seq "
                "FROM action_results WHERE CAST(transaction_id AS TEXT)=? ORDER BY action_seq ASC, time ASC",
                (tid,),
            )
            if row.get("entity_id") or row.get("service")
        ]

        raw_actions = _decode_json_list(
            detail.get("actions"),
            detail.get("actions_json"),
            detail.get("result_json"),
        )
        raw_results = _decode_json_list(
            detail.get("action_results"),
            detail.get("results"),
            detail.get("results_json"),
            detail.get("result_json"),
        )
        if not raw_results and legacy_action_results:
            raw_results = legacy_action_results
        if not raw_actions and legacy_action_results:
            raw_actions = [
                {
                    key: row.get(key)
                    for key in ("entity_id", "domain", "service", "expected_state", "actual_state", "action_seq")
                    if row.get(key) not in (None, "")
                }
                for row in legacy_action_results
            ]
        execution_payload = detail.get("execution") if isinstance(detail.get("execution"), dict) else {}
        execution_payload = dict(execution_payload)
        if raw_results:
            execution_payload.setdefault("action_results", raw_results)
        rollback_payload = detail.get("rollback_info") if isinstance(detail.get("rollback_info"), dict) else {}
        rollback_payload = dict(rollback_payload)
        pre_states = _decode_json_object(raw_detail.get("pre_states_json"))
        if pre_states:
            rollback_payload.setdefault("pre_states", pre_states)

        _status = detail.get("status", "")
        _created_at = detail.get("created_at", detail.get("time", ""))
        _confidence = detail.get("confidence", 0)
        _action_count = detail.get("action_count", 0)
        _blocked_count = detail.get("blocked_count", 0)
        _failed_count = detail.get("failed_count", 0)
        _trigger = detail.get("trigger_summary", "")
        if not _trigger and legacy_events:
            _trigger = legacy_events[0].get("detail") or legacy_events[0].get("type") or ""
        _context_snapshot = {
            "confidence": _confidence,
            "action_count": _action_count,
            "blocked_count": _blocked_count,
            "failed_count": _failed_count,
            "created_at": _created_at,
        }
        if legacy_events:
            _context_snapshot["events"] = legacy_events
        if legacy_action_results:
            _context_snapshot["action_results"] = legacy_action_results

        trace_payload = {
            "trace_version": "1.0",
            "trace_source": "ha_local_cache",
            "transaction_id": tid,
            "trigger": _trigger,
            "scene": detail.get("scene_desc", detail.get("scene", "")),
            "status": _status,
            "summary": {
                "status": _status,
                "confidence": _confidence,
                "action_count": _action_count,
                "blocked_count": _blocked_count,
                "failed_count": _failed_count,
                "created_at": _created_at,
            },
            "context_snapshot": _context_snapshot,
            "actions": raw_actions,
            "execution": execution_payload,
            "verification": {
                "blocked_count": _blocked_count,
                "failed_count": _failed_count,
            },
            "rollback": rollback_payload,
            "final_outcome": _status,
            "raw": detail,
        }
        return self.json(trace_payload)

class SmartAgentTransactionRollbackView(HomeAssistantView):
    """事务回滚接口。"""

    url = "/api/v1/transactions/{txn_id}/rollback"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:transactions:rollback"
    requires_auth = True

    async def post(self, request: web.Request, txn_id: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        tid_raw = txn_id
        if not tid_raw:
            try:
                body = await request.json()
            except Exception:
                body = {}
            tid_raw = body.get("id") or body.get("transaction_id")

        try:
            tid = int(tid_raw)
        except (TypeError, ValueError):
            return self.json(
                _json_error_payload("invalid_transaction_id", "bad_request", False),
                status_code=400,
            )
        if tid <= 0:
            return self.json(
                _json_error_payload("invalid_transaction_id", "bad_request", False),
                status_code=400,
            )

        is_addon_proxy = _is_addon_proxy_request(request)

        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                result = await _addon_client.rollback_transaction(tid)
                if isinstance(result, dict):
                    normalized = _json_from_addon_http_result(result)
                    if normalized is not None:
                        payload, status = normalized
                    elif "__status" in result:
                        payload, status = _json_from_addon_result(result)
                    else:
                        return self.json(_addon_unreachable_payload("transactions_rollback"), status_code=502)
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("transactions_rollback"), status_code=status)
                    return self.json(payload, status_code=status)
                else:
                    return self.json(_addon_unreachable_payload("transactions_rollback"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[TxnRollback] add-on rollback proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("transactions_rollback"), status_code=502)

        return self.json(_addon_unreachable_payload("transactions_rollback"), status_code=502)


class SmartAgentEnergyView(HomeAssistantView):
    """能耗统计接口。"""

    url = "/api/v1/energy"
    name = "api:smart_agent:v1:energy"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None or isinstance(coord, bool):
            return self.json(_addon_unreachable_payload("energy"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            cached_stats = getattr(coord, "_energy_stats", [])
            if not isinstance(cached_stats, list):
                return self.json([])
            device_info = getattr(coord, "device_info", {})
            if not isinstance(device_info, dict):
                device_info = {}
            rows: list[Any] = []
            for item in cached_stats:
                if not isinstance(item, dict):
                    rows.append(item)
                    continue
                row = dict(item)
                entity_id = str(row.get("entity_id") or "")
                info = device_info.get(entity_id, {})
                if not isinstance(info, dict):
                    info = {}
                if "triggers" not in row and "on_count" in row:
                    row["triggers"] = row.get("on_count")
                if not row.get("name"):
                    row["name"] = info.get("name") or info.get("friendly_name") or entity_id
                if not row.get("room"):
                    row["room"] = info.get("room") or info.get("area") or ""
                rows.append(row)
            return self.json(rows)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("energy"), status_code=502)

        try:
            rows, proxied_error = await _addon_probe_list_result(
                _addon_client,
                "GET",
                ("/energy",),
            )
            if proxied_error is not None:
                payload, status = proxied_error
                return self.json(payload, status_code=status)
            if rows is not None:
                return self.json(rows)

            stats = await _addon_client.get_energy()
            proxied = _addon_result_payload_status(stats if isinstance(stats, dict) else None)
            if proxied is not None:
                payload, status = proxied
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("energy"), status_code=status)
                return self.json(payload, status_code=status)
            if isinstance(stats, list):
                return self.json(stats)
            if isinstance(stats, dict):
                rows = _addon_result_list_body(stats)
                if rows is not None:
                    return self.json(rows)
        except Exception as exc:
            _LOGGER.debug("[Energy] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("energy"), status_code=502)

        return self.json(_addon_unreachable_payload("energy"), status_code=502)


class SmartAgentLicenseStatusView(HomeAssistantView):
    """License 状态接口。"""

    url = "/api/v1/license/status"
    name = "api:smart_agent:v1:license:status"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("license_status"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            payload: dict[str, Any] = {}
            try:
                get_status = getattr(coord, "get_license_status", None)
                if callable(get_status):
                    raw = get_status()
                    if isinstance(raw, dict):
                        payload = dict(raw)
            except Exception as exc:
                _LOGGER.debug("[LicenseStatus] local add-on proxy fallback failed: %s", exc)
            if not payload:
                payload = {
                    "valid": False,
                    "tier": "free",
                    "tier_label": "免费版",
                    "daily_limit": 30,
                    "daily_used": 0,
                }
            payload.setdefault("valid", bool(payload.get("tier") in {"business", "biz", "pro", "enterprise"}))
            payload.setdefault("tier", "free")
            payload.setdefault("tier_label", "免费版")
            payload.setdefault("daily_limit", 30)
            payload.setdefault("daily_used", 0)
            payload["source"] = "ha_local_proxy_fallback"
            payload["upstream_status"] = 404
            return self.json(payload)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                status = await _addon_client.get_license_status()
                if isinstance(status, dict):
                    normalized = _json_from_addon_http_result(status)
                    if normalized is not None:
                        payload, status_code = normalized
                    else:
                        payload, status_code = _json_from_addon_result(status)
                    if status_code in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("license_status"), status_code=status_code)
                    return self.json(payload, status_code=status_code)
                return self.json(_addon_unreachable_payload("license_status"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[LicenseStatus] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("license_status"), status_code=502)

        return self.json(_addon_endpoint_missing_payload("license_status"), status_code=404)


class SmartAgentLicenseVerifyView(HomeAssistantView):
    """License 验证接口。"""

    url = "/api/v1/license/verify"
    name = "api:smart_agent:v1:license:verify"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("license_verify"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            body = {}
        key = str((body or {}).get("license_key", "") or "").strip() or None

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                result = await _addon_client.post_license_verify(key)
                if isinstance(result, dict):
                    normalized = _json_from_addon_http_result(result)
                    if normalized is not None:
                        payload, status = normalized
                    else:
                        payload, status = _json_from_addon_result(result)
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("license_verify"), status_code=status)
                    return self.json(payload, status_code=status)
                return self.json(_addon_unreachable_payload("license_verify"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[LicenseVerify] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("license_verify"), status_code=502)

        return self.json(_addon_endpoint_missing_payload("license_verify"), status_code=404)

class SmartAgentBackupsView(HomeAssistantView):
    """备份列表接口。"""

    url = "/api/v1/backups"
    name = "api:smart_agent:v1:backups"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("backups"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            rows: list[dict[str, Any]] = []
            backup_manager = getattr(coord, "_backup_manager", None)
            if backup_manager is not None:
                for method_name in ("list_backups", "get_backups", "list"):
                    method = getattr(backup_manager, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        result = method()
                        if asyncio.iscoroutine(result):
                            result = await result
                        if isinstance(result, list):
                            rows = [item for item in result if isinstance(item, dict)]
                            break
                        if isinstance(result, dict):
                            data = result.get("data") if isinstance(result.get("data"), list) else result.get("backups")
                            if isinstance(data, list):
                                rows = [item for item in data if isinstance(item, dict)]
                                break
                    except Exception as exc:
                        _LOGGER.debug("[Backups] local add-on proxy fallback failed via %s: %s", method_name, exc)
                        break
            return self.json(rows)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                rows, proxied_error = await _addon_probe_list_result(
                    _addon_client,
                    "GET",
                    ("/backups",),
                )
                if proxied_error is not None:
                    payload, status = proxied_error
                    return self.json(payload, status_code=status)
                if rows is not None:
                    return self.json(rows)

                backups = await _addon_client.get_backups()
                proxied = _addon_result_payload_status(backups if isinstance(backups, dict) else None)
                if proxied is not None:
                    payload, status = proxied
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("backups"), status_code=status)
                    return self.json(payload, status_code=status)
                if isinstance(backups, list):
                    return self.json(backups)
                if isinstance(backups, dict):
                    rows = _addon_result_list_body(backups)
                    if rows is not None:
                        return self.json(rows)
            except Exception as exc:
                _LOGGER.debug("[Backups] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("backups"), status_code=502)

        return self.json(_addon_unreachable_payload("backups"), status_code=502)


class SmartAgentBackupsActionView(HomeAssistantView):
    """备份操作接口。"""

    url = "/api/v1/backups/{action}"
    name = "api:smart_agent:v1:backups:action"
    requires_auth = True

    async def post(self, request: web.Request, action: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("backups_action"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            body = {}

        act = action.strip().lower()
        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            internal_execute = str(request.headers.get("X-SA-Internal-Execute", "") or "").strip() == "1"
            if internal_execute and act in {"create", "restore", "delete"}:
                backup_manager = getattr(coord, "_backup_manager", None)
                if backup_manager is None:
                    try:
                        from .backup import BackupManager

                        backup_manager = BackupManager(coord)
                        setattr(coord, "_backup_manager", backup_manager)
                    except Exception as exc:
                        _LOGGER.debug("[BackupsAction] local backup manager unavailable: %s", exc)
                        return self.json(_addon_unreachable_payload("backups_action"), status_code=502)

                def _backup_level(value: Any) -> str:
                    raw = str(value or "").strip().lower()
                    if raw == "full":
                        return "full"
                    if raw in {"basic", "partial"}:
                        return "standard"
                    return "standard"

                try:
                    if act == "create":
                        result = backup_manager.backup_now(
                            password=str(body.get("password") or ""),
                            level=_backup_level(body.get("level")),
                        )
                        if hasattr(result, "__await__"):
                            result = await result
                    elif act == "restore":
                        backup_id = str(body.get("backup_id") or body.get("id") or "").strip()
                        if not backup_id:
                            return self.json(
                                _json_error_payload(
                                    "backup_id_required",
                                    error_type="bad_request",
                                    retryable=False,
                                ),
                                status_code=400,
                            )
                        result = backup_manager.restore_backup(
                            backup_id=backup_id,
                            password=str(body.get("password") or ""),
                        )
                        if hasattr(result, "__await__"):
                            result = await result
                    else:
                        sanitizer = getattr(backup_manager, "_sanitize_backup_id", None)
                        backup_id = str(body.get("backup_id") or body.get("id") or "").strip()
                        if not backup_id:
                            return self.json(
                                _json_error_payload(
                                    "backup_id_required",
                                    error_type="bad_request",
                                    retryable=False,
                                ),
                                status_code=400,
                            )
                        if callable(sanitizer):
                            backup_id = sanitizer(backup_id)
                        backup_dir = os.path.join(coord.hass.config.config_dir, "smart_agent_backups")
                        fpath = os.path.join(backup_dir, f"{backup_id}.enc")
                        if not os.path.exists(fpath):
                            return self.json(
                                _json_error_payload(
                                    "backup_not_found",
                                    error_type="not_found",
                                    retryable=False,
                                ),
                                status_code=404,
                            )
                        await coord.hass.async_add_executor_job(os.remove, fpath)
                        result = {"ok": True, "action": "delete", "backup_id": backup_id}
                except Exception as exc:
                    _LOGGER.debug("[BackupsAction] local backup action failed: %s", exc)
                    return self.json(
                        _json_error_payload(
                            "backup_action_failed",
                            error_type="internal_error",
                            retryable=False,
                            message=str(exc),
                        ),
                        status_code=500,
                    )

                payload = result if isinstance(result, dict) else {"result": result}
                payload.setdefault("ok", bool(payload.get("success", True)))
                payload.setdefault("action", act)
                return self.json(payload, status_code=200)
            return self.json(_addon_endpoint_missing_payload("backups_action"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("backups_action"), status_code=502)

        try:
            proxied = await _addon_client.post_backup_action(act, body if isinstance(body, dict) else {})
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                normalized = _json_from_addon_result(proxied) if isinstance(proxied, dict) and "__status" in proxied else None
            if normalized is None:
                return self.json(_addon_unreachable_payload("backups_action"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("backups_action"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[BackupsAction] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("backups_action"), status_code=502)


class SmartAgentAiSceneOpsView(HomeAssistantView):
    """AI 场景扩展动作（分析/文本创建）。"""

    url = "/api/v1/ai-scenes/analyze"
    extra_urls = [
        "/api/v1/ai-scenes/create-from-text",
    ]
    name = "api:smart_agent:v1:ai_scenes:ops"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("ai_scene_ops"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            body = {}

        path = request.path.lower()
        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("ai_scene_ops"), status_code=404)

        if not (path.endswith("/analyze") or path.endswith("create-from-text")):
            return self.json({"ok": False, "error": "unsupported action"}, status_code=400)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("ai_scene_ops"), status_code=502)

        try:
            suffix = path.removeprefix("/api/v1")
            proxied = await _addon_client.request_json(
                "POST",
                suffix,
                body=body if isinstance(body, dict) else {},
            )
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                return self.json(_addon_unreachable_payload("ai_scene_ops"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("ai_scene_ops"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[AiSceneOps] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("ai_scene_ops"), status_code=502)


class SmartAgentModeView(HomeAssistantView):
    """运行模式切换接口（home/showroom）。"""

    url = "/api/v1/mode"
    name = "api:smart_agent:v1:mode"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("mode"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            body = {}

        mode = str((body or {}).get("mode", "") or "").strip().lower()
        if mode not in ("home", "showroom"):
            return self.json(_json_error_payload("invalid mode", "validation_error", False), status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            set_mode = getattr(coord, "async_set_mode", None)
            if callable(set_mode):
                result = set_mode(mode)
                if asyncio.iscoroutine(result):
                    await result
            else:
                setattr(coord, "_mode", mode)
            current_mode = str(getattr(coord, "_mode", mode) or mode)
            return self.json({
                "ok": True,
                "mode": current_mode,
                "source": "ha_local_proxy_fallback",
                "upstream_status": 404,
            })

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("mode"), status_code=502)

        try:
            proxied = await _addon_client.request_json("POST", "/mode", body={"mode": mode})
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                return self.json(_addon_unreachable_payload("mode"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("mode"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[Mode] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("mode"), status_code=502)


class SmartAgentShowroomSceneView(HomeAssistantView):
    """展厅场景/自定义提示设置接口。"""

    url = "/api/v1/showroom/scene"
    name = "api:smart_agent:v1:showroom:scene"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("showroom_scene"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            body = {}

        scene = str((body or {}).get("scene", "") or "").strip()
        custom_prompt = str((body or {}).get("custom_prompt", "") or "").strip()
        is_command = bool((body or {}).get("is_command", False))

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("showroom_scene"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("showroom_scene"), status_code=502)

        try:
            proxied = await _addon_client.request_json(
                "POST",
                "/showroom/scene",
                body={
                    "scene": scene,
                    "custom_prompt": custom_prompt,
                    "is_command": is_command,
                },
            )
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                return self.json(_addon_unreachable_payload("showroom_scene"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("showroom_scene"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[ShowroomScene] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("showroom_scene"), status_code=502)


class SmartAgentShowroomSceneConfigView(HomeAssistantView):
    """展厅预设场景配置更新接口。"""

    url = "/api/v1/showroom/scene-config"
    name = "api:smart_agent:v1:showroom:scene-config"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("showroom_scene_config"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            body = {}

        scene_key = str((body or {}).get("scene_key", "") or "").strip()
        if not scene_key:
            return self.json(_json_error_payload("scene_key required", "validation_error", False), status_code=400)

        patch_body = {
            "scene_key": scene_key,
            "label": (body or {}).get("label"),
            "virtual_time": (body or {}).get("virtual_time"),
            "scene_desc": (body or {}).get("scene_desc"),
            "hint": (body or {}).get("hint"),
        }
        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("showroom_scene_config"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("showroom_scene_config"), status_code=502)

        try:
            proxied = await _addon_client.request_json(
                "POST",
                "/showroom/scene-config",
                body=patch_body,
            )
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                return self.json(_addon_unreachable_payload("showroom_scene_config"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_addon_endpoint_missing_payload("showroom_scene_config"), status_code=status)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[ShowroomSceneConfig] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("showroom_scene_config"), status_code=502)


class SmartAgentPatrolTriggerView(HomeAssistantView):
    """巡检触发接口。"""

    url = "/api/v1/patrol/trigger"
    name = "api:smart_agent:v1:patrol:trigger"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("patrol_trigger"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_patrol_trigger_plan_only_payload("addon_proxy_loop_guard"), status_code=409)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("patrol_trigger"), status_code=502)

        try:
            proxied = await _addon_client.post_patrol_trigger()
            normalized = _json_from_addon_http_result(proxied if isinstance(proxied, dict) else None)
            if normalized is None:
                normalized = _json_from_addon_result(proxied) if isinstance(proxied, dict) and "__status" in proxied else None
            if normalized is None:
                return self.json(_addon_unreachable_payload("patrol_trigger"), status_code=502)
            payload, status = normalized
            if status in (404, 405):
                return self.json(_patrol_trigger_plan_only_payload("addon_endpoint_missing"), status_code=409)
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[PatrolTrigger] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("patrol_trigger"), status_code=502)


class SmartAgentDevicePairStartView(HomeAssistantView):
    """设备配对开始接口（复用极速配对逻辑）。"""

    url = "/api/v1/device/pair/start"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:pair:start"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.post_pair_start()
                if isinstance(proxied, dict):
                    normalized = _json_from_addon_http_result(proxied)
                    if normalized is not None:
                        payload, status = normalized
                    else:
                        payload, status = _json_from_addon_result(proxied)
                        if "__status" not in proxied:
                            return self.json(_addon_unreachable_payload("pair_start"), status_code=502)
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("pair_start"), status_code=status)
                    return self.json(payload, status_code=status)
                else:
                    return self.json(_addon_unreachable_payload("pair_start"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[PairStart] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("pair_start"), status_code=502)

        hass_user = request.get("hass_user")
        if hass_user is None:
            return self.json(
                _json_error_payload("unauthorized", "auth_failed", False),
                status_code=401,
            )

        try:
            from datetime import timedelta
            refresh_token = await hass.auth.async_create_refresh_token(
                hass_user,
                client_name="SmartAgent 中控屏",
                access_token_expiration=timedelta(days=90),
            )
            access_token = hass.auth.async_create_access_token(refresh_token)
        except Exception as ex:
            _LOGGER.error("[配对] 创建 Token 失败: %s", ex, exc_info=True)
            return self.json(
                _json_error_payload("token_issue_failed", "internal_error", False),
                status_code=500,
            )

        hass.data[_PAIR_KEY] = {
            "token": access_token,
            "ha_url": f"{request.scheme}://{request.host}",
            "expires_at": time.time() + 60,
        }
        return self.json({
            "ok": True,
            "status": "pairing_started",
            "expires_in": 60,
        })

class SmartAgentVoiceSessionView(HomeAssistantView):
    """语音会话事件流（迁移期最小实现）。"""

    url = "/api/v1/voice/session"
    name = "api:smart_agent:v1:voice:session"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                session = await _addon_client.get_http_session()
                upstream = await session.ws_connect(
                    _addon_client.ws_url("/voice/session"),
                    params=dict(request.query),
                    headers=_addon_client.auth_headers,
                    heartbeat=30,
                    timeout=20,
                )
            except aiohttp.WSServerHandshakeError as exc:
                status = int(getattr(exc, "status", 0) or 0)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("voice_session_ws"), status_code=status)
                elif status > 0:
                    error = "upstream_request_failed"
                    if status == 401:
                        error = "unauthorized"
                    elif status == 403:
                        error = "forbidden"
                    return self.json(
                        _json_error_payload(error, _status_error_type(status), _is_retryable_status(status)),
                        status_code=status,
                    )
                else:
                    return self.json(_addon_unreachable_payload("voice_session_ws"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[VoiceSessionWS] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("voice_session_ws"), status_code=502)
            else:
                ws = web.WebSocketResponse(heartbeat=30)
                await ws.prepare(request)
                try:
                    async def _up_to_client() -> None:
                        async for msg in upstream:
                            if msg.type == web.WSMsgType.TEXT:
                                await ws.send_str(str(msg.data))
                            elif msg.type == web.WSMsgType.BINARY:
                                await ws.send_bytes(msg.data)
                            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                                break

                    async def _client_to_up() -> None:
                        async for msg in ws:
                            if msg.type == web.WSMsgType.TEXT:
                                await upstream.send_str(str(msg.data))
                            elif msg.type == web.WSMsgType.BINARY:
                                await upstream.send_bytes(msg.data)
                            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                                break

                    up_task = asyncio.create_task(_up_to_client())
                    client_task = asyncio.create_task(_client_to_up())
                    done, pending = await asyncio.wait(
                        {up_task, client_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    for task in done:
                        task.result()
                except asyncio.TimeoutError:
                    _LOGGER.warning("[VoiceSessionWS] proxy relay timeout after handshake")
                except Exception as exc:
                    _LOGGER.warning("[VoiceSessionWS] proxy relay error after handshake: %s", exc)
                finally:
                    try:
                        await upstream.close()
                    except Exception:
                        pass
                    try:
                        await ws.close()
                    except Exception:
                        pass
                return ws

        user = await _resolve_request_user(request)
        if user is None:
            return self.json(_json_error_payload("unauthorized", "auth_failed", False), status_code=401)
        if not user.is_admin:
            return self.json(_json_error_payload("forbidden", "auth_failed", False), status_code=403)

        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        status = getattr(coord, "_voice_status", "idle") if coord is not None else "idle"
        reply = getattr(coord, "_voice_reply", "") if coord is not None else ""
        await ws.send_json({
            "type": "voice.session.updated",
            "data": {
                "status": status,
                "reply": str(reply or "")[:300],
            },
        })

        async def _forward(event):
            evt_type = getattr(event, "event_type", "")
            if evt_type != "smart_agent_voice_command":
                return
            payload = {
                "type": "voice.session.updated",
                "event_type": evt_type,
                "data": dict(getattr(event, "data", {}) or {}),
            }
            try:
                await ws.send_json(payload)
            except Exception:
                pass

        unsub = hass.bus.async_listen("smart_agent_voice_command", _forward)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT and msg.data == "ping":
                    await ws.send_str("pong")
                elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.ERROR):
                    break
        finally:
            try:
                unsub()
            except Exception:
                pass

        return ws


class SmartAgentVoiceInterruptView(HomeAssistantView):
    """语音中断接口（迁移期最小实现）。"""

    url = "/api/v1/voice/interrupt"
    name = "api:smart_agent:v1:voice:interrupt"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.post_voice_interrupt()
                if isinstance(proxied, dict):
                    normalized = _json_from_addon_http_result(proxied)
                    if normalized is not None:
                        payload, status = normalized
                    else:
                        payload, status = _json_from_addon_result(proxied)
                        if "__status" not in proxied:
                            return self.json(_addon_unreachable_payload("voice_interrupt"), status_code=502)
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("voice_interrupt"), status_code=status)
                    return self.json(payload, status_code=status)
                else:
                    return self.json(_addon_unreachable_payload("voice_interrupt"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[VoiceInterrupt] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("voice_interrupt"), status_code=502)

        user = await _resolve_request_user(request)
        if user is None:
            return self.json(
                _json_error_payload("unauthorized", "auth_failed", False),
                status_code=401,
            )
        if not user.is_admin:
            return self.json({"ok": False, "error": "forbidden"}, status_code=403)

        if coord is not None:
            setattr(coord, "_voice_status", "interrupted")
            setattr(coord, "_voice_reply", "")
            coord.async_set_updated_data({})

        request.app["hass"].bus.async_fire("smart_agent_voice_command", {
            "type": "interrupt",
            "status": "interrupted",
        })
        return self.json({"ok": True, "status": "interrupted"})

class SmartAgentVisionCamerasView(HomeAssistantView):
    """视觉摄像头查询接口。"""

    url = "/api/v1/vision/cameras"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:vision:cameras"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("vision_cameras"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("vision_cameras"), status_code=404)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("vision_cameras"), status_code=502)

        try:
            rows, proxied_error = await _addon_probe_list_result(
                _addon_client,
                "GET",
                ("/vision/cameras",),
            )
            if proxied_error is not None:
                payload, status = proxied_error
                return self.json(payload, status_code=status)
            if rows is not None:
                return self.json(rows)

            cameras = await _addon_client.get_vision_cameras()
            payload, status = _addon_list_read_strict_response(cameras, scope="vision_cameras")
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[VisionCameras] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("vision_cameras"), status_code=502)


class SmartAgentVisionCamerasActionView(HomeAssistantView):
    """视觉摄像头注册/删除接口。"""

    url = "/api/v1/vision/cameras/{action}"
    extra_urls = [
        "/api/v1/vision/cameras/register",
        "/api/v1/vision/cameras/delete",
    ]
    name = "api:smart_agent:v1:vision:cameras:action"
    requires_auth = True

    async def post(self, request: web.Request, action: str | None = None) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json({"ok": False, "error": "coordinator not found"}, status_code=404)

        try:
            body = await request.json()
        except Exception:
            body = {}

        act = (action or "").strip().lower()
        if not act:
            if request.path.endswith("/register"):
                act = "register"
            elif request.path.endswith("/delete"):
                act = "delete"
        if act not in {"register", "delete"}:
            return self.json({"ok": False, "error": f"unsupported action: {act}"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("vision_cameras_action"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("vision_cameras_action"), status_code=502)

        try:
            proxied = await _addon_client.post_vision_camera_action(act, body if isinstance(body, dict) else {})
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                else:
                    payload, status = _json_from_addon_result(proxied)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("vision_cameras_action"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("vision_cameras_action"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[VisionCamerasAction] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("vision_cameras_action"), status_code=502)


class SmartAgentVisionZonesView(HomeAssistantView):
    """视觉 zone 查询接口。"""

    url = "/api/v1/vision/zones"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:vision:zones"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(_addon_unreachable_payload("vision_zones"), status_code=502)

        try:
            body = await request.json()
        except Exception:
            body = {}
        camera_id = str((body or {}).get("camera_id", "") or "").strip()
        if not camera_id:
            return self.json({"ok": False, "error": "camera_id required"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("vision_zones"), status_code=404)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("vision_zones"), status_code=502)

        try:
            rows, proxied_error = await _addon_probe_list_result(
                _addon_client,
                "POST",
                ("/vision/zones",),
                {"camera_id": camera_id},
            )
            if proxied_error is not None:
                payload, status = proxied_error
                return self.json(payload, status_code=status)
            if rows is not None:
                return self.json(rows)

            zones = await _addon_client.get_vision_zones(camera_id)
            payload, status = _addon_list_read_strict_response(zones, scope="vision_zones")
            return self.json(payload, status_code=status)
        except Exception as exc:
            _LOGGER.debug("[VisionZones] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("vision_zones"), status_code=502)


class SmartAgentVisionZonesSaveView(HomeAssistantView):
    """视觉 zone 保存接口。"""

    url = "/api/v1/vision/zones/save"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:vision:zones:save"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json({"ok": False, "error": "coordinator not found"}, status_code=404)

        try:
            body = await request.json()
        except Exception:
            return self.json({"ok": False, "error": "invalid JSON"}, status_code=400)

        camera_id = str((body or {}).get("camera_id", "") or "").strip()
        zone_id = str((body or {}).get("zone_id", "") or "").strip()
        if not camera_id or not zone_id:
            return self.json({"ok": False, "error": "camera_id and zone_id required"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("vision_zones_save"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("vision_zones_save"), status_code=502)

        try:
            proxied = await _addon_client.save_vision_zone(body if isinstance(body, dict) else {})
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                else:
                    payload, status = _json_from_addon_result(proxied)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("vision_zones_save"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("vision_zones_save"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[VisionZonesSave] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("vision_zones_save"), status_code=502)


class SmartAgentMcpStatusView(HomeAssistantView):
    """MCP 状态查询接口。"""

    url = "/api/v1/mcp/status"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:mcp:status"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("mcp_status"), status_code=502)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            try:
                attrs = coord.get_config_attributes() if hasattr(coord, "get_config_attributes") else {}
            except Exception as exc:
                _LOGGER.debug("[McpStatus] local add-on proxy fallback failed: %s", exc)
                attrs = {}
            attrs = attrs if isinstance(attrs, dict) else {}
            enabled = bool(attrs.get("mcp_enabled", getattr(coord, "_mcp_enabled", True)))
            return self.json({
                "ok": True,
                "enabled": enabled,
                "status": "available" if enabled else "disabled",
                "endpoint": "/api/smart_agent/mcp",
                "tools": [],
                "protocol": {
                    "read_only_methods": ["tools/list"],
                    "write_methods_allowed": False,
                },
                "source": "ha_local_proxy_fallback",
                "upstream_status": 404,
            })

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("mcp_status"), status_code=502)

        try:
            status = await _addon_client.get_mcp_status()
            if isinstance(status, dict):
                normalized = _json_from_addon_http_result(status)
                if normalized is not None:
                    payload, status_code = normalized
                else:
                    payload, status_code = _json_from_addon_result(status)
                if status_code in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("mcp_status"), status_code=status_code)
                return self.json(payload, status_code=status_code)
            return self.json(_addon_unreachable_payload("mcp_status"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[McpStatus] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("mcp_status"), status_code=502)


class SmartAgentMcpSettingsView(HomeAssistantView):
    """MCP 设置写入接口（迁移期映射到 update_config）。"""

    url = "/api/v1/mcp/settings"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:mcp:settings"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("JSON body must be object")
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False),
                status_code=400,
            )

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("mcp_settings"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("mcp_settings"), status_code=502)

        try:
            proxied = await _addon_client.post_mcp_settings(body)
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    payload, status = normalized
                else:
                    payload, status = _json_from_addon_result(proxied)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("mcp_settings"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("mcp_settings"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[McpSettings] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("mcp_settings"), status_code=502)


class SmartAgentHaExecuteView(HomeAssistantView):
    """HA 宿主执行边界：统一承接 CommandEnvelope。"""

    url = "/api/v1/ha/execute"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:ha:execute"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        if not _is_addon_internal_execute_request(request):
            return self.json(
                _json_error_payload(
                    "ha_execute_requires_addon_internal",
                    "auth_failed",
                    False,
                    execution_path="ha_execute_adapter",
                ),
                status_code=403,
            )
        try:
            body = await request.json()
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False),
                status_code=400,
            )

        if not isinstance(body, dict):
            return self.json(
                _json_error_payload("invalid_body", "bad_request", False),
                status_code=400,
            )

        result = await async_execute_command_envelope(request.app["hass"], body)
        status_code = 200 if bool(result.get("ok")) else 409
        error_type = str(result.get("error_type") or "")
        if error_type in {"bad_request", "safety_blocked"}:
            status_code = 400
        payload = dict(result)
        payload["execution_path"] = "ha_execute_adapter"
        return self.json(payload, status_code=status_code)


class SmartAgentCapabilityDryRunView(HomeAssistantView):
    """P5-C capability dry-run：仅输出建议与拒绝原因，不执行真实动作。"""

    url = "/api/v1/capability/dry-run"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:capability:dry_run"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("JSON body must be object")
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False),
                status_code=400,
            )

        capability = str(body.get("capability") or "").strip().lower()
        if capability not in {"security", "vacuum", "appliance"}:
            return self.json(
                _json_error_payload(
                    "invalid_capability",
                    "validation_error",
                    False,
                    details={"allowed": ["security", "vacuum", "appliance"]},
                ),
                status_code=400,
            )

        payload = {
            "capability": capability,
            "dry_run": bool(body.get("dry_run", True)),
            "context": body.get("context") if isinstance(body.get("context"), dict) else {},
            "constraints": body.get("constraints") if isinstance(body.get("constraints"), dict) else {},
        }

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("capability_dry_run"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("capability_dry_run"), status_code=502)

        try:
            proxied = await _addon_client.post_capability_dry_run(payload)
            if isinstance(proxied, dict):
                normalized = _json_from_addon_http_result(proxied)
                if normalized is not None:
                    body_payload, status = normalized
                else:
                    body_payload, status = _json_from_addon_result(proxied)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("capability_dry_run"), status_code=status)
                return self.json(body_payload, status_code=status)
            return self.json(_addon_unreachable_payload("capability_dry_run"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[CapabilityDryRun] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("capability_dry_run"), status_code=502)


class SmartAgentAiSceneDeleteFallbackView(HomeAssistantView):
    """场景删除回退接口：POST /api/v1/ai-scenes/{id}。"""

    url = "/api/v1/ai-scenes/{scene_id}"
    name = "api:smart_agent:v1:ai_scenes:delete_fallback"
    requires_auth = True

    async def post(self, request: web.Request, scene_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("ai_scene_delete_fallback"), status_code=502)

        try:
            sid = int(scene_id)
        except (TypeError, ValueError):
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)
        if sid <= 0:
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        if is_addon_proxy:
            return self.json(_addon_endpoint_missing_payload("ai_scene_delete_fallback"), status_code=404)

        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is None:
            return self.json(_addon_unreachable_payload("ai_scene_delete_fallback"), status_code=502)

        try:
            proxied = await _addon_client.post_ai_scene_delete_fallback(sid)
            if isinstance(proxied, dict):
                payload, status = _json_from_addon_result(proxied)
                if status in (404, 405):
                    return self.json(_addon_endpoint_missing_payload("ai_scene_delete_fallback"), status_code=status)
                return self.json(payload, status_code=status)
            return self.json(_addon_unreachable_payload("ai_scene_delete_fallback"), status_code=502)
        except Exception as exc:
            _LOGGER.debug("[AiSceneDeleteFallback] add-on proxy failed: %s", exc)
            return self.json(_addon_unreachable_payload("ai_scene_delete_fallback"), status_code=502)


class SmartAgentAiSceneArchiveView(HomeAssistantView):
    """场景归档接口：POST /api/v1/ai-scenes/{scene_id}/archive。"""

    url = "/api/v1/ai-scenes/{scene_id}/archive"
    name = "api:smart_agent:v1:ai_scenes:archive"
    requires_auth = True

    async def post(self, request: web.Request, scene_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err
        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json(_addon_unreachable_payload("ai_scene_archive"), status_code=502)

        try:
            sid = int(scene_id)
        except (TypeError, ValueError):
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)
        if sid <= 0:
            return self.json({"ok": False, "error": "invalid scene id"}, status_code=400)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None)
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.post_ai_scene_archive(sid)
                if isinstance(proxied, dict):
                    payload, status = _json_from_addon_result(proxied)
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("ai_scene_archive"), status_code=status)
                    return self.json(payload, status_code=status)
                else:
                    return self.json(_addon_unreachable_payload("ai_scene_archive"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[AiSceneArchive] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("ai_scene_archive"), status_code=502)

        return self.json(_addon_unreachable_payload("ai_scene_archive"), status_code=502)


# 极速配对临时存储 key（存于 hass.data）
_PAIR_KEY = "smart_agent_pairing_token"
_AUTH_SESSION_KEY = "smart_agent_auth_sessions"
_AUTH_SESSION_TTL = 24 * 3600


def _get_auth_sessions(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    sessions = hass.data.get(_AUTH_SESSION_KEY)
    if isinstance(sessions, dict):
        return sessions
    sessions = {}
    hass.data[_AUTH_SESSION_KEY] = sessions
    return sessions


def _purge_auth_sessions(hass: HomeAssistant) -> None:
    sessions = _get_auth_sessions(hass)
    now_ts = time.time()
    expired = [tk for tk, info in sessions.items() if float((info or {}).get("expires_at", 0) or 0) <= now_ts]
    for tk in expired:
        sessions.pop(tk, None)


async def _issue_auth_session(hass: HomeAssistant, user, source_token: str) -> str:
    _purge_auth_sessions(hass)

    refresh_token = None
    try:
        refresh_token = next(
            (t for t in getattr(user, "refresh_tokens", {}).values() if t.client_name == "SmartAgent 管理端会话"),
            None,
        )
    except Exception:
        refresh_token = None

    if refresh_token is None:
        refresh_token = await hass.auth.async_create_refresh_token(
            user,
            client_name="SmartAgent 管理端会话",
            access_token_expiration=timedelta(seconds=_AUTH_SESSION_TTL),
        )

    session_token = hass.auth.async_create_access_token(refresh_token)
    sessions = _get_auth_sessions(hass)
    sessions[session_token] = {
        "user_id": getattr(user, "id", "") or "",
        "is_admin": bool(getattr(user, "is_admin", False)),
        "is_owner": bool(getattr(user, "is_owner", False)),
        "name": getattr(user, "name", "") or "",
        "source_token": str(source_token or ""),
        "issued_at": time.time(),
        "expires_at": time.time() + _AUTH_SESSION_TTL,
        "refresh_token_id": getattr(refresh_token, "id", "") or "",
    }
    return session_token


async def _resolve_user_by_auth_session(hass: HomeAssistant, session_token: str):
    _purge_auth_sessions(hass)
    sessions = _get_auth_sessions(hass)
    info = sessions.get(str(session_token or ""))
    if not isinstance(info, dict):
        return None
    uid = str(info.get("user_id", "") or "")
    if not uid:
        return None
    try:
        return await hass.auth.async_get_user(uid)
    except Exception:
        return None


class SmartAgentDevicePairConfirmView(HomeAssistantView):
    """设备配对确认接口（复用现有授权逻辑）。"""

    url = "/api/v1/device/pair/confirm"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:pair:confirm"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        try:
            body = await request.json()
            if not isinstance(body, dict):
                body = {}
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False),
                status_code=400,
            )

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.post_pair_confirm(body)
                if isinstance(proxied, dict):
                    normalized = _json_from_addon_http_result(proxied)
                    if normalized is not None:
                        payload, status = normalized
                    else:
                        payload, status = _json_from_addon_result(proxied)
                        if "__status" not in proxied:
                            return self.json(_addon_unreachable_payload("pair_confirm"), status_code=502)
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("pair_confirm"), status_code=status)
                    return self.json(payload, status_code=status)
                else:
                    return self.json(_addon_unreachable_payload("pair_confirm"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[PairConfirm] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("pair_confirm"), status_code=502)

        code = str((body or {}).get("code", "") or "").strip()
        if not code:
            return self.json(
                _json_error_payload("missing_code", "bad_request", False),
                status_code=400,
            )

        if coord is None:
            return self.json(
                _json_error_payload("coordinator_not_found", "not_found", False),
                status_code=404,
            )

        pairing_view = getattr(coord, "_pairing_view", None)
        pending_pairs = getattr(pairing_view, "_pending_pairs", None)
        if not isinstance(pending_pairs, dict):
            return self.json(
                _json_error_payload("pairing_service_unavailable", "service_unavailable", True),
                status_code=503,
            )

        pending_id = None
        pending_info = None
        for pid, info in pending_pairs.items():
            if str((info or {}).get("code", "")).strip() == code:
                pending_id = pid
                pending_info = info
                break

        if pending_id is None or not isinstance(pending_info, dict):
            return self.json(
                _json_error_payload("invalid_code", "not_found", False),
                status_code=404,
            )

        claimed_info = pending_pairs.pop(pending_id, None)
        if claimed_info is not pending_info or not isinstance(claimed_info, dict):
            return self.json(
                _json_error_payload("invalid_code", "not_found", False),
                status_code=404,
            )

        if time.time() > float(claimed_info.get("expires", 0) or 0):
            return self.json(
                _json_error_payload("expired_code", "bad_request", False),
                status_code=400,
            )

        pending_info = claimed_info

        try:
            users = await hass.auth.async_get_users()
            owner = next((u for u in users if u.is_owner and u.is_active), None)
            if owner is None:
                return self.json(
                    _json_error_payload("owner_not_found", "internal_error", False),
                    status_code=500,
                )

            client_name = "SmartAgent 中控屏"
            refresh_token = next(
                (t for t in owner.refresh_tokens.values() if t.client_name == client_name),
                None,
            )
            if refresh_token is None:
                refresh_token = await hass.auth.async_create_refresh_token(
                    owner,
                    client_name=client_name,
                    token_type=auth_models.TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
                    access_token_expiration=timedelta(days=3650),
                )

            access_token = hass.auth.async_create_access_token(refresh_token)
        except Exception as ex:
            _LOGGER.error("[配对] /api/v1 配对确认创建 Token 失败: %s", ex, exc_info=True)
            return self.json(
                _json_error_payload("token_issue_failed", "internal_error", False),
                status_code=500,
            )

        pending_info["token"] = access_token
        hass.data[_PAIR_KEY] = {
            "token": access_token,
            "ha_url": f"{request.scheme}://{request.host}",
            "expires_at": time.time() + 60,
        }
        hass.bus.async_fire("smart_agent_pairing_event", {
            "type": "pair_confirmed",
            "code": code,
        })

        return self.json({
            "ok": True,
            "status": "paired",
            "device_id": str(pending_id),
        })

class SmartAgentPairCreateView(HomeAssistantView):
    """极速配对开启接口（管理员调用，强制认证）。

    POST /api/smart_agent/pair/create
    生成长效 Token（10 年），存储 60 秒供平板一次性领取。
    """

    url = "/api/smart_agent/pair/create"
    name = "api:smart_agent:pair:create"
    requires_auth = True  # HA 强制验证，确保 hass_user 一定有值

    async def post(self, request: web.Request) -> web.Response:
        """管理员开启配对，生成长效 Token 存储 60 秒。"""
        if (err := _view_admin_check(request)):
            return err
        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)

        is_addon_proxy = _is_addon_proxy_request(request)
        _addon_client = getattr(coord, "_addon_client", None) if coord is not None else None
        if (not is_addon_proxy) and _addon_client is not None:
            try:
                proxied = await _addon_client.request_json("POST", "/device/pair/create", body={})
                converted = _addon_result_payload_status(proxied)
                if converted is not None:
                    payload, status = converted
                    if status in (404, 405):
                        return self.json(_addon_endpoint_missing_payload("pair_create"), status_code=status)
                    return self.json(payload, status_code=status)
                else:
                    return self.json(_addon_unreachable_payload("pair_create"), status_code=502)
            except Exception as exc:
                _LOGGER.debug("[PairCreate] add-on proxy failed: %s", exc)
                return self.json(_addon_unreachable_payload("pair_create"), status_code=502)

        hass_user = request["hass_user"]

        try:
            from datetime import timedelta

            # 兼容不同 HA 版本：新版有 TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN，旧版没有
            try:
                from homeassistant.auth.const import TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN
                refresh_token = await hass.auth.async_create_refresh_token(
                    hass_user,
                    client_name="SmartAgent 中控屏",
                    token_type=TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
                )
                _LOGGER.debug("[配对] 已创建长效 Token（10 年）")
            except (ImportError, TypeError, Exception) as import_ex:
                # 当前 HA 版本不支持长效 Token 常量或参数，退回 90 天普通 Token
                _LOGGER.warning("[配对] 长效 Token 不可用（%s），退回 90 天 Token", import_ex)
                refresh_token = await hass.auth.async_create_refresh_token(
                    hass_user,
                    client_name="SmartAgent 中控屏",
                    access_token_expiration=timedelta(days=90),
                )

            access_token = hass.auth.async_create_access_token(refresh_token)
        except Exception as ex:
            _LOGGER.error("[配对] 创建 Token 失败: %s", ex, exc_info=True)
            return self.json({"ok": False, "error": str(ex)}, status_code=500)

        origin = f"{request.scheme}://{request.host}"
        hass.data[_PAIR_KEY] = {
            "token": access_token,
            "ha_url": origin,
            "expires_at": time.time() + 60,
        }
        _LOGGER.info("[配对] 极速配对已开启，60 秒内有效，来自用户: %s", hass_user.name)
        return self.json({"ok": True, "expires_in": 60})


PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.TEXT,
    Platform.CONVERSATION,
    Platform.UPDATE,  # Phase 9.7: 版本自动检查实体
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the SmartAgent component."""
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["panel_degraded_mode"] = _HA_PANEL_DEGRADED_MODE

    async def _register_panel(_event=None) -> None:
        frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
        www_dir = os.path.join(os.path.dirname(__file__), "www")

        static_paths: list[StaticPathConfig] = []
        if _HA_PANEL_STATIC_EXPOSED:
            static_paths.append(StaticPathConfig("/smart_agent_static", frontend_dir, cache_headers=False))
        if _HA_SCREEN_STATIC_EXPOSED:
            static_paths.append(StaticPathConfig("/smart_agent_screen", www_dir, cache_headers=True))

        if static_paths:
            try:
                await hass.http.async_register_static_paths(static_paths)
            except Exception as ex:
                _LOGGER.debug("Static path already registered or failed: %s", ex)

        if _HA_PANEL_REGISTER_ENABLED:
            if not _HA_PANEL_STATIC_EXPOSED:
                _LOGGER.warning(
                    "Skip SmartAgent panel registration because SA_HA_PANEL_STATIC_EXPOSED=0",
                )
            else:
                try:
                    await async_register_panel(
                        hass,
                        webcomponent_name="smart-agent-panel",
                        sidebar_title="AI 智能管家",
                        sidebar_icon="mdi:brain",
                        frontend_url_path="smart-agent",
                        module_url="/smart_agent_static/smart-agent-panel.js?v=5.5.2",
                        require_admin=True,
                        config={},
                    )
                    _LOGGER.info("SmartAgent panel registered at /smart-agent")
                except Exception as ex:
                    _LOGGER.error("Panel registration failed: %s", ex)

    if hass.is_running:
        await _register_panel()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_panel)

    if _HA_PANEL_DEGRADED_MODE:
        _LOGGER.warning(
            "SmartAgent panel degraded mode active | panel_register=%s | panel_static=%s | screen_static=%s | /api/v1 chain stays enabled",
            _HA_PANEL_REGISTER_ENABLED,
            _HA_PANEL_STATIC_EXPOSED,
            _HA_SCREEN_STATIC_EXPOSED,
        )
    else:
        _LOGGER.info(
            "SmartAgent panel normal mode active | panel_register=%s | panel_static=%s | screen_static=%s",
            _HA_PANEL_REGISTER_ENABLED,
            _HA_PANEL_STATIC_EXPOSED,
            _HA_SCREEN_STATIC_EXPOSED,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartAgent from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = SmartAgentCoordinator(hass, entry)
    await hass.async_add_executor_job(coordinator._blocking_init)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    register_host_views(hass, globals())

    entry.async_create_background_task(
        hass, coordinator.async_start_listeners(), "smart_agent_listeners"
    )

    # ── 注册 HA 服务 ──────────────────────────────────────────────

    async def _check_admin(call: ServiceCall) -> bool:
        """P1修复：校验服务调用者是否为管理员，非管理员记录警告并返回 False。
        系统调用（user_id=None）视为受信任，始终放行。"""
        uid = call.context.user_id
        if uid is None:
            return True
        user = await hass.auth.async_get_user(uid)
        if user is None or not user.is_admin:
            _LOGGER.warning(
                "[Auth] SmartAgent 服务 '%s' 被非管理员调用拒绝（user=%s）",
                call.service,
                user.name if user else uid,
            )
            return False
        return True

    async def svc_discover(call: ServiceCall) -> None:
        await coordinator._async_discover_devices()

    async def svc_sync_rooms_to_ha(call: ServiceCall) -> None:
        """将 SmartAgent 的房间信息同步到 HA Area Registry。"""
        await coordinator.async_sync_rooms_to_ha()

    async def svc_save_room_topology(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        body = {"topology": call.data.get("topology") or []}
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log("WARN", "[Topology] add-on topology provider unavailable: save_room_topology")
            return
        try:
            normalized = await _save_rooms_topology_via_addon(_addon_client, body)
        except Exception as exc:
            coordinator._sys_log("WARN", f"[Topology] add-on topology save failed: {exc}")
            return
        if normalized is None:
            coordinator._sys_log("WARN", "[Topology] add-on topology provider unavailable: save_room_topology")
            return
        payload, status = normalized
        if status >= 400 or payload.get("ok") is False:
            error = payload.get("error") or payload.get("error_type") or f"http_{status}"
            coordinator._sys_log("WARN", f"[Topology] add-on topology save rejected: {error}")
            return
        await _refresh_coord_room_topology_cache(coordinator)
        coordinator.async_set_updated_data({})

    async def svc_batch_add(call: ServiceCall) -> None:
        raw = call.data.get("entities", "")
        entity_ids = [e.strip() for e in raw.split(",") if e.strip()]
        await coordinator.async_batch_add_devices(entity_ids)

    async def svc_add_device(call: ServiceCall) -> None:
        await coordinator.async_svc_add_device(
            call.data["entity_id"], call.data["description"]
        )

    async def svc_delete_device(call: ServiceCall) -> None:
        await coordinator.async_svc_delete_device(call.data["entity_id"])

    async def svc_update_device(call: ServiceCall) -> None:
        await coordinator.async_svc_update_device(
            call.data["entity_id"],
            name=call.data.get("name", ""),
            room=call.data.get("room", ""),
            dev_type=call.data.get("type", ""),
            ops=call.data.get("ops", ""),
        )

    async def svc_add_habit(call: ServiceCall) -> None:
        await coordinator.async_svc_add_habit(call.data["content"])

    async def svc_delete_habit(call: ServiceCall) -> None:
        await coordinator.async_svc_delete_habit(call.data["content"])

    async def svc_toggle_habit_lock(call: ServiceCall) -> None:
        await coordinator.async_svc_toggle_habit_lock(call.data["content"])

    async def svc_add_rule(call: ServiceCall) -> None:
        await coordinator.async_svc_add_rule(call.data["content"])

    async def svc_delete_rule(call: ServiceCall) -> None:
        await coordinator.async_svc_delete_rule(call.data["content"])

    async def svc_toggle_rule_lock(call: ServiceCall) -> None:
        await coordinator.async_svc_toggle_rule_lock(call.data["content"])

    async def svc_manual_inference(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        trigger = call.data.get("trigger", "手动测试触发")
        await coordinator.async_manual_inference(trigger)

    async def svc_clear_overrides(call: ServiceCall) -> None:
        await coordinator.async_clear_overrides()

    async def svc_delete_behavior_pattern(call: ServiceCall) -> None:
        pattern_id = call.data.get("id")
        if pattern_id is not None:
            await coordinator.async_delete_behavior_pattern(int(pattern_id))

    async def svc_set_mode(call: ServiceCall) -> None:
        mode = call.data.get("mode", "home")
        if mode not in (MODE_HOME, MODE_SHOWROOM):
            mode = MODE_HOME
        await coordinator.async_set_mode(mode)

    async def svc_set_showroom_scene(call: ServiceCall) -> None:
        scene = call.data.get("scene") or None
        if scene == "":
            scene = None
        custom_prompt = call.data.get("custom_prompt", "").strip()
        is_command = bool(call.data.get("is_command", False))
        await coordinator.async_set_showroom_scene(
            scene_key=scene, custom_prompt=custom_prompt, is_command=is_command
        )


    # ── Phase 4: AI 场景管理服务 ──────────────────────────────────────────────
    async def _proxy_ai_scene_lifecycle(action: str, scene_id: int) -> None:
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log("WARN", "[AI场景] add-on lifecycle provider unavailable")
            return

        try:
            if action == "approve":
                result = await _addon_client.post_ai_scene_action("approve", scene_id)
            elif action == "reject":
                result = await _addon_client.post_ai_scene_action("reject", scene_id)
            elif action == "delete":
                result = await _addon_client.post_ai_scene_delete_fallback(scene_id)
            elif action == "trigger":
                result = await _addon_client.trigger_ai_scene(scene_id)
            else:
                coordinator._sys_log("WARN", f"[AI场景] 不支持的 lifecycle action: {action}")
                return
        except Exception as exc:
            coordinator._sys_log("WARN", f"[AI场景] add-on lifecycle provider 调用失败: {exc}")
            return

        if not isinstance(result, dict):
            coordinator._sys_log("WARN", "[AI场景] add-on lifecycle provider unavailable")
            return
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_type") or f"http_{status}"
            coordinator._sys_log("WARN", f"[AI场景] add-on lifecycle provider 返回失败: {action} id={scene_id} error={error}")
            return

        coordinator._sys_log("INFO", f"[AI场景] lifecycle 已交由 add-on provider: {action} id={scene_id}")
        coordinator.async_set_updated_data({})

    async def svc_approve_ai_scene(call: ServiceCall) -> None:
        scene_id = int(call.data["id"])
        await _proxy_ai_scene_lifecycle("approve", scene_id)

    async def svc_reject_ai_scene(call: ServiceCall) -> None:
        scene_id = int(call.data["id"])
        await _proxy_ai_scene_lifecycle("reject", scene_id)

    async def svc_delete_ai_scene(call: ServiceCall) -> None:
        scene_id = int(call.data["id"])
        await _proxy_ai_scene_lifecycle("delete", scene_id)

    async def svc_trigger_ai_scene(call: ServiceCall) -> None:
        scene_id = int(call.data["id"])
        await _proxy_ai_scene_lifecycle("trigger", scene_id)

    _ai_scene_schema = vol.Schema({vol.Required("id"): vol.Coerce(int)})

    # ── 一句话生成场景 ─────────────────────────────────────────────────────────
    async def svc_create_scene_from_text(call: ServiceCall) -> None:
        """用自然语言描述直接创建 AI 场景。

        参数：
          text (str, 必填)：场景描述，如"下午 2 点到 6 点，工作日，打开客厅灯 80%"
          auto_activate (bool, 可选, 默认 False)：是否跳过审批直接激活
        """
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log("WARN", "[AI场景] add-on ops provider unavailable: create-from-text")
            return
        body = {
            "text": call.data["text"],
            "auto_activate": bool(call.data.get("auto_activate", False)),
        }
        result = await _addon_client.post_ai_scene_ops("ai-scenes/create-from-text", body)
        if not isinstance(result, dict):
            coordinator._sys_log("WARN", "[AI场景] add-on ops provider unavailable: create-from-text")
            return
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_type") or f"http_{status}"
            coordinator._sys_log("WARN", f"[AI场景] add-on create-from-text failed: {error}")
            return
        coordinator.hass.bus.async_fire(
            "smart_agent_scene_created",
            {"success": result.get("success"), "scene_id": result.get("scene_id"),
             "name": result.get("name"), "status": result.get("status"),
             "error": result.get("error", "")},
        )

    _create_scene_schema = vol.Schema({
        vol.Required("text"): str,
        vol.Optional("auto_activate", default=False): bool,
    })

    # ── Layer 2: 事务管理服务 ──────────────────────────────────────────────────
    async def svc_rollback_transaction(call: ServiceCall) -> None:
        """回滚指定事务：将目标设备恢复到执行前的状态快照。"""
        if not await _check_admin(call):
            return
        await coordinator.async_rollback_transaction(int(call.data["id"]))

    async def svc_refresh_transactions(call: ServiceCall) -> None:
        """刷新事务缓存（强制重新从 DB 加载近期记录）。"""
        coordinator._transactions_cache = await hass.async_add_executor_job(
            coordinator._query_recent_transactions, 30
        )
        coordinator.async_set_updated_data({})

    _txn_schema = vol.Schema({vol.Required("id"): vol.Coerce(int)})

    async def svc_set_device_control_mode(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        mode = call.data["mode"]
        await coordinator.async_set_device_control_mode(entity_id, mode)

    async def svc_batch_set_control_mode(call: ServiceCall) -> None:
        mode = call.data["mode"]
        room = call.data.get("room", "")
        dev_type = call.data.get("type", "")
        await coordinator.async_batch_set_control_mode(mode, room=room, dev_type=dev_type)

    async def svc_update_showroom_scene_config(call: ServiceCall) -> None:
        scene_key = call.data.get("scene_key", "")
        await coordinator.async_update_showroom_scene_config(
            scene_key=scene_key,
            label=call.data.get("label") or None,
            virtual_time=call.data.get("virtual_time") or None,
            scene_desc=call.data.get("scene_desc") or None,
            hint=call.data.get("hint") or None,
        )

    async def svc_update_config(call: ServiceCall) -> None:
        """前端设置面板保存通用配置，持久化到 config entry options。"""
        if not await _check_admin(call):
            return
        from .const import (
            CONF_TTS_SERVICE, CONF_TTS_TARGET, CONF_TTS_LEVEL,
            CONF_ENGINE, CONF_OLLAMA_URL, CONF_OLLAMA_MODEL,
            CONF_ONLINE_API_KEY, CONF_ONLINE_BASE_URL, CONF_ONLINE_MODEL,
            CONF_CONFIDENCE_AUTO, CONF_CONFIDENCE_NOTIFY, CONF_COOLDOWN,
            CONF_SHOWROOM_BIZ_START, CONF_SHOWROOM_BIZ_END,
            CONF_SHOWROOM_AREA_NAME, CONF_SHOWROOM_EXCLUDED_SUBAREAS,
            CONF_SHOWROOM_ZONE_MAP,
            CONF_FRIGATE_ENABLED, CONF_QWEATHER_API_KEY, CONF_SEARXNG_URL,
            CONF_CLOUD_FALLBACK, CONF_VISION_ENABLED, CONF_VISION_ENGINE,
            CONF_VISION_MODEL,
            CONF_BRAND_NAME, CONF_BRAND_PRIMARY_COLOR, CONF_BRAND_LOGO_URL, CONF_DEPLOY_NAME,
            CONF_LICENSE_KEY, CONF_LOG_RETENTION,
            CONF_PRESENCE_FUSION,
            CONF_CIRCADIAN_ENABLED, CONF_CIRCADIAN_WAKE_TIME,
            CONF_CIRCADIAN_SLEEP_TIME, CONF_CIRCADIAN_MAX_BRIGHTNESS,
            CONF_CIRCADIAN_AUTO_ADJUST,
        )
        opts = dict(entry.options or {})
        
        # 定义所有可能的配置键及其转换函数
        conf_map = {
            "tts_service": (CONF_TTS_SERVICE, str),
            "tts_target": (CONF_TTS_TARGET, str),
            "tts_level": (CONF_TTS_LEVEL, int),
            "engine": (CONF_ENGINE, str),
            "ollama_url": (CONF_OLLAMA_URL, str),
            "ollama_model": (CONF_OLLAMA_MODEL, str),
            "online_api_key": (CONF_ONLINE_API_KEY, str),
            "online_base_url": (CONF_ONLINE_BASE_URL, str),
            "online_model": (CONF_ONLINE_MODEL, str),
            "confidence_auto": (CONF_CONFIDENCE_AUTO, int),
            "confidence_notify": (CONF_CONFIDENCE_NOTIFY, int),
            "cooldown": (CONF_COOLDOWN, int),
            "showroom_biz_start": (CONF_SHOWROOM_BIZ_START, int),
            "showroom_biz_end": (CONF_SHOWROOM_BIZ_END, int),
            "showroom_area_name": (CONF_SHOWROOM_AREA_NAME, str),
            "showroom_excluded_subareas": (CONF_SHOWROOM_EXCLUDED_SUBAREAS, str),
            "showroom_zone_map": (CONF_SHOWROOM_ZONE_MAP, str),
            "frigate_enabled": (CONF_FRIGATE_ENABLED, bool),
            "qweather_api_key": (CONF_QWEATHER_API_KEY, str),
            "searxng_url": (CONF_SEARXNG_URL, str),
            "cloud_fallback": (CONF_CLOUD_FALLBACK, bool),
            "vision_enabled": (CONF_VISION_ENABLED, bool),
            "vision_engine": (CONF_VISION_ENGINE, str),
            "vision_model": (CONF_VISION_MODEL, str),
            "license_key": (CONF_LICENSE_KEY, str),
            "log_retention_days": (CONF_LOG_RETENTION, int),
            "mcp_enabled": ("mcp_enabled", bool),
            # 品牌化/白标
            "brand_name": (CONF_BRAND_NAME, str),
            "brand_primary_color": (CONF_BRAND_PRIMARY_COLOR, str),
            "brand_logo_url": (CONF_BRAND_LOGO_URL, str),
            "deploy_name": (CONF_DEPLOY_NAME, str),
            # 存在传感器融合域（Phase 12.0）
            "presence_fusion": (CONF_PRESENCE_FUSION, str),
            # 昼夜节律引擎（Phase 13）
            "circadian_enabled": (CONF_CIRCADIAN_ENABLED, bool),
            "circadian_wake_time": (CONF_CIRCADIAN_WAKE_TIME, str),
            "circadian_sleep_time": (CONF_CIRCADIAN_SLEEP_TIME, str),
            "circadian_max_brightness": (CONF_CIRCADIAN_MAX_BRIGHTNESS, int),
            "circadian_auto_adjust": (CONF_CIRCADIAN_AUTO_ADJUST, bool),
        }

        import re as _re
        import json as _json
        # HH:MM 严格校验：小时 00-23，分钟 00-59
        _TIME_RE = _re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        _TIME_KEYS = {"circadian_wake_time", "circadian_sleep_time"}
        # 需要合法 JSON 数组或对象的字段，写入前校验
        _JSON_ARRAY_KEYS = {"presence_fusion"}
        _JSON_OBJ_KEYS   = {"showroom_zone_map"}

        any_changed = False
        for key, (conf_key, transform) in conf_map.items():
            if key in call.data:
                val = call.data[key]
                if transform == int:
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        continue
                elif transform == bool:
                    # bool("false") == True，需要专门处理字符串布尔值
                    if isinstance(val, str):
                        val = val.strip().lower() not in ("false", "0", "no", "off", "")
                    else:
                        val = bool(val)
                elif key in _TIME_KEYS:
                    # HH:MM 严格格式校验，范围外值（如 99:99）跳过
                    if not _TIME_RE.match(str(val)):
                        _LOGGER.warning(
                            "[Config] %s 格式错误（应为 HH:MM，小时00-23分钟00-59）: %s，已忽略",
                            key, val
                        )
                        continue
                elif key in _JSON_ARRAY_KEYS:
                    # P2修复：写入前验证为合法 JSON 数组，防止无效值存入配置导致运行时崩溃
                    if val and isinstance(val, str):
                        try:
                            _parsed = _json.loads(val)
                            if not isinstance(_parsed, list):
                                raise ValueError("非数组")
                        except (ValueError, TypeError) as _je:
                            _LOGGER.warning("[Config] %s 不是合法 JSON 数组: %s，已忽略", key, _je)
                            continue
                elif key in _JSON_OBJ_KEYS:
                    # P2修复：写入前验证为合法 JSON 对象
                    if val and isinstance(val, str):
                        try:
                            _parsed = _json.loads(val)
                            if not isinstance(_parsed, dict):
                                raise ValueError("非对象")
                        except (ValueError, TypeError) as _je:
                            _LOGGER.warning("[Config] %s 不是合法 JSON 对象: %s，已忽略", key, _je)
                            continue

                if opts.get(conf_key) != val:
                    # 密码型字段保护：前端回显使用掩码（如 **** / sk-xx****yy），
                    # 空值或掩码值不应覆盖已保存的真实密钥。
                    if conf_key in (CONF_ONLINE_API_KEY, CONF_QWEATHER_API_KEY, CONF_LICENSE_KEY):
                        if not str(val or "").strip() or "****" in str(val):
                            continue
                    opts[conf_key] = val
                    # 同步更新 coordinator 内存中的值（JSON 字段保持运行态结构类型）
                    sync_val = val
                    if key in _JSON_OBJ_KEYS and isinstance(val, str):
                        try:
                            _obj = _json.loads(val) if val else {}
                            sync_val = _obj if isinstance(_obj, dict) else {}
                        except (ValueError, TypeError):
                            sync_val = {}
                    attr_name = f"_{key}" if hasattr(coordinator, f"_{key}") else key
                    if hasattr(coordinator, attr_name):
                        setattr(coordinator, attr_name, sync_val)
                    elif hasattr(coordinator, key):
                        setattr(coordinator, key, sync_val)
                    any_changed = True

        if any_changed:
            # Phase 13: 热更新昼夜节律引擎配置
            _ce = getattr(coordinator, "_circadian_engine", None)
            if _ce is not None:
                _ce.update_config(
                    wake_time=opts.get(CONF_CIRCADIAN_WAKE_TIME),
                    sleep_time=opts.get(CONF_CIRCADIAN_SLEEP_TIME),
                    max_brightness=opts.get(CONF_CIRCADIAN_MAX_BRIGHTNESS),
                    enabled=opts.get(CONF_CIRCADIAN_ENABLED),
                )
                coordinator._circadian_auto_adjust = opts.get(CONF_CIRCADIAN_AUTO_ADJUST, False)

            coordinator._skip_next_reload = True
            hass.config_entries.async_update_entry(entry, options=opts)
            coordinator.async_set_updated_data(coordinator.get_config_attributes())
            coordinator._sys_log("INFO", "[配置] 系统参数已更新")


    async def svc_tts_test(call: ServiceCall) -> None:
        """发送一条测试 TTS 播报，验证 TTS 配置是否正确。"""
        await coordinator._tts_speak("SmartAgent TTS 测试，语音播报正常。", min_level=0)

    async def svc_voice_command(call: ServiceCall) -> None:
        """处理来自中控屏的语音文本指令"""
        command = call.data.get("command", "")
        source = call.data.get("source", "touch")
        await coordinator._run_voice_inference(command, source=source)


    async def svc_run_pattern_analysis(_call: ServiceCall) -> None:
        """触发行为规律分析与 AI 场景生成（async 处理器，事件循环内直接 await）。"""
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log("WARN", "[AI场景] add-on ops provider unavailable: analyze")
            return
        result = await _addon_client.post_ai_scene_ops("ai-scenes/analyze", {})
        if not isinstance(result, dict):
            coordinator._sys_log("WARN", "[AI场景] add-on ops provider unavailable: analyze")
            return
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_type") or f"http_{status}"
            coordinator._sys_log("WARN", f"[AI场景] add-on analyze failed: {error}")
            return
        coordinator.async_set_updated_data({})

    register_smart_agent_services(
        hass,
        (
            ServiceRegistration("discover_devices", svc_discover),
            ServiceRegistration("sync_rooms_to_ha", svc_sync_rooms_to_ha, vol.Schema({})),
            ServiceRegistration(
                "save_room_topology",
                svc_save_room_topology,
                vol.Schema({vol.Required("topology"): list}),
            ),
            ServiceRegistration(
                "batch_add_devices",
                svc_batch_add,
                vol.Schema({vol.Required("entities"): cv.string}),
            ),
            ServiceRegistration(
                "add_device",
                svc_add_device,
                vol.Schema({
                    vol.Required("entity_id"): cv.string,
                    vol.Required("description"): cv.string,
                }),
            ),
            ServiceRegistration(
                "delete_device",
                svc_delete_device,
                vol.Schema({vol.Required("entity_id"): cv.string}),
            ),
            ServiceRegistration(
                "update_device",
                svc_update_device,
                vol.Schema({
                    vol.Required("entity_id"): cv.string,
                    vol.Optional("name"): cv.string,
                    vol.Optional("room"): cv.string,
                    vol.Optional("type"): cv.string,
                    vol.Optional("ops"): cv.string,
                }),
            ),
            ServiceRegistration(
                "add_habit",
                svc_add_habit,
                vol.Schema({vol.Required("content"): cv.string}),
            ),
            ServiceRegistration(
                "delete_habit",
                svc_delete_habit,
                vol.Schema({vol.Required("index"): vol.Coerce(int)}),
            ),
            ServiceRegistration(
                "toggle_habit_lock",
                svc_toggle_habit_lock,
                vol.Schema({vol.Required("index"): vol.Coerce(int)}),
            ),
            ServiceRegistration(
                "add_rule",
                svc_add_rule,
                vol.Schema({vol.Required("content"): cv.string}),
            ),
            ServiceRegistration(
                "delete_rule",
                svc_delete_rule,
                vol.Schema({vol.Required("index"): vol.Coerce(int)}),
            ),
            ServiceRegistration(
                "toggle_rule_lock",
                svc_toggle_rule_lock,
                vol.Schema({vol.Required("index"): vol.Coerce(int)}),
            ),
            ServiceRegistration(
                "manual_inference",
                svc_manual_inference,
                vol.Schema({vol.Optional("trigger", default="鎵嬪姩娴嬭瘯瑙﹀彂"): cv.string}),
            ),
            ServiceRegistration("clear_overrides", svc_clear_overrides, vol.Schema({})),
            ServiceRegistration(
                "delete_behavior_pattern",
                svc_delete_behavior_pattern,
                vol.Schema({vol.Required("id"): vol.Coerce(int)}),
            ),
            ServiceRegistration(
                "set_mode",
                svc_set_mode,
                vol.Schema({vol.Required("mode"): vol.In([MODE_HOME, MODE_SHOWROOM])}),
            ),
            ServiceRegistration(
                "set_showroom_scene",
                svc_set_showroom_scene,
                vol.Schema({
                    vol.Optional("scene", default=""): cv.string,
                    vol.Optional("custom_prompt", default=""): cv.string,
                    vol.Optional("is_command", default=False): cv.boolean,
                }),
            ),
            ServiceRegistration("approve_ai_scene", svc_approve_ai_scene, _ai_scene_schema),
            ServiceRegistration("reject_ai_scene", svc_reject_ai_scene, _ai_scene_schema),
            ServiceRegistration("delete_ai_scene", svc_delete_ai_scene, _ai_scene_schema),
            ServiceRegistration("trigger_ai_scene", svc_trigger_ai_scene, _ai_scene_schema),
            ServiceRegistration("create_scene_from_text", svc_create_scene_from_text, _create_scene_schema),
            ServiceRegistration("rollback_transaction", svc_rollback_transaction, _txn_schema),
            ServiceRegistration("refresh_transactions", svc_refresh_transactions, vol.Schema({})),
            ServiceRegistration(
                "set_device_control_mode",
                svc_set_device_control_mode,
                vol.Schema({
                    vol.Required("entity_id"): cv.string,
                    vol.Required("mode"): vol.In(["ai", "ha", "shared"]),
                }),
            ),
            ServiceRegistration(
                "batch_set_control_mode",
                svc_batch_set_control_mode,
                vol.Schema({
                    vol.Required("mode"): vol.In(["ai", "ha", "shared"]),
                    vol.Optional("room", default=""): cv.string,
                    vol.Optional("type", default=""): cv.string,
                }),
            ),
            ServiceRegistration(
                "update_showroom_scene_config",
                svc_update_showroom_scene_config,
                vol.Schema({
                    vol.Required("scene_key"): cv.string,
                    vol.Optional("label"): cv.string,
                    vol.Optional("virtual_time"): cv.string,
                    vol.Optional("scene_desc"): cv.string,
                    vol.Optional("hint"): cv.string,
                }),
            ),
            ServiceRegistration("update_config", svc_update_config),
            ServiceRegistration("tts_test", svc_tts_test, vol.Schema({})),
            ServiceRegistration("run_pattern_analysis", svc_run_pattern_analysis, vol.Schema({})),
            ServiceRegistration(
                "verify_license",
                coordinator.async_svc_verify_license,
                vol.Schema({vol.Optional("license_key", default=""): cv.string}),
            ),
            ServiceRegistration(
                "voice_command",
                svc_voice_command,
                vol.Schema({
                    vol.Required("command"): cv.string,
                    vol.Optional("source", default="touch"): cv.string,
                }),
            ),
        ),
    )


    # ── WebSocket API：大数据列表通过 WS 按需下发，绕过 sensor 属性 16KB 上限 ──
    register_smart_agent_websocket_commands(
        hass,
        build_smart_agent_websocket_commands(
            _normalize_addon_diagnostics=_normalize_addon_diagnostics,
            _build_presence_sensors_payload=_build_presence_sensors_payload,
            _async_save_presence_sensor_type=_async_save_presence_sensor_type,
        ),
    )

    # ── 选项变更时自动重载集成（API Key / 模型 / 引擎等全部生效）──
    entry.async_on_unload(
        entry.add_update_listener(_async_reload_on_options_update)
    )

    _LOGGER.info(
        "SmartAgent initialized | engine=%s | grace_period=%ss",
        coordinator.engine,
        coordinator._startup_grace,
    )
    return True


async def _async_reload_on_options_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """选项流保存后重载集成，使新 API Key / 模型 / 引擎立即生效。
    但排除运行时状态持久化（模式切换/展厅场景设置）引起的 options 更新，
    这些只是将内存状态写入 config entry 以便重启恢复，不需要重载。
    """
    coordinator: SmartAgentCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator and getattr(coordinator, "_skip_next_reload", False):
        coordinator._skip_next_reload = False
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SmartAgentCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    # 只有在 domain 数据为空时才移除服务（多实例场景下其他实例仍在运行）
    if not hass.data.get(DOMAIN):
        remove_smart_agent_services(hass)
        try:
            async_remove_panel(hass, "smart-agent")
        except Exception:
            pass
    return unload_ok
