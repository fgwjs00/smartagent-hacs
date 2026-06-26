# Changelog

## Beta 0.0.133 - 2026-06-27

Beta 0.0.133 测试版发布：修复 HA 监听器刷新后已处于触发态的人体传感器不会补发 fast-path 的问题；监听器重建时会对已纳管且当前为 on 的 presence binary_sensor 做一次状态补偿，写入可见诊断事件并提交快路径，避免 HA 已触发但 SmartAgent 没有后续实施流程。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.133`，用于 Home Assistant 更新检测。
