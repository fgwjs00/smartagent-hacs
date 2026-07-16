# Changelog

## Beta 0.0.170 - 2026-07-16

Beta 0.0.170 修复 V3 设备页无法显示灯具和开关控制的问题：Gateway `/devices` 现在从服务器标准服务注册表回流 `supported_services`，产品设备清单与 HA `/api/states` 权威回退路径使用同一能力真值，前端不按实体域猜测操作；原有批量控制、状态确认和逐项回执链保持不变。G13 继续默认关闭且 hard-off 为 true；MCP 暂缓。真实 HA 开关结果、Presence、HA-L、Frigate 和日志现场验收仍需部署后复验，不得视为生产绿灯。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.170`，用于 Home Assistant 更新检测。
