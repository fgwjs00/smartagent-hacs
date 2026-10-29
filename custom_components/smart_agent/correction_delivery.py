"""One recent-action feedback handle; durable evidence lives in the existing outbox."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import logging

_LOGGER = logging.getLogger(__name__)


class _PendingCorrection(dict):
    """Recent actions are JSON responses; runtime handles stay off their fields."""
    def __init__(self, payload: dict) -> None:
        super().__init__(payload=deepcopy(payload))
        self.lock = asyncio.Lock()
        self.admission: asyncio.Task | None = None


def _admission_done(pending: _PendingCorrection, task: asyncio.Task) -> None:
    """Capture executor completion even if its caller was cancelled repeatedly."""
    pending.admission = None
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        _LOGGER.warning("operation=correction_delivery.admission exception_type=%s outcome=not_admitted",
                        type(error).__name__)
        return
    pending["frozen"] = task.result()


async def submit_correction(bridge, recent: dict, payload: dict) -> dict:
    pending = recent.get("_correction_delivery")
    if pending is None:
        pending = _PendingCorrection(payload)
        recent["_correction_delivery"] = pending
    if pending["payload"] != payload:
        return {"ok": False, "error": "original_correction_pending"}
    async with pending.lock:
        if "confirmed" in pending:
            return pending["confirmed"]
        if "frozen" not in pending:
            if pending.admission is None:
                admission = asyncio.create_task(asyncio.to_thread(bridge.prepare_correction, payload))
                pending.admission = admission
                admission.add_done_callback(lambda task: _admission_done(pending, task))
            pending["frozen"] = await asyncio.shield(pending.admission)
        result = await bridge.post_confirmed("correction", pending["frozen"])
        if result.get("ok") is True and result.get("persistence_confirmed") is True:
            pending["confirmed"] = result
        return result


async def confirm_correction(bridge, recent: dict, payload: dict, recent_actions: dict) -> bool:
    """A service may clear its context only after the bound durable Add-on ACK."""
    try:
        result = await submit_correction(bridge, recent, payload)
    except Exception as exc:
        _LOGGER.warning("operation=correction_delivery.confirm exception_type=%s outcome=unconfirmed",
                        type(exc).__name__)
        return False
    if result.get("ok") is not True or result.get("persistence_confirmed") is not True:
        return False
    entity_id = payload["entity_id"]
    if recent_actions.get(entity_id) is recent:
        recent_actions.pop(entity_id, None)
    return True


async def clear_correction_prompt(coordinator) -> None:
    await asyncio.sleep(5)
    coordinator.last_correction_text = ""
    coordinator.async_set_updated_data({})
