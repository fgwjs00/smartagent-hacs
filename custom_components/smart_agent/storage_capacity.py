# Generated from contracts/python/storage_capacity.py; do not edit.
"""Local managed-writer admission, not a filesystem or cross-process quota.

Callers validate accepted-result identity and supply a conservative peak estimate.
SQLite uses its authorizer (including triggers), never SQL-prefix classification.
One SQL operation can exceed its estimate; native extensions, SQLite temporary
sort files and writers outside this adapter remain outside this admission bound.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from collections import OrderedDict
from enum import StrEnum
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import weakref

MiB = 1024 * 1024
DEFAULT_SQL_PEAK = 256 * 1024


class WriteClass(StrEnum):
    NORMAL = "normal"
    ACCEPTED_RESULT = "accepted_result"
    MAINTENANCE = "maintenance"


class StorageCapacityError(sqlite3.OperationalError):
    """Admission failed before this statement; no implied transaction rollback."""

    def __init__(self, reason: str):
        self.code, self.retryable = "storage_capacity", True
        self.reason = reason
        super().__init__("storage_capacity: " + reason)


class CapacityLedger:
    """Share between policies for one process; no persistent allocation claim."""

    def __init__(self):
        self.lock = threading.RLock()
        self.volumes = {}


_PROCESS_LEDGER = CapacityLedger()


def _existing_parent(path):
    parent = Path(path).absolute()
    while True:
        try:
            metadata = parent.stat()  # Follows symlinks; no repeated path-component walk.
        except FileNotFoundError:
            if parent == parent.parent:
                raise
            parent = parent.parent
            continue
        return parent if stat.S_ISDIR(metadata.st_mode) else parent.parent


def _nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(name + " must be a nonnegative integer")
    return value


class StorageAdmission:
    def __init__(self, *, reserve_bytes=64 * MiB, emergency_bytes=16 * MiB,
                 hysteresis_bytes=16 * MiB, free_bytes=None, volume_key=None, ledger=None):
        self.reserve_bytes = _nonnegative(reserve_bytes, "reserve_bytes")
        self.emergency_bytes = _nonnegative(emergency_bytes, "emergency_bytes")
        self.hysteresis_bytes = _nonnegative(hysteresis_bytes, "hysteresis_bytes")
        if not 0 < emergency_bytes < reserve_bytes:
            raise ValueError("require 0 < emergency_bytes < reserve_bytes")
        self._free = free_bytes or (lambda path: shutil.disk_usage(path).free)
        self._volume = volume_key or (lambda path: os.stat(path).st_dev)
        self._ledger = ledger if ledger is not None else _PROCESS_LEDGER

    def reserve(self, target_path, estimated_peak_bytes, write_class=WriteClass.NORMAL):
        return CapacityLease(self, target_path, estimated_peak_bytes, WriteClass(write_class))

    def _observe(self, target_path):
        try:
            parent = _existing_parent(target_path)
            key = self._volume(parent)
            free = _nonnegative(self._free(parent), "free_bytes")
            return key, free
        except (OSError, ValueError, TypeError) as exc:
            raise StorageCapacityError("measurement_unavailable") from exc

    def _check(self, lease, amount, write_class):
        key, free = self._observe(lease.target_path)
        if lease.active and key != lease.volume:
            raise StorageCapacityError("target_volume_changed")
        state = self._ledger.volumes.setdefault(key, {"inflight": 0, "pressure": False})
        own = lease.amount if lease.active else 0
        available = free - (state["inflight"] - own)
        if available < self.reserve_bytes:
            state["pressure"] = True
        elif available >= self.reserve_bytes + self.hysteresis_bytes:
            state["pressure"] = False
        threshold = self.emergency_bytes
        if write_class == WriteClass.NORMAL:
            threshold = self.reserve_bytes + (self.hysteresis_bytes if state["pressure"] else 0)
        if available - amount < threshold:
            reason = "normal_headroom_insufficient" if write_class == WriteClass.NORMAL else "emergency_headroom_insufficient"
            raise StorageCapacityError(reason)
        state["inflight"] += amount - own
        lease.volume, lease.amount, lease.active = key, amount, True

    def snapshot(self, target_path):
        with self._ledger.lock:
            key, free = self._observe(target_path)
            state = self._ledger.volumes.get(key, {"inflight": 0, "pressure": False})
            return {"filesystem_free_bytes": free, "inflight_estimated_bytes": state["inflight"],
                    "reserve_bytes": self.reserve_bytes, "emergency_bytes": self.emergency_bytes,
                    "hysteresis_bytes": self.hysteresis_bytes, "pressure_latched": state["pressure"],
                    "admission_enabled": True, "physical_quota_enforced": False}


class CapacityLease:
    def __init__(self, admission, target_path, amount, write_class):
        self.admission, self.target_path, self.write_class = admission, target_path, write_class
        self.amount = _nonnegative(amount, "estimated_peak_bytes")
        self.active, self.volume, self._entered = False, None, False

    def __enter__(self):
        with self.admission._ledger.lock:
            if self._entered:
                raise RuntimeError("capacity lease cannot be reused")
            self.admission._check(self, self.amount, self.write_class)
            self._entered = True
        return self

    def recheck(self, remaining_peak_bytes=None, *, write_class=None):
        with self.admission._ledger.lock:
            if not self.active:
                raise RuntimeError("capacity lease is not active")
            amount = self.amount if remaining_peak_bytes is None else _nonnegative(remaining_peak_bytes, "remaining_peak_bytes")
            category = self.write_class if write_class is None else WriteClass(write_class)
            self.admission._check(self, amount, category)

    def release(self):
        with self.admission._ledger.lock:
            if self.active:
                self.admission._ledger.volumes[self.volume]["inflight"] -= self.amount
                self.active = False

    def __exit__(self, *_args):
        self.release()


DEFAULT_ADMISSION = StorageAdmission()
_READ_ACTIONS = {sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION,
                 sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT,
                 sqlite3.SQLITE_RECURSIVE, sqlite3.SQLITE_DETACH}
_READ_PRAGMAS = frozenset("table_info table_xinfo table_list index_info index_xinfo index_list "
                         "foreign_key_list foreign_key_check integrity_check quick_check "
                         "database_list compile_options pragma_list function_list module_list collation_list".split())
_CONNECTION_PRAGMAS = frozenset("busy_timeout cache_size cache_spill mmap_size synchronous "
                               "foreign_keys defer_foreign_keys recursive_triggers query_only "
                               "trusted_schema read_uncommitted temp_store threads".split())
_ACTION_PRAGMAS = frozenset("wal_checkpoint optimize incremental_vacuum shrink_memory".split())


def _disk_target(database, uri=False):
    name = os.fsdecode(database)
    if uri and name.startswith("file:"):
        parts = urlsplit(name)
        if parse_qs(parts.query).get("mode") == ["memory"]:
            return None
        name = unquote(parts.path)
        if parts.netloc and parts.netloc != "localhost":
            name = "//" + parts.netloc + name
        if os.name == "nt" and len(name) > 2 and name[0] == "/" and name[2] == ":":
            name = name[1:]
    if name == ":memory:":
        return None
    return Path(name).absolute() if name else Path(tempfile.gettempdir())


def _read_only_uri(database, uri):
    name = os.fsdecode(database)
    if not uri or not name.startswith("file:"):
        return False
    return parse_qs(urlsplit(name).query).get("mode") == ["ro"]


def _is_write(action, first, second):
    if action in _READ_ACTIONS:
        return False
    if action != sqlite3.SQLITE_PRAGMA:
        return True
    pragma = (first or "").lower()
    if pragma in _READ_PRAGMAS or pragma in _CONNECTION_PRAGMAS:
        return False
    return second is not None or pragma in _ACTION_PRAGMAS


class _Statement:
    def __init__(self, write_class, estimate):
        self.write_class, self.estimate = write_class, estimate
        self.leases, self.error, self.wrote = {}, None, False
        self.actions, self.failed = set(), False

    def reject(self, error):
        # Authorizer must return a SQLite code; the execution boundary rethrows
        # this typed error instead of swallowing it inside SQLite's callback.
        self.error = error
        return sqlite3.SQLITE_DENY


def _release(leases):
    for lease in leases.values():
        lease.release()
    leases.clear()


class CapacityConnection(sqlite3.Connection):
    """Standard SQLite connection with admission on SQL execution surfaces.

    capacity_scope is service-owned, not an authorization mechanism. User
    authorizers still run and set_authorizer(None) only removes the user's hook.
    """

    def __init__(self, database, *args, admission=None, estimated_peak_bytes=DEFAULT_SQL_PEAK, **kwargs):
        self._admission = admission if admission is not None else DEFAULT_ADMISSION
        self._estimate = _nonnegative(estimated_peak_bytes, "estimated_peak_bytes")
        self._target = _disk_target(database, kwargs.get("uri", args[6] if len(args) > 6 else False))
        self._capacity_lock, self._frames = threading.RLock(), []
        self._transaction_leases, self._extra_paths = {}, set()
        self._has_attachments = False
        self._profiles = OrderedDict()
        self._capacity_cursors = weakref.WeakSet()
        self._user_authorizer = None
        self._capacity_context = ContextVar("sqlite_capacity", default=(WriteClass.NORMAL, self._estimate))
        self._read_only_main = _read_only_uri(database, kwargs.get("uri", args[6] if len(args) > 6 else False))
        creation = self._admission.reserve(self._target, self._estimate) if self._target and not self._read_only_main and not self._target.exists() else nullcontext()
        with creation:
            super().__init__(database, *args, **kwargs)
        self._paths = {"main": self._target, "temp": None}
        sqlite3.Connection.set_authorizer(self, self._authorize)

    @contextmanager
    def capacity_scope(self, write_class=WriteClass.NORMAL, *, estimated_peak_bytes=None):
        estimate = self._estimate if estimated_peak_bytes is None else _nonnegative(estimated_peak_bytes, "estimated_peak_bytes")
        token = self._capacity_context.set((WriteClass(write_class), estimate))
        try:
            yield self
        finally:
            self._capacity_context.reset(token)

    def set_authorizer(self, authorizer_callback):
        with self._capacity_lock:
            self._user_authorizer = authorizer_callback
            sqlite3.Connection.set_authorizer(self, self._authorize)

    def _authorize(self, action, first, second, database, source):
        result = sqlite3.SQLITE_OK
        if self._user_authorizer is not None:
            result = self._user_authorizer(action, first, second, database, source)
            if result == sqlite3.SQLITE_DENY:
                return result
        if not _is_write(action, first, second):
            return result
        if not self._frames:
            return sqlite3.SQLITE_DENY
        frame = self._frames[-1]
        try:
            frame.actions.add((action, first, database))
            self._admit_action(frame, action, first, database)
        except StorageCapacityError as exc:
            return frame.reject(exc)
        return result

    def _admit_action(self, frame, action, first, database):
        if action == sqlite3.SQLITE_ALTER_TABLE:
            database = first
        elif action == sqlite3.SQLITE_PRAGMA and database is None:
            database = "main"
        if self._read_only_main and database == "main":
            # SQLite supplies the native readonly error/code. This main cannot
            # grow; writable ATTACH targets still pass their own admission.
            return
        frame.wrote = True
        if action == sqlite3.SQLITE_ATTACH:
            if first is None:
                raise StorageCapacityError("attachment_target_unresolved")
            target = _disk_target(first or "", True)
            self._has_attachments = True
            if target is not None:
                self._extra_paths.add(target)
            paths = [target]
        elif database in self._paths:
            paths = [self._paths[database]]
        else:
            paths = [self._target, *self._extra_paths]
        for path in paths:
            if path is not None:
                self._admit_path(frame, path)

    def _admit_path(self, frame, path):
        key = str(path)
        lease = frame.leases.get(key) or self._transaction_leases.get(key)
        if lease is None:
            lease = self._admission.reserve(path, frame.estimate, frame.write_class).__enter__()
        else:
            lease.recheck(max(lease.amount, frame.estimate), write_class=frame.write_class)
        frame.leases[key] = lease

    def _refresh_paths(self):
        # Outside authorizer: SQLite forbids changing the connection in its callback.
        if not self._has_attachments:
            return
        cursor = sqlite3.Connection.cursor(self)
        cursor.row_factory = None
        try:
            for _, name, filename in sqlite3.Cursor.execute(cursor, "PRAGMA database_list"):
                self._paths[name] = Path(filename) if filename else None
        finally:
            cursor.close()

    def _invoke(self, cursor, method, operation, *args):
        with self._capacity_lock:
            cursor._release_pending()
            frame = _Statement(*self._capacity_context.get())
            self._frames.append(frame)
            try:
                if args[0] not in self._profiles:
                    # A profile may have been evicted while SQLite retained its
                    # prepared statement. A miss must force SQLite to teach us.
                    sqlite3.Connection.set_authorizer(self, self._authorize)
                self._refresh_paths()
                # Keep SQLite's statement cache. Replay only the write targets
                # learned from its authorizer, with fresh admission on every call.
                # Schema recompilation invokes the authorizer for any new targets.
                known_actions = self._profiles.get(args[0], ())
                # A rejected target must not erase later targets from an already
                # compiled statement. Seed the entire profile before any check.
                frame.actions.update(known_actions)
                for action in known_actions:
                    self._admit_action(frame, *action)
                if method == "executemany":
                    args = (args[0], self._checked_parameters(frame, args[1]))
                return operation(*args)
            except BaseException as exc:
                frame.failed = True
                if frame.error is not None:
                    raise frame.error from exc
                raise
            finally:
                self._frames.pop()
                self._profiles[args[0]] = tuple(frame.actions)
                self._profiles.move_to_end(args[0])
                if len(self._profiles) > 256:
                    self._profiles.popitem(last=False)
                self._finish_statement(cursor, frame, method)

    def _checked_parameters(self, frame, parameters):
        for params in parameters:
            for lease in frame.leases.values():
                lease.recheck(write_class=frame.write_class)
            yield params

    def _finish_statement(self, cursor, frame, method):
        if self.in_transaction:
            self._transaction_leases.update(frame.leases)
        elif method == "execute" and frame.wrote and cursor.description is not None and not frame.failed:
            cursor._pending_leases = frame.leases
            self._transaction_leases = {k: v for k, v in self._transaction_leases.items() if k not in frame.leases}
            _release(self._transaction_leases)
        else:
            _release(frame.leases)
            if not self.in_transaction:
                _release(self._transaction_leases)

    def cursor(self, factory=None):
        chosen = factory or CapacityCursor
        if not issubclass(chosen, CapacityCursor):
            chosen = type("Capacity" + chosen.__name__, (CapacityCursor, chosen), {})
        cursor = super().cursor(chosen)
        self._capacity_cursors.add(cursor)
        return cursor

    def execute(self, sql, parameters=()):
        return self.cursor().execute(sql, parameters)

    def executemany(self, sql, parameters):
        return self.cursor().executemany(sql, parameters)

    def executescript(self, sql_script):
        return self.cursor().executescript(sql_script)

    def _control(self, operation, *args):
        with self._capacity_lock:
            try:
                result = operation(*args)
                _release(self._transaction_leases)
                return result
            finally:
                if not self.in_transaction:
                    _release(self._transaction_leases)

    def commit(self):
        return self._control(super().commit)

    def rollback(self):
        return self._control(super().rollback)

    def __exit__(self, *args):
        return self._control(super().__exit__, *args)

    def close(self):
        with self._capacity_lock:
            try:
                super().close()
            finally:
                _release(self._transaction_leases)
                for cursor in self._capacity_cursors:
                    cursor._release_pending()


class CapacityCursor(sqlite3.Cursor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_leases = {}

    def _release_pending(self):
        _release(self._pending_leases)

    def execute(self, sql, parameters=()):
        return self.connection._invoke(self, "execute", super().execute, sql, parameters)

    def executemany(self, sql, parameters):
        return self.connection._invoke(self, "executemany", super().executemany, sql, parameters)

    def executescript(self, sql_script):
        return self.connection._invoke(self, "executescript", super().executescript, sql_script)

    def _fetch(self, operation, *args, all_rows=False):
        with self.connection._capacity_lock:
            try:
                result = operation(*args)
            except BaseException:
                self._release_pending()
                raise
            if all_rows or result is None or result == []:
                self._release_pending()
            return result

    def fetchone(self):
        return self._fetch(super().fetchone)

    def fetchmany(self, size=None):
        args = () if size is None else (size,)
        return self._fetch(super().fetchmany, *args)

    def fetchall(self):
        return self._fetch(super().fetchall, all_rows=True)

    def __next__(self):
        return self._fetch(super().__next__)

    def close(self):
        with self.connection._capacity_lock:
            try:
                super().close()
            finally:
                self._release_pending()

    def __del__(self):
        _release(getattr(self, "_pending_leases", {}))


def connect(database, timeout=5.0, detect_types=0, isolation_level="", check_same_thread=True,
            factory=CapacityConnection, cached_statements=128, uri=False, *,
            autocommit=getattr(sqlite3, "LEGACY_TRANSACTION_CONTROL", -1), admission=None,
            estimated_peak_bytes=DEFAULT_SQL_PEAK):
    """sqlite3.connect signature plus policy/estimate, with ordinary DB-API types."""
    chosen = factory
    if not issubclass(chosen, CapacityConnection):
        chosen = type("Capacity" + chosen.__name__, (CapacityConnection, chosen), {})

    def create(*args, **kwargs):
        return chosen(*args, admission=admission, estimated_peak_bytes=estimated_peak_bytes, **kwargs)

    options = {"autocommit": autocommit} if hasattr(sqlite3, "LEGACY_TRANSACTION_CONTROL") else {}
    if not options and autocommit != -1:
        raise ValueError("autocommit requires Python 3.12 or newer")
    return sqlite3.connect(database, timeout, detect_types, isolation_level, check_same_thread,
                           create, cached_statements, uri, **options)
