# Changelog

## Beta 0.0.184 - 2026-07-29

Beta 0.0.184 汇总发布主线收口修复：管理首页近期决策流改为有界分页加载并补齐中文原因回退，避免无限增长和大量“后端未提供中文说明”；OTA 下载增加 manifest 身份绑定、设备认领窗口、传输时限、有限重试和过期事务释放；设备维护回流固件信任模式，LD2410 页面接入真实工程视图并保护不完整配置。源码、Linux amd64 预构建、前端产物和自动回归已通过，业主已授权进入五发布面、ACR 与真实 HA 部署。发行默认仍为 shadow、真实执行开关默认 false；部署必须保留现场 zhu_wo + light/switch + 精确两实体 canary，Orvibo HomeBridge 继续停用。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.184`，用于 Home Assistant 更新检测。
