"""Presence configuration migration helpers.

This module is intentionally free of Home Assistant imports so startup and
regression tests can reuse the same conversion logic.
"""
from __future__ import annotations

import copy
import json
from typing import Any


def _as_record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = value.strip()
        return [item] if item else []
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                result.append(text)
        return result
    text = str(value or "").strip()
    return [text] if text else []


def _bool_value(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _int_value(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _unique_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _space_rows(core_config: dict[str, Any]) -> list[dict[str, Any]]:
    space_section = _as_record(core_config.get("space") or core_config.get("space_model"))
    raw_spaces = space_section.get("spaces")
    if raw_spaces is None:
        raw_spaces = core_config.get("spaces")
    if isinstance(raw_spaces, dict):
        rows: list[dict[str, Any]] = []
        for key, value in raw_spaces.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("id", key)
                rows.append(row)
            else:
                rows.append({"id": key, "name": str(value)})
        return rows
    if isinstance(raw_spaces, list):
        return [item for item in raw_spaces if isinstance(item, dict)]
    return []


def _alias_keys(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return _unique_strings([text, text.casefold(), text.replace(" ", "_").casefold()])


def _core_space_alias_index(core_config: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for row in _space_rows(core_config):
        space_id = str(row.get("id") or row.get("space_id") or row.get("name") or "").strip()
        if not space_id:
            continue
        candidates: list[str] = []
        for key in ("id", "space_id", "name", "display_name", "room", "area"):
            value = row.get(key)
            if value is not None:
                candidates.append(str(value))
        for key in ("aliases", "zones", "vision_zones"):
            candidates.extend(_string_list(row.get(key)))
        for candidate in candidates:
            for alias_key in _alias_keys(candidate):
                aliases.setdefault(alias_key, space_id)
    return aliases


def _resolve_space_id(value: str, aliases: dict[str, str] | None) -> str:
    text = str(value or "").strip()
    if not text or not aliases:
        return text
    for alias_key in _alias_keys(text):
        resolved = aliases.get(alias_key)
        if resolved:
            return resolved
    return text


def _resolve_space_ids(values: list[str], aliases: dict[str, str] | None) -> list[str]:
    return _unique_strings([_resolve_space_id(value, aliases) for value in values])


def _legacy_scopes(legacy_json: str) -> list[dict[str, Any]]:
    raw = str(legacy_json or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _member_entity_id(member: Any) -> str:
    if isinstance(member, str):
        return member.strip()
    record = _as_record(member)
    return str(record.get("entity_id") or record.get("id") or "").strip()


def _member_use_for(member: dict[str, Any]) -> list[str]:
    explicit = _string_list(member.get("use_for"))
    if explicit:
        return explicit

    use_for: list[str] = []
    if _bool_value(member.get("can_enter_trigger"), True):
        use_for.append("turn_on")
    if _bool_value(member.get("can_leave_evidence"), True):
        use_for.append("turn_off")
    return use_for


def _policy_from_legacy_scope(
    scope: dict[str, Any],
    *,
    space_aliases: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    scope_id = str(scope.get("scope_id") or scope.get("id") or scope.get("name") or "").strip()
    raw_rooms = _string_list(scope.get("rooms") or scope.get("space_ids") or scope.get("spaces"))
    if not raw_rooms and scope_id:
        raw_rooms = [scope_id]
    rooms = _resolve_space_ids(raw_rooms, space_aliases)
    primary_space_id = rooms[0] if rooms else scope_id
    if not primary_space_id:
        return None

    raw_members = scope.get("members")
    members = raw_members if isinstance(raw_members, list) else []
    member_ids = [_member_entity_id(member) for member in members]
    member_ids = [entity_id for entity_id in member_ids if entity_id]
    if not member_ids:
        return None

    enter_triggers: list[str] = []
    leave_evidence: list[str] = []
    for member in members:
        member_record = _as_record(member)
        entity_id = _member_entity_id(member)
        if not entity_id:
            continue
        use_for = _member_use_for(member_record)
        if "turn_on" in use_for or "occupied_or" in use_for:
            enter_triggers.append(entity_id)
        if "turn_off" in use_for or "vacant_and" in use_for:
            leave_evidence.append(entity_id)

    normalized_scope_id = scope_id or primary_space_id
    return {
        "space_id": primary_space_id,
        "scope_id": normalized_scope_id,
        "name": str(scope.get("name") or normalized_scope_id),
        "occupied_strategy": "occupied_or",
        "vacant_strategy": "vacant_and",
        "strategy": "vacant_and" if str(scope.get("strategy") or "") == "vacant_and" else "occupied_or",
        "rooms": list(rooms),
        "space_ids": list(rooms),
        "member_evidence_ids": member_ids,
        "members": member_ids,
        "evidence_use": {
            "enter_triggers": enter_triggers,
            "leave_evidence": leave_evidence,
        },
        "enter_hold_secs": _int_value(scope.get("enter_hold_secs"), 3),
        "vacant_hold_secs": _int_value(scope.get("vacant_hold_secs"), 60),
    }


def _evidence_from_legacy_member(member: Any) -> dict[str, Any] | None:
    entity_id = _member_entity_id(member)
    if not entity_id:
        return None
    record = _as_record(member)
    return {
        "id": entity_id,
        "entity_id": entity_id,
        "name": str(record.get("name") or entity_id),
        "source": str(record.get("source") or "ha"),
        "sensor_type": str(record.get("sensor_type") or "auto"),
        "use_for": _member_use_for(record),
        "freshness_ttl_secs": _int_value(record.get("freshness_ttl_secs"), 0),
        "battery_powered": _bool_value(record.get("battery_powered"), False),
        "confidence": _float_value(record.get("confidence"), 1.0),
    }


def _core_evidence_by_id(core_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    presence = _as_record(core_config.get("presence"))
    evidences = presence.get("evidences")
    result: dict[str, dict[str, Any]] = {}
    for item in evidences if isinstance(evidences, list) else []:
        record = _as_record(item)
        evidence_id = str(record.get("id") or record.get("entity_id") or "").strip()
        if evidence_id:
            result[evidence_id] = dict(record)
    return result


def _core_policy_member_entries(policy: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    raw_members = policy.get("member_evidence_ids")
    if raw_members is None:
        raw_members = policy.get("members")
    entries: list[tuple[str, dict[str, Any]]] = []
    if isinstance(raw_members, list):
        for member in raw_members:
            entity_id = _member_entity_id(member)
            if entity_id:
                entries.append((entity_id, _as_record(member)))
    else:
        for entity_id in _string_list(raw_members):
            entries.append((entity_id, {}))

    result: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for entity_id, record in entries:
        if entity_id in seen:
            continue
        seen.add(entity_id)
        result.append((entity_id, record))
    return result


def _use_for_flags(use_for: list[str]) -> tuple[bool, bool]:
    values = {str(item or "").strip() for item in use_for if str(item or "").strip()}
    can_enter = bool(values & {"turn_on", "occupied_or", "enter", "entry"})
    can_leave = bool(values & {"turn_off", "vacant_and", "leave", "exit"})
    return can_enter, can_leave


def _core_policy_evidence_use_sets(policy: dict[str, Any]) -> tuple[set[str], set[str]] | None:
    evidence_use = policy.get("evidence_use")
    if not isinstance(evidence_use, dict):
        return None
    enter = set(
        _string_list(
            evidence_use.get("enter_triggers")
            or evidence_use.get("turn_on")
            or evidence_use.get("occupied_or")
            or evidence_use.get("enter")
        )
    )
    leave = set(
        _string_list(
            evidence_use.get("leave_evidence")
            or evidence_use.get("turn_off")
            or evidence_use.get("vacant_and")
            or evidence_use.get("leave")
        )
    )
    return enter, leave


def _core_member_projection(
    entity_id: str,
    member_record: dict[str, Any],
    *,
    evidence_record: dict[str, Any],
    evidence_use_sets: tuple[set[str], set[str]] | None,
) -> dict[str, Any]:
    if evidence_use_sets is not None:
        enter, leave = evidence_use_sets
        can_enter = entity_id in enter
        can_leave = entity_id in leave
    elif "can_enter_trigger" in member_record or "can_leave_evidence" in member_record:
        can_enter = _bool_value(member_record.get("can_enter_trigger"), True)
        can_leave = _bool_value(member_record.get("can_leave_evidence"), True)
    else:
        use_for = _string_list(member_record.get("use_for") or evidence_record.get("use_for"))
        if use_for:
            can_enter, can_leave = _use_for_flags(use_for)
        else:
            can_enter = True
            can_leave = True

    return {
        "entity_id": entity_id,
        "can_enter_trigger": bool(can_enter),
        "can_leave_evidence": bool(can_leave),
        "priority": _int_value(member_record.get("priority") or evidence_record.get("priority"), 50),
        "confidence": _float_value(member_record.get("confidence") or evidence_record.get("confidence"), 1.0),
    }


def legacy_presence_fusion_scopes_from_core_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    presence = _as_record(config.get("presence"))
    policies = presence.get("policies")
    if not isinstance(policies, list):
        return []

    evidence_by_id = _core_evidence_by_id(config)
    scopes: list[dict[str, Any]] = []
    for policy in policies:
        policy_record = _as_record(policy)
        if not policy_record:
            continue
        space_id = str(
            policy_record.get("space_id")
            or policy_record.get("room")
            or policy_record.get("scope_id")
            or ""
        ).strip()
        if not space_id:
            continue

        evidence_use_sets = _core_policy_evidence_use_sets(policy_record)
        members = [
            _core_member_projection(
                entity_id,
                member_record,
                evidence_record=evidence_by_id.get(entity_id, {}),
                evidence_use_sets=evidence_use_sets,
            )
            for entity_id, member_record in _core_policy_member_entries(policy_record)
        ]
        scopes.append(
            {
                "scope_id": str(policy_record.get("scope_id") or space_id),
                "name": str(policy_record.get("name") or policy_record.get("display_name") or space_id),
                "strategy": (
                    "vacant_and"
                    if str(policy_record.get("strategy") or policy_record.get("occupied_strategy") or "") == "vacant_and"
                    else "occupied_or"
                ),
                "rooms": _string_list(policy_record.get("rooms") or policy_record.get("space_ids")) or [space_id],
                "members": members,
                "enter_hold_secs": _int_value(policy_record.get("enter_hold_secs"), 3),
                "vacant_hold_secs": _int_value(policy_record.get("vacant_hold_secs"), 60),
            }
        )
    return scopes


def seed_legacy_presence_fusion_into_core_config(
    core_config: dict[str, Any] | None,
    legacy_presence_fusion_json: str,
) -> tuple[dict[str, Any], bool]:
    """Seed Core Config `presence.policies` from legacy `presence_fusion`.

    Returns `(next_config, applied)`. Existing Core presence policies are never
    overwritten; this is a startup-only compatibility bridge for old HA options.
    """
    config = copy.deepcopy(core_config) if isinstance(core_config, dict) else {}
    presence = _as_record(config.get("presence"))
    existing_policies = presence.get("policies")
    if isinstance(existing_policies, list) and existing_policies:
        return config, False

    scopes = _legacy_scopes(legacy_presence_fusion_json)
    space_aliases = _core_space_alias_index(config)
    policies = [
        policy
        for scope in scopes
        if (policy := _policy_from_legacy_scope(scope, space_aliases=space_aliases))
    ]
    if not policies:
        return config, False

    next_presence = dict(presence)
    next_presence["policies"] = policies

    existing_evidences = next_presence.get("evidences")
    evidence_rows = list(existing_evidences) if isinstance(existing_evidences, list) else []
    evidence_by_id = {
        str(_as_record(item).get("id") or _as_record(item).get("entity_id") or ""): dict(_as_record(item))
        for item in evidence_rows
        if isinstance(item, dict)
    }
    for scope in scopes:
        members = scope.get("members")
        for member in members if isinstance(members, list) else []:
            evidence = _evidence_from_legacy_member(member)
            if evidence is None:
                continue
            current = evidence_by_id.get(evidence["id"], {})
            evidence_by_id[evidence["id"]] = {**evidence, **current}
    next_presence["evidences"] = list(evidence_by_id.values())

    config["presence"] = next_presence
    return config, True
