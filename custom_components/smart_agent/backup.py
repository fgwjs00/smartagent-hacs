"""
SmartAgent 端到端加密云备份模块 (Phase 9.8)。

安全设计原则：
  - 零知识存储：云端只存储密文，服务器无法解密
  - 客户端加密：所有加密/解密在用户本地完成
  - 强密钥派生：PBKDF2-HMAC-SHA256（600,000 轮）
  - 认证加密：AES-256-GCM（防篡改 + 保密性）
  - 每次备份独立 salt + nonce（密钥不重用）

备份内容分级：
  - basic:    设备配置 + 规则/习惯 (~50KB)
  - standard: basic + 行为模式 + 修正记录 (~500KB)
  - full:     standard + 近30天事件日志 (~5MB)

永不备份：生物特征、摄像头画面、音频录音

HA 服务注册：
  smart_agent.backup_now   - 立即备份
  smart_agent.restore_backup - 从云端恢复

隐私说明：
  - 用户密码永远不会离开用户设备
  - 云端接收的只有加密后的二进制密文
  - GDPR 合规：支持 DELETE /api/v1/account/data 彻底删除
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# ── 加密常量 ──────────────────────────────────────────────────────────────────

_SALT_LEN = 16      # bytes，随机盐（per-backup）
_NONCE_LEN = 12     # bytes，GCM nonce（per-backup）
_KEY_LEN = 32       # bytes，AES-256
_PBKDF2_ITER = 600_000  # PBKDF2-HMAC-SHA256 迭代次数（NIST 2024 推荐）
_MAGIC = b"SMAGB01"  # 备份文件魔数（SmartAgent Backup v01）

# ── 备份等级 ──────────────────────────────────────────────────────────────────

BACKUP_LEVEL_BASIC = "basic"
BACKUP_LEVEL_STANDARD = "standard"
BACKUP_LEVEL_FULL = "full"

_FIXED_TIMEZONE_OFFSETS = {
    "Asia/Shanghai": 8,
    "Asia/Chongqing": 8,
    "Asia/Harbin": 8,
    "Asia/Hong_Kong": 8,
    "Hongkong": 8,
    "PRC": 8,
    "UTC": 0,
}


def _restore_text(value: Any, default: Any = "", limit: int = 0) -> str:
    raw = default if value is None else value
    if raw is None:
        raw = ""
    text = str(raw)
    return text[:limit] if limit > 0 else text


class BackupManager:
    """
    SmartAgent 端到端加密云备份管理器。

    使用方法::

        mgr = BackupManager(coordinator)
        # 加密并上传备份
        await mgr.backup_now(password="用户密码", level="standard")
        # 列出云端备份
        backups = await mgr.list_backups()
        # 恢复备份
        await mgr.restore_backup(backup_id="bkp_xxx", password="用户密码")
    """

    def __init__(self, coordinator) -> None:
        """
        Args:
            coordinator: SmartAgentCoordinator 实例（访问 hass、device_info、_memory_db）
        """
        self._coord = coordinator
        self._hass = coordinator.hass
        # 云端 API 基础地址（从集成配置读取，可为空）
        self._cloud_api_url: str = getattr(coordinator, "_backup_cloud_url", "")
        self._cloud_token: str = getattr(coordinator, "_backup_cloud_token", "")
        # 动态读取集成版本号（避免在 executor 线程中重复读文件）
        self._integration_version: str = self._read_manifest_version()

    @staticmethod
    def _read_manifest_version() -> str:
        """从 manifest.json 动态读取集成版本号（仅在初始化时调用一次）。"""
        try:
            manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
            with open(manifest_path, encoding="utf-8") as f:
                return json.load(f).get("version", "unknown")
        except Exception:
            return "unknown"

    def _ha_backup_now(self) -> datetime:
        local_now = getattr(self._coord, "_ha_local_now", None)
        if callable(local_now):
            try:
                value = local_now()
                if isinstance(value, datetime):
                    return value
            except Exception:
                pass

        configured_timezone = str(
            getattr(getattr(getattr(self, "_hass", None), "config", None), "time_zone", "") or ""
        ).strip()
        if configured_timezone:
            try:
                from zoneinfo import ZoneInfo

                return datetime.now(ZoneInfo(configured_timezone))
            except Exception:
                offset = _FIXED_TIMEZONE_OFFSETS.get(configured_timezone)
                if offset is not None:
                    return datetime.now(timezone(timedelta(hours=offset), configured_timezone))

        from homeassistant.util import dt as dt_util

        return dt_util.now()

    def _ha_backup_now_iso(self) -> str:
        return self._ha_backup_now().isoformat()

    def _ha_backup_file_timestamp(self) -> str:
        return self._ha_backup_now().strftime("%Y%m%d_%H%M%S")

    def _ha_backup_datetime_text(self) -> str:
        return self._ha_backup_now().strftime("%Y-%m-%d %H:%M:%S")

    def _ha_backup_timestamp_iso(self, timestamp: float) -> str:
        try:
            tzinfo = self._ha_backup_now().tzinfo
            if tzinfo is not None:
                return datetime.fromtimestamp(float(timestamp), timezone.utc).astimezone(tzinfo).isoformat()
        except Exception:
            pass
        return datetime.fromtimestamp(timestamp).isoformat()

    @staticmethod
    def _sanitize_backup_id(backup_id: str) -> str:
        """
        清洗 backup_id，防止路径穿越（../）或 SSRF 注入。

        仅允许字母、数字、下划线、连字符，长度不超过 128 字符。

        Args:
            backup_id: 用户提供的备份 ID

        Returns:
            清洗后安全的 backup_id

        Raises:
            ValueError: 当 backup_id 包含非法字符时
        """
        import re
        if not backup_id or not re.fullmatch(r"[A-Za-z0-9_\-]{1,128}", backup_id):
            raise ValueError(
                f"非法的 backup_id: '{backup_id}'。"
                "仅允许字母、数字、下划线和连字符（1-128字符）。"
            )
        return backup_id

    # ── 公共 API ──────────────────────────────────────────────────────────────

    async def backup_now(
        self,
        password: str,
        level: str = BACKUP_LEVEL_STANDARD,
    ) -> dict:
        """
        立即执行备份：收集数据 → 序列化 → AES-256-GCM 加密 → 上传云端。

        Args:
            password: 用户备份密码（不存储，不上传，仅用于密钥派生）
            level: 备份等级 basic / standard / full

        Returns:
            {"success": bool, "backup_id": str, "size_bytes": int, "message": str}
        """
        _msg = f"[Backup] 开始备份（等级: {level}）"
        _LOGGER.info(_msg)
        if hasattr(self._coord, "_sys_log"):
            self._coord._sys_log("INFO", _msg)

        try:
            # 1. 在事件循环中快照协调器的内存数据（线程安全）
            snapshot = await self._collect_canonical_snapshot(level)
            payload = await self._hass.async_add_executor_job(
                self._collect_data, level, snapshot
            )
            payload_bytes = json.dumps(payload, ensure_ascii=False, indent=None).encode("utf-8")

            # 2. 加密
            encrypted = await self._hass.async_add_executor_job(
                self._encrypt, payload_bytes, password
            )

            # 3. 上传（如果配置了云端 URL）
            if self._cloud_api_url and self._cloud_token:
                result = await self._upload(encrypted, level)
            else:
                # 无云端配置：保存到本地文件
                result = await self._save_local(encrypted, level)

            size = len(encrypted)
            _res_msg = f"[Backup] 备份完成: {result.get('backup_id')} ({size} bytes)"
            _LOGGER.info(_res_msg)
            if hasattr(self._coord, "_sys_log"):
                self._coord._sys_log("INFO", _res_msg)
            return {
                "success": True,
                "backup_id": result.get("backup_id", ""),
                "size_bytes": size,
                "message": f"备份成功（{size / 1024:.1f} KB）",
            }

        except Exception as exc:
            _err_msg = f"[Backup] 备份失败: {exc}"
            _LOGGER.error(_err_msg)
            if hasattr(self._coord, "_sys_log"):
                self._coord._sys_log("ERROR", _err_msg)
            return {"success": False, "backup_id": "", "size_bytes": 0, "message": f"备份失败: {exc}"}

    async def restore_backup(
        self,
        backup_id: str,
        password: str,
    ) -> dict:
        """
        从云端下载备份并恢复（解密 → 写入本地数据库）。

        Args:
            backup_id: 云端备份 ID
            password: 用户备份密码

        Returns:
            {"success": bool, "message": str, "restored_keys": list[str]}
        """
        _msg = f"[Backup] 开始恢复备份: {backup_id}"
        _LOGGER.info(_msg)
        if hasattr(self._coord, "_sys_log"):
            self._coord._sys_log("INFO", _msg)

        try:
            # 0. 清洗 backup_id，防止路径穿越
            backup_id = self._sanitize_backup_id(backup_id)

            # 1. 下载密文
            encrypted = await self._download(backup_id)
            if not encrypted:
                _err_msg = "[Backup] 恢复失败：未找到备份或下载失败"
                _LOGGER.error(_err_msg)
                if hasattr(self._coord, "_sys_log"):
                    self._coord._sys_log("ERROR", _err_msg)
                return {"success": False, "message": "未找到备份或下载失败", "restored_keys": []}

            # 2. 解密
            payload_bytes = await self._hass.async_add_executor_job(
                self._decrypt, encrypted, password
            )
            if payload_bytes is None:
                _err_msg = "[Backup] 恢复失败：解密失败，密码错误或备份已损坏"
                _LOGGER.error(_err_msg)
                if hasattr(self._coord, "_sys_log"):
                    self._coord._sys_log("ERROR", _err_msg)
                return {"success": False, "message": "解密失败：密码错误或备份已损坏", "restored_keys": []}

            # 3. 恢复数据
            payload = json.loads(payload_bytes.decode("utf-8"))
            restored_keys = await self._hass.async_add_executor_job(
                self._restore_data, payload
            )

            # 成功语义以 DB 确认为前提：_restore_data 返回 None 表示事务回滚/失败，
            # 不得报告恢复成功（否则用户会以为数据已恢复，实际什么都没写入）。
            if restored_keys is None:
                _fail_msg = "[Backup] 恢复失败：恢复事务已回滚，数据库未变更"
                _LOGGER.error(_fail_msg)
                if hasattr(self._coord, "_sys_log"):
                    self._coord._sys_log("ERROR", _fail_msg)
                return {"success": False, "message": "恢复失败：恢复事务已回滚，数据库保持原状", "restored_keys": []}

            refresh_errors = await self._async_refresh_restored_projections(restored_keys)
            if refresh_errors:
                _fail_msg = (
                    "[Backup] Add-on restore committed, but runtime projection refresh failed: "
                    + ", ".join(refresh_errors)
                )
                _LOGGER.error(_fail_msg)
                if hasattr(self._coord, "_sys_log"):
                    self._coord._sys_log("ERROR", _fail_msg)
                return {
                    "success": False,
                    "committed": True,
                    "requires_restart": True,
                    "message": "Restore committed, but runtime refresh failed; restart is required",
                    "restored_keys": restored_keys,
                    "refresh_errors": refresh_errors,
                }
            _res_msg = f"[Backup] 恢复完成，恢复数据类别: {restored_keys}"
            _LOGGER.info(_res_msg)
            if hasattr(self._coord, "_sys_log"):
                self._coord._sys_log("INFO", _res_msg)
            return {
                "success": True,
                "message": f"恢复成功，已恢复 {len(restored_keys)} 个数据类别",
                "restored_keys": restored_keys,
            }

        except Exception as exc:
            _err_msg = f"[Backup] 恢复失败: {exc}"
            _LOGGER.error(_err_msg)
            if hasattr(self._coord, "_sys_log"):
                self._coord._sys_log("ERROR", _err_msg)
            return {"success": False, "message": f"恢复失败: {exc}", "restored_keys": []}

    async def list_backups(self) -> list[dict]:
        """
        列出云端备份列表（仅元数据，不含内容）。

        Returns:
            [{"backup_id": str, "timestamp": str, "level": str, "size_bytes": int}]
        """
        if not (self._cloud_api_url and self._cloud_token):
            # 列出本地备份文件
            return await self._hass.async_add_executor_job(self._list_local)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._cloud_api_url}/api/v1/backup/list",
                    headers={"Authorization": f"Bearer {self._cloud_token}"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception as exc:
            _LOGGER.warning("[Backup] 列表查询失败: %s", exc)
            return []

    # ── 加密核心 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        """
        从用户密码派生 AES-256 密钥（PBKDF2-HMAC-SHA256）。

        Args:
            password: 用户明文密码
            salt: 随机盐（16 bytes）

        Returns:
            32 bytes 密钥
        """
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            _PBKDF2_ITER,
            dklen=_KEY_LEN,
        )

    @staticmethod
    def _encrypt(plaintext: bytes, password: str) -> bytes:
        """
        AES-256-GCM 加密（Python 标准库 + cryptography 包）。

        统一二进制格式（与 _encrypt_pycrypto 完全兼容）：
          MAGIC(7B) | salt(16B) | nonce(12B) | ciphertext | tag(16B，末尾)

        AESGCM.encrypt() 返回的 ciphertext_with_tag 格式正好是 ciphertext+tag，
        因此可以直接写入，无需额外处理。

        Args:
            plaintext: 明文字节
            password: 用户密码

        Returns:
            加密后的二进制数据
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            # 回退：使用 PyCryptodome（格式与上方完全一致）
            return BackupManager._encrypt_pycrypto(plaintext, password)

        salt = os.urandom(_SALT_LEN)
        nonce = os.urandom(_NONCE_LEN)
        key = BackupManager._derive_key(password, salt)

        aesgcm = AESGCM(key)
        # AESGCM.encrypt 返回 ciphertext + tag（tag 在末尾 16 bytes）
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)

        buf = io.BytesIO()
        buf.write(_MAGIC)
        buf.write(salt)
        buf.write(nonce)
        buf.write(ciphertext_with_tag)  # = ciphertext + tag(末尾)
        return buf.getvalue()

    @staticmethod
    def _encrypt_pycrypto(plaintext: bytes, password: str) -> bytes:
        """
        PyCryptodome 回退加密（当 cryptography 包不可用时）。

        输出格式与 _encrypt 完全一致：
          MAGIC(7B) | salt(16B) | nonce(12B) | ciphertext | tag(16B，末尾)
        """
        try:
            from Crypto.Cipher import AES
            from Crypto.Random import get_random_bytes
        except ImportError:
            raise RuntimeError(
                "备份加密需要 'cryptography' 或 'pycryptodome' 包。"
                "请在 HA 中运行：pip install cryptography"
            )
        salt = get_random_bytes(_SALT_LEN)
        nonce = get_random_bytes(_NONCE_LEN)
        key = BackupManager._derive_key(password, salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)

        buf = io.BytesIO()
        buf.write(_MAGIC)
        buf.write(salt)
        buf.write(nonce)
        buf.write(ciphertext)  # ciphertext 在前（与 AESGCM 格式一致）
        buf.write(tag)         # tag(16B) 在末尾
        return buf.getvalue()

    @staticmethod
    def _decrypt(data: bytes, password: str) -> bytes | None:
        """
        AES-256-GCM 解密。

        Args:
            data: 加密二进制数据（含 MAGIC + salt + nonce + ...）
            password: 用户密码

        Returns:
            解密后的明文字节，或 None（密码错误/数据损坏）
        """
        buf = io.BytesIO(data)

        # 验证魔数
        magic = buf.read(len(_MAGIC))
        if magic != _MAGIC:
            _LOGGER.error("[Backup] 无效的备份文件格式（魔数不匹配）")
            return None

        salt = buf.read(_SALT_LEN)
        nonce = buf.read(_NONCE_LEN)
        key = BackupManager._derive_key(password, salt)

        remaining = buf.read()

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, remaining, None)
        except ImportError:
            pass
        except Exception:
            _LOGGER.error("[Backup] 解密失败：密码错误或数据损坏")
            return None

        # PyCryptodome 回退（格式与 AESGCM 一致：ciphertext | tag(末尾16B)）
        try:
            from Crypto.Cipher import AES
            if len(remaining) < 16:
                _LOGGER.error("[Backup] 备份数据长度不足，无法提取认证标签")
                return None
            ciphertext = remaining[:-16]   # tag 在末尾，ciphertext 在前
            tag = remaining[-16:]          # 末尾 16 bytes 为 GCM tag
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag)
        except Exception:
            _LOGGER.error("[Backup] PyCryptodome 解密失败：密码错误或数据损坏")
            return None

    # ── 数据收集与恢复 ────────────────────────────────────────────────────────

    @staticmethod
    def _canonical_rows(value: Any, source: str) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [dict(row) for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            status = int(value.get("__status") or value.get("status_code") or 0)
            if value.get("ok") is False or status >= 400:
                raise RuntimeError(f"canonical_backup_source_failed:{source}")
            rows = value.get("data")
            if isinstance(rows, list):
                return [dict(row) for row in rows if isinstance(row, dict)]
        raise RuntimeError(f"canonical_backup_source_invalid:{source}")

    async def _collect_canonical_snapshot(self, level: str) -> dict[str, Any]:
        if level not in {BACKUP_LEVEL_BASIC, BACKUP_LEVEL_STANDARD, BACKUP_LEVEL_FULL}:
            raise ValueError(f"invalid_backup_level:{level}")
        client = getattr(self._coord, "_addon_client", None)
        if client is None:
            raise RuntimeError("canonical_backup_addon_unavailable")

        required = [
            ("devices", "get_devices"),
            ("rules", "get_memory_profiles"),
            ("habits", "get_memory_habits"),
        ]
        if level in {BACKUP_LEVEL_STANDARD, BACKUP_LEVEL_FULL}:
            required.extend(
                [
                    ("behavior_patterns", "get_behavior_patterns"),
                    ("corrections", "get_corrections"),
                ]
            )

        if level == BACKUP_LEVEL_FULL:
            required.append(("events", "get_backup_events"))

        snapshot: dict[str, Any] = {}
        for key, getter_name in required:
            getter = getattr(client, getter_name, None)
            if not callable(getter):
                raise RuntimeError(f"canonical_backup_getter_unavailable:{getter_name}")
            try:
                value = await getter()
            except Exception as exc:
                raise RuntimeError(f"canonical_backup_source_exception:{key}") from exc
            snapshot[key] = self._canonical_rows(value, key)
        return snapshot

    def _collect_data(self, level: str, snapshot: dict) -> dict:
        """Build a serializable payload from an Add-on canonical snapshot."""
        payload: dict[str, Any] = {
            "version": "1.1",
            "level": level,
            "exported_at": self._ha_backup_now_iso(),
            "integration_version": self._integration_version,
        }

        device_info: dict[str, dict[str, Any]] = {}
        for row in snapshot.get("devices", []):
            if not isinstance(row, dict):
                continue
            entity_id = str(row.get("entity_id") or "").strip()
            if entity_id:
                device_info[entity_id] = dict(row)
        payload["device_info"] = device_info
        payload["rules"] = [
            dict(row) for row in snapshot.get("rules", []) if isinstance(row, dict)
        ]
        payload["habits"] = [
            dict(row) for row in snapshot.get("habits", []) if isinstance(row, dict)
        ]

        if level in {BACKUP_LEVEL_STANDARD, BACKUP_LEVEL_FULL}:
            payload["behavior_patterns"] = [
                dict(row)
                for row in snapshot.get("behavior_patterns", [])
                if isinstance(row, dict)
            ]
            payload["corrections"] = [
                dict(row)
                for row in snapshot.get("corrections", [])
                if isinstance(row, dict)
            ]

        if level == BACKUP_LEVEL_FULL:
            payload["events"] = [
                dict(row) for row in snapshot.get("events", []) if isinstance(row, dict)
            ]

        return payload

    def _restore_data(self, payload: dict) -> list[str] | None:
        """Restore business data through the Add-on single-writer transaction."""
        confirm = getattr(self._coord, "_post_internal_event_confirmed", None)
        if not callable(confirm):
            _LOGGER.error("[Backup] restore failed: Add-on persistence confirmation unavailable")
            return None
        result = confirm("backup_restore", {"backup": dict(payload or {})}, timeout=60.0)
        if (
            not isinstance(result, dict)
            or result.get("ok") is not True
            or result.get("committed") is not True
        ):
            _LOGGER.error(
                "[Backup] restore failed: Add-on did not confirm atomic commit: %s",
                (result or {}).get("error") if isinstance(result, dict) else "invalid_receipt",
            )
            return None
        restored = result.get("restored")
        if not isinstance(restored, list):
            _LOGGER.error("[Backup] restore failed: receipt has no restored list")
            return None
        return [str(item) for item in restored if str(item).strip()]

    async def _async_refresh_restored_projections(self, restored_keys: list[str]) -> list[str]:
        restored = {str(item or "").strip() for item in restored_keys}
        errors: list[str] = []
        if restored.intersection({"device_info", "devices"}):
            refresh_devices = getattr(
                self._coord,
                "_async_refresh_device_info_from_addon_devices",
                None,
            )
            if not callable(refresh_devices):
                errors.append("device_projection_refresh_unavailable")
            else:
                try:
                    await refresh_devices(reason="backup_restore")
                    status = getattr(self._coord, "_last_addon_device_sync_status", {})
                    if not isinstance(status, dict) or status.get("ok") is not True:
                        errors.append("device_projection_refresh_failed")
                except Exception:
                    errors.append("device_projection_refresh_failed")

        if restored.intersection({"rules", "rules_db", "habits"}):
            refresh_memory = getattr(self._coord, "_async_refresh_memory_assets_from_addon", None)
            if not callable(refresh_memory):
                errors.append("memory_projection_refresh_unavailable")
            else:
                try:
                    refreshed = await refresh_memory()
                    status = getattr(self._coord, "_last_addon_memory_sync_status", {})
                    if refreshed is not True or not isinstance(status, dict) or status.get("ok") is not True:
                        errors.append("memory_projection_refresh_failed")
                except Exception:
                    errors.append("memory_projection_refresh_failed")
        return errors

    async def _upload(self, encrypted: bytes, level: str) -> dict:
        """上传加密数据到云端 API。"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._cloud_api_url}/api/v1/backup/upload",
                    data=encrypted,
                    headers={
                        "Authorization": f"Bearer {self._cloud_token}",
                        "Content-Type": "application/octet-stream",
                        "X-Backup-Level": level,
                        "X-Client-Version": "4.6.0",
                    },
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status in (200, 201):
                        return await resp.json()
                    raise RuntimeError(f"HTTP {resp.status}: {await resp.text()}")
        except Exception as exc:
            raise RuntimeError(f"上传失败: {exc}") from exc

    async def _download(self, backup_id: str) -> bytes | None:
        """从云端下载备份密文。"""
        if not (self._cloud_api_url and self._cloud_token):
            # 尝试本地文件
            return await self._hass.async_add_executor_job(self._load_local, backup_id)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._cloud_api_url}/api/v1/backup/{backup_id}",
                    headers={"Authorization": f"Bearer {self._cloud_token}"},
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    return None
        except Exception as exc:
            _LOGGER.warning("[Backup] 下载失败: %s", exc)
            return None

    # ── 本地文件备份（无云端时的回退） ──────────────────────────────────────

    async def _save_local(self, encrypted: bytes, level: str) -> dict:
        """保存到 HA 配置目录下的本地文件。"""
        ts = self._ha_backup_file_timestamp()
        backup_id = f"bkp_{ts}_{level}"

        def _write():
            backup_dir = os.path.join(self._hass.config.config_dir, "smart_agent_backups")
            os.makedirs(backup_dir, exist_ok=True)
            fpath = os.path.join(backup_dir, f"{backup_id}.enc")
            with open(fpath, "wb") as f:
                f.write(encrypted)
            _LOGGER.info("[Backup] 已保存本地备份: %s", fpath)
            return {"backup_id": backup_id, "path": fpath}

        return await self._hass.async_add_executor_job(_write)

    def _load_local(self, backup_id: str) -> bytes | None:
        """从本地文件加载备份密文。"""
        backup_dir = os.path.join(self._hass.config.config_dir, "smart_agent_backups")
        fpath = os.path.join(backup_dir, f"{backup_id}.enc")
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                return f.read()
        return None

    def _list_local(self) -> list[dict]:
        """列出本地备份文件。"""
        backup_dir = os.path.join(self._hass.config.config_dir, "smart_agent_backups")
        if not os.path.isdir(backup_dir):
            return []
        result = []
        for fname in sorted(os.listdir(backup_dir), reverse=True):
            if fname.endswith(".enc"):
                fpath = os.path.join(backup_dir, fname)
                stat = os.stat(fpath)
                backup_id = fname[:-4]
                result.append({
                    "backup_id": backup_id,
                    "timestamp": self._ha_backup_timestamp_iso(stat.st_mtime),
                    "level": backup_id.split("_")[-1] if "_" in backup_id else "unknown",
                    "size_bytes": stat.st_size,
                })
        return result
