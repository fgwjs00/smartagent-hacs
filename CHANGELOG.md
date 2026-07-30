# Changelog

## Beta 0.0.189 - 2026-07-30

Beta 0.0.189 修复 add-on 家庭助理服务地址含首尾空白时未命中 Supervisor Core 专用认证分支的问题。启动脚本现在先规范化 URL，再固定使用 Supervisor 注入令牌，避免误用旧手填 HA Token 导致 /rooms、listener 和语音上游持续 401。0.0.188 的家庭 Wi-Fi 维护、AI 场景和认证边界能力保持不变；传感器固件、硬件和转换器仍属于独立项目。发行继续保留现有 canary，G13 默认 off/hard-off，不触发家庭设备。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.189`，用于 Home Assistant 更新检测。
