# Changelog

## Beta 0.0.52 - 2026-05-21

Beta 0.0.52 热修中控屏语音会话创建：Gateway POST /api/v1/voice/session 改为本地签发 session_id 与临时 WS ticket，不再向仅支持 WebSocket GET 的 HA adapter 发起 POST，修复语音按钮返回 405 Method Not Allowed 的问题。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.52`，用于 Home Assistant 更新检测。
