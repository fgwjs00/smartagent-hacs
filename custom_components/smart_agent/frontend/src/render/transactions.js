/**
 * SmartAgent Panel — AI 看板 + 执行记录 tab 渲染模块（5D-3）
 */

export const transactionsMethods = {
  /** 渲染 AI 看板：今日统计 + 房间推翻率 + 执行记录 */
  _renderTransactions() {
    this._renderDecisionStats();
    this._renderTxnList();
  },

  /** 5D-3: 今日决策统计卡片 + 房间推翻率 */
  async _renderDecisionStats() {
    const statsBox = this.shadowRoot.getElementById("decisionStatsContent");
    const roomBox = this.shadowRoot.getElementById("roomOverturnList");
    if (!statsBox || !roomBox) return;

    let data;
    try {
      data = await this._hass.connection.sendMessagePromise({
        type: "smart_agent/get_decision_stats",
      });
      if (!data || typeof data !== "object") throw new Error("返回数据为空");
    } catch (e) {
      const errMsg = this._esc(String(e.message || "未知错误"));
      statsBox.innerHTML = `<div style="opacity:.5;grid-column:1/-1;text-align:center">统计加载失败: ${errMsg}</div>`;
      roomBox.innerHTML = "";
      return;
    }

    const today_inferences  = Number(data.today_inferences  ?? 0);
    const today_corrections = Number(data.today_corrections ?? 0);
    const room_overturn_rates = Array.isArray(data.room_overturn_rates) ? data.room_overturn_rates : [];

    const overturnRate =
      today_inferences > 0
        ? Math.round((today_corrections / today_inferences) * 100)
        : 0;

    const statCardStyle =
      "background:var(--sa-card);border:1px solid var(--sa-border);" +
      "border-radius:var(--sa-shape-md);padding:12px;text-align:center";

    const overturnColor = overturnRate > 30
      ? "var(--sa-err)"
      : overturnRate > 15
        ? "var(--sa-state-warning)"
        : "var(--sa-succ)";

    statsBox.innerHTML = `
      <div style="${statCardStyle}">
        <div style="font-size:24px;font-weight:700;color:var(--sa-primary)">${today_inferences}</div>
        <div class="body-s" style="opacity:.6;margin-top:4px">今日决策</div>
      </div>
      <div style="${statCardStyle}">
        <div style="font-size:24px;font-weight:700;color:var(--sa-state-warning)">${today_corrections}</div>
        <div class="body-s" style="opacity:.6;margin-top:4px">今日纠正</div>
      </div>
      <div style="${statCardStyle}">
        <div style="font-size:24px;font-weight:700;color:${overturnColor}">
          ${overturnRate}%
        </div>
        <div class="body-s" style="opacity:.6;margin-top:4px">今日推翻率</div>
      </div>
    `;

    if (!room_overturn_rates.length) {
      roomBox.innerHTML = '<div style="opacity:.5;padding:8px 0;text-align:center">暂无房间统计</div>';
    } else {
      const validRates = room_overturn_rates.filter(r => typeof r.rate === "number" && !isNaN(r.rate));
      const maxRate = validRates.length ? Math.max(...validRates.map(r => r.rate), 1) : 1;
      roomBox.innerHTML = validRates
        .sort((a, b) => b.rate - a.rate)
        .map(r => {
          const barW = Math.round((r.rate / Math.max(maxRate, 1)) * 100);
          const color =
            r.rate > 30
              ? "var(--sa-err)"
              : r.rate > 15
              ? "var(--sa-state-warning)"
              : "var(--sa-succ)";
          const rateStr  = this._esc(String(r.rate));
          const corrStr  = this._esc(String(r.corrections ?? 0));
          const infStr   = this._esc(String(r.inferences ?? 0));
          return `
          <div style="display:flex;align-items:center;gap:10px;padding:4px 0">
            <div style="width:64px;font-size:12px;font-weight:500;flex-shrink:0">${this._esc(String(r.room ?? ""))}</div>
            <div style="flex:1;background:var(--sa-border,var(--divider-color));border-radius:4px;height:8px;overflow:hidden">
              <div style="width:${barW}%;background:${color};height:100%;border-radius:4px;transition:width .4s"></div>
            </div>
            <div style="width:80px;font-size:11px;opacity:.7;flex-shrink:0;text-align:right">
              ${rateStr}% · ${corrStr}/${infStr}次
            </div>
          </div>`;
        })
        .join("");
    }
  },

  /** 执行记录列表（原有内容） */
  _renderTxnList() {
    const list = this._wsGet("transactions", "transactions", []);
    const box = this.shadowRoot.getElementById("txnList");
    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(this.shadowRoot, ".txn-rollback");
    }
    if (!box) return;

    const STATUS_META = {
      success:     { label: "成功",    color: "var(--sa-succ, #4caf50)" },
      partial:     { label: "部分执行", color: "var(--sa-state-warning, #ff9800)" },
      blocked:     { label: "已拦截",  color: "var(--sa-secondary, #2196f3)" },
      failed:      { label: "失败",    color: "var(--sa-err, #f44336)" },
      pending:     { label: "执行中",  color: "var(--sa-text-variant, #9e9e9e)" },
      rolled_back: { label: "已回滚",  color: "var(--sa-tertiary, #9c27b0)" },
    };

    if (!list.length) {
      box.innerHTML = '<div style="opacity:.5;padding:16px 0;text-align:center">暂无执行记录</div>';
      return;
    }

    box.innerHTML = list
      .map(t => {
        const meta = STATUS_META[t.status] || { label: this._esc(String(t.status ?? "")), color: "#888" };
        const canRollback = ["success", "partial", "failed"].includes(t.status);
        const failBadge =
          t.failed_count > 0
            ? `<span style="color:var(--error-color,#f44336);font-size:11px"> · ${t.failed_count}失败</span>`
            : "";
        const blockedBadge =
          t.blocked_count > 0
            ? `<span style="color:var(--info-color,#2196f3);font-size:11px"> · ${t.blocked_count}拦截</span>`
            : "";
        return `
        <div style="background:var(--sa-card,var(--card-background-color));border:1px solid var(--sa-border,var(--divider-color));
                    border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:6px">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px">
            <div style="display:flex;align-items:center;gap:8px">
              <span style="background:${meta.color};color:#fff;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600">
                ${meta.label}
              </span>
              <span class="body-s" style="opacity:.6">${this._esc(t.time || "")}</span>
            </div>
            <div style="display:flex;gap:6px">
              ${canRollback ? `<md-outlined-button class="txn-rollback" data-id="${t.id}"
                  style="--md-outlined-button-container-height:28px;font-size:11px">⏪ 回滚</md-outlined-button>` : ""}
            </div>
          </div>
          <div style="font-size:13px;font-weight:500;color:var(--primary-text-color)">${this._esc(t.scene_desc || "(无场景描述)")}</div>
          <div class="body-s" style="opacity:.6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${this._esc(t.trigger_summary || "")}
          </div>
          <div style="display:flex;gap:12px;font-size:11px;opacity:.7">
            <span>动作 ${t.action_count || 0}</span>
            <span style="color:${meta.color}">执行 ${t.dispatched_count || 0}</span>
            ${failBadge}${blockedBadge}
            <span style="opacity:.5">置信度 ${t.confidence || 0}%</span>
            <span style="opacity:.5">#${t.id}</span>
          </div>
        </div>`;
      })
      .join("");

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(box, ".txn-rollback");
    }

    box.querySelectorAll(".txn-rollback").forEach(b => {
      b.onclick = async () => {
        const id = parseInt(b.dataset.id);
        if (!(await this._showConfirm(`确定回滚事务 #${id}？将把相关设备恢复到执行前的状态。`))) return;
        b.disabled = true;
        b.textContent = "回滚中…";
        try {
          await this._callService("smart_agent", "rollback_transaction", { transaction_id: id });
          this._msg(`事务 #${id} 回滚指令已发送`);
          this._wsRefresh("smart_agent/get_transactions", "transactions", () =>
            this._renderTransactions()
          );
        } catch (e) {
          this._msg("回滚失败: " + e.message);
          b.disabled = false;
          b.textContent = "⏪ 回滚";
        }
      };
    });
  },
};
