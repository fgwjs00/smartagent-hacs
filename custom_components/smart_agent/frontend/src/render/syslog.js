/**
 * SmartAgent Panel — 系统日志渲染模块
 * 包含实时日志、历史日志加载、过滤和下载功能
 */

export const syslogMethods = {
  async _wsRefreshSysLog() {
    if (this._sysLogMode !== "live") return;
    if (this._sysLogRefreshing) return;
    this._sysLogRefreshing = true;
    const box = this.shadowRoot.getElementById("sysLogBox");
    try {
      const result = await this._hass.callWS({ type: "smart_agent/get_sys_log" });
      const html = result?.html || "";
      if (box) {
        if (html) {
          box.innerHTML = html;
          this._applySysLogFilter();
        } else {
          box.innerHTML = '<span style="opacity:.5">暂无系统日志（等待 HA 产生日志后自动显示）</span>';
        }
      }
    } catch (e) {
      if (box) box.innerHTML = `<span style="opacity:.5;color:var(--sa-error)">日志服务暂不可用：${this._esc(String(e.message || e))}</span>`;
    } finally {
      this._sysLogRefreshing = false;
    }
  },

  _applySysLogFilter() {
    const box = this.shadowRoot.getElementById("sysLogBox");
    if (!box) return;
    const rows = box.querySelectorAll(".sl-row");
    const f = this._sysLogFilter || "all";
    const kw = (this._sysLogKeyword || "").toLowerCase();
    let total = 0, errs = 0, warns = 0, infos = 0;

    rows.forEach(row => {
      const lvl = row.getAttribute("data-level") || "";
      const txt = row.textContent || "";
      const txtLow = txt.toLowerCase();

      let levelMatch = true;
      if (f === "INFO")    levelMatch = lvl === "sl-i";
      else if (f === "WARN")  levelMatch = lvl === "sl-w";
      else if (f === "ERROR") levelMatch = lvl === "sl-e";
      else if (f === "protect") levelMatch = txt.includes("保护") || txt.includes("冷却") || txt.includes("过滤");
      else if (f === "trigger") levelMatch = txt.includes("触发") || txt.includes("事件") || txt.includes("调度");

      const kwMatch = !kw || txtLow.includes(kw);
      const visible = levelMatch && kwMatch;
      row.style.display = visible ? "" : "none";

      if (visible) {
        total++;
        if (lvl === "sl-e") errs++;
        else if (lvl === "sl-w") warns++;
        else infos++;
      }
    });

    const el = id => this.shadowRoot.getElementById(id);
    const stTotal = el("statTotal");
    const stErr   = el("statErr");
    const stWarn  = el("statWarn");
    const stInfo  = el("statInfo");
    if (stTotal) stTotal.textContent = `共 ${total} 条`;
    if (stErr)  { stErr.textContent  = `● 错误 ${errs}`;   stErr.style.display  = errs  ? "" : "none"; }
    if (stWarn) { stWarn.textContent = `● 警告 ${warns}`;  stWarn.style.display = warns ? "" : "none"; }
    if (stInfo) { stInfo.textContent = `● 信息 ${infos}`;  stInfo.style.display = (infos && f !== "all") ? "" : "none"; }
  },

  _downloadSysLog() {
    const box = this.shadowRoot.getElementById("sysLogBox");
    if (!box) return;
    const rows = box.querySelectorAll(".sl-row");
    const lines = [];
    rows.forEach(r => lines.push(r.textContent));
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const dateSuffix = this._sysLogMode === "live"
      ? new Date().toISOString().slice(0, 10)
      : this._sysLogMode;
    a.download = `smart_agent_log_${dateSuffix}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  },

  async _loadLogDates() {
    const sel = this.shadowRoot.getElementById("sysLogDate");
    if (!sel) return;
    const refreshBtn = this.shadowRoot.getElementById("sysLogRefresh");
    if (refreshBtn) refreshBtn.disabled = true;
    try {
      let infos = null;
      try {
        infos = await this._hass.callApi("GET", "smart_agent/log_info");
      } catch (_) { infos = null; }

      const currentVal = sel.value;
      sel.innerHTML = '<md-select-option value="live"><div slot="headline">⚡ 实时流水</div></md-select-option>';

      if (Array.isArray(infos) && infos.length > 0) {
        infos.forEach(item => {
          const opt = document.createElement("md-select-option");
          opt.value = item.date;
          const sizeStr = item.size_kb > 0 ? ` · ${item.size_kb}KB` : "";
          const errStr  = item.errors > 0  ? ` ⚠${item.errors}` : "";
          const label = item.today
            ? `📅 ${item.date} 今天${sizeStr}${errStr}`
            : `${item.date}${sizeStr}${errStr}`;
          opt.innerHTML = `<div slot="headline">${label}</div>`;
          sel.appendChild(opt);
        });
        const info = this.shadowRoot.getElementById("sysLogInfo");
        if (info && this._sysLogMode === "live") {
          info.title = `共 ${infos.length} 天历史记录，最大保留 30 天`;
        }
      } else {
        const dates = await this._hass.callApi("GET", "smart_agent/log_dates");
        if (Array.isArray(dates)) {
          const today = new Date().toISOString().slice(0, 10);
          dates.forEach(d => {
            const opt = document.createElement("md-select-option");
            opt.value = d;
            opt.innerHTML = `<div slot="headline">${d === today ? `📅 ${d} 今天` : d}</div>`;
            sel.appendChild(opt);
          });
        }
      }

      if (currentVal && [...sel.options].some(o => o.value === currentVal)) {
        sel.value = currentVal;
      }
    } catch (e) { /* API not available yet */ }
    finally {
      if (refreshBtn) refreshBtn.disabled = false;
    }
  },

  async _onLogDateChange(val) {
    const box = this.shadowRoot.getElementById("sysLogBox");
    const info = this.shadowRoot.getElementById("sysLogInfo");
    if (val === "live") {
      this._sysLogMode = "live";
      if (info) info.textContent = "实时模式 — 自动刷新最近500条 | 历史文件保留7天";
      this._wsRefreshSysLog();
      return;
    }
    this._sysLogMode = val;
    if (info) info.textContent = `查看历史日志: ${val} — 加载中...`;
    if (box) box.innerHTML = '<span style="opacity:.5">加载中...</span>';
    try {
      const resp = await this._hass.callApi("GET", `smart_agent/log_content?date=${val}`);
      const content = resp?.content || "";
      if (!content) {
        if (box) box.innerHTML = '<span style="opacity:.5">该日期无日志记录</span>';
        if (info) info.textContent = `${val} — 无记录`;
        return;
      }
      const lines = content.split("\n").filter(l => l.trim());
      const lineCount = lines.length;
      if (info) info.textContent = `${val} — 共 ${lineCount} 条记录`;
      if (box) {
        const html = lines.reverse().map(line => {
          let cls = "sl-i";
          if (line.includes("[WARNING]") || line.includes("[WARN]")) cls = "sl-w";
          else if (line.includes("[ERROR]")) cls = "sl-e";
          const escaped = line.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
          return `<div class="sl-row ${cls}" data-level="${cls}">${escaped}</div>`;
        }).join("");
        box.innerHTML = html;
        this._applySysLogFilter();
      }
    } catch (e) {
      if (box) box.innerHTML = `<span style="color:var(--sa-err)">加载失败: ${this._esc(e.message || String(e))}</span>`;
      if (info) info.textContent = `${val} — 加载失败`;
    }
  },
};
