"""
DatabaseService — SmartAgent 统一数据库访问服务 (Phase P4)。

设计目标：
  - 单一持久化连接：消除每次操作 sqlite3.connect/close 的开销和锁竞争
  - 写操作串行化：threading.Lock 保证同一时刻只有一个写操作（WAL 模式下读不受影响）
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
import sqlite3
import threading
from typing import Any

_LOGGER = logging.getLogger(__name__)


class DatabaseService:
    """
    SmartAgent 统一 SQLite 数据库服务。

    所有同步方法设计为在 executor 线程中调用（通过 hass.async_add_executor_job）。
    读写操作均通过 _write_lock 串行化，防止 Python sqlite3 单连接对象的多线程 SQLITE_MISUSE 错误。

    Attributes:
        _db_path: SQLite 数据库文件路径
        _conn: 持久化连接（open 后创建，close 时销毁）
        _write_lock: 写操作互斥锁（threading.Lock，保护 INSERT/UPDATE/DELETE）
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._write_lock = threading.Lock()

    @property
    def is_open(self) -> bool:
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
        if self._conn is not None:
            return  # 已打开，幂等
        try:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,   # 允许跨线程使用（配合 _write_lock 保证安全）
                isolation_level=None,       # 自动提交模式：禁用 Python 隐式事务管理
            )
            conn.row_factory = sqlite3.Row  # 全局设置，query() 无需再修改（线程安全）
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA cache_size=-8000")    # 8MB 内存缓存
            conn.execute("PRAGMA synchronous=NORMAL")  # 性能与安全的平衡点
            conn.execute("PRAGMA busy_timeout=5000")   # 锁等待 5s，避免 SQLITE_BUSY
            self._conn = conn
            _LOGGER.info("[DB Service] 持久化连接已打开: %s (WAL + autocommit)", self._db_path)
        except Exception as exc:
            _LOGGER.error("[DB Service] 无法打开数据库: %s", exc)
            raise

    def close(self) -> None:
        """
        安全关闭持久化连接。

        在 Coordinator.async_shutdown → executor 中调用。
        关闭后调用 execute/query 将抛出 RuntimeError。
        """
        if self._conn is None:
            return
        try:
            self._conn.close()
            _LOGGER.info("[DB Service] 持久化连接已关闭")
        except Exception as exc:
            _LOGGER.warning("[DB Service] 关闭连接时出错: %s", exc)
        finally:
            self._conn = None

    def _ensure_open(self) -> sqlite3.Connection:
        """获取持久化连接，未打开时自动尝试重新打开（容错）。"""
        if self._conn is None:
            _LOGGER.warning("[DB Service] 连接未打开，尝试自动重连...")
            self.open()
        return self._conn  # type: ignore[return-value]

    # ── 写操作（加锁） ─────────────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> bool:
        """
        执行单条写 SQL（INSERT/UPDATE/DELETE）。

        使用 _write_lock 串行化，保证多 executor 线程的写操作不会冲突。
        WAL 模式下读操作不受此锁影响，可并行执行。
        isolation_level=None（自动提交）下每条语句独立提交，无需手动 commit。

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            P2修复：True=成功；False=执行失败（已记录 WARNING），调用方可据此决策
        """
        conn = self._ensure_open()
        with self._write_lock:
            try:
                conn.execute(sql, params)
                # isolation_level=None 时已自动提交，无需显式 commit
                return True
            except Exception as exc:
                _LOGGER.warning("[DB Service] Write failed: %s", exc)
                return False

    def execute_many(self, sql: str, params_list: list[tuple]) -> bool:
        """
        批量执行写 SQL（同一条 SQL 对多组参数）。

        整个批次在同一锁内完成，避免中间状态可见。

        Args:
            sql: SQL 语句（含占位符）
            params_list: 参数元组列表

        Returns:
            True=全部成功；False=已回滚（已记录 WARNING）
        """
        if not params_list:
            return True
        conn = self._ensure_open()
        with self._write_lock:
            try:
                # isolation_level=None 下每条 SQL 独立提交，必须显式 BEGIN/COMMIT
                # 确保整个批次作为单一事务，避免 N×fsync 带来的性能惩罚
                conn.execute("BEGIN")
                conn.executemany(sql, params_list)
                conn.execute("COMMIT")
                return True
            except Exception as exc:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                _LOGGER.warning("[DB Service] Batch write failed (rolled back): %s", exc)
                return False

    def execute_script(self, statements: list[tuple[str, tuple]]) -> bool:
        """
        在同一事务内执行多条写 SQL（原子性保证）。

        Args:
            statements: [(sql, params), ...] 列表

        Returns:
            True=全部成功，False=已回滚
        """
        conn = self._ensure_open()
        with self._write_lock:
            try:
                # isolation_level=None（自动提交）下必须显式 BEGIN；
                # 此时连接处于 autocommit 状态，不存在隐式事务冲突
                conn.execute("BEGIN")
                for sql, params in statements:
                    conn.execute(sql, params)
                conn.execute("COMMIT")
                return True
            except Exception as exc:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                _LOGGER.error("[DB Service] Transaction failed (rolled back): %s", exc)
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
        conn = self._ensure_open()
        with self._write_lock:
            try:
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
            except Exception as exc:
                _sql_snippet = sql.strip()[:120].replace("\n", " ")
                _LOGGER.warning("[DB Service] Query failed: %s | SQL: %s | params=%s", exc, _sql_snippet, params)
                return []

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
        conn = self._ensure_open()
        with self._write_lock:
            try:
                row = conn.execute(sql, params).fetchone()
                return row[0] if row else None
            except Exception as exc:
                _LOGGER.warning("[DB Service] Scalar query failed: %s", exc)
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
            _LOGGER.warning("[DB Service] DDL failed: %s | SQL: %s", exc, sql[:60])

    def get_raw_connection(self) -> sqlite3.Connection:
        """
        获取底层连接（仅用于迁移/备份等需要原始连接的场景）。

        调用者需自行保证线程安全。
        """
        return self._ensure_open()
