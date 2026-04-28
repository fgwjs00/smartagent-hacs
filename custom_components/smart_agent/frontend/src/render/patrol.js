/**
 * SmartAgent Panel — 巡检配置页
 */

export const patrolMethods = {
  _renderPatrol() {
    const view = this.shadowRoot.getElementById("view-patrol");
    if (!view) return;

    // 读取当前配置
    const cfg = this._cfg?.attributes || {};
    const patrolEnabled = cfg.patrol_enabled !== false;
    const activeInterval = cfg.patrol_active_interval || 30;
    const nightInterval = cfg.patrol_night_interval || 60;
    const activeStart = cfg.patrol_active_start || "07:00";
    const activeEnd = cfg.patrol_active_end || "23:00";

    view.innerHTML = `
      <div class="main">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
          <div>
            <div class="title-l">巡检配置</div>
            <div class="body-s" style="margin-top:4px;opacity:.7">
              AI 定期主动扫描全屋设备状态，发现异常（如无人但灯亮）并自动处理
            </div>
          </div>
          <div style="display:flex;gap:8px">
            <md-outlined-button id="patrolTriggerBtn">▶ 立即巡检</md-outlined-button>
            <md-filled-button id="patrolSaveBtn">保存配置</md-filled-button>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px">

          <!-- 基础设置 -->
          <div class="card">
            <div class="card-title">基础设置</div>
            <div style="display:grid;gap:16px">

              <!-- 巡检总开关 -->
              <div style="display:flex;align-items:center;justify-content:space-between;
                padding:12px 14px;border-radius:12px;background:var(--sa-primary-container)">
                <div>
                  <div class="title-s">启用定期巡检</div>
                  <div class="body-s">AI 按设定间隔主动扫描全屋状态</div>
                </div>
                <md-switch id="patrolEnabled" ${patrolEnabled ? "selected" : ""}></md-switch>
              </div>

              <!-- 活跃时段间隔 -->
              <div>
                <div class="label-s">活跃时段巡检间隔</div>
                <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
                  <md-slider id="patrolActiveInterval" min="5" max="120" step="5" value="${activeInterval}" style="flex:1"></md-slider>
                  <span id="patrolActiveIntervalVal" style="min-width:56px;text-align:right;
                    font-weight:600;color:var(--sa-primary)">${activeInterval} 分钟</span>
                </div>
                <div class="body-s" style="margin-top:4px;opacity:.7">
                  有人在家时的巡检频率，建议 15-60 分钟
                </div>
              </div>

              <!-- 深夜时段间隔 -->
              <div>
                <div class="label-s">深夜时段巡检间隔</div>
                <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
                  <md-slider id="patrolNightInterval" min="30" max="240" step="30" value="${nightInterval}" style="flex:1"></md-slider>
                  <span id="patrolNightIntervalVal" style="min-width:56px;text-align:right;
                    font-weight:600;color:var(--sa-tertiary, #7D5260)">${nightInterval} 分钟</span>
                </div>
                <div class="body-s" style="margin-top:4px;opacity:.7">
                  无人/休眠时的巡检频率，建议 60-120 分钟
                </div>
              </div>
            </div>
          </div>

          <!-- 时段配置 -->
          <div class="card">
            <div class="card-title">活跃时段配置</div>
            <div style="display:grid;gap:16px">
              <div style="padding:12px;border-radius:10px;border:1px solid var(--sa-border)">
                <div class="label-m" style="margin-bottom:10px;color:var(--sa-primary)">
                  活跃时段（高频巡检）
                </div>
                <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
                  <div>
                    <div class="label-s">开始时间</div>
                    <md-outlined-text-field type="time" id="patrolActiveStart" value="${activeStart}" style="width:140px;margin-top:4px"></md-outlined-text-field>
                  </div>
                  <span style="opacity:.5;margin-top:16px">—</span>
                  <div>
                    <div class="label-s">结束时间</div>
                    <md-outlined-text-field type="time" id="patrolActiveEnd" value="${activeEnd}" style="width:140px;margin-top:4px"></md-outlined-text-field>
                  </div>
                </div>
                <div class="body-s" style="margin-top:8px;opacity:.7">
                  此时段外自动切换为深夜间隔
                </div>
              </div>

              <!-- 巡检功能开关 -->
              <div style="display:grid;gap:8px">
                <div class="label-s">巡检检查项</div>
                ${[
                  { id: "patrolCheckAbnormal", label: "异常检测", desc: "无人但灯亮/设备异常" },
                  { id: "patrolCheckEnergy",   label: "能耗巡检", desc: "统计设备开启时长" },
                  { id: "patrolCheckHabits",   label: "习惯分析", desc: "定期分析行为规律" },
                ].map(({ id, label, desc }) => `
                  <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:8px 12px;border-radius:8px;background:var(--sa-bg)">
                    <div>
                      <div style="font-size:13px;font-weight:500">${label}</div>
                      <div class="body-s">${desc}</div>
                    </div>
                    <md-switch id="${id}" selected></md-switch>
                  </div>`).join("")}
              </div>
            </div>
          </div>
        </div>

        <!-- 巡检状态 -->
        <div class="card">
          <div class="card-title">巡检状态</div>
          <div id="patrolStatus" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px">
            <div class="sys-card">
              <div class="sys-icon">🔍</div>
              <div class="sys-card-label">上次巡检</div>
              <div class="sys-val-row">
                <span class="sys-val-num" style="font-size:14px">${this._esc(cfg.last_patrol_time || "—")}</span>
              </div>
            </div>
            <div class="sys-card">
              <div class="sys-icon">📊</div>
              <div class="sys-card-label">今日巡检次数</div>
              <div class="sys-val-row">
                <span class="sys-val-num">${cfg.patrol_count_today || 0}</span>
                <span class="sys-val-unit">次</span>
              </div>
            </div>
            <div class="sys-card">
              <div class="sys-icon">⚠️</div>
              <div class="sys-card-label">今日发现异常</div>
              <div class="sys-val-row">
                <span class="sys-val-num" style="color:${(cfg.patrol_anomaly_today || 0) > 0 ? 'var(--sa-err)' : 'var(--sa-succ)'}">
                  ${cfg.patrol_anomaly_today || 0}
                </span>
                <span class="sys-val-unit">项</span>
              </div>
            </div>
          </div>
        </div>
      </div>`;

    // 事件绑定
    const $ = id => view.querySelector("#" + id);

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(view, "#patrolEnabled,#patrolActiveInterval,#patrolNightInterval,#patrolActiveStart,#patrolActiveEnd,#patrolCheckAbnormal,#patrolCheckEnergy,#patrolCheckHabits,#patrolTriggerBtn,#patrolSaveBtn");
    }

    // 滑块实时显示
    $("patrolActiveInterval").oninput = e => {
      $("patrolActiveIntervalVal").textContent = e.target.value + " 分钟";
    };
    $("patrolNightInterval").oninput = e => {
      $("patrolNightIntervalVal").textContent = e.target.value + " 分钟";
    };

    // 立即巡检
    $("patrolTriggerBtn").onclick = async () => {
      const btn = $("patrolTriggerBtn");
      btn.disabled = true;
      btn.textContent = "巡检中...";
      try {
        await this._callService("smart_agent", "trigger_patrol", {});
        this._msg("巡检指令已发送");
      } catch (e) {
        this._msg("触发失败: " + e.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "▶ 立即巡检";
      }
    };

    // 保存配置
    $("patrolSaveBtn").onclick = async () => {
      const data = {
        patrol_enabled:         $("patrolEnabled").selected,
        patrol_active_interval: parseInt($("patrolActiveInterval").value),
        patrol_night_interval:  parseInt($("patrolNightInterval").value),
        patrol_active_start:    $("patrolActiveStart").value,
        patrol_active_end:      $("patrolActiveEnd").value,
      };
      try {
        await this._callService("smart_agent", "update_config", data);
        this._msg("巡检配置已保存");
      } catch (e) {
        this._msg("保存失败: " + e.message);
      }
    };
  },
};
