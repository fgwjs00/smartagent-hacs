"""Existing slow-decision canary selection and owner scope projection."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .action_normalization import action_entity_id
from .active_ai_rollout import (
    ActiveAiRolloutConfig,
    blocked_rollout_actions,
    enrich_active_ai_action_spaces,
    scope_active_ai_canary_actions,
    evaluate_active_ai_execution_gate,
)


@dataclass(frozen=True, slots=True)
class DecisionRolloutSelection:
    actions: list[dict[str, Any]]
    enriched_actions: list[dict[str, Any]]
    blocked_entity_ids: set[str]
    blocked_actions: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class DecisionRollout:
    config: ActiveAiRolloutConfig
    selection: DecisionRolloutSelection
    active_space_id: str
    trace: dict[str, Any]
    reason: str
    allow_execution: bool


def _select_actions(
    valid_actions: list[dict[str, Any]],
    candidate_actions: list[dict[str, Any]],
    device_info: dict[str, Any],
    config: ActiveAiRolloutConfig,
    explicit_voice_control: bool,
) -> DecisionRolloutSelection:
    enriched = enrich_active_ai_action_spaces(valid_actions, device_info)
    scoped = None if explicit_voice_control else scope_active_ai_canary_actions(enriched, config)
    blocked_ids = set() if scoped is None else set(scoped.blocked_entity_ids)
    if scoped is not None and not scoped.entity_missing and blocked_ids:
        valid_actions = [
            action
            for action in valid_actions
            if action_entity_id(action).lower() not in blocked_ids
        ]
        enriched = enrich_active_ai_action_spaces(valid_actions, device_info)
    blocked_actions = blocked_rollout_actions(candidate_actions, blocked_ids)
    return DecisionRolloutSelection(valid_actions, enriched, blocked_ids, blocked_actions)


def _space_ids(actions: list[dict[str, Any]]) -> set[str]:
    return {
        str(action.get("target_space_id") or action.get("space_id") or "").strip()
        for action in actions
        if isinstance(action, dict)
    }


def _active_space(
    bundle: dict[str, Any],
    result: dict[str, Any],
    actions: list[dict[str, Any]],
    explicit_voice_control: bool,
) -> str:
    space = str(
        bundle.get("trigger_space_id")
        or result.get("trigger_space_id")
        or bundle.get("trigger_room")
        or result.get("trigger_room")
        or ""
    ).strip()
    if not space and explicit_voice_control:
        spaces = _space_ids(actions)
        if "" not in spaces and len(spaces) == 1:
            space = next(iter(spaces))
    return space


def _owner_domains(actions: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(action.get("domain") or "").strip().lower()
            for action in actions
            if isinstance(action, dict) and str(action.get("domain") or "").strip()
        }
    )


def _owner_entities(actions: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(action.get("entity_id") or action.get("entity") or "").strip().lower()
            for action in actions
            if isinstance(action, dict)
            and str(action.get("entity_id") or action.get("entity") or "").strip()
        }
    )


def _owner_trace(
    config: ActiveAiRolloutConfig, active_space_id: str, actions: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "mode": config.mode,
        "allow_model": True,
        "allow_execution": True,
        "reason": "user_explicit_rollout_bypass",
        "trigger_space_id": active_space_id,
        "action_domains": _owner_domains(actions),
        "blocked_domains": [],
        "action_space_ids": sorted(space for space in _space_ids(actions) if space),
        "blocked_space_ids": [],
        "action_entity_ids": _owner_entities(actions),
        "blocked_entity_ids": [],
        "bypass_scope": "authenticated_user_explicit_voice",
    }


def _execution_gate(
    host: Any,
    config: ActiveAiRolloutConfig,
    selection: DecisionRolloutSelection,
    active_space_id: str,
    execution_flags: dict[str, Any],
    explicit_voice_control: bool,
) -> tuple[dict[str, Any], str, bool]:
    if explicit_voice_control:
        return (
            _owner_trace(config, active_space_id, selection.enriched_actions),
            "user_explicit_rollout_bypass",
            True,
        )
    decision = evaluate_active_ai_execution_gate(
        ai_enabled=bool(getattr(host, "_enabled", False)),
        config=config,
        trigger_space_id=active_space_id,
        actions=selection.enriched_actions,
        execution_flags=execution_flags,
    )
    trace, reason = decision.as_trace(), decision.reason
    if selection.blocked_entity_ids and not selection.actions:
        reason = "active_ai_canary_entity_not_allowed"
        trace["reason"] = reason
        trace["blocked_entity_ids"] = sorted(selection.blocked_entity_ids)
    return trace, reason, decision.allow_execution


def prepare_decision_rollout(
    host: Any,
    *,
    bundle: dict[str, Any],
    result: dict[str, Any],
    valid_actions: list[dict[str, Any]],
    candidate_actions: list[dict[str, Any]],
    explicit_voice_control: bool,
) -> DecisionRollout:
    payload = (
        result.get("active_ai_rollout") if isinstance(result.get("active_ai_rollout"), dict) else {}
    )
    config = ActiveAiRolloutConfig.from_mapping(payload)
    flags = (
        payload.get("execution_flags") if isinstance(payload.get("execution_flags"), dict) else {}
    )
    device_info = bundle.get("device_info") if isinstance(bundle.get("device_info"), dict) else {}
    selection = _select_actions(
        valid_actions, candidate_actions, device_info, config, explicit_voice_control
    )
    result["candidate_action_count"] = len(candidate_actions)
    result["authorized_action_count"] = len(selection.actions)
    result["authorized_actions"] = list(selection.actions)
    result["rollout_blocked_actions"] = selection.blocked_actions
    space = _active_space(bundle, result, selection.enriched_actions, explicit_voice_control)
    trace, reason, allowed = _execution_gate(
        host, config, selection, space, flags, explicit_voice_control
    )
    result["rollout"] = trace
    result["rollout_reason"] = reason
    return DecisionRollout(config, selection, space, trace, reason, allowed)
