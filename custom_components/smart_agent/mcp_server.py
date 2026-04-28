from __future__ import annotations
import logging
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class SmartAgentMCPEndpointView(HomeAssistantView):
    """
    Phase 8B: MCP (Model Context Protocol) Server Endpoint.
    对外暴露安全的 HTTP POST 接口，响应 MCP 原生 tool/list 和 tool/call 请求。
    使用 HA 的原生 Long-Lived Token 进行鉴权拦截 (requires_auth=True)。
    """
    url = "/api/smart_agent/mcp"
    name = "api:smart_agent:mcp"
    requires_auth = True  # HA 会自动拦截未携带正确 Bearer Token 的请求

    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle MCP tool call requests."""
        try:
            req_data = await request.json()
            method = req_data.get("method")
            msg_id = req_data.get("id")
            
            if method == "tools/list":
                from .mcp_tools import get_mcp_tools
                return self.json({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": get_mcp_tools()
                    }
                })
            elif method == "tools/call":
                from .mcp_tools import execute_mcp_tool
                result = await execute_mcp_tool(
                    self._hass,
                    req_data.get("params", {}),
                    hass_user=request.get("hass_user"),
                )
                return self.json({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                })
            else:
                return self.json({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method {method} not found"}
                })
        except Exception as exc:
            _LOGGER.exception("MCP server error: %s", exc)
            return self.json({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(exc)}
            }, status=500)
