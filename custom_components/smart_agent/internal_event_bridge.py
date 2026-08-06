"""HA-side internal event bridge for the P1 add-on storage migration."""
from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import UTC, datetime
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)

LogCallback = Callable[[str, str], None]
_ENVELOPE_VERSION = 1
_TRANSPORT = "ha_internal_event_bridge"


def _now_iso() -> str:
    try:
        from homeassistant.util import dt as dt_util

        return dt_util.now().isoformat()
    except Exception:
        return datetime.now(UTC).isoformat()


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
        now_provider: Callable[[], Any] | None = None,
    ) -> None:
        self._addon_client = addon_client
        self._log_callback = log_callback
        self._now_provider = now_provider
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max(1, int(maxsize)))
        self._warn_threshold = max(1, int(warn_threshold))
        self._monitor_interval = max(1.0, float(monitor_interval))
        self._worker_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._retry_tasks: set[asyncio.Task] = set()
        self._posted = 0
        self._failed = 0
        self._dropped = 0
        self._seq = 0

    @property
    def stats(self) -> dict[str, int]:
        return {
            "queued": self._queue.qsize(),
            "posted": self._posted,
            "failed": self._failed,
            "dropped": self._dropped,
            "retrying": len(self._retry_tasks),
        }

    def _default_ts(self) -> str:
        provider = self._now_provider
        if callable(provider):
            try:
                value = provider()
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if hasattr(value, "isoformat"):
                    return value.isoformat()
            except Exception:
                pass
        return _now_iso()

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _client_accepts_envelope_headers(self) -> bool:
        method = getattr(self._addon_client, "post_internal_event", None)
        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            return True
        parameters = signature.parameters
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
            return True
        return "envelope_version" in parameters and "transport" in parameters and "seq" in parameters

    def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._worker_task = asyncio.ensure_future(self._worker_loop())
        self._monitor_task = asyncio.ensure_future(self._monitor_loop())

    async def stop(self) -> None:
        tasks = [
            task
            for task in (
                self._monitor_task,
                self._worker_task,
                *tuple(self._retry_tasks),
            )
            if task is not None
        ]
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._retry_tasks.clear()
        self._monitor_task = None
        self._worker_task = None

    def _build_item(self, kind: str, payload: dict[str, Any], *, ts: str | None = None) -> dict[str, Any]:
        return {
            "kind": str(kind or "").strip(),
            "payload": dict(payload or {}),
            "ts": str(ts or self._default_ts()),
            "envelope_version": _ENVELOPE_VERSION,
            "transport": _TRANSPORT,
            "seq": self._next_seq(),
            "attempts": 0,
        }

    def enqueue(self, kind: str, payload: dict[str, Any], *, ts: str | None = None) -> bool:
        item = self._build_item(kind, payload, ts=ts)
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
                    self._schedule_retry(item)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._failed += 1
                self._warn(f"[P1] internal event post failed: {exc}")
                self._schedule_retry(item)
            finally:
                self._queue.task_done()

    @staticmethod
    def _normalize_persistence_receipt(
        result: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, int]:
        if not isinstance(result, dict):
            return None, 502
        nested_receipt = result.get("result")
        receipt = (
            {**result, **nested_receipt}
            if isinstance(nested_receipt, dict)
            else dict(result)
        )
        if result.get("ok") is False:
            receipt["ok"] = False
        try:
            status = int(result.get("__status") or result.get("status") or 200)
        except (TypeError, ValueError):
            status = 502
        return receipt, status


    async def post_confirmed(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        ts: str | None = None,
    ) -> dict[str, Any]:
        """Post one event directly and return the Add-on persistence receipt."""
        item = self._build_item(kind, payload, ts=ts)
        result = await self._post_item_result(item)
        receipt, status = self._normalize_persistence_receipt(result)
        if receipt is None:
            return {"ok": False, "status": 502, "error": "invalid_addon_persistence_receipt"}
        if status >= 400 or receipt.get("ok") is not True:
            return {**receipt, "ok": False, "status": status}
        return {**receipt, "ok": True, "status": status, "persistence_confirmed": True}

    async def _post_item_result(self, item: dict[str, Any]) -> dict[str, Any] | None:
        kwargs: dict[str, Any] = {"ts": str(item.get("ts") or self._default_ts())}
        if self._client_accepts_envelope_headers():
            kwargs.update(
                {
                    "envelope_version": int(item.get("envelope_version") or _ENVELOPE_VERSION),
                    "transport": str(item.get("transport") or _TRANSPORT),
                    "seq": int(item.get("seq") or 0),
                }
            )
        result = await self._addon_client.post_internal_event(
            str(item.get("kind") or ""),
            dict(item.get("payload") or {}),
            **kwargs,
        )
        return result if isinstance(result, dict) else None

    async def _post_item(self, item: dict[str, Any]) -> bool:
        result = await self._post_item_result(item)
        receipt, status = self._normalize_persistence_receipt(result)
        return receipt is not None and status < 400 and receipt.get("ok") is True

    def _schedule_retry(self, item: dict[str, Any]) -> None:
        attempts = int(item.get("attempts") or 0) + 1
        item["attempts"] = attempts

        async def _requeue_after_delay() -> None:
            await asyncio.sleep(min(30.0, float(attempts)))
            self._enqueue_retry_item(item)

        task = asyncio.ensure_future(_requeue_after_delay())
        self._retry_tasks.add(task)
        task.add_done_callback(self._retry_tasks.discard)

    def _enqueue_retry_item(self, item: dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(item)
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
            except asyncio.QueueFull:
                self._dropped += 1
                self._warn("[P1] internal event queue full; failed to enqueue retry event")

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
