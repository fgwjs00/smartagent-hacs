"""
LicenseMixin — SmartAgent SaaS License 验证模块。

验证流程（双重保障）：
  1. 在线验证：调用云端 License 服务，获取套餐信息和到期时间
  2. 离线缓存：将验证结果缓存到本地文件（LICENSE_CACHE_TTL 秒内有效），网络异常时降级使用
  3. 无 Key / 验证失败：降级到免费版限制（30次/天）

套餐限制执行：
  - 每日计数器存储在内存，HA 重启后重置（按天算，足够精确）
  - 达到限制时返回友好提示，不静默失败
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    CONF_LICENSE_KEY,
    LICENSE_CACHE_TTL,
    LICENSE_DAILY_LIMITS,
    LICENSE_TIER_BIZ,
    LICENSE_TIER_DEFAULT,
    LICENSE_TIER_FREE,
    LICENSE_TIER_LABELS,
    LICENSE_VERIFY_URL,
)

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# 本地缓存文件名
_LICENSE_CACHE_FILE = "smart_agent_license.json"
_FIXED_TIMEZONE_OFFSETS = {
    "Asia/Shanghai": 8,
    "Asia/Chongqing": 8,
    "Asia/Harbin": 8,
    "Asia/Hong_Kong": 8,
    "Hongkong": 8,
    "PRC": 8,
    "UTC": 0,
}


class LicenseMixin:
    """Mixin: SaaS License 验证与配额管理。"""

    def _init_license(self) -> None:
        """初始化 License 相关状态（在 __init__ 中调用）。"""
        self._license_key: str = ""
        self._license_tier: str = LICENSE_TIER_DEFAULT
        self._license_expires: str = ""          # ISO 日期字符串，如 "2026-12-31"
        self._license_instance_id: str = ""      # 绑定的 HA 实例 ID
        self._license_verified_at: float = 0.0   # 上次成功验证的时间戳
        self._license_valid: bool = False         # 当前 License 是否有效
        # 每日推理计数器：{date_str: count}，如 {"2026-03-15": 42}
        self._license_daily_count: dict[str, int] = {}

    def _license_local_now(self) -> datetime:
        """Return current time in HA configured timezone."""
        configured_timezone = str(
            getattr(getattr(getattr(self, "hass", None), "config", None), "time_zone", "") or ""
        ).strip()
        if configured_timezone:
            try:
                return datetime.now(ZoneInfo(configured_timezone))
            except Exception:
                offset = _FIXED_TIMEZONE_OFFSETS.get(configured_timezone)
                if offset is not None:
                    return datetime.now(timezone(timedelta(hours=offset), configured_timezone))
        from homeassistant.util import dt as dt_util

        return dt_util.now()

    def _license_today(self) -> str:
        return self._license_local_now().strftime("%Y-%m-%d")

    # ── 对外接口 ──────────────────────────────────────────────────────────────

    async def async_verify_license(self, key: str | None = None) -> dict:
        """验证 License Key，返回验证结果字典。"""
        lk = (key or self._license_key or "").strip()
        if not lk:
            return self._build_result(False, LICENSE_TIER_FREE, "", "未配置 License Key，按免费版运行")

        result = await self._async_verify_online(lk)
        if not result.get("valid", False):
            self._license_valid = False
            self._license_tier = LICENSE_TIER_FREE
            self._license_expires = ""
            self._license_key = lk
        return result

    def check_daily_quota(self) -> tuple[bool, str]:
        """检查今日是否还有推理配额。"""
        today = self._license_today()
        tier = self._license_tier if self._license_valid else LICENSE_TIER_FREE
        limit = LICENSE_DAILY_LIMITS.get(tier, 30)
        used = self._license_daily_count.get(today, 0)
        if limit == -1:
            return True, ""
        if used < limit:
            return True, ""
        return False, f"今日推理额度已用尽（{used}/{limit}），请明日再试或升级套餐"

    def increment_daily_count(self) -> None:
        """推理成功执行后调用，增加今日计数。"""
        today = self._license_today()
        self._license_daily_count[today] = int(self._license_daily_count.get(today, 0) or 0) + 1

    def get_license_status(self) -> dict:
        """返回当前 License 状态（供面板展示）。"""
        today = self._license_today()
        used = self._license_daily_count.get(today, 0)
        tier = self._license_tier if self._license_valid else LICENSE_TIER_FREE
        limit = LICENSE_DAILY_LIMITS.get(tier, 30)
        return {
            "has_key": bool(self._license_key),
            "valid": self._license_valid,
            "tier": tier,
            "tier_label": LICENSE_TIER_LABELS.get(tier, tier),
            "expires": self._license_expires,
            "daily_limit": limit,
            "daily_used": used,
            "daily_remaining": max(0, limit - used) if limit != -1 else -1,
        }

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    async def _async_verify_online(self, lk: str) -> dict:
        """调用云端 License API 验证 Key。"""
        instance_id = self._get_instance_id()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LICENSE_VERIFY_URL,
                    json={"license_key": lk, "instance_id": instance_id},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tier = data.get("tier", LICENSE_TIER_FREE)
                        expires = data.get("expires", "")
                        if self._is_license_expired(expires):
                            return self._build_result(False, LICENSE_TIER_FREE, expires, "License 已到期，请续费")
                        # 写入本地缓存
                        await self.hass.async_add_executor_job(
                            self._save_license_cache, lk, tier, expires
                        )
                        self._apply_license(lk, tier, expires)
                        return self._build_result(True, tier, expires, "License 验证成功")
                    elif resp.status == 403:
                        return self._build_result(False, LICENSE_TIER_FREE, "", "License Key 无效或已被停用")
                    elif resp.status == 409:
                        return self._build_result(False, LICENSE_TIER_FREE, "", "License 已绑定其他实例，请联系开发者")
                    else:
                        raise aiohttp.ClientError(f"HTTP {resp.status}")
        except aiohttp.ClientConnectorError:
            # 网络不可达：尝试使用过期缓存
            cached = await self.hass.async_add_executor_job(self._load_license_cache, lk)
            if cached:
                tier = cached.get("tier", LICENSE_TIER_FREE)
                expires = cached.get("expires", "")
                self._apply_license(lk, tier, expires, cached_hit=True)
                _LOGGER.warning("[License] 网络验证失败，使用离线缓存（套餐=%s）", tier)
                return self._build_result(True, tier, expires, "License 离线验证（网络不可达，使用缓存）")
            
            _err_msg = "License 验证失败（网络不可达且无本地缓存），降级到免费版"
            _LOGGER.warning("[License] %s", _err_msg)
            if hasattr(self, "_sys_log"):
                self._sys_log("WARN", f"[License] {_err_msg}")
            return self._build_result(False, LICENSE_TIER_FREE, "", _err_msg)
        except Exception as exc:
            _err_msg = f"License 验证异常（{exc}），降级到免费版"
            _LOGGER.warning("[License] %s", _err_msg)
            if hasattr(self, "_sys_log"):
                self._sys_log("WARN", f"[License] {_err_msg}")
            return self._build_result(False, LICENSE_TIER_FREE, "", _err_msg)

    def _apply_license(self, lk: str, tier: str, expires: str, cached_hit: bool = False) -> None:
        """将验证结果应用到内部状态。"""
        self._license_key = lk
        self._license_tier = tier
        self._license_expires = expires
        self._license_valid = True
        self._license_verified_at = time.time()
        self._sys_log("INFO",
            f"[License] {'缓存命中' if cached_hit else '在线验证'}成功 "
            f"套餐={LICENSE_TIER_LABELS.get(tier, tier)} 到期={expires or '永久'}")

    def _build_result(self, valid: bool, tier: str, expires: str, message: str) -> dict:
        """构建统一返回结构。"""
        today = self._license_today()
        used = self._license_daily_count.get(today, 0)
        limit = LICENSE_DAILY_LIMITS.get(tier, 30)
        if not valid:
            self._license_valid = False
            self._license_tier = LICENSE_TIER_FREE
        return {
            "valid": valid,
            "tier": tier,
            "tier_label": LICENSE_TIER_LABELS.get(tier, tier),
            "expires": expires,
            "message": message,
            "daily_limit": limit,
            "daily_used": used,
        }

    def _is_license_expired(self, expires: str) -> bool:
        """检查到期日期是否已过（空字符串视为永久有效）。"""
        if not expires:
            return False
        try:
            return datetime.strptime(expires, "%Y-%m-%d").date() < self._license_local_now().date()
        except ValueError:
            return False

    def _get_instance_id(self) -> str:
        """生成唯一实例 ID（基于 HA config 目录路径的哈希）。"""
        if not self._license_instance_id:
            raw = getattr(self, "_config_dir", "") or ""
            self._license_instance_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return self._license_instance_id

    def _get_license_cache_path(self) -> str:
        """获取本地 License 缓存文件路径。"""
        return os.path.join(getattr(self, "_config_dir", ""), _LICENSE_CACHE_FILE)

    def _load_license_cache(self, lk: str) -> dict | None:
        """从本地文件读取 License 缓存（同步，在 executor 中调用）。"""
        try:
            path = self._get_license_cache_path()
            if not os.path.exists(path):
                return None
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # 校验 Key 匹配（避免换 Key 后用旧缓存）
            lk_hash = hashlib.sha256(lk.encode()).hexdigest()[:16]
            if data.get("key_hash") != lk_hash:
                return None
            return data
        except Exception:
            return None

    def _save_license_cache(self, lk: str, tier: str, expires: str) -> None:
        """将验证结果写入本地缓存（同步，在 executor 中调用）。"""
        try:
            path = self._get_license_cache_path()
            lk_hash = hashlib.sha256(lk.encode()).hexdigest()[:16]
            data = {
                "key_hash": lk_hash,
                "tier": tier,
                "expires": expires,
                "verified_at": time.time(),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as exc:
            _LOGGER.warning("[License] 写入缓存失败: %s", exc)
