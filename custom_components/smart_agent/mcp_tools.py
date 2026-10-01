from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .mcp_tool_context import McpToolContext, _mcp_args, mcp_text
from .mcp_tool_control import smart_device_list, smart_control
from .mcp_tool_history import (
    smart_recent_decisions,
    smart_decision_stats,
    smart_correction_analysis,
)
from .mcp_tool_rooms import smart_room_status
from .mcp_tool_health import smart_health_check

_LOGGER = logging.getLogger(__name__)


def get_mcp_tools() -> list[dict]:
    """Returns a list of MCP tool definitions exposed to external LLMs."""
    return [
        {
            "name": "smart_control",
            "description": "通过 AI SmartAgent 控制智能家居设备。此调用会受到 P0-P4 分级保护拦截，绝对安全。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "被控实体 ID (例如: light.living_room_light)",
                    },
                    "command_text": {
                        "type": "string",
                        "description": "控制指令描述 (例如: '打开灯', '亮度调整为 50%')",
                    },
                },
                "required": ["entity_id", "command_text"],
            },
        },
        {
            "name": "smart_device_list",
            "description": "获取 AI SmartAgent 纳管的所有设备列表及其当前状态",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "room": {"type": "string", "description": "（可选）只查询指定房间内的设备"},
                },
            },
        },
        {
            "name": "smart_recent_decisions",
            "description": (
                "查询 AI SmartAgent 最近 N 次推理决策记录，包括：触发原因、场景识别、"
                "置信度、执行了哪些动作、被拦截了哪些动作及原因。"
                "用于排查'AI为什么没做某件事'或'AI为什么做了某件事'。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回记录数（1-20，默认 5）",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
            },
        },
        {
            "name": "smart_decision_stats",
            "description": (
                "统计 AI SmartAgent 在指定天数内的决策质量指标，包括："
                "总决策次数、执行率、拦截率、平均置信度、用户修正次数。"
                "用于评估 AI 是否在正常工作，是否过于激进或保守。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "统计周期（1-30 天，默认 7）",
                        "minimum": 1,
                        "maximum": 30,
                    },
                },
            },
        },
        {
            "name": "smart_correction_analysis",
            "description": (
                "分析 AI SmartAgent 的用户修正记录，识别冲突修正"
                "（同一设备既被修正'开'又被修正'关'）、高频抑制设备、以及可能需要清理的过期修正。"
                "用于排查 AI 为什么不执行某个动作，以及修正记忆是否已经混乱。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "（可选）只分析指定房间的修正记录",
                    },
                },
            },
        },
        {
            "name": "smart_room_status",
            "description": (
                "查询指定房间（或所有房间）的实时状态：人员占用情况 + 设备开关状态。"
                "可用于判断某个房间当前是否有人、灯光是否开着等。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "（可选）房间名称，留空返回所有房间摘要",
                    },
                },
            },
        },
        {
            "name": "smart_health_check",
            "description": (
                "全面检查 AI SmartAgent 系统健康状态，返回：\n"
                "① 系统运行时长与设备在线率（包含不可用设备明细）\n"
                "② DecisionCache 缓存命中统计（到达/离开分类）\n"
                "③ Phase 3 就绪进度（距命中率目标还差多少）\n"
                "④ 设备可靠性：过去 7 天动作失败次数 Top 5（对应 SYS-01 风险）\n"
                "⑤ 行为戒律质量：已生成数量、冲突数量\n"
                "建议每周查询一次，了解系统运行质量并判断是否可以开启 Phase 3。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


_HANDLERS = (
    ("smart_device_list", smart_device_list),
    ("smart_control", smart_control),
    ("smart_recent_decisions", smart_recent_decisions),
    ("smart_decision_stats", smart_decision_stats),
    ("smart_correction_analysis", smart_correction_analysis),
    ("smart_room_status", smart_room_status),
    ("smart_health_check", smart_health_check),
)


async def execute_mcp_tool(hass: HomeAssistant, params: dict, hass_user=None) -> dict:
    """Dispatch existing tools with the original coordinator and owner context."""
    tool_name = params.get("name")
    tool_args = _mcp_args(params.get("arguments", {}))
    coordinator = None
    for coord in hass.data.get(DOMAIN, {}).values():
        coordinator = coord
        break
    if not coordinator:
        _LOGGER.error("[MCP Tools] 找不到 SmartAgent Coordinator 实例")
        return mcp_text("错误: 找不到 SmartAgent Coordinator 实例。", is_error=True)
    _LOGGER.info("[MCP Tools] 执行工具: %s", tool_name)
    context = McpToolContext(hass, coordinator, tool_args, hass_user)
    for name, handler in _HANDLERS:
        if tool_name == name:
            return await handler(context)
    _LOGGER.warning("[MCP Tools] 未知工具调用: %s", tool_name)
    return mcp_text(f"错误: 找不到工具 {tool_name}", is_error=True)
