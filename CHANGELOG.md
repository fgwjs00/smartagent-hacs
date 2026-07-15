# Changelog

## Beta 0.0.166 - 2026-07-15

Beta 0.0.166 add-on 启动修复：cryptography 进入正式 Python runtime rootfs，并在镜像构建阶段实际导入远程网关身份模块，阻断缺依赖镜像发布。G13 继续默认关闭且 hard-off 为 true；MCP 暂缓。HA-L、Frigate 配置应用和日志现场验收尚未完成，不得视为生产绿灯。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.166`，用于 Home Assistant 更新检测。
