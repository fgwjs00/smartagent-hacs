"""Conservative Simplified-Chinese normalization for SmartAgent voice input."""
from __future__ import annotations

from typing import Any

_ZH_CN_TRANSLATION = str.maketrans(
    {
        "開": "开",
        "關": "关",
        "閉": "闭",
        "啟": "启",
        "廳": "厅",
        "臥": "卧",
        "燈": "灯",
        "帶": "带",
        "簾": "帘",
        "廚": "厨",
        "衛": "卫",
        "間": "间",
        "調": "调",
        "聲": "声",
        "網": "网",
        "線": "线",
        "風": "风",
        "氣": "气",
        "溫": "温",
        "濕": "湿",
        "鎖": "锁",
        "門": "门",
        "處": "处",
        "這": "这",
        "個": "个",
        "請": "请",
        "測": "测",
        "試": "试",
        "識": "识",
        "別": "别",
        "執": "执",
        "為": "为",
        "與": "与",
        "裡": "里",
        "裏": "里",
        "設": "设",
        "攝": "摄",
    }
)
_SMART_HOME_FIXES = (
    ("\u67e5\u770b\u5728\u7ebf\u8bbe\u5b9a", "\u67e5\u770b\u5728\u7ebf\u8bbe\u5907"),
    ("\u67e5\u8be2\u5728\u7ebf\u8bbe\u5b9a", "\u67e5\u8be2\u5728\u7ebf\u8bbe\u5907"),
    ("\u5728\u7ebf\u7684\u8bbe\u5b9a", "\u5728\u7ebf\u7684\u8bbe\u5907"),
    ("\u5728\u7ebf\u8bbe\u5b9a", "\u5728\u7ebf\u8bbe\u5907"),
    ("主握", "主卧"),
    ("主我", "主卧"),
    ("摄灯", "射灯"),
    ("设、灯", "射灯"),
    ("设，灯", "射灯"),
    ("设,灯", "射灯"),
    ("设 灯", "射灯"),
    ("设灯", "射灯"),
)


def normalize_voice_stt_text(value: Any) -> str:
    """Return a Simplified-Chinese, domain-normalized voice transcript."""
    text = str(value or "").strip().translate(_ZH_CN_TRANSLATION)
    for source, target in _SMART_HOME_FIXES:
        text = text.replace(source, target)
    return text
