"""Constants for the SmartAgent integration."""

from .service_contracts import DISCOVERY_DOMAINS

DOMAIN = "smart_agent"

CONF_REFRESH_REGISTRY_SOURCE_ENABLED = "refresh_registry_source_enabled"
CONF_REFRESH_REGISTRY_INGRESS_URL = "refresh_registry_ingress_url"
CONF_REFRESH_REGISTRY_SITE_ID = "refresh_registry_site_id"
CONF_REFRESH_REGISTRY_INGRESS_SECRET = "refresh_registry_ingress_secret"
CONF_REFRESH_REGISTRY_ATTESTATION_SECRET = "refresh_registry_attestation_secret"
DEFAULT_REFRESH_REGISTRY_INGRESS_URL = ""

# Dedicated add-on -> HA observation-refresh Provider channel.  The shared
# request secret signs both directions under separate purpose-derived keys;
# replay state uses an independent HA-only integrity secret.
CONF_OBSERVATION_REFRESH_PROVIDER_RUNTIME_ENABLED = (
    "observation_refresh_provider_runtime_enabled"
)
CONF_OBSERVATION_REFRESH_PROVIDER_REQUEST_SECRET = (
    "observation_refresh_provider_request_secret"
)
CONF_OBSERVATION_REFRESH_PROVIDER_PREVIOUS_REQUEST_SECRET = (
    "observation_refresh_provider_previous_request_secret"
)
CONF_OBSERVATION_REFRESH_PROVIDER_REPLAY_INTEGRITY_SECRET = (
    "observation_refresh_provider_replay_integrity_secret"
)

# Dedicated HA -> add-on output ledger channel.  It is independent from the
# ordinary add-on bearer and remains disabled unless all three secret domains
# are explicitly provisioned on the two sides.
CONF_OUTPUT_LEDGER_INGRESS_ENABLED = "output_ledger_ingress_enabled"
CONF_OUTPUT_LEDGER_INGRESS_URL = "output_ledger_ingress_url"
CONF_OUTPUT_LEDGER_INGRESS_SECRET = "output_ledger_ingress_secret"
CONF_OUTPUT_LEDGER_ATTESTATION_SECRET = "output_ledger_attestation_secret"
DEFAULT_OUTPUT_LEDGER_INGRESS_URL = ""

# Dedicated current-admin -> add-on maintenance delegation ledger.  This
# channel persists only a pre-dispatch reservation or a no-dispatch terminal
# receipt; it never grants change application or device-effect authority.
CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED = "maintenance_change_ingress_enabled"
CONF_MAINTENANCE_CHANGE_INGRESS_URL = "maintenance_change_ingress_url"
CONF_MAINTENANCE_CHANGE_INGRESS_SECRET = "maintenance_change_ingress_secret"
CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET = (
    "maintenance_delegation_attestation_secret"
)
DEFAULT_MAINTENANCE_CHANGE_INGRESS_URL = ""

# Explicit current-session Field Canary operator identity ingress.  This is
# intentionally separate from the ordinary add-on bearer and from the
# RegistrySnapshot transport.  Enabling it can persist only an operator
# identity fact; it does not publish an approval or execution authority.
CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED = (
    "field_canary_operator_identity_ingress_enabled"
)
CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL = (
    "field_canary_operator_identity_ingress_url"
)
CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET = (
    "field_canary_operator_identity_ingress_secret"
)
CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET = (
    "field_canary_operator_identity_attestation_secret"
)
CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET = (
    "field_canary_operator_identity_previous_attestation_secret"
)
DEFAULT_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL = ""

# Dedicated add-on -> HA verification keyring for Field Canary dispatch proof
# v2.  It must never fall back to the ordinary add-on bearer used by v1.
CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_ENABLED = (
    "field_canary_host_dispatch_proof_enabled"
)
CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_SECRET = (
    "field_canary_host_dispatch_proof_secret"
)
CONF_FIELD_CANARY_PREVIOUS_HOST_DISPATCH_PROOF_SECRET = (
    "field_canary_previous_host_dispatch_proof_secret"
)

# Dedicated add-on -> HA Host Proof v3 keyring.  The current key signs and
# verifies; the staged key is verification-only during a bounded rotation.
CONF_HOST_DISPATCH_PROOF_ENABLED = "host_dispatch_proof_enabled"
CONF_HOST_DISPATCH_PROOF_CURRENT_SECRET = (
    "host_dispatch_proof_current_secret"
)
CONF_HOST_DISPATCH_PROOF_STAGED_SECRET = (
    "host_dispatch_proof_staged_secret"
)

DEVICE_CONTROL_MODES = frozenset({"ai", "ha", "shared"})

# Config entry keys
CONF_ENGINE = "engine"
CONF_OLLAMA_URL = "ollama_url"
CONF_OLLAMA_MODEL = "ollama_model"
CONF_ONLINE_API_KEY = "online_api_key"
CONF_ONLINE_BASE_URL = "online_base_url"
CONF_ONLINE_MODEL = "online_model"
CONF_CONFIDENCE_AUTO = "confidence_auto"
CONF_CONFIDENCE_NOTIFY = "confidence_notify"
CONF_COOLDOWN = "cooldown_seconds"
CONF_MANUAL_OVERRIDE_PROTECTION_SECONDS = "manual_override_protection_seconds"
CONF_VOICE_INPUT_ENTITY = "voice_input_entity"
CONF_TTS_SERVICE = "tts_service"
CONF_TTS_TARGET = "tts_target"
# TTS 播报级别: 0=关闭  1=仅 AI speak 字段  2=执行动作时播报  3=全部（含巡检提示）
CONF_TTS_LEVEL = "tts_level"
TTS_LEVEL_OFF = 0
TTS_LEVEL_SPEAK_ONLY = 1    # 仅播报 AI 主动 speak 内容
TTS_LEVEL_ACTIONS = 2       # speak + 动作执行摘要
TTS_LEVEL_ALL = 3           # speak + 动作 + 习惯提示 + 系统提示
CONF_MODE = "mode"
CONF_SHOWROOM_SCENE = "showroom_scene"
CONF_SHOWROOM_CUSTOM_PROMPT = "showroom_custom_prompt"
CONF_SHOWROOM_SCENE_OVERRIDES = "showroom_scene_overrides"
CONF_AI_ENABLED = "ai_enabled"
CONF_ACTIVE_AI_MODE = "active_ai_mode"
DEFAULT_ACTIVE_AI_MODE = "shadow"
CONF_SENSORS_MUTED = "sensors_muted"
CONF_LEARNING_MODE = "learning_mode"
CONF_HABIT_PROACTIVE = "habit_proactive"
CONF_FRIGATE_ENABLED = "frigate_enabled"  # Frigate NVR 视觉感知集成（可选功能）
CONF_SHOWROOM_BIZ_START = "showroom_biz_start"  # 展厅营业开始时间 (0-23)
CONF_SHOWROOM_BIZ_END = "showroom_biz_end"      # 展厅营业结束时间 (0-23)
CONF_SHOWROOM_AREA_NAME = "showroom_area_name"          # 展厅对应的 HA Area 名称（用户在 HA 区域注册表中设置的名字）
CONF_SHOWROOM_EXCLUDED_SUBAREAS = "showroom_excluded_subareas"  # 展厅内需要排除的子区域名称（逗号分隔，如"走廊,门厅"）

# ── 存在传感器融合域配置（Phase 12.0）────────────────────────────────────────
# 解决「一镜多区 / 大开间多传感器」误判问题。
# 格式：JSON 数组字符串（与 showroom_zone_map 风格一致）。
# 示例：[{"scope_id":"living_open","name":"客餐厅开间","strategy":"occupied_or",
#          "rooms":["客厅","餐厅"],"members":["binary_sensor.xxx","binary_sensor.yyy"]}]
CONF_PRESENCE_FUSION = "presence_fusion"   # 存在融合域配置（JSON 字符串）
DEFAULT_PRESENCE_FUSION = ""               # 默认空：不启用，各房间独立判断

# ── 昼夜节律引擎配置（Phase 13）─────────────────────────────────────────────
CONF_CIRCADIAN_ENABLED = "circadian_enabled"          # 是否启用节律引擎
CONF_CIRCADIAN_WAKE_TIME = "circadian_wake_time"      # 起床时间 HH:MM
CONF_CIRCADIAN_SLEEP_TIME = "circadian_sleep_time"    # 睡觉时间 HH:MM
CONF_CIRCADIAN_MAX_BRIGHTNESS = "circadian_max_brightness"  # 全天最大亮度%
CONF_CIRCADIAN_AUTO_ADJUST = "circadian_auto_adjust"  # 巡检时自动调整已开灯光
DEFAULT_CIRCADIAN_ENABLED = True
DEFAULT_CIRCADIAN_WAKE_TIME = "07:00"
DEFAULT_CIRCADIAN_SLEEP_TIME = "23:00"
DEFAULT_CIRCADIAN_MAX_BRIGHTNESS = 100
DEFAULT_CIRCADIAN_AUTO_ADJUST = False

CONF_LICENSE_KEY = "license_key"         # SaaS License Key
CONF_ADDON_AUTH_TOKEN = "addon_auth_token"  # Add-on 内部认证令牌（对应 SA_AUTH_TOKEN 环境变量）
CONF_ADDON_BASE_URL = "addon_base_url"      # HA 侧访问 Add-on API 的完整地址；留空时使用端口回退
CONF_ADDON_PORT = "addon_port"              # Add-on 内部 API 端口（对应 SA_INTERNAL_PORT 环境变量）
CONF_CLEANUP_LEGACY_PAIR_TOKENS = "cleanup_legacy_pair_tokens"  # 一次性清理历史配对长效令牌
DEFAULT_ADDON_PORT = 18099                  # 默认使用高位私有端口，避免与 8099 常用服务冲突

# ── 品牌化/白标配置（Phase D 商业化前置）──────────────────────────────────────
CONF_BRAND_NAME        = "brand_name"         # 面板品牌名称（默认 SmartAgent）
CONF_BRAND_PRIMARY_COLOR = "brand_primary_color"  # 主题色（CSS 颜色值，如 #6750A4）
CONF_BRAND_LOGO_URL    = "brand_logo_url"     # Logo 图片 URL（空则显示默认图标）
CONF_DEPLOY_NAME       = "deploy_name"        # 部署点标识名（如"演示展厅"）

# 品牌化默认值
DEFAULT_BRAND_NAME          = "SmartAgent"
DEFAULT_BRAND_PRIMARY_COLOR = "#6750A4"
DEFAULT_BRAND_LOGO_URL      = ""
DEFAULT_DEPLOY_NAME         = ""

# Phase 5: 联网工具与知识库 (Tools & Knowledge)
CONF_QWEATHER_API_KEY = "qweather_api_key"
CONF_SEARXNG_URL = "searxng_url"
CONF_CLOUD_FALLBACK = "cloud_fallback"   # 显式备用在线模型开关
CONF_VISION_ENABLED = "vision_enabled"   # 是否启用 LLMVision 视觉增强
CONF_VISION_ENGINE = "vision_engine"      # 视觉引擎（local / online）
CONF_VISION_MODEL = "vision_model"       # 视觉分析使用的模型（如 gemini-1.5-flash）

# ── License 套餐定义 ──────────────────────────────────────────────────────────
LICENSE_TIER_FREE    = "free"      # 免费版：30次/天
LICENSE_TIER_BASIC   = "basic"     # 基础版：200次/天
LICENSE_TIER_PRO     = "pro"       # 专业版：无限次
LICENSE_TIER_BIZ     = "business"  # 商业版：无限次 + 多实例

# 各套餐每日推理限额（-1 = 无限制）
LICENSE_DAILY_LIMITS: dict[str, int] = {
    LICENSE_TIER_FREE:  30,
    LICENSE_TIER_BASIC: 200,
    LICENSE_TIER_PRO:   -1,
    LICENSE_TIER_BIZ:   -1,
}

LICENSE_TIER_LABELS: dict[str, str] = {
    LICENSE_TIER_FREE:  "免费版",
    LICENSE_TIER_BASIC: "基础版 ¥39/月",
    LICENSE_TIER_PRO:   "专业版 ¥99/月",
    LICENSE_TIER_BIZ:   "商业版 ¥299/月",
}

# 未激活时默认按免费版限制
LICENSE_TIER_DEFAULT = LICENSE_TIER_FREE

# SmartAgent 云端服务地址（License 验证 + 数据同步 + 版本管理）
SA_CLOUD_BASE_URL        = "https://license.smartagent.ai"
LICENSE_VERIFY_URL       = f"{SA_CLOUD_BASE_URL}/v1/verify"
SA_VERSION_CHECK_URL     = f"{SA_CLOUD_BASE_URL}/v1/version/latest"
SA_HEARTBEAT_URL         = f"{SA_CLOUD_BASE_URL}/v1/devices/heartbeat"
SA_DATA_SYNC_URL         = f"{SA_CLOUD_BASE_URL}/v1/data/sync"

# 本地验证缓存有效期（秒）：1小时内不重复联网验证
LICENSE_CACHE_TTL = 3600

# ── 数据同步配置 ─────────────────────────────────────────────────────────────
# 是否启用训练数据回传（用于联邦学习和模型改进）
CONF_DATA_SYNC_ENABLED   = "data_sync_enabled"
DEFAULT_DATA_SYNC_ENABLED = True
# 数据同步间隔（秒）：默认 6 小时
DATA_SYNC_INTERVAL        = 6 * 3600
# 每批最多上传条数（防止单次请求过大）
DATA_SYNC_BATCH_SIZE      = 100

# Mode choices (home / showroom)
MODE_HOME = "home"
MODE_SHOWROOM = "showroom"

# ── 展厅区域角色定义（v4.11.0）────────────────────────────────────────────────
# 展厅模式下每个 HA 区域可被划分为三种角色，独立适用不同的灯光控制策略。
ZONE_ROLE_DISPLAY    = "display"     # 展示区：营业时间保持灯光，Core/Display/Auxiliary 分层保护
ZONE_ROLE_EXPERIENCE = "experience"  # 体验区：有人→演示场景开灯；无人→关灯节能（与家庭模式相同）
ZONE_ROLE_WORK       = "work"        # 工作区：完全不受展厅规则影响，按家庭模式逻辑独立运行
ZONE_ROLE_DEFAULT    = ZONE_ROLE_EXPERIENCE  # 展厅模式下未显式配置区域的默认角色

ZONE_ROLE_LABELS: dict[str, str] = {
    ZONE_ROLE_DISPLAY:    "展示区（营业时间保持灯光）",
    ZONE_ROLE_EXPERIENCE: "体验区（有人演示/无人关灯）",
    ZONE_ROLE_WORK:       "工作区（独立家庭模式）",
}

# 展厅区域角色映射配置键（JSON 字符串：{"区域名": "display|experience|work"}）
CONF_SHOWROOM_ZONE_MAP   = "showroom_zone_map"
DEFAULT_SHOWROOM_ZONE_MAP = ""   # 默认空；仅 showroom_area_name 对应区域固定为 display，其余 experience

# 展厅预设场景：virtual_time 虚拟时间, scene_desc 场景描述, hint AI 行为提示
SHOWROOM_SCENES = {
    "night_sleep": {
        "label": "晚间休息",
        "virtual_time": "23:00",
        "scene_desc": "晚间休息场景（模拟23:00）：灯光调暗至10-20%，窗帘关闭，营造就寝氛围",
        "hint": "灯光宜调暗、窗帘关闭，不主动开灯",
    },
    "morning_wake": {
        "label": "晨起",
        "virtual_time": "07:00",
        "scene_desc": "晨起场景（模拟07:00）：灯光渐亮、窗帘打开，营造起床氛围",
        "hint": "灯光渐亮、窗帘打开，可开空调预热",
    },
    "movie": {
        "label": "影院",
        "virtual_time": "20:30",
        "scene_desc": "影院场景：关灯、拉窗帘、营造观影氛围",
        "hint": "关闭主灯、拉上窗帘，保留氛围灯或关闭全部灯光",
    },
    "welcome_home": {
        "label": "回家",
        "virtual_time": "18:30",
        "scene_desc": "回家场景：开灯、开空调、可播放音乐，营造欢迎氛围",
        "hint": "开灯、开空调，可开启媒体播放器",
    },
    "leave_home": {
        "label": "离家",
        "virtual_time": "08:00",
        "scene_desc": "离家场景：关闭所有设备，节能模式",
        "hint": "关闭灯光、空调、窗帘等，仅保留必要设备",
    },
}

# Engine choices
ENGINE_LOCAL = "local"
ENGINE_ONLINE = "online"

# 云端供应商 → 仅用于 UI 流程（不存入 config entry，最终存 base_url）
CONF_ONLINE_PROVIDER = "online_provider"

ONLINE_PROVIDER_URLS: dict[str, str] = {
    "dashscope":   "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek":    "https://api.deepseek.com/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "custom":      "",
}

# 云端文本模型下拉列表（支持 custom_value，用户可手动输入任意名称）
# 百炼新版模型优先，旧 Qwen3.5/Qwen 仍保留兼容。
ONLINE_MODELS_ALL: list[str] = [
    # ── 通义千问 Qwen3.7 / Qwen3.6 系列（百炼新版文档推荐）──
    "qwen3.7-plus",           # 推荐默认：百炼新版文档示例模型
    "qwen3.7-max",            # 旗舰：最高精度，成本较高
    "qwen3.6-flash",          # 快速：低延迟/低成本
    # ── 通义千问 Qwen3.5 系列（向后兼容）──
    "qwen3.5-flash",          # 推荐默认：高性价比，智能家居场景首选
    "qwen3.5-plus",           # 均衡：复杂场景/展厅模式推荐
    "qwen3.5-max",            # 旗舰：最高精度，成本较高
    # ── 通义千问旧系列（向后兼容）──
    "qwen-turbo",
    "qwen-plus",
    "qwen-max",
    # ── DeepSeek ──
    "deepseek-chat",
    "deepseek-reasoner",
    # ── SiliconFlow（自托管/低成本）──
    "Qwen/Qwen3.5-9B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "deepseek-ai/DeepSeek-V3",
]

# 云端视觉模型下拉列表（用于 LLMVision 视觉增强功能）
ONLINE_VISION_MODELS: list[str] = [
    "qwen3.5-omni-flash",     # 推荐默认：多模态快速推理，支持图片+视频
    "qwen-vl-max",            # 高精度视觉分析
    "qwen-vl-plus",           # 均衡视觉分析
    "gemini-1.5-flash",       # Google 替代方案
    "gpt-4o-mini",            # OpenAI 替代方案
]

# 本地 Ollama 文本模型下拉建议（支持 custom_value）
LOCAL_MODELS_SUGGESTIONS: list[str] = [
    "qwen3-smarthome",        # 定制微调模型（推荐首选）
    "qwen3.5:9b",             # 8845HS 旗舰机推荐：高精度本地推理
    "qwen3.5:8b",             # 8B 本地模型
    "qwen3.5:4b",             # 4B 本地模型
    "qwen3:8b",               # 备选 8B 模型
    "qwen3:4b",               # 轻量：8250U / N305 VM 适用
    "qwen3:1.7b",             # 极轻量：N305 本地兜底
    "qwen2.5:7b",
    "qwen2.5:1.5b",
    "llama3:8b",
]

# 本地 Ollama 视觉模型建议（LLMVision 本地路径）
LOCAL_VISION_MODELS: list[str] = [
    "qwen3-vl:8b",            # 8845HS 推荐：本地视觉分析
    "llava:7b",
    "llava:13b",
    "moondream",              # 轻量视觉：低内存设备
]

# Defaults
DEFAULT_ENGINE = ENGINE_LOCAL
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3-smarthome"
DEFAULT_ONLINE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_ONLINE_MODEL = "qwen3.7-plus"        # 百炼新版文档示例模型；旧 qwen3.5-flash 保留兼容
DEFAULT_VISION_MODEL = "qwen3.5-omni-flash"  # 云端视觉默认模型
DEFAULT_CONFIDENCE_AUTO = 90
DEFAULT_CONFIDENCE_NOTIFY = 50
DEFAULT_COOLDOWN = 60
DEFAULT_SHOWROOM_BIZ_START = "08:50"   # 默认营业开始时间（HH:MM 格式）
DEFAULT_SHOWROOM_BIZ_END   = "19:00"   # 默认营业结束时间（HH:MM 格式）
DEFAULT_SHOWROOM_AREA_NAME = ""        # 默认为空；展厅模式用户必须填写才能正确识别展厅设备
DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS = ""  # 默认不排除任何子区域


def parse_biz_time(value) -> int:
    """将营业时间配置解析为从午夜起的分钟数。

    兼容三种格式：
    - "HH:MM" 字符串（新格式，如 "08:50"）
    - "H" 或 "HH" 整数字符串（旧格式，如 "8" 代表 8:00）
    - 整数（旧格式，如 8 代表 8:00）

    :param value: 营业时间配置值
    :return: 从午夜起的分钟数（0-1439）
    """
    if isinstance(value, str) and ":" in value:
        parts = value.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    v = int(value)
    # 旧格式：值 < 24 代表整数小时
    if v < 24:
        return v * 60
    # 已经是分钟数（兼容未来可能的存储格式）
    return v


def format_biz_time(minutes: int) -> str:
    """将从午夜起的分钟数格式化为 HH:MM 字符串。

    :param minutes: 从午夜起的分钟数
    :return: "HH:MM" 格式字符串
    """
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

# Entity IDs (suffixes, prefixed with smart_agent_)
ENTITY_PAUSED = "paused"
ENTITY_STATUS = "status"
ENTITY_LAST_ACTION = "last_action"
ENTITY_ENGINE = "engine"
ENTITY_CONFIDENCE_AUTO = "confidence_auto"
ENTITY_CONFIDENCE_NOTIFY = "confidence_notify"
ENTITY_DISCOVER = "discover"
ENTITY_DEV_ENTITY = "dev_entity"
ENTITY_DEV_DESC = "dev_desc"
ENTITY_DEV_SELECT = "dev_select"
ENTITY_DEV_ADD = "dev_add"
ENTITY_DEV_DELETE = "dev_delete"
ENTITY_HABIT_INPUT = "habit_input"
ENTITY_HABIT_SELECT = "habit_select"
ENTITY_HABIT_ADD = "habit_add"
ENTITY_HABIT_DELETE = "habit_delete"
ENTITY_HABIT_LOCK = "habit_lock"
ENTITY_RULE_INPUT = "rule_input"
ENTITY_RULE_SELECT = "rule_select"
ENTITY_RULE_ADD = "rule_add"
ENTITY_RULE_DELETE = "rule_delete"
ENTITY_RULE_LOCK = "rule_lock"
ENTITY_CONFIG_SENSOR = "config"
ENTITY_SENSOR_MUTE = "sensor_mute"
ENTITY_LEARNING_MODE = "learning_mode"
ENTITY_HABIT_PROACTIVE = "habit_proactive"
ENTITY_FRIGATE = "frigate_enabled"
ENTITY_VISION = "vision_enabled"
ENTITY_HABIT_CONFIRM = "confirm_habit"
ENTITY_HABIT_CANCEL = "cancel_habit"

# 习惯主动询问：检查间隔(分钟)、询问超时(秒)、同一设备冷却(秒)
HABIT_CHECK_INTERVAL_MIN = 10
HABIT_SUGGEST_TIMEOUT_SEC = 60
HABIT_SUGGEST_COOLDOWN_SEC = 30 * 60  # 30 分钟

# Storage
DB_FILENAME = "smart_agent_memory.db"
PATTERN_FILENAME = "smart_agent_patterns.json"
LOG_FILENAME = "smart_agent_system.log"
LOG_RETENTION_DAYS = 30          # 默认保留 30 天
LOG_MEM_MAX = 500                 # 内存实时日志最大条数

CONF_LOG_RETENTION = "log_retention_days"   # 可配置日志保留天数
CONF_FILE_LOG_LEVEL = "file_log_level"      # HA 侧 SmartAgent system 文件日志级别
DEFAULT_FILE_LOG_LEVEL = "INFO"

# ── Wave 0：共享语义契约（冻结键名，不引入行为变更）────────────────────────────
SEMANTIC_CONTRACT_VERSION = "wave0-v1"
SEMANTIC_SNAPSHOT_VERSION = "v1"

# 记忆层与来源桶（供 rules/decision_cache 语义归档使用）
MEMORY_LAYER_BEHAVIOR = "behavior"
MEMORY_LAYER_CONSTRAINT = "constraint"
MEMORY_LAYER_REFLEX = "reflex"
MEMORY_LAYER_EPISODIC = "episodic"

MEMORY_SOURCE_BUCKET_RULES = "rules"
MEMORY_SOURCE_BUCKET_DECISION_CACHE = "decision_cache"
MEMORY_SOURCE_BUCKET_CORRECTIONS = "corrections"
MEMORY_SOURCE_BUCKET_PATROL = "patrol"

# rules 语义桶（后续分流到 Behavior / Constraint Memory）
RULES_SEMANTIC_BUCKET_BEHAVIOR = "behavior"
RULES_SEMANTIC_BUCKET_CONSTRAINT = "constraint"

# Snapshot / Bundle / Trace 顶层键
KEY_SPACE_SNAPSHOT = "space_snapshot"
KEY_PRESENCE_SNAPSHOT = "presence_snapshot"
KEY_DEVICE_CAPABILITIES = "device_capabilities"
KEY_CONTEXT_BUNDLE = "context_bundle"
KEY_DECISION_TRACE = "decision_trace"

# 通用版本键
KEY_VERSION = "version"
KEY_SCHEMA_VERSION = "schema_version"

# Space Snapshot 关键字段
SPACE_SNAPSHOT_ROOM_ID = "room_id"
SPACE_SNAPSHOT_ROOM_NAME = "room_name"
SPACE_SNAPSHOT_TOPOLOGY = "topology"
SPACE_SNAPSHOT_NEIGHBORS = "neighbors"
SPACE_SNAPSHOT_ZONES = "zones"

# Presence Snapshot 关键字段
PRESENCE_SNAPSHOT_SCOPE_ID = "scope_id"
PRESENCE_SNAPSHOT_SCOPE_NAME = "scope_name"
PRESENCE_SNAPSHOT_STATE = "state"
PRESENCE_SNAPSHOT_CONFIDENCE = "confidence"
PRESENCE_SNAPSHOT_MEMBERS = "members"
PRESENCE_SNAPSHOT_UPDATED_AT = "updated_at"

# Device Capability 关键字段
DEVICE_CAPABILITY_ENTITY_ID = "entity_id"
DEVICE_CAPABILITY_DOMAIN = "domain"
DEVICE_CAPABILITY_OPS = "ops"
DEVICE_CAPABILITY_CONTROL_MODE = "control_mode"
DEVICE_CAPABILITY_SENSOR_TYPE = "sensor_type"
DEVICE_CAPABILITY_PARAMS = "params"
DEVICE_CAPABILITY_UPDATED_AT = "updated_at"

# Context Bundle 关键字段
CONTEXT_BUNDLE_TRIGGER = "trigger"
CONTEXT_BUNDLE_ROOM = "room"
CONTEXT_BUNDLE_TIME = "time"
CONTEXT_BUNDLE_MEMORY_LAYERS = "memory_layers"
CONTEXT_BUNDLE_P1 = "p1"
CONTEXT_BUNDLE_P2 = "p2"
CONTEXT_BUNDLE_P3 = "p3"

# Decision Trace 关键字段
DECISION_TRACE_TRACE_ID = "trace_id"
DECISION_TRACE_STAGE = "stage"
DECISION_TRACE_PATH = "path"
DECISION_TRACE_INPUT_HASH = "input_hash"
DECISION_TRACE_OUTPUT = "output"
DECISION_TRACE_CONFIDENCE = "confidence"
DECISION_TRACE_REASON = "reason"
DECISION_TRACE_CREATED_AT = "created_at"

# Timing
STARTUP_GRACE_SECONDS = 30
MERGE_WINDOW_SECONDS = 3
MEMORY_RETENTION_DAYS = 365
NOTIFY_DEDUP_SECONDS = 300
# 纠错学习窗口（允许延迟手动纠错进入 corrections）
CORRECTION_WINDOW_SECONDS = 600
TERMINAL_LOGS_MAX = 15

# Listeners — 触发调度与防抖参数
AI_ACTION_SKIP_WINDOW = 8        # AI 操作后 N 秒内同向变化不再触发
URGENT_MERGE_WINDOW = 1          # binary_sensor 类触发合并窗口（秒）
NORMAL_MERGE_WINDOW = 3          # 其他触发合并窗口（秒，与 MERGE_WINDOW_SECONDS 一致）

# 通信闪断累计抑制
GLITCH_THRESHOLD = 5             # 闪断次数阈值
GLITCH_WINDOW = 600              # 统计时间窗口（秒，10分钟）
GLITCH_SUPPRESS_SECS = 300       # 不可信抑制时长（秒，5分钟）

# 存在传感器去抖
PRESENCE_OFF_DELAY = 30          # 离开确认延迟（秒）
PRESENCE_ON_COOLDOWN = 60        # 持续有人抑制窗口（秒）
PRESENCE_ON_MIN_HOLD = 3         # on 最短持续时间（秒），不足则视为闪烁
PRESENCE_FLAP_WINDOW = 20        # 抖动统计窗口（秒）
PRESENCE_FLAP_THRESHOLD = 12     # 窗口内状态反转次数阈值（达到后判定为抖动风暴）
PRESENCE_FLAP_SUPPRESS_SECS = 120  # 抖动风暴抑制时长（秒）

# Frigate 人数传感器防抖
FRIGATE_COUNT_ON_HOLD = 5        # 人数增加确认延迟（秒）
FRIGATE_COUNT_CHANGE_HOLD = 8    # 人数减少（非零）确认延迟（秒）
FRIGATE_COUNT_OFF_HOLD = 15      # 人数归零确认延迟（秒）
FRIGATE_COUNT_COOLDOWN = 45      # 同传感器相同值冷却时间（秒）

# 数值型传感器触发死区（变化量占基准值百分比低于此值不触发）
SENSOR_DEADBAND_PCT: float = 10.0

# Phase 4: AI Scene Generation（习惯驱动自动生成场景）
# 阈值说明：confidence = min(95, 40 + date_count*8 + dev_count*5)
#   4天2设备 → 40+32+10=82，5天2设备 → 40+40+10=90
#   低于 MIN_DATES=4 天的模式（如展厅规则每天执行的2天数据）会被自动过滤掉
AI_SCENE_MIN_DATES = 5           # 候选场景至少在几个不同日期出现过（需要足够的重复性才有意义）
                                 # v4.11.16: 4→5，进一步减少低质量候选，避免数据库膨胀
AI_SCENE_MIN_DEVICES = 2         # 候选场景至少包含几个设备
AI_SCENE_CONFIDENCE_THRESHOLD = 75  # 生成候选场景的最低置信度
                                    # v4.11.16: 70→75（5天3设备 = 40+40+15 = 95，品质更高）
AI_SCENE_MAX_PER_RUN = 100       # 单次分析最多写入的场景数量（安全上限，防止数据库膨胀）
                                 # 超出时只保留置信度最高的 N 个
AI_SCENE_COOCCUR_WINDOW_MIN = 10    # 共现时间窗口（分钟）
AI_SCENE_STATUS_PENDING = "pending"
AI_SCENE_STATUS_ACTIVE = "active"
AI_SCENE_STATUS_REJECTED = "rejected"
AI_SCENE_STATUS_ARCHIVED = "archived"

# 动作比较必须按实体领域能力收敛，不能把灯光、空调、风扇等参数混成 COMMON 集合。
ACTION_PARAM_KEYS_BY_DOMAIN = {
    "light": frozenset({
        "brightness_pct", "brightness", "color_temp", "color_temp_kelvin",
        "rgb_color", "hs_color", "xy_color", "color_name", "transition",
        "flash", "effect",
    }),
    "climate": frozenset({
        "temperature", "target_temp_low", "target_temp_high", "hvac_mode",
        "fan_mode", "swing_mode", "preset_mode",
    }),
    "cover": frozenset({"position", "tilt_position"}),
    "fan": frozenset({"percentage", "preset_mode", "oscillating"}),
    "media_player": frozenset({"volume_level", "is_volume_muted"}),
    "scene": frozenset({"transition"}),
    "switch": frozenset(),
    "input_boolean": frozenset(),
}


def action_parameter_keys(domain: str) -> frozenset[str]:
    return ACTION_PARAM_KEYS_BY_DOMAIN.get(str(domain or "").strip().lower(), frozenset())


def comparable_action_params(domain: str, params: dict | None) -> dict:
    allowed = action_parameter_keys(domain)
    return {
        str(key): value
        for key, value in (params or {}).items()
        if str(key) in allowed
    }

ACTION_PARAM_KEYS_LIGHT_SCENE = frozenset({
    "brightness_pct", "brightness", "color_temp", "color_temp_kelvin",
    "rgb_color", "hs_color", "xy_color", "transition", "flash", "effect",
})
ACTION_PARAM_KEYS_USELESS_WHEN_OFF = frozenset({
    "brightness_pct", "brightness", "color_temp", "color_temp_kelvin",
    "rgb_color", "hs_color", "xy_color", "temperature",
    "target_temp_high", "target_temp_low", "hvac_mode",
})
ACTION_PARAM_KEYS_COLOR = frozenset({
    "color_temp_kelvin", "color_temp", "rgb_color", "hs_color", "xy_color", "color_name",
})

# Target domains for device discovery
TARGET_DOMAINS = set(DISCOVERY_DOMAINS)

# entity_id 包含以下关键词时跳过
SKIP_KEYWORDS = [
    # HA 系统内置
    "zigbee2mqtt_bridge", "sun.", "zone.", "persistent_notification",
    "script.", "automation.", "scene.", "input_", "timer.", "counter.",
    "schedule.", "weather.", "image.", "update.",
    # 本集成自身实体
    "smart_agent",
    # 备份类
    "backup.",
    # 固件更新类
    "_update",
    # 电池 / 信号 / 硬件诊断（对 AI 决策无意义）
    "_battery", "_battery_level", "_battery_low",
    "_lqi", "_rssi", "_linkquality",
    "_tamper",
    # HA 平台内部辅助
    "number.", "button.", "select.", "text.", "camera.", "tts.", "stt.",
    # Frigate 内部噪声实体（缩略图/快照/调试，无决策价值）
    "_thumbnail", "_snapshot", "_debug", "frigate_version",
    # Frigate 统计计数传感器（纯数字，无动作价值）
    # 注意：_person_occupancy / _all_occupancy 不在此处过滤——
    #       binary_sensor.{zone}_person_occupancy 是布尔占用传感器，AI 可用作触发源
    "_all_count", "_all_active_count",
    "_person_count", "_person_active_count",
    "_review_alerts", "_review_detections",
    # Frigate 控制开关（录像/快照，不应被 AI 控制）
    # 注意：_detect / _motion 不放这里——会误杀普通人体传感器（如 binary_sensor.office_motion）
    # Frigate 控制开关的精确过滤改在 devices.py 中用 FRIGATE_CONTROL_SUFFIXES 处理
    "_recordings",
    # LeMesh / LeTone 遥控器原始传感器（仅透传遥控器按键，非受控设备）
    # _wy0c09_remote_ 可匹配所有 LeMesh 遥控器 MAC 传感器（remote_a ~ remote_z）
    "_wy0c09_remote_",
    # 兜底：其他品牌遥控器按键上报传感器
    "_remote_on_off", "_remote_dim",
]

# friendly_name 包含以下词时也跳过
SKIP_NAME_KEYWORDS = ["电量", "电池", "信号", "rssi", "lqi", "tamper", "篡改", "备份", "backup",
                      "遥控器", "remote key", "按键上报"]

# Frigate 摄像头控制实体后缀（仅对 cam_xxxxxxxx 格式的实体生效，避免误杀普通传感器）
# 用法：entity_id 的 object_id（点后部分）以 cam_ 开头 且 以下列后缀结尾，则跳过
FRIGATE_CONTROL_SUFFIXES = (
    "_detect",        # switch.cam_xxx_detect（侦测开关）
    "_motion",        # switch.cam_xxx_motion（动态检测开关）
    "_improve_contrast", # switch.cam_xxx_improve_contrast
    "_autotracking",  # switch.cam_xxx_autotracking
)
# Frigate 摄像头 object_id 前缀标志（HA Frigate 集成生成的实体固定以此开头）
FRIGATE_CAM_ID_PREFIX = "cam_"

# Frigate 视觉传感器关键词（用于识别人数/占用传感器，需特殊处理）
# 注意：HA Frigate 集成生成的传感器名称可能是中文拼音，如 huo_dong_shu_liang（活动数量）
FRIGATE_PERSON_COUNT_KW = (
    "person_count",         # Frigate 标准命名（旧版：person_count）
    "person_active_count",  # Frigate HACS 集成生成的实体（新版标准）
    "active_count",         # 兜底匹配（如 cam_xxx_active_count）
    "people_count", "person_detected", "人数",
    "huo_dong_shu_liang",   # 活动数量（Frigate 中文拼音命名）
    "ren_yuan_huo_dong",    # 人员活动
)
FRIGATE_OCCUPANCY_KW    = ("person_occupancy", "object_count")   # Frigate 生成的占用 binary_sensor

# ── Product Rule P1-P3 / legacy action priority management ──────────────────
# Product Rule 优先级数值越小权限越高；高优先级可覆盖低优先级。
# legacy 常量仍保留 0..4 数值，注释必须带 Product Rule 前缀，避免和 Guard P0-P4 混用。
PRIORITY_EMERGENCY   = 0   # Product Rule P0: 紧急安全（烟雾报警、漏水、安防告警）→ 立即强制执行
PRIORITY_USER_DIRECT = 1   # Product Rule P1: 用户直接操作（物理开关、面板点击、语音指令）→ AI 无条件让步
PRIORITY_AUTOMATION  = 2   # Product Rule P2: HA 自动化/脚本（用户预设的定时和联动规则）→ AI 退让
PRIORITY_AI_LOCKED   = 3   # Product Rule P3: AI 锁定规则（用户确认过的习惯规则）→ 正常执行
PRIORITY_AI_LEARNED  = 4   # Product Rule P4: AI 学习推理（巡检、传感器推理）→ 最低优先级，随时可被覆盖

# 操作来源类型
SOURCE_PHYSICAL   = "physical"       # 物理开关 / Zigbee 联动
SOURCE_DASHBOARD  = "dashboard"      # HA 前端面板点击
SOURCE_VOICE      = "voice"          # 语音助手指令
SOURCE_AUTOMATION = "automation"     # HA 自动化 / 脚本
SOURCE_AI_RULE    = "ai_rule"        # AI 锁定规则执行
SOURCE_AI_INFER   = "ai_infer"       # AI 推理执行
SOURCE_EMERGENCY  = "emergency"      # 安全传感器触发

# 保护时间窗口（秒）。只有人工操作可由 entry data/options 配置保护时长；
# 自动化与 AI 操作不以固定秒数阻断新的 world fact。
PRIORITY_GUARD_WINDOWS = {
    PRIORITY_EMERGENCY:   300,   # 紧急事件设备级保护 5 分钟（与全局抑制同步）
    PRIORITY_USER_DIRECT: 0,
    PRIORITY_AUTOMATION:  0,
    PRIORITY_AI_LOCKED:   0,
    PRIORITY_AI_LEARNED:  0,
}

# 连续操作升级阈值：用户在 N 分钟内对同一设备操作 M 次 → 延长保护到 X 秒
ESCALATION_WINDOW_MIN   = 10     # 10 分钟统计窗口
ESCALATION_COUNT        = 3      # 3 次操作触发升级
ESCALATION_GUARD_SEC    = 1800   # 升级后保护延长至 30 分钟

# 来源 → 优先级映射
SOURCE_PRIORITY_MAP = {
    SOURCE_EMERGENCY:  PRIORITY_EMERGENCY,
    SOURCE_PHYSICAL:   PRIORITY_USER_DIRECT,
    SOURCE_DASHBOARD:  PRIORITY_USER_DIRECT,
    SOURCE_VOICE:      PRIORITY_USER_DIRECT,
    SOURCE_AUTOMATION: PRIORITY_AUTOMATION,
    SOURCE_AI_RULE:    PRIORITY_AI_LOCKED,
    SOURCE_AI_INFER:   PRIORITY_AI_LEARNED,
}

# 优先级名称（日志 & 前端展示用）
PRIORITY_LABELS = {
    PRIORITY_EMERGENCY:   "🚨 紧急安全",
    PRIORITY_USER_DIRECT: "👤 用户直接",
    PRIORITY_AUTOMATION:  "⚙️ HA自动化",
    PRIORITY_AI_LOCKED:   "🔒 AI锁定规则",
    PRIORITY_AI_LEARNED:  "🤖 AI推理",
}

SOURCE_LABELS = {
    SOURCE_PHYSICAL:   "物理开关",
    SOURCE_DASHBOARD:  "面板操作",
    SOURCE_VOICE:      "语音指令",
    SOURCE_AUTOMATION: "自动化/脚本",
    SOURCE_AI_RULE:    "AI锁定规则",
    SOURCE_AI_INFER:   "AI推理",
    SOURCE_EMERGENCY:  "安全告警",
}

# ── 展厅灯光调光配置 ────────────────────────────────────────────────────────
# Display 层灯具：无人时降至此亮度（节能+保持展示效果）
SHOWROOM_DISPLAY_DIM_PCT: int = 10
# Display/Core 层：有人时的默认亮度目标（未指定亮度时使用）
SHOWROOM_OCCUPIED_PCT: int = 90
# Core 层：有人时亮度下限（防止 AI 过度调暗）
SHOWROOM_CORE_MIN_PCT: int = 30

# ── 房间场景照明情景表（中英文关键字匹配）────────────────────────────────────
# 格式：关键字 → (建议亮度%, 建议色温K, 场景说明)
# 优先级：字典顺序，越靠前优先级越高（较精确关键字应在前）
ROOM_LIGHT_CONTEXT: dict[str, tuple[int, int, str]] = {
    # ── 茶室 / 休闲 ────────────────────────────────────────
    "茶室":    (60, 3000, "茶室温馨氛围，低色温暖白，放松交流"),
    "茶": (60, 3000, "茶区温馨"),
    "tea":     (60, 3000, "Tea room warm ambiance"),
    # ── 餐厅 ────────────────────────────────────────────────
    "餐厅":    (70, 3000, "餐厅暖光食欲感，促进就餐体验"),
    "dining":  (70, 3000, "Dining room warm light"),
    # ── 卧室 ────────────────────────────────────────────────
    "卧室":    (40, 2700, "卧室极暖光，有助入睡放松"),
    "主卧":    (40, 2700, "主卧极暖光"),
    "次卧":    (40, 2700, "次卧极暖光"),
    "bedroom": (40, 2700, "Bedroom warm cozy light"),
    # ── 书房 / 学习 ─────────────────────────────────────────
    "书房":    (100, 6000, "书房冷白光高亮，提升专注力"),
    "学习":    (100, 6000, "学习区专注模式"),
    "study":   (100, 6000, "Study room cool white"),
    # ── 办公 ────────────────────────────────────────────────
    "办公":    (100, 5500, "办公中性偏冷，提高工作效率"),
    "工作":    (90,  5000, "工作区明亮"),
    "office":  (100, 5500, "Office neutral cool light"),
    # ── 客厅 ────────────────────────────────────────────────
    "客厅":    (80, 4000, "客厅中性白，日常活动舒适"),
    "living":  (80, 4000, "Living room neutral"),
    # ── 厨房 ────────────────────────────────────────────────
    "厨房":    (100, 5000, "厨房明亮冷白，便于操作安全"),
    "kitchen": (100, 5000, "Kitchen bright cool"),
    # ── 卫生间 / 浴室 ───────────────────────────────────────
    "卫生间":  (80, 4500, "卫浴中性白，梳妆/清洁适用"),
    "浴室":    (80, 4500, "浴室中性白"),
    "洗手间":  (80, 4500, "洗手间明亮"),
    "bathroom":(80, 4500, "Bathroom neutral"),
    # ── 玄关 / 走廊 ─────────────────────────────────────────
    "玄关":    (80, 4000, "玄关欢迎光，迎接归家"),
    "走廊":    (70, 4000, "走廊通道适中亮度"),
    "corridor":(70, 4000, "Corridor path light"),
    "entrance":(80, 4000, "Entrance welcome light"),
    # ── 阳台 / 花园 ─────────────────────────────────────────
    "阳台":    (60, 3500, "阳台放松暖白"),
    "花园":    (50, 3000, "花园庭院柔和"),
    "balcony": (60, 3500, "Balcony relaxing"),
    "garden":  (50, 3000, "Garden soft warm"),
}


# ─────────────────────────────────────────────────────────────────────────────
# AI 场景时间匹配工具函数
# ─────────────────────────────────────────────────────────────────────────────

def ai_scene_matches_now(scene: dict, now_hour: int, python_weekday: int) -> bool:
    """判断 AI 场景在当前时间是否应激活。

    统一使用 **SQLite %w 格式** 的星期掩码（0=日, 1=一, …, 6=六），
    与 patrol.py 的 SQL 查询 ``strftime('%w', time)`` 保持一致。

    Args:
        scene: ai_scenes 缓存字典，包含 hour_start/hour_end/weekday_mask 等字段。
        now_hour: 当前小时数（0–23）。
        python_weekday: Python ``datetime.weekday()`` 返回值（0=Mon, …, 6=Sun）。

    Returns:
        True 表示当前时间在场景设定的活跃窗口内。
    """
    # Python weekday 0=Mon … 6=Sun → SQLite %w 1=Mon … 6=Sat, 0=Sun
    sqlite_wd = str((python_weekday + 1) % 7)
    if not (scene.get("hour_start", 0) <= now_hour <= scene.get("hour_end", 23)):
        return False
    wd_mask = scene.get("weekday_mask", "0123456")
    return sqlite_wd in wd_mask


# ── RAG 检索配置（Phase RAG）──────────────────────────────────────────────────
RAG_MAX_TOKENS: int = 500                       # RAG 上下文总 token 预算
RAG_SIMILAR_HOUR_RANGE: int = 2                 # 相似时段检索范围（±小时）
RAG_CORRECTIONS_LOOKBACK_DAYS: int = 90         # 修正记录回溯天数
RAG_MIN_CORRECTION_COUNT: int = 2               # 最小修正次数（过滤噪声）
RAG_BEHAVIOR_MIN_CONFIDENCE: int = 40           # 行为模式最低置信度

# ── 房间拓扑关系类型（Roadmap Priority Phase P1-2）──────────────────────────
ROOM_RELATION_ADJACENT: str = "adjacent"        # 相邻（如客厅-走廊）
ROOM_RELATION_CONNECTED: str = "connected"      # 连通（如开放式客餐厅）

# ── Wave 6: 空间运行时 / 设备能力快照键名（统一常量，避免分散硬编码）────────────
SPACE_SNAPSHOT_KEY_ROOM_TOPOLOGY = "room_topology"
SPACE_SNAPSHOT_KEY_SHOWROOM_ZONE_MAP = "showroom_zone_map"
SPACE_SNAPSHOT_KEY_SHARED_CONTROL_ZONES = "shared_control_zones"

DEVICE_CAP_KEY_COVERAGE_SPACES = "coverage_spaces"
DEVICE_CAP_KEY_SHARED_FIXTURE = "shared_fixture"
DEVICE_CAP_KEY_SLEEP_SAFE = "sleep_safe"
DEVICE_CAP_KEY_RISK_LEVEL = "risk_level"
DEVICE_CAP_KEY_ENERGY_LEVEL = "energy_level"
DEVICE_CAP_KEY_CAN_TRIGGER_ENTER = "can_trigger_enter"
DEVICE_CAP_KEY_CAN_CONFIRM_LEAVE = "can_confirm_leave"
DEVICE_CAP_KEY_CAN_BLOCK_TURN_OFF = "can_block_turn_off"
DEVICE_CAP_KEY_CAN_LOCALIZE_ZONE = "can_localize_zone"

# ── 中国法定节假日（Roadmap Priority Phase P0-2 特征工程）───────────────────
# 每年需更新；节假日期间 AI 行为应参照周末模式
CHINESE_HOLIDAYS_2026: frozenset[str] = frozenset({
    # 元旦
    "2026-01-01", "2026-01-02", "2026-01-03",
    # 春节
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19",
    "2026-02-20", "2026-02-21", "2026-02-22",
    # 清明
    "2026-04-04", "2026-04-05", "2026-04-06",
    # 劳动节
    "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
    # 端午
    "2026-06-19", "2026-06-20", "2026-06-21",
    # 中秋+国庆
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
    "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
})
