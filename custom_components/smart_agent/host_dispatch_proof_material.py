"""Read the add-on-owned Host Proof material from Home Assistant config."""
from __future__ import annotations

import json
import os
import stat
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any

from .security_channel_secrets import security_channel_secret_mapping_is_valid


MATERIAL_SCHEMA = "smartagent.host_dispatch_proof_material.v1"
MATERIAL_RELATIVE_PATH = ("smartagent", "host_dispatch_proof.json")
HOST_PROOF_CONFIG_KEYS = (
    "host_dispatch_proof_enabled",
    "host_dispatch_proof_current_secret",
    "host_dispatch_proof_staged_secret",
)


class HostDispatchProofMaterialError(RuntimeError):
    """The shared material is missing, unsafe, corrupt, or conflicts with HA."""


def _strict_secret(value: object, *, required: bool) -> str:
    if type(value) is not str:
        raise HostDispatchProofMaterialError("host_proof_material_secret_invalid")
    if not value:
        if required:
            raise HostDispatchProofMaterialError("host_proof_material_secret_missing")
        return ""
    if (
        len(value) < 32
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise HostDispatchProofMaterialError("host_proof_material_secret_invalid")
    return value


def read_host_dispatch_proof_material(
    config_dir: str | os.PathLike[str],
    *,
    config_values: Mapping[str, object],
) -> dict[str, object]:
    """Read one private file and validate it against every HA secret domain."""

    path = Path(config_dir).joinpath(*MATERIAL_RELATIVE_PATH)
    try:
        file_stat = path.lstat()
    except OSError as exc:
        raise HostDispatchProofMaterialError("host_proof_material_unavailable") from exc
    if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
        raise HostDispatchProofMaterialError("host_proof_material_type_invalid")
    if os.name != "nt" and stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise HostDispatchProofMaterialError("host_proof_material_permissions_invalid")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HostDispatchProofMaterialError("host_proof_material_read_failed") from exc
    if not isinstance(payload, Mapping) or set(payload) != {
        "schema_version",
        "enabled",
        "current_secret",
        "staged_secret",
    }:
        raise HostDispatchProofMaterialError("host_proof_material_shape_invalid")
    if payload.get("schema_version") != MATERIAL_SCHEMA or payload.get("enabled") is not True:
        raise HostDispatchProofMaterialError("host_proof_material_state_invalid")
    current_secret = _strict_secret(payload.get("current_secret"), required=True)
    staged_secret = _strict_secret(payload.get("staged_secret"), required=False)
    if staged_secret and staged_secret == current_secret:
        raise HostDispatchProofMaterialError("host_proof_material_secret_reuse")

    merged = dict(config_values)
    merged.update(
        {
            HOST_PROOF_CONFIG_KEYS[0]: True,
            HOST_PROOF_CONFIG_KEYS[1]: current_secret,
            HOST_PROOF_CONFIG_KEYS[2]: staged_secret,
        }
    )
    if not security_channel_secret_mapping_is_valid(merged):
        raise HostDispatchProofMaterialError("host_proof_material_domain_conflict")

    legacy_present = tuple(key in config_values for key in HOST_PROOF_CONFIG_KEYS)
    if any(legacy_present):
        legacy_values = (
            config_values.get(HOST_PROOF_CONFIG_KEYS[0]),
            config_values.get(HOST_PROOF_CONFIG_KEYS[1]),
            config_values.get(HOST_PROOF_CONFIG_KEYS[2]),
        )
        empty_legacy = legacy_values == (False, "", "")
        exact_legacy = legacy_values == (True, current_secret, staged_secret)
        if not empty_legacy and not exact_legacy:
            raise HostDispatchProofMaterialError("host_proof_material_legacy_conflict")

    return {
        "enabled": True,
        "current_secret": current_secret,
        "staged_secret": staged_secret,
    }


def without_legacy_host_proof_fields(values: Mapping[str, object]) -> dict[str, object]:
    """Return an entry mapping without the retired machine fields."""

    return {
        str(key): value
        for key, value in values.items()
        if str(key) not in HOST_PROOF_CONFIG_KEYS
    }


async def async_prepare_host_dispatch_proof_material_for_entry(
    hass: Any,
    entry: Any,
) -> tuple[dict[str, object], str | None]:
    """Read shared material and retire the legacy ConfigEntry fields."""

    persisted_values = {
        **dict(entry.data or {}),
        **dict(entry.options or {}),
    }
    material = await hass.async_add_executor_job(
        partial(
            read_host_dispatch_proof_material,
            hass.config.config_dir,
            config_values=persisted_values,
        )
    )
    cleaned_data = without_legacy_host_proof_fields(dict(entry.data or {}))
    cleaned_options = without_legacy_host_proof_fields(dict(entry.options or {}))
    if cleaned_data != dict(entry.data or {}) or cleaned_options != dict(entry.options or {}):
        hass.config_entries.async_update_entry(
            entry,
            data=cleaned_data,
            options=cleaned_options,
        )
        if any(
            key in dict(entry.data or {}) or key in dict(entry.options or {})
            for key in HOST_PROOF_CONFIG_KEYS
        ):
            return material, (
                "SmartAgent setup blocked: retired Host Proof fields were not removed "
                "through the ConfigEntry framework"
            )

    security_values = {
        **cleaned_data,
        **cleaned_options,
        "host_dispatch_proof_enabled": material["enabled"],
        "host_dispatch_proof_current_secret": material["current_secret"],
        "host_dispatch_proof_staged_secret": material["staged_secret"],
    }
    if not security_channel_secret_mapping_is_valid(security_values):
        return material, (
            "SmartAgent setup blocked: dedicated security channel secret "
            "domains are invalid; update the integration options"
        )
    return material, None


__all__ = [
    "HOST_PROOF_CONFIG_KEYS",
    "HostDispatchProofMaterialError",
    "MATERIAL_RELATIVE_PATH",
    "async_prepare_host_dispatch_proof_material_for_entry",
    "read_host_dispatch_proof_material",
    "without_legacy_host_proof_fields",
]
