"""HTTP view registration helpers for the SmartAgent HA host."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

HOST_VIEW_CLASS_NAMES: tuple[str, ...] = (
)


V1_VIEW_CLASS_NAMES: tuple[str, ...] = (
    "SmartAgentAuthLoginView",
    "SmartAgentAuthMeView",
    "SmartAgentAuthLogoutView",
    "SmartAgentEventsWSView",
    "SmartAgentHaExecuteView",
    "SmartAgentRoomsView",
    "SmartAgentRoomsSyncView",
    "SmartAgentRoomDetailView",
    "SmartAgentBackupsView",
    "SmartAgentLicenseStatusView",
    "SmartAgentMcpStatusView",
    "SmartAgentDevicePairStartView",
    "SmartAgentDevicePairConfirmView",
)

POST_V1_HOST_VIEW_CLASS_NAMES: tuple[str, ...] = (
)

HASS_BOUND_VIEW_CLASS_NAMES: tuple[str, ...] = (
)

_HASS_BOUND_VIEW_CLASSES: Mapping[str, Any] = {}


def register_v1_views(hass: Any, view_namespace: Mapping[str, Any]) -> None:
    """Register /api/v1 view classes in canonical host order."""
    for name in V1_VIEW_CLASS_NAMES:
        view_cls = view_namespace[name]
        hass.http.register_view(view_cls())


def _register_view_classes(
    hass: Any, view_namespace: Mapping[str, Any], class_names: tuple[str, ...]
) -> None:
    for name in class_names:
        view_cls = view_namespace[name]
        hass.http.register_view(view_cls())


def register_host_views(hass: Any, view_namespace: Mapping[str, Any]) -> None:
    """Register SmartAgent host views in canonical setup order."""
    _register_view_classes(hass, view_namespace, HOST_VIEW_CLASS_NAMES)
    register_v1_views(hass, view_namespace)
    _register_view_classes(hass, view_namespace, POST_V1_HOST_VIEW_CLASS_NAMES)
    for name in HASS_BOUND_VIEW_CLASS_NAMES:
        view_cls = _HASS_BOUND_VIEW_CLASSES[name]
        hass.http.register_view(view_cls(hass))
