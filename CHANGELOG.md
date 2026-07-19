# Changelog

## Beta 0.0.177 - 2026-07-19

Beta 0.0.177 修复真实 Stage A 暴露的 Presence clear 语义边界：非语义 entity id 通过 canonical capability 与 Presence evidence 识别；在 leave_qualified=false 时拒绝模型错误生成的离开关电源 DesiredState，真实合格离开保持原规划。API split/prebuilt 聚合哈希与 hash-based pyc 改用 LF canonical source bytes，消除 Windows/Linux checkout 换行漂移。主动 AI 继续默认 shadow，canary 范围为空，两个真实执行开关默认 false；部署后必须重新起算 7 天且至少 300 次 Stage A 决策。继承 0.0.176 的 V3 本地 OTA 上传授权链修复。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.177`，用于 Home Assistant 更新检测。
