# Changelog

## Beta 0.0.188 - 2026-07-30

Beta 0.0.188 合入此前保护分支中的家庭 Wi-Fi 设备维护控制面：Wi-Fi 凭据仅在 SA 本地加密保存并经 Zigbee 一次性下发，设备主动连接 SA 的短时 WebSocket 调试会话使用双向认证、会话密钥、重放防护和有界最新帧；OTA 下载地址按当前私网请求 Host 派生。AI 文字场景改用正式 DesiredStatePlanner 生成规范 HA 动作，未知目标和能力冲突失败关闭；Gateway 登录不再把 HA 上游 401 误判为 Gateway 会话失效，Supervisor Core 固定使用注入令牌。传感器固件、硬件和转换器仍保持独立项目边界。发行默认保持 shadow、真实执行开关默认 false，G13 默认 off/hard-off；真实家庭 Wi-Fi、连续调试、OTA 下载和物理设备动作仍需现场验收。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.188`，用于 Home Assistant 更新检测。
