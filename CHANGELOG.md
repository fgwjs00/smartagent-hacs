# Changelog

## Beta 0.0.171 - 2026-07-16

Beta 0.0.171 重新打包并发布设备控制能力回流：Gateway `/devices` 从服务器标准服务注册表为灯具和开关补全 `supported_services`，V3 仅据此显示开关按钮并继续使用 canonical 批量控制、状态确认和逐项回执链。同时修复空间页将零设备房间误判为拓扑缺失的问题，并将 `adjacent`、`connected`、`blocked` 统一显示为“相邻 / 连通 / 隔断”。G13 继续默认关闭且 hard-off 为 true；MCP 暂缓。真实 HA 开关结果、Presence、HA-L、Frigate 和日志现场验收仍需部署后复验，不得视为生产绿灯。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.171`，用于 Home Assistant 更新检测。
