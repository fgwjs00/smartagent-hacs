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
from datetime import datetime, timedelta
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
            coord = self._coord
            snapshot = {
                "device_info": dict(getattr(coord, "device_info", {})),
                "rules": list(getattr(coord, "_rules", [])),
                "habits": list(getattr(coord, "_habits", [])),
                "memory_db": getattr(coord, "_memory_db", None),
            }

            # 2. 在 executor 中收集 DB 数据并组装 payload（使用快照，无需访问协调器）
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

    def _collect_data(self, level: str, snapshot: dict) -> dict:
        """
        收集需要备份的数据（同步，在 executor 中运行）。

        使用事先在事件循环中获取的 snapshot 快照，避免在 executor 线程中
        直接访问协调器属性（竞争条件）。

        数据内容根据 level 分级：
          basic:    device_info + rules + habits
          standard: basic + behavior_patterns + corrections
          full:     standard + recent events (30 days)

        永不包含：L5 生物特征、摄像头画面、音频

        Args:
            level: 备份等级
            snapshot: 在事件循环中预先快照的协调器内存数据

        Returns:
            可序列化的字典
        """
        payload: dict[str, Any] = {
            "version": "1.0",
            "level": level,
            "exported_at": datetime.now().isoformat(),
            "integration_version": self._integration_version,
        }

        # L0: 设备配置（来自快照，线程安全）
        payload["device_info"] = snapshot.get("device_info", {})

        # L1: 规则和习惯（来自快照）
        payload["rules"] = [
            {"content": c, "locked": lk}
            for c, lk in snapshot.get("rules", [])
        ]
        payload["habits"] = [
            {"content": c, "locked": lk}
            for c, lk in snapshot.get("habits", [])
        ]

        if level in (BACKUP_LEVEL_STANDARD, BACKUP_LEVEL_FULL):
            # L2: 行为模式 + 修正记录（通过 coordinator._db 读取，WAL 读无锁）
            db = getattr(self._coord, "_db", None)
            if db and db.is_open:
                try:
                    payload["behavior_patterns"] = db.query(
                        "SELECT entity_id, expected_state, hour_start, hour_end, "
                        "weekday_mask, confidence, last_reinforced "
                        "FROM behavior_patterns ORDER BY confidence DESC LIMIT 500"
                    )
                    payload["corrections"] = db.query(
                        "SELECT time, entity_id, ai_service, ai_state, user_state, "
                        "room, hour, correction_count, scene_desc "
                        "FROM corrections ORDER BY correction_count DESC LIMIT 200"
                    )
                    payload["rules_db"] = db.query(
                        "SELECT content, locked, created FROM rules"
                    )
                except Exception as exc:
                    _LOGGER.warning("[Backup] 数据库读取失败: %s", exc)

        if level == BACKUP_LEVEL_FULL:
            # L3: 近 30 天事件日志
            db = getattr(self._coord, "_db", None)
            if db and db.is_open:
                try:
                    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                    payload["events"] = db.query(
                        "SELECT time, type, detail, entity, state FROM events "
                        "WHERE time >= ? ORDER BY id DESC LIMIT 5000",
                        (cutoff,),
                    )
                except Exception as exc:
                    _LOGGER.warning("[Backup] 事件日志读取失败: %s", exc)

        return payload

    def _restore_data(self, payload: dict) -> list[str] | None:
        """
        将解密后的备份数据恢复到本地（同步，在 executor 中运行）。

        恢复优先级：
          1. device_info   → devices 表（核心设备配置）
          2. rules_db / rules → rules 表（rules_db 优先，含 created 字段）
          3. habits        → habits 表
          4. behavior_patterns → behavior_patterns 表
          5. corrections   → corrections 表
          6. events        → events 表（仅 full 备份）

        所有写操作在同一 SQLite EXCLUSIVE 事务内，任何失败触发完整 ROLLBACK。
        事务结束后调用 _load_config() 将 DB 数据同步回 coordinator 内存。

        Args:
            payload: 解密后的字典

        Returns:
            已恢复的数据类别列表
        """
        coord = self._coord
        restored: list[str] = []
        db = getattr(coord, "_db", None)

        if db and db.is_open:
            try:
                conn = db.get_raw_connection()
                # 先获取 DatabaseService 写锁，再执行 EXCLUSIVE 事务，
                # 保证与 execute() / execute_script() 不发生并发冲突。
                # isolation_level=None（自动提交）下可直接使用显式事务控制。
                with db._write_lock:
                    try:
                        conn.execute("BEGIN EXCLUSIVE")
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # ── 1. 设备配置（device_info → devices 表）────────────────
                        if "device_info" in payload and isinstance(payload["device_info"], dict):
                            conn.execute("DELETE FROM devices")
                            for eid, info in payload["device_info"].items():
                                if not isinstance(info, dict):
                                    continue
                                conn.execute(
                                    "INSERT OR REPLACE INTO devices "
                                    "(entity_id, name, area, type, ops, control_mode, sensor_type) "
                                    "VALUES (?,?,?,?,?,?,?)",
                                    (
                                        eid,
                                        _restore_text(info.get("name"), eid, 100),
                                        _restore_text(info.get("room") or info.get("area"), "", 50),
                                        _restore_text(info.get("type"), "", 30),
                                        _restore_text(info.get("ops"), "", 200),
                                        _restore_text(info.get("control_mode"), "shared", 20),
                                        _restore_text(info.get("sensor_type"), "", 30),
                                    ),
                                )
                            restored.append("device_info")
                            _LOGGER.info("[Backup] 恢复设备配置: %d 台", len(payload["device_info"]))

                        # ── 2. 规则（rules_db 含创建时间；rules 为内存快照回退）──
                        rules_source = payload.get("rules_db") or [
                            {"content": r["content"], "locked": r.get("locked", 0), "created": now_str}
                            for r in payload.get("rules", [])
                        ]
                        if rules_source:
                            conn.execute("DELETE FROM rules")
                            for r in rules_source:
                                if not isinstance(r, dict) or not r.get("content"):
                                    continue
                                conn.execute(
                                    "INSERT OR IGNORE INTO rules (content, locked, created) VALUES (?,?,?)",
                                    (r["content"], int(r.get("locked", 0)), r.get("created", now_str)),
                                )
                            restored.append("rules")
                            _LOGGER.info("[Backup] 恢复规则: %d 条", len(rules_source))

                        # ── 3. 习惯（habits → habits 表）────────────────────────
                        if "habits" in payload and isinstance(payload["habits"], list):
                            conn.execute("DELETE FROM habits")
                            for h in payload["habits"]:
                                if not isinstance(h, dict) or not h.get("content"):
                                    continue
                                conn.execute(
                                    "INSERT OR IGNORE INTO habits (content, locked, created) VALUES (?,?,?)",
                                    (h["content"], int(h.get("locked", 0)), now_str),
                                )
                            restored.append("habits")
                            _LOGGER.info("[Backup] 恢复习惯: %d 条", len(payload["habits"]))

                        # ── 4. 行为模式 ──────────────────────────────────────────
                        if "behavior_patterns" in payload and isinstance(payload["behavior_patterns"], list):
                            conn.execute("DELETE FROM behavior_patterns")
                            for r in payload["behavior_patterns"]:
                                if not isinstance(r, dict):
                                    continue
                                conn.execute(
                                    "INSERT OR IGNORE INTO behavior_patterns "
                                    "(entity_id, expected_state, hour_start, hour_end, "
                                    "weekday_mask, confidence, last_reinforced) "
                                    "VALUES (?,?,?,?,?,?,?)",
                                    (
                                        r.get("entity_id"), r.get("expected_state"),
                                        r.get("hour_start"), r.get("hour_end"),
                                        r.get("weekday_mask"), r.get("confidence"),
                                        r.get("last_reinforced"),
                                    ),
                                )
                            restored.append("behavior_patterns")

                        # ── 5. 修正记录 ──────────────────────────────────────────
                        if "corrections" in payload and isinstance(payload["corrections"], list):
                            conn.execute("DELETE FROM corrections")
                            for r in payload["corrections"]:
                                if not isinstance(r, dict):
                                    continue
                                # P0修复：time 为 NOT NULL，备份时已包含；老备份缺失时用 ISO 当前时间补全
                                _time = r.get("time") or datetime.now().isoformat()
                                conn.execute(
                                    "INSERT OR IGNORE INTO corrections "
                                    "(time, entity_id, ai_service, ai_state, user_state, "
                                    "room, hour, correction_count, scene_desc) "
                                    "VALUES (?,?,?,?,?,?,?,?,?)",
                                    (
                                        _time,
                                        r.get("entity_id"), r.get("ai_service"),
                                        r.get("ai_state"), r.get("user_state"),
                                        r.get("room"), r.get("hour"),
                                        r.get("correction_count", 1), r.get("scene_desc"),
                                    ),
                                )
                            restored.append("corrections")

                        # ── 6. 事件日志（full 备份才有）──────────────────────────
                        if "events" in payload and isinstance(payload["events"], list):
                            # 不清空 events 表，只补充备份中有而本地没有的旧事件
                            existing_events: set[tuple[str, str, str, str, str]] = set()
                            for row in conn.execute("SELECT time, type, detail, entity, state FROM events"):
                                if isinstance(row, tuple):
                                    existing_events.add(tuple("" if v is None else str(v) for v in row))
                                else:
                                    existing_events.add(tuple(
                                        "" if row[field] is None else str(row[field])
                                        for field in ("time", "type", "detail", "entity", "state")
                                    ))
                            inserted = 0
                            for r in payload["events"]:
                                if not isinstance(r, dict):
                                    continue
                                event_key = tuple(
                                    "" if r.get(field) is None else str(r.get(field))
                                    for field in ("time", "type", "detail", "entity", "state")
                                )
                                if event_key in existing_events:
                                    continue
                                conn.execute(
                                    "INSERT OR IGNORE INTO events (time, type, detail, entity, state) "
                                    "VALUES (?,?,?,?,?)",
                                    (
                                        r.get("time"), r.get("type"),
                                        r.get("detail"), r.get("entity"), r.get("state"),
                                    ),
                                )
                                existing_events.add(event_key)
                                inserted += 1
                            if inserted:
                                restored.append("events")
                                _LOGGER.info("[Backup] 恢复事件: %d 条", inserted)

                        conn.execute("COMMIT")
                        _LOGGER.info("[Backup] 数据库恢复事务提交成功: %s", restored)

                    except Exception as exc:
                        try:
                            conn.execute("ROLLBACK")
                        except Exception:
                            pass
                        _LOGGER.error("[Backup] 恢复事务失败，已完整回滚，数据库保持一致: %s", exc)
                        # 返回 None 作为失败哨兵，区别于"成功但 0 类别"的空列表，
                        # 避免调用方把回滚（什么都没写入）误报为恢复成功。
                        return None
                # 不关闭连接——DatabaseService 持久化连接由 async_shutdown 管理

            except Exception as exc:
                _LOGGER.error("[Backup] 无法访问 DatabaseService: %s", exc)
                return None

        # 将 DB 中已恢复的数据同步回 coordinator 内存（不在事务内，失败不影响已写入的 DB）
        if restored and hasattr(coord, "_load_config"):
            try:
                coord._load_config()
                _LOGGER.info("[Backup] 已从 DB 重新加载配置到 coordinator 内存")
            except Exception as exc:
                _LOGGER.warning("[Backup] 配置重载失败（数据库已恢复，重启 HA 后生效）: %s", exc)

        return restored

    # ── 网络 API 调用 ─────────────────────────────────────────────────────────

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
        def _write():
            backup_dir = os.path.join(self._hass.config.config_dir, "smart_agent_backups")
            os.makedirs(backup_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"bkp_{ts}_{level}"
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
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "level": backup_id.split("_")[-1] if "_" in backup_id else "unknown",
                    "size_bytes": stat.st_size,
                })
        return result
