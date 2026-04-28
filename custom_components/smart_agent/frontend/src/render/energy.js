/**
 * SmartAgent Panel — 能耗分析 tab 渲染模块
 */

export const energyMethods = {
  _renderEnergy() {
    const list = this._wsGet("energy_stats", "stats", []);
    const box = this.shadowRoot.getElementById("energyList");
    if (!box) return;

    if (!list.length) {
      box.innerHTML =
        '<div style="opacity:.5;padding:16px 0;text-align:center">暂无能耗数据（每天凌晨 3:00 自动分析一次，也可重启集成立即生成）</div>';
      return;
    }

    const maxOn = Math.max(...list.map(s => s.on_minutes), 1);

    box.innerHTML = list
      .map(s => {
        const name = s.entity_id.replace(/^[^.]+\./, "").replace(/_/g, " ");
        const onH = Math.floor(s.on_minutes / 60),
          onM = Math.round(s.on_minutes % 60);
        const wasteH = Math.floor(s.waste_minutes / 60),
          wasteM = Math.round(s.waste_minutes % 60);
        const onLabel = onH ? `${onH}h ${onM}m` : `${onM}m`;
        const wasteLabel =
          s.waste_minutes < 1 ? "无浪费" : wasteH ? `${wasteH}h ${wasteM}m` : `${wasteM}m`;
        const wasteRatio =
          s.on_minutes > 0 ? Math.round((s.waste_minutes / s.on_minutes) * 100) : 0;
        const barColor =
          wasteRatio > 50 ? "#f44336" : wasteRatio > 20 ? "#ff9800" : "var(--sa-primary,#6750a4)";
        const barWaste =
          s.on_minutes > 0 ? Math.round((s.waste_minutes / s.on_minutes) * 100) : 0;
        const barOn = Math.round((s.on_minutes / maxOn) * 100);

        return `
        <div style="background:var(--sa-card,var(--card-background-color));border:1px solid var(--sa-border,var(--divider-color));
                    border-radius:12px;padding:14px 16px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:4px">
            <div style="font-size:13px;font-weight:500">${this._esc(name)}</div>
            <div style="font-size:11px;opacity:.6">${this._esc(s.entity_id)}</div>
          </div>
          <div style="margin:8px 0 4px;display:flex;gap:16px;font-size:12px">
            <span>开启 <b>${onLabel}</b></span>
            <span style="color:${barColor}">空房间浪费 <b>${wasteLabel}</b>
              ${wasteRatio > 0 ? `<span style="opacity:.6">(${wasteRatio}%)</span>` : ""}
            </span>
            <span style="opacity:.5">开启 ${s.on_count} 次</span>
          </div>
          <div style="height:6px;border-radius:4px;background:var(--sa-border,#e0e0e0);overflow:hidden;margin-top:4px">
            <div style="height:100%;border-radius:4px;background:${barColor};
                        width:${barOn}%;transition:width .4s;display:flex;align-items:center">
              ${barWaste > 0 ? `<div style="height:100%;width:${barWaste}%;background:rgba(255,255,255,.4);border-radius:4px"></div>` : ""}
            </div>
          </div>
        </div>`;
      })
      .join("");
  },
};
