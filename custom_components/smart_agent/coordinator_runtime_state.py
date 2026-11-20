"""Pure in-memory runtime state initialization for SmartAgentCoordinator.

Extracted so ``SmartAgentCoordinator.__init__`` and unit-test harnesses
(``SmartAgentCoordinator.__new__`` + ``_init_runtime_state()``) share a single
authoritative set of attributes without Mixin ``getattr`` self-defenses.
"""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Mapping
import json
import logging
import os
import threading
import time
from typing import Any

from .active_ai_rollout import normalize_active_ai_mode
from .const import (
    CONF_ACTIVE_AI_MODE,
    CONF_AI_ENABLED,
    CONF_BRAND_LOGO_URL,
    CONF_BRAND_NAME,
    CONF_BRAND_PRIMARY_COLOR,
    CONF_CLOUD_FALLBACK,
    CONF_CONFIDENCE_AUTO,
    CONF_CONFIDENCE_NOTIFY,
    CONF_COOLDOWN,
    CONF_DEPLOY_NAME,
    CONF_ENGINE,
    CONF_FILE_LOG_LEVEL,
    CONF_FRIGATE_ENABLED,
    CONF_HABIT_PROACTIVE,
    CONF_LEARNING_MODE,
    CONF_LICENSE_KEY,
    CONF_LOG_RETENTION,
    CONF_MANUAL_OVERRIDE_PROTECTION_SECONDS,
    CONF_MODE,
    CONF_OLLAMA_MODEL,
    CONF_OLLAMA_URL,
    CONF_ONLINE_API_KEY,
    CONF_ONLINE_BASE_URL,
    CONF_ONLINE_MODEL,
    CONF_QWEATHER_API_KEY,
    CONF_SEARXNG_URL,
    CONF_SENSORS_MUTED,
    CONF_SHOWROOM_AREA_NAME,
    CONF_SHOWROOM_BIZ_END,
    CONF_SHOWROOM_BIZ_START,
    CONF_SHOWROOM_CUSTOM_PROMPT,
    CONF_SHOWROOM_EXCLUDED_SUBAREAS,
    CONF_SHOWROOM_SCENE,
    CONF_SHOWROOM_SCENE_OVERRIDES,
    CONF_SHOWROOM_ZONE_MAP,
    CONF_TTS_LEVEL,
    CONF_TTS_SERVICE,
    CONF_TTS_TARGET,
    CONF_VISION_ENABLED,
    CONF_VISION_ENGINE,
    CONF_VISION_MODEL,
    DB_FILENAME,
    DEFAULT_ACTIVE_AI_MODE,
    DEFAULT_BRAND_LOGO_URL,
    DEFAULT_BRAND_NAME,
    DEFAULT_BRAND_PRIMARY_COLOR,
    DEFAULT_CONFIDENCE_AUTO,
    DEFAULT_CONFIDENCE_NOTIFY,
    DEFAULT_DEPLOY_NAME,
    DEFAULT_FILE_LOG_LEVEL,
    DEFAULT_SHOWROOM_AREA_NAME,
    DEFAULT_SHOWROOM_BIZ_END,
    DEFAULT_SHOWROOM_BIZ_START,
    DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS,
    DEFAULT_SHOWROOM_ZONE_MAP,
    DOMAIN,
    ENGINE_ONLINE,
    LICENSE_TIER_FREE,
    LOG_RETENTION_DAYS,
    MEMORY_RETENTION_DAYS,
    MODE_HOME,
    PATTERN_FILENAME,
    SHOWROOM_SCENES,
    STARTUP_GRACE_SECONDS,
    TTS_LEVEL_OFF,
    parse_biz_time,
)
from .sensor_event_filter import EnvironmentTelemetryFilter

_LOGGER = logging.getLogger(__name__)
_FILE_LOG_LEVELS = {
    logging.DEBUG,
    logging.INFO,
    logging.WARNING,
    logging.ERROR,
    logging.CRITICAL,
}


def coerce_file_log_level(value: Any) -> int:
    text = str(value or DEFAULT_FILE_LOG_LEVEL).strip().upper()
    if text == "WARN":
        text = "WARNING"
    level = getattr(logging, text, logging.INFO)
    return level if isinstance(level, int) and level in _FILE_LOG_LEVELS else logging.INFO


def _parse_clamped_int(value: Any, *, field: str, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        _LOGGER.warning("[Coordinator] invalid integer config %s=%r; using %d", field, value, default)
        parsed = default
    return max(minimum, min(parsed, maximum))


def _parse_json_dict(raw: Any, *, field: str) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    trimmed = raw.strip()
    if not trimmed:
        return {}
    try:
        parsed = json.loads(trimmed)
    except (json.JSONDecodeError, TypeError, ValueError):
        _LOGGER.warning("[Coordinator] invalid JSON mapping for %s", field)
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _init_core_and_engine_state(self: Any, cfg: dict[str, Any], *, config_dir: str) -> None:
    if "hass" not in self.__dict__:
        self.hass = None
    if "_entry" not in self.__dict__:
        self._entry = None
    if "data" not in self.__dict__:
        self.data = None

    self._config_dir = str(config_dir or "")
    self._memory_db = os.path.join(self._config_dir, DB_FILENAME) if self._config_dir else DB_FILENAME
    self._pattern_file = (
        os.path.join(self._config_dir, PATTERN_FILENAME) if self._config_dir else PATTERN_FILENAME
    )
    self._file_log_level = coerce_file_log_level(
        cfg.get(CONF_FILE_LOG_LEVEL, DEFAULT_FILE_LOG_LEVEL)
    )
    self._file_log_level_name = logging.getLevelName(self._file_log_level)
    self._file_logger = logging.getLogger(f"{DOMAIN}.system")
    self._file_logger.setLevel(self._file_log_level)
    self._file_logger.handlers.clear()
    self._file_logger.propagate = False
    self._log_dir: str = ""
    self._log_queue_listener: Any = None

    self.engine = cfg.get(CONF_ENGINE, "local")
    self.ollama_url = cfg.get(CONF_OLLAMA_URL, "http://127.0.0.1:11434")
    self.ollama_model = cfg.get(CONF_OLLAMA_MODEL, "qwen3-smarthome")
    self._online_api_key = cfg.get(CONF_ONLINE_API_KEY, "")
    self.online_base_url = cfg.get(
        CONF_ONLINE_BASE_URL,
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    self.online_model = cfg.get(CONF_ONLINE_MODEL, "qwen3.7-plus")
    self.confidence_auto = int(cfg.get(CONF_CONFIDENCE_AUTO, DEFAULT_CONFIDENCE_AUTO))
    self.confidence_notify = int(cfg.get(CONF_CONFIDENCE_NOTIFY, DEFAULT_CONFIDENCE_NOTIFY))
    self.cooldown = int(cfg.get(CONF_COOLDOWN, 60))
    self._manual_override_protection_seconds = _parse_clamped_int(
        cfg.get(CONF_MANUAL_OVERRIDE_PROTECTION_SECONDS, 0),
        field=CONF_MANUAL_OVERRIDE_PROTECTION_SECONDS,
        default=0,
        minimum=0,
        maximum=86400,
    )
    self._tools: Any = None
    self._qweather_api_key: str = str(cfg.get(CONF_QWEATHER_API_KEY) or "").strip()
    self._searxng_url: str = str(cfg.get(CONF_SEARXNG_URL) or "").strip()
    self._cloud_fallback = bool(cfg.get(CONF_CLOUD_FALLBACK, False))
    self._vision_enabled = bool(cfg.get(CONF_VISION_ENABLED, False))
    self._vision_engine = cfg.get(CONF_VISION_ENGINE, ENGINE_ONLINE)
    self._vision_model = str(cfg.get(CONF_VISION_MODEL) or "qwen3.5-omni-flash").strip()


def _init_showroom_and_brand_state(self: Any, cfg: dict[str, Any]) -> None:
    self.showroom_biz_start_min: int = parse_biz_time(
        cfg.get(CONF_SHOWROOM_BIZ_START, DEFAULT_SHOWROOM_BIZ_START)
    )
    self.showroom_biz_end_min: int = parse_biz_time(
        cfg.get(CONF_SHOWROOM_BIZ_END, DEFAULT_SHOWROOM_BIZ_END)
    )
    self.showroom_biz_start: int = self.showroom_biz_start_min // 60
    self.showroom_biz_end: int = self.showroom_biz_end_min // 60
    self.showroom_area_name: str = str(
        cfg.get(CONF_SHOWROOM_AREA_NAME, DEFAULT_SHOWROOM_AREA_NAME) or ""
    ).strip()
    excl_raw = str(
        cfg.get(CONF_SHOWROOM_EXCLUDED_SUBAREAS, DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS) or ""
    ).strip()
    self.showroom_excluded_subareas: list[str] = (
        [s.strip() for s in excl_raw.split(",") if s.strip()] if excl_raw else []
    )
    self._showroom_zone_map: dict[str, str] = _parse_json_dict(
        cfg.get(CONF_SHOWROOM_ZONE_MAP, DEFAULT_SHOWROOM_ZONE_MAP),
        field=CONF_SHOWROOM_ZONE_MAP,
    )
    self._last_showroom_cmd_time: float = 0.0
    self._last_showroom_dedup_key: str = ""
    self._last_showroom_dedup_ts: float = 0.0
    self._last_departure_turnoff_time: dict[str, float] = {}

    self.brand_name: str = str(cfg.get(CONF_BRAND_NAME, DEFAULT_BRAND_NAME) or DEFAULT_BRAND_NAME).strip()
    self.brand_primary_color: str = str(
        cfg.get(CONF_BRAND_PRIMARY_COLOR, DEFAULT_BRAND_PRIMARY_COLOR)
        or DEFAULT_BRAND_PRIMARY_COLOR
    ).strip()
    self.brand_logo_url: str = str(cfg.get(CONF_BRAND_LOGO_URL, DEFAULT_BRAND_LOGO_URL) or "").strip()
    self.deploy_name: str = str(cfg.get(CONF_DEPLOY_NAME, DEFAULT_DEPLOY_NAME) or "").strip()

    self._mode = cfg.get(CONF_MODE, MODE_HOME)
    saved_scene = cfg.get(CONF_SHOWROOM_SCENE, "") or ""
    self._showroom_scene: str | None = saved_scene if saved_scene in SHOWROOM_SCENES else None
    self._showroom_custom_prompt: str = str(cfg.get(CONF_SHOWROOM_CUSTOM_PROMPT, "") or "").strip()
    self._showroom_scene_overrides: dict[str, Any] = _parse_json_dict(
        cfg.get(CONF_SHOWROOM_SCENE_OVERRIDES, ""),
        field=CONF_SHOWROOM_SCENE_OVERRIDES,
    )
    self._SHOWROOM_COOLDOWN = 15
    self._SHOWROOM_CONFIDENCE_AUTO = 70
    self._SHOWROOM_CONFIDENCE_NOTIFY = 40


def _init_listener_and_presence_state(self: Any, cfg: dict[str, Any]) -> None:
    self._startup_grace = STARTUP_GRACE_SECONDS
    self._startup_time = time.time()
    self._startup_ready_notified: bool = False
    self._last_inference: dict[str, float] = {}
    self._active_timers: dict[str, Any] = {}
    self._last_ai_actions: dict[str, dict] = {}
    self._recent_ai_action_results: list[dict[str, Any]] = []
    self._recent_ai_action_results_lock = threading.Lock()
    self._user_overrides: dict[str, dict] = {}
    self._user_overrides_lock = threading.Lock()
    self._user_manual_actions: dict[str, dict] = {}
    self._user_manual_actions_lock = threading.Lock()
    self._arrival_manual_action_evidence: dict[str, list[dict[str, Any]]] = {}
    self._trusted_manual_service_contexts: dict[str, dict[str, Any]] = {}
    self._manual_scene_learning_sessions: dict[str, dict[str, Any]] = {}
    self._manual_scene_learning_timers: dict[str, Any] = {}
    self._pending_triggers: list[dict] = []
    self._pending_triggers_lock = threading.Lock()
    self._pending_trigger_controllable: dict[str, str] = {}
    self._merge_timer_unsub: Any = None
    self._scan_timer_unsub: Any = None
    self._habit_check_timer_unsub: Any = None
    self._room_lighting_startup_cancel: Any = None
    self._last_notify: dict[str, float] = {}
    self._terminal_logs: list[str] = []
    self._action_history_structured: list[str] = []
    self._sys_logs: list[str] = []
    self._sys_log_html_rows: list[str] = []
    self._sys_log_lock = threading.Lock()
    self._log_retention_days: int = int(cfg.get(CONF_LOG_RETENTION, LOG_RETENTION_DAYS))
    self._pattern_summary = ""

    self._device_priority_map: dict[str, dict] = {}
    self._user_op_history: dict[str, list[float]] = {}
    self._global_suppress_until: float = 0.0
    self._global_suppress_reason: str = ""

    self._listener_removers: list = []
    self._state_listener_removers: list = []
    self._listener_entity_ids: set[str] = set()
    self._managed_registry_entity_ids: set[str] = set()
    self._unmanaged_listener_entity_warned: set[str] = set()
    self._last_listener_event: dict[str, Any] = {}
    self._last_listener_filter_reason: str = ""
    self._device_info_source: str = "ha_local_devices"
    self._last_addon_device_sync_status: dict[str, Any] = {}
    self._last_addon_memory_sync_status: dict[str, Any] = {}
    self._ha_area_sync_lock = asyncio.Lock()
    self._last_ha_area_sync: dict[str, Any] = {}
    self._environment_telemetry_event_filter = EnvironmentTelemetryFilter()

    self._glitch_history: dict[str, list[float]] = {}
    self._glitch_suppressed: dict[str, float] = {}
    self._room_topology_cache: dict[str, set[str]] = {}
    self._room_topology_cache_updated_at: float = 0.0
    self._room_topology_refresh_pending: bool = False
    self._presence_snapshot_cache: dict[str, dict[str, Any]] = {}
    self._presence_snapshot_cache_updated_at: float = 0.0
    self._presence_snapshot_cache_record: tuple[dict[str, dict[str, Any]], float] = ({}, 0.0)
    self._presence_snapshot_refresh_request_id: int = 0
    self._presence_snapshot_refresh_committed_request_id: int = 0
    self._arrival_occupancy_cycles: dict[str, dict[str, Any]] = {}
    self._arrival_occupancy_cycle_store: Any = None
    self._presence_off_timers: dict[str, Any] = {}
    self._presence_last_on: dict[str, float] = {}
    self._presence_on_start: dict[str, float] = {}
    self._presence_flap_history: dict[str, list[float]] = {}
    self._presence_flap_suppressed: dict[str, float] = {}
    self._rational_guard_last_retry: dict[str, float] = {}


def _init_collaborators_and_execution_state(self: Any, cfg: dict[str, Any]) -> None:
    self._enabled = bool(cfg.get(CONF_AI_ENABLED, True))
    self._active_ai_mode = normalize_active_ai_mode(
        cfg.get(CONF_ACTIVE_AI_MODE, DEFAULT_ACTIVE_AI_MODE)
    )
    self._sensors_muted = bool(cfg.get(CONF_SENSORS_MUTED, False))
    self._learning_mode = bool(cfg.get(CONF_LEARNING_MODE, False))
    self._habit_proactive = bool(cfg.get(CONF_HABIT_PROACTIVE, False))
    self._mcp_enabled = bool(cfg.get("mcp_enabled", False))
    self._patrol_enabled = False
    self._patrol_interval_minutes = 15
    self._patrol_scope_space_ids: tuple[str, ...] = ()
    self._patrol_excluded_space_ids: tuple[str, ...] = ()
    self._patrol_quiet_hours_start = ""
    self._patrol_quiet_hours_end = ""
    self._patrol_low_risk_entity_ids: tuple[str, ...] = ()
    self._patrol_last_automatic_submit_monotonic = 0.0
    self._ai_patrol_last_automatic_submit_monotonic = 0.0
    self._ai_patrol_retry_space_ids: tuple[str, ...] = ()
    self._ai_patrol_retry_not_before_monotonic = 0.0
    self._frigate_enabled = bool(cfg.get(CONF_FRIGATE_ENABLED, False))

    self._license_key: str = str(cfg.get(CONF_LICENSE_KEY) or "").strip()
    self._license_tier: str = LICENSE_TIER_FREE
    self._license_expires: str = ""
    self._license_instance_id: str = ""
    self._license_verified_at: float = 0.0
    self._license_valid: bool = False
    self._license_from_cache: bool = False

    self._db: Any = None
    self._backup_manager: Any = None
    self._addon_client: Any = None
    self._output_ledger_publisher: Any = None
    self._internal_event_bridge: Any = None
    self._pairing_view: Any = None
    self._circadian_engine: Any = None
    self._circadian_auto_adjust: bool = False
    self._addon_repair_issue_active = False
    self._addon_repair_first_failure_at: float | None = None
    self._addon_repair_failure_count = 0
    self._addon_repair_last_check_at = 0.0
    self._addon_repair_last_error = ""
    self._addon_repair_sync_pending = False
    self._addon_sync_failures: dict[str, int] = {}

    self._tts_service: str = str(cfg.get(CONF_TTS_SERVICE) or "").strip()
    self._tts_target: str = str(cfg.get(CONF_TTS_TARGET) or "").strip()
    self._tts_level: int = int(cfg.get(CONF_TTS_LEVEL, TTS_LEVEL_OFF))
    self._transactions_cache: list[dict] = []
    self._service_call_errors: dict[str, dict[str, Any]] = {}
    self._inflight_smartagent_state_feedback: dict[str, dict[str, Any]] = {}
    self._active_service_correlation_ids: dict[Any, str] = {}
    self._native_execution_attribution: Any = None
    self._last_live_presence_guard_status: dict[str, Any] = {}
    self._last_presence_guard_conflict: dict[str, Any] = {}
    self._last_turnoff_presence_guard_detail: dict[str, Any] = {}
    self._correction_suppressions_cache: list[dict[str, Any]] = []
    self._correction_suppressions_cache_refresh_at: float = 0.0

    self._env_feedback_tasks: list[dict] = []
    self._env_feedback_lock = asyncio.Lock()
    self._inference_lock = asyncio.Lock()
    self._room_inference_locks: dict[str, asyncio.Lock] = {}
    self._analysis_lock = asyncio.Lock()
    self._pending_habit_suggestion: dict | None = None
    self._habit_suggest_cooldown: dict[str, float] = {}
    self._habit_suggest_timeout_handle: Any = None
    self._energy_stats: list[dict] | None = None
    self._energy_stats_error: dict[str, str] | None = None


def _init_frigate_and_catalog_state(self: Any, *, integration_version: str) -> None:
    self._frigate_count_timers: dict[str, Any] = {}
    self._frigate_count_last_trigger: dict[str, tuple[float, int]] = {}
    self._frigate_mqtt_unsub: Any = None
    self._frigate_events_cache: OrderedDict[str, dict] = OrderedDict()
    self._frigate_zone_last_trigger: dict[str, float] = {}
    self._frigate_mqtt_debounce_timers: dict[str, Any] = {}
    self._frigate_zone_occupancy: dict[str, dict[str, int]] = {}
    self._frigate_event_counted_zones: dict[str, set[str]] = {}
    self._frigate_visual_descriptions: OrderedDict[str, str] = OrderedDict()
    self._vision_provider: Any = None
    self._frigate_camera_activity: dict[str, dict] = {}
    self._frigate_activity_last_analyzed: dict[str, float] = {}
    self._critical_frigate_event: dict | None = None

    self._voice_status = "idle"
    self._voice_reply = ""
    self._last_stt_text = ""
    self._scene_last_exec: dict[str, float] = {}
    self._last_patrol_snapshot: str = ""
    self._patrol_no_change_count: int = 0
    self._last_inference_result: dict | None = None
    self._pending_verifications: list[dict] = []
    self._pairing_mode_end_time: float = 0
    self._express_token: str = ""
    self._skip_next_reload = False

    self._integration_version = integration_version
    self.status_text = "正在初始化"
    self.last_action_text = ""
    self.last_correction_text = ""
    self.terminal_log_html = ""
    self.sys_log_html = ""
    self.sys_log_html_short = ""

    self.device_info: dict[str, dict] = {}
    self._environment_context_device_info: dict[str, dict[str, Any]] = {}
    self._habits: list[tuple[str, bool]] = []
    self._rules: list[tuple[str, bool]] = []
    self._habit_assets: list[dict[str, Any]] = []
    self._rule_assets: list[dict[str, Any]] = []
    self._presence_inference: Any = None
    self._fusion_registry: Any = None

    self._ha_scripts: list[dict] = []
    self._ha_scenes: list[dict] = []
    self._ha_automations: list[dict] = []
    self._automation_managed_sensors: set[str] = set()
    self._automation_managed_devices: dict[str, set[str]] = {}
    self._automation_managed_device_entities: dict[str, set[str]] = {}
    self._automation_executing: dict[str, float] = {}

    self._memory_retention_days = MEMORY_RETENTION_DAYS
    self._action_quality_cache: dict = {}
    self._ai_scenes_cache: list[dict] = []
    self._ai_scenes_read_error: BaseException | None = None


def init_coordinator_runtime_state(
    self: Any,
    data: Mapping[str, Any] | None = None,
    *,
    config_dir: str = "",
    integration_version: str = "unknown",
) -> None:
    """Initialize all pure in-memory attributes on ``SmartAgentCoordinator``."""
    cfg = dict(data) if data is not None else {}
    _init_core_and_engine_state(self, cfg, config_dir=config_dir)
    _init_showroom_and_brand_state(self, cfg)
    _init_listener_and_presence_state(self, cfg)
    _init_collaborators_and_execution_state(self, cfg)
    _init_frigate_and_catalog_state(self, integration_version=integration_version)
