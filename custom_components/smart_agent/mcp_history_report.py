"""Existing recent-decision and correction report projections."""

from __future__ import annotations
from typing import Any
import json
from .mcp_tool_context import mcp_text


def _action_summary(r: dict, actions_raw: Any, coordinator: Any) -> str:
    action_summary = ""
    try:
        raw_actions = r.get("actions")
        acts = raw_actions if isinstance(raw_actions, list) else json.loads(actions_raw or "[]")
        if acts:
            parts = []
            for a in acts[:3]:
                eid = a.get("entity_id", "")
                svc = a.get("service", "")
                rsn = a.get("reason", "")[:30]
                name = coordinator.device_info.get(eid, {}).get("name", eid)
                parts.append(f"{name}({svc})" + (f"：{rsn}" if rsn else ""))
            action_summary = "；".join(parts)
            if len(acts) > 3:
                action_summary += f"（共 {len(acts)} 个）"
    except Exception:
        pass
    return action_summary


def decision_record(r: dict, coordinator: Any) -> str:
    t = r.get("time", "")
    trig = r.get("trigger_summary", "")
    scene = r.get("scene_desc", "")
    conf = r.get("confidence")  # 可能为 NULL
    a_total = r.get("action_count", 0) or 0
    a_disp = r.get("dispatched_count", 0) or 0
    a_block = r.get("blocked_count", 0) or 0
    status = r.get("status", "")
    actions_raw = r.get("actions_json", "[]")

    # 解析 actions_json 取前 3 条摘要
    action_summary = _action_summary(r, actions_raw, coordinator)

    status_label = {
        "success": "✅已自动执行",
        "partial": "⚠️部分执行",
        "pending": "⏳等待确认",
        "auto": "✅已自动执行",
        "approved": "✅用户批准",
        "blocked": "🚫已拦截",
        "failed": "❌执行失败",
    }.get(status or "", status or "未知")
    exec_info = f"执行 {a_disp}/{a_total}" if a_total else ""
    block_info = f"  拦截 {a_block} 个" if a_block else ""
    return (
        f"📌 {t}\n   触发：{(trig or '')[:80]}\n   场景：{scene or '未知'} | 置信度：{(conf if conf is not None else '?')}% | {exec_info}{block_info} | {status_label}\n"
        + (f"   动作：{action_summary}\n" if action_summary else "   动作：（无）\n")
    )


def correction_report(
    coordinator: Any,
    room_filter: str,
    stats_rows: list[dict],
    conflict_rows: list[dict],
    top_rows: list[dict],
) -> dict:
    stats = stats_rows[0] if stats_rows else {}
    entity_cnt = stats.get("entity_cnt", 0) or 0
    record_cnt = stats.get("record_cnt", 0) or 0
    total_events = stats.get("total_events", 0) or 0

    title = f"{'房间「' + room_filter + '」' if room_filter else '全局'}修正记忆分析\n"
    lines = [
        title,
        f"受影响设备：{entity_cnt} 个 | 修正记录：{record_cnt} 条 | 累计修正次数：{total_events}\n",
    ]

    # ── 冲突修正 ──────────────────────────────────────────────────────────
    if conflict_rows:
        lines.append("⚠️  冲突修正（同一设备有互相矛盾的修正记录，AI 会混乱）：")
        for r in conflict_rows:
            eid = r.get("entity_id", "")
            room_name = r.get("room", "")
            services = r.get("services", "")
            count = r.get("total_count", 0)
            last_t = r.get("last_time", "")
            dev_name = coordinator.device_info.get(eid, {}).get("name", eid)
            lines.append(
                f"  • {dev_name}（{eid}）[{room_name}]\n"
                f"    修正方向：{services}  累计 {count} 次  最近：{last_t}\n"
                f"    → 建议：在前端手动删除该设备的旧修正记录，保留最新一条。\n"
            )
    else:
        lines.append("✅ 未发现冲突修正（各设备修正方向一致）。\n")

    # ── 高频修正（AI 最受抑制的设备）─────────────────────────────────────
    if top_rows:
        lines.append("\n📋 修正频率 TOP 设备（影响 AI 自主操控能力）：")
        for r in top_rows:
            eid = r.get("entity_id", "")
            room_name = r.get("room", "")
            svc = r.get("ai_service", "")
            u_state = r.get("user_state", "")
            count = r.get("correction_count", 0)
            last_t = r.get("time", "")
            presence = r.get("presence_context", "any")
            presence_label = {"occupied": "有人时", "empty": "无人时", "any": "不限时机"}.get(
                presence, presence
            )
            dev_name = coordinator.device_info.get(eid, {}).get("name", eid)
            lines.append(
                f"  {count:>3}次  {dev_name}（{room_name}）"
                f"  AI 尝试 {svc} → 用户改为 {u_state}  [{presence_label}]  最近：{last_t}"
            )

    if not conflict_rows and total_events < 5:
        lines.append("\n ℹ️ 修正记录较少，AI 尚在学习阶段，行为可能不够稳定。")

    return mcp_text("\n".join(lines))
