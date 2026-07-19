# Changelog

## Beta 0.0.178 - 2026-07-19

Beta 0.0.178 修复真实 Stage A 暴露的 Home Assistant 线程安全缺陷：Presence 离开时态复查与动作层 delayed action 现在使用 HA callback 合同运行在事件循环，不再从 SyncWorker 直接创建异步 task。修复不改变 DesiredState、Planner、CommandEnvelope、设备策略或最终执行守卫。主动 AI 继续默认 shadow，canary 范围为空，两个真实执行开关默认 false；部署并确认运行版本后必须从首个有效 listener 周期重新累计 7 天且至少 300 次 Stage A 决策。继承 0.0.177 的 Presence clear 语义与跨平台发布哈希修复。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.178`，用于 Home Assistant 更新检测。
