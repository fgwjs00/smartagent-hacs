"""Existing MCP tool handlers, isolated from transport dispatch."""

from __future__ import annotations
import logging
from .mcp_tool_context import McpToolContext, mcp_text
from .service_contracts import STATEFUL_EXECUTION_DOMAINS

_LOGGER = logging.getLogger("custom_components.smart_agent.mcp_tools")


async def smart_room_status(context: McpToolContext) -> dict:
    hass, coordinator, tool_args = context.hass, context.coordinator, context.arguments
    room_filter: str = tool_args.get("room", "")
    occ_map = (
        coordinator._get_room_occupancy_map()
        if hasattr(coordinator, "_get_room_occupancy_map")
        else {}
    )
    # 按房间组织设备
    room_devices = _room_devices(hass, coordinator, room_filter)

    # 若房间名称有效但所有设备都是 off（被过滤），仍需展示占用状态；
    # 只有当房间名称既不在 occ_map 也无设备时，才视为"房间不存在"
    room_in_occ = room_filter and room_filter in occ_map
    if not room_devices and room_filter and not room_in_occ:
        return mcp_text(f"房间「{room_filter}」未找到，请确认房间名称是否正确。")

    lines = [f"{'房间「' + room_filter + '」' if room_filter else '全屋'}实时状态\n"]
    rooms_to_show = (
        [room_filter]
        if room_filter
        else sorted(set(list(occ_map.keys()) + list(room_devices.keys())))
    )

    for room in rooms_to_show:
        _append_room_summary(lines, room, occ_map, room_devices, room_filter)

    # 当指定房间时，附加该房间的 AI 行为戒律（来自 Phase 3 Lite correction_lessons）
    # 帮助用户理解 AI 在该房间的决策逻辑，以及是否存在冲突修正
    await _append_room_lessons(hass, coordinator, room_filter, lines)

    return mcp_text("\n".join(lines))


def _room_devices(hass, coordinator, room_filter: str) -> dict[str, list[str]]:
    room_devices: dict[str, list[str]] = {}
    for eid, info in coordinator.device_info.items():
        r = info.get("room", "未知")
        if room_filter and r != room_filter:
            continue
        domain = eid.split(".")[0] if "." in eid else ""
        if domain not in STATEFUL_EXECUTION_DOMAINS:
            continue
        st = hass.states.get(eid)
        state_val = st.state if st else "unknown"
        if state_val in ("unavailable", "unknown"):
            continue
        room_devices.setdefault(r, []).append(f"  - {info.get('name', eid)}：{state_val}")
    return room_devices


def _append_room_summary(
    lines: list[str], room: str, occ_map: dict, room_devices: dict, room_filter: str
) -> None:
    sensors = occ_map.get(room, [])
    is_occ = any(s == "on" for _, s in sensors)
    is_unknown = not sensors or all(s in ("unknown", "unavailable") for _, s in sensors)
    occ_label = "🟢 有人" if is_occ else ("❓ 未知" if is_unknown else "⚫ 无人")

    devs = room_devices.get(room, [])
    on_devs = [
        d for d in devs if d.split("：")[-1].strip() in ("on", "open", "heat", "cool", "auto")
    ]
    dev_summary = f"{len(on_devs)} 个设备开启" if on_devs else "无设备开启"

    lines.append(f"🏠 {room}  {occ_label}  {dev_summary}")
    if room_filter and devs:
        lines.extend(devs)


async def _append_room_lessons(hass, coordinator, room_filter: str, lines: list[str]) -> None:
    if room_filter:
        try:
            lesson_rows = await hass.async_add_executor_job(
                coordinator._db.query,
                """SELECT lesson_text, correction_count, confidence, is_conflicted,
                              presence_context, updated
                       FROM correction_lessons
                       WHERE room = ?
                       ORDER BY is_conflicted DESC, correction_count DESC
                       LIMIT 10""",
                (room_filter,),
            )
            if lesson_rows:
                lines.append(f"\n📚 AI 行为戒律（来自学习历史，共 {len(lesson_rows)} 条）：")
                for lr in lesson_rows:
                    lesson = lr.get("lesson_text", "")
                    conf = lr.get("confidence") or 0.0
                    updated = (lr.get("updated") or "")[:10]
                    conf_pct = f"{conf * 100:.0f}%"
                    conflict_tag = " ⚠️冲突" if lr.get("is_conflicted") else ""
                    lines.append(f"  {lesson} （可信度 {conf_pct}{conflict_tag}，更新 {updated}）")
            else:
                lines.append("\n📚 AI 行为戒律：暂无（修正次数不足 2 次，或每日维护尚未运行）")
        except Exception as _exc:
            _LOGGER.debug("[MCP Tools] 查询 correction_lessons 失败: %s", _exc)
