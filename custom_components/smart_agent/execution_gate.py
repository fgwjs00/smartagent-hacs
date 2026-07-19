"""Portable thin execution gate for HA command dispatch."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


ALLOWED_DOMAINS = frozenset({
    "light", "switch", "climate", "cover", "fan",
    "media_player", "script", "scene",
    "input_boolean", "input_number", "input_select",
})
BLOCKED_SERVICES = frozenset({
    "reload", "restart", "stop", "delete", "remove",
    "enable", "disable",
})
STATELESS_DOMAINS = frozenset({"script", "scene"})


@dataclass(frozen=True)
class ThinExecutionGateResult:
    allowed: bool
    entity_id: str = ""
    service: str = ""
    status: str = ""
    msg: str = ""
    log_code: str = ""
    error_type: str = ""
    clear_expired_override: bool = False
    automation_name: str = ""
    age_seconds: int = 0
    remaining_seconds: int = 0
    normalized_params: dict[str, Any] | None = None
    color_temp_mireds: str = ""
    color_temp_kelvin: int = 0

    def to_action_result(self) -> dict[str, Any]:
        result = {
            "entity_id": self.entity_id,
            "service": self.service,
            "status": self.status,
            "msg": self.msg,
            "error_type": self.error_type,
        }
        return {key: value for key, value in result.items() if value not in (None, "")}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def evaluate_slow_brain_confidence_gate(
    *,
    confidence: Any,
    threshold: Any,
) -> ThinExecutionGateResult:
    """Fail closed unless a finite 0-100 score reaches the local threshold."""

    try:
        score = float(confidence)
        minimum = float(threshold)
    except (TypeError, ValueError, OverflowError):
        return ThinExecutionGateResult(allowed=False, log_code="confidence_invalid")

    if not math.isfinite(score) or not math.isfinite(minimum):
        return ThinExecutionGateResult(allowed=False, log_code="confidence_invalid")
    if not 0 <= score <= 100 or not 0 <= minimum <= 100:
        return ThinExecutionGateResult(allowed=False, log_code="confidence_invalid")
    if score < minimum:
        return ThinExecutionGateResult(
            allowed=False,
            log_code="confidence_below_auto_threshold",
        )
    return ThinExecutionGateResult(allowed=True)


def evaluate_thin_execution_gate(
    *,
    domain: Any,
    service: Any,
    entity_id: Any,
    raw_entity_id: Any = None,
    entity_exists: bool = True,
    raw_entity_exists: bool = True,
) -> ThinExecutionGateResult:
    """Check only transport-portable hard gates before HA service dispatch."""

    domain_s = _clean(domain)
    service_s = _clean(service)
    entity_s = _clean(entity_id)
    raw_entity_s = _clean(raw_entity_id)

    if not domain_s or not service_s or not entity_s:
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=entity_s or raw_entity_s,
            service=service_s,
            status="blocked_invalid_action",
            msg="missing_required_action_fields",
            log_code="missing_required_action_fields",
        )

    if domain_s not in ALLOWED_DOMAINS:
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=entity_s,
            service=service_s,
            status="blocked_disallowed_domain",
            msg=f"domain_not_allowed:{domain_s}",
            log_code="domain_not_allowed",
        )

    if service_s in BLOCKED_SERVICES:
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=entity_s,
            service=service_s,
            status="blocked_service",
            msg=f"service_blocked:{service_s}",
            log_code="service_blocked",
        )

    if raw_entity_s and "." in raw_entity_s and domain_s not in STATELESS_DOMAINS and not raw_entity_exists:
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=raw_entity_s,
            service=service_s,
            status="blocked_nonexistent",
            msg="原始动作实体不存在或未注册到 HA，疑似模型幻觉",
            log_code="raw_entity_not_found",
        )

    if domain_s not in STATELESS_DOMAINS and not entity_exists:
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=entity_s,
            service=service_s,
            status="blocked_nonexistent",
            msg="实体不存在或未注册到 HA，疑似模型幻觉",
            log_code="entity_not_found",
        )

    return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)


def evaluate_manual_override_window(
    *,
    entity_id: Any,
    service: Any,
    now_ts: float,
    override: Any,
    off_states: set[str] | frozenset[str],
    window_seconds: float,
) -> ThinExecutionGateResult:
    """Evaluate the legacy manual override reverse-action window as a pure gate."""

    entity_s = _clean(entity_id)
    service_s = _clean(service)
    if not isinstance(override, dict):
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    try:
        override_time = float(override["time"])
    except (KeyError, TypeError, ValueError):
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    try:
        window = float(window_seconds)
    except (TypeError, ValueError):
        window = 0.0

    age = float(now_ts) - override_time
    if age >= window:
        return ThinExecutionGateResult(
            allowed=True,
            entity_id=entity_s,
            service=service_s,
            clear_expired_override=True,
        )

    override_state = override.get("state")
    user_off = override_state in off_states
    ai_on = "turn_on" in service_s or "open" in service_s
    ai_off = "turn_off" in service_s or "close" in service_s
    reversing = (user_off and ai_on) or (not user_off and ai_off)
    if not reversing:
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    return ThinExecutionGateResult(
        allowed=False,
        entity_id=entity_s,
        service=service_s,
        status="blocked_user_override",
        msg=(
            f"user_override_protection: user set {entity_s} to {override_state} "
            f"{int(age)}s ago; rejected reverse {service_s}"
        ),
        log_code="user_override_protection",
        error_type="user_override_protection",
    )


def evaluate_automation_conflict_window(
    *,
    entity_id: Any,
    service: Any,
    managed_automation_names: Any,
    automation_records: Any,
    now_ts: float,
    window_seconds: float,
) -> ThinExecutionGateResult:
    """Evaluate whether a HA automation recently controlled this entity."""

    entity_s = _clean(entity_id)
    service_s = _clean(service)
    if not managed_automation_names:
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    labels = [str(name) for name in managed_automation_names if str(name or "").strip()]
    if not labels:
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)
    label_set = set(labels)

    try:
        now = float(now_ts)
    except (TypeError, ValueError):
        now = 0.0
    try:
        window = float(window_seconds)
    except (TypeError, ValueError):
        window = 0.0

    if not isinstance(automation_records, (list, tuple)):
        automation_records = []

    for record in automation_records:
        if not isinstance(record, dict):
            continue
        name = _clean(record.get("name") or record.get("friendly_name"))
        if name not in label_set:
            continue
        try:
            last_triggered_ts = float(record.get("last_triggered_ts"))
        except (TypeError, ValueError):
            continue
        age = now - last_triggered_ts
        if age < window:
            return ThinExecutionGateResult(
                allowed=False,
                entity_id=entity_s,
                service=service_s,
                status="blocked",
                msg=f"automation_recently_triggered: {','.join(labels)}",
                log_code="automation_recently_triggered",
                error_type="automation_conflict",
                automation_name=name,
                age_seconds=int(age),
            )

    return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)


def evaluate_self_trigger_protection(
    *,
    entity_id: Any,
    service: Any,
    trigger_entities: Any,
) -> ThinExecutionGateResult:
    """Block AI from operating the same controllable entity that triggered inference."""

    entity_s = _clean(entity_id)
    service_s = _clean(service)
    if entity_s and entity_s in set(trigger_entities or []):
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=entity_s,
            service=service_s,
            status="blocked_self_trigger",
            msg=f"self_trigger_protection: {entity_s} triggered current inference; rejected {service_s}",
            log_code="self_trigger_protection",
            error_type="self_trigger_protection",
        )
    return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)


def evaluate_global_suppress_window(
    *,
    entity_id: Any,
    service: Any,
    now_ts: float,
    suppress_until: Any,
    suppress_reason: Any,
) -> ThinExecutionGateResult:
    """Evaluate Product Rule P0 global suppress without HA runtime access."""

    entity_s = _clean(entity_id)
    service_s = _clean(service)
    try:
        now = float(now_ts)
    except (TypeError, ValueError):
        now = 0.0
    try:
        suppress_until_ts = float(suppress_until)
    except (TypeError, ValueError):
        suppress_until_ts = 0.0

    if now >= suppress_until_ts:
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    remaining = int(suppress_until_ts - now)
    reason_s = _clean(suppress_reason) or "global_suppress"
    return ThinExecutionGateResult(
        allowed=False,
        entity_id=entity_s,
        service=service_s,
        status="blocked",
        msg=f"[P0 global suppress] {reason_s} ({remaining}s remaining)",
        log_code="global_suppress",
        error_type="global_suppress",
        remaining_seconds=remaining,
    )


def evaluate_color_temp_mireds_param(
    *,
    entity_id: Any,
    service: Any,
    params: Any,
) -> ThinExecutionGateResult:
    """Normalize legacy HA color_temp mireds or reject invalid values."""

    entity_s = _clean(entity_id)
    service_s = _clean(service)
    safe_params = dict(params) if isinstance(params, dict) else {}
    if "color_temp" not in safe_params or "color_temp_kelvin" in safe_params:
        return ThinExecutionGateResult(
            allowed=True,
            entity_id=entity_s,
            service=service_s,
            normalized_params=safe_params,
        )

    mired_val = safe_params.pop("color_temp")
    try:
        mired_num = float(mired_val)
    except (TypeError, ValueError):
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=entity_s,
            service=service_s,
            status="blocked_invalid_params",
            msg=f"invalid_color_temp_mireds:{mired_val}",
            log_code="invalid_color_temp_mireds",
            error_type="invalid_action_param",
        )
    if mired_num <= 0:
        return ThinExecutionGateResult(
            allowed=False,
            entity_id=entity_s,
            service=service_s,
            status="blocked_invalid_params",
            msg=f"invalid_color_temp_mireds:{mired_val}",
            log_code="invalid_color_temp_mireds",
            error_type="invalid_action_param",
        )

    kelvin = round(1_000_000 / mired_num)
    safe_params["color_temp_kelvin"] = kelvin
    return ThinExecutionGateResult(
        allowed=True,
        entity_id=entity_s,
        service=service_s,
        normalized_params=safe_params,
        color_temp_mireds=str(mired_val),
        color_temp_kelvin=kelvin,
    )


def evaluate_priority_arbitration(
    *,
    entity_id: Any,
    ai_source: Any,
    ai_service: Any,
    existing: Any,
    now_ts: float,
    source_priority_map: dict[str, int],
    default_priority: int,
    off_states: set[str] | frozenset[str],
) -> ThinExecutionGateResult:
    """Evaluate source-priority guard arbitration without HA runtime access."""

    entity_s = _clean(entity_id)
    service_s = _clean(ai_service)
    source_s = _clean(ai_source)
    if not isinstance(existing, dict):
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    try:
        guard_until = float(existing.get("guard_until", 0))
    except (TypeError, ValueError):
        guard_until = 0.0
    if float(now_ts) > guard_until:
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    try:
        existing_priority = int(existing.get("priority", default_priority))
    except (TypeError, ValueError):
        existing_priority = int(default_priority)
    incoming_priority = int(source_priority_map.get(source_s, default_priority))
    if incoming_priority < existing_priority:
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    current_state = _clean(existing.get("state"))
    is_off = current_state in off_states
    ai_turning_on = "turn_on" in service_s or "open" in service_s
    ai_turning_off = "turn_off" in service_s or "close" in service_s
    if not ((is_off and ai_turning_on) or (not is_off and ai_turning_off)):
        return ThinExecutionGateResult(allowed=True, entity_id=entity_s, service=service_s)

    remaining = int(guard_until - float(now_ts))
    return ThinExecutionGateResult(
        allowed=False,
        entity_id=entity_s,
        service=service_s,
        status="blocked_priority_guard",
        msg=(
            f"[优先级仲裁] AI 尝试反向操作 {entity_s}"
            f"（当前由 {existing.get('source_label', 'unknown')} 控制，保护剩余 {remaining}s）"
        ),
        log_code="priority_guard_rejected",
        error_type="priority_guard",
    )
