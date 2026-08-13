# Changelog

## Beta 0.0.212 - 2026-08-14

Beta 0.0.212 修复显式语音控制被自主 AI 灰度误拦截与错误成功播报，并修复 AI 场景手动触发因世界快照缺失返回 503；归一化中控屏 Workbox 产物、保留 AI 场景真实接口来源说明，并关闭当前阿里云 ACR 不支持的 OCI provenance/SBOM 附加清单；用户明确语音只绕过自主 AI 灰度，仍保留纳管、精确实体、服务白名单、世界状态与执行回执门禁，自主传感器控制继续仅限精确 canary。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.212`，用于 Home Assistant 更新检测。
