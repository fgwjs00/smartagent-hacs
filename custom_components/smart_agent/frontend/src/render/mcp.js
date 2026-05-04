/**
 * SmartAgent Panel — MCP 服务页
 */

export const mcpMethods = {
  _renderMcp() {
    const view = this.shadowRoot.getElementById("view-mcp");
    if (!view) return;
    const cfg = this._cfg?.attributes || {};
    const mcpEnabled = cfg.mcp_enabled !== false;
    const mcpUrl = `${window.location.origin}/api/v1/mcp`;

    view.innerHTML = `
      <div class="main">
        <div>
          <div class="title-l">MCP 服务</div>
          <div class="body-s" style="margin-top:4px;opacity:.7">
            Model Context Protocol — 允许 Claude Desktop、ESP32 等外部客户端调用 SmartAgent 工具
          </div>
        </div>

        <!-- 服务状态 -->
        <div class="card">
          <div class="card-title">服务状态</div>
          <div style="display:flex;align-items:center;justify-content:space-between;
            padding:12px 14px;border-radius:12px;background:var(--sa-primary-container);margin-bottom:16px">
            <div>
              <div class="title-s">启用 MCP 服务</div>
              <div class="body-s">开启后外部 AI 客户端可通过 HTTP 调用智能家居控制工具</div>
            </div>
            <md-switch id="mcpEnabledSwitch" ${mcpEnabled ? "selected" : ""}></md-switch>
          </div>
          <div style="display:grid;gap:8px">
            <div class="label-s">服务端点</div>
            <div style="display:flex;align-items:center;gap:8px;padding:10px 14px;
              background:var(--sa-bg);border-radius:8px;border:1px solid var(--sa-border)">
              <code style="flex:1;font-size:13px;font-family:monospace;word-break:break-all">
                ${mcpUrl}
              </code>
              <md-icon-button id="mcpCopyBtn" title="复制地址">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
              </md-icon-button>
            </div>
          </div>
        </div>

        <!-- 已注册工具列表 -->
        <div class="card">
          <div class="card-title">已注册工具</div>
          <div style="display:flex;flex-direction:column;gap:8px">
            ${[
              { name: "smart_control",     desc: "控制智能家居设备（开关灯、调节温度等）",   icon: "⚡" },
              { name: "smart_device_list", desc: "获取已托管设备列表及当前状态",             icon: "📋" },
              { name: "smart_query",       desc: "查询设备状态、房间信息、AI 决策历史",       icon: "🔍" },
              { name: "smart_scene",       desc: "触发 AI 场景或自定义场景",                icon: "🎬" },
            ].map(t => `
              <div style="display:flex;align-items:center;gap:12px;padding:12px 14px;
                border-radius:10px;border:1px solid var(--sa-border);background:var(--sa-bg)">
                <span style="font-size:22px">${t.icon}</span>
                <div style="flex:1">
                  <div style="font-size:13px;font-weight:600;font-family:monospace">${t.name}</div>
                  <div class="body-s">${t.desc}</div>
                </div>
                <span style="padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;
                  background:var(--sa-succ-container);color:var(--sa-succ)">已注册</span>
              </div>`).join("")}
          </div>
        </div>

        <!-- 接入说明 -->
        <div class="card">
          <div class="card-title">接入说明</div>
          <div style="display:grid;gap:12px">
            <div style="padding:12px 14px;background:var(--sa-primary-container);border-radius:10px">
              <div class="label-m" style="margin-bottom:6px">Claude Desktop 接入</div>
              <div class="body-s" style="margin-bottom:8px">在 claude_desktop_config.json 中添加：</div>
              <pre style="background:var(--sa-bg);border-radius:8px;padding:10px 12px;
                font-size:12px;overflow-x:auto;border:1px solid var(--sa-border)">{
  "mcpServers": {
    "smart_agent": {
      "url": "${mcpUrl}",
      "transport": "http"
    }
  }
}</pre>
            </div>
          </div>
        </div>
      </div>`;

    const $ = id => view.querySelector("#" + id);

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(view, "#mcpEnabledSwitch");
    }

    $("mcpCopyBtn").onclick = () => {
      navigator.clipboard?.writeText(mcpUrl).then(() => this._msg("地址已复制"));
    };

    $("mcpEnabledSwitch").addEventListener("change", async e => {
      try {
        await this._callService("smart_agent", "update_config", { mcp_enabled: e.target.selected });
        this._msg(e.target.selected ? "MCP 服务已启用" : "MCP 服务已禁用");
      } catch (err) { this._msg("设置失败: " + err.message); }
    });
  },
};
