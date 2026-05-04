/**
 * SmartAgent Panel — AI 场景 tab 渲染模块
 */

export const aiscenesMethods = {
  _renderAiScenes() {
    const ICO = this._getIcons();
    const scenes = this._wsGet("ai_scenes", "scenes", []);

    const runBtn = this.shadowRoot.getElementById("runAnalysisBtn");
    if (runBtn && !runBtn._bound) {
      runBtn._bound = true;
      runBtn.onclick = async () => {
        runBtn.disabled = true;
        runBtn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px">⏳ 分析中...</span>`;
        try {
          await this._callService("smart_agent", "run_pattern_analysis", {});
          this._msg("行为分析已启动，约 15-30 秒后自动刷新");
          setTimeout(() => {
            this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          }, 15000);
        } catch (e) {
          this._msg("分析失败: " + e.message);
        } finally {
          runBtn.disabled = false;
          runBtn.innerHTML = `🔍 立即分析`;
        }
      };
    }

    const pending  = scenes.filter(s => s.status === "pending");
    const active   = scenes.filter(s => s.status === "active");
    const rejected = scenes.filter(s => s.status === "rejected");

    const $ = id => this.shadowRoot.getElementById(id);
    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(this.shadowRoot, [
        "#runAnalysisBtn",
        "#aiSceneParseBtn",
        "#aiSceneConfirmBtn",
        "#aiSceneCreateCancel",
        ".ai-scene-approve",
        ".ai-scene-reject",
        ".ai-scene-trigger",
        ".ai-scene-delete",
        "#writeYaml"
      ].join(","));
    }
    const pendingBadge = $("aiScenesPendingBadge");
    if (pendingBadge) pendingBadge.textContent = pending.length;
    const activeBadge = $("aiScenesActiveBadge");
    if (activeBadge) activeBadge.textContent = active.length;
    const rejectedBadge = $("aiScenesRejectedBadge");
    if (rejectedBadge) rejectedBadge.textContent = rejected.length;

    /* ── 置信度样式 ── */
    const confMeta = c => {
      if (c >= 85) return { cls: "conf-high",  label: "高置信",  color: "var(--sa-succ)" };
      if (c >= 70) return { cls: "conf-med",   label: "中置信",  color: "var(--sa-primary)" };
      return              { cls: "conf-low",   label: "低置信",  color: "var(--sa-text-variant)" };
    };

    const parseJsonArray = (value) => {
      try {
        const parsed = JSON.parse(value || "[]");
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    };

    /* ── 实体芯片渲染（优先 actions_json，回退 entities_json） ── */
    const renderEntities = (entities_json, actions_json, limit = 6) => {
      const entities = parseJsonArray(entities_json);
      const actions = parseJsonArray(actions_json);

      const actionMap = new Map();
      for (const a of actions) {
        const eid = a?.entity_id;
        if (!eid) continue;
        actionMap.set(eid, a);
      }

      const summarizeParams = (entity, action) => {
        const p = (action && typeof action.params === "object" && action.params) || {};
        const merged = { ...(entity || {}), ...p };
        const parts = [];
        if (merged.brightness_pct != null) parts.push(`${merged.brightness_pct}%`);
        else if (merged.brightness != null) {
          const pct = Math.round((Number(merged.brightness) / 255) * 100);
          if (!Number.isNaN(pct)) parts.push(`${pct}%`);
        }
        if (merged.color_temp_kelvin != null) parts.push(`${merged.color_temp_kelvin}K`);
        else if (merged.color_temp != null) parts.push(`CT:${merged.color_temp}`);
        if (merged.temperature != null) parts.push(`${merged.temperature}°C`);
        if (merged.position != null) parts.push(`位置${merged.position}%`);
        if (merged.tilt_position != null) parts.push(`倾角${merged.tilt_position}%`);
        if (merged.hvac_mode) parts.push(`${merged.hvac_mode}`);
        if (merged.fan_mode) parts.push(`风速:${merged.fan_mode}`);
        return parts.join(" · ");
      };

      const source = actions.length ? actions.map(a => ({
        entity_id: a.entity_id,
        state: a.service?.includes("off") || a.service?.includes("close") ? "off" : "on",
        _action: a,
      })) : entities;

      const visible = source.slice(0, limit);
      const more = source.length - visible.length;
      const chips = visible.map(e => {
        const stOn = ["on", "open", "heat", "cool", "auto"].includes(e.state);
        const dot  = stOn
          ? `<span style="width:6px;height:6px;border-radius:50%;background:var(--sa-succ);flex-shrink:0"></span>`
          : `<span style="width:6px;height:6px;border-radius:50%;background:var(--sa-border);flex-shrink:0"></span>`;
        const domain = (e.entity_id || "").split(".")[0];
        const dIco   = ICO[domain] || ICO.device;
        const name   = (e.entity_id || "").split(".")[1] || e.entity_id;
        const action = e._action || actionMap.get(e.entity_id) || null;
        const summary = summarizeParams(e, action);
        return `<span title="${this._esc(e.entity_id)}" style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px 3px 6px;
                  border-radius:20px;background:rgba(128,128,128,.1);font-size:11px;max-width:260px;overflow:hidden;
                  white-space:nowrap;text-overflow:ellipsis">
                  ${dot}${dIco}<span style="overflow:hidden;text-overflow:ellipsis">${this._esc(name)}${summary ? ` · ${this._esc(summary)}` : ""}</span>
                </span>`;
      }).join("");
      const extra = more > 0
        ? `<span style="font-size:11px;opacity:.55;padding:3px 6px">+${more} 个</span>` : "";
      return chips + extra;
    };

    /* ── 场景卡片渲染 ── */
    const renderCard = (s, { showApprove = false, showReject = false, showTrigger = false, dimmed = false } = {}) => {
      const cm = confMeta(s.confidence);
      const actions = parseJsonArray(s.actions_json);
      const entities = actions.length ? [] : parseJsonArray(s.entities_json);
      const entCount = actions.length ? actions.length : entities.length;
      const borderColor = dimmed ? "var(--sa-border)" : cm.color;

      return `
      <div class="scene-card ${dimmed ? "scene-card--dimmed" : ""}"
           data-scene-id="${s.id}"
           style="border-left: 3px solid ${borderColor};margin-bottom:10px;border-radius:0 14px 14px 0;
                  background:var(--sa-card);border-top:1px solid var(--sa-border);
                  border-right:1px solid var(--sa-border);border-bottom:1px solid var(--sa-border);">

        <!-- 卡片主体 -->
        <div style="padding:14px 16px 10px">

          <!-- 标题行 -->
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:6px">
            <div style="display:flex;align-items:center;gap:7px;min-width:0;flex:1">
              <span style="color:${cm.color};flex-shrink:0">${ICO.spark}</span>
              <span class="label-l" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">
                ${this._esc(s.name)}
              </span>
            </div>
            <span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;
                         background:${cm.color}1a;color:${cm.color};font-size:11px;font-weight:600;flex-shrink:0;white-space:nowrap">
              ${ICO.gauge} ${s.confidence}% · ${cm.label}
            </span>
          </div>

          <!-- 描述 -->
          <div class="body-s" style="opacity:.75;margin-bottom:10px;line-height:1.5">
            ${this._esc(s.description || "")}
          </div>

          <!-- 元数据行 -->
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap">
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              ${ICO.schedule} ${this._esc(s.trigger_context || "—")}
            </span>
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              📊 历史触发 ${s.hit_count} 次
            </span>
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              💡 ${entCount} 个设备
            </span>
          </div>

          <!-- 实体芯片 -->
          <div style="display:flex;flex-wrap:wrap;gap:5px">
            ${renderEntities(s.entities_json, s.actions_json)}
          </div>
        </div>

        <!-- 操作按钮行 -->
        <div style="display:flex;align-items:center;gap:8px;padding:8px 16px 12px;border-top:1px solid var(--sa-border);flex-wrap:wrap">
          ${showApprove ? `<md-filled-button class="ai-scene-approve" data-id="${s.id}"
              style="--md-filled-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.check} 确认启用</md-filled-button>` : ""}
          ${showTrigger ? `<md-filled-tonal-button class="ai-scene-trigger" data-id="${s.id}"
              style="--md-filled-tonal-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.play} 立即触发</md-filled-tonal-button>` : ""}
          <md-outlined-button class="ai-scene-yaml" data-id="${s.id}"
              style="--md-outlined-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.yaml} 导出 YAML</md-outlined-button>
          ${showReject ? `<md-outlined-button class="ai-scene-reject" data-id="${s.id}"
              style="--md-outlined-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px;color:var(--sa-text-variant)">
              ${ICO.close} 拒绝</md-outlined-button>` : ""}
          <span style="flex:1"></span>
          <md-icon-button class="ai-scene-delete" data-id="${s.id}"
              title="删除场景" style="color:var(--sa-error);opacity:.7">
              ${ICO.delete}</md-icon-button>
        </div>
      </div>`;
    };

    /* ── 渲染各分区 ── */

    /* ── 一句话创建场景面板 ── */
    const createPanel = $("aiSceneCreatePanel");
    if (createPanel && !createPanel._bound) {
      createPanel._bound = true;

      const toggleBtn  = $("aiSceneCreateToggle");
      const body       = $("aiSceneCreateBody");
      const textarea   = $("aiSceneCreateText");
      const autoChk    = $("aiSceneAutoActivate");
      const parseBtn   = $("aiSceneParseBtn");
      const confirmBtn = $("aiSceneConfirmBtn");
      const cancelBtn  = $("aiSceneCreateCancel");
      const preview    = $("aiSceneCreatePreview");

      // 折叠/展开
      toggleBtn.onclick = () => {
        const open = body.style.display !== "none";
        body.style.display = open ? "none" : "block";
        toggleBtn.textContent = open ? "＋ 用自然语言创建场景" : "－ 收起";
      };

      // 取消
      cancelBtn.onclick = () => {
        textarea.value = "";
        preview.style.display = "none";
        confirmBtn.style.display = "none";
        cancelBtn.style.display = "none";
      };

      // AI 解析（预览模式：先解析再确认）
      parseBtn.onclick = async () => {
        const text = textarea.value.trim();
        if (!text) { this._msg("请先输入场景描述"); return; }
        parseBtn.disabled = true;
        parseBtn.textContent = "⏳ AI 解析中...";
        preview.style.display = "none";
        confirmBtn.style.display = "none";
        cancelBtn.style.display = "none";

        // 监听 smart_agent_scene_created 事件（一次性）
        const onCreated = (ev) => {
          clearTimeout(eventTimeout);
          if (typeof unsubSceneCreated === "function") unsubSceneCreated();
          parseBtn.disabled = false;
          parseBtn.textContent = "🤖 AI 解析生成";
          const d = ev.data || ev.detail || {};
          if (!d.success) {
            this._msg("解析失败：" + (d.error || "未知错误"));
            return;
          }
          // 显示预览
          preview.innerHTML = `
            <div style="font-size:13px;color:var(--sa-text-variant);margin-bottom:6px">解析结果预览</div>
            <div style="font-weight:600;margin-bottom:4px">📋 ${this._esc(d.name || "新场景")}</div>
            <div style="font-size:12px;color:var(--sa-text-variant)">
              状态：${d.status === "active" ? "✅ 已直接激活" : "⏳ 待确认"}
            </div>`;
          preview.style.display = "block";
          confirmBtn.style.display = "inline-flex";
          cancelBtn.style.display = "inline-flex";
          // 存储 scene_id 供确认按钮使用
          confirmBtn.dataset.sceneId = d.scene_id;
          confirmBtn.dataset.status  = d.status;
          // 若已直接激活，刷新列表
          if (d.status === "active") {
            this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          }
        };

        let eventTimeout = null;
        let unsubSceneCreated = null;
        try {
          unsubSceneCreated = await this._hass.connection.subscribeEvents(onCreated, "smart_agent_scene_created");
          eventTimeout = setTimeout(() => {
            if (typeof unsubSceneCreated === "function") unsubSceneCreated();
            parseBtn.disabled = false;
            parseBtn.textContent = "🤖 AI 解析生成";
            this._msg("解析超时，请稍后重试");
          }, 30000);
          await this._callService("smart_agent", "create_scene_from_text", {
            text: text,
            auto_activate: autoChk ? autoChk.checked : false,
          });
        } catch (e) {
          if (eventTimeout) clearTimeout(eventTimeout);
          if (typeof unsubSceneCreated === "function") unsubSceneCreated();
          parseBtn.disabled = false;
          parseBtn.textContent = "🤖 AI 解析生成";
          this._msg("调用失败: " + e.message);
        }
      };

      // 确认后刷新列表
      confirmBtn.onclick = async () => {
        const status = confirmBtn.dataset.status;
        if (status !== "active") {
          // 若未直接激活，提示用户去待确认区审批
          this._msg("场景已创建，请在「待确认」区审批激活");
        }
        textarea.value = "";
        preview.style.display = "none";
        confirmBtn.style.display = "none";
        cancelBtn.style.display = "none";
        await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
      };
    }

    $("aiScenesPending").innerHTML = pending.length
      ? pending.map(s => renderCard(s, { showApprove: true, showReject: true })).join("")
      : `<div class="empty-state">
           <div class="empty-state-icon">🔮</div>
           <div class="empty-state-title">暂无待确认候选场景</div>
           <div class="empty-state-desc">每日凌晨行为分析后自动生成，或点击「立即分析」手动触发</div>
         </div>`;

    $("aiScenesActive").innerHTML = active.length
      ? active.map(s => renderCard(s, { showTrigger: true })).join("")
      : `<div class="empty-state">
           <div class="empty-state-icon">✨</div>
           <div class="empty-state-title">暂无已激活场景</div>
           <div class="empty-state-desc">审批通过的场景将在此显示</div>
         </div>`;

    $("aiScenesRejected").innerHTML = rejected.length
      ? rejected.map(s => renderCard(s, { showApprove: true, dimmed: true })).join("")
      : `<div class="empty-state">
           <div class="empty-state-icon">🗂️</div>
           <div class="empty-state-title">暂无已拒绝场景</div>
         </div>`;

    /* ── 事件绑定 ── */
    const view = this.shadowRoot.getElementById("view-aiscenes");
    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(view, ".ai-scene-approve,.ai-scene-reject,.ai-scene-trigger,.ai-scene-delete,#writeYaml");
    }

    view.querySelectorAll(".ai-scene-approve").forEach(b => {
      b.onclick = async () => {
        b.disabled = true;
        try {
          await this._callService("smart_agent", "approve_ai_scene", { id: parseInt(b.dataset.id) });
          this._msg("场景已激活，将加入 AI 推理上下文");
          await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
        } catch (e) {
          this._msg("操作失败: " + e.message);
          b.disabled = false;
        }
      };
    });

    view.querySelectorAll(".ai-scene-reject").forEach(b => {
      b.onclick = async () => {
        if (!(await this._showConfirm("拒绝后该场景不再自动推荐，确认吗？"))) return;
        b.disabled = true;
        try {
          await this._callService("smart_agent", "reject_ai_scene", { id: parseInt(b.dataset.id) });
          this._msg("已拒绝场景");
          await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
        } catch (e) {
          this._msg("操作失败: " + e.message);
          b.disabled = false;
        }
      };
    });

    view.querySelectorAll(".ai-scene-trigger").forEach(b => {
      b.onclick = async () => {
        if (!(await this._showConfirm("立即触发此场景？将批量执行场景内所有设备动作。"))) return;
        b.disabled = true;
        try {
          await this._callService("smart_agent", "trigger_ai_scene", { id: parseInt(b.dataset.id) });
          this._msg("场景触发指令已发送");
        } catch (e) {
          this._msg("触发失败: " + e.message);
        } finally {
          b.disabled = false;
        }
      };
    });

    view.querySelectorAll(".ai-scene-delete").forEach(b => {
      b.onclick = async () => {
        if (!(await this._showConfirm("确定删除此 AI 场景？"))) return;
        b.disabled = true;
        try {
          await this._callService("smart_agent", "delete_ai_scene", { id: parseInt(b.dataset.id) });
          this._msg("已删除 AI 场景");
          await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
        } catch (e) {
          this._msg("删除失败: " + e.message);
          b.disabled = false;
        }
      };
    });

    view.querySelectorAll(".ai-scene-yaml").forEach(b => {
      b.onclick = async () => {
        const id = b.dataset.id;
        b.disabled = true;
        try {
          const resp = await this._hass.fetchWithAuth(`/api/v1/scenes/export-yaml?scene_id=${id}`);
          const data = await resp.json();
          if (data.error) { this._msg("导出失败: " + data.error); return; }

          const overlay = document.createElement("div");
          overlay.style = `position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.65);
                           z-index:9999;display:flex;align-items:center;justify-content:center;
                           padding:20px;backdrop-filter:blur(6px)`;
          const dialog = document.createElement("div");
          dialog.style = `background:var(--sa-card);width:100%;max-width:600px;border-radius:24px;
                          padding:24px;box-shadow:0 16px 48px rgba(0,0,0,0.45);display:flex;flex-direction:column;gap:16px`;
          dialog.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center">
              <h3 style="margin:0;font-size:17px;display:flex;align-items:center;gap:8px">${ICO.yaml} 自动化 YAML 导出</h3>
              <md-icon-button id="closeYaml" style="background:transparent">${ICO.close}</md-icon-button>
            </div>
            <div style="font-size:12px;opacity:0.65;line-height:1.6">
              复制到 HA 的 <code style="background:rgba(128,128,128,.15);padding:1px 5px;border-radius:4px">automations.yaml</code>，
              或点击「写入 HA」自动追加。首次使用需在 <code style="background:rgba(128,128,128,.15);padding:1px 5px;border-radius:4px">configuration.yaml</code>
              的 <code>automation:</code> 段加入 <code>!include smart_agent_automations.yaml</code> 并重启一次。
            </div>
            <textarea id="yamlText" readonly style="width:100%;height:280px;background:var(--sa-bg);color:var(--sa-text);
                      border:1px solid var(--sa-border);border-radius:12px;padding:12px;font-family:monospace;
                      font-size:12px;resize:vertical;box-sizing:border-box">${this._esc(data.yaml)}</textarea>
            <div style="display:flex;gap:10px">
              <md-filled-tonal-button id="copyYaml" style="flex:1">复制到剪贴板</md-filled-tonal-button>
              <md-filled-button id="writeYaml" style="flex:1">写入 HA 自动化</md-filled-button>
            </div>`;

          overlay.appendChild(dialog);
          this.shadowRoot.appendChild(overlay);

          const close = dialog.querySelector("#closeYaml");
          const copy  = dialog.querySelector("#copyYaml");
          const write = dialog.querySelector("#writeYaml");
          const area  = dialog.querySelector("#yamlText");

          close.onclick = () => this.shadowRoot.removeChild(overlay);
          overlay.onclick = e => { if (e.target === overlay) close.onclick(); };

          copy.onclick = () => {
            area.select();
            document.execCommand("copy");
            copy.textContent = "✅ 已复制";
            setTimeout(() => { copy.textContent = "复制到剪贴板"; }, 2000);
          };

          write.onclick = async () => {
            if (this._isHaFallbackReadOnly()) {
              this._warnHaFallbackReadOnly();
              return;
            }
            write.disabled = true;
            write.textContent = "写入中...";
            try {
              const wr = await this._hass.fetchWithAuth(`/api/v1/scenes/export-yaml`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scene_id: parseInt(id) }),
              });
              const wd = await wr.json();
              if (wd.success) {
                write.textContent = "✅ 已写入";
                this._msg(`已写入 smart_agent_automations.yaml（共 ${wd.automation_count} 条）${wd.reload_ok ? "，HA 已重载" : "，请手动重启 HA 一次"}`);
              } else {
                write.disabled = false;
                write.textContent = "写入 HA 自动化";
                this._msg("写入失败: " + (wd.error || "未知错误"));
              }
            } catch (err) {
              write.disabled = false;
              write.textContent = "写入 HA 自动化";
              this._msg("写入失败: " + err.message);
            }
          };
        } catch (e) {
          this._msg("导出失败: " + e.message);
        } finally {
          b.disabled = false;
        }
      };
    });
  },
};
