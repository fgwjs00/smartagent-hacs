# Changelog

## Beta 0.0.185 - 2026-07-30

Beta 0.0.185 统一 V3 面向业主的中文展示和执行事实：空间、状态、来源、服务、日志与场景名称通过稳定投影显示中文，未知内部值失败关闭；事务页严格区分候选动作与真实 action_results，不再把计划动作包装成已执行；待确认决策记录主体打开独立确认窗口并保留明确提交回执，右侧追溯按钮只打开只读证据链。固定照明场景以空间注册表生成中文名称但保持 canonical space_id，图文手册同步为 42 页面、164 功能、302 截图。源码、预构建、前端产物和自动回归完成后进入五发布面、ACR 与真实 HA 部署。发行默认仍为 shadow、真实执行开关默认 false；部署必须保留现场 zhu_wo + light/switch + 精确两实体 canary，Orvibo HomeBridge 继续停用。

- 发布最新 SmartAgent Home Assistant 集成。
- 同步公开版本 `0.0.185`，用于 Home Assistant 更新检测。
