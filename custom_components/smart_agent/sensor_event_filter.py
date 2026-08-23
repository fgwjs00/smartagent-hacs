"""Bound high-frequency environment telemetry before SmartAgent event processing."""
from __future__ import annotations

import hashlib
import json
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
    signal_kind: str
    canonical_unit: str
    accepted_units: tuple[str, ...]
    absolute_delta: float
    heartbeat_interval: float
    relative_delta: float = 0.0


_SAMPLING_CONTRACT_SCHEMA_VERSION = "smartagent.signal_sampling_contract.v0.1"
_SIGNAL_MANIFEST_SCHEMA_VERSION = "0.1"
_SAMPLING_CONTRACT_FIELDS = {
    "schema_version",
    "source_entity_id",
    "signal_manifest",
    "policy_source",
    "observation_only",
    "positive_authority",
    "execution_eligible",
    "device_effect_authority",
    "contract_digest",
}
_SIGNAL_MANIFEST_FIELDS = {
    "signal_id",
    "kind",
    "value_type",
    "canonical_unit",
    "accepted_units",
    "valid_range",
    "deadband",
    "heartbeat_secs",
    "staleness_secs",
    "trend_window_secs",
    "privacy_class",
    "model_context_allowed",
    "decision_uses",
    "value_profiles",
    "schema_version",
    "manifest_version",
    "manifest_id",
    "manifest_digest",
}
_DEADBAND_FIELDS = {
    "mode",
    "absolute",
    "relative_fraction",
    "baseline",
    "cumulative",
}
_DEADBAND_MODES = {"absolute", "relative", "cumulative", "absolute_relative"}
_NON_NUMERIC_STATES = {"", "none", "null", "unknown", "unavailable"}
_DEVICE_CLASS_ALIASES = {
    "temperature": "temperature",
    "humidity": "humidity",
    "illuminance": "illuminance",
    "carbon_dioxide": "co2",
    "carbon_dioxide_concentration": "co2",
    "co2": "co2",
    "pm25": "pm25",
    "pm2_5": "pm25",
    "pm2.5": "pm25",
}


def environment_sensor_kind(entity_id: str, metadata: dict[str, Any]) -> str:
    """Return the supported environment kind for a managed HA sensor."""
    policy, _reason = _validated_sampling_policy(entity_id, metadata)
    return policy.signal_kind if policy is not None else ""


def _environment_sensor_hint(entity_id: str, metadata: dict[str, Any]) -> str:
    if not str(entity_id or "").startswith("sensor."):
        return ""

    device_class = str(metadata.get("device_class") or "").strip().lower()
    device_class_kind = _DEVICE_CLASS_ALIASES.get(device_class, "")
    if device_class_kind:
        return device_class_kind

    unit = str(metadata.get("unit_of_measurement") or "").strip().lower()
    if unit in {"°c", "c", "℃", "°f", "f", "℉"}:
        return "temperature"
    if unit in {"lx", "lux"}:
        return "illuminance"

    return ""


def _stable_digest(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, OverflowError):
        return ""
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _finite_nonnegative(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if isfinite(numeric) and numeric >= 0 else None


def _validated_sampling_policy(
    entity_id: str,
    metadata: dict[str, Any],
) -> tuple[_EnvironmentTelemetryPolicy | None, str]:
    normalized_entity_id = str(entity_id or "").strip()
    if not normalized_entity_id.startswith("sensor."):
        return None, "not_environment_sensor"
    raw_contract = metadata.get("signal_sampling_contract")
    if type(raw_contract) is not dict:
        return None, "signal_sampling_contract_missing"
    contract = dict(raw_contract)
    if set(contract) != _SAMPLING_CONTRACT_FIELDS:
        return None, "signal_sampling_contract_invalid"
    if contract.get("schema_version") != _SAMPLING_CONTRACT_SCHEMA_VERSION:
        return None, "signal_sampling_contract_invalid"
    if contract.get("source_entity_id") != normalized_entity_id:
        return None, "signal_sampling_contract_entity_mismatch"
    if (
        contract.get("policy_source") != "core_signal_manifest"
        or contract.get("observation_only") is not True
        or contract.get("positive_authority") is not False
        or contract.get("execution_eligible") is not False
        or contract.get("device_effect_authority") != "none"
    ):
        return None, "signal_sampling_contract_authority_invalid"
    contract_digest = contract.get("contract_digest")
    if not isinstance(contract_digest, str) or len(contract_digest) != 64:
        return None, "signal_sampling_contract_digest_invalid"
    contract_projection = {
        key: value for key, value in contract.items() if key != "contract_digest"
    }
    if _stable_digest(contract_projection) != contract_digest:
        return None, "signal_sampling_contract_digest_invalid"

    raw_manifest = contract.get("signal_manifest")
    if type(raw_manifest) is not dict:
        return None, "signal_manifest_invalid"
    manifest = dict(raw_manifest)
    if set(manifest) != _SIGNAL_MANIFEST_FIELDS:
        return None, "signal_manifest_invalid"
    manifest_digest = manifest.get("manifest_digest")
    if not isinstance(manifest_digest, str) or len(manifest_digest) != 64:
        return None, "signal_manifest_digest_invalid"
    manifest_projection = {
        key: value for key, value in manifest.items() if key != "manifest_digest"
    }
    if _stable_digest(manifest_projection) != manifest_digest:
        return None, "signal_manifest_digest_invalid"

    signal_kind = manifest.get("kind")
    if (
        not isinstance(signal_kind, str)
        or not signal_kind
        or manifest.get("signal_id") != signal_kind
        or manifest.get("manifest_id") != f"builtin.signal.{signal_kind}"
        or manifest.get("schema_version") != _SIGNAL_MANIFEST_SCHEMA_VERSION
        or manifest.get("manifest_version") != "0.1"
        or manifest.get("value_type") not in {"number", "integer"}
    ):
        return None, "signal_manifest_identity_invalid"
    hinted_kind = _environment_sensor_hint(normalized_entity_id, metadata)
    if hinted_kind and hinted_kind != signal_kind:
        return None, "signal_sampling_contract_kind_mismatch"

    canonical_unit = manifest.get("canonical_unit")
    raw_units = manifest.get("accepted_units")
    if not isinstance(canonical_unit, str) or not canonical_unit:
        return None, "signal_manifest_unit_invalid"
    if not isinstance(raw_units, (list, tuple)) or not raw_units:
        return None, "signal_manifest_unit_invalid"
    accepted_units = tuple(
        str(unit).strip().lower()
        for unit in raw_units
        if isinstance(unit, str) and str(unit).strip()
    )
    if len(accepted_units) != len(raw_units) or len(set(accepted_units)) != len(accepted_units):
        return None, "signal_manifest_unit_invalid"
    observed_unit = str(metadata.get("unit_of_measurement") or "").strip().lower()
    if observed_unit not in accepted_units:
        return None, "signal_sampling_unit_not_accepted"

    raw_deadband = manifest.get("deadband")
    if type(raw_deadband) is not dict or set(raw_deadband) != _DEADBAND_FIELDS:
        return None, "signal_manifest_deadband_invalid"
    deadband = dict(raw_deadband)
    absolute_delta = _finite_nonnegative(deadband.get("absolute"))
    relative_delta = _finite_nonnegative(deadband.get("relative_fraction"))
    if (
        deadband.get("mode") not in _DEADBAND_MODES
        or deadband.get("baseline") != "last_forwarded"
        or deadband.get("cumulative") is not True
        or absolute_delta is None
        or relative_delta is None
        or (absolute_delta == 0 and relative_delta == 0)
    ):
        return None, "signal_manifest_deadband_invalid"
    heartbeat = manifest.get("heartbeat_secs")
    if isinstance(heartbeat, bool) or not isinstance(heartbeat, int) or heartbeat <= 0:
        return None, "signal_manifest_heartbeat_invalid"
    if heartbeat > 86400:
        return None, "signal_manifest_heartbeat_invalid"

    return (
        _EnvironmentTelemetryPolicy(
            signal_kind=signal_kind,
            canonical_unit=canonical_unit,
            accepted_units=accepted_units,
            absolute_delta=absolute_delta,
            heartbeat_interval=float(heartbeat),
            relative_delta=relative_delta,
        ),
        "signal_sampling_contract_verified",
    )


def _finite_float(value: Any) -> float | None:
    text = str(value or "").strip().lower()
    if text in _NON_NUMERIC_STATES:
        return None
    try:
        numeric = float(text)
    except (TypeError, ValueError):
        return None
    return numeric if isfinite(numeric) else None


def _canonical_numeric(
    policy: _EnvironmentTelemetryPolicy,
    value: Any,
    metadata: dict[str, Any],
) -> float | None:
    numeric = _finite_float(value)
    if numeric is None:
        return None
    unit = str(metadata.get("unit_of_measurement") or "").strip().lower()
    if unit not in policy.accepted_units:
        return None
    if policy.signal_kind == "temperature" and unit in {"°f", "f", "℉"}:
        return (numeric - 32.0) * 5.0 / 9.0
    return numeric


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
        metadata_row = dict(metadata or {})
        policy, policy_reason = _validated_sampling_policy(
            normalized_entity_id,
            metadata_row,
        )
        if policy is None:
            hinted_kind = _environment_sensor_hint(normalized_entity_id, metadata_row)
            if hinted_kind:
                self._last_forwarded.pop(normalized_entity_id, None)
                return EnvironmentTelemetryDecision(
                    True,
                    False,
                    policy_reason,
                    hinted_kind,
                )
            return EnvironmentTelemetryDecision(False, True, "not_environment_sensor")

        sensor_kind = policy.signal_kind
        old_value = _canonical_numeric(policy, old_state, metadata_row)
        new_value = _canonical_numeric(policy, new_state, metadata_row)
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
