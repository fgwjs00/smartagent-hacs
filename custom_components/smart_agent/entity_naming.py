"""Entity naming helpers shared by SmartAgent HA-side endpoints."""
from __future__ import annotations

import re
from typing import Iterable

try:  # pragma: no cover - optional runtime dependency
    from pypinyin import lazy_pinyin as _lazy_pinyin
except Exception:  # pragma: no cover - Home Assistant may not bundle pypinyin
    _lazy_pinyin = None


_PINYIN_FALLBACK = {
    "主": "zhu",
    "卧": "wo",
    "客": "ke",
    "厅": "ting",
    "餐": "can",
    "厨": "chu",
    "房": "fang",
    "书": "shu",
    "卫": "wei",
    "生": "sheng",
    "间": "jian",
    "阳": "yang",
    "台": "tai",
    "玄": "xuan",
    "关": "guan",
    "开": "kai",
    "左": "zuo",
    "右": "you",
    "上": "shang",
    "下": "xia",
    "中": "zhong",
    "前": "qian",
    "后": "hou",
    "灯": "deng",
    "射": "she",
    "带": "dai",
    "具": "ju",
    "筒": "tong",
    "人": "ren",
    "体": "ti",
    "传": "chuan",
    "感": "gan",
    "器": "qi",
    "门": "men",
    "窗": "chuang",
    "帘": "lian",
    "空": "kong",
    "调": "tiao",
    "风": "feng",
    "扇": "shan",
}


def _fallback_pinyin_chars(text: str) -> Iterable[str]:
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            yield _PINYIN_FALLBACK.get(char, "")
        else:
            yield char


def _slugify_name(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", raw))
    if _lazy_pinyin is not None and has_chinese:
        tokens = _lazy_pinyin(raw, errors="ignore")
        raw = "_".join(token for token in tokens if token)
    elif has_chinese:
        raw = "_".join(token for token in _fallback_pinyin_chars(raw) if token)
    raw = raw.lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw


def name_to_entity_id(current_entity_id: str, name: str) -> str:
    """Build a HA entity_id from a display name while preserving the domain."""
    entity_id = str(current_entity_id or "").strip()
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    slug = _slugify_name(name)
    if not domain or not slug:
        return entity_id
    return f"{domain}.{slug}"
