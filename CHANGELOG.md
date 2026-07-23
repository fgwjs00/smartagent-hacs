# Changelog

## Beta 0.0.181 - 2026-07-24

Beta 0.0.181 是主卧无人关灯 C1 纠错候选：在 fast-path、普通即时关灯、延迟登记和延迟真实下发前刷新权威 Presence 投影；light/switch turn_off 同时校验 canonical Presence 与 Core 已授权的 HA 实时证据，刷新失败、证据过期、数值异常或 occupied/unknown 冲突均失败关闭；禁止把关灯改写为关联脚本，保留同一事务 lineage 和最终 action result。Linux amd64 native prebuilt 已重建并完成容器内行为重放。发行默认仍为 shadow、真实执行开关默认 false；发布安装后必须重新完成 B1 自然周期、post-state 和 72 小时门槛，不能把版本发布记为现场验收通过。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.181`，用于 Home Assistant 更新检测。
