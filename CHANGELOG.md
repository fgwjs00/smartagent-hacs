# Changelog

## Beta 0.0.182 - 2026-07-26

Beta 0.0.182 发布 Presence 到达照明学习选择与执行边界整改：毫米波可作为主要到达与离开证据，PIR off 不单独证明无人；到达候选统一覆盖显式纳管的照明 light/switch，取消无成熟学习证据时的批量开灯回退，冷启动改为业主子集选择或保持全关。确认后仍经 CommandEnvelope、preflight、HA action result 和逐实体可信学习链；SmartAgent 自身动作、外部自动化和 legacy_unverified 样本不得晋升。实体级 canary、no-op 真实性、switch 空参数、Presence 刷新和失败关闭继续保留。发行默认仍为 shadow、真实执行开关默认 false，Orvibo 保持停用；业主已授权正式发布，真实 HA 部署与现场验收仍为独立后续门禁。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.182`，用于 Home Assistant 更新检测。
