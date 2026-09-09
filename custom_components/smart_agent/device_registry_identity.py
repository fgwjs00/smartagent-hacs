"""Identity shared by HA discovery and registry reconciliation."""
from __future__ import annotations

from typing import Any


REGISTRY_IDENTITY_FIELDS = (
    'ha_entity_registry_id', 'ha_platform', 'ha_unique_id', 'ha_device_id',
)


def registry_metadata(entry: Any) -> dict[str, str]:
    if entry is None:
        return {}
    return {
        'ha_entity_registry_id': str(getattr(entry, 'id', '') or ''),
        'ha_platform': str(getattr(entry, 'platform', '') or ''),
        'ha_unique_id': str(getattr(entry, 'unique_id', '') or ''),
        'ha_device_id': str(getattr(entry, 'device_id', '') or ''),
    }


def registry_entry_matches(entity_id: str, info: dict[str, Any], entry: Any) -> bool:
    """Match HA's registry ID, or its complete domain/platform/unique_id tuple."""
    if entry is None:
        return False
    metadata = registry_metadata(entry)
    registry_id = info.get('ha_entity_registry_id')
    if registry_id:
        return registry_id == metadata['ha_entity_registry_id']
    platform = info.get('ha_platform')
    unique_id = info.get('ha_unique_id')
    return bool(
        platform and unique_id
        and entity_id.partition('.')[0] == str(getattr(entry, 'entity_id', '')).partition('.')[0]
        and platform == metadata['ha_platform']
        and unique_id == metadata['ha_unique_id']
    )
