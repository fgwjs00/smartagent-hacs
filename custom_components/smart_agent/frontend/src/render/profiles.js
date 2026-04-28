/**
 * SmartAgent Panel — 个性化画像 tab 渲染模块
 */

export const profilesMethods = {
  _renderProfs() {
    const allRules = this._wsGet("rules", "rules", []);
    const h = this.shadowRoot.getElementById("hList"),
      r = this.shadowRoot.getElementById("rList");

    if (!this._wsData["habits"]) {
      this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
      return;
    }
    const allHabits = this._wsGet("habits", "habits", []);
    const userRules = allRules.filter(i => !i.is_ai);

    h.innerHTML = this._drawList(allHabits, "habit");
    r.innerHTML = this._drawList(userRules, "rule");

    this.shadowRoot.querySelectorAll(".prof-lock").forEach(b => {
      b.onclick = async () => {
        try {
          await this._callService("smart_agent", "toggle_" + b.dataset.t + "_lock", {
            content: b.dataset.c,
          });
          this._msg(b.dataset.lk === "1" ? "配置已解锁" : "配置已锁定");
          delete this._wsData["rules"];
          delete this._wsData["habits"];
          await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
            await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
          });
        } catch (e) {
          this._msg("操作失败: " + e.message);
        }
      };
    });

    this.shadowRoot.querySelectorAll(".prof-del").forEach(b => {
      b.onclick = async () => {
        if (b.disabled) return;
        try {
          await this._callService("smart_agent", "delete_" + b.dataset.t, {
            content: b.dataset.c,
          });
          this._msg("已删除");
          delete this._wsData["rules"];
          delete this._wsData["habits"];
          await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
            await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
          });
        } catch (e) {
          this._msg("删除失败: " + e.message);
        }
      };
    });
  },

  _drawList(items, type) {
    if (!items.length) {
      return `<div class="body-s" style="padding:20px;text-align:center;opacity:.5">暂无条目</div>`;
    }
    const lockIco = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>`;
    const unlockIco = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6h1.9c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm0 12H6V10h12v10z"/></svg>`;
    const delIco = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>`;

    let html = `<div class="m3-list">`;
    items.forEach(i => {
      const ec = this._esc(i.content);
      const itemBg = i.locked ? "background:var(--sa-secondary-container);opacity:.8" : "";
      html += `
        <div class="m3-item" style="${itemBg}">
          <div class="m3-content">
            <div class="body-m" style="word-break:break-all">${ec}</div>
          </div>
          <div style="display:flex;gap:4px">
            <md-icon-button class="prof-lock" style="${i.locked ? 'background:var(--sa-secondary-container)' : ''}"
              data-t="${type}" data-c="${ec}" data-lk="${i.locked ? "1" : "0"}"
              title="${i.locked ? "解锁（允许 AI 自动修改）" : "锁定（防止 AI 反向操作）"}">
              ${i.locked ? lockIco : unlockIco}
            </md-icon-button>
            <md-icon-button class="prof-del" style="color:var(--sa-error)" data-t="${type}" data-c="${ec}"
              ${i.locked ? 'disabled' : ""} title="删除">
              ${delIco}
            </md-icon-button>
          </div>
        </div>`;
    });
    return html + `</div>`;
  },
};
