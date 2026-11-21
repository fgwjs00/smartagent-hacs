"""Transport-only execution receipt spool; never stores executable work.

Admission returns only after a FULL SQLite commit. Pending evidence is never
evicted. Its bounded capacity is not a reservation for future device actions.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from .storage_capacity import connect
import threading
import time
from uuid import uuid4

POLICY = "sqlite_wal_full.v1"


def receipt_outbox_path(config_dir: str, entry_id: str, destination: str) -> str:
    """A changed entry or destination cannot silently receive another spool."""
    scope = hashlib.sha256(json.dumps([entry_id, destination]).encode()).hexdigest()[:32]
    return str(Path(config_dir) / ".storage" / f"smart_agent_receipts_{scope}.sqlite3")


def _validate_frozen(frozen: object, stream: str, sequence: int) -> dict:
    if (not isinstance(frozen, dict) or frozen.get("stream_id") != stream
            or type(frozen.get("seq")) is not int or not 0 < frozen["seq"] <= sequence
            or not isinstance(frozen.get("ts"), str) or not frozen["ts"]):
        raise ValueError("receipt_outbox_identity_invalid")
    return frozen


class ReceiptOutbox:
    def __init__(self, path: str, *, max_items: int = 10000,
                 max_bytes: int = 64 * 1024 * 1024) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._max_items, self._max_bytes = max_items, max_bytes
        self._closed = False
        self._conn = connect(path, isolation_level=None, check_same_thread=False)
        try:
            self._conn.execute("PRAGMA busy_timeout=1000")
            mode = self._conn.execute("PRAGMA journal_mode").fetchone()[0]
            if mode != "wal":
                mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            self._conn.execute("PRAGMA synchronous=FULL")
            if mode != "wal" or self._conn.execute("PRAGMA synchronous").fetchone()[0] != 2:
                raise RuntimeError("receipt_outbox_durability_unavailable")
            self._initialize()
        except BaseException:
            self._conn.close()
            raise

    def _initialize(self) -> None:
        tables = {row[0] for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"delivery_cursor", "pending_receipts"}.issubset(tables):
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS delivery_cursor (
                    id INTEGER PRIMARY KEY CHECK(id=1), stream TEXT NOT NULL, sequence INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS pending_receipts (
                    sequence INTEGER PRIMARY KEY, envelope TEXT NOT NULL, bytes INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0);
            """)
        if self._conn.execute("SELECT 1 FROM delivery_cursor WHERE id=1").fetchone() is None:
            self._conn.execute("INSERT OR IGNORE INTO delivery_cursor VALUES(1,?,0)", (uuid4().hex,))
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            columns = {row[1] for row in self._conn.execute("PRAGMA table_info(pending_receipts)")}
            for name in ("first_failed_at", "last_failed_at"):
                if name not in columns:
                    self._conn.execute(f"ALTER TABLE pending_receipts ADD COLUMN {name} TEXT")
            if "delivery_state" not in columns:
                self._conn.execute("ALTER TABLE pending_receipts ADD COLUMN delivery_state TEXT NOT NULL DEFAULT 'pending'")
            self._conn.execute("COMMIT")
        except BaseException:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
            raise

    def admit(self, payload: dict, *, ts: str, kind: str = "decision_execution") -> dict:
        if kind not in {"decision_execution", "correction"}:
            raise ValueError("receipt_outbox_kind_invalid")
        # Execution evidence was produced before this local transport boundary;
        # a new correction is new learning, even though both use FULL commits.
        category = "accepted_result" if kind == "decision_execution" else "normal"
        peak = 256 * 1024 + 4 * len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        with self._conn.capacity_scope(category, estimated_peak_bytes=peak):
            return self._admit_payload(payload, ts=ts, kind=kind)

    def _admit_payload(self, payload: dict, *, ts: str, kind: str) -> dict:
        body = dict(payload)
        frozen = body.pop("_receipt_delivery", None)
        with self._lock:
            if self._closed:
                raise RuntimeError("receipt_outbox_closed")
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                stream, sequence = self._conn.execute("SELECT stream,sequence FROM delivery_cursor WHERE id=1").fetchone()
                if frozen is not None:
                    frozen = _validate_frozen(frozen, stream, sequence)
                    sequence, ts = frozen["seq"], frozen["ts"]
                else:
                    sequence += 1
                    self._conn.execute("UPDATE delivery_cursor SET sequence=? WHERE id=1", (sequence,))
                item = {"kind": kind, "payload": body, "ts": ts,
                        "stream_id": stream, "seq": sequence, "envelope_version": 1,
                        "transport": "ha_internal_event_bridge", "durability": POLICY}
                text = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
                previous = self._conn.execute("SELECT envelope FROM pending_receipts WHERE sequence=?", (sequence,)).fetchone()
                if previous and previous[0] != text:
                    raise ValueError("receipt_outbox_identity_conflict")
                if not previous:
                    size = len(text.encode("utf8"))
                    count, total = self._conn.execute("SELECT count(*),coalesce(sum(bytes),0) FROM pending_receipts").fetchone()
                    if count >= self._max_items or total + size > self._max_bytes:
                        raise RuntimeError("receipt_outbox_capacity_exceeded")
                    self._conn.execute("INSERT INTO pending_receipts(sequence,envelope,bytes) VALUES(?,?,?)", (sequence, text, size))
                self._conn.execute("COMMIT")
                return item
            except BaseException:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise

    def next_due(self) -> dict | None:
        item, _ = self.next_due_or_wait()
        return item

    def next_due_or_wait(self, default_wait: float = 30.0) -> tuple[dict | None, float]:
        with self._lock:
            now = time.time()
            row = self._conn.execute(
                "SELECT envelope FROM pending_receipts WHERE delivery_state!='quarantined' AND (retry_at<=? OR retry_at>?) ORDER BY sequence LIMIT 1",
                (now, now + 60)).fetchone()
            if row:
                return json.loads(row[0]), 0.0
            pending = self._conn.execute(
                "SELECT MIN(retry_at) FROM pending_receipts WHERE delivery_state!='quarantined'"
            ).fetchone()
            if not pending or pending[0] is None:
                return None, float(default_wait)
            return None, max(0.05, min(float(default_wait), float(pending[0]) - now))

    @staticmethod
    def confirmed(item: dict, receipt: dict | None, status: int) -> bool:
        delivery_ack = receipt.get("delivery_ack") if isinstance(receipt, dict) else None
        return (isinstance(receipt, dict) and 200 <= status < 300
                and receipt.get("ok") is True and receipt.get("committed") is True
                and receipt.get("durability") == POLICY
                and receipt.get("receipt_disposition") in (
                    ("applied", "duplicate") if item["kind"] == "correction" else ("applied", "duplicate", "stale"))
                and (item["kind"] != "correction" or receipt.get("kind") == "correction")
                and isinstance(delivery_ack, dict) and type(delivery_ack.get("seq")) is int
                and delivery_ack == {key: item[key] for key in ("stream_id", "seq", "ts")})

    def acknowledge(self, item: dict) -> None:
        with self._lock, self._conn.capacity_scope("maintenance"):
            self._conn.execute("DELETE FROM pending_receipts WHERE sequence=?", (item["seq"],))

    def retry(self, item: dict, *, quarantine: bool = False) -> None:
        with self._lock, self._conn.capacity_scope("maintenance"):
            from datetime import UTC, datetime
            failed_at = datetime.now(UTC).isoformat()
            self._conn.execute("""UPDATE pending_receipts SET attempts=attempts+1,
                first_failed_at=CASE WHEN attempts=0 THEN ? ELSE first_failed_at END,
                last_failed_at=?, retry_at=?+min(60,1+attempts*2), delivery_state=? WHERE sequence=?""",
                (failed_at, failed_at, time.time(), 'quarantined' if quarantine else 'retrying', item["seq"]))

    def resume_quarantined(self, stream_id: str, seq: int) -> bool:
        with self._lock, self._conn.capacity_scope("maintenance"):
            stream = self._conn.execute("SELECT stream FROM delivery_cursor WHERE id=1").fetchone()[0]
            if stream != stream_id or type(seq) is not int:
                return False
            cursor = self._conn.execute("""UPDATE pending_receipts SET delivery_state='retrying', retry_at=0
                WHERE sequence=? AND delivery_state='quarantined'""", (seq,))
            return cursor.rowcount == 1

    @property
    def delivery_diagnostics(self) -> dict:
        with self._lock:
            count = self._conn.execute("SELECT count(*) FROM pending_receipts WHERE attempts>0").fetchone()[0]
            quarantined = self._conn.execute("SELECT count(*) FROM pending_receipts WHERE delivery_state='quarantined'").fetchone()[0]
            rows = self._conn.execute("""SELECT envelope,attempts,first_failed_at,last_failed_at,delivery_state
                FROM pending_receipts WHERE attempts>0 ORDER BY sequence LIMIT 100""").fetchall()
            events = []
            for envelope, attempts, first, last, state in rows:
                item = json.loads(envelope)
                events.append({**{key: item[key] for key in ("kind", "stream_id", "seq")},
                    "failure_count": attempts, "first_failed_at": first, "last_failed_at": last,
                    "state": "quarantined" if state == "quarantined" else "retrying", "durable": True})
            return {"failed_events": count, "retrying": count - quarantined, "quarantined": quarantined,
                    "events": events, "truncated": count > 100}

    @property
    def stats(self) -> dict:
        with self._lock:
            count, total, retrying = self._conn.execute(
                "SELECT count(*),coalesce(sum(bytes),0),coalesce(sum(attempts>0 AND delivery_state!='quarantined'),0) FROM pending_receipts").fetchone()
            return {"durable_pending": count, "durable_bytes": total, "durable_retrying": retrying}

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._conn.close()
