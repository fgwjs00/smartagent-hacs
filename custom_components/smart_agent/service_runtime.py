"""Entry-scoped HA service handlers that proxy add-on owned capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import voluptuous as vol
from homeassistant.core import ServiceCall

from .admin_actor import is_current_human_user
from .ha_adapter import _bind_user_explicit_output_authority


AdminCheck = Callable[[ServiceCall], Awaitable[bool]]


@dataclass(frozen=True, slots=True)
class EntryServiceRuntime:
    approve_ai_scene: Any
    reject_ai_scene: Any
    delete_ai_scene: Any
    trigger_ai_scene: Any
    create_scene_from_text: Any
    rollback_transaction: Any
    refresh_transactions: Any
    tts_test: Any
    voice_command: Any
    run_pattern_analysis: Any
    ai_scene_schema: Any
    create_scene_schema: Any
    transaction_schema: Any


def build_entry_service_runtime(
    *,
    hass: Any,
    coordinator: Any,
    _check_admin: AdminCheck,
) -> EntryServiceRuntime:
    """Build handlers while keeping the config-entry lifecycle thin."""

    async def _proxy_ai_scene_lifecycle(action: str, scene_id: int) -> None:
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log(
                "WARN",
                "[AI场景] add-on lifecycle provider unavailable",
            )
            return

        try:
            if action == "approve":
                result = await _addon_client.post_ai_scene_action("approve", scene_id)
            elif action == "reject":
                result = await _addon_client.post_ai_scene_action("reject", scene_id)
            elif action == "delete":
                result = await _addon_client.post_ai_scene_delete_fallback(scene_id)
            elif action == "trigger":
                result = await _addon_client.trigger_ai_scene(scene_id)
            else:
                coordinator._sys_log(
                    "WARN",
                    f"[AI场景] 不支持的 lifecycle action: {action}",
                )
                return
        except Exception as exc:
            coordinator._sys_log(
                "WARN",
                f"[AI场景] add-on lifecycle provider 调用失败: {exc}",
            )
            return

        if not isinstance(result, dict):
            coordinator._sys_log(
                "WARN",
                "[AI场景] add-on lifecycle provider unavailable",
            )
            return
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_type") or f"http_{status}"
            coordinator._sys_log(
                "WARN",
                "[AI场景] add-on lifecycle provider 返回失败: "
                f"{action} id={scene_id} error={error}",
            )
            return

        coordinator._sys_log(
            "INFO",
            f"[AI场景] lifecycle 已交由 add-on provider: {action} id={scene_id}",
        )
        coordinator.async_set_updated_data({})

    async def svc_approve_ai_scene(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        await _proxy_ai_scene_lifecycle("approve", int(call.data["id"]))

    async def svc_reject_ai_scene(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        await _proxy_ai_scene_lifecycle("reject", int(call.data["id"]))

    async def svc_delete_ai_scene(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        await _proxy_ai_scene_lifecycle("delete", int(call.data["id"]))

    async def svc_trigger_ai_scene(call: ServiceCall) -> None:
        await _proxy_ai_scene_lifecycle("trigger", int(call.data["id"]))

    async def svc_create_scene_from_text(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log(
                "WARN",
                "[AI场景] add-on ops provider unavailable: create-from-text",
            )
            return
        body = {
            "text": call.data["text"],
            "auto_activate": bool(call.data.get("auto_activate", False)),
        }
        result = await _addon_client.post_ai_scene_ops(
            "ai-scenes/create-from-text",
            body,
        )
        if not isinstance(result, dict):
            coordinator._sys_log(
                "WARN",
                "[AI场景] add-on ops provider unavailable: create-from-text",
            )
            return
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_type") or f"http_{status}"
            coordinator._sys_log(
                "WARN",
                f"[AI场景] add-on create-from-text failed: {error}",
            )
            return
        coordinator.hass.bus.async_fire(
            "smart_agent_scene_created",
            {
                "success": result.get("success"),
                "scene_id": result.get("scene_id"),
                "name": result.get("name"),
                "status": result.get("status"),
                "error": result.get("error", ""),
            },
        )

    async def svc_rollback_transaction(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        await coordinator.async_rollback_transaction(int(call.data["id"]))

    async def svc_refresh_transactions(_call: ServiceCall) -> None:
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log(
                "WARN",
                "[Transaction] refresh unavailable: add-on client missing",
            )
            return
        try:
            payload = await _addon_client.get_transactions()
        except Exception as exc:
            coordinator._sys_log(
                "WARN",
                f"[Transaction] add-on transaction refresh failed: {exc}",
            )
            return
        rows: list[dict[str, Any]] = []
        if isinstance(payload, list):
            rows = [dict(item) for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            try:
                status = int(payload.get("__status") or payload.get("status") or 0)
            except (TypeError, ValueError):
                status = 0
            if status >= 400 or payload.get("ok") is False:
                error = (
                    payload.get("error")
                    or payload.get("error_type")
                    or f"http_{status}"
                )
                coordinator._sys_log(
                    "WARN",
                    f"[Transaction] add-on transaction refresh failed: {error}",
                )
                return
            for key in ("transactions", "items", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    rows = [dict(item) for item in value if isinstance(item, dict)]
                    break
        else:
            coordinator._sys_log(
                "WARN",
                "[Transaction] add-on transaction refresh returned empty result",
            )
            return
        coordinator._transactions_cache = rows
        coordinator.async_set_updated_data({})

    async def svc_tts_test(call: ServiceCall) -> None:
        context = getattr(call, "context", None)
        user_id = str(getattr(context, "user_id", "") or "").strip()
        user = await hass.auth.async_get_user(user_id) if user_id else None
        service_ref = str(getattr(coordinator, "_tts_service", "") or "").strip()
        target = str(getattr(coordinator, "_tts_target", "") or "").strip()
        if not is_current_human_user(user) or "." not in service_ref or not target:
            coordinator._sys_log(
                "WARN",
                "[TTS] 拒绝非当前人类用户或无效 TTS 配置",
            )
            return
        domain, service = service_ref.split(".", 1)
        try:
            output_authority = _bind_user_explicit_output_authority(
                authenticated_user_id=user_id,
                domain=domain,
                service=service,
                target_entity_id=target,
            )
        except ValueError:
            coordinator._sys_log(
                "WARN",
                "[TTS] 当前配置不满足受控 tts.speak 合同",
            )
            return
        await coordinator._tts_speak(
            "SmartAgent TTS 测试，语音播报正常。",
            min_level=0,
            authority=output_authority,
        )

    async def svc_voice_command(call: ServiceCall) -> None:
        context = getattr(call, "context", None)
        user_id = str(getattr(context, "user_id", "") or "").strip()
        user = await hass.auth.async_get_user(user_id) if user_id else None
        if not is_current_human_user(user):
            coordinator._sys_log(
                "WARN",
                "[语音] 拒绝无当前用户、停用用户或系统生成用户的显式语音指令",
            )
            return
        await coordinator._run_voice_inference(
            call.data.get("command", ""),
            source="ha_service",
            user_explicit_voice=True,
        )

    async def svc_run_pattern_analysis(call: ServiceCall) -> None:
        if not await _check_admin(call):
            return
        _addon_client = getattr(coordinator, "_addon_client", None)
        if _addon_client is None:
            coordinator._sys_log(
                "WARN",
                "[AI场景] add-on ops provider unavailable: analyze",
            )
            return
        result = await _addon_client.post_ai_scene_ops("ai-scenes/analyze", {})
        if not isinstance(result, dict):
            coordinator._sys_log(
                "WARN",
                "[AI场景] add-on ops provider unavailable: analyze",
            )
            return
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_type") or f"http_{status}"
            coordinator._sys_log(
                "WARN",
                f"[AI场景] add-on analyze failed: {error}",
            )
            return
        coordinator.async_set_updated_data({})

    return EntryServiceRuntime(
        approve_ai_scene=svc_approve_ai_scene,
        reject_ai_scene=svc_reject_ai_scene,
        delete_ai_scene=svc_delete_ai_scene,
        trigger_ai_scene=svc_trigger_ai_scene,
        create_scene_from_text=svc_create_scene_from_text,
        rollback_transaction=svc_rollback_transaction,
        refresh_transactions=svc_refresh_transactions,
        tts_test=svc_tts_test,
        voice_command=svc_voice_command,
        run_pattern_analysis=svc_run_pattern_analysis,
        ai_scene_schema=vol.Schema({vol.Required("id"): vol.Coerce(int)}),
        create_scene_schema=vol.Schema(
            {
                vol.Required("text"): str,
                vol.Optional("auto_activate", default=False): bool,
            }
        ),
        transaction_schema=vol.Schema({vol.Required("id"): vol.Coerce(int)}),
    )


__all__ = ["EntryServiceRuntime", "build_entry_service_runtime"]
