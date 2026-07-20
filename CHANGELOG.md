# Changelog

## Beta 0.0.179 - 2026-07-20

Beta 0.0.179 修复真实 Stage A 暴露的 Presence 时态状态污染：共享 PresenceEngine 继续作为唯一权威状态机，但房间列表等读模型改用只读评估，不再以 guard 查询重置离开候选。真实状态事件仍推进 60 秒迟滞，DesiredState、Planner、CommandEnvelope、设备策略与最终执行守卫不变。主动 AI 继续默认 shadow，canary 范围为空，两个真实执行开关默认 false；部署后从首个完成 60 秒复查且 candidate_since 连续的有效周期重新累计 7 天和至少 300 次决策。继承 0.0.178 的 HA callback 线程安全修复。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.179`，用于 Home Assistant 更新检测。
