"""
Pairing API for Smart Control Screen.

设计原则:
- /api/smart_agent/pair         - 免认证（中控屏调用）
- /api/smart_agent/auth_page    - 免认证（手机扫码打开的 HTML 页）
- /api/smart_agent/pair_confirm - 免认证（auth_page 里的 JS 调用，用配对码作为共享密钥）
- 安全性由"6位随机配对码 + 局域网隔离 + 5分钟过期"三重保护
"""
from __future__ import annotations

import secrets
import time
import logging
from datetime import timedelta
from homeassistant.components.http import HomeAssistantView
from homeassistant.auth import models as auth_models

_LOGGER = logging.getLogger(__name__)


def _derive_ha_url(request) -> str:
    """从 HTTP 请求中推导出可被手机/中控屏访问的 HA 地址。"""
    host = request.host  # e.g. "192.168.2.9:8123"
    scheme = "https" if request.secure else "http"
    return f"{scheme}://{host}"


class SmartAgentPairingView(HomeAssistantView):
    """API 视图：处理中控屏配对请求。"""
    url = "/api/smart_agent/pair"
    name = "api:smart_agent:pair"
    requires_auth = False

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._pending_pairs: dict = {}

    async def get(self, request):
        """旧配对入口已下线：统一迁移到 /api/v1/device/pair/start。"""
        return self.json(
            {
                "ok": False,
                "error": "deprecated_endpoint",
                "error_type": "endpoint_removed",
                "retryable": False,
                "message": "该入口已下线，请使用 /api/v1/device/pair/start",
            },
            status_code=410,
        )

class SmartAgentAuthPageView(HomeAssistantView):
    """手机扫码后的确认页面 — 必须 requires_auth=False，否则手机打不开。"""
    url = "/api/smart_agent/auth_page"
    name = "api:smart_agent:auth_page"
    requires_auth = False

    def __init__(self, coordinator):
        self.coordinator = coordinator

    async def get(self, request):
        """旧授权页入口已下线：统一迁移到 /api/v1/device/pair/start。"""
        return self.json(
            {
                "ok": False,
                "error": "deprecated_endpoint",
                "error_type": "endpoint_removed",
                "retryable": False,
                "message": "该入口已下线，请使用 /api/v1/device/pair/start",
            },
            status_code=410,
        )

class SmartAgentPairConfirmView(HomeAssistantView):
    """处理确认授权 — requires_auth=True：调用方必须持有有效的 HA Bearer Token。

    安全设计：
    - 配对码 (6位数字) 作为会话绑定凭证（防重放）
    - requires_auth=True 确保只有已登录 HA 的用户才能触发令牌铸造
    - 两层保护：HA 身份认证 + 时效配对码，缺一不可
    - CORS 仅允许同源（移除通配符），防止跨站请求伪造
    """
    url = "/api/smart_agent/pair_confirm"
    name = "api:smart_agent:pair_confirm"
    requires_auth = True  # ← P0修复：必须持有有效 HA 会话才能铸造 Owner Token

    def __init__(self, coordinator):
        self.coordinator = coordinator

    async def post(self, request):
        """旧配对确认入口已下线：统一迁移到 /api/v1/device/pair/confirm。"""
        return self.json(
            {
                "ok": False,
                "error": "deprecated_endpoint",
                "error_type": "endpoint_removed",
                "retryable": False,
                "message": "该入口已下线，请使用 /api/v1/device/pair/confirm",
            },
            status_code=410,
        )