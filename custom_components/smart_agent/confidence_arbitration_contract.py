"""Fail-closed validation for add-on confidence arbitration responses."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, NamedTuple


class AutoExecutionArbitrationValidation(NamedTuple):
    allowed: bool
    reason: str


_REQUIRED_FIELDS = (
    "confidence",
    "confidence_auto",
    "confidence_notify",
    "threshold",
    "auto_execute",
    "confirm_required",
    "arbitration_result",
)
_QUALIFIED_AUTO_EXECUTE_REASONS = frozenset({"confirmed_presence_lighting"})
_ARRIVAL_LIGHTING_POLICY_VERSION = "arrival_lighting_auto_v1"
_ARRIVAL_LIGHTING_CONFIRMATION_POLICY_VERSION = "arrival_lighting_confirmation_v1"
_ARRIVAL_LIGHTING_REQUIRED_EVIDENCE_COUNT = 3
_ARRIVAL_LIGHTING_TYPED_THRESHOLD = 70.0
_ARRIVAL_LIGHTING_EVIDENCE_SOURCES = frozenset({"decision_cache_confirmations"})
_ARRIVAL_LIGHTING_CONFIRMATION_GATE = "arrival_lighting_owner_confirmation"


def _finite_percent(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0 or parsed > 100:
        return None
    return parsed


def _typed_actions_fingerprint(actions: Any) -> str:
    if not isinstance(actions, list) or not actions:
        return ""
    canonical: list[dict[str, Any]] = []
    for raw in actions:
        if not isinstance(raw, dict):
            return ""
        entity_id = str(raw.get("entity_id") or raw.get("entity") or "").strip()
        domain = str(
            raw.get("domain")
            or (entity_id.split(".", 1)[0] if "." in entity_id else "")
        ).strip()
        service = str(raw.get("service") or raw.get("action") or "").strip()
        data = raw.get("data") if isinstance(raw.get("data"), dict) else raw.get("params")
        if not entity_id or domain not in {"light", "switch"} or service != "turn_on":
            return ""
        canonical.append(
            {
                "entity_id": entity_id,
                "domain": domain,
                "service": service,
                "data": dict(data) if isinstance(data, dict) else {},
            }
        )
    canonical.sort(key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _has_lighting_turn_on(actions: Any) -> bool:
    if not isinstance(actions, list):
        return False
    for raw in actions:
        if not isinstance(raw, dict):
            continue
        entity_id = str(raw.get("entity_id") or raw.get("entity") or "").strip()
        domain = str(
            raw.get("domain")
            or (entity_id.split(".", 1)[0] if "." in entity_id else "")
        ).strip()
        service = str(raw.get("service") or raw.get("action") or "").strip()
        if "." in service:
            service_domain, service = service.split(".", 1)
            domain = domain or service_domain
        if domain in {"light", "switch"} and service == "turn_on":
            return True
    return False


def _snapshot_environment_bucket(snapshot: dict[str, Any]) -> str:
    context = (
        snapshot.get("environment_context")
        if isinstance(snapshot.get("environment_context"), dict)
        else {}
    )
    if context.get("is_dark") is True:
        return "dark"
    if context.get("is_daylight") is True:
        return "bright"
    raw_lux = context.get("illuminance_lux_min", context.get("illuminance_lux"))
    try:
        lux = float(raw_lux)
    except (TypeError, ValueError):
        return "unknown"
    return "dark" if lux <= 80.0 else "bright"


def _arrival_lighting_turn_on_candidate(
    actions: Any,
    context_snapshot: dict[str, Any] | None,
) -> bool:
    if not isinstance(context_snapshot, dict):
        return False
    trigger_context = (
        context_snapshot.get("trigger_context")
        if isinstance(context_snapshot.get("trigger_context"), dict)
        else {}
    )
    trigger_entity_id = str(context_snapshot.get("trigger_entity_id") or "").strip()
    is_listener_arrival = bool(
        str(context_snapshot.get("source") or "").strip().lower()
        == "ha_bridge_listener"
        and trigger_entity_id.startswith("binary_sensor.")
        and str(context_snapshot.get("old_state") or "").strip().lower() == "off"
        and str(context_snapshot.get("new_state") or "").strip().lower() == "on"
    )
    is_arrival = (
        bool(str(context_snapshot.get("occupancy_cycle_id") or "").strip())
        or str(trigger_context.get("kind") or "").strip().lower()
        == "startup_reconciliation"
        or is_listener_arrival
    )
    return bool(is_arrival and _has_lighting_turn_on(actions))


def _actions_match_policy_space(
    actions: Any,
    context_snapshot: dict[str, Any] | None,
    policy_space: str,
) -> bool:
    if not isinstance(actions, list) or not actions or not isinstance(context_snapshot, dict):
        return False
    device_info = (
        context_snapshot.get("device_info")
        if isinstance(context_snapshot.get("device_info"), dict)
        else {}
    )
    for action in actions:
        if not isinstance(action, dict):
            return False
        entity_id = str(action.get("entity_id") or action.get("entity") or "").strip()
        info = device_info.get(entity_id) if isinstance(device_info.get(entity_id), dict) else {}
        action_space = str(
            info.get("space_id")
            or info.get("room_id")
            or info.get("area_id")
            or info.get("room")
            or info.get("area")
            or ""
        ).strip()
        if not action_space or action_space != policy_space:
            return False
    return True


def apply_arrival_lighting_confirmation_gate(
    payload: dict[str, Any],
    *,
    actions: list[dict[str, Any]],
    context_snapshot: dict[str, Any],
) -> bool:
    """Turn an unproved slow-brain arrival lighting action into a confirmation."""
    if not _arrival_lighting_turn_on_candidate(actions, context_snapshot):
        return False
    nested = dict(payload.get("result")) if isinstance(payload.get("result"), dict) else {}
    details = dict(payload.get("details")) if isinstance(payload.get("details"), dict) else {}
    nested.update({"actions": list(actions), "confirmation_gate": _ARRIVAL_LIGHTING_CONFIRMATION_GATE})
    details["confirmation_gate"] = _ARRIVAL_LIGHTING_CONFIRMATION_GATE
    payload.update(
        {
            "result": nested,
            "details": details,
            "auto_execute": False,
            "confirm_required": True,
            "arbitration_result": "pending_confirmation",
            "reason": "arrival_lighting_confirmation_required",
            "confirmation_gate": _ARRIVAL_LIGHTING_CONFIRMATION_GATE,
            "occupancy_cycle_id": str(context_snapshot.get("occupancy_cycle_id") or "").strip(),
        }
    )
    return True


def pending_confirmation_allowed(
    validation_reason: str,
    *,
    local_confidence_block: bool,
    payload: dict[str, Any],
) -> bool:
    return bool(
        not local_confidence_block
        and validation_reason
        in {"confidence_below_auto_threshold", "arrival_lighting_confirmation_required"}
        and payload.get("confirm_required") is True
        and str(payload.get("arbitration_result") or "").strip() == "pending_confirmation"
    )


def _valid_arrival_lighting_typed_policy(
    policy: Any,
    *,
    confidence_auto: float,
    actions: Any,
    context_snapshot: dict[str, Any] | None,
) -> bool:
    if not isinstance(policy, dict):
        return False
    if str(policy.get("policy_version") or "") != _ARRIVAL_LIGHTING_POLICY_VERSION:
        return False
    evidence_source = str(policy.get("evidence_source") or "")
    if evidence_source not in _ARRIVAL_LIGHTING_EVIDENCE_SOURCES:
        return False
    evidence_count = policy.get("evidence_count")
    required_count = policy.get("required_evidence_count")
    if isinstance(evidence_count, bool) or isinstance(required_count, bool):
        return False
    try:
        parsed_evidence_count = int(evidence_count)
        parsed_required_count = int(required_count)
    except (TypeError, ValueError):
        return False
    if (
        parsed_required_count != _ARRIVAL_LIGHTING_REQUIRED_EVIDENCE_COUNT
        or parsed_evidence_count < parsed_required_count
    ):
        return False
    configured_auto = _finite_percent(policy.get("configured_confidence_auto"))
    effective_auto = _finite_percent(policy.get("effective_confidence_auto"))
    if (
        configured_auto is None
        or effective_auto != _ARRIVAL_LIGHTING_TYPED_THRESHOLD
        or effective_auto != confidence_auto
        or configured_auto < effective_auto
    ):
        return False
    if not str(policy.get("space_id") or "").strip():
        return False
    fingerprint = str(policy.get("actions_fingerprint") or "").strip().lower()
    if len(fingerprint) != 64 or any(char not in "0123456789abcdef" for char in fingerprint):
        return False
    if fingerprint != _typed_actions_fingerprint(actions):
        return False
    policy_space = str(policy.get("space_id") or "").strip()
    if isinstance(context_snapshot, dict):
        active_space = str(
            context_snapshot.get("active_space_id")
            or context_snapshot.get("trigger_room")
            or ""
        ).strip()
        if active_space and active_space != policy_space:
            return False
        if _snapshot_environment_bucket(context_snapshot) != str(
            policy.get("environment_bucket") or ""
        ).strip():
            return False
        if not _actions_match_policy_space(actions, context_snapshot, policy_space):
            return False
    if not str(policy.get("confirmation_key") or "").strip():
        return False
    if (
        str(policy.get("confirmation_policy_version") or "")
        != _ARRIVAL_LIGHTING_CONFIRMATION_POLICY_VERSION
    ):
        return False
    return True


def validate_auto_execution_arbitration(
    payload: dict[str, Any] | None,
    *,
    context_snapshot: dict[str, Any] | None = None,
) -> AutoExecutionArbitrationValidation:
    """Validate an automatic response without making a second policy decision."""
    if not isinstance(payload, dict) or any(
        key not in payload or payload.get(key) in (None, "")
        for key in _REQUIRED_FIELDS
    ):
        return AutoExecutionArbitrationValidation(False, "confidence_arbitration_missing")

    confidence = _finite_percent(payload.get("confidence"))
    confidence_auto = _finite_percent(payload.get("confidence_auto"))
    confidence_notify = _finite_percent(payload.get("confidence_notify"))
    threshold = _finite_percent(payload.get("threshold"))
    if None in (confidence, confidence_auto, confidence_notify, threshold):
        return AutoExecutionArbitrationValidation(False, "confidence_arbitration_invalid")
    assert confidence is not None
    assert confidence_auto is not None
    assert confidence_notify is not None
    assert threshold is not None

    if confidence_notify > confidence_auto or threshold != confidence_auto:
        return AutoExecutionArbitrationValidation(False, "confidence_arbitration_invalid")
    if not isinstance(payload.get("auto_execute"), bool) or not isinstance(
        payload.get("confirm_required"), bool
    ):
        return AutoExecutionArbitrationValidation(False, "confidence_arbitration_invalid")

    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    actions = (
        result.get("actions")
        if isinstance(result.get("actions"), list)
        else payload.get("actions")
    )
    qualified_reason = str(payload.get("auto_execute_reason") or "").strip()
    typed_policy = payload.get("typed_auto_policy")
    has_canonical_qualification = False
    if qualified_reason in _QUALIFIED_AUTO_EXECUTE_REASONS:
        has_canonical_qualification = (
            str(result.get("auto_execute_reason") or "").strip() == qualified_reason
            and str(details.get("auto_execute_reason") or "").strip() == qualified_reason
            and isinstance(typed_policy, dict)
            and result.get("typed_auto_policy") == typed_policy
            and details.get("typed_auto_policy") == typed_policy
            and _valid_arrival_lighting_typed_policy(
                typed_policy,
                confidence_auto=confidence_auto,
                actions=actions,
                context_snapshot=context_snapshot,
            )
        )
        if not has_canonical_qualification:
            return AutoExecutionArbitrationValidation(
                False,
                "confidence_arbitration_invalid",
            )

    arrival_candidate = _arrival_lighting_turn_on_candidate(actions, context_snapshot)
    confirmation_gate = str(payload.get("confirmation_gate") or "").strip()
    has_confirmation_gate = bool(
        confirmation_gate == _ARRIVAL_LIGHTING_CONFIRMATION_GATE
        and str(result.get("confirmation_gate") or "").strip() == confirmation_gate
        and str(details.get("confirmation_gate") or "").strip() == confirmation_gate
    )
    if arrival_candidate and not has_canonical_qualification:
        if not has_confirmation_gate:
            return AutoExecutionArbitrationValidation(
                False,
                "confidence_arbitration_invalid",
            )
        expected = (False, True, "pending_confirmation")
        actual = (
            payload.get("auto_execute"),
            payload.get("confirm_required"),
            str(payload.get("arbitration_result") or "").strip(),
        )
        if actual != expected:
            return AutoExecutionArbitrationValidation(
                False,
                "confidence_arbitration_invalid",
            )
        return AutoExecutionArbitrationValidation(
            False,
            "arrival_lighting_confirmation_required",
        )

    if confidence >= confidence_auto:
        expected = (True, False, "auto_execute")
        denied_reason = ""
    elif confidence >= confidence_notify:
        expected = (False, True, "pending_confirmation")
        denied_reason = "confidence_below_auto_threshold"
    else:
        expected = (False, False, "observe_only")
        denied_reason = "confidence_below_notify_threshold"

    actual = (
        payload.get("auto_execute"),
        payload.get("confirm_required"),
        str(payload.get("arbitration_result") or "").strip(),
    )
    if actual != expected:
        return AutoExecutionArbitrationValidation(False, "confidence_arbitration_invalid")
    return AutoExecutionArbitrationValidation(expected[0], denied_reason)
