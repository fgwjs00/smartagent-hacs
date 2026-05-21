# Changelog

## Beta 0.0.51 - 2026-05-21

Beta 0.0.51 热修中控屏设备与房间清单：中控屏受管设备改为从 Gateway REST /devices 读取，房间从 /rooms?include_local_only=true 读取，并携带 gateway_token 授权，修复连接成功后设备和房间为空的问题。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.51`，用于 Home Assistant 更新检测。
