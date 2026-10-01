"""Fast-path request evidence, transport, and fail-closed request events."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import logging
from .active_ai_rollout import DEFAULT_ACTIVE_AI_MODE, normalize_active_ai_mode
from .presence_runtime import enrich_fast_path_presence_timing

_LOGGER = logging.getLogger("custom_components.smart_agent.fast_path_listener")


@dataclass(frozen=True, slots=True)
class FastPathTrigger:
    entity_id: str
    new_state: str
    old_state: str

    @property
    def summary(self) -> str:
        return f"{self.entity_id}: {self.old_state} -> {self.new_state}"


@dataclass(frozen=True, slots=True)
class FastPathProviderResponse:
    payload: Any
    failed: bool


@dataclass(frozen=True, slots=True)
class FastPathRequest:
    host: Any
    client: Any
    trigger: FastPathTrigger
    snapshot: dict[str, Any]
    diagnostics: dict[str, Any]
    request_id: str

    async def fetch(self) -> FastPathProviderResponse:
        if self.client is None:
            return FastPathProviderResponse(None, False)
        addon_client = self.client
        entity_id, old_state, new_state = (
            self.trigger.entity_id,
            self.trigger.old_state,
            self.trigger.new_state,
        )
        snapshot, request_id = self.snapshot, self.request_id
        try:
            response = await addon_client.run_decision_fast_path(
                entity_id=entity_id,
                new_state=new_state,
                old_state=old_state,
                snapshot=snapshot,
                request_id=request_id,
            )
        except Exception as exc:
            self.report_failure(exc)
            return FastPathProviderResponse(None, True)
        return FastPathProviderResponse(response, False)

    def report_failure(self, exc: Exception) -> None:
        exception_type = type(exc).__name__
        _LOGGER.debug(
            "[Listeners] add-on fast-path decision failed: exception_type=%s request_id=%s",
            exception_type, self.request_id,
        )
        self.report_unavailable(reason="exception", exception_type=exception_type)

    def report_unavailable(self, *, reason: str = "unreachable", exception_type: str = "") -> None:
        host = self.host
        entity_id, old_state, new_state = (
            self.trigger.entity_id,
            self.trigger.old_state,
            self.trigger.new_state,
        )
        snapshot_diag, request_id = self.diagnostics, self.request_id
        exception_fields = {"exception_type": exception_type} if exception_type else {}
        exception_log = f" exception_type={exception_type}" if exception_type else ""
        host._sys_log(
            "ERROR",
            f"[Add-on FastPath] addon_unreachable fail-closed | entity={entity_id} "
            f"reason={reason}{exception_log} request_id={request_id}",
        )
        host._emit_addon_fast_path_event(
            {
                "source": "addon_fast_path",
                "entity_id": entity_id,
                "old_state": old_state,
                "new_state": new_state,
                "status": 0,
                "matched": False,
                "path_taken": "none",
                "reason": reason,
                **exception_fields,
                "request_id": request_id,
                "correlation_id": request_id,
                "fail_closed": True,
                "snapshot": snapshot_diag,
            }
        )


def fast_path_disabled(host: Any, trigger: FastPathTrigger) -> bool:
    entity_id, old_state, new_state = trigger.entity_id, trigger.old_state, trigger.new_state
    if normalize_active_ai_mode(getattr(host, "_active_ai_mode", DEFAULT_ACTIVE_AI_MODE)) == "off":
        host._sys_log(
            "INFO",
            f"[Add-on FastPath] active_ai_off | entity={entity_id}",
        )
        host._emit_addon_fast_path_event(
            {
                "source": "addon_fast_path",
                "entity_id": entity_id,
                "old_state": old_state,
                "new_state": new_state,
                "status": 200,
                "matched": False,
                "path_taken": "active_ai_rollout_gate",
                "reason": "active_ai_off",
                "executed": False,
                "fail_closed": True,
            }
        )
        return True
    return False


def _bind_transition_observation(
    snapshot: dict[str, Any], trigger: FastPathTrigger, causal_event: dict[str, Any] | None
) -> None:
    entity_id, old_state, new_state = trigger.entity_id, trigger.old_state, trigger.new_state
    observations = snapshot.get("state_observations")
    if isinstance(causal_event, dict) and causal_event:
        snapshot["causal_events"] = [dict(causal_event)]
    elif isinstance(observations, dict):
        trigger_observation = observations.get(entity_id)
        if isinstance(trigger_observation, dict):
            # Bind the transition to the same HA state observation used by
            # the typed signal gate. The add-on must not trust the HTTP
            # old_state/new_state pair as an independent evidence source.
            trigger_observation["previous_state"] = str(old_state or "")
            trigger_observation["event_current_state"] = str(new_state or "")


def _log_request(request: FastPathRequest) -> None:
    entity_id, old_state, new_state = (
        request.trigger.entity_id,
        request.trigger.old_state,
        request.trigger.new_state,
    )
    request_id, snapshot_diag = request.request_id, request.diagnostics
    request.host._sys_log(
        "INFO",
        "[Add-on FastPath] request "
        f"entity={entity_id} old={old_state} new={new_state} "
        f"request_id={request_id} "
        f"active_space={snapshot_diag.get('active_space') or '-'} "
        f"capability_rows={snapshot_diag.get('capability_rows', 0)} "
        f"device_info_count={snapshot_diag.get('device_info_count', 0)} "
        f"topology_count={snapshot_diag.get('topology_count', 0)}",
    )


async def prepare_fast_path_request(
    host: Any,
    trigger: FastPathTrigger,
    *,
    occupancy_cycle_id: str,
    causal_event: dict[str, Any] | None,
    trigger_context: dict[str, Any] | None,
) -> FastPathRequest:
    entity_id, old_state, new_state = trigger.entity_id, trigger.old_state, trigger.new_state
    if str(new_state or "").strip().lower() in {
        "on",
        "open",
        "home",
        "occupied",
        "present",
        "detected",
        "motion",
        "person",
    }:
        host._cancel_presence_temporal_recheck(entity_id)
    addon_client = getattr(host, "_addon_client", None)
    if addon_client is not None:
        await host._refresh_correction_suppressions_cache(addon_client)
    snapshot = host._build_addon_fast_path_snapshot(entity_id)
    _bind_transition_observation(snapshot, trigger, causal_event)
    enrich_fast_path_presence_timing(host, snapshot, trigger_context)
    snapshot["occupancy_cycle_id"] = str(occupancy_cycle_id or "").strip()
    request_id = host._new_addon_fast_path_request_id(entity_id, old_state, new_state)
    snapshot["request_id"] = request_id
    snapshot_diag = host._addon_fast_path_snapshot_diagnostics(snapshot, entity_id)
    request = FastPathRequest(host, addon_client, trigger, snapshot, snapshot_diag, request_id)
    _log_request(request)
    return request


def report_fast_path_unavailable(request: FastPathRequest) -> None:
    request.report_unavailable()


def schedule_fast_path_remainder(request: FastPathRequest, response: dict) -> None:
    from .room_remainder_runtime import schedule_room_remainder

    schedule_room_remainder(
        request.host,
        response,
        entity_id=request.trigger.entity_id,
        trigger=request.trigger.summary,
        new_state=request.trigger.new_state,
    )
