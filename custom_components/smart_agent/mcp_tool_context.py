"""Explicit MCP request context and shared protocol/transaction projections."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import logging

_LOGGER = logging.getLogger("custom_components.smart_agent.mcp_tools")


@dataclass(frozen=True, slots=True)
class McpToolContext:
    hass: Any
    coordinator: Any
    arguments: dict
    user: Any = None


def mcp_text(text: str, *, is_error: bool = False) -> dict:
    result = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    return result


def _mcp_args(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _mcp_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _mcp_bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


async def _get_addon_transactions(
    coordinator: Any, *, limit: int | None = None
) -> list[dict[str, Any]] | None:
    client = getattr(coordinator, "_addon_client", None)
    if client is None or not hasattr(client, "get_transactions"):
        return None
    try:
        payload = await client.get_transactions()
    except Exception as exc:
        _LOGGER.debug("[MCP Tools] add-on transactions fetch failed: %s", exc)
        return None
    rows: Any
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("transactions") or payload.get("items") or payload.get("data")
    else:
        rows = None
    if not isinstance(rows, list):
        return None
    normalized = [dict(row) for row in rows if isinstance(row, dict)]
    if limit is not None:
        normalized = normalized[-limit:]
    return normalized
