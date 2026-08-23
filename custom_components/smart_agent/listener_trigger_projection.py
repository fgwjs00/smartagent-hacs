"""Portable listener-trigger text and audit-summary projections.

The HA listener owns event subscription and state acquisition.  This module
only formats already-admitted values for prompts and log-safe summaries; it
does not read HA state, call the add-on, persist data, or execute actions.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any


def format_listener_state(
    owner: Any,
    domain: str,
    entity_id: str,
    state: str,
) -> str:
    """Return the existing domain-aware Chinese state label."""
    if domain in owner._PRESENCE_DOMAINS:
        entity_text = entity_id.lower()
        device_info = getattr(owner, "device_info", {})
        if not isinstance(device_info, dict):
            device_info = {}
        raw_info = device_info.get(entity_id)
        info = raw_info if isinstance(raw_info, dict) else {}
        device_name = str(info.get("name") or "").lower()
        is_presence = any(
            keyword in entity_text or keyword in device_name
            for keyword in owner._PRESENCE_KW
        )
        if is_presence:
            return owner._PRESENCE_STATE_ZH.get(state, state)
    return owner._CTRL_STATE_ZH.get(state, state)


def format_listener_trigger(
    owner: Any,
    source: str,
    domain: str,
    name: str,
    entity_id: str,
    old_state: str,
    new_state: str,
) -> str:
    """Build the existing compact trigger text used by inference."""
    domain_label = owner._DOMAIN_ZH_MAP.get(domain, domain)
    old_label = format_listener_state(owner, domain, entity_id, old_state)
    new_label = format_listener_state(owner, domain, entity_id, new_state)
    source_label = {
        "物理/自动": "物理",
        "自动化/脚本": "脚本",
        "用户界面": "用户",
    }.get(source, source)
    return (
        f"[{source_label}] {domain_label}「{name}」"
        f"{old_label}→{new_label}（{entity_id}）"
    )


def listener_trigger_public_summary(
    trigger: Any,
    *,
    entity_id: str = "",
    old_state: str = "",
    new_state: str = "",
) -> str:
    """Return a log-safe trigger summary without friendly names or raw text."""
    if isinstance(trigger, (list, tuple, set)):
        texts = [
            str(item or "").strip()
            for item in trigger
            if str(item or "").strip()
        ]
    else:
        text = str(trigger or "").strip()
        texts = [text] if text else []

    patterns = (
        re.compile(
            r"\[(?P<src>[^\]]+)\].*?」(?P<old>[^→（）\s]+)"
            r"→(?P<new>[^（）\s]+)（(?P<eid>[^）]+)）"
        ),
        re.compile(
            r"\[(?P<src>[^\]]+)\].*?\((?P<eid>[^)]+)\)\]\s+changed:"
            r"\s+(?P<old>\S+)\s+->\s+(?P<new>\S+)"
        ),
        re.compile(
            r"(?P<eid>[A-Za-z0-9_]+\.[A-Za-z0-9_.-]+)\s*[:：]?\s*"
            r"(?P<old>[^\s→-]+)\s*(?:→|->)\s*(?P<new>\S+)"
        ),
    )

    summaries: list[str] = []
    seen: set[str] = set()
    for text in texts:
        summary = ""
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            source = str(match.groupdict().get("src") or "").strip()
            matched_entity = str(match.group("eid") or "").strip()
            old_value = str(match.group("old") or "?").strip()
            new_value = str(match.group("new") or "?").strip()
            if matched_entity:
                prefix = f"[{source}] " if source else ""
                summary = (
                    f"{prefix}{matched_entity}:{old_value}->{new_value}"
                )
            break
        if summary and summary not in seen:
            summaries.append(summary)
            seen.add(summary)

    fallback_entity = str(entity_id or "").strip()
    if fallback_entity:
        old_value = str(old_state or "?").strip() or "?"
        new_value = str(new_state or "?").strip() or "?"
        fallback = f"{fallback_entity}:{old_value}->{new_value}"
        if fallback not in seen:
            summaries.append(fallback)

    if summaries:
        visible = summaries[:6]
        hidden_count = len(summaries) - len(visible)
        suffix = f"; +{hidden_count} more" if hidden_count else ""
        return ("; ".join(visible) + suffix)[:240]

    combined = "\n".join(texts)
    if not combined:
        return "-"
    digest = hashlib.sha256(combined.encode("utf-8", "ignore")).hexdigest()[:12]
    return f"trigger_hash={digest} len={len(combined)}"


def compact_listener_triggers(owner: Any, texts: list[str]) -> str:
    """Group equivalent listener transitions while preserving room hints."""
    new_pattern = re.compile(
        r"\[(.+?)\]\s+\S+「(.+?)」(\S+)→(\S+)（(\S+?)）"
    )
    old_pattern = re.compile(
        r"\[(.+?)\]\s+\S+\s+\[(.+?)\((.+?)\)\]\s+changed:"
        r"\s+(\S+)\s+->\s+(\S+)"
    )
    parsed: list[dict[str, str]] = []
    unparsed: list[str] = []
    for text in texts:
        match = new_pattern.search(text)
        if match:
            source, name, old_state, new_state, entity_id = match.groups()
            parsed.append(
                {
                    "source": source,
                    "name": name,
                    "entity_id": entity_id,
                    "domain": entity_id.split(".")[0],
                    "old_state": old_state,
                    "new_state": new_state,
                }
            )
            continue
        match = old_pattern.search(text)
        if match:
            source, name, entity_id, old_state, new_state = match.groups()
            parsed.append(
                {
                    "source": source,
                    "name": name,
                    "entity_id": entity_id,
                    "domain": entity_id.split(".")[0],
                    "old_state": old_state,
                    "new_state": new_state,
                }
            )
        else:
            unparsed.append(text)

    groups: dict[tuple[str, str, str, str], list[tuple[str, str]]] = (
        defaultdict(list)
    )
    for item in parsed:
        key = (
            item["source"],
            item["domain"],
            item["old_state"],
            item["new_state"],
        )
        groups[key].append((item["name"], item["entity_id"]))

    lines: list[str] = []
    for (source, domain, old_state, new_state), items in groups.items():
        domain_label = owner._DOMAIN_ZH_MAP.get(domain, domain)
        representative = items[0][1] if items else ""
        old_label = format_listener_state(
            owner, domain, representative, old_state
        )
        new_label = format_listener_state(
            owner, domain, representative, new_state
        )
        names = [item[0] for item in items]
        if len(names) == 1:
            lines.append(
                f"[{source}] {domain_label}「{names[0]}」{old_label}→{new_label}"
            )
            continue
        first_name = names[0]
        rest_names = "、".join(names[1:3])
        suffix = (
            f"等{len(names)}台"
            if len(names) > 2
            else (f"、{rest_names}" if rest_names else "")
        )
        lines.append(
            f"[{source}] {domain_label}「{first_name}」{suffix} "
            f"{old_label}→{new_label}"
        )

    lines.extend(unparsed)
    result = "同时发生：\n" + "\n".join(f"  · {line}" for line in lines)
    return result[:218] + "…" if len(result) > 220 else result


__all__ = [
    "compact_listener_triggers",
    "format_listener_state",
    "format_listener_trigger",
    "listener_trigger_public_summary",
]
