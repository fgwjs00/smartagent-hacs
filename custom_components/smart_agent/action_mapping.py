"""
action_mapping — 场景 entities/actions 统一映射工具。
"""
from __future__ import annotations

from typing import Any

from .const import comparable_action_params

DEFAULT_ON_STATES = ("on", "open", "heat", "cool", "auto")


def normalize_raw_actions(
    raw_actions: list[dict] | None,
    *,
    device_info: dict[str, dict] | None = None,
) -> list[dict]:
    """将外部 actions 标准化为统一结构。"""
    out: list[dict] = []
    if not isinstance(raw_actions, list):
        return out
    for a in raw_actions:
        if not isinstance(a, dict):
            continue
        eid = a.get("entity_id", "")
        if not isinstance(eid, str) or not eid:
            continue
        if device_info is not None and eid not in device_info:
            continue
        domain = a.get("domain") or (eid.split(".")[0] if "." in eid else "")
        service = a.get("service", "")
        if not isinstance(domain, str) or not domain or not isinstance(service, str) or not service:
            continue
        params = a.get("params") if isinstance(a.get("params"), dict) else {}
        out.append({
            "entity_id": eid,
            "domain": domain,
            "service": service,
            "params": params,
            "delay_seconds": a.get("delay_seconds", 0),
        })
    return out


def entities_to_actions(
    entities: list[dict],
    *,
    device_info: dict[str, dict] | None = None,
    on_states: tuple[str, ...] = DEFAULT_ON_STATES,
    param_keys: tuple[str, ...] | None = None,
    default_delay_seconds: int = 0,
) -> list[dict]:
    """从 entities 推导 canonical actions。"""
    out: list[dict] = []
    if not isinstance(entities, list):
        return out
    on_state_set = set(on_states)
    for e in entities:
        if not isinstance(e, dict):
            continue
        eid = e.get("entity_id", "")
        if not isinstance(eid, str) or not eid:
            continue
        if device_info is not None and eid not in device_info:
            continue
        state = e.get("state", "on")
        domain = eid.split(".")[0] if "." in eid else ""
        if not domain:
            continue
        if domain == "cover":
            service = "open_cover" if state == "open" else "close_cover"
        else:
            service = "turn_on" if state in on_state_set else "turn_off"
        if param_keys is None:
            params = comparable_action_params(domain, e)
        else:
            params: dict[str, Any] = {}
            for k in param_keys:
                if k in e:
                    params[k] = e[k]
        out.append({
            "entity_id": eid,
            "domain": domain,
            "service": service,
            "params": params,
            "delay_seconds": default_delay_seconds,
        })
    return out
