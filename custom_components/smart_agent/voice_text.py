"""Conservative Simplified-Chinese normalization for SmartAgent voice input."""
from __future__ import annotations

from typing import Any

VOICE_TEXT_NORMALIZATION_CONTRACT_VERSION = "smartagent.voice-text.zh-CN.v1"

# Compatibility projection only. The authoritative rule source is
# smartagent-addon/api_server_voice_protocol.py::voice_text_normalization_contract().
# The backend contract test rejects any projection drift before release.
_VOICE_TEXT_NORMALIZATION_COMPATIBILITY_PROJECTION = {
    "contract_version": VOICE_TEXT_NORMALIZATION_CONTRACT_VERSION,
    "language": "zh-CN",
    "translation_pairs": (
        ("\u958b", "\u5f00"),
        ("\u95dc", "\u5173"),
        ("\u9589", "\u95ed"),
        ("\u555f", "\u542f"),
        ("\u5ef3", "\u5385"),
        ("\u81e5", "\u5367"),
        ("\u71c8", "\u706f"),
        ("\u5e36", "\u5e26"),
        ("\u7c3e", "\u5e18"),
        ("\u5eda", "\u53a8"),
        ("\u885b", "\u536b"),
        ("\u9593", "\u95f4"),
        ("\u8abf", "\u8c03"),
        ("\u8072", "\u58f0"),
        ("\u7db2", "\u7f51"),
        ("\u7dda", "\u7ebf"),
        ("\u98a8", "\u98ce"),
        ("\u6c23", "\u6c14"),
        ("\u6eab", "\u6e29"),
        ("\u6fd5", "\u6e7f"),
        ("\u9396", "\u9501"),
        ("\u9580", "\u95e8"),
        ("\u8655", "\u5904"),
        ("\u9019", "\u8fd9"),
        ("\u500b", "\u4e2a"),
        ("\u8acb", "\u8bf7"),
        ("\u6e2c", "\u6d4b"),
        ("\u8a66", "\u8bd5"),
        ("\u8b58", "\u8bc6"),
        ("\u5225", "\u522b"),
        ("\u57f7", "\u6267"),
        ("\u70ba", "\u4e3a"),
        ("\u8207", "\u4e0e"),
        ("\u88e1", "\u91cc"),
        ("\u88cf", "\u91cc"),
        ("\u8a2d", "\u8bbe"),
        ("\u651d", "\u6444"),
    ),
    "replacements": (
        ("\u67e5\u770b\u5728\u7ebf\u8bbe\u5b9a", "\u67e5\u770b\u5728\u7ebf\u8bbe\u5907"),
        ("\u67e5\u8be2\u5728\u7ebf\u8bbe\u5b9a", "\u67e5\u8be2\u5728\u7ebf\u8bbe\u5907"),
        ("\u5728\u7ebf\u7684\u8bbe\u5b9a", "\u5728\u7ebf\u7684\u8bbe\u5907"),
        ("\u5728\u7ebf\u8bbe\u5b9a", "\u5728\u7ebf\u8bbe\u5907"),
        ("\u4e3b\u63e1", "\u4e3b\u5367"),
        ("\u4e3b\u6211", "\u4e3b\u5367"),
        ("\u6444\u706f", "\u5c04\u706f"),
        ("\u8bbe\u3001\u706f", "\u5c04\u706f"),
        ("\u8bbe\uff0c\u706f", "\u5c04\u706f"),
        ("\u8bbe,\u706f", "\u5c04\u706f"),
        ("\u8bbe \u706f", "\u5c04\u706f"),
        ("\u8bbe\u706f", "\u5c04\u706f"),
    ),
}
_VOICE_TEXT_COMPATIBILITY_TRANSLATION = str.maketrans(
    dict(_VOICE_TEXT_NORMALIZATION_COMPATIBILITY_PROJECTION["translation_pairs"])
)


def voice_text_normalization_compatibility_projection() -> dict[str, Any]:
    """Return the version-locked HA projection of the Gateway normalization contract."""
    projection = _VOICE_TEXT_NORMALIZATION_COMPATIBILITY_PROJECTION
    return {
        "contract_version": projection["contract_version"],
        "language": projection["language"],
        "translation_pairs": [
            list(pair)
            for pair in sorted(
                projection["translation_pairs"],
                key=lambda pair: ord(pair[0]),
            )
        ],
        "replacements": [list(pair) for pair in projection["replacements"]],
    }


def normalize_voice_stt_text(value: Any) -> str:
    """Return a Simplified-Chinese, domain-normalized voice transcript."""
    text = str(value or "").strip().translate(_VOICE_TEXT_COMPATIBILITY_TRANSLATION)
    for source, target in _VOICE_TEXT_NORMALIZATION_COMPATIBILITY_PROJECTION[
        "replacements"
    ]:
        text = text.replace(source, target)
    return text
