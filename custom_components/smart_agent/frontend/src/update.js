/**
 * SmartAgent Panel — _update() 状态同步模块
 * 每次 hass 属性更新时调用，将 HA 传感器状态同步到 DOM。
 */

export const updateMethods = {
  _update() {
    const $ = id => this.shadowRoot.getElementById(id);
    const c = this._cfg.attributes || {}, s = this._sts.attributes || {};
    if ($("dCnt")) $("dCnt").textContent = c.device_count || 0;
    if ($("hCnt")) $("hCnt").textContent = c.habit_count || 0;
    if ($("rCnt")) $("rCnt").textContent = c.rule_count || 0;
    // 推理规则拆分：用户手动规则 vs AI 学习规则
    if ($("rCntSub")) {
      const total = c.rule_count || 0;
      const aiCount = c.ai_rule_count || 0;
      const userCount = total - aiCount;
      if (total > 0) {
        $("rCntSub").textContent = `用户 ${userCount} · AI ${aiCount}`;
      }
    }
    if ($("sTxt")) $("sTxt").textContent = s.full_text || "正在监控中...";

    // ── 动作质量统计 ──
    const aq = c.action_quality || {};
    const qCard = $("qualityCard");
    if (qCard) {
      if (aq.total > 0) {
        qCard.style.display = "block";
        const rateColor = aq.rate >= 95 ? "var(--sa-succ)" : aq.rate >= 80 ? "#d29922" : "#f85149";
        $("qualityStats").innerHTML = `
          <div class="sys-card"><div class="label-m">总执行次数</div><div class="stat-num" style="font-size:28px">${aq.total}</div></div>
          <div class="sys-card"><div class="label-m">成功率</div><div class="stat-num" style="font-size:28px;color:${rateColor}">${aq.rate}%</div></div>
          <div class="sys-card"><div class="label-m">失败次数</div><div class="stat-num" style="font-size:28px;color:${aq.failed?'#f85149':'var(--sa-succ)'}">${aq.failed}</div></div>
          <div class="sys-card"><div class="label-m">自动重试</div><div class="stat-num" style="font-size:28px">${aq.retry_total}</div></div>
          <div class="sys-card"><div class="label-m">平均验证延迟</div><div class="stat-num" style="font-size:28px">${aq.avg_latency_ms}<span style="font-size:12px;opacity:.6">ms</span></div></div>
        `;
        const tf = aq.top_failures || [];
        if (tf.length) {
          $("qualityFailures").innerHTML = `<div class="label-m" style="margin-bottom:8px;color:#f85149">失败最多的设备 Top ${tf.length}</div>` +
            tf.map(f => `<div class="body-s" style="padding:4px 0;display:flex;justify-content:space-between"><span>${this._esc(f.entity_id)}</span><span style="color:#f85149;font-weight:600">${f.count} 次</span></div>`).join("");
        } else {
          $("qualityFailures").innerHTML = "";
        }
      } else {
        qCard.style.display = "none";
      }
    }

    // ── 优先级保护状态 ──
    const guards = c.priority_guards || [];
    const priCard = $("priorityCard");
    const priList = $("priorityList");
    const priCount = $("priorityCount");
    if (priCard && priList) {
      if (guards.length > 0) {
        priCard.style.display = "block";
        if (priCount) priCount.textContent = `${guards.length} 个设备受保护`;
        const priColors = {0: "#ef4444", 1: "#f59e0b", 2: "#3b82f6", 3: "#8b5cf6", 4: "var(--sa-text-variant)"};
        priList.innerHTML = guards.map(g => {
          const color = priColors[g.priority] || "var(--sa-text-variant)";
          const mins = Math.ceil(g.remaining_sec / 60);
          const timeStr = g.remaining_sec > 60 ? `${mins}分钟` : `${g.remaining_sec}秒`;
          return `<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;background:var(--sa-bg);border:1px solid var(--sa-border)">
            <span style="color:${color};font-weight:700;font-size:12px;white-space:nowrap">${this._esc(g.priority_label)}</span>
            <span style="flex:1;font-size:13px">${this._esc(g.name)}<span style="opacity:.5;font-size:11px;margin-left:4px">${this._esc(g.entity_id)}</span></span>
            <span style="font-size:12px;opacity:.7">← ${this._esc(g.source_label)}</span>
            <span style="font-size:11px;color:${color};font-weight:600;white-space:nowrap">${timeStr}</span>
          </div>`;
        }).join("");
      } else {
        priCard.style.display = "none";
      }
    }

    // 同步系统策略控件（engSel/engModelHint 已移至系统配置页，用 if 保护避免 null 报错）
    const numA = $("numA"), numN = $("numN");
    if (numA && this._numA.state) {
      numA.value = parseFloat(this._numA.state);
      $("numAVal").textContent = this._numA.state;
    }
    if (numN && this._numN.state) {
      numN.value = parseFloat(this._numN.state);
      $("numNVal").textContent = this._numN.state;
    }

    const modeSel = $("modeSel"), showroomPanel = $("showroomPanel"), modeIcon = $("modeIcon");
    const modeChip = $("modeChip"), sceneIconWrap = $("sceneIconWrap");
    const ICO = this._getIcons();
    this._uiCache = this._uiCache || {};

    // ── 近期 AI 操作：控制台只显示徽章 + 摘要，详情移至"纠错学习"页 ──
    const recentAi = s.recent_ai_actions || [];
    const now = Date.now() / 1000;
    const FRESH_SEC = 30 * 60;
    const freshAi = recentAi.filter(a => a.time && (now - a.time) < FRESH_SEC);
    const aiCard = $("recentAiCard");
    if (aiCard) {
      if (recentAi.length > 0) {
        aiCard.style.display = "block";
        const badge = $("corrBadge");
        // 徽章：30分钟内为"急需处理"，用红色数字；有旧记录但无新记录时显示灰色
        if (badge) {
          badge.textContent = freshAi.length > 0 ? freshAi.length : recentAi.length;
          badge.style.background = freshAi.length > 0 ? "" : "var(--sa-border, #555)";
          badge.title = freshAi.length > 0
            ? `${freshAi.length} 个设备在 30 分钟内被 AI 操作，可纠正`
            : `${recentAi.length} 个设备有历史 AI 操作记录（已超过 30 分钟）`;
        }
        // 摘要：按场景展示设备数小标签
        const groups = new Map();
        recentAi.forEach(a => {
          const key = a.scene || '(未知场景)';
          if (!groups.has(key)) groups.set(key, 0);
          groups.set(key, groups.get(key) + 1);
        });
        const summary = $("recentAiSummary");
        if (summary) {
          let h = '';
          groups.forEach((cnt, scene) => {
            h += `<span class="chip" style="font-size:11px;cursor:pointer;max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
              title="${this._esc(scene)}" data-goto-corr="1">
              ${ICO.bolt} ${this._esc(scene.length > 20 ? scene.slice(0,20)+'…' : scene)} · ${cnt} 设备</span>`;
          });
          summary.innerHTML = h;
          summary.querySelectorAll("[data-goto-corr]").forEach(el => {
            el.onclick = () => this._setTab("corrections");
          });
        }
      } else {
        aiCard.style.display = "none";
      }
    }
    const goBtn = $("goToCorrections");
    if (goBtn) goBtn.onclick = () => this._setTab("corrections");
    const isShowroom = c.mode === "showroom";
    if (this._uiCache.mode !== c.mode) {
      this._uiCache.mode = c.mode;
      if (modeSel && !modeSel.matches(":focus-within")) modeSel.value = c.mode || "home";
      if (modeIcon) modeIcon.innerHTML = isShowroom ? ICO.showroom : ICO.home;
      if (modeChip) {
        modeChip.textContent = isShowroom ? "展厅模式" : "家庭模式";
        modeChip.classList.toggle("active", isShowroom);
      }
      if (sceneIconWrap) sceneIconWrap.innerHTML = isShowroom ? ICO.showroom : ICO.home;
      if (showroomPanel) showroomPanel.style.display = isShowroom ? "block" : "none";
    }

    // 动态渲染场景按钮
    const sceneBtns = $("showroomSceneBtns");
    if (sceneBtns && Array.isArray(c.showroom_scenes)) {
      const activeScene = c.showroom_scene || "";
      const hasCustom = !!(c.showroom_custom_prompt || "");
      sceneBtns.innerHTML = c.showroom_scenes.map(s => {
        const isActive = (activeScene === s.key) && !hasCustom;
        return `
          <div style="display:flex;align-items:center;gap:4px">
            <button class="chip ${isActive ? 'active' : ''} showroom-scene-btn" 
              data-scene="${this._esc(s.key)}" data-label="${this._esc(s.label)}">
              ${this._esc(s.label)}
            </button>
            <button class="showroom-edit-btn" data-scene="${this._esc(s.key)}" 
              style="background:none;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:4px;border-radius:50%;transition:.2s" 
              title="编辑">
              <span style="opacity:.5">${ICO.edit}</span>
            </button>
        </div>`;
      }).join("");
    }

    const customInput = $("showroomCustomInput");
    if (customInput && !customInput.matches(":focus") && (c.showroom_custom_prompt || "")) {
      customInput.value = c.showroom_custom_prompt;
    }

    const b = $("aiBtn"), isOn = this._sw.state === "on";
    b.className = isOn ? "btn btn-tonal btn-sm" : "btn btn-error btn-sm";
    b.textContent = isOn ? "托管中" : "已暂停";

    // 同步开关状态
    const learnSt = this._hass?.states["switch.smart_agent_learning_mode"];
    const learnOn = learnSt?.state === "on";
    const learnToggle = $("learningModeToggle");
    if (learnToggle) learnToggle.selected = learnOn;
    const learnItem = $("learningModeItem");
    if (learnItem) learnItem.classList.toggle("active", learnOn);

    const habitSt = this._hass?.states["switch.smart_agent_habit_proactive"];
    const habitOn = habitSt?.state === "on";
    const habitToggle = $("habitProactiveToggle");
    if (habitToggle) habitToggle.selected = habitOn;
    const habitItem = $("habitProactiveItem");
    if (habitItem) habitItem.classList.toggle("active", habitOn);

    const frigateSt = this._hass?.states["switch.smart_agent_frigate_enabled"];
    const frigateOn = frigateSt?.state === "on";
    const frigateToggle = $("frigateToggle");
    if (frigateToggle) frigateToggle.selected = frigateOn;
    const frigateItem = $("frigateItem");
    if (frigateItem) frigateItem.classList.toggle("active", frigateOn);

    const visionSt = this._hass?.states["switch.smart_agent_vision_enabled"];
    const visionOn = visionSt?.state === "on";
    const visionToggle = $("visionToggle");
    if (visionToggle) visionToggle.selected = visionOn;
    const visionItem = $("visionItem");
    if (visionItem) visionItem.classList.toggle("active", visionOn);

    // License 状态渲染
    this._renderLicenseStatus(c.license);

    // WS 驱动的 tab 不在 _update 中重渲染（数据由 _wsRefresh 独立更新）
    // 仅 dashboard 相关的状态变化在 _update 中处理（已在上方处理）
    if (this._tab === "syslog" && this._sysLogMode === "live") {
      // sensor 属性有 16KB 上限会丢弃 sys_log，改由 WebSocket 拉取完整日志
      this._wsRefreshSysLog();
    }

    // 品牌配置：状态刷新时同步更新标题栏（仅当品牌非默认时才需要更新）
    if (c.brand_name || c.brand_primary_color) {
      this._applyBrand();
    }
  }
};
