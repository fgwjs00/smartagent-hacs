# SmartAgent for Home Assistant

当前公开版本：`Beta 0.0.133`

## 中文说明

SmartAgent 是一套基于 HA OS / Home Assistant 生态构建的 AI 全屋智能管控系统。它利用 Home Assistant 的设备接入、实体状态、自动化、脚本、场景和 add-on 生态，同时提供 SmartAgent 自己的 Gateway、Local Core、管理控制台、中控屏、AI 决策、记忆学习和安全执行能力。

本仓库提供 SmartAgent 的 Home Assistant 集成部分，用于通过 HACS 或手动复制安装。它负责把 Home Assistant 的设备生态接入 SmartAgent 产品运行时，并提供 SmartAgent 在 HA 侧需要的集成入口。

### HACS 仓库地址

HACS 只能使用 GitHub 公共仓库作为自定义仓库地址。请在 HACS 中添加 `https://github.com/fgwjs00/smartagent-hacs`，类型选择 `Integration`。

Gitee 仓库仅作为镜像和手动下载来源，不能作为 HACS 自定义仓库地址。

### 更新

SmartAgent Home Assistant 集成通过 HACS 更新。当前公开版本为 `Beta 0.0.133`。
