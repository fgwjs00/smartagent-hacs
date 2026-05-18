"""
AddOnClient — SmartAgent Add-on 内部 API 客户端。

架构角色：
    thin 集成（coordinator）
        ↓  ContextBuilder 采集数据 → InferenceBundle
        ↓  调用 AddOnClient.infer(bundle)
    此模块
        ↓  HTTP POST /infer  传入完整 InferenceBundle（含 X-SA-Token 认证头）
    smartagent-addon（Docker 容器，端口 18099，可通过 CONF_ADDON_PORT 配置）
        ↓  inference_engine.py 构建 Prompt + 调用 LLM（受 Cython 保护）

接口约定（v4.10.10）：
  - /infer  接受 InferenceBundle（完整上下文字典），返回决策 JSON（需 X-SA-Token）
  - /health 健康检查（无需认证）
  - /status 运行状态摘要（需 X-SA-Token）

Fail-safe 设计：
  - Add-on 未安装 / 容器未启动时，`is_available()` 返回 False
  - 调用方检测到不可用时必须 fail-closed，不再回退到 HA 本地推理
  - infer() 超时 90 秒（LLM 调用可能需要较长时间）
  - auth_token 为空时不发送认证头（向后兼容未配置令牌的环境）
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Add-on 默认内部端口（与 smartagent-addon/config.yaml SA_INTERNAL_PORT 保持一致）
# 不直接使用此常量构造 URL，由 coordinator 通过 CONF_ADDON_PORT 读取后传入
_DEFAULT_ADDON_PORT = 18099
_DEFAULT_ADDON_GATEWAY_PORT = 8234

def _build_addon_base_url(port: int) -> str:
    """根据端口构建 Add-on 内部 API 基础 URL。"""
    return f"http://localhost:{port}"


def derive_addon_gateway_base_url(ha_url: str, gateway_port: int = _DEFAULT_ADDON_GATEWAY_PORT) -> str:
    """Derive the add-on gateway URL from a Home Assistant URL.

    HA Core usually cannot reach the add-on through its own localhost. When HA is
    accessed through a LAN URL, the add-on's mapped gateway port on that same
    host is the practical default.
    """
    raw = (ha_url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.strip()
    if host.lower() == "localhost" or host in {"127.0.0.1", "::1"}:
        return ""
    netloc = f"[{host}]:{gateway_port}" if ":" in host and not host.startswith("[") else f"{host}:{gateway_port}"
    return urlunsplit((parsed.scheme, netloc, "", "", ""))

_HEALTH_TIMEOUT = aiohttp.ClientTimeout(total=5)
# LLM 调用可能需要 60s+，推理超时设宽裕一些
_INFER_TIMEOUT = aiohttp.ClientTimeout(total=90)
# 可用性检查缓存有效期（秒）：成功=60s，失败=10s（快速重试）
_AVAIL_CACHE_OK = 60.0
_AVAIL_CACHE_FAIL = 10.0


class AddOnClient:
    """SmartAgent Add-on HTTP 客户端。

    使用方式（v4.10.10 Bundle 模式）：
        client = AddOnClient(port=18099, auth_token="your-secret")
        if await client.is_available():
            bundle = await ContextBuilder(coordinator).build(trigger)
            result = await client.infer(bundle)
        else:
            result = None  # fail-closed upstream
    """

    def __init__(
        self,
        base_url: str = "",
        auth_token: str = "",
        port: int = _DEFAULT_ADDON_PORT,
    ) -> None:
        """初始化客户端。

        :param base_url: Add-on 内部 API 地址（完整 URL）。若为空则由 port 参数自动构建。
        :param auth_token: 内部认证令牌（对应 Add-on 环境变量 SA_AUTH_TOKEN），
                           空字符串表示不发送认证头（向后兼容）
        :param port: Add-on 内部 API 端口，默认 18099。base_url 非空时忽略此参数。
        """
        self._base = (base_url.rstrip("/") if base_url else _build_addon_base_url(port))
        self._auth_token: str = auth_token.strip()
        self._session: aiohttp.ClientSession | None = None
        # 可用性缓存：避免每次推理都发 HTTP 健康检查
        self._avail_cache: bool = False
        self._avail_checked_at: float = 0.0

    @property
    def _auth_headers(self) -> dict[str, str]:
        """返回认证请求头，未配置令牌时返回空字典。"""
        if self._auth_token:
            return {"X-SA-Token": self._auth_token}
        return {}

    @property
    def auth_headers(self) -> dict[str, str]:
        """公开认证头（供外部代理链路复用）。"""
        return dict(self._auth_headers)

    def ws_url(self, path: str) -> str:
        """构建 Add-on WebSocket 地址。"""
        p = path if str(path or "").startswith("/") else f"/{path}"
        base = self._base
        if base.startswith("https://"):
            return "wss://" + base[len("https://"):] + p
        if base.startswith("http://"):
            return "ws://" + base[len("http://"):] + p
        return base + p

    def _redact_sensitive(self, text: str) -> str:
        """脱敏日志中的令牌与常见密钥片段。"""
        out = text
        if self._auth_token and self._auth_token in out:
            out = out.replace(self._auth_token, self._auth_token[:4] + "***" + self._auth_token[-4:])
        out = re.sub(r"(Bearer\s+)[A-Za-z0-9._\-]+", r"\1***", out)
        out = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)[\w\-]{8,}", r"\1***", out)
        return out

    def _http_retryable(self, status: int) -> bool:
        """判断 HTTP 状态码是否可重试。"""
        return status in (408, 429, 500, 502, 503, 504)

    def _build_status_result(self, status: int, data: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
        """构造结构化透传结果，避免吞掉 add-on 明确响应。"""
        result = data if isinstance(data, dict) else dict(fallback or {"ok": 200 <= status < 300})
        if status >= 400:
            result.setdefault("error", f"http_{status}")
            result.setdefault("error_type", "http_error")
            result.setdefault("retryable", self._http_retryable(status))
        result["__status"] = status
        return result

    def _build_client_exception_result(self, exc: Exception) -> dict[str, Any]:
        """构造客户端内部异常的结构化结果。"""
        return {
            "ok": False,
            "error": self._redact_sensitive(str(exc) or exc.__class__.__name__),
            "error_type": "client_exception",
            "retryable": False,
            "__status": 500,
        }

    def _is_fallback_exception(self, exc: Exception) -> bool:
        """仅网络不可达/超时异常允许走回退。"""
        return isinstance(exc, (aiohttp.ClientConnectionError, asyncio.TimeoutError))

    def _handle_request_exception(self, exc: Exception) -> dict[str, Any] | None:
        """统一异常处理：网络异常回退，其他异常结构化上报。"""
        if self._is_fallback_exception(exc):
            return None
        return self._build_client_exception_result(exc)

    async def _get_session(self, timeout: aiohttp.ClientTimeout | None = None) -> aiohttp.ClientSession:
        """获取（或创建）共享 HTTP Session。

        :param timeout: 请求超时配置，None 时使用健康检查默认超时
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=timeout or _HEALTH_TIMEOUT)
        return self._session

    async def get_http_session(self, timeout: aiohttp.ClientTimeout | None = None) -> aiohttp.ClientSession:
        """公开会话对象（供外部代理链路复用）。"""
        return await self._get_session(timeout=timeout)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
    ) -> dict[str, Any] | None:
        """统一 JSON 请求能力，返回 status_code + body 供上层状态码感知透传。"""
        m = str(method or "GET").upper()
        p = path if str(path or "").startswith("/") else f"/{path}"
        kwargs: dict[str, Any] = {
            "headers": self._auth_headers,
            "timeout": timeout or _HEALTH_TIMEOUT,
        }
        if body is not None:
            kwargs["json"] = body

        try:
            session = await self._get_session()
            async with session.request(m, f"{self._base}{p}", **kwargs) as resp:
                try:
                    payload = await resp.json(content_type=None)
                except Exception:
                    payload = {}
                return {
                    "status_code": int(resp.status),
                    "body": payload if isinstance(payload, (dict, list)) else {},
                }
        except Exception as exc:
            _LOGGER.debug("[AddOnClient] request_json failed: %s", self._redact_sensitive(str(exc)))
            handled = self._handle_request_exception(exc)
            if isinstance(handled, dict):
                return {
                    "status_code": int(handled.get("__status", 500) or 500),
                    "body": handled,
                }
            return None

    async def run_decision_fast_path(
        self,
        *,
        entity_id: str,
        new_state: str,
        old_state: str = "",
        snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Run add-on Core fast-path decision orchestration."""
        payload: dict[str, Any] = {
            "entity_id": str(entity_id or ""),
            "new_state": str(new_state or ""),
            "old_state": str(old_state or ""),
        }
        if snapshot is not None:
            payload["snapshot"] = snapshot

        result = await self.request_json("POST", "/decision/fast-path", body=payload)
        if not isinstance(result, dict):
            return None
        status = int(result.get("status_code") or 0)
        body = result.get("body")
        response = body if isinstance(body, dict) else {"ok": 200 <= status < 300}
        response["__status"] = status
        return response

    async def is_available(self) -> bool:
        """检查 Add-on 是否在线（带缓存，避免每次推理都发 HTTP 请求）。

        - 上次结果为 True：60 秒内复用，不重复健康检查
        - 上次结果为 False：10 秒后重试（快速检测恢复）

        :return: True 表示 Add-on 健康运行，False 表示不可用（上游应 fail-closed）
        """
        now = time.monotonic()
        ttl = _AVAIL_CACHE_OK if self._avail_cache else _AVAIL_CACHE_FAIL
        if now - self._avail_checked_at < ttl:
            return self._avail_cache

        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/health",
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                result = resp.status == 200
        except Exception:
            result = False

        self._avail_cache = result
        self._avail_checked_at = time.monotonic()
        return result

    async def get_capabilities(self) -> dict[str, Any] | None:
        """Fetch Add-on Gateway capabilities, returning None on network failure only."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/capabilities",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data if isinstance(data, dict) else None
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)

    async def get_core_status(self) -> dict[str, Any] | None:
        """Fetch Add-on Core migration status, returning None on network/endpoint-missing failure."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/core/status",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data if isinstance(data, dict) else None
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)

    async def get_addon_system_status(self) -> dict[str, Any] | None:
        """Fetch Add-on system status, returning None on network/endpoint-missing failure."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/addon/system-status",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data if isinstance(data, dict) else None
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)

    async def infer(self, bundle: dict[str, Any]) -> dict[str, Any] | None:
        """委托 Add-on 执行 AI 推理（Bundle 模式，v4.10.10+）。

        传入由 ContextBuilder 生成的完整 InferenceBundle，
        Add-on 负责构建 Prompt + 调用 LLM + 解析响应。

        :param bundle: InferenceBundle 字典（含 trigger、context_text、rules、LLM 配置等）
        :return: 决策字典（含 scene/confidence/actions/reply/speak），失败时返回 None
        """
        try:
            session = await self._get_session()
            bundle_payload = dict(bundle)
            online_api_key = str(bundle_payload.pop("online_api_key", "") or "")
            infer_headers = dict(self._auth_headers)
            if online_api_key:
                infer_headers["X-SA-Online-Key"] = online_api_key
            async with session.post(
                f"{self._base}/infer",
                json=bundle_payload,
                headers=infer_headers,
                timeout=_INFER_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    # 基本有效性检查：必须有 actions 字段
                    if isinstance(result, dict) and "actions" in result:
                        return result
                    _LOGGER.warning("[AddOnClient] 推理响应格式无效: %s", self._redact_sensitive(str(result)[:200]))
                elif resp.status == 401:
                    # 401 是配置错误（令牌不一致），不是可用性问题：
                    # 不重置 _avail_cache，避免下次 is_available() → /health(200) → True
                    # → infer() → 401 的无效循环。Add-on 确实在运行，只是令牌配对错误。
                    _LOGGER.error(
                        "[AddOnClient] 认证失败（401）: X-SA-Token 不匹配，"
                        "请确认 HA 集成 Options 中的 addon_auth_token 与 Add-on 的 SA_AUTH_TOKEN 环境变量一致"
                    )
                elif resp.status in (429, 503):
                    try:
                        payload = await resp.json()
                    except Exception:
                        payload = {}
                    err = payload.get("error") or ("service_unavailable" if resp.status == 503 else "rate_limited")
                    err = self._redact_sensitive(str(err))
                    retryable = bool(payload.get("retryable", True))
                    _LOGGER.info(
                        "[AddOnClient] Add-on 推理不可用（HTTP %s, error=%s, retryable=%s），返回 None 由上游 fail-closed",
                        resp.status,
                        err,
                        retryable,
                    )
                    self._avail_cache = False
                    self._avail_checked_at = 0.0
                else:
                    _LOGGER.warning("[AddOnClient] 推理请求失败: HTTP %s", resp.status)
        except aiohttp.ClientConnectorError:
            _LOGGER.debug("[AddOnClient] Add-on 未启动（连接拒绝），返回 None 由上游 fail-closed")
            self._avail_cache = False          # 让下次立即重新检查
            self._avail_checked_at = 0.0
        except asyncio.TimeoutError:
            _LOGGER.warning("[AddOnClient] 推理超时（>90s），返回 None 由上游 fail-closed")
            self._avail_cache = False
            self._avail_checked_at = 0.0
        except Exception as exc:
            _LOGGER.debug("[AddOnClient] 推理请求异常: %s", self._redact_sensitive(str(exc)))
        return None

    async def get_log_dates(self) -> list[str] | dict[str, Any] | None:
        """获取日志日期列表（优先 add-on canonical 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/logs/dates",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = []
                if resp.status == 200:
                    if isinstance(data, list):
                        return [str(x) for x in data]
                    return {
                        "ok": False,
                        "error": "invalid_response_body",
                        "error_type": "invalid_response",
                        "retryable": False,
                        "__status": 502,
                    }
                if resp.status in (404, 405):
                    return self._build_status_result(resp.status, data)
                return self._build_status_result(resp.status, data)
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
            return None
        except Exception as exc:
            return self._build_client_exception_result(exc)

    async def get_log_content(
        self,
        date: str,
        *,
        level: str | None = None,
        keyword: str | None = None,
        max_bytes: int | str | None = None,
        tail_lines: int | str | None = None,
        raw: bool = False,
    ) -> dict[str, Any] | None:
        """按日期读取日志内容（优先 add-on canonical 服务面）。"""
        d = str(date or "").strip()
        if not d:
            return None
        params: dict[str, str] = {"date": d}
        if str(level or "").strip() and str(level or "").strip().lower() != "all":
            params["level"] = str(level or "").strip().lower()
        if str(keyword or "").strip():
            params["keyword"] = str(keyword or "").strip()
        if max_bytes not in (None, ""):
            params["max_bytes"] = str(max_bytes)
        if tail_lines not in (None, ""):
            params["tail_lines"] = str(tail_lines)
        headers = self._auth_headers
        if raw:
            params["raw"] = "true"
            headers = {**headers, "X-SA-Log-Raw": "1"}
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/logs/content",
                params=params,
                headers=headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_log_info(self) -> dict[str, Any] | None:
        """读取日志元信息（优先 add-on canonical 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/logs/info",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_scene_yaml_export(self, scene_id: int) -> dict[str, Any] | None:
        """读取场景 YAML 导出（优先 add-on canonical 服务面）。"""
        sid = int(scene_id)
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/scenes/export-yaml",
                params={"scene_id": sid},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_scene_yaml_export(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """写入场景 YAML 导出（优先 add-on root-base 服务面）。"""
        payload = body if isinstance(body, dict) else {}
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/scenes/export-yaml",
                json=payload,
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_auth_login(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """登录（优先 add-on 服务面）。"""
        payload = body if isinstance(body, dict) else {}
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/auth/login",
                json=payload,
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_auth_me(self, token: str = "") -> dict[str, Any] | None:
        """读取当前会话用户信息（优先 add-on 服务面）。"""
        _ = token
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/auth/me",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_auth_logout(self, token: str = "") -> dict[str, Any] | None:
        """退出登录（优先 add-on 服务面）。"""
        _ = token
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/auth/logout",
                json={},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_pair_start(self) -> dict[str, Any] | None:
        """触发配对开始（优先 add-on 服务面）。"""
        for path in ("/device/pair/start",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json={},
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_pair_confirm(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """提交配对确认（优先 add-on 服务面）。"""
        payload = body if isinstance(body, dict) else {}
        for path in ("/device/pair/confirm",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_voice_interrupt(self) -> dict[str, Any] | None:
        """触发语音中断（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/voice/interrupt",
                json={},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                if 200 <= resp.status < 300 and "status" not in result:
                    result["status"] = "interrupted"
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_status(self) -> dict[str, Any]:
        """获取 Add-on 运行状态摘要（兼容旧 /status）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/status",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            pass
        return {}

    async def get_system_status(self) -> dict[str, Any]:
        """获取系统状态（优先新端点 /system/status，失败时兼容 /status）。"""
        result = await self.request_json("GET", "/system/status")
        if isinstance(result, dict):
            status = int(result.get("status_code", 0) or 0)
            body = result.get("body")
            if status == 200 and isinstance(body, dict):
                return body
            if status in (404, 405):
                pass
            else:
                return self._build_status_result(status, body)

        legacy = await self.get_status()
        if not isinstance(legacy, dict) or not legacy:
            return {}
        return {
            "gateway": "online",
            "core": "online",
            "ha": "online",
            "mode": legacy.get("mode", "unknown"),
            "uptime_sec": 0,
            "devices_managed": 0,
            "active_scenes": 0,
            "voice_provider": "unknown",
            "cpu": 0,
            "memory": 0,
            "addon_version": legacy.get("addon_version", ""),
            "inference_count_today": int(legacy.get("inference_count_today", 0) or 0),
        }

    async def get_dashboard_summary(self) -> dict[str, Any]:
        """获取仪表盘摘要（优先 /dashboard/summary）。"""
        result = await self.request_json("GET", "/dashboard/summary")
        if isinstance(result, dict):
            status = int(result.get("status_code", 0) or 0)
            body = result.get("body")
            if status == 200 and isinstance(body, dict):
                return body
            if status in (404, 405):
                pass
            else:
                return self._build_status_result(status, body)

        legacy_result = await self.request_json("GET", "/addon/dashboard-summary")
        if isinstance(legacy_result, dict):
            status = int(legacy_result.get("status_code", 0) or 0)
            body = legacy_result.get("body")
            if status == 200 and isinstance(body, dict):
                return body
            if status in (404, 405):
                pass
            else:
                return self._build_status_result(status, body)

        legacy = await self.get_status()
        if not isinstance(legacy, dict) or not legacy:
            return {}
        return {
            "decisions_today": int(legacy.get("inference_count_today", 0) or 0),
            "addon_mode": legacy.get("mode", "unknown"),
            "addon_inference_count_today": int(legacy.get("inference_count_today", 0) or 0),
        }

    async def get_devices(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取设备列表（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/devices",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                    if isinstance(data, dict) and isinstance(data.get("data"), list):
                        return [x for x in data.get("data", []) if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_rooms(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取房间列表（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/rooms",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                    if isinstance(data, dict) and isinstance(data.get("data"), list):
                        return [x for x in data.get("data", []) if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def discover_devices(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """发现设备（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/devices/discover",
                json={},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def batch_add_devices(self, entities: list[str]) -> dict[str, Any] | None:
        """批量纳管设备（优先 add-on 服务面）。"""
        payload = {"entities": [str(e).strip() for e in (entities or []) if str(e).strip()]}
        for path in ("/devices/batch-add",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def update_device(self, entity_id: str, body: dict[str, Any]) -> dict[str, Any] | None:
        """更新单设备（优先 add-on 服务面）。"""
        eid = str(entity_id or "").strip()
        if not eid:
            return None
        try:
            session = await self._get_session()
            async with session.patch(
                f"{self._base}/devices/{eid}",
                json=body if isinstance(body, dict) else {},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def delete_device(self, entity_id: str) -> dict[str, Any] | None:
        """删除单设备（优先 add-on 服务面）。"""
        eid = str(entity_id or "").strip()
        if not eid:
            return None
        try:
            session = await self._get_session()
            async with session.delete(
                f"{self._base}/devices/{eid}",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def sync_rooms(self) -> dict[str, Any] | None:
        """同步房间到 HA Area（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/rooms/sync",
                json={},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_rooms_topology(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取房间拓扑（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/rooms/topology",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                    if isinstance(data, dict) and isinstance(data.get("data"), list):
                        return [x for x in data.get("data", []) if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def save_rooms_topology(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """Save room topology into the add-on canonical projection."""
        body = body if isinstance(body, dict) else {}
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/rooms/topology",
                json=body,
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_learning_stats(self) -> dict[str, Any] | None:
        """获取学习统计（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/learning/stats",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_ai_scenes(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取 AI 场景列表（优先 add-on 服务面）。"""
        for path in ("/ai-scenes",):
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self._base}{path}",
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return [x for x in data if isinstance(x, dict)]
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_ai_scene_action(self, action: str, scene_id: int) -> dict[str, Any] | None:
        """执行场景审批/拒绝（优先 add-on 服务面）。"""
        act = "reject" if str(action).strip().lower() == "reject" else "approve"
        endpoints = [
            f"/ai-scenes/{act}",
        ]
        payload = {"id": int(scene_id)}
        for path in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def trigger_ai_scene(self, scene_id: int) -> dict[str, Any] | None:
        """触发 AI 场景（优先 add-on 服务面）。"""
        sid = int(scene_id)
        endpoints = [
            (f"/ai-scenes/{sid}/trigger", None),
        ]
        for path, payload in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "id": sid}
                    result.setdefault("id", sid)
                    if resp.status >= 400:
                        result.setdefault("error", f"http_{resp.status}")
                        result.setdefault("error_type", "http_error")
                        result.setdefault("retryable", resp.status in (408, 429, 500, 502, 503, 504))
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                _LOGGER.debug("[AddOnClient] trigger_ai_scene exception: %s", self._redact_sensitive(str(exc)))
                return self._handle_request_exception(exc)
        return None

    async def get_transactions(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取事务列表（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/transactions",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_decision_trace_detail(self, txn_id: int | str) -> dict[str, Any] | None:
        """获取 decision-trace 详情（优先 add-on 服务面）。"""
        tid = str(txn_id or "").strip()
        if not tid:
            return None
        encoded_tid = quote(tid, safe="")
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/decision-trace/{encoded_tid}",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                if resp.status >= 400:
                    result.setdefault("error", f"http_{resp.status}")
                    result.setdefault("error_type", "http_error")
                    result.setdefault("retryable", resp.status in (408, 429, 500, 502, 503, 504))
                result["__status"] = resp.status
                return result
        except Exception as exc:
            _LOGGER.debug("[AddOnClient] get_decision_trace_detail exception: %s", self._redact_sensitive(str(exc)))
            return self._handle_request_exception(exc)

    async def rollback_transaction(self, txn_id: int) -> dict[str, Any] | None:
        """回滚事务（优先 add-on 服务面）。"""
        tid = int(txn_id)
        endpoints = [
            (f"/transactions/{tid}/rollback", None),
        ]
        for path, payload in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "id": tid}
                    result.setdefault("id", tid)
                    if resp.status >= 400:
                        result.setdefault("error", f"http_{resp.status}")
                        result.setdefault("error_type", "http_error")
                        result.setdefault("retryable", resp.status in (408, 429, 500, 502, 503, 504))
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                _LOGGER.debug("[AddOnClient] rollback_transaction exception: %s", self._redact_sensitive(str(exc)))
                return self._handle_request_exception(exc)
        return None

    async def get_memory_profiles(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取画像列表（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/memory/profiles",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_memory_habits(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取习惯列表（优先 add-on 服务面）。"""
        for path in ("/memory/habits",):
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self._base}{path}",
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return [x for x in data if isinstance(x, dict)]
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def get_corrections(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取纠错列表（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/corrections",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_profile_action(self, action: str, content: str) -> dict[str, Any] | None:
        """执行画像操作（add/delete/toggle-lock）。"""
        act = str(action or "").strip().lower()
        if act == "toggle_lock":
            act = "toggle-lock"
        if act not in ("add", "delete", "toggle-lock"):
            return None

        endpoints = [
            f"/memory/profiles/{act}",
        ]
        payload = {"content": str(content or "").strip()}
        for path in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "action": act}
                    result.setdefault("action", act)
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_habit_action(self, action: str, content: str) -> dict[str, Any] | None:
        """执行习惯操作（add/delete/toggle-lock，canonical /memory/habits/*）。"""
        act = str(action or "").strip().lower()
        if act == "toggle_lock":
            act = "toggle-lock"
        if act not in ("add", "delete", "toggle-lock"):
            return None

        endpoints = [
            f"/memory/habits/{act}",
        ]
        payload = {"content": str(content or "").strip()}
        for path in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "action": act}
                    result.setdefault("action", act)
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_correction_action(self, action: str, entity_id: str | None) -> dict[str, Any] | None:
        """执行纠错动作（dismiss/report）。"""
        act = str(action or "").strip().lower()
        if act not in ("dismiss", "report"):
            return None
        endpoints = [
            f"/corrections/{act}",
        ]
        payload: dict[str, Any] = {}
        eid = str(entity_id or "").strip()
        if eid:
            payload["entity_id"] = eid
        for path in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "action": act}
                    result.setdefault("action", act)
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def get_license_status(self) -> dict[str, Any] | None:
        """获取 License 状态（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/license/status",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_license_verify(self, license_key: str | None) -> dict[str, Any] | None:
        """验证 License（优先 add-on 服务面）。"""
        payload = {"license_key": str(license_key or "").strip()}
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/license/verify",
                json=payload,
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_backups(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取备份列表（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/backups",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_backup_action(self, action: str, body: dict[str, Any]) -> dict[str, Any] | None:
        """执行备份操作（create/restore/delete，优先 add-on 服务面）。"""
        act = str(action or "").strip().lower()
        if act not in ("create", "restore", "delete"):
            return None
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/backups/{act}",
                json=body,
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_patrol_trigger(self) -> dict[str, Any] | None:
        """触发巡检（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/patrol/trigger",
                json={},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_energy(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取能耗统计（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/energy",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                return self._build_status_result(resp.status, data)
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_ai_scene_ops(self, path_suffix: str, body: dict[str, Any]) -> dict[str, Any] | None:
        """执行 AI 场景扩展操作（analyze/create-from-text）。"""
        suffix = str(path_suffix or "").strip().lower().lstrip("/")
        allowed = {
            "ai-scenes/analyze",
            "ai-scenes/create-from-text",
        }
        if suffix not in allowed:
            return None
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}/{suffix}",
                json=body if isinstance(body, dict) else {},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def post_ai_scene_delete_fallback(self, scene_id: int) -> dict[str, Any] | None:
        """删除场景（canonical /ai-scenes/{id}）。"""
        sid = int(scene_id)
        endpoints = [
            (f"/ai-scenes/{sid}", {}),
        ]
        for path, payload in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "id": sid}
                    result.setdefault("id", sid)
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_ai_scene_archive(self, scene_id: int) -> dict[str, Any] | None:
        """归档场景（canonical /ai-scenes/{id}/archive）。"""
        sid = int(scene_id)
        path = f"/ai-scenes/{sid}/archive"
        try:
            session = await self._get_session()
            async with session.post(
                f"{self._base}{path}",
                json={"id": sid},
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "id": sid}
                result.setdefault("id", sid)
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)

    async def get_vision_cameras(self) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取视觉摄像头列表（优先 add-on 服务面）。"""
        for path in ("/vision/cameras",):
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self._base}{path}",
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return [x for x in data if isinstance(x, dict)]
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_vision_camera_action(self, action: str, body: dict[str, Any]) -> dict[str, Any] | None:
        """执行视觉摄像头动作（register/delete）。"""
        act = str(action or "").strip().lower()
        if act not in ("register", "delete"):
            return None
        endpoints = [
            f"/vision/cameras/{act}",
        ]
        payload = body if isinstance(body, dict) else {}
        for path in endpoints:
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300, "action": act}
                    result.setdefault("action", act)
                    if resp.status >= 400:
                        result.setdefault("error", f"http_{resp.status}")
                        result.setdefault("error_type", "http_error")
                        result.setdefault("retryable", resp.status in (408, 429, 500, 502, 503, 504))
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                _LOGGER.debug("[AddOnClient] post_vision_camera_action exception: %s", self._redact_sensitive(str(exc)))
                return self._handle_request_exception(exc)
        return None

    async def get_vision_zones(self, camera_id: str) -> list[dict[str, Any]] | dict[str, Any] | None:
        """获取视觉 zones（优先 add-on 服务面）。"""
        payload = {"camera_id": str(camera_id or "").strip()}
        for path in ("/vision/zones",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return [x for x in data if isinstance(x, dict)]
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def save_vision_zone(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """保存视觉 zone（优先 add-on 服务面）。"""
        payload = body if isinstance(body, dict) else {}
        for path in ("/vision/zones/save",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    if resp.status == 200 and isinstance(data, dict):
                        return data
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def get_system_brand(self) -> dict[str, Any] | None:
        """获取系统品牌信息（优先 add-on 服务面）。"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base}/system/brand",
                headers=self._auth_headers,
                timeout=_HEALTH_TIMEOUT,
            ) as resp:
                if resp.status in (404, 405):
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                result["__status"] = resp.status
                return result
        except Exception as exc:
            return self._handle_request_exception(exc)
        return None

    async def get_system_settings(self) -> dict[str, Any] | None:
        """读取系统设置（优先 add-on 服务面）。"""
        for path in ("/settings/system",):
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self._base}{path}",
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            return data
                        return self._build_status_result(resp.status, data)
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_system_settings(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """写入系统设置（优先 add-on 服务面）。"""
        payload = body if isinstance(body, dict) else {}
        for path in ("/settings/system",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            return data
                        return self._build_status_result(resp.status, data)
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def get_mcp_status(self) -> dict[str, Any] | None:
        """获取 MCP 状态（优先 add-on 服务面）。"""
        for path in ("/mcp/status",):
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self._base}{path}",
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                    if resp.status >= 400:
                        result.setdefault("error", f"http_{resp.status}")
                        result.setdefault("error_type", "http_error")
                        result.setdefault("retryable", resp.status in (408, 429, 500, 502, 503, 504))
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                _LOGGER.debug("[AddOnClient] get_mcp_status exception: %s", self._redact_sensitive(str(exc)))
                return self._handle_request_exception(exc)
        return None

    async def post_mcp_settings(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """写入 MCP 设置（优先 add-on 服务面）。"""
        payload = body if isinstance(body, dict) else {}
        for path in ("/mcp/settings",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            return data
                        return self._build_status_result(resp.status, data)
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def post_capability_dry_run(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """请求 capability dry-run 规划结果（仅建议，不执行）。"""
        payload = body if isinstance(body, dict) else {}
        for path in ("/capability/dry-run",):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self._base}{path}",
                    json=payload,
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    result = data if isinstance(data, dict) else {"ok": 200 <= resp.status < 300}
                    result.setdefault("ok", 200 <= resp.status < 300)
                    if resp.status >= 400:
                        result["ok"] = False
                        result.setdefault("error", f"http_{resp.status}")
                        result.setdefault("error_type", "http_error")
                        result.setdefault("retryable", resp.status in (408, 429, 500, 502, 503, 504))
                    result["__status"] = resp.status
                    return result
            except Exception as exc:
                return self._handle_request_exception(exc)
        return None

    async def get_diagnostics(self) -> dict[str, Any] | None:
        """获取 Add-on 诊断信息（优先 /system/diagnostics，兼容 /diagnostics）。"""
        for path in ("/system/diagnostics", "/diagnostics"):
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self._base}{path}",
                    headers=self._auth_headers,
                    timeout=_HEALTH_TIMEOUT,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data if isinstance(data, dict) else {}
                    if resp.status in (404, 405):
                        continue
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    return self._build_status_result(resp.status, data)
            except Exception as exc:
                return self._handle_request_exception(exc)
        return {}

    async def close(self) -> None:
        """关闭 HTTP Session，在 HA 卸载集成时调用。"""
        if self._session and not self._session.closed:
            await self._session.close()


