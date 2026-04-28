/**
 * SmartAgent Panel — 行为习惯 tab 渲染模块
 */
import { DOMAIN_LABELS } from "../constants.js";

export const habitsMethods = {
  _renderHabitPatterns() {
    const $ = id => this.shadowRoot.getElementById(id);
    const patterns = this._wsGet("behavior_patterns", "patterns", []);
    const statRow = $("habitStatRow");
    const tbl = $("habitPatTable");
    if (!tbl) return;

    const ICO = this._getIcons();

    const total = patterns.length;
    const active = patterns.filter(p => p.confidence >= 60).length;
    const avgConf = total
      ? Math.round(patterns.reduce((s, p) => s + p.confidence, 0) / total)
      : 0;
    const deviceCount = total ? new Set(patterns.map(p => p.entity_id)).size : 0;
    if (statRow) {
      statRow.innerHTML = [
        `<span class="hab-stat-chip">${ICO.schedule} ${total} 条规律</span>`,
        total ? `<span class="hab-stat-chip">${ICO.device} ${deviceCount} 个设备</span>` : "",
        total
          ? `<span class="hab-stat-chip" style="color:var(--sa-succ);border-color:rgba(20,108,46,.2);background:var(--sa-succ-bg)">${ICO.check} ${active} 条激活</span>`
          : "",
        total ? `<span class="hab-stat-chip">${ICO.gauge} 平均置信度 ${avgConf}%</span>` : "",
      ].join("");
    }

    if (!total) {
      const domFilterEl = $("habDomainFilter");
      if (domFilterEl) domFilterEl.innerHTML = "";
      tbl.innerHTML = `
        <div class="hab-empty">
          <div class="hab-empty-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="currentColor"><path d="M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z"/></svg>
          </div>
          <div class="hab-empty-title">暂无行为规律</div>
          <div class="hab-empty-desc">开启「静默学习模式」，记录一段时间的日常操作后，系统会自动分析并提取您的行为习惯规律。</div>
        </div>`;
      return;
    }

    const domains = [...new Set(patterns.map(p => (p.entity_id || "").split(".")[0]))].sort();
    const domFilterEl = $("habDomainFilter");
    if (domFilterEl) {
      const df = this._habDomainFilter || "all";
      domFilterEl.innerHTML = ["all", ...domains]
        .map(d => {
          const cnt =
            d === "all"
              ? total
              : patterns.filter(p => (p.entity_id || "").split(".")[0] === d).length;
          const lbl = d === "all" ? "全部" : (DOMAIN_LABELS[d] || this._esc(d));
          return `<md-filter-chip class="hab-df-btn" ${df === d ? "selected" : ""} data-d="${this._esc(d)}" label="${lbl} (${cnt})"></md-filter-chip>`;
        })
        .join("");
      domFilterEl.querySelectorAll(".hab-df-btn").forEach(b => {
        b.onclick = () => {
          this._habDomainFilter = b.dataset.d;
          this._renderHabitPatterns();
        };
      });
    }

    const search = (this._habSearch || "").toLowerCase().trim();
    const domFilt = this._habDomainFilter || "all";
    let filtered = patterns.filter(p => {
      if (domFilt !== "all" && (p.entity_id || "").split(".")[0] !== domFilt) return false;
      if (search) {
        const n = (p.name || p.entity_id || "").toLowerCase();
        const e = (p.entity_id || "").toLowerCase();
        if (!n.includes(search) && !e.includes(search)) return false;
      }
      return true;
    });

    const sortKey = this._habSort || "conf";
    if (sortKey === "conf") filtered.sort((a, b) => b.confidence - a.confidence);
    else if (sortKey === "time")
      filtered.sort((a, b) => (a.time_label || "").localeCompare(b.time_label || ""));
    else if (sortKey === "name")
      filtered.sort((a, b) =>
        (a.name || a.entity_id || "").localeCompare(b.name || b.entity_id || "")
      );

    if (!filtered.length) {
      tbl.innerHTML = `<div class="body-s" style="text-align:center;padding:32px;opacity:.5">无匹配结果，请调整搜索条件</div>`;
      return;
    }

    const ON_STATES = new Set(["on", "open", "playing", "heat", "cool", "auto", "fan_only"]);
    const confFillClass = c => (c >= 80 ? "hab-conf-high" : c >= 60 ? "hab-conf-mid" : "hab-conf-low");
    const confColor = c =>
      c >= 80 ? "var(--sa-succ)" : c >= 60 ? "var(--sa-primary)" : "var(--sa-text2)";
    const domainIcon = eid => {
      const d = (eid || "").split(".")[0];
      return ICO[d] || ICO.device;
    };
    const stateChipCls = s => (ON_STATES.has(s) ? "hab-chip hab-chip-on" : "hab-chip hab-chip-off");
    const stateIco = s => (ON_STATES.has(s) ? ICO.check : ICO.close);
    const confChip = p => `
      <span class="hab-conf-chip">
        <span class="hab-conf-track"><span class="hab-conf-fill ${confFillClass(p.confidence)}" style="width:${p.confidence}%"></span></span>
        <span class="hab-conf-val" style="color:${confColor(p.confidence)}">${p.confidence}%</span>
      </span>`;

    let h = "";

    if (this._habGrouped) {
      const groups = new Map();
      filtered.forEach(p => {
        const key = p.entity_id || "unknown";
        if (!groups.has(key)) {
          groups.set(key, { name: p.name || p.entity_id, eid: p.entity_id, items: [] });
        }
        groups.get(key).items.push(p);
      });

      h += `<div class="hab-list">`;
      for (const [, g] of groups) {
        h += `
          <div class="hab-dev-section">
            <div class="hab-dev-header">
              <div class="hab-dev-icon">${domainIcon(g.eid)}</div>
              <div style="flex:1;min-width:0">
                <div class="hab-dev-name">${this._esc(g.name)}</div>
                <div class="hab-dev-eid">${this._esc(g.eid)}</div>
              </div>
              <span class="hab-dev-badge">${g.items.length} 条规律</span>
            </div>
            <div class="hab-dev-rows">`;
        g.items.forEach(p => {
          const isActive = p.confidence >= 60;
          const st = (p.expected_state || "").toLowerCase();
          h += `
              <div class="hab-row-compact${isActive ? "" : " hab-inactive"}">
                <span class="${stateChipCls(st)}">${stateIco(st)} ${this._esc(p.state_cn || p.expected_state)}</span>
                <span class="hab-chip">${ICO.schedule} ${this._esc(p.time_label)}</span>
                <span class="hab-chip">${ICO.calendar} ${this._esc(p.weekday)}</span>
                ${confChip(p)}
                <md-icon-button class="hab-del-btn" data-id="${p.id}" title="删除此规律" style="color:var(--sa-text-variant)">${ICO.delete}</md-icon-button>
              </div>`;
        });
        h += `
            </div>
          </div>`;
      }
      h += `</div>`;
    } else {
      h += `<div class="hab-list">`;
      filtered.forEach(p => {
        const isActive = p.confidence >= 60;
        const st = (p.expected_state || "").toLowerCase();
        h += `
          <div class="hab-item${isActive ? "" : " hab-inactive"}">
            <div class="hab-icon-wrap ${ON_STATES.has(st) ? "state-on" : "state-off"}">${domainIcon(p.entity_id)}</div>
            <div class="hab-body">
              <div class="hab-name">${this._esc(p.name || p.entity_id)}</div>
              <div class="hab-eid">${this._esc(p.entity_id)}</div>
              <div class="hab-chips">
                <span class="${stateChipCls(st)}">${stateIco(st)} ${this._esc(p.state_cn || p.expected_state)}</span>
                <span class="hab-chip">${ICO.schedule} ${this._esc(p.time_label)}</span>
                <span class="hab-chip">${ICO.calendar} ${this._esc(p.weekday)}</span>
                ${confChip(p)}
              </div>
            </div>
            <md-icon-button class="hab-del-btn" data-id="${p.id}" title="删除此规律" style="color:var(--sa-text-variant)">${ICO.delete}</md-icon-button>
          </div>`;
      });
      h += `</div>`;
    }

    tbl.innerHTML = h;
    tbl.querySelectorAll(".hab-del-btn").forEach(b => {
      b.onclick = async () => {
        if (!(await this._showConfirm("确定删除此行为习惯规律？"))) return;
        try {
          await this._callService("smart_agent", "delete_behavior_pattern", {
            id: parseInt(b.dataset.id),
          });
          this._msg("已删除行为规律");
          await this._wsRefresh("smart_agent/get_behavior_patterns", "behavior_patterns", () =>
            this._renderHabitPatterns()
          );
        } catch (err) {
          this._msg("删除失败: " + String(err.message || err));
        }
      };
    });
  },
};
