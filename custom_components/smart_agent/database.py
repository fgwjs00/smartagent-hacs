"""Thin SQLite bridge helpers for the Home Assistant integration."""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any

from .db_service import DatabaseService

_LOGGER = logging.getLogger(__name__)

_VALID_MIGRATION_TABLES = frozenset({"events", "devices", "habits", "rules", "action_results", "ai_scenes", "action_transactions", "room_topology"})

_BRIDGE_SCHEMA: tuple[tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]], ...] = (
    ("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, type TEXT NOT NULL, detail TEXT, entity TEXT, state TEXT, source TEXT DEFAULT 'system', area TEXT, confidence INTEGER, transaction_id INTEGER DEFAULT 0, action_seq INTEGER DEFAULT 0)", ("CREATE INDEX IF NOT EXISTS idx_events_time ON events(time)", "CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)", "CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity)"), (("events", "transaction_id INTEGER DEFAULT 0"), ("events", "action_seq INTEGER DEFAULT 0"))),
    ("CREATE TABLE IF NOT EXISTS devices (entity_id TEXT PRIMARY KEY, name TEXT NOT NULL, area TEXT DEFAULT '', type TEXT DEFAULT '', ops TEXT DEFAULT '', control_mode TEXT DEFAULT 'shared', sensor_type TEXT DEFAULT '', created TEXT, updated TEXT)", (), (("devices", "control_mode TEXT DEFAULT 'shared'"), ("devices", "sensor_type TEXT DEFAULT ''"))),
    ("CREATE TABLE IF NOT EXISTS habits (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, locked INTEGER DEFAULT 0, created TEXT)", (), (("habits", "locked INTEGER DEFAULT 0"),)),
    ("CREATE TABLE IF NOT EXISTS rules (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, locked INTEGER DEFAULT 0, created TEXT)", (), (("rules", "locked INTEGER DEFAULT 0"),)),
    ("CREATE TABLE IF NOT EXISTS action_results (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, entity_id TEXT NOT NULL, domain TEXT NOT NULL, service TEXT NOT NULL, expected_state TEXT, actual_state TEXT, verified INTEGER DEFAULT 0, success INTEGER DEFAULT 0, retry_count INTEGER DEFAULT 0, latency_ms INTEGER DEFAULT 0, reason TEXT DEFAULT '', transaction_id INTEGER DEFAULT 0, action_seq INTEGER DEFAULT 0)", ("CREATE INDEX IF NOT EXISTS idx_ar_time ON action_results(time)", "CREATE INDEX IF NOT EXISTS idx_ar_entity ON action_results(entity_id)"), (("action_results", "transaction_id INTEGER DEFAULT 0"), ("action_results", "action_seq INTEGER DEFAULT 0"))),
    ("CREATE TABLE IF NOT EXISTS ai_scenes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT DEFAULT '', entities_json TEXT NOT NULL, trigger_context TEXT DEFAULT '', hour_start INTEGER DEFAULT 0, hour_end INTEGER DEFAULT 23, weekday_mask TEXT DEFAULT '0123456', confidence INTEGER DEFAULT 80, hit_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', source TEXT DEFAULT 'auto', created TEXT, updated TEXT, ha_entity_id TEXT DEFAULT '', actions_json TEXT DEFAULT '[]')", ("CREATE INDEX IF NOT EXISTS idx_ai_scenes_status ON ai_scenes(status)",), (("ai_scenes", "ha_entity_id TEXT DEFAULT ''"), ("ai_scenes", "actions_json TEXT DEFAULT '[]'"))),
    ("CREATE TABLE IF NOT EXISTS action_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, trigger_summary TEXT DEFAULT '', scene_desc TEXT DEFAULT '', confidence INTEGER DEFAULT 0, action_count INTEGER DEFAULT 0, dispatched_count INTEGER DEFAULT 0, blocked_count INTEGER DEFAULT 0, failed_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', pre_states_json TEXT DEFAULT '{}', actions_json TEXT DEFAULT '[]', results_json TEXT DEFAULT '[]')", ("CREATE INDEX IF NOT EXISTS idx_txn_time ON action_transactions(time)",), ()),
    ("CREATE TABLE IF NOT EXISTS room_topology (id INTEGER PRIMARY KEY AUTOINCREMENT, room_a TEXT NOT NULL, room_b TEXT NOT NULL, relation TEXT DEFAULT 'adjacent', updated_at TEXT DEFAULT '', UNIQUE(room_a, room_b))", (), ()),
)


def _safe_add_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    table_name = (table or "").strip()
    col_def = (column_def or "").strip()

    if table_name not in _VALID_MIGRATION_TABLES:
        raise ValueError(f"invalid migration table: {table_name}")
    if not col_def:
        raise ValueError("invalid empty column definition")
    upper_col_def = col_def.upper()
    if ";" in col_def or "--" in col_def or "/*" in col_def or "DROP TABLE" in upper_col_def:
        raise ValueError(f"invalid column definition: {col_def}")

    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_def}")
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            _LOGGER.error("[DB] migration failed: ALTER TABLE %s ADD COLUMN %s: %s", table_name, col_def, exc)
            raise


class DatabaseMixin:
    _VALID_CONTROL_MODES = frozenset({"ai", "ha", "shared"})

    def _init_memory_db(self) -> None:
        try:
            self._db = DatabaseService(self._memory_db)
            self._db.open()
            conn = self._db.get_raw_connection()
            for create_sql, indexes, columns in _BRIDGE_SCHEMA:
                conn.execute(create_sql)
                for index_sql in indexes:
                    conn.execute(index_sql)
                for table, column_def in columns:
                    _safe_add_column(conn, table, column_def)
        except Exception as exc:
            _LOGGER.error("[DB] initialization failed: %s", exc)
            if hasattr(self, "_sys_log"):
                self._sys_log("ERROR", f"Database initialization failed: {exc}")
            return

        if hasattr(self, "_sys_log"):
            self._sys_log("INFO", f"Database initialized: {self._memory_db}")
        self._migrate_json_config()

    def _migrate_json_config(self) -> None:
        """Migrate the old JSON configuration file into the bridge config tables."""
        try:
            conn = self._db.get_raw_connection()
            if conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] > 0:
                return
        except Exception as exc:
            _LOGGER.warning("[DB] JSON migration skipped: %s", exc)
            return

        json_path = os.path.join(self._config_dir, "smart_agent_config.json")
        if not os.path.exists(json_path):
            return

        try:
            with open(json_path, "r", encoding="utf-8") as file:
                cfg = json.load(file)
            os.rename(json_path, json_path + ".migrated")
        except Exception as exc:
            _LOGGER.debug("[DB] legacy JSON read failed: %s", exc)
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            for eid, desc in cfg.get("devices", {}).items():
                parts = [part.strip() for part in str(desc).split("|")]
                conn.execute(
                    "INSERT OR IGNORE INTO devices "
                    "(entity_id, name, area, type, ops, created, updated) VALUES (?,?,?,?,?,?,?)",
                    (
                        eid,
                        parts[0] if parts else eid,
                        parts[1] if len(parts) > 1 else "",
                        parts[2] if len(parts) > 2 else "",
                        parts[3] if len(parts) > 3 else "",
                        now,
                        now,
                    ),
                )
            for habit in cfg.get("habits", []):
                conn.execute("INSERT INTO habits (content, created) VALUES (?,?)", (habit, now))
            for rule in cfg.get("rules", []):
                conn.execute("INSERT INTO rules (content, created) VALUES (?,?)", (rule, now))
        except Exception as exc:
            _LOGGER.warning("[DB] legacy JSON migration failed: %s", exc)
    def _load_config(self) -> None:
        """Load devices, habits, and rules from local HA bridge config tables."""
        self.device_info = {}
        try:
            conn = self._db.get_raw_connection()
            for row in conn.execute("SELECT * FROM devices"):
                columns = row.keys()
                mode = row["control_mode"] if "control_mode" in columns else "shared"
                if mode not in self._VALID_CONTROL_MODES:
                    mode = "shared"
                sensor_type = row["sensor_type"] if "sensor_type" in columns else ""
                self.device_info[row["entity_id"]] = {
                    "name": row["name"],
                    "room": row["area"],
                    "type": row["type"],
                    "ops": row["ops"],
                    "control_mode": mode,
                    "sensor_type": sensor_type,
                }
            self._habits = [
                (row["content"], bool(row["locked"]))
                for row in conn.execute("SELECT content, locked FROM habits ORDER BY id")
            ]
            self._rules = [
                (row["content"], bool(row["locked"]))
                for row in conn.execute("SELECT content, locked FROM rules ORDER BY id")
            ]
        except Exception as exc:
            _LOGGER.warning("[DB] load config failed: %s", exc)
            self._habits = []
            self._rules = []

    def _db_exec(self, sql: str, params: tuple = ()) -> bool:
        """Execute a permitted HA-local write."""
        if self._p1_blocks_local_write(sql):
            return False
        return bool(self._db.execute(sql, params))

    async def _async_db_exec(self, sql: str, params: tuple = ()) -> bool:
        """Async wrapper for permitted HA-local writes."""
        if self._p1_blocks_local_write(sql):
            return False
        return bool(await self.hass.async_add_executor_job(self._db.execute, sql, params))
    def _p1_blocks_local_write(self, sql: str) -> bool:
        """P1/P5 gate: HA storage is read-only except scene entity registration."""
        normalized = " ".join(str(sql or "").split())
        upper = normalized.upper()
        if not upper.startswith(("INSERT ", "UPDATE ", "DELETE ", "REPLACE ")):
            return False
        if upper.startswith("UPDATE AI_SCENES SET HA_ENTITY_ID"):
            return False
        _LOGGER.warning("[P1] Legacy HA local write blocked: %s", normalized[:140])
        return True

    def _query_events(self, sql: str, params: tuple = (), max_rows: int = 10000) -> list[dict]:
        """Run a read query with an automatic LIMIT on simple SELECT statements."""
        normalized = (sql or "").strip()
        tail = normalized.rstrip(" ;\t\r\n")
        has_limit = bool(re.search(r"\bLIMIT\b", tail, re.IGNORECASE))
        is_complex = bool(
            re.search(r"\bGROUP\s+BY\b", tail, re.IGNORECASE)
            or re.search(r"\bHAVING\b", tail, re.IGNORECASE)
            or re.search(r"\bUNION\b", tail, re.IGNORECASE)
            or re.search(r"\bINTERSECT\b", tail, re.IGNORECASE)
            or re.search(r"\bEXCEPT\b", tail, re.IGNORECASE)
        )
        effective_sql = f"{tail} LIMIT {max_rows}" if max_rows > 0 and not has_limit and not is_complex else tail
        rows = self._db.query(effective_sql, params)
        if effective_sql != tail and len(rows) >= max_rows and hasattr(self, "_sys_log"):
            self._sys_log("INFO", f"[QueryLimit] automatic LIMIT {max_rows} applied")
        return rows

    async def _async_query(self, sql: str, params: tuple = (), max_rows: int = 10000) -> list[dict]:
        return await self.hass.async_add_executor_job(self._query_events, sql, params, max_rows)

    def _enqueue_bridge_event(self, kind: str, payload: dict[str, Any], *, ts: str | None = None) -> bool:
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue):
            return False
        return bool(enqueue(kind, payload, ts=ts))
    def _record_event(
        self,
        event_type: str,
        detail: str,
        entity_id: str | None = None,
        new_state: str | None = None,
        source: str = "system",
        confidence: int | None = None,
        transaction_id: int = 0,
        action_seq: int = 0,
    ) -> None:
        """Forward an HA event into add-on owned storage."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        area = ""
        if entity_id and entity_id in getattr(self, "device_info", {}):
            area = self.device_info[entity_id].get("room", "")
        payload = {
            "time": timestamp,
            "type": event_type,
            "detail": detail,
            "entity_id": entity_id,
            "state": new_state,
            "source": source,
            "area": area,
            "confidence": confidence,
            "transaction_id": int(transaction_id or 0),
            "action_seq": int(action_seq or 0),
        }
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue) or not enqueue("event", payload, ts=timestamp):
            _LOGGER.warning("[DB] failed to enqueue event: type=%s entity=%s", event_type, entity_id)

    def _record_action_result(
        self,
        entity_id: str,
        domain: str,
        service: str,
        expected: str,
        actual: str,
        success: int,
        retry_count: int,
        latency_ms: int,
        reason: str,
        transaction_id: int = 0,
        action_seq: int = 0,
    ) -> None:
        """Forward action verification into add-on transaction storage."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "action": "action_result",
            "transaction_id": str(transaction_id or f"action-{int(time.time() * 1000)}-{action_seq}"),
            "updated_at": timestamp,
            "result": {
                "action_results": [
                    {
                        "time": timestamp,
                        "entity_id": entity_id,
                        "domain": domain,
                        "service": service,
                        "expected_state": expected,
                        "actual_state": actual,
                        "verified": 1,
                        "success": int(success),
                        "retry_count": int(retry_count),
                        "latency_ms": int(latency_ms),
                        "reason": reason,
                        "transaction_id": int(transaction_id or 0),
                        "action_seq": int(action_seq or 0),
                    }
                ]
            },
        }
        if not self._enqueue_bridge_event("transaction_end", payload, ts=timestamp):
            _LOGGER.warning("[ActionResult] failed to enqueue result: entity=%s service=%s", entity_id, service)

    def _get_action_quality_stats(self) -> dict:
        stats: dict[str, Any] = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "rate": 0.0,
            "retry_total": 0,
            "avg_latency_ms": 0,
            "top_failures": [],
        }
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            rows = self._db.query(
                "SELECT COUNT(*) as total, SUM(success) as ok, SUM(retry_count) as retries, "
                "AVG(latency_ms) as avg_lat FROM action_results WHERE time >= ?",
                (cutoff,),
            )
            if rows and rows[0].get("total"):
                row = rows[0]
                stats["total"] = row["total"]
                stats["success"] = row["ok"] or 0
                stats["failed"] = stats["total"] - stats["success"]
                stats["rate"] = round(stats["success"] / stats["total"] * 100, 1) if stats["total"] else 0.0
                stats["retry_total"] = row["retries"] or 0
                stats["avg_latency_ms"] = int(row["avg_lat"] or 0)
            failures = self._db.query(
                "SELECT entity_id, COUNT(*) as fail_cnt FROM action_results "
                "WHERE success=0 AND time >= ? GROUP BY entity_id ORDER BY fail_cnt DESC LIMIT 5",
                (cutoff,),
            )
            stats["top_failures"] = [{"entity_id": row["entity_id"], "count": row["fail_cnt"]} for row in failures]
        except Exception as exc:
            _LOGGER.warning("[QualityStats] query failed: %s", exc)
        return stats

    def _query_ai_scenes(self, status: str | None = None) -> list[dict]:
        try:
            if status:
                return self._db.query(
                    "SELECT * FROM ai_scenes WHERE status=? ORDER BY confidence DESC, id DESC",
                    (status,),
                )
            return self._db.query("SELECT * FROM ai_scenes ORDER BY confidence DESC, id DESC")
        except Exception as exc:
            _LOGGER.warning("[AiScenes] query failed: %s", exc)
            return []

    def _upsert_ai_scene(
        self,
        name: str,
        description: str,
        entities_json: str,
        trigger_context: str,
        hour_start: int,
        hour_end: int,
        weekday_mask: str,
        confidence: int,
        hit_count: int,
        actions_json: str = "[]",
    ) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "action": "upsert",
            "name": name,
            "description": description,
            "entities_json": entities_json,
            "actions_json": actions_json,
            "trigger_context": trigger_context,
            "hour_start": int(hour_start),
            "hour_end": int(hour_end),
            "weekday_mask": weekday_mask,
            "confidence": int(confidence),
            "hit_count": int(hit_count),
            "status": "pending",
            "source": "auto",
            "created": now,
            "updated": now,
        }
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] upsert enqueue failed: name=%s", name)

    def _upsert_ai_scene_manual(
        self,
        name: str,
        description: str,
        entities_json: str,
        trigger_context: str,
        hour_start: int,
        hour_end: int,
        weekday_mask: str,
        confidence: int,
        actions_json: str = "[]",
    ) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "action": "upsert",
            "name": name,
            "description": description,
            "entities_json": entities_json,
            "actions_json": actions_json,
            "trigger_context": trigger_context,
            "hour_start": int(hour_start),
            "hour_end": int(hour_end),
            "weekday_mask": weekday_mask,
            "confidence": int(confidence),
            "hit_count": 0,
            "status": "pending",
            "source": "manual",
            "created": now,
            "updated": now,
        }
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] manual upsert enqueue failed: name=%s", name)
            return False
        return True

    def _update_ai_scene_status(self, scene_id: int, status: str) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {"action": "update_status", "id": int(scene_id), "status": status, "updated": now}
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] status enqueue failed: id=%s", scene_id)
            return False
        return True

    def _update_ai_scene_ha_entity(self, scene_id: int, ha_entity_id: str) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ok = self._db.execute(
            "UPDATE ai_scenes SET ha_entity_id=?, updated=? WHERE id=?",
            (ha_entity_id, now, scene_id),
        )
        if not ok:
            _LOGGER.warning("[AiScenes] HA entity update failed: id=%s", scene_id)
        return bool(ok)

    def _mark_ai_scene_ephemeral(self, scene_id: int) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {"action": "mark_ephemeral", "id": int(scene_id), "updated": now}
        if not self._enqueue_bridge_event("ai_scene", payload, ts=now):
            _LOGGER.warning("[AiScenes] ephemeral marker enqueue failed: id=%s", scene_id)
            return False
        return True

    def _delete_ai_scene_db(self, scene_id: int) -> bool:
        payload = {"action": "delete", "id": int(scene_id)}
        if not self._enqueue_bridge_event("ai_scene", payload):
            _LOGGER.warning("[AiScenes] delete enqueue failed: id=%s", scene_id)
            return False
        return True

    def _begin_transaction_db(
        self,
        trigger_summary: str,
        scene_desc: str,
        confidence: int,
        action_count: int,
        pre_states_json: str,
        actions_json: str,
    ) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        txn_id = int(time.time() * 1000)
        payload = {
            "transaction_id": str(txn_id),
            "created_at": now,
            "status": "pending",
            "trigger_summary": trigger_summary[:200],
            "scene_desc": scene_desc[:200],
            "confidence": int(confidence),
            "action_count": int(action_count),
            "rollback_json": pre_states_json,
            "envelope_json": {"actions": actions_json},
        }
        if not self._enqueue_bridge_event("transaction_start", payload, ts=now):
            _LOGGER.warning("[Transaction] begin enqueue failed: trigger=%s", trigger_summary[:60])
            return 0
        return txn_id

    def _complete_transaction_db(
        self,
        txn_id: int,
        dispatched: int,
        blocked: int,
        failed: int,
        results_json: str,
    ) -> None:
        if not txn_id:
            return
        has_scheduled = False
        try:
            decoded_results = json.loads(results_json or "[]")
            if isinstance(decoded_results, list):
                has_scheduled = any(
                    str((item or {}).get("status") or "") in {"scheduled", "delayed"}
                    for item in decoded_results
                    if isinstance(item, dict)
                )
        except Exception:
            has_scheduled = False

        if has_scheduled:
            status = "scheduled"
        elif failed == 0 and (dispatched > 0 or blocked == 0):
            status = "success"
        elif dispatched > 0 and failed > 0:
            status = "partial"
        elif dispatched == 0 and blocked > 0:
            status = "blocked"
        else:
            status = "failed"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "transaction_id": str(txn_id),
            "updated_at": timestamp,
            "status": status,
            "final_outcome": status,
            "blocked_count": int(blocked),
            "failed_count": int(failed),
            "result": {
                "dispatched_count": int(dispatched),
                "blocked_count": int(blocked),
                "failed_count": int(failed),
                "results": results_json,
            },
        }
        if not self._enqueue_bridge_event("transaction_end", payload, ts=timestamp):
            _LOGGER.warning("[Transaction] complete enqueue failed: txn_id=%s", txn_id)

    def _rollback_transaction_db(self, txn_id: int) -> dict | None:
        try:
            rows = self._db.query("SELECT * FROM action_transactions WHERE id=?", (txn_id,))
            return rows[0] if rows else None
        except Exception as exc:
            _LOGGER.warning("[Transaction] rollback query failed: %s", exc)
            return None

    def _query_recent_transactions(self, limit: int = 30) -> list[dict]:
        try:
            return self._db.query("SELECT * FROM action_transactions ORDER BY id DESC LIMIT ?", (limit,))
        except Exception as exc:
            _LOGGER.warning("[Transaction] query failed: %s", exc)
            return []

    def _get_entity_room(self, entity_id: str) -> str:
        room = getattr(self, "device_info", {}).get(entity_id, {}).get("room", "")
        if room:
            return room
        area_getter = getattr(self, "_get_entity_area", None)
        if callable(area_getter):
            try:
                return area_getter(entity_id) or "unknown"
            except Exception:
                return "unknown"
        return "unknown"

    def _get_device_usage_stats(self, days: int = 7) -> list[dict]:
        """Return a small HA-local energy projection from stored event rows."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            rows = self._query_events(
                "SELECT entity AS entity_id, state, time FROM events WHERE time >= ? "
                "AND (entity LIKE 'light.%' OR entity LIKE 'switch.%' OR entity LIKE 'climate.%' "
                "OR entity LIKE 'cover.%' OR entity LIKE 'fan.%') ORDER BY entity, time",
                (cutoff,),
            )
        except Exception as exc:
            _LOGGER.warning("[EnergyStats] query failed: %s", exc)
            return []

        stats: dict[str, dict[str, Any]] = {}
        for row in rows:
            entity_id = row.get("entity_id")
            if not entity_id:
                continue
            item = stats.setdefault(
                entity_id,
                {"entity_id": entity_id, "on_minutes": 0.0, "waste_minutes": 0.0, "on_count": 0, "last_on": ""},
            )
            if str(row.get("state")) in {"on", "open", "heat", "cool", "auto", "fan_only", "playing"}:
                item["on_count"] += 1
                item["last_on"] = row.get("time") or item["last_on"]
        return sorted(stats.values(), key=lambda item: item["on_count"], reverse=True)

    def _record_arrival_snapshot(
        self,
        room: str,
        presence_entity_id: str,
        light_states: dict[str, str | None] | None = None,
    ) -> None:
        """Forward arrival lighting samples to add-on owned memory."""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        if light_states is None:
            light_states = {}
            for entity_id, info in getattr(self, "device_info", {}).items():
                if not entity_id.startswith("light.") or info.get("room") != room:
                    continue
                state = self.hass.states.get(entity_id)
                light_states[entity_id] = state.state if state else None

        normalized_states = [
            str(state or "").strip().lower()
            for state in light_states.values()
            if state is not None
        ]
        if normalized_states and not any(state == "on" for state in normalized_states):
            _LOGGER.debug("[ArrivalBaseline] skip ambiguous all-off sample: room=%s sensor=%s", room, presence_entity_id)
            return

        for entity_id, state in light_states.items():
            if state is None:
                continue
            payload = {
                "action": "arrival_sample",
                "time": timestamp,
                "entity_id": entity_id,
                "room": room,
                "presence_entity_id": presence_entity_id,
                "is_on": state == "on",
                "hour_bucket": now.hour,
            }
            enqueue = getattr(self, "_enqueue_internal_event", None)
            if not callable(enqueue) or not enqueue("baseline", payload, ts=timestamp):
                _LOGGER.debug("[ArrivalBaseline] sample enqueue failed: %s", entity_id)

    def _get_showroom_light_tier_v2(self, entity_id: str) -> str:
        """Return the neutral tier after HA-local showroom preference storage removal."""
        return "core"
