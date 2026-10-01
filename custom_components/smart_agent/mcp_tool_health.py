"""Existing MCP tool handlers, isolated from transport dispatch."""

from __future__ import annotations
import logging
from .mcp_tool_context import McpToolContext, mcp_text
import asyncio
from .mcp_tool_context import _get_addon_transactions

_LOGGER = logging.getLogger("custom_components.smart_agent.mcp_tools")


from .mcp_health_report import (
    system_health_lines,
    append_frigate_health,
    append_cache_health,
    append_readiness,
    append_device_reliability,
    append_lessons_health,
    append_diagnostics,
)


async def smart_health_check(context: McpToolContext) -> dict:
    hass, coordinator = context.hass, context.coordinator
    addon_txns = await _get_addon_transactions(coordinator)
    base_query = coordinator._db.query

    def _health_query(sql, params=()):
        if addon_txns is not None and "action_results" in sql:
            return []
        if addon_txns is not None and "action_transactions" in sql:
            return [{"cnt": len(addon_txns)}]
        return base_query(sql, params)

    _health_query.__self__ = coordinator._db
    # 并发查询四张表，避免串行等待
    try:
        cache_rows, fail_rows, lesson_rows, txn30_rows = await asyncio.gather(
            hass.async_add_executor_job(
                _health_query,
                """SELECT trigger_type,
                              COUNT(*) AS entries,
                              SUM(hit_count) AS hits,
                              COUNT(CASE WHEN hit_count >= 5 THEN 1 END) AS mature
                       FROM decision_cache
                       GROUP BY trigger_type""",
                (),
            ),
            hass.async_add_executor_job(
                _health_query,
                """SELECT entity_id, COUNT(*) AS fail_cnt, MAX(time) AS last_fail
                       FROM action_results
                       WHERE success = 0 AND time >= datetime('now', '-7 days')
                       GROUP BY entity_id
                       ORDER BY fail_cnt DESC
                       LIMIT 5""",
                (),
            ),
            hass.async_add_executor_job(
                _health_query,
                """SELECT COUNT(*) AS total,
                              SUM(is_conflicted) AS conflicted,
                              COUNT(DISTINCT room) AS rooms
                       FROM correction_lessons""",
                (),
            ),
            hass.async_add_executor_job(
                _health_query,
                "SELECT COUNT(*) AS cnt FROM action_transactions WHERE time >= datetime('now', '-30 days')",
                (),
            ),
        )
    except Exception as exc:
        _LOGGER.warning("[MCP Tools] smart_health_check 查询失败: %s", exc)
        return mcp_text(f"查询失败: {exc}", is_error=True)

    addon_diag: dict = {}
    _addon_client = getattr(coordinator, "_addon_client", None)
    if _addon_client is not None:
        try:
            addon_diag = await _addon_client.get_diagnostics()
        except Exception as _addon_exc:
            _LOGGER.debug("[MCP Tools] 获取 Add-on diagnostics 失败: %s", _addon_exc)

    lines, uptime_s = system_health_lines(hass, coordinator)
    await append_frigate_health(context, lines)
    cache_by_type = append_cache_health(lines, cache_rows)
    readiness = append_readiness(lines, txn30_rows, cache_by_type, lesson_rows, uptime_s)
    append_device_reliability(lines, fail_rows, coordinator)
    append_lessons_health(lines, readiness.lesson, readiness.conflicted)
    append_diagnostics(lines, addon_diag)
    return mcp_text("\n".join(lines))
