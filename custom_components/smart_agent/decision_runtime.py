"""HA slow-decision request, rollout, and receipt orchestration."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
from datetime import datetime, timezone
from typing import Any

from .active_ai_rollout import (
    ActiveAiRolloutConfig,
    DEFAULT_ACTIVE_AI_MODE,
    enrich_active_ai_action_spaces,
    evaluate_active_ai_execution_gate,
    evaluate_active_ai_model_gate,
    scope_active_ai_canary_actions,
)
from .confidence_arbitration_contract import (
    apply_arrival_lighting_confirmation_gate,
    pending_confirmation_allowed,
    validate_auto_execution_arbitration,
)
from .execution_gate import evaluate_slow_brain_confidence_gate
from .admin_actor import AuthenticatedOwnerSession

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
                    str(value or "").strip()
                    for value in raw_values
                    if str(value or "").strip()
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
            observation.get("last_updated")
            or observation.get("last_changed")
            or ""
        ).strip()
        age_seconds: float | None = None
        if timestamp_text:
            try:
                observed_time = datetime.fromisoformat(
                    timestamp_text.replace("Z", "+00:00")
                )
                if observed_time.tzinfo is None:
                    observed_time = observed_time.replace(
                        tzinfo=reference_now.tzinfo
                    )
                age_seconds = (
                    reference_now.astimezone(timezone.utc)
                    - observed_time.astimezone(timezone.utc)
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
            age_seconds is not None
            and -60.0 <= age_seconds <= environment_max_age_seconds
        )
        is_fresh = timestamp_is_fresh and state_is_valid
        observation["freshness_status"] = "fresh" if is_fresh else "stale"
        observation["freshness_reason"] = (
            "fresh"
            if is_fresh
            else "invalid_or_unavailable_state"
            if timestamp_is_fresh and not state_is_valid
            else "timestamp_stale_or_missing"
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
        presence_snapshot.get("rooms")
        if isinstance(presence_snapshot.get("rooms"), dict)
        else {}
    )
    presence_key = str(trigger_space_id or trigger_room or "").strip()
    room_presence = (
        rooms.get(presence_key)
        if presence_key and isinstance(rooms.get(presence_key), dict)
        else {}
    )
    presence_state = str(
        room_presence.get("state")
        or room_presence.get("presence_state")
        or "unknown"
    ).strip().lower()
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
        type(user_intent_authority) is AuthenticatedOwnerSession
        and bundle.get("is_voice")
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

    def _emit_slow_decision_bubble(
        *,
        result_payload: dict[str, Any] | None = None,
        status_code: int = 200,
        matched: bool = False,
        reason: str = "",
        scene_desc: str = "",
        confidence_value: int = 0,
        actions_payload: list[dict[str, Any]] | None = None,
        transaction_id_value: str = "",
        executed_count: int = 0,
        final_outcome_value: str = "no_actions",
        fail_closed: bool = False,
        record_decision_log: bool = False,
    ) -> None:
        result_payload = result_payload if isinstance(result_payload, dict) else {}
        actions_payload = actions_payload if isinstance(actions_payload, list) else []
        transaction_id_value = str(
            transaction_id_value
            or result_payload.get("transaction_id")
            or result_payload.get("decision_id")
            or result_payload.get("id")
            or ""
        ).strip()
        result_details = (
            result_payload.get("details")
            if isinstance(result_payload.get("details"), dict)
            else {}
        )
        path_taken = str(
            result_details.get("path_taken")
            or result_payload.get("path_taken")
            or "llm"
        )
        reason_value = str(reason or result_payload.get("reason") or ("matched" if matched else "no_actions"))
        scene_value = str(scene_desc or result_payload.get("scene") or "")
        event_payload = {
            "source": "ha_slow_decision",
            "entity_id": str(bundle.get("trigger_entity_id") or ""),
            "trigger_entity_id": str(bundle.get("trigger_entity_id") or ""),
            "old_state": str(bundle.get("old_state") or ""),
            "new_state": str(bundle.get("new_state") or ""),
            "trigger": trigger_public_summary,
            "trigger_summary": trigger_public_summary,
            "status": status_code,
            "matched": matched,
            "path_taken": path_taken,
            "reason": reason_value,
            "scene": scene_value,
            "confidence": confidence_value,
            "confidence_auto": result_payload.get("confidence_auto"),
            "confidence_notify": result_payload.get("confidence_notify"),
            "threshold": result_payload.get("threshold"),
            "auto_execute": result_payload.get("auto_execute") is True,
            "confirm_required": result_payload.get("confirm_required") is True,
            "arbitration_result": str(result_payload.get("arbitration_result") or ""),
            "action_count": len(actions_payload),
            "actions": actions_payload,
            "transaction_id": transaction_id_value,
            "parent_transaction_id": str(bundle.get("parent_transaction_id") or ""),
            "parent_decision_trace": bundle.get("parent_decision_trace") if isinstance(bundle.get("parent_decision_trace"), dict) else {},
            "source_trace_context": bundle.get("source_trace_context") if isinstance(bundle.get("source_trace_context"), dict) else {},
            "parent_correlation_id": str(bundle.get("parent_correlation_id") or ""),
            "parent_world_snapshot_id": str(bundle.get("parent_world_snapshot_id") or ""),
            "executed": bool(actions_payload and executed_count >= len(actions_payload)),
            "executed_count": executed_count,
            "final_outcome": final_outcome_value,
            "fail_closed": fail_closed,
        }
        try:
            self.hass.bus.async_fire("smart_agent_decision_bubble", event_payload)
        except Exception as exc:
            _LOGGER.debug("[Coordinator] slow decision bubble emit failed: %s", exc)
        if record_decision_log:
            log_result = dict(result_payload)
            log_result.setdefault("source", "ha_slow_decision")
            log_result.setdefault("path_taken", path_taken)
            log_result.setdefault("reason", reason_value)
            log_result.setdefault("scene", scene_value)
            log_result.setdefault("actions", actions_payload)
            log_result["trigger"] = trigger_public_summary
            log_result["trigger_summary"] = trigger_public_summary
            log_result["matched"] = bool(matched)
            log_result["final_outcome"] = final_outcome_value
            log_result["fail_closed"] = bool(fail_closed)
            log_payload: dict[str, Any] = {
                "trigger": trigger_public_summary,
                "trigger_summary": trigger_public_summary,
                "scene": scene_value,
                "source": "ha_slow_decision",
                "path_taken": path_taken,
                "confidence": confidence_value,
                "confidence_auto": result_payload.get("confidence_auto"),
                "confidence_notify": result_payload.get("confidence_notify"),
                "threshold": result_payload.get("threshold"),
                "auto_execute": result_payload.get("auto_execute") is True,
                "confirm_required": result_payload.get("confirm_required") is True,
                "arbitration_result": str(result_payload.get("arbitration_result") or ""),
                "matched": bool(matched),
                "action_count": len(actions_payload),
                "reason": reason_value,
                "actions": actions_payload,
                "result": log_result,
            }
            if transaction_id_value:
                log_payload["id"] = transaction_id_value
            enqueue = getattr(self, "_enqueue_internal_event", None)
            if not callable(enqueue) or not enqueue("decision_log", log_payload):
                self._sys_log(
                    "WARN",
                    f"[决策] decision_log 回写入队失败 reason={reason_value or '-'} trigger={trigger_public_summary or '-'}",
                )

    def _rollout_public_reason(reason: str) -> str:
        if reason == "active_ai_shadow":
            return "主动 AI 当前处于影子模式，仅记录决策，不执行设备"
        if reason in {"active_ai_global_disabled", "active_ai_off"}:
            return "主动 AI 已关闭，本次不执行设备"
        if reason in {
            "active_ai_canary_space_not_allowed",
            "active_ai_canary_domain_not_allowed",
        }:
            return "本次动作不在主动 AI 灰度范围内，已阻止执行"
        if reason in {
            "active_ai_domain_execution_disabled",
            "active_ai_lighting_execution_disabled",
        }:
            return "主动 AI 真实执行开关未开启，本次仅记录决策"
        return "主动 AI 灰度门禁未允许执行"

    pre_rollout_config = ActiveAiRolloutConfig.from_values(
        mode=getattr(self, "_active_ai_mode", DEFAULT_ACTIVE_AI_MODE)
    )
    pre_rollout = evaluate_active_ai_model_gate(
        ai_enabled=bool(getattr(self, "_enabled", False)),
        config=pre_rollout_config,
    )
    if not pre_rollout.allow_model and not explicit_voice_control:
        public_reason = _rollout_public_reason(pre_rollout.reason)
        rollout_trace = pre_rollout.as_trace()
        _emit_slow_decision_bubble(
            result_payload={
                "path_taken": "active_ai_rollout_gate",
                "rollout": rollout_trace,
                "rollout_reason": pre_rollout.reason,
            },
            status_code=200,
            matched=False,
            reason=public_reason,
            scene_desc="主动 AI 灰度门禁",
            final_outcome_value="blocked",
            fail_closed=True,
            record_decision_log=True,
        )
        blocked_response = {
            "status": "ok",
            "matched": False,
            "actions": [],
            "executed_count": 0,
            "reason": pre_rollout.reason,
            "rollout": rollout_trace,
            "final_outcome": "blocked",
        }
        if bundle.get("is_voice"):
            blocked_response["reply"] = policy_unauthorized_speech
            blocked_response["speak"] = policy_unauthorized_speech
        return blocked_response

    if addon_client is None:
        self._sys_log("WARN", "[决策] add-on decision provider unavailable")
        _emit_slow_decision_bubble(
            status_code=502,
            matched=False,
            reason="addon_decision_provider_unavailable",
            scene_desc="add-on decision provider unavailable",
            final_outcome_value="failed",
            fail_closed=True,
            record_decision_log=True,
        )
        return {"status": "error", "message": "add-on decision provider unavailable"}

    # ── 空设备表防裸推：无已同步设备时直接判无动作，避免模型在零设备上凭空幻觉 ──
    if not str(bundle.get("device_table") or "").strip():
        self._sys_log(
            "WARN",
            "[决策] 设备表为空（无已同步设备），跳过在线慢脑以防模型幻觉编造设备",
        )
        _emit_slow_decision_bubble(
            status_code=200,
            matched=False,
            reason="empty_device_table_no_action",
            scene_desc="无已同步设备，跳过决策",
            final_outcome_value="no_actions",
            fail_closed=True,
            record_decision_log=True,
        )
        return {
            "status": "ok",
            "matched": False,
            "actions": [],
            "scene": "无已同步设备，跳过决策",
            "confidence": 0,
            "reason": "empty_device_table_no_action",
        }
    room_lock_key = str(bundle.get("trigger_room") or "").strip()
    inference_lock = self._get_room_lock(room_lock_key) if room_lock_key else getattr(self, "_inference_lock", None)
    if inference_lock is None:
        self._inference_lock = asyncio.Lock()
        inference_lock = self._inference_lock
    if hasattr(inference_lock, "locked") and inference_lock.locked():
        self._sys_log("INFO", f"[决策] 同空间推理进行中，等待: {room_lock_key or 'global'}")
    async with inference_lock:
        try:
            result = await addon_client.run_decision(
                trigger=str(trigger or ""),
                bundle=bundle,
                request_id=str(bundle.get("parent_correlation_id") or "") or None,
                user_explicit_voice=explicit_voice_control,
            )
        except Exception as exc:
            self._sys_log("WARN", f"[决策] add-on decision provider 调用失败: {exc}")
            _emit_slow_decision_bubble(
                status_code=502,
                matched=False,
                reason="addon_decision_provider_error",
                scene_desc="线上大模型调用失败",
                final_outcome_value="failed",
                fail_closed=True,
                record_decision_log=True,
            )
            return {"status": "error", "message": str(exc)}
        if not isinstance(result, dict):
            self._sys_log("WARN", "[决策] add-on decision provider 无响应")
            _emit_slow_decision_bubble(
                status_code=502,
                matched=False,
                reason="addon_decision_provider_unavailable",
                scene_desc="线上大模型无响应",
                final_outcome_value="failed",
                fail_closed=True,
                record_decision_log=True,
            )
            return {"status": "error", "message": "add-on decision provider unavailable"}
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_type") or f"http_{status}"
            result_details = (
                result.get("details") if isinstance(result.get("details"), dict) else {}
            )
            planner_invoked = result_details.get("planner_invoked")
            if str(result.get("scene") or "").strip():
                failure_scene = str(result["scene"])
            elif planner_invoked is False:
                failure_scene = (
                    "前置事件合同冲突"
                    if str(error) == "decision_event_payload_mismatch"
                    else "决策在规划前被拒绝"
                )
            else:
                failure_scene = "线上大模型返回失败"
            policy_rejected = bool(
                str(result.get("error_type") or "").strip().lower()
                == "policy_rejected"
                or str(error or "").strip().lower().startswith(("active_ai_", "policy_"))
            )
            self._sys_log("WARN", f"[决策] add-on decision provider 返回失败: {error}")
            _emit_slow_decision_bubble(
                result_payload=result,
                status_code=status,
                matched=False,
                reason=str(error),
                scene_desc=failure_scene,
                confidence_value=0,
                actions_payload=[],
                transaction_id_value=str(result.get("transaction_id") or ""),
                executed_count=0,
                final_outcome_value="failed",
                fail_closed=True,
                record_decision_log=True,
            )
            error_response = {"status": "error", **result}
            error_response["status"] = "error"
            error_response["message"] = (
                policy_unauthorized_speech
                if bundle.get("is_voice") and policy_rejected
                else str(error)
            )
            if bundle.get("is_voice") and policy_rejected:
                error_response["reply"] = policy_unauthorized_speech
                error_response["speak"] = policy_unauthorized_speech
            return error_response

        actions = result.get("actions") if isinstance(result.get("actions"), list) else []
        valid_actions = [item for item in actions if isinstance(item, dict)]
        candidate_actions = [dict(item) for item in valid_actions]
        patrol_policy_blocked_actions: list[dict[str, Any]] = []
        if isinstance(bundle.get("patrol_execution_policy"), dict) and bundle.get(
            "patrol_execution_policy"
        ):
            valid_actions, patrol_policy_blocked_actions = (
                self._filter_patrol_reconciliation_actions(
                    valid_actions,
                    bundle,
                )
            )
            result["candidate_action_count"] = len(candidate_actions)
            result["authorized_action_count"] = len(valid_actions)
            result["authorized_actions"] = list(valid_actions)
            result["patrol_policy_blocked_actions"] = list(
                patrol_policy_blocked_actions
            )
            result["execution_authorized"] = bool(valid_actions)
            if patrol_policy_blocked_actions and not valid_actions:
                result["execution_suppressed_reason"] = "patrol_policy"
                result["reason"] = "patrol_policy_blocked"
                result["auto_execute"] = False
                result["confirm_required"] = False
                result["arbitration_result"] = "blocked_by_patrol_policy"
        scene = str(result.get("scene") or "")
        transaction_id = str(
            result.get("transaction_id")
            or result.get("decision_id")
            or result.get("id")
            or ""
        ).strip()
        decision_id = str(result.get("decision_id") or transaction_id or "unknown").strip() or "unknown"
        nested_result = result.get("result") if isinstance(result.get("result"), dict) else {}
        world_snapshot_id = str(
            result.get("world_snapshot_id")
            or nested_result.get("world_snapshot_id")
            or "unknown"
        ).strip() or "unknown"
        decision_lineage = self._build_decision_trace_lineage(
            bundle=bundle,
            result=result,
            actions=valid_actions,
        )
        try:
            confidence = int(float(result.get("confidence") or 0))
        except (TypeError, ValueError, OverflowError):
            confidence = 0
        learning_observe_only = bool(getattr(self, "_learning_mode", False)) and source == "listener"
        executed = 0
        action_results: list[dict[str, Any]] = []
        final_outcome = "no_actions"
        if patrol_policy_blocked_actions and not valid_actions:
            final_outcome = "blocked"
            result["matched"] = bool(candidate_actions)
            result["executed_count"] = 0
            result["final_outcome"] = final_outcome
            result["execution_status"] = final_outcome
        fast_path_execution_audit = (
            bundle.get("fast_path_execution_audit")
            if isinstance(bundle.get("fast_path_execution_audit"), dict)
            else {}
        )
        fast_path_audit_observe_only = bool(
            fast_path_execution_audit
            and str(fast_path_execution_audit.get("final_outcome") or "").strip()
            == "succeeded"
        )
        if fast_path_audit_observe_only:
            # The fast path already crossed the physical-effect boundary.
            # System 2 is an auditor for this occurrence, never a second
            # executor.  Any correction must start from a fresh snapshot as
            # a new decision occurrence instead of replaying this handoff.
            audit_candidates = [dict(item) for item in candidate_actions]
            valid_actions = []
            final_outcome = "observe_only"
            result["matched"] = bool(audit_candidates)
            result["executed_count"] = 0
            result["candidate_action_count"] = len(audit_candidates)
            result["authorized_action_count"] = 0
            result["authorized_actions"] = []
            result["auto_execute"] = False
            result["confirm_required"] = False
            result["arbitration_result"] = "observe_only"
            result["execution_audit_pending"] = False
            result["execution_suppressed_reason"] = (
                "fast_path_execution_already_committed"
            )
            result["reason"] = "fast_path_execution_already_committed"
            result["final_outcome"] = final_outcome
            result["execution_status"] = final_outcome
            rollout_blocked_actions: list[dict[str, Any]] = []
            if transaction_id:
                execution_event_enqueued = self._enqueue_internal_event(
                    "decision_execution",
                    {
                        "transaction_id": transaction_id,
                        "trigger": str(trigger or ""),
                        "scene": scene,
                        "confidence": confidence,
                        "confidence_auto": result.get("confidence_auto"),
                        "confidence_notify": result.get("confidence_notify"),
                        "threshold": result.get("threshold"),
                        "auto_execute": False,
                        "confirm_required": False,
                        "arbitration_result": "observe_only",
                        "reason": "fast_path_execution_already_committed",
                        "planned_count": len(candidate_actions),
                        "candidate_action_count": len(candidate_actions),
                        "authorized_action_count": 0,
                        "executed_count": 0,
                        "final_outcome": final_outcome,
                        "actions": [],
                        "candidate_actions": candidate_actions,
                        "authorized_actions": [],
                        "rollout_blocked_actions": [],
                        "action_results": [],
                        "training_sample": None,
                        "source": "ha_slow_fast_path_audit",
                        "origin": "smartagent",
                        "actor": "smartagent:ha_slow_fast_path_audit",
                        "decision_id": decision_id,
                        "execution_transaction_id": "",
                        "parent_execution_transaction_id": str(
                            bundle.get("parent_execution_transaction_id") or ""
                        ),
                        "world_snapshot_id": world_snapshot_id,
                        "lineage": decision_lineage,
                    },
                )
                if not execution_event_enqueued:
                    self._sys_log(
                        "WARN",
                        "[Decision] fast-path audit decision_execution enqueue failed "
                        f"transaction_id={transaction_id}",
                    )
        else:
            rollout_blocked_actions = []

        if valid_actions:
            rollout_payload = (
                result.get("active_ai_rollout")
                if isinstance(result.get("active_ai_rollout"), dict)
                else {}
            )
            rollout_config = ActiveAiRolloutConfig.from_mapping(rollout_payload)
            execution_flags = (
                rollout_payload.get("execution_flags")
                if isinstance(rollout_payload.get("execution_flags"), dict)
                else {}
            )
            rollout_actions = enrich_active_ai_action_spaces(
                valid_actions,
                bundle.get("device_info")
                if isinstance(bundle.get("device_info"), dict)
                else {},
            )
            scoped_actions = (
                None
                if explicit_voice_control
                else scope_active_ai_canary_actions(
                    rollout_actions,
                    rollout_config,
                )
            )
            blocked_entity_ids = (
                set()
                if scoped_actions is None
                else set(scoped_actions.blocked_entity_ids)
            )
            if (
                scoped_actions is not None
                and not scoped_actions.entity_missing
                and blocked_entity_ids
            ):
                valid_actions = [
                    action
                    for action in valid_actions
                    if str(
                        action.get("entity_id")
                        or action.get("entity")
                        or (
                            action.get("target", {}).get("entity_id")
                            if isinstance(action.get("target"), dict)
                            else ""
                        )
                        or ""
                    ).strip().lower()
                    not in blocked_entity_ids
                ]
                rollout_actions = enrich_active_ai_action_spaces(
                    valid_actions,
                    bundle.get("device_info")
                    if isinstance(bundle.get("device_info"), dict)
                    else {},
                )
            rollout_blocked_actions = []
            for action in candidate_actions:
                action_entity_id = str(
                    action.get("entity_id")
                    or action.get("entity")
                    or (
                        action.get("target", {}).get("entity_id")
                        if isinstance(action.get("target"), dict)
                        else ""
                    )
                    or ""
                ).strip().lower()
                if action_entity_id not in blocked_entity_ids:
                    continue
                rollout_blocked_actions.append(
                    {
                        **action,
                        "status": "blocked_by_rollout",
                        "reason": "active_ai_canary_entity_not_allowed",
                    }
                )
            result["candidate_action_count"] = len(candidate_actions)
            result["authorized_action_count"] = len(valid_actions)
            result["authorized_actions"] = list(valid_actions)
            result["rollout_blocked_actions"] = rollout_blocked_actions
            active_execution_space_id = str(
                bundle.get("trigger_space_id")
                or result.get("trigger_space_id")
                or bundle.get("trigger_room")
                or result.get("trigger_room")
                or ""
            ).strip()
            if not active_execution_space_id and explicit_voice_control:
                action_space_ids = {
                    str(
                        action.get("target_space_id")
                        or action.get("space_id")
                        or ""
                    ).strip()
                    for action in rollout_actions
                    if isinstance(action, dict)
                }
                if "" not in action_space_ids and len(action_space_ids) == 1:
                    active_execution_space_id = next(iter(action_space_ids))
            if explicit_voice_control:
                action_domains = sorted(
                    {
                        str(action.get("domain") or "").strip().lower()
                        for action in rollout_actions
                        if isinstance(action, dict) and str(action.get("domain") or "").strip()
                    }
                )
                action_space_ids = sorted(
                    {
                        str(action.get("target_space_id") or action.get("space_id") or "").strip()
                        for action in rollout_actions
                        if isinstance(action, dict)
                        and str(action.get("target_space_id") or action.get("space_id") or "").strip()
                    }
                )
                action_entity_ids = sorted(
                    {
                        str(action.get("entity_id") or action.get("entity") or "").strip().lower()
                        for action in rollout_actions
                        if isinstance(action, dict)
                        and str(action.get("entity_id") or action.get("entity") or "").strip()
                    }
                )
                rollout_reason = "user_explicit_rollout_bypass"
                rollout_allow_execution = True
                rollout_trace = {
                    "mode": rollout_config.mode,
                    "allow_model": True,
                    "allow_execution": True,
                    "reason": rollout_reason,
                    "trigger_space_id": active_execution_space_id,
                    "action_domains": action_domains,
                    "blocked_domains": [],
                    "action_space_ids": action_space_ids,
                    "blocked_space_ids": [],
                    "action_entity_ids": action_entity_ids,
                    "blocked_entity_ids": [],
                    "bypass_scope": "authenticated_user_explicit_voice",
                }
            else:
                rollout_decision = evaluate_active_ai_execution_gate(
                    ai_enabled=bool(getattr(self, "_enabled", False)),
                    config=rollout_config,
                    trigger_space_id=active_execution_space_id,
                    actions=rollout_actions,
                    execution_flags=execution_flags,
                )
                rollout_trace = rollout_decision.as_trace()
                rollout_reason = rollout_decision.reason
                rollout_allow_execution = rollout_decision.allow_execution
                if blocked_entity_ids and not valid_actions:
                    rollout_reason = "active_ai_canary_entity_not_allowed"
                    rollout_trace["reason"] = rollout_reason
                    rollout_trace["blocked_entity_ids"] = sorted(blocked_entity_ids)
            if source == "patrol_reconciliation":
                proactive_shadow = (
                    result.get("proactive_shadow")
                    if isinstance(result.get("proactive_shadow"), dict)
                    else {}
                )
                proactive_runtime = (
                    proactive_shadow.get("runtime_materialization")
                    if isinstance(proactive_shadow.get("runtime_materialization"), dict)
                    else proactive_shadow
                )
                if proactive_runtime.get("execution_permitted") is not True:
                    rollout_reason = "proactive_execution_not_permitted"
                    rollout_allow_execution = False
                    rollout_trace["allow_execution"] = False
                    rollout_trace["reason"] = rollout_reason
                    rollout_trace["proactive_execution_permitted"] = False
            result["rollout"] = rollout_trace
            result["rollout_reason"] = rollout_reason
            if not rollout_allow_execution:
                is_shadow = rollout_reason in {
                    "active_ai_shadow",
                    "proactive_execution_not_permitted",
                }
                final_outcome = "observe_only" if is_shadow else "blocked"
                action_status = "not_executed" if is_shadow else "blocked"
                public_reason = _rollout_public_reason(rollout_reason)
                result["matched"] = True
                result["executed_count"] = 0
                result["auto_execute"] = False
                result["confirm_required"] = False
                result["arbitration_result"] = "blocked_by_rollout"
                result["execution_suppressed_reason"] = public_reason
                result["final_outcome"] = final_outcome
                result["execution_status"] = final_outcome
                action_results = [
                    {
                        "domain": str(action.get("domain") or ""),
                        "service": str(action.get("service") or ""),
                        "entity_id": str(action.get("entity_id") or ""),
                        "status": action_status,
                        "reason": rollout_reason,
                    }
                    for action in valid_actions
                ]
                if transaction_id:
                    execution_event_enqueued = self._enqueue_internal_event(
                        "decision_execution",
                        {
                            "transaction_id": transaction_id,
                            "trigger": str(trigger or ""),
                            "scene": scene,
                            "confidence": confidence,
                            "confidence_auto": result.get("confidence_auto"),
                            "confidence_notify": result.get("confidence_notify"),
                            "threshold": result.get("threshold"),
                            "auto_execute": False,
                            "confirm_required": False,
                            "arbitration_result": "blocked_by_rollout",
                            "reason": rollout_reason,
                            "planned_count": len(valid_actions),
                            "candidate_action_count": len(candidate_actions),
                            "authorized_action_count": len(valid_actions),
                            "executed_count": 0,
                            "final_outcome": final_outcome,
                            "actions": valid_actions,
                            "candidate_actions": candidate_actions,
                            "authorized_actions": valid_actions,
                            "rollout_blocked_actions": rollout_blocked_actions,
                            "action_results": [
                                *action_results,
                                *rollout_blocked_actions,
                            ],
                            "training_sample": None,
                            "source": "ha_slow_decision",
                            "origin": "smartagent",
                            "actor": "smartagent:ha_slow_decision",
                            "decision_id": decision_id,
                            "world_snapshot_id": world_snapshot_id,
                            "lineage": decision_lineage,
                            "rollout": rollout_trace,
                        },
                    )
                    if not execution_event_enqueued:
                        self._sys_log(
                            "WARN",
                            "[Decision] rollout decision_execution enqueue failed "
                            f"transaction_id={transaction_id}",
                        )
                self._sys_log(
                    "INFO",
                    "[Decision] active-AI rollout blocked execution "
                    f"mode={rollout_config.mode} "
                    f"reason={rollout_reason} "
                    f"transaction_id={transaction_id or '-'}",
                )
                _emit_slow_decision_bubble(
                    result_payload=result,
                    status_code=status,
                    matched=True,
                    reason=public_reason,
                    scene_desc=scene,
                    confidence_value=confidence,
                    actions_payload=valid_actions,
                    transaction_id_value=transaction_id,
                    executed_count=0,
                    final_outcome_value=final_outcome,
                    fail_closed=not is_shadow,
                    record_decision_log=not bool(transaction_id),
                )
                nested = (
                    result.get("result")
                    if isinstance(result.get("result"), dict)
                    else {}
                )
                if bundle.get("is_voice"):
                    result["reply"] = policy_unauthorized_speech
                    result["speak"] = policy_unauthorized_speech
                else:
                    result.setdefault("reply", nested.get("reply") or public_reason)
                result.setdefault("status", "ok")
                return result

            apply_arrival_lighting_confirmation_gate(
                result,
                actions=valid_actions,
                context_snapshot=bundle,
            )

            arbitration_result = str(
                result.get("arbitration_result") or ""
            ).strip()
            confidence_gate = evaluate_slow_brain_confidence_gate(
                confidence=result.get("confidence"),
                threshold=self.confidence_auto,
            )
            arbitration_validation = validate_auto_execution_arbitration(
                result if confidence_gate.log_code != "confidence_invalid" else {},
                context_snapshot=bundle,
            )
            local_confidence_block = not confidence_gate.allowed
            auto_execute = arbitration_validation.allowed and confidence_gate.allowed
            confirm_required = pending_confirmation_allowed(
                arbitration_validation.reason,
                local_confidence_block=local_confidence_block,
                payload=result,
            )
            if not auto_execute:
                decision_reason = str(result.get("reason") or "").strip()
                if local_confidence_block:
                    suppressed_reason = confidence_gate.log_code or "confidence_invalid"
                elif arbitration_validation.reason in {
                    "confidence_arbitration_missing",
                    "confidence_arbitration_invalid",
                }:
                    suppressed_reason = arbitration_validation.reason
                    if decision_reason and decision_reason != suppressed_reason:
                        result.setdefault("decision_reason", decision_reason)
                else:
                    suppressed_reason = arbitration_validation.reason
                public_reason = (
                    "置信度未达到自动执行阈值"
                    if local_confidence_block
                    else suppressed_reason
                )
                if local_confidence_block:
                    final_outcome = "blocked"
                elif confirm_required:
                    final_outcome = "pending_confirmation"
                else:
                    final_outcome = "observe_only"
                result["matched"] = True
                result["executed_count"] = 0
                result["execution_suppressed_reason"] = public_reason
                result["final_outcome"] = final_outcome
                result["execution_status"] = final_outcome
                if local_confidence_block:
                    result["confidence_auto"] = self.confidence_auto
                    result["threshold"] = self.confidence_auto
                    result["auto_execute"] = False
                    result["confirm_required"] = False
                    result["arbitration_result"] = "blocked"
                    result["reason"] = public_reason
                    arbitration_result = "blocked"
                action_results = [
                    {
                        "domain": str(action.get("domain") or ""),
                        "service": str(action.get("service") or ""),
                        "entity_id": str(action.get("entity_id") or ""),
                        "status": (
                            "blocked" if local_confidence_block else "not_executed"
                        ),
                        "reason": suppressed_reason,
                    }
                    for action in valid_actions
                ]
                if transaction_id:
                    execution_event_enqueued = self._enqueue_internal_event(
                        "decision_execution",
                        {
                            "transaction_id": transaction_id,
                            "trigger": str(trigger or ""),
                            "scene": scene,
                            "confidence": confidence,
                            "confidence_auto": result.get("confidence_auto"),
                            "confidence_notify": result.get("confidence_notify"),
                            "threshold": result.get("threshold"),
                            "auto_execute": False,
                            "confirm_required": confirm_required,
                            "arbitration_result": arbitration_result or "missing",
                            "reason": suppressed_reason,
                            "planned_count": len(valid_actions),
                            "candidate_action_count": len(candidate_actions),
                            "authorized_action_count": len(valid_actions),
                            "executed_count": 0,
                            "final_outcome": final_outcome,
                            "actions": valid_actions,
                            "candidate_actions": candidate_actions,
                            "authorized_actions": valid_actions,
                            "rollout_blocked_actions": rollout_blocked_actions,
                            "action_results": [
                                *action_results,
                                *rollout_blocked_actions,
                            ],
                            "training_sample": None,
                            "source": "ha_slow_decision",
                            "origin": "smartagent",
                            "actor": "smartagent:ha_slow_decision",
                            "decision_id": decision_id,
                            "world_snapshot_id": world_snapshot_id,
                            "lineage": decision_lineage,
                        },
                    )
                    if not execution_event_enqueued:
                        self._sys_log(
                            "WARN",
                            "[Decision] decision_execution enqueue failed "
                            f"transaction_id={transaction_id}",
                        )
                if confirm_required:
                    try:
                        self.hass.bus.async_fire(
                            "smart_agent_confirm_required",
                            {
                                "source": "ha_slow_decision",
                                "trigger": trigger_public_summary,
                                "scene": scene,
                                "confidence": confidence,
                                "confidence_auto": result.get("confidence_auto"),
                                "confidence_notify": result.get("confidence_notify"),
                                "threshold": result.get("threshold"),
                                "arbitration_result": arbitration_result,
                                "confirm_required": True,
                                "reason": suppressed_reason,
                                "actions": valid_actions,
                                "action_count": len(valid_actions),
                                "transaction_id": transaction_id,
                                "result": result,
                            },
                        )
                    except Exception as exc:
                        _LOGGER.debug("[Coordinator] slow confirmation emit failed: %s", exc)
                self._sys_log(
                    "INFO",
                    f"[决策] 置信度仲裁禁止自动执行 result={arbitration_result or 'missing'} "
                    f"confidence={confidence} threshold={result.get('threshold')} reason={suppressed_reason}",
                )
                _emit_slow_decision_bubble(
                    result_payload=result,
                    status_code=status,
                    matched=True,
                    reason=public_reason,
                    scene_desc=scene,
                    confidence_value=confidence,
                    actions_payload=valid_actions,
                    transaction_id_value=transaction_id,
                    executed_count=0,
                    final_outcome_value=final_outcome,
                    fail_closed=(
                        confidence_gate.log_code == "confidence_invalid"
                        if local_confidence_block
                        else arbitration_validation.reason in {
                            "confidence_arbitration_missing",
                            "confidence_arbitration_invalid",
                        }
                    ),
                    record_decision_log=not bool(transaction_id),
                )
                nested = result.get("result") if isinstance(result.get("result"), dict) else {}
                if local_confidence_block:
                    result["reply"] = (
                        policy_unauthorized_speech
                        if bundle.get("is_voice")
                        else public_reason
                    )
                    if bundle.get("is_voice"):
                        result["speak"] = policy_unauthorized_speech
                else:
                    result.setdefault(
                        "reply",
                        nested.get("reply")
                        or ("等待用户确认" if confirm_required else "置信度不足，仅记录未执行"),
                    )
                result.setdefault("status", "ok")
                return result
            if learning_observe_only:
                result["matched"] = True
                result["executed_count"] = 0
                result["execution_suppressed_reason"] = "learning_mode"
                result.setdefault("reason", "learning_mode_observe_only")
                final_outcome = "observe_only"
                result["final_outcome"] = final_outcome
                result["execution_status"] = final_outcome
                action_results = []
                for action in valid_actions:
                    if not isinstance(action, dict):
                        continue
                    action_results.append(
                        {
                            "domain": str(action.get("domain") or ""),
                            "service": str(action.get("service") or ""),
                            "entity_id": str(action.get("entity_id") or ""),
                            "status": "not_executed",
                            "reason": "learning_mode_observe_only",
                        }
                    )
                if transaction_id:
                    execution_event_enqueued = self._enqueue_internal_event(
                        "decision_execution",
                        {
                            "transaction_id": transaction_id,
                            "trigger": str(trigger or ""),
                            "scene": scene,
                            "confidence": confidence,
                            "confidence_auto": result.get("confidence_auto"),
                            "confidence_notify": result.get("confidence_notify"),
                            "threshold": result.get("threshold"),
                            "auto_execute": False,
                            "confirm_required": False,
                            "arbitration_result": "observe_only",
                            "reason": "learning_mode_observe_only",
                            "planned_count": len(valid_actions),
                            "candidate_action_count": len(candidate_actions),
                            "authorized_action_count": len(valid_actions),
                            "executed_count": 0,
                            "final_outcome": final_outcome,
                            "actions": valid_actions,
                            "candidate_actions": candidate_actions,
                            "authorized_actions": valid_actions,
                            "rollout_blocked_actions": rollout_blocked_actions,
                            "action_results": [
                                *action_results,
                                *rollout_blocked_actions,
                            ],
                            "training_sample": None,
                            "source": "ha_slow_decision",
                            "origin": "smartagent",
                            "actor": "smartagent:ha_slow_decision",
                            "decision_id": decision_id,
                            "world_snapshot_id": world_snapshot_id,
                            "lineage": decision_lineage,
                        },
                    )
                    if not execution_event_enqueued:
                        self._sys_log(
                            "WARN",
                            f"[Decision] decision_execution enqueue failed transaction_id={transaction_id}",
                        )
                self._sys_log(
                    "INFO",
                    f"[Decision] learning observe-only: received {len(valid_actions)} action(s), executed 0",
                )
                _emit_slow_decision_bubble(
                    result_payload=result,
                    status_code=status,
                    matched=True,
                    reason=str(result.get("reason") or "learning_mode_observe_only"),
                    scene_desc=scene,
                    confidence_value=confidence,
                    actions_payload=valid_actions,
                    transaction_id_value=transaction_id,
                    executed_count=0,
                    final_outcome_value=final_outcome,
                    fail_closed=False,
                    record_decision_log=not bool(transaction_id),
                )
                nested = result.get("result") if isinstance(result.get("result"), dict) else {}
                result.setdefault("reply", nested.get("reply") or "learning_mode_observe_only")
                result.setdefault("status", "ok")
                return result
            response_details = result.get("details") if isinstance(result.get("details"), dict) else {}
            execution_correlation_id = str(
                result.get("correlation_id")
                or response_details.get("correlation_id")
                or bundle.get("parent_correlation_id")
                or ""
            ).strip()
            execution_result = await self._execute_actions(
                valid_actions,
                trigger_summary=str(trigger or ""),
                scene_desc=scene,
                confidence=confidence,
                trigger_room=str(bundle.get("trigger_room") or result.get("trigger_room") or ""),
                parent_transaction_id=transaction_id,
                cmd_source=str(bundle.get("cmd_source") or result.get("cmd_source") or ""),
                world_snapshot_id=world_snapshot_id,
                correlation_id=execution_correlation_id,
                active_space_id=active_execution_space_id,
                decision_time=str(
                    result.get("decision_time")
                    or (
                        result.get("result", {}).get("decision_time")
                        if isinstance(result.get("result"), dict)
                        else ""
                    )
                    or ""
                ).strip(),
                require_world_snapshot_guard=True,
                # Canonical decisions already carry the exact Core-selected
                # entity/service/parameters.  The HA host must not reinterpret
                # them through the legacy name-based scene/script router.
                direct_entity_only=True,
                decision_contract_lineage=decision_lineage,
                user_intent_authority=user_intent_authority,
            )
            executed = int(execution_result)
            execution_transaction_id = str(
                getattr(execution_result, "transaction_id", "") or "unknown"
            ).strip() or "unknown"
            result["executed_count"] = executed
            final_outcome = (
                "succeeded"
                if executed >= len(valid_actions)
                else "partial"
                if executed > 0
                else "failed"
            )
            raw_action_results = getattr(execution_result, "action_results", None)
            action_results = list(raw_action_results) if isinstance(raw_action_results, list) else []
            for index, action in enumerate(valid_actions):
                if not isinstance(action, dict):
                    continue
                params = action.get("params")
                action_reason = str(action.get("reason") or "").strip()
                if index < len(action_results) and isinstance(action_results[index], dict):
                    merged = {
                        **action_results[index],
                        "domain": str(action_results[index].get("domain") or action.get("domain") or ""),
                        "service": str(action_results[index].get("service") or action.get("service") or ""),
                        "entity_id": str(action_results[index].get("entity_id") or action.get("entity_id") or ""),
                    }
                    if isinstance(params, dict) and params and not isinstance(merged.get("params"), dict):
                        merged["params"] = dict(params)
                    if action_reason and not str(merged.get("action_reason") or "").strip():
                        merged["action_reason"] = action_reason
                    if execution_correlation_id:
                        merged["correlation_id"] = execution_correlation_id
                    action_results[index] = merged
                    continue
                fallback_result = {
                    "domain": str(action.get("domain") or ""),
                    "service": str(action.get("service") or ""),
                    "entity_id": str(action.get("entity_id") or ""),
                    "status": "executed" if index < executed else "not_executed",
                    "reason": "ha_execute_actions_missing_structured_result",
                }
                if isinstance(params, dict) and params:
                    fallback_result["params"] = dict(params)
                if action_reason:
                    fallback_result["action_reason"] = action_reason
                if execution_correlation_id:
                    fallback_result["correlation_id"] = execution_correlation_id
                action_results.append(fallback_result)
            audit_action_results = [
                dict(item)
                for item in [*action_results, *rollout_blocked_actions]
                if isinstance(item, dict)
            ]
            training_sample_payload = self._build_training_sample_payload(
                bundle=bundle,
                actions=valid_actions,
                confidence=confidence,
                final_outcome=final_outcome,
                decision_id=decision_id,
                transaction_id=transaction_id,
                execution_transaction_id=execution_transaction_id,
                world_snapshot_id=world_snapshot_id,
                planned_count=len(valid_actions),
                executed_count=executed,
                action_results=action_results,
            )
            if transaction_id:
                execution_event_enqueued = self._enqueue_internal_event(
                    "decision_execution",
                    {
                        "transaction_id": transaction_id,
                        "trigger": str(trigger or ""),
                        "scene": scene,
                        "confidence": confidence,
                        "confidence_auto": result.get("confidence_auto"),
                        "confidence_notify": result.get("confidence_notify"),
                        "threshold": result.get("threshold"),
                        "auto_execute": True,
                        "confirm_required": False,
                        "arbitration_result": arbitration_result,
                        "reason": str(result.get("reason") or "confidence_threshold_met"),
                        "planned_count": len(valid_actions),
                        "candidate_action_count": len(candidate_actions),
                        "authorized_action_count": len(valid_actions),
                        "executed_count": executed,
                        "final_outcome": final_outcome,
                        "actions": valid_actions,
                        "candidate_actions": candidate_actions,
                        "authorized_actions": valid_actions,
                        "rollout_blocked_actions": rollout_blocked_actions,
                        "action_results": audit_action_results,
                        "training_sample": training_sample_payload,
                        "source": "ha_slow_decision",
                        "origin": "smartagent",
                        "actor": "smartagent:ha_slow_decision",
                        "decision_id": decision_id,
                        "execution_transaction_id": execution_transaction_id,
                        "world_snapshot_id": world_snapshot_id,
                        "correlation_id": execution_correlation_id,
                        "lineage": decision_lineage,
                    },
                )
                if not execution_event_enqueued:
                    self._sys_log(
                        "WARN",
                        f"[决策] decision_execution 回写入队失败 transaction_id={transaction_id}",
                    )
            self._sys_log("INFO", f"[决策] add-on 返回 {len(valid_actions)} 个动作，已执行 {executed} 个")
        else:
            self._sys_log("INFO", f"[决策] add-on 未返回可执行动作: {result.get('reason') or 'no_actions'}")
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
        nested = result.get("result") if isinstance(result.get("result"), dict) else {}
        desired_states = result.get("desired_states")
        if not isinstance(desired_states, list):
            desired_states = nested.get("desired_states") if isinstance(nested.get("desired_states"), list) else []
        reply_text = next(
            (
                str(value).strip()
                for value in (
                    result.get("reply"),
                    result.get("speak"),
                    nested.get("reply"),
                    nested.get("speak"),
                )
                if str(value or "").strip()
            ),
            "",
        )
        policy_rejected_action = any(
            str(item.get("error_type") or "").strip().lower() == "policy_rejected"
            or str(item.get("error") or item.get("reason") or "")
            .strip()
            .lower()
            .startswith(("active_ai_", "policy_"))
            for item in action_results
            if isinstance(item, dict)
        )
        policy_rejected_result = bool(
            str(result.get("error_type") or "").strip().lower() == "policy_rejected"
            or str(result.get("rollout_reason") or "")
            .strip()
            .lower()
            .startswith(("active_ai_", "policy_"))
            and str(result.get("final_outcome") or final_outcome).strip().lower()
            in {"blocked", "observe_only"}
        )
        if bundle.get("is_voice") and (policy_rejected_action or policy_rejected_result):
            reply_text = policy_unauthorized_speech
        elif bundle.get("is_voice") and desired_states:
            if not valid_actions:
                reply_text = (
                    "目标设备已经处于所需状态。"
                    if str(result.get("reason") or "") == "desired_state_already_satisfied"
                    else "已理解语音控制指令，但没有生成可安全执行的设备动作。"
                )
            elif executed < len(valid_actions):
                reply_text = (
                    "语音控制只执行了部分设备动作，请检查设备状态。"
                    if executed > 0
                    else "语音控制未实际执行成功，请检查设备状态。"
                )
        if not reply_text:
            if bundle.get("is_voice") and not valid_actions:
                reply_text = (
                    "已理解语音控制指令，但没有生成可安全执行的设备动作。"
                    if desired_states
                    else "查询已完成，但没有可播报的结果。"
                )
            else:
                reply_text = "已处理" if valid_actions else "未命中可执行动作"
        result["reply"] = reply_text
        if bundle.get("is_voice") and desired_states:
            result["speak"] = reply_text
        elif bundle.get("is_voice") and not str(result.get("speak") or "").strip():
            result["speak"] = reply_text
        result.setdefault("status", "ok")
        return result

__all__ = [
    "build_patrol_environment_projection",
    "build_patrol_task_occurrence",
    "run_addon_decision",
    "scope_patrol_snapshot_projection",
]
