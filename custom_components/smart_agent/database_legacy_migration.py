"""Deterministic read-only projection for the legacy configuration migration."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any


class LegacyConfigMigrationError(RuntimeError):
    """Identify which legacy source could not be projected."""

    def __init__(self, stage: str) -> None:
        super().__init__(f"legacy_config_migration_{stage}_failed")
        self.stage = stage


def _legacy_sql_projection(
    conn: Any,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    devices_by_id: dict[str, dict[str, Any]] = {}
    habits_by_content: dict[str, dict[str, Any]] = {}
    rules_by_content: dict[str, dict[str, Any]] = {}
    for row in conn.execute("SELECT * FROM devices ORDER BY entity_id"):
        columns = set(row.keys())
        entity_id = str(row["entity_id"] or "").strip()
        if not entity_id:
            continue
        devices_by_id[entity_id] = {
            "entity_id": entity_id,
            "name": str(row["name"] or entity_id),
            "area": str(row["area"] or ""),
            "type": str(row["type"] or ""),
            "ops": str(row["ops"] or ""),
            "control_mode": (
                str(row["control_mode"] or "shared")
                if "control_mode" in columns
                else "shared"
            ),
            "sensor_type": (
                str(row["sensor_type"] or "") if "sensor_type" in columns else ""
            ),
        }
    for table, output in (
        ("habits", habits_by_content),
        ("rules", rules_by_content),
    ):
        for row in conn.execute(
            f"SELECT content, locked, created FROM {table} ORDER BY id"
        ):
            content = str(row["content"] or "").strip()
            if content:
                output[content] = {
                    "content": content,
                    "locked": bool(row["locked"]),
                    "created": str(row["created"] or ""),
                }
    return devices_by_id, habits_by_content, rules_by_content


def _merge_json_devices(
    devices_by_id: dict[str, dict[str, Any]],
    raw_devices: Any,
) -> None:
    for entity_key, description in raw_devices.items():
        entity_id = str(entity_key or "").strip()
        if not entity_id or entity_id in devices_by_id:
            continue
        parts = [part.strip() for part in str(description).split("|")]
        devices_by_id[entity_id] = {
            "entity_id": entity_id,
            "name": parts[0] if parts else entity_id,
            "area": parts[1] if len(parts) > 1 else "",
            "type": parts[2] if len(parts) > 2 else "",
            "ops": parts[3] if len(parts) > 3 else "",
            "control_mode": "shared",
            "sensor_type": "",
        }


def _merge_json_text_rows(
    output: dict[str, dict[str, Any]],
    items: Any,
) -> None:
    for item in items:
        content = str(item or "").strip()
        if content and content not in output:
            output[content] = {
                "content": content,
                "locked": False,
                "created": "",
            }


def _merge_json_projection(
    devices_by_id: dict[str, dict[str, Any]],
    habits_by_content: dict[str, dict[str, Any]],
    rules_by_content: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> None:
    _merge_json_devices(devices_by_id, config.get("devices", {}))
    _merge_json_text_rows(habits_by_content, config.get("habits", []))
    _merge_json_text_rows(rules_by_content, config.get("rules", []))


def _migration_payload(
    devices_by_id: dict[str, dict[str, Any]],
    habits_by_content: dict[str, dict[str, Any]],
    rules_by_content: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    devices = [devices_by_id[key] for key in sorted(devices_by_id)]
    habits = [habits_by_content[key] for key in sorted(habits_by_content)]
    rules = [rules_by_content[key] for key in sorted(rules_by_content)]
    if not devices and not habits and not rules:
        return None
    canonical = {"devices": devices, "habits": habits, "rules": rules}
    digest = hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "migration_id": f"legacy-config:sha256:{digest}",
        "devices": devices,
        "habits": habits,
        "rules": rules,
    }


def build_legacy_config_migration_batch(
    conn: Any,
    config_dir: str,
) -> tuple[dict[str, Any], str | None] | None:
    """Project SQL plus optional JSON into one deterministic migration batch."""
    try:
        devices_by_id, habits_by_content, rules_by_content = _legacy_sql_projection(conn)
    except Exception as exc:
        raise LegacyConfigMigrationError("sql_projection") from exc

    json_path = os.path.join(config_dir, "smart_agent_config.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
            config = loaded if isinstance(loaded, dict) else {}
            _merge_json_projection(
                devices_by_id,
                habits_by_content,
                rules_by_content,
                config,
            )
        except Exception as exc:
            raise LegacyConfigMigrationError("json_projection") from exc

    payload = _migration_payload(
        devices_by_id,
        habits_by_content,
        rules_by_content,
    )
    if payload is None:
        return None
    return payload, json_path if os.path.exists(json_path) else None


__all__ = [
    "LegacyConfigMigrationError",
    "build_legacy_config_migration_batch",
]
