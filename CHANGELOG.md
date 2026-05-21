# Changelog

## Beta 0.0.50 - 2026-05-21

Beta 0.0.50 热修 8234 中控屏 WebSocket 认证时序：/api/websocket 先完成浏览器 WebSocket 握手并按 HA 协议接收 gateway_token，再由 add-on 使用 HA token 认证上游 Home Assistant，修复 0.0.49 路由存在但被 invalid_internal_token 预握手拦截的问题。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.50`，用于 Home Assistant 更新检测。
