"""Existing MCP tool handlers, isolated from transport dispatch."""

from __future__ import annotations
import logging
from .mcp_tool_context import McpToolContext, mcp_text
import asyncio
from .mcp_statistics import addon_decision_stats, database_decision_stats
from .mcp_history_report import decision_record, correction_report
from .mcp_tool_context import _mcp_bounded_int, _get_addon_transactions

_LOGGER = logging.getLogger("custom_components.smart_agent.mcp_tools")


async def smart_recent_decisions(context: McpToolContext) -> dict:
    hass, coordinator, tool_args = context.hass, context.coordinator, context.arguments
    limit = _mcp_bounded_int(tool_args.get("limit"), default=5, minimum=1, maximum=20)
    rows = await _get_addon_transactions(coordinator, limit=limit)
    if rows is None:
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
            _LOGGER.warning("[MCP Tools] query action_transactions failed: %s", exc)
            return mcp_text(f"query failed: {exc}", is_error=True)

    if not rows:
        return mcp_text("暂无决策记录。AI 尚未执行过任何推理。")

    lines = [f"最近 {len(rows)} 条 AI 决策记录：\n"]
    for r in rows:
        lines.append(decision_record(r, coordinator))

    return mcp_text("\n".join(lines))


async def smart_decision_stats(context: McpToolContext) -> dict:
    hass, coordinator, tool_args = context.hass, context.coordinator, context.arguments
    days = _mcp_bounded_int(tool_args.get("days"), default=7, minimum=1, maximum=30)
    date_param = (f"-{days} days",)
    addon_txns = await _get_addon_transactions(coordinator)
    if addon_txns is not None:
        return addon_decision_stats(addon_txns, days)
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
        return mcp_text(f"查询失败: {exc}", is_error=True)
    return database_decision_stats(txn_rows, corr_rows, cache_rows, days)


async def smart_correction_analysis(context: McpToolContext) -> dict:
    hass, coordinator, tool_args = context.hass, context.coordinator, context.arguments
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
        return mcp_text(f"查询失败: {exc}", is_error=True)

    return correction_report(coordinator, room_filter, stats_rows, conflict_rows, top_rows)
