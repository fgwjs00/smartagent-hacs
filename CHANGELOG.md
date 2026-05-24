# Changelog

## Beta 0.0.61 - 2026-05-25

Beta 0.0.61 测试版发布：8234 管理端新增“本地快脑自动决策”开关，local_fast_brain_enabled 由 /settings/system 持久化；关闭后 /decision/fast-path 在构造本地 FastPathDecisionPipeline 前返回 local_fast_brain_disabled，不再执行本地 fast-path 自动判断，同时保留 /infer 慢脑和大模型主链可用。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.61`，用于 Home Assistant 更新检测。
