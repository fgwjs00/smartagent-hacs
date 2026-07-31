"""Conversation support for AI SmartAgent."""
from __future__ import annotations

import logging
from typing import Literal

from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import SmartAgentCoordinator
from .voice_text import normalize_voice_stt_text

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
    """Set up the SmartAgent conversation platform."""
    coordinator: SmartAgentCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    agent = SmartAgentConversation(hass, coordinator)
    async_add_entities([agent])
    _LOGGER.info("SmartAgent Conversation Agent registered successfully.")

class SmartAgentConversation(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """SmartAgent conversation agent."""

    _attr_has_entity_name = True
    _attr_name = "AI SmartAgent"

    def __init__(self, hass: HomeAssistant, coordinator: SmartAgentCoordinator) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator._entry.entry_id}_conversation"

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages. We support any (*) to catch all voice via Whisper."""
        return ["zh", "en", "*"]

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence passed from HA Assist or Wyoming satellites."""
        raw_text = user_input.text
        text = normalize_voice_stt_text(raw_text)
        source_id = user_input.device_id or "unknown"
        if text != str(raw_text or "").strip():
            _LOGGER.info(
                "[Conversation API] Normalized zh-CN voice input: %s -> %s from device %s",
                raw_text,
                text,
                source_id,
            )
        else:
            _LOGGER.info("[Conversation API] Received user dialog: %s from device %s", text, source_id)
        
        # Dispatch to AI SmartAgent's voice inference router (System 2 Slow Brain)
        try:
            result = await self.coordinator._run_voice_inference(text, source=f"conversation_api_{source_id}")
            
            reply_text = result.get("reply", "处理完毕")
            if result.get("status") == "error":
                reply_text = result.get("message", "抱歉，由于未知异常，AI无法处理您的指令")
                
        except Exception as exc:
            _LOGGER.exception("[Conversation API] Core exception during inference: %s", exc)
            reply_text = "系统发生活跃错误，请检查日志"

        # Construct the HA Intent Response so HA knows what to speak via TTS
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(reply_text)
        
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )
