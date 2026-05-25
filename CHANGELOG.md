# Changelog

## Beta 0.0.64 - 2026-05-25

Beta 0.0.64 测试版发布：修复设备纳管本地 fallback 与 AI 场景可信灯光目录不同步的问题；product route 缺失时，/devices/batch-add 会从 HA /api/states 补齐用户明确纳管实体的名称、空间和状态后写入 add-on 本地投影，同时保持普通设备列表只展示不自动入库。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.64`，用于 Home Assistant 更新检测。
