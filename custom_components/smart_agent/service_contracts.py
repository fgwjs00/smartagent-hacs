"""Runtime loader and pure validator for the generated HA service contract."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


_CONTRACT_PATH = Path(__file__).with_name("ha_service_contracts.v1.json")
_CONTRACT_BYTES = _CONTRACT_PATH.read_bytes()
_CONTRACT_PAYLOAD = json.loads(_CONTRACT_BYTES.decode("utf-8"))

if not isinstance(_CONTRACT_PAYLOAD, dict):
    raise RuntimeError("HA service contract must be an object")
if int(_CONTRACT_PAYLOAD.get("version") or 0) != 1:
    raise RuntimeError("unsupported HA service contract version")
if not isinstance(_CONTRACT_PAYLOAD.get("services"), dict):
    raise RuntimeError("HA service contract services must be an object")

CONTRACT_VERSION = int(_CONTRACT_PAYLOAD["version"])
CONTRACT_HASH = hashlib.sha256(_CONTRACT_BYTES).hexdigest()
SERVICE_CONTRACTS: dict[str, dict[str, Any]] = {
    str(key): dict(value)
    for key, value in _CONTRACT_PAYLOAD["services"].items()
    if isinstance(value, dict)
}

ALLOWED_COMMAND_SERVICES: dict[str, frozenset[str]] = {}
_services_by_domain: dict[str, set[str]] = {}
_domains_by_service: dict[str, set[str]] = {}
for _service_key in SERVICE_CONTRACTS:
    _domain, _service = _service_key.split(".", 1)
    _services_by_domain.setdefault(_domain, set()).add(_service)
    _domains_by_service.setdefault(_service, set()).add(_domain)
ALLOWED_COMMAND_SERVICES = {
    domain: frozenset(services)
    for domain, services in _services_by_domain.items()
}
SERVICES_TO_DOMAINS: dict[str, frozenset[str]] = {
    service: frozenset(domains)
    for service, domains in _domains_by_service.items()
}


@dataclass(frozen=True, slots=True)
class ServiceContractResult:
    allowed: bool
    service_key: str
    reason_code: str = ""
    invalid_fields: tuple[str, ...] = ()
    normalized_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["invalid_fields"] = list(self.invalid_fields)
        payload["normalized_data"] = dict(self.normalized_data or {})
        return payload


def _rejected(service_key: str, reason_code: str, fields: tuple[str, ...] = ()) -> ServiceContractResult:
    return ServiceContractResult(
        allowed=False,
        service_key=service_key,
        reason_code=reason_code,
        invalid_fields=fields,
        normalized_data={},
    )


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    normalized = float(value)
    return normalized if math.isfinite(normalized) else None


def _value_error_reason(value: Any, schema: dict[str, Any]) -> str:
    kind = str(schema.get("type") or "")
    numbers: list[float] = []
    if kind == "boolean":
        if type(value) is not bool:
            return "service_parameter_type_invalid"
    elif kind == "string":
        if not isinstance(value, str):
            return "service_parameter_type_invalid"
        if int(schema.get("minLength") or 0) > 0 and not value.strip():
            return "service_parameter_type_invalid"
    elif kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return "service_parameter_type_invalid"
        numbers = [float(value)]
    elif kind == "number":
        number = _number(value)
        if number is None:
            return "service_parameter_type_invalid"
        numbers = [number]
    elif kind in {"integer_array", "number_array"}:
        if not isinstance(value, (list, tuple)):
            return "service_parameter_type_invalid"
        expected_length = schema.get("length")
        if isinstance(expected_length, int) and len(value) != expected_length:
            return "service_parameter_length_invalid"
        for item in value:
            if kind == "integer_array":
                if isinstance(item, bool) or not isinstance(item, int):
                    return "service_parameter_type_invalid"
                numbers.append(float(item))
            else:
                number = _number(item)
                if number is None:
                    return "service_parameter_type_invalid"
                numbers.append(number)
    else:
        return "service_contract_schema_invalid"

    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    if minimum is not None and any(item < float(minimum) for item in numbers):
        return "service_parameter_out_of_range"
    if maximum is not None and any(item > float(maximum) for item in numbers):
        return "service_parameter_out_of_range"
    return ""


def _required_one_of_error(schema: dict[str, Any], data: dict[str, Any]) -> ServiceContractResult | None:
    raw_groups = schema.get("requiredOneOf")
    if not isinstance(raw_groups, list) or not raw_groups:
        return None
    groups = [
        tuple(str(field) for field in group)
        for group in raw_groups
        if isinstance(group, list) and group
    ]
    complete = [group for group in groups if all(field in data for field in group)]
    if len(complete) == 1:
        return None
    service_key = str(schema.get("_service_key") or "")
    if len(complete) > 1:
        fields = tuple(dict.fromkeys(field for group in complete for field in group))
        return _rejected(service_key, "service_parameter_combination_invalid", fields)
    partial = [group for group in groups if any(field in data for field in group)]
    if partial:
        fields = tuple(field for field in partial[0] if field not in data)
    else:
        fields = tuple(dict.fromkeys(field for group in groups for field in group))
    return _rejected(service_key, "service_parameter_required", fields)


def _capability_value(capability: Any, key: str) -> Any:
    if isinstance(capability, dict):
        if key in capability:
            return capability.get(key)
        for container_key in ("metadata", "attributes"):
            container = capability.get(container_key)
            if isinstance(container, dict) and key in container:
                return container.get(key)
        return None
    direct = getattr(capability, key, None)
    if direct is not None:
        return direct
    for container_key in ("metadata", "attributes"):
        container = getattr(capability, container_key, None)
        if isinstance(container, dict) and key in container:
            return container.get(key)
    return None


def _capability_dimension(capability: Any, key: str) -> dict[str, Any] | None:
    dimensions = _capability_value(capability, "behavior_dims")
    if not isinstance(dimensions, (list, tuple)):
        return None
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            continue
        dimension_key = str(dimension.get("key") or dimension.get("name") or "").strip().lower()
        if dimension_key == key:
            return dimension
    return None


def _capability_allows(capability: Any, capability_key: str, requested: Any) -> bool:
    raw_values = _capability_value(capability, capability_key)
    if not isinstance(raw_values, (list, tuple, set, frozenset)):
        dimension_key = {
            "hvac_modes": "hvac_mode",
            "preset_modes": "preset_mode",
        }.get(capability_key, capability_key)
        dimension = _capability_dimension(capability, dimension_key)
        if dimension is not None:
            raw_values = dimension.get("states", dimension.get("values"))
    if not isinstance(raw_values, (list, tuple, set, frozenset)):
        return False
    allowed = {str(value).strip() for value in raw_values if str(value).strip()}
    return str(requested).strip() in allowed


def _capability_range(capability: Any, capability_key: str) -> tuple[float, float] | None:
    raw_range: Any = None
    dimension = _capability_dimension(capability, capability_key)
    if dimension is not None:
        raw_range = dimension.get("range", dimension.get("value_range"))
    if isinstance(raw_range, (list, tuple)) and len(raw_range) >= 2:
        minimum = _number(raw_range[0])
        maximum = _number(raw_range[1])
    elif capability_key == "target_temp":
        minimum = _number(
            _capability_value(capability, "min_temp")
            if _capability_value(capability, "min_temp") is not None
            else _capability_value(capability, "target_temp_min")
        )
        maximum = _number(
            _capability_value(capability, "max_temp")
            if _capability_value(capability, "max_temp") is not None
            else _capability_value(capability, "target_temp_max")
        )
    else:
        return None
    if minimum is None or maximum is None or minimum > maximum:
        return None
    return minimum, maximum


def validate_service_call(
    domain: str,
    service: str,
    data: Any,
    capability: Any = None,
) -> ServiceContractResult:
    """Validate one HA service call without mutating or silently filtering data."""
    service_key = f"{str(domain or '').strip()}.{str(service or '').strip()}"
    schema = SERVICE_CONTRACTS.get(service_key)
    if schema is None:
        return _rejected(service_key, "service_not_supported")
    if not isinstance(data, dict):
        return _rejected(service_key, "service_data_invalid")

    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        return _rejected(service_key, "service_contract_schema_invalid")

    unknown_fields = tuple(sorted(str(field) for field in data if field not in properties))
    if unknown_fields:
        return _rejected(service_key, "service_parameter_not_allowed", unknown_fields)

    missing_fields = tuple(str(field) for field in required if field not in data)
    if missing_fields:
        return _rejected(service_key, "service_parameter_required", missing_fields)

    one_of_schema = dict(schema)
    one_of_schema["_service_key"] = service_key
    one_of_error = _required_one_of_error(one_of_schema, data)
    if one_of_error is not None:
        return one_of_error

    for field, value in data.items():
        property_schema = properties.get(field)
        if not isinstance(property_schema, dict):
            return _rejected(service_key, "service_contract_schema_invalid", (str(field),))
        reason = _value_error_reason(value, property_schema)
        if reason:
            return _rejected(service_key, reason, (str(field),))
        capability_key = property_schema.get("capabilityValues")
        if capability is not None and isinstance(capability_key, str):
            if not _capability_allows(capability, capability_key, value):
                return _rejected(
                    service_key,
                    "service_parameter_not_supported_by_capability",
                    (str(field),),
                )
        capability_range_key = property_schema.get("capabilityRange")
        if capability is not None and isinstance(capability_range_key, str):
            capability_range = _capability_range(capability, capability_range_key)
            number = _number(value)
            if (
                capability_range is None
                or number is None
                or number < capability_range[0]
                or number > capability_range[1]
            ):
                return _rejected(
                    service_key,
                    "service_parameter_not_supported_by_capability",
                    (str(field),),
                )

    relations = schema.get("relations")
    if isinstance(relations, list):
        for relation in relations:
            if not isinstance(relation, dict) or relation.get("operator") != "<=":
                continue
            left = str(relation.get("left") or "")
            right = str(relation.get("right") or "")
            if left in data and right in data and float(data[left]) > float(data[right]):
                return _rejected(
                    service_key,
                    "service_parameter_relation_invalid",
                    (left, right),
                )

    return ServiceContractResult(
        allowed=True,
        service_key=service_key,
        normalized_data=copy.deepcopy(data),
    )


__all__ = [
    "ALLOWED_COMMAND_SERVICES",
    "CONTRACT_HASH",
    "CONTRACT_VERSION",
    "SERVICE_CONTRACTS",
    "SERVICES_TO_DOMAINS",
    "ServiceContractResult",
    "validate_service_call",
]
