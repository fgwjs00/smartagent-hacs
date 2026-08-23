"""HA-host publisher for one exact current-admin maintenance transition.

The add-on prepares redacted persisted-state projections; this publisher binds
them to a fresh current HA administrator, then requests the exact local change.
It never calls a Home Assistant service or a device/provider transport.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import aiohttp

from .admin_actor import is_current_human_admin
from .const import (
    CONF_AI_ENABLED,
    CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED,
    CONF_MAINTENANCE_CHANGE_INGRESS_SECRET,
    CONF_MAINTENANCE_CHANGE_INGRESS_URL,
    CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET,
    DEFAULT_MAINTENANCE_CHANGE_INGRESS_URL,
)
from .maintenance_change_ingress import (
    maintenance_change_ingress_key_id,
    sign_maintenance_ai_management_enable_finalize_request,
    sign_maintenance_ai_management_enable_permit_request,
    sign_maintenance_ai_management_enable_reconcile_request,
    sign_maintenance_finalize_request,
    sign_maintenance_learning_mode_disable_request,
    sign_maintenance_prepare_ai_management_enable_request,
    sign_maintenance_prepare_learning_mode_disable_request,
    sign_maintenance_reserve_request,
    verify_maintenance_change_ingress_response,
)
from .refresh_registry_snapshot import ha_installation_digest


MAINTENANCE_DELEGATION_SCHEMA_VERSION = (
    "smartagent.maintenance_delegation_attestation.v0.1"
)
MAINTENANCE_RESERVE_PATH = (
    "/api/v1/internal/maintenance-delegations/reservations"
)
MAINTENANCE_FINALIZE_PATH = (
    "/api/v1/internal/maintenance-delegations/finalizations"
)
MAINTENANCE_APPLY_LEARNING_MODE_DISABLE_PATH = (
    "/api/v1/internal/maintenance-delegations/apply-learning-mode-disable"
)
MAINTENANCE_PREPARE_LEARNING_MODE_DISABLE_PATH = (
    "/api/v1/internal/maintenance-delegations/prepare-learning-mode-disable"
)
MAINTENANCE_PREPARE_AI_MANAGEMENT_ENABLE_PATH = (
    "/api/v1/internal/maintenance-delegations/prepare-ai-management-enable"
)
MAINTENANCE_PERMIT_AI_MANAGEMENT_ENABLE_PATH = (
    "/api/v1/internal/maintenance-delegations/permit-ai-management-enable"
)
MAINTENANCE_FINALIZE_AI_MANAGEMENT_ENABLE_PATH = (
    "/api/v1/internal/maintenance-delegations/finalize-ai-management-enable"
)
MAINTENANCE_RECONCILE_AI_MANAGEMENT_ENABLE_PATH = (
    "/api/v1/internal/maintenance-delegations/reconcile-ai-management-enable"
)
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
_RESERVATION_SEAL = object()
_EXECUTION_CLASSES = frozenset({"scene_maintenance", "admin_maintenance"})


class MaintenanceDelegationPublisherError(RuntimeError):
    """The maintenance delegation handshake failed closed."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise MaintenanceDelegationPublisherError(
            "maintenance_delegation_projection_invalid"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _secret(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) < 32
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise MaintenanceDelegationPublisherError(f"{name}_invalid")
    return value


def _safe_text(value: Any, *, field: str, maximum: int = 255) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise MaintenanceDelegationPublisherError(
            f"maintenance_delegation_{field}_invalid"
        )
    return value


def _digest_text(value: Any, *, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise MaintenanceDelegationPublisherError(
            f"maintenance_delegation_{field}_invalid"
        )
    return value


def _prefixed_hex_id(value: Any, *, prefix: str, field: str) -> str:
    if (
        type(value) is not str
        or not value.startswith(prefix)
        or len(value) != len(prefix) + 32
        or any(character not in "0123456789abcdef" for character in value[len(prefix) :])
    ):
        raise MaintenanceDelegationPublisherError(
            f"maintenance_delegation_{field}_invalid"
        )
    return value


def _validated_learning_mode_disable_projections(
    value: Any,
) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != {
        "resource_ref",
        "payload",
        "before_state",
        "expected_after_state",
        "backup_ref",
        "rollback_plan",
    } or any(type(item) is not dict for item in value.values()):
        raise MaintenanceDelegationPublisherError(
            "maintenance_change_preparation_projection_invalid"
        )
    projections = json.loads(_canonical(value))
    before = projections["before_state"]
    after = projections["expected_after_state"]
    version = before.get("version")
    if type(version) is not int or isinstance(version, bool) or version < 1:
        raise MaintenanceDelegationPublisherError(
            "maintenance_change_preparation_projection_invalid"
        )
    before_digest = _digest_text(
        before.get("settings_digest"), field="before_settings_digest"
    )
    after_digest = _digest_text(
        after.get("settings_digest"), field="after_settings_digest"
    )
    expected = {
        "resource_ref": {
            "schema_version": "smartagent.maintenance_resource.v0.1",
            "config_key": "system_settings",
            "field": "learning_mode",
        },
        "payload": {
            "schema_version": "smartagent.system_settings_patch.v0.1",
            "learning_mode": False,
        },
        "before_state": {
            "schema_version": "smartagent.system_settings_state.v0.1",
            "config_key": "system_settings",
            "field": "learning_mode",
            "value": True,
            "version": version,
            "settings_digest": before_digest,
        },
        "expected_after_state": {
            "schema_version": "smartagent.system_settings_state.v0.1",
            "config_key": "system_settings",
            "field": "learning_mode",
            "value": False,
            "version": version + 1,
            "settings_digest": after_digest,
        },
        "backup_ref": {
            "schema_version": "smartagent.maintenance_backup_ref.v0.1",
            "kind": "inline_digest_only",
            "config_key": "system_settings",
            "field": "learning_mode",
            "value": True,
            "version": version,
            "settings_digest": before_digest,
        },
        "rollback_plan": {
            "schema_version": "smartagent.maintenance_rollback_plan.v0.1",
            "strategy": "restore_system_settings_field",
            "config_key": "system_settings",
            "field": "learning_mode",
            "value": True,
            "automatic": False,
        },
    }
    if projections != expected:
        raise MaintenanceDelegationPublisherError(
            "maintenance_change_preparation_projection_invalid"
        )
    return projections


def _validated_ai_management_enable_projections(
    value: Any, *, bridge_config_entry_id: str
) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != {
        "resource_ref",
        "payload",
        "before_state",
        "expected_after_state",
        "backup_ref",
        "rollback_plan",
    } or any(type(item) is not dict for item in value.values()):
        raise MaintenanceDelegationPublisherError(
            "maintenance_host_change_projection_invalid"
        )
    entry_id = _safe_text(
        bridge_config_entry_id, field="bridge_entry_id"
    )
    projections = json.loads(_canonical(value))
    before_digest = _digest_text(
        projections["before_state"].get("options_digest"),
        field="before_options_digest",
    )
    after_digest = _digest_text(
        projections["expected_after_state"].get("options_digest"),
        field="after_options_digest",
    )
    expected = {
        "resource_ref": {
            "schema_version": "smartagent.maintenance_resource.v0.1",
            "kind": "ha_config_entry_options",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
        },
        "payload": {
            "schema_version": "smartagent.ha_config_entry_options_patch.v0.1",
            "ai_enabled": True,
        },
        "before_state": {
            "schema_version": "smartagent.ha_runtime_gate_state.v0.1",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": False,
            "options_digest": before_digest,
        },
        "expected_after_state": {
            "schema_version": "smartagent.ha_runtime_gate_state.v0.1",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": True,
            "options_digest": after_digest,
        },
        "backup_ref": {
            "schema_version": "smartagent.maintenance_backup_ref.v0.1",
            "kind": "inline_digest_only",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": False,
            "options_digest": before_digest,
        },
        "rollback_plan": {
            "schema_version": "smartagent.maintenance_rollback_plan.v0.1",
            "strategy": "restore_ha_config_entry_option",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": False,
            "automatic": False,
        },
    }
    if projections != expected or before_digest == after_digest:
        raise MaintenanceDelegationPublisherError(
            "maintenance_host_change_projection_invalid"
        )
    return projections


def _ai_management_state(entry: Any) -> dict[str, Any]:
    entry_id = _safe_text(
        getattr(entry, "entry_id", None), field="bridge_entry_id"
    )
    options = dict(getattr(entry, "options", {}) or {})
    value = options.get(CONF_AI_ENABLED)
    if type(value) is not bool:
        raise MaintenanceDelegationPublisherError(
            "maintenance_host_change_current_state_invalid"
        )
    return {
        "schema_version": "smartagent.ha_runtime_gate_state.v0.1",
        "bridge_config_entry_id": entry_id,
        "field": "ai_enabled",
        "value": value,
        "options_digest": _digest(options),
    }


def _build_ai_management_enable_projections(
    entry: Any,
) -> dict[str, dict[str, Any]]:
    before_state = _ai_management_state(entry)
    if before_state["value"] is not False:
        raise MaintenanceDelegationPublisherError(
            "maintenance_host_change_not_applicable"
        )
    entry_id = before_state["bridge_config_entry_id"]
    next_options = dict(getattr(entry, "options", {}) or {})
    next_options[CONF_AI_ENABLED] = True
    projections = {
        "resource_ref": {
            "schema_version": "smartagent.maintenance_resource.v0.1",
            "kind": "ha_config_entry_options",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
        },
        "payload": {
            "schema_version": "smartagent.ha_config_entry_options_patch.v0.1",
            "ai_enabled": True,
        },
        "before_state": before_state,
        "expected_after_state": {
            "schema_version": "smartagent.ha_runtime_gate_state.v0.1",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": True,
            "options_digest": _digest(next_options),
        },
        "backup_ref": {
            "schema_version": "smartagent.maintenance_backup_ref.v0.1",
            "kind": "inline_digest_only",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": False,
            "options_digest": before_state["options_digest"],
        },
        "rollback_plan": {
            "schema_version": "smartagent.maintenance_rollback_plan.v0.1",
            "strategy": "restore_ha_config_entry_option",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": False,
            "automatic": False,
        },
    }
    return _validated_ai_management_enable_projections(
        projections, bridge_config_entry_id=entry_id
    )


def _build_ai_management_reconciliation_projections(
    entry: Any,
    *,
    blocked_receipt_id: Any,
    blocked_receipt_digest: Any,
) -> dict[str, dict[str, Any]]:
    state = _ai_management_state(entry)
    if state["value"] is not False:
        raise MaintenanceDelegationPublisherError(
            "maintenance_host_reconciliation_safe_state_required"
        )
    receipt_id = _prefixed_hex_id(
        blocked_receipt_id, prefix="mchr_", field="blocked_receipt_id"
    )
    receipt_digest = _digest_text(
        blocked_receipt_digest, field="blocked_receipt_digest"
    )
    entry_id = state["bridge_config_entry_id"]
    return {
        "resource_ref": {
            "schema_version": "smartagent.maintenance_resource.v0.1",
            "kind": "ha_config_entry_options",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
        },
        "payload": {
            "schema_version": "smartagent.maintenance_reconciliation.v0.1",
            "action": "clear_effect_unknown_after_safe_readback",
            "blocked_receipt_id": receipt_id,
            "blocked_receipt_digest": receipt_digest,
        },
        "before_state": state,
        "expected_after_state": state,
        "backup_ref": {
            "schema_version": "smartagent.maintenance_backup_ref.v0.1",
            "kind": "not_required_safe_state_verified",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": False,
            "options_digest": state["options_digest"],
        },
        "rollback_plan": {
            "schema_version": "smartagent.maintenance_rollback_plan.v0.1",
            "strategy": "not_required_safe_state_verified",
            "bridge_config_entry_id": entry_id,
            "field": "ai_enabled",
            "value": False,
            "automatic": False,
        },
    }


def _url(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MaintenanceDelegationPublisherError(
            "maintenance_change_ingress_url_invalid"
        )
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise MaintenanceDelegationPublisherError(
            "maintenance_change_ingress_url_invalid"
        )
    return value.rstrip("/")


def _now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise MaintenanceDelegationPublisherError(
            "maintenance_delegation_publisher_clock_invalid"
        )
    try:
        return value.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MaintenanceDelegationPublisherError(
            "maintenance_delegation_publisher_clock_invalid"
        ) from exc


def _utc_text(value: datetime) -> str:
    return _now(lambda: value).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _utc(value: Any, *, field: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise MaintenanceDelegationPublisherError(
            f"maintenance_delegation_{field}_invalid"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MaintenanceDelegationPublisherError(
            f"maintenance_delegation_{field}_invalid"
        ) from exc
    if _utc_text(parsed) != value:
        raise MaintenanceDelegationPublisherError(
            f"maintenance_delegation_{field}_invalid"
        )
    return parsed


def maintenance_delegation_key_id(secret: str | bytes) -> str:
    raw = secret.encode("utf-8") if type(secret) is str else secret
    if type(raw) is not bytes or len(raw) < 32:
        raise MaintenanceDelegationPublisherError(
            "maintenance_delegation_secret_invalid"
        )
    return "mdak_" + hashlib.sha256(
        b"smartagent.maintenance-delegation.key-id.v1\x00" + raw
    ).hexdigest()[:24]


def _sign_delegation(
    *,
    delegation_jti: str,
    secret: str,
    ha_installation_digest_value: str,
    bridge_config_entry_id: str,
    admin_principal_digest: str,
    admin_session_digest: str,
    execution_class: str,
    operation_id: str,
    resource_ref_digest: str,
    payload_digest: str,
    before_state_digest: str,
    expected_after_state_digest: str,
    backup_ref_digest: str,
    rollback_plan_digest: str,
    controlled_device_effect_required: bool,
    issued_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    if execution_class not in _EXECUTION_CLASSES:
        raise MaintenanceDelegationPublisherError(
            "maintenance_delegation_execution_class_invalid"
        )
    if type(controlled_device_effect_required) is not bool:
        raise MaintenanceDelegationPublisherError(
            "maintenance_delegation_effect_flag_invalid"
        )
    if not delegation_jti.startswith("mdeleg_") or len(delegation_jti) != 39:
        raise MaintenanceDelegationPublisherError(
            "maintenance_delegation_jti_invalid"
        )
    facts = {
        "schema_version": MAINTENANCE_DELEGATION_SCHEMA_VERSION,
        "delegation_jti": delegation_jti,
        "key_id": maintenance_delegation_key_id(secret),
        "ha_installation_digest": ha_installation_digest_value,
        "bridge_config_entry_id": _safe_text(
            bridge_config_entry_id, field="bridge_entry_id"
        ),
        "admin_principal_digest": admin_principal_digest,
        "admin_session_digest": admin_session_digest,
        "execution_class": execution_class,
        "operation_id": _safe_text(operation_id, field="operation_id", maximum=128),
        "resource_ref_digest": resource_ref_digest,
        "payload_digest": payload_digest,
        "before_state_digest": before_state_digest,
        "expected_after_state_digest": expected_after_state_digest,
        "backup_ref_digest": backup_ref_digest,
        "rollback_plan_digest": rollback_plan_digest,
        "controlled_device_effect_required": controlled_device_effect_required,
        "issued_at": _utc_text(issued_at),
        "expires_at": _utc_text(expires_at),
    }
    for field in (
        "ha_installation_digest",
        "admin_principal_digest",
        "admin_session_digest",
        "resource_ref_digest",
        "payload_digest",
        "before_state_digest",
        "expected_after_state_digest",
        "backup_ref_digest",
        "rollback_plan_digest",
    ):
        if (
            type(facts[field]) is not str
            or len(facts[field]) != 64
            or any(character not in "0123456789abcdef" for character in facts[field])
        ):
            raise MaintenanceDelegationPublisherError(
                f"maintenance_delegation_{field}_invalid"
            )
    attestation_id = "mda_" + _digest(facts)[:32]
    signed = dict(facts, attestation_id=attestation_id)
    signature = hmac.new(
        _secret(secret, "maintenance_delegation_attestation_secret").encode(
            "utf-8"
        ),
        b"smartagent.maintenance-delegation.signature.v1\x00"
        + _canonical(signed).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return dict(
        signed,
        signature=signature,
        attestation_digest=_digest(dict(signed, signature=signature)),
    )


@dataclass(frozen=True, slots=True)
class MaintenanceDelegationPublisherConfig:
    enabled: bool
    ingress_url: str = DEFAULT_MAINTENANCE_CHANGE_INGRESS_URL
    ingress_secret: str = ""
    attestation_secret: str = ""

    @classmethod
    def from_entry(cls, entry: Any) -> "MaintenanceDelegationPublisherConfig":
        values = {
            **dict(getattr(entry, "data", {}) or {}),
            **dict(getattr(entry, "options", {}) or {}),
        }
        return cls(
            enabled=values.get(CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED, False),
            ingress_url=values.get(
                CONF_MAINTENANCE_CHANGE_INGRESS_URL,
                DEFAULT_MAINTENANCE_CHANGE_INGRESS_URL,
            ),
            ingress_secret=values.get(
                CONF_MAINTENANCE_CHANGE_INGRESS_SECRET, ""
            ),
            attestation_secret=values.get(
                CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET, ""
            ),
        ).validated()

    def validated(self) -> "MaintenanceDelegationPublisherConfig":
        if type(self.enabled) is not bool:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_ingress_enabled_invalid"
            )
        if not self.enabled:
            return self
        _url(self.ingress_url)
        ingress = _secret(
            self.ingress_secret, "maintenance_change_ingress_secret"
        )
        attestation = _secret(
            self.attestation_secret, "maintenance_delegation_attestation_secret"
        )
        if ingress == attestation:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_secret_reuse_forbidden"
            )
        return self


@dataclass(frozen=True, slots=True, init=False)
class MaintenancePreDispatchReservation:
    attempt_id: str
    attempt_digest: str
    delegation_jti: str
    state: str
    dispatch_permitted: bool
    execution_eligible: bool
    execution_permitted: bool
    change_applied: bool
    rollback_verified: bool
    device_effect_authority: str

    def __init__(self, projection: Mapping[str, Any], *, seal: object) -> None:
        if seal is not _RESERVATION_SEAL or type(projection) is not dict:
            raise MaintenanceDelegationPublisherError(
                "maintenance_reservation_constructor_forbidden"
            )
        for key, value in projection.items():
            object.__setattr__(self, key, value)


async def _post_json(
    session: aiohttp.ClientSession,
    *,
    url: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    async with session.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=_REQUEST_TIMEOUT,
    ) as response:
        try:
            body = await response.json(content_type=None)
        except Exception as exc:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_ingress_response_invalid"
            ) from exc
        if response.status != 200 or type(body) is not dict:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_ingress_request_rejected"
            )
        return body


class MaintenanceDelegationPublisher:
    """One HA-entry-owned, current-admin maintenance ledger publisher."""

    def __init__(
        self,
        hass: Any,
        entry: Any,
        *,
        config: MaintenanceDelegationPublisherConfig | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        session_factory: Callable[[], aiohttp.ClientSession] | None = None,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._config = (
            config or MaintenanceDelegationPublisherConfig.from_entry(entry)
        ).validated()
        self._clock = clock
        self._session_factory = session_factory or (
            lambda: aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT)
        )

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    async def _installation_digest(self) -> str:
        from homeassistant.helpers import instance_id

        installation_id = await instance_id.async_get(self._hass)
        return ha_installation_digest(installation_id)

    async def _post_with_safe_retry(
        self, *, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                session = self._session_factory()
                async with session:
                    return await _post_json(
                        session,
                        url=f"{_url(self._config.ingress_url)}{path}",
                        payload=payload,
                    )
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                MaintenanceDelegationPublisherError,
            ) as exc:
                last_error = exc
        raise MaintenanceDelegationPublisherError(
            "maintenance_change_ingress_transport_unknown"
        ) from last_error

    async def async_prepare_learning_mode_disable(self) -> dict[str, Any]:
        """Fetch the server-owned, redacted projection for the exact change."""

        if not self.enabled:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_ingress_disabled"
            )
        now = _now(self._clock)
        request = sign_maintenance_prepare_learning_mode_disable_request(
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_PREPARE_LEARNING_MODE_DISABLE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(
                    self._config.ingress_secret
                ): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="prepare_learning_mode_disable",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("operation_id")
            != "admin_maintenance.system_settings.learning_mode.disable.v0.1"
            or result.get("status") not in {"prepared", "already_disabled"}
            or type(result.get("settings_version")) is not int
            or isinstance(result.get("settings_version"), bool)
            or result.get("settings_version") < 1
            or result.get("settings_digest")
            != _digest_text(
                result.get("settings_digest"), field="settings_digest"
            )
            or result.get("state_verified") is not True
            or result.get("runtime_consumer_enabled") is not False
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not False
            or result.get("execution_permitted") is not False
            or result.get("change_applied") is not False
            or result.get("rollback_verified") is not False
            or result.get("controlled_device_effect_required") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_preparation_response_invalid"
            )
        if result["status"] == "already_disabled":
            if result.get("change_required") is not False or result.get(
                "projections"
            ) != {}:
                raise MaintenanceDelegationPublisherError(
                    "maintenance_change_preparation_response_invalid"
                )
            return result
        if result.get("change_required") is not True:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_preparation_response_invalid"
            )
        projections = _validated_learning_mode_disable_projections(
            result.get("projections")
        )
        if (
            result.get("projections_digest") != _digest(projections)
            or result["settings_version"]
            != projections["before_state"]["version"]
            or result["settings_digest"]
            != projections["before_state"]["settings_digest"]
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_preparation_response_invalid"
            )
        result["projections"] = projections
        return result

    async def async_disable_learning_mode(
        self,
        *,
        user: Any,
        admin_context: Any,
    ) -> dict[str, Any]:
        """Prepare, authorize, and apply only learning_mode true -> false."""

        if not self.enabled or not is_current_human_admin(user):
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_current_admin_required"
            )
        user_id = _safe_text(
            getattr(user, "id", None), field="admin_user_id"
        )
        if _safe_text(
            getattr(admin_context, "user_id", None),
            field="admin_context_user_id",
        ) != user_id:
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_admin_context_mismatch"
            )
        prepared = await self.async_prepare_learning_mode_disable()
        if prepared["status"] == "already_disabled":
            return prepared
        projections = prepared["projections"]
        reservation = await self.async_reserve(
            user=user,
            admin_context=admin_context,
            execution_class="admin_maintenance",
            operation_id=(
                "admin_maintenance.system_settings.learning_mode.disable.v0.1"
            ),
            controlled_device_effect_required=False,
            **projections,
        )
        return await self.async_apply_learning_mode_disable(
            reservation,
            **projections,
        )

    async def async_prepare_ai_management_enable(self) -> dict[str, Any]:
        """Check for an unfinished host mutation before creating a new one."""

        if not self.enabled:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_ingress_disabled"
            )
        now = _now(self._clock)
        request = sign_maintenance_prepare_ai_management_enable_request(
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_PREPARE_AI_MANAGEMENT_ENABLE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(
                    self._config.ingress_secret
                ): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="prepare_ai_management_enable",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("status")
            not in {
                "ready",
                "reconciliation_required",
                "reconciliation_blocked",
            }
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not False
            or result.get("execution_permitted") is not False
            or result.get("change_applied") is not False
            or result.get("rollback_verified") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_preparation_response_invalid"
            )
        if result["status"] == "ready":
            if result.get("host_change_permitted") is not False:
                raise MaintenanceDelegationPublisherError(
                    "maintenance_host_change_preparation_response_invalid"
                )
            return result
        if result["status"] == "reconciliation_blocked":
            if (
                result.get("operation_id")
                != "admin_maintenance.ha_runtime.ai_enabled.enable.v0.1"
                or result.get("effect_status") != "effect_unknown"
                or result.get("host_change_permitted") is not False
                or result.get("reconciliation_required") is not True
                or _prefixed_hex_id(
                    result.get("receipt_id"),
                    prefix="mchr_",
                    field="receipt_id",
                )
                != result.get("receipt_id")
                or _digest_text(
                    result.get("receipt_digest"), field="receipt_digest"
                )
                != result.get("receipt_digest")
            ):
                raise MaintenanceDelegationPublisherError(
                    "maintenance_host_change_preparation_response_invalid"
                )
            return result
        entry_id = _safe_text(
            getattr(self._entry, "entry_id", None), field="bridge_entry_id"
        )
        projections = _validated_ai_management_enable_projections(
            result.get("projections"), bridge_config_entry_id=entry_id
        )
        if (
            result.get("operation_id")
            != "admin_maintenance.ha_runtime.ai_enabled.enable.v0.1"
            or result.get("host_change_permitted") is not True
            or _prefixed_hex_id(
                result.get("permit_id"), prefix="mchp_", field="permit_id"
            )
            != result.get("permit_id")
            or _digest_text(
                result.get("permit_digest"), field="permit_digest"
            )
            != result.get("permit_digest")
            or _prefixed_hex_id(
                result.get("attempt_id"), prefix="mca_", field="attempt_id"
            )
            != result.get("attempt_id")
            or _digest_text(
                result.get("attempt_digest"), field="attempt_digest"
            )
            != result.get("attempt_digest")
            or result.get("projection_digest") != _digest(projections)
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_preparation_response_invalid"
            )
        result["projections"] = projections
        return result

    async def async_reconcile_ai_management_block(
        self,
        *,
        user: Any,
        admin_context: Any,
        blocked: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append a safe-disabled fact without mutating the HA entry."""

        if not self.enabled or not is_current_human_admin(user):
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_current_admin_required"
            )
        user_id = _safe_text(
            getattr(user, "id", None), field="admin_user_id"
        )
        if _safe_text(
            getattr(admin_context, "user_id", None),
            field="admin_context_user_id",
        ) != user_id:
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_admin_context_mismatch"
            )
        blocked_fact = (
            await self.async_prepare_ai_management_enable()
            if blocked is None
            else json.loads(_canonical(blocked))
        )
        if (
            type(blocked_fact) is not dict
            or blocked_fact.get("status") != "reconciliation_blocked"
            or blocked_fact.get("effect_status") != "effect_unknown"
            or blocked_fact.get("reconciliation_required") is not True
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_reconciliation_not_required"
            )
        current = _ai_management_state(self._entry)
        coordinator = self._hass.data.get("smart_agent", {}).get(
            getattr(self._entry, "entry_id", "")
        )
        if (
            current["value"] is not False
            or coordinator is None
            or getattr(coordinator, "_enabled", None) is not False
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_reconciliation_safe_state_required"
            )
        projections = _build_ai_management_reconciliation_projections(
            self._entry,
            blocked_receipt_id=blocked_fact.get("receipt_id"),
            blocked_receipt_digest=blocked_fact.get("receipt_digest"),
        )
        reservation = await self.async_reserve(
            user=user,
            admin_context=admin_context,
            execution_class="admin_maintenance",
            operation_id=(
                "admin_maintenance.ha_runtime.ai_enabled.reconcile_clear.v0.1"
            ),
            controlled_device_effect_required=False,
            **projections,
        )
        return await self.async_reconcile_ai_management_enable(
            reservation,
            blocked_receipt_id=blocked_fact["receipt_id"],
            blocked_receipt_digest=blocked_fact["receipt_digest"],
            observed_state=current,
            reason={"reason": "current_admin_safe_disabled_readback"},
        )

    async def async_enable_ai_management(
        self,
        *,
        user: Any,
        admin_context: Any,
    ) -> dict[str, Any]:
        """Reconcile, authorize, apply, and verify the host AI gate."""

        if not self.enabled or not is_current_human_admin(user):
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_current_admin_required"
            )
        user_id = _safe_text(
            getattr(user, "id", None), field="admin_user_id"
        )
        if _safe_text(
            getattr(admin_context, "user_id", None),
            field="admin_context_user_id",
        ) != user_id:
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_admin_context_mismatch"
            )
        prepared = await self.async_prepare_ai_management_enable()
        if prepared["status"] == "reconciliation_blocked":
            await self.async_reconcile_ai_management_block(
                user=user,
                admin_context=admin_context,
                blocked=prepared,
            )
            prepared = await self.async_prepare_ai_management_enable()
            if prepared["status"] != "ready":
                raise MaintenanceDelegationPublisherError(
                    "maintenance_host_change_reconciliation_blocked"
                )
        if prepared["status"] == "reconciliation_required":
            recovered = await self.async_finalize_ai_management_enable(
                permit=prepared,
                projections=prepared["projections"],
                observed_before_state=prepared["projections"]["before_state"],
                observed_after_state=_ai_management_state(self._entry),
                reason={"reason": "host_change_recovery_readback"},
            )
            if recovered["effect_status"] == "verified_success":
                return dict(recovered, status="reconciled_success")
            if recovered["effect_status"] == "effect_unknown":
                raise MaintenanceDelegationPublisherError(
                    "maintenance_host_change_reconciliation_required"
                )
        current = _ai_management_state(self._entry)
        coordinator_enabled = getattr(
            self._hass.data.get("smart_agent", {}).get(
                getattr(self._entry, "entry_id", "")
            ),
            "_enabled",
            None,
        )
        if current["value"] is True:
            if coordinator_enabled is not True:
                raise MaintenanceDelegationPublisherError(
                    "maintenance_host_change_runtime_state_mismatch"
                )
            return {
                "ok": True,
                "status": "already_enabled",
                "effect_status": "verified_success",
                "change_applied": False,
                "device_effect_authority": "none",
            }
        if coordinator_enabled is not False:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_runtime_state_mismatch"
            )
        projections = _build_ai_management_enable_projections(self._entry)
        reservation = await self.async_reserve(
            user=user,
            admin_context=admin_context,
            execution_class="admin_maintenance",
            operation_id=(
                "admin_maintenance.ha_runtime.ai_enabled.enable.v0.1"
            ),
            controlled_device_effect_required=False,
            **projections,
        )
        permit = await self.async_permit_ai_management_enable(
            reservation, **projections
        )
        if _now(self._clock) >= _utc(permit["expires_at"], field="permit_expiry"):
            receipt = await self.async_finalize_ai_management_enable(
                permit=permit,
                projections=projections,
                observed_before_state=projections["before_state"],
                observed_after_state=_ai_management_state(self._entry),
                reason={"reason": "host_change_permit_expired_before_apply"},
            )
            raise MaintenanceDelegationPublisherError(
                f"maintenance_host_change_not_applied:{receipt['effect_status']}"
            )
        next_options = dict(getattr(self._entry, "options", {}) or {})
        next_options[CONF_AI_ENABLED] = True
        apply_error: Exception | None = None
        coordinator = self._hass.data.get("smart_agent", {}).get(
            getattr(self._entry, "entry_id", "")
        )
        if coordinator is None or getattr(coordinator, "_enabled", None) is not False:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_runtime_state_mismatch"
            )
        coordinator._skip_next_reload = True
        try:
            self._hass.config_entries.async_update_entry(
                self._entry, options=next_options
            )
        except Exception as exc:  # HA mutation fact is settled by exact readback.
            apply_error = exc
        observed_after = _ai_management_state(self._entry)
        if observed_after == projections["before_state"]:
            coordinator._skip_next_reload = False
        receipt = await self.async_finalize_ai_management_enable(
            permit=permit,
            projections=projections,
            observed_before_state=projections["before_state"],
            observed_after_state=observed_after,
            reason={
                "reason": (
                    "host_change_apply_returned"
                    if apply_error is None
                    else "host_change_apply_raised"
                )
            },
        )
        if receipt["effect_status"] != "verified_success":
            raise MaintenanceDelegationPublisherError(
                f"maintenance_host_change_not_applied:{receipt['effect_status']}"
            ) from apply_error
        return receipt

    async def async_reconcile_ai_management_startup(self) -> dict[str, Any]:
        """Settle an already-authorized host mutation without reapplying it."""

        if not self.enabled:
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_ingress_disabled"
            )
        current = _ai_management_state(self._entry)
        prepared = await self.async_prepare_ai_management_enable()
        if prepared["status"] == "reconciliation_blocked":
            return prepared
        if prepared["status"] == "ready":
            return {
                "ok": True,
                "status": "stable_no_pending_change",
                "effect_status": "verified_success",
                "change_applied": False,
                "current_value": current["value"],
                "device_effect_authority": "none",
            }
        receipt = await self.async_finalize_ai_management_enable(
            permit=prepared,
            projections=prepared["projections"],
            observed_before_state=prepared["projections"]["before_state"],
            observed_after_state=current,
            reason={"reason": "host_change_startup_recovery_readback"},
        )
        return dict(receipt, status="startup_reconciled")

    async def async_reconcile_ai_management_enable(
        self,
        reservation: MaintenancePreDispatchReservation,
        *,
        blocked_receipt_id: str,
        blocked_receipt_digest: str,
        observed_state: Mapping[str, Any],
        reason: Mapping[str, Any],
    ) -> dict[str, Any]:
        if type(reservation) is not MaintenancePreDispatchReservation:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_reconciliation_reservation_invalid"
            )
        if type(observed_state) is not dict or type(reason) is not dict:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_reconciliation_request_invalid"
            )
        receipt_id = _prefixed_hex_id(
            blocked_receipt_id, prefix="mchr_", field="blocked_receipt_id"
        )
        receipt_digest = _digest_text(
            blocked_receipt_digest, field="blocked_receipt_digest"
        )
        current = _ai_management_state(self._entry)
        if current != dict(observed_state) or current["value"] is not False:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_reconciliation_safe_state_required"
            )
        now = _now(self._clock)
        request = sign_maintenance_ai_management_enable_reconcile_request(
            attempt_id=reservation.attempt_id,
            attempt_digest=reservation.attempt_digest,
            blocked_receipt_id=receipt_id,
            blocked_receipt_digest=receipt_digest,
            observed_state=current,
            reason_digest=_digest(reason),
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_RECONCILE_AI_MANAGEMENT_ENABLE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(
                    self._config.ingress_secret
                ): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="reconcile_ai_management_enable",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("status")
            not in {"reconciled_safe_disabled", "already_reconciled"}
            or result.get("blocked_receipt_id") != receipt_id
            or result.get("blocked_receipt_digest") != receipt_digest
            or result.get("reconciliation_attempt_id") != reservation.attempt_id
            or result.get("reconciliation_attempt_digest")
            != reservation.attempt_digest
            or result.get("operation_id")
            != "admin_maintenance.ha_runtime.ai_enabled.reconcile_clear.v0.1"
            or result.get("observed_state_digest") != _digest(current)
            or result.get("resolution") != "verified_safe_disabled"
            or result.get("safe_state_verified") is not True
            or result.get("host_change_permitted") is not False
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not False
            or result.get("execution_permitted") is not False
            or result.get("change_applied") is not False
            or result.get("reconciliation_required") is not False
            or result.get("rollback_verified") is not False
            or result.get("controlled_device_effect_required") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_reconciliation_response_invalid"
            )
        _prefixed_hex_id(
            result.get("reconciliation_id"),
            prefix="mchx_",
            field="reconciliation_id",
        )
        _digest_text(
            result.get("reconciliation_digest"),
            field="reconciliation_digest",
        )
        return result

    async def async_permit_ai_management_enable(
        self,
        reservation: MaintenancePreDispatchReservation,
        *,
        resource_ref: Mapping[str, Any],
        payload: Mapping[str, Any],
        before_state: Mapping[str, Any],
        expected_after_state: Mapping[str, Any],
        backup_ref: Mapping[str, Any],
        rollback_plan: Mapping[str, Any],
    ) -> dict[str, Any]:
        if type(reservation) is not MaintenancePreDispatchReservation:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_reservation_invalid"
            )
        entry_id = _safe_text(
            getattr(self._entry, "entry_id", None), field="bridge_entry_id"
        )
        projections = _validated_ai_management_enable_projections(
            {
                "resource_ref": resource_ref,
                "payload": payload,
                "before_state": before_state,
                "expected_after_state": expected_after_state,
                "backup_ref": backup_ref,
                "rollback_plan": rollback_plan,
            },
            bridge_config_entry_id=entry_id,
        )
        now = _now(self._clock)
        request = sign_maintenance_ai_management_enable_permit_request(
            attempt_id=reservation.attempt_id,
            attempt_digest=reservation.attempt_digest,
            secret=self._config.ingress_secret,
            requested_at=now,
            **projections,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_PERMIT_AI_MANAGEMENT_ENABLE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(
                    self._config.ingress_secret
                ): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="permit_ai_management_enable",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("operation_id")
            != "admin_maintenance.ha_runtime.ai_enabled.enable.v0.1"
            or result.get("attempt_id") != reservation.attempt_id
            or result.get("attempt_digest") != reservation.attempt_digest
            or result.get("projection_digest") != _digest(projections)
            or result.get("host_change_permitted") is not True
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not False
            or result.get("execution_permitted") is not False
            or result.get("change_applied") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_permit_response_invalid"
            )
        _prefixed_hex_id(
            result.get("permit_id"), prefix="mchp_", field="permit_id"
        )
        _digest_text(result.get("permit_digest"), field="permit_digest")
        _utc(result.get("permit_started_at"), field="permit_started_at")
        _utc(result.get("expires_at"), field="permit_expiry")
        return result

    async def async_finalize_ai_management_enable(
        self,
        *,
        permit: Mapping[str, Any],
        projections: Mapping[str, Any],
        observed_before_state: Mapping[str, Any],
        observed_after_state: Mapping[str, Any],
        reason: Mapping[str, Any],
    ) -> dict[str, Any]:
        if type(permit) is not dict or type(reason) is not dict:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_finalize_invalid"
            )
        entry_id = _safe_text(
            getattr(self._entry, "entry_id", None), field="bridge_entry_id"
        )
        _validated_ai_management_enable_projections(
            projections, bridge_config_entry_id=entry_id
        )
        now = _now(self._clock)
        request = sign_maintenance_ai_management_enable_finalize_request(
            permit_id=permit["permit_id"],
            permit_digest=permit["permit_digest"],
            attempt_id=permit["attempt_id"],
            attempt_digest=permit["attempt_digest"],
            observed_before_state=observed_before_state,
            observed_after_state=observed_after_state,
            reason_digest=_digest(reason),
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_FINALIZE_AI_MANAGEMENT_ENABLE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(
                    self._config.ingress_secret
                ): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="finalize_ai_management_enable",
            evaluated_at=_now(self._clock),
        )
        effect = result.get("effect_status")
        expected_matrix = {
            "verified_success": (True, True, False),
            "verified_failed": (True, False, False),
            "effect_unknown": (False, False, True),
        }
        if effect not in expected_matrix:
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_receipt_invalid"
            )
        after_verified, change_applied, reconciliation = expected_matrix[effect]
        if (
            result.get("ok") is not True
            or result.get("permit_id") != permit["permit_id"]
            or result.get("permit_digest") != permit["permit_digest"]
            or result.get("attempt_id") != permit["attempt_id"]
            or result.get("attempt_digest") != permit["attempt_digest"]
            or result.get("host_change_permitted") is not False
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not False
            or result.get("execution_permitted") is not False
            or result.get("before_state_verified") is not True
            or result.get("after_state_verified") is not after_verified
            or result.get("change_applied") is not change_applied
            or result.get("reconciliation_required") is not reconciliation
            or result.get("rollback_verified") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_host_change_receipt_invalid"
            )
        return result

    async def async_reserve(
        self,
        *,
        user: Any,
        admin_context: Any,
        execution_class: str,
        operation_id: str,
        resource_ref: Mapping[str, Any],
        payload: Mapping[str, Any],
        before_state: Mapping[str, Any],
        expected_after_state: Mapping[str, Any],
        backup_ref: Mapping[str, Any],
        rollback_plan: Mapping[str, Any],
        controlled_device_effect_required: bool,
    ) -> MaintenancePreDispatchReservation:
        if not self.enabled or not is_current_human_admin(user):
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_current_admin_required"
            )
        user_id = _safe_text(getattr(user, "id", None), field="admin_user_id")
        context_user_id = _safe_text(
            getattr(admin_context, "user_id", None),
            field="admin_context_user_id",
        )
        if context_user_id != user_id:
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_admin_context_mismatch"
            )
        session_id = _safe_text(
            getattr(admin_context, "id", None), field="admin_session_id"
        )
        exact_objects = (
            resource_ref,
            payload,
            before_state,
            expected_after_state,
            backup_ref,
            rollback_plan,
        )
        if any(type(value) is not dict for value in exact_objects):
            raise MaintenanceDelegationPublisherError(
                "maintenance_delegation_change_projection_invalid"
            )
        now = _now(self._clock)
        installation = await self._installation_digest()
        bridge_entry = _safe_text(
            getattr(self._entry, "entry_id", None), field="bridge_entry_id"
        )
        delegation_jti = f"mdeleg_{secrets.token_hex(16)}"
        attestation = _sign_delegation(
            delegation_jti=delegation_jti,
            secret=self._config.attestation_secret,
            ha_installation_digest_value=installation,
            bridge_config_entry_id=bridge_entry,
            admin_principal_digest=_digest(
                {
                    "user_id": user_id,
                    "is_active": True,
                    "is_admin": True,
                    "is_system_generated": False,
                }
            ),
            admin_session_digest=_digest(
                {"user_id": user_id, "admin_session_id": session_id}
            ),
            execution_class=execution_class,
            operation_id=operation_id,
            resource_ref_digest=_digest(resource_ref),
            payload_digest=_digest(payload),
            before_state_digest=_digest(before_state),
            expected_after_state_digest=_digest(expected_after_state),
            backup_ref_digest=_digest(backup_ref),
            rollback_plan_digest=_digest(rollback_plan),
            controlled_device_effect_required=controlled_device_effect_required,
            issued_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        request = sign_maintenance_reserve_request(
            attestation,
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_RESERVE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(self._config.ingress_secret): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="reserve",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("delegation_jti") != delegation_jti
            or result.get("state") != "reserved_pre_dispatch"
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not False
            or result.get("execution_permitted") is not False
            or result.get("change_applied") is not False
            or result.get("rollback_verified") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_reservation_response_invalid"
            )
        return MaintenancePreDispatchReservation(
            {
                "attempt_id": result["attempt_id"],
                "attempt_digest": result["attempt_digest"],
                "delegation_jti": result["delegation_jti"],
                "state": result["state"],
                "dispatch_permitted": False,
                "execution_eligible": False,
                "execution_permitted": False,
                "change_applied": False,
                "rollback_verified": False,
                "device_effect_authority": "none",
            },
            seal=_RESERVATION_SEAL,
        )

    async def async_finalize_pre_dispatch(
        self,
        reservation: MaintenancePreDispatchReservation,
        *,
        outcome: str,
        reason: Mapping[str, Any],
    ) -> dict[str, Any]:
        if (
            not self.enabled
            or type(reservation) is not MaintenancePreDispatchReservation
            or reservation.dispatch_permitted is not False
            or type(reason) is not dict
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_finalize_invalid"
            )
        now = _now(self._clock)
        request = sign_maintenance_finalize_request(
            attempt_id=reservation.attempt_id,
            attempt_digest=reservation.attempt_digest,
            outcome=outcome,
            reason_digest=_digest(reason),
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_FINALIZE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(self._config.ingress_secret): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="finalize",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("attempt_id") != reservation.attempt_id
            or result.get("attempt_digest") != reservation.attempt_digest
            or result.get("effect_status") != "not_dispatched"
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not False
            or result.get("execution_permitted") is not False
            or result.get("change_applied") is not False
            or result.get("rollback_verified") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_finalize_response_invalid"
            )
        return result

    async def async_apply_learning_mode_disable(
        self,
        reservation: MaintenancePreDispatchReservation,
        *,
        resource_ref: Mapping[str, Any],
        payload: Mapping[str, Any],
        before_state: Mapping[str, Any],
        expected_after_state: Mapping[str, Any],
        backup_ref: Mapping[str, Any],
        rollback_plan: Mapping[str, Any],
    ) -> dict[str, Any]:
        exact_objects = (
            resource_ref,
            payload,
            before_state,
            expected_after_state,
            backup_ref,
            rollback_plan,
        )
        if (
            not self.enabled
            or type(reservation) is not MaintenancePreDispatchReservation
            or reservation.dispatch_permitted is not False
            or any(type(value) is not dict for value in exact_objects)
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_apply_invalid"
            )
        now = _now(self._clock)
        request = sign_maintenance_learning_mode_disable_request(
            attempt_id=reservation.attempt_id,
            attempt_digest=reservation.attempt_digest,
            resource_ref=resource_ref,
            payload=payload,
            before_state=before_state,
            expected_after_state=expected_after_state,
            backup_ref=backup_ref,
            rollback_plan=rollback_plan,
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=MAINTENANCE_APPLY_LEARNING_MODE_DISABLE_PATH,
            payload=request,
        )
        result = verify_maintenance_change_ingress_response(
            response,
            keyring={
                maintenance_change_ingress_key_id(
                    self._config.ingress_secret
                ): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="apply_learning_mode_disable",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("attempt_id") != reservation.attempt_id
            or result.get("attempt_digest") != reservation.attempt_digest
            or result.get("operation_id")
            != "admin_maintenance.system_settings.learning_mode.disable.v0.1"
            or result.get("effect_status") != "verified_success"
            or result.get("dispatch_permitted") is not False
            or result.get("execution_eligible") is not True
            or result.get("execution_permitted") is not True
            or result.get("before_state_verified") is not True
            or result.get("after_state_verified") is not True
            or result.get("change_applied") is not True
            or result.get("rollback_verified") is not False
            or result.get("controlled_device_effect_required") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise MaintenanceDelegationPublisherError(
                "maintenance_change_apply_response_invalid"
            )
        return result


__all__: list[str] = []
