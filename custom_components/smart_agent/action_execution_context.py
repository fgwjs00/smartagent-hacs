"""Explicit context carried by the existing HA action execution stages."""

from __future__ import annotations
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .action_receipts import ActionExecutionResult, ActionResultCollector


@dataclass(frozen=True, slots=True)
class ActionBatchContext:
    scene_desc: str
    trigger_summary: str
    transaction_id: int
    parent_transaction_id: str
    world_snapshot_id: str
    correlation_id: str
    active_space_id: str
    decision_time: str
    cmd_source: str
    require_world_snapshot_guard: bool
    decision_contract_lineage: dict[str, Any] | None
    user_intent_authority: object | None
    trigger_room: str = ""
    is_global_cmd: bool = False
    confidence: int = 0
    authenticated_user_intent: bool = False

    def receipt_metadata(self) -> dict[str, str]:
        return {
            **({"scene_desc": self.scene_desc} if self.scene_desc else {}),
            **({"trigger_summary": self.trigger_summary} if self.trigger_summary else {}),
        }


@dataclass(slots=True)
class ActionPreparationState:
    original_actions: list[Any]
    actions: list[Any]
    collector: ActionResultCollector
    guard_pre_states: dict[str, str] = field(default_factory=dict)
    normalized_actions: list[tuple[int, Any, dict[str, Any]]] = field(default_factory=list)
    pre_states: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActionTransactionStart:
    transaction_id: int
    failure_result: ActionExecutionResult | None = None


@dataclass(slots=True)
class ActionCall:
    """Mutable service target during routing; receipt context stays separately captured."""

    domain: str
    service: str
    entity_id: str
    params: dict[str, Any]
    reason: str


@dataclass(frozen=True, slots=True)
class ActionGuardOutcome:
    result: dict[str, Any]
    blocked: int = 0
    failed: int = 0


@dataclass(slots=True)
class ActionGuardContext:
    batch: ActionBatchContext
    call: ActionCall
    receipt: dict[str, Any]
    original_actions: list[Any]
    daylight_evaluation: dict[str, Any] | None = None
    action_seq: int = 0


@dataclass(frozen=True, slots=True)
class ShowroomBatchEvidence:
    people_counts: dict[str, Any]
    people_rules: list[Any]
    working_hour: bool
    occupied: bool
    light_tiers: dict[str, str]


@dataclass(slots=True)
class ActionItem:
    original_position: int
    call: ActionCall
    receipt: dict[str, Any]
    target_space_id: str
    priority_override_claim: dict[str, Any] | None
    delay: int

    @property
    def action_seq(self) -> int:
        return self.original_position + 1


@dataclass(slots=True)
class ActionExecutionProgress:
    results: list[dict[str, Any]]
    guard_result_count: int
    blocked: int
    executed: int = 0
    failed: int = 0
    prepared_batch_calls: list[dict[str, Any]] = field(default_factory=list)
    preparation_failures: dict[int, dict[str, Any]] = field(default_factory=dict)

    def record_guard(self, outcome: ActionGuardOutcome, position: int) -> None:
        if outcome.failed:
            self.record_failure(position, outcome.result)
            return
        self.blocked += outcome.blocked
        self.results.append(outcome.result)

    def record_failure(self, position: int, result: dict[str, Any]) -> None:
        self.failed += 1
        self.results.append(result)
        if result.get("error_id") and result.get("ha_command_status") == "not_dispatched":
            self.preparation_failures[position] = result


@dataclass(frozen=True, slots=True)
class DelayedActionContext:
    domain: str
    service: str
    entity_id: str
    params: dict[str, Any]
    reason: str
    action_seq: int
    target_space_id: str
    priority_override_claim: dict[str, Any] | None
    batch: ActionBatchContext
    result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DelayedActionCallbacks:
    refresh_transaction: Callable[[], Awaitable[None]]
    refresh_transaction_sync: Callable[[], None]
    pop_service_error: Callable[[int, int, str], dict[str, Any]]
