"""Ordered action-batch orchestration. All physical calls stay on ActionsMixin."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from functools import partial
from typing import Any
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from .admin_actor import AuthenticatedOwnerSession
from .action_receipts import ActionResultCollector
from .action_execution_context import (
    ActionBatchContext,
    ActionPreparationState,
    ActionGuardContext,
    ActionExecutionProgress,
    DelayedActionCallbacks,
)
from .action_execution_accounting import (
    ActionReceiptWriter,
    finish_action_transaction,
    pop_service_error,
)
from .action_execution_batch import execute_prepared_batch
from .action_execution_dispatch import execute_or_schedule_action
from .action_execution_guards import apply_initial_batch_guards
from .action_execution_items import prepare_action_item, evaluate_action_shape
from .action_execution_policy import evaluate_before_router, evaluate_after_router
from .action_execution_preparation import prepare_action_transaction
from .action_execution_router import route_action
from .action_execution_showroom import collect_showroom_evidence


class ActionExecutionRuntimeMixin:
    """Orchestrate one guarded action batch without owning the HA transport."""

    async def _execute_actions(
        self,
        actions: list,
        trigger_summary: str = "",
        scene_desc: str = "",
        confidence: int = 0,
        trigger_room: str = "",
        is_global_cmd: bool = False,
        cmd_source: str = "",
        parent_transaction_id: str = "",
        world_snapshot_id: str = "",
        correlation_id: str = "",
        active_space_id: str = "",
        decision_time: str = "",
        require_world_snapshot_guard: bool = False,
        direct_entity_only: bool = False,
        decision_contract_lineage: dict[str, Any] | None = None,
        user_intent_authority: Any | None = None,
    ) -> int:
        """Execute existing guards, service preparation and transaction accounting in order."""
        correlation_id = str(correlation_id or "").strip()
        if not actions:
            return self._action_execution_result(0, correlation_id=correlation_id)

        original_actions = list(actions)
        result_collector = ActionResultCollector(original_actions, correlation_id=correlation_id)
        user_explicit = cmd_source == "USER_EXPLICIT"
        authenticated_user_intent = bool(
            user_explicit and type(user_intent_authority) is AuthenticatedOwnerSession
        )
        lineage = decision_contract_lineage if isinstance(decision_contract_lineage, dict) else {}
        decision_transaction_id = str(lineage.get("decision_transaction_id") or "").strip()
        decision_linked_batch = bool(
            require_world_snapshot_guard
            and not user_explicit
            and decision_transaction_id
            and len(original_actions) > 1
        )
        preparation = ActionPreparationState(original_actions, actions, result_collector)
        batch = ActionBatchContext(
            scene_desc=scene_desc,
            trigger_summary=trigger_summary,
            transaction_id=0,
            parent_transaction_id=parent_transaction_id,
            world_snapshot_id=world_snapshot_id,
            correlation_id=correlation_id,
            active_space_id=active_space_id,
            decision_time=decision_time,
            cmd_source=cmd_source,
            require_world_snapshot_guard=require_world_snapshot_guard,
            decision_contract_lineage=decision_contract_lineage,
            user_intent_authority=user_intent_authority,
            trigger_room=trigger_room,
            is_global_cmd=is_global_cmd,
            confidence=confidence,
            authenticated_user_intent=authenticated_user_intent,
        )
        guard_result = await apply_initial_batch_guards(self, preparation, batch)
        if guard_result is not None:
            return guard_result
        start = await prepare_action_transaction(
            self,
            preparation,
            batch,
            decision_linked_batch=decision_linked_batch,
            decision_transaction_id=decision_transaction_id,
        )
        if start.failure_result is not None:
            return start.failure_result

        results = result_collector.ordered_results()
        progress = ActionExecutionProgress(results, len(results), len(results))
        batch = replace(
            batch,
            transaction_id=start.transaction_id,
            parent_transaction_id=str(parent_transaction_id or "").strip(),
        )
        showroom_evidence = await collect_showroom_evidence(self)
        # Preserve the existing Zigbee pacing for batches larger than five actions.
        pacing_delay = 0.2 if len(preparation.actions) > 5 else 0.0
        writer = ActionReceiptWriter(
            batch.transaction_id,
            results,
            self._complete_transaction_db,
            self.hass.async_add_executor_job,
        )
        delayed_callbacks = DelayedActionCallbacks(
            writer.refresh, writer.refresh_sync, partial(pop_service_error, self)
        )

        for index, (position, raw, action) in enumerate(preparation.normalized_actions):
            if index > 0 and pacing_delay > 0:
                await asyncio.sleep(pacing_delay)
            item = prepare_action_item(self, batch, action, position)
            outcome = evaluate_action_shape(self, item, raw, action)
            if outcome is not None:
                progress.record_guard(outcome, position)
                continue
            guard_context = ActionGuardContext(
                batch, item.call, item.receipt, original_actions, action_seq=item.action_seq
            )
            outcome = evaluate_before_router(self, guard_context)
            if outcome is not None:
                progress.record_guard(outcome, position)
                continue
            routing_result = route_action(self, guard_context, direct_entity_only=direct_entity_only)
            if routing_result is not None:
                progress.record_guard(routing_result, position)
                continue
            outcome = await evaluate_after_router(self, guard_context, showroom_evidence)
            if outcome is not None:
                progress.record_guard(outcome, position)
                continue
            await execute_or_schedule_action(
                self,
                item,
                batch,
                progress,
                delayed_callbacks,
                decision_linked_batch=decision_linked_batch,
                schedule=async_call_later,
                decorate=callback,
            )

        if decision_linked_batch:
            outcome = await execute_prepared_batch(
                self, preparation, batch, progress.prepared_batch_calls,
                preparation_failures=progress.preparation_failures,
            )
            if outcome.rejection is not None:
                return outcome.rejection
            progress.results = outcome.results
            progress.executed, progress.blocked, progress.failed = (
                outcome.executed,
                outcome.blocked,
                outcome.failed,
            )
        return await finish_action_transaction(self, preparation, batch, progress)


__all__ = ["ActionExecutionRuntimeMixin"]
