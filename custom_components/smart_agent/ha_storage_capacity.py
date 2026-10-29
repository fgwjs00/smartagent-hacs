"""Capacity checks at HA file I/O, sharing the generated process policy."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import logging.handlers
import os
from pathlib import Path
import tempfile
import sys

from .storage_capacity import DEFAULT_ADMISSION, StorageCapacityError, WriteClass

_STORE_CLASS = ContextVar("ha_store_write_class", default=WriteClass.NORMAL)
_STORE_CONFIRMATION = ContextVar("ha_store_confirmation", default=None)
_FILE_OVERHEAD = 4096


@contextmanager
def ha_store_write_scope(write_class: str):
    """Only a verified existing replay operation may assign result priority."""
    token = _STORE_CLASS.set(WriteClass(write_class))
    try:
        yield
    finally:
        _STORE_CLASS.reset(token)


def atomic_write_bytes(path: str, body: bytes) -> None:
    """Preserve the previous file until a complete same-directory replacement."""
    target = Path(path)
    with DEFAULT_ADMISSION.reserve(target, len(body) + _FILE_OVERHEAD) as lease:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                for offset in range(0, len(body), 1024 * 1024):
                    lease.recheck(len(body) - offset + _FILE_OVERHEAD)
                    stream.write(body[offset:offset + 1024 * 1024])
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            primary = sys.exception()
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass  # Successful replace consumed only this invocation's temporary.
            except OSError:
                if primary is None:
                    raise
                primary.add_note("backup_temporary_cleanup_failed")


class CapacityTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Only this file sink pauses; rejection accounting never logs to itself."""
    def __init__(self, *args, **kwargs):
        kwargs["delay"] = True
        super().__init__(*args, **kwargs)
        self.capacity_deferred = 0

    def emit(self, record):
        try:
            encoded = (self.format(record) + self.terminator).encode(self.encoding or "utf-8", errors="backslashreplace")
            with DEFAULT_ADMISSION.reserve(self.baseFilename, len(encoded) + _FILE_OVERHEAD):
                super().emit(record)
        except StorageCapacityError:
            self.capacity_deferred += 1
        except Exception:
            self.handleError(record)  # Match logging.Handler's observable formatting/I/O boundary.

    def _open(self):
        Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
        return super()._open()


def _write_capacity_store(owner, writer, mode, body, category, confirmation) -> None:
    """Guard encoded bytes in the executor using the caller's captured scope."""
    from homeassistant.util.file import WriteError
    size = len(body.encode("utf-8")) if isinstance(body, str) else len(body)
    with DEFAULT_ADMISSION.reserve(owner.path, size + _FILE_OVERHEAD, write_class=category):
        try:
            writer(mode, body)
        except WriteError as exc:
            # Store normally logs WriteError and returns; critical callers must
            # observe that this document did not reach the file.
            raise RuntimeError("ha_store_write_unconfirmed") from exc
        if confirmation is not None and confirmation["owner"] is owner:
            confirmation["written"] = True


def create_capacity_store(hass, version: int, key: str):
    """Use HA's envelope and atomic writer, with checks at actual file I/O."""
    from homeassistant.helpers.storage import Store

    class CapacityStore(Store):
        def __init__(self):
            super().__init__(hass, version, key, atomic_writes=True)

        async def _async_write_data(self, data):
            # HA 2026.10.4 uses _write_prepared_data, not the newer dev _io.
            # Preserve Store's default event-loop serialization and envelope.
            from homeassistant.helpers.json import prepare_save_json
            if "data_func" in data:
                data["data"] = data.pop("data_func")()
            mode, body = prepare_save_json(data, encoder=self._encoder)
            await self.hass.async_add_executor_job(
                _write_capacity_store, self, super()._write_prepared_data,
                mode, body, _STORE_CLASS.get(), _STORE_CONFIRMATION.get())

        async def async_save(self, data):
            confirmation = {"owner": self, "written": False}
            token = _STORE_CONFIRMATION.set(confirmation)
            try:
                await super().async_save(data)
                if self._data is not None:
                    # Stopping normally defers async_save until final-write.
                    await self._async_handle_write_data()
                if not confirmation["written"]:
                    raise RuntimeError("ha_store_write_unconfirmed")
            finally:
                _STORE_CONFIRMATION.reset(token)

    return CapacityStore()
