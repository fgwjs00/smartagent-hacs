"""Fail-closed validation for add-on confidence arbitration responses."""
from __future__ import annotations

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


def _finite_percent(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0 or parsed > 100:
        return None
    return parsed


def validate_auto_execution_arbitration(
    payload: dict[str, Any] | None,
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
    qualified_reason = str(payload.get("auto_execute_reason") or "").strip()
    qualified_floor = _finite_percent(payload.get("qualified_confidence_floor"))
    has_canonical_qualification = (
        qualified_reason in _QUALIFIED_AUTO_EXECUTE_REASONS
        and qualified_floor == confidence_auto
        and str(result.get("auto_execute_reason") or "").strip() == qualified_reason
        and _finite_percent(result.get("qualified_confidence_floor")) == qualified_floor
        and str(details.get("auto_execute_reason") or "").strip() == qualified_reason
        and _finite_percent(details.get("qualified_confidence_floor")) == qualified_floor
    )

    if confidence >= confidence_auto:
        expected = (True, False, "auto_execute")
        denied_reason = ""
    elif has_canonical_qualification:
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
