"""
SmartAgent Update 平台实体 (Phase 9.7)。

在 HA 设备/更新面板中显示 SmartAgent 当前版本和最新版本，
支持一键跳转到 GitHub Releases 查看更新日志。

检查逻辑：
  - 集成加载时异步检查一次 GitHub Releases API
  - 每 24 小时周期性检查（由 patrol.py 触发或独立 scheduler）
  - 发现新版本时推送 HA 持久通知（可在 UI 中手动触发 update.install）

隐私说明：
  - 仅向 GitHub 公共 API 发送 GET 请求，无任何用户数据附带
  - 请求 URL: https://api.github.com/repos/fgwjs00/smart_agent/releases/latest
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.components.persistent_notification import async_create as pn_async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

#: 自有版本服务器（优先）
_SA_VERSION_URL = "https://license.smartagent.ai/v1/version/latest"
#: GitHub Releases API（回退，自有服务器不可达时使用）
_GITHUB_RELEASES_URL = "https://api.github.com/repos/fgwjs00/smart_agent/releases/latest"

#: 版本检查间隔
_CHECK_INTERVAL = timedelta(hours=24)


def _handle_update_task_done(task: Any, *, label: str) -> None:
    try:
        if hasattr(task, "cancelled") and task.cancelled():
            return
        exc = task.exception()
    except asyncio.CancelledError:
        return
    except Exception as err:
        _LOGGER.warning(
            "[Update] background task exception retrieval failed | task=%s exception_type=%s: %s",
            label,
            type(err).__name__,
            err,
            exc_info=True,
        )
        return
    if exc is None:
        return
    _LOGGER.warning(
        "[Update] background task failed | task=%s exception_type=%s: %s",
        label,
        type(exc).__name__,
        exc,
        exc_info=(type(exc), exc, exc.__traceback__),
    )


def _observe_update_task(task: Any, label: str) -> Any:
    try:
        add_done_callback = getattr(task, "add_done_callback", None)
        if callable(add_done_callback):
            add_done_callback(lambda done: _handle_update_task_done(done, label=label))
    except Exception as exc:
        _LOGGER.debug("[Update] failed to attach task observer | task=%s: %s", label, exc)
    return task


def _spawn_update_task(hass: HomeAssistant, coro: Any, label: str) -> Any | None:
    try:
        task = hass.async_create_task(coro)
    except Exception as exc:
        close = getattr(coro, "close", None)
        if callable(close):
            close()
        _LOGGER.warning(
            "[Update] background task create failed | task=%s exception_type=%s: %s",
            label,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return None
    return _observe_update_task(task, label)


# 在模块导入时（HA 事件循环启动前）读取 manifest.json，避免在异步上下文中执行阻塞 I/O
def _read_manifest_version() -> str:
    """从 manifest.json 读取当前版本号（模块级同步调用，在事件循环外执行）。"""
    import json as _json
    import os as _os
    try:
        _path = _os.path.join(_os.path.dirname(__file__), "manifest.json")
        with open(_path, encoding="utf-8") as _f:
            return _json.load(_f).get("version", "unknown")
    except Exception:
        return "unknown"

_CURRENT_VERSION: str = _read_manifest_version()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """注册 SmartAgent update 实体。"""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    entity = SmartAgentUpdateEntity(hass, entry, coordinator)
    async_add_entities([entity])

    # 立即检查一次
    _spawn_update_task(hass, entity.async_check_for_update(), "initial_update_check")
    # 每 24 小时定时检查，返回值是取消函数；存入实体以便卸载时注销
    entity._cancel_interval = async_track_time_interval(
        hass, entity._scheduled_check, _CHECK_INTERVAL
    )


class SmartAgentUpdateEntity(UpdateEntity):
    """SmartAgent 版本更新实体。"""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = UpdateEntityFeature.RELEASE_NOTES
    _attr_has_entity_name = True
    _attr_name = "SmartAgent 更新"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator) -> None:
        """初始化。"""
        self.hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_update"
        self._cancel_interval: Any = None  # 定时器取消函数，卸载时调用

        # 使用模块级常量（在事件循环外已读取，避免阻塞性 I/O 警告）
        self._current_version = _CURRENT_VERSION
        self._latest_version: str | None = None
        self._release_notes: str = ""
        self._release_url: str = ""

    @property
    def device_info(self) -> DeviceInfo:
        """将实体关联到 SmartAgent 设备，使其出现在设备页面而非孤立实体。"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="SmartAgent",
            manufacturer="SmartAgent",
            model="AI 智能家居控制器",
        )

    async def async_will_remove_from_hass(self) -> None:
        """集成卸载时取消定时器，防止内存泄漏。"""
        if self._cancel_interval is not None:
            self._cancel_interval()
            self._cancel_interval = None
            _LOGGER.debug("[Update] 已取消版本检查定时器")

    @property
    def installed_version(self) -> str | None:
        """当前安装的版本。"""
        return self._current_version

    @property
    def latest_version(self) -> str | None:
        """最新可用版本（来自 GitHub Releases）。"""
        return self._latest_version

    @property
    def release_url(self) -> str | None:
        """发布页面 URL。"""
        return self._release_url or None

    async def async_release_notes(self) -> str | None:
        """返回 Release Notes（显示在 HA 更新卡片中）。"""
        return self._release_notes or None

    async def async_check_for_update(self) -> None:
        """
        异步检查最新版本。优先查询自有版本服务器，不可达时回退 GitHub Releases。

        成功时更新 _latest_version 并触发实体状态刷新；
        网络错误时静默失败（不影响正常使用）。
        """
        tag, release_url, release_notes, force_update = await self._fetch_version_info()
        if not tag:
            return

        self._latest_version = tag
        self._release_url = release_url
        self._release_notes = release_notes

        if self._is_newer(tag, self._current_version):
            _LOGGER.info("[Update] 发现新版本 v%s（当前 v%s）", tag, self._current_version)
            force_hint = "**⚠️ 强制更新：建议尽快升级**\n\n" if force_update else ""
            pn_async_create(
                self.hass,
                message=(
                    f"SmartAgent 有新版本可用：**v{tag}**（当前 v{self._current_version}）\n\n"
                    f"{force_hint}"
                    f"[查看更新日志]({release_url})\n\n"
                    f"通过 HACS 或手动下载更新。"
                ),
                title="SmartAgent 更新",
                notification_id="smart_agent_update",
            )
        else:
            _LOGGER.debug("[Update] 当前已是最新版本 v%s", self._current_version)

        self.async_write_ha_state()

    async def _fetch_version_info(self) -> tuple[str, str, str, bool]:
        """
        依次尝试自有服务器和 GitHub，返回 (版本号, 下载地址, 更新日志, 是否强制更新)。

        Returns:
            四元组，失败时版本号为空字符串。
        """
        # 优先查询自有版本服务器
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    _SA_VERSION_URL,
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tag = str(data.get("version", "")).lstrip("v")
                        if tag:
                            _LOGGER.debug("[Update] 自有服务器版本查询成功: v%s", tag)
                            return (
                                tag,
                                data.get("download_url", ""),
                                data.get("changelog", "")[:2000],
                                bool(data.get("force_update", False)),
                            )
        except Exception as exc:
            _LOGGER.debug("[Update] 自有服务器不可达，回退 GitHub: %s", exc)

        # 回退：查询 GitHub Releases
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    _GITHUB_RELEASES_URL,
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.info("[Update] GitHub API 返回 %d，跳过版本检查", resp.status)
                        return "", "", "", False
                    data = await resp.json()

            tag = data.get("tag_name", "").lstrip("v")
            if not tag:
                return "", "", "", False
            return tag, data.get("html_url", ""), data.get("body", "")[:2000], False

        except asyncio.TimeoutError:
            _LOGGER.info("[Update] GitHub API 超时，跳过本次检查")
        except Exception as exc:
            _LOGGER.warning("[Update] 版本检查异常: %s", exc)
        return "", "", "", False

    async def _scheduled_check(self, _now: Any = None) -> None:
        """定期版本检查回调。"""
        await self.async_check_for_update()

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        """
        比较版本号（SemVer）：latest > current 时返回 True。

        Args:
            latest: 最新版本字符串，如 "4.7.0"
            current: 当前版本字符串，如 "4.6.0"
        """
        try:
            def _parse(v: str) -> tuple[int, ...]:
                return tuple(int(x) for x in v.split(".")[:3])
            return _parse(latest) > _parse(current)
        except (ValueError, AttributeError):
            return False
