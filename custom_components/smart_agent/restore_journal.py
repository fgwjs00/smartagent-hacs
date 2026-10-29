"""HA-side restore handles, not a second business-data writer.

Persist identity before sending; retain confirmed terminal facts across HA
restart and unavailable later queries. No password or backup body is stored.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from .storage_capacity import connect


class RestoreJournal:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def _initialize(self, db) -> None:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='restore_handles'").fetchone():
            return
        db.execute("""CREATE TABLE restore_handles (
            operation_id TEXT PRIMARY KEY, backup_id TEXT NOT NULL,
            payload_digest TEXT NOT NULL DEFAULT '', receipt_json TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)))""")
        db.execute("CREATE UNIQUE INDEX restore_one_active ON restore_handles(active) WHERE active=1")

    @contextmanager
    def _transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            self._initialize(db)
            yield db
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def claim(self, operation_id: str, backup_id: str) -> dict:
        with self._transaction() as db:
            row = db.execute("SELECT * FROM restore_handles WHERE operation_id=?", (operation_id,)).fetchone()
            if row:
                return {"state": "existing" if row["backup_id"] == backup_id else "conflict", **dict(row)}
            active = db.execute("SELECT operation_id FROM restore_handles WHERE active=1").fetchone()
            if active:
                return {"state": "blocked", "blocking_operation_id": active["operation_id"]}
            db.execute("INSERT INTO restore_handles(operation_id,backup_id) VALUES(?,?)", (operation_id, backup_id))
            return {"state": "created"}

    def read(self, operation_id: str = "") -> dict | None:
        if not self.path.exists():
            return None
        db = connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute("SELECT * FROM restore_handles WHERE operation_id=?" if operation_id else
                             "SELECT * FROM restore_handles WHERE active=1", (operation_id,) if operation_id else ()).fetchone()
            return dict(row) if row else None
        finally:
            db.close()

    def bind(self, operation_id: str, digest: str) -> None:
        with self._transaction() as db:
            row = db.execute("SELECT active,payload_digest,receipt_json FROM restore_handles WHERE operation_id=?",
                             (operation_id,)).fetchone()
            if row is None or row["active"] != 1 or row["receipt_json"] or row["payload_digest"] not in ("", digest):
                raise RuntimeError("restore_handle_not_pending")
            with db.capacity_scope("accepted_result"):
                count = db.execute("UPDATE restore_handles SET payload_digest=? WHERE operation_id=? AND active=1 "
                                   "AND receipt_json='' AND payload_digest IN ('',?)", (digest, operation_id, digest)).rowcount
            if count != 1:
                raise RuntimeError("restore_handle_not_pending")

    def remember(self, operation_id: str, receipt: dict) -> dict:
        with self._transaction() as db:
            row = db.execute("SELECT * FROM restore_handles WHERE operation_id=?", (operation_id,)).fetchone()
            if row is None:
                raise RuntimeError("restore_handle_missing")
            if row["receipt_json"]:
                # Immutable known terminal; later timeout/unknown cannot demote it.
                return json.loads(row["receipt_json"])
            encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
            with db.capacity_scope("accepted_result", estimated_peak_bytes=256 * 1024 + 4 * len(encoded.encode("utf-8"))):
                db.execute("UPDATE restore_handles SET receipt_json=? WHERE operation_id=?", (encoded, operation_id))
            return receipt

    def acknowledge(self, operation_id: str) -> None:
        with self._transaction() as db:
            terminal = db.execute("SELECT 1 FROM restore_handles WHERE operation_id=? AND receipt_json<>''",
                                  (operation_id,)).fetchone()
            if terminal is None:
                raise RuntimeError("restore_handle_terminal_missing")
            with db.capacity_scope("maintenance"):
                count = db.execute("UPDATE restore_handles SET active=0 WHERE operation_id=? AND receipt_json<>''", (operation_id,)).rowcount
            if count != 1:
                raise RuntimeError("restore_handle_terminal_missing")
