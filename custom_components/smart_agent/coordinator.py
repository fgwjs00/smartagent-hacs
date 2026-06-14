"""
SmartAgentCoordinator — 主协调器（生命周期、UI 状态、调度入口）。

拆分结构：
    coordinator.py  ← 本文件：__init__、生命周期、UI 状态、对外接口
    database.py     ← SQLite 数据层（建表、迁移、CRUD、查询）
    inference.py    ← AI 推理（Prompt 构建、API 调用、JSON 解析）
    actions.py      ← 动作执行（路由、验证、重试、质量统计）
    listeners.py    ← 事件监听（状态变化处理、存在传感器去抖）
    patrol.py       ← 巡检 & 行为分析（定时扫描、习惯建议）
    protection.py   ← 保护机制（用户覆盖、自动化冲突、在场守卫）
    devices.py      ← 设备管理（发现、批量添加、管辖域配置、习惯/规则 CRUD）
"""
from __future__ import annotations

import asyncio
import html as _html
import json
import logging
import logging.handlers
import os
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any

# HA 2025.x 阻塞检测修复：不在模块级（事件循环内）执行任何 open() 调用。
# 版本号在 _blocking_init()（executor 线程）中懒加载，模块导入时仅占位。
# 与 manifest.json 的 version 字段保持一致，两者同步更新。
_SA_VERSION: str = "unknown"
_ROOM_INFERENCE_LOCKS_HARD_LIMIT = 256

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    async_track_utc_time_change,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .actions import ActionsMixin
from .database import DatabaseMixin
from .devices import DevicesMixin
from .frigate import FrigateMixin
from .ha_adapter import async_call_service
from .license import LicenseMixin
from .listeners import ListenersMixin
from .api import SmartAgentPairingView, SmartAgentAuthPageView, SmartAgentPairConfirmView

from .const import (
    ACTION_PARAM_KEYS_COMMON,
    CONF_AI_ENABLED,
    CONF_COOLDOWN,
    CONF_ENGINE,
    CONF_FRIGATE_ENABLED,
    DOMAIN,
    CONF_LICENSE_KEY,
    CONF_HABIT_PROACTIVE,
    CONF_LEARNING_MODE,
    CONF_MODE,
    CONF_SENSORS_MUTED,
    CONF_TTS_SERVICE,
    CONF_TTS_TARGET,
    CONF_TTS_LEVEL,
    TTS_LEVEL_OFF,
    LICENSE_TIER_FREE,
    LICENSE_TIER_BIZ,
    CONF_SHOWROOM_SCENE,
    CONF_SHOWROOM_CUSTOM_PROMPT,
    CONF_SHOWROOM_SCENE_OVERRIDES,
    CONF_OLLAMA_URL,
    CONF_OLLAMA_MODEL,
    CONF_ONLINE_API_KEY,
    CONF_ONLINE_BASE_URL,
    CONF_ONLINE_MODEL,
    CONF_CONFIDENCE_AUTO,
    CONF_CONFIDENCE_NOTIFY,
    CONF_CLOUD_FALLBACK,
    DEFAULT_CONFIDENCE_AUTO,
    DEFAULT_CONFIDENCE_NOTIFY,
    CONF_VISION_ENABLED,
    CONF_VISION_ENGINE,
    CONF_VISION_MODEL,
    CONF_SHOWROOM_BIZ_START,
    CONF_SHOWROOM_BIZ_END,
    CONF_SHOWROOM_AREA_NAME,
    CONF_SHOWROOM_EXCLUDED_SUBAREAS,
    CONF_SHOWROOM_ZONE_MAP,
    DEFAULT_SHOWROOM_BIZ_START,
    DEFAULT_SHOWROOM_BIZ_END,
    DEFAULT_SHOWROOM_AREA_NAME,
    DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS,
    DEFAULT_SHOWROOM_ZONE_MAP,
    ZONE_ROLE_DISPLAY,
    ZONE_ROLE_DEFAULT,
    CONF_BRAND_NAME,
    CONF_BRAND_PRIMARY_COLOR,
    CONF_BRAND_LOGO_URL,
    CONF_DEPLOY_NAME,
    DEFAULT_BRAND_NAME,
    DEFAULT_BRAND_PRIMARY_COLOR,
    DEFAULT_BRAND_LOGO_URL,
    DEFAULT_DEPLOY_NAME,
    parse_biz_time,
    format_biz_time,
    ENGINE_ONLINE,
    ESCALATION_COUNT,
    ESCALATION_GUARD_SEC,
    ESCALATION_WINDOW_MIN,
    CONF_LOG_RETENTION,
    CONF_ADDON_AUTH_TOKEN,
    CONF_ADDON_BASE_URL,
    DB_FILENAME,
    DOMAIN,
    LOG_FILENAME,
    LOG_MEM_MAX,
    LOG_RETENTION_DAYS,
    MEMORY_RETENTION_DAYS,
    MERGE_WINDOW_SECONDS,
    MODE_HOME,
    MODE_SHOWROOM,
    NOTIFY_DEDUP_SECONDS,
    OVERRIDE_WINDOW_SECONDS,
    PRIORITY_AI_LEARNED,
    PRIORITY_GUARD_WINDOWS,
    PRIORITY_LABELS,
    PATTERN_FILENAME,
    SHOWROOM_SCENES,
    SOURCE_AUTOMATION,
    SOURCE_DASHBOARD,
    SOURCE_EMERGENCY,
    SOURCE_LABELS,
    SOURCE_PHYSICAL,
    SOURCE_PRIORITY_MAP,
    SOURCE_VOICE,
    STARTUP_GRACE_SECONDS,
    TARGET_DOMAINS,
    TERMINAL_LOGS_MAX,
    DEVICE_CAP_KEY_COVERAGE_SPACES,
    DEVICE_CAP_KEY_SHARED_FIXTURE,
    SPACE_SNAPSHOT_KEY_ROOM_TOPOLOGY,
    SPACE_SNAPSHOT_KEY_SHARED_CONTROL_ZONES,
    SPACE_SNAPSHOT_KEY_SHOWROOM_ZONE_MAP,
)

_LOGGER = logging.getLogger(__name__)
_PRIORITY_MAP_HARD_LIMIT = 500
_USER_OP_HISTORY_HARD_LIMIT = 500
_EMERGENCY_KEYWORDS = frozenset((
    "smoke", "gas", "leak", "flood", "alarm", "security", "fire", "co2",
    "烟雾", "烟感", "燃气", "漏水", "水浸", "告警", "警报", "火灾", "安防",
))
_EMERGENCY_EXCLUDE = frozenset((
    "gas_meter", "gas_consumption", "gas_cost",
    "alarm_clock", "alarm_volume",
    "security_camera", "security_mode",
    "fire_tv", "fireplace",
))
_EMERGENCY_THRESHOLDS: dict[str, float] = {
    "temperature": 55.0,
    "carbon_monoxide": 50.0,
    "carbon_dioxide": 5000.0,
    "gas": 20.0,
    "pm25": 500.0,
}


class SmartAgentCoordinator(
    DatabaseMixin,
    ActionsMixin,
    ListenersMixin,
    DevicesMixin,
    FrigateMixin,
    LicenseMixin,
    DataUpdateCoordinator,
):
    """
    主协调器：整合所有 Mixin，负责生命周期管理、UI 状态维护、对外服务接口。

    方法分布：
        DatabaseMixin   → _init_memory_db / _migrate_json_config / _load_config
                          _db_exec / _async_db_exec / _query_events / _async_query
                          _record_event / _cleanup_old_memory
                          _record_action_result / _get_action_quality_stats
        ActionsMixin    → _normalize_action / _fuzzy_match_entity / _find_associated_script
                          _execute_actions / _do_call_service / _verify_pending_actions
        ListenersMixin  → _should_trigger / _effective_cooldown
                          _schedule_inference / _flush_triggers
                          _get_time_brightness / _find_room_lights
                          _make_state_handler / _refresh_listeners
        DevicesMixin    → get_device_name / _get_entity_area
                          _async_discover_devices / async_batch_add_devices
                          async_svc_add/delete/update_device / async_dev_add/delete
                          async_refresh_device_areas
                          async_set_device_control_mode / async_batch_set_control_mode
                          habit/rule CRUD / async_delete_behavior_pattern
        FrigateMixin    → _init_frigate_mqtt / _async_start_frigate_mqtt / _async_stop_frigate_mqtt
                          _on_frigate_mqtt_event / _update_zone_occupancy
                          _schedule_frigate_inference / _build_frigate_trigger
                          get_frigate_zone_summary / get_recent_frigate_events
    """

    _OFF_STATES = frozenset(("off", "closed", "idle", "standby", "locked"))
    _AUTOMATION_EXEC_WINDOW = 30
    _USER_OVERRIDE_PROTECTION = 120
    _USER_MANUAL_WINDOW = 1800

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize and load config from entry (data + options)."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=5))
        self._entry = entry
        self._config_dir = hass.config.config_dir
        self._memory_db = os.path.join(self._config_dir, DB_FILENAME)
        self._pattern_file = os.path.join(self._config_dir, PATTERN_FILENAME)
        
        # 文件日志记录器（handler 延迟到 async_start_listeners 中在 executor 里初始化，避免阻塞事件循环）
        self._file_logger = logging.getLogger(f"{DOMAIN}.system")
        self._file_logger.setLevel(logging.INFO)
        self._file_logger.handlers.clear()
        self._file_logger.propagate = False

        # Merge entry.data and entry.options (options override)
        data = {**(entry.data or {}), **(entry.options or {})}
        self.engine = data.get(CONF_ENGINE, "local")
        self.ollama_url = data.get(CONF_OLLAMA_URL, "http://127.0.0.1:11434")
        self.ollama_model = data.get(CONF_OLLAMA_MODEL, "qwen3-smarthome")
        self._online_api_key = data.get(CONF_ONLINE_API_KEY, "")
        self.online_base_url = data.get(CONF_ONLINE_BASE_URL, "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.online_model = data.get(CONF_ONLINE_MODEL, "qwen3.5-flash")
        self.confidence_auto = int(data.get(CONF_CONFIDENCE_AUTO, DEFAULT_CONFIDENCE_AUTO))
        self.confidence_notify = int(data.get(CONF_CONFIDENCE_NOTIFY, DEFAULT_CONFIDENCE_NOTIFY))
        self.cooldown = int(data.get(CONF_COOLDOWN, 60))
        self.showroom_biz_start_min: int = parse_biz_time(data.get(CONF_SHOWROOM_BIZ_START, DEFAULT_SHOWROOM_BIZ_START))
        self.showroom_biz_end_min: int   = parse_biz_time(data.get(CONF_SHOWROOM_BIZ_END, DEFAULT_SHOWROOM_BIZ_END))
        # 兼容旧版：保留整数小时属性，供仍引用旧属性的代码过渡（将逐步废弃）
        self.showroom_biz_start: int = self.showroom_biz_start_min // 60
        self.showroom_biz_end: int   = self.showroom_biz_end_min // 60
        self.showroom_area_name: str = (data.get(CONF_SHOWROOM_AREA_NAME, DEFAULT_SHOWROOM_AREA_NAME) or "").strip()
        _excl_raw: str = (data.get(CONF_SHOWROOM_EXCLUDED_SUBAREAS, DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS) or "").strip()
        self.showroom_excluded_subareas: list[str] = [s.strip() for s in _excl_raw.split(",") if s.strip()] if _excl_raw else []
        # 区域角色映射（v4.11.0）：展厅 → display，体验区 → experience，工作区 → work
        _zone_map_raw: str = (data.get(CONF_SHOWROOM_ZONE_MAP, DEFAULT_SHOWROOM_ZONE_MAP) or "").strip()
        try:
            import json as _json_coord
            self._showroom_zone_map: dict[str, str] = _json_coord.loads(_zone_map_raw) if _zone_map_raw else {}
        except (ValueError, TypeError):
            self._showroom_zone_map = {}
        self._last_showroom_cmd_time: float = 0.0  # 记录最近一次操作员指令时间，用于巡检抑制
        # Phase 11.3: 记录各房间最近一次"离开触发关灯"的时间戳
        # 巡检在冷却期（5分钟）内不会对同一房间重复发起推理，防止巡检覆盖离开决策
        self._last_departure_turnoff_time: dict[str, float] = {}

        # ── 品牌化/白标配置 ────────────────────────────────────────────────────
        self.brand_name: str         = (data.get(CONF_BRAND_NAME, DEFAULT_BRAND_NAME) or DEFAULT_BRAND_NAME).strip()
        self.brand_primary_color: str = (data.get(CONF_BRAND_PRIMARY_COLOR, DEFAULT_BRAND_PRIMARY_COLOR) or DEFAULT_BRAND_PRIMARY_COLOR).strip()
        self.brand_logo_url: str     = (data.get(CONF_BRAND_LOGO_URL, DEFAULT_BRAND_LOGO_URL) or "").strip()
        self.deploy_name: str        = (data.get(CONF_DEPLOY_NAME, DEFAULT_DEPLOY_NAME) or "").strip()

        self._startup_grace = STARTUP_GRACE_SECONDS
        self._startup_time = time.time()
        self._last_inference: dict[str, float] = {}
        self._active_timers: dict[str, Any] = {}
        self._last_ai_actions: dict[str, dict] = {}
        self._user_overrides: dict[str, dict] = {}
        self._user_overrides_lock = threading.Lock()
        self._user_manual_actions: dict[str, dict] = {}
        self._user_manual_actions_lock = threading.Lock()
        self._pending_triggers: list[dict] = []
        self._pending_triggers_lock = threading.Lock()
        self._pending_trigger_controllable: dict[str, str] = {}
        self._batch_trigger_controllable: dict[str, str] = {}
        self._merge_timer_unsub: Any = None
        self._scan_timer_unsub: Any = None
        self._habit_check_timer_unsub: Any = None
        self._last_notify: dict[str, float] = {}
        self._terminal_logs: list[str] = []
        self._action_history_structured: list[str] = [] # 结构化动作历史
        self._sys_logs: list[str] = []
        self._sys_log_lock = threading.Lock()  # P1修复：保护 _sys_logs 跨线程读写
        self._log_retention_days: int = int(data.get(CONF_LOG_RETENTION, LOG_RETENTION_DAYS))
        self._pattern_summary = ""

        # 初始化优先级仲裁引擎
        self._init_priority_system()
        self._listener_removers: list = []
        self._enabled = bool(data.get(CONF_AI_ENABLED, True))
        self._sensors_muted = bool(data.get(CONF_SENSORS_MUTED, False))
        self._learning_mode = bool(data.get(CONF_LEARNING_MODE, False))
        self._habit_proactive = bool(data.get(CONF_HABIT_PROACTIVE, False))
        self._frigate_enabled = bool(data.get(CONF_FRIGATE_ENABLED, False))  # 默认关闭，需手动启用
        # Phase 5: 联网工具与知识库
        from .tools import ToolRegistry
        self._tools = ToolRegistry(hass, data)
        self._cloud_fallback = bool(data.get(CONF_CLOUD_FALLBACK, False))
        self._vision_enabled = bool(data.get(CONF_VISION_ENABLED, False))
        self._vision_engine = data.get(CONF_VISION_ENGINE, ENGINE_ONLINE)
        self._vision_model = (data.get(CONF_VISION_MODEL) or "qwen3.5-omni-flash").strip()
        # License
        self._init_license()
        self._license_key = (data.get(CONF_LICENSE_KEY) or "").strip()
        # Add-on 客户端（显式 URL 优先；留空时按端口回退）
        from .addon_client import AddOnClient, derive_addon_gateway_base_url
        from .const import CONF_ADDON_PORT, DEFAULT_ADDON_PORT
        _addon_token = (data.get(CONF_ADDON_AUTH_TOKEN) or "").strip()
        _addon_base_url = (data.get(CONF_ADDON_BASE_URL) or "").strip()
        if not _addon_base_url:
            _addon_base_url = derive_addon_gateway_base_url(self._get_ha_url())
        _addon_port = int(data.get(CONF_ADDON_PORT) or DEFAULT_ADDON_PORT)
        self._addon_client = AddOnClient(base_url=_addon_base_url, port=_addon_port, auth_token=_addon_token)
        from .internal_event_bridge import InternalEventBridge
        self._internal_event_bridge = InternalEventBridge(
            self._addon_client,
            log_callback=self._sys_log,
        )
        # TTS 配置
        self._tts_service: str = (data.get(CONF_TTS_SERVICE) or "").strip()
        self._tts_target: str = (data.get(CONF_TTS_TARGET) or "").strip()
        self._tts_level: int = int(data.get(CONF_TTS_LEVEL, TTS_LEVEL_OFF))
        self._transactions_cache: list[dict] = []
        self._env_feedback_tasks: list[dict] = []
        self._env_feedback_lock = asyncio.Lock()
        # Phase A: DeviceAdapter — AI Core 与 HA 设备层解耦（可测试化）
        # 当前唯一实现：HAAdapter（通过 SmartAgent command envelope）
        from .device_adapter import HAAdapter
        self._device_adapter = HAAdapter(hass)
        # 全局推理互斥锁：作为无法提取房间名时的兜底（如巡检、定时、位置变化触发）
        self._inference_lock = asyncio.Lock()
        # 按房间隔离的推理锁：不同房间的 LLM 推理可并发执行，互不阻塞
        # key=房间名, value=asyncio.Lock()；动态创建，生命周期与 coordinator 相同
        self._room_inference_locks: dict[str, asyncio.Lock] = {}
        # 行为分析互斥锁：防止手动触发与定时触发重叠执行
        self._analysis_lock = asyncio.Lock()
        self._pending_habit_suggestion: dict | None = None
        self._habit_suggest_cooldown: dict[str, float] = {}
        self._habit_suggest_timeout_handle: Any = None
        self._glitch_history: dict[str, list[float]] = {}      # 闪断检测历史
        self._glitch_suppressed: dict[str, float] = {}         # 闪断抑制期
        self._behavior_patterns_cache: list[dict] = []
        self._room_topology_cache: dict[str, set[str]] = {}  # P1-2: room → {adjacent rooms}
        self._room_topology_cache_updated_at: float = 0.0
        self._room_topology_refresh_pending: bool = False
        self._energy_stats: list[dict] = []
        self._mode = data.get(CONF_MODE, MODE_HOME)
        _saved_scene = data.get(CONF_SHOWROOM_SCENE, "") or ""
        self._showroom_scene: str | None = _saved_scene if _saved_scene in SHOWROOM_SCENES else None
        self._showroom_custom_prompt: str = (data.get(CONF_SHOWROOM_CUSTOM_PROMPT, "") or "").strip()
        _raw_overrides = data.get(CONF_SHOWROOM_SCENE_OVERRIDES, "")
        try:
            if isinstance(_raw_overrides, dict):
                self._showroom_scene_overrides = _raw_overrides
            elif isinstance(_raw_overrides, str):
                _parsed_overrides = json.loads(_raw_overrides) if _raw_overrides else {}
                self._showroom_scene_overrides = _parsed_overrides if isinstance(_parsed_overrides, dict) else {}
            else:
                # 兼容历史异常类型（如 list/int），避免推理阶段 .items() / 索引报错
                self._showroom_scene_overrides = {}
        except (json.JSONDecodeError, TypeError):
            self._showroom_scene_overrides = {}

        # 展厅模式下的置信度与冷却（更积极执行）
        self._SHOWROOM_COOLDOWN = 15
        self._SHOWROOM_CONFIDENCE_AUTO = 70
        self._SHOWROOM_CONFIDENCE_NOTIFY = 40

        # 存在传感器去抖（防止 mmWave/存在雷达高频抖动淹没推理队列）
        self._presence_off_timers: dict[str, Any] = {}
        self._presence_last_on: dict[str, float] = {}
        self._presence_on_start: dict[str, float] = {}
        self._presence_flap_history: dict[str, list[float]] = {}      # 高频反转历史
        self._presence_flap_suppressed: dict[str, float] = {}         # 抖动风暴抑制期

        # 自我合理化防护限流（避免同一触发在短时间内反复对抗重试）
        self._rational_guard_last_retry: dict[str, float] = {}

        # Frigate 人数传感器防抖（防止摄像头检测抖动反复触发推理）
        self._frigate_count_timers: dict[str, Any] = {}          # 待确认的防抖计时器取消句柄
        self._frigate_count_last_trigger: dict[str, tuple[float, int]] = {}  # (时间戳, 人数)

        # Frigate MQTT 深度集成状态（Phase 7A）
        self._init_frigate_mqtt()
        
        # 语音交互状态（UI 同步用）
        self._voice_status = "idle"
        self._voice_reply = ""
        self._last_stt_text = ""

        # 场景/脚本重复执行冷却
        self._scene_last_exec: dict[str, float] = {}

        # 关键视觉事件追踪（Phase 7B）
        self._critical_frigate_event: dict | None = None

        # 注册配对 API 视图
        self._pairing_view = SmartAgentPairingView(self)
        self.hass.http.register_view(self._pairing_view)
        self.hass.http.register_view(SmartAgentAuthPageView(self))
        self.hass.http.register_view(SmartAgentPairConfirmView(self))

        # 注册配对授权服务
        self.hass.services.async_register(
            DOMAIN, "authorize_pairing", self.async_svc_authorize_pairing
        )

        # 注册 AI 纠错服务（Phase 7B）
        self.hass.services.async_register(
            DOMAIN, "report_correction", self.async_svc_report_correction
        )
        # 注册忽略服务：从近期操作列表移除条目（不记入学习）
        self.hass.services.async_register(
            DOMAIN, "dismiss_ai_action",
            self.async_svc_dismiss_ai_action,
        )

        # 巡检设备状态快照（用于检测是否有变化，无变化则跳过推理节省算力）
        self._last_patrol_snapshot: str = ""
        self._patrol_no_change_count: int = 0

        # 重复推理抑制（记录上次推理结果，避免重复调用被冷却拦截的推理）
        self._last_inference_result: dict | None = None

        # 动作执行结果追踪
        self._pending_verifications: list[dict] = []

        # 极速配对模式（限时开启，无需扫码确认）
        self._pairing_mode_end_time: float = 0
        self._express_token: str = ""  # 极速配对时预创建的 HA LLAT
        
        # 运行时 options 更新标志：为 True 时跳过重载
        self._skip_next_reload = False

        # UI state (entities read these)
        self.status_text = "正在初始化"
        self.last_action_text = ""
        self.last_correction_text = "" # 最新一次修正记录
        self.terminal_log_html = ""
        self.sys_log_html = ""
        self.sys_log_html_short = ""  # 最新 30 条，用于 sensor 属性（避免超 16KB）

        self.device_info: dict[str, dict] = {}
        self._habits: list[tuple[str, bool]] = []
        self._rules: list[tuple[str, bool]] = []

        # Phase 10.0: 虚拟在场推断引擎（无传感器家庭兜底）
        # 在 device_info 加载完成后（_async_setup 中）初始化
        self._presence_inference = None

        # Phase 12.0: 存在传感器融合域注册表（解决大开间/一镜多区误判）
        self._fusion_registry = None

        # HA 已有脚本/场景/自动化缓存（启动时和巡检时刷新）
        self._ha_scripts: list[dict] = []
        self._ha_scenes: list[dict] = []
        self._ha_automations: list[dict] = []
        self._automation_managed_sensors: set[str] = set()
        self._automation_managed_devices: dict[str, set[str]] = {}
        self._automation_executing: dict[str, float] = {}

        self._memory_retention_days = MEMORY_RETENTION_DAYS
        self._action_quality_cache: dict = {}

        # Phase 4: AI 场景缓存（_blocking_init 中加载）
        self._ai_scenes_cache: list[dict] = []

    def _blocking_init(self) -> None:
        """All blocking I/O initialization (DB, pattern file, config). Runs in executor."""
        # 在 executor 中安全读取 manifest.json（非事件循环，不触发 HA 阻塞检测器）
        global _SA_VERSION
        try:
            _mp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json")
            with open(_mp, encoding="utf-8") as _mf:
                _SA_VERSION = json.load(_mf).get("version", "unknown")
        except Exception:
            pass
        self._init_memory_db()
        self._load_config()
        # Phase 4: 加载 AI 场景缓存
        self._ai_scenes_cache = self._query_ai_scenes()
        # Layer 2: 加载近期事务缓存（最近 30 条）
        self._transactions_cache = self._query_recent_transactions(30)
        # 能耗分析：启动时执行一次，加载缓存
        try:
            self._energy_stats = self._get_device_usage_stats(days=7)
        except Exception:
            self._energy_stats = []

    def _get_ha_url(self) -> str:
        """获取 HA 的外部访问地址。"""
        from homeassistant.helpers.network import get_url
        try:
            return get_url(self.hass)
        except Exception:
            return "http://localhost:8123"

    def _enqueue_internal_event(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        ts: str | None = None,
    ) -> bool:
        """Thread-safe enqueue into the P1 HA-to-add-on storage bridge."""
        bridge = getattr(self, "_internal_event_bridge", None)
        if bridge is None:
            return False

        def _enqueue() -> None:
            bridge.enqueue(kind, payload, ts=ts)

        try:
            loop = getattr(self.hass, "loop", None)
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            if loop is not None and running_loop is loop:
                return bool(bridge.enqueue(kind, payload, ts=ts))
            if loop is not None:
                loop.call_soon_threadsafe(_enqueue)
                return True
            return bool(bridge.enqueue(kind, payload, ts=ts))
        except Exception as exc:
            _LOGGER.warning("[P1] internal event enqueue failed: %s", exc)
            return False

    # ── 系统日志 ──────────────────────────────────────────────────────────────

    def _sys_log(self, level: str, msg: str) -> None:
        """Append a system-level log entry and write to daily rotating file."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] [{level}] {msg}"
        if level == "ERROR":
            self._file_logger.error(msg)
        elif level == "WARN":
            self._file_logger.warning(msg)
        else:
            self._file_logger.info(msg)
        _LOGGER.debug("SysLog %s: %s", level, msg)
        # P1修复：_sys_log 同时从事件循环和 executor 线程调用，需要 threading.Lock 保护
        # asyncio.Lock 不适用于 executor 线程，必须使用 threading.Lock
        with self._sys_log_lock:
            self._sys_logs.insert(0, entry)
            if len(self._sys_logs) > LOG_MEM_MAX:
                self._sys_logs = self._sys_logs[:LOG_MEM_MAX]
            _snapshot = self._sys_logs[:30]
            _full_snapshot = self._sys_logs[:]
        self.sys_log_html = "".join(self._format_log_row(r) for r in _full_snapshot)
        # 供 sensor 属性使用的短版本（最新 30 条），避免 HA 16KB 属性超限
        self.sys_log_html_short = "".join(self._format_log_row(r) for r in _snapshot)

    @staticmethod
    def _format_log_row(r: str) -> str:
        """Format a single log entry into structured HTML with tag highlighting."""
        if "[ERROR]" in r:
            cls = "sl-e"
        elif "[WARN]" in r:
            cls = "sl-w"
        else:
            cls = "sl-i"
        safe = _html.escape(r)
        tag_map = {
            "[自触发保护]": "sl-tag-protect", "[保护]": "sl-tag-protect",
            "[用户操作]": "sl-tag-protect", "[冷却]": "sl-tag-protect",
            "[触发]": "sl-tag-trigger", "[事件]": "sl-tag-trigger",
            "[过滤]": "sl-tag-trigger", "[调度]": "sl-tag-trigger",
            "[Prompt]": "sl-tag-infer", "[推理]": "sl-tag-infer",
            "[执行]": "sl-tag-exec", "[动作]": "sl-tag-exec",
            "[原始动作]": "sl-tag-exec",
            "[巡检]": "sl-tag-patrol", "[启动]": "sl-tag-patrol",
            "[行为分析]": "sl-tag-patrol",
        }
        for tag, tag_cls in tag_map.items():
            escaped_tag = _html.escape(tag)
            if escaped_tag in safe:
                safe = safe.replace(escaped_tag, f'<span class="sl-tag {tag_cls}">{escaped_tag}</span>', 1)
                break
        if safe.startswith("["):
            close = safe.find("]")
            if close > 0:
                ts = safe[1:close]
                safe = f'<span class="sl-ts">[{ts}]</span>{safe[close+1:]}'
        return f'<div class="sl-row {cls}" data-level="{cls}">{safe}</div>'

    # ── UI 状态 ───────────────────────────────────────────────────────────────

    async def _async_update_status(self, status: str, last_action: str = "") -> None:
        """Update UI state (status, last_action, terminal_log)."""
        ts = datetime.now().strftime("%H:%M:%S")
        if last_action:
            self._terminal_logs.insert(0, f"[{ts}] {_html.escape(last_action)}")
            self._terminal_logs = self._terminal_logs[:TERMINAL_LOGS_MAX]
            # 维护结构化历史
            self._action_history_structured.insert(0, last_action)
            self._action_history_structured = self._action_history_structured[:10]
        # HA text 实体上限 255 字，超出部分截断（显示 … 提示）
        self.status_text = status[:254] if len(status) > 255 else status
        action_val = last_action or self.last_action_text
        self.last_action_text = (action_val[:253] + "…") if len(action_val) > 255 else action_val
        self.terminal_log_html = "<br/>".join(self._terminal_logs)
        self.async_set_updated_data({"status": self.status_text, "last_action": self.last_action_text,
                                     "terminal_log": self.terminal_log_html})

    def _notify_dedup(self, message: str, title: str) -> None:
        key = f"{title}:{message}"
        now = time.time()
        if now - self._last_notify.get(key, 0) < NOTIFY_DEDUP_SECONDS:
            return
        self._last_notify[key] = now
        self.hass.async_create_task(
            async_call_service(
                self.hass,
                "persistent_notification",
                "create",
                {"message": message, "title": title},
            )
        )

    async def _tts_speak(self, text: str, min_level: int = 1) -> None:
        """通用 TTS 播报接口。

        当 _tts_level >= min_level 且已配置 TTS 服务/目标实体时发送语音播报。
        min_level 对应:
          1 = TTS_LEVEL_SPEAK_ONLY   (AI speak 字段)
          2 = TTS_LEVEL_ACTIONS      (动作执行摘要)
          3 = TTS_LEVEL_ALL          (系统提示/习惯建议)
        """
        if not text:
            return
        if self._tts_level < min_level:
            return
        svc = self._tts_service.strip()
        target = self._tts_target.strip()
        if not svc or not target or "." not in svc:
                return
        domain, service = svc.split(".", 1)
        try:
            await async_call_service(
                self.hass,
                domain, service,
                {"entity_id": target, "message": text},
            )
            self._sys_log("INFO", f"[TTS] 播报: {text[:60]}")
        except Exception as exc:
            self._sys_log("WARN", f"[TTS] 播报失败: {exc}")

    def _init_priority_system(self) -> None:
        self._device_priority_map: dict[str, dict] = {}
        self._user_op_history: dict[str, list[float]] = {}
        self._global_suppress_until: float = 0.0
        self._global_suppress_reason: str = ""

    @staticmethod
    def _extract_entity_ids_from_config(config_items: list | dict | None, out: set[str]) -> None:
        if config_items is None:
            return
        if isinstance(config_items, dict):
            config_items = [config_items]
        if not isinstance(config_items, list):
            return
        for item in config_items:
            if not isinstance(item, dict):
                continue
            for key in ("entity_id", "device_id", "target"):
                val = item.get(key)
                if isinstance(val, str) and "." in val:
                    out.add(val)
                elif isinstance(val, list):
                    for v in val:
                        if isinstance(v, str) and "." in v:
                            out.add(v)
                elif isinstance(val, dict):
                    for v in val.values():
                        if isinstance(v, str) and "." in v:
                            out.add(v)
                        elif isinstance(v, list):
                            for vv in v:
                                if isinstance(vv, str) and "." in vv:
                                    out.add(vv)
            for sub_key in ("then", "else", "sequence", "action", "actions"):
                sub = item.get(sub_key)
                if sub:
                    SmartAgentCoordinator._extract_entity_ids_from_config(sub, out)

    def _refresh_ha_resources(self) -> None:
        scripts, scenes, autos = [], [], []
        managed_sensors: set[str] = set()
        managed_devices: dict[str, set[str]] = {}
        for state in self.hass.states.async_all("script"):
            scripts.append({"entity_id": state.entity_id, "name": state.attributes.get("friendly_name", state.entity_id)})
        for state in self.hass.states.async_all("scene"):
            scenes.append({"entity_id": state.entity_id, "name": state.attributes.get("friendly_name", state.entity_id)})
        for state in self.hass.states.async_all("automation"):
            autos.append({
                "entity_id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.entity_id),
                "state": state.state,
            })

        try:
            auto_configs = self.hass.data.get("automation.config", {}) or {}
            for auto_state in self.hass.states.async_all("automation"):
                if auto_state.state != "on":
                    continue
                auto_id = auto_state.attributes.get("id", "")
                auto_name = auto_state.attributes.get("friendly_name", auto_state.entity_id)
                cfg = auto_configs.get(auto_id, {}) if auto_id else {}
                trigger_eids: set[str] = set()
                action_eids: set[str] = set()
                self._extract_entity_ids_from_config(cfg.get("trigger", cfg.get("triggers", [])), trigger_eids)
                self._extract_entity_ids_from_config(cfg.get("action", cfg.get("actions", [])), action_eids)
                self._extract_entity_ids_from_config(cfg.get("condition", cfg.get("conditions", [])), trigger_eids)
                for eid in trigger_eids:
                    if eid.startswith(("binary_sensor.", "sensor.")):
                        managed_sensors.add(eid)
                for eid in action_eids:
                    domain = eid.split(".", 1)[0]
                    if domain in ("light", "switch", "fan", "cover", "climate", "media_player", "script", "scene"):
                        managed_devices.setdefault(eid, set()).add(auto_name)
        except Exception as exc:
            self._sys_log("WARN", f"[资源] 自动化配置解析出错（不影响核心功能）: {exc}")

        self._ha_scripts = scripts
        self._ha_scenes = scenes
        self._ha_automations = autos
        self._automation_managed_sensors = managed_sensors
        self._automation_managed_devices = managed_devices
        self._sys_log("INFO", f"[资源] HA资源刷新: 脚本={len(scripts)} 场景={len(scenes)} 自动化={len(autos)}")

    def _get_room_occupancy_map(self) -> dict[str, list[tuple[str, str]]]:
        getter = getattr(self, "get_presence_snapshot", None)
        if callable(getter):
            try:
                presence_snapshot = getter()
            except Exception:
                presence_snapshot = None
            rooms = presence_snapshot.get("rooms") if isinstance(presence_snapshot, dict) else None
            canonical: dict[str, list[tuple[str, str]]] = {}
            if isinstance(rooms, dict):
                room_items = rooms.items()
            elif isinstance(rooms, list):
                room_items = (
                    (
                        str(item.get("room") or item.get("space") or item.get("space_id") or ""),
                        item,
                    )
                    for item in rooms
                    if isinstance(item, dict)
                )
            else:
                room_items = ()
            for raw_room, payload in room_items:
                if not isinstance(payload, dict):
                    continue
                room = str(raw_room or payload.get("room") or payload.get("space") or payload.get("space_id") or "").strip()
                if not room:
                    continue
                state = str(payload.get("state") or "").strip().lower()
                if state in {"occupied", "present", "on", "home", "motion", "person"}:
                    mapped_state = "on"
                    evidence_ids = payload.get("occupied_evidence_ids") or payload.get("evidence_ids") or ()
                elif state in {"vacant", "clear", "off", "away", "none", "idle", "empty"}:
                    mapped_state = "off"
                    evidence_ids = payload.get("vacant_evidence_ids") or payload.get("evidence_ids") or ()
                else:
                    mapped_state = "unknown"
                    evidence_ids = payload.get("evidence_ids") or payload.get("occupied_evidence_ids") or payload.get("vacant_evidence_ids") or ()
                if isinstance(evidence_ids, str):
                    evidence = [evidence_ids]
                else:
                    evidence = [str(eid or "") for eid in evidence_ids or () if str(eid or "").strip()]
                if not evidence:
                    evidence = [f"presence.{room}"]
                canonical[room] = [(eid, mapped_state) for eid in evidence]
            if canonical:
                return canonical

        occ: dict[str, list[tuple[str, str]]] = {}
        for entity_id, info in self.device_info.items():
            if not entity_id.startswith(("binary_sensor.", "sensor.", "person.", "device_tracker.")):
                continue
            name = str(info.get("name") or entity_id).lower()
            eid_lower = entity_id.lower()
            if entity_id.startswith(("binary_sensor.", "sensor.")) and not any(
                kw in eid_lower or kw in name for kw in self._PRESENCE_KW
            ):
                continue
            room = str(info.get("room") or info.get("area") or "").strip()
            if not room:
                continue
            state = self.hass.states.get(entity_id)
            occ.setdefault(room, []).append((entity_id, state.state if state else "unknown"))
        return occ

    def _get_room_person_counts(self) -> dict[str, int]:
        return {}

    def _build_locked_people_rules(self) -> list[dict]:
        return []

    def _is_occupancy_active(self, entity_id: str) -> bool:
        room = str(self.device_info.get(entity_id, {}).get("room") or "").strip()
        if not room:
            return False
        return any(state == "on" for _, state in self._get_room_occupancy_map().get(room, []))

    def _classify_source(self, entity_id: str, source_type: str, context: dict | None = None) -> str:
        eid_lower = entity_id.lower()
        name = self.device_info.get(entity_id, {}).get("name", "").lower()
        if any(kw in eid_lower or kw in name for kw in _EMERGENCY_KEYWORDS):
            if not any(ex in eid_lower for ex in _EMERGENCY_EXCLUDE):
                return SOURCE_EMERGENCY
        state_obj = self.hass.states.get(entity_id)
        if state_obj and entity_id.startswith("sensor."):
            dev_class = (state_obj.attributes.get("device_class") or "").lower()
            threshold = _EMERGENCY_THRESHOLDS.get(dev_class)
            if threshold is not None:
                try:
                    if float(state_obj.state) >= threshold:
                        return SOURCE_EMERGENCY
                except (ValueError, TypeError):
                    pass
        if source_type == "自动化/脚本":
            return SOURCE_AUTOMATION
        if source_type == "用户界面":
            return SOURCE_DASHBOARD
        if source_type == "语音":
            return SOURCE_VOICE
        return SOURCE_PHYSICAL

    def _record_device_operation(self, entity_id: str, source: str, new_state: str, params: dict | None = None) -> dict:
        now = time.time()
        priority = SOURCE_PRIORITY_MAP.get(source, PRIORITY_AI_LEARNED)
        guard_until = now + PRIORITY_GUARD_WINDOWS.get(priority, 120)
        if priority == 1:
            history = self._user_op_history.setdefault(entity_id, [])
            cutoff = now - ESCALATION_WINDOW_MIN * 60
            history[:] = [t for t in history if t > cutoff]
            history.append(now)
            if len(history) >= ESCALATION_COUNT:
                guard_until = now + ESCALATION_GUARD_SEC
                self._sys_log("WARN", f"[优先级] {entity_id} 连续用户操作，保护升级至 {ESCALATION_GUARD_SEC // 60} 分钟")
        record = {
            "priority": priority,
            "source": source,
            "source_label": SOURCE_LABELS.get(source, source),
            "priority_label": PRIORITY_LABELS.get(priority, f"P{priority}"),
            "time": now,
            "state": new_state,
            "params": {k: v for k, v in (params or {}).items() if k in ACTION_PARAM_KEYS_COMMON},
            "guard_until": guard_until,
        }
        self._device_priority_map[entity_id] = record
        self._enforce_priority_storage_limits()
        return record

    def _is_reverse_op(self, current_state: str, service: str) -> bool:
        is_off = current_state in self._OFF_STATES
        ai_turning_on = "turn_on" in service or "open" in service
        ai_turning_off = "turn_off" in service or "close" in service
        return (is_off and ai_turning_on) or (not is_off and ai_turning_off)

    def _arbitrate(
        self,
        entity_id: str,
        ai_source: str,
        ai_service: str,
        ai_params: dict | None = None,
    ) -> tuple[bool, str]:
        now = time.time()
        if now < self._global_suppress_until:
            remaining = int(self._global_suppress_until - now)
            return False, f"[P0 全局抑制] {self._global_suppress_reason}（剩余 {remaining}s）"
        existing = self._device_priority_map.get(entity_id)
        if not existing or now > existing.get("guard_until", 0):
            return True, ""
        ai_priority = SOURCE_PRIORITY_MAP.get(ai_source, PRIORITY_AI_LEARNED)
        if ai_priority < int(existing.get("priority", PRIORITY_AI_LEARNED)):
            return True, ""
        if self._is_reverse_op(str(existing.get("state") or ""), ai_service):
            remaining = int(existing["guard_until"] - now)
            return False, (
                f"[优先级仲裁] AI 尝试反向操作 {entity_id}"
                f"（当前由 {existing.get('source_label', 'unknown')} 控制，保护剩余 {remaining}s）"
            )
        return True, ""

    def _build_priority_prompt_section(self) -> str:
        active = self._get_priority_summary()
        if not active:
            return ""
        lines = ["【设备操作优先级保护】"]
        for item in active[:15]:
            lines.append(
                f"- {item['name']}({item['entity_id']})："
                f"当前由「{item['source_label']}」控制 → {item['state']}，"
                f"{item['priority_label']}保护中（剩余 {item['remaining_sec']}s）"
            )
        return "\n".join(lines) + "\n"

    def _enforce_priority_storage_limits(self) -> None:
        if len(self._device_priority_map) > _PRIORITY_MAP_HARD_LIMIT:
            ordered = sorted(self._device_priority_map.items(), key=lambda kv: kv[1].get("guard_until", 0))
            for eid, _ in ordered[: len(self._device_priority_map) - _PRIORITY_MAP_HARD_LIMIT]:
                self._device_priority_map.pop(eid, None)
        if len(self._user_op_history) > _USER_OP_HISTORY_HARD_LIMIT:
            ordered = sorted(self._user_op_history.items(), key=lambda kv: max(kv[1]) if kv[1] else 0)
            for eid, _ in ordered[: len(self._user_op_history) - _USER_OP_HISTORY_HARD_LIMIT]:
                self._user_op_history.pop(eid, None)

    def _cleanup_expired_priorities(self) -> None:
        now = time.time()
        for eid in [eid for eid, rec in self._device_priority_map.items() if now > rec.get("guard_until", 0)]:
            del self._device_priority_map[eid]
        cutoff = now - ESCALATION_WINDOW_MIN * 60
        for eid, history in list(self._user_op_history.items()):
            history[:] = [t for t in history if t > cutoff]
            if not history:
                del self._user_op_history[eid]

    def _get_priority_summary(self) -> list[dict]:
        now = time.time()
        result = []
        for eid, rec in self._device_priority_map.items():
            if now > rec.get("guard_until", 0):
                continue
            result.append({
                "entity_id": eid,
                "name": self.device_info.get(eid, {}).get("name", eid),
                "priority": rec["priority"],
                "priority_label": rec["priority_label"],
                "source_label": rec["source_label"],
                "state": rec["state"],
                "remaining_sec": int(rec["guard_until"] - now),
            })
        result.sort(key=lambda x: (x["priority"], -x["remaining_sec"]))
        return result

    def _trigger_emergency(self, entity_id: str, reason: str, suppress_seconds: int = 300) -> None:
        now = time.time()
        self._global_suppress_until = now + suppress_seconds
        self._global_suppress_reason = reason
        self._record_device_operation(entity_id, SOURCE_EMERGENCY, "alert")
        self._sys_log("ERROR", f"[P0紧急] {reason}，全局 AI 抑制 {suppress_seconds}s | 触发: {entity_id}")

    def _refresh_behavior_patterns_cache(self) -> None:
        self._behavior_patterns_cache = []

    def _get_behavior_patterns_snapshot(self) -> list[dict]:
        return list(self._behavior_patterns_cache)

    async def async_confirm_habit(self) -> None:
        self._sys_log("INFO", "[习惯建议] HA 本地确认入口已下架，请在 8234/add-on 侧处理")

    async def async_cancel_habit(self) -> None:
        self._sys_log("INFO", "[习惯建议] HA 本地取消入口已下架，请在 8234/add-on 侧处理")

    async def _async_update_data(self) -> dict[str, Any]:
        """DataUpdateCoordinator: return current UI state."""
        self._cleanup_expired_priorities()
        return {"status": self.status_text, "last_action": self.last_action_text,
                "terminal_log": self.terminal_log_html}

    def _is_enabled(self) -> bool:
        """Check if AI is enabled (switch on)."""
        return self._enabled

    def _presence_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if str(item)]
        return [str(value)] if str(value) else []

    def _presence_fusion_scopes_from_core_config(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        presence = config.get("presence") if isinstance(config.get("presence"), dict) else {}
        policies = presence.get("policies") if isinstance(presence, dict) else []
        if not isinstance(policies, list):
            return []

        scopes: list[dict[str, Any]] = []
        for policy in policies:
            if not isinstance(policy, dict):
                continue
            space_id = str(policy.get("space_id") or policy.get("room") or policy.get("scope_id") or "").strip()
            if not space_id:
                continue
            members = [
                {
                    "entity_id": entity_id,
                    "can_enter_trigger": True,
                    "can_leave_evidence": True,
                    "priority": 50,
                    "confidence": 1,
                }
                for entity_id in self._presence_string_list(policy.get("member_evidence_ids") or policy.get("members"))
            ]
            strategy = str(policy.get("strategy") or policy.get("occupied_strategy") or "")
            scopes.append(
                {
                    "scope_id": str(policy.get("scope_id") or space_id),
                    "name": str(policy.get("name") or policy.get("display_name") or space_id),
                    "strategy": "vacant_and" if strategy == "vacant_and" else "occupied_or",
                    "rooms": (
                        self._presence_string_list(policy.get("rooms") or policy.get("space_ids"))
                        or [space_id]
                    ),
                    "members": members,
                    "enter_hold_secs": int(policy.get("enter_hold_secs") or 3),
                    "vacant_hold_secs": int(policy.get("vacant_hold_secs") or 60),
                }
            )
        return scopes

    async def _async_presence_fusion_json_from_core(self) -> str | None:
        """Read Core Config presence policies and export the legacy registry shape."""
        addon_client = getattr(self, "_addon_client", None)
        request_json = getattr(addon_client, "request_json", None)
        if not callable(request_json):
            return None
        try:
            result = await request_json("GET", "/core/config")
        except Exception as exc:
            _LOGGER.debug("[FusionRegistry] Core Config presence read failed: %s", exc)
            return None
        if not isinstance(result, dict):
            return None
        status = int(result.get("status_code") or 0)
        if status < 200 or status >= 300:
            return None
        body = result.get("body")
        if not isinstance(body, dict):
            return None
        config = body.get("config")
        if not isinstance(config, dict):
            return None
        scopes = self._presence_fusion_scopes_from_core_config(config)
        if not scopes:
            return None
        return json.dumps(scopes, ensure_ascii=False)

    async def _async_apply_addon_system_settings(self) -> bool:
        """Pull canonical system settings from add-on and apply to coordinator state.

        add-on 是真源；HA 仅作消费方。本函数在启动时和收到 settings 变更广播时调用。
        失败时不抛出，保留现有内存态（来自 config_entry 的初始化值）。
        """
        addon_client = getattr(self, "_addon_client", None)
        if addon_client is None:
            return False
        try:
            payload = await addon_client.get_system_settings()
        except Exception as exc:
            _LOGGER.debug("[AddonSettings] get_system_settings 失败: %s", exc)
            return False
        if not isinstance(payload, dict):
            return False
        # 兼容旧字段名 habit_proactive_ask
        habit_value = payload.get("habit_proactive")
        if habit_value is None:
            habit_value = payload.get("habit_proactive_ask")
        applied: list[str] = []
        frigate_runtime_action: str | None = None
        if "engine" in payload:
            new_value = "online" if str(payload.get("engine") or "").strip().lower() == "online" else "local"
            if new_value != self.engine:
                self.engine = new_value
                applied.append(f"engine={new_value}")
        if "ollama_url" in payload:
            new_value = str(payload.get("ollama_url") or "").strip() or "http://127.0.0.1:11434"
            if new_value != self.ollama_url:
                self.ollama_url = new_value
                applied.append("ollama_url=updated")
        if "ollama_model" in payload:
            new_value = str(payload.get("ollama_model") or "").strip()
            if new_value and new_value != self.ollama_model:
                self.ollama_model = new_value
                applied.append(f"ollama_model={new_value}")
        if "online_base_url" in payload:
            new_value = str(payload.get("online_base_url") or "").strip()
            if new_value and new_value != self.online_base_url:
                self.online_base_url = new_value
                applied.append("online_base_url=updated")
        if "online_model" in payload:
            new_value = str(payload.get("online_model") or "").strip()
            if new_value and new_value != self.online_model:
                self.online_model = new_value
                applied.append(f"online_model={new_value}")
        if "online_api_key" in payload:
            new_value = str(payload.get("online_api_key") or "").strip()
            if new_value and set(new_value) != {"*"} and new_value != self._online_api_key:
                self._online_api_key = new_value
                applied.append("online_api_key=updated")
        if "cloud_fallback" in payload:
            new_value = bool(payload.get("cloud_fallback"))
            if new_value != self._cloud_fallback:
                self._cloud_fallback = new_value
                applied.append(f"cloud_fallback={new_value}")
        if "confidence_auto" in payload:
            try:
                new_value = int(float(payload.get("confidence_auto")))
            except (TypeError, ValueError):
                new_value = self.confidence_auto
            if new_value != self.confidence_auto:
                self.confidence_auto = new_value
                applied.append(f"confidence_auto={new_value}")
        if "confidence_notify" in payload:
            try:
                new_value = int(float(payload.get("confidence_notify")))
            except (TypeError, ValueError):
                new_value = self.confidence_notify
            if new_value != self.confidence_notify:
                self.confidence_notify = new_value
                applied.append(f"confidence_notify={new_value}")
        if "cooldown" in payload:
            try:
                new_value = int(float(payload.get("cooldown")))
            except (TypeError, ValueError):
                new_value = self.cooldown
            if new_value != self.cooldown:
                self.cooldown = new_value
                applied.append(f"cooldown={new_value}")
        if "mode" in payload:
            new_value = "showroom" if str(payload.get("mode") or "").strip().lower() == "showroom" else "home"
            if new_value != self._mode:
                self._mode = new_value
                applied.append(f"mode={new_value}")
        if "learning_mode" in payload:
            new_value = bool(payload.get("learning_mode"))
            if new_value != self._learning_mode:
                self._learning_mode = new_value
                applied.append(f"learning_mode={new_value}")
        if habit_value is not None:
            new_value = bool(habit_value)
            if new_value != self._habit_proactive:
                self._habit_proactive = new_value
                applied.append(f"habit_proactive={new_value}")
        if "vision_enabled" in payload:
            new_value = bool(payload.get("vision_enabled"))
            if new_value != self._vision_enabled:
                self._vision_enabled = new_value
                applied.append(f"vision_enabled={new_value}")
        if "frigate_enabled" in payload:
            new_value = bool(payload.get("frigate_enabled"))
            if new_value != self._frigate_enabled:
                self._frigate_enabled = new_value
                frigate_runtime_action = "start" if new_value else "stop"
                applied.append(f"frigate_enabled={new_value}")
        if frigate_runtime_action == "start":
            await self._async_start_frigate_mqtt()
        elif frigate_runtime_action == "stop":
            await self._async_stop_frigate_mqtt()
        if applied:
            self._sys_log(
                "INFO",
                "[AddonSettings] 已从 add-on 同步策略开关：" + ", ".join(applied),
            )
            self.async_set_updated_data({})
        return True

    # ── 生命周期 ──────────────────────────────────────────────────────────────

    async def async_start_listeners(self) -> None:
        """Register state change listeners for device domains."""
        await self.hass.async_add_executor_job(self._init_file_logger)

        # add-on first：启动时把 add-on settings 当作真源覆写到内存（learning/habit/frigate）
        try:
            await self._async_apply_addon_system_settings()
        except Exception as exc:
            _LOGGER.debug("[AddonSettings] 启动期同步失败（保留 config_entry 初值）: %s", exc)

        # 周期同步：每 60 秒比对一次 add-on settings，发现变更即时刷内存
        try:
            async def _settings_periodic_sync(_now: Any) -> None:
                try:
                    await self._async_apply_addon_system_settings()
                except Exception as exc:
                    _LOGGER.debug("[AddonSettings] 周期同步失败: %s", exc)

            self._listener_removers.append(
                async_track_time_interval(
                    self.hass,
                    _settings_periodic_sync,
                    timedelta(seconds=60),
                )
            )
        except Exception as exc:
            _LOGGER.debug("[AddonSettings] 周期同步注册失败: %s", exc)

        # Phase 10.0: 初始化虚拟在场推断引擎（device_info 此时已加载完成）
        try:
            from .presence_inference import PresenceInference
            self._presence_inference = PresenceInference(self.hass, self.device_info)
            _LOGGER.debug("[PresenceInference] 虚拟在场推断引擎已初始化")
        except Exception as exc:
            _LOGGER.warning("[PresenceInference] 初始化失败，将使用纯传感器模式: %s", exc)
            self._presence_inference = None

        # Phase 12.0: 初始化存在传感器融合域注册表
        try:
            from .presence_fusion import PresenceFusionRegistry
            from .const import CONF_PRESENCE_FUSION, DEFAULT_PRESENCE_FUSION
            _core_presence_fusion_json = await self._async_presence_fusion_json_from_core()
            _fusion_json = (
                _core_presence_fusion_json
                or (self._entry.options or {}).get(CONF_PRESENCE_FUSION)
                or (self._entry.data or {}).get(CONF_PRESENCE_FUSION)
                or DEFAULT_PRESENCE_FUSION
            )
            self._fusion_registry = PresenceFusionRegistry(self.hass, _fusion_json)
            if self._fusion_registry.has_scopes:
                self._sys_log(
                    "INFO",
                    f"[FusionRegistry] Presence policies loaded from {'Core Config' if _core_presence_fusion_json else 'legacy presence_fusion'}; "
                    f"存在融合域已启用，共 {len(self._fusion_registry.scopes)} 个域: "
                    + ", ".join(s.display_name for s in self._fusion_registry.scopes),
                )
        except Exception as exc:
            _LOGGER.warning("[FusionRegistry] 初始化失败，融合功能已禁用: %s", exc)
            self._fusion_registry = None

        # Phase 13: 初始化昼夜节律引擎
        try:
            from .circadian import CircadianEngine
            from .const import (
                CONF_CIRCADIAN_ENABLED, DEFAULT_CIRCADIAN_ENABLED,
                CONF_CIRCADIAN_WAKE_TIME, DEFAULT_CIRCADIAN_WAKE_TIME,
                CONF_CIRCADIAN_SLEEP_TIME, DEFAULT_CIRCADIAN_SLEEP_TIME,
                CONF_CIRCADIAN_MAX_BRIGHTNESS, DEFAULT_CIRCADIAN_MAX_BRIGHTNESS,
                CONF_CIRCADIAN_AUTO_ADJUST, DEFAULT_CIRCADIAN_AUTO_ADJUST,
            )
            _opts = self._entry.options or self._entry.data or {}
            self._circadian_engine = CircadianEngine(
                self.hass,
                wake_time=_opts.get(CONF_CIRCADIAN_WAKE_TIME, DEFAULT_CIRCADIAN_WAKE_TIME),
                sleep_time=_opts.get(CONF_CIRCADIAN_SLEEP_TIME, DEFAULT_CIRCADIAN_SLEEP_TIME),
                max_brightness=int(_opts.get(CONF_CIRCADIAN_MAX_BRIGHTNESS, DEFAULT_CIRCADIAN_MAX_BRIGHTNESS)),
                enabled=_opts.get(CONF_CIRCADIAN_ENABLED, DEFAULT_CIRCADIAN_ENABLED),
            )
            self._circadian_auto_adjust = _opts.get(CONF_CIRCADIAN_AUTO_ADJUST, DEFAULT_CIRCADIAN_AUTO_ADJUST)
            _c_flag = "✓" if self._circadian_engine.enabled else "✗(disabled)"
            self._sys_log("INFO", f"[Circadian] 昼夜节律引擎已初始化 {_c_flag}")
        except Exception as exc:
            _LOGGER.warning("[Circadian] 初始化失败: %s", exc)
            self._circadian_engine = None
            self._circadian_auto_adjust = False

        _vision_flag = "✓" if getattr(self, "_vision_enabled", False) else "✗"
        _frigate_flag = "✓" if getattr(self, "_frigate_enabled", False) else "✗"
        self._sys_log("INFO", f"SmartAgent v{_SA_VERSION} 启动 — 引擎={self.engine}, "
                      f"设备数={len(self.device_info)}, 画像={len(self._habits)}, 规则={len(self._rules)}, "
                      f"视觉分析={_vision_flag}, Frigate={_frigate_flag}")
        bridge = getattr(self, "_internal_event_bridge", None)
        if bridge is not None:
            bridge.start()
        self._refresh_listeners()
        # Phase 11.9: 启动时立即刷新行为戒律（强制使用最新措辞，无需等待凌晨3点）
        # Frigate MQTT 深度集成（Phase 7A）
        await self._async_start_frigate_mqtt()
        # License 首次验证（不阻塞启动，异步后台执行）
        self.hass.async_create_task(self._async_license_startup_check())

        async def _startup_state_refresh() -> None:
            await asyncio.sleep(10)
            refreshed = 0
            failed = 0
            for eid in self.device_info:
                try:
                    await async_call_service(self.hass, "homeassistant", "update_entity", {"entity_id": eid})
                    refreshed += 1
                except Exception:
                    failed += 1
                if refreshed % 5 == 0:
                    await asyncio.sleep(0.5)
            self._sys_log("INFO", f"[启动] 设备状态强制刷新完成: 成功={refreshed}, 失败={failed}")
            area_updated = await self.async_refresh_device_areas()
            if area_updated:
                self._sys_log("INFO", f"[启动] 自动补全 {area_updated} 个设备的区域信息")
            self._refresh_ha_resources()
            await self._async_update_status("正在监控", "系统初始化完成")

        self.hass.async_create_task(_startup_state_refresh())

        async def _startup_unavail_check() -> None:
            """DEV-01: 启动冷却结束后额外等待 30s，扫描仍处于 unavailable 的托管设备并告警。
            帮助用户快速定位 Zigbee 信号弱/Z2M 未连接等硬件问题。
            """
            await asyncio.sleep(self._startup_grace + 30)
            unavail: list[str] = []
            for _eid, _info in self.device_info.items():
                _st = self.hass.states.get(_eid)
                if _st and _st.state == "unavailable":
                    _name = _info.get("name", _eid)
                    _room = _info.get("room", "未知")
                    unavail.append(f"{_name}（{_eid}）[{_room}]")
            if unavail:
                self._sys_log(
                    "WARN",
                    f"[DEV-01] 启动后 {self._startup_grace + 30}s，仍有 {len(unavail)} 个设备处于 unavailable："
                    f" {'; '.join(unavail[:8])}"
                    + ("…" if len(unavail) > 8 else "")
                    + "。建议检查 Zigbee 信号强度或 Z2M 连接状态。",
                )
            else:
                self._sys_log(
                    "INFO",
                    f"[DEV-01] 设备健康检查通过：{len(self.device_info)} 个托管设备全部在线",
                )

        self.hass.async_create_task(_startup_unavail_check())

    async def async_shutdown(self) -> None:
        for remove in self._listener_removers:
            try:
                remove()
            except Exception:
                pass
        self._listener_removers.clear()
        for cancel in self._active_timers.values():
            try:
                cancel()
            except Exception:
                pass
        self._active_timers.clear()
        for handle_name in ("_merge_timer_unsub", "_scan_timer_unsub",
                            "_habit_check_timer_unsub", "_habit_suggest_timeout_handle"):
            handle = getattr(self, handle_name, None)
            if handle:
                try:
                    handle()
                except Exception:
                    pass
                setattr(self, handle_name, None)
        # 停止日志后台线程（flush 队列后退出）
        listener = getattr(self, "_log_queue_listener", None)
        if listener:
            try:
                listener.stop()
            except Exception:
                pass
        # Frigate MQTT 清理
        await self._async_stop_frigate_mqtt()
        bridge = getattr(self, "_internal_event_bridge", None)
        if bridge is not None:
            await bridge.stop()
        # Add-on 客户端 HTTP Session 清理（v4.8.79）
        if hasattr(self, "_addon_client"):
            await self._addon_client.close()

        # 关闭 DatabaseService 持久化连接（P4 架构：所有 DB 操作结束后安全释放）
        db = getattr(self, "_db", None)
        if db is not None:
            try:
                await self.hass.async_add_executor_job(db.close)
            except Exception as exc:
                _LOGGER.warning("[Shutdown] DatabaseService 关闭异常: %s", exc)

    # ── 对外服务接口 ──────────────────────────────────────────────────────────

    async def async_manual_inference(self, trigger: str = "手动测试触发") -> None:
        """Manually trigger add-on owned AI decision."""
        self._sys_log("INFO", f"[手动] 手动触发推理: {trigger}")
        await self._run_addon_decision(trigger, source="manual")

    def _parse_addon_decision_trigger(self, trigger: str) -> dict[str, str]:
        """Parse HA listener trigger text into structured entity transition fields."""
        text = str(trigger or "").strip()
        parsed = {"trigger_entity_id": "", "old_state": "", "new_state": ""}

        def _state(value: str) -> str:
            token = str(value or "").strip().lower()
            return {
                "有人": "on",
                "无人": "off",
                "开": "on",
                "打开": "on",
                "开启": "on",
                "关": "off",
                "关闭": "off",
            }.get(token, token)

        match = re.search(
            r"(?P<entity>[a-zA-Z_]+\.[\w\d_]+)\s*[:：]\s*(?P<old>[^\s]+)\s*(?:->|→)\s*(?P<new>[^\s]+)",
            text,
        )
        if match:
            parsed["trigger_entity_id"] = match.group("entity")
            parsed["old_state"] = _state(match.group("old"))
            parsed["new_state"] = _state(match.group("new"))
            return parsed

        entity_match = re.search(r"[（(](?P<entity>[a-zA-Z_]+\.[^)）]+)[)）]", text)
        if entity_match:
            parsed["trigger_entity_id"] = entity_match.group("entity")
        cn_match = re.search(
            r"(?P<old>有人|无人|开启|关闭|打开|关|开|on|off)\s*(?:->|→)\s*"
            r"(?P<new>有人|无人|开启|关闭|打开|关|开|on|off)",
            text,
        )
        if cn_match:
            parsed["old_state"] = _state(cn_match.group("old"))
            parsed["new_state"] = _state(cn_match.group("new"))
        return parsed

    @staticmethod
    def _is_addon_presence_clear(parsed: dict[str, str]) -> bool:
        entity_id = str(parsed.get("trigger_entity_id") or "").lower()
        if not entity_id.startswith("binary_sensor."):
            return False
        markers = ("occupancy", "presence", "motion", "ren_ti", "人体", "有人")
        return (
            any(marker in entity_id for marker in markers)
            and parsed.get("old_state") == "on"
            and parsed.get("new_state") == "off"
        )

    @staticmethod
    def _render_addon_decision_device_table(
        device_info: dict[str, Any],
        states: dict[str, str],
        *,
        trigger_room: str = "",
        max_rows: int = 48,
    ) -> str:
        rows: list[str] = []
        for entity_id, raw_info in sorted(device_info.items()):
            if not entity_id:
                continue
            info = raw_info if isinstance(raw_info, dict) else {}
            room = str(info.get("room") or info.get("area") or "").strip()
            domain = entity_id.split(".", 1)[0]
            if trigger_room and room and room != trigger_room and domain not in {"light", "switch", "binary_sensor", "sensor"}:
                continue
            name = str(info.get("name") or entity_id).strip()
            control_mode = str(info.get("control_mode") or "").strip()
            state = str(states.get(entity_id) or "").strip()
            rows.append(
                f"- [{room or '未分配'}] {name} ({entity_id}) state={state or 'unknown'}"
                f"{f' control_mode={control_mode}' if control_mode else ''}"
            )
            if len(rows) >= max_rows:
                break
        return "【设备状态表】\n" + "\n".join(rows) if rows else ""

    @staticmethod
    def _render_addon_decision_occupancy_section(
        presence_snapshot: dict[str, Any],
        *,
        trigger_room: str = "",
    ) -> str:
        if not isinstance(presence_snapshot, dict):
            return ""
        rooms = presence_snapshot.get("rooms")
        if not isinstance(rooms, dict):
            return ""
        rows: list[str] = []
        for room, raw in sorted(rooms.items(), key=lambda item: str(item[0])):
            if trigger_room and str(room) != trigger_room:
                continue
            value = raw if isinstance(raw, dict) else {}
            state = value.get("state") or value.get("presence_state") or value.get("status") or ""
            confidence = value.get("confidence")
            rows.append(f"- {room}: state={state or 'unknown'} confidence={confidence if confidence is not None else 'unknown'}")
        return "【占用快照】\n" + "\n".join(rows) + "\n" if rows else ""

    def _build_addon_slow_decision_bundle(
        self,
        trigger: str,
        *,
        one_off_prompt: str = "",
        source: str = "listener",
    ) -> dict[str, Any]:
        """Build the rich bundle used by add-on slow decisions."""
        parsed = self._parse_addon_decision_trigger(trigger)
        entity_id = parsed.get("trigger_entity_id", "")
        snapshot: dict[str, Any] = {}
        if entity_id:
            snapshot_builder = getattr(self, "_build_addon_fast_path_snapshot", None)
            if callable(snapshot_builder):
                try:
                    snapshot = snapshot_builder(entity_id)
                except Exception as exc:
                    _LOGGER.debug("[决策] 慢脑快照构建失败: %s", exc)
                    snapshot = {}

        raw_device_info = snapshot.get("device_info") if isinstance(snapshot.get("device_info"), dict) else getattr(self, "device_info", {})
        device_info = dict(raw_device_info or {}) if isinstance(raw_device_info, dict) else {}
        raw_states = snapshot.get("states") if isinstance(snapshot.get("states"), dict) else {}
        states = dict(raw_states or {}) if isinstance(raw_states, dict) else {}
        trigger_info = device_info.get(entity_id, {}) if entity_id else {}
        if not isinstance(trigger_info, dict):
            trigger_info = {}
        trigger_room = str(
            trigger_info.get("room")
            or trigger_info.get("area")
            or snapshot.get("trigger_room")
            or ""
        ).strip()
        if not trigger_room and entity_id:
            area_lookup = getattr(self, "_get_entity_area", None)
            if callable(area_lookup):
                try:
                    trigger_room = str(area_lookup(entity_id) or "").strip()
                except Exception:
                    trigger_room = ""

        presence_snapshot = snapshot.get("presence_snapshot") if isinstance(snapshot.get("presence_snapshot"), dict) else {}
        device_table = self._render_addon_decision_device_table(
            device_info,
            states,
            trigger_room=trigger_room,
        )
        occupancy_section = self._render_addon_decision_occupancy_section(
            presence_snapshot,
            trigger_room=trigger_room,
        )

        context_parts = [
            str(one_off_prompt or "").strip(),
            f"触发事件：{trigger}",
        ]
        if entity_id:
            context_parts.append(f"触发实体：{entity_id}")
        if trigger_room:
            context_parts.append(f"触发空间：{trigger_room}")
        if parsed.get("old_state") or parsed.get("new_state"):
            context_parts.append(f"状态变化：{parsed.get('old_state') or '?'} -> {parsed.get('new_state') or '?'}")
        if self._is_addon_presence_clear(parsed):
            context_parts.append(
                "触发约束：占用清除。binary_sensor on->off 只表示近期未检测到活动，"
                "不等于确认无人，不等于确认有人离开；没有 leave_qualified 或多源确认时，"
                "不要生成“有人离开，准备关闭灯光”的场景。"
            )

        _now = datetime.now()
        _weekdays = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
        time_str = _now.strftime("%H:%M")
        day_str = f"{_now.strftime('%Y-%m-%d')} {_weekdays[_now.weekday()]}"

        bundle = {
            "trigger": str(trigger or ""),
            "context_text": "\n".join(part for part in context_parts if part),
            "source": f"ha_bridge_{source}",
            "time_str": time_str,
            "day_str": day_str,
            "mode": self._mode,
            "engine": self.engine,
            "confidence_auto": self.confidence_auto,
            "confidence_notify": self.confidence_notify,
            "trigger_entity_id": entity_id,
            "old_state": parsed.get("old_state", ""),
            "new_state": parsed.get("new_state", ""),
            "trigger_room": trigger_room,
            "device_info": device_info,
            "states": states,
            "presence_snapshot": presence_snapshot,
            "space_snapshot": snapshot.get("space_snapshot") if isinstance(snapshot.get("space_snapshot"), dict) else {},
            "device_capability_snapshot": snapshot.get("device_capability_snapshot") if isinstance(snapshot.get("device_capability_snapshot"), dict) else {},
            "room_topology": snapshot.get("room_topology") if isinstance(snapshot.get("room_topology"), dict) else {},
            "device_table": device_table,
            "occupancy_section": occupancy_section,
        }
        return bundle

    def _enqueue_decision_cache_write(
        self,
        *,
        bundle: dict[str, Any],
        result: dict[str, Any],
        actions: list[dict[str, Any]],
        confidence: int,
        scene: str,
    ) -> None:
        trigger_room = str(bundle.get("trigger_room") or result.get("trigger_room") or "").strip()
        if not trigger_room or not actions:
            return
        new_state = str(bundle.get("new_state") or "").strip().lower()
        trigger_type = "departure" if new_state in {"off", "closed", "not_home", "away", "idle", "clear"} else "arrival"
        now = datetime.now()
        payload = {
            "action": "write_decision",
            "trigger_room": trigger_room,
            "room": trigger_room,
            "hour_bucket": now.hour,
            "weekday": int(now.strftime("%w")),
            "trigger_type": trigger_type,
            "actions": actions,
            "confidence": confidence,
            "scene": scene,
            "intent": str(result.get("intent") or ""),
            "scene_candidate": str(result.get("scene_candidate") or result.get("scene") or ""),
        }
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue) or not enqueue("cache_invalidate", payload):
            _LOGGER.debug("[DecisionCache] write_decision enqueue skipped room=%s", trigger_room)

    def _behavior_expected_state_from_action(self, action: dict[str, Any]) -> str:
        service = str(action.get("service") or action.get("action") or "").strip().lower()
        service_name = service.rsplit(".", 1)[-1]
        service_state = {
            "turn_on": "on",
            "open_cover": "open",
            "open": "open",
            "turn_off": "off",
            "close_cover": "off",
            "close": "off",
        }
        if service_name in service_state:
            return service_state[service_name]
        expected = str(action.get("expected_state") or action.get("state") or "").strip().lower()
        return expected if expected in {"on", "off", "open", "closed", "close"} else ""

    def _enqueue_behavior_pattern_write(
        self,
        *,
        bundle: dict[str, Any],
        result: dict[str, Any],
        actions: list[dict[str, Any]],
        confidence: int,
    ) -> None:
        trigger_room = str(bundle.get("trigger_room") or result.get("trigger_room") or "").strip()
        if not trigger_room or not actions:
            return
        now = datetime.now()
        hour_start = (now.hour - 1) % 24
        hour_end = (now.hour + 1) % 24
        weekday_mask = str(now.strftime("%w"))
        enqueue = getattr(self, "_enqueue_internal_event", None)
        if not callable(enqueue):
            return
        normalized_confidence = max(55, min(95, int(confidence or result.get("confidence") or 70)))
        for action in actions:
            if not isinstance(action, dict):
                continue
            entity_id = str(action.get("entity_id") or "").strip()
            expected_state = self._behavior_expected_state_from_action(action)
            if not entity_id or not expected_state:
                continue
            payload = {
                "action": "upsert",
                "entity_id": entity_id,
                "expected_state": expected_state,
                "room": trigger_room,
                "hour_start": hour_start,
                "hour_end": hour_end,
                "weekday_mask": weekday_mask,
                "confidence": normalized_confidence,
                "hit_count": 1,
                "lifecycle_state": "active",
            }
            if not enqueue("behavior", payload, ts=now.strftime("%Y-%m-%d %H:%M:%S")):
                _LOGGER.debug("[BehaviorPattern] upsert enqueue skipped entity=%s", entity_id)

    def _build_training_sample_payload(
        self,
        *,
        bundle: dict[str, Any],
        actions: list[dict[str, Any]],
        confidence: int,
        final_outcome: str,
    ) -> dict[str, Any] | None:
        if final_outcome != "succeeded" or not actions:
            return None

        sample_actions: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            entity_id = str(action.get("entity_id") or action.get("entity") or "").strip()
            service = str(action.get("service") or "").strip()
            if not entity_id or not service:
                continue
            domain = str(action.get("domain") or entity_id.split(".", 1)[0]).strip()
            sample_actions.append(
                {
                    "domain": domain,
                    "service": service,
                    "entity_id": entity_id,
                    "confidence": max(0.0, min(float(confidence or 0) / 100.0, 1.0)),
                }
            )
        if not sample_actions:
            return None

        now = datetime.now()
        trigger_entity = str(bundle.get("trigger_entity_id") or "").strip()
        trigger_domain = trigger_entity.split(".", 1)[0] if "." in trigger_entity else ""
        trigger_room = str(bundle.get("trigger_room") or "").strip()
        presence_snapshot = bundle.get("presence_snapshot") if isinstance(bundle.get("presence_snapshot"), dict) else {}
        room_presence = {}
        rooms = presence_snapshot.get("rooms") if isinstance(presence_snapshot, dict) else {}
        if isinstance(rooms, dict) and trigger_room:
            room_presence = rooms.get(trigger_room) if isinstance(rooms.get(trigger_room), dict) else {}
        room_state = str(room_presence.get("state") or room_presence.get("presence") or "").strip().lower()
        room_person_count = 1 if room_state in {"occupied", "present", "on", "home"} else 0
        month = now.month
        season = "spring" if month in {3, 4, 5} else "summer" if month in {6, 7, 8} else "autumn" if month in {9, 10, 11} else "winter"
        quality_score = max(0.0, min(float(confidence or 0) / 100.0, 1.0))
        return {
            "source": "ha_slow_decision",
            "feature_json": {
                "time_hour": now.hour,
                "is_weekend": now.weekday() >= 5,
                "trigger_domain": trigger_domain or "unknown",
                "room_person_count": room_person_count,
                "outdoor_temp": None,
                "season_encoding": season,
            },
            "decision_json": {"actions": sample_actions},
            "label": 1,
            "quality_score": quality_score,
            "is_verified": True,
            "lifecycle_state": "active",
            "privacy_tier": "derived_private",
            "model_schema_version": "system1_v1",
        }

    async def _run_addon_decision(
        self,
        trigger: str,
        *,
        one_off_prompt: str = "",
        source: str = "listener",
    ) -> dict[str, Any]:
        addon_client = getattr(self, "_addon_client", None)
        if addon_client is None:
            self._sys_log("WARN", "[决策] add-on decision provider unavailable")
            return {"status": "error", "message": "add-on decision provider unavailable"}
        bundle = self._build_addon_slow_decision_bundle(
            trigger,
            one_off_prompt=one_off_prompt,
            source=source,
        )
        self._sys_log(
            "INFO",
            "[决策] 慢脑上下文 "
            f"entity={bundle.get('trigger_entity_id') or '-'} "
            f"room={bundle.get('trigger_room') or '-'} "
            f"state={bundle.get('old_state') or '?'}->{bundle.get('new_state') or '?'} "
            f"devices={len(bundle.get('device_info') or {})}",
        )

        def _emit_slow_decision_bubble(
            *,
            result_payload: dict[str, Any] | None = None,
            status_code: int = 200,
            matched: bool = False,
            reason: str = "",
            scene_desc: str = "",
            confidence_value: int = 0,
            actions_payload: list[dict[str, Any]] | None = None,
            transaction_id_value: str = "",
            executed_count: int = 0,
            final_outcome_value: str = "no_actions",
            fail_closed: bool = False,
        ) -> None:
            result_payload = result_payload if isinstance(result_payload, dict) else {}
            actions_payload = actions_payload if isinstance(actions_payload, list) else []
            transaction_id_value = str(
                transaction_id_value
                or result_payload.get("transaction_id")
                or result_payload.get("decision_id")
                or result_payload.get("id")
                or ""
            ).strip()
            try:
                self.hass.bus.async_fire("smart_agent_decision_bubble", {
                    "source": "ha_slow_decision",
                    "entity_id": str(bundle.get("trigger_entity_id") or ""),
                    "trigger_entity_id": str(bundle.get("trigger_entity_id") or ""),
                    "old_state": str(bundle.get("old_state") or ""),
                    "new_state": str(bundle.get("new_state") or ""),
                    "trigger": str(trigger or ""),
                    "status": status_code,
                    "matched": matched,
                    "path_taken": str(result_payload.get("path_taken") or "llm"),
                    "reason": str(reason or result_payload.get("reason") or ("matched" if matched else "no_actions")),
                    "scene": str(scene_desc or result_payload.get("scene") or ""),
                    "confidence": confidence_value,
                    "action_count": len(actions_payload),
                    "actions": actions_payload,
                    "transaction_id": transaction_id_value,
                    "executed": bool(actions_payload and executed_count >= len(actions_payload)),
                    "executed_count": executed_count,
                    "final_outcome": final_outcome_value,
                    "fail_closed": fail_closed,
                })
            except Exception as exc:
                _LOGGER.debug("[Coordinator] slow decision bubble emit failed: %s", exc)

        # ── 空设备表防裸推：无已同步设备时直接判无动作，避免模型在零设备上凭空幻觉 ──
        if not str(bundle.get("device_table") or "").strip():
            self._sys_log(
                "WARN",
                "[决策] 设备表为空（无已同步设备），跳过在线慢脑以防模型幻觉编造设备",
            )
            _emit_slow_decision_bubble(
                status_code=200,
                matched=False,
                reason="empty_device_table_no_action",
                scene_desc="无已同步设备，跳过决策",
                final_outcome_value="no_actions",
                fail_closed=True,
            )
            return {
                "status": "ok",
                "matched": False,
                "actions": [],
                "scene": "无已同步设备，跳过决策",
                "confidence": 0,
                "reason": "empty_device_table_no_action",
            }
        room_lock_key = str(bundle.get("trigger_room") or "").strip()
        inference_lock = self._get_room_lock(room_lock_key) if room_lock_key else getattr(self, "_inference_lock", None)
        if inference_lock is None:
            self._inference_lock = asyncio.Lock()
            inference_lock = self._inference_lock
        if hasattr(inference_lock, "locked") and inference_lock.locked():
            self._sys_log("INFO", f"[决策] 同空间推理进行中，等待: {room_lock_key or 'global'}")
        async with inference_lock:
            try:
                result = await addon_client.run_decision(trigger=str(trigger or ""), bundle=bundle)
            except Exception as exc:
                self._sys_log("WARN", f"[决策] add-on decision provider 调用失败: {exc}")
                _emit_slow_decision_bubble(
                    status_code=502,
                    matched=False,
                    reason="addon_decision_provider_error",
                    scene_desc="线上大模型调用失败",
                    final_outcome_value="failed",
                    fail_closed=True,
                )
                return {"status": "error", "message": str(exc)}
            if not isinstance(result, dict):
                self._sys_log("WARN", "[决策] add-on decision provider 无响应")
                _emit_slow_decision_bubble(
                    status_code=502,
                    matched=False,
                    reason="addon_decision_provider_unavailable",
                    scene_desc="线上大模型无响应",
                    final_outcome_value="failed",
                    fail_closed=True,
                )
                return {"status": "error", "message": "add-on decision provider unavailable"}
            status = int(result.get("__status", 200) or 200)
            if status >= 400 or result.get("ok") is False:
                error = result.get("error") or result.get("error_type") or f"http_{status}"
                self._sys_log("WARN", f"[决策] add-on decision provider 返回失败: {error}")
                _emit_slow_decision_bubble(
                    result_payload=result,
                    status_code=status,
                    matched=False,
                    reason=str(error),
                    scene_desc=str(result.get("scene") or "线上大模型返回失败"),
                    confidence_value=0,
                    actions_payload=[],
                    transaction_id_value=str(result.get("transaction_id") or ""),
                    executed_count=0,
                    final_outcome_value="failed",
                    fail_closed=True,
                )
                return {"status": "error", "message": str(error), **result}

            actions = result.get("actions") if isinstance(result.get("actions"), list) else []
            valid_actions = [item for item in actions if isinstance(item, dict)]
            scene = str(result.get("scene") or "")
            transaction_id = str(
                result.get("transaction_id")
                or result.get("decision_id")
                or result.get("id")
                or ""
            ).strip()
            try:
                confidence = int(float(result.get("confidence") or 0))
            except (TypeError, ValueError):
                confidence = 0
            executed = 0
            final_outcome = "no_actions"
            if valid_actions:
                executed = await self._execute_actions(
                    valid_actions,
                    trigger_summary=str(trigger or ""),
                    scene_desc=scene,
                    confidence=confidence,
                    trigger_room=str(bundle.get("trigger_room") or result.get("trigger_room") or ""),
                )
                result["executed_count"] = executed
                final_outcome = (
                    "succeeded"
                    if executed >= len(valid_actions)
                    else "partial"
                    if executed > 0
                    else "failed"
                )
                action_results = []
                for index, action in enumerate(valid_actions):
                    if not isinstance(action, dict):
                        continue
                    action_results.append(
                        {
                            "domain": str(action.get("domain") or ""),
                            "service": str(action.get("service") or ""),
                            "entity_id": str(action.get("entity_id") or ""),
                            "status": "executed" if index < executed else "not_executed",
                            "reason": "ha_execute_actions_returned_count_only",
                        }
                    )
                training_sample_payload = self._build_training_sample_payload(
                    bundle=bundle,
                    actions=valid_actions,
                    confidence=confidence,
                    final_outcome=final_outcome,
                )
                if transaction_id:
                    execution_event_enqueued = self._enqueue_internal_event(
                        "decision_execution",
                        {
                            "transaction_id": transaction_id,
                            "trigger": str(trigger or ""),
                            "scene": scene,
                            "confidence": confidence,
                            "planned_count": len(valid_actions),
                            "executed_count": executed,
                            "final_outcome": final_outcome,
                            "actions": valid_actions,
                            "action_results": action_results,
                            "training_sample": training_sample_payload,
                            "source": "ha_slow_decision",
                        },
                    )
                    if not execution_event_enqueued:
                        self._sys_log(
                            "WARN",
                            f"[决策] decision_execution 回写入队失败 transaction_id={transaction_id}",
                        )
                if executed == len(valid_actions):
                    self._enqueue_decision_cache_write(
                        bundle=bundle,
                        result=result,
                        actions=valid_actions,
                        confidence=confidence,
                        scene=scene,
                    )
                    self._enqueue_behavior_pattern_write(
                        bundle=bundle,
                        result=result,
                        actions=valid_actions,
                        confidence=confidence,
                    )
                self._sys_log("INFO", f"[决策] add-on 返回 {len(valid_actions)} 个动作，已执行 {executed} 个")
            else:
                self._sys_log("INFO", f"[决策] add-on 未返回可执行动作: {result.get('reason') or 'no_actions'}")
            _emit_slow_decision_bubble(
                result_payload=result,
                status_code=status,
                matched=bool(valid_actions),
                reason=str(result.get("reason") or ("matched" if valid_actions else "no_actions")),
                scene_desc=scene,
                confidence_value=confidence,
                actions_payload=valid_actions,
                transaction_id_value=transaction_id,
                executed_count=executed,
                final_outcome_value=final_outcome,
                fail_closed=False,
            )
            nested = result.get("result") if isinstance(result.get("result"), dict) else {}
            result.setdefault("reply", nested.get("reply") or ("已处理" if actions else "未命中可执行动作"))
            result.setdefault("status", "ok")
            return result

    async def _run_voice_inference(self, text: str, source: str = "touch") -> dict:
        """Handle voice text through add-on owned decision provider."""
        return await self._run_addon_decision(text, source=f"voice_{source}")

    async def async_run_pattern_analysis(self) -> None:
        """Delegate behavior analysis to the add-on owned AI-scene provider."""
        if self._analysis_lock.locked():
            self._sys_log("INFO", "[手动] 行为分析已在进行中，跳过重复触发")
            return
        async with self._analysis_lock:
            addon_client = getattr(self, "_addon_client", None)
            if addon_client is None:
                self._sys_log("WARN", "[AI场景] add-on ops provider unavailable: analyze")
                return
            self._sys_log("INFO", "[手动] 触发 add-on 行为规律分析与 AI 场景生成...")
            await self._async_update_status("分析中", "正在分析历史行为规律...")
            result = await addon_client.post_ai_scene_ops("ai-scenes/analyze", {})
            status = int(result.get("__status", 200) or 200) if isinstance(result, dict) else 503
            if status >= 400 or not isinstance(result, dict) or result.get("ok") is False:
                error = result.get("error") if isinstance(result, dict) else "provider_unavailable"
                self._sys_log("WARN", f"[AI场景] add-on analyze failed: {error}")
                await self._async_update_status("运行中", "行为分析请求失败")
                return
            self._sys_log("INFO", "[手动] add-on 行为分析请求已完成")
            await self._async_update_status("运行中", "行为分析完成")

    async def async_set_mode(self, mode: str) -> None:
        """Switch between home and showroom mode, and persist to config entry.

        展厅模式（MODE_SHOWROOM）仅限商业版（LICENSE_TIER_BIZ）授权使用。
        内部开发版当前 license_tier 固定为 business，生产上线后该门控将生效。
        """
        if mode not in (MODE_HOME, MODE_SHOWROOM):
            self._sys_log("WARN", f"无效模式: {mode}，保持当前 {self._mode}")
            return
        # License 门控：展厅模式仅限商业版
        if mode == MODE_SHOWROOM and self._license_tier not in (LICENSE_TIER_BIZ,):
            self._sys_log(
                "WARN",
                f"[模式] 展厅模式仅限商业版授权（当前套餐: {self._license_tier}），"
                "请升级至商业版后再切换。",
            )
            return
        self._mode = mode
        self._skip_next_reload = True
        new_options = {**(self._entry.options or {}), CONF_MODE: mode}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self._sys_log("INFO", f"[模式] 已切换为: {'展厅模式' if mode == MODE_SHOWROOM else '家庭模式'}")
        await self._async_update_status("运行中", f"当前模式: {'展厅' if mode == MODE_SHOWROOM else '家庭'}")
        self.async_set_updated_data({})

    def get_zone_role(self, room: str) -> str:
        """返回指定区域在展厅模式下的角色（display / experience / work）。

        优先级（v4.11.8 调整）：
          1. _showroom_zone_map 中有显式配置 → 使用配置值（v4.11.0+ 主路径）
          2. 旧字段 showroom_area_name 匹配 → ZONE_ROLE_DISPLAY（向后兼容旧配置迁移）
          3. 其余区域 → ZONE_ROLE_DEFAULT（experience）
        """
        if not room:
            return ZONE_ROLE_DEFAULT
        if room in self._showroom_zone_map:
            return self._showroom_zone_map[room]
        # 向后兼容：旧版 showroom_area_name 字段非空时自动视为展示区
        if self.showroom_area_name and room == self.showroom_area_name:
            return ZONE_ROLE_DISPLAY
        return ZONE_ROLE_DEFAULT

    async def async_set_showroom_scene(
        self,
        scene_key: str | None = None,
        custom_prompt: str = "",
        is_command: bool = False,
    ) -> None:
        """Set showroom preset scene or custom description, and persist.

        is_command=True 时为一次性指令模式：
          - 触发一次推理后立即清空，不写入持久配置
          - 后续巡检不再以此为「当前场景」背景，避免反复执行
        is_command=False（默认）为持久模式：
          - 写入 config entry，巡检时持续作为场景上下文
        """
        import time as _time_mod
        _new_key = scene_key if scene_key in SHOWROOM_SCENES else None
        _new_prompt = (custom_prompt or "").strip()
        # ── 防重复调用保护：同一场景/指令在 2s 内重复触发时忽略第二次 ──────────────
        _dedup_key = f"{_new_key}|{_new_prompt}|cmd={is_command}"
        _dedup_now = _time_mod.time()
        _last_dedup_key: str = getattr(self, "_last_showroom_dedup_key", "")
        _last_dedup_ts: float = getattr(self, "_last_showroom_dedup_ts", 0.0)
        if _dedup_key == _last_dedup_key and (_dedup_now - _last_dedup_ts) < 2.0:
            self._sys_log("INFO", "[展厅] 忽略重复调用（2s 内相同指令）")
            return
        self._last_showroom_dedup_key = _dedup_key
        self._last_showroom_dedup_ts = _dedup_now
        # ──────────────────────────────────────────────────────────────────────────

        # ── 一次性指令：直接触发推理，不保存到持久状态，不影响巡检上下文 ────────────
        if is_command and _new_prompt:
            _suspicious = {"所以灯": "所有灯", "所以光": "所有光", "所有的": "所有"}
            for wrong, right in _suspicious.items():
                if wrong in _new_prompt:
                    self._sys_log("WARN", f"[展厅] ⚠️ 一次性指令疑似拼写错误：「{wrong}」→ 建议「{right}」")
            self._sys_log("INFO", f"[展厅] 一次性指令（执行后自动清空）: {_new_prompt[:50]}...")
            trigger_desc = f"[展厅] 自定义场景: {_new_prompt[:40]}"
            if self._mode == MODE_SHOWROOM:
                # 即使是一次性指令，我们也应该清空之前的持久化状态，防止后续巡检冲突
                self._showroom_scene = None
                self._showroom_custom_prompt = ""
                # 更新持久化配置（清空之前的）
                self._skip_next_reload = True
                new_options = {
                    **(self._entry.options or {}),
                    CONF_SHOWROOM_SCENE: "",
                    CONF_SHOWROOM_CUSTOM_PROMPT: "",
                }
                self.hass.config_entries.async_update_entry(self._entry, options=new_options)
                
                self._schedule_inference("展厅系统", trigger_desc, new_state="on", one_off_prompt=_new_prompt)
            return  # 不保存、不更新 config entry
        # ──────────────────────────────────────────────────────────────────────────

        self._showroom_scene = _new_key
        self._showroom_custom_prompt = _new_prompt
        if self._showroom_scene:
            label = self._effective_showroom_scenes[self._showroom_scene]["label"]
            self._sys_log("INFO", f"[展厅] 场景设为: {label}")
            trigger_desc = f"[展厅] 场景切换: {label}"
        elif self._showroom_custom_prompt:
            # 检查常见拼写错误，给出警告（如"所以"代替"所有"）
            _prompt = self._showroom_custom_prompt
            _suspicious = {"所以灯": "所有灯", "所以光": "所有光", "所有的": "所有"}
            for wrong, right in _suspicious.items():
                if wrong in _prompt:
                    self._sys_log("WARN", f"[展厅] ⚠️ 自定义场景指令疑似拼写错误：「{wrong}」→ 建议改为「{right}」")
            self._sys_log("INFO", f"[展厅] 持久场景模式: {_prompt[:50]}...")
            trigger_desc = f"[展厅] 自定义场景: {_prompt[:40]}"
        else:
            self._sys_log("INFO", "[展厅] 场景已清除，使用通用演示逻辑")
            trigger_desc = "[展厅] 场景已清除"
        self._skip_next_reload = True
        new_options = {
            **(self._entry.options or {}),
            CONF_SHOWROOM_SCENE: self._showroom_scene or "",
            CONF_SHOWROOM_CUSTOM_PROMPT: self._showroom_custom_prompt,
        }
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_set_updated_data({})
        if self._mode == MODE_SHOWROOM and (self._showroom_scene or self._showroom_custom_prompt):
            self._schedule_inference("展厅系统", trigger_desc, new_state="on")

    async def async_update_showroom_scene_config(
        self,
        scene_key: str,
        label: str | None = None,
        virtual_time: str | None = None,
        scene_desc: str | None = None,
        hint: str | None = None,
    ) -> None:
        """Update a showroom scene's configuration and persist to config entry."""
        if scene_key not in SHOWROOM_SCENES:
            self._sys_log("WARN", f"[展厅] 未知场景 key: {scene_key}")
            return
        overrides = dict(self._showroom_scene_overrides)
        if scene_key not in overrides:
            overrides[scene_key] = {}
        if label is not None:
            overrides[scene_key]["label"] = label.strip()
        if virtual_time is not None:
            overrides[scene_key]["virtual_time"] = virtual_time.strip()
        if scene_desc is not None:
            overrides[scene_key]["scene_desc"] = scene_desc.strip()
        if hint is not None:
            overrides[scene_key]["hint"] = hint.strip()
        self._showroom_scene_overrides = overrides
        self._skip_next_reload = True
        new_options = {
            **(self._entry.options or {}),
            CONF_SHOWROOM_SCENE_OVERRIDES: json.dumps(overrides, ensure_ascii=False),
        }
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self._sys_log("INFO", f"[展厅] 场景配置已更新: {scene_key} → {overrides[scene_key]}")
        self.async_set_updated_data({})

    async def async_clear_overrides(self) -> None:
        """Clear all user-override protections and related history so AI starts fresh."""
        with self._user_overrides_lock:
            mem_count = len(self._user_overrides)
            self._user_overrides.clear()
        self._last_ai_actions.clear()
        self._last_inference.clear()
        rows = await self._async_query("SELECT COUNT(*) as cnt FROM events", max_rows=0)
        db_count = rows[0]["cnt"] if rows else 0
        _ok = await self._async_db_exec("DELETE FROM events")
        if not _ok:
            self._sys_log("WARN", f"[清除] 历史事件清空失败: 预估待清空={db_count}条；内存覆盖保护已清空={mem_count}条")
        else:
            self._sys_log("INFO", f"[清除] AI 记忆已重置: 覆盖保护={mem_count}条, 历史事件={db_count}条已清空")
        self.async_set_updated_data({})

    # ── Per-room 推理锁 ────────────────────────────────────────────────────────

    def _get_room_lock(self, room: str) -> asyncio.Lock:
        """返回指定房间的推理锁，不存在则即时创建。

        设计原理：
          - 不同房间的 LLM 推理可真正并发执行（asyncio 事件循环，I/O 等待时交出控制权）
          - 同一房间内仍串行，防止重复触发产生动作冲突
          - 无法提取房间名的触发（巡检/定时等）使用全局 _inference_lock 兜底

        Args:
            room: 房间名称（来自 trigger 文本解析或 device_info）

        Returns:
            该房间专属的 asyncio.Lock 实例
        """
        if room not in self._room_inference_locks:
            if len(self._room_inference_locks) > _ROOM_INFERENCE_LOCKS_HARD_LIMIT:
                stale_rooms = [
                    k for k, lock in self._room_inference_locks.items()
                    if not lock.locked()
                ]
                while len(self._room_inference_locks) > _ROOM_INFERENCE_LOCKS_HARD_LIMIT and stale_rooms:
                    self._room_inference_locks.pop(stale_rooms.pop(0), None)
            self._room_inference_locks[room] = asyncio.Lock()
        return self._room_inference_locks[room]

    # ── 传感器属性（get_config_attributes）────────────────────────────────────

    def get_config_attributes(self) -> dict[str, Any]:
        """Attributes for config sensor.

        v4.8.25 架构升级：大列表数据（devices/habits/rules/scenes/energy/transactions 等）
        已迁移到 WebSocket API（smart_agent/get_* 命令）按需下发，不再放入 sensor 属性。
        此处只保留小型统计值和配置参数（预计 < 2KB），彻底解决 16KB 上限问题。
        """
        locked_rules = sum(1 for _, lk in self._rules if lk)
        locked_habits = sum(1 for _, lk in self._habits if lk)
        # AI 规则计数（用于 Dashboard 摘要）
        _AI_MARKS = ("[自动修正规则]", "[强化修正规则]")
        ai_rule_count = sum(1 for c, _ in self._rules if any(c.startswith(m) for m in _AI_MARKS))
        return {
            # ── 统计摘要（Dashboard 所需）──
            "device_count": len(self.device_info),
            "rule_count": len(self._rules),
            "locked_rules": locked_rules,
            "habit_count": len(self._habits),
            "locked_habits": locked_habits,
            "ai_rule_count": ai_rule_count,
            # ── 引擎配置 ──
            "engine": self.engine,
            "engine_label": "本地 Ollama" if self.engine == "local" else "云端 API",
            "current_model": self.ollama_model if self.engine == "local" else self.online_model,
            "ollama_url": self.ollama_url,
            "ollama_model": self.ollama_model,
            "online_api_key": (self._online_api_key[:4] + "****" + self._online_api_key[-4:]) if len(self._online_api_key) > 8 else "****",
            "online_base_url": self.online_base_url,
            "online_model": self.online_model,
            # ── 模式 / 场景配置 ──
            "mode": self._mode,
            "showroom_scene": self._showroom_scene or "",
            "showroom_scene_label": self._effective_showroom_scenes.get(
                self._showroom_scene, {}).get("label", "") if self._showroom_scene else "",
            "showroom_scenes": [
                {"key": k, "label": s.get("label", k)[:20]}
                for k, s in list(self._effective_showroom_scenes.items())[:20]
            ],
            # ── 阈值参数 ──
            "confidence_auto": self.confidence_auto,
            "confidence_notify": self.confidence_notify,
            "cooldown": self.cooldown,
            "showroom_biz_start": format_biz_time(self.showroom_biz_start_min),
            "showroom_biz_end": format_biz_time(self.showroom_biz_end_min),
            "showroom_area_name": self.showroom_area_name,
            "showroom_excluded_subareas": self.showroom_excluded_subareas,
            "showroom_zone_map": json.dumps(self._showroom_zone_map, ensure_ascii=False),
            # ── 语音/TTS/视觉配置 ──
            "voice_status": getattr(self, "_voice_status", "idle"),
            "voice_reply": getattr(self, "_voice_reply", "")[:100],
            "last_stt": getattr(self, "_last_stt_text", "")[:100],
            "frigate_enabled": self._frigate_enabled,
            "tts_service": self._tts_service,
            "tts_target": self._tts_target,
            "tts_level": self._tts_level,
            "vision_enabled": self._vision_enabled,
            "vision_engine": self._vision_engine,
            "vision_model": self._vision_model,
            # ── 外部服务配置 ──
            "qweather_api_key": "****" if getattr(self, "_qweather_api_key", "") else "",
            "searxng_url": getattr(self, "_searxng_url", ""),
            "cloud_fallback": self._cloud_fallback,
            # ── 其他配置 ──
            "license_key": (self._license_key[:6] + "****" + self._license_key[-4:]) if len(self._license_key) > 10 else "****",
            "log_retention_days": self._log_retention_days,
            "mcp_enabled": bool(getattr(self, "_mcp_enabled", True)),
            # ── 品牌化配置 ──
            "brand_name": self.brand_name,
            "brand_primary_color": self.brand_primary_color,
            "brand_logo_url": self.brand_logo_url,
            "deploy_name": self.deploy_name,
            # ── 存在传感器融合域（Phase 12.1，供前端编辑器读取）──
            "presence_fusion": (self._entry.options or {}).get("presence_fusion", "") or "",
            # ── 轻量摘要（仅保留最近 3 条，供 Dashboard 快速预览）──
            "action_quality": self._action_quality_cache if not isinstance(
                self._action_quality_cache, list) else self._action_quality_cache[-3:],
            "priority_guards": self._get_priority_summary()[:5],
            # ── License 状态 ──
            "license": self.get_license_status(),
        }

    # ── License ───────────────────────────────────────────────────────────────

    async def _async_license_startup_check(self) -> None:
        """启动后异步校验 License（无 Key 时 fail-closed 为免费版）。"""
        key = (self._license_key or "").strip()
        if not key:
            self._license_valid = False
            self._license_tier = LICENSE_TIER_FREE
            self._license_expires = ""
            self._sys_log("WARN", "[License] 未配置 license_key，按免费版配额运行")
            return

        result = await self.async_verify_license(key=key)
        if not result.get("valid", False):
            self._license_valid = False
            self._license_tier = LICENSE_TIER_FREE
            self._license_expires = ""
            self._sys_log("WARN", f"[License] 启动校验失败，降级免费版: {result.get('message', '')}")
            return

        self._sys_log(
            "INFO",
            f"[License] 启动校验通过，套餐={result.get('tier_label', '')} 到期={result.get('expires', '') or '永久'}",
        )

    async def async_svc_verify_license(self, call) -> None:
        """HA 服务：手动触发 License 验证，结果通过 TTS / 通知播报。"""
        key = (call.data.get("license_key") or self._license_key or "").strip()
        result = await self.async_verify_license(key=key or None)
        msg = f"License 验证结果：{result['message']}（套餐：{result['tier_label']}）"
        self._sys_log("INFO", f"[License] 手动验证 → {msg}")
        self._notify_dedup(msg, title="SmartAgent License")

    async def async_svc_authorize_pairing(self, call) -> None:
        """HA 服务：为中控屏授权配对码。"""
        from homeassistant.auth import models as auth_models

        # P1安全修复：配对服务会生成长效 Owner 令牌，必须限制管理员才能调用。
        # fail-closed：无 user_id（自动化/脚本/内部 context 触发）或非管理员一律拒绝，
        # 不得因 user_id 缺失而跳过鉴权铸造 Owner 级长效令牌。
        _uid = call.context.user_id
        if _uid is None:
            _LOGGER.warning(
                "[配对] authorize_pairing 缺少 user_id（自动化/脚本/内部调用）已拒绝，"
                "该服务仅允许管理员手动调用"
            )
            return
        _caller = await self.hass.auth.async_get_user(_uid)
        if _caller is None or not _caller.is_admin:
            _LOGGER.warning(
                "[配对] authorize_pairing 被非管理员调用拒绝（user=%s）",
                _caller.name if _caller else _uid,
            )
            return

        code = str(call.data.get("code", "")).strip()

        if not code:
            # ── 极速配对模式 ──────────────────────────────
            self._express_token = ""
            error_msg = ""

            try:
                # 获取用户
                user = None
                uid = call.context.user_id
                _LOGGER.info("[配对] authorize_pairing 被调用，user_id=%s", uid)
                if uid:
                    user = await self.hass.auth.async_get_user(uid)
                if user is None:
                    users = await self.hass.auth.async_get_users()
                    user = next((u for u in users if u.is_owner and u.is_active), None)
                    _LOGGER.info("[配对] 回退到 Owner: %s", user.name if user else "无")

                if user is None:
                    error_msg = "找不到活跃的 Owner 用户"
                else:
                    client_name = "SmartAgent 中控屏（极速配对）"
                    # 复用已有的同名刷新令牌，避免 "already exists" 冲突
                    rt = next(
                        (t for t in user.refresh_tokens.values()
                         if t.client_name == client_name),
                        None,
                    )
                    if rt is None:
                        rt = await self.hass.auth.async_create_refresh_token(
                            user,
                            client_name=client_name,
                            token_type=auth_models.TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
                            access_token_expiration=timedelta(days=3650),
                        )
                        _LOGGER.info("[配对] 新刷新令牌已创建")
                    else:
                        _LOGGER.info("[配对] 复用已有刷新令牌: %s", rt.id)
                    self._express_token = self.hass.auth.async_create_access_token(rt)
                    _LOGGER.info("[配对] JWT 创建成功，长度=%d", len(self._express_token or ""))
            except Exception as exc:
                _LOGGER.error("[配对] 创建令牌异常: %s", exc, exc_info=True)
                error_msg = str(exc)

            if self._express_token:
                self._pairing_mode_end_time = time.time() + 60
                self._sys_log("INFO", "[配对] 极速配对就绪，60 秒窗口已开启")
                await async_call_service(
                    self.hass,
                    "persistent_notification", "create",
                    {
                        "message": "极速配对已就绪，中控屏将在数秒内自动连接。",
                        "title": "✅ 配对就绪",
                        "notification_id": "smart_agent_pairing",
                    },
                )
            else:
                self._pairing_mode_end_time = 0
                self._sys_log("ERROR", f"[配对] 极速配对失败: {error_msg}")
                await async_call_service(
                    self.hass,
                    "persistent_notification", "create",
                    {
                        "message": f"极速配对令牌创建失败: {error_msg}\n请检查 HA 日志获取详情。",
                        "title": "❌ 配对失败",
                        "notification_id": "smart_agent_pairing",
                    },
                )
            return

        token = str(call.data.get("token", "")).strip()
        
        if not code or not token:
            self._sys_log("WARN", "[配对] 授权失败：配对码或令牌不能为空")
            return

        # 调用 API 视图中的授权逻辑
        for pid, info in self._pairing_view._pending_pairs.items():
            if info["code"] == code:
                info["token"] = token
                self._sys_log("INFO", f"[配对] 设备授权成功！配对码：{code}")
                self._notify_dedup(f"已成功授权配对码 {code}", title="SmartAgent 配对")
                return

        self._sys_log("WARN", f"[配对] 授权失败：未找到匹配的配对码 {code}")

    async def async_svc_report_correction(self, call) -> None:
        """HA 服务：上报并记录 AI 的错误决策。"""
        entity_id = call.data.get("entity_id")
        reason = call.data.get("reason", "用户手动纠正")
        
        if not entity_id:
            return

        # 检查是否在 AI 近期操作列表中
        last_ai = self._last_ai_actions.get(entity_id)
        if not last_ai:
            self._sys_log("INFO", f"[修正] {entity_id} 不在 AI 近期操作窗口内，视为普通手动操作")
            return

        ai_target = last_ai.get("state", "")
        # 推断用户期望状态：前端会先执行反向操作再调用此服务，若 HA 状态已更新则直接读取；
        # 否则根据 AI 目标状态取反，作为兜底，避免 ai_state == user_state 的错误记录。
        now_state = self.hass.states.get(entity_id)
        now_value = now_state.state if now_state else ""
        if now_value and now_value != ai_target:
            user_state = now_value
        elif ai_target in ("on", "open", "heat", "cool"):
            user_state = "off"
        elif ai_target in ("off", "closed"):
            user_state = "on"
        else:
            user_state = now_value or "unknown"
        
        # 记录修正
        correction_payload = {
            "action": "record",
            "entity_id": entity_id,
            "ai_service": last_ai.get("service", ""),
            "ai_state": last_ai.get("state", ""),
            "user_state": user_state,
            "room": self.device_info.get(entity_id, {}).get("room", ""),
            "scene": last_ai.get("scene", ""),
            "trigger": last_ai.get("trigger", ""),
            "reason": reason,
        }
        name = self.get_device_name(entity_id)
        # fail-closed：入队是该纠错的唯一持久路径。写失败时不得输出"已记录"成功语义，
        # 也不得 pop 源记录（否则无法重试），让用户/后续重试有机会重新提交。
        if not self._enqueue_internal_event("correction", correction_payload):
            self._sys_log("WARN", f"[Correction] add-on correction enqueue failed: {entity_id}")
            self.last_correction_text = f"记录失败: {name}（add-on 不可达，请稍后重试）"
            self.async_set_updated_data({})

            async def _clear_fail():
                await asyncio.sleep(5)
                self.last_correction_text = ""
                self.async_set_updated_data({})

            self.hass.async_create_task(_clear_fail())
            return

        # 更新 UI 状态让前端感知
        self.last_correction_text = f"已记录: {name} (AI建议{last_ai.get('state')} -> 用户改为{user_state})"
        self._sys_log("WARN", f"[修正学习] 🎯 用户显式纠正了 AI 对 {name} 的操作")

        # 清除记录，防止重复触发
        self._last_ai_actions.pop(entity_id, None)
        
        # 强制更新传感器
        self.async_set_updated_data({})
        
        # 5秒后清除修正提示
        async def _clear():
            await asyncio.sleep(5)
            self.last_correction_text = ""
            self.async_set_updated_data({})
        self.hass.async_create_task(_clear())

    async def async_svc_dismiss_ai_action(self, call) -> None:
        """HA 服务：忽略 AI 近期操作（不纠错，仅从列表移除）。"""
        entity_id = call.data.get("entity_id") if call.data else None
        if entity_id:
            self._last_ai_actions.pop(entity_id, None)
            self._sys_log("INFO", f"[纠错] 已忽略 {entity_id} 的操作记录（不计入学习）")
        else:
            # 未传 entity_id → 清空全部
            self._last_ai_actions.clear()
            self._sys_log("INFO", "[纠错] 已清空全部近期操作记录")
        self.async_set_updated_data({})

    # ── 文件日志 ──────────────────────────────────────────────────────────────

    def _init_file_logger(self) -> None:
        """Initialize the midnight rotating file handler (runs in executor).

        轮转策略：每天本地时间零点轮转，保留可配置天数（默认 30 天）。
        使用 QueueHandler + QueueListener 模式：_sys_log 仅向内存队列写入（非阻塞），
        QueueListener 在独立后台线程中执行真正的文件 I/O（含 listdir/轮转），
        彻底消除事件循环中的阻塞性文件操作警告。
        """
        import queue as _q
        try:
            self._log_dir = os.path.join(self._config_dir, "custom_components", DOMAIN, "logs")
            os.makedirs(self._log_dir, exist_ok=True)
            log_path = os.path.join(self._log_dir, LOG_FILENAME)
            retention = getattr(self, "_log_retention_days", LOG_RETENTION_DAYS)
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_path,
                when="midnight",
                interval=1,
                backupCount=retention,
                encoding="utf-8",
                atTime=None,
            )
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
            ))
            # QueueHandler 向队列写入（O(1)，非阻塞），QueueListener 在后台线程消费
            log_q: _q.Queue = _q.Queue(-1)
            self._log_queue_listener = logging.handlers.QueueListener(
                log_q, file_handler, respect_handler_level=True
            )
            self._log_queue_listener.start()
            self._file_logger.addHandler(logging.handlers.QueueHandler(log_q))
        except Exception as ex:
            _LOGGER.warning("Failed to initialize file logger: %s", ex)

    def get_log_dates(self) -> list[str]:
        """Return available log dates (YYYY-MM-DD), newest first. Runs in executor."""
        seen: set[str] = set()
        log_dir = getattr(self, "_log_dir", "")
        if not log_dir or not os.path.isdir(log_dir):
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        base = LOG_FILENAME
        for f in os.listdir(log_dir):
            if f == base:
                seen.add(today)
            elif f.startswith(base + "."):
                suffix = f[len(base) + 1:]
                # 使用 fullmatch 确保后缀就是纯日期，与 read_log_file 保持一致
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", suffix):
                    seen.add(suffix)
        return sorted(seen, reverse=True)

    def read_log_file(self, date: str) -> str:
        """Read log content for a specific date. Runs in executor."""
        log_dir = getattr(self, "_log_dir", "")
        if not log_dir:
            return ""
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            return ""
        today = datetime.now().strftime("%Y-%m-%d")
        if date == today:
            path = os.path.join(log_dir, LOG_FILENAME)
        else:
            path = os.path.join(log_dir, f"{LOG_FILENAME}.{date}")
        real = os.path.realpath(path)
        log_root = os.path.realpath(log_dir)
        if os.path.commonpath([log_root, real]) != log_root:
            return ""
        if not os.path.isfile(path):
            return ""
        try:
            max_bytes = 256 * 1024
            size = os.path.getsize(path)
            with open(path, "rb") as f:
                if size > max_bytes:
                    f.seek(size - max_bytes)
                data = f.read(max_bytes)
            return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def get_log_info(self) -> list[dict]:
        """Return metadata for each available log date. Runs in executor.

        返回格式：[{date, size_kb, lines, errors, warns, today}, ...]，按日期降序。
        """
        dates = self.get_log_dates()
        if not dates:
            return []
        log_dir = getattr(self, "_log_dir", "")
        today = datetime.now().strftime("%Y-%m-%d")
        result = []
        for date in dates:
            if date == today:
                path = os.path.join(log_dir, LOG_FILENAME)
            else:
                path = os.path.join(log_dir, f"{LOG_FILENAME}.{date}")
            info: dict = {"date": date, "size_kb": 0, "lines": 0, "errors": 0, "warns": 0, "today": date == today}
            try:
                if os.path.isfile(path):
                    info["size_kb"] = round(os.path.getsize(path) / 1024, 1)
            except Exception:
                pass
            result.append(info)
        return result

    async def _async_refresh_room_topology_cache(self) -> None:
        """Refresh room topology from add-on without exposing failures to callers."""
        addon_client = getattr(self, "_addon_client", None)
        get_topology = getattr(addon_client, "get_rooms_topology", None)
        if not callable(get_topology):
            return

        try:
            payload = await get_topology()
        except Exception:
            return

        def _text(value: Any) -> str:
            return str(value or "").strip()

        topology: dict[str, set[str]] = {}

        def _add_edge(left: Any, right: Any) -> None:
            room_a = _text(left)
            room_b = _text(right)
            if not room_a or not room_b or room_a == room_b:
                return
            topology.setdefault(room_a, set()).add(room_b)
            topology.setdefault(room_b, set()).add(room_a)

        def _is_error_payload(value: dict[str, Any]) -> bool:
            if value.get("ok") is False:
                return True
            try:
                return int(value.get("__status", 200) or 200) >= 400
            except (TypeError, ValueError):
                return True

        rows: Any = payload
        if isinstance(payload, dict) and _is_error_payload(payload):
            return
        if isinstance(payload, dict) and isinstance(payload.get("topology"), (dict, list, tuple, set)):
            rows = payload.get("topology")
        elif isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list, tuple, set)):
            rows = payload.get("data")

        if isinstance(rows, dict):
            if _is_error_payload(rows):
                return
            for room, raw_neighbors in rows.items():
                if str(room).startswith("__") or room in {"ok", "error", "error_type", "retryable"}:
                    continue
                if isinstance(raw_neighbors, (list, tuple, set)):
                    for neighbor in raw_neighbors:
                        _add_edge(room, neighbor)
                else:
                    _add_edge(room, raw_neighbors)
        elif isinstance(rows, (list, tuple, set)):
            for item in rows:
                if not isinstance(item, dict):
                    continue
                room_a = item.get("room_a") or item.get("room") or item.get("from") or item.get("source")
                room_b = item.get("room_b") or item.get("neighbor") or item.get("to") or item.get("target")
                _add_edge(room_a, room_b)
        elif rows is None:
            return
        else:
            return

        self._room_topology_cache = topology
        self._room_topology_cache_updated_at = time.monotonic()

    def get_space_runtime_snapshot(self) -> dict[str, Any]:
        """返回空间运行时快照（只读内存态，不触发 DB 热路径）。"""
        room_topology: dict[str, list[str]] = {}
        for room, neighbors in (self._room_topology_cache or {}).items():
            room_name = str(room or "").strip()
            if not room_name:
                continue
            clean_neighbors: list[str] = []
            if isinstance(neighbors, (set, list, tuple)):
                for nb in neighbors:
                    nb_name = str(nb or "").strip()
                    if nb_name and nb_name != room_name and nb_name not in clean_neighbors:
                        clean_neighbors.append(nb_name)
            room_topology[room_name] = sorted(clean_neighbors)

        showroom_zone_map: dict[str, str] = {}
        for room, role in (self._showroom_zone_map or {}).items():
            room_name = str(room or "").strip()
            role_name = str(role or "").strip()
            if room_name and role_name:
                showroom_zone_map[room_name] = role_name

        shared_control_zones: dict[str, list[str]] = {}
        device_coverage: dict[str, list[str]] = {}
        space_roles: dict[str, str] = {}
        capability_snapshot = self.get_device_capability_snapshot()
        for entity_id, cap in capability_snapshot.items():
            if not isinstance(cap, dict):
                continue
            raw_spaces = cap.get(DEVICE_CAP_KEY_COVERAGE_SPACES)
            coverage_spaces = []
            if isinstance(raw_spaces, list):
                for room in raw_spaces:
                    room_name = str(room or "").strip()
                    if room_name and room_name not in coverage_spaces:
                        coverage_spaces.append(room_name)
            room = str(cap.get("room") or "").strip()
            if room and room not in coverage_spaces:
                coverage_spaces.append(room)
            for room_name in coverage_spaces:
                device_coverage.setdefault(room_name, []).append(entity_id)
                if room_name not in space_roles:
                    space_roles[room_name] = self.get_zone_role(room_name) if hasattr(self, "get_zone_role") else ""

            if cap.get(DEVICE_CAP_KEY_SHARED_FIXTURE) is not True:
                continue
            for room_name in coverage_spaces:
                shared_control_zones.setdefault(room_name, []).append(entity_id)

        for room_name, entities in shared_control_zones.items():
            shared_control_zones[room_name] = sorted({e for e in entities if isinstance(e, str) and e.strip()})
        for room_name, entities in device_coverage.items():
            device_coverage[room_name] = sorted({e for e in entities if isinstance(e, str) and e.strip()})

        return {
            SPACE_SNAPSHOT_KEY_ROOM_TOPOLOGY: room_topology,
            SPACE_SNAPSHOT_KEY_SHOWROOM_ZONE_MAP: showroom_zone_map,
            SPACE_SNAPSHOT_KEY_SHARED_CONTROL_ZONES: shared_control_zones,
            "space_roles": space_roles,
            "device_coverage": device_coverage,
        }

    def get_presence_snapshot(self) -> dict[str, Any]:
        """Return the HA-side canonical presence snapshot adapter."""

        def _text(value: Any) -> str:
            return str(value or "").strip()

        def _as_list(value: Any) -> list[str]:
            if value is None:
                return []
            if isinstance(value, (list, tuple, set)):
                result: list[str] = []
                for item in value:
                    text = _text(item)
                    if text and text not in result:
                        result.append(text)
                return result
            text = _text(value)
            return [text] if text else []

        def _confidence(value: Any) -> float:
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return 0.0
            return max(0.0, min(1.0, parsed))

        def _state(value: Any) -> str:
            raw = _text(value).lower()
            if raw in {"on", "occupied", "present", "detected", "home", "person", "motion"}:
                return "occupied"
            if raw in {"off", "vacant", "empty", "away", "clear", "none", "idle"}:
                return "vacant"
            return "unknown"

        def _bool_or_default(value: Any, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            return default

        def _merge_room(room: Any, raw: Any) -> None:
            room_id = _text(room)
            if not room_id:
                return
            row = raw if isinstance(raw, dict) else {"state": raw}
            state = _state(row.get("state"))
            existing = rooms.setdefault(
                room_id,
                {
                    "state": "unknown",
                    "confidence": 0.0,
                    "reasons": [],
                    "enter_qualified": False,
                    "leave_qualified": False,
                    "localized_spaces": [room_id],
                    "blocked_actions": [],
                    "occupied_evidence_ids": [],
                    "vacant_evidence_ids": [],
                },
            )
            if state != "unknown" or existing.get("state") == "unknown":
                existing["state"] = state
            existing["confidence"] = max(float(existing.get("confidence") or 0.0), _confidence(row.get("confidence")))
            existing["enter_qualified"] = _bool_or_default(row.get("enter_qualified"), state == "occupied")
            existing["leave_qualified"] = _bool_or_default(row.get("leave_qualified"), state == "vacant")
            for key in (
                "reasons",
                "localized_spaces",
                "blocked_actions",
                "occupied_evidence_ids",
                "vacant_evidence_ids",
            ):
                merged = list(existing.get(key) or [])
                for item in _as_list(row.get(key)):
                    if item not in merged:
                        merged.append(item)
                if key == "localized_spaces" and room_id not in merged:
                    merged.insert(0, room_id)
                existing[key] = merged

        rooms: dict[str, dict[str, Any]] = {}

        inference = getattr(self, "_presence_inference", None)
        if inference is not None:
            snapshots_fn = getattr(inference, "infer_presence_snapshots", None)
            if callable(snapshots_fn):
                try:
                    snapshots = snapshots_fn()
                except Exception:
                    snapshots = None
                if isinstance(snapshots, dict):
                    for room, raw in snapshots.items():
                        _merge_room(room, raw)

            room_fn = getattr(inference, "infer_room_presence_snapshot", None)
            if callable(room_fn):
                device_info = getattr(self, "device_info", {}) or {}
                for info in device_info.values():
                    if not isinstance(info, dict):
                        continue
                    room = _text(info.get("room"))
                    if not room or room in rooms:
                        continue
                    try:
                        _merge_room(room, room_fn(room))
                    except Exception:
                        continue

        fusion = getattr(self, "_fusion_registry", None)
        if fusion is not None:
            scopes = getattr(fusion, "scopes", None)
            if scopes is None:
                scopes = getattr(fusion, "_scopes", None)
            scope_rows = scopes.values() if isinstance(scopes, dict) else scopes
            evaluate_scope = getattr(fusion, "evaluate_scope", None)
            if scope_rows and callable(evaluate_scope):
                for scope in scope_rows:
                    scope_id = _text(getattr(scope, "scope_id", None) or getattr(scope, "id", None))
                    scope_rooms = getattr(scope, "rooms", None)
                    if not scope_rooms and isinstance(scope, dict):
                        scope_id = _text(scope.get("scope_id") or scope.get("id"))
                        scope_rooms = scope.get("rooms")
                    if not scope_id:
                        continue
                    try:
                        result = evaluate_scope(scope_id)
                    except Exception:
                        continue
                    raw_state = getattr(result, "state", None)
                    for room in _as_list(scope_rooms):
                        _merge_room(
                            room,
                            {
                                "state": raw_state,
                                "confidence": getattr(result, "confidence", 0.0),
                                "reasons": [f"fusion:{scope_id}"],
                            },
                        )

        return {
            "version": "1.0",
            "source": "ha_presence_snapshot_adapter",
            "rooms": rooms,
        }
