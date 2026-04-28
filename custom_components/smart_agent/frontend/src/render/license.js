/**
 * SmartAgent Panel — License 管理页
 */

export const licenseMethods = {
  _renderLicensePage() {
    const view = this.shadowRoot.getElementById("view-license");
    if (!view) return;
    const cfg = this._cfg?.attributes || {};
    const lic = cfg.license || {};

    const tierColors = { free: "#888", basic: "#2196f3", pro: "#4caf50", business: "#ff9800" };
    const tierColor = tierColors[lic.tier] || "#888";
    const progressPct = lic.daily_limit > 0
      ? Math.min(100, Math.round((lic.daily_used / lic.daily_limit) * 100))
      : 0;
    const progressColor = progressPct >= 90 ? "var(--sa-err)" : progressPct >= 70 ? "#ff9800" : "var(--sa-succ)";

    view.innerHTML = `
      <div class="main">
        <div>
          <div class="title-l">License 管理</div>
          <div class="body-s" style="margin-top:4px;opacity:.7">
            管理 SmartAgent 授权，查看套餐信息和每日配额使用情况
          </div>
        </div>

        <!-- 当前状态 -->
        <div class="card">
          <div class="card-title">当前授权状态</div>
          <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px">
            <div style="font-size:28px;font-weight:700;color:${tierColor}">
              ${this._esc(lic.tier_label || "免费版")}
            </div>
            ${lic.valid
              ? `<span style="color:var(--sa-succ);font-weight:600">✅ 已激活</span>`
              : lic.has_key
                ? `<span style="color:var(--sa-err);font-weight:600">❌ 验证失败</span>`
                : `<span style="opacity:.5">⚪ 未激活</span>`}
            ${lic.expires ? `<span class="body-s" style="opacity:.6">到期：${this._esc(String(lic.expires))}</span>` : ""}
          </div>

          <!-- 配额进度 -->
          <div style="margin-bottom:16px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
              <span class="label-s">今日 AI 推理配额</span>
              <span class="body-s">
                ${lic.daily_limit === -1
                  ? `已用 ${lic.daily_used || 0} 次（无限制）`
                  : `${lic.daily_used || 0} / ${lic.daily_limit || 0} 次`}
              </span>
            </div>
            ${lic.daily_limit > 0 ? `
              <div style="height:8px;background:var(--sa-border);border-radius:4px;overflow:hidden">
                <div style="height:100%;width:${progressPct}%;background:${progressColor};
                  border-radius:4px;transition:width .3s"></div>
              </div>` : ""}
          </div>

          <!-- 重新验证 -->
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <md-filled-tonal-button id="licenseVerifyBtn">🔄 重新验证</md-filled-tonal-button>
            <md-outlined-button id="licenseHelpBtn">如何获取 License Key？</md-outlined-button>
          </div>
        </div>

        <!-- 套餐对比 -->
        <div class="card">
          <div class="card-title">套餐说明</div>
          <div style="overflow-x:auto">
            <table style="width:100%;border-collapse:collapse;font-size:13px">
              <thead>
                <tr style="background:var(--sa-primary-container)">
                  <th style="padding:8px 12px;text-align:left;font-weight:600">套餐</th>
                  <th style="padding:8px 12px;text-align:center;font-weight:600">每日配额</th>
                  <th style="padding:8px 12px;text-align:center;font-weight:600">AI 场景</th>
                  <th style="padding:8px 12px;text-align:center;font-weight:600">数据备份</th>
                </tr>
              </thead>
              <tbody>
                ${[
                  { tier: "免费版",   quota: "30 次",  scene: "✅", backup: "❌" },
                  { tier: "基础版",   quota: "200 次", scene: "✅", backup: "✅" },
                  { tier: "专业版",   quota: "无限制", scene: "✅", backup: "✅" },
                  { tier: "商业版",   quota: "无限制", scene: "✅", backup: "✅" },
                ].map((r, i) => `
                  <tr style="border-bottom:1px solid var(--sa-border);
                    ${i % 2 === 0 ? "background:var(--sa-bg)" : ""}">
                    <td style="padding:8px 12px;font-weight:500">${r.tier}</td>
                    <td style="padding:8px 12px;text-align:center">${r.quota}</td>
                    <td style="padding:8px 12px;text-align:center">${r.scene}</td>
                    <td style="padding:8px 12px;text-align:center">${r.backup}</td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
        </div>

        <!-- 填写说明 -->
        ${!lic.has_key ? `
        <div class="card" style="border:1px solid var(--sa-primary);background:var(--sa-primary-container)">
          <div class="card-title" style="color:var(--sa-primary)">💡 如何填写 License Key</div>
          <ol style="padding-left:20px;display:grid;gap:6px" class="body-m">
            <li>进入 <b>HA 设置 → 设备与服务</b></li>
            <li>找到 <b>AI SmartAgent</b> → 点击 <b>⋮ 三点菜单 → 选项</b></li>
            <li>滚动到底部，找到 <b>License Key</b> 字段填入</li>
            <li>点击提交保存，返回此页面点击「重新验证」</li>
          </ol>
        </div>` : ""}
      </div>`;

    const $ = id => view.querySelector("#" + id);

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(view, "#licenseVerifyBtn");
    }

    $("licenseVerifyBtn").onclick = async () => {
      const btn = $("licenseVerifyBtn");
      btn.disabled = true;
      btn.textContent = "验证中...";
      try {
        await this._callService("smart_agent", "verify_license", {});
        this._msg("License 验证完成，请刷新页面查看结果");
      } catch (e) {
        this._msg("验证失败: " + e.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "🔄 重新验证";
      }
    };

    $("licenseHelpBtn").onclick = () => {
      window.open("https://smartagent.ai/license", "_blank");
    };
  },
};
