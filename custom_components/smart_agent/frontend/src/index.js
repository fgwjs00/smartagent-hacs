/**
 * SmartAgent Panel — 模块化入口
 *
 * 构建方式: node build.mjs
 * 输出:     smart-agent-panel.js（esbuild IIFE 格式）
 *
 * 每个 *Methods 对象通过 Object.assign 混入 SmartAgentPanel.prototype，
 * 保持与单文件版本完全相同的 this 绑定行为。
 */

import { getIcons } from "./icons.js";
import "./mwc.js";  // Material Web 组件按需导入

// ── 渲染层：主模板 ──
import { renderMethods } from "./render/main.js";

// ── 渲染层：各 tab 独立模块 ──
import { syslogMethods }       from "./render/syslog.js";
import { habitsMethods }       from "./render/habits.js";
import { aiscenesMethods }     from "./render/aiscenes.js";
import { correctionsMethods }  from "./render/corrections.js";
import { transactionsMethods } from "./render/transactions.js";
import { energyMethods }       from "./render/energy.js";
import { profilesMethods }     from "./render/profiles.js";
import { configMethods }       from "./render/config.js";
import { devicesMethods }      from "./render/devices.js";
import { roomsMethods }        from "./render/rooms.js";
import { backupMethods }       from "./render/backup.js";
import { patrolMethods }       from "./render/patrol.js";
import { mcpMethods }          from "./render/mcp.js";
import { licenseMethods }      from "./render/license.js";

// ── 状态同步层 ──
import { updateMethods } from "./update.js";

// ── 工具层 ──
import { helperMethods } from "./utils/helpers.js";

// ── 核心层（全局开关切换、标签页切换、分页、批量操作等）──
import { coreMethods } from "./panel-core.js";

/**
 * SmartAgent 主面板类。
 * 所有业务方法均通过 Object.assign 从独立模块混入，保持单一 class 签名。
 *
 * ── 模块化状态（全部已迁移）──
 * render/main.js     — _render() 主模板
 * update.js          — _update() 状态同步
 * render/config.js   — _renderConfig() + _initZoneRoleUI() + _saveSystemConfig()
 * render/devices.js  — _renderDevs()
 * render/syslog.js   — 系统日志
 * render/habits.js   — 行为习惯
 * render/aiscenes.js — AI 场景
 * render/corrections.js — 纠错学习
 * render/transactions.js — 执行记录
 * render/energy.js   — 能耗分析
 * render/profiles.js — 个性化画像
 * panel-core.js      — 公共核心（标签切换、分页、批量操作、品牌）
 * utils/helpers.js   — 工具函数
 * styles.js          — CSS
 * icons.js           — SVG 图标
 * constants.js       — 全局常量
 */
class SmartAgentPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "dashboard";
    this._selectedNew = new Set();
    this._selectedCfg = new Set();
    this._init = false;
    this._editingSceneKey = null;
    this._sysLogMode = "live";
    this._sysLogFilter = "all";
    this._sysLogKeyword = "";
    this._habSearch = "";
    this._habDomainFilter = "all";
    this._habSort = "conf";
    this._habGrouped = true;
    this._wsData = {};
    this._wsLoading = {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._init) {
      this._render();
      this._init = true;
      // 5A-3: 订阅决策气泡事件（仅首次初始化时注册一次）
      this._initDecisionBubble();
      // 5B-2: 订阅 need_confirm 确认气泡事件
      this._initConfirmBubble();
    }
    this._update();
  }

  /* ── Getters ── */
  _get(match) { return Object.values(this._hass?.states || {}).find(match) || {}; }
  get _cfg() { return this._hass?.states["sensor.smart_agent_config"] || this._get(s => s.attributes?.device_count !== undefined); }
  get _sts() { return this._hass?.states["sensor.smart_agent_status"] || this._get(s => s.attributes?.full_text !== undefined); }
  get _sw()  { return this._hass?.states["switch.smart_agent_paused"] || {}; }
  get _eng() { return this._hass?.states["select.smart_agent_engine"] || {}; }
  get _numA(){ return this._hass?.states["number.smart_agent_confidence_auto"] || {}; }
  get _numN(){ return this._hass?.states["number.smart_agent_confidence_notify"] || {}; }

  /** 图标访问器（各模块通过 this._getIcons() 调用） */
  _getIcons() { return getIcons(); }
}

// ── 混入所有模块方法到 prototype ──
Object.assign(
  SmartAgentPanel.prototype,
  // 工具层（最先混入，其他模块方法可能依赖）
  helperMethods,
  // 核心层
  coreMethods,
  // 状态同步
  updateMethods,
  // 主模板
  renderMethods,
  // 渲染层（各 tab）
  configMethods,
  devicesMethods,
  syslogMethods,
  habitsMethods,
  aiscenesMethods,
  correctionsMethods,
  transactionsMethods,
  energyMethods,
  profilesMethods,
  roomsMethods,
  backupMethods,
  patrolMethods,
  mcpMethods,
  licenseMethods,
);

customElements.define("smart-agent-panel", SmartAgentPanel);
