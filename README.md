# SmartAgent for Home Assistant

Current release: `Beta 0.0.2`

## 中文说明

SmartAgent 是一套基于 HA OS / Home Assistant 生态构建的 AI 全屋智能管控系统。

它不是要替代 Home Assistant，而是在 Home Assistant 的设备接入、实体状态、自动化、脚本、场景和 add-on 生态之上，提供 SmartAgent 自己的产品层能力：

- SmartAgent Gateway 统一入口
- Local Core 本地核心能力
- 面向安装人员、售后、管理员和开发者的管理控制台
- 面向家庭日常使用的中控屏
- AI 双脑决策、记忆学习、场景发现与安全执行链
- 未来可选的远程访问、云端专家增强和订阅能力

本仓库提供 SmartAgent 的 Home Assistant 集成部分，用于通过 HACS 安装。它负责把 Home Assistant 的设备生态接入 SmartAgent 产品运行时，并提供 SmartAgent 在 HA 侧需要的集成入口。

### SmartAgent 的目标

SmartAgent 的目标是让智能家居从“被动响应”升级为“主动服务”：

- 理解家庭设备、房间、场景和用户习惯
- 根据传感器、视觉、语音和历史行为做本地实时决策
- 通过安全校验、事务记录和回滚机制降低误操作风险
- 让普通家庭用户通过中控屏进行日常控制
- 让安装人员和售后通过管理控制台完成配置、诊断和维护

### 安装方式

1. 打开 Home Assistant 中的 HACS。
2. 添加本仓库为自定义仓库。
3. 类型选择 `Integration`。
4. 安装 `AI SmartAgent`。
5. 重启 Home Assistant。
6. 在 Home Assistant 的集成页面添加 SmartAgent。

### 使用要求

- 已部署兼容的 Home Assistant 环境。
- 已部署 SmartAgent Core 服务。
- Home Assistant 与 SmartAgent Core 服务之间网络可达。

### 日常使用入口

- 普通家庭用户：使用中控屏进行房间、设备、场景和语音控制。
- 安装人员、售后、管理员、开发者：使用 SmartAgent 管理控制台进行安装配置、诊断、日志、授权、备份和维护。
- Home Assistant 后台：保留为底层设备生态、运维和高级调试入口。

### 更新

SmartAgent Home Assistant 集成通过 HACS 更新。当前公开版本为 `Beta 0.0.2`。

## English

SmartAgent is an AI whole-home intelligence system built on top of the HA OS / Home Assistant ecosystem.

It does not replace Home Assistant. Instead, it uses Home Assistant for device integration, entity state, automations, scripts, scenes, and the add-on ecosystem, then adds SmartAgent's own product layer:

- SmartAgent Gateway as the unified product entry
- Local Core for local intelligence
- management console for installers, support teams, administrators, and developers
- central control screen for everyday household use
- dual-brain AI decision making, memory learning, scene discovery, and safety execution chain
- future optional remote access, cloud expert enhancement, and subscription capabilities

This repository provides the Home Assistant integration part of SmartAgent for HACS installation. It connects the Home Assistant device ecosystem to the SmartAgent product runtime and provides the integration entry points needed on the Home Assistant side.

### Product Goal

SmartAgent aims to move the smart home experience from passive response to proactive service:

- understand home devices, rooms, scenes, and user habits
- make local real-time decisions from sensors, vision, voice, and historical behavior
- reduce unsafe actions through safety checks, transaction logs, and rollback support
- let household users control daily scenes through the central control screen
- let installers and support teams configure, diagnose, and maintain projects through the management console

### Installation

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository.
3. Select `Integration`.
4. Install `AI SmartAgent`.
5. Restart Home Assistant.
6. Add SmartAgent from the Home Assistant integrations page.

### Requirements

- A compatible Home Assistant environment.
- SmartAgent Core service deployed for the project.
- Network access between Home Assistant and SmartAgent Core.

### Main Entry Points

- Household users: central control screen for rooms, devices, scenes, and voice control.
- Installers, support teams, administrators, and developers: SmartAgent management console for setup, diagnostics, logs, license, backup, and maintenance.
- Home Assistant backend: retained for device ecosystem, operations, and advanced troubleshooting.

### Updates

The SmartAgent Home Assistant integration is updated through HACS. The current public release is `Beta 0.0.2`.
