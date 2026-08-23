"""Config flow for SmartAgent: engine -> connect, with add-on connection options."""
from __future__ import annotations

from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVE_AI_MODE,
    CONF_COOLDOWN,
    CONF_ENGINE,
    CONF_ADDON_AUTH_TOKEN,
    CONF_ADDON_BASE_URL,
    CONF_CLEANUP_LEGACY_PAIR_TOKENS,
    CONF_REFRESH_REGISTRY_SOURCE_ENABLED,
    CONF_REFRESH_REGISTRY_INGRESS_URL,
    CONF_REFRESH_REGISTRY_SITE_ID,
    CONF_REFRESH_REGISTRY_INGRESS_SECRET,
    CONF_REFRESH_REGISTRY_ATTESTATION_SECRET,
    DEFAULT_REFRESH_REGISTRY_INGRESS_URL,
    CONF_OBSERVATION_REFRESH_PROVIDER_RUNTIME_ENABLED,
    CONF_OBSERVATION_REFRESH_PROVIDER_REQUEST_SECRET,
    CONF_OBSERVATION_REFRESH_PROVIDER_PREVIOUS_REQUEST_SECRET,
    CONF_OBSERVATION_REFRESH_PROVIDER_REPLAY_INTEGRITY_SECRET,
    CONF_OUTPUT_LEDGER_INGRESS_ENABLED,
    CONF_OUTPUT_LEDGER_INGRESS_URL,
    CONF_OUTPUT_LEDGER_INGRESS_SECRET,
    CONF_OUTPUT_LEDGER_ATTESTATION_SECRET,
    DEFAULT_OUTPUT_LEDGER_INGRESS_URL,
    CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED,
    CONF_MAINTENANCE_CHANGE_INGRESS_URL,
    CONF_MAINTENANCE_CHANGE_INGRESS_SECRET,
    CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET,
    DEFAULT_MAINTENANCE_CHANGE_INGRESS_URL,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET,
    CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET,
    DEFAULT_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
    CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_ENABLED,
    CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_SECRET,
    CONF_FIELD_CANARY_PREVIOUS_HOST_DISPATCH_PROOF_SECRET,
    CONF_USER_INTENT_DELEGATION_SECRET,
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
    DEFAULT_ACTIVE_AI_MODE,
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
from .security_channel_secrets import security_channel_secret_mapping_is_valid


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

def _url_to_provider(url: str) -> str:
    """将已保存的 base_url 反向映射回供应商 key，用于回显。"""
    for prov, purl in ONLINE_PROVIDER_URLS.items():
        if purl and purl == url:
            return prov
    return "custom"


def _build_initial_entry_data(engine_data: dict) -> dict:
    """Build a complete first-install config entry from engine connection data."""
    data = dict(engine_data)
    data.setdefault(CONF_ACTIVE_AI_MODE, DEFAULT_ACTIVE_AI_MODE)
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
    """First-install flow for choosing the engine and its connection settings."""

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
            refresh_enabled = (
                user_input.get(CONF_REFRESH_REGISTRY_SOURCE_ENABLED, False) is True
            )
            refresh_url_raw = user_input.get(CONF_REFRESH_REGISTRY_INGRESS_URL) or ""
            refresh_site_raw = user_input.get(CONF_REFRESH_REGISTRY_SITE_ID) or ""
            refresh_url = (
                refresh_url_raw.strip() if type(refresh_url_raw) is str else ""
            )
            refresh_site = (
                refresh_site_raw.strip() if type(refresh_site_raw) is str else ""
            )
            refresh_ingress_secret = user_input.get(
                CONF_REFRESH_REGISTRY_INGRESS_SECRET, ""
            )
            refresh_attestation_secret = user_input.get(
                CONF_REFRESH_REGISTRY_ATTESTATION_SECRET, ""
            )
            provider_runtime_enabled_value = user_input.get(
                CONF_OBSERVATION_REFRESH_PROVIDER_RUNTIME_ENABLED,
                False,
            )
            provider_runtime_enabled = provider_runtime_enabled_value is True
            provider_request_secret = user_input.get(
                CONF_OBSERVATION_REFRESH_PROVIDER_REQUEST_SECRET,
                "",
            )
            provider_previous_request_secret = user_input.get(
                CONF_OBSERVATION_REFRESH_PROVIDER_PREVIOUS_REQUEST_SECRET,
                "",
            )
            provider_replay_integrity_secret = user_input.get(
                CONF_OBSERVATION_REFRESH_PROVIDER_REPLAY_INTEGRITY_SECRET,
                "",
            )
            output_enabled_value = user_input.get(
                CONF_OUTPUT_LEDGER_INGRESS_ENABLED,
                False,
            )
            output_enabled = output_enabled_value is True
            output_url_raw = user_input.get(
                CONF_OUTPUT_LEDGER_INGRESS_URL,
                "",
            )
            output_url = (
                output_url_raw.strip()
                if type(output_url_raw) is str
                else ""
            )
            output_ingress_secret = user_input.get(
                CONF_OUTPUT_LEDGER_INGRESS_SECRET,
                "",
            )
            output_attestation_secret = user_input.get(
                CONF_OUTPUT_LEDGER_ATTESTATION_SECRET,
                "",
            )
            maintenance_enabled_value = user_input.get(
                CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED,
                False,
            )
            maintenance_enabled = maintenance_enabled_value is True
            maintenance_url_raw = user_input.get(
                CONF_MAINTENANCE_CHANGE_INGRESS_URL,
                "",
            )
            maintenance_url = (
                maintenance_url_raw.strip()
                if type(maintenance_url_raw) is str
                else ""
            )
            maintenance_ingress_secret = user_input.get(
                CONF_MAINTENANCE_CHANGE_INGRESS_SECRET,
                "",
            )
            maintenance_attestation_secret = user_input.get(
                CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET,
                "",
            )
            operator_enabled = (
                user_input.get(
                    CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED, False
                )
                is True
            )
            operator_url_raw = user_input.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL
            ) or ""
            operator_url = (
                operator_url_raw.strip()
                if type(operator_url_raw) is str
                else ""
            )
            operator_ingress_secret = user_input.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET, ""
            )
            operator_attestation_secret = user_input.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET, ""
            )
            operator_previous_attestation_secret = user_input.get(
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET,
                "",
            )
            host_proof_enabled = (
                user_input.get(
                    CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_ENABLED,
                    False,
                )
                is True
            )
            host_proof_secret_raw = user_input.get(
                CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_SECRET,
                "",
            )
            previous_host_proof_secret_raw = user_input.get(
                CONF_FIELD_CANARY_PREVIOUS_HOST_DISPATCH_PROOF_SECRET,
                "",
            )
            host_proof_secret = (
                host_proof_secret_raw.strip()
                if type(host_proof_secret_raw) is str
                else ""
            )
            previous_host_proof_secret = (
                previous_host_proof_secret_raw.strip()
                if type(previous_host_proof_secret_raw) is str
                else ""
            )
            user_intent_delegation_secret = user_input.get(
                CONF_USER_INTENT_DELEGATION_SECRET,
                "",
            )
            if refresh_enabled:
                parsed_refresh_url = urlsplit(refresh_url)
                refresh_texts = (
                    refresh_site,
                    refresh_ingress_secret,
                    refresh_attestation_secret,
                )
                if (
                    parsed_refresh_url.scheme not in {"http", "https"}
                    or type(refresh_url_raw) is not str
                    or type(refresh_site_raw) is not str
                    or not parsed_refresh_url.hostname
                    or parsed_refresh_url.username is not None
                    or parsed_refresh_url.password is not None
                    or parsed_refresh_url.query
                    or parsed_refresh_url.fragment
                    or parsed_refresh_url.path not in {"", "/"}
                    or any(type(value) is not str for value in refresh_texts)
                    or not refresh_site
                    or refresh_site != refresh_site.strip()
                    or len(refresh_ingress_secret) < 32
                    or len(refresh_attestation_secret) < 32
                    or refresh_ingress_secret != refresh_ingress_secret.strip()
                    or refresh_attestation_secret
                    != refresh_attestation_secret.strip()
                    or refresh_ingress_secret == refresh_attestation_secret
                    or any(
                        ord(character) < 32 or ord(character) == 127
                        for value in refresh_texts
                        for character in value
                    )
                ):
                    errors["base"] = "invalid_refresh_registry_config"
                    user_input = None
            if user_input is not None and operator_enabled:
                parsed_operator_url = urlsplit(operator_url)
                operator_secrets = (
                    operator_ingress_secret,
                    operator_attestation_secret,
                )
                optional_operator_secrets = (
                    operator_previous_attestation_secret,
                )
                all_operator_values = operator_secrets + tuple(
                    value for value in optional_operator_secrets if value
                )
                if (
                    type(operator_url_raw) is not str
                    or parsed_operator_url.scheme not in {"http", "https"}
                    or not parsed_operator_url.hostname
                    or parsed_operator_url.username is not None
                    or parsed_operator_url.password is not None
                    or parsed_operator_url.query
                    or parsed_operator_url.fragment
                    or parsed_operator_url.path not in {"", "/"}
                    or any(type(value) is not str for value in all_operator_values)
                    or any(len(value) < 32 for value in all_operator_values)
                    or any(value != value.strip() for value in all_operator_values)
                    or len(set(all_operator_values)) != len(all_operator_values)
                    or any(
                        ord(character) < 32 or ord(character) == 127
                        for value in all_operator_values
                        for character in value
                    )
                ):
                    errors["base"] = "invalid_field_canary_operator_identity_config"
                    user_input = None
            if user_input is not None and (
                provider_runtime_enabled
                or bool(provider_request_secret)
                or bool(provider_previous_request_secret)
                or bool(provider_replay_integrity_secret)
            ):
                provider_secrets = (
                    provider_request_secret,
                    provider_previous_request_secret,
                    provider_replay_integrity_secret,
                )
                nonempty_provider_secrets = tuple(
                    value for value in provider_secrets if value
                )
                if (
                    type(provider_runtime_enabled_value) is not bool
                    or any(type(value) is not str for value in provider_secrets)
                    or (
                        provider_runtime_enabled
                        and (
                            not provider_request_secret
                            or not provider_replay_integrity_secret
                        )
                    )
                    or any(
                        len(value) < 32 for value in nonempty_provider_secrets
                    )
                    or any(
                        value != value.strip()
                        for value in nonempty_provider_secrets
                    )
                    or len(set(nonempty_provider_secrets))
                    != len(nonempty_provider_secrets)
                    or any(
                        ord(character) < 32 or ord(character) == 127
                        for value in nonempty_provider_secrets
                        for character in value
                    )
                ):
                    errors["base"] = (
                        "invalid_observation_refresh_provider_config"
                    )
                    user_input = None
            if user_input is not None and output_enabled:
                parsed_output_url = urlsplit(output_url)
                output_secrets = (
                    output_ingress_secret,
                    output_attestation_secret,
                )
                if (
                    type(output_enabled_value) is not bool
                    or type(output_url_raw) is not str
                    or parsed_output_url.scheme not in {"http", "https"}
                    or not parsed_output_url.hostname
                    or parsed_output_url.username is not None
                    or parsed_output_url.password is not None
                    or parsed_output_url.query
                    or parsed_output_url.fragment
                    or parsed_output_url.path not in {"", "/"}
                    or any(type(value) is not str for value in output_secrets)
                    or any(len(value) < 32 for value in output_secrets)
                    or any(value != value.strip() for value in output_secrets)
                    or len(set(output_secrets)) != len(output_secrets)
                    or any(
                        ord(character) < 32 or ord(character) == 127
                        for value in output_secrets
                        for character in value
                    )
                ):
                    errors["base"] = "invalid_output_ledger_config"
                    user_input = None
            if user_input is not None and maintenance_enabled:
                parsed_maintenance_url = urlsplit(maintenance_url)
                maintenance_secrets = (
                    maintenance_ingress_secret,
                    maintenance_attestation_secret,
                )
                if (
                    type(maintenance_enabled_value) is not bool
                    or type(maintenance_url_raw) is not str
                    or parsed_maintenance_url.scheme not in {"http", "https"}
                    or not parsed_maintenance_url.hostname
                    or parsed_maintenance_url.username is not None
                    or parsed_maintenance_url.password is not None
                    or parsed_maintenance_url.query
                    or parsed_maintenance_url.fragment
                    or parsed_maintenance_url.path not in {"", "/"}
                    or any(type(value) is not str for value in maintenance_secrets)
                    or any(len(value) < 32 for value in maintenance_secrets)
                    or any(value != value.strip() for value in maintenance_secrets)
                    or len(set(maintenance_secrets)) != len(maintenance_secrets)
                    or any(
                        ord(character) < 32 or ord(character) == 127
                        for value in maintenance_secrets
                        for character in value
                    )
                ):
                    errors["base"] = "invalid_maintenance_change_ingress_config"
                    user_input = None
            if user_input is not None and (
                host_proof_enabled
                or bool(host_proof_secret_raw)
                or bool(previous_host_proof_secret_raw)
            ):
                host_proof_values = (
                    host_proof_secret,
                    previous_host_proof_secret,
                )
                nonempty_host_proof_values = tuple(
                    value for value in host_proof_values if value
                )
                addon_auth_token = user_input.get(CONF_ADDON_AUTH_TOKEN) or ""
                if (
                    type(host_proof_secret_raw) is not str
                    or type(previous_host_proof_secret_raw) is not str
                    or type(addon_auth_token) is not str
                    or (host_proof_enabled and not host_proof_secret)
                    or any(len(value) < 32 for value in nonempty_host_proof_values)
                    or host_proof_secret_raw != host_proof_secret
                    or previous_host_proof_secret_raw
                    != previous_host_proof_secret
                    or len(set(nonempty_host_proof_values))
                    != len(nonempty_host_proof_values)
                    or addon_auth_token.strip() in nonempty_host_proof_values
                    or any(
                        ord(character) < 32 or ord(character) == 127
                        for value in nonempty_host_proof_values
                        for character in value
                    )
                ):
                    errors["base"] = (
                        "invalid_field_canary_host_dispatch_proof_config"
                    )
                    user_input = None
            if user_input is not None and not (
                security_channel_secret_mapping_is_valid(user_input)
            ):
                errors["base"] = "invalid_security_channel_secret_separation"
                user_input = None
            if user_input is None:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._options_schema(d),
                    errors=errors,
                )
            saved = {
                CONF_ADDON_BASE_URL: (user_input.get(CONF_ADDON_BASE_URL) or "").strip(),
                CONF_ADDON_AUTH_TOKEN: (user_input.get(CONF_ADDON_AUTH_TOKEN) or "").strip(),
                CONF_CLEANUP_LEGACY_PAIR_TOKENS: bool(user_input.get(CONF_CLEANUP_LEGACY_PAIR_TOKENS, False)),
                CONF_REFRESH_REGISTRY_SOURCE_ENABLED: refresh_enabled,
                CONF_REFRESH_REGISTRY_INGRESS_URL: refresh_url,
                CONF_REFRESH_REGISTRY_SITE_ID: refresh_site,
                CONF_REFRESH_REGISTRY_INGRESS_SECRET: refresh_ingress_secret,
                CONF_REFRESH_REGISTRY_ATTESTATION_SECRET: refresh_attestation_secret,
                CONF_OBSERVATION_REFRESH_PROVIDER_RUNTIME_ENABLED: provider_runtime_enabled,
                CONF_OBSERVATION_REFRESH_PROVIDER_REQUEST_SECRET: provider_request_secret,
                CONF_OBSERVATION_REFRESH_PROVIDER_PREVIOUS_REQUEST_SECRET: provider_previous_request_secret,
                CONF_OBSERVATION_REFRESH_PROVIDER_REPLAY_INTEGRITY_SECRET: provider_replay_integrity_secret,
                CONF_OUTPUT_LEDGER_INGRESS_ENABLED: output_enabled,
                CONF_OUTPUT_LEDGER_INGRESS_URL: output_url,
                CONF_OUTPUT_LEDGER_INGRESS_SECRET: output_ingress_secret,
                CONF_OUTPUT_LEDGER_ATTESTATION_SECRET: output_attestation_secret,
                CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED: maintenance_enabled,
                CONF_MAINTENANCE_CHANGE_INGRESS_URL: maintenance_url,
                CONF_MAINTENANCE_CHANGE_INGRESS_SECRET: maintenance_ingress_secret,
                CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET: maintenance_attestation_secret,
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED: operator_enabled,
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL: operator_url,
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET: operator_ingress_secret,
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET: operator_attestation_secret,
                CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET: operator_previous_attestation_secret,
                CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_ENABLED: host_proof_enabled,
                CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_SECRET: host_proof_secret,
                CONF_FIELD_CANARY_PREVIOUS_HOST_DISPATCH_PROOF_SECRET: previous_host_proof_secret,
                CONF_USER_INTENT_DELEGATION_SECRET: user_intent_delegation_secret,
            }
            return self.async_create_entry(title="", data=saved)

        addon_base_default = (d.get(CONF_ADDON_BASE_URL) or "").strip() or _suggest_addon_base_url(self.hass)

        return self.async_show_form(
            step_id="init",
            data_schema=self._options_schema(d, addon_base_default=addon_base_default),
            errors=errors,
        )

    def _options_schema(
        self, d: dict, *, addon_base_default: str | None = None
    ) -> vol.Schema:
        if addon_base_default is None:
            addon_base_default = (
                (d.get(CONF_ADDON_BASE_URL) or "").strip()
                or _suggest_addon_base_url(self.hass)
            )
        return vol.Schema({
                vol.Optional(CONF_ADDON_BASE_URL,
                             default=addon_base_default): str,
                vol.Optional(CONF_ADDON_AUTH_TOKEN,
                             default=d.get(CONF_ADDON_AUTH_TOKEN, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_ENABLED,
                             default=d.get(CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_ENABLED, False)): bool,
                vol.Optional(CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_SECRET,
                             default=d.get(CONF_FIELD_CANARY_HOST_DISPATCH_PROOF_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_FIELD_CANARY_PREVIOUS_HOST_DISPATCH_PROOF_SECRET,
                             default=d.get(CONF_FIELD_CANARY_PREVIOUS_HOST_DISPATCH_PROOF_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_USER_INTENT_DELEGATION_SECRET,
                             default=d.get(CONF_USER_INTENT_DELEGATION_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_CLEANUP_LEGACY_PAIR_TOKENS,
                             default=d.get(CONF_CLEANUP_LEGACY_PAIR_TOKENS, False)): bool,
                vol.Optional(CONF_REFRESH_REGISTRY_SOURCE_ENABLED,
                             default=d.get(CONF_REFRESH_REGISTRY_SOURCE_ENABLED, False)): bool,
                vol.Optional(CONF_REFRESH_REGISTRY_INGRESS_URL,
                             default=d.get(CONF_REFRESH_REGISTRY_INGRESS_URL,
                                           DEFAULT_REFRESH_REGISTRY_INGRESS_URL)): str,
                vol.Optional(CONF_REFRESH_REGISTRY_SITE_ID,
                             default=d.get(CONF_REFRESH_REGISTRY_SITE_ID, "")): str,
                vol.Optional(CONF_REFRESH_REGISTRY_INGRESS_SECRET,
                             default=d.get(CONF_REFRESH_REGISTRY_INGRESS_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_REFRESH_REGISTRY_ATTESTATION_SECRET,
                             default=d.get(CONF_REFRESH_REGISTRY_ATTESTATION_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_OBSERVATION_REFRESH_PROVIDER_RUNTIME_ENABLED,
                             default=d.get(CONF_OBSERVATION_REFRESH_PROVIDER_RUNTIME_ENABLED, False)): bool,
                vol.Optional(CONF_OBSERVATION_REFRESH_PROVIDER_REQUEST_SECRET,
                             default=d.get(CONF_OBSERVATION_REFRESH_PROVIDER_REQUEST_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_OBSERVATION_REFRESH_PROVIDER_PREVIOUS_REQUEST_SECRET,
                             default=d.get(CONF_OBSERVATION_REFRESH_PROVIDER_PREVIOUS_REQUEST_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_OBSERVATION_REFRESH_PROVIDER_REPLAY_INTEGRITY_SECRET,
                             default=d.get(CONF_OBSERVATION_REFRESH_PROVIDER_REPLAY_INTEGRITY_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_OUTPUT_LEDGER_INGRESS_ENABLED,
                             default=d.get(CONF_OUTPUT_LEDGER_INGRESS_ENABLED, False)): bool,
                vol.Optional(CONF_OUTPUT_LEDGER_INGRESS_URL,
                             default=d.get(CONF_OUTPUT_LEDGER_INGRESS_URL,
                                           DEFAULT_OUTPUT_LEDGER_INGRESS_URL)): str,
                vol.Optional(CONF_OUTPUT_LEDGER_INGRESS_SECRET,
                             default=d.get(CONF_OUTPUT_LEDGER_INGRESS_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_OUTPUT_LEDGER_ATTESTATION_SECRET,
                             default=d.get(CONF_OUTPUT_LEDGER_ATTESTATION_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED,
                             default=d.get(CONF_MAINTENANCE_CHANGE_INGRESS_ENABLED, False)): bool,
                vol.Optional(CONF_MAINTENANCE_CHANGE_INGRESS_URL,
                             default=d.get(CONF_MAINTENANCE_CHANGE_INGRESS_URL,
                                           DEFAULT_MAINTENANCE_CHANGE_INGRESS_URL)): str,
                vol.Optional(CONF_MAINTENANCE_CHANGE_INGRESS_SECRET,
                             default=d.get(CONF_MAINTENANCE_CHANGE_INGRESS_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET,
                             default=d.get(CONF_MAINTENANCE_DELEGATION_ATTESTATION_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED,
                             default=d.get(CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_ENABLED, False)): bool,
                vol.Optional(CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
                             default=d.get(CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL,
                                           DEFAULT_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_URL)): str,
                vol.Optional(CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET,
                             default=d.get(CONF_FIELD_CANARY_OPERATOR_IDENTITY_INGRESS_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET,
                             default=d.get(CONF_FIELD_CANARY_OPERATOR_IDENTITY_ATTESTATION_SECRET, "")): _PASSWORD_SELECTOR,
                vol.Optional(CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET,
                             default=d.get(CONF_FIELD_CANARY_OPERATOR_IDENTITY_PREVIOUS_ATTESTATION_SECRET, "")): _PASSWORD_SELECTOR,
            })
