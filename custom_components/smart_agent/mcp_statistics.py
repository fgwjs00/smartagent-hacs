"""Decision statistics from the existing add-on and legacy query sources."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .mcp_tool_context import mcp_text


@dataclass(frozen=True, slots=True)
class DecisionTotals:
    total: Any
    executed: Any
    blocked_only: Any
    avg_conf: Any
    t_actions: Any
    t_disp: Any
    t_blocked: Any


@dataclass(frozen=True, slots=True)
class CacheQuality:
    entries: Any
    rooms: Any
    hits: Any
    average: Any
    last_hit: Any


def _transaction_counts(addon_txns: list[dict]) -> tuple[int, int, int]:
    total = len(addon_txns)
    executed = sum(1 for row in addon_txns if int(row.get("dispatched_count") or 0) > 0)
    blocked_only = sum(
        1
        for row in addon_txns
        if int(row.get("blocked_count") or 0) > 0 and int(row.get("dispatched_count") or 0) == 0
    )
    return total, executed, blocked_only


def _average_confidence(addon_txns: list[dict]) -> float | None:
    confidences = [
        float(row.get("confidence")) for row in addon_txns if row.get("confidence") is not None
    ]
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    return avg_conf


def _display_rates(
    total: Any, executed: Any, t_actions: Any, t_blocked: Any, avg_conf: Any
) -> tuple[str, str, str]:
    exec_rate = f"{executed / total * 100:.0f}%" if total else "N/A"
    block_rate = f"{t_blocked / t_actions * 100:.0f}%" if t_actions else "N/A"
    conf_str = f"{avg_conf:.0f}%" if avg_conf is not None else "N/A"
    return exec_rate, block_rate, conf_str


def addon_decision_stats(addon_txns: list[dict], days: int) -> dict:
    total, executed, blocked_only = _transaction_counts(addon_txns)
    avg_conf = _average_confidence(addon_txns)
    t_actions = sum(int(row.get("action_count") or 0) for row in addon_txns)
    t_disp = sum(int(row.get("dispatched_count") or 0) for row in addon_txns)
    t_blocked = sum(int(row.get("blocked_count") or 0) for row in addon_txns)
    exec_rate, block_rate, conf_str = _display_rates(
        total, executed, t_actions, t_blocked, avg_conf
    )
    text = (
        f"过去 {days} 天 AI 决策质量统计\n\n"
        f"总推理次数：{total}\n"
        f"有动作执行：{executed} 次（执行率 {exec_rate}）\n"
        f"纯拦截（无执行）：{blocked_only} 次\n"
        f"平均置信度：{conf_str}\n"
        f"动作总数：{t_actions}，已执行 {t_disp}，被拦截 {t_blocked}（动作拦截率 {block_rate}）\n"
        "数据源：add-on transactions"
    )
    return mcp_text(text)


def _database_totals(row: dict) -> DecisionTotals:
    total = row.get("total", 0) or 0
    executed = row.get("executed", 0) or 0
    blocked_only = row.get("blocked", 0) or 0
    avg_conf = row.get("avg_conf")
    t_actions = row.get("total_actions", 0) or 0
    t_disp = row.get("total_dispatched", 0) or 0
    t_blocked = row.get("total_blocked", 0) or 0
    return DecisionTotals(total, executed, blocked_only, avg_conf, t_actions, t_disp, t_blocked)


def _cache_quality(cache_rows: list[dict]) -> CacheQuality:
    cache_row = cache_rows[0] if cache_rows else {}
    cache_entries = cache_row.get("total_entries", 0) or 0
    cache_rooms = cache_row.get("rooms", 0) or 0
    cache_hits = cache_row.get("total_hits", 0) or 0
    cache_avg = cache_row.get("avg_hits") or 0.0
    cache_last = cache_row.get("last_hit") or "无"
    return CacheQuality(cache_entries, cache_rooms, cache_hits, cache_avg, cache_last)


def database_decision_stats(
    txn_rows: list[dict], corr_rows: list[dict], cache_rows: list[dict], days: int
) -> dict:
    row = txn_rows[0] if txn_rows else {}
    totals = _database_totals(row)
    total, executed, blocked_only = totals.total, totals.executed, totals.blocked_only
    avg_conf, t_actions, t_disp, t_blocked = (
        totals.avg_conf,
        totals.t_actions,
        totals.t_disp,
        totals.t_blocked,
    )
    corr_row = corr_rows[0] if corr_rows else {}
    corrections = corr_row.get("cnt", 0) or 0
    cache = _cache_quality(cache_rows)
    cache_entries, cache_rooms, cache_hits = cache.entries, cache.rooms, cache.hits
    cache_avg, cache_last = cache.average, cache.last_hit
    exec_rate, block_rate, conf_str = _display_rates(
        total, executed, t_actions, t_blocked, avg_conf
    )
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

    return mcp_text(text)
