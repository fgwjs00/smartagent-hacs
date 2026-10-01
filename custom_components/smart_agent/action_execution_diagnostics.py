"""Safe, receipt-correlated diagnostics shared by action execution boundaries."""
from __future__ import annotations

import hashlib
import logging
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .action_execution_context import ActionBatchContext, ActionGuardContext, ActionGuardOutcome

_LOGGER = logging.getLogger(__name__)


def _failure_details(error: Exception, operation: str) -> dict[str, str]:
    return {
        "operation": operation, "error_id": secrets.token_hex(12),
        "exception_type": type(error).__name__,
    }


def action_failure_details(
    batch: ActionBatchContext, action_seq: int, error: Exception, *, operation: str
) -> dict[str, str]:
    details = _failure_details(error, operation)
    _LOGGER.error(
        "operation=%s error_id=%s transaction_id=%s action_seq=%s cause_type=%s",
        operation, details["error_id"], batch.transaction_id, action_seq, details["exception_type"],
    )
    return details


def action_predispatch_failure(
    context: ActionGuardContext, error: Exception, *, operation: str, code: str,
) -> ActionGuardOutcome:
    """A failed prerequisite read stops this action and counts as a failure."""
    from .action_execution_context import ActionGuardOutcome

    return ActionGuardOutcome(
        {
            **context.receipt,
            **action_failure_details(context.batch, context.action_seq, error, operation=operation),
            "status": "blocked_or_error", "msg": code,
            "error": code, "error_type": code, "ha_command_status": "not_dispatched",
        },
        failed=1,
    )


def presence_refresh_failure(
    batch: ActionBatchContext, action_seq: int, error: Exception, *, operation: str,
) -> dict[str, object]:
    """A refresh exception is a failed read, not an ordinary presence veto."""
    return {
        **action_failure_details(batch, action_seq, error, operation=operation),
        "status": "blocked_or_error",
        "msg": "presence_refresh_failed",
        "error": "presence_refresh_failed",
        "error_type": "presence_refresh_failed",
        "ha_command_status": "not_dispatched",
        "presence_source": "addon_presence_engine",
        "presence_reason": "presence_refresh_failed",
        "presence_evidence_ids": [],
        "presence_states": [],
    }


def envelope_failure_details(
    request_id: str, action_seq: int, error: Exception, *, operation: str,
) -> dict[str, str]:
    details = _failure_details(error, operation)
    request_digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    _LOGGER.error(
        "operation=%s error_id=%s request_id_digest=%s action_seq=%s cause_type=%s",
        operation, details["error_id"], request_digest, action_seq, details["exception_type"],
    )
    return details
