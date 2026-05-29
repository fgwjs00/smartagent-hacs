"""Config flow for SmartAgent: engine → connect → options."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_COOLDOWN,
    CONF_ENGINE,
    CONF_LICENSE_KEY,
    CONF_ADDON_AUTH_TOKEN,
    CONF_ADDON_BASE_URL,
    CONF_CLEANUP_LEGACY_PAIR_TOKENS,
    CONF_OLLAMA_URL,
    CONF_OLLAMA_MODEL,
    CONF_ONLINE_API_KEY,
    CONF_ONLINE_BASE_URL,
    CONF_ONLINE_MODEL,
    CONF_ONLINE_PROVIDER,
    CONF_CONFIDENCE_AUTO,
    CONF_CONFIDENCE_NOTIFY,
    CONF_TTS_SERVICE,
    CONF_TTS_TARGET,
    CONF_TTS_LEVEL,
    CONF_FRIGATE_ENABLED,
    CONF_QWEATHER_API_KEY,
    CONF_SEARXNG_URL,
    CONF_CLOUD_FALLBACK,
    CONF_VISION_ENABLED,
    CONF_VISION_ENGINE,
    CONF_VISION_MODEL,
    CONF_MODE,
    TTS_LEVEL_OFF,
    DEFAULT_COOLDOWN,
    DEFAULT_CONFIDENCE_AUTO,
    DEFAULT_CONFIDENCE_NOTIFY,
    DEFAULT_SHOWROOM_BIZ_START,
    DEFAULT_SHOWROOM_BIZ_END,
    CONF_SHOWROOM_BIZ_START,
    CONF_SHOWROOM_BIZ_END,
    CONF_SHOWROOM_AREA_NAME,
    CONF_SHOWROOM_EXCLUDED_SUBAREAS,
    CONF_SHOWROOM_ZONE_MAP,
    DEFAULT_SHOWROOM_AREA_NAME,
    DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS,
    DEFAULT_SHOWROOM_ZONE_MAP,
    CONF_PRESENCE_FUSION,
    DEFAULT_PRESENCE_FUSION,
    MODE_HOME,
    MODE_SHOWROOM,
    parse_biz_time,
    format_biz_time,
    DEFAULT_ENGINE,
    DEFAULT_OLLAMA_URL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_ONLINE_BASE_URL,
    DEFAULT_ONLINE_MODEL,
    DOMAIN,
    ENGINE_LOCAL,
    ENGINE_ONLINE,
    ONLINE_PROVIDER_URLS,
    ONLINE_MODELS_ALL,
    LOCAL_MODELS_SUGGESTIONS,
)
from .addon_client import derive_addon_gateway_base_url

def _validate_hhmm(value: str) -> str:
    """校验并规范化 HH:MM 格式的营业时间字符串。

    :param value: 用户输入的时间字符串（如 "8:50"、"08:50"、"19:00"）
    :return: 规范化的 "HH:MM" 字符串
    :raises vol.Invalid: 格式非法或数值超出范围
    """
    v = str(value).strip()
    if ":" not in v:
        raise vol.Invalid("时间格式应为 HH:MM，如 08:50 或 19:00")
    parts = v.split(":", 1)
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        raise vol.Invalid("时间格式应为 HH:MM，如 08:50 或 19:00")
    if not (0 <= h <= 23):
        raise vol.Invalid("小时必须在 0-23 之间")
    if not (0 <= m <= 59):
        raise vol.Invalid("分钟必须在 0-59 之间")
    return f"{h:02d}:{m:02d}"


# 供应商下拉选项
_PROVIDER_OPTIONS = [
    {"value": "dashscope",   "label": "通义千问 (DashScope)"},
    {"value": "deepseek",    "label": "DeepSeek"},
    {"value": "siliconflow", "label": "SiliconFlow"},
    {"value": "custom",      "label": "自定义（手动填写 API 地址）"},
]

# 云端模型下拉（支持 custom_value，用户可手动输入任意名称）
_ONLINE_MODEL_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=ONLINE_MODELS_ALL,
        custom_value=True,
        mode=selector.SelectSelectorMode.DROPDOWN,
        sort=False,
    )
)

# 本地模型下拉（支持 custom_value）
_LOCAL_MODEL_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=LOCAL_MODELS_SUGGESTIONS,
        custom_value=True,
        mode=selector.SelectSelectorMode.DROPDOWN,
        sort=False,
    )
)

# 引擎选择（单选列表）
_ENGINE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            {"value": ENGINE_LOCAL,  "label": "本地 Ollama"},
            {"value": ENGINE_ONLINE, "label": "云端 API（通义千问 / DeepSeek / 其他）"},
        ],
        mode=selector.SelectSelectorMode.LIST,
    )
)

# 供应商下拉
_PROVIDER_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=_PROVIDER_OPTIONS,
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)

# P2修复：API Key 等敏感字段使用密码选择器，避免在 HA UI 中明文展示
_PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)

# 视觉引擎选择
_VISION_ENGINE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            {"value": ENGINE_LOCAL,  "label": "本地 (Ollama/Llava)"},
            {"value": ENGINE_ONLINE, "label": "云端 (Qwen-VL/Gemini)"},
        ],
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)


def _url_to_provider(url: str) -> str:
    """将已保存的 base_url 反向映射回供应商 key，用于回显。"""
    for prov, purl in ONLINE_PROVIDER_URLS.items():
        if purl and purl == url:
            return prov
    return "custom"


def _build_initial_entry_data(engine_data: dict) -> dict:
    """Build a complete first-install config entry from engine connection data."""
    data = dict(engine_data)
    data.setdefault(CONF_CONFIDENCE_AUTO, DEFAULT_CONFIDENCE_AUTO)
    data.setdefault(CONF_CONFIDENCE_NOTIFY, DEFAULT_CONFIDENCE_NOTIFY)
    data.setdefault(CONF_COOLDOWN, DEFAULT_COOLDOWN)
    data.setdefault(CONF_TTS_SERVICE, "")
    data.setdefault(CONF_TTS_TARGET, "")
    data.setdefault(CONF_TTS_LEVEL, TTS_LEVEL_OFF)
    data.setdefault(CONF_FRIGATE_ENABLED, False)
    data.setdefault(CONF_PRESENCE_FUSION, DEFAULT_PRESENCE_FUSION)
    data.setdefault(CONF_QWEATHER_API_KEY, "")
    data.setdefault(CONF_SEARXNG_URL, "")
    data.setdefault(CONF_CLOUD_FALLBACK, False)
    data.setdefault(CONF_VISION_ENABLED, False)
    data.setdefault(CONF_VISION_ENGINE, ENGINE_ONLINE)
    data.setdefault(CONF_VISION_MODEL, "qwen-vl-max")
    data.setdefault(CONF_MODE, MODE_HOME)
    data.setdefault(CONF_SHOWROOM_BIZ_START, DEFAULT_SHOWROOM_BIZ_START)
    data.setdefault(CONF_SHOWROOM_BIZ_END, DEFAULT_SHOWROOM_BIZ_END)
    data.setdefault(CONF_SHOWROOM_AREA_NAME, DEFAULT_SHOWROOM_AREA_NAME)
    data.setdefault(CONF_SHOWROOM_EXCLUDED_SUBAREAS, DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS)
    data.setdefault(CONF_SHOWROOM_ZONE_MAP, DEFAULT_SHOWROOM_ZONE_MAP)
    return data


def _suggest_addon_base_url(hass: HomeAssistant | None) -> str:
    """Suggest the LAN add-on gateway URL from the HA URL when available."""
    if hass is None:
        return ""
    try:
        from homeassistant.helpers.network import get_url

        return derive_addon_gateway_base_url(get_url(hass))
    except Exception:
        return ""


class SmartAgentConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """多步配置流：engine → connect → options。"""

    VERSION = 1

    def __init__(self) -> None:
        self._engine: str = DEFAULT_ENGINE
        self._data: dict = {}

    # ──────────────────────────────────────────────────────────
    # Step 1: 选择引擎
    # ──────────────────────────────────────────────────────────
    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Step 1: 选择 本地 Ollama 或 云端 API。"""
        if user_input is not None:
            self._engine = user_input[CONF_ENGINE]
            if self._engine == ENGINE_LOCAL:
                return await self.async_step_connect_local()
            return await self.async_step_connect_online()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ENGINE, default=DEFAULT_ENGINE): _ENGINE_SELECTOR,
            }),
        )
    # ──────────────────────────────────────────────────────────
    # Step 2a: 本地 Ollama — IP 地址 + 模型
    # ──────────────────────────────────────────────────────────
    async def async_step_connect_local(self, user_input: dict | None = None) -> FlowResult:
        """Step 2a: 填写 Ollama 服务 IP/URL 与模型名。"""
        if user_input is not None:
            self._data = _build_initial_entry_data({
                CONF_ENGINE:           ENGINE_LOCAL,
                CONF_OLLAMA_URL:       (user_input.get(CONF_OLLAMA_URL) or DEFAULT_OLLAMA_URL).strip(),
                CONF_OLLAMA_MODEL:     (user_input.get(CONF_OLLAMA_MODEL) or DEFAULT_OLLAMA_MODEL).strip(),
                CONF_ONLINE_API_KEY:   "",
                CONF_ONLINE_BASE_URL:  DEFAULT_ONLINE_BASE_URL,
                CONF_ONLINE_MODEL:     DEFAULT_ONLINE_MODEL,
            })
            return self.async_create_entry(title="AI SmartAgent", data=self._data)

        return self.async_show_form(
            step_id="connect_local",
            data_schema=vol.Schema({
                vol.Required(CONF_OLLAMA_URL,   default=DEFAULT_OLLAMA_URL):   str,
                vol.Required(CONF_OLLAMA_MODEL, default=DEFAULT_OLLAMA_MODEL): _LOCAL_MODEL_SELECTOR,
            }),
        )

    # ──────────────────────────────────────────────────────────
    # Step 2b: 云端 API — 供应商 + Key + 模型
    # ──────────────────────────────────────────────────────────
    async def async_step_connect_online(self, user_input: dict | None = None) -> FlowResult:
        """Step 2b: 选择供应商、填写 API Key 与模型。"""
        errors: dict = {}

        if user_input is not None:
            key = (user_input.get(CONF_ONLINE_API_KEY) or "").strip()
            provider = user_input.get(CONF_ONLINE_PROVIDER, "dashscope")

            if not key:
                errors["base"] = "invalid_api_key"
            else:
                if provider == "custom":
                    base_url = (user_input.get(CONF_ONLINE_BASE_URL) or "").strip()
                    if not base_url:
                        errors["base"] = "invalid_base_url"
                else:
                    base_url = ONLINE_PROVIDER_URLS.get(provider, DEFAULT_ONLINE_BASE_URL)

            if not errors:
                self._data = _build_initial_entry_data({
                    CONF_ENGINE:          ENGINE_ONLINE,
                    CONF_OLLAMA_URL:      DEFAULT_OLLAMA_URL,
                    CONF_OLLAMA_MODEL:    DEFAULT_OLLAMA_MODEL,
                    CONF_ONLINE_API_KEY:  key,
                    CONF_ONLINE_BASE_URL: base_url,
                    CONF_ONLINE_MODEL:    (user_input.get(CONF_ONLINE_MODEL) or DEFAULT_ONLINE_MODEL).strip(),
                })
                return self.async_create_entry(title="AI SmartAgent", data=self._data)

        # 回显上次输入（有错误时）
        prev = user_input or {}
        return self.async_show_form(
            step_id="connect_online",
            data_schema=vol.Schema({
                vol.Required(CONF_ONLINE_PROVIDER,
                             default=prev.get(CONF_ONLINE_PROVIDER, "dashscope")): _PROVIDER_SELECTOR,
                vol.Required(CONF_ONLINE_API_KEY,
                             default=prev.get(CONF_ONLINE_API_KEY, "")): _PASSWORD_SELECTOR,
                vol.Required(CONF_ONLINE_MODEL,
                             default=prev.get(CONF_ONLINE_MODEL, DEFAULT_ONLINE_MODEL)): _ONLINE_MODEL_SELECTOR,
                # 仅在选择「自定义」时需要填写，其他供应商留空即可
                vol.Optional(CONF_ONLINE_BASE_URL,
                             default=prev.get(CONF_ONLINE_BASE_URL, "")): str,
            }),
            errors=errors,
        )
    # ──────────────────────────────────────────────────────────
    # Step 3: 置信度与冷却
    # ──────────────────────────────────────────────────────────
    async def async_step_options(self, user_input: dict | None = None) -> FlowResult:
        """Step 3: 自动执行阈值、通知阈值、设备冷却时间，以及 TTS / Frigate 可选配置。"""
        errors: dict = {}
        if user_input is not None:
            self._data[CONF_CONFIDENCE_AUTO]   = int(user_input[CONF_CONFIDENCE_AUTO])
            self._data[CONF_CONFIDENCE_NOTIFY] = int(user_input[CONF_CONFIDENCE_NOTIFY])
            self._data[CONF_COOLDOWN]          = int(user_input[CONF_COOLDOWN])
            self._data[CONF_TTS_SERVICE]       = (user_input.get(CONF_TTS_SERVICE) or "").strip()
            self._data[CONF_TTS_TARGET]        = (user_input.get(CONF_TTS_TARGET) or "").strip()
            self._data[CONF_TTS_LEVEL]         = int(user_input.get(CONF_TTS_LEVEL, TTS_LEVEL_OFF))
            self._data[CONF_FRIGATE_ENABLED]   = bool(user_input.get(CONF_FRIGATE_ENABLED, False))
            self._data[CONF_QWEATHER_API_KEY]  = (user_input.get(CONF_QWEATHER_API_KEY) or "").strip()
            self._data[CONF_SEARXNG_URL]       = (user_input.get(CONF_SEARXNG_URL) or "").strip()
            self._data[CONF_CLOUD_FALLBACK]    = bool(user_input.get(CONF_CLOUD_FALLBACK, False))
            self._data[CONF_VISION_ENABLED]    = bool(user_input.get(CONF_VISION_ENABLED, False))
            self._data[CONF_VISION_ENGINE]     = user_input.get(CONF_VISION_ENGINE, ENGINE_ONLINE)
            self._data[CONF_VISION_MODEL]      = (user_input.get(CONF_VISION_MODEL) or "qwen-vl-max").strip()
            
            try:
                biz_start_str = _validate_hhmm(user_input.get(CONF_SHOWROOM_BIZ_START, DEFAULT_SHOWROOM_BIZ_START))
                biz_end_str   = _validate_hhmm(user_input.get(CONF_SHOWROOM_BIZ_END, DEFAULT_SHOWROOM_BIZ_END))
            except vol.Invalid as e:
                errors["base"] = "biz_time_invalid"
                biz_start_str, biz_end_str = DEFAULT_SHOWROOM_BIZ_START, DEFAULT_SHOWROOM_BIZ_END

            if not errors and parse_biz_time(biz_start_str) >= parse_biz_time(biz_end_str):
                errors["base"] = "biz_time_invalid"

            if not errors:
                self._data[CONF_SHOWROOM_BIZ_START] = biz_start_str
                self._data[CONF_SHOWROOM_BIZ_END]   = biz_end_str

                # P2修复：以下字段在 schema 中定义但初始安装时未写入 _data，
                # 导致首次安装后缺失，需在此补全
                self._data[CONF_PRESENCE_FUSION]           = (user_input.get(CONF_PRESENCE_FUSION) or "").strip()
                self._data[CONF_SHOWROOM_AREA_NAME]        = (user_input.get(CONF_SHOWROOM_AREA_NAME) or DEFAULT_SHOWROOM_AREA_NAME).strip()
                self._data[CONF_SHOWROOM_EXCLUDED_SUBAREAS] = (user_input.get(CONF_SHOWROOM_EXCLUDED_SUBAREAS) or DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS).strip()

                # TODO(license): 上线时取消注释
                # self._data[CONF_LICENSE_KEY] = (user_input.get(CONF_LICENSE_KEY) or "").strip()
                return self.async_create_entry(title="AI SmartAgent", data=self._data)

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({
                # ── 置信度与冷却 ──
                vol.Required(CONF_CONFIDENCE_AUTO,   default=DEFAULT_CONFIDENCE_AUTO):   vol.All(int, vol.Range(min=50, max=100)),
                vol.Required(CONF_CONFIDENCE_NOTIFY, default=DEFAULT_CONFIDENCE_NOTIFY): vol.All(int, vol.Range(min=30, max=100)),
                vol.Required(CONF_COOLDOWN,          default=DEFAULT_COOLDOWN):          vol.All(int, vol.Range(min=10, max=300)),
                # ── TTS 语音播报（可选）──
                vol.Optional(CONF_TTS_SERVICE,  default=""): str,
                vol.Optional(CONF_TTS_TARGET,   default=""): str,
                vol.Optional(CONF_TTS_LEVEL,    default=TTS_LEVEL_OFF): vol.All(int, vol.Range(min=0, max=3)),
                # ── Frigate NVR 视觉感知（可选）──
                vol.Optional(CONF_FRIGATE_ENABLED, default=False): bool,
                # ── 存在传感器融合域（Phase 12.0，可选）──
                # 解决「一镜多区 / 大开间多传感器」误判：茶桌 zone 无人 ≠ 整个客餐厅无人。
                # 支持两种 members 写法：
                # 1) 旧版字符串数组：
                #    "members": ["binary_sensor.a", "binary_sensor.b"]
                # 2) 新版对象数组（能力驱动，推荐）：
                #    "members": [
                #      {"entity_id":"binary_sensor.cam_living","can_enter_trigger":true,"can_leave_evidence":true},
                #      {"entity_id":"binary_sensor.mmwave_living","can_enter_trigger":false,"can_leave_evidence":true}
                #    ]
                # 额外支持 enter_hold_secs / vacant_hold_secs 做进入/离开迟滞。
                vol.Optional(CONF_PRESENCE_FUSION, default=""): str,
                # ── 联网与工具（Phase 5）──
                vol.Optional(CONF_QWEATHER_API_KEY, default=""): str,
                vol.Optional(CONF_SEARXNG_URL,      default=""): str,
                vol.Optional(CONF_CLOUD_FALLBACK,   default=False): bool,
                # ── AI 视觉增强（Phase 7E）──
                vol.Optional(CONF_VISION_ENABLED,   default=False): bool,
                vol.Optional(CONF_VISION_ENGINE,    default=ENGINE_ONLINE): _VISION_ENGINE_SELECTOR,
                vol.Optional(CONF_VISION_MODEL,     default="qwen-vl-max"): str,

                # ── 展厅营业时间与区域配置 ──
                vol.Required(CONF_SHOWROOM_BIZ_START,
                             default=DEFAULT_SHOWROOM_BIZ_START): _validate_hhmm,
                vol.Required(CONF_SHOWROOM_BIZ_END,
                             default=DEFAULT_SHOWROOM_BIZ_END): _validate_hhmm,
                vol.Optional(CONF_SHOWROOM_AREA_NAME,
                             default=DEFAULT_SHOWROOM_AREA_NAME): str,
                vol.Optional(CONF_SHOWROOM_EXCLUDED_SUBAREAS,
                             default=DEFAULT_SHOWROOM_EXCLUDED_SUBAREAS): str,

                # TODO(license): 上线时取消注释
                # vol.Optional(CONF_LICENSE_KEY, default=""): str,
            }),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "SmartAgentOptionsFlowHandler":
        """返回选项流。"""
        return SmartAgentOptionsFlowHandler()


class SmartAgentOptionsFlowHandler(config_entries.OptionsFlow):
    """选项流：仅保留 HA 到 add-on 的连接参数。"""

    def __init__(self) -> None:
        """初始化选项流。"""
        super().__init__()

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """HA 侧只维护连接 add-on 所需的最小配置。"""
        d = {**(self.config_entry.data or {}), **(self.config_entry.options or {})}
        errors: dict = {}

        if user_input is not None:
            saved = {
                CONF_ADDON_BASE_URL: (user_input.get(CONF_ADDON_BASE_URL) or "").strip(),
                CONF_ADDON_AUTH_TOKEN: (user_input.get(CONF_ADDON_AUTH_TOKEN) or "").strip(),
                CONF_CLEANUP_LEGACY_PAIR_TOKENS: bool(user_input.get(CONF_CLEANUP_LEGACY_PAIR_TOKENS, False)),
            }
            return self.async_create_entry(title="", data=saved)

        addon_base_default = (d.get(CONF_ADDON_BASE_URL) or "").strip() or _suggest_addon_base_url(self.hass)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_ADDON_BASE_URL,
                             default=addon_base_default): str,
                vol.Optional(CONF_ADDON_AUTH_TOKEN,
                             default=d.get(CONF_ADDON_AUTH_TOKEN, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_CLEANUP_LEGACY_PAIR_TOKENS,
                             default=d.get(CONF_CLEANUP_LEGACY_PAIR_TOKENS, False)): bool,
            }),
            errors=errors,
        )
