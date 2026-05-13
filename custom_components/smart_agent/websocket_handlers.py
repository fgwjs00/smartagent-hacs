"""HA WebSocket command handlers for the SmartAgent host."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SmartAgentCoordinator
from .ha_adapter import (
    get_ai_scenes_cache_snapshot,
    get_device_info_snapshot,
    get_habits_cache_snapshot,
    get_rules_snapshot,
    get_transactions_cache_snapshot,
)

_LOGGER = logging.getLogger(__name__)


def build_smart_agent_websocket_commands(
    *,
    _normalize_addon_diagnostics: Callable[[Any], dict[str, Any]],
    _build_presence_sensors_payload: Callable[[HomeAssistant, SmartAgentCoordinator], dict[str, Any]],
    _async_save_presence_sensor_type: Callable[
        [HomeAssistant, SmartAgentCoordinator, str, str], Awaitable[dict[str, Any]]
    ],
) -> tuple[Any, ...]:
    # ── WebSocket API：大数据列表通过 WS 按需下发，绕过 sensor 属性 16KB 上限 ──

    def _get_coord(hass: HomeAssistant) -> SmartAgentCoordinator | None:
        """从 hass.data 取出第一个 coordinator 实例（单实例部署常用）。"""
        return next(iter(hass.data.get(DOMAIN, {}).values()), None)

    def _require_admin(connection, msg_id: int) -> bool:
        """校验调用者是否为管理员，非管理员返回 False 并发送 forbidden 错误。

        WS 面板注册时已 require_admin=True，此校验为纵深防御，
        防止非管理员用户绕过 UI 直接调用 WebSocket 命令。
        """
        if not connection.user.is_admin:
            connection.send_error(msg_id, "forbidden", "Admin access required")
            return False
        return True

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_devices"})
    @websocket_api.async_response
    async def ws_get_devices(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整设备列表（所有字段，无截断），供设备管理页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        devices = [
            {
                "entity_id": eid,
                "name": info.get("name", eid),
                "room": info.get("room", ""),
                "type": info.get("type", ""),
                "control_mode": info.get("control_mode", "shared"),
                "ops": info.get("ops", ""),
                "sensor_type": info.get("sensor_type", ""),
            }
            for eid, info in get_device_info_snapshot(coord).items()
        ]
        connection.send_result(msg["id"], {"devices": devices})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_habits"})
    @websocket_api.async_response
    async def ws_get_habits(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整习惯列表（内容无截断），供个性化画像页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        habits = [
            {"index": i, "content": c, "locked": lk}
            for i, (c, lk) in enumerate(get_habits_cache_snapshot(coord))
        ]
        connection.send_result(msg["id"], {"habits": habits})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_rules"})
    @websocket_api.async_response
    async def ws_get_rules(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整规则列表（含 AI 自动规则，内容无截断），供个性化画像页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        _AI_MARKS = ("[自动修正规则]", "[强化修正规则]")
        rules = [
            {"index": i, "content": c, "locked": lk, "is_ai": any(c.startswith(m) for m in _AI_MARKS)}
            for i, (c, lk) in enumerate(get_rules_snapshot(coord))
        ]
        connection.send_result(msg["id"], {"rules": rules})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_ai_scenes"})
    @websocket_api.async_response
    async def ws_get_ai_scenes(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整 AI 候选场景列表（含 entities_json），供 AI 场景页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        scenes = get_ai_scenes_cache_snapshot(coord)
        connection.send_result(msg["id"], {"scenes": scenes})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_energy_stats"})
    @websocket_api.async_response
    async def ws_get_energy_stats(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整能耗统计数据，供能耗分析页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        stats = coord._energy_stats if isinstance(coord._energy_stats, list) else []
        connection.send_result(msg["id"], {"stats": stats})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_transactions"})
    @websocket_api.async_response
    async def ws_get_transactions(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整执行记录（最近 50 条），供执行记录页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        txns = get_transactions_cache_snapshot(coord)
        # 去掉超大 JSON 快照字段，只保留展示所需字段
        _DROP = {"pre_states_json"}
        result = [
            {k: v for k, v in t.items() if k not in _DROP}
            for t in txns[-50:]
            if isinstance(t, dict)
        ]
        connection.send_result(msg["id"], {"transactions": result})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_decision_stats"})
    @websocket_api.async_response
    async def ws_get_decision_stats(hass: HomeAssistant, connection, msg: dict) -> None:
        """5D-3 AI 决策看板统计 API — 返回今日决策概览和按房间推翻率。

        返回结构：
          today_inferences: 今日 AI 推理触发次数
          today_blocked:    今日被意图验证拦截的动作数
          today_corrections: 今日用户主动修正次数
          room_overturn_rates: [{room, inferences, corrections, rate}]
          recent_decisions: 最近 5 条事务摘要
        """
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return

        from datetime import date as _date, timedelta as _td

        today_str = _date.today().isoformat()
        # P2 fix: 近30天截止日期（原代码误用了今天）
        cutoff_30 = (_date.today() - _td(days=30)).strftime("%Y-%m-%d")

        def _fetch():
            # P1 fix: 整体 try/except，避免任何 SQL 异常导致 WS 处理函数崩溃
            try:
                db = coord._db
                # 今日 AI 推理次数（events 表 type=AI_Inference）
                inf_rows = db.query(
                    "SELECT COUNT(*) AS cnt FROM events WHERE type='AI_Inference' AND time >= ?",
                    (today_str,),
                )
                today_inferences = inf_rows[0]["cnt"] if inf_rows else 0

                # 今日拦截动作数（action_transactions 中 blocked_count 合计）
                blk_rows = db.query(
                    "SELECT COALESCE(SUM(blocked_count),0) AS cnt FROM action_transactions WHERE time >= ?",
                    (today_str,),
                )
                today_blocked = blk_rows[0]["cnt"] if blk_rows else 0

                # 今日用户修正次数（corrections 表 time 今日）
                cor_rows = db.query(
                    "SELECT COUNT(*) AS cnt FROM corrections WHERE time >= ?",
                    (today_str,),
                )
                today_corrections = cor_rows[0]["cnt"] if cor_rows else 0

                # 按房间统计推翻率（近 30 天）
                room_inf = db.query(
                    "SELECT area AS room, COUNT(*) AS cnt FROM events "
                    "WHERE type='AI_Inference' AND area != '' AND time >= ? "
                    "GROUP BY area ORDER BY cnt DESC LIMIT 10",
                    (cutoff_30,),
                )
                # P3 fix: 移除 SELECT 中未使用的 c.entity_id（GROUP BY d.area 时返回值不确定）
                room_cor = db.query(
                    "SELECT d.area AS room, SUM(c.correction_count) AS corrections "
                    "FROM corrections c "
                    "LEFT JOIN devices d ON c.entity_id = d.entity_id "
                    "WHERE c.time >= ? AND d.area != '' "
                    "GROUP BY d.area",
                    (cutoff_30,),
                )
                cor_map = {r["room"]: int(r.get("corrections") or 0) for r in room_cor if r.get("room")}
                room_overturn_rates = []
                for r in room_inf:
                    room = r.get("room", "")
                    infs = int(r.get("cnt") or 0)
                    cors = cor_map.get(room, 0)
                    rate = round(cors / infs * 100, 1) if infs > 0 else 0.0
                    room_overturn_rates.append({"room": room, "inferences": infs, "corrections": cors, "rate": rate})

                return today_inferences, today_blocked, today_corrections, room_overturn_rates
            except Exception as _exc:
                _LOGGER.warning("[DecisionStats] DB 查询失败: %s", _exc)
                return 0, 0, 0, []

        ti, tb, tc, rates = await hass.async_add_executor_job(_fetch)

        addon_diagnostics: dict[str, Any] = {}
        _addon_client = getattr(coord, "_addon_client", None)
        if _addon_client is not None:
            try:
                addon_diagnostics = _normalize_addon_diagnostics(await _addon_client.get_diagnostics())
            except Exception as _diag_exc:
                _LOGGER.debug("[DecisionStats] 获取 Add-on diagnostics 失败: %s", _diag_exc)
                addon_diagnostics = {
                    "ok": False,
                    "error": "addon_diagnostics_fetch_failed",
                    "error_type": "dependency_unreachable",
                    "retryable": True,
                }

        # 最近 5 条事务（from cache）
        txns = coord._transactions_cache if isinstance(coord._transactions_cache, list) else []
        _DROP = {"pre_states_json", "actions_json", "results_json"}
        recent = [
            {k: v for k, v in t.items() if k not in _DROP}
            for t in txns[-5:]
            if isinstance(t, dict)
        ]

        connection.send_result(msg["id"], {
            "today_inferences": ti,
            "today_blocked": tb,
            "today_corrections": tc,
            "room_overturn_rates": rates,
            "recent_decisions": recent,
            "addon_diagnostics": addon_diagnostics,
        })

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_behavior_patterns"})
    @websocket_api.async_response
    async def ws_get_behavior_patterns(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整行为模式列表，供行为习惯页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        patterns = coord._behavior_patterns_cache if isinstance(coord._behavior_patterns_cache, list) else []
        connection.send_result(msg["id"], {"patterns": patterns})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_ai_actions"})
    @websocket_api.async_response
    async def ws_get_ai_actions(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回近期 AI 操作记录（_last_ai_actions dict），供纠错学习页使用。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        raw = getattr(coord, "_last_ai_actions", {})
        actions = [{"entity_id": eid, **v} for eid, v in raw.items()]
        connection.send_result(msg["id"], {"actions": actions})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_sys_log"})
    @websocket_api.async_response
    async def ws_get_sys_log(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回完整系统运行日志 HTML（不受 sensor 16KB 限制）。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        html = getattr(coord, "sys_log_html", "") or ""
        connection.send_result(msg["id"], {"html": html})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_terminal_log"})
    @websocket_api.async_response
    async def ws_get_terminal_log(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回决策流水 HTML（绕过 sensor 16KB 限制，支持前端轮询）。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return
        html = getattr(coord, "terminal_log_html", "") or ""
        connection.send_result(msg["id"], {"html": html})

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_learning_stats"})
    @websocket_api.async_response
    async def ws_get_learning_stats(hass: HomeAssistant, connection, msg: dict) -> None:
        """
        返回 AI 学习数据积累统计，供前端「学习进度仪表盘」使用。

        包含各核心学习表的记录数、设备区域覆盖率、纠正学习趋势等。
        """
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return

        def _query_stats():
            q = coord._db.query
            # _safe_int: 返回 COUNT/SUM 查询结果中 "c" 列的整数值
            # 原错误：_safe(sql)[0] 对 dict 使用整数下标 → KeyError: 0（v4.11.1 修复）
            _safe_int = lambda sql: ((q(sql) or [{}])[0].get("c") or 0)

            # 各表记录数
            arrival_count    = _safe_int("SELECT COUNT(*) as c FROM arrival_baseline")
            correction_count = _safe_int("SELECT COUNT(*) as c FROM corrections")
            cache_count      = _safe_int("SELECT COUNT(*) as c FROM decision_cache")
            cache_hits       = _safe_int("SELECT SUM(hit_count) as c FROM decision_cache")
            pattern_count    = _safe_int("SELECT COUNT(*) as c FROM behavior_patterns")
            reflexion_count  = _safe_int("SELECT COUNT(*) as c FROM reflexion_patterns")

            # 设备区域覆盖率
            total_devices  = _safe_int("SELECT COUNT(*) as c FROM devices")
            noroom_devices = _safe_int("SELECT COUNT(*) as c FROM devices WHERE area='' OR area IS NULL")

            # 近 7 天纠正趋势（按天分组）
            correction_trend = []
            rows = q(
                "SELECT DATE(time) as day, COUNT(*) as cnt "
                "FROM corrections WHERE time >= DATE('now','-7 days') "
                "GROUP BY DATE(time) ORDER BY day"
            )
            if rows:
                correction_trend = [{"day": r["day"], "count": r["cnt"]} for r in rows]

            # 被纠正最多的 Top-5 设备
            top_corrected = []
            rows = q(
                "SELECT entity_id, SUM(correction_count) as total "
                "FROM corrections GROUP BY entity_id ORDER BY total DESC LIMIT 5"
            )
            if rows:
                top_corrected = [{"entity_id": r["entity_id"], "count": r["total"]} for r in rows]

            return {
                "arrival_baseline": arrival_count,
                "corrections": correction_count,
                "decision_cache": cache_count,
                "decision_cache_hits": cache_hits,
                "behavior_patterns": pattern_count,
                "reflexion_patterns": reflexion_count,
                "total_devices": total_devices,
                "noroom_devices": noroom_devices,
                "correction_trend": correction_trend,
                "top_corrected": top_corrected,
            }

        try:
            stats = await hass.async_add_executor_job(_query_stats)
        except Exception as _exc:
            _LOGGER.warning("[WS] get_learning_stats 查询异常: %s", _exc)
            connection.send_error(msg["id"], "query_error", str(_exc))
            return
        connection.send_result(msg["id"], stats)

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_frigate_cameras"})
    @websocket_api.async_response
    async def ws_get_frigate_cameras(hass: HomeAssistant, connection, msg: dict) -> None:
        """
        返回 Frigate 摄像头配置列表（合并 DB 绑定 + Frigate 现有摄像头）。

        数据来源优先级：
          1. Frigate HTTP API（主路径，跨容器网络，无需文件系统权限）
          2. 文件系统搜索（降级兜底，适用于本地开发/非 Supervisor 部署）

        DB 中有绑定记录的摄像头会附带 room 信息；
        Frigate 中存在但尚未绑定的摄像头也会列出（room 为空，提示用户补充）。
        """
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return

        from .frigate_config import (
            find_frigate_config_path, read_frigate_config,
            list_cameras_from_config, get_cameras_from_frigate_api,
        )

        try:
            # 查 DB 中的摄像头绑定记录
            def _db_query():
                rows = coord._db.query("SELECT * FROM frigate_cameras ORDER BY created_at DESC")
                return [dict(r) for r in rows] if rows else []

            db_cameras = await hass.async_add_executor_job(_db_query)
            db_ids = {c["camera_id"] for c in db_cameras}

            # ── 主路径：Frigate HTTP API（HA Core 容器不挂载 /addon_configs/）──
            yml_cameras, config_path = await get_cameras_from_frigate_api()

            # ── 降级：文件系统搜索（本地开发 / 特殊部署场景）──
            if not yml_cameras:
                fs_path = await hass.async_add_executor_job(find_frigate_config_path)
                if fs_path:
                    config = await hass.async_add_executor_job(read_frigate_config, fs_path)
                    yml_cameras = list_cameras_from_config(config)
                    config_path = fs_path

            # 合并：DB 记录优先，API/文件中未绑定的追加
            result = list(db_cameras)
            for yc in yml_cameras:
                if yc["camera_id"] not in db_ids:
                    result.append({**yc, "room": "", "enabled": yc.get("enabled", True)})

            connection.send_result(msg["id"], {
                "cameras": result,
                "config_path": config_path or "",
            })
        except Exception as _exc:
            _LOGGER.warning("[WS] get_frigate_cameras 异常: %s", _exc)
            connection.send_error(msg["id"], "query_error", str(_exc))

    # ── Frigate Zone 房间绑定 WS 接口 ──────────────────────────────────
    @websocket_api.websocket_command({
        vol.Required("type"): "smart_agent/get_frigate_zones",
        vol.Required("camera_id"): str,
    })
    @websocket_api.async_response
    async def ws_get_frigate_zones(hass: HomeAssistant, connection, msg: dict) -> None:
        """
        返回指定摄像头的所有 zone 及其房间绑定信息。

        先从 Frigate API 读取摄像头配置中的 zones 定义，
        再与 DB frigate_zones 表合并（已绑定的附带 room 信息）。
        """
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return

        camera_id = msg["camera_id"]

        from .frigate_config import get_cameras_from_frigate_api

        try:
            # 从 Frigate API 获取 zone 定义
            yml_cameras, _ = await get_cameras_from_frigate_api()
            cam_config = next((c for c in yml_cameras if c.get("camera_id") == camera_id), None)
            frigate_zones: list[dict] = cam_config.get("zones", []) if cam_config else []

            # 查 DB 中已绑定的 zone
            def _db_query():
                rows = coord._db.query(
                    "SELECT * FROM frigate_zones WHERE camera_id=?", (camera_id,)
                )
                return {r["zone_id"]: r for r in rows} if rows else {}

            db_zones = await hass.async_add_executor_job(_db_query)

            # 合并：DB 记录优先
            result = []
            for z in frigate_zones:
                zid = z["zone_id"]
                db_rec = db_zones.get(zid)
                result.append({
                    "zone_id": zid,
                    "friendly_name": (db_rec or {}).get("friendly_name") or z.get("friendly_name", zid),
                    "room": (db_rec or {}).get("room", ""),
                    "camera_id": camera_id,
                })
            # 追加在 Frigate API 中未出现但 DB 有记录的 zone（可能 zone 已删除）
            seen = {z["zone_id"] for z in frigate_zones}
            for zid, db_rec in db_zones.items():
                if zid not in seen:
                    result.append({
                        "zone_id": zid,
                        "friendly_name": db_rec.get("friendly_name", zid),
                        "room": db_rec.get("room", ""),
                        "camera_id": camera_id,
                        "_orphan": True,
                    })

            connection.send_result(msg["id"], {"zones": result, "camera_id": camera_id})
        except Exception as _exc:
            _LOGGER.warning("[WS] get_frigate_zones 异常: %s", _exc)
            connection.send_error(msg["id"], "query_error", str(_exc))

    @websocket_api.websocket_command({
        vol.Required("type"): "smart_agent/save_frigate_zone",
        vol.Required("camera_id"): str,
        vol.Required("zone_id"): str,
        vol.Optional("friendly_name", default=""): str,
        vol.Optional("room", default=""): str,
    })
    @websocket_api.async_response
    async def ws_save_frigate_zone(hass: HomeAssistant, connection, msg: dict) -> None:
        """保存 Frigate zone 的房间绑定（upsert）。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return

        camera_id = msg["camera_id"]
        zone_id = msg["zone_id"]
        friendly_name = msg.get("friendly_name", "")
        room = msg.get("room", "")

        from datetime import datetime as _dt_now

        def _db_upsert() -> bool:
            now_str = _dt_now.now().isoformat()
            return bool(coord._db.execute(
                """INSERT INTO frigate_zones (camera_id, zone_id, friendly_name, room, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(camera_id, zone_id) DO UPDATE SET
                     friendly_name=excluded.friendly_name,
                     room=excluded.room,
                     updated_at=excluded.updated_at""",
                (camera_id, zone_id, friendly_name, room, now_str, now_str),
            ))

        db_ok = await hass.async_add_executor_job(_db_upsert)
        if not db_ok:
            connection.send_error(msg["id"], "db_write_failed", "保存 Frigate zone 失败")
            return
        connection.send_result(msg["id"], {"ok": True})

    # ── 传感器管理 WS（Phase 12.1）──────────────────────────────────────────────

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_presence_sensors"})
    @websocket_api.async_response
    async def ws_get_presence_sensors(hass: HomeAssistant, connection, msg: dict) -> None:
        """
        返回 HA 中所有存在类传感器（binary_sensor.*），附带 SmartAgent DB 信息。

        数据来源：
          1. HA states → 全量 binary_sensor 实体（不限于已注册到 SA 的设备）
          2. coordinator.device_info → 补充 name / room / sensor_type
          3. coordinator._fusion_registry → 补充所属融合域
          4. coordinator._cfg.options / presence_fusion → 当前融合域配置 JSON
        """
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return

        connection.send_result(msg["id"], _build_presence_sensors_payload(hass, coord))

    @websocket_api.websocket_command({
        vol.Required("type"): "smart_agent/save_sensor_type",
        vol.Required("entity_id"): str,
        vol.Required("sensor_type"): str,
    })
    @websocket_api.async_response
    async def ws_save_sensor_type(hass: HomeAssistant, connection, msg: dict) -> None:
        """保存单个传感器的 sensor_type（pir / mmwave / frigate / ""）到 DB。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "SmartAgent coordinator not loaded")
            return

        result = await _async_save_presence_sensor_type(
            hass,
            coord,
            msg["entity_id"],
            msg["sensor_type"],
        )
        status = int(result.pop("status", 200) or 200)
        if not result.get("ok"):
            code = "invalid_input" if status == 400 else "not_found" if status == 404 else "db_write_failed"
            connection.send_error(msg["id"], code, str(result.get("error") or "保存 sensor_type 失败"))
            return

        connection.send_result(msg["id"], result)

    # ── 房间拓扑 WS ───────────────────────────────────────────────────────────

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/get_room_topology"})
    @websocket_api.async_response
    async def ws_get_room_topology(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回已保存的房间拓扑关系列表。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_result(msg["id"], {"topology": []})
            return

        def _query():
            try:
                rows = coord._db.query(
                    "SELECT room_a, room_b, relation FROM room_topology", ()
                )
                return rows or []
            except Exception:
                return []

        rows = await hass.async_add_executor_job(_query)
        connection.send_result(msg["id"], {"topology": rows})

    # ── 备份列表 WS ───────────────────────────────────────────────────────────

    @websocket_api.websocket_command({vol.Required("type"): "smart_agent/list_backups"})
    @websocket_api.async_response
    async def ws_list_backups(hass: HomeAssistant, connection, msg: dict) -> None:
        """返回备份文件列表。"""
        if not _require_admin(connection, msg["id"]):
            return
        coord = _get_coord(hass)
        if coord is None:
            connection.send_result(msg["id"], {"backups": []})
            return

        try:
            backup_mgr = getattr(coord, "_backup_manager", None)
            if backup_mgr and hasattr(backup_mgr, "list_backups"):
                backups = await hass.async_add_executor_job(backup_mgr.list_backups)
            else:
                backups = []
            connection.send_result(msg["id"], {"backups": backups})
        except Exception as e:
            connection.send_error(msg["id"], "error", str(e))

    # ── 传感器管理 WS END ─────────────────────────────────────────────────────

    return (
        ws_get_devices,
        ws_get_habits,
        ws_get_rules,
        ws_get_ai_scenes,
        ws_get_energy_stats,
        ws_get_transactions,
        ws_get_decision_stats,
        ws_get_behavior_patterns,
        ws_get_ai_actions,
        ws_get_sys_log,
        ws_get_terminal_log,
        ws_get_frigate_cameras,
        ws_get_learning_stats,
        ws_get_frigate_zones,
        ws_save_frigate_zone,
        ws_get_presence_sensors,
        ws_save_sensor_type,
        ws_get_room_topology,
        ws_list_backups,
    )

