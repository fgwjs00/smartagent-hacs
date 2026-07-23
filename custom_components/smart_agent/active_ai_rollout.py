"""Pure rollout gate for active-AI model access and HA execution."""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any, NamedTuple

from .action_normalization import action_domain


ACTIVE_AI_MODES = frozenset({"off", "shadow", "canary", "on"})
DEFAULT_ACTIVE_AI_MODE = "shadow"


def _string_set(value: Any, *, lowercase: bool = False) -> frozenset[str]:
    if value is None:
        return frozenset()
    raw_values: Iterable[Any]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return frozenset()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except (TypeError, ValueError, json.JSONDecodeError):
                parsed = None
            raw_values = parsed if isinstance(parsed, list) else re.split(r"[,\s]+", text)
        else:
            raw_values = re.split(r"[,\s]+", text)
    elif isinstance(value, (list, tuple, set, frozenset)):
        raw_values = value
    else:
        raw_values = (value,)
    values = []
    for item in raw_values:
        text = str(item or "").strip()
        if not text:
            continue
        values.append(text.lower() if lowercase else text)
    return frozenset(values)


def normalize_active_ai_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in ACTIVE_AI_MODES else DEFAULT_ACTIVE_AI_MODE


class ActiveAiRolloutConfig(NamedTuple):
    mode: str
    canary_space_ids: frozenset[str]
    canary_domains: frozenset[str]

    @classmethod
    def from_values(
        cls,
        *,
        mode: Any = DEFAULT_ACTIVE_AI_MODE,
        canary_space_ids: Any = (),
        canary_domains: Any = (),
    ) -> "ActiveAiRolloutConfig":
        return cls(
            mode=normalize_active_ai_mode(mode),
            canary_space_ids=_string_set(canary_space_ids),
            canary_domains=_string_set(canary_domains, lowercase=True),
        )

    @classmethod
    def from_mapping(cls, value: Any) -> "ActiveAiRolloutConfig":
        source = value if isinstance(value, Mapping) else {}
        return cls.from_values(
            mode=source.get("mode", source.get("active_ai_mode")),
            canary_space_ids=source.get(
                "canary_space_ids",
                source.get("active_ai_canary_space_ids"),
            ),
            canary_domains=source.get(
                "canary_domains",
                source.get("active_ai_canary_domains"),
            ),
        )


class ActiveAiRolloutDecision(NamedTuple):
    mode: str
    allow_model: bool
    allow_execution: bool
    reason: str
    trigger_space_id: str
    action_domains: tuple[str, ...]
    blocked_domains: tuple[str, ...]
    action_space_ids: tuple[str, ...]
    blocked_space_ids: tuple[str, ...]

    def as_trace(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "allow_model": self.allow_model,
            "allow_execution": self.allow_execution,
            "reason": self.reason,
            "trigger_space_id": self.trigger_space_id,
            "action_domains": list(self.action_domains),
            "blocked_domains": list(self.blocked_domains),
            "action_space_ids": list(self.action_space_ids),
            "blocked_space_ids": list(self.blocked_space_ids),
        }


def _decision(
    config: ActiveAiRolloutConfig,
    *,
    allow_model: bool,
    allow_execution: bool,
    reason: str,
    trigger_space_id: str = "",
    action_domains: Iterable[str] = (),
    blocked_domains: Iterable[str] = (),
    action_space_ids: Iterable[str] = (),
    blocked_space_ids: Iterable[str] = (),
) -> ActiveAiRolloutDecision:
    return ActiveAiRolloutDecision(
        mode=config.mode,
        allow_model=allow_model,
        allow_execution=allow_execution,
        reason=reason,
        trigger_space_id=str(trigger_space_id or "").strip(),
        action_domains=tuple(sorted(set(action_domains))),
        blocked_domains=tuple(sorted(set(blocked_domains))),
        action_space_ids=tuple(sorted(set(action_space_ids))),
        blocked_space_ids=tuple(sorted(set(blocked_space_ids))),
    )


def enrich_active_ai_action_spaces(
    actions: Any,
    device_info: Any,
) -> list[Any]:
    """Attach canonical target spaces without mutating planner output."""
    if not isinstance(actions, list):
        return []
    devices = device_info if isinstance(device_info, Mapping) else {}
    enriched: list[Any] = []
    for raw_action in actions:
        if not isinstance(raw_action, Mapping):
            enriched.append(raw_action)
            continue
        action = dict(raw_action)
        target_space_id = str(
            action.get("target_space_id")
            or action.get("space_id")
            or ""
        ).strip()
        target = action.get("target")
        target_entity_id = (
            target.get("entity_id")
            if isinstance(target, Mapping)
            else ""
        )
        entity_id = str(
            action.get("entity_id")
            or action.get("entity")
            or target_entity_id
            or ""
        ).strip()
        info = devices.get(entity_id, {}) if entity_id else {}
        if not target_space_id and isinstance(info, Mapping):
            target_space_id = str(
                info.get("space_id")
                or info.get("room_id")
                or info.get("area_id")
                or info.get("room")
                or info.get("area")
                or ""
            ).strip()
        if target_space_id:
            action["target_space_id"] = target_space_id
        enriched.append(action)
    return enriched


def evaluate_active_ai_model_gate(
    *,
    ai_enabled: bool,
    config: ActiveAiRolloutConfig,
) -> ActiveAiRolloutDecision:
    if not ai_enabled:
        return _decision(
            config,
            allow_model=False,
            allow_execution=False,
            reason="active_ai_global_disabled",
        )
    if config.mode == "off":
        return _decision(
            config,
            allow_model=False,
            allow_execution=False,
            reason="active_ai_off",
        )
    return _decision(
        config,
        allow_model=True,
        allow_execution=False,
        reason=f"active_ai_{config.mode}_model_allowed",
    )


def evaluate_active_ai_execution_gate(
    *,
    ai_enabled: bool,
    config: ActiveAiRolloutConfig,
    trigger_space_id: Any,
    actions: Any,
    execution_flags: Any,
) -> ActiveAiRolloutDecision:
    model_gate = evaluate_active_ai_model_gate(ai_enabled=ai_enabled, config=config)
    if not model_gate.allow_model:
        return model_gate

    space_id = str(trigger_space_id or "").strip()
    if not isinstance(actions, list) or not actions:
        return _decision(
            config,
            allow_model=True,
            allow_execution=False,
            reason="active_ai_no_actions",
            trigger_space_id=space_id,
        )
    domains: list[str] = []
    action_space_ids: list[str] = []
    action_space_missing = False
    for action in actions:
        service = (
            str(
                action.get("service")
                or action.get("action")
                or action.get("command")
                or ""
            ).strip()
            if isinstance(action, Mapping)
            else ""
        )
        explicit_domain = (
            str(action.get("domain") or "").strip()
            if isinstance(action, Mapping)
            else ""
        )
        domain = (
            action_domain(dict(action))
            if isinstance(action, Mapping) and (explicit_domain or service)
            else ""
        )
        if not domain:
            return _decision(
                config,
                allow_model=True,
                allow_execution=False,
                reason="active_ai_action_domain_missing",
                trigger_space_id=space_id,
                action_domains=domains,
            )
        domains.append(domain)
        target_space_id = (
            str(
                action.get("target_space_id")
                or action.get("space_id")
                or ""
            ).strip()
            if isinstance(action, Mapping)
            else ""
        )
        if target_space_id:
            action_space_ids.append(target_space_id)
        else:
            action_space_missing = True

    if config.mode == "shadow":
        return _decision(
            config,
            allow_model=True,
            allow_execution=False,
            reason="active_ai_shadow",
            trigger_space_id=space_id,
            action_domains=domains,
            action_space_ids=action_space_ids,
        )
    if config.mode == "canary":
        if not space_id or space_id not in config.canary_space_ids:
            return _decision(
                config,
                allow_model=True,
                allow_execution=False,
                reason="active_ai_canary_space_not_allowed",
                trigger_space_id=space_id,
                action_domains=domains,
                action_space_ids=action_space_ids,
            )
        blocked_domains = sorted(set(domains) - config.canary_domains)
        if blocked_domains:
            return _decision(
                config,
                allow_model=True,
                allow_execution=False,
                reason="active_ai_canary_domain_not_allowed",
                trigger_space_id=space_id,
                action_domains=domains,
                blocked_domains=blocked_domains,
                action_space_ids=action_space_ids,
            )
        if action_space_missing:
            return _decision(
                config,
                allow_model=True,
                allow_execution=False,
                reason="active_ai_action_space_missing",
                trigger_space_id=space_id,
                action_domains=domains,
                action_space_ids=action_space_ids,
            )
        blocked_space_ids = sorted(set(action_space_ids) - config.canary_space_ids)
        if blocked_space_ids:
            return _decision(
                config,
                allow_model=True,
                allow_execution=False,
                reason="active_ai_canary_action_space_not_allowed",
                trigger_space_id=space_id,
                action_domains=domains,
                action_space_ids=action_space_ids,
                blocked_space_ids=blocked_space_ids,
            )

    flags = execution_flags if isinstance(execution_flags, Mapping) else {}
    if flags.get("domain_real_execution_enabled") is not True:
        return _decision(
            config,
            allow_model=True,
            allow_execution=False,
            reason="active_ai_domain_execution_disabled",
            trigger_space_id=space_id,
            action_domains=domains,
            action_space_ids=action_space_ids,
        )
    if (
        "light" in domains
        and flags.get("lighting_controlled_execution_enabled") is not True
    ):
        return _decision(
            config,
            allow_model=True,
            allow_execution=False,
            reason="active_ai_lighting_execution_disabled",
            trigger_space_id=space_id,
            action_domains=domains,
            action_space_ids=action_space_ids,
        )

    return _decision(
        config,
        allow_model=True,
        allow_execution=True,
        reason=(
            "active_ai_canary_allowed"
            if config.mode == "canary"
            else "active_ai_on_allowed"
        ),
        trigger_space_id=space_id,
        action_domains=domains,
        action_space_ids=action_space_ids,
    )
