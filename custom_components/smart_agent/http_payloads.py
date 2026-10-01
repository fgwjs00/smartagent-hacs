"""Read HA HTTP bodies without confusing transport faults with invalid input."""
from __future__ import annotations

import codecs
import json
import logging
import secrets
from typing import Any

from aiohttp import web

_LOGGER = logging.getLogger(__name__)


async def read_json_payload(request: Any, *, operation: str) -> Any:
    try:
        return await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, web.HTTPException):
        # Callers own their existing malformed-input response; HTTP limits keep
        # the framework status. Neither can become a successful empty body.
        raise
    except Exception as exc:
        if isinstance(exc, LookupError):
            charset = getattr(request, "charset", None)
            if isinstance(charset, str):
                try:
                    codecs.lookup(charset)
                except LookupError:
                    payload = {"ok": False, "error": "invalid_charset", "operation": operation}
                    raise web.HTTPBadRequest(text=json.dumps(payload), content_type="application/json") from exc
        error_id = secrets.token_hex(12)
        _LOGGER.error("operation=%s error_id=%s cause_type=%s", operation, error_id, type(exc).__name__)
        payload = {"ok": False, "error": "request_body_unavailable",
                   "error_type": "dependency_unavailable", "retryable": False,
                   "operation": operation, "error_id": error_id}
        raise web.HTTPServiceUnavailable(text=json.dumps(payload), content_type="application/json") from exc
