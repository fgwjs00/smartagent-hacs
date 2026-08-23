"""Private HA view assembly for signed observation-refresh Provider requests.

The endpoint is default-off and accepts only an authenticated Home Assistant
request that also arrives from the add-on proxy, carries the dedicated header,
and verifies under the observation-refresh request keyring.  It never calls an
HA service itself; the builtin Provider adapter registry is intentionally empty.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any, Callable, Mapping

from .observation_refresh_provider_request_attestation import (
    ObservationRefreshHostProviderRuntime,
    ObservationRefreshProviderRequestVerificationError,
    provider_request_attestation_key_id,
    sign_observation_refresh_provider_response,
    verify_observation_refresh_provider_request,
)
from .observation_refresh_provider_runtime import (
    ObservationRefreshHostProviderRuntimeInstallation,
    install_observation_refresh_host_provider_runtime,
)


OBSERVATION_REFRESH_PROVIDER_PATH = (
    "/api/v1/internal/smart-agent/observation-refresh/provider"
)
OBSERVATION_REFRESH_PROVIDER_HEADER = "X-SA-Internal"
OBSERVATION_REFRESH_PROVIDER_HEADER_VALUE = "observation-refresh-provider-v0.1"
OBSERVATION_REFRESH_PROVIDER_MAX_BODY_BYTES = 1024 * 1024
_STATE_KEY = "_smartagent_observation_refresh_provider_view"


@dataclass(frozen=True, slots=True)
class _ProviderBinding:
    entry_id: str
    installation: ObservationRefreshHostProviderRuntimeInstallation
    request_keyring: Mapping[str, str]
    response_secret: str
    clock: Callable[[], datetime]


@dataclass(slots=True)
class _ProviderViewState:
    bindings: dict[str, _ProviderBinding] = field(default_factory=dict)
    view_registered: bool = False


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > OBSERVATION_REFRESH_PROVIDER_MAX_BODY_BYTES:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_http_body_invalid"
        )

    def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if type(key) is not str or key in result:
                raise ObservationRefreshProviderRequestVerificationError(
                    "refresh_provider_http_body_invalid"
                )
            result[key] = value
        return result

    def _reject_constant(_value: str) -> None:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_http_body_invalid"
        )

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        ObservationRefreshProviderRequestVerificationError,
    ) as exc:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_http_body_invalid"
        ) from exc
    if type(value) is not dict:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_http_body_invalid"
        )
    return value


def _error_payload(error: str, *, retryable: bool) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        "retryable": retryable,
        "fresh_evidence_verified": False,
        "execution_eligible": False,
        "device_effect_authority": "none",
    }


def setup_observation_refresh_provider_view(
    *,
    hass: Any,
    entry_id: str,
    enabled: bool,
    request_attestation_secret: str,
    previous_request_attestation_secret: str,
    replay_integrity_secret: str,
    clock: Callable[[], datetime],
    trusted_peer: Callable[[Any], bool],
    register_view: Callable[[], None],
    adapter_registry: Any = None,
    store_factory: Callable[[Any, int, str], Any] | None = None,
) -> Callable[[], None]:
    """Install one entry-scoped runtime and register the private view once."""

    if (
        type(enabled) is not bool
        or not callable(trusted_peer)
        or not callable(register_view)
    ):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_view_configuration_invalid"
        )
    if not enabled:
        state = hass.data.get(_STATE_KEY)
        if state is not None and type(state) is not _ProviderViewState:
            raise ObservationRefreshProviderRequestVerificationError(
                "refresh_provider_view_state_invalid"
            )
        if type(state) is _ProviderViewState:
            state.bindings.pop(str(entry_id), None)
        return lambda: None
    state = hass.data.get(_STATE_KEY)
    if state is None:
        state = _ProviderViewState()
        hass.data[_STATE_KEY] = state
    if type(state) is not _ProviderViewState:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_view_state_invalid"
        )
    if state.bindings and entry_id not in state.bindings:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_view_multiple_entries_forbidden"
        )

    install_kwargs: dict[str, Any] = {
        "hass": hass,
        "entry_id": entry_id,
        "enabled": True,
        "request_attestation_secret": request_attestation_secret,
        "previous_request_attestation_secret": previous_request_attestation_secret,
        "replay_integrity_secret": replay_integrity_secret,
        "clock": clock,
        "store_factory": store_factory,
    }
    if adapter_registry is not None:
        install_kwargs["adapter_registry"] = adapter_registry
    installation = install_observation_refresh_host_provider_runtime(**install_kwargs)
    if installation.runtime is None:
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_view_runtime_missing"
        )
    keyring = {
        provider_request_attestation_key_id(secret): secret
        for secret in (
            request_attestation_secret,
            previous_request_attestation_secret,
        )
        if secret
    }
    state.bindings[entry_id] = _ProviderBinding(
        entry_id=entry_id,
        installation=installation,
        request_keyring=keyring,
        response_secret=request_attestation_secret,
        clock=clock,
    )
    if not state.view_registered:
        register_view()
        state.view_registered = True

    def _cleanup() -> None:
        state.bindings.pop(entry_id, None)

    return _cleanup


async def handle_observation_refresh_provider_request(
    request: Any,
    *,
    trusted_peer: Callable[[Any], bool],
) -> tuple[int, dict[str, Any]]:
    """Handle one request and return an HTTP status plus detached payload."""

    if (
        str(request.headers.get("X-SA-Proxy-From", "") or "").strip().lower()
        != "addon"
        or str(
            request.headers.get(OBSERVATION_REFRESH_PROVIDER_HEADER, "") or ""
        ).strip()
        != OBSERVATION_REFRESH_PROVIDER_HEADER_VALUE
        or not trusted_peer(request)
    ):
        return 403, _error_payload("refresh_provider_peer_forbidden", retryable=False)
    if str(request.headers.get("Content-Encoding", "") or "").strip().lower() not in {
        "",
        "identity",
    }:
        return 415, _error_payload("refresh_provider_encoding_forbidden", retryable=False)
    content_type = str(getattr(request, "content_type", "") or "").strip().lower()
    if content_type != "application/json":
        return 415, _error_payload("refresh_provider_content_type_invalid", retryable=False)
    content_length = getattr(request, "content_length", None)
    if type(content_length) is int and (
        content_length <= 0
        or content_length > OBSERVATION_REFRESH_PROVIDER_MAX_BODY_BYTES
    ):
        return 413, _error_payload("refresh_provider_body_too_large", retryable=False)
    try:
        content = getattr(request, "content", None)
        bounded_reader = getattr(content, "read", None)
        if callable(bounded_reader):
            raw = await bounded_reader(
                OBSERVATION_REFRESH_PROVIDER_MAX_BODY_BYTES + 1
            )
        else:
            raw = await request.read()
        if len(raw) > OBSERVATION_REFRESH_PROVIDER_MAX_BODY_BYTES:
            return 413, _error_payload(
                "refresh_provider_body_too_large",
                retryable=False,
            )
        envelope = _strict_json_object(raw)
    except Exception:
        return 400, _error_payload("refresh_provider_request_invalid", retryable=False)

    hass = request.app.get("hass")
    state = getattr(hass, "data", {}).get(_STATE_KEY) if hass is not None else None
    if type(state) is not _ProviderViewState or len(state.bindings) != 1:
        return 503, _error_payload("refresh_provider_runtime_unavailable", retryable=False)
    binding = next(iter(state.bindings.values()))
    runtime = binding.installation.runtime
    if type(runtime) is not ObservationRefreshHostProviderRuntime:
        return 503, _error_payload("refresh_provider_runtime_unavailable", retryable=False)
    try:
        verified = verify_observation_refresh_provider_request(
            envelope,
            keyring=dict(binding.request_keyring),
            evaluated_at=binding.clock(),
        )
    except ObservationRefreshProviderRequestVerificationError:
        return 403, _error_payload("refresh_provider_request_rejected", retryable=False)
    try:
        result = await runtime.handle(envelope)
        signed = sign_observation_refresh_provider_response(
            verified,
            result,
            secret=binding.response_secret,
            responded_at=binding.clock(),
        )
    except Exception:
        return 503, _error_payload("refresh_provider_runtime_uncertain", retryable=True)
    return 200, signed


def make_observation_refresh_provider_view(
    view_base: type,
    *,
    trusted_peer: Callable[[Any], bool],
) -> type:
    """Build the HA view without adding another public class to ``__init__``."""

    if type(view_base) is not type or not callable(trusted_peer):
        raise ObservationRefreshProviderRequestVerificationError(
            "refresh_provider_view_factory_invalid"
        )

    class ObservationRefreshProviderView(view_base):
        url = OBSERVATION_REFRESH_PROVIDER_PATH
        extra_urls: list[str] = []
        name = "api:smart_agent:internal:observation-refresh:provider"
        requires_auth = True

        async def post(self, request: Any) -> Any:
            status, payload = await handle_observation_refresh_provider_request(
                request,
                trusted_peer=trusted_peer,
            )
            return self.json(payload, status_code=status)

    return ObservationRefreshProviderView


__all__: list[str] = []
