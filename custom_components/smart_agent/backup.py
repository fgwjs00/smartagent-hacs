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
        await mgr.restore_backup(backup_id="bkp_xxx", password="用户密码", operation_id="restore_unique_id")
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
        except Exception as exc:
            _LOGGER.warning(
                "Backup manifest version unavailable: operation=read_manifest_version "
                "exception_type=%s; using unknown version",
                type(exc).__name__,
            )
            return "unknown"

    def _ha_backup_now(self) -> datetime:
        local_now = getattr(self._coord, "_ha_local_now", None)
        if callable(local_now):
            try:
                value = local_now()
                if isinstance(value, datetime):
                    return value
            except Exception as exc:
                _LOGGER.warning(
                    "Backup clock fallback: operation=backup_now.local_clock exception_type=%s",
                    type(exc).__name__,
                )

        configured_timezone = str(
            getattr(getattr(getattr(self, "_hass", None), "config", None), "time_zone", "") or ""
        ).strip()
        if configured_timezone:
            try:
                from zoneinfo import ZoneInfo

                return datetime.now(ZoneInfo(configured_timezone))
            except Exception as exc:
                _LOGGER.warning(
                    "Backup clock fallback: operation=backup_now.timezone_lookup exception_type=%s",
                    type(exc).__name__,
                )
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
            if tzinfo is None:
                raise ValueError("HA backup timezone unavailable")
            return datetime.fromtimestamp(float(timestamp), timezone.utc).astimezone(tzinfo).isoformat()
        except Exception as exc:
            raise RuntimeError(
                "backup_timestamp_conversion_failed: BackupManager._ha_backup_timestamp_iso"
            ) from exc

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

    def _get_restore_journal(self):
        from .restore_journal import RestoreJournal

        journal = getattr(self, "_restore_journal_store", None)
        if journal is None:
            config_dir = getattr(getattr(self._hass, "config", None), "config_dir", None)
            if not isinstance(config_dir, str) or not os.path.isabs(config_dir):
                raise RuntimeError("restore_journal_path_unavailable")
            journal = RestoreJournal(os.path.join(config_dir, ".storage", "smart_agent_restore.sqlite3"))
            self._restore_journal_store = journal
        return journal

    @staticmethod
    def _restore_unknown(operation_id: str, error: str) -> dict:
        return {"operation_id": operation_id, "outcome": "unknown", "committed": None,
                "ok": False, "restored": [], "error": error, "acknowledged": False}

    @staticmethod
    def _restore_payload_digest(backup_id: str, payload: dict) -> str:
        body = {"scope": "ha_bridge:local_business_data", "backup_id": backup_id, "backup": payload}
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode()).hexdigest()

    def _validate_restore_receipt(self, receipt, operation_id: str, backup_id: str, digest: str = "") -> dict:
        unknown = self._restore_unknown(operation_id, "invalid_restore_receipt")
        if not isinstance(receipt, dict) or receipt.get("contract") != "backup_restore.v1":
            if isinstance(receipt, dict) and receipt.get("error"):
                unknown["error"] = str(receipt["error"])
            return unknown
        if receipt.get("operation_id") != operation_id or receipt.get("scope") != "ha_bridge:local_business_data":
            return unknown
        outcome = receipt.get("outcome")
        if outcome == "unknown":
            return {**unknown, "protocol_supported": True,
                    "error": str(receipt.get("error") or "restore_unconfirmed")}
        if outcome not in {"committed", "rolled_back", "not_committed", "rejected"}:
            return unknown
        if receipt.get("backup_id") != backup_id or receipt.get("committed") is not (outcome == "committed"):
            return unknown
        if (outcome == "rejected" and receipt.get("request_rejected") is True
                and receipt.get("error") == "restore_identity_conflict"
                and (not digest or receipt.get("payload_digest") == digest)):
            return {**receipt, "not_dispatched": True}
        fenced = outcome == "not_committed" and receipt.get("error") == "restore_fenced_before_commit"
        actual_digest = receipt.get("payload_digest")
        if (digest and actual_digest != digest and not (fenced and actual_digest == "")) or (
                not fenced and (not isinstance(actual_digest, str) or len(actual_digest) != 64)):
            return unknown
        if not isinstance(receipt.get("receipt_token"), str) or len(receipt["receipt_token"]) != 48:
            return unknown
        if not receipt.get("completed_at") or not isinstance(receipt.get("restored"), list) or not all(
                isinstance(item, str) for item in receipt["restored"]):
            return unknown
        if outcome == "committed" and receipt.get("ok") is not True:
            return unknown
        return dict(receipt)

    def _restore_request(self, operation_id: str, backup_id: str, *, action: str, **body) -> dict:
        confirm = getattr(self._coord, "_post_internal_event_confirmed", None)
        if not callable(confirm):
            return self._restore_unknown(operation_id, "restore_confirmation_unavailable")
        try:
            receipt = confirm("backup_restore", {"operation_id": operation_id, "backup_id": backup_id,
                                                 "action": action, **body}, timeout=60.0)
        except Exception:
            return self._restore_unknown(operation_id, "restore_confirmation_unavailable")
        digest = self._restore_payload_digest(backup_id, body["backup"]) if action == "restore" else ""
        return self._validate_restore_receipt(receipt, operation_id, backup_id, digest)

    def _read_restore_status(self, operation_id: str | None, reconcile: bool) -> dict:
        journal = self._get_restore_journal()
        handle = journal.read(operation_id or "")
        if handle is None:
            return self._restore_unknown(operation_id or "", "restore_handle_not_found")
        operation_id = handle["operation_id"]
        cached = json.loads(handle["receipt_json"]) if handle["receipt_json"] else None
        if cached and cached.get("not_dispatched"):
            return cached
        receipt = self._restore_request(operation_id, handle["backup_id"], action="reconcile" if reconcile else "status")
        if receipt.get("outcome") != "unknown":
            receipt = self._validate_restore_receipt(receipt, operation_id, handle["backup_id"], handle["payload_digest"])
        if cached:
            return {**cached, "acknowledged": not handle["active"] or receipt.get("acknowledged") is True,
                    "local_gate_released": not bool(handle["active"]),
                    **({"status_query_error": receipt.get("error")} if receipt["outcome"] == "unknown" else {})}
        if receipt["outcome"] != "unknown":
            try:
                return journal.remember(operation_id, receipt)
            except Exception:
                return {**receipt, "handle_cache_error": True}
        return receipt

    async def get_restore_status(self, operation_id: str | None = None, *, reconcile: bool = False) -> dict:
        """Recover the current handle after HA restart; status never replays writes.

        Explicit reconcile fences an absent/pending Add-on operation under its
        writer lock. Ordinary status is read-only on the Add-on business store.
        """
        try:
            receipt = await self._hass.async_add_executor_job(self._read_restore_status, operation_id, reconcile)
        except Exception:
            receipt = self._restore_unknown(operation_id or "", "restore_status_unavailable")
        return await self._restore_reply(receipt)

    def _validate_restore_ack_receipt(self, receipt: dict, handle: dict, known: dict | None = None) -> dict:
        bound = self._validate_restore_receipt(receipt, handle["operation_id"],
                                               handle["backup_id"], handle["payload_digest"])
        if bound["outcome"] == "unknown":
            return bound
        immutable = ("contract", "scope", "operation_id", "backup_id", "payload_digest", "outcome",
                     "committed", "ok", "restored", "completed_at", "receipt_token", "error")
        if known is not None and any(bound.get(key) != known.get(key) for key in immutable):
            return self._restore_unknown(handle["operation_id"], "restore_terminal_mismatch")
        return bound

    @staticmethod
    def _restore_ack_failure(known: dict, handle: dict, error: str, *, sent: bool = False) -> dict:
        return {**known, "acknowledged": False, "local_gate_released": not bool(handle["active"]),
                "acknowledgement_outcome": "unknown" if sent else "not_sent",
                "acknowledgement_error": error}

    def _acknowledge_restore(self, operation_id: str, receipt_token: str) -> dict:
        journal = self._get_restore_journal()
        handle = journal.read(operation_id)
        if handle is None:
            return self._restore_unknown(operation_id, "restore_handle_not_found")
        known = None
        if handle["receipt_json"]:
            known = self._validate_restore_ack_receipt(json.loads(handle["receipt_json"]), handle)
            if known["outcome"] == "unknown":
                return self._restore_ack_failure(known, handle, "invalid_cached_restore_receipt")
        status = self._restore_request(operation_id, handle["backup_id"], action="status")
        basis = self._validate_restore_ack_receipt(status, handle, known)
        if basis["outcome"] == "unknown":
            return self._restore_ack_failure(known or basis, handle, basis["error"])
        if not isinstance(receipt_token, str) or receipt_token != basis.get("receipt_token"):
            return self._restore_ack_failure(known or basis, handle, "restore_acknowledgement_token_mismatch")
        try:
            remembered = journal.remember(operation_id, basis)
        except Exception:
            return self._restore_ack_failure(known or basis, handle, "restore_handle_cache_unavailable")
        basis = self._validate_restore_ack_receipt(basis, handle, remembered)
        if basis["outcome"] == "unknown":
            return self._restore_ack_failure(known or basis, handle, basis["error"])
        receipt = self._restore_request(operation_id, handle["backup_id"], action="acknowledge", receipt_token=receipt_token)
        receipt = self._validate_restore_ack_receipt(receipt, handle, basis)
        if receipt["outcome"] == "unknown" or receipt.get("acknowledged") is not True:
            return self._restore_ack_failure(basis, handle, "restore_acknowledgement_unconfirmed", sent=True)
        try:
            journal.acknowledge(operation_id)
        except Exception:
            return {**receipt, "local_gate_released": False, "handle_acknowledgement_error": True}
        return {**receipt, "local_gate_released": True, "acknowledgement_outcome": "confirmed"}

    async def acknowledge_restore(self, operation_id: str, receipt_token: str) -> dict:
        """Acknowledge only a terminal bound to the local intent and observed result."""
        try:
            receipt = await self._hass.async_add_executor_job(self._acknowledge_restore, operation_id, receipt_token)
        except Exception:
            receipt = self._restore_unknown(operation_id, "restore_acknowledgement_unavailable")
        return await self._restore_reply(receipt)


    async def _restore_reply(self, receipt: dict) -> dict:
        reply = {**receipt, "success": False, "restored_keys": list(receipt.get("restored") or [])}
        outcome = receipt["outcome"]
        if outcome == "committed":
            try:
                errors = await self._async_refresh_restored_projections(reply["restored_keys"])
            except Exception as exc:
                errors = ["projection_refresh_exception:" + type(exc).__name__]
            if errors:
                return {**reply, "committed": True, "requires_restart": True, "refresh_errors": errors,
                        "message": "数据已提交，但运行投影刷新失败；需要重启或重新查询刷新，不要再次恢复"}
            return {**reply, "success": True, "requires_restart": False, "refresh_errors": [],
                    "message": "恢复已提交；确认该结果后再开始新的恢复操作"}
        messages = {"rolled_back": "恢复事务已确认回滚", "not_committed": "已对账确认未提交，迟到请求已被阻止",
                    "rejected": "恢复未开始：请求被拒绝", "unknown": "恢复结果未知；保留原操作 ID 查询或对账，不要换 ID 重试"}
        return {**reply, "message": messages[outcome]}

    async def restore_backup(self, backup_id: str, password: str, *, operation_id: str) -> dict:
        """Start one explicit restore identity; duplicates only query its result."""
        issued = False
        claimed = False
        try:
            operation_id = self._sanitize_backup_id(operation_id)
            backup_id = self._sanitize_backup_id(backup_id)
            journal = self._get_restore_journal()
            admission = await self._hass.async_add_executor_job(journal.claim, operation_id, backup_id)
            if admission["state"] == "existing":
                return await self.get_restore_status(operation_id)
            if admission["state"] != "created":
                return await self._restore_reply({"operation_id": operation_id, "outcome": "rejected", "committed": False,
                    "error": "restore_handle_" + admission["state"], "restored": [],
                    "blocking_operation_id": admission.get("blocking_operation_id", "")})
            claimed = True
            encrypted = await self._download(backup_id)
            if not encrypted:
                raise ValueError("backup_download_unavailable")
            plaintext = await self._hass.async_add_executor_job(self._decrypt, encrypted, password)
            if plaintext is None:
                raise ValueError("backup_decryption_failed")
            payload = json.loads(plaintext.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("invalid_backup_payload")
            digest = self._restore_payload_digest(backup_id, payload)
            await self._hass.async_add_executor_job(journal.bind, operation_id, digest)
            issued = True  # Cancellation/timeout from this point cannot prove non-dispatch.
            receipt = await self._hass.async_add_executor_job(self._restore_data, payload, operation_id, backup_id)
            if receipt["outcome"] != "unknown":
                try:
                    receipt = await self._hass.async_add_executor_job(journal.remember, operation_id, receipt)
                    if receipt.get("not_dispatched"):
                        await self._hass.async_add_executor_job(journal.acknowledge, operation_id)
                except Exception:
                    # Preserve an already confirmed commit even if local caching fails.
                    receipt = {**receipt, "handle_cache_error": True}
            return await self._restore_reply(receipt)
        except Exception as exc:
            if issued:
                return await self._restore_reply(self._restore_unknown(operation_id, "restore_wait_unconfirmed"))
            safe_error = str(exc) if str(exc) in {
                "backup_download_unavailable", "backup_decryption_failed", "invalid_backup_payload",
            } else type(exc).__name__
            receipt = {"operation_id": operation_id, "outcome": "rejected", "committed": False,
                       "restored": [], "not_dispatched": True, "error": safe_error}
            if claimed:
                try:
                    receipt = await self._hass.async_add_executor_job(journal.remember, operation_id, receipt)
                    if receipt.get("not_dispatched"):
                        await self._hass.async_add_executor_job(journal.acknowledge, operation_id)
                except Exception:
                    return await self._restore_reply(self._restore_unknown(operation_id, "restore_handle_update_failed"))
            return await self._restore_reply(receipt)

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
                    if resp.status != 200:
                        raise RuntimeError(f"BackupManager.list_backups: upstream_status={resp.status}")
                    rows = await resp.json()
                    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                        raise ValueError("BackupManager.list_backups: invalid_backup_inventory")
                    return rows
        except Exception as exc:
            raise RuntimeError(
                f"BackupManager.list_backups: cloud_inventory_failed exception_type={type(exc).__name__}"
            ) from exc

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

    def _restore_data(self, payload: dict, operation_id: str, backup_id: str) -> dict:
        """Return a bound result protocol, never None/implicit rollback."""
        status = self._restore_request(operation_id, backup_id, action="status")
        if status["outcome"] != "unknown":
            return self._validate_restore_receipt(status, operation_id, backup_id,
                                                  self._restore_payload_digest(backup_id, payload))
        # Strict protocol gate: an old/mixed Add-on must never receive a restore
        # body before proving that it supports operation identity and receipts.
        if not status.get("protocol_supported") or status.get("error") != "restore_not_found":
            return status
        return self._restore_request(operation_id, backup_id, action="restore", backup=dict(payload))

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
            from .ha_storage_capacity import atomic_write_bytes
            fpath = os.path.join(backup_dir, f"{backup_id}.enc")
            atomic_write_bytes(fpath, encrypted)
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
        try:
            filenames = os.listdir(backup_dir)
        except FileNotFoundError:
            return []
        result = []
        for fname in sorted(filenames, reverse=True):
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
