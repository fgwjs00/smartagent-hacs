"""Context for the existing single-service preparation and dispatch boundary."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .action_execution_context import ActionBatchContext, ActionCall


@dataclass(frozen=True, slots=True)
class ServiceCallContext:
    call: ActionCall
    batch: ActionBatchContext
    action_seq: int
    target_space_id: str
    priority_override_claim: dict[str, Any] | None = None

    @property
    def is_user_explicit(self) -> bool:
        return str(self.batch.cmd_source or "").strip().upper() == "USER_EXPLICIT"


@dataclass(frozen=True, slots=True)
class PreparedServiceState:
    now_ts: float
    ai_source: str
    ai_new_state: str
    safe_params: dict[str, Any]
