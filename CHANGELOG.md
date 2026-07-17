# Changelog

## Beta 0.0.173 - 2026-07-18

Beta 0.0.173 完成 V3 运行事实卡片、本地快脑总开关和 8MB 双协议本地 OTA 候选：Dashboard 正确区分候选、执行与复核回执，并回流巡检日报、当日决策和日志归档库存；关闭本地快脑后合格触发转交慢脑，安全过滤继续生效；OTA 只接受浏览器上传的 Ed25519 签名 `.safw` 单包，通过私网 HTTP 向设备一次性授权下载，8MB 设备升级失败进入恢复模式，Matter 固件保持预留且默认不可执行。G13 继续默认关闭且 hard-off 为 true；MCP 暂缓。真实设备 OTA、远程调试、HA-L、Frigate 和日志现场验收仍需部署后复验，不得视为生产绿灯。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.173`，用于 Home Assistant 更新检测。
