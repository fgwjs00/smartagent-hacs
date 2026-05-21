"""HA-side internal event bridge for the P1 add-on storage migration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)

LogCallback = Callable[[str, str], None]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InternalEventBridge:
    """Bounded async queue that posts HA storage events to the add-on."""

    def __init__(
        self,
        addon_client: Any,
        *,
        log_callback: LogCallback | None = None,
        maxsize: int = 1000,
        warn_threshold: int = 100,
        monitor_interval: float = 60.0,
    ) -> None:
        self._addon_client = addon_client
        self._log_callback = log_callback
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max(1, int(maxsize)))
        self._warn_threshold = max(1, int(warn_threshold))
        self._monitor_interval = max(1.0, float(monitor_interval))
        self._worker_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._posted = 0
        self._failed = 0
        self._dropped = 0

    @property
    def stats(self) -> dict[str, int]:
        return {
            "queued": self._queue.qsize(),
            "posted": self._posted,
            "failed": self._failed,
            "dropped": self._dropped,
        }

    def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._worker_task = asyncio.ensure_future(self._worker_loop())
        self._monitor_task = asyncio.ensure_future(self._monitor_loop())

    async def stop(self) -> None:
        for task in (self._monitor_task, self._worker_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._monitor_task = None
        self._worker_task = None

    def enqueue(self, kind: str, payload: dict[str, Any], *, ts: str | None = None) -> bool:
        item = {
            "kind": str(kind or "").strip(),
            "payload": dict(payload or {}),
            "ts": str(ts or _now_iso()),
            "attempts": 0,
        }
        try:
            self._queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
                self._dropped += 1
            except asyncio.QueueEmpty:
                pass
            try:
                self._queue.put_nowait(item)
                self._warn(
                    f"[P1] internal event queue full; dropped oldest event "
                    f"(dropped={self._dropped}, queued={self._queue.qsize()})"
                )
                return True
            except asyncio.QueueFull:
                self._dropped += 1
                self._warn("[P1] internal event queue full; failed to enqueue latest event")
                return False

    async def _worker_loop(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                ok = await self._post_item(item)
                if ok:
                    self._posted += 1
                else:
                    self._failed += 1
                    await self._retry_later(item)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._failed += 1
                self._warn(f"[P1] internal event post failed: {exc}")
                await self._retry_later(item)
            finally:
                self._queue.task_done()

    async def _post_item(self, item: dict[str, Any]) -> bool:
        result = await self._addon_client.post_internal_event(
            str(item.get("kind") or ""),
            dict(item.get("payload") or {}),
            ts=str(item.get("ts") or _now_iso()),
        )
        if not isinstance(result, dict):
            return False
        status = int(result.get("__status") or result.get("status") or 200)
        return status < 400 and result.get("ok") is not False

    async def _retry_later(self, item: dict[str, Any]) -> None:
        attempts = int(item.get("attempts") or 0) + 1
        item["attempts"] = attempts
        await asyncio.sleep(min(30.0, float(attempts)))
        self.enqueue(str(item.get("kind") or ""), dict(item.get("payload") or {}), ts=str(item.get("ts") or ""))

    async def _monitor_loop(self) -> None:
        while True:
            await asyncio.sleep(self._monitor_interval)
            queued = self._queue.qsize()
            if queued > self._warn_threshold:
                self._warn(f"[P1] internal event queue backlog high: queued={queued}")

    def _warn(self, message: str) -> None:
        if self._log_callback:
            try:
                self._log_callback("WARN", message)
                return
            except Exception:
                pass
        _LOGGER.warning(message)
