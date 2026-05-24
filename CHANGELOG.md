# Changelog

## Beta 0.0.60 - 2026-05-24

Beta 0.0.60 测试版发布：在 8234 管理端加入全局“AI 托管中 / 服务已暂停”开关，service_paused 由 /settings/system 持久化；暂停时 /infer 在调用大模型前返回 423 service_paused，并阻断主动分析和执行类 mutating 路由，同时保留 /favicon.ico 静态资源兼容修复。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.60`，用于 Home Assistant 更新检测。
