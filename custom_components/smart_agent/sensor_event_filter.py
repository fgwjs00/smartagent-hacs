"""Bound high-frequency environment telemetry before SmartAgent event processing."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class EnvironmentTelemetryDecision:
    tracked: bool
    forward: bool
    reason: str
    sensor_kind: str = ""
    delta: float | None = None
    threshold: float | None = None
    elapsed: float | None = None


@dataclass(frozen=True)
class _EnvironmentTelemetryPolicy:
    absolute_delta: float
    minimum_interval: float
    heartbeat_interval: float
    relative_delta: float = 0.0


_POLICIES = {
    "temperature": _EnvironmentTelemetryPolicy(
        absolute_delta=0.2,
        minimum_interval=0.0,
        heartbeat_interval=300.0,
    ),
    "humidity": _EnvironmentTelemetryPolicy(
        absolute_delta=1.0,
        minimum_interval=0.0,
        heartbeat_interval=300.0,
    ),
    "illuminance": _EnvironmentTelemetryPolicy(
        absolute_delta=5.0,
        relative_delta=0.10,
        minimum_interval=0.0,
        heartbeat_interval=60.0,
    ),
}
_NON_NUMERIC_STATES = {"", "none", "null", "unknown", "unavailable"}
_ENTITY_HINTS = {
    "temperature": ("temperature", "_temp", "wen_du", "_wendu", "温度"),
    "humidity": ("humidity", "humid", "shi_du", "_shidu", "湿度"),
    "illuminance": ("illuminance", "_lux", "light_level", "zhao_du", "照度", "光照"),
}


def environment_sensor_kind(entity_id: str, metadata: dict[str, Any]) -> str:
    """Return the supported environment kind for a managed HA sensor."""
    return _environment_sensor_kind(entity_id, metadata)


def _environment_sensor_kind(entity_id: str, metadata: dict[str, Any]) -> str:
    if not str(entity_id or "").startswith("sensor."):
        return ""

    device_class = str(metadata.get("device_class") or "").strip().lower()
    if device_class in _POLICIES:
        return device_class

    unit = str(metadata.get("unit_of_measurement") or "").strip().lower()
    if unit in {"°c", "c", "℃", "°f", "f", "℉"}:
        return "temperature"
    if unit in {"lx", "lux"}:
        return "illuminance"

    searchable = " ".join(
        (
            str(entity_id or "").lower(),
            str(metadata.get("friendly_name") or metadata.get("name") or "").lower(),
        )
    )
    for kind, hints in _ENTITY_HINTS.items():
        if any(hint in searchable for hint in hints):
            return kind
    return ""


def _finite_float(value: Any) -> float | None:
    text = str(value or "").strip().lower()
    if text in _NON_NUMERIC_STATES:
        return None
    try:
        numeric = float(text)
    except (TypeError, ValueError):
        return None
    return numeric if isfinite(numeric) else None


class EnvironmentTelemetryFilter:
    """Sample environment telemetry without changing Home Assistant state."""

    def __init__(self, *, max_entities: int = 2048) -> None:
        self._max_entities = max(1, int(max_entities))
        self._last_forwarded: dict[str, tuple[float, float]] = {}

    def evaluate(
        self,
        entity_id: str,
        old_state: Any,
        new_state: Any,
        *,
        metadata: dict[str, Any] | None = None,
        now: float,
    ) -> EnvironmentTelemetryDecision:
        normalized_entity_id = str(entity_id or "").strip()
        sensor_kind = _environment_sensor_kind(normalized_entity_id, dict(metadata or {}))
        if not sensor_kind:
            return EnvironmentTelemetryDecision(False, True, "not_environment_sensor")

        old_value = _finite_float(old_state)
        new_value = _finite_float(new_state)
        if old_value is None or new_value is None:
            self._last_forwarded.pop(normalized_entity_id, None)
            if new_value is not None:
                self._remember(normalized_entity_id, new_value, float(now))
            return EnvironmentTelemetryDecision(True, True, "state_transition", sensor_kind)

        now_value = float(now)
        previous = self._last_forwarded.get(normalized_entity_id)
        if previous is None:
            self._remember(normalized_entity_id, new_value, now_value)
            return EnvironmentTelemetryDecision(True, True, "first_sample", sensor_kind)

        baseline, forwarded_at = previous
        policy = _POLICIES[sensor_kind]
        elapsed = max(0.0, now_value - forwarded_at)
        delta = round(abs(new_value - baseline), 6)
        threshold = round(
            max(policy.absolute_delta, abs(baseline) * policy.relative_delta),
            6,
        )
        detail = {
            "sensor_kind": sensor_kind,
            "delta": delta,
            "threshold": threshold,
            "elapsed": round(elapsed, 6),
        }

        if delta >= threshold * 3:
            self._remember(normalized_entity_id, new_value, now_value)
            return EnvironmentTelemetryDecision(True, True, "critical_change", **detail)
        if elapsed < policy.minimum_interval:
            return EnvironmentTelemetryDecision(True, False, "minimum_interval", **detail)
        if delta >= threshold:
            self._remember(normalized_entity_id, new_value, now_value)
            return EnvironmentTelemetryDecision(True, True, "cumulative_deadband", **detail)
        if elapsed >= policy.heartbeat_interval:
            self._remember(normalized_entity_id, new_value, now_value)
            return EnvironmentTelemetryDecision(True, True, "heartbeat", **detail)
        return EnvironmentTelemetryDecision(True, False, "below_deadband", **detail)

    def _remember(self, entity_id: str, value: float, now: float) -> None:
        if len(self._last_forwarded) >= self._max_entities and entity_id not in self._last_forwarded:
            oldest_entity_id = min(
                self._last_forwarded,
                key=lambda candidate: self._last_forwarded[candidate][1],
            )
            self._last_forwarded.pop(oldest_entity_id, None)
        self._last_forwarded[entity_id] = (value, now)
