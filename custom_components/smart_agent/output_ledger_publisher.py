"""HA-host client for the dedicated output-ledger authority ingress.

The publisher obtains a one-use non-device output permission before HA service
I/O and persists a conservative Receipt after the I/O boundary.  It never uses
the ordinary add-on bearer and never upgrades ACK to delivery/playback proof.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import aiohttp

from .const import (
    CONF_OUTPUT_LEDGER_ATTESTATION_SECRET,
    CONF_OUTPUT_LEDGER_INGRESS_ENABLED,
    CONF_OUTPUT_LEDGER_INGRESS_SECRET,
    CONF_OUTPUT_LEDGER_INGRESS_URL,
    DEFAULT_OUTPUT_LEDGER_INGRESS_URL,
)
from .output_contracts import (
    OutputAttempt,
    OutputReceipt,
    sign_output_attempt_attestation,
    sign_output_receipt_attestation,
)
from .output_ledger_ingress import (
    output_ledger_ingress_key_id,
    sign_output_ledger_claim_request,
    sign_output_ledger_finalize_request,
    verify_output_ledger_ingress_response,
)
from .refresh_registry_snapshot import ha_installation_digest


OUTPUT_LEDGER_CLAIM_PATH = "/api/v1/internal/output-ledger/claims"
OUTPUT_LEDGER_FINALIZE_PATH = "/api/v1/internal/output-ledger/finalizations"
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
_CLAIM_SEAL = object()


class OutputLedgerPublisherError(RuntimeError):
    """The persistent output authority handshake did not complete safely."""


def _secret(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) < 32
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise OutputLedgerPublisherError(f"{name}_invalid")
    return value


def _url(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise OutputLedgerPublisherError("output_ledger_ingress_url_invalid")
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
        raise OutputLedgerPublisherError("output_ledger_ingress_url_invalid")
    return value.rstrip("/")


def _now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise OutputLedgerPublisherError("output_ledger_publisher_clock_invalid")
    try:
        return value.astimezone(UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OutputLedgerPublisherError(
            "output_ledger_publisher_clock_invalid"
        ) from exc


@dataclass(frozen=True, slots=True)
class OutputLedgerPublisherConfig:
    enabled: bool
    ingress_url: str = DEFAULT_OUTPUT_LEDGER_INGRESS_URL
    ingress_secret: str = ""
    attestation_secret: str = ""

    @classmethod
    def from_entry(cls, entry: Any) -> "OutputLedgerPublisherConfig":
        values = {
            **dict(getattr(entry, "data", {}) or {}),
            **dict(getattr(entry, "options", {}) or {}),
        }
        return cls(
            enabled=values.get(CONF_OUTPUT_LEDGER_INGRESS_ENABLED, False),
            ingress_url=values.get(
                CONF_OUTPUT_LEDGER_INGRESS_URL,
                DEFAULT_OUTPUT_LEDGER_INGRESS_URL,
            ),
            ingress_secret=values.get(CONF_OUTPUT_LEDGER_INGRESS_SECRET, ""),
            attestation_secret=values.get(
                CONF_OUTPUT_LEDGER_ATTESTATION_SECRET, ""
            ),
        ).validated()

    def validated(self) -> "OutputLedgerPublisherConfig":
        if type(self.enabled) is not bool:
            raise OutputLedgerPublisherError(
                "output_ledger_ingress_enabled_invalid"
            )
        if not self.enabled:
            return self
        _url(self.ingress_url)
        ingress = _secret(
            self.ingress_secret, "output_ledger_ingress_secret"
        )
        attestation = _secret(
            self.attestation_secret, "output_ledger_attestation_secret"
        )
        if ingress == attestation:
            raise OutputLedgerPublisherError(
                "output_ledger_secret_reuse_forbidden"
            )
        return self


@dataclass(frozen=True, slots=True, init=False)
class OutputDispatchClaim:
    attempt_id: str
    attempt_digest: str
    dispatch_token: str
    attempt_attestation: Mapping[str, Any]
    dispatch_permitted: bool
    execution_permitted: bool
    device_effect_authority: str

    def __init__(self, projection: Mapping[str, Any], *, seal: object) -> None:
        if seal is not _CLAIM_SEAL or type(projection) is not dict:
            raise OutputLedgerPublisherError(
                "output_ledger_dispatch_claim_constructor_forbidden"
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
            raise OutputLedgerPublisherError(
                "output_ledger_ingress_response_invalid"
            ) from exc
        if response.status != 200 or type(body) is not dict:
            raise OutputLedgerPublisherError(
                "output_ledger_ingress_request_rejected"
            )
        return body


class OutputLedgerPublisher:
    """One coordinator-owned output authority client."""

    def __init__(
        self,
        hass: Any,
        entry: Any,
        *,
        config: OutputLedgerPublisherConfig | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        session_factory: Callable[[], aiohttp.ClientSession] | None = None,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._config = (config or OutputLedgerPublisherConfig.from_entry(entry)).validated()
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
            except (aiohttp.ClientError, asyncio.TimeoutError, OutputLedgerPublisherError) as exc:
                last_error = exc
        raise OutputLedgerPublisherError(
            "output_ledger_ingress_transport_unknown"
        ) from last_error

    async def async_claim(self, attempt: OutputAttempt) -> OutputDispatchClaim:
        if not self.enabled or type(attempt) is not OutputAttempt:
            raise OutputLedgerPublisherError("output_ledger_claim_invalid")
        now = _now(self._clock)
        installation = await self._installation_digest()
        bridge_entry = str(getattr(self._entry, "entry_id", "") or "").strip()
        if not bridge_entry:
            raise OutputLedgerPublisherError(
                "output_ledger_bridge_config_entry_id_invalid"
            )
        attestation = sign_output_attempt_attestation(
            attempt,
            secret=self._config.attestation_secret,
            ha_installation_digest=installation,
            bridge_config_entry_id=bridge_entry,
            issued_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        request = sign_output_ledger_claim_request(
            attestation,
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=OUTPUT_LEDGER_CLAIM_PATH,
            payload=request,
        )
        result = verify_output_ledger_ingress_response(
            response,
            keyring={
                output_ledger_ingress_key_id(self._config.ingress_secret): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="claim",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("attempt_id") != attempt.attempt_id
            or result.get("attempt_digest") != attempt.attempt_digest
            or result.get("dispatch_permitted") is not True
            or type(result.get("dispatch_token")) is not str
            or len(result["dispatch_token"]) != 64
            or result.get("execution_permitted") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise OutputLedgerPublisherError(
                "output_ledger_dispatch_not_permitted"
            )
        return OutputDispatchClaim(
            {
                "attempt_id": attempt.attempt_id,
                "attempt_digest": attempt.attempt_digest,
                "dispatch_token": result["dispatch_token"],
                "attempt_attestation": attestation,
                "dispatch_permitted": True,
                "execution_permitted": False,
                "device_effect_authority": "none",
            },
            seal=_CLAIM_SEAL,
        )

    async def async_finalize(
        self,
        receipt: OutputReceipt,
        claim: OutputDispatchClaim,
    ) -> dict[str, Any]:
        if (
            not self.enabled
            or type(receipt) is not OutputReceipt
            or type(claim) is not OutputDispatchClaim
            or claim.dispatch_permitted is not True
            or receipt.attempt_id != claim.attempt_id
            or receipt.attempt_digest != claim.attempt_digest
        ):
            raise OutputLedgerPublisherError("output_ledger_finalize_invalid")
        now = _now(self._clock)
        installation = await self._installation_digest()
        bridge_entry = str(getattr(self._entry, "entry_id", "") or "").strip()
        receipt_attestation = sign_output_receipt_attestation(
            receipt,
            parent_attestation=claim.attempt_attestation,
            secret=self._config.attestation_secret,
            ha_installation_digest=installation,
            bridge_config_entry_id=bridge_entry,
            issued_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        request = sign_output_ledger_finalize_request(
            attempt_id=claim.attempt_id,
            attempt_digest=claim.attempt_digest,
            dispatch_token=claim.dispatch_token,
            receipt_attestation=receipt_attestation,
            secret=self._config.ingress_secret,
            requested_at=now,
        )
        response = await self._post_with_safe_retry(
            path=OUTPUT_LEDGER_FINALIZE_PATH,
            payload=request,
        )
        result = verify_output_ledger_ingress_response(
            response,
            keyring={
                output_ledger_ingress_key_id(self._config.ingress_secret): self._config.ingress_secret
            },
            expected_request_id=request["request_id"],
            expected_kind="finalize",
            evaluated_at=_now(self._clock),
        )
        if (
            result.get("ok") is not True
            or result.get("status") != "terminal_persisted"
            or result.get("attempt_id") != receipt.attempt_id
            or result.get("source_receipt_id") != receipt.receipt_id
            or result.get("source_receipt_digest") != receipt.receipt_digest
            or result.get("delivered") is not False
            or result.get("read_by_user") is not False
            or result.get("played") is not False
            or result.get("execution_permitted") is not False
            or result.get("device_effect_authority") != "none"
        ):
            raise OutputLedgerPublisherError(
                "output_ledger_finalize_response_invalid"
            )
        return result


__all__: list[str] = []
