"""HA adapter boundary for add-on command envelopes.

This module is allowed to touch Home Assistant runtime objects. Business
decision modules should stay in the add-on Core and call this boundary through a
plain command envelope.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any
from homeassistant.core import HomeAssistant

if __package__:
    from .service_contracts import ServiceContractResult, validate_service_call
    from .output_contracts import begin_output_attempt, finalize_output_attempt
else:
    _contract_module_name = "_smart_agent_service_contracts_runtime"
    _contract_module = sys.modules.get(_contract_module_name)
    if _contract_module is None:
        _contract_path = Path(__file__).with_name("service_contracts.py")
        _contract_spec = importlib.util.spec_from_file_location(_contract_module_name, _contract_path)
        if _contract_spec is None or _contract_spec.loader is None:
            raise RuntimeError(f"unable to load HA service contract module: {_contract_path}")
        _contract_module = importlib.util.module_from_spec(_contract_spec)
        sys.modules[_contract_module_name] = _contract_module
        _contract_spec.loader.exec_module(_contract_module)
    ServiceContractResult = _contract_module.ServiceContractResult
    validate_service_call = _contract_module.validate_service_call
    _output_module_name = "_smart_agent_output_contracts_runtime"
    _output_module = sys.modules.get(_output_module_name)
    if _output_module is None:
        _output_path = Path(__file__).with_name("output_contracts.py")
        _output_spec = importlib.util.spec_from_file_location(_output_module_name, _output_path)
        if _output_spec is None or _output_spec.loader is None:
            raise RuntimeError(f"unable to load output contract module: {_output_path}")
        _output_module = importlib.util.module_from_spec(_output_spec)
        sys.modules[_output_module_name] = _output_module
        _output_spec.loader.exec_module(_output_module)
    begin_output_attempt = _output_module.begin_output_attempt
    finalize_output_attempt = _output_module.finalize_output_attempt


_POST_STATE_VERIFY_TIMEOUT_SECONDS = 2.0
_POST_STATE_VERIFY_INTERVAL_SECONDS = 0.1
_EXECUTION_RECEIPT_VERSION = "0.1"
_DISPATCH_AUTHORITY_SEAL = object()
_USER_OUTPUT_AUTHORITY_SEAL = object()


def _host_envelope_digest(envelope: dict[str, Any]) -> str:
    """Bind an in-process dispatch authority to one exact JSON envelope."""
    try:
        canonical = json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("verified_dispatch_envelope_invalid") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _VerifiedDispatchAuthority:
    """Opaque host capability issued only after proof verification/consumption."""

    __slots__ = ("_seal", "_used", "envelope_digest", "proof_jti")

    def __init__(self, envelope_digest: str, proof_jti: str, *, seal: object) -> None:
        if seal is not _DISPATCH_AUTHORITY_SEAL:
            raise ValueError("verified_dispatch_authority_constructor_forbidden")
        self._seal = seal
        self._used = False
        self.envelope_digest = envelope_digest
        self.proof_jti = proof_jti


class _UserExplicitOutputAuthority:
    """One-use host capability for one exact authenticated TTS test call."""

    __slots__ = ("_seal", "_used", "service_key", "target_entity_id", "user_id")

    def __init__(
        self,
        *,
        user_id: str,
        service_key: str,
        target_entity_id: str,
        seal: object,
    ) -> None:
        if seal is not _USER_OUTPUT_AUTHORITY_SEAL:
            raise ValueError("user_output_authority_constructor_forbidden")
        self._seal = seal
        self._used = False
        self.user_id = user_id
        self.service_key = service_key
        self.target_entity_id = target_entity_id


def _bind_user_explicit_output_authority(
    *,
    authenticated_user_id: str,
    domain: str,
    service: str,
    target_entity_id: str,
) -> _UserExplicitOutputAuthority:
    """Bind a verified HA user to one exact supported diagnostic output."""
    user_id = str(authenticated_user_id or "").strip()
    domain_text = str(domain or "").strip().lower()
    service_text = str(service or "").strip().lower()
    target_text = str(target_entity_id or "").strip()
    if not user_id or (domain_text, service_text) != ("tts", "speak") or not target_text:
        raise ValueError("user_output_authority_binding_invalid")
    return _UserExplicitOutputAuthority(
        user_id=user_id,
        service_key=f"{domain_text}.{service_text}",
        target_entity_id=target_text,
        seal=_USER_OUTPUT_AUTHORITY_SEAL,
    )


def _consume_user_output_authority(
    authority: Any,
    *,
    service_key: str,
    target_entity_id: str,
) -> bool:
    valid = bool(
        isinstance(authority, _UserExplicitOutputAuthority)
        and authority._seal is _USER_OUTPUT_AUTHORITY_SEAL
        and authority._used is False
        and authority.service_key == service_key
        and authority.target_entity_id == target_entity_id
        and bool(authority.user_id)
    )
    if valid:
        authority._used = True
    return valid


def _bind_verified_dispatch_authority(
    envelope: dict[str, Any],
    verified_proof: dict[str, Any],
) -> _VerifiedDispatchAuthority:
    """Convert already verified and consumed proof claims into a sink capability."""
    digest = _host_envelope_digest(envelope)
    proof_digest = str(verified_proof.get("envelope_sha256") or "").strip().lower()
    proof_jti = str(verified_proof.get("jti") or "").strip().lower()
    if proof_digest != digest or len(proof_jti) != 64:
        raise ValueError("verified_dispatch_authority_binding_invalid")
    return _VerifiedDispatchAuthority(
        digest,
        proof_jti,
        seal=_DISPATCH_AUTHORITY_SEAL,
    )


def _dispatch_authority_matches(
    authority: Any,
    envelope: dict[str, Any],
) -> bool:
    valid = bool(
        isinstance(authority, _VerifiedDispatchAuthority)
        and authority._seal is _DISPATCH_AUTHORITY_SEAL
        and authority._used is False
        and authority.envelope_digest == _host_envelope_digest(envelope)
    )
    if valid:
        # Consume before the first await in the physical sink. A local caller
        # cannot reuse the in-process capability even if it retains a reference.
        authority._used = True
    return valid


def async_get_state(hass: HomeAssistant, entity_id: str) -> Any:
    """最小运行时读取：返回指定实体当前 state 对象。"""
    return hass.states.get(entity_id)


def _state_snapshot(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Serialize the pre-execution HA state needed for rollback/audit."""
    state_obj = async_get_state(hass, entity_id)
    if state_obj is None:
        return {
            "entity_id": entity_id,
            "available": False,
            "state": "",
            "attributes": {},
            "last_changed": "",
            "last_updated": "",
        }
    attrs = getattr(state_obj, "attributes", {})
    return {
        "entity_id": entity_id,
        "available": True,
        "state": str(getattr(state_obj, "state", "") or ""),
        "attributes": attrs if isinstance(attrs, dict) else {},
        "last_changed": str(getattr(state_obj, "last_changed", "") or ""),
        "last_updated": str(getattr(state_obj, "last_updated", "") or ""),
    }


def _brightness_pct_from_snapshot(snapshot: dict[str, Any]) -> int | None:
    attrs = snapshot.get("attributes") if isinstance(snapshot.get("attributes"), dict) else {}
    raw = attrs.get("brightness")
    try:
        brightness = float(raw)
    except (TypeError, ValueError):
        return None
    if brightness < 0:
        return 0
    if brightness > 255:
        brightness = 255
    return int(round(brightness * 100 / 255))


def _numeric_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalized_vector(value: Any, length: int) -> tuple[float, ...] | None:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        return None
    values = tuple(_numeric_value(item) for item in value)
    if any(item is None for item in values):
        return None
    return tuple(float(item) for item in values if item is not None)


def _attribute_check(expected: Any, actual: Any, *, verified: bool) -> dict[str, Any]:
    return {"expected": expected, "actual": actual, "verified": bool(verified)}


def _light_attribute_checks(
    command: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    data = command.get("data") if isinstance(command.get("data"), dict) else {}
    attrs = snapshot.get("attributes") if isinstance(snapshot.get("attributes"), dict) else {}
    checks: dict[str, dict[str, Any]] = {}

    if "brightness_pct" in data:
        requested = _numeric_value(data.get("brightness_pct"))
        expected = int(round(requested)) if requested is not None else data.get("brightness_pct")
        actual = _brightness_pct_from_snapshot(snapshot)
        checks["brightness_pct"] = _attribute_check(
            expected,
            actual,
            verified=requested is not None and actual is not None and abs(actual - requested) <= 1,
        )

    if "color_temp_kelvin" in data:
        requested = _numeric_value(data.get("color_temp_kelvin"))
        expected = int(round(requested)) if requested is not None else data.get("color_temp_kelvin")
        actual_value = _numeric_value(attrs.get("color_temp_kelvin"))
        if actual_value is None:
            actual_mired = _numeric_value(attrs.get("color_temp"))
            if actual_mired and actual_mired > 0:
                actual_value = 1_000_000 / actual_mired
        actual = int(round(actual_value)) if actual_value is not None else None
        checks["color_temp_kelvin"] = _attribute_check(
            expected,
            actual,
            verified=(
                requested is not None
                and actual_value is not None
                and abs(actual_value - requested) <= 100
            ),
        )

    if "color_temp" in data:
        requested = _numeric_value(data.get("color_temp"))
        expected = int(round(requested)) if requested is not None else data.get("color_temp")
        actual_value = _numeric_value(attrs.get("color_temp"))
        if actual_value is None:
            actual_kelvin = _numeric_value(attrs.get("color_temp_kelvin"))
            if actual_kelvin and actual_kelvin > 0:
                actual_value = 1_000_000 / actual_kelvin
        actual = int(round(actual_value)) if actual_value is not None else None
        checks["color_temp"] = _attribute_check(
            expected,
            actual,
            verified=(
                requested is not None
                and actual_value is not None
                and abs(actual_value - requested) <= 2
            ),
        )

    if "effect" in data:
        expected = str(data.get("effect") or "")
        actual = str(attrs.get("effect") or "")
        checks["effect"] = _attribute_check(expected, actual, verified=actual == expected)

    vector_specs = {
        "rgb_color": (3, 2.0),
        "hs_color": (2, 2.0),
        "xy_color": (2, 0.02),
    }
    for key, (length, tolerance) in vector_specs.items():
        if key not in data:
            continue
        expected_vector = _normalized_vector(data.get(key), length)
        actual_vector = _normalized_vector(attrs.get(key), length)
        if key == "rgb_color":
            expected = [int(round(item)) for item in expected_vector] if expected_vector else data.get(key)
            actual = [int(round(item)) for item in actual_vector] if actual_vector else None
        else:
            expected = list(expected_vector) if expected_vector else data.get(key)
            actual = list(actual_vector) if actual_vector else None
        verified = bool(
            expected_vector
            and actual_vector
            and all(
                abs(actual_item - expected_item) <= tolerance
                for actual_item, expected_item in zip(actual_vector, expected_vector)
            )
        )
        checks[key] = _attribute_check(expected, actual, verified=verified)

    return checks


def _command_already_in_target_state(command: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    if not snapshot.get("available"):
        return False
    state = str(snapshot.get("state") or "").strip().lower()
    service = str(command.get("service") or "").strip()
    domain = str(command.get("domain") or "").strip()
    data = command.get("data") if isinstance(command.get("data"), dict) else {}

    if service == "turn_off":
        return state == "off"
    if service != "turn_on":
        return False
    if state != "on":
        return False
    if domain == "light":
        attribute_checks = _light_attribute_checks(command, snapshot)
        return all(item["verified"] for item in attribute_checks.values())
    return True


def _expected_post_state(command: dict[str, Any]) -> str | None:
    domain = str(command.get("domain") or "")
    service = str(command.get("service") or "")
    data = command.get("data") if isinstance(command.get("data"), dict) else {}
    if domain in {"light", "switch", "fan"} and service == "turn_on":
        return "on"
    if (
        domain in {"light", "switch", "fan", "climate", "media_player"}
        and service == "turn_off"
    ):
        return "off"
    if domain == "cover":
        return {"open_cover": "open", "close_cover": "closed"}.get(service)
    if domain == "climate" and service == "set_hvac_mode":
        return str(data.get("hvac_mode") or "").strip().lower() or None
    if domain == "media_player":
        return {
            "media_play": "playing",
            "media_pause": "paused",
        }.get(service)
    return None


def _post_state_verification(hass: Any, command: dict[str, Any]) -> dict[str, Any]:
    expected = _expected_post_state(command)
    domain = str(command.get("domain") or "")
    snapshot = _state_snapshot(hass, str(command.get("entity_id") or ""))
    actual = str(snapshot.get("state") or "").strip().lower()
    if expected is None:
        return {
            "expected": "",
            "actual": actual,
            "verified": False,
            "verification_supported": False,
            "verification_reason": "verification_contract_missing",
            "attribute_checks": {},
            "post_state_snapshot": snapshot,
        }
    attribute_checks = {}
    if expected == "on" and domain == "light":
        attribute_checks = _light_attribute_checks(command, snapshot)
    verified = bool(snapshot.get("available")) and actual == expected
    if attribute_checks:
        verified = verified and all(item["verified"] for item in attribute_checks.values())
    return {
        "expected": expected,
        "actual": actual,
        "verified": verified,
        "verification_supported": True,
        "verification_reason": "",
        "attribute_checks": attribute_checks,
        "post_state_snapshot": snapshot,
    }


async def _wait_for_post_state_verification(hass: Any, command: dict[str, Any]) -> dict[str, Any]:
    verification = _post_state_verification(hass, command)
    if (
        verification.get("verified")
        or verification.get("verification_supported") is False
    ):
        return verification
    deadline = time.monotonic() + max(0.0, float(_POST_STATE_VERIFY_TIMEOUT_SECONDS))
    interval = max(0.0, float(_POST_STATE_VERIFY_INTERVAL_SECONDS))
    while time.monotonic() < deadline:
        await asyncio.sleep(interval)
        verification = _post_state_verification(hass, command)
        if verification.get("verified"):
            return verification
    return verification


def _execution_receipt_fields(
    *,
    transport_status: str,
    verification: dict[str, Any] | None,
    workflow_status: str = "",
) -> dict[str, Any]:
    verification = verification if isinstance(verification, dict) else {}
    snapshot = verification.get("post_state_snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    if verification.get("verified") is True:
        effect_status = "verified_success"
    elif (
        verification.get("verification_supported") is False
        or snapshot.get("available") is False
        or transport_status == "transport_error"
    ):
        effect_status = "effect_unknown"
    else:
        effect_status = "verified_failed"
    if not workflow_status:
        workflow_status = {
            "verified_success": "completed",
            "verified_failed": "failed",
            "effect_unknown": "reconciliation_required",
        }[effect_status]
    retry_disposition = "manual_review" if effect_status == "effect_unknown" else "forbidden"
    return {
        "receipt_version": _EXECUTION_RECEIPT_VERSION,
        "verification_contract_version": (
            "ha_post_state.v1"
            if verification.get("verification_supported") is not False
            else "missing"
        ),
        "transport_status": transport_status,
        "effect_status": effect_status,
        "workflow_status": workflow_status,
        "retry_disposition": retry_disposition,
        "automatic_retry_allowed": False,
        "reconciliation_required": workflow_status == "reconciliation_required",
    }


def async_get_entity_registry(hass: HomeAssistant) -> Any:
    """最小运行时读取：返回实体 registry 快照对象。"""
    from homeassistant.helpers import entity_registry as er

    return er.async_get(hass)


def async_get_device_registry(hass: HomeAssistant) -> Any:
    """最小运行时读取：返回设备 registry 快照对象。"""
    from homeassistant.helpers import device_registry as dr

    return dr.async_get(hass)


def async_get_area_registry(hass: HomeAssistant) -> Any:
    """最小运行时读取：返回区域 registry 快照对象。"""
    from homeassistant.helpers import area_registry as ar

    return ar.async_get(hass)


def _area_entry_to_row(area: Any) -> dict[str, Any]:
    area_id = str(
        getattr(area, "id", "")
        or getattr(area, "area_id", "")
        or getattr(area, "slug", "")
        or ""
    ).strip()
    name = str(getattr(area, "name", "") or area_id).strip()
    return {
        "id": area_id or name,
        "name": name or area_id,
        "area_id": area_id,
        "device_count": 0,
        "source": "ha_area_registry",
    }


def _find_area(area_reg: Any, area_id_or_name: str) -> Any | None:
    target = str(area_id_or_name or "").strip()
    if not target:
        return None
    getter = getattr(area_reg, "async_get_area", None)
    if callable(getter):
        try:
            area = getter(target)
            if area is not None:
                return area
        except Exception:
            pass
    raw_areas = getattr(area_reg, "areas", None)
    area_items = raw_areas.values() if isinstance(raw_areas, dict) else ()
    folded = target.casefold()
    for area in area_items:
        area_id = str(getattr(area, "id", "") or getattr(area, "area_id", "") or "").strip()
        name = str(getattr(area, "name", "") or "").strip()
        if target in {area_id, name} or folded in {area_id.casefold(), name.casefold()}:
            return area
    return None


async def async_ensure_ha_area(
    hass: Any,
    *,
    name: str,
    area_id: str | None = None,
) -> dict[str, Any]:
    """Create or reuse a HA Area and return its normalized row."""
    area_name = str(name or "").strip()
    requested_id = str(area_id or "").strip()
    if not area_name and not requested_id:
        return {"ok": False, "error": "area_name_required", "error_type": "bad_request", "retryable": False}

    area_reg = async_get_area_registry(hass)
    existing = _find_area(area_reg, requested_id or area_name)
    if existing is None and area_name:
        existing = _find_area(area_reg, area_name)
    if existing is None:
        existing = area_reg.async_get_or_create(area_name or requested_id)
    row = _area_entry_to_row(existing)
    row["ok"] = True
    return row


async def async_delete_ha_area(hass: Any, area_id_or_name: str) -> dict[str, Any]:
    """Delete a HA Area by id or name and return a normalized result."""
    target = str(area_id_or_name or "").strip()
    if not target:
        return {"ok": False, "error": "area_id_required", "error_type": "bad_request", "retryable": False}

    area_reg = async_get_area_registry(hass)
    area = _find_area(area_reg, target)
    if area is None:
        return {
            "ok": False,
            "error": "area_not_found",
            "error_type": "not_found",
            "retryable": False,
            "area_id": target,
        }

    row = _area_entry_to_row(area)
    area_id = str(row.get("area_id") or row.get("id") or target)
    area_reg.async_delete(area_id)
    return {"ok": True, "deleted": True, **row}


async def async_rename_ha_area(hass: Any, area_id_or_name: str, name: str) -> dict[str, Any]:
    """Rename one HA Area without changing its stable registry identifier."""
    target = str(area_id_or_name or "").strip()
    next_name = str(name or "").strip()
    if not target or not next_name:
        return {"ok": False, "error": "area_id_and_name_required", "error_type": "bad_request", "retryable": False}
    area_reg = async_get_area_registry(hass)
    area = _find_area(area_reg, target)
    if area is None:
        return {"ok": False, "error": "area_not_found", "error_type": "not_found", "retryable": False, "area_id": target}
    before = _area_entry_to_row(area)
    area_id = str(before.get("area_id") or before.get("id") or target).strip()
    if str(before.get("name") or "").strip() == next_name:
        return {"ok": True, "status": "verified", "changed": False, "area": before}
    try:
        updated = area_reg.async_update(area_id, name=next_name)
    except Exception as exc:
        return {
            "ok": False,
            "error": "area_rename_failed",
            "error_type": "internal_error",
            "retryable": False,
            "area_id": area_id,
            "exception_type": type(exc).__name__,
        }
    after = _area_entry_to_row(updated)
    return {"ok": True, "status": "verified", "changed": True, "previous_name": before["name"], "area": after}


def _registry_entries(registry: Any, attribute: str) -> tuple[Any, ...]:
    rows = getattr(registry, attribute, None)
    if isinstance(rows, dict):
        return tuple(rows.values())
    if isinstance(rows, (list, tuple)):
        return tuple(rows)
    return ()


async def async_merge_ha_area(hass: Any, source_area_id: str, target_area_id: str) -> dict[str, Any]:
    """Move direct HA assignments to a target Area, then delete the source Area.

    The add-on owns SmartAgent configuration migration. This adapter is restricted
    to HA registry changes and returns a verified receipt only after all direct
    entity/device assignments have moved and the source Area is deleted.
    """
    source_key = str(source_area_id or "").strip()
    target_key = str(target_area_id or "").strip()
    if not source_key or not target_key:
        return {
            "ok": False,
            "error": "source_and_target_area_required",
            "error_type": "bad_request",
            "retryable": False,
        }

    area_registry = async_get_area_registry(hass)
    source_area = _find_area(area_registry, source_key)
    target_area = _find_area(area_registry, target_key)
    if source_area is None or target_area is None:
        missing = source_key if source_area is None else target_key
        return {
            "ok": False,
            "error": "area_not_found",
            "error_type": "not_found",
            "retryable": False,
            "area_id": missing,
        }

    source = _area_entry_to_row(source_area)
    target = _area_entry_to_row(target_area)
    source_id = str(source.get("area_id") or source.get("id") or source_key).strip()
    target_id = str(target.get("area_id") or target.get("id") or target_key).strip()
    if not source_id or not target_id or source_id == target_id:
        return {
            "ok": False,
            "error": "source_and_target_area_must_differ",
            "error_type": "bad_request",
            "retryable": False,
            "source_area_id": source_id or source_key,
            "target_area_id": target_id or target_key,
        }

    entity_registry = async_get_entity_registry(hass)
    device_registry = async_get_device_registry(hass)
    entity_ids = [
        str(getattr(entry, "entity_id", "") or "").strip()
        for entry in _registry_entries(entity_registry, "entities")
        if str(getattr(entry, "area_id", "") or "").strip() == source_id
        and str(getattr(entry, "entity_id", "") or "").strip()
    ]
    device_ids = [
        str(getattr(entry, "id", "") or getattr(entry, "device_id", "") or "").strip()
        for entry in _registry_entries(device_registry, "devices")
        if str(getattr(entry, "area_id", "") or "").strip() == source_id
        and str(getattr(entry, "id", "") or getattr(entry, "device_id", "") or "").strip()
    ]

    moved_entities: list[str] = []
    moved_devices: list[str] = []
    try:
        for entity_id in entity_ids:
            entity_registry.async_update_entity(entity_id, area_id=target_id)
            moved_entities.append(entity_id)
        for device_id in device_ids:
            device_registry.async_update_device(device_id, area_id=target_id)
            moved_devices.append(device_id)
        area_registry.async_delete(source_id)
    except Exception as exc:
        rollback_errors: list[str] = []
        for device_id in reversed(moved_devices):
            try:
                device_registry.async_update_device(device_id, area_id=source_id)
            except Exception as rollback_exc:  # pragma: no cover - defensive HA registry failure path
                rollback_errors.append(f"device:{device_id}:{rollback_exc.__class__.__name__}")
        for entity_id in reversed(moved_entities):
            try:
                entity_registry.async_update_entity(entity_id, area_id=source_id)
            except Exception as rollback_exc:  # pragma: no cover - defensive HA registry failure path
                rollback_errors.append(f"entity:{entity_id}:{rollback_exc.__class__.__name__}")
        return {
            "ok": False,
            "error": "area_merge_failed",
            "error_type": "internal_error",
            "retryable": False,
            "source_area_id": source_id,
            "target_area_id": target_id,
            "exception_type": exc.__class__.__name__,
            "rollback": "restored" if not rollback_errors else "restore_failed",
            "rollback_errors": rollback_errors,
        }

    return {
        "ok": True,
        "status": "verified",
        "source_area": source,
        "target_area": target,
        "source_area_id": source_id,
        "target_area_id": target_id,
        "migrated_entity_ids": moved_entities,
        "migrated_device_ids": moved_devices,
        "deleted_source_area": True,
    }


def get_device_info_snapshot(coord: Any) -> dict[str, Any]:
    """最小只读读取面：返回 coord.device_info 的安全 dict 视图。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 该快照用于 presence payload 的组装（第二阶段最小下沉切口）。
    """
    device_info = getattr(coord, "device_info", None)
    if not isinstance(device_info, dict):
        return {}
    return dict(device_info)


def get_room_topology_cache_snapshot(coord: Any) -> dict[Any, set[Any]]:
    """最小只读读取面：返回 coord._room_topology_cache 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 该快照用于 diagnostics/UI 汇总，避免直接读取可变内存态。
    """
    cache = getattr(coord, "_room_topology_cache", None)
    if not isinstance(cache, dict) or not cache:
        return {}

    snapshot: dict[Any, set[Any]] = {}
    for key, raw_value in cache.items():
        if isinstance(raw_value, set):
            snapshot[key] = set(raw_value)
        elif isinstance(raw_value, (list, tuple)):
            snapshot[key] = set(raw_value)
        else:
            snapshot[key] = set()
    return snapshot


def get_transactions_cache_snapshot(coord: Any) -> list[dict[str, Any]]:
    """最小只读读取面：返回 coord._transactions_cache 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。
    """
    cache = getattr(coord, "_transactions_cache", None)
    if not isinstance(cache, list) or not cache:
        return []

    snapshot: list[dict[str, Any]] = []
    for item in cache:
        if isinstance(item, dict):
            snapshot.append(dict(item))
    return snapshot


def get_ai_scenes_cache_snapshot(coord: Any) -> list[dict[str, Any]]:
    """最小只读读取面：返回 coord._ai_scenes_cache 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。
    """
    cache = getattr(coord, "_ai_scenes_cache", None)
    if not isinstance(cache, list) or not cache:
        return []

    snapshot: list[dict[str, Any]] = []
    for item in cache:
        if isinstance(item, dict):
            snapshot.append(dict(item))
    return snapshot


def get_habits_snapshot(coord: Any) -> list[tuple[str, bool]]:
    """最小只读读取面：返回 coord._habits 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。

    兼容说明：
    - 历史上该 helper 命名为 get_habits_snapshot；新增的 get_habits_cache_snapshot 是等价别名，
      用于明确 "cache" 语义，便于未来统一收口。
    """
    habits = getattr(coord, "_habits", None)
    if not isinstance(habits, (list, tuple)) or not habits:
        return []

    snapshot: list[tuple[str, bool]] = []
    for item in habits:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        content, locked = item
        if not isinstance(content, str):
            continue
        snapshot.append((content, bool(locked)))
    return snapshot


def get_habits_cache_snapshot(coord: Any) -> list[tuple[str, bool]]:
    """最小只读读取面：返回 coord._habits 的安全副本（cache 语义别名）。

    说明：
    - 仅负责读取 + 最小形态保护 + 返回安全副本；不承载任何业务逻辑。
    - 与 get_habits_snapshot 等价，避免 WS/HTTP 层直接触碰 coord._habits。
    """
    return get_habits_snapshot(coord)


def get_rules_snapshot(coord: Any) -> list[tuple[str, bool]]:
    """最小只读读取面：返回 coord._rules 的安全副本。

    说明：
    - 仅负责从宿主 coordinator 上读取并做最小形态保护；不承载任何业务逻辑。
    - 返回值用于 WS/HTTP 层组装展示 payload，避免直接引用可变内存态。
    """
    rules = getattr(coord, "_rules", None)
    if not isinstance(rules, (list, tuple)) or not rules:
        return []

    snapshot: list[tuple[str, bool]] = []
    for item in rules:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        content, locked = item
        if not isinstance(content, str):
            continue
        snapshot.append((content, bool(locked)))
    return snapshot


async def async_call_service(
    hass: Any,
    domain: str,
    service: str,
    data: dict[str, Any] | None = None,
    *,
    blocking: bool = True,
    execution_class: str = "",
    actor_ref: str = "",
    authority: Any = None,
    output_ledger_publisher: Any = None,
) -> Any:
    """Execute an explicitly classified non-autonomous HA service call."""
    domain_text = str(domain or "").strip().lower()
    service_text = str(service or "").strip().lower()
    class_text = str(execution_class or "").strip().lower()
    actor_text = str(actor_ref or "").strip()
    service_key = f"{domain_text}.{service_text}"
    internal_policy = {
        ("notification", "coordinator.notify"): {
            "persistent_notification.create",
        },
        ("notification", "coordinator.addon_repair"): {
            "persistent_notification.create",
            "persistent_notification.dismiss",
        },
        ("notification", "coordinator.pairing"): {
            "persistent_notification.create",
        },
    }
    authority_ref = actor_text
    if class_text == "user_explicit_output":
        target_entity_id = str(
            (data if isinstance(data, dict) else {}).get("entity_id") or ""
        ).strip()
        allowed = _consume_user_output_authority(
            authority,
            service_key=service_key,
            target_entity_id=target_entity_id,
        )
        if allowed:
            authority_ref = str(authority.user_id)
    else:
        allowed = service_key in internal_policy.get((class_text, actor_text), set())
    if not allowed:
        raise ValueError("classified_ha_service_call_required")
    payload = data if isinstance(data, dict) else {}
    output_attempt = None
    if class_text in {"notification", "user_explicit_output"}:
        try:
            detached_payload = json.loads(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("output_payload_invalid") from exc
        payload = detached_payload
        if class_text == "user_explicit_output":
            target_ref = str(payload.get("entity_id") or "").strip()
            audience_ref = target_ref
            ttl_seconds = 30
        else:
            notification_id = str(payload.get("notification_id") or "").strip()
            target_ref = notification_id or "ha:persistent_notification_store"
            audience_ref = "ha:authenticated_frontend_users"
            ttl_seconds = 86_400
        output_attempt = begin_output_attempt(
            execution_class=class_text,
            authority_ref=authority_ref,
            service_key=service_key,
            target_ref=target_ref,
            payload=payload,
            audience_ref=audience_ref,
            ttl_seconds=ttl_seconds,
        )
    output_claim = None
    publisher_enabled = bool(
        output_attempt is not None
        and getattr(output_ledger_publisher, "enabled", False) is True
    )
    if publisher_enabled:
        claim = getattr(output_ledger_publisher, "async_claim", None)
        finalize = getattr(output_ledger_publisher, "async_finalize", None)
        if not callable(claim) or not callable(finalize):
            raise ValueError("output_ledger_publisher_invalid")
        output_claim = await claim(output_attempt)

    try:
        await hass.services.async_call(domain_text, service_text, payload, blocking=blocking)
    except Exception as exc:
        if output_attempt is not None:
            receipt = finalize_output_attempt(output_attempt, accepted_by_ha=False)
            try:
                setattr(exc, "smartagent_output_receipt", receipt.to_dict())
            except Exception:
                pass
            if output_claim is not None:
                try:
                    await output_ledger_publisher.async_finalize(
                        receipt,
                        output_claim,
                    )
                except Exception as ledger_exc:
                    try:
                        setattr(
                            exc,
                            "smartagent_output_ledger_error_type",
                            ledger_exc.__class__.__name__,
                        )
                    except Exception:
                        pass
        raise
    if output_attempt is not None:
        receipt = finalize_output_attempt(output_attempt, accepted_by_ha=True)
        if output_claim is not None:
            try:
                await output_ledger_publisher.async_finalize(
                    receipt,
                    output_claim,
                )
            except Exception as exc:
                try:
                    setattr(exc, "smartagent_output_receipt", receipt.to_dict())
                except Exception:
                    pass
                raise
        return receipt
    return None


async def async_reload_scenes(hass: Any, *, authority: Any = None) -> None:
    """Reload HA scene YAML through the adapter boundary."""
    await async_call_service(
        hass,
        "scene",
        "reload",
        {},
        execution_class="scene_maintenance",
        authority=authority,
    )


async def async_create_scene(
    hass: Any,
    *,
    scene_id: str,
    entities: dict[str, Any],
    authority: Any = None,
) -> None:
    """Create an ephemeral HA scene through the adapter boundary."""
    await async_call_service(
        hass,
        "scene",
        "create",
        {"scene_id": scene_id, "entities": entities if isinstance(entities, dict) else {}},
        execution_class="scene_maintenance",
        authority=authority,
    )


async def async_delete_scene(hass: Any, entity_id: str, *, authority: Any = None) -> None:
    """Delete a HA scene entity through the adapter boundary."""
    await async_call_service(
        hass,
        "scene",
        "delete",
        {"entity_id": entity_id},
        execution_class="scene_maintenance",
        authority=authority,
    )


async def async_reload_automations(hass: Any, *, authority: Any = None) -> None:
    """Reload HA automations through the adapter boundary."""
    await async_call_service(
        hass,
        "automation",
        "reload",
        {},
        execution_class="scene_maintenance",
        authority=authority,
    )


def list_binary_sensor_states(hass: HomeAssistant) -> list[dict[str, Any]]:
    """返回 binary_sensor 的最小只读快照列表。"""
    rows: list[dict[str, Any]] = []
    for st in hass.states.async_all("binary_sensor"):
        attrs = st.attributes if isinstance(st.attributes, dict) else {}
        rows.append({
            "entity_id": st.entity_id,
            "state": st.state,
            "attributes": attrs,
        })
    return rows


async def async_run_in_executor(hass: HomeAssistant, func: Any, *args: Any) -> Any:
    """统一 executor 调用边界，供宿主桥接层复用。"""
    return await hass.async_add_executor_job(func, *args)


class _ServiceContractError(ValueError):
    def __init__(self, result: ServiceContractResult) -> None:
        super().__init__(result.reason_code)
        self.result = result


def _json_error(
    request_id: str,
    error: str,
    *,
    error_type: str = "execution_error",
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "request_id": request_id,
        "ok": False,
        "results": [],
        "error": error,
        "error_type": error_type,
        "retryable": retryable,
    }
    if details:
        payload["details"] = details
    return payload


def _envelope_safety_error(envelope: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    safety = envelope.get("safety") if isinstance(envelope, dict) else None

    def _invalid_safety(reason: str) -> tuple[str, dict[str, Any]]:
        return (
            "invalid_safety_envelope",
            {
                "risk_level": "unknown",
                "requires_confirmation": False,
                "reason": reason,
            },
        )

    if not isinstance(envelope, dict) or "safety" not in envelope:
        return _invalid_safety("missing_safety")
    if not isinstance(safety, dict):
        return _invalid_safety("invalid_safety")
    if "risk_level" not in safety:
        return _invalid_safety("missing_risk_level")
    raw_risk_level = safety.get("risk_level")
    if not isinstance(raw_risk_level, str):
        return _invalid_safety("invalid_risk_level")
    risk_level = raw_risk_level.strip().lower()
    if not risk_level:
        return _invalid_safety("invalid_risk_level")
    requires_confirmation = bool(safety.get("requires_confirmation", False))
    reason = str(safety.get("reason") or "")

    if requires_confirmation:
        return (
            "confirmation_required",
            {
                "risk_level": risk_level,
                "requires_confirmation": True,
                "reason": reason,
            },
        )
    if risk_level != "safe":
        return (
            "unsafe_risk_level",
            {
                "risk_level": risk_level,
                "requires_confirmation": False,
                "reason": reason,
            },
        )
    return None


def _normalize_command(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("command must be an object")
    entity_id = str(raw.get("entity_id") or "").strip()
    domain = str(raw.get("domain") or "").strip()
    service = str(raw.get("service") or "").strip()
    data = raw.get("data", raw.get("params", {}))
    if not entity_id:
        raise ValueError("entity_id required")
    if "." not in entity_id:
        raise ValueError("entity_id must include domain prefix")
    inferred_domain = entity_id.split(".", 1)[0]
    if not domain:
        domain = inferred_domain
    if domain != inferred_domain:
        raise ValueError(f"domain mismatch: {domain} != {inferred_domain}")
    if not service:
        raise ValueError("service required")
    contract_result = validate_service_call(domain, service, data)
    if not contract_result.allowed:
        raise _ServiceContractError(contract_result)
    return {
        "entity_id": entity_id,
        "domain": domain,
        "service": service,
        "data": contract_result.normalized_data or {},
    }


async def async_execute_command_envelope(
    hass: Any,
    envelope: dict[str, Any],
    *,
    authority: _VerifiedDispatchAuthority | None = None,
) -> dict[str, Any]:
    """Execute a CommandEnvelope through HA services and return ExecutionResult."""
    request_id = str((envelope or {}).get("request_id") or "")
    if not request_id:
        request_id = "unknown"
    try:
        authority_valid = _dispatch_authority_matches(authority, envelope)
    except (TypeError, ValueError):
        authority_valid = False
    if not authority_valid:
        return _json_error(
            request_id,
            "verified_dispatch_authority_required",
            error_type="forbidden",
            retryable=False,
        )
    commands_raw = (envelope or {}).get("commands")
    if not isinstance(commands_raw, list) or not commands_raw:
        return _json_error(request_id, "commands_required", error_type="bad_request")
    safety_error = _envelope_safety_error(envelope if isinstance(envelope, dict) else {})
    if safety_error is not None:
        error, details = safety_error
        return _json_error(
            request_id,
            error,
            error_type="safety_blocked",
            retryable=False,
            details=details,
        )

    policy = (envelope or {}).get("execution_policy")
    policy = policy if isinstance(policy, dict) else {}
    stop_on_first_error = bool(policy.get("stop_on_first_error", True))
    results: list[dict[str, Any]] = []
    pre_state_snapshot: list[dict[str, Any]] = []
    stopped_after_error = False
    for raw in commands_raw:
        if stopped_after_error:
            entity_id = str(raw.get("entity_id", "") if isinstance(raw, dict) else "")
            domain = str(raw.get("domain", "") if isinstance(raw, dict) else "")
            service = str(raw.get("service", "") if isinstance(raw, dict) else "")
            results.append({
                "entity_id": entity_id,
                "domain": domain,
                "service": service,
                "ok": False,
                "status": "skipped",
                "error": "command_skipped_after_failure",
                "error_type": "execution_skipped",
                "retryable": False,
                "latency_ms": 0,
                "data": {},
                **_execution_receipt_fields(
                    transport_status="not_sent",
                    verification=None,
                    workflow_status="skipped",
                ),
            })
            continue
        started = time.monotonic()
        try:
            command = _normalize_command(raw)
        except _ServiceContractError as exc:
            contract_result = exc.result
            results.append({
                "entity_id": str(raw.get("entity_id", "") if isinstance(raw, dict) else ""),
                "domain": str(raw.get("domain", "") if isinstance(raw, dict) else ""),
                "service": str(raw.get("service", "") if isinstance(raw, dict) else ""),
                "ok": False,
                "error": contract_result.reason_code,
                "error_type": "service_contract_rejected",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "data": {},
                "status": "failed",
                "details": {
                    "service_key": contract_result.service_key,
                    "invalid_fields": list(contract_result.invalid_fields),
                },
                **_execution_receipt_fields(
                    transport_status="not_sent",
                    verification=None,
                ),
            })
            if stop_on_first_error:
                stopped_after_error = True
            continue
        except ValueError as exc:
            results.append({
                "entity_id": str(raw.get("entity_id", "") if isinstance(raw, dict) else ""),
                "domain": "",
                "service": "",
                "ok": False,
                "error": str(exc),
                "error_type": "bad_request",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "data": {},
                "status": "failed",
                **_execution_receipt_fields(
                    transport_status="not_sent",
                    verification=None,
                ),
            })
            if stop_on_first_error:
                stopped_after_error = True
            continue

        snapshot = _state_snapshot(hass, command["entity_id"])
        pre_state_snapshot.append(snapshot)
        if _command_already_in_target_state(command, snapshot):
            verification = _post_state_verification(hass, command)
            results.append({
                **command,
                "ok": True,
                "executed": False,
                "service_call_succeeded": None,
                "error": "",
                "error_type": "",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "status": "skipped",
                "reason": "already_in_target_state",
                **verification,
                **_execution_receipt_fields(
                    transport_status="not_sent",
                    verification=verification,
                    workflow_status="skipped",
                ),
            })
            continue
        try:
            await hass.services.async_call(
                command["domain"],
                command["service"],
                {"entity_id": command["entity_id"], **command["data"]},
                blocking=True,
            )
            verification = await _wait_for_post_state_verification(hass, command)
            receipt = _execution_receipt_fields(
                transport_status="acknowledged",
                verification=verification,
            )
            effect_status = str(receipt["effect_status"])
            verified = effect_status == "verified_success"
            unknown = effect_status == "effect_unknown"
            results.append({
                **command,
                "ok": verified,
                "executed": True,
                "service_call_succeeded": True,
                "error": "" if verified else "physical_effect_unknown" if unknown else "post_state_not_converged",
                "error_type": "" if verified else "effect_unknown" if unknown else "state_verification_failed",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "status": "succeeded" if verified else "effect_unknown" if unknown else "verification_failed",
                **verification,
                **receipt,
            })
            if not verified and stop_on_first_error:
                stopped_after_error = True
        except Exception as exc:
            verification = _post_state_verification(hass, command)
            receipt = _execution_receipt_fields(
                transport_status="transport_error",
                verification=verification,
            )
            verified = receipt["effect_status"] == "verified_success"
            results.append({
                **command,
                "ok": verified,
                "executed": True if verified else None,
                "service_call_succeeded": False,
                "error": "" if verified else str(exc) or exc.__class__.__name__,
                "error_type": "" if verified else "ha_service_error",
                "transport_error_detail": str(exc) or exc.__class__.__name__,
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "status": "succeeded" if verified else "effect_unknown",
                **verification,
                **receipt,
            })
            if not verified and stop_on_first_error:
                stopped_after_error = True

    ok = bool(results) and all(bool(item.get("ok")) for item in results)
    first_error = next((item for item in results if not item.get("ok")), None)
    succeeded_count = sum(1 for item in results if bool(item.get("ok")) and item.get("status") != "skipped")
    failed_count = sum(1 for item in results if not bool(item.get("ok")) and item.get("status") != "skipped")
    effect_unknown_count = sum(1 for item in results if item.get("effect_status") == "effect_unknown")
    skipped_count = sum(1 for item in results if item.get("status") == "skipped")
    partial_success = succeeded_count > 0 and (failed_count > 0 or skipped_count > 0)
    rollback_available = bool(pre_state_snapshot)
    rollback_mode = "manual" if rollback_available else "not_supported"
    if effect_unknown_count:
        effect_status = "effect_unknown"
        workflow_status = "reconciliation_required"
        retry_disposition = "manual_review"
    elif ok:
        effect_status = "verified_success"
        workflow_status = "completed"
        retry_disposition = "forbidden"
    else:
        effect_status = "verified_failed"
        workflow_status = "failed"
        retry_disposition = "forbidden"
    transport_statuses = {str(item.get("transport_status") or "not_sent") for item in results}
    if "transport_error" in transport_statuses:
        transport_status = "transport_error"
    elif "acknowledged" in transport_statuses:
        transport_status = "acknowledged"
    elif "sent" in transport_statuses:
        transport_status = "sent"
    else:
        transport_status = "not_sent"
    safety = envelope.get("safety") if isinstance(envelope.get("safety"), dict) else {}
    safety_context = safety.get("context") if isinstance(safety.get("context"), dict) else {}
    return {
        "request_id": request_id,
        "ok": ok,
        "results": results,
        "receipt_version": _EXECUTION_RECEIPT_VERSION,
        "transport_status": transport_status,
        "effect_status": effect_status,
        "workflow_status": workflow_status,
        "retry_disposition": retry_disposition,
        "automatic_retry_allowed": False,
        "reconciliation_required": workflow_status == "reconciliation_required",
        "effect_unknown_count": effect_unknown_count,
        "idempotency_key": str(envelope.get("idempotency_key") or request_id),
        "decision_snapshot_id": str(safety_context.get("world_snapshot_id") or ""),
        "policy_version": str(
            policy.get("policy_version") or safety.get("policy_version") or ""
        ),
        "pre_state_snapshot": pre_state_snapshot,
        "partial_success": partial_success,
        "stop_on_first_error": stop_on_first_error,
        "command_status": {
            "succeeded": succeeded_count,
            "failed": failed_count,
            "effect_unknown": effect_unknown_count,
            "skipped": skipped_count,
            "partial_success": partial_success,
        },
        "rollback_available": rollback_available,
        "rollback_mode": rollback_mode,
        "rollback_intent": {
            "required": bool(pre_state_snapshot),
            "strategy": "restore_pre_state",
            "state_snapshot_captured": bool(pre_state_snapshot),
            "state_snapshot": pre_state_snapshot,
            "available": rollback_available,
            "mode": rollback_mode,
            "failure_policy": "stop_on_first_error" if stop_on_first_error else "continue_on_error",
        },
        "error": str(first_error.get("error", "") if first_error else ""),
        "error_type": str(first_error.get("error_type", "") if first_error else ""),
        "retryable": bool(first_error.get("retryable", False) if first_error else False),
    }
