"""HTTP view registration helpers for the SmartAgent HA host."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .mcp_server import SmartAgentMCPEndpointView


HOST_VIEW_CLASS_NAMES: tuple[str, ...] = (
    "SmartAgentLogDatesView",
    "SmartAgentLogContentView",
    "SmartAgentLogInfoView",
    "SmartAgentSceneExportView",
    "SmartAgentDevicesView",
)


V1_VIEW_CLASS_NAMES: tuple[str, ...] = (
    "SmartAgentDevicesDiscoverView",
    "SmartAgentDevicesBatchAddView",
    "SmartAgentDeviceDetailView",
    "SmartAgentDeviceControlView",
    "SmartAgentPresenceSensorsView",
    "SmartAgentPresenceSensorTypeView",
    "SmartAgentRoomsView",
    "SmartAgentRoomsSyncView",
    "SmartAgentRoomsTopologyView",
    "SmartAgentAiScenesView",
    "SmartAgentAiSceneActionView",
    "SmartAgentAiSceneTriggerView",
    "SmartAgentSystemStatusView",
    "SmartAgentCompatStatsView",
    "SmartAgentDeprecationReadinessView",
    "SmartAgentDryoffSessionReportView",
    "SmartAgentDashboardSummaryView",
    "SmartAgentDiagnosticsView",
    "SmartAgentSystemSettingsView",
    "SmartAgentAuthLoginView",
    "SmartAgentAuthMeView",
    "SmartAgentAuthLogoutView",
    "SmartAgentSystemBrandView",
    "SmartAgentEventsWSView",
    "SmartAgentMemoryProfilesView",
    "SmartAgentMemoryHabitsView",
    "SmartAgentLearningStatsView",
    "SmartAgentProfileActionView",
    "SmartAgentHabitActionView",
    "SmartAgentCorrectionsView",
    "SmartAgentCorrectionActionView",
    "SmartAgentTransactionsView",
    "SmartAgentTransactionDetailView",
    "SmartAgentDecisionTraceView",
    "SmartAgentTransactionRollbackView",
    "SmartAgentEnergyView",
    "SmartAgentLicenseStatusView",
    "SmartAgentLicenseVerifyView",
    "SmartAgentBackupsView",
    "SmartAgentBackupsActionView",
    "SmartAgentAiSceneOpsView",
    "SmartAgentPatrolTriggerView",
    "SmartAgentModeView",
    "SmartAgentShowroomSceneView",
    "SmartAgentShowroomSceneConfigView",
    "SmartAgentDevicePairStartView",
    "SmartAgentDevicePairConfirmView",
    "SmartAgentVoiceSessionView",
    "SmartAgentVoiceInterruptView",
    "SmartAgentVisionCamerasView",
    "SmartAgentVisionCamerasActionView",
    "SmartAgentVisionZonesView",
    "SmartAgentVisionZonesSaveView",
    "SmartAgentMcpStatusView",
    "SmartAgentMcpSettingsView",
    "SmartAgentHaExecuteView",
    "SmartAgentCapabilityDryRunView",
    "SmartAgentAiSceneDeleteFallbackView",
    "SmartAgentAiSceneArchiveView",
)

POST_V1_HOST_VIEW_CLASS_NAMES: tuple[str, ...] = (
    "SmartAgentPairCreateView",
)

HASS_BOUND_VIEW_CLASS_NAMES: tuple[str, ...] = (
    "SmartAgentMCPEndpointView",
)

_HASS_BOUND_VIEW_CLASSES: Mapping[str, Any] = {
    "SmartAgentMCPEndpointView": SmartAgentMCPEndpointView,
}


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
