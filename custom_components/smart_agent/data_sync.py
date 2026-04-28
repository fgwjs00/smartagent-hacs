"""
DataSyncMixin — 多机数据同步与设备心跳模块（v4.8.78）。

职责：
  1. 设备心跳：每 6 小时向 SmartAgent Cloud 上报版本 + 运行统计，
     并接收"是否有新版本"等服务端指令。
  2. 训练数据回传：将本地 training_data / corrections 脱敏后批量上传，
     用于联邦学习和通用先验模型改进。
  3. 同步标记：已成功上传的记录打上 synced_at 时间戳，避免重复上传。

隐私设计（不上传任何个人可识别信息）：
  - training_samples: 仅含 feature_json（6 维数值向量）+ label（0/1）
    + decision_actions_json（只含 service 和参数，不含 entity_id）
  - corrections:      仅含 ai_service + user_state + hour + weekday
  - 永远不上传：context_json（完整 HA 上下文）/ entity_id / 房间名 / 地址

架构规则：
  - 所有 DB 操作通过 self._db（DatabaseService），在 executor 中执行
  - HTTP 请求使用 asyncio 协程（aiohttp），在事件循环中执行
  - 同步失败时静默跳过，不中断 HA 主流程
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    CONF_DATA_SYNC_ENABLED,
    CONF_DEPLOY_NAME,
    CONF_LICENSE_KEY,
    DATA_SYNC_BATCH_SIZE,
    DATA_SYNC_INTERVAL,
    DEFAULT_DATA_SYNC_ENABLED,
    DEFAULT_DEPLOY_NAME,
    SA_DATA_SYNC_URL,
    SA_HEARTBEAT_URL,
)

_LOGGER = logging.getLogger(__name__)

# 心跳 / 同步超时（秒），避免网络阻塞 HA 事件循环
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15)


class DataSyncMixin:
    """
    数据同步 Mixin — 向 SmartAgent Cloud 上报心跳和训练数据。

    依赖（由 SmartAgentCoordinator 提供）：
        self.hass           — HomeAssistant 实例
        self._db            — DatabaseService 实例
        self._license_key   — License Key 字符串
        self._instance_id   — HA 实例唯一 ID
        self._start_time    — 集成启动时间 (datetime)
        self.hass.config.config_dir — HA 配置目录（用于读取 manifest 版本）
    """

    # ── 初始化 ───────────────────────────────────────────────────────────────

    def _init_data_sync(self) -> None:
        """在 coordinator.__init__ 中调用，初始化同步状态。"""
        data = self.entry.options if hasattr(self, "entry") else {}
        self._data_sync_enabled: bool = bool(
            data.get(CONF_DATA_SYNC_ENABLED, DEFAULT_DATA_SYNC_ENABLED)
        )
        self._deploy_name: str = str(data.get(CONF_DEPLOY_NAME, DEFAULT_DEPLOY_NAME))
        self._sync_task: asyncio.Task | None = None
        self._sync_http_session: aiohttp.ClientSession | None = None

    # ── 启停管理 ─────────────────────────────────────────────────────────────

    async def _start_data_sync(self) -> None:
        """启动后台定时同步任务（在 coordinator._async_setup 完成后调用）。

        使用 asyncio.ensure_future() 而非 hass.async_create_task()：
        后者创建的 Task 会被 HA bootstrap 追踪，_sync_loop() 是永久循环，
        会导致 HA 启动超时（Setup timed out for bootstrap）。
        """
        if not self._data_sync_enabled:
            _LOGGER.debug("[DataSync] 数据同步已禁用，跳过启动")
            return
        if self._sync_task and not self._sync_task.done():
            return
        import asyncio as _asyncio
        self._sync_task = _asyncio.ensure_future(self._sync_loop())
        _LOGGER.info("[DataSync] 后台同步任务已启动（间隔 %d 小时）", DATA_SYNC_INTERVAL // 3600)

    async def _stop_data_sync(self) -> None:
        """停止同步任务并关闭 HTTP Session（在集成卸载时调用）。"""
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        if self._sync_http_session and not self._sync_http_session.closed:
            await self._sync_http_session.close()

    # ── 主同步循环 ───────────────────────────────────────────────────────────

    async def _sync_loop(self) -> None:
        """
        定时循环：首次立即执行心跳，之后每 DATA_SYNC_INTERVAL 秒执行一次完整同步。
        """
        # 集成启动后等待 60 秒再首次同步（避免影响 HA 启动性能）
        await asyncio.sleep(60)
        while True:
            try:
                await self._do_heartbeat()
                if self._data_sync_enabled:
                    await self._do_data_sync()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _LOGGER.debug("[DataSync] 同步周期异常（不影响主流程）: %s", exc)
            await asyncio.sleep(DATA_SYNC_INTERVAL)

    # ── 心跳上报 ─────────────────────────────────────────────────────────────

    async def _do_heartbeat(self) -> None:
        """向服务端发送心跳，上报版本和运行统计，接收服务端指令。"""
        license_key = getattr(self, "_license_key", "")
        instance_id = getattr(self, "_instance_id", "")
        if not license_key or not instance_id:
            return

        version = self._get_current_version()
        stats = await self.hass.async_add_executor_job(self._collect_stats)

        payload = {
            "license_key": license_key,
            "instance_id": instance_id,
            "version": version,
            "deploy_name": self._deploy_name,
            "stats": stats,
        }

        try:
            session = await self._get_http_session()
            async with session.post(SA_HEARTBEAT_URL, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("has_update"):
                        latest = data.get("latest_version", "")
                        force = data.get("force_update", False)
                        msg = f"SmartAgent 有新版本 {latest} 可用"
                        if force:
                            msg += "（建议尽快更新）"
                        _LOGGER.info("[DataSync] %s", msg)
                        if hasattr(self, "_sys_log"):
                            self._sys_log("INFO", f"[更新] {msg}")
                else:
                    _LOGGER.debug("[DataSync] 心跳响应 HTTP %s", resp.status)
        except Exception as exc:
            _LOGGER.debug("[DataSync] 心跳请求失败（网络问题）: %s", exc)

    def _collect_stats(self) -> dict:
        """
        收集本地运行统计数据（在 executor 中执行）。

        Returns:
            包含训练样本数、修正数、缓存大小等统计信息的字典。
        """
        stats: dict[str, Any] = {
            "training_samples": 0,
            "corrections_count": 0,
            "decision_cache_size": 0,
            "ai_calls_today": 0,
            "uptime_hours": 0.0,
        }
        try:
            stats["training_samples"] = self._db.query_scalar(
                "SELECT COUNT(*) FROM training_data WHERE is_verified = 1"
            ) or 0
            stats["corrections_count"] = self._db.query_scalar(
                "SELECT COUNT(*) FROM corrections"
            ) or 0
            stats["decision_cache_size"] = self._db.query_scalar(
                "SELECT COUNT(*) FROM decision_cache"
            ) or 0
            today = datetime.now().strftime("%Y-%m-%d")
            stats["ai_calls_today"] = self._db.query_scalar(
                "SELECT COUNT(*) FROM training_data WHERE time >= ?", (today,)
            ) or 0
            if hasattr(self, "_start_time"):
                elapsed = (datetime.now() - self._start_time).total_seconds()
                stats["uptime_hours"] = round(elapsed / 3600, 1)
        except Exception as exc:
            _LOGGER.debug("[DataSync] 统计采集失败: %s", exc)
        return stats

    # ── 训练数据回传 ─────────────────────────────────────────────────────────

    async def _do_data_sync(self) -> None:
        """
        读取未同步的训练数据和修正记录，脱敏后批量上传到 SmartAgent Cloud。
        上传成功后打 synced_at 时间戳，避免重复上传。
        """
        license_key = getattr(self, "_license_key", "")
        instance_id = getattr(self, "_instance_id", "")
        if not license_key or not instance_id:
            return

        # 在 executor 中读取待同步数据
        samples, sample_ids = await self.hass.async_add_executor_job(
            self._get_unsynced_training_data
        )
        corrections, correction_ids = await self.hass.async_add_executor_job(
            self._get_unsynced_corrections
        )

        if not samples and not corrections:
            _LOGGER.debug("[DataSync] 无待同步数据")
            return

        payload = {
            "license_key": license_key,
            "instance_id": instance_id,
            "version": self._get_current_version(),
            "deploy_name": self._deploy_name,
            "training_samples": samples,
            "corrections": corrections,
        }

        try:
            session = await self._get_http_session()
            async with session.post(SA_DATA_SYNC_URL, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    accepted_s = result.get("accepted_samples", 0)
                    accepted_c = result.get("accepted_corrections", 0)
                    _LOGGER.info(
                        "[DataSync] 上传成功：%d 条训练样本，%d 条修正记录",
                        accepted_s, accepted_c,
                    )
                    # 标记已同步（executor 中执行 DB 写入）
                    if sample_ids:
                        await self.hass.async_add_executor_job(
                            self._mark_synced_training, sample_ids
                        )
                    if correction_ids:
                        await self.hass.async_add_executor_job(
                            self._mark_synced_corrections, correction_ids
                        )
                else:
                    _LOGGER.warning("[DataSync] 数据上传失败: HTTP %s", resp.status)
        except Exception as exc:
            _LOGGER.debug("[DataSync] 数据上传异常（稍后重试）: %s", exc)

    def _get_unsynced_training_data(self) -> tuple[list[dict], list[int]]:
        """
        查询未同步的已验证训练样本，脱敏后返回。

        Returns:
            (脱敏后的样本列表, 原始记录 ID 列表)
        """
        try:
            rows = self._db.query(
                "SELECT id, time, feature_json, decision_json, label "
                "FROM training_data "
                "WHERE is_verified = 1 AND synced_at IS NULL "
                "ORDER BY id ASC LIMIT ?",
                (DATA_SYNC_BATCH_SIZE,),
            ) or []
        except Exception as exc:
            _LOGGER.debug("[DataSync] 读取训练数据失败: %s", exc)
            return [], []

        samples = []
        ids = []
        for row in rows:
            try:
                desensitized_actions = _desensitize_decision(row.get("decision_json") or "")
                samples.append({
                    "time": row["time"],
                    "feature_json": row.get("feature_json") or "",
                    "decision_actions_json": desensitized_actions,
                    "label": row.get("label", 1),
                })
                ids.append(row["id"])
            except Exception as exc:
                _LOGGER.debug("[DataSync] 样本脱敏失败，跳过: %s", exc)
        return samples, ids

    def _get_unsynced_corrections(self) -> tuple[list[dict], list[int]]:
        """
        查询未同步的修正记录，脱敏后返回（仅保留统计特征，不含设备和房间名）。

        Returns:
            (脱敏后的修正列表, 原始记录 ID 列表)
        """
        try:
            rows = self._db.query(
                "SELECT id, time, ai_service, user_state, hour, weekday "
                "FROM corrections "
                "WHERE synced_at IS NULL "
                "ORDER BY id ASC LIMIT ?",
                (DATA_SYNC_BATCH_SIZE,),
            ) or []
        except Exception as exc:
            _LOGGER.debug("[DataSync] 读取修正记录失败: %s", exc)
            return [], []

        corrections = []
        ids = []
        for row in rows:
            corrections.append({
                "time": row["time"],
                "ai_service": row.get("ai_service", ""),
                "user_state": row.get("user_state", ""),
                "hour": row.get("hour", 0),
                "weekday": row.get("weekday", 0),
            })
            ids.append(row["id"])
        return corrections, ids

    def _mark_synced_training(self, ids: list[int]) -> None:
        """将已上传的训练样本打上 synced_at 时间戳。"""
        if not ids:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        placeholders = ",".join("?" * len(ids))
        _ok = self._db_exec(
            f"UPDATE training_data SET synced_at = ? WHERE id IN ({placeholders})",
            (ts, *ids),
        )
        if not _ok:
            _LOGGER.debug("[DataSync] 标记训练样本同步状态失败: ids=%s", len(ids))

    def _mark_synced_corrections(self, ids: list[int]) -> None:
        """将已上传的修正记录打上 synced_at 时间戳。"""
        if not ids:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        placeholders = ",".join("?" * len(ids))
        _ok = self._db_exec(
            f"UPDATE corrections SET synced_at = ? WHERE id IN ({placeholders})",
            (ts, *ids),
        )
        if not _ok:
            _LOGGER.debug("[DataSync] 标记修正记录同步状态失败: ids=%s", len(ids))

    # ── 工具方法 ─────────────────────────────────────────────────────────────

    def _get_current_version(self) -> str:
        """读取 manifest.json 中的版本号。"""
        try:
            import os
            manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
            with open(manifest_path, encoding="utf-8") as f:
                return json.load(f).get("version", "unknown")
        except Exception:
            return "unknown"

    async def _get_http_session(self) -> aiohttp.ClientSession:
        """获取（或重建）共享 HTTP Session。"""
        if self._sync_http_session is None or self._sync_http_session.closed:
            self._sync_http_session = aiohttp.ClientSession(timeout=_HTTP_TIMEOUT)
        return self._sync_http_session


# ── 模块级工具函数 ────────────────────────────────────────────────────────────

def _desensitize_decision(decision_json: str) -> str:
    """
    从 decision_json 中提取动作信息并脱敏：
    保留 service / brightness / color_temp / temperature 等参数，
    去除 entity_id（避免泄露家庭设备信息）。

    Args:
        decision_json: AI 推理输出的 JSON 字符串

    Returns:
        脱敏后的动作列表 JSON 字符串（空字符串表示解析失败）
    """
    if not decision_json:
        return ""
    try:
        decision = json.loads(decision_json)
        actions = decision.get("actions", [])
        safe_actions = []
        _SAFE_KEYS = {"service", "brightness", "color_temp", "temperature",
                      "brightness_pct", "hvac_mode", "fan_mode", "position"}
        for action in actions:
            if not isinstance(action, dict):
                continue
            safe = {k: v for k, v in action.items() if k in _SAFE_KEYS}
            # data 子字典也脱敏
            if "data" in action and isinstance(action["data"], dict):
                safe["data"] = {k: v for k, v in action["data"].items()
                                if k in _SAFE_KEYS}
            if safe:
                safe_actions.append(safe)
        return json.dumps(safe_actions, ensure_ascii=False) if safe_actions else ""
    except Exception:
        return ""
