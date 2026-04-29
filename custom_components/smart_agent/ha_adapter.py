"""HA adapter boundary for add-on command envelopes.

This module is allowed to touch Home Assistant runtime objects. Business
decision modules should stay in the add-on Core and call this boundary through a
plain command envelope.
"""
from __future__ import annotations

import time
from typing import Any


def _json_error(
    request_id: str,
    error: str,
    *,
    error_type: str = "execution_error",
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "ok": False,
        "results": [],
        "error": error,
        "error_type": error_type,
        "retryable": retryable,
    }


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
    return {
        "entity_id": entity_id,
        "domain": domain,
        "service": service,
        "data": data if isinstance(data, dict) else {},
    }


async def async_execute_command_envelope(hass: Any, envelope: dict[str, Any]) -> dict[str, Any]:
    """Execute a CommandEnvelope through HA services and return ExecutionResult."""
    request_id = str((envelope or {}).get("request_id") or "")
    if not request_id:
        request_id = "unknown"
    commands_raw = (envelope or {}).get("commands")
    if not isinstance(commands_raw, list) or not commands_raw:
        return _json_error(request_id, "commands_required", error_type="bad_request")

    results: list[dict[str, Any]] = []
    for raw in commands_raw:
        started = time.monotonic()
        try:
            command = _normalize_command(raw)
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
            })
            continue

        try:
            await hass.services.async_call(
                command["domain"],
                command["service"],
                {"entity_id": command["entity_id"], **command["data"]},
                blocking=True,
            )
            results.append({
                **command,
                "ok": True,
                "error": "",
                "error_type": "",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
            })
        except Exception as exc:
            results.append({
                **command,
                "ok": False,
                "error": str(exc) or exc.__class__.__name__,
                "error_type": "ha_service_error",
                "retryable": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
            })

    ok = bool(results) and all(bool(item.get("ok")) for item in results)
    first_error = next((item for item in results if not item.get("ok")), None)
    return {
        "request_id": request_id,
        "ok": ok,
        "results": results,
        "error": str(first_error.get("error", "") if first_error else ""),
        "error_type": str(first_error.get("error_type", "") if first_error else ""),
        "retryable": bool(first_error.get("retryable", False) if first_error else False),
    }
