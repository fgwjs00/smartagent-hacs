# Changelog

## Beta 0.0.168 - 2026-07-15

Beta 0.0.168 设备管理热修：显示名称与房间通过预检后在 HA Registry 原子更新，不再隐式重命名 entity_id；温湿度和照度等数值传感器状态保留 HA device_class 与单位并在 V3 真实显示。G13 继续默认关闭且 hard-off 为 true；MCP 暂缓。真实 HA 房间编辑复验、HA-L、Frigate 配置应用和日志现场验收尚未完成，不得视为生产绿灯。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.168`，用于 Home Assistant 更新检测。
