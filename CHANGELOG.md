# Changelog

## Beta 0.0.199 - 2026-08-03

Beta 0.0.199 修复远程维护 HA 压缩响应在流式代理中因 Content-Length 与解压后正文不一致而中断的问题；保持 HA 原始压缩字节与响应头一致，并继续沿用 0.0.198 已发布能力。发布继续使用正式五发布面与阿里云 ACR；G13 保持 off/hard-off，Orvibo HomeBridge 与 MCP 继续停用。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.199`，用于 Home Assistant 更新检测。
