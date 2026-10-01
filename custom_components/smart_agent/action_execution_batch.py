"""Decision-linked batch dispatch and receipt accounting through the existing sink."""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any
from .action_execution_context import ActionBatchContext, ActionPreparationState
from .action_execution_diagnostics import action_failure_details
from .action_normalization import action_domain, action_entity_id


@dataclass(frozen=True, slots=True)
class BatchDispatchResult:
    results: list[dict[str, Any]]
    executed: int = 0
    blocked: int = 0
    failed: int = 0
    rejection: Any = None


def _preparation_complete(state: ActionPreparationState, prepared: list[dict[str, Any]]) -> bool:
    return (
        len(prepared) == len(state.original_actions)
        and len(state.normalized_actions) == len(state.original_actions)
        and all(str(item.get("target_space_id") or "").strip() for item in prepared)
    )


async def _reject_incomplete_batch(
    host: Any, state: ActionPreparationState, context: ActionBatchContext,
    preparation_failures: dict[int, dict[str, Any]],
) -> BatchDispatchResult:
    reason = "decision_linked_batch_preparation_incomplete"
    lineage = (
        context.decision_contract_lineage
        if isinstance(context.decision_contract_lineage, dict)
        else {}
    )
    decision_id = str(lineage.get("decision_transaction_id") or "").strip()
    results = []
    failed = 0
    for position, raw in enumerate(state.original_actions):
        service = (
            str(raw.get("service") or raw.get("action") or raw.get("command") or "").strip()
            if isinstance(raw, dict)
            else ""
        )
        results.append(
            {
                "domain": str(action_domain(raw) or ""),
                "service": service.split(".", 1)[-1],
                "entity_id": str(action_entity_id(raw) or ""),
                "status": "blocked_decision_linked_batch_preparation_incomplete",
                "msg": reason,
                "error": reason,
                "error_type": reason,
                "ha_command_status": "not_dispatched",
                "decision_trace": {"decision_transaction_id": decision_id},
                **({"correlation_id": context.correlation_id} if context.correlation_id else {}),
                **preparation_failures.get(position, {}),
            }
        )
        failed += int(position in preparation_failures)
    await host.hass.async_add_executor_job(
        host._complete_transaction_db,
        context.transaction_id,
        0,
        len(results) - failed,
        failed,
        json.dumps(results, ensure_ascii=False),
    )
    rejection = host._action_execution_result(
        0,
        transaction_id=context.transaction_id,
        results=results,
        pre_states=state.pre_states,
        correlation_id=context.correlation_id,
    )
    return BatchDispatchResult(results, blocked=len(results)-failed, failed=failed, rejection=rejection)


async def _dispatch_batch(
    host: Any, prepared: list[dict[str, Any]], context: ActionBatchContext
) -> dict[str, Any]:
    commands = [
        {
            "entity_id": item["entity_id"],
            "domain": item["domain"],
            "service": item["service"],
            "data": dict(item["data"]),
        }
        for item in prepared
    ]
    target_spaces = [str(item["target_space_id"]).strip() for item in prepared]
    primary = prepared[0]
    try:
        return await host._execute_enveloped_service(
            primary["domain"],
            primary["service"],
            primary["entity_id"],
            primary["data"],
            context.scene_desc or "decision_linked_batch",
            context.transaction_id,
            int(primary["action_seq"]),
            world_snapshot_id=context.world_snapshot_id,
            active_space_id=context.active_space_id,
            decision_time=context.decision_time,
            target_space_id=primary["target_space_id"],
            cmd_source=context.cmd_source,
            require_world_snapshot_guard=True,
            decision_contract_lineage=context.decision_contract_lineage,
            commands_override=commands,
            target_space_ids_override=target_spaces,
            return_failed_result=True,
            correlation_id_override=context.correlation_id,
            user_intent_authority=context.user_intent_authority,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": "decision_linked_batch_dispatch_failed",
            "error_type": "decision_linked_batch_dispatch_failed",
            "status": "failed",
            "_smartagent_dispatch_failure": action_failure_details(
                context, int(primary["action_seq"]), exc,
                operation="decision_linked_batch_dispatch",
            ),
        }


def _validated_rows(response: dict[str, Any], expected_count: int) -> tuple[list[Any], Any]:
    rows = response.get("results")
    dispositions = response.get("_smartagent_receipt_dispositions")
    valid = (
        isinstance(rows, list)
        and len(rows) == expected_count
        and all(isinstance(row, dict) for row in rows)
        and isinstance(dispositions, list)
        and len(dispositions) == expected_count
    )
    return (rows if valid else [None] * expected_count), dispositions


def _receipt_context(prepared: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    result = dict(prepared["result_context"])
    if "_smartagent_dispatch_failure" in response:
        result.update(response["_smartagent_dispatch_failure"])
    if response.get("http_status") is not None:
        result["http_status"] = response["http_status"]
        result["request_id"] = response["request_id"]
    result.update(
        {
            "domain": prepared["domain"],
            "service": prepared["service"],
            "entity_id": prepared["entity_id"],
        }
    )
    if prepared["data"]:
        result["params"] = dict(prepared["data"])
    return result


async def _record_verified_success(
    host: Any, prepared: dict[str, Any], context: ActionBatchContext
) -> None:
    lineage = (
        context.decision_contract_lineage
        if isinstance(context.decision_contract_lineage, dict)
        else {}
    )
    await host._record_prepared_service_success(
        domain=prepared["domain"],
        service=prepared["service"],
        entity_id=prepared["entity_id"],
        params=dict(prepared["data"]),
        reason=prepared["reason"],
        scene_desc=context.scene_desc,
        trigger_text=context.trigger_summary,
        transaction_id=context.transaction_id,
        action_seq=int(prepared["action_seq"]),
        parent_transaction_id=context.parent_transaction_id,
        world_snapshot_id=context.world_snapshot_id,
        correlation_id=context.correlation_id,
        now_ts=float(prepared["now_ts"]),
        ai_source=prepared["ai_source"],
        ai_new_state=prepared["ai_new_state"],
        occupancy_cycle_id=str(lineage.get("occupancy_cycle_id") or "").strip(),
    )
    host._clear_service_call_error(
        context.transaction_id, int(prepared["action_seq"]), prepared["entity_id"]
    )


def _receipt_failure(receipt: Any, response: dict[str, Any]) -> tuple[str, str, str]:
    if isinstance(receipt, dict):
        status = str(receipt.get("status") or "").strip()
        error = str(
            receipt.get("error")
            or receipt.get("reason")
            or status
            or "ha_execution_receipt_unverified"
        ).strip()
        error_type = str(receipt.get("error_type") or "ha_service_unverified_success").strip()
        command_status = str(
            receipt.get("effect_status")
            or receipt.get("ha_command_status")
            or status
            or "effect_unknown"
        ).strip()
    else:
        error = str(
            response.get("error")
            or response.get("error_type")
            or "decision_linked_batch_receipt_shape_invalid"
        ).strip()
        error_type = str(
            response.get("error_type") or "decision_linked_batch_receipt_shape_invalid"
        ).strip()
        status = str(response.get("status") or "").strip().lower()
        command_status = (
            "not_dispatched"
            if status in {"blocked", "rejected"}
            or error_type in {"policy_rejected", "preflight_rejected"}
            else "effect_unknown"
        )
    return error, error_type, command_status


async def _account_receipt(
    host: Any,
    prepared: dict[str, Any],
    receipt: Any,
    disposition: Any,
    response: dict[str, Any],
    context: ActionBatchContext,
) -> BatchDispatchResult:
    result = _receipt_context(prepared, response)
    if (
        isinstance(receipt, dict)
        and receipt.get("ok") is True
        and receipt.get("executed") is True
        and disposition == "verified_success"
    ):
        await _record_verified_success(host, prepared, context)
        return BatchDispatchResult([{**result, "status": "ok"}], executed=1)
    error, error_type, command_status = _receipt_failure(receipt, response)
    if (
        isinstance(receipt, dict)
        and disposition == "noop"
        and receipt.get("ok") is True
        and (
            receipt.get("executed") is False
            or str(receipt.get("status") or "").strip().lower() == "skipped"
        )
    ):
        return BatchDispatchResult(
            [{**result, "status": "skip", "msg": error, "ha_command_status": "skipped"}], blocked=1
        )
    host._remember_service_call_error(
        context.transaction_id,
        int(prepared["action_seq"]),
        prepared["entity_id"],
        msg=error,
        error=error,
        error_type=error_type,
        status=command_status,
        http_status=response.get("http_status"),
        request_id=str(response.get("request_id") or ""),
    )
    return BatchDispatchResult(
        [
            {
                **result,
                "status": "blocked_or_error",
                "msg": error,
                "error": error,
                "error_type": error_type,
                "ha_command_status": command_status,
            }
        ],
        failed=1,
    )


async def execute_prepared_batch(
    host: Any,
    state: ActionPreparationState,
    context: ActionBatchContext,
    prepared: list[dict[str, Any]],
    *,
    preparation_failures: dict[int, dict[str, Any]] | None = None,
) -> BatchDispatchResult:
    if not _preparation_complete(state, prepared):
        return await _reject_incomplete_batch(host, state, context, preparation_failures or {})
    prepared.sort(key=lambda item: int(item["original_position"]))
    response = await _dispatch_batch(host, prepared, context)
    rows, dispositions = _validated_rows(response, len(prepared))
    results, executed, blocked, failed = [], 0, 0, 0
    for index, (command, receipt) in enumerate(zip(prepared, rows)):
        disposition = (
            dispositions[index]
            if isinstance(dispositions, list) and index < len(dispositions)
            else ""
        )
        outcome = await _account_receipt(host, command, receipt, disposition, response, context)
        results.extend(outcome.results)
        executed += outcome.executed
        blocked += outcome.blocked
        failed += outcome.failed
    return BatchDispatchResult(results, executed=executed, blocked=blocked, failed=failed)
