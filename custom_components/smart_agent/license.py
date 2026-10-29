"""
LicenseMixin — SmartAgent SaaS License 验证模块。

验证流程：
  1. 在线验证：调用云端 License 服务，获取套餐信息和到期时间
  2. 离线缓存：将验证结果缓存到本地文件（LICENSE_CACHE_TTL 秒内有效），网络异常时降级使用
  3. 无 Key / 验证失败：显示免费版授权状态，不限制普通本地功能

套餐额度仅供展示；当前未接入推理用量计量或配额扣减。
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    LICENSE_CACHE_TTL,
    LICENSE_DAILY_LIMITS,
    LICENSE_TIER_DEFAULT,
    LICENSE_TIER_FREE,
    LICENSE_TIER_LABELS,
    LICENSE_VERIFY_URL,
)
from .storage_capacity import DEFAULT_ADMISSION, StorageCapacityError

_LOGGER = logging.getLogger(__name__)

# 本地缓存文件名
_LICENSE_CACHE_FILE = "smart_agent_license.json"
_LICENSE_INSTANCE_FILE = "smart_agent_license_instance.json"
_INSTANCE_LOCK = Lock()
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
    """Mixin: SaaS License 验证及套餐信息展示。"""

    def _init_license(self) -> None:
        """初始化 License 相关状态（在 __init__ 中调用）。"""
        self._license_key: str = ""
        self._license_tier: str = LICENSE_TIER_DEFAULT
        self._license_expires: str = ""          # ISO 日期字符串，如 "2026-12-31"
        self._license_instance_id: str = ""      # 绑定的 HA 实例 ID
        self._license_verified_at: float = 0.0   # 上次成功验证的时间戳
        self._license_valid: bool = False         # 当前 License 是否有效
        self._license_from_cache = False

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

    def get_license_status(self) -> dict:
        """返回当前 License 状态（供面板展示）。"""
        if self._license_valid and (
            self._is_license_expired(self._license_expires)
            or (self._license_from_cache and not self._cache_time_valid(self._license_verified_at))
        ):
            self._license_valid = False
            self._license_tier = LICENSE_TIER_FREE
        tier = self._license_tier if self._license_valid else LICENSE_TIER_FREE
        return {
            "has_key": bool(self._license_key),
            "valid": self._license_valid,
            "tier": tier,
            "tier_label": LICENSE_TIER_LABELS.get(tier, tier),
            "expires": self._license_expires,
            **self._quota_information(tier),
        }

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    async def _async_verify_online(self, lk: str) -> dict:
        """调用云端 License API 验证 Key。"""
        try:
            instance_id = await self.hass.async_add_executor_job(self._get_instance_id)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LICENSE_VERIFY_URL,
                    json={"license_key": lk, "instance_id": instance_id},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tier = data.get("tier")
                        expires = data.get("expires")
                        expires = "" if expires is None else expires
                        if (data.get("valid") is not True
                                or data.get("instance_id") != instance_id
                                or tier not in LICENSE_DAILY_LIMITS):
                            return self._build_result(False, LICENSE_TIER_FREE, "", "License 验证响应无效")
                        if self._is_license_expired(expires):
                            return self._build_result(False, LICENSE_TIER_FREE, expires, "License 已到期，请续费")
                        verified_at = time.time()
                        await self.hass.async_add_executor_job(
                            self._save_license_cache, lk, tier, expires, verified_at
                        )
                        self._apply_license(lk, tier, expires, verified_at)
                        return self._build_result(True, tier, expires, "License 验证成功")
                    elif resp.status == 403:
                        return self._build_result(False, LICENSE_TIER_FREE, "", "License Key 无效或已被停用")
                    elif resp.status == 409:
                        return self._build_result(False, LICENSE_TIER_FREE, "", "License 已绑定其他实例，请联系开发者")
                    elif resp.status == 410:
                        return self._build_result(False, LICENSE_TIER_FREE, "", "License 已到期，请续费")
                    else:
                        return self._build_result(False, LICENSE_TIER_FREE, "", f"License 验证失败（HTTP {resp.status}）")
        except (aiohttp.ClientError, TimeoutError):
            _LOGGER.warning("[License] 网络验证失败，检查有效期内的本地缓存")
            return await self._async_use_license_cache(lk)
        except Exception as exc:
            _err_msg = f"License 验证异常（{exc}），降级到免费版"
            _LOGGER.warning("[License] %s", _err_msg)
            if hasattr(self, "_sys_log"):
                self._sys_log("WARN", f"[License] {_err_msg}")
            return self._build_result(False, LICENSE_TIER_FREE, "", _err_msg)

    async def _async_use_license_cache(self, lk: str) -> dict:
        cached = await self.hass.async_add_executor_job(self._load_license_cache, lk)
        if cached is not None:
            tier, expires = cached["tier"], cached["expires"]
            self._apply_license(lk, tier, expires, cached["verified_at"], cached_hit=True)
            return self._build_result(True, tier, expires, "License 离线验证（使用有效期内缓存）")
        return self._build_result(False, LICENSE_TIER_FREE, "", "License 网络验证失败且无有效缓存，按免费版运行")

    def _apply_license(self, lk: str, tier: str, expires: str, verified_at: float, cached_hit: bool = False) -> None:
        """将验证结果应用到内部状态。"""
        self._license_key = lk
        self._license_tier = tier
        self._license_expires = expires
        self._license_valid = True
        self._license_verified_at = verified_at
        self._license_from_cache = cached_hit
        self._sys_log("INFO",
            f"[License] {'缓存命中' if cached_hit else '在线验证'}成功 "
            f"套餐={LICENSE_TIER_LABELS.get(tier, tier)} 到期={expires or '永久'}")

    def _build_result(self, valid: bool, tier: str, expires: str, message: str) -> dict:
        """构建统一返回结构。"""
        if not valid:
            self._license_valid = False
            self._license_tier = LICENSE_TIER_FREE
        return {
            "valid": valid,
            "tier": tier,
            "tier_label": LICENSE_TIER_LABELS.get(tier, tier),
            "expires": expires,
            "message": message,
            **self._quota_information(tier),
        }

    @staticmethod
    def _quota_information(tier: str) -> dict:
        """参考套餐额度不是实际用量，也不是生产执行限制。"""
        return {
            "daily_limit": LICENSE_DAILY_LIMITS.get(tier, 30),
            "daily_used": None,
            "daily_remaining": None,
            "usage_metered": False,
            "quota_enforced": False,
        }

    def _is_license_expired(self, expires: str) -> bool:
        """检查到期日期是否已过（空字符串视为永久有效）。"""
        if expires == "":
            return False
        try:
            return datetime.strptime(expires, "%Y-%m-%d").date() < self._license_local_now().date()
        except (TypeError, ValueError):
            _LOGGER.warning("[License] 到期日期无效，不接受该授权状态")
            return True

    def _get_instance_id(self) -> str:
        """持久随机安装身份；重启复用，保存失败不发送临时身份。"""
        with _INSTANCE_LOCK:
            if not self._license_instance_id:
                path = self._get_license_instance_path()
                try:
                    with open(path, encoding="utf-8") as stream:
                        instance_id = json.load(stream)["instance_id"]
                    if not isinstance(instance_id, str) or UUID(instance_id).hex != instance_id:
                        raise ValueError("License 安装身份无效")
                except FileNotFoundError:
                    instance_id = uuid4().hex
                    content = json.dumps({"instance_id": instance_id}, ensure_ascii=False).encode("utf-8")
                    with DEFAULT_ADMISSION.reserve(path, len(content), write_class="normal"):
                        created = False
                        try:
                            with open(path, "xb") as stream:
                                created = True
                                stream.write(content)
                                stream.flush()
                                os.fsync(stream.fileno())
                        except BaseException as exc:
                            if created:
                                try:
                                    Path(path).unlink(missing_ok=True)
                                except OSError as cleanup_exc:
                                    exc.add_note(f"License 身份文件清理失败: {type(cleanup_exc).__name__}")
                                    _LOGGER.warning("[License] 未完成的身份文件清理失败")
                            raise
                    _LOGGER.debug("[License] 已持久保存新的安装身份")
                self._license_instance_id = instance_id
        return self._license_instance_id

    def _get_license_instance_path(self) -> str:
        directory = getattr(self, "_config_dir", "")
        if not directory:
            raise ValueError("未配置 HA 安装目录")
        return os.path.join(directory, _LICENSE_INSTANCE_FILE)

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
            lk_hash = hashlib.sha256(lk.encode()).hexdigest()[:16]
            if (data.get("key_hash") != lk_hash
                    or data.get("instance_id") != self._get_instance_id()
                    or data.get("tier") not in LICENSE_DAILY_LIMITS
                    or not self._cache_time_valid(data.get("verified_at"))
                    or self._is_license_expired(data.get("expires"))):
                return None
            return data
        except Exception:
            return None

    @staticmethod
    def _cache_time_valid(verified_at: object) -> bool:
        return (type(verified_at) in (int, float) and math.isfinite(verified_at)
                and 0 <= time.time() - verified_at < LICENSE_CACHE_TTL)

    def _save_license_cache(self, lk: str, tier: str, expires: str, verified_at: float) -> None:
        """将验证结果写入本地缓存（同步，在 executor 中调用）。"""
        try:
            path = self._get_license_cache_path()
            lk_hash = hashlib.sha256(lk.encode()).hexdigest()[:16]
            data = {
                "key_hash": lk_hash,
                "instance_id": self._get_instance_id(),
                "tier": tier,
                "expires": expires,
                "verified_at": verified_at,
            }
            content = json.dumps(data, ensure_ascii=False).encode("utf-8")
            # 旧文件已计入实际占用；新增峰值是同目录临时文件的完整编码字节。
            with DEFAULT_ADMISSION.reserve(path, len(content), write_class="normal"):
                fd, temporary = tempfile.mkstemp(
                    dir=os.path.dirname(path), prefix=f".{os.path.basename(path)}.", suffix=".tmp"
                )
                try:
                    with os.fdopen(fd, "wb") as stream:
                        fd = -1
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, path)
                finally:
                    if fd >= 0:
                        os.close(fd)
                    Path(temporary).unlink(missing_ok=True)
        except StorageCapacityError as exc:
            _LOGGER.warning("[License] 缓存写入延后: %s", exc.reason)
        except Exception as exc:
            _LOGGER.warning("[License] 写入缓存失败: %s", exc)
