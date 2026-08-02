"""Thin SQLite bridge helpers for the Home Assistant integration."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any

from .const import DEVICE_CONTROL_MODES
from .db_service import DatabaseService
from .database_learning_projection import DatabaseLearningProjectionMixin
from .database_scenes import DatabaseSceneBridgeMixin
from .database_write_ownership import _safe_add_column, classify_ha_local_write, ha_local_write_allowed

_LOGGER = logging.getLogger(__name__)

_BRIDGE_SCHEMA: tuple[tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]], ...] = (
    ("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, type TEXT NOT NULL, detail TEXT, entity TEXT, state TEXT, source TEXT DEFAULT 'system', area TEXT, confidence INTEGER, transaction_id INTEGER DEFAULT 0, action_seq INTEGER DEFAULT 0)", ("CREATE INDEX IF NOT EXISTS idx_events_time ON events(time)", "CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)", "CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity)"), (("events", "transaction_id INTEGER DEFAULT 0"), ("events", "action_seq INTEGER DEFAULT 0"))),
    ("CREATE TABLE IF NOT EXISTS devices (entity_id TEXT PRIMARY KEY, name TEXT NOT NULL, area TEXT DEFAULT '', type TEXT DEFAULT '', ops TEXT DEFAULT '', control_mode TEXT DEFAULT 'shared', sensor_type TEXT DEFAULT '', ha_unique_id TEXT DEFAULT '', ha_device_id TEXT DEFAULT '', created TEXT, updated TEXT)", (), (("devices", "control_mode TEXT DEFAULT 'shared'"), ("devices", "sensor_type TEXT DEFAULT ''"), ("devices", "ha_unique_id TEXT DEFAULT ''"), ("devices", "ha_device_id TEXT DEFAULT ''"))),
    ("CREATE TABLE IF NOT EXISTS habits (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, locked INTEGER DEFAULT 0, created TEXT)", (), (("habits", "locked INTEGER DEFAULT 0"),)),
    ("CREATE TABLE IF NOT EXISTS rules (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, locked INTEGER DEFAULT 0, created TEXT)", (), (("rules", "locked INTEGER DEFAULT 0"),)),
    ("CREATE TABLE IF NOT EXISTS action_results (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, entity_id TEXT NOT NULL, domain TEXT NOT NULL, service TEXT NOT NULL, expected_state TEXT, actual_state TEXT, verified INTEGER DEFAULT 0, success INTEGER DEFAULT 0, retry_count INTEGER DEFAULT 0, latency_ms INTEGER DEFAULT 0, reason TEXT DEFAULT '', transaction_id INTEGER DEFAULT 0, action_seq INTEGER DEFAULT 0)", ("CREATE INDEX IF NOT EXISTS idx_ar_time ON action_results(time)", "CREATE INDEX IF NOT EXISTS idx_ar_entity ON action_results(entity_id)"), (("action_results", "transaction_id INTEGER DEFAULT 0"), ("action_results", "action_seq INTEGER DEFAULT 0"))),
    ("CREATE TABLE IF NOT EXISTS ai_scenes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT DEFAULT '', entities_json TEXT NOT NULL, trigger_context TEXT DEFAULT '', hour_start INTEGER DEFAULT 0, hour_end INTEGER DEFAULT 23, weekday_mask TEXT DEFAULT '0123456', confidence INTEGER DEFAULT 80, hit_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', source TEXT DEFAULT 'auto', created TEXT, updated TEXT, ha_entity_id TEXT DEFAULT '', actions_json TEXT DEFAULT '[]', space_id TEXT DEFAULT '', room TEXT DEFAULT '', explain_bundle_json TEXT DEFAULT '{}')", ("CREATE INDEX IF NOT EXISTS idx_ai_scenes_status ON ai_scenes(status)", "CREATE INDEX IF NOT EXISTS idx_ai_scenes_space ON ai_scenes(space_id)"), (("ai_scenes", "ha_entity_id TEXT DEFAULT ''"), ("ai_scenes", "actions_json TEXT DEFAULT '[]'"), ("ai_scenes", "space_id TEXT DEFAULT ''"), ("ai_scenes", "room TEXT DEFAULT ''"), ("ai_scenes", "explain_bundle_json TEXT DEFAULT '{}'"))),
    ("CREATE TABLE IF NOT EXISTS action_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, trigger_summary TEXT DEFAULT '', scene_desc TEXT DEFAULT '', confidence INTEGER DEFAULT 0, action_count INTEGER DEFAULT 0, dispatched_count INTEGER DEFAULT 0, blocked_count INTEGER DEFAULT 0, failed_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', pre_states_json TEXT DEFAULT '{}', actions_json TEXT DEFAULT '[]', results_json TEXT DEFAULT '[]')", ("CREATE INDEX IF NOT EXISTS idx_txn_time ON action_transactions(time)",), ()),
    ("CREATE TABLE IF NOT EXISTS room_topology (id INTEGER PRIMARY KEY AUTOINCREMENT, room_a TEXT NOT NULL, room_b TEXT NOT NULL, relation TEXT DEFAULT 'adjacent', updated_at TEXT DEFAULT '', UNIQUE(room_a, room_b))", (), ()),
)


class DatabaseMixin(DatabaseLearningProjectionMixin, DatabaseSceneBridgeMixin):
    _VALID_CONTROL_MODES = DEVICE_CONTROL_MODES

    def _init_memory_db(self) -> None:
        try:
            self._db = DatabaseService(self._memory_db)
            self._db.open()
            conn = self._db.get_raw_connection()
            for create_sql, indexes, columns in _BRIDGE_SCHEMA:
                conn.execute(create_sql)
                for table, column_def in columns:
                    _safe_add_column(conn, table, column_def)
                for index_sql in indexes:
                    conn.execute(index_sql)
        except Exception as exc:
            _LOGGER.error("[DB] initialization failed: %s", exc)
            if hasattr(self, "_sys_log"):
                self._sys_log("ERROR", f"Database initialization failed: {exc}")
            return

        if hasattr(self, "_sys_log"):
            self._sys_log("INFO", f"Database initialized: {self._memory_db}")

    def _legacy_config_migration_batch(self) -> tuple[dict[str, Any], str | None] | None:
        """Build one deterministic migration batch from legacy HA projections and JSON."""
        devices_by_id: dict[str, dict[str, Any]] = {}
        habits_by_content: dict[str, dict[str, Any]] = {}
        rules_by_content: dict[str, dict[str, Any]] = {}
        try:
            conn = self._db.get_raw_connection()
            for row in conn.execute("SELECT * FROM devices ORDER BY entity_id"):
                columns = set(row.keys())
                entity_id = str(row["entity_id"] or "").strip()
                if not entity_id:
                    continue
                devices_by_id[entity_id] = {
                    "entity_id": entity_id,
                    "name": str(row["name"] or entity_id),
                    "area": str(row["area"] or ""),
                    "type": str(row["type"] or ""),
                    "ops": str(row["ops"] or ""),
                    "control_mode": str(row["control_mode"] or "shared") if "control_mode" in columns else "shared",
                    "sensor_type": str(row["sensor_type"] or "") if "sensor_type" in columns else "",
                }
            for target, output in (("habits", habits_by_content), ("rules", rules_by_content)):
                for row in conn.execute(f"SELECT content, locked, created FROM {target} ORDER BY id"):
                    content = str(row["content"] or "").strip()
                    if content:
                        output[content] = {
                            "content": content,
                            "locked": bool(row["locked"]),
                            "created": str(row["created"] or ""),
                        }
        except Exception as exc:
            _LOGGER.warning("[DB] legacy SQL projection read failed: %s", exc)
            return None

        json_path = os.path.join(self._config_dir, "smart_agent_config.json")
        cfg: dict[str, Any] = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as file:
                    loaded = json.load(file)
                cfg = loaded if isinstance(loaded, dict) else {}
            except Exception as exc:
                _LOGGER.warning("[DB] legacy JSON read failed: %s", exc)
                return None
            for eid, desc in cfg.get("devices", {}).items():
                entity_id = str(eid or "").strip()
                if not entity_id or entity_id in devices_by_id:
                    continue
                parts = [part.strip() for part in str(desc).split("|")]
                devices_by_id[entity_id] = {
                    "entity_id": entity_id,
                    "name": parts[0] if parts else entity_id,
                    "area": parts[1] if len(parts) > 1 else "",
                    "type": parts[2] if len(parts) > 2 else "",
                    "ops": parts[3] if len(parts) > 3 else "",
                    "control_mode": "shared",
                    "sensor_type": "",
                }
            for target, output in (("habits", habits_by_content), ("rules", rules_by_content)):
                for item in cfg.get(target, []):
                    content = str(item or "").strip()
                    if content and content not in output:
                        output[content] = {"content": content, "locked": False, "created": ""}

        devices = [devices_by_id[key] for key in sorted(devices_by_id)]
        habits = [habits_by_content[key] for key in sorted(habits_by_content)]
        rules = [rules_by_content[key] for key in sorted(rules_by_content)]
        if not devices and not habits and not rules:
            return None
        canonical = {"devices": devices, "habits": habits, "rules": rules}
        digest = hashlib.sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        payload = {
            "migration_id": f"legacy-config:sha256:{digest}",
            "devices": devices,
            "habits": habits,
            "rules": rules,
        }
        return payload, json_path if os.path.exists(json_path) else None

    @staticmethod
    def _legacy_migration_committed(result: Any, expected: int) -> bool:
        return bool(
            isinstance(result, dict)
            and result.get("ok") is True
            and result.get("committed") is True
            and int(result.get("accepted_count") or -1) == expected
        )

    @staticmethod
    def _mark_legacy_json_migrated(json_path: str | None) -> None:
        if not json_path or not os.path.exists(json_path):
            return
        os.replace(json_path, json_path + ".migrated")

    def _migrate_json_config(self) -> None:
        """Compatibility entrypoint for non-event-loop migration callers."""
        batch = self._legacy_config_migration_batch()
        if batch is None:
            return
        payload, json_path = batch
        now = self._ha_db_now_text()
        confirm = getattr(self, "_post_internal_event_confirmed", None)
        if not callable(confirm):
            _LOGGER.warning("[DB] legacy migration deferred: persistence confirmation unavailable")
            return
        result = confirm("legacy_config_migration", payload, ts=now)
        expected = len(payload["devices"]) + len(payload["habits"]) + len(payload["rules"])
        if not self._legacy_migration_committed(result, expected):
            _LOGGER.warning("[DB] legacy migration deferred: add-on did not confirm durable commit")
            return
        try:
            self._mark_legacy_json_migrated(json_path)
        except Exception as exc:
            _LOGGER.warning("[DB] legacy JSON migration committed but marker rename failed: %s", exc)

    async def _async_migrate_legacy_config(self) -> bool:
        """Migrate legacy projections through the Add-on writer without blocking HA's loop."""
        batch = await self.hass.async_add_executor_job(self._legacy_config_migration_batch)
        if batch is None:
            return True
        payload, json_path = batch
        result = await self._post_internal_event_confirmed_async(
            "legacy_config_migration",
            payload,
            ts=self._ha_db_now_text(),
        )
        expected = len(payload["devices"]) + len(payload["habits"]) + len(payload["rules"])
        if not self._legacy_migration_committed(result, expected):
            _LOGGER.warning("[DB] legacy migration deferred: add-on did not confirm durable commit")
            return False
        try:
            await self.hass.async_add_executor_job(self._mark_legacy_json_migrated, json_path)
        except Exception as exc:
            _LOGGER.warning("[DB] legacy JSON migration committed but marker rename failed: %s", exc)
        return True

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
                    "ha_unique_id": row["ha_unique_id"] if "ha_unique_id" in columns else "",
                    "ha_device_id": row["ha_device_id"] if "ha_device_id" in columns else "",
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
        """Enforce the executable table/operation ownership contract."""
        normalized = " ".join(str(sql or "").split())
        if ha_local_write_allowed(normalized):
            return False
        table, operation, _columns = classify_ha_local_write(normalized)
        _LOGGER.warning(
            "[P1] HA local write blocked operation=%s table=%s: %s",
            operation or "unclassified",
            table or "unclassified",
            normalized[:140],
        )
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

    def _ha_db_now_text(self) -> str:
        try:
            local_now = getattr(self, "_ha_local_now", None)
            now_value = local_now() if callable(local_now) else None
            if hasattr(now_value, "strftime"):
                return now_value.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        try:
            from homeassistant.util import dt as dt_util
            return dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            from datetime import timezone
            return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _ha_db_cutoff_text(self, days: int) -> str:
        try:
            local_now = getattr(self, "_ha_local_now", None)
            now_value = local_now() if callable(local_now) else None
            if hasattr(now_value, "strftime"):
                return (now_value - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        try:
            from homeassistant.util import dt as dt_util
            now = dt_util.now()
        except Exception:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        return (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    def _ha_transaction_id_ms(self) -> int:
        try:
            local_now = getattr(self, "_ha_local_now", None)
            now_value = local_now() if callable(local_now) else None
            if hasattr(now_value, "timestamp"):
                return int(now_value.timestamp() * 1000)
        except Exception:
            pass
        return int(time.time() * 1000)

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
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Forward an HA event into add-on owned storage."""
        timestamp = self._ha_db_now_text()
        area = ""
        if entity_id and entity_id in getattr(self, "device_info", {}):
            area = self.device_info[entity_id].get("room", "")
        detail_payload = detail
        if isinstance(metadata, dict) and metadata:
            structured = dict(metadata)
            structured.setdefault("detail", detail)
            detail_payload = json.dumps(structured, ensure_ascii=False, default=str)
        payload = {
            "time": timestamp,
            "type": event_type,
            "detail": detail_payload,
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
        timestamp = self._ha_db_now_text()
        self._record_recent_ai_action_results(
            transaction_id,
            [
                {
                    "entity_id": entity_id,
                    "domain": domain,
                    "service": service,
                    "status": "ok" if int(success) else "blocked_or_error",
                    "verified": True,
                    "success": bool(success),
                    "action_seq": int(action_seq or 0),
                }
            ],
        )
        payload = {
            "action": "action_result",
            "transaction_id": str(transaction_id or f"action-{self._ha_transaction_id_ms()}-{action_seq}"),
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
        cutoff = self._ha_db_cutoff_text(7)
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

    def _begin_transaction_db(
        self,
        trigger_summary: str,
        scene_desc: str,
        confidence: int,
        action_count: int,
        pre_states_json: str,
        actions_json: str,
    ) -> int:
        now = self._ha_db_now_text()
        txn_id = self._ha_transaction_id_ms()
        try:
            decoded_actions = json.loads(actions_json or "[]")
            actions_payload = list(decoded_actions) if isinstance(decoded_actions, list) else []
        except Exception:
            actions_payload = []
        payload = {
            "transaction_id": str(txn_id),
            "created_at": now,
            "status": "pending",
            "trigger_summary": trigger_summary[:200],
            "scene_desc": scene_desc[:200],
            "confidence": int(confidence),
            "action_count": int(action_count),
            "rollback_json": pre_states_json,
            "envelope_json": {"actions": actions_payload},
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
        all_skipped = False
        action_results: list[dict[str, Any]] = []
        try:
            decoded_results = json.loads(results_json or "[]")
            if isinstance(decoded_results, list):
                action_results = [dict(item) for item in decoded_results if isinstance(item, dict)]
                has_scheduled = any(
                    str((item or {}).get("status") or "") in {"scheduled", "delayed"}
                    for item in action_results
                )
                all_skipped = bool(action_results) and all(
                    str((item or {}).get("status") or "").strip().lower() in {"skip", "skipped"}
                    or str((item or {}).get("ha_command_status") or "").strip().lower() == "skipped"
                    for item in action_results
                )
        except Exception:
            has_scheduled = False
            all_skipped = False
        self._record_recent_ai_action_results(txn_id, action_results)

        if has_scheduled:
            status = "scheduled"
        elif all_skipped and dispatched == 0 and blocked == 0 and failed == 0:
            status = "skipped"
        elif failed == 0 and (dispatched > 0 or blocked == 0):
            status = "success"
        elif dispatched > 0 and failed > 0:
            status = "partial"
        elif dispatched == 0 and blocked > 0:
            status = "blocked"
        else:
            status = "failed"
        timestamp = self._ha_db_now_text()
        payload = {
            "transaction_id": str(txn_id),
            "updated_at": timestamp,
            "status": status,
            "final_outcome": status,
            "blocked_count": int(blocked),
            "failed_count": int(failed),
            "action_results": action_results,
            "result": {
                "dispatched_count": int(dispatched),
                "blocked_count": int(blocked),
                "failed_count": int(failed),
                "action_results": action_results,
                "results": results_json,
            },
        }
        if not self._enqueue_bridge_event("transaction_end", payload, ts=timestamp):
            _LOGGER.warning("[Transaction] complete enqueue failed: txn_id=%s", txn_id)

    def _rollback_transaction_db(self, txn_id: int) -> dict | None:
        _LOGGER.warning(
            "[Transaction] legacy local rollback lookup disabled; use add-on rollback service: txn_id=%s",
            txn_id,
        )
        return None

    def _query_recent_transactions(self, limit: int = 30) -> list[dict]:
        _LOGGER.warning(
            "[Transaction] legacy local transaction query disabled; use add-on transaction read API: limit=%s",
            limit,
        )
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
        cutoff = self._ha_db_cutoff_text(days)
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
