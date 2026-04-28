/**
 * SmartAgent Panel — 备份/恢复页
 */

export const backupMethods = {
  _renderBackup() {
    const view = this.shadowRoot.getElementById("view-backup");
    if (!view) return;
    const ICO = this._getIcons();

    view.innerHTML = `
      <div class="main">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
          <div>
            <div class="title-l">备份与恢复</div>
            <div class="body-s" style="margin-top:4px;opacity:.7">
              备份 SmartAgent 的设备配置、画像规则、行为习惯等数据，支持加密导出
            </div>
          </div>
          <md-filled-button id="backupCreateBtn">💾 立即备份</md-filled-button>
        </div>

        <!-- 创建备份面板 -->
        <div class="card" id="backupCreatePanel" style="display:none">
          <div class="card-title">创建新备份</div>
          <div style="display:grid;gap:16px">
            <div>
              <div class="label-s">备份级别</div>
              <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px" id="backupLevelGroup">
                ${[
                  { v: "full",   label: "完整备份",   desc: "配置 + 数据 + 习惯" },
                  { v: "config", label: "配置备份",   desc: "仅系统配置" },
                  { v: "data",   label: "数据备份",   desc: "设备 + 画像 + 规则" },
                ].map(({ v, label, desc }) => `
                  <label style="display:flex;align-items:center;gap:10px;padding:10px 16px;
                    border-radius:12px;border:2px solid var(--sa-border);cursor:pointer;
                    transition:.15s" data-level="${v}">
                    <input type="radio" name="backupLevel" value="${v}" ${v === "full" ? "checked" : ""}
                      style="display:none">
                    <div>
                      <div style="font-weight:600;font-size:14px">${label}</div>
                      <div class="body-s">${desc}</div>
                    </div>
                  </label>`).join("")}
              </div>
            </div>
            <md-outlined-text-field id="backupNote"
              placeholder="如：升级前备份"></md-outlined-text-field>
            <div style="display:flex;gap:8px;justify-content:flex-end">
              <md-outlined-button id="backupCancelBtn">取消</md-outlined-button>
              <md-filled-button id="backupConfirmBtn">开始备份</md-filled-button>
            </div>
          </div>
        </div>

        <!-- 备份列表 -->
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
            <div class="card-title" style="margin:0">备份列表</div>
            <md-outlined-button id="backupRefreshBtn"
              style="--md-outlined-button-container-height:32px;font-size:13px">
              刷新
            </md-outlined-button>
          </div>
          <div id="backupListArea">
            <div class="empty-state">
              <div class="empty-state-icon">📦</div>
              <div class="empty-state-title">加载中...</div>
            </div>
          </div>
        </div>

        <!-- 恢复确认 Dialog -->
        <md-dialog id="backupRestoreDialog">
          <div slot="headline">确认恢复备份</div>
          <div slot="content">
            <div class="body-m" style="margin-bottom:12px">
              即将恢复备份 <strong id="restoreTargetName"></strong>，此操作将覆盖当前所有配置和数据。
            </div>
            <div style="padding:10px 12px;background:var(--sa-err-container);border-radius:8px;
              color:var(--sa-err);font-size:13px">
              ⚠️ 恢复后系统将自动重启，当前未保存的更改将丢失。建议先创建一个新备份。
            </div>
          </div>
          <div slot="actions">
            <md-text-button id="restoreCancelBtn">取消</md-text-button>
            <md-filled-button id="restoreConfirmBtn"
              style="--md-filled-button-container-color:var(--sa-err)">
              确认恢复
            </md-filled-button>
          </div>
        </md-dialog>
      </div>`;

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(view, [
        "#backupCreateBtn",
        "#backupCancelBtn",
        "#backupConfirmBtn",
        "#restoreConfirmBtn",
        ".backup-restore-btn",
        ".backup-delete-btn"
      ].join(","));
    }
    this._bindBackupEvents(view);
    this._loadBackupList(view);
  },

  _bindBackupEvents(view) {
    const $ = id => view.querySelector("#" + id);

    // 备份级别选择样式
    view.querySelectorAll("[data-level]").forEach(label => {
      label.onclick = () => {
        view.querySelectorAll("[data-level]").forEach(l => {
          l.style.borderColor = "var(--sa-border)";
          l.style.background = "";
        });
        label.style.borderColor = "var(--sa-primary)";
        label.style.background = "var(--sa-primary-container)";
        label.querySelector("input").checked = true;
      };
    });
    // 默认选中 full
    const fullLabel = view.querySelector("[data-level='full']");
    if (fullLabel) {
      fullLabel.style.borderColor = "var(--sa-primary)";
      fullLabel.style.background = "var(--sa-primary-container)";
    }

    // 展开/收起创建面板
    $("backupCreateBtn").onclick = () => {
      const panel = $("backupCreatePanel");
      panel.style.display = panel.style.display === "none" ? "block" : "none";
    };
    $("backupCancelBtn").onclick = () => { $("backupCreatePanel").style.display = "none"; };

    // 创建备份
    $("backupConfirmBtn").onclick = async () => {
      const level = view.querySelector("input[name='backupLevel']:checked")?.value || "full";
      const note = $("backupNote")?.value?.trim() || "";
      const btn = $("backupConfirmBtn");
      btn.disabled = true;
      btn.textContent = "备份中...";
      try {
        await this._callService("smart_agent", "create_backup", { level, note });
        this._msg("备份创建成功");
        $("backupCreatePanel").style.display = "none";
        await this._loadBackupList(view);
      } catch (e) {
        this._msg("备份失败: " + e.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "开始备份";
      }
    };

    // 刷新列表
    $("backupRefreshBtn").onclick = () => this._loadBackupList(view);

    // 恢复确认 dialog
    const dlg = $("backupRestoreDialog");
    $("restoreCancelBtn").onclick = () => dlg.close();
    $("restoreConfirmBtn").onclick = async () => {
      const backupId = dlg.dataset.backupId;
      dlg.close();
      try {
        await this._callService("smart_agent", "restore_backup", { backup_id: backupId });
        this._msg("恢复指令已发送，系统即将重启");
      } catch (e) { this._msg("恢复失败: " + e.message); }
    };
  },

  async _loadBackupList(view) {
    const area = view.querySelector("#backupListArea");
    if (!area) return;
    area.innerHTML = `<div style="text-align:center;padding:32px">
      <md-circular-progress indeterminate></md-circular-progress>
      <div class="body-s" style="margin-top:8px">加载备份列表...</div>
    </div>`;
    try {
      const result = await this._hass.callWS({ type: "smart_agent/list_backups" });
      const backups = result?.backups || [];
      if (!backups.length) {
        area.innerHTML = `<div class="empty-state">
          <div class="empty-state-icon">📦</div>
          <div class="empty-state-title">暂无备份</div>
          <div class="empty-state-desc">点击「立即备份」创建第一个备份</div>
        </div>`;
        return;
      }
      const levelColors = { full: "var(--sa-primary)", config: "var(--sa-tertiary)", data: "var(--sa-succ)" };
      const levelLabels = { full: "完整", config: "配置", data: "数据" };
      area.innerHTML = `<div style="display:flex;flex-direction:column;gap:8px">
        ${backups.map(b => `
          <div style="display:flex;align-items:center;gap:12px;padding:14px 16px;
            border-radius:12px;border:1px solid var(--sa-border);background:var(--sa-bg)">
            <div style="width:44px;height:44px;border-radius:10px;flex-shrink:0;
              background:var(--sa-primary-container);
              display:flex;align-items:center;justify-content:center;font-size:22px">📦</div>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span class="title-s">${this._esc(b.note || "备份")}</span>
                <span style="padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;
                  background:var(--sa-primary-container);color:${levelColors[b.level] || "var(--sa-primary)"}">
                  ${levelLabels[b.level] || b.level}
                </span>
              </div>
              <div class="body-s" style="margin-top:2px;opacity:.7">
                ${this._esc(b.created_at || "")} · ${b.size_kb ? b.size_kb + " KB" : ""}
              </div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0">
              <md-outlined-button class="backup-restore-btn" data-id="${this._esc(b.id)}"
                data-note="${this._esc(b.note || b.id)}"
                style="--md-outlined-button-container-height:32px;font-size:12px">
                恢复
              </md-outlined-button>
              <md-icon-button class="backup-delete-btn" data-id="${this._esc(b.id)}" title="删除">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
              </md-icon-button>
            </div>
          </div>`).join("")}
      </div>`;

      // 恢复按钮
      area.querySelectorAll(".backup-restore-btn").forEach(btn => {
        btn.onclick = () => {
          const dlg = view.querySelector("#backupRestoreDialog");
          dlg.dataset.backupId = btn.dataset.id;
          view.querySelector("#restoreTargetName").textContent = btn.dataset.note;
          dlg.show();
        };
      });

      // 删除按钮
      area.querySelectorAll(".backup-delete-btn").forEach(btn => {
        btn.onclick = async () => {
          if (!(await this._showConfirm("确定删除此备份？"))) return;
          try {
            await this._callService("smart_agent", "delete_backup", { backup_id: btn.dataset.id });
            this._msg("备份已删除");
            await this._loadBackupList(view);
          } catch (e) { this._msg("删除失败: " + e.message); }
        };
      });
    } catch (e) {
      area.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">加载失败</div>
        <div class="empty-state-desc">${this._esc(e.message)}</div>
      </div>`;
    }
  },
};
