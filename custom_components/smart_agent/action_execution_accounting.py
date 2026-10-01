"""Explicit transaction writers for immediate and delayed action receipts."""

from __future__ import annotations
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from .database_transactions import mark_transaction_audit
from .action_execution_context import (
    ActionBatchContext,
    ActionExecutionProgress,
    ActionPreparationState,
)


@dataclass(frozen=True, slots=True)
class ActionReceiptWriter:
    transaction_id: int
    results: list[dict[str, Any]]
    complete: Callable[..., Any]
    run_in_executor: Callable[..., Any]

    def _counts(self) -> tuple[int, int, int]:
        executed = sum(1 for item in self.results if item.get("status") == "ok")
        blocked = sum(
            1
            for item in self.results
            if str(item.get("status") or "").startswith("blocked")
            and item.get("status") != "blocked_or_error"
        )
        failed = sum(1 for item in self.results if item.get("status") == "blocked_or_error")
        return executed, blocked, failed

    async def refresh(self) -> None:
        executed, blocked, failed = self._counts()
        confirmed = await self.run_in_executor(
            self.complete,
            self.transaction_id,
            executed,
            blocked,
            failed,
            json.dumps(self.results, ensure_ascii=False),
        )
        mark_transaction_audit(self.results, confirmed is True)

    def refresh_sync(self) -> None:
        executed, blocked, failed = self._counts()
        confirmed = self.complete(
            self.transaction_id,
            executed,
            blocked,
            failed,
            json.dumps(self.results, ensure_ascii=False),
        )
        mark_transaction_audit(self.results, confirmed is True)


def pop_service_error(
    host: Any, transaction_id: int, action_seq: int, entity_id: str
) -> dict[str, Any]:
    detail = host._pop_service_call_error(transaction_id, action_seq, entity_id)
    if detail:
        return detail
    return {
        "msg": "ha_service_returned_false",
        "error": "ha_service_returned_false",
        "error_type": "ha_service_unknown_failure",
        "ha_command_status": "failed",
    }


async def finish_action_transaction(
    host: Any,
    preparation: ActionPreparationState,
    batch: ActionBatchContext,
    progress: ActionExecutionProgress,
) -> Any:
    for (position, _raw, _action), result in zip(
        preparation.normalized_actions, progress.results[progress.guard_result_count :]
    ):
        preparation.collector.remember(position, result)
    progress.results[:] = preparation.collector.ordered_results()
    if batch.correlation_id:
        for item in progress.results:
            item["correlation_id"] = batch.correlation_id
    if batch.transaction_id:
        confirmed = await host.hass.async_add_executor_job(
            host._complete_transaction_db,
            batch.transaction_id,
            progress.executed,
            progress.blocked,
            progress.failed,
            json.dumps(progress.results, ensure_ascii=False),
        )
        mark_transaction_audit(progress.results, confirmed is True)
    return host._action_execution_result(
        progress.executed,
        transaction_id=batch.transaction_id,
        results=progress.results,
        pre_states=preparation.pre_states,
        correlation_id=batch.correlation_id,
    )
