"""Tools for SmartAgent: Weather, Search, etc."""
from __future__ import annotations
import logging
import json
import aiohttp
from typing import Any
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class BaseTool:
    """Base class for all AI tools."""
    name: str
    description: str

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]):
        self.hass = hass
        self.config = config

    async def execute(self, query: str) -> str:
        """Execute the tool with a query string."""
        raise NotImplementedError()

class QWeatherTool(BaseTool):
    """Tool for fetching real-time weather from QWeather (HeFeng)."""
    name = "weather"
    description = "查询实时天气、温度、穿衣建议。参数: 城市名称或'local'表示本地。"

    async def execute(self, query: str) -> str:
        api_key = self.config.get("qweather_api_key")
        if not api_key:
            return "错误: 未配置和风天气 API Key。"

        # 如果是 local，尝试从 HA 获取地理位置
        location = query
        if "local" in query.lower() or not query:
            lat = self.hass.config.latitude
            lon = self.hass.config.longitude
            location = f"{lon:.2f},{lat:.2f}"
        
        url = f"https://devapi.qweather.com/v7/weather/now?location={location}&key={api_key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        _LOGGER.error("[Tools] QWeather HTTP %d: %s", resp.status, url)
                        return f"错误: 无法获取天气 (HTTP {resp.status})"
                    data = await resp.json()
                    if data.get("code") != "200":
                        _LOGGER.warning("[Tools] QWeather API 返回错误码 %s: %s", data.get("code"), url)
                        return f"错误: 和风天气返回 {data.get('code')}"
                    
                    now = data.get("now", {})
                    temp = now.get("temp")
                    feels_like = now.get("feelsLike")
                    text = now.get("text")
                    wind_dir = now.get("windDir")
                    humidity = now.get("humidity")
                    
                    # 获取穿衣建议（生活指数）
                    indices_url = f"https://devapi.qweather.com/v7/indices/1d?type=3&location={location}&key={api_key}"
                    async with session.get(indices_url, timeout=10) as idx_resp:
                        idx_text = ""
                        if idx_resp.status == 200:
                            idx_data = await idx_resp.json()
                            if idx_data.get("code") == "200":
                                idx = idx_data.get("daily", [{}])[0]
                                idx_text = f" 穿衣建议: {idx.get('text', '')}"

                    return (f"当前天气: {text}，温度: {temp}℃，体感: {feels_like}℃，"
                            f"风向: {wind_dir}，湿度: {humidity}%。{idx_text}")
        except Exception as e:
            _LOGGER.exception("[Tools] QWeather 查询异常")
            return f"错误: 天气查询异常 ({str(e)})"

class SearXNGSearchTool(BaseTool):
    """Tool for general web search using SearXNG."""
    name = "search"
    description = "互联网搜索通用知识、新闻、电影等。参数: 搜索关键词。"

    async def execute(self, query: str) -> str:
        base_url = self.config.get("searxng_url")
        if not base_url:
            return "错误: 未配置 SearXNG URL。"

        # 确保以 /search 结尾
        if not base_url.endswith("/search"):
            base_url = base_url.rstrip("/") + "/search"

        payload = {
            "q": query,
            "format": "json",
            "engines": "google,bing,duckduckgo",
            "pageno": 1,
            "language": "zh-CN"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=payload, timeout=15) as resp:
                    if resp.status != 200:
                        _LOGGER.error("[Tools] SearXNG HTTP %d: %s", resp.status, base_url)
                        return f"错误: 搜索失败 (HTTP {resp.status})"
                    data = await resp.json()
                    results = data.get("results", [])[:3] # 取前3条
                    if not results:
                        _LOGGER.info("[Tools] SearXNG 搜索无结果: %s", query)
                        return "搜索完成，但没有找到相关结果。"
                    
                    summaries = []
                    for i, r in enumerate(results):
                        summaries.append(f"[{i+1}] {r.get('title')}: {r.get('content')}")
                    
                    return "\n".join(summaries)
        except Exception as e:
            _LOGGER.exception("[Tools] SearXNG 搜索异常")
            return f"错误: 搜索异常 ({str(e)})"

class ToolRegistry:
    """Registry to manage and call tools."""
    def __init__(self, hass: HomeAssistant, config: dict[str, Any]):
        self.tools: dict[str, BaseTool] = {
            "weather": QWeatherTool(hass, config),
            "search": SearXNGSearchTool(hass, config)
        }

    def get_tool_definitions(self) -> str:
        """Get definitions for prompt injection."""
        defs = []
        for name, tool in self.tools.items():
            defs.append(f"- {name}: {tool.description}")
        return "\n".join(defs)

    async def call_tool(self, name: str, query: str) -> str:
        """Call a tool by name."""
        if name not in self.tools:
            return f"错误: 未知工具 {name}"
        return await self.tools[name].execute(query)
