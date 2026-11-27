"""Fast-path canary scoping retains its autonomous execution boundary."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .active_ai_rollout import (
    ActiveAiRolloutConfig,
    ActiveAiRolloutDecision,
    evaluate_active_ai_execution_gate,
)
from .decision_rollout import finalize_canary_empty_gate, select_rollout_actions


@dataclass(frozen=True, slots=True)
class FastPathActionSelection:
    config: ActiveAiRolloutConfig
    original_actions: list[Any]
    actions: list[Any]
    enriched_actions: list[dict[str, Any]]
    blocked_entity_ids: list[str]
    blocked_actions: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class FastPathRollout:
    payload: dict[str, Any]
    selection: FastPathActionSelection
    decision: ActiveAiRolloutDecision


def _select_actions(
    actions: list[Any], device_info: dict[str, Any], rollout_payload: dict[str, Any]
) -> FastPathActionSelection:
    original_actions = list(actions)
    rollout_config = ActiveAiRolloutConfig.from_mapping(rollout_payload)
    authorized_actions, rollout_actions, blocked_ids, rollout_blocked_actions = select_rollout_actions(
        original_actions,
        device_info,
        rollout_config,
    )
    return FastPathActionSelection(
        rollout_config,
        original_actions,
        authorized_actions,
        rollout_actions,
        list(blocked_ids),
        rollout_blocked_actions,
    )


def _trigger_space(
    result: Any, device_info: dict[str, Any], entity_id: str, trigger_info: dict[str, Any]
) -> str:
    return str(
        (result.get("trigger_space_id") if isinstance(result, dict) else "")
        or trigger_info.get("space_id")
        or trigger_info.get("room_id")
        or trigger_info.get("area_id")
        or (result.get("trigger_room") if isinstance(result, dict) else "")
        or trigger_info.get("room", "")
    ).strip()


def prepare_fast_path_rollout(
    host: Any, response: dict[str, Any], result: Any, actions: list[Any], entity_id: str
) -> FastPathRollout:
    rollout_payload = (
        response.get("active_ai_rollout")
        if isinstance(response.get("active_ai_rollout"), dict)
        else {}
    )
    rollout_flags = (
        rollout_payload.get("execution_flags")
        if isinstance(rollout_payload.get("execution_flags"), dict)
        else {}
    )
    device_info = host.device_info
    selection = _select_actions(actions, device_info, rollout_payload)
    trigger_info = device_info.get(entity_id, {}) if isinstance(device_info, dict) else {}
    if not isinstance(trigger_info, dict):
        trigger_info = {}
    rollout_decision = finalize_canary_empty_gate(
        evaluate_active_ai_execution_gate(
            ai_enabled=bool(host._is_enabled()),
            config=selection.config,
            trigger_space_id=_trigger_space(result, device_info, entity_id, trigger_info),
            actions=selection.enriched_actions,
            execution_flags=rollout_flags,
        ),
        selection.blocked_entity_ids,
        selection.actions,
    )
    return FastPathRollout(rollout_payload, selection, rollout_decision)
