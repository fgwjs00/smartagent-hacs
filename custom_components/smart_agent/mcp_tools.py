from __future__ import annotations
import asyncio
import json
import logging
import re
import time as _time

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Prompt 注入防护：模块级预编译，避免每次 smart_control 调用时重建
_INJECT_PATTERNS = [
    re.compile(r"ignore\s+previous",    re.IGNORECASE),
    re.compile(r"disregard\s+above",    re.IGNORECASE),
    re.compile(r"forget\s+instructions",re.IGNORECASE),
    re.compile(r"你现在是",              re.IGNORECASE),
    re.compile(r"act\s+as\s+",          re.IGNORECASE),
    re.compile(r"jailbreak",            re.IGNORECASE),
    re.compile(r"DAN\s+mode",           re.IGNORECASE),
]


def get_mcp_tools() -> list[dict]:
    """Returns a list of MCP tool definitions exposed to external LLMs."""
    return [
        {
            "name": "smart_control",
            "description": "通过 AI SmartAgent 控制智能家居设备。此调用会受到 P0-P4 分级保护拦截，绝对安全。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "被控实体 ID (例如: light.living_room_light)"},
                    "command_text": {"type": "string", "description": "控制指令描述 (例如: '打开灯', '亮度调整为 50%')"},
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


async def execute_mcp_tool(hass: HomeAssistant, params: dict, hass_user=None) -> dict:
    """Execute the requested MCP tool based on params."""
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})
    
    coordinator = None
    for coord in hass.data.get(DOMAIN, {}).values():
        coordinator = coord
        break
        
    if not coordinator:
        _LOGGER.error("[MCP Tools] 找不到 SmartAgent Coordinator 实例")
        return {"content": [{"type": "text", "text": "错误: 找不到 SmartAgent Coordinator 实例。"}], "isError": True}

    _LOGGER.info("[MCP Tools] 执行工具: %s", tool_name)

    if tool_name == "smart_device_list":
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
        return {"content": [{"type": "text", "text": result_text}]}

    elif tool_name == "smart_control":
        user = hass_user
        is_admin = bool(getattr(user, "is_admin", False))
        is_owner = bool(getattr(user, "is_owner", False))
        if user is None or not (is_admin or is_owner):
            _LOGGER.warning("[MCP Tools] 拒绝 smart_control：需要 admin/owner 权限")
            return {
                "content": [{"type": "text", "text": "错误：smart_control 仅允许管理员或 Owner 调用"}],
                "isError": True,
            }

        eid = tool_args.get("entity_id", "")
        cmd = tool_args.get("command_text", "")

        # ── 输入验证：防止 prompt injection 和资源耗尽 ──────────────────────
        # 1. entity_id 格式校验（domain.name，仅允许小写字母/数字/下划线/点）
        if not eid or not re.fullmatch(r"[a-z_][a-z0-9_.]*\.[a-z0-9_]+", eid):
            _LOGGER.warning("[MCP Tools] 非法 entity_id: %s", eid)
            return {"content": [{"type": "text", "text": f"错误：entity_id 格式无效: {eid}"}], "isError": True}

        # 2. entity_id 必须在托管设备列表中（防止控制未授权设备）
        if eid not in coordinator.device_info:
            _LOGGER.warning("[MCP Tools] entity_id 不在托管列表: %s", eid)
            return {"content": [{"type": "text", "text": f"错误：设备 {eid} 未在 SmartAgent 托管列表中"}], "isError": True}

        # 3. command_text 长度限制（防止超长 prompt 导致 LLM 成本失控）
        if not cmd or len(cmd) > 200:
            _LOGGER.warning("[MCP Tools] command_text 长度非法: %d", len(cmd))
            return {"content": [{"type": "text", "text": "错误：command_text 为空或超过 200 字符上限"}], "isError": True}

        # 4. command_text 内容清洗：使用模块级预编译正则，防止提示词注入
        if any(p.search(cmd) for p in _INJECT_PATTERNS):
            _LOGGER.warning("[MCP Tools] 检测到可疑 prompt injection 模式: %s", cmd[:50])
            return {"content": [{"type": "text", "text": "错误：指令包含不允许的内容"}], "isError": True}

        # 5. 构造触发字符串（使用固定前缀防止 cmd 内容改变解析语义）
        device_name = coordinator.device_info[eid].get("name", eid)
        trigger_str = f"[MCP外部调用指令] 对设备「{device_name}」({eid}) 执行: {cmd[:200]}"
        _LOGGER.info("[MCP Tools] 接收到控制任务: %s", trigger_str)

        # 通过异步任务派发给慢脑处理（受完整保护层拦截）
        hass.async_create_task(coordinator._run_inference(trigger_str))

        return {"content": [{"type": "text", "text": f"指令已安全提交: {trigger_str[:100]}"}]}

    elif tool_name == "smart_recent_decisions":
        limit = min(max(int(tool_args.get("limit") or 5), 1), 20)
        try:
            rows = await hass.async_add_executor_job(
                coordinator._db.query,
                """SELECT time, trigger_summary, scene_desc, confidence,
                          action_count, dispatched_count, blocked_count, status, actions_json
                   FROM action_transactions
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            )
        except Exception as exc:
            _LOGGER.warning("[MCP Tools] 查询 action_transactions 失败: %s", exc)
            return {"content": [{"type": "text", "text": f"查询失败: {exc}"}], "isError": True}

        if not rows:
            return {"content": [{"type": "text", "text": "暂无决策记录。AI 尚未执行过任何推理。"}]}

        lines = [f"最近 {len(rows)} 条 AI 决策记录：\n"]
        for r in rows:
            t       = r.get("time", "")
            trig    = r.get("trigger_summary", "")
            scene   = r.get("scene_desc", "")
            conf      = r.get("confidence")         # 可能为 NULL
            a_total   = r.get("action_count", 0) or 0
            a_disp    = r.get("dispatched_count", 0) or 0
            a_block   = r.get("blocked_count", 0) or 0
            status    = r.get("status", "")
            actions_raw = r.get("actions_json", "[]")

            # 解析 actions_json 取前 3 条摘要
            action_summary = ""
            try:
                acts = json.loads(actions_raw or "[]")
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

            status_label = {
                "success":  "✅已自动执行",
                "partial":  "⚠️部分执行",
                "pending":  "⏳等待确认",
                "auto":     "✅已自动执行",
                "approved": "✅用户批准",
                "blocked":  "🚫已拦截",
                "failed":   "❌执行失败",
            }.get(status or "", status or "未知")
            exec_info = f"执行 {a_disp}/{a_total}" if a_total else ""
            block_info = f"  拦截 {a_block} 个" if a_block else ""
            lines.append(
                f"📌 {t}\n"
                f"   触发：{(trig or '')[:80]}\n"
                f"   场景：{scene or '未知'} | 置信度：{conf if conf is not None else '?'}%"
                f" | {exec_info}{block_info} | {status_label}\n"
                + (f"   动作：{action_summary}\n" if action_summary else "   动作：（无）\n")
            )

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    elif tool_name == "smart_decision_stats":
        days = min(max(int(tool_args.get("days") or 7), 1), 30)
        date_param = (f"-{days} days",)
        try:
            # 三个独立查询并发执行，节省串行等待时间
            txn_rows, corr_rows, cache_rows = await asyncio.gather(
                hass.async_add_executor_job(
                    coordinator._db.query,
                    """SELECT
                           COUNT(*) as total,
                           SUM(CASE WHEN dispatched_count > 0 THEN 1 ELSE 0 END) as executed,
                           SUM(CASE WHEN blocked_count > 0 AND dispatched_count = 0 THEN 1 ELSE 0 END) as blocked,
                           AVG(confidence) as avg_conf,
                           SUM(action_count) as total_actions,
                           SUM(dispatched_count) as total_dispatched,
                           SUM(blocked_count) as total_blocked
                       FROM action_transactions
                       WHERE time >= datetime('now', ?)""",
                    date_param,
                ),
                hass.async_add_executor_job(
                    coordinator._db.query,
                    "SELECT COUNT(*) AS cnt FROM corrections WHERE time >= datetime('now', ?)",
                    date_param,
                ),
                hass.async_add_executor_job(
                    coordinator._db.query,
                    """SELECT
                           COUNT(*) AS total_entries,
                           COUNT(DISTINCT trigger_room) AS rooms,
                           SUM(hit_count) AS total_hits,
                           AVG(hit_count) AS avg_hits,
                           MAX(last_hit) AS last_hit
                       FROM decision_cache""",
                    (),
                ),
            )
        except Exception as exc:
            _LOGGER.warning("[MCP Tools] 查询决策统计失败: %s", exc)
            return {"content": [{"type": "text", "text": f"查询失败: {exc}"}], "isError": True}

        row = txn_rows[0] if txn_rows else {}
        total        = row.get("total", 0) or 0
        executed     = row.get("executed", 0) or 0
        blocked_only = row.get("blocked", 0) or 0
        avg_conf     = row.get("avg_conf")
        t_actions    = row.get("total_actions", 0) or 0
        t_disp       = row.get("total_dispatched", 0) or 0
        t_blocked    = row.get("total_blocked", 0) or 0
        corr_row     = corr_rows[0] if corr_rows else {}
        corrections  = corr_row.get("cnt", 0) or 0
        cache_row    = cache_rows[0] if cache_rows else {}
        cache_entries = cache_row.get("total_entries", 0) or 0
        cache_rooms   = cache_row.get("rooms", 0) or 0
        cache_hits    = cache_row.get("total_hits", 0) or 0
        cache_avg     = cache_row.get("avg_hits") or 0.0
        cache_last    = cache_row.get("last_hit") or "无"

        exec_rate  = f"{executed / total * 100:.0f}%" if total else "N/A"
        block_rate = f"{t_blocked / t_actions * 100:.0f}%" if t_actions else "N/A"
        conf_str   = f"{avg_conf:.0f}%" if avg_conf is not None else "N/A"

        text = (
            f"📊 过去 {days} 天 AI 决策质量统计\n\n"
            f"总推理次数：{total}\n"
            f"有动作执行：{executed} 次（执行率 {exec_rate}）\n"
            f"纯拦截（无执行）：{blocked_only} 次\n"
            f"平均置信度：{conf_str}\n"
            f"动作明细：提案 {t_actions} 个 / 执行 {t_disp} 个 / 拦截 {t_blocked} 个\n"
            f"  动作拦截率：{block_rate}\n"
            f"用户修正次数：{corrections} 次\n\n"
        )

        # Phase 1 DecisionCache 命中情况
        if cache_entries > 0:
            cache_last_str = cache_last[:16] if cache_last and cache_last != "无" else "无"
            text += (
                f"⚡ DecisionCache（AI 快路径缓存）\n"
                f"  缓存条目：{cache_entries} 个（覆盖 {cache_rooms} 个房间）\n"
                f"  历史命中：{cache_hits} 次（均值 {cache_avg:.1f} 次/条目）\n"
                f"  最近命中：{cache_last_str}\n\n"
            )
        else:
            text += "⚡ DecisionCache：暂无缓存（正在积累 LLM 决策经验）\n\n"

        # corrections == 0 时 ratio = 0 < 0.05，同样给出 ✅ 确认
        if total:
            ratio = corrections / total
            if ratio > 0.3:
                text += "⚠️ 修正/决策比 > 30%，建议检查修正记录是否存在冲突方向。\n"
            elif ratio < 0.05:
                text += "✅ 修正率较低，AI 决策与用户习惯较为一致。\n"

        return {"content": [{"type": "text", "text": text}]}

    elif tool_name == "smart_correction_analysis":
        room_filter: str = tool_args.get("room", "")
        room_clause = "AND room = ?" if room_filter else ""
        room_params: tuple = (room_filter,) if room_filter else ()
        try:
            # 冲突修正：同一设备被纠正过"开"也被纠正过"关"
            conflict_rows, top_rows, stats_rows = await asyncio.gather(
                hass.async_add_executor_job(
                    coordinator._db.query,
                    f"""SELECT entity_id,
                               MAX(room) AS room,
                               GROUP_CONCAT(DISTINCT ai_service) AS services,
                               SUM(correction_count) AS total_count,
                               MAX(time) AS last_time
                        FROM corrections
                        WHERE 1=1 {room_clause}
                        GROUP BY entity_id
                        HAVING COUNT(DISTINCT ai_service) > 1
                        ORDER BY total_count DESC
                        LIMIT 10""",
                    room_params,
                ),
                hass.async_add_executor_job(
                    coordinator._db.query,
                    f"""SELECT entity_id, room, ai_service, user_state,
                               correction_count, time,
                               COALESCE(presence_context, 'any') AS presence_context
                        FROM corrections
                        WHERE 1=1 {room_clause}
                        ORDER BY correction_count DESC, time DESC
                        LIMIT 10""",
                    room_params,
                ),
                hass.async_add_executor_job(
                    coordinator._db.query,
                    f"""SELECT COUNT(DISTINCT entity_id) AS entity_cnt,
                               COUNT(*) AS record_cnt,
                               SUM(correction_count) AS total_events
                        FROM corrections
                        WHERE 1=1 {room_clause}""",
                    room_params,
                ),
            )
        except Exception as exc:
            _LOGGER.warning("[MCP Tools] 查询修正分析失败: %s", exc)
            return {"content": [{"type": "text", "text": f"查询失败: {exc}"}], "isError": True}

        stats = stats_rows[0] if stats_rows else {}
        entity_cnt   = stats.get("entity_cnt", 0) or 0
        record_cnt   = stats.get("record_cnt", 0) or 0
        total_events = stats.get("total_events", 0) or 0

        title = f"{'房间「' + room_filter + '」' if room_filter else '全局'}修正记忆分析\n"
        lines = [title, f"受影响设备：{entity_cnt} 个 | 修正记录：{record_cnt} 条 | 累计修正次数：{total_events}\n"]

        # ── 冲突修正 ──────────────────────────────────────────────────────────
        if conflict_rows:
            lines.append("⚠️  冲突修正（同一设备有互相矛盾的修正记录，AI 会混乱）：")
            for r in conflict_rows:
                eid       = r.get("entity_id", "")
                room_name = r.get("room", "")
                services  = r.get("services", "")
                count     = r.get("total_count", 0)
                last_t    = r.get("last_time", "")
                dev_name  = coordinator.device_info.get(eid, {}).get("name", eid)
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
                eid      = r.get("entity_id", "")
                room_name= r.get("room", "")
                svc      = r.get("ai_service", "")
                u_state  = r.get("user_state", "")
                count    = r.get("correction_count", 0)
                last_t   = r.get("time", "")
                presence = r.get("presence_context", "any")
                presence_label = {"occupied": "有人时", "empty": "无人时", "any": "不限时机"}.get(presence, presence)
                dev_name = coordinator.device_info.get(eid, {}).get("name", eid)
                lines.append(
                    f"  {count:>3}次  {dev_name}（{room_name}）"
                    f"  AI 尝试 {svc} → 用户改为 {u_state}  [{presence_label}]  最近：{last_t}"
                )

        if not conflict_rows and total_events < 5:
            lines.append("\n ℹ️ 修正记录较少，AI 尚在学习阶段，行为可能不够稳定。")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    elif tool_name == "smart_room_status":
        room_filter: str = tool_args.get("room", "")
        occ_map = coordinator._get_room_occupancy_map() if hasattr(coordinator, "_get_room_occupancy_map") else {}
        _CTRL_DOMAINS = {"light", "switch", "climate", "cover", "fan", "media_player"}

        # 按房间组织设备
        room_devices: dict[str, list[str]] = {}
        for eid, info in coordinator.device_info.items():
            r = info.get("room", "未知")
            if room_filter and r != room_filter:
                continue
            domain = eid.split(".")[0] if "." in eid else ""
            if domain not in _CTRL_DOMAINS:
                continue
            st = hass.states.get(eid)
            state_val = st.state if st else "unknown"
            if state_val in ("unavailable", "unknown"):
                continue
            room_devices.setdefault(r, []).append(
                f"  - {info.get('name', eid)}：{state_val}"
            )

        # 若房间名称有效但所有设备都是 off（被过滤），仍需展示占用状态；
        # 只有当房间名称既不在 occ_map 也无设备时，才视为"房间不存在"
        room_in_occ = room_filter and room_filter in occ_map
        if not room_devices and room_filter and not room_in_occ:
            return {"content": [{"type": "text", "text": f"房间「{room_filter}」未找到，请确认房间名称是否正确。"}]}

        lines = [f"{'房间「' + room_filter + '」' if room_filter else '全屋'}实时状态\n"]
        rooms_to_show = [room_filter] if room_filter else sorted(set(
            list(occ_map.keys()) + list(room_devices.keys())
        ))

        for room in rooms_to_show:
            sensors = occ_map.get(room, [])
            is_occ = any(s == "on" for _, s in sensors)
            is_unknown = not sensors or all(s in ("unknown", "unavailable") for _, s in sensors)
            occ_label = "🟢 有人" if is_occ else ("❓ 未知" if is_unknown else "⚫ 无人")

            devs = room_devices.get(room, [])
            on_devs = [d for d in devs if d.split("：")[-1].strip() in ("on", "open", "heat", "cool", "auto")]
            dev_summary = f"{len(on_devs)} 个设备开启" if on_devs else "无设备开启"

            lines.append(f"🏠 {room}  {occ_label}  {dev_summary}")
            if room_filter and devs:
                lines.extend(devs)

        # 当指定房间时，附加该房间的 AI 行为戒律（来自 Phase 3 Lite correction_lessons）
        # 帮助用户理解 AI 在该房间的决策逻辑，以及是否存在冲突修正
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

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    elif tool_name == "smart_health_check":
        # 并发查询四张表，避免串行等待
        try:
            cache_rows, fail_rows, lesson_rows, txn30_rows = await asyncio.gather(
                hass.async_add_executor_job(
                    coordinator._db.query,
                    """SELECT trigger_type,
                              COUNT(*) AS entries,
                              SUM(hit_count) AS hits,
                              COUNT(CASE WHEN hit_count >= 5 THEN 1 END) AS mature
                       FROM decision_cache
                       GROUP BY trigger_type""",
                    (),
                ),
                hass.async_add_executor_job(
                    coordinator._db.query,
                    """SELECT entity_id, COUNT(*) AS fail_cnt, MAX(time) AS last_fail
                       FROM action_results
                       WHERE success = 0 AND time >= datetime('now', '-7 days')
                       GROUP BY entity_id
                       ORDER BY fail_cnt DESC
                       LIMIT 5""",
                    (),
                ),
                hass.async_add_executor_job(
                    coordinator._db.query,
                    """SELECT COUNT(*) AS total,
                              SUM(is_conflicted) AS conflicted,
                              COUNT(DISTINCT room) AS rooms
                       FROM correction_lessons""",
                    (),
                ),
                hass.async_add_executor_job(
                    coordinator._db.query,
                    "SELECT COUNT(*) AS cnt FROM action_transactions WHERE time >= datetime('now', '-30 days')",
                    (),
                ),
            )
        except Exception as exc:
            _LOGGER.warning("[MCP Tools] smart_health_check 查询失败: %s", exc)
            return {"content": [{"type": "text", "text": f"查询失败: {exc}"}], "isError": True}

        addon_diag: dict = {}
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is not None:
            try:
                addon_diag = await _addon_client.get_diagnostics()
            except Exception as _addon_exc:
                _LOGGER.debug("[MCP Tools] 获取 Add-on diagnostics 失败: %s", _addon_exc)

        # ── ① 系统运行状态 ─────────────────────────────────────────────────────
        uptime_s = int(_time.time() - getattr(coordinator, "_startup_time", _time.time()))
        uptime_str = (
            f"{uptime_s // 3600}h {(uptime_s % 3600) // 60}m"
            if uptime_s >= 3600 else f"{uptime_s // 60}m {uptime_s % 60}s"
        )
        total_devices = len(coordinator.device_info)
        unavail_devs = []
        for _eid, _info in coordinator.device_info.items():
            _st = hass.states.get(_eid)
            if _st and _st.state == "unavailable":
                _name = _info.get("name", _eid)
                _room = _info.get("room", "未知")
                unavail_devs.append(f"{_name}[{_room}]")
        unavail_cnt = len(unavail_devs)
        online_rate = f"{(total_devices - unavail_cnt) / total_devices * 100:.0f}%" if total_devices else "N/A"

        lines = [
            "🩺 SmartAgent 系统健康报告\n",
            f"🔋 系统运行时长：{uptime_str}",
            f"📡 托管设备：{total_devices} 个 | 在线率：{online_rate}",
        ]
        if unavail_devs:
            lines.append(f"⚠️  不可用设备（{unavail_cnt} 个，建议检查 Zigbee/Z2M）：")
            for _d in unavail_devs[:10]:
                lines.append(f"   • {_d}")
            if len(unavail_devs) > 10:
                lines.append(f"   …（共 {unavail_cnt} 个，仅显示前 10）")
        else:
            lines.append("✅ 所有托管设备均在线")

        # ── ⑥ Frigate 僵尸实体检测（v4.11.2）──────────────────────────────────
        # 检测 HA 实体注册表中有 binary_sensor.*_person_occupancy 但
        # Frigate HTTP API 配置和 SmartAgent DB 均无对应 zone 记录的"僵尸实体"。
        # v4.11.2：使用 Frigate API 交叉校验，避免 DB 为空时的假阳性。
        try:
            from .frigate_config import get_cameras_from_frigate_api as _get_cameras

            # 从 Frigate API 获取实际 zones
            _known_zones: set[str] = set()
            try:
                _yml_cams, _ = await _get_cameras()
                for _cam in _yml_cams:
                    _known_zones.add(str(_cam.get("camera_id", "")).lower())
                    for _z in _cam.get("zones", []):
                        _known_zones.add(str(_z.get("zone_id", "")).lower())
            except Exception:
                pass

            # 从 SmartAgent DB 补充
            _fz_rows = coordinator._db.query("SELECT zone_id FROM frigate_zones")
            for _fz in (_fz_rows or []):
                _known_zones.add(str(_fz.get("zone_id", "")).lower())
            _fc_rows = coordinator._db.query("SELECT camera_id FROM frigate_cameras")
            for _fc in (_fc_rows or []):
                _known_zones.add(str(_fc.get("camera_id", "")).lower())

            frigate_zombie_entities: list[str] = []
            _suffix = "_person_occupancy"

            if _known_zones:
                # 仅在能获取到 zone 信息时才做判断（避免 Frigate 离线时的假阳性）
                for _state in hass.states.async_all():
                    _eid_lower = _state.entity_id.lower()
                    if not _eid_lower.endswith(_suffix):
                        continue
                    _zone_cand = _eid_lower.split(".")[-1][: -len(_suffix)]
                    if _zone_cand not in _known_zones:
                        frigate_zombie_entities.append(_state.entity_id)

            if frigate_zombie_entities:
                lines.append("\n🚨 Frigate 僵尸实体（须手动处理）")
                lines.append(
                    "  以下实体在 HA 注册表中存在，但 Frigate 配置中已不存在对应 zone，"
                    "导致 HA 持续输出 \"Forced update failed\" 错误并使人数计数恒为 0："
                )
                for _ze in frigate_zombie_entities:
                    lines.append(f"   ⛔ {_ze}")
                lines.append(
                    "  修复（二选一）：\n"
                    "  方法 A（推荐）：在 Frigate config.yml 中重新添加对应 zone，重启 Frigate。\n"
                    "  方法 B（快速）：HA → 设置 → 设备和服务 → 实体 → 搜索上述实体 → 禁用/删除 → 重启 HA。"
                )
            elif _known_zones:
                lines.append("\n✅ 未发现 Frigate 僵尸实体")
            else:
                lines.append("\n⚠️ Frigate 僵尸实体检测跳过（Frigate 不可达且 DB 无 zone 记录）")
        except Exception as _fze:
            _LOGGER.debug("[MCP Tools] Frigate 僵尸实体检测跳过: %s", _fze)
            lines.append("\n⚠️ Frigate 僵尸实体检测跳过（检测异常）")

        # ── ② DecisionCache 命中统计 ──────────────────────────────────────────
        lines.append("\n⚡ DecisionCache 缓存健康")
        cache_by_type: dict[str, dict] = {}
        for r in cache_rows:
            cache_by_type[r.get("trigger_type", "unknown")] = r
        total_cache_entries = sum(r.get("entries", 0) or 0 for r in cache_rows)
        total_cache_hits   = sum(r.get("hits",    0) or 0 for r in cache_rows)
        total_mature       = sum(r.get("mature",  0) or 0 for r in cache_rows)

        if total_cache_entries == 0:
            lines.append("  暂无缓存条目（AI 正在积累 LLM 决策经验，通常需要 3-7 天）")
        else:
            for _ttype, _r in cache_by_type.items():
                _label = {"arrival": "到达缓存", "departure": "离开缓存"}.get(_ttype, _ttype)
                _e = _r.get("entries", 0) or 0
                _h = _r.get("hits",    0) or 0
                _m = _r.get("mature",  0) or 0
                lines.append(f"  {_label}：{_e} 条 / 命中 {_h} 次 / 成熟条目 {_m} 个（命中≥5次）")
            lines.append(f"  合计：{total_cache_entries} 条 / {total_cache_hits} 次命中 / {total_mature} 个成熟")

        # ── ③ Phase 3 就绪进度 ────────────────────────────────────────────────
        # 判断标准：
        #   A. 离开缓存成熟条目数（hit_count ≥ 5）≥ 3（覆盖主要房间的离开模式）
        #   B. 系统运行时长 ≥ 7 天（保证数据充分）
        #   C. 无冲突行为戒律
        # 注意：不使用"累计命中/LLM决策"命中率，因为两者来自不同时间窗口，
        #       历史累计命中数 >> 近30天LLM决策，该比率会虚高并误导就绪判断。
        lines.append("\n🎯 Phase 3 就绪进度")
        txn30 = (txn30_rows[0].get("cnt", 0) or 0) if txn30_rows else 0
        uptime_days = uptime_s / 86400
        dep_r = cache_by_type.get("departure", {})
        dep_mature = dep_r.get("mature", 0) or 0
        dep_entries = dep_r.get("entries", 0) or 0
        dep_hits    = dep_r.get("hits",   0) or 0
        lesson_r = lesson_rows[0] if lesson_rows else {}
        lesson_conflict = lesson_r.get("conflicted", 0) or 0

        crit_a = dep_mature >= 3
        crit_b = uptime_days >= 7
        crit_c = lesson_conflict == 0

        lines.append(f"  近 30 天 LLM 推理：{txn30} 次")
        lines.append(f"  离开缓存：{dep_entries} 条 / 命中 {dep_hits} 次 / 成熟（≥5次）{dep_mature} 条")
        lines.append(
            f"  就绪条件：{'✅' if crit_a else '❌'} 离开成熟条目≥3（当前{dep_mature}）  "
            f"{'✅' if crit_b else '❌'} 运行≥7天（当前{uptime_days:.1f}天）  "
            f"{'✅' if crit_c else '⚠️'} 无冲突戒律"
        )
        if crit_a and crit_b and crit_c:
            lines.append("  ✅ 已具备 Phase 3 启用条件！建议联系配置 AI 自主修正权限。")
        else:
            missing = []
            if not crit_a:
                missing.append(f"还需 {max(0, 3 - dep_mature)} 个成熟离开缓存条目（每个房间出现 ≥5 次空房时自动积累）")
            if not crit_b:
                missing.append(f"还需运行 {max(0, 7 - uptime_days):.1f} 天")
            if not crit_c:
                missing.append("需先解决冲突戒律（用 smart_correction_analysis 排查）")
            lines.append("  🔵 积累中，待完成：" + "；".join(missing))

        # ── ④ 设备可靠性（SYS-01）────────────────────────────────────────────
        lines.append("\n🔧 设备可靠性（过去 7 天动作失败）")
        if not fail_rows:
            lines.append("  ✅ 过去 7 天无动作失败记录")
        else:
            lines.append(f"  ⚠️ 共 {len(fail_rows)} 个设备有失败记录（对应 SYS-01 隐患）：")
            for _r in fail_rows:
                _eid  = _r.get("entity_id", "")
                _cnt  = _r.get("fail_cnt", 0)
                _last = (_r.get("last_fail") or "")[:16]
                _name = coordinator.device_info.get(_eid, {}).get("name", _eid)
                lines.append(f"   {_cnt:>3}次  {_name}（{_eid}）  最近：{_last}")
            lines.append("  → 建议：检查上述设备的 Zigbee 信号强度或 Z2M 固件版本。")

        # ── ⑤ 行为戒律质量 ───────────────────────────────────────────────────
        lines.append("\n📚 AI 行为戒律（Phase 3 Lite）")
        lesson_total = lesson_r.get("total", 0) or 0
        lesson_rooms = lesson_r.get("rooms", 0) or 0
        if lesson_total == 0:
            lines.append("  暂无戒律（修正次数不足，或每日维护尚未运行）")
        else:
            lines.append(f"  已生成：{lesson_total} 条（覆盖 {lesson_rooms} 个房间）")
            if lesson_conflict > 0:
                lines.append(
                    f"  ⚠️ 冲突戒律：{lesson_conflict} 条 → 建议用 smart_correction_analysis 排查后手动删除旧记录"
                )
            else:
                lines.append("  ✅ 无冲突戒律")

        # ── ⑥ Add-on 诊断摘要（供 8234/UI 直接消费）────────────────────────────
        lines.append("\n🧠 Add-on 推理引擎诊断")
        if addon_diag:
            _mode = addon_diag.get("mode", "unknown")
            _last_err = addon_diag.get("last_infer_error") or "无"
            _last_err_at = addon_diag.get("last_infer_error_at") or "-"
            lines.append(f"  模式：{_mode}")
            lines.append(f"  最近错误：{_last_err}")
            lines.append(f"  错误时间：{_last_err_at}")
            _emap = addon_diag.get("error_mapping") or {}
            if _emap:
                lines.append("  错误映射：")
                for _k in ("401", "429", "503", "timeout"):
                    _v = _emap.get(_k)
                    if isinstance(_v, dict):
                        lines.append(
                            f"   {_k}: type={_v.get('error_type', '')}, retryable={bool(_v.get('retryable', False))}"
                        )
        else:
            lines.append("  未获取到 diagnostics（Add-on 不可达或未启用）")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    _LOGGER.warning("[MCP Tools] 未知工具调用: %s", tool_name)
    return {"content": [{"type": "text", "text": f"错误: 找不到工具 {tool_name}"}], "isError": True}
