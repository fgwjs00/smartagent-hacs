# Changelog

## Beta 0.0.139 - 2026-07-01

Beta 0.0.139 快路执行结果回写修复：HA listener 在 fast-path 自动执行后回写 decision_execution/action_results，使真实主卧到达事务可在 /decision-trace/{transaction_id} 回放逐动作执行结果；推送 v0.0.139 tag 后由 GitHub Actions 构建并推送 ACR 0.0.139 与 beta 镜像，现场需同步更新 HACS integration。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.139`，用于 Home Assistant 更新检测。
