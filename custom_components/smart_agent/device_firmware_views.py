"""Authenticated thin HA views for add-on-owned firmware maintenance."""
from __future__ import annotations

import base64
from typing import Any

from homeassistant.components.http import HomeAssistantView


def _admin_actor(request: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
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


class _FirmwareView(HomeAssistantView):
    requires_auth = True
    extra_urls: list[str] = []

    def _response(self, payload: Any, *, fallback_status: int = 502):
        if not isinstance(payload, dict):
            return self.json({"ok": False, "error": "firmware_addon_unavailable"}, status_code=fallback_status)
        body = dict(payload)
        status = int(body.pop("__status", 200) or 200)
        return self.json(body, status_code=status)

    def _read_client(self, request: Any):
        if request.get("hass_user") is None:
            return None, self.json({"ok": False, "error": "unauthorized"}, status_code=401)
        client = _addon_client(request)
        if client is None:
            return None, self.json({"ok": False, "error": "coordinator_unavailable", "retryable": True}, status_code=503)
        return client, None

    def _admin_client(self, request: Any):
        actor, error = _admin_actor(request)
        if error is not None:
            return None, self.json({"ok": False, "error": error["error"]}, status_code=error["status"])
        client = _addon_client(request)
        if client is None:
            return None, self.json({"ok": False, "error": "coordinator_unavailable", "retryable": True}, status_code=503)
        return (client, actor), None

    async def _json_body(self, request: Any) -> dict[str, Any] | None:
        try:
            body = await request.json()
        except Exception:
            return None
        return body if isinstance(body, dict) else None


class SmartAgentFirmwareImagesView(_FirmwareView):
    url = "/api/v1/firmware/images"
    name = "api:smart_agent:v1:firmware:images"

    async def get(self, request: Any):
        client, error = self._read_client(request)
        if error is not None:
            return error
        return self._response(await client.list_firmware_images())

    async def post(self, request: Any):
        authorized, error = self._admin_client(request)
        if error is not None:
            return error
        client, actor = authorized
        encoded_manifest = str(request.headers.get("X-SA-Firmware-Manifest", "") or "")
        try:
            manifest_bytes = base64.urlsafe_b64decode((encoded_manifest + "=" * (-len(encoded_manifest) % 4)).encode("ascii"))
            import json
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except Exception:
            return self.json({"ok": False, "error": "firmware_manifest_header_invalid"}, status_code=400)
        if not isinstance(manifest, dict):
            return self.json({"ok": False, "error": "firmware_manifest_header_invalid"}, status_code=400)
        image = await request.read()
        return self._response(await client.upload_firmware_image(image, manifest, actor=actor))


class SmartAgentDeviceFirmwareView(_FirmwareView):
    url = "/api/v1/devices/{entity_id}/firmware"
    name = "api:smart_agent:v1:devices:firmware"

    async def get(self, request: Any, entity_id: str):
        client, error = self._read_client(request)
        if error is not None:
            return error
        return self._response(await client.get_device_firmware(str(entity_id or "")))


class SmartAgentDeviceFirmwarePlanView(_FirmwareView):
    url = "/api/v1/devices/{entity_id}/firmware/plan"
    name = "api:smart_agent:v1:devices:firmware:plan"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._admin_client(request)
        if error is not None:
            return error
        body = await self._json_body(request)
        if body is None:
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        client, actor = authorized
        return self._response(await client.plan_device_firmware(str(entity_id or ""), str(body.get("image_sha256") or ""), actor=actor))


class SmartAgentDeviceFirmwareExecuteView(_FirmwareView):
    url = "/api/v1/devices/{entity_id}/firmware/execute"
    name = "api:smart_agent:v1:devices:firmware:execute"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._admin_client(request)
        if error is not None:
            return error
        body = await self._json_body(request)
        if body is None:
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        client, actor = authorized
        return self._response(await client.execute_device_firmware(str(entity_id or ""), body, actor=actor))


class SmartAgentDeviceFirmwareRetryView(_FirmwareView):
    url = "/api/v1/devices/{entity_id}/firmware/retry"
    name = "api:smart_agent:v1:devices:firmware:retry"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._admin_client(request)
        if error is not None:
            return error
        body = await self._json_body(request)
        if body is None:
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        client, actor = authorized
        return self._response(await client.retry_device_firmware(str(entity_id or ""), str(body.get("transaction_id") or ""), actor=actor))


class SmartAgentDeviceFirmwareCancelView(_FirmwareView):
    url = "/api/v1/devices/{entity_id}/firmware/cancel"
    name = "api:smart_agent:v1:devices:firmware:cancel"

    async def post(self, request: Any, entity_id: str):
        authorized, error = self._admin_client(request)
        if error is not None:
            return error
        body = await self._json_body(request)
        if body is None:
            return self.json({"ok": False, "error": "invalid_request_body"}, status_code=400)
        client, actor = authorized
        return self._response(await client.cancel_device_firmware(str(entity_id or ""), str(body.get("transaction_id") or ""), actor=actor))


class SmartAgentDeviceFirmwareTransactionView(_FirmwareView):
    url = "/api/v1/devices/{entity_id}/firmware/transactions/{transaction_id}"
    name = "api:smart_agent:v1:devices:firmware:transaction"

    async def get(self, request: Any, entity_id: str, transaction_id: str):
        client, error = self._read_client(request)
        if error is not None:
            return error
        return self._response(await client.get_device_firmware_transaction(str(entity_id or ""), str(transaction_id or "")))


DEVICE_FIRMWARE_VIEW_CLASSES = (
    SmartAgentFirmwareImagesView,
    SmartAgentDeviceFirmwareView,
    SmartAgentDeviceFirmwarePlanView,
    SmartAgentDeviceFirmwareExecuteView,
    SmartAgentDeviceFirmwareRetryView,
    SmartAgentDeviceFirmwareCancelView,
    SmartAgentDeviceFirmwareTransactionView,
)
