/**
 * SmartAgent Panel — 系统配置 tab 渲染模块
 * 包含配置表单渲染、区域角色映射 UI、配对功能、系统配置保存。
 * _updateBizStatus() 和 _applyBrand() 在 panel-core.js，通过 this.xxx() 调用。
 */

export const configMethods = {
  _renderConfig() {
    const $ = id => this.shadowRoot.getElementById(id);
    const ICO = this._getIcons();
    const cfg = this._cfg.attributes || {};
    const container = $("configArea");
    if (!container) return;

    container.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(350px, 1fr));gap:20px;padding-bottom:40px">

        <!-- 品牌与部署 -->
        <div class="card">
          <div class="card-title">🎨 品牌与部署配置</div>
          <div style="display:grid;gap:15px">
            <div style="background:var(--sa-surface-2);border-radius:10px;padding:12px;font-size:12px;opacity:.8;line-height:1.6">
              白标定制：修改面板显示名称、主题色和 Logo，适用于不同客户部署场景（如某某智慧家）。
            </div>

            <!-- Logo 预览 + 输入 -->
            <div style="display:flex;align-items:center;gap:12px">
              <div id="brandLogoPreview" style="
                width:52px;height:52px;border-radius:12px;
                background:var(--sa-primary-container);
                display:flex;align-items:center;justify-content:center;
                overflow:hidden;flex-shrink:0;border:1px solid var(--sa-border)">
                ${cfg.brand_logo_url
                  ? `<img src="${this._esc(cfg.brand_logo_url)}" style="width:100%;height:100%;object-fit:cover">`
                  : `<span style="font-size:24px">${ICO.bolt}</span>`}
              </div>
              <div style="flex:1">
                <div class="label-s">Logo 图片 URL</div>
                <md-outlined-text-field id="cfg_brand_logo"
                  value="${this._esc(cfg.brand_logo_url || '')}"
                  placeholder="https://example.com/logo.png"></md-outlined-text-field>
                <div class="body-s" style="opacity:.55;margin-top:3px">支持 PNG/SVG，建议 64×64 以上，留空使用默认图标</div>
              </div>
            </div>

            <div>
              <div class="label-s">品牌名称</div>
              <md-outlined-text-field id="cfg_brand_name"
                value="${this._esc(cfg.brand_name || 'SmartAgent')}"
                placeholder="SmartAgent"></md-outlined-text-field>
              <div class="body-s" style="opacity:.55;margin-top:3px">显示在面板标题栏、页脚和帮助页面</div>
            </div>

            <div>
              <div class="label-s">主题色</div>
              <div style="display:flex;align-items:center;gap:10px">
                <input id="cfg_brand_color" type="color"
                  value="${cfg.brand_primary_color || '#6750A4'}"
                  style="width:52px;height:40px;padding:2px 4px;cursor:pointer;border:1px solid var(--sa-border);border-radius:8px">
                <md-outlined-text-field id="cfg_brand_color_hex" style="flex:1"
                  value="${this._esc(cfg.brand_primary_color || '#6750A4')}"
                  placeholder="#6750A4" maxlength="7"></md-outlined-text-field>
              </div>
              <div class="body-s" style="opacity:.55;margin-top:3px">作用于按钮、选中状态、高亮元素</div>
            </div>

            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-s">部署点标识名</div>
              <md-outlined-text-field id="cfg_deploy_name"
                value="${this._esc(cfg.deploy_name || '')}"
                placeholder="如：演示展厅 / 主卧样板间"></md-outlined-text-field>
              <div class="body-s" style="opacity:.55;margin-top:3px">显示在面板标题栏括号内，便于区分多个部署点</div>
            </div>
          </div>
        </div>

        <!-- AI 核心引擎 -->
        <div class="card">
          <div class="card-title">${ICO.bolt} AI 核心引擎配置</div>
          <div style="display:grid;gap:15px">
            <div>
              <div class="label-s">推理引擎类型</div>
              <md-outlined-select id="cfg_engine">
                <md-select-option value="local" ${cfg.engine === 'local' ? 'selected' : ''}>本地 Ollama (推荐)</md-select-option>
                <md-select-option value="online" ${cfg.engine === 'online' ? 'selected' : ''}>云端 OpenAI 兼容 API</md-select-option>
              </md-outlined-select>
            </div>
            <div id="cfg_local_group" style="display:${cfg.engine === 'local' ? 'grid' : 'none'};gap:12px">
              <div>
                <div class="label-s">Ollama 服务地址</div>
                <md-outlined-text-field id="cfg_ollama_url" value="${this._esc(cfg.ollama_url || '')}" placeholder="http://127.0.0.1:11434"></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">Ollama 模型名称</div>
                <md-outlined-text-field id="cfg_ollama_model" value="${this._esc(cfg.ollama_model || '')}" placeholder="qwen3-smarthome"></md-outlined-text-field>
              </div>
            </div>
            <div id="cfg_online_group" style="display:${cfg.engine === 'online' ? 'grid' : 'none'};gap:12px">
              <div>
                <div class="label-s">API Base URL</div>
                <md-outlined-text-field id="cfg_online_base_url" value="${this._esc(cfg.online_base_url || '')}" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">API Key</div>
                <md-outlined-text-field id="cfg_online_api_key" type="password" value="${this._esc(cfg.online_api_key || '')}" placeholder="sk-xxxx..."></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">模型名称</div>
                <md-outlined-text-field id="cfg_online_model" value="${this._esc(cfg.online_model || '')}" placeholder="qwen-turbo"></md-outlined-text-field>
              </div>
            </div>
          </div>
        </div>

        <!-- 多媒体与语音 -->
        <div class="card">
          <div class="card-title">${ICO.mic} 多媒体与语音配置</div>
          <div style="display:grid;gap:15px">
            <div>
              <div class="label-s">TTS 服务 (domain.service)</div>
              <md-outlined-text-field id="cfg_tts_service" value="${this._esc(cfg.tts_service || '')}" placeholder="tts.google_translate_say"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">目标媒体播放器</div>
              <md-outlined-text-field id="cfg_tts_target" value="${this._esc(cfg.tts_target || '')}" placeholder="media_player.bedroom_speaker"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">TTS 播报级别</div>
              <md-outlined-select id="cfg_tts_level">
                <md-select-option value="0" ${cfg.tts_level === 0 ? 'selected' : ''}>关闭</md-select-option>
                <md-select-option value="1" ${cfg.tts_level === 1 ? 'selected' : ''}>仅 AI 回复</md-select-option>
                <md-select-option value="2" ${cfg.tts_level === 2 ? 'selected' : ''}>回复 + 执行摘要</md-select-option>
                <md-select-option value="3" ${cfg.tts_level === 3 ? 'selected' : ''}>全部 (含系统提示)</md-select-option>
              </md-outlined-select>
            </div>
          </div>
        </div>

        <!-- 视觉感知 -->
        <div class="card">
          <div class="card-title">${ICO.vision} 视觉感知配置 (LLMVision)</div>
          <div style="display:grid;gap:15px">
            <div>
              <div class="label-s">LLMVision 引擎</div>
              <md-outlined-select id="cfg_vision_engine">
                <md-select-option value="local" ${cfg.vision_engine === 'local' ? 'selected' : ''}>本地 (Ollama/Llava)</md-select-option>
                <md-select-option value="online" ${cfg.vision_engine === 'online' ? 'selected' : ''}>在线 (Qwen-VL/Gemini)</md-select-option>
              </md-outlined-select>
            </div>
            <div>
              <div class="label-s">视觉模型名称</div>
              <md-outlined-text-field id="cfg_vision_model" value="${this._esc(cfg.vision_model || '')}" placeholder="qwen-vl-max"></md-outlined-text-field>
            </div>
            <div class="body-s" style="opacity:.6">视觉增强功能需要较强的 AI 处理能力。建议在线引擎使用 qwen-vl-max 或 gemini-1.5-pro。</div>
          </div>
        </div>

        <!-- 展厅运营配置 -->
        <div class="card" id="showroomConfigCard">
          <div class="card-title">🏬 展厅运营配置</div>
          <div style="display:grid;gap:15px">
            <div style="background:var(--sa-surface-2);border-radius:10px;padding:12px;font-size:12px;opacity:.8;line-height:1.6">
              🏬 展厅模式专属：配置营业时间后，AI 在开店前/打烊后自动调整策略（减少干预），营业中积极展示。切换至「展厅模式」后生效。
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div>
                <div class="label-s">营业开始时间</div>
                <md-outlined-text-field id="cfg_biz_start" type="time"
                  value="${cfg.showroom_biz_start || '09:00'}"></md-outlined-text-field>
                <div class="body-s" style="opacity:.55;margin-top:4px">AI 开始主动展示的时间</div>
              </div>
              <div>
                <div class="label-s">营业结束时间</div>
                <md-outlined-text-field id="cfg_biz_end" type="time"
                  value="${cfg.showroom_biz_end || '21:00'}"></md-outlined-text-field>
                <div class="body-s" style="opacity:.55;margin-top:4px">AI 进入节能待机的时间</div>
              </div>
            </div>
            <!-- ── 三区域角色映射（v4.11.0）────────────────────────────── -->
            <div style="border:1px solid var(--sa-border);border-radius:12px;padding:14px;background:var(--sa-surface-2)">
              <div class="label-m" style="margin-bottom:6px">区域角色划分</div>
              <div class="body-s" style="opacity:.7;margin-bottom:12px;line-height:1.6">
                展厅模式下每个区域可独立设置角色：<br>
                🏬 <b>展示区</b>：营业时间保持灯光，无人也不关灯（如展厅主陈列区）<br>
                ✨ <b>体验区</b>：有人演示开灯，无人关灯节能（如客厅、餐厅体验区）<br>
                💼 <b>工作区</b>：完全不受展厅规则影响，按家庭模式独立运行（如办公室）
              </div>
              <div id="zoneRoleList" style="display:flex;flex-direction:column;gap:8px"></div>
              <div style="display:flex;gap:8px;margin-top:10px">
                <md-filled-tonal-button id="addZoneRoleBtn" style="flex:1;--md-filled-tonal-button-container-height:32px;font-size:13px">+ 添加区域角色</md-filled-tonal-button>
                <md-filled-tonal-button id="clearZoneRoleBtn" style="opacity:.6;--md-filled-tonal-button-container-height:32px;font-size:13px" title="清空所有区域角色配置">清空</md-filled-tonal-button>
              </div>
              <div class="body-s" style="opacity:.5;margin-top:6px">未列出的区域默认为「体验区」角色 · 点击清空可重置所有配置</div>
            </div>

            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div style="display:flex;align-items:center;justify-content:space-between">
                <div>
                  <div class="label-m">当前营业状态</div>
                  <div class="body-s" id="bizStatusTip">加载中…</div>
                </div>
                <div id="bizStatusBadge" style="padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 联网工具与高级 -->
        <div class="card">
          <div class="card-title">${ICO.expand} 联网工具与高级设置</div>
          <div style="display:grid;gap:15px">
            <div>
              <div class="label-s">和风天气 API Key</div>
              <md-outlined-text-field id="cfg_qweather_api_key" type="password" value="${this._esc(cfg.qweather_api_key || '')}" placeholder="用于获取精准天气预报"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">SearXNG URL</div>
              <md-outlined-text-field id="cfg_searxng_url" value="${this._esc(cfg.searxng_url || '')}" placeholder="用于 AI 联网搜索"></md-outlined-text-field>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between">
              <div>
                <div class="label-m">备用在线模型</div>
                <div class="body-s">仅本地引擎失败且显式开启时调用，默认关闭</div>
              </div>
              <md-switch id="cfg_cloud_fallback" ${cfg.cloud_fallback ? 'selected' : ''}></md-switch>
            </div>
            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-s">设备冷却时间 (秒)</div>
              <md-outlined-text-field id="cfg_cooldown" type="number" value="${cfg.cooldown || 60}"></md-outlined-text-field>
            </div>
            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-m">${ICO.calendar} 日志保留天数</div>
              <div class="body-s" style="margin:4px 0 8px">文件日志每天零点轮转，超期自动删除（最小 3 天，最大 90 天）</div>
              <md-outlined-text-field id="cfg_log_retention" type="number" min="3" max="90" value="${cfg.log_retention_days || 30}"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">License Key</div>
              <md-outlined-text-field id="cfg_license_key" type="password" value="${this._esc(cfg.license_key || '')}" placeholder="企业版/商业授权码"></md-outlined-text-field>
            </div>
          </div>
        </div>

        <!-- 中控屏极速配对 -->
        <div class="card">
          <div class="card-title">📱 中控屏配对</div>
          <div style="display:grid;gap:12px">
            <div style="background:var(--sa-surface-2);border-radius:10px;padding:12px;font-size:12px;opacity:.8;line-height:1.6">
              首次使用中控屏时，点击"开启配对"，然后在平板浏览器打开下方地址，60 秒内将自动完成连接。Token 长期有效，保存后无需重复配对。
            </div>
            <div>
              <div class="label-s">中控屏访问地址</div>
              <div style="display:flex;align-items:center;gap:8px;margin-top:4px">
                <code id="pairUrl" style="flex:1;font-size:12px;background:var(--sa-surface-2);padding:8px 10px;border-radius:8px;word-break:break-all;user-select:all;line-height:1.5"></code>
                <md-outlined-button id="pairCopyBtn" style="white-space:nowrap;flex-shrink:0;--md-outlined-button-container-height:32px;font-size:13px">复制</md-outlined-button>
              </div>
            </div>
            <div id="pairStatus" style="display:none;text-align:center;padding:16px;background:var(--sa-primary-container);border-radius:12px;border:1px solid var(--sa-primary)">
              <div style="font-size:36px;font-weight:700;color:var(--sa-primary);letter-spacing:2px" id="pairCountdown">60</div>
              <div style="font-size:13px;color:var(--sa-primary);margin-top:4px;opacity:.85">秒内请在平板上打开上方地址，将自动完成配对</div>
            </div>
            <md-filled-button id="pairBtn">📱 开启极速配对（60 秒）</md-filled-button>
          </div>
        </div>

      </div>

      <!-- ── 传感器配置（全宽，独立于网格）──────────────────────────────── -->
      <div class="card" style="margin-top:0;grid-column:1/-1" id="sensorConfigCard">
        <div class="card-title">🔍 传感器配置</div>

        <!-- 子 tab 切换 -->
        <div style="display:flex;gap:0;border-bottom:1px solid var(--sa-border);margin-bottom:16px">
          <md-filled-tonal-button id="sensorTabType" style="
            border-radius:8px 8px 0 0;--md-filled-tonal-button-container-height:32px;font-size:13px;
            background:var(--sa-primary-container);color:var(--sa-primary);font-weight:700">
            传感器类型
          </md-filled-tonal-button>
          <md-filled-tonal-button id="sensorTabFusion" style="
            border-radius:8px 8px 0 0;--md-filled-tonal-button-container-height:32px;font-size:13px;
            background:transparent;color:var(--sa-text-variant)">
            融合域（父级区域）
          </md-filled-tonal-button>
        </div>

        <!-- 传感器类型面板 -->
        <div id="sensorPanelType">
          <div class="body-s" style="opacity:.7;margin-bottom:12px;line-height:1.6">
            从 HA 实时读取所有存在类传感器，设置类型后影响系统判断精度：<br>
            🟡 <b>PIR 红外</b>：静止时无法检测，离开信号不可信，不触发关灯推理<br>
            🔵 <b>mmWave 毫米波</b>：静止检测可靠，30s 确认无人后触发关灯<br>
            📷 <b>Frigate 摄像头</b>：覆盖有死角，自动延长至 90-180s 离开确认
          </div>
          <div id="sensorTypeLoading" class="body-s" style="opacity:.5;padding:20px 0;text-align:center">正在从 HA 加载传感器…</div>
          <div id="sensorTypeList" style="display:flex;flex-direction:column;gap:6px"></div>
        </div>

        <!-- 融合域面板 -->
        <div id="sensorPanelFusion" style="display:none">
          <div class="body-s" style="opacity:.7;margin-bottom:12px;line-height:1.6">
            融合域（父级区域）：将多个传感器合并为一个逻辑区域，任一成员有人即视为有人。<br>
            适用场景：一个大开间被多个传感器覆盖，避免单个子区无人就关全场的灯。
          </div>
          <div id="fusionScopeList" style="display:flex;flex-direction:column;gap:10px;margin-bottom:12px"></div>
          <md-filled-tonal-button id="addFusionScopeBtn" style="--md-filled-tonal-button-container-height:32px;font-size:13px">+ 添加融合域</md-filled-tonal-button>
        </div>
      </div>

      <div style="position:fixed;bottom:20px;right:40px;display:flex;gap:12px;z-index:100">
        <md-outlined-button id="cfgTestTts" style="background:var(--sa-card)">${ICO.mic} 测试播报</md-outlined-button>
        <md-filled-button id="cfgSaveBtn" style="--md-filled-button-container-height:48px;padding:0 32px;box-shadow:var(--sa-shadow-lg)">保存全局配置</md-filled-button>
      </div>
    `;

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(container, [
        "#cfgSaveBtn",
        "#cfgTestTts",
        "#pairBtn",
        "#addZoneRoleBtn",
        "#clearZoneRoleBtn",
        "#addFusionScopeBtn"
      ].join(","));
    }

    // 绑定交互逻辑
    const engSel = $("cfg_engine");
    if (engSel) engSel.onchange = () => {
      $("cfg_local_group").style.display = engSel.value === 'local' ? 'grid' : 'none';
      $("cfg_online_group").style.display = engSel.value === 'online' ? 'grid' : 'none';
    };

    $("cfgSaveBtn").onclick = () => this._saveSystemConfig();
    $("cfgTestTts").onclick = () =>
      this._callService("smart_agent", "tts_test", {}).catch(e =>
        this._msg("TTS 测试失败: " + String(e.message || e))
      );

    // 中控屏配对卡片逻辑
    const screenUrl = `${location.origin}/smart_agent_screen/index.html`;
    const pairUrlEl = $("pairUrl");
    if (pairUrlEl) pairUrlEl.textContent = screenUrl;

    const pairCopyBtn = $("pairCopyBtn");
    if (pairCopyBtn) {
      pairCopyBtn.onclick = () => {
        navigator.clipboard?.writeText(screenUrl).then(() => {
          pairCopyBtn.textContent = "✅ 已复制";
          setTimeout(() => { pairCopyBtn.textContent = "复制"; }, 2000);
        });
      };
    }

    const pairBtn = $("pairBtn");
    if (pairBtn) {
      pairBtn.onclick = () => this._startPairing();
    }

    // 更新营业状态徽章
    this._updateBizStatus();

    // ── 区域角色映射（v4.11.8）：从 hass.areas 同步初始化下拉 ──────────
    this._initZoneRoleUI(cfg);

    // ── 传感器配置（Phase 12.1）─────────────────────────────────────────
    this._initSensorConfigUI();

    // 颜色选择器与十六进制输入框双向同步
    const colorPicker = $("cfg_brand_color");
    const colorHex    = $("cfg_brand_color_hex");
    const logoInput   = $("cfg_brand_logo");
    const logoPreview = $("brandLogoPreview");
    const ICO2 = this._getIcons();
    if (colorPicker && colorHex) {
      colorPicker.oninput = () => { colorHex.value = colorPicker.value; };
      colorHex.oninput = () => {
        if (/^#[0-9A-Fa-f]{6}$/.test(colorHex.value)) colorPicker.value = colorHex.value;
      };
    }
    // Logo URL 实时预览
    if (logoInput && logoPreview) {
      logoInput.oninput = () => {
        const url = logoInput.value.trim();
        logoPreview.innerHTML = url
          ? `<img src="${this._esc(url)}" style="width:100%;height:100%;object-fit:cover">`
          : `<span style="font-size:24px">${ICO2.bolt}</span>`;
      };
    }
  }
,

  async _startPairing() {
    const $ = id => this.shadowRoot.getElementById(id);
    const pairBtn = $("pairBtn");
    const pairStatus = $("pairStatus");
    const pairCountdown = $("pairCountdown");

    if (!pairBtn || !pairStatus || !pairCountdown) return;

    pairBtn.disabled = true;
    pairBtn.textContent = "正在生成配对凭证...";

    try {
      if (this._isHaFallbackReadOnly()) {
        this._warnHaFallbackReadOnly();
        pairBtn.disabled = false;
        pairBtn.textContent = "📱 开启极速配对（60 秒）";
        return;
      }
      // 使用 HA 官方 callApi，自动处理认证，避免 fetch 的 JSON 解析问题
      const data = await this._hass.callApi("POST", "smart_agent/pair/create");
      if (!data || !data.ok) {
        const reason = data?.error || data?.message || JSON.stringify(data) || "未知错误";
        this._msg("❌ 配对失败：" + reason);
        pairBtn.disabled = false;
        pairBtn.textContent = "📱 开启极速配对（60 秒）";
        return;
      }

      // 显示倒计时
      pairStatus.style.display = "block";
      let remaining = 60;
      pairCountdown.textContent = remaining;
      pairBtn.textContent = "⏳ 等待平板连接...";

      const timer = setInterval(() => {
        remaining--;
        pairCountdown.textContent = remaining;
        if (remaining <= 0) {
          clearInterval(timer);
          pairStatus.style.display = "none";
          pairBtn.disabled = false;
          pairBtn.textContent = "📱 开启极速配对（60 秒）";
        }
      }, 1000);

      this._msg("✅ 配对已开启，请在 60 秒内用平板打开中控屏地址");
    } catch (err) {
      // HA callApi 可能抛出含 statusCode/body 的对象，而非标准 Error
      const errMsg = err?.message
        || err?.body?.message
        || err?.body?.error
        || (err?.statusCode ? `HTTP ${err.statusCode}` : null)
        || (typeof err === "string" ? err : null)
        || JSON.stringify(err)
        || "未知错误";
      this._msg("❌ 配对请求失败：" + errMsg);
      console.error("[SmartAgent] 配对失败详情:", err);
      pairBtn.disabled = false;
      pairBtn.textContent = "📱 开启极速配对（60 秒）";
    }
  }
,

  async _saveSystemConfig() {
    const $ = id => this.shadowRoot.getElementById(id);

    /**
     * 将 "HH:MM" 时间字符串转换为后端期望的整数分钟数。
     * @param {string} t - 时间字符串，如 "09:30"
     * @returns {number} 分钟数，如 570
     */
    const timeToMin = t => {
      if (!t) return null;
      const [h, m] = t.split(":").map(Number);
      return h * 60 + (m || 0);
    };

    const data = {
      engine: $("cfg_engine").value,
      ollama_url: $("cfg_ollama_url").value,
      ollama_model: $("cfg_ollama_model").value,
      online_base_url: $("cfg_online_base_url").value,
      online_model: $("cfg_online_model").value,
      tts_service: $("cfg_tts_service").value,
      tts_target: $("cfg_tts_target").value,
      tts_level: parseInt($("cfg_tts_level").value),
      vision_engine: $("cfg_vision_engine").value,
      vision_model: $("cfg_vision_model").value,
      searxng_url: $("cfg_searxng_url").value,
      cloud_fallback: $("cfg_engine").value === "local" && $("cfg_cloud_fallback").checked,
      cooldown: parseInt($("cfg_cooldown").value),
      log_retention_days: Math.max(3, Math.min(90, parseInt($("cfg_log_retention").value) || 30)),
      license_key: $("cfg_license_key").value,
    };

    const onlineApiKey = $("cfg_online_api_key").value.trim();
    const qweatherApiKey = $("cfg_qweather_api_key").value.trim();
    if (onlineApiKey && !onlineApiKey.includes("****")) data.online_api_key = onlineApiKey;
    if (qweatherApiKey && !qweatherApiKey.includes("****")) data.qweather_api_key = qweatherApiKey;

    // 品牌化配置
    const brandName  = $("cfg_brand_name");
    const brandColor = $("cfg_brand_color_hex");
    const brandLogo  = $("cfg_brand_logo");
    const deployName = $("cfg_deploy_name");
    if (brandName)  data.brand_name          = brandName.value.trim() || "SmartAgent";
    if (brandColor) data.brand_primary_color = brandColor.value.trim() || "#6750A4";
    if (brandLogo)  data.brand_logo_url      = brandLogo.value.trim();
    if (deployName) data.deploy_name         = deployName.value.trim();

    // 展厅营业时间
    const bizStart = $("cfg_biz_start");
    const bizEnd   = $("cfg_biz_end");
    if (bizStart) {
      const startMin = timeToMin(bizStart.value);
      const endMin   = timeToMin(bizEnd ? bizEnd.value : null);
      if (startMin !== null) data.showroom_biz_start = startMin;
      if (endMin   !== null) data.showroom_biz_end   = endMin;
    }

    // 区域角色映射：收集 #zoneRoleList 内所有有值的行（value 由下拉控制，只会是合法 area_name）
    const zoneMap = {};
    const zoneList = this.shadowRoot.getElementById("zoneRoleList");
    if (zoneList) {
      zoneList.querySelectorAll(".zone-role-row").forEach(row => {
        const areaVal = row.querySelector(".zone-area-select")?.value?.trim();
        const role    = row.querySelector(".zone-role-select")?.value;
        if (areaVal && role) zoneMap[areaVal] = role;
      });
    }
    data.showroom_zone_map = JSON.stringify(zoneMap);

    try {
      await this._callService("smart_agent", "update_config", data);
      this._msg("✅ 系统配置已保存并生效");
      this._updateBizStatus();
      // 立即应用品牌配置（无需等待 WS 状态刷新）
      if (data.brand_name || data.brand_primary_color) {
        this._applyBrand({
          brand_name: data.brand_name,
          brand_primary_color: data.brand_primary_color,
          brand_logo_url: data.brand_logo_url,
          deploy_name: data.deploy_name,
        });
      }
    } catch (err) {
      this._msg("❌ 保存失败: " + String(err.message || err));
    }
  }
,

  _initZoneRoleUI(cfg) {
    const list    = this.shadowRoot.getElementById("zoneRoleList");
    const addBtn  = this.shadowRoot.getElementById("addZoneRoleBtn");
    const clearBtn = this.shadowRoot.getElementById("clearZoneRoleBtn");
    if (!list || !addBtn) return;

    // ── 从 hass.areas 构建两张查找表 ──────────────────────────────────────
    // hass.areas 结构: { area_id: { area_id, name, ... } }
    const rawAreas = this._hass.areas || {};
    // area_name 集合（valid name set）
    const haAreaNames = new Set(Object.values(rawAreas).map(a => a.name));
    // area_id → area_name 映射表（用于迁移旧版数字 ID 存储）
    const idToName = {};
    Object.entries(rawAreas).forEach(([id, a]) => { idToName[id] = a.name; });

    // 按名称排序的区域列表，option value = area_name（与后端 get_zone_role 保持一致）
    const haAreas = Object.values(rawAreas)
      .sort((a, b) => a.name.localeCompare(b.name, "zh-CN"))
      .map(a => ({ id: a.name, label: a.name }));
    const haAreaIds = haAreaNames;  // 别名，保持其余代码不变

    const ROLE_OPTIONS = [
      { value: "display",    label: "🏬 展示区" },
      { value: "experience", label: "✨ 体验区" },
      { value: "work",       label: "💼 工作区" },
    ];

    // ── 获取当前所有已选区域（用于防重复）──────────────────────────────
    const getSelected = () => {
      const sel = [];
      list.querySelectorAll(".zone-area-select").forEach(s => { if (s.value) sel.push(s.value); });
      return sel;
    };

    // ── 刷新所有区域下拉：排除已被其他行选中的区域（防止重复选择同一区域）──
    const refreshAllAreaSelects = () => {
      const selected = getSelected();
      list.querySelectorAll(".zone-role-row").forEach(row => {
        const sel = row.querySelector(".zone-area-select");
        if (!sel) return;
        const cur = sel.value;
        sel.innerHTML = "";
        const ph = document.createElement("md-select-option");
        ph.value = ""; ph.innerHTML = '<div slot="headline">请选择区域…</div>';
        sel.appendChild(ph);
        haAreas.forEach(a => {
          if (selected.includes(a.id) && a.id !== cur) return;
          const o = document.createElement("md-select-option");
          o.value = a.id; o.innerHTML = `<div slot="headline">${a.label}</div>`;
          if (a.id === cur) o.selected = true;
          sel.appendChild(o);
        });
        if (!cur) sel.value = "";
      });
    };

    // ── 创建一行：区域下拉 + 角色下拉 + 删除按钮 ───────────────────────
    const createRow = (areaName = "", role = "experience") => {
      const row = document.createElement("div");
      row.className = "zone-role-row";
      row.style.cssText = "display:flex;align-items:center;gap:8px";

      // 区域下拉
      const areaSelect = document.createElement("md-outlined-select");
      areaSelect.className = "zone-area-select";
      areaSelect.style.cssText = "flex:1;min-width:0;height:36px;font-size:13px";
      const ph = document.createElement("md-select-option");
      ph.value = ""; ph.innerHTML = '<div slot="headline">请选择区域…</div>';
      areaSelect.appendChild(ph);
      // 若 areaName 不在当前 haAreas 中（hass.areas 未就绪或区域已删除），补一个已选项保留数据
      const nameInList = haAreas.some(a => a.id === areaName);
      if (areaName && !nameInList) {
        const kept = document.createElement("md-select-option");
        kept.value = areaName; kept.innerHTML = `<div slot="headline">${areaName}</div>`; kept.selected = true;
        areaSelect.appendChild(kept);
      }
      haAreas.forEach(a => {
        const o = document.createElement("md-select-option");
        o.value = a.id; o.innerHTML = `<div slot="headline">${a.label}</div>`;
        if (a.id === areaName) o.selected = true;
        areaSelect.appendChild(o);
      });
      areaSelect.onchange = () => refreshAllAreaSelects();

      // 角色下拉
      const roleSelect = document.createElement("md-outlined-select");
      roleSelect.className = "zone-role-select";
      roleSelect.style.cssText = "width:152px;flex-shrink:0;height:36px;font-size:13px";
      ROLE_OPTIONS.forEach(opt => {
        const o = document.createElement("md-select-option");
        o.value = opt.value; o.innerHTML = `<div slot="headline">${opt.label}</div>`;
        if (opt.value === role) o.selected = true;
        roleSelect.appendChild(o);
      });

      // 删除按钮
      const delBtn = document.createElement("md-icon-button");
      delBtn.className = "help-close";
      delBtn.title = "删除此区域";
      delBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
      delBtn.onclick = () => { row.remove(); refreshAllAreaSelects(); };

      row.appendChild(areaSelect);
      row.appendChild(roleSelect);
      row.appendChild(delBtn);
      return row;
    };

    // ── 解析已有配置，自动迁移旧版 area_id 键 → area_name 键 ───────────
    list.innerHTML = "";
    let rawZoneMap = {};
    try {
      const raw = cfg.showroom_zone_map;
      if (typeof raw === "string" && raw) {
        rawZoneMap = JSON.parse(raw);
      } else if (raw && typeof raw === "object") {
        rawZoneMap = raw;
      }
    } catch (_) {}

    // 迁移：将旧版 area_id 键（如 "68"）转换为 area_name（如 "展厅"），去重
    // 若 hass.areas 不可用（haAreaNames 为空）则直接透传，保证数据不丢失
    const areasAvailable = haAreaNames.size > 0;
    const zoneMap = {};
    Object.entries(rawZoneMap).forEach(([key, role]) => {
      if (!key || typeof key !== "string") return;
      if (!areasAvailable) {
        // hass.areas 未就绪：原样保留，让下拉渲染时再判断
        if (!zoneMap[key]) zoneMap[key] = role;
        return;
      }
      // 若 key 已是合法 area_name → 直接使用
      if (haAreaNames.has(key)) {
        if (!zoneMap[key]) zoneMap[key] = role;
        return;
      }
      // 若 key 是旧版 area_id → 转换为 area_name（一次性迁移）
      const migrated = idToName[key];
      if (migrated) {
        if (!zoneMap[migrated]) zoneMap[migrated] = role;
        return;
      }
      // 完全无法识别（既非 area_name 也非已知 area_id）→ 丢弃
    });

    Object.entries(zoneMap).forEach(([name, role]) => {
      list.appendChild(createRow(name, role));
    });

    // 初始刷新，排除已选项
    refreshAllAreaSelects();

    // 添加按钮：创建新空行
    addBtn.onclick = () => {
      list.appendChild(createRow());
      refreshAllAreaSelects();
      list.lastElementChild?.querySelector(".zone-area-select")?.focus();
    };

    // 清空按钮：移除所有已保存的区域角色配置
    if (clearBtn) {
      clearBtn.onclick = async () => {
        if (!(await this._showConfirm("确认清空所有区域角色配置？"))) return;
        list.innerHTML = "";
      };
    }
  },

  // ── 传感器配置 UI（Phase 12.1）────────────────────────────────────────────

  async _initSensorConfigUI() {
    const $ = id => this.shadowRoot.getElementById(id);

    // 子 tab 切换
    const tabType   = $("sensorTabType");
    const tabFusion = $("sensorTabFusion");
    const panelType   = $("sensorPanelType");
    const panelFusion = $("sensorPanelFusion");
    if (!tabType || !panelType) return;

    const _activateTab = (which) => {
      const isType = which === "type";
      tabType.style.background   = isType ? "var(--sa-primary-container)" : "transparent";
      tabType.style.color        = isType ? "var(--sa-primary)" : "var(--sa-text-variant)";
      tabType.style.fontWeight   = isType ? "700" : "400";
      tabFusion.style.background = isType ? "transparent" : "var(--sa-primary-container)";
      tabFusion.style.color      = isType ? "var(--sa-text-variant)" : "var(--sa-primary)";
      tabFusion.style.fontWeight = isType ? "400" : "700";
      panelType.style.display   = isType ? "" : "none";
      panelFusion.style.display = isType ? "none" : "";
    };
    tabType.onclick   = () => _activateTab("type");
    tabFusion.onclick = () => _activateTab("fusion");

    // 从 HA 加载传感器数据
    let sensorData = { sensors: [], fusion_config: [], rooms: [] };
    try {
      sensorData = await this._hass.connection.sendMessagePromise({
        type: "smart_agent/get_presence_sensors",
      });
    } catch (err) {
      const loading = $("sensorTypeLoading");
      if (loading) loading.textContent = "❌ 加载失败: " + String(err.message || err);
      return;
    }

    this._sensorData = sensorData;  // 缓存供融合域编辑器使用

    this._renderSensorTypeList(sensorData.sensors);
    this._renderFusionScopes(sensorData.fusion_config, sensorData.rooms, sensorData.sensors);
  },

  _renderSensorTypeList(sensors) {
    const $ = id => this.shadowRoot.getElementById(id);
    const loading = $("sensorTypeLoading");
    const list    = $("sensorTypeList");
    if (!list) return;
    if (loading) loading.style.display = "none";

    const SENSOR_TYPE_OPTIONS = [
      { value: "",       label: "自动识别" },
      { value: "pir",    label: "🟡 PIR 红外" },
      { value: "mmwave", label: "🔵 mmWave 毫米波" },
      { value: "frigate",label: "📷 Frigate 摄像头" },
    ];

    if (!sensors.length) {
      list.innerHTML = `<div class="body-s" style="opacity:.5;padding:16px 0;text-align:center">
        HA 中未找到存在类传感器（occupancy / presence / motion / person_occupancy）
      </div>`;
      return;
    }

    list.innerHTML = "";
    sensors.forEach(s => {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;background:var(--sa-card);border:1px solid var(--sa-border)";

      // 状态点
      const dot = s.state === "on" ? "#4caf50" : s.state === "off" ? "#9e9e9e" : "#ff9800";
      const inSaBadge = s.in_sa
        ? `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:var(--sa-primary-container);color:var(--sa-primary)">SA已注册</span>`
        : `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:rgba(0,0,0,.07);color:var(--sa-text-variant)">未注册</span>`;
      const fusionBadge = s.fusion_scope
        ? `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:var(--sa-secondary-container,rgba(100,180,255,.15));color:var(--sa-secondary,#1565c0)">
            融合域: ${this._esc(s.fusion_scope)}</span>`
        : "";

      // 传感器类型下拉
      const selId = `stype_${s.entity_id.replace(/\./g, "_")}`;
      const opts = SENSOR_TYPE_OPTIONS.map(o =>
        `<option value="${o.value}" ${s.sensor_type === o.value ? "selected" : ""}>${o.label}</option>`
      ).join("");

      row.innerHTML = `
        <span style="width:10px;height:10px;border-radius:50%;background:${dot};flex-shrink:0"></span>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${this._esc(s.name)}
            <span style="font-size:11px;font-weight:400;margin-left:6px;opacity:.6">${this._esc(s.room || "未分区")}</span>
          </div>
          <div style="font-size:11px;font-family:monospace;opacity:.5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${this._esc(s.entity_id)}
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:3px">${inSaBadge}${fusionBadge}</div>
        </div>
        <md-outlined-select id="${selId}" style="width:160px;flex-shrink:0;font-size:12px">
          ${opts}
        </md-outlined-select>
        <md-filled-tonal-button class="stype-save-btn" data-eid="${this._esc(s.entity_id)}" data-sel="${selId}"
          style="flex-shrink:0;--md-filled-tonal-button-container-height:32px;font-size:12px">保存</md-filled-tonal-button>
      `;
      list.appendChild(row);
    });

    // 事件委托：保存传感器类型
    list.addEventListener("click", async e => {
      const btn = e.target.closest(".stype-save-btn");
      if (!btn) return;
      if (this._isHaFallbackReadOnly()) {
        this._warnHaFallbackReadOnly();
        return;
      }
      const eid = btn.dataset.eid;
      const selEl = this.shadowRoot.getElementById(btn.dataset.sel);
      if (!selEl) return;
      const s_type = selEl.value;
      btn.disabled = true;
      btn.textContent = "…";
      try {
        await this._hass.connection.sendMessagePromise({
          type: "smart_agent/save_sensor_type",
          entity_id: eid,
          sensor_type: s_type,
        });
        btn.textContent = "✅";
        setTimeout(() => { btn.disabled = false; btn.textContent = "保存"; }, 1500);
      } catch (err) {
        btn.disabled = false;
        btn.textContent = "❌";
        this._msg("保存失败: " + String(err.message || err));
      }
    });
  },

  _renderFusionScopes(fusionConfig, rooms, sensors) {
    const $ = id => this.shadowRoot.getElementById(id);
    const scopeList = $("fusionScopeList");
    const addBtn = $("addFusionScopeBtn");
    if (!scopeList || !addBtn) return;

    const sensorMap = new Map((sensors || []).map(s => [s.entity_id, s]));
    const roomList = Array.isArray(rooms) ? [...rooms] : [];

    const normalizeMember = (member) => {
      if (typeof member === "string") {
        return {
          entity_id: member,
          can_enter_trigger: true,
          can_leave_evidence: true,
          priority: 50,
          confidence: 1,
        };
      }
      if (!member || typeof member !== "object") {
        return {
          entity_id: "",
          can_enter_trigger: true,
          can_leave_evidence: true,
          priority: 50,
          confidence: 1,
        };
      }
      return {
        entity_id: String(member.entity_id || ""),
        can_enter_trigger: member.can_enter_trigger !== false,
        can_leave_evidence: member.can_leave_evidence !== false,
        priority: Number.isFinite(Number(member.priority)) ? Number(member.priority) : 50,
        confidence: Number.isFinite(Number(member.confidence)) ? Number(member.confidence) : 1,
      };
    };

    const normalizeScope = (scope) => {
      const rawMembers = Array.isArray(scope?.members) ? scope.members : [];
      return {
        scope_id: String(scope?.scope_id || ""),
        name: String(scope?.name || ""),
        strategy: scope?.strategy === "vacant_and" ? "vacant_and" : "occupied_or",
        rooms: Array.isArray(scope?.rooms) ? scope.rooms.map(r => String(r)).filter(Boolean) : [],
        members: rawMembers.map(normalizeMember).filter(m => m.entity_id),
        enter_hold_secs: Number.isFinite(Number(scope?.enter_hold_secs)) ? Number(scope.enter_hold_secs) : 3,
        vacant_hold_secs: Number.isFinite(Number(scope?.vacant_hold_secs)) ? Number(scope.vacant_hold_secs) : 60,
      };
    };

    let scopes = Array.isArray(fusionConfig) ? fusionConfig.map(normalizeScope) : [];

    const _save = async () => {
      try {
        await this._callService("smart_agent", "update_config", {
          presence_fusion: JSON.stringify(scopes),
        });
        this._msg("✅ 融合域配置已保存");
      } catch (err) {
        this._msg("❌ 保存失败: " + String(err.message || err));
      }
    };

    const memberName = (m) => {
      const meta = sensorMap.get(m.entity_id);
      return meta?.name || m.entity_id.split(".").pop() || m.entity_id;
    };

    const memberSummary = (members) => {
      const total = members.length;
      const enterCount = members.filter(m => m.can_enter_trigger).length;
      const leaveCount = members.filter(m => m.can_leave_evidence).length;
      return `成员 ${total} · 入场触发 ${enterCount} · 离场证据 ${leaveCount}`;
    };

    const _render = () => {
      scopeList.innerHTML = "";
      if (!scopes.length) {
        scopeList.innerHTML = `<div class="body-s" style="opacity:.5;padding:16px 0;text-align:center;border:1px dashed var(--sa-border);border-radius:10px">
          暂无融合域配置，点击"添加融合域"新建
        </div>`;
        return;
      }

      scopes.forEach((sc, idx) => {
        const card = document.createElement("div");
        card.style.cssText = "border:1px solid var(--sa-border);border-radius:12px;overflow:hidden";
        const strategyLabel = sc.strategy === "vacant_and" ? "全员无人才关灯" : "任一有人即有人（推荐）";
        const roomsStr = sc.rooms.join("、");
        const topMembers = sc.members.slice(0, 3).map(m => {
          const enter = m.can_enter_trigger ? "入" : "";
          const leave = m.can_leave_evidence ? "离" : "";
          return `${memberName(m)}(${enter || "-"}/${leave || "-"})`;
        }).join("、");
        const extra = sc.members.length > 3 ? ` 等${sc.members.length}个` : "";

        card.innerHTML = `
          <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--sa-surface-2)">
            <div style="flex:1;min-width:0">
              <div style="font-weight:700;font-size:13px">${this._esc(sc.name || sc.scope_id || "未命名域")}</div>
              <div class="body-s" style="opacity:.6;margin-top:2px">
                主/邻房间: ${this._esc(roomsStr || "—")} &nbsp;·&nbsp;
                策略: ${this._esc(strategyLabel)}
              </div>
              <div class="body-s" style="opacity:.55;margin-top:2px">
                进入确认: ${sc.enter_hold_secs}s &nbsp;·&nbsp; 离开确认: ${sc.vacant_hold_secs}s &nbsp;·&nbsp; ${this._esc(memberSummary(sc.members))}
              </div>
              <div class="body-s" style="opacity:.5;margin-top:2px;word-break:break-all">
                ${this._esc(topMembers || "未配置成员")}${this._esc(extra)}
              </div>
            </div>
            <md-filled-tonal-button class="fusion-edit-btn" data-idx="${idx}" style="flex-shrink:0;--md-filled-tonal-button-container-height:32px;font-size:13px">编辑</md-filled-tonal-button>
            <md-filled-tonal-button class="fusion-del-btn" data-idx="${idx}" style="flex-shrink:0;--md-filled-tonal-button-container-height:32px;font-size:13px;color:var(--sa-error);opacity:.8">删除</md-filled-tonal-button>
          </div>
        `;
        scopeList.appendChild(card);
      });
    };

    const _showEditor = (idx) => {
      const isNew = idx === -1;
      const sc = isNew
        ? {
            scope_id: "",
            name: "",
            strategy: "occupied_or",
            rooms: [],
            members: [],
            enter_hold_secs: 3,
            vacant_hold_secs: 60,
          }
        : normalizeScope(scopes[idx]);

      const defaultPrimary = sc.rooms[0] || roomList[0] || "";
      const defaultNeighbors = sc.rooms.slice(1);

      const roomOptions = roomList.map(r => `<option value="${this._esc(r)}">${this._esc(r)}</option>`).join("");
      const sensorRows = (sensors || []).map(s => {
        const existing = sc.members.find(m => m.entity_id === s.entity_id);
        const m = existing || {
          entity_id: s.entity_id,
          can_enter_trigger: true,
          can_leave_evidence: true,
          priority: 50,
          confidence: 1,
        };
        const checked = existing ? "checked" : "";
        const roomTag = s.room ? `<span style="opacity:.6">${this._esc(s.room)}</span>` : "<span style=\"opacity:.4\">未分区</span>";
        return `
          <div class="fe-member-row" data-eid="${this._esc(s.entity_id)}" style="display:grid;grid-template-columns:minmax(160px,1fr) 84px 84px 92px 92px;gap:8px;align-items:center;padding:8px;border:1px solid var(--sa-border);border-radius:8px">
            <label style="display:flex;align-items:center;gap:8px;min-width:0">
              <input type="checkbox" class="fe-member-enable" ${checked}>
              <span style="display:flex;flex-direction:column;min-width:0">
                <span style="font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(s.name)}</span>
                <span style="font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(s.entity_id)} · ${roomTag}</span>
              </span>
            </label>
            <label style="font-size:11px;display:flex;align-items:center;gap:4px"><input type="checkbox" class="fe-member-enter" ${m.can_enter_trigger ? "checked" : ""}>入场</label>
            <label style="font-size:11px;display:flex;align-items:center;gap:4px"><input type="checkbox" class="fe-member-leave" ${m.can_leave_evidence ? "checked" : ""}>离场</label>
            <input class="fe-member-priority" type="number" min="0" max="100" value="${m.priority}" style="width:100%;border:1px solid var(--sa-border);border-radius:6px;padding:6px;font-size:12px" title="优先级 0-100">
            <input class="fe-member-confidence" type="number" min="0" max="1" step="0.05" value="${m.confidence}" style="width:100%;border:1px solid var(--sa-border);border-radius:6px;padding:6px;font-size:12px" title="置信度 0-1">
          </div>
        `;
      }).join("");

      const overlay = document.createElement("div");
      overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px";
      overlay.innerHTML = `
        <div style="background:var(--sa-card);border-radius:16px;padding:24px;width:min(860px,100%);max-height:85vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.3)">
          <div style="font-size:16px;font-weight:700;margin-bottom:14px">${isNew ? "新建融合域" : "编辑融合域"}</div>
          <div style="display:grid;gap:14px">
            <div>
              <div class="label-s">显示名称</div>
              <md-outlined-text-field id="fe_name" value="${this._esc(sc.name)}" placeholder="如：客餐厅开间"></md-outlined-text-field>
            </div>

            <div style="border:1px solid var(--sa-border);border-radius:12px;padding:12px;background:var(--sa-surface-2)">
              <div class="label-m" style="margin-bottom:8px">房间覆盖（渐进配置）</div>
              <div class="body-s" style="opacity:.68;margin-bottom:10px">先选一个主房间，再添加邻接房间；避免一次性多选误配。</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <div>
                  <div class="label-s">主房间</div>
                  <select id="fe_primary_room" style="height:36px;width:100%;border:1px solid var(--sa-border);border-radius:8px;padding:4px">
                    <option value="">请选择主房间</option>
                    ${roomOptions}
                  </select>
                </div>
                <div>
                  <div class="label-s">邻接房间（可多选）</div>
                  <select id="fe_neighbor_rooms" multiple size="4" style="min-height:88px;width:100%;border:1px solid var(--sa-border);border-radius:8px;padding:4px"></select>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">
                <md-filled-tonal-button id="fe_preset_living" style="--md-filled-tonal-button-container-height:30px;font-size:12px">示例: 客厅+餐厅</md-filled-tonal-button>
                <md-filled-tonal-button id="fe_preset_master" style="--md-filled-tonal-button-container-height:30px;font-size:12px">示例: 主卧+衣帽间</md-filled-tonal-button>
              </div>
            </div>

            <div style="border:1px solid var(--sa-border);border-radius:12px;padding:12px">
              <div class="label-m" style="margin-bottom:8px">成员能力配置</div>
              <div class="body-s" style="opacity:.68;margin-bottom:8px">按成员独立设置入场触发/离场证据，并可调整优先级与置信度。</div>
              <div style="display:grid;gap:8px">
                ${sensorRows || '<div class="body-s" style="opacity:.5">暂无可用传感器</div>'}
              </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
              <div>
                <div class="label-s">融合策略</div>
                <md-outlined-select id="fe_strategy">
                  <md-select-option value="occupied_or" ${sc.strategy !== "vacant_and" ? "selected" : ""}>任一有人即有人</md-select-option>
                  <md-select-option value="vacant_and" ${sc.strategy === "vacant_and" ? "selected" : ""}>全员无人才关灯</md-select-option>
                </md-outlined-select>
              </div>
              <div>
                <div class="label-s">进入确认秒数</div>
                <md-outlined-text-field id="fe_enter_hold" type="number" min="1" max="120" value="${sc.enter_hold_secs}"></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">离开确认秒数</div>
                <md-outlined-text-field id="fe_hold" type="number" min="10" max="600" value="${sc.vacant_hold_secs}"></md-outlined-text-field>
              </div>
            </div>
          </div>
          <div style="display:flex;gap:10px;margin-top:20px;justify-content:flex-end">
            <md-outlined-button id="fe_cancel">取消</md-outlined-button>
            <md-filled-button id="fe_confirm">${isNew ? "创建" : "保存修改"}</md-filled-button>
          </div>
        </div>
      `;
      this.shadowRoot.appendChild(overlay);

      const primarySel = overlay.querySelector("#fe_primary_room");
      const neighborSel = overlay.querySelector("#fe_neighbor_rooms");

      const refreshNeighborOptions = () => {
        const primary = primarySel.value;
        const selected = new Set([...neighborSel.selectedOptions].map(o => o.value));
        neighborSel.innerHTML = "";
        roomList.filter(r => r !== primary).forEach(r => {
          const op = document.createElement("option");
          op.value = r;
          op.textContent = r;
          if (selected.has(r)) op.selected = true;
          neighborSel.appendChild(op);
        });
      };

      const applyRoomSelection = (primary, neighbors) => {
        primarySel.value = primary || "";
        refreshNeighborOptions();
        const wanted = new Set((neighbors || []).filter(r => r !== primary));
        [...neighborSel.options].forEach(op => {
          op.selected = wanted.has(op.value);
        });
      };

      const guessPreset = (pairs) => {
        const all = roomList;
        const pick = (patterns) => all.find(r => patterns.some(p => p.test(r)));
        for (const [aPatterns, bPatterns] of pairs) {
          const a = pick(aPatterns);
          const b = pick(bPatterns);
          if (a && b && a !== b) return { primary: a, neighbors: [b] };
        }
        return null;
      };

      primarySel.onchange = () => refreshNeighborOptions();
      applyRoomSelection(defaultPrimary, defaultNeighbors);

      overlay.querySelector("#fe_preset_living").onclick = () => {
        const picked = guessPreset([
          [[/客厅/, /living/i], [/餐厅/, /dining/i]],
          [[/客餐/, /open/i], [/走廊/, /hall/i]],
        ]);
        if (!picked) {
          this._msg("未匹配到示例房间，请手动选择");
          return;
        }
        applyRoomSelection(picked.primary, picked.neighbors);
      };

      overlay.querySelector("#fe_preset_master").onclick = () => {
        const picked = guessPreset([
          [[/主卧/, /master/i], [/衣帽间/, /cloak|wardrobe/i]],
          [[/卧室/, /bed/i], [/卫生间/, /bath/i]],
        ]);
        if (!picked) {
          this._msg("未匹配到示例房间，请手动选择");
          return;
        }
        applyRoomSelection(picked.primary, picked.neighbors);
      };

      const _close = () => overlay.remove();
      overlay.querySelector("#fe_cancel").onclick = _close;
      overlay.querySelector("#fe_confirm").onclick = async () => {
        const nameVal = overlay.querySelector("#fe_name").value.trim();
        const strategy = overlay.querySelector("#fe_strategy").value;
        const enterHoldSecs = Math.max(1, Math.min(120, parseInt(overlay.querySelector("#fe_enter_hold").value, 10) || 3));
        const holdSecs = Math.max(10, Math.min(600, parseInt(overlay.querySelector("#fe_hold").value, 10) || 60));

        const primary = primarySel.value;
        const neighbors = [...neighborSel.selectedOptions].map(o => o.value).filter(Boolean);
        const roomsSel = primary ? [primary, ...neighbors.filter(r => r !== primary)] : [];

        const members = [];
        overlay.querySelectorAll(".fe-member-row").forEach(row => {
          const enabled = row.querySelector(".fe-member-enable")?.checked;
          if (!enabled) return;
          const entityId = row.dataset.eid || "";
          if (!entityId) return;
          const priority = Number(row.querySelector(".fe-member-priority")?.value);
          const confidence = Number(row.querySelector(".fe-member-confidence")?.value);
          members.push({
            entity_id: entityId,
            can_enter_trigger: !!row.querySelector(".fe-member-enter")?.checked,
            can_leave_evidence: !!row.querySelector(".fe-member-leave")?.checked,
            priority: Number.isFinite(priority) ? Math.max(0, Math.min(100, priority)) : 50,
            confidence: Number.isFinite(confidence) ? Math.max(0, Math.min(1, confidence)) : 1,
          });
        });

        if (!nameVal) {
          this._msg("请填写显示名称");
          return;
        }
        if (!roomsSel.length) {
          this._msg("请至少选择一个主房间");
          return;
        }
        if (!members.length) {
          this._msg("请至少启用一个传感器成员");
          return;
        }
        if (!members.some(m => m.can_enter_trigger)) {
          this._msg("至少需要一个可触发入场的成员");
          return;
        }
        if (!members.some(m => m.can_leave_evidence)) {
          this._msg("至少需要一个可作为离场证据的成员");
          return;
        }

        const scopeId = (sc.scope_id || nameVal.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, "_") || `scope_${Date.now()}`);
        const newScope = {
          scope_id: scopeId,
          name: nameVal,
          strategy,
          rooms: roomsSel,
          members,
          enter_hold_secs: enterHoldSecs,
          vacant_hold_secs: holdSecs,
        };

        if (isNew) scopes.push(newScope);
        else scopes[idx] = newScope;

        _close();
        await _save();
        _render();
      };
    };

    scopeList.addEventListener("click", async e => {
      const editBtn = e.target.closest(".fusion-edit-btn");
      const delBtn = e.target.closest(".fusion-del-btn");
      if (editBtn) _showEditor(parseInt(editBtn.dataset.idx, 10));
      if (delBtn) {
        const i = parseInt(delBtn.dataset.idx, 10);
        if (!(await this._showConfirm(`确认删除融合域「${scopes[i]?.name || i}」？`))) return;
        scopes.splice(i, 1);
        _save().then(() => _render());
      }
    });

    addBtn.onclick = () => _showEditor(-1);
    _render();
  }
};
