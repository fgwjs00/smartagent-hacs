"""Narrow HA Area Registry merge view implementation.

The add-on owns canonical SmartAgent space migration.  This mixin is limited to
moving direct HA registry assignments and returning its verified receipt.
"""
from __future__ import annotations

from aiohttp import web

from .ha_adapter import async_merge_ha_area


def _error_payload(error: str, error_type: str, *, scope: str) -> dict[str, object]:
    return {
        "ok": False,
        "error": error,
        "error_type": error_type,
        "retryable": False,
        "scope": scope,
    }


class RoomMergeViewMixin:
    """Keep the verified HA Area migration outside the integration entrypoint."""

    async def post(self, request: web.Request, room_id: str) -> web.Response:
        user = request.get("hass_user")
        if user is not None and not user.is_admin:
            return self.json(_error_payload("forbidden_admin_required", "auth_failed", scope="rooms_merge"), status_code=403)
        try:
            body = await request.json()
        except Exception:
            return self.json(_error_payload("invalid_json", "bad_request", scope="rooms_merge"), status_code=400)
        if not isinstance(body, dict):
            return self.json(_error_payload("invalid_body", "bad_request", scope="rooms_merge"), status_code=400)
        target_area_id = str(body.get("target_area_id") or "").strip()
        result = await async_merge_ha_area(request.app["hass"], room_id, target_area_id)
        if not bool(result.get("ok")):
            error_type = str(result.get("error_type") or "internal_error")
            status_code = 400 if error_type == "bad_request" else 404 if error_type == "not_found" else 500
            return self.json(dict(result, scope="rooms_merge"), status_code=status_code)
        return self.json(result, status_code=200)
