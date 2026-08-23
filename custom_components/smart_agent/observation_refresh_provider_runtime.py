"""Default-off HA persistence assembly for observation-refresh Provider facts.

This module binds the pure replay ledger to Home Assistant ``Store`` shape.  It
does not register an HTTP view, call an HA service, or provide a production
adapter.  The builtin adapter registry is intentionally empty.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Any, Callable, Mapping

from .observation_refresh_provider_request_attestation import (
    BUILTIN_OBSERVATION_REFRESH_HOST_PROVIDER_ADAPTER_REGISTRY,
    ObservationRefreshHostJsonReplayLedger,
    ObservationRefreshHostProviderAdapterRegistry,
    ObservationRefreshHostProviderRuntime,
    ObservationRefreshHostProviderRuntimeConfig,
    ObservationRefreshProviderRequestVerificationError,
    provider_request_attestation_key_id,
)


_STORE_VERSION = 1
_STORE_KEY_PREFIX = "smart_agent.observation_refresh_provider_replay"
_SAFE_ENTRY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _detached_json(value: Any) -> Any:
    try:
        return json.loads(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_store_projection_invalid"
        ) from exc


class ObservationRefreshHomeAssistantReplayStorage:
    """Strict adapter around one Home Assistant Store instance."""

    def __init__(self, store: Any) -> None:
        if not callable(getattr(store, "async_load", None)) or not callable(
            getattr(store, "async_save", None)
        ):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_store_invalid"
            )
        self._store = store

    async def async_load(self) -> object | None:
        value = await self._store.async_load()
        if value is None:
            return None
        detached = _detached_json(value)
        if type(detached) is not dict:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_store_document_invalid"
            )
        return detached

    async def async_save(self, value: Mapping[str, Any]) -> None:
        if type(value) is not dict:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_store_document_invalid"
            )
        detached = _detached_json(value)
        if type(detached) is not dict:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_store_document_invalid"
            )
        await self._store.async_save(detached)


@dataclass(frozen=True, slots=True)
class ObservationRefreshHostProviderRuntimeInstallation:
    enabled: bool
    status: str
    runtime: ObservationRefreshHostProviderRuntime | None
    storage: ObservationRefreshHomeAssistantReplayStorage | None
    provider_io_available: bool
    execution_eligible: bool
    device_effect_authority: str

    def __post_init__(self) -> None:
        if (
            type(self.enabled) is not bool
            or self.status
            not in {"disabled", "installed_no_builtin_adapter", "installed"}
            or type(self.provider_io_available) is not bool
            or self.execution_eligible is not False
            or self.device_effect_authority != "none"
        ):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_runtime_installation_invalid"
            )
        if not self.enabled and (self.runtime is not None or self.storage is not None):
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_runtime_installation_invalid"
            )


def install_observation_refresh_host_provider_runtime(
    *,
    hass: Any,
    entry_id: str,
    enabled: bool,
    request_attestation_secret: str = "",
    previous_request_attestation_secret: str = "",
    replay_integrity_secret: str = "",
    clock: Callable[[], datetime],
    adapter_registry: ObservationRefreshHostProviderAdapterRegistry | None = None,
    store_factory: Callable[[Any, int, str], Any] | None = None,
) -> ObservationRefreshHostProviderRuntimeInstallation:
    """Install one entry-scoped replay runtime without registering a route."""

    if type(enabled) is not bool or not callable(clock):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_runtime_configuration_invalid"
        )
    if not enabled:
        return ObservationRefreshHostProviderRuntimeInstallation(
            enabled=False,
            status="disabled",
            runtime=None,
            storage=None,
            provider_io_available=False,
            execution_eligible=False,
            device_effect_authority="none",
        )
    if (
        type(entry_id) is not str
        or not _SAFE_ENTRY_ID_RE.fullmatch(entry_id)
        or type(request_attestation_secret) is not str
        or type(previous_request_attestation_secret) is not str
        or type(replay_integrity_secret) is not str
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_runtime_configuration_invalid"
        )
    secrets = tuple(
        value
        for value in (
            request_attestation_secret,
            previous_request_attestation_secret,
            replay_integrity_secret,
        )
        if value
    )
    if (
        not request_attestation_secret
        or not replay_integrity_secret
        or any(len(value.encode("utf-8")) < 32 for value in secrets)
        or any(value != value.strip() for value in secrets)
        or len(set(secrets)) != len(secrets)
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_runtime_secret_invalid"
        )
    if adapter_registry is None:
        adapter_registry = BUILTIN_OBSERVATION_REFRESH_HOST_PROVIDER_ADAPTER_REGISTRY
    if type(adapter_registry) is not ObservationRefreshHostProviderAdapterRegistry:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_runtime_registry_invalid"
        )
    if store_factory is None:
        from homeassistant.helpers.storage import Store

        store_factory = Store
    if not callable(store_factory):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_store_factory_invalid"
        )
    store = store_factory(hass, _STORE_VERSION, f"{_STORE_KEY_PREFIX}.{entry_id}")
    storage = ObservationRefreshHomeAssistantReplayStorage(store)
    ledger = ObservationRefreshHostJsonReplayLedger(
        storage=storage,
        integrity_secret=replay_integrity_secret,
        clock=clock,
    )
    keyring = {
        provider_request_attestation_key_id(secret): secret
        for secret in (
            request_attestation_secret,
            previous_request_attestation_secret,
        )
        if secret
    }
    runtime = ObservationRefreshHostProviderRuntime(
        keyring=keyring,
        adapter_registry=adapter_registry,
        replay_ledger=ledger,
        clock=clock,
        config=ObservationRefreshHostProviderRuntimeConfig(enabled=True),
    )
    provider_io_available = bool(adapter_registry.adapters)
    return ObservationRefreshHostProviderRuntimeInstallation(
        enabled=True,
        status=("installed" if provider_io_available else "installed_no_builtin_adapter"),
        runtime=runtime,
        storage=storage,
        provider_io_available=provider_io_available,
        execution_eligible=False,
        device_effect_authority="none",
    )


__all__: list[str] = []
