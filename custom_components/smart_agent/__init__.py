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
from homeassistant.helpers import entity_registry
from homeassistant.helpers import config_validation as cv

from .const import CONF_CLEANUP_LEGACY_PAIR_TOKENS, DOMAIN, MODE_HOME, MODE_SHOWROOM
from .coordinator import SmartAgentCoordinator
from .host_read_models import (
    build_presence_sensors_payload as _build_presence_sensors_payload,
    local_device_rows as _local_device_rows,
    local_room_rows as _local_room_rows,
)
from .ha_adapter import (
    async_call_service,
    async_delete_ha_area,
    async_ensure_ha_area,
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

def _env_flag(name: str, default: bool = True) -> bool:
    raw = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return bool(default)


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


_TRUSTED_ADDON_PROXY_PEERS = {"127.0.0.1", "::1", "localhost", "172.30.33.1"}
_TRUSTED_ADDON_PROXY_PEER_PREFIXES = ("127.", "172.30.32.", "172.30.33.")
_LEGACY_PAIR_TOKEN_CLIENT_NAMES = {
    "SmartAgent 中控屏",
    "SmartAgent 管理端会话",
    "SmartAgent 中控屏（极速配对）",
}


def _is_addon_proxy_request(request: web.Request) -> bool:
    if str(request.headers.get("X-SA-Proxy-From", "") or "").strip().lower() != "addon":
        return False

    transport = getattr(request, "transport", None)
    try:
        peer = transport.get_extra_info("peername") if transport is not None else None
    except Exception:
        peer = None
    log_debug = getattr(_LOGGER, "debug", lambda *args, **kwargs: None)
    log_info = getattr(_LOGGER, "info", log_debug)
    log_warning = getattr(_LOGGER, "warning", log_debug)
    if not peer:
        log_warning("[Auth] proxied request peername=%s trusted=False", peer)
        return False

    peer_host = str(peer[0]) if isinstance(peer, (tuple, list)) and peer else str(peer)
    trusted_peers = globals().get("_TRUSTED_ADDON_PROXY_PEERS", {"127.0.0.1", "::1", "localhost"})
    trusted_prefixes = globals().get("_TRUSTED_ADDON_PROXY_PEER_PREFIXES", ("127.", "172.30.32."))
    trusted = peer_host in trusted_peers or any(peer_host.startswith(prefix) for prefix in trusted_prefixes)
    log_info("[Auth] proxied request peername=%s trusted=%s", peer, trusted)
    if not trusted:
        log_warning("[Auth] rejected forged add-on proxy header from peername=%s", peer)
    return trusted


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


def _ha_log_query_flag(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _ha_log_content_window(content: str, query: Any) -> tuple[str, dict[str, Any]]:
    q = query if hasattr(query, "get") else {}
    full_day = (
        _ha_log_query_flag(q.get("full_day"))
        or _ha_log_query_flag(q.get("all_day"))
        or str(q.get("scope") or "").strip().lower() in {"day", "full_day", "all_day"}
    )
    level = str(q.get("level") or "all").strip().lower()
    if level not in {"all", "error", "warning", "info"}:
        level = "all"
    keyword = str(q.get("keyword") or "").strip()
    keyword_lower = keyword.lower()
    max_bytes = _ha_log_window_int(
        q.get("max_bytes"),
        default=16 * 1024 * 1024 if full_day else 128 * 1024,
        minimum=1,
        maximum=16 * 1024 * 1024 if full_day else 512 * 1024,
    )
    tail_lines = _ha_log_window_int(
        q.get("tail_lines"),
        default=200000 if full_day else 800,
        minimum=1,
        maximum=200000 if full_day else 3000,
    )

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
        or full_day
        or "max_bytes" in q
        or "tail_lines" in q
    )
    window = {
        "active": active,
        "level": level,
        "keyword": keyword,
        "max_bytes": max_bytes,
        "tail_lines": tail_lines,
        "full_day": full_day,
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
    if _is_auth_token_revoked(hass, token):
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


async def _resolve_request_user(request: web.Request, *, allow_query_token: bool = False):
    """解析请求用户：优先 HA 会话，其次会话 token，再回退 HA token。"""
    user = request.get("hass_user")
    if user is not None:
        return user

    token = _extract_bearer_token(request)
    if not token and allow_query_token:
        token = str(request.query.get("token", "") or "").strip()
    if not token:
        return None

    hass = request.app["hass"]
    session_user = await _resolve_user_by_auth_session(hass, token)
    if session_user is not None:
        return session_user
    return await _resolve_user_from_token(hass, token)









_LOGGER = logging.getLogger(__name__)


def _get_first_coordinator(hass: HomeAssistant) -> SmartAgentCoordinator | None:
    """获取当前集成实例（单实例部署取第一个）。"""
    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, SmartAgentCoordinator):
            return value
    return None

































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

        if session_token:
            sessions = _get_auth_sessions(hass)
            if session_token in sessions:
                session_info = sessions.pop(session_token, None)
                await _async_revoke_auth_session_token(hass, session_token, session_info)
                return self.json({"ok": True})

        user = await _resolve_request_user(request, allow_query_token=True)
        if user is None:
            return self.json(
                _json_error_payload("unauthorized", "auth_failed", False),
                status_code=401,
            )
        if session_token:
            _mark_auth_token_revoked(hass, session_token)
        return self.json({"ok": True})



class SmartAgentEventsWSView(HomeAssistantView):
    """最小可用事件流端点（迁移期）。"""

    url = "/api/v1/events"
    name = "api:smart_agent:v1:events"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        hass = request.app["hass"]

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
        managed_event_entity_ids: set[str] = set()
        managed_event_entity_ids_updated_at = 0.0

        def _refresh_managed_event_entity_ids() -> set[str]:
            nonlocal managed_event_entity_ids, managed_event_entity_ids_updated_at
            now_monotonic = time.monotonic()
            if managed_event_entity_ids_updated_at and now_monotonic - managed_event_entity_ids_updated_at < 5:
                return managed_event_entity_ids

            coord = _get_first_coordinator(hass)
            next_ids: set[str] = set()
            if coord is not None:
                for row in _local_device_rows(coord, hass):
                    if not isinstance(row, dict):
                        continue
                    entity_id = str(row.get("entity_id") or "").strip()
                    if not entity_id:
                        continue
                    if row.get("managed") is False or row.get("in_sa") is False:
                        continue
                    next_ids.add(entity_id)

            managed_event_entity_ids = next_ids
            managed_event_entity_ids_updated_at = now_monotonic
            return managed_event_entity_ids

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
                managed_event_entity_ids = _refresh_managed_event_entity_ids()
                if entity_id not in managed_event_entity_ids:
                    return
                event_data = {
                    "entity_id": entity_id,
                    "old_state": old_state,
                    "new_state": new_state,
                }
            elif evt_type == "smart_agent_listener_event":
                listener_entity_id = str(event_data.get("entity_id") or "")
                listener_filter_reason = str(event_data.get("filter_reason") or "")
                managed_event_entity_ids = _refresh_managed_event_entity_ids()
                if (
                    listener_entity_id
                    and listener_entity_id not in managed_event_entity_ids
                    and listener_filter_reason != "unmanaged_entity"
                ):
                    return
                event_data = {
                    "listener_action": str(event_data.get("listener_action") or ""),
                    "entity_id": listener_entity_id,
                    "old_state": str(event_data.get("old_state") or ""),
                    "new_state": str(event_data.get("new_state") or ""),
                    "filter_reason": listener_filter_reason,
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










































class SmartAgentListenerDiagnosticsView(HomeAssistantView):
    """Expose HA listener subscription state for SmartAgent UI diagnostics."""

    url = "/api/v1/listener/diagnostics"
    name = "api:smart_agent:v1:listener:diagnostics"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        hass = request.app["hass"]
        coord = _get_first_coordinator(hass)
        if coord is None:
            return self.json(
                _json_error_payload("coordinator_unavailable", "dependency_unavailable", True),
                status_code=503,
            )

        def _sorted_str_list(value: Any) -> list[str]:
            if value is None:
                return []
            if isinstance(value, dict):
                items = value.keys()
            elif isinstance(value, (set, list, tuple)):
                items = value
            else:
                items = []
            return sorted({str(item).strip() for item in items if str(item or "").strip()})

        device_info = getattr(coord, "device_info", {}) or {}
        managed_entity_ids = _sorted_str_list(device_info)
        if not managed_entity_ids:
            managed_getter = getattr(coord, "_managed_listener_entity_ids", None)
            if callable(managed_getter):
                managed_entity_ids = _sorted_str_list(managed_getter())

        listener_entity_ids = _sorted_str_list(getattr(coord, "_listener_entity_ids", set()) or set())
        unmanaged_warned_entity_ids = _sorted_str_list(
            getattr(coord, "_unmanaged_listener_entity_warned", set()) or set()
        )
        last_listener_event_raw = getattr(coord, "_last_listener_event", {}) or {}
        last_listener_event = dict(last_listener_event_raw) if isinstance(last_listener_event_raw, dict) else {}
        last_listener_filter_reason = str(
            last_listener_event.get("filter_reason")
            or getattr(coord, "_last_listener_filter_reason", "")
            or ""
        )

        managed_set = set(managed_entity_ids)
        listener_set = set(listener_entity_ids)

        is_enabled = getattr(coord, "_is_enabled", None)
        enabled = bool(is_enabled()) if callable(is_enabled) else bool(getattr(coord, "_enabled", False))

        return self.json(
            {
                "ok": True,
                "source": "ha_listener_runtime",
                "enabled": enabled,
                "sensors_muted": bool(getattr(coord, "_sensors_muted", False)),
                "mode": str(getattr(coord, "_mode", "") or ""),
                "device_info_count": len(managed_entity_ids),
                "subscribed_entity_count": len(listener_entity_ids),
                "managed_entity_ids": managed_entity_ids,
                "listener_entity_ids": listener_entity_ids,
                "missing_listener_entity_ids": sorted(managed_set - listener_set),
                "extra_listener_entity_ids": sorted(listener_set - managed_set),
                "unmanaged_warned_entity_ids": unmanaged_warned_entity_ids,
                "last_listener_event": last_listener_event,
                "last_listener_filter_reason": last_listener_filter_reason,
                "state_listener_active": bool(getattr(coord, "_state_listener_removers", []) or []),
                "periodic_refresh_active": bool(getattr(coord, "_listener_removers", []) or []),
            }
        )


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
                    "forbidden",
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


class SmartAgentRoomsView(HomeAssistantView):
    """Area Registry Bridge（主计划 P4.2 例外）：只做 HA Area 读写，不承载房间业务语义。"""

    url = "/api/v1/rooms"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:rooms"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        coord = _get_first_coordinator(request.app["hass"])
        return self.json(_local_room_rows(coord, request.app["hass"]))

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        try:
            body = await request.json()
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False, scope="rooms_create"),
                status_code=400,
            )
        if not isinstance(body, dict):
            return self.json(
                _json_error_payload("invalid_body", "bad_request", False, scope="rooms_create"),
                status_code=400,
            )

        name = str(body.get("name") or body.get("room") or body.get("id") or "").strip()
        area_id = str(body.get("area_id") or body.get("id") or "").strip()
        result = await async_ensure_ha_area(request.app["hass"], name=name, area_id=area_id)
        if not bool(result.get("ok")):
            error_type = str(result.get("error_type") or "internal_error")
            status_code = 400 if error_type == "bad_request" else 500
            return self.json(dict(result, scope="rooms_create"), status_code=status_code)
        return self.json(result, status_code=200)


class SmartAgentRoomsSyncView(HomeAssistantView):
    """Area Registry Bridge（主计划 P4.2 例外）：供 add-on 同步 HA Area，不承载业务字段。"""

    url = "/api/v1/rooms/sync"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:rooms:sync"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        coord = _get_first_coordinator(request.app["hass"])
        sync_rooms = getattr(coord, "async_sync_rooms_to_ha", None) if coord is not None else None
        if not callable(sync_rooms):
            return self.json(
                _json_error_payload(
                    "addon_unreachable",
                    "dependency_unreachable",
                    True,
                    scope="rooms_sync",
                    source="ha_host_local",
                ),
                status_code=502,
            )

        try:
            result = await sync_rooms()
        except Exception as exc:
            _LOGGER.exception("[RoomsSync] HA area registry sync failed: %s", exc)
            return self.json(
                _json_error_payload(
                    "addon_unreachable",
                    "dependency_unreachable",
                    True,
                    scope="rooms_sync",
                    source="ha_host_local",
                    exception_type=exc.__class__.__name__,
                ),
                status_code=502,
            )

        payload = dict(result) if isinstance(result, dict) else {}
        errors = int(payload.get("errors", 0) or 0)
        payload.setdefault("ok", errors == 0)
        return self.json(payload, status_code=200 if payload.get("ok") else 500)


class SmartAgentRoomDetailView(HomeAssistantView):
    """Area Registry Bridge（主计划 P4.2 例外）：只删除 HA Area，业务清理由 add-on 承接。"""

    url = "/api/v1/rooms/{room_id}"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:rooms:detail"
    requires_auth = True

    async def delete(self, request: web.Request, room_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        result = await async_delete_ha_area(request.app["hass"], room_id)
        if not bool(result.get("ok")):
            error_type = str(result.get("error_type") or "internal_error")
            if error_type == "bad_request":
                status_code = 400
            elif error_type == "not_found":
                status_code = 404
            else:
                status_code = 500
            return self.json(dict(result, scope="rooms_delete"), status_code=status_code)
        return self.json(result, status_code=200)


class SmartAgentManagedDevicesView(HomeAssistantView):
    """Read-only SmartAgent managed-device projection for add-on reinstall recovery."""

    url = "/api/v1/devices"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:devices"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        coord = _get_first_coordinator(request.app["hass"])
        if coord is None:
            return self.json([])
        return self.json(_local_device_rows(coord, request.app["hass"]))


class SmartAgentDeviceDetailView(HomeAssistantView):
    """Area Registry Bridge：仅把 add-on 设备房间选择镜像到 HA 实体 Area。"""

    url = "/api/v1/devices/{entity_id}"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:devices:detail"
    requires_auth = True

    async def patch(self, request: web.Request, entity_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        try:
            body = await request.json()
        except Exception:
            return self.json(
                _json_error_payload("invalid_json", "bad_request", False, scope="device_registry_sync"),
                status_code=400,
            )
        if not isinstance(body, dict):
            return self.json(
                _json_error_payload("invalid_body", "bad_request", False, scope="device_registry_sync"),
                status_code=400,
            )

        coord = _get_first_coordinator(request.app["hass"])
        sync_patch = getattr(coord, "async_sync_device_patch_to_ha", None) if coord is not None else None
        if not callable(sync_patch):
            return self.json(
                _json_error_payload(
                    "addon_unreachable",
                    "dependency_unreachable",
                    True,
                    scope="device_registry_sync",
                    source="ha_host_local",
                    entity_id=str(entity_id or "").strip(),
                ),
                status_code=502,
            )

        try:
            result = await sync_patch(str(entity_id or "").strip(), body)
        except Exception as exc:
            _LOGGER.exception("[DeviceRegistrySync] HA registry sync failed: %s", exc)
            return self.json(
                _json_error_payload(
                    "addon_unreachable",
                    "dependency_unreachable",
                    True,
                    scope="device_registry_sync",
                    source="ha_host_local",
                    entity_id=str(entity_id or "").strip(),
                    exception_type=exc.__class__.__name__,
                ),
                status_code=502,
            )

        payload = dict(result) if isinstance(result, dict) else {}
        errors = int(payload.get("errors", 0) or 0)
        payload.setdefault("ok", errors == 0)
        payload.setdefault("entity_id", str(entity_id or "").strip())
        payload.setdefault("source", "ha_entity_registry_mirror")
        status_code = int(payload.get("status") or 0)
        if status_code <= 0:
            error_type = str(payload.get("error_type") or "")
            if payload.get("ok", True):
                status_code = 200
            elif error_type == "bad_request":
                status_code = 400
            elif error_type == "not_found":
                status_code = 404
            elif error_type == "conflict":
                status_code = 409
            else:
                status_code = 502
        return self.json(payload, status_code=status_code)

    async def delete(self, request: web.Request, entity_id: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        eid = str(entity_id or "").strip()
        coord = _get_first_coordinator(request.app["hass"])
        delete_device = getattr(coord, "async_svc_delete_device", None) if coord is not None else None
        if not callable(delete_device):
            return self.json(
                _json_error_payload(
                    "addon_unreachable",
                    "dependency_unreachable",
                    True,
                    scope="device_delete",
                    source="ha_host_local",
                    entity_id=eid,
                ),
                status_code=502,
            )

        try:
            await delete_device(eid)
        except Exception as exc:
            _LOGGER.exception("[DeviceRegistrySync] HA device delete failed: %s", exc)
            return self.json(
                _json_error_payload(
                    "addon_unreachable",
                    "dependency_unreachable",
                    True,
                    scope="device_delete",
                    source="ha_host_local",
                    entity_id=eid,
                    exception_type=exc.__class__.__name__,
                ),
                status_code=502,
            )

        return self.json(
            {
                "ok": True,
                "entity_id": eid,
                "deleted_entity_id": eid,
                "deleted": True,
                "scope": "entity",
                "source": "ha_host_local",
            },
            status_code=200,
        )


class SmartAgentBackupsView(HomeAssistantView):
    """Operations Bridge read model: HA-owned backup inventory for the add-on."""

    url = "/api/v1/backups"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:backups"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        coord = _get_first_coordinator(request.app["hass"])
        backup_mgr = getattr(coord, "_backup_manager", None) if coord is not None else None
        list_backups = getattr(backup_mgr, "list_backups", None)
        if not callable(list_backups):
            return self.json({"backups": [], "source": "ha_host_local"}, status_code=200)

        try:
            result = list_backups()
            if hasattr(result, "__await__"):
                result = await result
        except Exception as exc:
            _LOGGER.exception("[BackupsBridge] list backups failed: %s", exc)
            return self.json(
                _json_error_payload(
                    "backups_inventory_unavailable",
                    "dependency_unreachable",
                    True,
                    scope="backups",
                    source="ha_host_local",
                    exception_type=exc.__class__.__name__,
                ),
                status_code=502,
            )

        rows = result if isinstance(result, list) else []
        return self.json({"backups": rows, "source": "ha_host_local"}, status_code=200)


class SmartAgentBackupsActionView(HomeAssistantView):
    """Operations Bridge action model: HA-owned backup create endpoint for the add-on."""

    url = "/api/v1/backups/{action}"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:backups:action"
    requires_auth = True

    async def post(self, request: web.Request, action: str) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        act = str(action or "").strip().lower()
        if act not in {"create", "restore", "delete"}:
            return self.json(
                _json_error_payload(
                    "unknown_backup_action",
                    "not_found",
                    False,
                    scope="backups_action",
                    action=act,
                    source="ha_host_local",
                ),
                status_code=404,
            )

        try:
            body = await request.json()
        except Exception:
            return self.json(
                _json_error_payload(
                    "invalid_json",
                    "bad_request",
                    False,
                    scope="backups_action",
                    action=act,
                    source="ha_host_local",
                ),
                status_code=400,
            )
        if not isinstance(body, dict):
            return self.json(
                _json_error_payload(
                    "invalid_body",
                    "bad_request",
                    False,
                    scope="backups_action",
                    action=act,
                    source="ha_host_local",
                ),
                status_code=400,
            )

        if act != "create":
            return self.json(
                _json_error_payload(
                    "backup_action_not_open",
                    "safety_blocked",
                    False,
                    scope="backups_action",
                    action=act,
                    source="ha_host_local",
                ),
                status_code=409,
            )

        coord = _get_first_coordinator(request.app["hass"])
        backup_mgr = getattr(coord, "_backup_manager", None) if coord is not None else None
        backup_now = getattr(backup_mgr, "backup_now", None)
        if not callable(backup_now):
            return self.json(
                _json_error_payload(
                    "backup_manager_unavailable",
                    "dependency_unreachable",
                    True,
                    scope="backups_action",
                    action=act,
                    source="ha_host_local",
                ),
                status_code=503,
            )

        requested_level = str(body.get("level") or "").strip().lower()
        if requested_level == "full":
            level = "full"
        elif requested_level == "basic":
            level = "basic"
        else:
            level = "standard"
        password = str(body.get("password") or body.get("backup_password") or "smart_agent_local_backup")

        try:
            result = backup_now(password=password, level=level)
            if hasattr(result, "__await__"):
                result = await result
        except Exception as exc:
            _LOGGER.exception("[BackupsBridge] create backup failed: %s", exc)
            return self.json(
                _json_error_payload(
                    "backup_create_failed",
                    "dependency_unreachable",
                    True,
                    scope="backups_action",
                    action=act,
                    source="ha_host_local",
                    exception_type=exc.__class__.__name__,
                ),
                status_code=502,
            )

        payload = dict(result) if isinstance(result, dict) else {}
        ok = bool(payload.get("ok", payload.get("success", True)))
        payload.setdefault("ok", ok)
        payload.setdefault("action", act)
        payload.setdefault("source", "ha_host_local")
        return self.json(payload, status_code=200)


class SmartAgentLicenseStatusView(HomeAssistantView):
    """Operations Bridge read model: HA-owned license state for the add-on."""

    url = "/api/v1/license/status"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:license:status"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        coord = _get_first_coordinator(request.app["hass"])
        get_status = getattr(coord, "get_license_status", None) if coord is not None else None
        if not callable(get_status):
            return self.json(
                {
                    "has_key": False,
                    "valid": False,
                    "tier": "free",
                    "source": "ha_host_local",
                },
                status_code=200,
            )

        try:
            payload = get_status()
        except Exception as exc:
            _LOGGER.exception("[LicenseBridge] status read failed: %s", exc)
            return self.json(
                _json_error_payload(
                    "license_status_unavailable",
                    "dependency_unreachable",
                    True,
                    scope="license_status",
                    source="ha_host_local",
                    exception_type=exc.__class__.__name__,
                ),
                status_code=502,
            )

        data = dict(payload) if isinstance(payload, dict) else {}
        data.setdefault("source", "ha_host_local")
        return self.json(data, status_code=200)


class SmartAgentMcpStatusView(HomeAssistantView):
    """Operations Bridge read model: HA-owned MCP status for the add-on."""

    url = "/api/v1/mcp/status"
    extra_urls: list[str] = []
    name = "api:smart_agent:v1:mcp:status"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        if (err := _view_admin_check(request)):
            return err

        coord = _get_first_coordinator(request.app["hass"])
        tools: list[dict[str, Any]] = []
        try:
            from .mcp_tools import get_mcp_tools

            loaded_tools = get_mcp_tools()
            if isinstance(loaded_tools, list):
                tools = [dict(item) for item in loaded_tools if isinstance(item, dict)]
        except Exception as exc:
            _LOGGER.debug("[McpBridge] tool inventory read failed: %s", exc)

        return self.json(
            {
                "enabled": bool(getattr(coord, "_mcp_enabled", True)) if coord is not None else False,
                "protocol": "mcp",
                "endpoint": "/api/v1/mcp",
                "tools": tools,
                "source": "ha_host_local",
            },
            status_code=200,
        )


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
























# 极速配对临时存储 key（存于 hass.data）
_PAIR_KEY = "smart_agent_pairing_token"
_AUTH_SESSION_KEY = "smart_agent_auth_sessions"
_AUTH_REVOKED_TOKEN_KEY = "smart_agent_revoked_auth_tokens"
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


def _get_revoked_auth_tokens(hass: HomeAssistant) -> dict[str, float]:
    tokens = hass.data.get(_AUTH_REVOKED_TOKEN_KEY)
    if isinstance(tokens, dict):
        return tokens
    tokens = {}
    hass.data[_AUTH_REVOKED_TOKEN_KEY] = tokens
    return tokens


def _purge_revoked_auth_tokens(hass: HomeAssistant) -> None:
    tokens = _get_revoked_auth_tokens(hass)
    now_ts = time.time()
    expired = [tk for tk, expires_at in tokens.items() if float(expires_at or 0) <= now_ts]
    for tk in expired:
        tokens.pop(tk, None)


def _mark_auth_token_revoked(hass: HomeAssistant, token: str, *, expires_at: float | None = None) -> None:
    token = str(token or "").strip()
    if not token:
        return
    _purge_revoked_auth_tokens(hass)
    expiry = float(expires_at or 0)
    if expiry <= time.time():
        expiry = time.time() + _AUTH_SESSION_TTL
    _get_revoked_auth_tokens(hass)[token] = expiry


def _is_auth_token_revoked(hass: HomeAssistant, token: str) -> bool:
    token = str(token or "").strip()
    if not token:
        return False
    _purge_revoked_auth_tokens(hass)
    return token in _get_revoked_auth_tokens(hass)


async def _async_revoke_auth_session_token(
    hass: HomeAssistant,
    session_token: str,
    session_info: dict[str, Any] | None,
) -> None:
    info = session_info if isinstance(session_info, dict) else {}
    _mark_auth_token_revoked(hass, session_token, expires_at=float(info.get("expires_at", 0) or 0))

    refresh_token_id = str(info.get("refresh_token_id", "") or "")
    user_id = str(info.get("user_id", "") or "")
    if not refresh_token_id or not user_id:
        return

    try:
        user = await hass.auth.async_get_user(user_id)
    except Exception as exc:
        _LOGGER.debug("[Auth] logout refresh token lookup failed: %s", exc)
        return
    refresh_tokens = getattr(user, "refresh_tokens", {}) or {}
    refresh_token = refresh_tokens.get(refresh_token_id)
    if refresh_token is None:
        refresh_token = next(
            (token for token in refresh_tokens.values() if getattr(token, "id", None) == refresh_token_id),
            None,
        )
    if refresh_token is None:
        return
    try:
        await hass.auth.async_remove_refresh_token(refresh_token)
    except Exception as exc:
        _LOGGER.debug("[Auth] logout refresh token revoke failed: %s", exc)


async def _async_cleanup_legacy_pair_tokens(hass: HomeAssistant) -> int:
    removed = 0
    long_lived_type = getattr(auth_models, "TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN", "long_lived")
    users = await hass.auth.async_get_users()
    for user in users:
        refresh_tokens = getattr(user, "refresh_tokens", {}) or {}
        for refresh_token in list(refresh_tokens.values()):
            client_name = str(getattr(refresh_token, "client_name", "") or "")
            token_type = getattr(refresh_token, "token_type", None)
            if client_name not in _LEGACY_PAIR_TOKEN_CLIENT_NAMES:
                continue
            if token_type != long_lived_type:
                continue
            await hass.auth.async_remove_refresh_token(refresh_token)
            removed += 1
    hass.data.pop(_PAIR_KEY, None)
    _LOGGER.info("[Auth] 历史配对长效令牌清理完成，撤销数量=%s", removed)
    return removed


async def _async_cleanup_legacy_pair_tokens_if_enabled(hass: HomeAssistant, entry: ConfigEntry) -> int:
    options = dict(getattr(entry, "options", {}) or {})
    if not bool(options.get(CONF_CLEANUP_LEGACY_PAIR_TOKENS, False)):
        return 0

    removed = await _async_cleanup_legacy_pair_tokens(hass)
    options[CONF_CLEANUP_LEGACY_PAIR_TOKENS] = False
    try:
        hass.config_entries.async_update_entry(entry, options=options)
    except Exception as exc:
        _LOGGER.warning("[Auth] 历史配对令牌清理开关自动关闭失败: %s", exc)
    return removed


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
    if _is_auth_token_revoked(hass, session_token):
        return None
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



PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CONVERSATION,
    Platform.UPDATE,  # Phase 9.7: 版本自动检查实体
]


LEGACY_ENTITY_IDS: tuple[str, ...] = (
    "button.smart_agent_discover",
    "button.smart_agent_dev_add",
    "button.smart_agent_dev_delete",
    "button.smart_agent_habit_add",
    "button.smart_agent_habit_delete",
    "button.smart_agent_habit_lock",
    "button.smart_agent_rule_add",
    "button.smart_agent_rule_delete",
    "button.smart_agent_rule_lock",
    "button.smart_agent_confirm_habit",
    "button.smart_agent_cancel_habit",
    "number.smart_agent_confidence_auto",
    "number.smart_agent_confidence_notify",
    "select.smart_agent_engine",
    "select.smart_agent_dev_select",
    "select.smart_agent_habit_select",
    "select.smart_agent_rule_select",
    "text.smart_agent_status",
    "text.smart_agent_last_action",
    "text.smart_agent_dev_entity",
    "text.smart_agent_dev_desc",
    "text.smart_agent_habit_input",
    "text.smart_agent_rule_input",
    "sensor.smart_agent_config",
)

LEGACY_ENTITY_KEY_DOMAINS: dict[str, tuple[str, ...]] = {
    "discover": ("button",),
    "dev_add": ("button",),
    "dev_delete": ("button",),
    "habit_add": ("button",),
    "habit_delete": ("button",),
    "habit_lock": ("button",),
    "rule_add": ("button",),
    "rule_delete": ("button",),
    "rule_lock": ("button",),
    "confirm_habit": ("button",),
    "cancel_habit": ("button",),
    "confidence_auto": ("number",),
    "confidence_notify": ("number",),
    "engine": ("select",),
    "dev_select": ("select",),
    "habit_select": ("select",),
    "rule_select": ("select",),
    "status": ("text",),
    "last_action": ("text",),
    "dev_entity": ("text",),
    "dev_desc": ("text",),
    "habit_input": ("text",),
    "rule_input": ("text",),
    "config": ("sensor",),
}
LEGACY_ENTITY_KEYS: tuple[str, ...] = tuple(LEGACY_ENTITY_KEY_DOMAINS)


async def _async_remove_legacy_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    entity_reg = entity_registry.async_get(hass)
    for entity_id in LEGACY_ENTITY_IDS:
        if entity_reg.async_get(entity_id):
            entity_reg.async_remove(entity_id)
    for registry_entry in entity_registry.async_entries_for_config_entry(entity_reg, entry.entry_id):
        entity_id = str(getattr(registry_entry, "entity_id", "") or "")
        domain = str(getattr(registry_entry, "domain", "") or entity_id.split(".", 1)[0])
        unique_id = str(getattr(registry_entry, "unique_id", "") or "")
        for key, domains in LEGACY_ENTITY_KEY_DOMAINS.items():
            if domain in domains and unique_id.endswith(f"_{key}"):
                entity_reg.async_remove(entity_id)
                break


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
        _LOGGER.info(
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
    await _async_cleanup_legacy_pair_tokens_if_enabled(hass, entry)
    await _async_remove_legacy_entities(hass, entry)
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
            capability=call.data.get("capability", ""),
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
            CONF_CLEANUP_LEGACY_PAIR_TOKENS,
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
            "cleanup_legacy_pair_tokens": (CONF_CLEANUP_LEGACY_PAIR_TOKENS, bool),
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
                vol.Schema({vol.Required("content"): cv.string}),
            ),
            ServiceRegistration(
                "toggle_habit_lock",
                svc_toggle_habit_lock,
                vol.Schema({vol.Required("content"): cv.string}),
            ),
            ServiceRegistration(
                "add_rule",
                svc_add_rule,
                vol.Schema({vol.Required("content"): cv.string}),
            ),
            ServiceRegistration(
                "delete_rule",
                svc_delete_rule,
                vol.Schema({vol.Required("content"): cv.string}),
            ),
            ServiceRegistration(
                "toggle_rule_lock",
                svc_toggle_rule_lock,
                vol.Schema({vol.Required("content"): cv.string}),
            ),
            ServiceRegistration(
                "manual_inference",
                svc_manual_inference,
                vol.Schema({vol.Optional("trigger", default="手动测试触发"): cv.string}),
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
