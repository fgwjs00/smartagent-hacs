"""Slow-decision admission and provider response handling; caller owns lock lifetime."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any
from .active_ai_rollout import (
    ActiveAiRolloutConfig,
    DEFAULT_ACTIVE_AI_MODE,
    evaluate_active_ai_model_gate,
)
from .decision_presentation import SlowDecisionEmitter, rollout_public_reason


def _provider_failure_scene(result: dict[str, Any], error: Any) -> str:
    result_details = result.get("details") if isinstance(result.get("details"), dict) else {}
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
    return failure_scene


@dataclass(frozen=True, slots=True)
class DecisionProviderResponse:
    payload: dict[str, Any]
    status: int
    terminal: bool


@dataclass(frozen=True, slots=True)
class SlowDecisionProvider:
    host: Any
    bundle: dict[str, Any]
    client: Any
    trigger: str
    explicit_voice_control: bool
    emitter: SlowDecisionEmitter
    policy_unauthorized_speech: str

    def _model_gate(self) -> dict[str, Any] | None:
        host = self.host
        bundle = self.bundle
        explicit_voice_control = self.explicit_voice_control
        policy_unauthorized_speech = self.policy_unauthorized_speech
        _emit_slow_decision_bubble = self.emitter.emit
        pre_rollout_config = ActiveAiRolloutConfig.from_values(
            mode=getattr(host, "_active_ai_mode", DEFAULT_ACTIVE_AI_MODE)
        )
        pre_rollout = evaluate_active_ai_model_gate(
            ai_enabled=bool(getattr(host, "_enabled", False)),
            config=pre_rollout_config,
        )
        if not pre_rollout.allow_model and not explicit_voice_control:
            public_reason = rollout_public_reason(pre_rollout.reason)
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

        return None

    def _availability(self) -> dict[str, Any] | None:
        host = self.host
        addon_client = self.client
        _emit_slow_decision_bubble = self.emitter.emit
        if addon_client is None:
            host._sys_log("WARN", "[决策] add-on decision provider unavailable")
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

        return None

    def _device_table(self) -> dict[str, Any] | None:
        host = self.host
        bundle = self.bundle
        _emit_slow_decision_bubble = self.emitter.emit
        # ── 空设备表防裸推：无已同步设备时直接判无动作，避免模型在零设备上凭空幻觉 ──
        if not str(bundle.get("device_table") or "").strip():
            host._sys_log(
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
        return None

    def preflight(self) -> dict[str, Any] | None:
        for check in (self._model_gate, self._availability, self._device_table):
            rejection = check()
            if rejection is not None:
                return rejection
        return None

    def inference_lock(self) -> Any:
        host, bundle = self.host, self.bundle
        room_lock_key = str(bundle.get("trigger_room") or "").strip()
        inference_lock = (
            host._get_room_lock(room_lock_key)
            if room_lock_key
            else getattr(host, "_inference_lock", None)
        )
        if inference_lock is None:
            host._inference_lock = asyncio.Lock()
            inference_lock = host._inference_lock
        if hasattr(inference_lock, "locked") and inference_lock.locked():
            host._sys_log("INFO", f"[决策] 同空间推理进行中，等待: {room_lock_key or 'global'}")
        return inference_lock

    async def fetch(self) -> DecisionProviderResponse:
        host = self.host
        bundle = self.bundle
        addon_client = self.client
        explicit_voice_control = self.explicit_voice_control
        _emit_slow_decision_bubble = self.emitter.emit
        try:
            result = await addon_client.run_decision(
                trigger=str(self.trigger or ""),
                bundle=bundle,
                request_id=str(bundle.get("parent_correlation_id") or "") or None,
                user_explicit_voice=explicit_voice_control,
            )
        except Exception as exc:
            host._sys_log("WARN", f"[决策] add-on decision provider 调用失败: {exc}")
            _emit_slow_decision_bubble(
                status_code=502,
                matched=False,
                reason="addon_decision_provider_error",
                scene_desc="线上大模型调用失败",
                final_outcome_value="failed",
                fail_closed=True,
                record_decision_log=True,
            )
            return DecisionProviderResponse({"status": "error", "message": str(exc)}, 502, True)
        if not isinstance(result, dict):
            host._sys_log("WARN", "[决策] add-on decision provider 无响应")
            _emit_slow_decision_bubble(
                status_code=502,
                matched=False,
                reason="addon_decision_provider_unavailable",
                scene_desc="线上大模型无响应",
                final_outcome_value="failed",
                fail_closed=True,
                record_decision_log=True,
            )
            return DecisionProviderResponse(
                {"status": "error", "message": "add-on decision provider unavailable"}, 502, True
            )
        status = int(result.get("__status", 200) or 200)
        if status >= 400 or result.get("ok") is False:
            return DecisionProviderResponse(self._rejected(result, status), status, True)
        return DecisionProviderResponse(result, status, False)

    def _rejected(self, result: dict[str, Any], status: int) -> dict[str, Any]:
        host = self.host
        bundle = self.bundle
        policy_unauthorized_speech = self.policy_unauthorized_speech
        _emit_slow_decision_bubble = self.emitter.emit
        error = result.get("error") or result.get("error_type") or f"http_{status}"
        failure_scene = _provider_failure_scene(result, error)
        policy_rejected = bool(
            str(result.get("error_type") or "").strip().lower() == "policy_rejected"
            or str(error or "").strip().lower().startswith(("active_ai_", "policy_"))
        )
        host._sys_log("WARN", f"[决策] add-on decision provider 返回失败: {error}")
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
            policy_unauthorized_speech if bundle.get("is_voice") and policy_rejected else str(error)
        )
        if bundle.get("is_voice") and policy_rejected:
            error_response["reply"] = policy_unauthorized_speech
            error_response["speak"] = policy_unauthorized_speech
        return error_response
