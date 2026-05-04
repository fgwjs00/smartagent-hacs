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
    async_track_utc_time_change,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .actions import ActionsMixin
from .data_sync import DataSyncMixin
from .database import DatabaseMixin
from .decision_pipeline import DecisionPipeline
from .devices import DevicesMixin
from .frigate import FrigateMixin
from .inference import InferenceMixin
from .license import LicenseMixin
from .listeners import ListenersMixin
from .patrol import PatrolMixin
from .protection import ProtectionMixin
from .api import SmartAgentPairingView, SmartAgentAuthPageView, SmartAgentPairConfirmView

from .const import (
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
    CONF_LOG_RETENTION,
    CONF_ADDON_AUTH_TOKEN,
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
    PATTERN_FILENAME,
    SHOWROOM_SCENES,
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


class SmartAgentCoordinator(
    DatabaseMixin,
    DataSyncMixin,
    ProtectionMixin,
    ActionsMixin,
    InferenceMixin,
    ListenersMixin,
    PatrolMixin,
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
        ProtectionMixin → _refresh_ha_resources / _extract_entity_ids_from_config
                          _get_room_occupancy_map / _build_occupancy_section
                          _guess_scene_room / _occupancy_guard_check / _is_occupancy_active
        ActionsMixin    → _normalize_action / _fuzzy_match_entity / _find_associated_script
                          _execute_actions / _do_call_service / _verify_pending_actions
        InferenceMixin  → _detect_scene / _build_context / _call_ai_engine / _run_inference
                          _get_habits_text / _get_rules_text / _annotate_time
                          _habit_display / _rule_display / _find_habit_idx / _find_rule_idx
                          _load_pattern_summary / _save_pattern_summary
                          _get_history_context / _get_realtime_habits / _get_recent_overrides
                          _effective_showroom_scenes (property) / _speak_tts
        ListenersMixin  → _should_trigger / _effective_cooldown
                          _schedule_inference / _flush_triggers
                          _get_time_brightness / _find_room_lights
                          _make_state_handler / _refresh_listeners
        PatrolMixin     → _get_scan_interval / _schedule_next_scan / _run_periodic_scan
                          _analyze_patterns / _get_arrival_prediction
                          _run_habit_proactive_check / _habit_notify
                          async_confirm_habit / async_cancel_habit
                          _refresh_behavior_patterns_cache / _get_behavior_patterns_snapshot
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
        self.confidence_auto = int(data.get(CONF_CONFIDENCE_AUTO, 90))
        self.confidence_notify = int(data.get(CONF_CONFIDENCE_NOTIFY, 60))
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
        self._cloud_fallback = bool(data.get(CONF_CLOUD_FALLBACK, True))
        self._vision_enabled = bool(data.get(CONF_VISION_ENABLED, False))
        self._vision_engine = data.get(CONF_VISION_ENGINE, ENGINE_ONLINE)
        self._vision_model = (data.get(CONF_VISION_MODEL) or "qwen3.5-omni-flash").strip()
        # License
        self._init_license()
        self._license_key = (data.get(CONF_LICENSE_KEY) or "").strip()
        # 数据同步（v4.8.78）
        self._init_data_sync()
        # Add-on 客户端（v4.10.10：新增内部认证令牌支持；端口可通过 CONF_ADDON_PORT 配置）
        from .addon_client import AddOnClient
        from .const import CONF_ADDON_PORT, DEFAULT_ADDON_PORT
        _addon_token = (data.get(CONF_ADDON_AUTH_TOKEN) or "").strip()
        _addon_port = int(data.get(CONF_ADDON_PORT) or DEFAULT_ADDON_PORT)
        self._addon_client = AddOnClient(port=_addon_port, auth_token=_addon_token)
        # TTS 配置
        self._tts_service: str = (data.get(CONF_TTS_SERVICE) or "").strip()
        self._tts_target: str = (data.get(CONF_TTS_TARGET) or "").strip()
        self._tts_level: int = int(data.get(CONF_TTS_LEVEL, TTS_LEVEL_OFF))
        self._transactions_cache: list[dict] = []
        self._env_feedback_tasks: list[dict] = []
        self._env_feedback_lock = asyncio.Lock()
        # Phase A: DeviceAdapter — AI Core 与 HA 设备层解耦（可测试化）
        # 当前唯一实现：HAAdapter（通过 hass.services.async_call）
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
        self._decision_pipeline = DecisionPipeline(self)

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
        self._pattern_summary = self._load_pattern_summary()
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
            self.hass.services.async_call("persistent_notification", "create",
                                          {"message": message, "title": title})
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
            await self.hass.services.async_call(
                domain, service,
                {"entity_id": target, "message": text},
            )
            self._sys_log("INFO", f"[TTS] 播报: {text[:60]}")
        except Exception as exc:
            self._sys_log("WARN", f"[TTS] 播报失败: {exc}")

    async def _async_update_data(self) -> dict[str, Any]:
        """DataUpdateCoordinator: return current UI state."""
        self._cleanup_expired_priorities()
        return {"status": self.status_text, "last_action": self.last_action_text,
                "terminal_log": self.terminal_log_html}

    def _is_enabled(self) -> bool:
        """Check if AI is enabled (switch on)."""
        return self._enabled

    # ── 生命周期 ──────────────────────────────────────────────────────────────

    async def async_start_listeners(self) -> None:
        """Register state change listeners for device domains."""
        await self.hass.async_add_executor_job(self._init_file_logger)

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
            _fusion_json = (
                (self._entry.options or {}).get(CONF_PRESENCE_FUSION)
                or (self._entry.data or {}).get(CONF_PRESENCE_FUSION)
                or DEFAULT_PRESENCE_FUSION
            )
            self._fusion_registry = PresenceFusionRegistry(self.hass, _fusion_json)
            if self._fusion_registry.has_scopes:
                self._sys_log(
                    "INFO",
                    f"[FusionRegistry] 存在融合域已启用，共 {len(self._fusion_registry.scopes)} 个域: "
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
            # 注入到快脑引擎（如果已初始化）
            if hasattr(self, "_fast_brain") and self._fast_brain:
                self._fast_brain._circadian_engine = self._circadian_engine
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
        self._refresh_listeners()
        # 智能巡检：动态间隔，自调度
        if self._scan_timer_unsub:
            try:
                self._scan_timer_unsub()
            except Exception:
                pass
        self._scan_timer_unsub = None
        self._schedule_next_scan()
        # 习惯主动询问
        if self._habit_check_timer_unsub:
            try:
                self._habit_check_timer_unsub()
            except Exception:
                pass
        self._habit_check_timer_unsub = None
        self._schedule_next_habit_check()
        # 每天凌晨 3:00 行为规律分析（UTC 19:00 = 北京时间 03:00）
        self._listener_removers.append(
            async_track_utc_time_change(self.hass, self._on_daily_pattern_analysis, hour=19, minute=0, second=0)
        )
        # 启动时执行一次分析（确保 pattern_summary 有值），走统一分析入口（含 _analysis_lock）
        self.hass.async_create_task(self.async_run_pattern_analysis())
        # Phase 11.9: 启动时立即刷新行为戒律（强制使用最新措辞，无需等待凌晨3点）
        self.hass.async_add_executor_job(self._startup_lessons_refresh)
        # Frigate MQTT 深度集成（Phase 7A）
        await self._async_start_frigate_mqtt()
        # License 首次验证（不阻塞启动，异步后台执行）
        self.hass.async_create_task(self._async_license_startup_check())
        # 数据同步（心跳 + 训练数据回传，v4.8.78）
        await self._start_data_sync()

        async def _startup_state_refresh() -> None:
            await asyncio.sleep(10)
            refreshed = 0
            failed = 0
            for eid in self.device_info:
                try:
                    await self.hass.services.async_call("homeassistant", "update_entity", {"entity_id": eid})
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
        # 数据同步任务清理（关闭 HTTP Session）
        await self._stop_data_sync()
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
        """Manually trigger an AI inference (bypasses listeners & cooldown)."""
        self._sys_log("INFO", f"[手动] 手动触发推理: {trigger}")
        await self._run_inference(trigger)

    async def async_run_pattern_analysis(self) -> None:
        """手动触发行为规律分析 + Phase 4 候选 AI 场景生成（无需等到凌晨 3:00）。

        使用 _analysis_lock 防止手动触发与每日定时触发重叠执行。
        """
        if self._analysis_lock.locked():
            self._sys_log("INFO", "[手动] 行为分析已在进行中，跳过重复触发")
            return
        async with self._analysis_lock:
            self._sys_log("INFO", "[手动] 触发行为规律分析与 AI 场景生成...")
            await self._async_update_status("分析中", "正在分析历史行为规律...")
            await self.hass.async_add_executor_job(self._analyze_patterns)
            count = len([s for s in self._ai_scenes_cache if s.get("status") == "pending"])
            self._sys_log("INFO", f"[手动] 行为分析完成，待确认候选场景: {count} 个")
            await self._async_update_status("运行中", f"行为分析完成，发现 {count} 个候选场景")

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

        # P1安全修复：配对服务会生成长效 Owner 令牌，必须限制管理员才能调用
        _uid = call.context.user_id
        if _uid is not None:
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
                await self.hass.services.async_call(
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
                await self.hass.services.async_call(
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
        self.hass.async_add_executor_job(
            self._record_correction,
            entity_id,
            last_ai.get("service", ""),
            last_ai.get("state", ""),
            user_state,
            self.device_info.get(entity_id, {}).get("room", ""),
            last_ai.get("scene", ""),
            last_ai.get("trigger", ""),
        )
        
        # 更新 UI 状态让前端感知
        name = self.get_device_name(entity_id)
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
        if not real.startswith(os.path.realpath(log_dir)):
            return ""
        if not os.path.isfile(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
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
            if os.path.isfile(path):
                try:
                    size = os.path.getsize(path)
                    info["size_kb"] = round(size / 1024, 1)
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            info["lines"] += 1
                            if "[ERROR]" in line:
                                info["errors"] += 1
                            elif "[WARNING]" in line or "[WARN]" in line:
                                info["warns"] += 1
                except Exception:
                    pass
            result.append(info)
        return result

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
