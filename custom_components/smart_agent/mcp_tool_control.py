"""Existing MCP tool handlers, isolated from transport dispatch."""

from __future__ import annotations
import logging
from .mcp_tool_context import McpToolContext, mcp_text
import re
from .mcp_tool_context import _mcp_string

_LOGGER = logging.getLogger("custom_components.smart_agent.mcp_tools")

# Compile injection patterns once for all control calls.
_INJECT_PATTERNS = [
    re.compile(r"ignore\s+previous", re.IGNORECASE),
    re.compile(r"disregard\s+above", re.IGNORECASE),
    re.compile(r"forget\s+instructions", re.IGNORECASE),
    re.compile(r"你现在是", re.IGNORECASE),
    re.compile(r"act\s+as\s+", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
]


async def smart_device_list(context: McpToolContext) -> dict:
    hass, coordinator, tool_args = context.hass, context.coordinator, context.arguments
    room_filter = tool_args.get("room")
    devices = []
    for eid, info in coordinator.device_info.items():
        if room_filter and info.get("room") != room_filter:
            continue
        state = hass.states.get(eid)
        s_val = state.state if state else "unknown"
        devices.append(f"{eid} ({info.get('name', eid)}): {s_val} in {info.get('room', '未知')}")

    result_text = "\n".join(devices) if devices else "未找到符合条件的设备。"
    _LOGGER.debug("[MCP Tools] 返回设备列表，共 %d 个", len(devices))
    return mcp_text(result_text)


async def smart_control(context: McpToolContext) -> dict:
    hass, coordinator, tool_args, hass_user = (
        context.hass,
        context.coordinator,
        context.arguments,
        context.user,
    )
    user = hass_user
    is_admin = bool(getattr(user, "is_admin", False))
    is_owner = bool(getattr(user, "is_owner", False))
    if user is None or not (is_admin or is_owner):
        _LOGGER.warning("[MCP Tools] 拒绝 smart_control：需要 admin/owner 权限")
        return mcp_text("错误：smart_control 仅允许管理员或 Owner 调用", is_error=True)

    eid = _mcp_string(tool_args.get("entity_id", ""))
    cmd = _mcp_string(tool_args.get("command_text", ""))

    # ── 输入验证：防止 prompt injection 和资源耗尽 ──────────────────────
    # 1. entity_id 格式校验（domain.name，仅允许小写字母/数字/下划线/点）
    if not eid or not re.fullmatch(r"[a-z_][a-z0-9_.]*\.[a-z0-9_]+", eid):
        _LOGGER.warning("[MCP Tools] 非法 entity_id: %s", eid)
        return mcp_text(f"错误：entity_id 格式无效: {eid}", is_error=True)

    # 2. entity_id 必须在托管设备列表中（防止控制未授权设备）
    if eid not in coordinator.device_info:
        _LOGGER.warning("[MCP Tools] entity_id 不在托管列表: %s", eid)
        return mcp_text(f"错误：设备 {eid} 未在 SmartAgent 托管列表中", is_error=True)

    # 3. command_text 长度限制（防止超长 prompt 导致 LLM 成本失控）
    if not cmd or len(cmd) > 200:
        _LOGGER.warning("[MCP Tools] command_text 长度非法: %d", len(cmd))
        return mcp_text("错误：command_text 为空或超过 200 字符上限", is_error=True)

    # 4. command_text 内容清洗：使用模块级预编译正则，防止提示词注入
    if any(p.search(cmd) for p in _INJECT_PATTERNS):
        _LOGGER.warning("[MCP Tools] 检测到可疑 prompt injection 模式: %s", cmd[:50])
        return mcp_text("错误：指令包含不允许的内容", is_error=True)

    # 5. 构造触发字符串（使用固定前缀防止 cmd 内容改变解析语义）
    device_name = coordinator.device_info[eid].get("name", eid)
    trigger_str = f"[MCP外部调用指令] 对设备「{device_name}」({eid}) 执行: {cmd[:200]}"
    _LOGGER.info("[MCP Tools] 接收到控制任务: %s", trigger_str)

    # 通过异步任务派发给慢脑处理（受完整保护层拦截）
    hass.async_create_task(coordinator._run_inference(trigger_str))

    return mcp_text(f"指令已安全提交: {trigger_str[:100]}")
