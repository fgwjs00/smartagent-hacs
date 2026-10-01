"""HA slow-decision request, rollout, and receipt orchestration."""

from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import datetime, timezone
from typing import Any

from .admin_actor import AuthenticatedOwnerSession
from .decision_provider import SlowDecisionProvider
from .decision_submission import submit_slow_decision
from .decision_planning import prepare_slow_decision
from .decision_confidence import prepare_decision_confidence, report_confidence_rejection
from .decision_policy_outcomes import (
    DecisionPolicyContext,
    observe_committed_fast_path,
    report_rollout_rejection,
    report_learning_observation,
)
from .decision_rollout import prepare_decision_rollout
from .decision_presentation import SlowDecisionEmitter, finalize_decision_reply

_LOGGER = logging.getLogger(__name__)


def build_patrol_task_occurrence(
    *,
    now: datetime,
    interval_minutes: int,
    scope_id: str,
    policy: dict[str, Any],
    job_id: str = "ha_low_frequency_patrol",
) -> dict[str, str]:
    """Build one stable schedule-slot identity without snapshot-value hashing."""

    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("patrol_occurrence_now_invalid")
    if type(interval_minutes) is not int or not 1 <= interval_minutes <= 1440:
        raise ValueError("patrol_occurrence_interval_invalid")
    if type(scope_id) is not str or not scope_id.strip():
        raise ValueError("patrol_occurrence_scope_invalid")
    if type(job_id) is not str or job_id not in {
        "ha_low_frequency_patrol",
        "ha_low_frequency_patrol_safety_net",
        "ha_manual_patrol",
    }:
        raise ValueError("patrol_occurrence_job_invalid")
    if type(policy) is not dict:
        raise ValueError("patrol_occurrence_policy_invalid")
    try:
        policy_json = json.dumps(
            {
                "schema_version": "smartagent.patrol_policy_revision.v0.1",
                "job_id": job_id,
                "interval_minutes": interval_minutes,
                "policy": policy,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("patrol_occurrence_policy_invalid") from exc
    current = now.astimezone(timezone.utc)
    interval_seconds = interval_minutes * 60
    slot_epoch = int(current.timestamp()) // interval_seconds * interval_seconds
    scheduled_for = datetime.fromtimestamp(slot_epoch, timezone.utc)
    return {
        "schema_version": "0.1",
        "job_id": job_id,
        "scheduled_for_utc": scheduled_for.isoformat(timespec="microseconds"),
        "scope_id": scope_id.strip(),
        "policy_revision": hashlib.sha256(policy_json.encode("utf-8")).hexdigest(),
    }


def scope_patrol_snapshot_projection(
    *,
    requested_space_id: str,
    device_info: dict[str, Any],
    states: dict[str, Any],
    state_observations: dict[str, Any],
    capability_snapshot: dict[str, Any],
    low_risk_entity_ids: Any,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Restrict a patrol snapshot to one space and its admitted actuators."""
    normalized_space_id = str(requested_space_id or "").strip()
    if not normalized_space_id:
        return (
            dict(device_info),
            dict(states),
            dict(state_observations),
            dict(capability_snapshot),
        )

    scoped_entity_ids: set[str] = set()
    normalized_low_risk_ids = {
        str(value or "").strip()
        for value in (low_risk_entity_ids or ())
        if str(value or "").strip()
    }
    read_only_domains = {"sensor", "binary_sensor", "person", "device_tracker"}
    for managed_entity_id, raw_info in device_info.items():
        info = raw_info if isinstance(raw_info, dict) else {}
        primary_spaces = {
            str(info.get(key) or "").strip()
            for key in ("space_id", "room_id", "area_id", "room", "area")
            if str(info.get(key) or "").strip()
        }
        candidate_spaces = set(primary_spaces)
        capability = (
            capability_snapshot.get(managed_entity_id)
            if isinstance(capability_snapshot.get(managed_entity_id), dict)
            else {}
        )
        for key in ("space_id", "room_id", "area_id", "room", "area"):
            value = str(capability.get(key) or "").strip()
            if value:
                candidate_spaces.add(value)
                primary_spaces.add(value)
        for key in (
            "coverage_spaces",
            "target_space_ids",
            "coverage_space_ids",
        ):
            raw_values = capability.get(key)
            if isinstance(raw_values, (list, tuple, set)):
                candidate_spaces.update(
                    str(value or "").strip() for value in raw_values if str(value or "").strip()
                )
        domain = managed_entity_id.split(".", 1)[0]
        actuator_allowed = (
            not normalized_low_risk_ids
            or domain in read_only_domains
            or managed_entity_id in normalized_low_risk_ids
        )
        scope_matches = normalized_space_id in (
            candidate_spaces if domain in read_only_domains else primary_spaces
        )
        if scope_matches and actuator_allowed:
            scoped_entity_ids.add(managed_entity_id)

    return (
        {
            managed_entity_id: info
            for managed_entity_id, info in device_info.items()
            if managed_entity_id in scoped_entity_ids
        },
        {
            managed_entity_id: state
            for managed_entity_id, state in states.items()
            if managed_entity_id in scoped_entity_ids
        },
        {
            managed_entity_id: observation
            for managed_entity_id, observation in state_observations.items()
            if managed_entity_id in scoped_entity_ids
        },
        {
            managed_entity_id: capability
            for managed_entity_id, capability in capability_snapshot.items()
            if managed_entity_id in scoped_entity_ids
        },
    )


def build_patrol_environment_projection(
    *,
    now: datetime,
    device_info: dict[str, Any],
    states: dict[str, Any],
    state_observations: dict[str, Any],
    presence_snapshot: dict[str, Any],
    trigger_space_id: str,
    trigger_room: str,
    interval_minutes: Any,
    quiet_start: str,
    quiet_end: str,
    low_risk_entity_ids: Any,
    quiet_hours_active: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    """Project patrol-only freshness and policy facts without owning dispatch."""
    working_states = dict(states)
    working_observations = dict(state_observations)
    normalized_interval = max(1, int(interval_minutes or 15))
    environment_max_age_seconds = max(
        300,
        min(1800, normalized_interval * 120),
    )
    fresh_environment_entity_ids: list[str] = []
    stale_environment_entity_ids: list[str] = []
    environment_markers = (
        "temperature",
        "humidity",
        "heat_index",
        "apparent_temperature",
        "wendu",
        "shidu",
        "温度",
        "湿度",
    )
    reference_now = now
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=timezone.utc)
    for managed_entity_id, raw_info in device_info.items():
        if not str(managed_entity_id).startswith("sensor."):
            continue
        info = raw_info if isinstance(raw_info, dict) else {}
        descriptor = " ".join(
            str(info.get(key) or "").strip().lower()
            for key in (
                "capability",
                "type",
                "device_class",
                "name",
            )
        )
        descriptor = f"{descriptor} {managed_entity_id.lower()}"
        if not any(marker in descriptor for marker in environment_markers):
            continue
        observation = working_observations.get(managed_entity_id)
        if not isinstance(observation, dict):
            observation = {}
            working_observations[managed_entity_id] = observation
        timestamp_text = str(
            observation.get("last_updated") or observation.get("last_changed") or ""
        ).strip()
        age_seconds: float | None = None
        if timestamp_text:
            try:
                observed_time = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
                if observed_time.tzinfo is None:
                    observed_time = observed_time.replace(tzinfo=reference_now.tzinfo)
                age_seconds = (
                    reference_now.astimezone(timezone.utc) - observed_time.astimezone(timezone.utc)
                ).total_seconds()
            except (TypeError, ValueError, OverflowError):
                age_seconds = None
        raw_state_value = working_states.get(managed_entity_id)
        if raw_state_value in (None, ""):
            raw_state_value = observation.get("state")
        try:
            numeric_state = float(str(raw_state_value or "").strip())
            state_is_valid = math.isfinite(numeric_state)
        except (TypeError, ValueError, OverflowError):
            state_is_valid = False
        timestamp_is_fresh = bool(
            age_seconds is not None and -60.0 <= age_seconds <= environment_max_age_seconds
        )
        is_fresh = timestamp_is_fresh and state_is_valid
        observation["freshness_status"] = "fresh" if is_fresh else "stale"
        observation["freshness_reason"] = (
            "fresh"
            if is_fresh
            else (
                "invalid_or_unavailable_state"
                if timestamp_is_fresh and not state_is_valid
                else "timestamp_stale_or_missing"
            )
        )
        observation["max_age_seconds"] = environment_max_age_seconds
        if age_seconds is not None:
            observation["age_seconds"] = round(age_seconds, 1)
        if is_fresh:
            fresh_environment_entity_ids.append(managed_entity_id)
        else:
            stale_environment_entity_ids.append(managed_entity_id)
            working_states.pop(managed_entity_id, None)
            observation.pop("state", None)

    rooms = (
        presence_snapshot.get("rooms") if isinstance(presence_snapshot.get("rooms"), dict) else {}
    )
    presence_key = str(trigger_space_id or trigger_room or "").strip()
    room_presence = (
        rooms.get(presence_key)
        if presence_key and isinstance(rooms.get(presence_key), dict)
        else {}
    )
    presence_state = (
        str(room_presence.get("state") or room_presence.get("presence_state") or "unknown")
        .strip()
        .lower()
    )
    normalized_low_risk_ids = list(
        dict.fromkeys(
            str(value or "").strip()
            for value in (low_risk_entity_ids or ())
            if str(value or "").strip()
        )
    )
    policy = {
        "quiet_hours_active": quiet_hours_active(now, quiet_start, quiet_end),
        "quiet_hours": {"start": quiet_start, "end": quiet_end},
        "low_risk_entity_ids": normalized_low_risk_ids,
        "presence_state": presence_state,
        "environment_max_age_seconds": environment_max_age_seconds,
        "fresh_environment_entity_ids": fresh_environment_entity_ids,
        "stale_environment_entity_ids": stale_environment_entity_ids,
    }
    return working_states, working_observations, policy, stale_environment_entity_ids


async def run_addon_decision(
    self,
    trigger: str,
    *,
    one_off_prompt: str = "",
    source: str = "listener",
    user_explicit_voice: bool = False,
    source_trace_context: dict[str, Any] | None = None,
    trigger_space_id: str = "",
    causal_events: list[dict[str, Any]] | None = None,
    task_occurrence: dict[str, Any] | None = None,
    user_intent_authority: Any | None = None,
) -> dict[str, Any]:
    policy_unauthorized_speech = "当前策略未授权执行"
    bundle = self._build_addon_slow_decision_bundle(
        trigger,
        one_off_prompt=one_off_prompt,
        source=source,
        user_explicit_voice=user_explicit_voice,
        source_trace_context=source_trace_context,
        trigger_space_id=trigger_space_id,
        causal_events=causal_events,
        task_occurrence=task_occurrence,
    )
    # Only the typed authority created by the HA conversation boundary can
    # establish a user-explicit voice execution.  Keep the legacy boolean for
    # compatibility with non-conversation callers, but it never selects the
    # owner execution class.
    explicit_voice_control = bool(
        type(user_intent_authority) is AuthenticatedOwnerSession and bundle.get("is_voice")
    )
    addon_client = getattr(self, "_addon_client", None)
    self._sys_log(
        "INFO",
        "[决策] 慢脑上下文 "
        f"entity={bundle.get('trigger_entity_id') or '-'} "
        f"room={bundle.get('trigger_room') or '-'} "
        f"state={bundle.get('old_state') or '?'}->{bundle.get('new_state') or '?'} "
        f"devices={len(bundle.get('device_info') or {})}",
    )
    trigger_public_summary = self._trigger_public_summary(
        trigger,
        entity_id=str(bundle.get("trigger_entity_id") or ""),
        old_state=str(bundle.get("old_state") or ""),
        new_state=str(bundle.get("new_state") or ""),
    )

    emitter = SlowDecisionEmitter(self, bundle, trigger_public_summary)
    _emit_slow_decision_bubble = emitter.emit

    provider = SlowDecisionProvider(
        host=self,
        bundle=bundle,
        client=addon_client,
        trigger=trigger,
        explicit_voice_control=explicit_voice_control,
        emitter=emitter,
        policy_unauthorized_speech=policy_unauthorized_speech,
    )
    rejected = provider.preflight()
    if rejected is not None:
        return rejected
    inference_lock = provider.inference_lock()
    async with inference_lock:
        provider_response = await provider.fetch()
        if provider_response.terminal:
            return provider_response.payload
        result, status = provider_response.payload, provider_response.status

        prepared = prepare_slow_decision(self, bundle=bundle, result=result, trigger=trigger)
        records = prepared.records
        valid_actions = prepared.actions
        candidate_actions = records.candidate_actions
        patrol_policy_blocked_actions = prepared.patrol_blocked_actions
        transaction_id, scene, confidence = (
            records.transaction_id,
            records.scene,
            records.confidence,
        )
        policy_context = DecisionPolicyContext(records, emitter, status, policy_unauthorized_speech)
        learning_observe_only = (
            bool(getattr(self, "_learning_mode", False)) and source == "listener"
        )
        executed = 0
        action_results: list[dict[str, Any]] = []
        final_outcome = "no_actions"
        if patrol_policy_blocked_actions and not valid_actions:
            final_outcome = "blocked"
            result["matched"] = bool(candidate_actions)
            result["executed_count"] = 0
            result["final_outcome"] = final_outcome
            result["execution_status"] = final_outcome
        fast_path_audit_observe_only = observe_committed_fast_path(policy_context)
        rollout_blocked_actions: list[dict[str, Any]] = []
        if fast_path_audit_observe_only:
            valid_actions = []
            final_outcome = "observe_only"

        if valid_actions:
            rollout = prepare_decision_rollout(
                self,
                bundle=bundle,
                result=result,
                valid_actions=valid_actions,
                candidate_actions=candidate_actions,
                explicit_voice_control=explicit_voice_control,
            )
            valid_actions = rollout.selection.actions
            rollout_blocked_actions = rollout.selection.blocked_actions
            active_execution_space_id = rollout.active_space_id
            if not rollout.allow_execution:
                return report_rollout_rejection(policy_context, rollout)

            admission = prepare_decision_confidence(policy_context, valid_actions)
            arbitration_result = admission.arbitration_result
            if not admission.auto_execute:
                return report_confidence_rejection(
                    policy_context, admission, valid_actions, rollout_blocked_actions
                )
            if learning_observe_only:
                return report_learning_observation(
                    policy_context, valid_actions, rollout_blocked_actions
                )
            submission = await submit_slow_decision(
                policy_context,
                valid_actions,
                rollout_blocked_actions,
                active_space_id=active_execution_space_id,
                authority=user_intent_authority,
                arbitration_result=arbitration_result,
            )
            executed, final_outcome = submission.executed, submission.final_outcome
            action_results = submission.action_results
        else:
            self._sys_log(
                "INFO", f"[决策] add-on 未返回可执行动作: {result.get('reason') or 'no_actions'}"
            )
        _emit_slow_decision_bubble(
            result_payload=result,
            status_code=status,
            matched=bool(valid_actions) or fast_path_audit_observe_only,
            reason=str(result.get("reason") or ("matched" if valid_actions else "no_actions")),
            scene_desc=scene,
            confidence_value=confidence,
            actions_payload=valid_actions,
            transaction_id_value=transaction_id,
            executed_count=executed,
            final_outcome_value=final_outcome,
            fail_closed=False,
            record_decision_log=not bool(transaction_id),
        )
        finalize_decision_reply(
            result=result,
            is_voice=bundle.get("is_voice"),
            valid_actions=valid_actions,
            executed=executed,
            action_results=action_results,
            final_outcome=final_outcome,
            policy_unauthorized_speech=policy_unauthorized_speech,
        )
        if isinstance(result.get("room_remainder_ref"), dict):
            from .room_remainder_runtime import schedule_room_remainder

            schedule_room_remainder(
                self,
                result,
                entity_id=str(bundle.get("trigger_entity_id") or ""),
                trigger=str(trigger or ""),
                new_state=str(bundle.get("new_state") or ""),
            )
        return result


__all__ = [
    "build_patrol_environment_projection",
    "build_patrol_task_occurrence",
    "run_addon_decision",
    "scope_patrol_snapshot_projection",
]
