"""Per-action identity, immutable receipt inputs, and the portable thin gate."""

from __future__ import annotations
from typing import Any
from .action_execution_context import ActionBatchContext, ActionCall, ActionGuardOutcome, ActionItem
from .action_normalization import action_delay_seconds
from .execution_gate import evaluate_thin_execution_gate
from .service_contracts import EXECUTION_DOMAINS, STATELESS_DOMAINS


def _target_space(host: Any, entity_id: str, action: dict[str, Any], claim: Any) -> str:
    info = host.device_info.get(entity_id, {}) if isinstance(host.device_info, dict) else {}
    if not isinstance(info, dict):
        info = {}
    authoritative = str(
        info.get("space_id") or info.get("room_id") or info.get("area_id") or ""
    ).strip()
    return str(
        authoritative
        or action.get("target_space_id")
        or action.get("space_id")
        or (claim.get("space_id") if isinstance(claim, dict) else "")
        or info.get("space_id")
        or info.get("room_id")
        or info.get("area_id")
        or info.get("room")
        or info.get("area")
        or ""
    ).strip()


def _receipt_inputs(call: ActionCall, batch: ActionBatchContext) -> dict[str, Any]:
    result = {"domain": call.domain, "service": call.service, "entity_id": call.entity_id}
    if batch.correlation_id:
        result["correlation_id"] = batch.correlation_id
    if batch.parent_transaction_id:
        result["execution_transaction_id"] = batch.transaction_id
        result["parent_transaction_id"] = batch.parent_transaction_id
        result["decision_trace"] = {
            "available": True,
            "transaction_id": batch.parent_transaction_id,
            "url": f"/decision-trace/{batch.parent_transaction_id}",
        }
    if isinstance(call.params, dict) and call.params:
        result["params"] = dict(call.params)
    result.update(batch.receipt_metadata())
    if call.reason:
        result["reason"] = call.reason
    return result


def prepare_action_item(
    host: Any, batch: ActionBatchContext, action: dict[str, Any], position: int
) -> ActionItem:
    call = ActionCall(
        action.get("domain"),
        action.get("service"),
        action.get("entity_id"),
        action.get("params", {}),
        action.get("reason", ""),
    )
    claim = action.get("priority_override_claim")
    target = _target_space(host, call.entity_id, action, claim)
    receipt = _receipt_inputs(call, batch)
    delay = action_delay_seconds(action, action_seq=position + 1)
    return ActionItem(position, call, receipt, target, claim, delay)


def _log_thin_rejection(
    host: Any, code: str, call: ActionCall, raw_entity: Any, raw: Any, action: dict[str, Any]
) -> None:
    if code == "missing_required_action_fields":
        host._sys_log("WARN", f"[动作] 字段缺失，跳过: {raw} → 标准化后: {action}")
    elif code == "domain_not_allowed":
        host._sys_log(
            "WARN",
            f"[安全] 拒绝 AI 操作不在白名单中的域: {call.domain}.{call.service}({call.entity_id})",
        )
    elif code == "service_blocked":
        host._sys_log(
            "WARN", f"[安全] 拒绝 AI 执行危险服务: {call.domain}.{call.service}({call.entity_id})"
        )
    elif code == "raw_entity_not_found":
        host._sys_log(
            "WARN",
            f"[安全] 拒绝原始动作中不存在的实体（防幻觉）: {call.domain}.{call.service}({raw_entity})",
        )
    elif code == "entity_not_found":
        host._sys_log(
            "WARN",
            f"[安全] 拒绝操作不存在的实体（防幻觉）: {call.domain}.{call.service}({call.entity_id})",
        )


def evaluate_action_shape(
    host: Any, item: ActionItem, raw: Any, action: dict[str, Any]
) -> ActionGuardOutcome | None:
    call = item.call
    target = raw.get("target") if isinstance(raw, dict) else None
    raw_entity = (
        raw.get("entity_id")
        or raw.get("entity")
        or (target.get("entity_id") if isinstance(target, dict) else None)
    )
    raw_exists = True
    if isinstance(raw_entity, str) and "." in raw_entity and call.domain not in STATELESS_DOMAINS:
        raw_exists = host.hass.states.get(raw_entity) is not None
    exists = True
    if isinstance(call.entity_id, str) and call.domain not in STATELESS_DOMAINS:
        exists = host.hass.states.get(call.entity_id) is not None
    thin_gate = evaluate_thin_execution_gate(
        domain=call.domain,
        service=call.service,
        entity_id=call.entity_id,
        raw_entity_id=raw_entity,
        entity_exists=exists,
        raw_entity_exists=raw_exists,
        allowed_domains=EXECUTION_DOMAINS,
        stateless_domains=STATELESS_DOMAINS,
    )
    if not thin_gate.allowed:
        _log_thin_rejection(host, thin_gate.log_code, call, raw_entity, raw, action)
        return ActionGuardOutcome(thin_gate.to_action_result(), blocked=1)
    return None
