"""
DatabaseService — SmartAgent 统一数据库访问服务 (Phase P4)。

设计目标：
  - 单一持久化连接：消除每次操作 sqlite3.connect/close 的开销和锁竞争
  - 写操作串行化：threading.RLock 保证同一时刻只有一个连接操作
  - 生命周期管理：随 Coordinator 创建/销毁，shutdown 时安全关闭连接
  - 向后兼容：提供与原 _db_exec/_query_events 签名一致的方法，迁移成本最小

使用方式::

    db = DatabaseService("/config/smart_agent.db")
    db.open()                           # Coordinator.__init__ 中调用
    db.execute("INSERT ...", (val,))    # 同步写（自动加锁）
    rows = db.query("SELECT ...")       # 同步读（加 _write_lock，与写操作串行）
    db.close()                          # async_shutdown 中调用
"""
from __future__ import annotations

import logging
import hashlib
import uuid
import re
import sqlite3
import threading
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _sql_snippet(sql: str) -> str:
    return str(sql or "").strip()[:120].replace("\n", " ")


def _sql_target(sql: str) -> str:
    text = str(sql or "").strip()
    patterns = (
        r"(?is)^\s*insert\s+(?:or\s+\w+\s+)?into\s+([`\"\[]?[\w.]+[`\"\]]?)",
        r"(?is)^\s*update\s+([`\"\[]?[\w.]+[`\"\]]?)",
        r"(?is)^\s*delete\s+from\s+([`\"\[]?[\w.]+[`\"\]]?)",
        r"(?is)^\s*replace\s+into\s+([`\"\[]?[\w.]+[`\"\]]?)",
        r"(?is)^\s*select\b.+?\bfrom\s+([`\"\[]?[\w.]+[`\"\]]?)",
        r"(?is)^\s*create\s+(?:unique\s+)?index\s+\S+\s+on\s+([`\"\[]?[\w.]+[`\"\]]?)",
    )
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            return match.group(1).strip("`\"[]")
    return ""


class DatabaseReadError(RuntimeError):
    """Strict-read diagnostics identify the failure without exposing SQL or values."""

    def __init__(self, sql: str, params_count: int, cause: BaseException) -> None:
        self.error_id = uuid.uuid4().hex
        self.sql_fingerprint = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]
        self.params_count = params_count
        super().__init__(
            f"ha_database_read_failed: operation=DatabaseService.query_required "
            f"error_id={self.error_id} sql_fingerprint={self.sql_fingerprint} "
            f"params_count={params_count} cause_type={type(cause).__name__}"
        )


class DatabaseTransactionError(RuntimeError):
    """Keep original causes for callers, but only safe context in diagnostics."""

    def __init__(self, cause: BaseException, rollback_error: BaseException | None,
                 details: dict[str, Any]) -> None:
        self.operation_error = cause
        self.rollback_error = rollback_error
        self.close_error: BaseException | None = None
        self.details = dict(details)
        super().__init__("ha_database_transaction_failed " + " | ".join(
            f"{key}={value}" for key, value in self.details.items()))


class DatabaseOpenError(RuntimeError):
    """Retain cleanup causes while exposing only safe initialization diagnostics."""

    def __init__(self, phase: str, cause: BaseException, close_error: BaseException | None,
                 quarantined: bool) -> None:
        self.error_id = uuid.uuid4().hex
        self.close_error = close_error
        super().__init__(
            f"ha_database_open_failed: operation=DatabaseService.open phase={phase} "
            f"error_id={self.error_id} cause_type={type(cause).__name__} "
            f"close_error_type={type(close_error).__name__ if close_error else ''} "
            f"connection_quarantined={quarantined}"
        )


class DatabaseService:
    """
    SmartAgent 统一 SQLite 数据库服务。

    所有同步方法设计为在 executor 线程中调用（通过 hass.async_add_executor_job）。
    读写操作均通过 _write_lock 串行化，防止 Python sqlite3 单连接对象的多线程 SQLITE_MISUSE 错误。

    Attributes:
        _db_path: SQLite 数据库文件路径
        _conn: 持久化连接（open 后创建，close 时销毁）
        _write_lock: 连接操作互斥锁（threading.RLock，保护持久连接和读写）
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._write_lock = threading.RLock()
        self._quarantined_conn: sqlite3.Connection | None = None
        self._quarantine_error: BaseException | None = None
        self._last_transaction_error: dict[str, Any] | None = None

    @property
    def is_open(self) -> bool:
        with self._write_lock:
            return self._conn is not None

    def open(self) -> None:
        """
        创建持久化数据库连接并配置 WAL 模式。

        必须在 Coordinator 初始化阶段调用（主线程或 executor 中均可），
        后续所有 execute/query 操作复用此连接。

        Notes:
            isolation_level=None 启用自动提交模式，事务完全由调用方通过
            显式 BEGIN/COMMIT/ROLLBACK 控制，避免 Python 隐式事务与
            execute_script() 中手动 BEGIN 产生"cannot start a transaction
            within a transaction"冲突。
            row_factory 全局设为 sqlite3.Row，消除 query() 中并发修改
            row_factory 导致的线程安全问题。
        """
        with self._write_lock:
            if self._quarantined_conn is not None:
                raise RuntimeError("DatabaseService.open: connection_quarantined; explicit close required") from self._quarantine_error
            if self._conn is not None:
                return  # 已打开，幂等
            conn = None
            phase = "connect"
            try:
                conn = sqlite3.connect(
                    self._db_path,
                    check_same_thread=False,   # 允许跨线程使用（配合 _write_lock 保证安全）
                    isolation_level=None,       # 自动提交模式：禁用 Python 隐式事务管理
                )
                phase = "row_factory"
                conn.row_factory = sqlite3.Row  # 全局设置，query() 无需再修改（线程安全）
                for phase, value in (("journal_mode", "WAL"), ("cache_size", "-8000"),
                                     ("synchronous", "NORMAL"), ("busy_timeout", "5000")):
                    conn.execute(f"PRAGMA {phase}={value}")
                self._conn = conn
            except BaseException as exc:
                self._handle_open_failure(conn, phase, exc)
            _LOGGER.info("[DB Service] 持久化连接已打开 (WAL + autocommit)")

    def _handle_open_failure(self, conn: sqlite3.Connection | None, phase: str,
                             cause: BaseException) -> None:
        close_error = None
        if conn is not None:
            self._conn = None
            self._quarantined_conn = conn
            self._quarantine_error = cause
            try:
                self.close()
            except BaseException as exc:
                close_error = exc
        error = DatabaseOpenError(phase, cause, close_error, self._quarantined_conn is not None)
        _LOGGER.error("[DB Service] %s", error)
        for interruption in (cause, close_error):
            if interruption is not None and not isinstance(interruption, Exception):
                raise interruption
        raise error from cause

    def close(self) -> None:
        """
        安全关闭持久化连接。

        在 Coordinator.async_shutdown → executor 中调用。
        关闭后调用 execute/query 将抛出 RuntimeError。
        """
        with self._write_lock:
            conn = self._quarantined_conn if self._quarantined_conn is not None else self._conn
            if conn is None:
                return
            try:
                conn.close()
            except BaseException as exc:
                self._conn = None
                self._quarantined_conn = conn
                if self._quarantine_error is None:
                    self._quarantine_error = exc
                if not isinstance(exc, Exception):
                    raise
                raise RuntimeError(
                    f"DatabaseService.close: connection_quarantined exception_type={type(exc).__name__}"
                ) from exc
            self._conn = None
            self._quarantined_conn = None
            self._quarantine_error = None
            _LOGGER.info("[DB Service] 持久化连接已关闭")

    def _ensure_open(self) -> sqlite3.Connection:
        """获取持久化连接，未打开时自动尝试重新打开（容错）。"""
        with self._write_lock:
            if self._conn is None:
                _LOGGER.warning("[DB Service] 连接未打开，尝试自动重连...")
                self.open()
            return self._conn  # type: ignore[return-value]

    # ── 写操作（加锁） ─────────────────────────────────────────────────────────

    def last_transaction_error(self) -> dict[str, Any] | None:
        """Safe diagnostics until the next nonempty transaction begins."""
        with self._write_lock:
            return dict(self._last_transaction_error) if self._last_transaction_error else None

    def _discard_transaction_connection(self, conn: sqlite3.Connection,
                                        error: DatabaseTransactionError) -> None:
        self._conn = None
        try:
            conn.close()
        except BaseException as exc:
            error.close_error = exc
            error.details["close_error_type"] = type(exc).__name__
            self._quarantined_conn = conn
            self._quarantine_error = error

    def _handle_transaction_failure(self, conn: sqlite3.Connection, cause: BaseException,
                                    details: dict[str, Any], preexisting: bool) -> None:
        rollback_error = None
        state = "not_started"
        try:
            if not preexisting and (details["phase"] != "begin" or conn.in_transaction):
                conn.execute("ROLLBACK")
                if conn.in_transaction:
                    raise RuntimeError("rollback_did_not_end_transaction")
                state = "rolled_back"
        except BaseException as exc:
            rollback_error = exc
            state = "unknown"
        details.update(transaction_state=state, error_id=uuid.uuid4().hex,
                       operation_error_type=type(cause).__name__,
                       rollback_error_type=type(rollback_error).__name__ if rollback_error else "")
        error = DatabaseTransactionError(cause, rollback_error, details)
        if state == "unknown":
            self._discard_transaction_connection(conn, error)
        self._last_transaction_error = dict(error.details)
        marker = "Batch write failed" if details["operation"].endswith("execute_many") else "Transaction failed"
        # A separate safe exception preserves the location without rendering raw causes.
        diagnostic = RuntimeError(str(error))
        _LOGGER.error("[DB Service] %s | %s | close_error_type=%s", marker, error,
                      type(error.close_error).__name__ if error.close_error else "",
                      exc_info=(RuntimeError, diagnostic, cause.__traceback__))
        for interruption in (cause, rollback_error, error.close_error):
            if interruption is not None and not isinstance(interruption, Exception):
                raise interruption
        if state == "unknown":
            raise error from cause

    def execute(self, sql: str, params: tuple = ()) -> bool:
        """
        执行单条写 SQL（INSERT/UPDATE/DELETE）。

        使用 _write_lock 串行化，保证多 executor 线程的写操作不会冲突。
        同一连接的读写均持此锁，WAL 的并行读取只适用于独立连接。
        isolation_level=None（自动提交）下每条语句独立提交，无需手动 commit。

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            P2修复：True=成功；False=执行失败（已记录 WARNING），调用方可据此决策
        """
        with self._write_lock:
            conn = self._ensure_open()
            try:
                conn.execute(sql, params)
                # isolation_level=None 时已自动提交，无需显式 commit
                return True
            except Exception as exc:
                _LOGGER.warning(
                    "[DB Service] Write failed: %s | table=%s | SQL: %s | params=%s",
                    exc,
                    _sql_target(sql) or "-",
                    _sql_snippet(sql),
                    params,
                    exc_info=True,
                )
                return False

    def execute_many(self, sql: str, params_list: list[tuple]) -> bool:
        """
        批量执行写 SQL（同一条 SQL 对多组参数）。

        整个批次在同一锁内完成，避免中间状态可见。

        Args:
            sql: SQL 语句（含占位符）
            params_list: 参数元组列表

        Returns:
            True=全部成功；False=事务未开始或已确认回滚；状态不明抛出异常。
        """
        if not params_list:
            return True
        with self._write_lock:
            conn = self._ensure_open()
            preexisting = conn.in_transaction
            details = {"operation": "DatabaseService.execute_many", "phase": "begin",
                       "sql_fingerprint": hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16],
                       "params_count": len(params_list[0]), "batch_size": len(params_list)}
            self._last_transaction_error = None
            try:
                # isolation_level=None 下每条 SQL 独立提交，必须显式 BEGIN/COMMIT
                # 确保整个批次作为单一事务，避免 N×fsync 带来的性能惩罚
                conn.execute("BEGIN")
                details["phase"] = "write"
                conn.executemany(sql, params_list)
                details["phase"] = "commit"
                conn.execute("COMMIT")
                if conn.in_transaction:
                    raise RuntimeError("commit_did_not_end_transaction")
                return True
            except BaseException as exc:
                self._handle_transaction_failure(conn, exc, details, preexisting)
                if not isinstance(exc, Exception):
                    raise
                return False

    def execute_script(self, statements: list[tuple[str, tuple]]) -> bool:
        """
        在同一事务内执行多条写 SQL（原子性保证）。

        Args:
            statements: [(sql, params), ...] 列表

        Returns:
            True=全部成功；False=事务未开始或已确认回滚；状态不明抛出异常。
        """
        with self._write_lock:
            conn = self._ensure_open()
            preexisting = conn.in_transaction
            details = {"operation": "DatabaseService.execute_script", "phase": "begin",
                       "statement_index": -1, "sql_fingerprint": "", "params_count": 0}
            self._last_transaction_error = None
            try:
                # isolation_level=None（自动提交）下必须显式 BEGIN；
                # 此时连接处于 autocommit 状态，不存在隐式事务冲突
                conn.execute("BEGIN")
                details["phase"] = "write"
                for current_index, (sql, params) in enumerate(statements):
                    details.update(statement_index=current_index, params_count=len(params),
                                   sql_fingerprint=hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16])
                    conn.execute(sql, params)
                details["phase"] = "commit"
                conn.execute("COMMIT")
                if conn.in_transaction:
                    raise RuntimeError("commit_did_not_end_transaction")
                return True
            except BaseException as exc:
                self._handle_transaction_failure(conn, exc, details, preexisting)
                if not isinstance(exc, Exception):
                    raise
                return False

    # ── 读操作（持 _write_lock，与写操作全局串行） ────────────────────────────

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        执行查询 SQL 并返回 dict 列表。

        使用 _write_lock 序列化所有连接操作，防止多个 executor 线程并发调用
        conn.execute() 导致底层 C 库 SQLITE_MISUSE 错误。
        注意：WAL 并发安全仅对独立连接（多进程）成立；单一 Python sqlite3.Connection
        对象本身不是线程安全的，check_same_thread=False 只绕过 Python 层检查。

        Args:
            sql: SELECT 语句
            params: 参数元组

        Returns:
            查询结果列表，每行为一个 dict
        """
        with self._write_lock:
            conn = self._ensure_open()
            try:
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
            except Exception as exc:
                _LOGGER.warning(
                    "[DB Service] Query failed: %s | table=%s | SQL: %s | params=%s",
                    exc,
                    _sql_target(sql) or "-",
                    _sql_snippet(sql),
                    params,
                    exc_info=True,
                )
                return []

    def query_required(self, sql: str, params: tuple = ()) -> list[dict]:
        """Opt-in strict read; retain the existing lock and legacy query/write contracts."""
        with self._write_lock:
            try:
                conn = self._ensure_open()
                return [dict(row) for row in conn.execute(sql, params).fetchall()]
            except Exception as exc:
                error = DatabaseReadError(sql, len(params), exc)
                _LOGGER.warning("[DB Service] Strict read failed: %s", error)
                raise error from exc

    def query_scalar(self, sql: str, params: tuple = ()) -> Any:
        """
        执行查询并返回第一行第一列的标量值。

        与 query() 一样使用 _write_lock 防 SQLITE_MISUSE（见 query() 注释）。

        Args:
            sql: SELECT 语句（应返回单值）
            params: 参数元组

        Returns:
            标量值，或 None（无结果/出错时）
        """
        with self._write_lock:
            conn = self._ensure_open()
            try:
                row = conn.execute(sql, params).fetchone()
                return row[0] if row else None
            except Exception as exc:
                _LOGGER.warning(
                    "[DB Service] Scalar query failed: %s | table=%s | SQL: %s | params=%s",
                    exc,
                    _sql_target(sql) or "-",
                    _sql_snippet(sql),
                    params,
                    exc_info=True,
                )
                return None

    # ── DDL / 迁移（初始化阶段使用） ──────────────────────────────────────────

    def execute_ddl(self, sql: str) -> None:
        """
        执行 DDL 语句（CREATE TABLE/INDEX 等），不使用写锁（初始化阶段单线程）。

        Args:
            sql: DDL 语句
        """
        conn = self._ensure_open()
        try:
            # isolation_level=None（自动提交）下 DDL 自动提交，无需显式 commit
            conn.execute(sql)
        except Exception as exc:
            _LOGGER.warning(
                "[DB Service] DDL failed: %s | table=%s | SQL: %s",
                exc,
                _sql_target(sql) or "-",
                _sql_snippet(sql),
                exc_info=True,
            )

    def get_raw_connection(self) -> sqlite3.Connection:
        """
        获取底层连接（仅用于迁移/备份等需要原始连接的场景）。

        调用者需自行保证线程安全。
        """
        return self._ensure_open()
