# Changelog

## Beta 0.0.176 - 2026-07-19

Beta 0.0.176 修复 V3 本地 OTA 上传授权链：有效本地管理员 token 会携带明确的 local_gateway 执行身份，Add-on 在 token 门禁通过后允许 BIN 入库、计划与执行；403 权限拒绝只在当前固件弹窗显示，不再清除有效会话或跳转登录，真正的 401 仍全局注销。继承 0.0.175 的主动 AI 完整性整改与 shadow 默认门禁，以及 0.0.174 的设备绑定 ESP-IDF BIN 本地 OTA 和 `.safw + Ed25519` 严格路径。真实设备 OTA 结果仍需现场验收。

- 发布最新 SmartAgent Home Assistant 集成 包。
- 同步公开版本 `0.0.176`，用于 Home Assistant 更新检测。
