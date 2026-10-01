"""Shared, strict camera/zone identity projection for HA and MCP read authority."""
from __future__ import annotations

from typing import Any

FRIGATE_ZONE_QUERIES = (
    ("SELECT zone_id FROM frigate_zones", "zone_id"),
    ("SELECT camera_id FROM frigate_cameras", "camera_id"),
)


def _identity(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"frigate_authority_invalid field={field}")
    return value.strip().lower()


def _records(value: Any, field: str) -> list[dict]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"frigate_authority_invalid field={field}")
    return value


def frigate_api_zone_ids(cameras: Any) -> set[str]:
    known: set[str] = set()
    for camera in _records(cameras, "cameras"):
        known.add(_identity(camera.get("camera_id"), "camera_id"))
        for zone in _records(camera.get("zones", []), "zones"):
            known.add(_identity(zone.get("zone_id"), "zone_id"))
    return known


def frigate_db_zone_ids(rows: Any, field: str) -> set[str]:
    return {_identity(row[field], field) for row in rows}
