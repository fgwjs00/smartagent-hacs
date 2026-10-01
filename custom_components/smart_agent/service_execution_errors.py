"""Service failure accounting shared by the existing HA service stages."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .action_execution_context import ActionBatchContext
from .action_execution_diagnostics import action_failure_details
from .service_failure_contracts import (
    is_param_rejection,
    is_service_missing_error,
    service_failure_error_type,
)


def _same_message_update(
    existing: dict[str, Any], msg: str, error_type: str, status: str
) -> dict[str, Any] | None:
    existing_type = str(existing.get("error_type") or "")
    existing_status = str(existing.get("ha_command_status") or "")
    upgrade = bool(error_type) and (
        not existing_type
        or (existing_type == "ha_service_error" and error_type == "service_missing")
    )
    if upgrade or (status and not existing_status):
        return {
            "msg": msg,
            "error": str(existing.get("error") or msg),
            "error_type": error_type if upgrade else existing_type,
            "status": existing_status or status,
        }
    return None


def _failure_update(
    existing: Any, msg: str, error_type: str, status: str, overwrite_stale: bool
) -> dict[str, Any] | None:
    if isinstance(existing, dict):
        existing_msg = str(existing.get("msg") or existing.get("error") or "")
        if existing_msg == str(msg or ""):
            return _same_message_update(existing, msg, error_type, status)
        existing_type = str(existing.get("error_type") or "")
        current_generic = not error_type or error_type == "ha_service_error"
        existing_specific = bool(existing_type) and existing_type != "ha_service_error"
        if not overwrite_stale and existing_specific and current_generic:
            return None
    return {"msg": msg, "error": msg, "error_type": error_type, "status": status}


def _redact_transport_error(detail: dict[str, Any]) -> None:
    error_type = str(detail.get("error_type") or "")
    if error_type in {"", "ha_service_error", "service_missing"}:
        code = "ha_service_missing" if error_type == "service_missing" else "ha_service_call_failed"
        detail.update(msg=code, error=code)


@dataclass(frozen=True, slots=True)
class ServiceErrorRecorder:
    host: Any
    transaction_id: int
    action_seq: int
    entity_id: str

    def after_exception(
        self, error: Exception, batch: ActionBatchContext, *, operation: str,
        overwrite_stale: bool = False,
    ) -> bool:
        return self.after(
            str(error), error_type=service_failure_error_type(error),
            overwrite_stale=overwrite_stale, redact_transport_error=True,
            failure_details=action_failure_details(
                batch, self.action_seq, error, operation=operation,
            ),
        )

    def before(
        self, msg: str, *, error_type: str = "ha_service_guard", status: str = "blocked",
        failure_details: dict[str, str] | None = None,
    ) -> bool:
        self.host._remember_service_call_error(
            self.transaction_id,
            self.action_seq,
            self.entity_id,
            msg=msg,
            error=msg,
            error_type=error_type,
            status=status,
            **({"failure_details": failure_details} if failure_details else {}),
        )
        return False

    def after(
        self,
        msg: str,
        *,
        error_type: str = "ha_service_error",
        status: str = "failed",
        overwrite_stale: bool = False,
        failure_details: dict[str, str] | None = None,
        redact_transport_error: bool = False,
    ) -> bool:
        store = getattr(self.host, "_service_call_errors", None)
        key = self.host._service_call_error_key(
            self.transaction_id, self.action_seq, self.entity_id
        )
        existing = store.get(key) if isinstance(store, dict) else None
        update = _failure_update(existing, msg, error_type, status, overwrite_stale)
        if update is None and isinstance(existing, dict):
            # Keep specific cached policy/receipt fields and their original status.
            if redact_transport_error:
                _redact_transport_error(existing)
            if failure_details:
                existing.update(failure_details)
        if update is not None:
            if redact_transport_error:
                _redact_transport_error(update)
            self.host._remember_service_call_error(
                self.transaction_id, self.action_seq, self.entity_id, **update,
                **({"failure_details": failure_details} if failure_details else {}),
            )
        return False
