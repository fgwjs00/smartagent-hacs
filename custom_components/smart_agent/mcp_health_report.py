"""Health report sections, retaining data sources and existing display semantics."""

from __future__ import annotations
from dataclasses import dataclass
import logging
import time as _time
from typing import Any
from .mcp_tool_context import McpToolContext
from .frigate_authority import FRIGATE_ZONE_QUERIES, frigate_api_zone_ids, frigate_db_zone_ids
from .task_completion import TaskCompletion, report_task_completion

_LOGGER = logging.getLogger("custom_components.smart_agent.mcp_tools")


@dataclass(frozen=True, slots=True)
class HealthReadiness:
    txn30: Any
    uptime_days: float
    dep_mature: Any
    dep_entries: Any
    dep_hits: Any
    lesson: dict
    conflicted: Any


def system_health_lines(hass: Any, coordinator: Any) -> tuple[list[str], int]:
    uptime_s = int(_time.time() - getattr(coordinator, "_startup_time", _time.time()))
    uptime_str = (
        f"{uptime_s // 3600}h {(uptime_s % 3600) // 60}m"
        if uptime_s >= 3600
        else f"{uptime_s // 60}m {uptime_s % 60}s"
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
    online_rate = (
        f"{(total_devices - unavail_cnt) / total_devices * 100:.0f}%" if total_devices else "N/A"
    )

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
    return lines, uptime_s


async def _known_frigate_zones(hass: Any, coordinator: Any) -> set[str] | None:
    from .frigate_config import get_cameras_from_frigate_api as _get_cameras

    cameras, base_url = await _get_cameras()
    if not base_url:
        return None
    known = frigate_api_zone_ids(cameras)
    for sql, field in FRIGATE_ZONE_QUERIES:
        rows = await hass.async_add_executor_job(coordinator._db.query_required, sql)
        known.update(frigate_db_zone_ids(rows, field))
    return known


async def append_frigate_health(context: McpToolContext, lines: list[str]) -> None:
    hass, coordinator = context.hass, context.coordinator
    phase = "read_authority"
    section: list[str] = []
    try:
        _known_zones = await _known_frigate_zones(hass, coordinator)
        if _known_zones is None:
            lines.append("\n⚠️ Frigate 僵尸实体检测暂时无法确认（未取得当前 Frigate 配置）")
            return

        frigate_zombie_entities: list[str] = []
        _suffix = "_person_occupancy"
        phase = "scan"
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
            section.append("\n🚨 Frigate 僵尸实体（须手动处理）")
            section.append(
                "  以下实体在 HA 注册表中存在，但 Frigate 配置中已不存在对应 zone，"
                '导致 HA 持续输出 "Forced update failed" 错误并使人数计数恒为 0：'
            )
            for _ze in frigate_zombie_entities:
                section.append(f"   ⛔ {_ze}")
            section.append(
                "  修复（二选一）：\n"
                "  方法 A（推荐）：在 Frigate config.yml 中重新添加对应 zone，重启 Frigate。\n"
                "  方法 B（快速）：HA → 设置 → 设备和服务 → 实体 → 搜索上述实体 → 禁用/删除 → 重启 HA。"
            )
        elif _known_zones:
            section.append("\n✅ 未发现 Frigate 僵尸实体")
        else:
            section.append("\n⚠️ Frigate 僵尸实体检测跳过（API 和 DB 尚无 camera/zone 记录）")
    except Exception as _fze:
        report_task_completion(context, TaskCompletion(error=_fze, phase=phase),
                               logger=_LOGGER, operation="mcp_frigate_health")
        lines.append(f"\n⚠️ Frigate 僵尸实体检测暂时无法确认（检测异常，参考号 {id(context):x}）")
        return
    lines.extend(section)


def append_cache_health(lines: list[str], cache_rows: list[dict]) -> dict[str, dict]:
    lines.append("\n⚡ DecisionCache 缓存健康")
    cache_by_type: dict[str, dict] = {}
    for r in cache_rows:
        cache_by_type[r.get("trigger_type", "unknown")] = r
    total_cache_entries = sum(r.get("entries", 0) or 0 for r in cache_rows)
    total_cache_hits = sum(r.get("hits", 0) or 0 for r in cache_rows)
    total_mature = sum(r.get("mature", 0) or 0 for r in cache_rows)

    if total_cache_entries == 0:
        lines.append("  暂无缓存条目（AI 正在积累 LLM 决策经验，通常需要 3-7 天）")
    else:
        for _ttype, _r in cache_by_type.items():
            _label = {"arrival": "到达缓存", "departure": "离开缓存"}.get(_ttype, _ttype)
            _e = _r.get("entries", 0) or 0
            _h = _r.get("hits", 0) or 0
            _m = _r.get("mature", 0) or 0
            lines.append(f"  {_label}：{_e} 条 / 命中 {_h} 次 / 成熟条目 {_m} 个（命中≥5次）")
        lines.append(
            f"  合计：{total_cache_entries} 条 / {total_cache_hits} 次命中 / {total_mature} 个成熟"
        )
    return cache_by_type


def _readiness_facts(
    txn30_rows: list[dict], cache_by_type: dict, lesson_rows: list[dict], uptime_s: int
) -> HealthReadiness:
    txn30 = (txn30_rows[0].get("cnt", 0) or 0) if txn30_rows else 0
    uptime_days = uptime_s / 86400
    dep_r = cache_by_type.get("departure", {})
    dep_mature = dep_r.get("mature", 0) or 0
    dep_entries = dep_r.get("entries", 0) or 0
    dep_hits = dep_r.get("hits", 0) or 0
    lesson_r = lesson_rows[0] if lesson_rows else {}
    lesson_conflict = lesson_r.get("conflicted", 0) or 0
    return HealthReadiness(
        txn30, uptime_days, dep_mature, dep_entries, dep_hits, lesson_r, lesson_conflict
    )


def append_readiness(
    lines: list[str],
    txn30_rows: list[dict],
    cache_by_type: dict,
    lesson_rows: list[dict],
    uptime_s: int,
) -> HealthReadiness:
    lines.append("\n🎯 Phase 3 就绪进度")
    facts = _readiness_facts(txn30_rows, cache_by_type, lesson_rows, uptime_s)
    txn30, uptime_days = facts.txn30, facts.uptime_days
    dep_mature, dep_entries, dep_hits = facts.dep_mature, facts.dep_entries, facts.dep_hits
    lesson_conflict = facts.conflicted
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
            missing.append(
                f"还需 {max(0, 3 - dep_mature)} 个成熟离开缓存条目（每个房间出现 ≥5 次空房时自动积累）"
            )
        if not crit_b:
            missing.append(f"还需运行 {max(0, 7 - uptime_days):.1f} 天")
        if not crit_c:
            missing.append("需先解决冲突戒律（用 smart_correction_analysis 排查）")
        lines.append("  🔵 积累中，待完成：" + "；".join(missing))
    return facts


def append_device_reliability(lines: list[str], fail_rows: list[dict], coordinator: Any) -> None:
    lines.append("\n🔧 设备可靠性（过去 7 天动作失败）")
    if not fail_rows:
        lines.append("  ✅ 过去 7 天无动作失败记录")
    else:
        lines.append(f"  ⚠️ 共 {len(fail_rows)} 个设备有失败记录（对应 SYS-01 隐患）：")
        for _r in fail_rows:
            _eid = _r.get("entity_id", "")
            _cnt = _r.get("fail_cnt", 0)
            _last = (_r.get("last_fail") or "")[:16]
            _name = coordinator.device_info.get(_eid, {}).get("name", _eid)
            lines.append(f"   {_cnt:>3}次  {_name}（{_eid}）  最近：{_last}")
        lines.append("  → 建议：检查上述设备的 Zigbee 信号强度或 Z2M 固件版本。")


def append_lessons_health(lines: list[str], lesson_r: dict, lesson_conflict: Any) -> None:
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


def append_diagnostics(lines: list[str], addon_diag: dict) -> None:
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
