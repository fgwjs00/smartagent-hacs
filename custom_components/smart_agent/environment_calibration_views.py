"""Authenticated read and admin-only mutation views for environment calibration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.http import HomeAssistantView


def _admin_actor(request: Any) -> tuple[dict[str, Any] | None, Any | None]:
    user = request.get("hass_user")
    if user is None:
        return None, {"status": 401, "error": "unauthorized"}
    if not bool(getattr(user, "is_admin", False)):
        return None, {"status": 403, "error": "forbidden_admin_required"}
    return {
        "mode": "ha_user",
        "actor_id": str(getattr(user, "id", "") or ""),
        "actor_name": str(getattr(user, "name", "") or ""),
        "is_admin": True,
    }, None


def _addon_client(request: Any) -> Any | None:
    hass = request.app["hass"]
    for coordinator in (hass.data.get("smart_agent", {}) or {}).values():
        client = getattr(coordinator, "_addon_client", None)
        if client is not None:
            return client
    return None


class _EnvironmentCalibrationView(HomeAssistantView):
    requires_auth = True
    extra_urls: list[str] = []

    def _response(self, payload: Any, *, fallback_status: int = 502):
        if not isinstance(payload, dict):
            return self.json(
                {"ok": False, "error": "environment_calibration_addon_unavailable"},
                status_code=fallback_status,
            )
        body = dict(payload)
        status = int(body.pop("__status", 200) or 200)
        return self.json(body, status_code=status)

    def _authorize(self, request: Any):
        actor, error = _admin_actor(request)
        if error is not None:
            return None, self.json(
                {"ok": False, "error": error["error"], "error_type": "auth_failed", "retryable": False},
                status_code=error["status"],
            )
        client = _addon_client(request)
        if client is None:
            return None, self.json(
                {"ok": False, "error": "coordinator_unavailable", "retryable": True},
                status_code=503,
            )
        return (client, actor), None

    def _authorize_read(self, request: Any):
        if request.get("hass_user") is None:
            return None, self.json(
                {"ok": False, "error": "unauthorized", "error_type": "auth_failed", "retryable": False},
                status_code=401,
            )
        client = _addon_client(request)
        if client is None:
            return None, self.json(
                {"ok": False, "error": "coordinator_unavailable", "retryable": True},
                status_code=503,
            )
        return client, None

    async def _json_body(self, request: Any) -> dict[str, Any] | None:
        try:
            body = await request.json()
        except Exception:
            return None
        return body if isinstance(body, dict) else None


class SmartAgentEnvironmentCalibrationView(_EnvironmentCalibrationView):
    url = "/api/v1/devices/{entity_id}/environment-calibration"
    name = "api:smart_agent:v1:devices:environment_calibration"

    async def get(self, request: Any, entity_id: str):
        client, error = self._authorize_read(request)
        if error is not None:
            return error
        return self._response(await client.get_environment_calibration(str(entity_id or "")))


class SmartAgentEnvironmentCalibrationSamplesView(_EnvironmentCalibrationView):
    url = "/api/v1/devices/{entity_id}/environment-calibration/samples"
    name = "api:smart_agent:v1:devices:environment_calibration:samples"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._authorize(request)
        if error is not None:
            return error
        client, actor = authorized
        body = await self._json_body(request)
        if body is None or not isinstance(body.get("samples"), list):
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        return self._response(
            await client.post_environment_calibration_samples(
                str(entity_id or ""), list(body["samples"]), actor=actor
            )
        )


class SmartAgentEnvironmentCalibrationSuggestionsView(_EnvironmentCalibrationView):
    url = "/api/v1/devices/{entity_id}/environment-calibration/suggestions"
    name = "api:smart_agent:v1:devices:environment_calibration:suggestions"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._authorize(request)
        if error is not None:
            return error
        client, actor = authorized
        body = await self._json_body(request)
        if body is None:
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        return self._response(
            await client.create_environment_calibration_suggestion(
                str(entity_id or ""), body, actor=actor
            )
        )


class SmartAgentEnvironmentCalibrationApplyView(_EnvironmentCalibrationView):
    url = "/api/v1/devices/{entity_id}/environment-calibration/apply"
    name = "api:smart_agent:v1:devices:environment_calibration:apply"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._authorize(request)
        if error is not None:
            return error
        client, actor = authorized
        body = await self._json_body(request)
        if body is None:
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        try:
            expected_version = int(body.get("expected_version"))
        except (TypeError, ValueError):
            return self.json({"ok": False, "error": "invalid_expected_version"}, status_code=400)
        return self._response(
            await client.apply_environment_calibration(
                str(entity_id or ""),
                str(body.get("suggestion_id") or ""),
                expected_version,
                confirmation_token=str(body.get("confirmation_token") or ""),
                actor=actor,
            )
        )


class SmartAgentEnvironmentCalibrationRollbackView(_EnvironmentCalibrationView):
    url = "/api/v1/devices/{entity_id}/environment-calibration/rollback"
    name = "api:smart_agent:v1:devices:environment_calibration:rollback"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._authorize(request)
        if error is not None:
            return error
        client, actor = authorized
        body = await self._json_body(request)
        if body is None:
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        try:
            expected_version = int(body.get("expected_version"))
        except (TypeError, ValueError):
            return self.json({"ok": False, "error": "invalid_expected_version"}, status_code=400)
        return self._response(
            await client.rollback_environment_calibration(
                str(entity_id or ""),
                expected_version,
                confirmation_token=str(body.get("confirmation_token") or ""),
                actor=actor,
            )
        )


ENVIRONMENT_CALIBRATION_VIEW_CLASSES = (
    SmartAgentEnvironmentCalibrationView,
    SmartAgentEnvironmentCalibrationSamplesView,
    SmartAgentEnvironmentCalibrationSuggestionsView,
    SmartAgentEnvironmentCalibrationApplyView,
    SmartAgentEnvironmentCalibrationRollbackView,
)
