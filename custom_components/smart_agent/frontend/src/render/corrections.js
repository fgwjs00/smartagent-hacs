/**
 * SmartAgent Panel — 纠错学习 tab 渲染模块
 */

export const correctionsMethods = {
  _renderCorrections() {
    const raw = this._wsGet("ai_actions", "actions", []);
    const $ = id => this.shadowRoot.getElementById(id);
    const ICO = this._getIcons();
    const box = $("corrList");
    if (!box) return;
    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(this.shadowRoot, "#corrClearAll,.corr-correct-btn,.corr-dismiss-btn,.corr-dismiss-scene");
    }

    const now = Date.now() / 1000;
    const FRESH_SEC = 30 * 60;
    const ALL_SEC = 8 * 3600;
    const WARN_SEC = 5 * 60;
    const filterMode = this._corrFilter || "all";

    const visible = raw.filter(a => {
      if (!a.time) return true;
      if (filterMode === "fresh") return now - a.time < FRESH_SEC;
      return now - a.time < ALL_SEC;
    });

    const btnAll = $("corrFilterAll"), btnFresh = $("corrFilterFresh");
    if (btnAll) btnAll.classList.toggle("dim", filterMode !== "all");
    if (btnFresh) btnFresh.classList.toggle("dim", filterMode !== "fresh");

    if (btnAll && !btnAll._bound) {
      btnAll._bound = true;
      btnAll.onclick = () => { this._corrFilter = "all"; this._renderCorrections(); };
    }
    if (btnFresh && !btnFresh._bound) {
      btnFresh._bound = true;
      btnFresh.onclick = () => { this._corrFilter = "fresh"; this._renderCorrections(); };
    }
    const btnClearAll = $("corrClearAll");
    if (btnClearAll && !btnClearAll._bound) {
      btnClearAll._bound = true;
      btnClearAll.onclick = async () => {
        if (!(await this._showConfirm("确定清空全部近期操作记录吗？"))) return;
        try {
          await this._callService("smart_agent", "dismiss_ai_action", {});
          this._msg("已清空全部操作记录");
        } catch (err) {
          this._msg("清空失败: " + String(err.message || err));
        }
      };
    }

    if (!visible.length) {
      box.innerHTML = `<div style="opacity:.5;text-align:center;padding:32px">
        ${filterMode === "fresh"
          ? "没有待处理的操作（30分钟内无新 AI 动作），或已全部处理完毕 ✅"
          : "最近 8 小时内无 AI 动作记录（记录在 8 小时后自动清理）"}
      </div>`;
      return;
    }

    const groups = new Map();
    visible.forEach(a => {
      const key = a.scene || "(未知场景)";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(a);
    });

    let html = "";
    groups.forEach((items, scene) => {
      const oldest = items[0];
      const age = oldest.time ? now - oldest.time : 0;
      const expired = age > FRESH_SEC;
      const warn = !expired && age > WARN_SEC;
      const timeStr = oldest.time
        ? new Date(oldest.time * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : "";
      const ageMin = Math.floor(age / 60);
      const ageLbl =
        age > 0 ? (ageMin >= 60 ? `${Math.floor(ageMin / 60)}h${ageMin % 60}m前` : `${ageMin}m前`) : "";
      const headerBg = expired ? "var(--sa-bg)" : "var(--sa-primary-container)";
      const headerColor = expired ? "var(--sa-text2,#666)" : "var(--sa-primary)";

      html += `
        <div style="background:var(--sa-card);border:1px solid ${expired ? "var(--sa-border)" : "var(--sa-primary)"};border-radius:14px;overflow:hidden;${expired ? "opacity:.6" : ""}">
          <div style="padding:10px 14px;display:flex;align-items:center;gap:8px;background:${headerBg}">
            ${expired ? `<span style="font-size:11px">⏰</span>` : ICO.bolt}
            <span style="flex:1;font-size:12px;font-weight:600;color:${headerColor};white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
              title="${this._esc(scene)}">${this._esc(scene)}</span>
            <span style="font-size:11px;opacity:.6">${timeStr} ${ageLbl}</span>
            ${expired
              ? `<span style="font-size:10px;background:#ff980020;color:#e65100;border-radius:6px;padding:2px 6px">已过期</span>`
              : warn
              ? `<span style="font-size:10px;background:#ff980020;color:#e65100;border-radius:6px;padding:2px 6px">即将过期</span>`
              : ""}
            <md-outlined-button class="corr-dismiss-scene" data-scene="${this._esc(scene)}"
              style="--md-outlined-button-container-height:24px;font-size:11px;opacity:.7">
              全部忽略
            </md-outlined-button>
          </div>
          <div style="display:flex;flex-direction:column;gap:1px">`;

      items.forEach(a => {
        const name = this._hass.states[a.entity_id]?.attributes.friendly_name || a.entity_id;
        const stateColor = a.state === "on" ? "var(--sa-succ,#4caf50)" : "var(--sa-text-variant,#888)";
        html += `
          <div style="padding:10px 14px;display:flex;align-items:center;gap:12px;border-top:1px solid var(--sa-border)">
            <div style="width:28px;height:28px;border-radius:8px;background:var(--sa-primary-container);color:var(--sa-primary);display:flex;align-items:center;justify-content:center;flex-shrink:0">
              ${ICO[(a.entity_id.split(".")[0])] || ICO.device}
            </div>
            <div style="flex:1;min-width:0">
              <div class="body-m" style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(name)}</div>
              <div class="body-s" style="opacity:.6">设为 <b style="color:${stateColor}">${this._esc(String(a.state ?? ""))}</b>
                <span style="font-size:11px;opacity:.5;margin-left:4px">${this._esc(a.entity_id)}</span></div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0">
              ${expired ? "" : `
              <md-filled-tonal-button class="corr-correct-btn" data-eid="${this._esc(a.entity_id)}"
                style="--md-filled-tonal-button-container-height:28px;font-size:11px;background:var(--sa-error-container);color:var(--sa-error)">
                🎯 纠正
              </md-filled-tonal-button>`}
              <md-outlined-button class="corr-dismiss-btn" data-eid="${this._esc(a.entity_id)}"
                style="--md-outlined-button-container-height:28px;font-size:11px;opacity:.7">
                ✕ 忽略
              </md-outlined-button>
            </div>
          </div>`;
      });
      html += `</div></div>`;
    });

    box.innerHTML = html;

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(box, ".corr-correct-btn,.corr-dismiss-btn,.corr-dismiss-scene");
    }

    const _refreshCorrList = () => {
      delete this._wsLoading["ai_actions"];
      this._wsRefresh("smart_agent/get_ai_actions", "ai_actions", () => this._renderCorrections());
    };

    box.querySelectorAll(".corr-correct-btn").forEach(btn => {
      btn.onclick = async () => {
        const eid = btn.dataset.eid;
        if (!(await this._showConfirm(`确定纠正对 ${eid} 的操作吗？将撤销并记录学习。`))) return;
        btn.disabled = true;
        btn.textContent = "处理中...";
        try {
          const cur = this._hass.states[eid]?.state;
          const domain = eid.split(".")[0];
          const svc =
            domain === "cover"
              ? cur === "open"
                ? "close_cover"
                : "open_cover"
              : cur === "on"
              ? "turn_off"
              : "turn_on";
          await this._callService(domain, svc, { entity_id: eid });
          await new Promise(r => setTimeout(r, 500));
          await this._callService("smart_agent", "report_correction", { entity_id: eid });
          this._msg(`已纠正 ${eid}，AI 将学习此偏好`);
          _refreshCorrList();
        } catch (e) {
          this._msg("纠正失败: " + e.message);
          btn.disabled = false;
          btn.textContent = "🎯 纠正";
        }
      };
    });

    box.querySelectorAll(".corr-dismiss-btn").forEach(btn => {
      btn.onclick = async () => {
        const eid = btn.dataset.eid;
        btn.disabled = true;
        btn.textContent = "忽略中...";
        try {
          await this._callService("smart_agent", "dismiss_ai_action", { entity_id: eid });
          this._msg(`已忽略 ${eid}`);
          _refreshCorrList();
        } catch (e) {
          this._msg("操作失败: " + e.message);
          btn.disabled = false;
          btn.textContent = "✕ 忽略";
        }
      };
    });

    box.querySelectorAll(".corr-dismiss-scene").forEach(btn => {
      btn.onclick = async () => {
        const scene = btn.dataset.scene;
        const targets = visible.filter(a => (a.scene || "(未知场景)") === scene);
        btn.disabled = true;
        btn.textContent = "处理中...";
        try {
          for (const a of targets) {
            await this._callService("smart_agent", "dismiss_ai_action", {
              entity_id: a.entity_id,
            });
          }
          this._msg(`已忽略「${scene}」的全部操作`);
          _refreshCorrList();
        } catch (e) {
          this._msg("操作失败: " + e.message);
          btn.disabled = false;
          btn.textContent = "全部忽略";
        }
      };
    });
  },
};
