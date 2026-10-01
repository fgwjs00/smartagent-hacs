"""Only verified service receipts may reach successful execution bookkeeping."""

from __future__ import annotations
from typing import Any
from .service_execution_context import ServiceCallContext
from .service_execution_errors import ServiceErrorRecorder


def _single_receipt(response: dict[str, Any]) -> Any:
    rows = response.get("results")
    return (
        rows[0] if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict) else None
    )


def _single_disposition(response: dict[str, Any]) -> str:
    dispositions = response.get("_smartagent_receipt_dispositions")
    return str(dispositions[0]) if isinstance(dispositions, list) and len(dispositions) == 1 else ""


def verify_service_receipt(
    host: Any, context: ServiceCallContext, response: dict[str, Any], errors: ServiceErrorRecorder
) -> bool:
    receipt = _single_receipt(response)
    disposition = _single_disposition(response)
    if isinstance(receipt, dict) and receipt.get("ok") is True:
        status = str(receipt.get("status") or "").strip().lower()
        strict = context.batch.require_world_snapshot_guard and not context.is_user_explicit
        if (receipt.get("executed") is False or status == "skipped") and (
            disposition == "noop" or not strict
        ):
            reason = str(
                receipt.get("reason") or receipt.get("status") or "already_in_target_state"
            ).strip()
            host._remember_service_call_error(
                context.batch.transaction_id,
                context.action_seq,
                context.call.entity_id,
                msg=reason,
                status="skipped",
            )
            return False
        if receipt.get("executed") is True and not (strict and disposition != "verified_success"):
            return True
    return errors.after(
        "ha_execution_receipt_unverified",
        error_type="ha_service_unverified_success",
        status="failed",
        overwrite_stale=True,
    )
