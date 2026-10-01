"""Decision presentation with explicit per-request state and separate event/log I/O."""

from __future__ import annotations
from dataclasses import dataclass
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def decision_transaction_id(result_payload: dict[str, Any], preferred: str = "") -> str:
    return str(
        preferred
        or result_payload.get("transaction_id")
        or result_payload.get("decision_id")
        or result_payload.get("id")
        or ""
    ).strip()


def rollout_public_reason(reason: str) -> str:
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


@dataclass(frozen=True, slots=True)
class SlowDecisionNotice:
    result: dict[str, Any]
    status: int
    matched: bool
    path: str
    reason: str
    scene: str
    confidence: int
    actions: list[dict[str, Any]]
    transaction_id: str
    executed_count: int
    final_outcome: str
    fail_closed: bool


def _event_payload(
    bundle: dict[str, Any], trigger_public_summary: str, notice: SlowDecisionNotice
) -> dict[str, Any]:
    event_payload = {
        "source": "ha_slow_decision",
        "entity_id": str(bundle.get("trigger_entity_id") or ""),
        "trigger_entity_id": str(bundle.get("trigger_entity_id") or ""),
        "old_state": str(bundle.get("old_state") or ""),
        "new_state": str(bundle.get("new_state") or ""),
        "trigger": trigger_public_summary,
        "trigger_summary": trigger_public_summary,
        "status": notice.status,
        "matched": notice.matched,
        "path_taken": notice.path,
        "reason": notice.reason,
        "scene": notice.scene,
        "confidence": notice.confidence,
        "confidence_auto": notice.result.get("confidence_auto"),
        "confidence_notify": notice.result.get("confidence_notify"),
        "threshold": notice.result.get("threshold"),
        "auto_execute": notice.result.get("auto_execute") is True,
        "confirm_required": notice.result.get("confirm_required") is True,
        "arbitration_result": str(notice.result.get("arbitration_result") or ""),
        "action_count": len(notice.actions),
        "actions": notice.actions,
        "transaction_id": notice.transaction_id,
        "parent_transaction_id": str(bundle.get("parent_transaction_id") or ""),
        "parent_decision_trace": (
            bundle.get("parent_decision_trace")
            if isinstance(bundle.get("parent_decision_trace"), dict)
            else {}
        ),
        "source_trace_context": (
            bundle.get("source_trace_context")
            if isinstance(bundle.get("source_trace_context"), dict)
            else {}
        ),
        "parent_correlation_id": str(bundle.get("parent_correlation_id") or ""),
        "parent_world_snapshot_id": str(bundle.get("parent_world_snapshot_id") or ""),
        "executed": bool(notice.actions and notice.final_outcome == "succeeded" and notice.executed_count >= len(notice.actions)),
        "executed_count": notice.executed_count,
        "final_outcome": notice.final_outcome,
        "fail_closed": notice.fail_closed,
    }
    return event_payload


@dataclass(frozen=True, slots=True)
class SlowDecisionEmitter:
    host: Any
    bundle: dict[str, Any]
    trigger_public_summary: str

    def emit(
        self,
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
        host, bundle, trigger_public_summary = self.host, self.bundle, self.trigger_public_summary
        result_payload = result_payload if isinstance(result_payload, dict) else {}
        actions_payload = actions_payload if isinstance(actions_payload, list) else []
        transaction_id_value = decision_transaction_id(result_payload, transaction_id_value)
        result_details = (
            result_payload.get("details") if isinstance(result_payload.get("details"), dict) else {}
        )
        path_taken = str(
            result_details.get("path_taken") or result_payload.get("path_taken") or "llm"
        )
        reason_value = str(
            reason or result_payload.get("reason") or ("matched" if matched else "no_actions")
        )
        scene_value = str(scene_desc or result_payload.get("scene") or "")
        notice = SlowDecisionNotice(
            result_payload,
            status_code,
            matched,
            path_taken,
            reason_value,
            scene_value,
            confidence_value,
            actions_payload,
            transaction_id_value,
            executed_count,
            final_outcome_value,
            fail_closed,
        )
        event_payload = _event_payload(bundle, trigger_public_summary, notice)
        try:
            host.hass.bus.async_fire("smart_agent_decision_bubble", event_payload)
        except Exception as exc:
            _LOGGER.debug("[Coordinator] slow decision bubble emit failed: %s", exc)
        if record_decision_log:
            self._record_log(notice)

    def _record_log(self, notice: SlowDecisionNotice) -> None:
        host, trigger_public_summary = self.host, self.trigger_public_summary
        log_result = dict(notice.result)
        log_result.setdefault("source", "ha_slow_decision")
        log_result.setdefault("path_taken", notice.path)
        log_result.setdefault("reason", notice.reason)
        log_result.setdefault("scene", notice.scene)
        log_result.setdefault("actions", notice.actions)
        log_result["trigger"] = trigger_public_summary
        log_result["trigger_summary"] = trigger_public_summary
        log_result["matched"] = bool(notice.matched)
        log_result["final_outcome"] = notice.final_outcome
        log_result["fail_closed"] = bool(notice.fail_closed)
        log_payload: dict[str, Any] = {
            "trigger": trigger_public_summary,
            "trigger_summary": trigger_public_summary,
            "scene": notice.scene,
            "source": "ha_slow_decision",
            "path_taken": notice.path,
            "confidence": notice.confidence,
            "confidence_auto": notice.result.get("confidence_auto"),
            "confidence_notify": notice.result.get("confidence_notify"),
            "threshold": notice.result.get("threshold"),
            "auto_execute": notice.result.get("auto_execute") is True,
            "confirm_required": notice.result.get("confirm_required") is True,
            "arbitration_result": str(notice.result.get("arbitration_result") or ""),
            "matched": bool(notice.matched),
            "action_count": len(notice.actions),
            "reason": notice.reason,
            "actions": notice.actions,
            "result": log_result,
        }
        if notice.transaction_id:
            log_payload["id"] = notice.transaction_id
        enqueue = getattr(host, "_enqueue_internal_event", None)
        if not callable(enqueue) or not enqueue("decision_log", log_payload):
            host._sys_log(
                "WARN",
                f"[决策] decision_log 回写入队失败 reason={notice.reason or '-'} trigger={trigger_public_summary or '-'}",
            )


def _policy_rejected_action(action_results) -> bool:
    return any(
        str(item.get("error_type") or "").strip().lower() == "policy_rejected"
        or str(item.get("error") or item.get("reason") or "")
        .strip()
        .lower()
        .startswith(("active_ai_", "policy_"))
        for item in action_results
        if isinstance(item, dict)
    )


def _policy_rejected_result(result, final_outcome) -> bool:
    return bool(
        str(result.get("error_type") or "").strip().lower() == "policy_rejected"
        or str(result.get("rollout_reason") or "")
        .strip()
        .lower()
        .startswith(("active_ai_", "policy_"))
        and str(result.get("final_outcome") or final_outcome).strip().lower()
        in {"blocked", "observe_only"}
    )


def _initial_reply(result, nested) -> str:
    return next(
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


def _voice_reply(
    result,
    desired_states,
    valid_actions,
    executed,
    reply_text,
    policy_rejected_action,
    policy_rejected_result,
    policy_unauthorized_speech,
) -> str:
    if policy_rejected_action or policy_rejected_result:
        reply_text = policy_unauthorized_speech
    elif desired_states:
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
    return reply_text


def finalize_decision_reply(
    *,
    result: dict[str, Any],
    is_voice: Any,
    valid_actions: list[dict[str, Any]],
    executed: int,
    action_results: list[dict[str, Any]],
    final_outcome: str,
    policy_unauthorized_speech: str,
) -> None:
    nested = result.get("result") if isinstance(result.get("result"), dict) else {}
    desired_states = result.get("desired_states")
    if not isinstance(desired_states, list):
        desired_states = (
            nested.get("desired_states") if isinstance(nested.get("desired_states"), list) else []
        )
    reply_text = _initial_reply(result, nested)
    policy_rejected_action = _policy_rejected_action(action_results)
    policy_rejected_result = _policy_rejected_result(result, final_outcome)
    if is_voice:
        reply_text = _voice_reply(
            result,
            desired_states,
            valid_actions,
            executed,
            reply_text,
            policy_rejected_action,
            policy_rejected_result,
            policy_unauthorized_speech,
        )
    if final_outcome == "unknown" and valid_actions:
        reply_text = "设备动作的执行回执不完整，暂时无法确认结果，请检查设备状态。"
        if is_voice:
            result["speak"] = reply_text
    if not reply_text:
        if is_voice and not valid_actions:
            reply_text = (
                "已理解语音控制指令，但没有生成可安全执行的设备动作。"
                if desired_states
                else "查询已完成，但没有可播报的结果。"
            )
        else:
            reply_text = "已处理" if valid_actions else "未命中可执行动作"
    result["reply"] = reply_text
    if is_voice and desired_states:
        result["speak"] = reply_text
    elif is_voice and not str(result.get("speak") or "").strip():
        result["speak"] = reply_text
    result.setdefault("status", "ok")
