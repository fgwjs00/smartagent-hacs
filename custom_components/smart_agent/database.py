"""
DatabaseMixin — SQLite 数据层。
负责建表/迁移、CRUD、事件记录、动作质量统计、内存清理。
所有阻塞 I/O 方法均设计为在 executor 中运行。

v4.8.27: 底层 I/O 已迁移到 DatabaseService（持久化单连接 + 写锁），
本 Mixin 不再直接调用 sqlite3.connect，统一通过 self._db 访问。
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .db_service import DatabaseService

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

_VALID_MIGRATION_TABLES = {
    "events", "devices", "habits", "rules", "behavior_patterns",
    "action_results", "ai_scenes", "action_transactions", "corrections",
    "showroom_light_preferences", "device_baseline", "device_baseline_hourly",
    "training_data", "reflexion_patterns", "arrival_baseline", "decision_cache",
    "frigate_cameras", "frigate_zones", "correction_lessons", "room_topology",
}


def _safe_add_column(conn, table: str, column_def: str) -> None:
    """安全添加列：仅忽略'列已存在'错误，其他错误上抛。"""
    table_name = (table or "").strip()
    col_def = (column_def or "").strip()

    if table_name not in _VALID_MIGRATION_TABLES:
        raise ValueError(f"非法迁移表名: {table_name}")
    if not col_def:
        raise ValueError("非法列定义: 不能为空")
    upper_col_def = col_def.upper()
    if ";" in col_def or "--" in col_def or "/*" in col_def or "DROP TABLE" in upper_col_def:
        raise ValueError(f"非法列定义: {col_def}")

    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_def}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            pass  # 列已存在，正常
        else:
            _LOGGER.error("[DB] 迁移失败 ALTER TABLE %s ADD COLUMN %s: %s", table_name, col_def, e)
            raise

# ── Phase 3 Lite：修正戒律蒸馏用常量（模块级，避免每次维护时重建）──────────────
_LESSON_SVC_LABEL: dict[str, str] = {
    "turn_on":        "开",   "turn_off":        "关",
    "light.turn_on":  "开",   "light.turn_off":  "关",
    "switch.turn_on": "开",   "switch.turn_off": "关",
}
_LESSON_STATE_LABEL: dict[str, str] = {
    "on": "保持开", "off": "保持关",
    "open": "保持开", "closed": "保持关",
}
_LESSON_PRESENCE_LABEL: dict[str, str] = {
    "occupied": "有人时", "empty": "无人时", "any": "",
}


class DatabaseMixin:
    """Mixin: SQLite 数据层，负责所有持久化读写。"""

    # ── 合法的设备管辖域值（此处定义，供 ActionsMixin / DevicesMixin 共用）──
    _VALID_CONTROL_MODES = frozenset({"ai", "ha", "shared"})

    def _init_memory_db(self) -> None:
        """Create SQLite tables and run migrations.

        v4.8.27: 使用 DatabaseService 管理持久化连接（WAL + 写锁），
        后续所有 DB 操作通过 self._db 访问，不再直接 sqlite3.connect。
        """
        try:
            # 初始化 DatabaseService 并打开持久化连接（WAL + 8MB cache + busy_timeout）
            self._db = DatabaseService(self._memory_db)
            self._db.open()
            conn = self._db.get_raw_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT NOT NULL, type TEXT NOT NULL, detail TEXT,
                    entity TEXT, state TEXT, source TEXT DEFAULT 'system',
                    area TEXT, confidence INTEGER)
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity)")
            _safe_add_column(conn, "events", "transaction_id INTEGER DEFAULT 0")
            _safe_add_column(conn, "events", "action_seq INTEGER DEFAULT 0")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    entity_id TEXT PRIMARY KEY, name TEXT NOT NULL,
                    area TEXT DEFAULT '', type TEXT DEFAULT '', ops TEXT DEFAULT '',
                    control_mode TEXT DEFAULT 'shared',
                    sensor_type TEXT DEFAULT '',
                    created TEXT, updated TEXT)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
                    locked INTEGER DEFAULT 0, created TEXT)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
                    locked INTEGER DEFAULT 0, created TEXT)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS behavior_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    expected_state TEXT NOT NULL,
                    hour_start INTEGER NOT NULL,
                    hour_end INTEGER NOT NULL,
                    weekday_mask TEXT DEFAULT '0123456',
                    confidence INTEGER DEFAULT 50,
                    hit_count INTEGER DEFAULT 0,
                    last_updated TEXT,
                    UNIQUE(entity_id, hour_start, weekday_mask))
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_behavior_patterns_hour ON behavior_patterns(hour_start, hour_end)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_behavior_patterns_entity ON behavior_patterns(entity_id)")
            for tbl in ("habits", "rules"):
                _safe_add_column(conn, tbl, "locked INTEGER DEFAULT 0")
            # migration: 旧版 devices 表补充 control_mode / sensor_type 列
            _safe_add_column(conn, "devices", "control_mode TEXT DEFAULT 'shared'")
            _safe_add_column(conn, "devices", "sensor_type TEXT DEFAULT ''")
            # ── action_results: AI 动作执行结果追踪 ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    service TEXT NOT NULL,
                    expected_state TEXT,
                    actual_state TEXT,
                    verified INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    latency_ms INTEGER DEFAULT 0,
                    reason TEXT DEFAULT '')
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_time ON action_results(time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_entity ON action_results(entity_id)")
            _safe_add_column(conn, "action_results", "transaction_id INTEGER DEFAULT 0")
            _safe_add_column(conn, "action_results", "action_seq INTEGER DEFAULT 0")
            # ── ai_scenes: Phase 4 习惯驱动自动生成场景 ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    entities_json TEXT NOT NULL,
                    trigger_context TEXT DEFAULT '',
                    hour_start INTEGER DEFAULT 0,
                    hour_end INTEGER DEFAULT 23,
                    weekday_mask TEXT DEFAULT '0123456',
                    confidence INTEGER DEFAULT 80,
                    hit_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    source TEXT DEFAULT 'auto',
                    created TEXT,
                    updated TEXT)
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_scenes_status ON ai_scenes(status)")
            # 5C-2: 新增 ha_entity_id 列存储已注册的 HA 场景 entity_id（静默跳过已存在）
            _safe_add_column(conn, "ai_scenes", "ha_entity_id TEXT DEFAULT ''")
            _safe_add_column(conn, "ai_scenes", "actions_json TEXT DEFAULT '[]'")
            # ── action_transactions: Layer 2 事务管理 ──────────────────────────
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT,
                    trigger_summary TEXT DEFAULT '',
                    scene_desc TEXT DEFAULT '',
                    confidence INTEGER DEFAULT 0,
                    action_count INTEGER DEFAULT 0,
                    dispatched_count INTEGER DEFAULT 0,
                    blocked_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    pre_states_json TEXT DEFAULT '{}',
                    actions_json TEXT DEFAULT '[]',
                    results_json TEXT DEFAULT '[]')
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_txn_time ON action_transactions(time)"
            )
            # migration: behavior_patterns 补充 last_reinforced 列（Phase 7C 衰减追踪）
            _safe_add_column(conn, "behavior_patterns", "last_reinforced TEXT DEFAULT ''")
            # ── corrections: Phase 7B 用户修正永久学习 ──────────────────────────
            conn.execute("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    ai_service TEXT DEFAULT '',
                    ai_state TEXT DEFAULT '',
                    user_state TEXT DEFAULT '',
                    room TEXT DEFAULT '',
                    hour INTEGER DEFAULT 0,
                    weekday INTEGER DEFAULT 0,
                    scene_desc TEXT DEFAULT '',
                    trigger_text TEXT DEFAULT '',
                    correction_count INTEGER DEFAULT 1)
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_corrections_entity ON corrections(entity_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_corrections_time ON corrections(time)")
            # migration: corrections 补充 decay_score 列（Phase 7C 缓存衰减分数）
            _safe_add_column(conn, "corrections", "decay_score REAL DEFAULT 1.0")
            # migration: corrections 补充 presence_context 列（Phase 11.1 在场维度）
            # 'occupied'=有人时修正, 'empty'=无人时修正, 'any'=兼容旧数据（不区分）
            _safe_add_column(conn, "corrections", "presence_context TEXT DEFAULT 'any'")
            # migration: corrections 补充 synced_at 列（v4.8.78 数据回传）
            _safe_add_column(conn, "corrections", "synced_at TEXT")

            # ── showroom_light_preferences: 展厅灯光层级学习 ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS showroom_light_preferences (
                    entity_id TEXT PRIMARY KEY,
                    on_count INTEGER DEFAULT 0,
                    off_count INTEGER DEFAULT 0,
                    tier TEXT DEFAULT 'core',
                    last_updated TEXT)
            """)

            # ── device_baseline: 设备使用基线 v1（全天汇总，向后兼容）──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS device_baseline (
                    entity_id       TEXT PRIMARY KEY,
                    room            TEXT DEFAULT '',
                    on_samples      INTEGER DEFAULT 0,
                    total_samples   INTEGER DEFAULT 0,
                    on_ratio        REAL DEFAULT 0.0,
                    avg_brightness  INTEGER DEFAULT 0,
                    correction_down INTEGER DEFAULT 0,
                    correction_up   INTEGER DEFAULT 0,
                    last_updated    TEXT)
            """)
            # 兼容旧版：尝试添加列
            for _col, _def in [
                ("correction_up",  "INTEGER DEFAULT 0"),
                ("avg_brightness", "INTEGER DEFAULT 0"),
            ]:
                _safe_add_column(conn, "device_baseline", f"{_col} {_def}")

            # ── device_baseline_hourly: 设备使用基线 v2（按小时分段，精细时段偏好）──
            # 每行代表 (entity_id, hour_bucket) 组合的累积统计，支持时段±1h 查询。
            # memory_store._build_baseline_hint_sync 优先使用本表；
            # 无数据时降级到 device_baseline（v1 全天汇总）。
            conn.execute("""
                CREATE TABLE IF NOT EXISTS device_baseline_hourly (
                    entity_id       TEXT    NOT NULL,
                    hour_bucket     INTEGER NOT NULL,
                    room            TEXT    DEFAULT '',
                    usage_ratio     REAL    DEFAULT 0.0,
                    sample_count    INTEGER DEFAULT 0,
                    last_updated    TEXT,
                    PRIMARY KEY (entity_id, hour_bucket))
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dbl_hourly_room_hour "
                "ON device_baseline_hourly(room, hour_bucket)"
            )

            # ── training_data: 模型训练自标注数据管道 ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT NOT NULL,
                    trigger_text TEXT,
                    context_json TEXT,
                    decision_json TEXT,
                    feature_json TEXT,  -- FeatureEncoder 输出的数值特征快照（用于本地 ML 训练）
                    label INTEGER DEFAULT 1, -- 1:正样本, 0:负样本(用户修正)
                    is_verified INTEGER DEFAULT 0, -- 是否经过30分钟回查验证
                    verified_at TEXT)
            """)
            # migration: training_data 补充 feature_json 列（v4.8.69）
            _safe_add_column(conn, "training_data", "feature_json TEXT")
            # migration: training_data 补充 synced_at 列（v4.8.78 数据回传）
            _safe_add_column(conn, "training_data", "synced_at TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_td_time ON training_data(time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_td_verified ON training_data(is_verified)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_td_synced ON training_data(synced_at)")

            # ── reflexion_patterns: Phase 9.4 Reflexion 失败模式反面教材 ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reflexion_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT,
                    ai_service TEXT,
                    hour INTEGER,
                    correction_count INTEGER,
                    failure_summary TEXT,
                    updated TEXT
                )
            """)

            # ── arrival_baseline: Phase 0 — 到达场景灯光基线（语义修正版）──────────────
            # 语义：P(灯在到达后5分钟时处于 on 状态 | 时段 bucket)
            # 相比 device_baseline.on_ratio（全天平均），本表专门描述「刚进门该开什么灯」。
            conn.execute("""
                CREATE TABLE IF NOT EXISTS arrival_baseline (
                    entity_id   TEXT NOT NULL,
                    room        TEXT NOT NULL DEFAULT '',
                    hour_bucket INTEGER NOT NULL DEFAULT 0,
                    on_samples  INTEGER DEFAULT 0,
                    total_samples INTEGER DEFAULT 0,
                    turn_on_ratio REAL DEFAULT 0.0,
                    last_updated TEXT,
                    PRIMARY KEY (entity_id, hour_bucket)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_arrival_bl_room "
                "ON arrival_baseline(room, hour_bucket)"
            )

            # ── decision_cache: Phase 1 — AI 决策缓存（快路径去规则化）──────────────
            # 语义：LLM 历史上在「房间+时段+星期+触发类型」下做出的决策，
            # 供快路径直接复用，彻底告别 if/else 规则。
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_cache (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_room TEXT NOT NULL,
                    hour_bucket  INTEGER NOT NULL,
                    weekday      INTEGER NOT NULL,
                    trigger_type TEXT NOT NULL DEFAULT 'arrival',
                    actions_json TEXT NOT NULL,
                    confidence   INTEGER DEFAULT 80,
                    scene        TEXT DEFAULT '',
                    hit_count    INTEGER DEFAULT 0,
                    created      TEXT,
                    last_hit     TEXT,
                    UNIQUE(trigger_room, hour_bucket, weekday, trigger_type)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dcache_room "
                "ON decision_cache(trigger_room, hour_bucket, weekday, trigger_type)"
            )
            # 5B-3: 新增 intent / scene_candidate 列（已存在的数据库静默跳过）
            for _col_def in (
                "intent          TEXT DEFAULT ''",
                "scene_candidate TEXT DEFAULT ''",
            ):
                _safe_add_column(conn, "decision_cache", _col_def)

            # ── frigate_cameras: Frigate 摄像头配置 + AI 区域绑定 ──────────────────
            # 存储摄像头 ID → 房间 映射，AI 推理时直接查表获取触发房间，
            # 无需依赖 HA camera.* 实体（适配摄像头未接入 HA 的场景）。
            conn.execute("""
                CREATE TABLE IF NOT EXISTS frigate_cameras (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_id    TEXT UNIQUE NOT NULL,
                    friendly_name TEXT NOT NULL DEFAULT '',
                    rtsp_url     TEXT NOT NULL DEFAULT '',
                    room         TEXT NOT NULL DEFAULT '',
                    min_score    REAL DEFAULT 0.7,
                    threshold    REAL DEFAULT 0.85,
                    fps          INTEGER DEFAULT 5,
                    enabled      INTEGER DEFAULT 1,
                    created_at   TEXT,
                    updated_at   TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_frigate_cam_id "
                "ON frigate_cameras(camera_id)"
            )

            # Frigate Zone → 房间 映射表
            # 一台摄像头可覆盖多个 zone，每个 zone 单独绑定房间，
            # AI 推理时按 entered_zones 中的 zone 查表获取精确触发房间。
            conn.execute("""
                CREATE TABLE IF NOT EXISTS frigate_zones (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_id    TEXT NOT NULL,
                    zone_id      TEXT NOT NULL,
                    friendly_name TEXT NOT NULL DEFAULT '',
                    room         TEXT NOT NULL DEFAULT '',
                    created_at   TEXT,
                    updated_at   TEXT,
                    UNIQUE(camera_id, zone_id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_frigate_zone "
                "ON frigate_zones(camera_id, zone_id)"
            )

            # ── correction_lessons: Phase 3 Lite — 自然语言行为戒律（从 corrections 蒸馏）──
            # 语义：AI 从用户历史修正中提炼的可读规则，直接注入 Prompt L2 层。
            # 每日维护时由 _refresh_correction_lessons() 自动更新。
            conn.execute("""
                CREATE TABLE IF NOT EXISTS correction_lessons (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id        TEXT NOT NULL,
                    room             TEXT DEFAULT '',
                    presence_context TEXT DEFAULT 'any',
                    lesson_text      TEXT NOT NULL,
                    ai_service       TEXT DEFAULT '',
                    user_state       TEXT DEFAULT '',
                    correction_count INTEGER DEFAULT 0,
                    confidence       REAL DEFAULT 0.5,
                    is_conflicted    INTEGER DEFAULT 0,
                    created          TEXT,
                    updated          TEXT,
                    UNIQUE(entity_id, presence_context, ai_service)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lessons_room "
                "ON correction_lessons(room, presence_context)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lessons_conflict "
                "ON correction_lessons(is_conflicted, correction_count)"
            )

            # ── room_topology: P1-2 房间邻接关系 ─────────────────────────────
            conn.execute("""
                CREATE TABLE IF NOT EXISTS room_topology (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_a TEXT NOT NULL,
                    room_b TEXT NOT NULL,
                    relation TEXT DEFAULT 'adjacent',
                    created TEXT,
                    UNIQUE(room_a, room_b)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_topo_room "
                "ON room_topology(room_a)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_topo_room_b "
                "ON room_topology(room_b)"
            )

            # isolation_level=None（自动提交）下 DDL 语句自动提交，无需显式 commit
            # 不再关闭连接——DatabaseService 维持持久化连接直到 async_shutdown
        except Exception as e:
            _LOGGER.warning("[DB] SQLite init failed: %s", e)
            self._sys_log("ERROR", f"数据库初始化失败: {e}")
            return
        self._sys_log("INFO", f"数据库初始化完成: {self._memory_db}")
        self._migrate_json_config()

    def _migrate_json_config(self) -> None:
        """Migrate from legacy JSON config if present."""
        conn = self._db.get_raw_connection()
        if conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] > 0:
            return
        json_path = os.path.join(self._config_dir, "smart_agent_config.json")
        cfg = None
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                os.rename(json_path, json_path + ".migrated")
            except Exception as exc:
                _LOGGER.debug("[DB] 迁移旧版 JSON 配置失败: %s", exc)
        if not cfg:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for eid, desc in cfg.get("devices", {}).items():
            parts = [p.strip() for p in str(desc).split("|")]
            conn.execute(
                "INSERT OR IGNORE INTO devices (entity_id, name, area, type, ops, created, updated) VALUES (?,?,?,?,?,?,?)",
                (eid, parts[0] if parts else eid, parts[1] if len(parts) > 1 else "",
                 parts[2] if len(parts) > 2 else "", parts[3] if len(parts) > 3 else "", now, now),
            )
        for h in cfg.get("habits", []):
            conn.execute("INSERT INTO habits (content, created) VALUES (?,?)", (h, now))
        for r in cfg.get("rules", []):
            conn.execute("INSERT INTO rules (content, created) VALUES (?,?)", (r, now))
        # isolation_level=None（自动提交）下每条 INSERT 自动提交，无需显式 commit
        _LOGGER.info("[DB] Migrated from JSON: %s devices, %s habits, %s rules",
                     len(cfg.get("devices", {})), len(cfg.get("habits", [])), len(cfg.get("rules", [])))

    def _load_config(self) -> None:
        """Load devices/habits/rules from SQLite into memory."""
        self.device_info = {}
        try:
            # row_factory=sqlite3.Row 已在 DatabaseService.open() 中全局设置，
            # 无需在此重复赋值（避免修改共享连接状态引发线程安全问题）。
            conn = self._db.get_raw_connection()
            for r in conn.execute("SELECT * FROM devices"):
                cols = r.keys()
                mode = r["control_mode"] if "control_mode" in cols else "shared"
                if mode not in self._VALID_CONTROL_MODES:
                    mode = "shared"
                s_type = r["sensor_type"] if "sensor_type" in cols else ""
                self.device_info[r["entity_id"]] = {
                    "name": r["name"], "room": r["area"], "type": r["type"],
                    "ops": r["ops"], "control_mode": mode,
                    "sensor_type": s_type,
                }
            self._habits = [(r["content"], bool(r["locked"])) for r in conn.execute("SELECT content, locked FROM habits ORDER BY id")]
            self._rules = [(r["content"], bool(r["locked"])) for r in conn.execute("SELECT content, locked FROM rules ORDER BY id")]
        except Exception as e:
            _LOGGER.warning("[DB] Load config failed: %s", e)
            self._habits = []
            self._rules = []
        _LOGGER.info("[DB] Loaded: %s devices, %s habits, %s rules",
                     len(self.device_info), len(self._habits), len(self._rules))

    def _db_exec(self, sql: str, params: tuple = ()) -> bool:
        """Execute write SQL (sync, run via executor from async context).

        v4.8.27: 委托给 DatabaseService.execute，利用持久化连接 + 写锁。

        Returns:
            True=写入成功；False=写入失败
        """
        return bool(self._db.execute(sql, params))

    async def _async_db_exec(self, sql: str, params: tuple = ()) -> bool:
        """Async wrapper: run write SQL in executor and return success flag."""
        return bool(await self.hass.async_add_executor_job(self._db.execute, sql, params))

    def _query_events(self, sql: str, params: tuple = (), max_rows: int = 10000) -> list[dict]:
        """Run query and return list of dicts (sync, run via executor from async context).

        v4.8.27: 委托给 DatabaseService.query，利用持久化连接（WAL 读无锁）。
        P2修复：简单明细查询自动添加 LIMIT 防止内存溢出；聚合/集合查询默认跳过自动 LIMIT。
        """
        _auto_limited = False
        _effective_sql = sql

        _normalized_sql = (sql or "").strip()
        _normalized_tail = _normalized_sql.rstrip(" ;\t\r\n")

        _has_explicit_limit = bool(re.search(r"\bLIMIT\b", _normalized_tail, re.IGNORECASE))
        _is_complex_query = bool(
            re.search(r"\bGROUP\s+BY\b", _normalized_tail, re.IGNORECASE)
            or re.search(r"\bHAVING\b", _normalized_tail, re.IGNORECASE)
            or re.search(r"\bUNION\b", _normalized_tail, re.IGNORECASE)
            or re.search(r"\bINTERSECT\b", _normalized_tail, re.IGNORECASE)
            or re.search(r"\bEXCEPT\b", _normalized_tail, re.IGNORECASE)
        )

        if max_rows > 0 and not _has_explicit_limit and not _is_complex_query:
            _effective_sql = f"{_normalized_tail} LIMIT {max_rows}"
            _auto_limited = True

        rows = self._db.query(_effective_sql, params)

        if _auto_limited and len(rows) >= max_rows:
            self._sys_log(
                "INFO",
                f"[查询截断] events 查询命中自动 LIMIT {max_rows}，结果可能被截断；如需全量请显式传 max_rows=0",
            )

        return rows

    async def _async_query(self, sql: str, params: tuple = (), max_rows: int = 10000) -> list[dict]:
        """Async wrapper: run _query_events in executor with the same LIMIT policy."""
        return await self.hass.async_add_executor_job(self._query_events, sql, params, max_rows)

    def _record_event(self, event_type: str, detail: str, entity_id: str | None = None,
                      new_state: str | None = None, source: str = "system",
                      confidence: int | None = None, transaction_id: int = 0,
                      action_seq: int = 0) -> None:
        """Record one event to SQLite. Sync (call from executor if needed)."""
        now_ts = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        area = ""
        if entity_id and entity_id in self.device_info:
            area = self.device_info[entity_id].get("room", "")
        if event_type in ("Trigger", "Learning") and entity_id and entity_id in self._last_ai_actions:
            last_ai = self._last_ai_actions[entity_id]
            from .const import OVERRIDE_WINDOW_SECONDS, CORRECTION_WINDOW_SECONDS, MODE_SHOWROOM
            _ai_age = now_ts - last_ai["time"]
            _is_opposite = last_ai["state"] != new_state
            if _is_opposite and _ai_age < OVERRIDE_WINDOW_SECONDS:
                event_type = "Override"
                source = "user"
                detail = f"用户手动覆盖：AI 将 {entity_id} 设为 {last_ai['state']}，用户 {int(_ai_age)}s 后改为 {new_state}"

            # 延迟纠错学习窗口：即使超过 Override 归类窗口，仍可写 corrections
            _in_correction_window = _is_opposite and _ai_age < CORRECTION_WINDOW_SECONDS
            if _in_correction_window:
                # Phase 11.7: 展厅打烊关灯豁免修正学习
                # 展厅非营业时间批量关灯是正常打烊行为，不是对 AI 的不满，不应污染 corrections 表。
                _skip_correction = False
                if (getattr(self, "_mode", None) == MODE_SHOWROOM
                        and last_ai.get("state") == "on"
                        and new_state == "off"):
                    _biz_start = getattr(self, "showroom_biz_start_min", 0)
                    _biz_end = getattr(self, "showroom_biz_end_min", 1439)
                    _now_min = datetime.now().hour * 60 + datetime.now().minute
                    _is_biz_hour = _biz_start <= _now_min < _biz_end
                    if not _is_biz_hour:
                        _skip_correction = True
                        self._sys_log("DEBUG",
                            f"[修正学习豁免] 展厅非营业时间关灯，跳过修正记录: {entity_id} AI→on 用户→off")

                if not _skip_correction:
                    # Phase 7B: 写入 corrections 表，永久记录用户修正
                    self._record_correction(
                        entity_id=entity_id,
                        ai_service=last_ai.get("service", ""),
                        ai_state=last_ai.get("state", ""),
                        user_state=new_state or "",
                        room=area,
                        scene_desc=last_ai.get("scene", ""),
                        trigger_text=last_ai.get("trigger", ""),
                    )
                del self._last_ai_actions[entity_id]

        # 展厅灯光层级学习：仅记录用户手动操作
        if source == "user" and entity_id and new_state:
            self._update_showroom_preference(entity_id, new_state)

        # 正向信号机制：用户主动开灯 → 降低该设备的修正抑制权重
        # 当设备处于"修正抑制"状态时，用户频繁手动开灯说明其想法已改变，
        # 递减 correction_count，让设备逐渐从"只读"恢复为"AI可控"
        if (source == "user" and entity_id and new_state == "on"
                and event_type not in ("Override",)):
            self._apply_positive_correction_signal(entity_id)

        _ok = self._db.execute(
            "INSERT INTO events (time, type, detail, entity, state, source, area, confidence, transaction_id, action_seq) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (timestamp, event_type, detail, entity_id or "", new_state or "", source, area, confidence, transaction_id, action_seq),
        )
        if not _ok:
            _LOGGER.warning("[Events] Write failed: type=%s entity=%s", event_type, entity_id or "")

    # ── Phase 7B: 用户修正永久学习 ─────────────────────────────────────────

    def _infer_presence_context(self, room: str) -> str:
        """
        推断修正发生时的在场状态。

        查询当前房间的占用传感器，返回 'occupied'、'empty' 或 'any'。
        用于 corrections 表的 presence_context 字段，使抑制逻辑能区分
        "有人时 AI 关灯用户开回" 与 "无人时 AI 开灯用户关掉" 两种截然不同的场景。

        Args:
            room: 房间名称

        Returns:
            'occupied' | 'empty' | 'any'（无法判断时降级为 any）
        """
        if not room or not hasattr(self, "hass"):
            return "any"
        try:
            occ_map = self._get_room_occupancy_map() if hasattr(self, "_get_room_occupancy_map") else {}
            sensors = occ_map.get(room, [])
            if not sensors:
                return "any"
            is_occupied = any(s == "on" for _, s in sensors)
            is_unknown = all(s in ("unknown", "unavailable") for _, s in sensors)
            if is_unknown:
                return "any"
            return "occupied" if is_occupied else "empty"
        except Exception:
            return "any"

    def _record_correction(
        self, entity_id: str, ai_service: str, ai_state: str,
        user_state: str, room: str, scene_desc: str, trigger_text: str,
    ) -> None:
        """
        记录用户对 AI 操作的修正（Phase 11.1 增加在场维度）。

        以 entity_id + ai_service + presence_context 为复合键。
        presence_context 区分 'occupied'（有人时修正）和 'empty'（无人时修正），
        使 _should_suppress_action 能根据当前在场状态精确匹配，避免
        "有人时不要关灯" 的合理修正被错误泛化为 "无论何时都不要关灯"。

        ai_service 格式统一为不带域名的服务名（如 "turn_on"）。
        """
        # 统一 ai_service 格式：剥离域名前缀，"light.turn_on" → "turn_on"
        if "." in ai_service:
            ai_service = ai_service.split(".", 1)[-1]

        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        hour = now.hour
        weekday = now.weekday()

        # Phase 11.1: 推断修正发生时的在场状态
        presence_ctx = self._infer_presence_context(room)

        # Phase 11.5 防线三：写入过滤预检（季节性过期修正清理）
        try:
            should_skip, skip_reason = self._memory_guard_write_filter(
                entity_id,
                ai_service,
                user_state,
                room,
                presence_ctx,
            )
            if should_skip:
                _LOGGER.info(
                    "[Corrections] Write skipped by memory guard: entity=%s service=%s reason=%s",
                    entity_id,
                    ai_service,
                    skip_reason,
                )
                return
        except Exception as exc:
            _LOGGER.warning(
                "[Corrections] Memory guard filter failed: entity=%s service=%s err=%s",
                entity_id,
                ai_service,
                exc,
            )
            return

        try:
            # 以 entity_id + ai_service + presence_context 为复合键
            rows = self._db.query(
                "SELECT id, correction_count FROM corrections "
                "WHERE entity_id = ? AND ai_service = ? AND presence_context = ?",
                (entity_id, ai_service, presence_ctx),
            )
            if rows:
                existing = rows[0]
                new_count = existing["correction_count"] + 1
                _ok = self._db.execute(
                    "UPDATE corrections SET correction_count = ?, time = ?, "
                    "hour = ?, weekday = ?, "
                    "user_state = ?, scene_desc = ?, trigger_text = ? WHERE id = ?",
                    (new_count, ts, hour, weekday,
                     user_state, scene_desc, trigger_text, existing["id"]),
                )
                if not _ok:
                    _LOGGER.warning("[Corrections] Update failed: entity=%s service=%s", entity_id, ai_service)
                    return
                count = new_count
            else:
                _ok = self._db.execute(
                    "INSERT INTO corrections "
                    "(time, entity_id, ai_service, ai_state, user_state, room, hour, weekday, "
                    "scene_desc, trigger_text, presence_context) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (ts, entity_id, ai_service, ai_state, user_state, room, hour, weekday,
                     scene_desc, trigger_text, presence_ctx),
                )
                if not _ok:
                    _LOGGER.warning("[Corrections] Insert failed: entity=%s service=%s", entity_id, ai_service)
                    return
                count = 1

            name = self.get_device_name(entity_id) if hasattr(self, "get_device_name") else entity_id
            self._sys_log("INFO",
                f"[修正学习] 记录用户修正: {name} AI→{ai_state} 用户→{user_state} "
                f"(累计第{count}次, {hour}时, {room}, 在场={presence_ctx})")

            # 修正直接更新基线（替代生成 P3 规则）：快速生效，无冲突风险
            # direction: AI 开灯用户关 → down；AI 关灯用户开 → up
            correction_direction = "down" if (ai_state == "on" and user_state == "off") else "up"
            self._apply_correction_to_baseline(entity_id, correction_direction, weight=1.5)

            # Phase 9.9 (TrainingData): 将最近 30 分钟内涉及该设备的 AI 样本标记为负样本
            self._mark_training_negative(entity_id)

            # Phase 1 (DecisionCache): 用户纠正后清除该房间缓存，强制 LLM 重新学习
            if room:
                try:
                    self._invalidate_decision_cache_for_room(room)
                except Exception:
                    pass

            # P1-1: 修正触发时降低被修正行为在 behavior_patterns 中的置信度
            try:
                self._decay_behavior_pattern_on_correction(entity_id, ai_service, hour)
            except Exception:
                pass

            # P1-1: 修正累计 ≥2 次时自动生成/更新该设备的 correction_lesson
            if count >= 2:
                try:
                    self._upsert_single_correction_lesson(
                        entity_id, ai_service, user_state, room, presence_ctx, count
                    )
                except Exception:
                    pass

        except Exception as e:
            _LOGGER.warning("[Corrections] Write failed: %s", e)

    def _decay_behavior_pattern_on_correction(
        self, entity_id: str, ai_service: str, hour: int,
    ) -> None:
        """P1-1: 修正发生时，降低对应 behavior_pattern 的置信度（-15，下限 10）。"""
        expected = "on" if "turn_on" in ai_service else "off"
        _ok = self._db.execute(
            "UPDATE behavior_patterns SET confidence = MAX(10, confidence - 15), "
            "last_updated = ? "
            "WHERE entity_id = ? AND expected_state = ? "
            "AND hour_start <= ? AND hour_end >= ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             entity_id, expected, hour, hour),
        )
        if not _ok:
            _LOGGER.warning("[BehaviorPattern] Decay write failed: entity=%s service=%s", entity_id, ai_service)

    def _upsert_single_correction_lesson(
        self, entity_id: str, ai_service: str, user_state: str,
        room: str, presence_ctx: str, count: int,
    ) -> None:
        """P1-1: 单设备增量更新 correction_lesson（从修正记录蒸馏可读规则）。"""
        _SVC_LABEL = {
            "turn_on": "开启", "turn_off": "关闭",
            "open_cover": "打开", "close_cover": "关闭",
        }
        name = self.get_device_name(entity_id) if hasattr(self, "get_device_name") else entity_id
        svc_label = _SVC_LABEL.get(ai_service, ai_service)
        pres_label = {"occupied": "有人时", "empty": "无人时"}.get(presence_ctx, "")
        lesson = f"{pres_label}不要{svc_label}{name}（用户已纠正{count}次→{user_state}）"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _ok = self._db.execute(
            "INSERT INTO correction_lessons "
            "(entity_id, room, presence_context, lesson_text, ai_service, "
            "user_state, correction_count, confidence, created, updated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0.5, ?, ?) "
            "ON CONFLICT(entity_id, presence_context, ai_service) DO UPDATE SET "
            "lesson_text = excluded.lesson_text, correction_count = excluded.correction_count, "
            "updated = excluded.updated",
            (entity_id, room, presence_ctx, lesson, ai_service,
             user_state, count, ts, ts),
        )
        if not _ok:
            _LOGGER.warning("[Corrections] Lesson upsert failed: entity=%s service=%s", entity_id, ai_service)

    def _apply_positive_correction_signal(self, entity_id: str) -> None:
        """
        正向信号：用户主动开灯时，递减该设备的修正抑制权重。

        当设备被修正抑制（AI 被用户关过多次）后，如果用户日后主动开灯，
        说明用户的偏好已经改变或是特殊场景需要。每次主动开灯将全局
        correction_count 减 1（最低为 0），让设备逐步从"只读"恢复为"AI可控"。

        触发条件：
          - 事件来源为用户手动操作（source == "user"）
          - 设备当前有 turn_on 方向的修正记录（ai_service 含 turn_on）
          - 非 Override 事件（避免与负向修正逻辑干扰）
          - 距上次负向修正超过 30 分钟（冷却保护）：
            避免"关灯纠正 → 立刻手动开其他灯"误消耗本设备的修正计数，
            或用户刚纠正完又开同一盏灯（场景切换）被系统误认为"原谅AI"。
        """
        try:
            # 冷却保护：若该设备 30 分钟内刚发生过负向修正，跳过正向信号
            cooldown_cutoff = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            recent_neg = self._db.query(
                "SELECT id FROM corrections "
                "WHERE entity_id = ? AND time >= ?",
                (entity_id, cooldown_cutoff),
            )
            if recent_neg:
                return  # 冷却期内，跳过正向信号，避免抵消刚刚记录的纠正

            rows = self._db.query(
                "SELECT id, correction_count FROM corrections "
                "WHERE entity_id = ? AND ai_service LIKE '%turn_on%' "
                "AND correction_count > 0",
                (entity_id,),
            )
            if not rows:
                return
            updated_any = False
            for row in rows:
                new_count = max(0, row["correction_count"] - 1)
                _ok = self._db_exec(
                    "UPDATE corrections SET correction_count = ? WHERE id = ?",
                    (new_count, row["id"]),
                )
                if not _ok:
                    _LOGGER.warning("[PositiveSignal] correction_count update failed: id=%s entity=%s", row["id"], entity_id)
                    continue
                updated_any = True
            if not updated_any:
                _LOGGER.warning("[PositiveSignal] no correction rows updated: entity=%s", entity_id)
                return
            name = self.get_device_name(entity_id) if hasattr(self, "get_device_name") else entity_id
            self._sys_log("INFO",
                f"[修正学习] 正向信号: {name} 用户主动开灯（冷却期已过），"
                f"修正计数 {rows[0]['correction_count']} → {max(0, rows[0]['correction_count'] - 1)}")
        except Exception as e:
            _LOGGER.debug("[PositiveSignal] Failed for %s: %s", entity_id, e)

    def _should_suppress_action(
        self, entity_id: str, service: str, hour: int | None = None,
        current_presence: str | None = None, room: str | None = None,
    ) -> tuple[bool, int, float]:
        """
        基于修正历史判断是否应抑制某个 AI 动作（Phase 11.1 增加在场维度）。

        设计原则：
          - 数据驱动，完全替代"规则生成"路径
          - 优先匹配当前在场状态的精确修正记录；精确记录不命中时降级匹配 'any' 记录
          - 首次纠正即生效：用户纠正一次即抑制，避免 AI 反复犯错
          - 记忆自然衰减：decay_score 降至阈值以下，抑制自动解除
          - 仅对 LLM 慢脑自动触发的动作生效；快脑反射弧和 USER_EXPLICIT 由调用方豁免

        关键修复（Phase 11.1）：
          - 增加 presence_context 维度，'occupied' 时的修正只在有人时生效，
            'empty' 时的修正只在无人时生效。避免 "有人时不要关灯" 的修正
            错误阻止 "无人时应该关灯" 的合理决策。

        Args:
            entity_id:        设备实体 ID
            service:          AI 动作服务名（如 "turn_on"）
            hour:             保留参数（向后兼容）
            current_presence: 当前在场状态 'occupied'|'empty'|None（None 则降级为 any 查询）
            room:             房间名（current_presence 为 None 时自动推断）

        Returns:
            (should_suppress, correction_count, decay_score)
        """
        svc_bare = service.split(".", 1)[-1] if "." in service else service
        cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")

        # Phase 11.1: 若未传入 current_presence，尝试从 room 推断
        if current_presence is None and room:
            current_presence = self._infer_presence_context(room)

        try:
            # 第一优先级：精确匹配当前在场状态（'occupied' 或 'empty'）
            if current_presence in ("occupied", "empty"):
                rows = self._db.query(
                    "SELECT correction_count, time FROM corrections "
                    "WHERE entity_id = ? AND ai_service LIKE '%' || ? || '%' "
                    "AND time >= ? AND correction_count >= 1 "
                    "AND presence_context = ? "
                    "ORDER BY correction_count DESC, time DESC LIMIT 1",
                    (entity_id, svc_bare, cutoff, current_presence),
                )
                if rows:
                    row = rows[0]
                    score = self._compute_memory_decay_score(row["time"], row["correction_count"])
                    if score >= 0.15:
                        return True, row["correction_count"], score

            # 第二优先级：降级匹配 'any'（旧数据或无法判断在场的修正）
            rows = self._db.query(
                "SELECT correction_count, time FROM corrections "
                "WHERE entity_id = ? AND ai_service LIKE '%' || ? || '%' "
                "AND time >= ? AND correction_count >= 1 "
                "AND presence_context = 'any' "
                "ORDER BY correction_count DESC, time DESC LIMIT 1",
                (entity_id, svc_bare, cutoff),
            )
            if not rows:
                return False, 0, 0.0
            row = rows[0]
            score = self._compute_memory_decay_score(row["time"], row["correction_count"])
            if score >= 0.15:
                return True, row["correction_count"], score
            return False, row["correction_count"], score
        except Exception as e:
            _LOGGER.debug("[Suppress] Query failed for %s/%s: %s", entity_id, service, e)
            return False, 0, 0.0

    def _get_recent_corrections(self, entity_id: str | None = None, limit: int = 10) -> list[dict]:
        """
        查询近期用户修正记录（同步，通过 executor 调用）。

        Args:
            entity_id: 指定设备 ID，None 则查全部
            limit: 返回数量上限
        """
        try:
            if entity_id:
                return self._db.query(
                    "SELECT * FROM corrections WHERE entity_id = ? ORDER BY time DESC LIMIT ?",
                    (entity_id, limit),
                )
            else:
                return self._db.query(
                    "SELECT * FROM corrections ORDER BY correction_count DESC, time DESC LIMIT ?",
                    (limit,),
                )
        except Exception as e:
            _LOGGER.warning("[Corrections] Query failed: %s", e)
            return []

    # ── 展厅灯光层级学习 ──────────────────────────────────────────────────────

    def _update_showroom_preference(self, entity_id: str, new_state: str) -> None:
        """根据用户手动操作更新展厅灯光偏好。"""
        if not entity_id or not entity_id.startswith("light."):
            return
        # 仅针对展厅设备
        room = (self.device_info.get(entity_id) or {}).get("room", "")
        _showroom_area = getattr(self, "showroom_area_name", "")
        # 完全基于 HA Area Registry 的 room 字段，不依赖实体 ID 拼音
        is_showroom = (
            bool(_showroom_area)
            and room == _showroom_area
            and room not in getattr(self, "showroom_excluded_subareas", [])
        )
        if not is_showroom:
            return

        is_on = new_state == "on"
        is_off = new_state == "off"
        if not (is_on or is_off):
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            _ok = self._db_exec("""
                INSERT INTO showroom_light_preferences (entity_id, on_count, off_count, tier, last_updated)
                VALUES (?, ?, ?, 'core', ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    on_count = on_count + ?,
                    off_count = off_count + ?,
                    last_updated = ?
            """, (entity_id, 1 if is_on else 0, 1 if is_off else 0, ts,
                  1 if is_on else 0, 1 if is_off else 0, ts))
            if not _ok:
                _LOGGER.warning("[ShowroomPref] Update write failed: entity=%s", entity_id)
        except Exception as e:
            _LOGGER.warning("[ShowroomPref] Update failed: %s", e)

    def _get_showroom_light_tier_v2(self, entity_id: str) -> str:
        """基于基线分数获取展厅灯光层级（v2，优先使用基线数据）。

        基线 on_ratio >= 0.6  → core（用户常开，保护不关）
        基线 on_ratio 0.25~0.6 → display（用户偶尔开，无人可调暗）
        基线 on_ratio < 0.25   → auxiliary（用户基本不开，无人可关）
        无足够基线数据（< 5 次采样）→ 回退旧 tier 表，再兜底 display（不再默认 core）

        :param entity_id: 设备实体 ID
        :return: 'core' | 'display' | 'auxiliary'
        """
        try:
            baseline = self._get_baseline(entity_id)
            if baseline and baseline["total_samples"] >= 5:
                ratio = baseline["on_ratio"]
                if ratio >= 0.6:
                    return "core"
                elif ratio >= 0.25:
                    return "display"
                else:
                    return "auxiliary"
            # 基线不足时回退旧 tier 表
            result = self._db.query_scalar(
                "SELECT tier FROM showroom_light_preferences WHERE entity_id = ?",
                (entity_id,),
            )
            # 旧 tier 表也没有时，默认 display（不再是 core，避免全锁死）
            return result if result is not None else "display"
        except Exception:
            return "display"

    def _recalculate_showroom_tiers(self) -> dict:
        """重新计算所有展厅灯光的层级。"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results = {"core": 0, "display": 0, "auxiliary": 0}
        try:
            rows = self._db.query("SELECT entity_id, on_count, off_count FROM showroom_light_preferences")
            for r in rows:
                eid, on_c, off_c = r["entity_id"], r["on_count"], r["off_count"]
                total = on_c + off_c
                if total < 5:
                    tier = "core"
                else:
                    off_ratio = off_c / total
                    if off_ratio < 0.2:
                        tier = "core"
                    elif off_ratio < 0.6:
                        tier = "display"
                    else:
                        tier = "auxiliary"

                _ok = self._db_exec(
                    "UPDATE showroom_light_preferences SET tier = ?, last_updated = ? WHERE entity_id = ?",
                    (tier, ts, eid),
                )
                if not _ok:
                    _LOGGER.warning("[ShowroomPref] Tier update failed: entity=%s tier=%s", eid, tier)
                    continue
                results[tier] += 1
            return results
        except Exception as e:
            _LOGGER.warning("[ShowroomPref] Recalculate failed: %s", e)
            return results

    # ── device_baseline: 设备使用基线采样与查询 ─────────────────────────────────

    def _sample_device_baseline(self, entity_id: str, is_on: bool, brightness: int = 0) -> None:
        """记录一次设备状态采样，更新基线统计。

        每次巡检时调用，无论设备是否在营业/在家时间均调用；
        调用方按需过滤（如展厅只在营业时间采样，家庭只在有人在场时采样）。

        :param entity_id: 设备实体 ID
        :param is_on:     当前是否为开启状态
        :param brightness: 灯光亮度百分比（0 表示非灯光设备）
        """
        info = self.device_info.get(entity_id, {})
        room = (info.get("room") or "").strip()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hour_bucket = datetime.now().hour
        on_inc = 1 if is_on else 0
        try:
            # v1：全天汇总（保持向后兼容）
            _ok_daily = self._db_exec("""
                INSERT INTO device_baseline
                    (entity_id, room, on_samples, total_samples, on_ratio, avg_brightness, last_updated)
                VALUES (?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    room          = excluded.room,
                    on_samples    = on_samples  + ?,
                    total_samples = total_samples + 1,
                    on_ratio      = CAST(on_samples + ? AS REAL) / (total_samples + 1),
                    avg_brightness= CASE WHEN ? > 0
                                    THEN (avg_brightness * total_samples + ?) / (total_samples + 1)
                                    ELSE avg_brightness END,
                    last_updated  = ?
            """, (
                entity_id, room, on_inc, float(on_inc), brightness, ts,
                on_inc, on_inc, brightness, brightness, ts,
            ))
            if not _ok_daily:
                _LOGGER.warning("[Baseline] Daily sample write failed: entity=%s", entity_id)
                return

            # v2：按小时分段（供 MemoryStore._build_baseline_hint_sync 精细查询）
            _ok_hourly = self._db_exec("""
                INSERT INTO device_baseline_hourly
                    (entity_id, hour_bucket, room, usage_ratio, sample_count, last_updated)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(entity_id, hour_bucket) DO UPDATE SET
                    room         = excluded.room,
                    usage_ratio  = CAST(
                                       (usage_ratio * sample_count + ?)
                                       AS REAL) / (sample_count + 1),
                    sample_count = sample_count + 1,
                    last_updated = ?
            """, (
                entity_id, hour_bucket, room, float(on_inc), ts,
                float(on_inc), ts,
            ))
            if not _ok_hourly:
                _LOGGER.warning("[Baseline] Hourly sample write failed: entity=%s hour=%s", entity_id, hour_bucket)
        except Exception as e:
            _LOGGER.warning("[Baseline] Sample failed for %s: %s", entity_id, e)

    def _apply_correction_to_baseline(self, entity_id: str, direction: str, weight: float = 1.5) -> None:
        """将用户修正直接反映到基线分数，替代生成 P3 规则。

        direction='down': 用户把 AI 开的灯关掉 → on_ratio 下压
        direction='up':   用户把 AI 关的灯开起来 → on_ratio 上推

        :param entity_id: 设备实体 ID
        :param direction: 'down' 或 'up'
        :param weight:    修正权重（1.5 = 一次修正相当于 1.5 次普通采样）
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info = self.device_info.get(entity_id, {})
        room = (info.get("room") or "").strip()
        try:
            if direction == "down":
                # 增加关闭采样，同时记录 correction_down 计数
                _ok = self._db_exec("""
                    INSERT INTO device_baseline
                        (entity_id, room, on_samples, total_samples, on_ratio, correction_down, last_updated)
                    VALUES (?, ?, 0, ?, ?, 1, ?)
                    ON CONFLICT(entity_id) DO UPDATE SET
                        room            = excluded.room,
                        total_samples   = total_samples + ?,
                        on_ratio        = CAST(on_samples AS REAL) / (total_samples + ?),
                        correction_down = correction_down + 1,
                        last_updated    = ?
                """, (entity_id, room, int(weight), 0.0, ts,
                      int(weight), int(weight), ts))
                if not _ok:
                    _LOGGER.warning("[Baseline] Correction down write failed: entity=%s", entity_id)
            else:
                # 增加开启采样
                w = int(weight)
                _ok = self._db_exec("""
                    INSERT INTO device_baseline
                        (entity_id, room, on_samples, total_samples, on_ratio, correction_up, last_updated)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(entity_id) DO UPDATE SET
                        room           = excluded.room,
                        on_samples     = on_samples + ?,
                        total_samples  = total_samples + ?,
                        on_ratio       = CAST(on_samples + ? AS REAL) / (total_samples + ?),
                        correction_up  = correction_up + 1,
                        last_updated   = ?
                """, (entity_id, room, w, w, 1.0, ts,
                      w, w, w, w, ts))
                if not _ok:
                    _LOGGER.warning("[Baseline] Correction up write failed: entity=%s", entity_id)
        except Exception as e:
            _LOGGER.warning("[Baseline] Correction failed for %s: %s", entity_id, e)

    def _get_baseline_for_room(self, room: str, min_samples: int = 3) -> list[dict]:
        """查询某房间所有设备的基线数据。

        :param room:        房间名称
        :param min_samples: 最少采样次数（样本不足的设备不返回）
        :return: list of dict 包含 entity_id / on_ratio / avg_brightness / correction_down
        """
        try:
            return self._db.query(
                "SELECT entity_id, on_ratio, avg_brightness, correction_down, total_samples "
                "FROM device_baseline WHERE room = ? AND total_samples >= ? "
                "ORDER BY on_ratio DESC",
                (room, min_samples),
            )
        except Exception as e:
            _LOGGER.warning("[Baseline] Query failed for room %s: %s", room, e)
            return []

    def _get_baseline(self, entity_id: str) -> dict | None:
        """查询单台设备的基线数据。

        :param entity_id: 设备实体 ID
        :return: dict 或 None
        """
        try:
            rows = self._db.query(
                "SELECT entity_id, on_ratio, avg_brightness, correction_down, total_samples "
                "FROM device_baseline WHERE entity_id = ?",
                (entity_id,),
            )
            return rows[0] if rows else None
        except Exception as e:
            _LOGGER.warning("[Baseline] Single query failed for %s: %s", entity_id, e)
            return None

    # ── Phase 0: arrival_baseline — 到达场景灯光基线 ─────────────────────────

    def _record_arrival_snapshot(
        self,
        room: str,
        presence_entity_id: str,
        light_states: "dict[str, str | None] | None" = None,
    ) -> None:
        """在存在传感器触发 5 分钟后对房间灯光进行快照，写入 arrival_baseline。

        由 listeners.py 中的存在传感器确认回调延迟调度，在 executor 中执行。

        :param room:               房间名
        :param presence_entity_id: 触发本次到达的传感器实体 ID（仅用于日志）
        :param light_states:       预先在事件循环中捕获的灯光状态
                                   {entity_id: state_str | None}。
                                   若为 None（兼容旧调用），回退到直接读 hass.states（不推荐）。
        """
        try:
            now = datetime.now()
            hour_bucket = now.hour  # 0-23，按小时分桶
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            # 优先使用事件循环预捕获的状态；回退到直接读取（仅用于兼容，有线程安全风险）
            if light_states is None:
                light_states = {}
                for eid, info in self.device_info.items():
                    if not eid.startswith("light.") or info.get("room") != room:
                        continue
                    st = self.hass.states.get(eid)
                    light_states[eid] = st.state if st else None

            # 收集该房间所有灯的当前状态
            updated_count = 0
            for eid, state_str in light_states.items():
                if state_str is None:
                    continue
                is_on = 1 if state_str == "on" else 0

                # UPSERT：累加采样计数，重算 turn_on_ratio
                try:
                    _ok = self._db_exec(
                        """
                        INSERT INTO arrival_baseline
                            (entity_id, room, hour_bucket,
                             on_samples, total_samples, turn_on_ratio, last_updated)
                        VALUES (?, ?, ?, ?, 1, ?, ?)
                        ON CONFLICT(entity_id, hour_bucket) DO UPDATE SET
                            on_samples    = on_samples + excluded.on_samples,
                            total_samples = total_samples + 1,
                            turn_on_ratio = CAST(on_samples + excluded.on_samples AS REAL)
                                            / (total_samples + 1),
                            last_updated  = excluded.last_updated
                        """,
                        (eid, room, hour_bucket, is_on, float(is_on), now_str),
                    )
                    if not _ok:
                        _LOGGER.debug("[ArrivalBaseline] UPSERT 写入失败 %s", eid)
                        continue
                    updated_count += 1
                except Exception as exc:
                    _LOGGER.debug("[ArrivalBaseline] UPSERT 失败 %s: %s", eid, exc)

            _LOGGER.debug(
                "[ArrivalBaseline] 快照完成: room=%s hour=%d 设备数=%d 触发传感器=%s",
                room, hour_bucket, updated_count, presence_entity_id,
            )
        except Exception as exc:
            _LOGGER.warning("[ArrivalBaseline] 快照异常: %s", exc)

    def _get_arrival_baseline_for_room(
        self, room: str, hour_bucket: int | None = None, min_samples: int = 3
    ) -> list[dict]:
        """查询某房间的到达基线数据。

        :param room:        房间名称
        :param hour_bucket: 当前小时（0-23），None 表示查所有时段的均值
        :param min_samples: 最少采样次数
        :return: list[dict] 含 entity_id / turn_on_ratio / total_samples
        """
        try:
            if hour_bucket is not None:
                # 精确时段匹配（含±1小时容差：e.g. 查 10 时覆盖 9/10/11）
                buckets = [
                    (hour_bucket - 1) % 24,
                    hour_bucket,
                    (hour_bucket + 1) % 24,
                ]
                placeholders = ",".join("?" * len(buckets))
                rows = self._db.query(
                    f"""
                    SELECT entity_id,
                           AVG(turn_on_ratio) AS turn_on_ratio,
                           SUM(total_samples) AS total_samples
                    FROM arrival_baseline
                    WHERE room = ?
                      AND hour_bucket IN ({placeholders})
                    GROUP BY entity_id
                    HAVING SUM(total_samples) >= ?
                    ORDER BY turn_on_ratio DESC
                    """,
                    (room, *buckets, min_samples),
                )
            else:
                rows = self._db.query(
                    """
                    SELECT entity_id,
                           AVG(turn_on_ratio) AS turn_on_ratio,
                           SUM(total_samples) AS total_samples
                    FROM arrival_baseline
                    WHERE room = ?
                    GROUP BY entity_id
                    HAVING SUM(total_samples) >= ?
                    ORDER BY turn_on_ratio DESC
                    """,
                    (room, min_samples),
                )
            return rows
        except Exception as exc:
            _LOGGER.warning(
                "[ArrivalBaseline] 查询失败 room=%s hour=%s: %s", room, hour_bucket, exc
            )
            return []

    # ── Phase 7C: 认知记忆衰减与语义权重 ──────────────────────────────────────

    @staticmethod
    def _compute_memory_decay_score(time_str: str, hit_count: int = 1) -> float:
        """
        计算记忆衰减得分。

        算法：时间衰减 × 强度系数
          - 时间衰减：半衰期 30 天的指数衰减，即 30 天后权重减半
          - 强度系数：hit_count（修正/命中次数）越多权重越高，上限 1.0
          - 最终得分 = time_decay × min(1.0, hit_count × 0.25)

        分数说明：
          - 1.0 = 今天的 4+ 次强化记忆（最高权重）
          - 0.5 = 30 天前的 4+ 次强化记忆
          - 0.1 ≈ 120 天前的单次记忆（接近被遗忘）
        """
        import math
        try:
            dt = datetime.strptime(time_str[:19], "%Y-%m-%d %H:%M:%S")
            days_ago = (datetime.now() - dt).total_seconds() / 86400
        except Exception:
            days_ago = 365

        HALF_LIFE_DAYS = 30
        decay_lambda = math.log(2) / HALF_LIFE_DAYS
        time_decay = math.exp(-decay_lambda * max(0, days_ago))

        # hit_count 越多，基础强度越高，最高 1.0
        strength = min(1.0, hit_count * 0.25)
        return round(time_decay * strength, 4)

    def _get_corrections_for_prompt(
        self,
        involved_entities: list[str] | None = None,
        trigger_room: str | None = None,
        current_presence: str | None = None,
    ) -> str:
        """
        生成修正记录的 Prompt 注入文本（Phase 11.4 增加房间过滤 + 在场上下文展示）。

        L2 记忆层策略：
          - 优先注入与触发房间 / 当前在场状态匹配的修正记录（精确相关记忆）
          - 其次降级到全局修正（保证兜底学习不丢失）
          - presence_context 字段在输出中明确标注，让 AI 理解"此修正在何种场景下发生"
          - 衰减得分 < 0.15 的过时记录不注入

        Args:
            involved_entities: 指定设备 ID 列表（精确过滤）
            trigger_room:      触发房间（L2 层：优先展示该房间修正）
            current_presence:  当前在场状态 'occupied'|'empty'（用于标注相关性）
        """
        try:
            cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")

            if involved_entities:
                placeholders = ",".join("?" for _ in involved_entities)
                rows = self._db.query(
                    f"SELECT * FROM corrections "
                    f"WHERE entity_id IN ({placeholders}) "
                    f"AND time >= ? AND correction_count >= 1 "
                    f"ORDER BY correction_count DESC, time DESC LIMIT 20",
                    (*involved_entities, cutoff),
                )
            elif trigger_room:
                # Phase 11.4 L2: 优先按触发房间过滤，减少无关记忆干扰
                rows = self._db.query(
                    "SELECT * FROM corrections "
                    "WHERE room = ? AND time >= ? AND correction_count >= 1 "
                    "ORDER BY correction_count DESC, time DESC LIMIT 15",
                    (trigger_room, cutoff),
                )
                # 若房间过滤结果不足 3 条，补充全局前几条（保证信息量）
                if len(rows) < 3:
                    extra = self._db.query(
                        "SELECT * FROM corrections "
                        "WHERE room != ? AND time >= ? AND correction_count >= 1 "
                        "ORDER BY correction_count DESC, time DESC LIMIT 5",
                        (trigger_room, cutoff),
                    )
                    rows = rows + extra
            else:
                rows = self._db.query(
                    "SELECT * FROM corrections "
                    "WHERE time >= ? AND correction_count >= 1 "
                    "ORDER BY correction_count DESC, time DESC LIMIT 20",
                    (cutoff,),
                )

            if not rows:
                return ""

            scored: list[tuple[float, dict]] = []
            for r in rows:
                score = self._compute_memory_decay_score(r["time"], r["correction_count"])
                if score >= 0.15:
                    scored.append((score, r))

            if not scored:
                return ""

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:5]

            lines = ["【⚠️ 用户修正历史（以下操作曾被用户纠正，权重越高越重要）】"]
            for score, r in top:
                name = self.get_device_name(r["entity_id"]) if hasattr(self, "get_device_name") else r["entity_id"]
                score_hint = "🔴强" if score >= 0.7 else ("🟡中" if score >= 0.4 else "🔵弱")
                # Phase 11.4: 展示 presence_context，让 AI 理解修正发生的在场条件
                pctx = r.get("presence_context", "any")
                pctx_cn = {"occupied": "有人时", "empty": "无人时", "any": "不限在场"}.get(pctx, pctx)
                # 标记与当前在场状态的相关性
                relevance = ""
                if current_presence and pctx != "any":
                    if pctx == current_presence:
                        relevance = " ⚡当前场景适用"
                    else:
                        relevance = " ⬛当前场景不适用"
                lines.append(
                    f"  - [{score_hint}|{r['correction_count']}次|{pctx_cn}{relevance}] {name}: "
                    f"在 {r['hour']}:00 左右 AI 执行 {r['ai_service']}→{r['ai_state']} 被用户改为→{r['user_state']}"
                )
            return "\n".join(lines)
        except Exception as e:
            _LOGGER.warning("[Corrections] Prompt generation failed: %s", e)
            return ""

    def _get_verified_success_ai_actions(self, days: int = 60) -> list[dict]:
        """返回最近 N 天 verified=1 且 success=1 的 AI_Action 聚合样本（按实体+状态+小时）。"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            return self._db.query(
                "SELECT entity_id AS entity, actual_state AS state, "
                "CAST(substr(time,12,2) AS INTEGER) AS h, "
                "CAST(strftime('%w', time) AS INTEGER) AS wd, "
                "COUNT(*) AS cnt "
                "FROM action_results "
                "WHERE verified=1 AND success=1 AND time >= ? "
                "AND (entity_id LIKE 'light.%' OR entity_id LIKE 'switch.%' OR "
                "entity_id LIKE 'climate.%' OR entity_id LIKE 'cover.%' OR entity_id LIKE 'fan.%') "
                "GROUP BY entity_id, actual_state, h, wd",
                (cutoff,),
            )
        except Exception as e:
            _LOGGER.warning("[ActionResult] Verified AI action query failed: %s", e)
            return []

    def _record_action_result(self, entity_id: str, domain: str, service: str,
                              expected: str, actual: str, success: int,
                              retry_count: int, latency_ms: int, reason: str,
                              transaction_id: int = 0, action_seq: int = 0) -> None:
        """同步写入 action_results 表（通过 executor 调用）。"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _ok = self._db.execute(
            "INSERT INTO action_results (time,entity_id,domain,service,expected_state,actual_state,verified,success,retry_count,latency_ms,reason,transaction_id,action_seq) "
            "VALUES (?,?,?,?,?,?,1,?,?,?,?,?,?)",
            (ts, entity_id, domain, service, expected, actual, success, retry_count, latency_ms, reason, transaction_id, action_seq),
        )
        if not _ok:
            _LOGGER.warning("[ActionResult] Write failed: entity=%s service=%s", entity_id, service)

    def _get_action_quality_stats(self) -> dict:
        """查询动作执行质量统计（同步，通过 executor 调用）。"""
        stats: dict = {"total": 0, "success": 0, "failed": 0, "rate": 0.0,
                       "retry_total": 0, "avg_latency_ms": 0, "top_failures": []}
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            agg_rows = self._db.query(
                "SELECT COUNT(*) as total, SUM(success) as ok, SUM(retry_count) as retries, AVG(latency_ms) as avg_lat "
                "FROM action_results WHERE time >= ?",
                (cutoff,),
            )
            if agg_rows and agg_rows[0]["total"]:
                row = agg_rows[0]
                stats["total"] = row["total"]
                stats["success"] = row["ok"] or 0
                stats["failed"] = stats["total"] - stats["success"]
                stats["rate"] = round(stats["success"] / stats["total"] * 100, 1) if stats["total"] else 0
                stats["retry_total"] = row["retries"] or 0
                stats["avg_latency_ms"] = int(row["avg_lat"] or 0)
            fail_rows = self._db.query(
                "SELECT entity_id, COUNT(*) as fail_cnt FROM action_results "
                "WHERE success=0 AND time >= ? "
                "GROUP BY entity_id ORDER BY fail_cnt DESC LIMIT 5",
                (cutoff,),
            )
            stats["top_failures"] = [{"entity_id": r["entity_id"], "count": r["fail_cnt"]} for r in fail_rows]
        except Exception as e:
            _LOGGER.warning("[QualityStats] Query failed: %s", e)
        return stats

    # ── Phase 4: AI 场景持久化 ────────────────────────────────────────────────

    def _query_ai_scenes(self, status: str | None = None) -> list[dict]:
        """查询 ai_scenes 表（同步，通过 executor 调用）。"""
        try:
            if status:
                return self._db.query(
                    "SELECT * FROM ai_scenes WHERE status=? ORDER BY confidence DESC, id DESC",
                    (status,),
                )
            else:
                return self._db.query(
                    "SELECT * FROM ai_scenes ORDER BY confidence DESC, id DESC"
                )
        except Exception as e:
            _LOGGER.warning("[AiScenes] Query failed: %s", e)
            return []

    def _upsert_ai_scene(self, name: str, description: str, entities_json: str,
                         trigger_context: str, hour_start: int, hour_end: int,
                         weekday_mask: str, confidence: int, hit_count: int,
                         actions_json: str = "[]") -> None:
        """插入或更新候选场景（同步，通过 executor 调用）。
        已存在且状态为 rejected/active 的场景不覆盖，只更新 pending 状态的。
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            rows = self._db.query(
                "SELECT id, status FROM ai_scenes WHERE name=?", (name,),
            )
            if rows:
                existing = rows[0]
                if existing["status"] in ("active", "rejected"):
                    _ok = self._db.execute(
                        "UPDATE ai_scenes SET hit_count=?, updated=? WHERE name=?",
                        (hit_count, now, name),
                    )
                    if not _ok:
                        _LOGGER.warning("[AiScenes] Upsert write failed(update-hit): name=%s", name)
                        return
                else:
                    _ok = self._db.execute(
                        "UPDATE ai_scenes SET description=?, entities_json=?, actions_json=?, "
                        "trigger_context=?, hour_start=?, hour_end=?, weekday_mask=?, "
                        "confidence=?, hit_count=?, updated=? WHERE name=?",
                        (description, entities_json, actions_json, trigger_context, hour_start, hour_end,
                         weekday_mask, confidence, hit_count, now, name),
                    )
                    if not _ok:
                        _LOGGER.warning("[AiScenes] Upsert write failed(update): name=%s", name)
                        return
            else:
                _ok = self._db.execute(
                    "INSERT INTO ai_scenes (name,description,entities_json,actions_json,trigger_context,"
                    "hour_start,hour_end,weekday_mask,confidence,hit_count,status,source,created,updated) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,'pending','auto',?,?)",
                    (name, description, entities_json, actions_json, trigger_context,
                     hour_start, hour_end, weekday_mask, confidence, hit_count, now, now),
                )
                if not _ok:
                    _LOGGER.warning("[AiScenes] Upsert write failed(insert): name=%s", name)
                    return
        except Exception as e:
            _LOGGER.warning("[AiScenes] Upsert failed: %s", e)

    def _update_ai_scene_status(self, scene_id: int, status: str) -> bool:
        """更新场景状态（同步）。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _ok = self._db.execute(
            "UPDATE ai_scenes SET status=?, updated=? WHERE id=?",
            (status, now, scene_id),
        )
        if not _ok:
            _LOGGER.warning("[AiScenes] Status update failed: id=%s", scene_id)
            return False
        return True
    def _update_ai_scene_ha_entity(self, scene_id: int, ha_entity_id: str) -> bool:
        """更新场景已注册的 HA entity_id（5C-2 场景持久化写入后调用，同步）。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _ok = self._db.execute(
            "UPDATE ai_scenes SET ha_entity_id=?, updated=? WHERE id=?",
            (ha_entity_id, now, scene_id),
        )
        if not _ok:
            _LOGGER.warning("[AiScenes] ha_entity_id update failed: id=%s", scene_id)
            return False
        return True
    def _delete_ai_scene_db(self, scene_id: int) -> bool:
        """从数据库删除场景（同步）。"""
        _ok = self._db.execute("DELETE FROM ai_scenes WHERE id=?", (scene_id,))
        if not _ok:
            _LOGGER.warning("[AiScenes] Delete failed: id=%s", scene_id)
            return False
        return True
    # ── Layer 2: 事务管理 CRUD ────────────────────────────────────────────────

    def _begin_transaction_db(
        self,
        trigger_summary: str,
        scene_desc: str,
        confidence: int,
        action_count: int,
        pre_states_json: str,
        actions_json: str,
    ) -> int:
        """写入一条 pending 事务记录，返回自增 id（同步，通过 executor 调用）。"""
        import json as _json
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _ok = self._db.execute(
            "INSERT INTO action_transactions "
            "(time,trigger_summary,scene_desc,confidence,action_count,"
            "pre_states_json,actions_json,status) "
            "VALUES (?,?,?,?,?,?,?,'pending')",
            (now, trigger_summary[:200], scene_desc[:200], confidence,
             action_count, pre_states_json, actions_json),
        )
        if not _ok:
            _LOGGER.warning("[Transaction] Begin failed: trigger=%s", trigger_summary[:60])
            return 0
        row_id = self._db.query_scalar("SELECT last_insert_rowid()")
        return row_id or 0

    def _complete_transaction_db(
        self,
        txn_id: int,
        dispatched: int,
        blocked: int,
        failed: int,
        results_json: str,
    ) -> None:
        """更新事务完成状态（同步，通过 executor 调用）。"""
        if not txn_id:
            return
        if failed == 0 and blocked == 0:
            status = "success"
        elif dispatched > 0 and failed == 0:
            status = "success"
        elif dispatched > 0 and failed > 0:
            status = "partial"
        elif dispatched == 0 and blocked > 0:
            status = "blocked"
        else:
            status = "failed"
        _ok = self._db.execute(
            "UPDATE action_transactions SET "
            "dispatched_count=?,blocked_count=?,failed_count=?,"
            "status=?,results_json=? WHERE id=?",
            (dispatched, blocked, failed, status, results_json, txn_id),
        )
        if not _ok:
            _LOGGER.warning("[Transaction] Complete failed: txn_id=%s", txn_id)

    def _rollback_transaction_db(self, txn_id: int) -> dict | None:
        """查询事务的预快照数据，用于回滚（同步）。返回 pre_states dict 或 None。"""
        import json as _json
        try:
            rows = self._db.query(
                "SELECT * FROM action_transactions WHERE id=?", (txn_id,),
            )
            if not rows:
                return None
            return rows[0]
        except Exception as e:
            _LOGGER.warning("[Transaction] Rollback query failed: %s", e)
            return None

    def _query_recent_transactions(self, limit: int = 30) -> list[dict]:
        """查询近期事务记录（同步）。"""
        try:
            return self._db.query(
                "SELECT * FROM action_transactions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        except Exception as e:
            _LOGGER.warning("[Transaction] Query failed: %s", e)
            return []

    def _get_entity_room(self, eid: str) -> str:
        """识别实体所属房间：优先 device_info，回退 HA 区域注册表，默认 'unknown'。"""
        # 1. 尝试从已录入的设备信息中获取
        room = self.device_info.get(eid, {}).get("room", "")
        if room:
            return room
            
        # 2. 尝试从 HA 区域注册表中获取 (调用 DevicesMixin 中的辅助方法或手动查找)
        # 如果 self 已经混入了 DevicesMixin，则可以直接调用 _get_entity_area
        if hasattr(self, "_get_entity_area"):
            room = getattr(self, "_get_entity_area")(eid)
            if room:
                return room
        
        return "unknown"

    def _get_device_usage_stats(self, days: int = 7) -> list[dict]:
        """分析最近 days 天内各设备的"开启时长"及"空房间浪费时长" (v4.8.6 增强隔离版)。

        算法优化：
        1. 统一时间格式，支持跨 T/空格 解析。
        2. 实现房间隔离：仅比对同房间传感器的占用状态（支持未录入传感器的自动区域识别）。
        3. 精确计算浪费：浪费时长 = 总开启时长 - 开启且有人的重叠时长。
        4. 补全边界状态：处理统计起点前已开启且持续开启的设备。
        """
        from datetime import datetime as _dt
        from collections import defaultdict
        
        # 1. 准备时间窗口
        _FMT = "%Y-%m-%d %H:%M:%S"
        now_dt = datetime.now()
        now_ts = now_dt.timestamp()
        cutoff_dt = now_dt - timedelta(days=days)
        cutoff = cutoff_dt.strftime(_FMT)
        cutoff_ts = cutoff_dt.timestamp()

        try:
            rows = self._db.query(
                """SELECT entity AS entity_id, state, time FROM events
                   WHERE time >= ?
                     AND (entity LIKE 'light.%'
                          OR entity LIKE 'switch.%'
                          OR entity LIKE 'climate.%'
                          OR entity LIKE 'fan.%')
                   ORDER BY entity, time""",
                (cutoff,),
            )
            prows = self._db.query(
                """SELECT entity AS entity_id, state, time FROM events
                   WHERE time >= ?
                     AND (entity LIKE '%presence%'
                          OR entity LIKE '%occupancy%'
                          OR entity LIKE '%motion%'
                          OR entity LIKE '%person%')
                   ORDER BY entity, time""",
                (cutoff,),
            )
        except Exception as e:
            _LOGGER.warning("[EnergyStats] 数据库查询失败: %s", e)
            return []

        # ── 2. 预处理占用状态 (分房间区间合并) ───────────────────────────────────
        # room -> list of (start_ts, end_ts)
        room_occupancy: dict[str, list[tuple[float, float]]] = defaultdict(list)
        sensor_last_on: dict[str, float] = {}
        
        # 处理历史事件中的占用信息
        for pr in prows:
            eid = pr["entity_id"]
            st = pr["state"]
            room = self._get_entity_room(eid)  # 修正：支持自动区域识别
            try:
                time_str = pr["time"].replace("T", " ")
                ts = _dt.strptime(time_str[:19], _FMT).timestamp()
            except Exception:
                continue
                
            is_occupied = st in ("on", "home", "true", "1")
            if is_occupied and eid not in sensor_last_on:
                sensor_last_on[eid] = ts
            elif not is_occupied and eid in sensor_last_on:
                start_t = sensor_last_on.pop(eid)
                room_occupancy[room].append((start_t, ts))
        
        # 补全边界：处理当前仍为"有人"状态的传感器
        for eid, start_t in sensor_last_on.items():
            room = self._get_entity_room(eid)  # 修正：支持自动区域识别
            room_occupancy[room].append((start_t, now_ts))

        # 算法：对每个房间的占用时间段进行 Union (并集) 合并
        for room in room_occupancy:
            intervals = sorted(room_occupancy[room])
            if not intervals: continue
            merged = []
            curr_s, curr_e = intervals[0]
            for next_s, next_e in intervals[1:]:
                if next_s <= curr_e:
                    curr_e = max(curr_e, next_e)
                else:
                    merged.append((curr_s, curr_e))
                    curr_s, curr_e = next_s, next_e
            merged.append((curr_s, curr_e))
            room_occupancy[room] = merged

        # ── 3. 计算设备开启时长与浪费时长 ────────────────────────────────────────
        stats: dict[str, dict] = {}
        device_last_on: dict[str, float] = {}
        
        # 边界处理：补全起点状态（若当前开启且期间无 on 事件，视为全程开启）
        for eid, info in self.device_info.items():
            if not any(eid.startswith(d + ".") for d in ("light", "switch", "climate", "fan")):
                continue
            st_obj = self.hass.states.get(eid)
            if st_obj and st_obj.state in ("on", "open", "heat", "cool", "auto", "fan_only", "playing"):
                device_last_on[eid] = cutoff_ts

        for r in rows:
            eid = r["entity_id"]
            st = r["state"]
            try:
                time_str = r["time"].replace("T", " ")
                ts = _dt.strptime(time_str[:19], _FMT).timestamp()
            except Exception:
                continue
                
            if eid not in stats:
                stats[eid] = {"entity_id": eid, "on_minutes": 0.0, "waste_minutes": 0.0,
                              "on_count": 0, "last_on": ""}
            
            is_on = st in ("on", "heat", "cool", "auto", "fan_only", "playing")
            was_on = eid in device_last_on
            
            if is_on and not was_on:
                device_last_on[eid] = ts
                stats[eid]["on_count"] += 1
                stats[eid]["last_on"] = r["time"]
            elif not is_on and was_on:
                start_t = device_last_on.pop(eid)
                duration = ts - start_t
                if duration <= 0: continue
                
                stats[eid]["on_minutes"] += duration / 60
                
                # 精确计算有人时长 (Intersection)
                room = self._get_entity_room(eid)  # 修正：支持自动区域识别
                occ_intervals = room_occupancy.get(room, [])
                occupied_duration = 0.0
                for os, oe in occ_intervals:
                    overlap_s = max(start_t, os)
                    overlap_e = min(ts, oe)
                    if overlap_s < overlap_e:
                        occupied_duration += (overlap_e - overlap_s)
                
                waste = max(0.0, duration - occupied_duration)
                stats[eid]["waste_minutes"] += waste / 60

        # 处理结算时刻仍处于开启状态的设备
        for eid, start_t in device_last_on.items():
            if eid not in stats:
                stats[eid] = {"entity_id": eid, "on_minutes": 0.0, "waste_minutes": 0.0,
                              "on_count": 0, "last_on": "N/A"}
            duration = now_ts - start_t
            if duration <= 0: continue
            
            stats[eid]["on_minutes"] += duration / 60
            room = self._get_entity_room(eid)  # 修正：支持自动区域识别
            occ_intervals = room_occupancy.get(room, [])
            occupied_duration = 0.0
            for os, oe in occ_intervals:
                overlap_s = max(start_t, os)
                overlap_e = min(now_ts, oe)
                if overlap_s < overlap_e:
                    occupied_duration += (overlap_e - overlap_s)
            
            waste = max(0.0, duration - occupied_duration)
            stats[eid]["waste_minutes"] += waste / 60

        # 4. 结果整理
        result = []
        for s in stats.values():
            if s["on_minutes"] < 1.0: continue
            s["on_minutes"] = round(s["on_minutes"], 1)
            s["waste_minutes"] = round(s["waste_minutes"], 1)
            result.append(s)
            
        return sorted(result, key=lambda x: x["waste_minutes"], reverse=True)

    # ── 模型训练自标注数据管道 (Training Data Pipeline) ─────────────────────────

    def _is_empty_lights_on_no_action(
        self, context: str, decision: dict
    ) -> bool:
        """
        Phase 11.2: 检测"无人+灯亮+无动作"的死亡螺旋样本。

        当 AI 在无人且灯亮的场景下判断"无需动作"时，该样本不应被记为正向训练样本，
        否则会强化"无人也不关灯"的错误行为。

        Args:
            context: 上下文 JSON 字符串
            decision: AI 决策字典

        Returns:
            True 表示应跳过此样本（不记录为待验证正样本）
        """
        try:
            # 只拦截 actions 为空的"不作为"决策
            if decision.get("actions"):
                return False

            # 检查上下文中是否有无人在场的信号
            ctx_lower = context.lower() if context else ""
            no_one_signals = ["无人", "empty", "nobody", "人员离开", "离开"]
            light_on_signals = ["灯.*开", "light.*on", "亮度", "brightness"]

            has_no_one = any(s in ctx_lower for s in no_one_signals)
            if not has_no_one:
                return False

            # 检查是否有灯处于开启状态（上下文中有"亮"或 light.* = on）
            import re as _re
            has_light_on = any(
                _re.search(s, ctx_lower) for s in light_on_signals
            )
            return has_light_on
        except Exception:
            return False

    def _record_training_sample(
        self,
        trigger: str,
        context: str,
        decision: dict,
        features: dict | None = None,
    ) -> None:
        """
        记录一次 AI 推理作为待验证的训练样本（Phase 11.2 增加写入过滤）。

        过滤规则：若为"无人+灯亮+无动作"场景，跳过记录，避免正向样本强化
        "无人也不关灯"的错误行为（死亡螺旋防护）。

        Args:
            trigger: 触发文本
            context: 上下文 JSON 字符串
            decision: AI 决策字典
            features: FeatureEncoder.encode() 的输出（数值特征快照），用于本地 ML 训练
        """
        try:
            # Phase 11.2: 死亡螺旋防护——无人+灯亮+不作为 不写入正向样本
            if self._is_empty_lights_on_no_action(context, decision):
                _LOGGER.debug(
                    "[TrainingData] 跳过记录：检测到无人+灯亮+无动作场景，"
                    "避免强化错误的不关灯行为"
                )
                return

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            decision_json = json.dumps(decision, ensure_ascii=False)
            feature_json = json.dumps(features, ensure_ascii=False) if features else None
            _ok = self._db.execute(
                "INSERT INTO training_data "
                "(time, trigger_text, context_json, decision_json, feature_json) "
                "VALUES (?,?,?,?,?)",
                (ts, trigger, context, decision_json, feature_json),
            )
            if not _ok:
                _LOGGER.warning("[TrainingData] Record write failed: trigger=%s", trigger[:60])
        except Exception as e:
            _LOGGER.warning("[TrainingData] Record failed: %s", e)

    def _mark_training_negative(self, entity_id: str) -> None:
        """当用户手动修正某设备时，将最近 30 分钟内涉及该设备的 AI 样本标记为负样本(0)。"""
        try:
            # 查找 30 分钟内包含该 entity_id 的 AI 决策
            cutoff = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            _ok = self._db.execute(
                "UPDATE training_data SET label = 0 WHERE time > ? AND decision_json LIKE ?",
                (cutoff, f"%{entity_id}%"),
            )
            if not _ok:
                _LOGGER.warning("[TrainingData] Mark negative write failed: entity=%s", entity_id)
        except Exception as e:
            _LOGGER.warning("[TrainingData] Mark negative failed: %s", e)

    def _verify_training_samples(self) -> int:
        """回查 30-60 分钟前的待验证样本，将其标记为已验证（Verified）。"""
        try:
            # 窗口：30 分钟前到 2 小时前
            now = datetime.now()
            start = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
            end = (now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            ts_now = now.strftime("%Y-%m-%d %H:%M:%S")

            count = self._db.query_scalar(
                "SELECT COUNT(*) FROM training_data "
                "WHERE is_verified = 0 AND time BETWEEN ? AND ?",
                (start, end),
            ) or 0
            _ok = self._db.execute(
                "UPDATE training_data SET is_verified = 1, verified_at = ? "
                "WHERE is_verified = 0 AND time BETWEEN ? AND ?",
                (ts_now, start, end),
            )
            if not _ok:
                _LOGGER.warning("[TrainingData] Verification write failed")
                return 0
            return count
        except Exception as e:
            _LOGGER.warning("[TrainingData] Verification failed: %s", e)
            return 0

    def _cleanup_old_memory(self) -> None:
        """Delete stale events/action_results and expired in-memory caches."""
        from .const import MEMORY_RETENTION_DAYS
        cutoff = (datetime.now() - timedelta(days=MEMORY_RETENTION_DAYS)).strftime("%Y-%m-%d")
        try:
            txn_cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            td_cutoff_verified = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            td_cutoff_unverified = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            _ok = self._db.execute_script([
                ("DELETE FROM events WHERE time < ?", (cutoff,)),
                ("DELETE FROM action_results WHERE time < ?", (cutoff,)),
                ("DELETE FROM action_transactions WHERE time < ?", (txn_cutoff,)),
                ("DELETE FROM training_data WHERE is_verified=1 AND time < ?", (td_cutoff_verified,)),
                ("DELETE FROM training_data WHERE is_verified=0 AND time < ?", (td_cutoff_unverified,)),
                ("DELETE FROM training_data WHERE id NOT IN "
                 "(SELECT id FROM training_data ORDER BY id DESC LIMIT 5000)", ()),
            ])
            if not _ok:
                _LOGGER.warning("[Memory] Cleanup write failed: cutoff=%s", cutoff)
        except Exception as e:
            _LOGGER.warning("[Memory] Cleanup failed: %s", e)
        now_ts = time.time()
        # _last_ai_actions 保留 8 小时供用户纠正，其余字典 1 小时过期
        stale_ai = 8 * 3600
        stale = 3600
        ai_expired = [
            k for k, v in self._last_ai_actions.items()
            if isinstance(v, dict) and now_ts - v.get("time", now_ts) > stale_ai
        ]
        for k in ai_expired:
            self._last_ai_actions.pop(k, None)
        for d in (self._last_notify, self._scene_last_exec, self._habit_suggest_cooldown,
                  self._last_inference,
                  self._presence_last_on, self._presence_on_start,
                  self._presence_flap_suppressed, self._rational_guard_last_retry):
            expired = [k for k, v in d.items() if isinstance(v, (int, float)) and now_ts - v > stale]
            if not expired:
                expired = [k for k, v in d.items() if isinstance(v, dict) and now_ts - v.get("time", now_ts) > stale]
            for k in expired:
                d.pop(k, None)

        flap_expired = [
            k for k, vals in self._presence_flap_history.items()
            if (not vals) or (now_ts - max(vals) > stale)
        ]
        for k in flap_expired:
            self._presence_flap_history.pop(k, None)

    # ── Phase 11.5: Smart Memory Guard 三道防线 ────────────────────────────────

    def _memory_guard_drift_protection(self) -> int:
        """
        防线一：漂移防护。

        扫描 corrections 和 behavior_patterns 表中引用的 entity_id，
        若设备已从 device_info 中注销（删除/改名），将对应记录标记为过期
        （correction_count 清零，让 decay_score 快速降至阈值以下）。

        Returns:
            过期的记录数量
        """
        expired = 0
        known_entities = set(self.device_info.keys())
        if not known_entities:
            return 0
        try:
            # 查询所有 corrections 中不再存在的 entity_id
            all_correction_ids = self._db.query(
                "SELECT id, entity_id FROM corrections WHERE correction_count > 0"
            )
            for row in all_correction_ids:
                if row["entity_id"] not in known_entities:
                    _ok = self._db_exec(
                        "UPDATE corrections SET correction_count = 0 WHERE id = ?",
                        (row["id"],),
                    )
                    if not _ok:
                        _LOGGER.warning(
                            "[MemoryGuard] 漂移防护写入失败: table=corrections id=%s entity=%s",
                            row["id"], row["entity_id"],
                        )
                        continue
                    expired += 1
                    _LOGGER.info(
                        "[MemoryGuard] 漂移防护: corrections 记录 %s 引用的实体 %s 已注销，清零修正计数",
                        row["id"], row["entity_id"],
                    )

            # 同理处理 behavior_patterns
            all_pattern_eids = self._db.query(
                "SELECT DISTINCT entity_id FROM behavior_patterns"
            )
            ghost_eids = [r["entity_id"] for r in all_pattern_eids
                          if r["entity_id"] not in known_entities]
            if ghost_eids:
                for ghost_eid in ghost_eids:
                    _ok = self._db_exec(
                        "UPDATE behavior_patterns SET confidence = 0 WHERE entity_id = ?",
                        (ghost_eid,),
                    )
                    if not _ok:
                        _LOGGER.warning(
                            "[MemoryGuard] 漂移防护写入失败: table=behavior_patterns entity=%s",
                            ghost_eid,
                        )
                        continue
                    expired += 1
                    _LOGGER.info(
                        "[MemoryGuard] 漂移防护: behavior_patterns 实体 %s 已注销，置信度清零",
                        ghost_eid,
                    )
        except Exception as e:
            _LOGGER.warning("[MemoryGuard] 漂移防护执行失败: %s", e)
        return expired

    def _memory_guard_bloat_check(
        self,
        corrections_limit: int = 50,
        patterns_limit: int = 200,
    ) -> dict:
        """
        防线二：膨胀检查。

        当 corrections 或 behavior_patterns 超过阈值时，按优先级截断：
          - corrections: 保留 correction_count >= 3（强修正），其余按最近使用时间排序保留到上限
          - behavior_patterns: 保留 confidence >= 40 的高置信模式，其余按 hit_count 排序截断

        Args:
            corrections_limit:  corrections 表最大保留条数（默认 50）
            patterns_limit:     behavior_patterns 表最大保留条数（默认 200）

        Returns:
            {'corrections_deleted': N, 'patterns_deleted': M}
        """
        result = {"corrections_deleted": 0, "patterns_deleted": 0}
        try:
            # ── corrections 膨胀检查 ──
            corr_count = self._db.query_scalar("SELECT COUNT(*) FROM corrections") or 0
            if corr_count > corrections_limit:
                # 保留所有强修正（count >= 3）以及最近使用的记录，删除其余
                to_delete = corr_count - corrections_limit
                _ok = self._db_exec(
                    "DELETE FROM corrections WHERE id IN ("
                    "  SELECT id FROM corrections "
                    "  WHERE correction_count < 3 "
                    "  ORDER BY time ASC LIMIT ?"
                    ")",
                    (to_delete,),
                )
                if not _ok:
                    _LOGGER.warning(
                        "[MemoryGuard] 膨胀检查写入失败: table=corrections count=%s limit=%s",
                        corr_count,
                        corrections_limit,
                    )
                else:
                    actual_deleted = corr_count - (self._db.query_scalar("SELECT COUNT(*) FROM corrections") or 0)
                    result["corrections_deleted"] = actual_deleted
                    if actual_deleted:
                        self._sys_log("INFO",
                            f"[MemoryGuard] 膨胀检查: corrections 超限({corr_count}>{corrections_limit})，"
                            f"已清理 {actual_deleted} 条弱修正记录"
                        )

            # ── behavior_patterns 膨胀检查 ──
            pat_count = self._db.query_scalar("SELECT COUNT(*) FROM behavior_patterns") or 0
            if pat_count > patterns_limit:
                to_delete = pat_count - patterns_limit
                _ok = self._db_exec(
                    "DELETE FROM behavior_patterns WHERE id IN ("
                    "  SELECT id FROM behavior_patterns "
                    "  WHERE confidence < 40 "
                    "  ORDER BY hit_count ASC, last_updated ASC LIMIT ?"
                    ")",
                    (to_delete,),
                )
                if not _ok:
                    _LOGGER.warning(
                        "[MemoryGuard] 膨胀检查写入失败: table=behavior_patterns count=%s limit=%s",
                        pat_count,
                        patterns_limit,
                    )
                else:
                    actual_deleted = pat_count - (self._db.query_scalar("SELECT COUNT(*) FROM behavior_patterns") or 0)
                    result["patterns_deleted"] = actual_deleted
                    if actual_deleted:
                        self._sys_log("INFO",
                            f"[MemoryGuard] 膨胀检查: behavior_patterns 超限({pat_count}>{patterns_limit})，"
                            f"已清理 {actual_deleted} 条低置信规律"
                        )
        except Exception as e:
            _LOGGER.warning("[MemoryGuard] 膨胀检查失败: %s", e)
        return result

    def _memory_guard_write_filter(
        self,
        entity_id: str,
        ai_service: str,
        user_state: str,
        room: str,
        presence_ctx: str,
    ) -> tuple[bool, str]:
        """
        防线三：写入过滤（供 _record_correction 调用前预检）。

        检查新增修正是否应跳过：
          1. 重复过滤：同一 entity_id + ai_service + presence_context 已有记录（仅需累加计数，无需外部重复调用）
          2. 时效过滤：季节性修正（如"冬天不开空调"）——上次记录与当前相差超过 4 个月
             且 correction_count < 3，则视为过期弱修正，返回跳过建议

        Args:
            entity_id:    设备 ID
            ai_service:   服务名（"turn_on" 等）
            user_state:   用户期望状态
            room:         房间
            presence_ctx: 当前在场状态

        Returns:
            (should_skip, reason): should_skip=True 时建议跳过本次写入
        """
        try:
            rows = self._db.query(
                "SELECT id, correction_count, time FROM corrections "
                "WHERE entity_id = ? AND ai_service = ? AND presence_context = ?",
                (entity_id, ai_service, presence_ctx),
            )
            if rows:
                # 已有记录：外层 _record_correction 会自动累加，此处直接放行
                return False, "已有记录，累加计数"

            # 季节性过滤：检查是否存在同方向但跨越 4 个月以上的旧记录
            old_rows = self._db.query(
                "SELECT time, correction_count FROM corrections "
                "WHERE entity_id = ? AND ai_service = ? "
                "AND correction_count < 3 "
                "ORDER BY time DESC LIMIT 1",
                (entity_id, ai_service),
            )
            if old_rows:
                from datetime import datetime as _dt
                try:
                    old_time = _dt.strptime(old_rows[0]["time"], "%Y-%m-%d %H:%M:%S")
                    months_diff = (datetime.now() - old_time).days / 30
                    if months_diff >= 4:
                        _LOGGER.debug(
                            "[MemoryGuard] 季节性过滤: %s/%s 旧记录已超 4 个月(%.1f月)且次数<3，视为过期",
                            entity_id, ai_service, months_diff,
                        )
                        # 删除过期弱修正，让新修正重新从计数 1 开始（新一轮学习）
                        _ok = self._db_exec(
                            "DELETE FROM corrections WHERE entity_id = ? AND ai_service = ? AND correction_count < 3",
                            (entity_id, ai_service),
                        )
                        if not _ok:
                            _LOGGER.warning(
                                "[MemoryGuard] 季节性过期清理写入失败: entity=%s service=%s",
                                entity_id,
                                ai_service,
                            )
                            return False, "过期修正清理失败，跳过写入过滤"
                        return False, "过期修正已清理，允许重新记录"
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            _LOGGER.debug("[MemoryGuard] 写入过滤检查失败: %s", e)
        return False, "通过"

    def _run_smart_memory_guard(self) -> dict:
        """
        执行 Smart Memory Guard 完整三道防线（统一入口，供巡检定期调用）。

        Returns:
            包含各防线执行结果的摘要字典
        """
        result: dict = {}
        drifted = self._memory_guard_drift_protection()
        if drifted:
            result["drifted"] = drifted

        bloat = self._memory_guard_bloat_check()
        result.update(bloat)

        if any(v > 0 for v in result.values()):
            self._sys_log("INFO",
                f"[MemoryGuard] 三道防线执行完毕: 漂移={drifted} "
                f"corrections清理={bloat.get('corrections_deleted', 0)} "
                f"patterns清理={bloat.get('patterns_deleted', 0)}"
            )
        return result

    # ── Phase 7C: 记忆衰减维护（每日/每周执行）────────────────────────────────

    def _run_memory_decay_maintenance(self) -> dict:
        """
        认知记忆衰减维护：清理过时记忆、降级行为模式置信度、提升高权重修正为规则。

        执行逻辑：
          1. 更新 corrections 表的 decay_score 字段
          2. 删除 decay_score < 0.05 且 correction_count <= 1 的弱记忆
          3. 将 decay_score >= 0.6 且 correction_count >= 3 的强修正自动提升为 P1 规则
          4. 对 behavior_patterns 中长期未命中的模式进行置信度衰减
          5. 删除置信度低于 20 且超过 60 天未更新的过时行为模式

        Returns:
            dict: 维护统计报告
        """
        report = {
            "corrections_updated": 0,
            "corrections_pruned": 0,
            "patterns_decayed": 0,
            "patterns_pruned": 0,
        }
        try:
            # ── 1. 更新所有 corrections 的 decay_score（批量，避免 N 次独立事务）──
            all_corr = self._db.query(
                "SELECT id, time, correction_count FROM corrections"
            )
            if all_corr:
                decay_updates = [
                    (
                        self._compute_memory_decay_score(row["time"], row["correction_count"]),
                        row["id"],
                    )
                    for row in all_corr
                ]
                _ok = self._db.execute_many(
                    "UPDATE corrections SET decay_score = ? WHERE id = ?",
                    decay_updates,
                )
                if not _ok:
                    _LOGGER.warning("[MemoryDecay] decay_score 批量更新失败: count=%s", len(decay_updates))
                    return report
                report["corrections_updated"] = len(decay_updates)

            # ── 2. 清除遗忘的弱修正（得分极低 + 仅修正 1 次）───────────
            stale_ids = self._db.query(
                "SELECT id FROM corrections WHERE decay_score < 0.05 AND correction_count <= 1"
            )
            if stale_ids:
                ids = [r["id"] for r in stale_ids]
                _ok = self._db_exec(
                    f"DELETE FROM corrections WHERE id IN ({','.join('?' * len(ids))})",
                    tuple(ids),
                )
                if not _ok:
                    _LOGGER.warning("[MemoryDecay] 弱修正清理失败: ids=%s", len(ids))
                    return report
                report["corrections_pruned"] = len(ids)

            # ── 3. 修正记忆自然衰减日志（无规则生成，仅记录状态供分析）────────
            # 抑制逻辑已移至 _should_suppress_action，由 IntentVerifier 实时查询
            # 此处调用 _should_suppress_action 获取真实抑制状态，避免日志误导
            strong_corr = self._db.query(
                "SELECT entity_id, ai_service, hour, correction_count, decay_score "
                "FROM corrections WHERE correction_count >= 1 AND decay_score >= 0.15"
            )
            for r in strong_corr:
                name = self.get_device_name(r["entity_id"]) if hasattr(self, "get_device_name") else r["entity_id"]
                # 实际调用抑制检查，反映真实状态（剥离域名前缀后查询）
                svc_bare = r["ai_service"].split(".", 1)[-1] if "." in r["ai_service"] else r["ai_service"]
                is_suppressed, _, real_score = self._should_suppress_action(r["entity_id"], svc_bare)
                status = "⛔ 执行层抑制生效" if is_suppressed else "⚠️ 未达抑制阈值（计数不足或已衰减）"
                self._sys_log(
                    "INFO",
                    f"[修正记忆] {name} 在{r['hour']}时 {r['ai_service']}"
                    f" 修正{r['correction_count']}次 权重={real_score:.2f} → {status}",
                )

            # ── 4. 行为模式置信度衰减 ────────────────────────────────────
            decay_cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
            stale_patterns = self._db.query(
                "SELECT id, confidence, entity_id FROM behavior_patterns "
                "WHERE confidence > 20 AND (last_reinforced < ? OR last_reinforced = '' OR last_reinforced IS NULL)",
                (decay_cutoff,),
            )
            for pat in stale_patterns:
                new_conf = max(20, int(pat["confidence"] * 0.85))
                _ok = self._db_exec(
                    "UPDATE behavior_patterns SET confidence = ? WHERE id = ?",
                    (new_conf, pat["id"]),
                )
                if not _ok:
                    _LOGGER.warning(
                        "[MemoryDecay] pattern decay write failed: id=%s entity=%s",
                        pat["id"],
                        pat["entity_id"],
                    )
                    continue
                report["patterns_decayed"] += 1

            # ── 5. 删除过时的弱行为模式 ─────────────────────────────────
            prune_cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
            pruned_count = self._db.query_scalar(
                "SELECT COUNT(*) FROM behavior_patterns WHERE confidence <= 20 "
                "AND last_updated < ?",
                (prune_cutoff,),
            ) or 0
            _ok = self._db_exec(
                "DELETE FROM behavior_patterns WHERE confidence <= 20 "
                "AND last_updated < ?",
                (prune_cutoff,),
            )
            if not _ok:
                _LOGGER.warning("[MemoryDecay] stale pattern prune failed: cutoff=%s", prune_cutoff)
                return report
            report["patterns_pruned"] = pruned_count

            # ── 6. 展厅灯光分层学习 ──────────────────────────────────────
            showroom_report = self._recalculate_showroom_tiers()
            report["showroom_tiers"] = showroom_report

        except Exception as e:
            _LOGGER.warning("[MemoryDecay] Maintenance failed: %s", e)

        # 修正抑制已移至 _should_suppress_action 实时判断，无需重载配置

        # Phase 1 (DecisionCache): 每日清理过期缓存条目
        try:
            self._cleanup_decision_cache()
        except Exception as exc:
            _LOGGER.warning("[DecisionCache] Cleanup failed: %s", exc)

        # Phase 9.4 (Reflexion): 每周运行一次聚合（由日期判断，周一触发）
        if datetime.now().weekday() == 0:
            try:
                self._aggregate_corrections_weekly()
            except Exception as exc:
                _LOGGER.warning("[Reflexion] Weekly aggregation failed: %s", exc)

        # Phase 3 Lite: 每日刷新自然语言行为戒律（从 corrections 蒸馏）
        try:
            n = self._refresh_correction_lessons()
            _LOGGER.info("[Lessons] 行为戒律刷新完成，共 %d 条", n)
        except Exception as exc:
            _LOGGER.warning("[Lessons] _refresh_correction_lessons 失败: %s", exc)

        return report

    # ── Phase 9.4: Reflexion 闭环聚合 ─────────────────────────────────────────

    def _aggregate_corrections_weekly(self) -> None:
        """
        Phase 9.4 (Reflexion): 每周聚合 corrections 表，生成失败模式摘要。

        执行逻辑：
          1. 统计最近 30 天高频失败操作（correction_count >= 2）
          2. 将 Top-5 失败模式写入 reflexion_patterns 表（表已在 _init_db 中统一创建）
          3. 这些 anti-patterns 将通过 _get_reflexion_antipatterns_for_prompt() 注入 User Prompt
        """
        try:
            cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            top_failures = self._db.query(
                "SELECT entity_id, ai_service, ai_state, user_state, hour, room, "
                "correction_count, scene_desc "
                "FROM corrections "
                "WHERE time >= ? AND correction_count >= 2 "
                "ORDER BY correction_count DESC LIMIT 10",
                (cutoff,),
            )

            if not top_failures:
                return

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stmts: list[tuple[str, tuple]] = [("DELETE FROM reflexion_patterns", ())]
            inserted = 0
            for r in top_failures[:5]:
                name = self.get_device_name(r["entity_id"]) if hasattr(self, "get_device_name") else r["entity_id"]
                summary = (
                    f"在 {r['hour']}:00 左右的「{r['room'] or '未知区域'}」，"
                    f"AI 对 {name} 执行 {r['ai_service']}（预期→{r['ai_state']}）"
                    f"但用户将其改为 {r['user_state']}，已发生 {r['correction_count']} 次。"
                    f"场景特征：{(r['scene_desc'] or '')[:50]}"
                )
                stmts.append((
                    "INSERT INTO reflexion_patterns "
                    "(entity_id, ai_service, hour, correction_count, failure_summary, updated) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (r["entity_id"], r["ai_service"], r["hour"], r["correction_count"], summary, now_str),
                ))
                inserted += 1
            _ok = self._db.execute_script(stmts)
            if not _ok:
                _LOGGER.warning("[Reflexion] 周聚合写入失败: statements=%s", len(stmts))
                return
            _LOGGER.info("[Reflexion] 周聚合完成，写入 %d 条 anti-pattern", inserted)

        except Exception as e:
            _LOGGER.warning("[Reflexion] _aggregate_corrections_weekly failed: %s", e)

    # ── Phase 3 Lite: Correction Lessons — 自然语言行为戒律 ──────────────────────

    def _refresh_correction_lessons(self) -> int:
        """Phase 3 Lite：从 corrections 表蒸馏自然语言行为戒律，写入 correction_lessons。

        执行逻辑：
          1. 聚合 corrections，找出每个 (entity_id, presence_context, ai_service) 三元组
             的累计修正次数（correction_count >= 2 才有统计意义）
          2. 检测冲突：同一 (entity_id, presence_context) 下有超过 1 种 ai_service 方向
          3. 按模板生成自然语言教训，冲突修正生成警告类文本
          4. Upsert 到 correction_lessons 表（保留首次创建时间）

        :return: 成功写入/更新的 lesson 数量
        """
        try:
            rows = self._db.query(
                """
                SELECT entity_id,
                       MAX(room)       AS room,
                       ai_service,
                       MAX(user_state) AS user_state,
                       COALESCE(presence_context, 'any') AS presence_context,
                       SUM(correction_count) AS total_count
                FROM corrections
                GROUP BY entity_id,
                         COALESCE(presence_context, 'any'),
                         ai_service
                HAVING total_count >= 2
                ORDER BY total_count DESC
                LIMIT 60
                """,
                (),
            )
        except Exception as exc:
            _LOGGER.warning("[Lessons] 查询 corrections 失败: %s", exc)
            return 0

        if not rows:
            return 0

        # 检测冲突：同一 (entity_id, presence_context) 有多种 ai_service
        seen_services: dict[tuple, set] = {}
        for r in rows:
            key = (r["entity_id"], r["presence_context"])
            seen_services.setdefault(key, set()).add(r["ai_service"])
        conflict_keys: set[tuple] = {
            k for k, svcs in seen_services.items() if len(svcs) > 1
        }

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated = 0
        for r in rows:
            eid      = r["entity_id"]
            room     = r["room"] or "未知区域"
            svc      = r["ai_service"]
            u_state  = r["user_state"]
            presence = r["presence_context"]
            count    = r["total_count"]

            name = self.get_device_name(eid) if hasattr(self, "get_device_name") else eid
            svc_lbl      = _LESSON_SVC_LABEL.get(svc, svc)
            state_lbl    = _LESSON_STATE_LABEL.get(u_state, u_state)
            presence_lbl = _LESSON_PRESENCE_LABEL.get(presence, "")
            is_conflicted = 1 if (eid, presence) in conflict_keys else 0

            if is_conflicted:
                lesson_text = (
                    f"[冲突⚠️] {room}{presence_lbl}：「{name}」存在互相矛盾的修正记录"
                    f"（AI 曾尝试{svc_lbl}，但也有方向相反的修正），"
                    f"修正方向不一致，AI 应根据当前具体场景判断，不要机械依赖修正历史。"
                )
            else:
                # Phase 11.8: 戒律措辞修正——从"主动执行"改为"避免反向操作"。
                # Phase 11.9: 对"无人时AI关灯→用户开灯"的空房间修正生成参考提示而非硬性戒律，
                # 避免该场景永久禁止 AI 执行节能关灯。
                avoid_svc_lbl = "关灯" if svc_lbl == "关" else "开灯"
                if presence == "empty" and svc == "turn_off" and u_state == "on":
                    # 无人关灯被翻转：可能是重启恢复/展示需求/短暂路过，不生成强制戒律
                    lesson_text = (
                        f"[参考] {room}[无人时]：AI 曾尝试关「{name}」后被手动开回（共 {count} 次）。"
                        f"该区域可能存在展示/保持照明需求，但若当前确认无人且无展示需求，"
                        f"AI 仍可根据实际情况关灯；如有常亮需求，请在展厅模式/习惯中明确设置。"
                    )
                else:
                    lesson_text = (
                        f"[戒律] {room}{presence_lbl}：每当 AI 尝试{svc_lbl}「{name}」，"
                        f"用户会将其改为{state_lbl}（共 {count} 次）。"
                        f"今后{presence_lbl}请【避免主动{avoid_svc_lbl}】「{name}」，"
                        f"但若用户/场景明确需要，可以保持或配合执行。"
                    )

            confidence = round(min(count / 5.0, 1.0), 3)
            try:
                _ok = self._db_exec(
                    """
                    INSERT INTO correction_lessons
                        (entity_id, room, presence_context, lesson_text,
                         ai_service, user_state, correction_count,
                         confidence, is_conflicted, created, updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entity_id, presence_context, ai_service) DO UPDATE SET
                        lesson_text      = excluded.lesson_text,
                        room             = excluded.room,
                        user_state       = excluded.user_state,
                        correction_count = excluded.correction_count,
                        confidence       = excluded.confidence,
                        is_conflicted    = excluded.is_conflicted,
                        updated          = excluded.updated
                    """,
                    (eid, room, presence, lesson_text, svc, u_state,
                     count, confidence, is_conflicted, now_str, now_str),
                )
                if not _ok:
                    _LOGGER.debug("[Lessons] upsert 写入失败 eid=%s", eid)
                    continue
                updated += 1
            except Exception as exc:
                _LOGGER.debug("[Lessons] upsert 失败 eid=%s: %s", eid, exc)

        return updated

    def _startup_lessons_refresh(self) -> None:
        """Phase 11.9: 启动时立即刷新行为戒律。

        清除含旧版 "今后请直接" 措辞的 correction_lessons，强制用最新版本重新生成。
        确保 v4.11.28 的措辞修正（"避免主动关灯"）立刻生效，无需等待凌晨3点。
        """
        try:
            old_count = self._db.query(
                "SELECT COUNT(*) AS n FROM correction_lessons WHERE lesson_text LIKE '%今后请直接%'",
                (),
            )
            n_old = old_count[0]["n"] if old_count else 0
            deleted_old = 0
            if n_old > 0:
                _ok = self._db_exec(
                    "DELETE FROM correction_lessons WHERE lesson_text LIKE '%今后请直接%'",
                    (),
                )
                if not _ok:
                    _LOGGER.warning("[Lessons] 旧格式戒律清理失败: count=%d", n_old)
                else:
                    deleted_old = n_old
                    _LOGGER.info("[Lessons] 清除 %d 条旧格式戒律（含'今后请直接'）", n_old)
            n_new = self._refresh_correction_lessons()
            _LOGGER.info("[Lessons] 启动刷新完成：清除旧格式=%d，写入新格式=%d", deleted_old, n_new)
        except Exception as exc:
            _LOGGER.warning("[Lessons] 启动刷新失败: %s", exc)

    # ── Phase 1: DecisionCache — AI 决策缓存 ────────────────────────────────────

    def _write_decision_cache(
        self,
        trigger_room: str,
        hour_bucket: int,
        weekday: int,
        trigger_type: str,
        actions: list,
        confidence: int,
        scene: str,
        intent: str = "",
        scene_candidate: str = "",
    ) -> None:
        """将 LLM 推理后的经验证动作写入缓存，供快路径直接复用。

        缓存以 (trigger_room, hour_bucket, weekday, trigger_type) 为唯一键，
        同一场景重复推理时直接覆盖更新，始终保留最新决策。

        :param trigger_room:    触发房间名称
        :param hour_bucket:     当前小时 (0-23)
        :param weekday:         星期 (0=周一, 6=周日)
        :param trigger_type:    触发类型（'arrival' / 'departure' / 'other'）
        :param actions:         经 IntentVerifier 验证后的动作列表
        :param confidence:      AI 决策置信度
        :param scene:           场景描述
        :param intent:          5B-3: AI 意图标识（如 'arrival_lighting'）
        :param scene_candidate: 5B-3: AI 推荐的 HA 场景 entity_id
        """
        import json as _json
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            actions_json = _json.dumps(actions, ensure_ascii=False)
            _ok = self._db_exec(
                """
                INSERT INTO decision_cache
                    (trigger_room, hour_bucket, weekday, trigger_type,
                     actions_json, confidence, scene, intent, scene_candidate,
                     hit_count, created, last_hit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(trigger_room, hour_bucket, weekday, trigger_type) DO UPDATE SET
                    actions_json    = excluded.actions_json,
                    confidence      = excluded.confidence,
                    scene           = excluded.scene,
                    intent          = excluded.intent,
                    scene_candidate = excluded.scene_candidate,
                    last_hit        = excluded.last_hit
                """,
                # created 字段刻意不在 UPDATE SET 中，以保留首次写入时间
                (trigger_room, hour_bucket, weekday, trigger_type,
                 actions_json, confidence, scene, intent, scene_candidate,
                 now_str, now_str),
            )
            if not _ok:
                _LOGGER.warning(
                    "[DecisionCache] 写入失败: room=%s h=%d wd=%d type=%s",
                    trigger_room,
                    hour_bucket,
                    weekday,
                    trigger_type,
                )
                return
            _LOGGER.debug(
                "[DecisionCache] 写入: room=%s h=%d wd=%d type=%s acts=%d conf=%d",
                trigger_room, hour_bucket, weekday, trigger_type, len(actions), confidence,
            )
        except Exception as exc:
            _LOGGER.warning("[DecisionCache] 写入失败: %s", exc)

    def _lookup_decision_cache(
        self,
        trigger_room: str,
        hour_bucket: int,
        weekday: int,
        trigger_type: str,
    ) -> dict | None:
        """从缓存查询 LLM 历史决策，支持 ±1 小时容差。

        优先精确匹配当前小时，无精确命中时扩展到相邻时段；
        同时更新命中计数用于缓存热度排序与统计。

        Returns:
            dict with keys: actions, confidence, scene, intent, scene_candidate
            None if no match or query error
        """
        import json as _json
        try:
            buckets = [(hour_bucket - 1) % 24, hour_bucket, (hour_bucket + 1) % 24]
            placeholders = ",".join("?" * len(buckets))
            rows = self._db.query(
                f"""
                SELECT actions_json, confidence, scene, hit_count, hour_bucket,
                       COALESCE(intent, '') AS intent,
                       COALESCE(scene_candidate, '') AS scene_candidate
                FROM decision_cache
                WHERE trigger_room = ?
                  AND weekday = ?
                  AND trigger_type = ?
                  AND hour_bucket IN ({placeholders})
                ORDER BY
                  CASE WHEN hour_bucket = ? THEN 0 ELSE 1 END,
                  hit_count DESC
                LIMIT 1
                """,
                (trigger_room, weekday, trigger_type, *buckets, hour_bucket),
            )
            if not rows:
                return None

            row = rows[0]
            actions = _json.loads(row["actions_json"])
            if not actions:
                return None

            # 仅更新实际命中的那一行（精确匹配 hour_bucket），而非 ±1h 范围内所有行
            matched_hour = row["hour_bucket"]
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _ok = self._db_exec(
                """
                UPDATE decision_cache
                SET hit_count = hit_count + 1, last_hit = ?
                WHERE trigger_room = ? AND weekday = ? AND trigger_type = ?
                  AND hour_bucket = ?
                """,
                (now_str, trigger_room, weekday, trigger_type, matched_hour),
            )
            if not _ok:
                _LOGGER.warning(
                    "[DecisionCache] 命中计数更新失败: room=%s wd=%s type=%s hour=%s",
                    trigger_room,
                    weekday,
                    trigger_type,
                    matched_hour,
                )
            _LOGGER.debug(
                "[DecisionCache] 命中: room=%s h=%d→cached_h=%d type=%s acts=%d hits=%d intent=%s",
                trigger_room, hour_bucket, matched_hour,
                trigger_type, len(actions), row["hit_count"] + 1, row["intent"],
            )
            return {
                "actions": actions,
                "confidence": row["confidence"],
                "scene": row["scene"],
                "intent": row["intent"],
                "scene_candidate": row["scene_candidate"],
            }
        except Exception as exc:
            _LOGGER.warning("[DecisionCache] 查询失败: %s", exc)
            return None

    def _invalidate_decision_cache_for_room(self, room: str) -> None:
        """用户纠正后清除该房间所有缓存条目，强制下次走 LLM 重新决策。

        在 `_record_correction` 中自动调用，确保错误决策不被复用。

        :param room: 触发修正的房间名称
        """
        try:
            _ok = self._db_exec(
                "DELETE FROM decision_cache WHERE trigger_room = ?",
                (room,),
            )
            if not _ok:
                _LOGGER.warning("[DecisionCache] 缓存清除写入失败 room=%s", room)
                return
            _LOGGER.debug("[DecisionCache] 已清除 room=%s 的所有缓存", room)
        except Exception as exc:
            _LOGGER.warning("[DecisionCache] 缓存清除失败 room=%s: %s", room, exc)

    def _cleanup_decision_cache(self) -> None:
        """清理冷门（< 3次命中）且超过 48 小时未访问的缓存条目。

        在每日维护 `_run_memory_decay_maintenance` 中调用。
        保留命中率高的热门缓存，避免频繁让 LLM 重新推理。
        """
        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
            _ok = self._db_exec(
                "DELETE FROM decision_cache WHERE last_hit < ? AND hit_count < 3",
                (cutoff,),
            )
            if not _ok:
                _LOGGER.warning("[DecisionCache] 过期缓存清理写入失败: cutoff=%s", cutoff)
                return
            _LOGGER.debug("[DecisionCache] 过期冷门缓存清理完成（cutoff=%s）", cutoff)
        except Exception as exc:
            _LOGGER.warning("[DecisionCache] 缓存清理失败: %s", exc)

    def _get_decision_cache_stats(self) -> dict:
        """返回缓存统计信息（供日志/面板展示）。

        :return: {'total': int, 'rooms': int, 'avg_hits': float}
        """
        try:
            rows = self._db.query(
                "SELECT COUNT(*) as total, COUNT(DISTINCT trigger_room) as rooms, "
                "AVG(hit_count) as avg_hits FROM decision_cache"
            )
            if rows:
                r = rows[0]
                return {
                    "total": r["total"] or 0,
                    "rooms": r["rooms"] or 0,
                    "avg_hits": round(r["avg_hits"] or 0.0, 2),
                }
        except Exception:
            pass
        return {"total": 0, "rooms": 0, "avg_hits": 0.0}

    def _get_reflexion_antipatterns_for_prompt(self) -> str:
        """
        Phase 9.4 (Reflexion): 获取 Top-5 失败模式，用于注入 System Prompt 作为反面教材。

        Returns:
            格式化的字符串，或空字符串（无记录时）
        """
        try:
            rows = self._db.query(
                "SELECT failure_summary, correction_count FROM reflexion_patterns "
                "ORDER BY correction_count DESC LIMIT 5"
            )
            if not rows:
                return ""
            lines = ["【🚫 Reflexion 反面教材 — 以下是 AI 曾经反复犯过的错误，绝对不要重蹈覆辙】"]
            for r in rows:
                lines.append(f"  ✗ [{r['correction_count']}次] {r['failure_summary']}")
            return "\n".join(lines)
        except Exception:
            return ""
