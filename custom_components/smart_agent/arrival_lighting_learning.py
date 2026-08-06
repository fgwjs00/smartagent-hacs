"""Pure contracts for learning arrival lighting preferences."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ArrivalObservationClassification:
    baseline_eligible: bool
    observation_only: bool
    evidence_kind: str
    evidence_weight: float
    evidence_tier: str = "legacy_untrusted"
    execution_permission: str = "suggest_only"
    exclusion_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "on"}


def _space_id(info: Mapping[str, Any]) -> str:
    return _text(info.get("space_id") or info.get("room") or info.get("area"))


def _managed(info: Mapping[str, Any]) -> bool:
    return any(
        _truthy(info.get(key))
        for key in ("managed", "in_sa", "in_smartagent")
    )


def _entity_state(entity_states: Any, entity_id: str) -> str:
    if entity_states is None or not hasattr(entity_states, "get"):
        return ""
    raw = entity_states.get(entity_id)
    return _text(getattr(raw, "state", raw)).lower()


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def arrival_environment_bucket(
    context: Mapping[str, Any],
    *,
    dark_lux_threshold: float,
) -> str:
    """Normalize arrival environment without guessing missing light levels."""

    if context.get("is_dark") is True:
        return "dark"
    if context.get("is_daylight") is True:
        return "bright"
    lux = _float_or_none(
        context.get("illuminance_lux_min", context.get("illuminance_lux"))
    )
    if lux is None:
        return "unknown"
    return "dark" if lux <= dark_lux_threshold else "bright"


def classify_arrival_observation(
    *,
    pre_state: str,
    observed_state: str,
    change_origin: str,
    causal_ai_actions: Sequence[Mapping[str, Any]],
    trusted_automation_source: bool = False,
    scope_matches: bool = True,
    time_window_matches: bool = True,
) -> ArrivalObservationClassification:
    """Classify one entity observation for arrival preference learning."""

    before = _text(pre_state).lower()
    after = _text(observed_state).lower()
    state_changed = before != after
    origin = _text(change_origin).lower()
    if not scope_matches:
        return ArrivalObservationClassification(
            baseline_eligible=False,
            observation_only=True,
            evidence_kind="",
            evidence_weight=0.0,
            exclusion_reason="arrival_scope_mismatch",
        )
    if not time_window_matches:
        return ArrivalObservationClassification(
            baseline_eligible=False,
            observation_only=True,
            evidence_kind="",
            evidence_weight=0.0,
            exclusion_reason="arrival_window_mismatch",
        )
    if causal_ai_actions:
        return ArrivalObservationClassification(
            baseline_eligible=False,
            observation_only=True,
            evidence_kind="",
            evidence_weight=0.0,
            exclusion_reason="recent_ai_action_same_entity",
        )
    if state_changed and origin in {
        "user_action",
        "physical_action",
        "user_scene_script_action",
    }:
        return ArrivalObservationClassification(
            baseline_eligible=True,
            observation_only=False,
            evidence_kind=(
                "explicit_positive" if after == "on" else "explicit_negative"
            ),
            evidence_weight=1.0,
            evidence_tier="direct_user_action",
            execution_permission="auto_eligible",
        )
    if state_changed and origin == "automation" and trusted_automation_source:
        return ArrivalObservationClassification(
            baseline_eligible=True,
            observation_only=False,
            evidence_kind=(
                "registered_habit_positive"
                if after == "on"
                else "registered_habit_negative"
            ),
            evidence_weight=0.5,
            evidence_tier="registered_ha_orchestration",
            execution_permission="suggest_only",
        )
    if state_changed and origin == "automation":
        return ArrivalObservationClassification(
            baseline_eligible=False,
            observation_only=True,
            evidence_kind="",
            evidence_weight=0.0,
            exclusion_reason="external_automation_untrusted",
        )
    if not state_changed and after == "off":
        return ArrivalObservationClassification(
            baseline_eligible=True,
            observation_only=False,
            evidence_kind="implicit_negative",
            evidence_weight=0.5,
            evidence_tier="observation_only",
            execution_permission="suggest_only",
        )
    return ArrivalObservationClassification(
        baseline_eligible=False,
        observation_only=True,
        evidence_kind="",
        evidence_weight=0.0,
        exclusion_reason=(
            "state_change_origin_unknown"
            if state_changed
            else "unchanged_on_without_owner_proof"
        ),
    )


def arrival_lighting_entity_ids(
    device_info: Mapping[str, Any],
    space_id: str,
    *,
    entity_states: Any = None,
) -> tuple[str, ...]:
    """Return available managed lighting entities in one space."""

    target = _text(space_id)
    selected: list[str] = []
    for entity_id, raw in device_info.items():
        if not isinstance(raw, Mapping):
            continue
        if _space_id(raw) != target or not _managed(raw):
            continue
        if _text(raw.get("capability")).lower() != "lighting":
            continue
        normalized_entity_id = _text(entity_id)
        if _entity_state(entity_states, normalized_entity_id) in {
            "unavailable",
            "unknown",
        }:
            continue
        if normalized_entity_id:
            selected.append(normalized_entity_id)
    return tuple(sorted(selected))
