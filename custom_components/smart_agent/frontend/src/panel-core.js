/**
 * SmartAgent Panel — 核心方法 mixin
 *
 * 包含公共核心方法，供各渲染模块调用：
 *   - _toggle()               暂停/恢复开关
 *   - _openSceneEdit()        展厅场景编辑
 *   - _setTab()               标签页切换
 *   - _startTerminalLogPoll() 决策流水轮询
 *   - _renderLicenseStatus()  License 状态渲染
 *   - _renderPager()          分页控件
 *   - _updateBatchFab()       批量操作悬浮条
 *   - _batchUpdateRoom/Mode/Delete/Add()  批量操作
 *   - _selAll()               全选/全取消
 *   - _updateBizStatus()      营业时间状态
 *   - _applyBrand()           品牌主题应用
 */

import { TARGET_DOMAINS, SKIP_KW, SKIP_NAME_KW } from "./constants.js";

export const coreMethods = {
  _toggle() {
    const s = this._sw;
    if (!s.entity_id) return;
    this._callService(
      "switch",
      s.state === "on" ? "turn_off" : "turn_on",
      { entity_id: s.entity_id }
    );
  },

  _openSceneEdit(key) {
    const c = this._cfg?.attributes || {};
    const scenes = Array.isArray(c.showroom_scenes) ? c.showroom_scenes : [];
    const scene = scenes.find(s => s.key === key);
    if (!scene) return;
    this._editingSceneKey = key;
    const $ = id => this.shadowRoot.getElementById(id);
    $("editSceneTitle").textContent = `编辑场景: ${scene.label}`;
    $("editSceneLabel").value = scene.label;
    $("editSceneTime").value = scene.virtual_time;
    $("editSceneDesc").value = scene.scene_desc;
    $("editSceneHint").value = scene.hint;
    $("showroomEditPanel").style.display = "block";
    $("editSceneLabel").focus();
  },

  // 主 Tab 分组映射
  _GROUP_TABS: {
    space:  ["devices", "rooms", "vision"],
    ai:     ["profiles", "habits", "aiscenes", "corrections"],
    data:   ["transactions", "energy"],
    system: ["config", "patrol", "backup", "mcp", "license"],
  },

  _setTab(t) {
    if (this._tab === t) return;
    this._tab = t;

    // 找出 t 属于哪个分组
    const groupMap = this._GROUP_TABS;
    let activeGroup = "";
    for (const [g, tabs] of Object.entries(groupMap)) {
      if (tabs.includes(t)) { activeGroup = g; break; }
    }

    // 更新主 Tab 激活状态
    this.shadowRoot.querySelectorAll(".nav-tab").forEach(b => {
      if (b.dataset.t) {
        // 直接 Tab（dashboard / syslog）
        b.classList.toggle("active", b.dataset.t === t);
      } else if (b.dataset.group) {
        // 分组 Tab：当前 t 属于该组时激活
        b.classList.toggle("active", b.dataset.group === activeGroup);
      }
    });

    // 显示/隐藏子 Tab 栏
    ["space", "ai", "data", "system"].forEach(g => {
      const el = this.shadowRoot.getElementById("sub-" + g);
      if (el) el.style.display = g === activeGroup ? "flex" : "none";
    });

    // 更新子 Tab 激活状态
    if (activeGroup) {
      const subBar = this.shadowRoot.getElementById("sub-" + activeGroup);
      if (subBar) {
        subBar.querySelectorAll(".nav-sub-tab").forEach(b =>
          b.classList.toggle("active", b.dataset.t === t)
        );
        // 记住该组上次访问的子页面
        this._lastSubTab = this._lastSubTab || {};
        this._lastSubTab[activeGroup] = t;
      }
    }

    // 显示/隐藏内容区
    this.shadowRoot.querySelectorAll(".tab-view").forEach(v =>
      v.classList.toggle("active", v.id === "view-" + t)
    );

    // 按需加载数据
    if (t === "syslog")      { this._loadLogDates(); this._wsRefreshSysLog(); }
    if (t === "config")      this._renderConfig();
    if (t === "devices")     this._wsRefresh("smart_agent/get_devices",          "devices",           () => this._renderDevs());
    if (t === "profiles")    this._wsRefresh("smart_agent/get_rules",             "rules",             () => this._renderProfs());
    if (t === "habits")      this._wsRefresh("smart_agent/get_behavior_patterns", "behavior_patterns", () => this._renderHabitPatterns());
    if (t === "aiscenes")    this._wsRefresh("smart_agent/get_ai_scenes",         "ai_scenes",         () => this._renderAiScenes());
    if (t === "corrections") this._wsRefresh("smart_agent/get_ai_actions",        "ai_actions",        () => this._renderCorrections());
    if (t === "transactions")this._wsRefresh("smart_agent/get_transactions",      "transactions",      () => this._renderTransactions());
    if (t === "energy")      this._wsRefresh("smart_agent/get_energy_stats",      "energy_stats",      () => this._renderEnergy());
    if (t === "rooms")       { this._loadRoomTopology?.().then(() => this._renderRooms?.()); }
    if (t === "patrol")      this._renderPatrol?.();
    if (t === "backup")      this._renderBackup?.();
    if (t === "mcp")         this._renderMcp?.();
    if (t === "license")     this._renderLicensePage?.();

    this._startTerminalLogPoll(t === "dashboard");
    this._update();
  },

  // 点击分组主 Tab 时，跳转到该组上次访问的子页面（或默认第一个）
  _setGroup(group) {
    const groupMap = this._GROUP_TABS;
    const tabs = groupMap[group] || [];
    const last = (this._lastSubTab || {})[group];
    const target = (last && tabs.includes(last)) ? last : tabs[0];
    if (target) this._setTab(target);
  },

  _startTerminalLogPoll(active) {
    if (this._terminalPollTimer) {
      clearInterval(this._terminalPollTimer);
      this._terminalPollTimer = null;
    }
    if (!active) return;
    let _polling = false;
    const poll = async () => {
      if (_polling) return;
      _polling = true;
      try {
        const result = await this._hass.callWS({ type: "smart_agent/get_terminal_log" });
        const html = result?.html || "";
        const box = this.shadowRoot.getElementById("lBox");
        if (box && box.innerHTML !== html) {
          box.innerHTML = html || "等待系统指令...";
        }
      } catch (_) { /* 静默失败 */ }
      finally { _polling = false; }
    };
    poll();
    this._terminalPollTimer = setInterval(poll, 3000);
  },

  _renderLicenseStatus(lic) {
    const area = this.shadowRoot?.getElementById("licenseStatusArea");
    if (!area) return;
    if (!lic) { area.innerHTML = '<span style="opacity:.5">暂无数据</span>'; return; }
    const tierColors = { free: "var(--sa-outline)", basic: "var(--sa-secondary)", pro: "var(--sa-succ)", business: "var(--sa-state-warning)" };
    const color = tierColors[lic.tier] || "var(--sa-outline)";
    const validBadge = lic.valid
      ? `<span style="color:var(--sa-succ);font-weight:600">✅ 已激活</span>`
      : lic.has_key
        ? `<span style="color:var(--sa-err);font-weight:600">❌ 验证失败</span>`
        : `<span style="color:var(--sa-outline)">⚪ 未激活（免费版）</span>`;
    const limitStr = lic.daily_limit === -1 ? "无限制" : `${lic.daily_limit} 次/天`;
    const usedStr =
      lic.daily_limit === -1
        ? `今日已用 ${lic.daily_used} 次`
        : `今日已用 ${lic.daily_used} / ${lic.daily_limit} 次`;
    const progressPct =
      lic.daily_limit === -1
        ? 0
        : Math.min(100, Math.round((lic.daily_used / lic.daily_limit) * 100));
    const progressColor =
      progressPct >= 90 ? "var(--sa-err)" : progressPct >= 70 ? "var(--sa-state-warning)" : "var(--sa-succ)";
    area.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
        <span style="font-size:18px;font-weight:700;color:${color}">${this._esc(lic.tier_label)}</span>
        ${validBadge}
        ${lic.expires ? `<span style="opacity:.6;font-size:12px">到期：${this._esc(String(lic.expires))}</span>` : ""}
      </div>
      <div style="margin-bottom:6px;color:var(--md-sys-color-on-surface-variant)">${usedStr}（${limitStr}）</div>
      ${lic.daily_limit !== -1 ? `
        <div style="height:6px;background:var(--md-sys-color-surface-container-highest);border-radius:3px;overflow:hidden;margin-bottom:8px">
          <div style="height:100%;width:${progressPct}%;background:${progressColor};border-radius:3px;transition:width .3s"></div>
        </div>` : ""}
      ${!lic.valid && lic.has_key ? `
        <div style="padding:8px 10px;background:var(--sa-err-container);border-radius:var(--sa-shape-sm);font-size:12px;color:var(--sa-err);margin-top:4px">
          ⚠️ License Key 验证失败，系统已降级到免费版限制。请检查 Key 是否正确，或联系开发者。
        </div>` : ""}
      ${!lic.has_key ? `
        <div style="padding:8px 10px;background:var(--md-sys-color-surface-container);border-radius:8px;font-size:12px;color:var(--md-sys-color-outline);margin-top:4px">
          💡 填写 License Key 步骤：<br>
          &nbsp;&nbsp;① 进入 <b>HA 设置 → 设备与服务</b><br>
          &nbsp;&nbsp;② 找到 <b>AI SmartAgent</b> → 点击 <b>⋮ 三点菜单 → 选项</b><br>
          &nbsp;&nbsp;③ 滚动到底部，找到 <b>License Key</b> 字段填入<br>
          &nbsp;&nbsp;④ 点击提交保存，返回此页面点击「重新验证」
        </div>` : ""}
    `;
  },

  _renderPager(container, curPage, totalPages, onPage) {
    if (!container) return;
    if (totalPages <= 1) { container.innerHTML = ""; return; }
    const start = Math.max(0, curPage - 2);
    const end = Math.min(totalPages - 1, curPage + 2);
    let h = `<button class="pager-btn" ${curPage === 0 ? "disabled" : ""} data-p="${curPage - 1}">‹</button>`;
    if (start > 0) h += `<button class="pager-btn" data-p="0">1</button><span class="pager-info">…</span>`;
    for (let i = start; i <= end; i++) {
      h += `<button class="pager-btn ${i === curPage ? "active" : ""}" data-p="${i}">${i + 1}</button>`;
    }
    if (end < totalPages - 1)
      h += `<span class="pager-info">…</span><button class="pager-btn" data-p="${totalPages - 1}">${totalPages}</button>`;
    h += `<button class="pager-btn" ${curPage === totalPages - 1 ? "disabled" : ""} data-p="${curPage + 1}">›</button>`;
    h += `<span class="pager-info">${curPage + 1} / ${totalPages} 页</span>`;
    container.innerHTML = h;
    container.querySelectorAll("[data-p]").forEach(b =>
      (b.onclick = () => onPage(parseInt(b.dataset.p)))
    );
  },

  _updateBatchFab() {
    const $ = id => this.shadowRoot.getElementById(id);
    const fab = $("batchFab");
    if (!fab) return;
    const totalSelected = this._selectedNew.size + this._selectedCfg.size;
    if (totalSelected > 0) {
      fab.classList.add("show");
      $("batchCount").textContent = `已选 ${totalSelected} 项`;
      const hasCfg = this._selectedCfg.size > 0;
      const hasNew = this._selectedNew.size > 0;
      $("batchFabClear").onclick = () => {
        this._selectedNew.clear();
        this._selectedCfg.clear();
        this._renderDevs();
        this._updateBatchFab();
      };
      $("batchFabAi").onclick = () => this._batchUpdateMode("ai");
      $("batchFabHa").onclick = () => this._batchUpdateMode("ha");
      $("batchFabDel").onclick = () => {
        if (this._selectedNew.size > 0) this._batchAdd();
        else this._batchDelete();
      };
      $("batchFabRoom").onchange = e => {
        if (e.target.value) this._batchUpdateRoom(e.target.value);
        e.target.value = "";
      };
      $("batchFabAi").style.display = hasCfg ? "block" : "none";
      $("batchFabHa").style.display = hasCfg ? "block" : "none";
      $("batchFabRoom").style.display = hasCfg ? "block" : "none";
      if (hasNew) {
        $("batchFabDel").textContent = "添加选中";
        $("batchFabDel").className = "btn btn-filled btn-sm";
      } else {
        $("batchFabDel").textContent = "停止托管";
        $("batchFabDel").className = "btn btn-error btn-sm";
      }
      const roomSel = $("batchFabRoom");
      if (roomSel) {
        while (roomSel.children.length > 1) roomSel.removeChild(roomSel.lastChild);
        const cAll = this._wsGet("devices", "devices", []);
        const smRooms = cAll.map(i => i.room || "").filter(r => r);
        const haAreas = this._hass.areas
          ? Object.values(this._hass.areas).map(a => a.name)
          : [];
        const allRooms = [...new Set([...haAreas, ...smRooms])].sort((a, b) =>
          a.localeCompare(b, "zh")
        );
        allRooms.forEach(r => {
          const opt = document.createElement("md-select-option");
          opt.value = r;
          opt.innerHTML = `<div slot="headline">${r}</div>`;
          roomSel.appendChild(opt);
        });
      }
    } else {
      fab.classList.remove("show");
    }
  },

  async _batchUpdateRoom(room) {
    const ids = Array.from(this._selectedCfg);
    if (!ids.length) return;
    const desc =
      ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
    if (!(await this._showConfirm(`确认将选中的 ${desc} 批量移动到「${room}」房间？`))) return;
    try {
      for (const id of ids) {
        await this._callService("smart_agent", "update_device", { entity_id: id, room });
      }
      this._selectedCfg.clear();
      this._msg("批量房间设置成功");
      delete this._wsData["devices"];
      await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
      this._updateBatchFab();
    } catch (e) { this._msg("操作失败: " + e.message); }
  },

  async _batchUpdateMode(mode) {
    const ids = Array.from(this._selectedCfg);
    if (!ids.length) return;
    const labels = { ai: "AI全权", ha: "HA优先", shared: "共享" };
    const desc =
      ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
    if (!(await this._showConfirm(`确认将选中的 ${desc} 批量设为「${labels[mode]}」模式？`))) return;
    try {
      for (const id of ids) {
        await this._callService("smart_agent", "set_device_control_mode", { entity_id: id, mode });
      }
      this._selectedCfg.clear();
      this._msg(`批量模式设置成功 -> ${labels[mode]}`);
      delete this._wsData["devices"];
      await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
      this._updateBatchFab();
    } catch (e) { this._msg("操作失败: " + e.message); }
  },

  async _batchDelete() {
    const ids = Array.from(this._selectedCfg);
    if (!ids.length) return;
    const desc =
      ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
    if (!(await this._showConfirm(`警告：确定停止托管选中的 ${desc} 吗？`))) return;
    try {
      for (const id of ids) {
        await this._callService("smart_agent", "delete_device", { entity_id: id });
      }
      this._selectedCfg.clear();
      this._msg("批量删除成功");
      delete this._wsData["devices"];
      await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
      this._updateBatchFab();
    } catch (e) { this._msg("操作失败: " + e.message); }
  },

  async _batchAdd() {
    const ids = Array.from(this._selectedNew);
    if (!ids.length) return;
    const desc =
      ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
    if (!(await this._showConfirm(`确认批量添加 ${desc} 到 SmartAgent 托管？`))) return;
    try {
      await this._callService("smart_agent", "batch_add_devices", {
        entities: ids.join(","),
      });
      this._selectedNew.clear();
      this._msg("批量添加成功");
      delete this._wsData["devices"];
      await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
      this._updateBatchFab();
    } catch (e) { this._msg("添加失败: " + e.message); }
  },

  _selAll(s) {
    if (s) {
      const configured = new Set(this._wsGet("devices", "devices", []).map(d => d.entity_id));
      const activeType = this._newTypeFilter || "all";
      const kw = (this._newSearchKw || "").trim().toLowerCase();
      const showIgnored = this._showIgnored || false;
      const showOffline = this._showOffline || false;
      Object.values(this._hass.states).forEach(st => {
        const d = st.entity_id.split(".")[0];
        if (!TARGET_DOMAINS.includes(d)) return;
        if (!showIgnored) {
          if (SKIP_KW.some(k => st.entity_id.includes(k))) return;
          const n = st.attributes?.friendly_name || "";
          if (SKIP_NAME_KW.some(k => n.toLowerCase().includes(k.toLowerCase()))) return;
        }
        if (configured.has(st.entity_id)) return;
        const unavail = ["unavailable", "unknown"].includes(st.state);
        if (!showOffline && unavail) return;
        if (activeType !== "all" && d !== activeType) return;
        const n = st.attributes?.friendly_name || "";
        if (kw && !n.toLowerCase().includes(kw) && !st.entity_id.toLowerCase().includes(kw)) return;
        this._selectedNew.add(st.entity_id);
      });
    } else {
      this._selectedNew.clear();
    }
    this._renderDevs();
  },

  _updateBizStatus() {
    const cfg = this._cfg.attributes || {};
    const badge = this.shadowRoot.getElementById("bizStatusBadge");
    const tip = this.shadowRoot.getElementById("bizStatusTip");
    if (!badge || !tip) return;
    const startStr = cfg.showroom_biz_start || "09:00";
    const endStr = cfg.showroom_biz_end || "21:00";
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const toMin = s => {
      const [h, m] = (s || "").split(":").map(Number);
      return (h || 0) * 60 + (m || 0);
    };
    const startMin = toMin(startStr);
    const endMin = toMin(endStr);
    const isOpen = nowMin >= startMin && nowMin < endMin;
    if (isOpen) {
      badge.textContent = "🟢 营业中";
      badge.style.background = "var(--sa-succ-container)";
      badge.style.color = "var(--sa-succ)";
      tip.textContent = `营业时间 ${startStr}–${endStr}，AI 处于积极展示模式`;
    } else {
      badge.textContent = "🌙 已打烊";
      badge.style.background = "var(--sa-tertiary-container)";
      badge.style.color = "var(--sa-tertiary)";
      tip.textContent = `营业时间 ${startStr}–${endStr}，AI 进入节能待机模式`;
    }
  },

  // ── 5A-3: 决策气泡通知 ─────────────────────────────────────────────────

  /** 订阅 HA smart_agent_decision_bubble 事件，初始化时调用一次。 */
  _initDecisionBubble() {
    if (this._bubbleUnsub) return;
    try {
      this._bubbleUnsub = this._hass.connection.subscribeEvents(
        (evt) => this._showDecisionBubble(evt.data),
        "smart_agent_decision_bubble"
      );
    } catch (e) {
      // 订阅失败不影响主功能
    }
  },

  /** 显示决策气泡通知。 */
  _showDecisionBubble(data) {
    // 若已有气泡，先清除旧的
    this._dismissDecisionBubble(true);
    const ICO = this._getIcons();
    const scene = this._esc(data.scene || "AI 自动操作");
    const _confRaw = data.confidence != null ? parseInt(data.confidence, 10) : NaN;
    const conf  = !isNaN(_confRaw) ? `${_confRaw}%` : "";
    const acts  = Array.isArray(data.actions) ? data.actions : [];
    const txnId = data.txn_id != null ? data.txn_id : "";
    const actHtml = acts.length
      ? `<div class="bubble-actions-list">${acts.map(a => `· ${this._esc(a)}`).join("<br>")}</div>`
      : "";
    const el = document.createElement("div");
    el.className = "decision-bubble";
    el.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-icon">${ICO.bolt || "⚡"}</span>
        <span class="bubble-scene">${scene}</span>
        ${conf ? `<span class="bubble-conf">${this._esc(conf)}</span>` : ""}
      </div>
      ${actHtml}
      <div class="bubble-footer">
        ${txnId != null && txnId !== "" ? `<button class="bubble-btn bubble-undo" data-txn="${this._esc(String(txnId))}">撤销</button>` : ""}
        <button class="bubble-btn bubble-dismiss">关闭</button>
      </div>`;
    // 挂载到 shadow root 内部，CSS 变量与 .decision-bubble 样式均可生效；
    // position:fixed 在 shadow DOM 内仍相对视口定位（标准行为）
    this.shadowRoot.appendChild(el);
    this._bubbleEl = el;
    el.querySelector(".bubble-dismiss")?.addEventListener("click", () => this._dismissDecisionBubble());
    const undoBtn = el.querySelector(".bubble-undo");
    if (undoBtn) {
      undoBtn.addEventListener("click", async () => {
        const txn = undoBtn.dataset.txn;
        if (txn) {
          try {
            await this._callService("smart_agent", "rollback_transaction", { transaction_id: Number(txn) });
          } catch (err) {
            console.warn("[SmartAgent] 撤销失败:", err);
          }
        }
        this._dismissDecisionBubble();
      });
    }
    // 8 秒后自动消失
    this._bubbleTimer = setTimeout(() => this._dismissDecisionBubble(), 8000);
  },

  // ── 5B-2: 确认气泡（need_confirm=true 时用户手动确认执行）─────────────────

  /** 订阅 smart_agent_confirm_required 事件。 */
  _initConfirmBubble() {
    if (this._confirmUnsub) return;
    try {
      this._confirmUnsub = this._hass.connection.subscribeEvents(
        (evt) => this._showConfirmBubble(evt.data),
        "smart_agent_confirm_required"
      );
    } catch (e) {
      // 订阅失败不影响主功能
    }
  },

  /** 显示确认气泡（AI 不确定，请用户二次确认后再通过 one_off_prompt 重新触发）。 */
  _showConfirmBubble(data) {
    this._dismissConfirmBubble(true);
    const ICO = this._getIcons();
    const scene       = this._esc(data.scene || "AI 推理结果");
    const intentLabel = this._esc(data.intent_label || data.intent || "");
    const _confRaw2   = data.confidence != null ? parseInt(data.confidence, 10) : NaN;
    const conf        = !isNaN(_confRaw2) ? `${_confRaw2}%` : "";
    const reply       = this._esc((data.reply || "").substring(0, 80));
    const acts        = Array.isArray(data.actions) ? data.actions : [];
    const actCount    = Number(data.action_count ?? acts.length) || 0;
    const actHtml     = acts.length
      ? `<div class="bubble-actions-list" style="font-size:11px;opacity:.75">${acts.map(a => `· ${this._esc(String(a))}`).join("<br>")}</div>`
      : "";
    const el = document.createElement("div");
    el.className = "decision-bubble confirm-bubble";
    el.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-icon">${ICO.help || "❓"}</span>
        <span class="bubble-scene">${scene}</span>
        ${conf ? `<span class="bubble-conf" style="background:rgba(234,108,31,.15);color:#e06c1f">${this._esc(conf)}</span>` : ""}
      </div>
      ${intentLabel ? `<div class="bubble-actions-list" style="color:var(--sa-text)">意图: ${intentLabel}</div>` : ""}
      ${reply ? `<div class="bubble-actions-list" style="font-style:italic;opacity:.8">"${reply}"</div>` : ""}
      ${actHtml}
      <div class="bubble-actions-list" style="color:var(--sa-text-variant)">
        ${actCount ? `${actCount} 个动作待执行，` : ""}请确认后 AI 将重新执行此决策
      </div>
      <div class="bubble-footer">
        <button class="bubble-btn bubble-confirm-ok">确认执行</button>
        <button class="bubble-btn bubble-dismiss">取消</button>
      </div>`;
    this.shadowRoot.appendChild(el);
    this._confirmEl = el;
    el.querySelector(".bubble-dismiss")?.addEventListener("click", () => this._dismissConfirmBubble());
    const okBtn = el.querySelector(".bubble-confirm-ok");
    if (okBtn) {
      okBtn.addEventListener("click", async () => {
        this._dismissConfirmBubble();
        try {
          // 用户确认后，以 one_off_prompt 重新触发推理（跳过 need_confirm 检查）
          await this._callService("smart_agent", "process_command", {
            text: `[用户确认] ${data.intent_label || data.scene || "执行AI推理"}`,
          });
        } catch (err) {
          console.warn("[SmartAgent] 确认执行失败:", err);
        }
      });
    }
    // 20 秒后自动消失（确认需要更长的考虑时间）
    this._confirmTimer = setTimeout(() => this._dismissConfirmBubble(), 20000);
  },

  /** 移除确认气泡。 */
  _dismissConfirmBubble(silent = false) {
    if (this._confirmTimer) {
      clearTimeout(this._confirmTimer);
      this._confirmTimer = null;
    }
    if (this._confirmEl) {
      if (!silent) {
        this._confirmEl.classList.add("bubble-out");
        setTimeout(() => this._confirmEl?.remove(), 350);
      } else {
        this._confirmEl.remove();
      }
      this._confirmEl = null;
    }
  },

  /** 移除决策气泡。 */
  _dismissDecisionBubble(silent = false) {
    if (this._bubbleTimer) {
      clearTimeout(this._bubbleTimer);
      this._bubbleTimer = null;
    }
    if (this._bubbleEl) {
      if (!silent) {
        this._bubbleEl.classList.add("bubble-out");
        setTimeout(() => this._bubbleEl?.remove(), 350);
      } else {
        this._bubbleEl.remove();
      }
      this._bubbleEl = null;
    }
  },

  _applyBrand(brand = {}) {
    const cfg = Object.assign({}, this._cfg ? this._cfg.attributes : {}, brand);
    const name = cfg.brand_name || "SmartAgent";
    const color = cfg.brand_primary_color || "#6750A4";
    const logo = cfg.brand_logo_url || "";
    const deploy = cfg.deploy_name ? ` · ${cfg.deploy_name}` : "";
    this.style.setProperty("--sa-primary", color);
    this.style.setProperty("--sa-on-primary-container", color);
    this.style.setProperty("--sa-on-primary", "#ffffff");
    const h1 = this.shadowRoot.querySelector(".app-bar h1");
    if (h1) {
      const ICO = this._getIcons();
      const logoHtml = logo
        ? `<img src="${this._esc(logo)}" style="width:28px;height:28px;border-radius:6px;object-fit:cover;margin-right:2px">`
        : `<span style="color:var(--sa-primary);display:flex;align-items:center">${ICO.bolt}</span>`;
      h1.innerHTML = `${logoHtml} ${this._esc(name)}${this._esc(deploy)}`;
    }
    const ver = this.shadowRoot.querySelector(".version");
    if (ver) ver.textContent = `${name}${deploy} — Material Design 3 Edition`;
    const preview = this.shadowRoot.getElementById("brandLogoPreview");
    if (preview) {
      const ICO = this._getIcons();
      preview.innerHTML = logo
        ? `<img src="${this._esc(logo)}" style="width:100%;height:100%;object-fit:cover">`
        : `<span style="font-size:24px">${ICO.bolt}</span>`;
    }
  },

};
