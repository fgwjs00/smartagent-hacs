/**
 * SmartAgent Panel — _render() 主模板模块
 * 负责整个 Shadow DOM 的初始化（HTML 模板 + 事件绑定）。
 * 分为两个内部阶段：
 *   1. this.shadowRoot.innerHTML 写入全部 tab 的 HTML（含帮助弹窗、对话框）
 *   2. 各控件事件监听器绑定 + 初始数据加载
 */
import { M3_CSS } from "../styles.js";

export const renderMethods = {
  _render() {
    const SA_HA_FALLBACK_READONLY = this._isHaFallbackReadOnly();
    const $ = id => this.shadowRoot.getElementById(id);
    const ICO = this._getIcons();
    this.shadowRoot.innerHTML = `<style>${M3_CSS}</style>
      <div class="app-bar">
        <h1 id="appBarTitle"><span style="color:var(--sa-primary);display:flex;align-items:center">${ICO.bolt}</span> SmartAgent（HA 面板兜底/应急入口）</h1>
        <div style="display:flex;gap:12px;align-items:center">
          <span class="migration-badge">请使用 SmartAgent UI v2 主控制台</span>
          <md-outlined-button id="helpBtn" class="btn-sm" style="display:flex;align-items:center;gap:5px;font-size:13px">
            <svg slot="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            使用说明
          </md-outlined-button>
          <md-filled-tonal-button id="aiBtn" class="btn-sm"></md-filled-tonal-button>
        </div>
      </div>
      <div style="margin:10px 16px 0;padding:10px 12px;border-radius:10px;border:1px dashed var(--sa-primary);background:var(--sa-primary-container);color:var(--sa-on-primary-container);font-size:12px;line-height:1.6;display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap">
        <span><strong>HA 面板兜底/应急入口</strong>：仅保留状态查看与排障能力，业务写操作已降级阻断。</span>
        <span style="font-weight:600">请使用 SmartAgent UI v2 主控制台</span>
      </div>

      <!-- ── 使用说明弹窗 ── -->
      <div class="help-overlay" id="helpOverlay">
        <div class="help-dialog">
          <div class="help-header">
            <h2>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              SmartAgent 完整使用说明
            </h2>
            <md-icon-button class="help-close" id="helpClose">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </md-icon-button>
          </div>
          <div class="help-layout">
            <!-- 左侧目录 -->
            <div class="help-nav" id="helpNav">
              <div class="help-nav-group">入门</div>
              <div class="help-nav-item" data-sec="overview">🏠 系统概览</div>
              <div class="help-nav-item" data-sec="quickstart">🚀 快速开始</div>
              <div class="help-nav-group">核心功能</div>
              <div class="help-nav-item" data-sec="devices">📱 设备管理</div>
              <div class="help-nav-item" data-sec="control-mode">⚙️ 设备管辖域</div>
              <div class="help-nav-item" data-sec="profiles">🧠 画像与规则</div>
              <div class="help-nav-item" data-sec="confidence">🎯 置信度阈值</div>
              <div class="help-nav-item" data-sec="protection">🛡️ 保护机制</div>
              <div class="help-nav-group">智能功能</div>
              <div class="help-nav-item" data-sec="habits">📊 行为习惯分析</div>
              <div class="help-nav-item" data-sec="aiscenes">🎬 AI 场景</div>
              <div class="help-nav-item" data-sec="transactions">📋 执行记录</div>
              <div class="help-nav-item" data-sec="energy">⚡ 能耗分析</div>
              <div class="help-nav-item" data-sec="feedback">🌡️ 效果反馈</div>
              <div class="help-nav-group">高级设置</div>
              <div class="help-nav-item" data-sec="modes">🎭 运行模式</div>
              <div class="help-nav-item" data-sec="tts">🔊 TTS 语音</div>
              <div class="help-nav-item" data-sec="frigate">📷 Frigate NVR</div>
              <div class="help-nav-item" data-sec="engine">🤖 AI 引擎</div>
              <div class="help-nav-item" data-sec="tips">💡 使用建议</div>
            </div>
            <!-- 右侧内容 -->
            <div class="help-body" id="helpBody">

              <!-- 系统概览 -->
              <div class="help-section" id="hsec-overview">
                <div class="help-section-title">🏠 系统概览</div>
                <p>SmartAgent 是基于 Home Assistant 的 <b>主动式 AI 智能家居管家</b>，通过监听传感器事件流，结合大模型推理，自动执行设备控制操作。与传统"定时自动化"相比，它能理解场景、学习习惯、主动决策。</p>
                <div class="help-sub">核心工作流程</div>
                <div class="help-flow">
                  <span class="help-flow-step">传感器事件触发</span>
                  <span class="help-flow-arrow">→</span>
                  <span class="help-flow-step">快速路径判断</span>
                  <span class="help-flow-arrow">→</span>
                  <span class="help-flow-step">AI 推理决策</span>
                  <span class="help-flow-arrow">→</span>
                  <span class="help-flow-step">Action Router</span>
                  <span class="help-flow-arrow">→</span>
                  <span class="help-flow-step">执行 + 状态验证</span>
                </div>
                <div class="help-sub">三级优先级体系</div>
                <table class="help-table">
                  <tr><th>级别</th><th>来源</th><th>说明</th></tr>
                  <tr><td><span class="help-badge red">P1 铁律</span></td><td>🔒 锁定的画像/规则</td><td>绝对服从，AI 不得违反，最高优先级</td></tr>
                  <tr><td><span class="help-badge orange">P2 行为学习</span></td><td>历史规律 + 实时习惯</td><td>学习用户覆盖记录，逐渐精准化决策</td></tr>
                  <tr><td><span class="help-badge">P3 参考</span></td><td>普通画像/规则</td><td>AI 决策的参考依据，可被 P2 覆盖</td></tr>
                </table>
              </div>

              <!-- 快速开始 -->
              <div class="help-section" id="hsec-quickstart">
                <div class="help-section-title">🚀 快速开始（推荐步骤）</div>
                <div class="help-item">
                  <span class="help-badge">① 添加设备</span>
                  <p>进入<b>设备管理</b> → 点击「扫描发现」→ 勾选要托管的设备 → 批量添加。建议先添加灯光、开关、空调等主要设备。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge">② 填写画像</span>
                  <p>进入<b>个性化画像</b> → 添加几条描述生活习惯的文字，例如："主人一般 23 点后休息"、"希望家里保持 22-26°C 舒适温度"、"在家工作，白天经常在书房"。越详细越准确。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge">③ 锁定铁律</span>
                  <p>对绝对不可违反的规则点击 🔒 锁定，例如："深夜 0 点到 6 点不得开启任何设备"、"厨房油烟机由自动化控制，AI 勿干预"。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge">④ 开启静默学习</span>
                  <p>首次使用时建议开启<b>静默学习模式</b>（控制台 → 系统策略），AI 只记录操作日志而不自动执行，积累 2-3 天数据后再关闭，AI 判断会更准确。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge">⑤ 调整阈值</span>
                  <p>根据实际体验调整置信度阈值。如果 AI 经常误操作 → 提高自动执行阈值；如果 AI 很少主动执行 → 适当降低阈值。</p>
                </div>
                <div class="help-tip">💡 等待 7 天后系统会自动分析行为规律并推荐 AI 场景，届时可在「AI 场景」标签页审批。</div>
              </div>

              <!-- 设备管理 -->
              <div class="help-section" id="hsec-devices">
                <div class="help-section-title">📱 设备管理</div>
                <div class="help-item">
                  <span class="help-badge blue">扫描发现</span>
                  <p>点击「扫描发现」按钮，系统会自动列出 HA 中所有可托管的实体（灯光/开关/空调/窗帘/风扇/传感器等），并过滤掉电池电量、信号强度等辅助传感器。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge green">批量添加</span>
                  <p>勾选需要的设备后点击「批量添加」，或点击「全选」后统一添加。可通过搜索框过滤设备名称。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge orange">显示离线</span>
                  <p>勾选"显示离线"可看到当前不可用的设备（unavailable 状态），方便排查设备掉线问题。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge">批量管辖域</span>
                  <p>选中多台设备后，可一键将整个房间或同类型设备设为相同管辖模式（AI全权/HA优先/共享）。</p>
                </div>
                <div class="help-tip">💡 传感器类设备（binary_sensor/sensor）也可以添加到托管列表，这样 AI 在推理时会优先关注这些传感器的实时读数。</div>
              </div>

              <!-- 设备管辖域 -->
              <div class="help-section" id="hsec-control-mode">
                <div class="help-section-title">⚙️ 设备管辖域（控制模式）</div>
                <p>每台设备可独立设置 AI 的控制权限，决定 AI 能否以及如何操作该设备。</p>
                <div class="help-item">
                  <span class="help-badge red">AI 全权</span>
                  <p>AI <b>完全接管</b>该设备，可随时直接调用 HA 服务操作。<b>不会</b>尝试走脚本/场景路由，效率最高。适合您希望 AI 完全自主管理且没有关联自动化的设备（如主卧灯光）。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge blue">HA 优先</span>
                  <p>该设备<b>由 HA 自动化或脚本负责</b>，AI 不会直接操作，仅在日志中记录"建议操作"。适合：已有成熟自动化的设备、安全相关设备（报警器、门锁）、您希望 AI 完全不干预的设备。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge green">共享（推荐）</span>
                  <p>默认模式。AI 会<b>优先路由</b>到与该设备关联的 HA 脚本或 AI 场景（若存在且时间匹配），若无则直接操作设备。兼顾已有自动化逻辑与 AI 智能，推荐大多数设备使用。</p>
                </div>
                <div class="help-sub">Action Router 路由优先级（共享模式）</div>
                <div class="help-flow">
                  <span class="help-flow-step">① 匹配激活 AI 场景</span>
                  <span class="help-flow-arrow">→</span>
                  <span class="help-flow-step">② 匹配 HA 关联脚本</span>
                  <span class="help-flow-arrow">→</span>
                  <span class="help-flow-step">③ 直接调用服务</span>
                </div>
                <div class="help-warn">⚠️ HA 优先模式下 AI 仍会分析场景并给出建议，建议内容可在系统日志中查看，但不会自动执行。</div>
              </div>

              <!-- 个性化画像与规则 -->
              <div class="help-section" id="hsec-profiles">
                <div class="help-section-title">🧠 个性化画像 & 规则</div>
                <p>画像和规则是 AI 决策的"知识库"，描述越准确，AI 的判断越符合您的期望。</p>
                <div class="help-sub">画像（习惯描述）</div>
                <div class="help-item">
                  <span class="help-badge">普通画像</span>
                  <p>自由描述生活习惯、偏好和环境要求。例如：<br>
                  • "主人一般 23 点后休息，深夜不希望有设备自动启动"<br>
                  • "希望家里保持 22-26°C 舒适温度，夏天 27°C 以上时开空调"<br>
                  • "家里有老人，过道灯需保持长亮"</p>
                </div>
                <div class="help-item">
                  <span class="help-badge red">🔒 铁律（锁定画像）</span>
                  <p>点击 🔒 图标锁定后升级为 <b>P1 铁律</b>，AI 无论何种情况都必须遵守。适合：<br>
                  • "凌晨 0-6 点绝不开启任何设备"<br>
                  • "空调最高设定 26°C，不得超过"<br>
                  • "厨房设备全部由 HA 自动化管控，AI 勿干预"</p>
                </div>
                <div class="help-sub">规则（条件指令）</div>
                <div class="help-item">
                  <span class="help-badge blue">规则</span>
                  <p>比画像更具体的触发式指令，例如：<br>
                  • "检测到有人进入客厅时，若亮度低于 50lux 则开灯"<br>
                  • "离家状态超过 30 分钟时关闭所有灯光和空调"<br>
                  • "温度超过 30°C 且有人在家时自动开启空调制冷"</p>
                </div>
                <div class="help-item">
                  <span class="help-badge red">🔒 铁律（锁定规则）</span>
                  <p>锁定的规则会成为 P1 铁律级的强制指令，AI 必须严格执行，不会被习惯学习覆盖。</p>
                </div>
                <div class="help-tip">💡 画像和规则越具体越好。"保持舒适"这类模糊描述效果远不如"室温超过 28°C 开制冷，低于 20°C 开制热"。</div>
              </div>

              <!-- 置信度阈值 -->
              <div class="help-section" id="hsec-confidence">
                <div class="help-section-title">🎯 置信度阈值</div>
                <p>AI 每次推理都会输出 0-100 的置信度分值，表示对当前决策的确信程度。阈值决定了 AI 在哪个置信度下自动执行。</p>
                <table class="help-table">
                  <tr><th>置信度区间</th><th>行为</th><th>推荐值</th></tr>
                  <tr><td>≥ 自动执行阈值</td><td>直接执行动作，不弹通知</td><td>80～90</td></tr>
                  <tr><td>通知阈值 ~ 自动执行阈值</td><td>仅推送 HA 通知，等待您确认</td><td>60～75</td></tr>
                  <tr><td>&lt; 通知阈值</td><td>静默忽略，仅记录到系统日志</td><td>—</td></tr>
                </table>
                <div class="help-sub">场景建议</div>
                <div class="help-item">
                  <span class="help-badge green">新安装</span>
                  <p>建议设置较高阈值（自动 90，通知 75），减少频繁误操作，先通过通知确认观察 AI 的判断质量。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge orange">运行稳定后</span>
                  <p>等 AI 积累 1-2 周习惯数据后，可适当降低（自动 80，通知 60），让 AI 更主动。</p>
                </div>
                <div class="help-tip">💡 控制台「动作执行质量」卡片会显示近 7 天的成功率和失败 Top 5，帮助您判断是否需要调整阈值。</div>
              </div>

              <!-- 保护机制 -->
              <div class="help-section" id="hsec-protection">
                <div class="help-section-title">🛡️ 保护机制（12 层防护）</div>
                <p>SmartAgent 内置 12 层保护，防止 AI 误操作或与 HA 自动化产生冲突。</p>
                <table class="help-table">
                  <tr><th>#</th><th>机制</th><th>说明</th></tr>
                  <tr><td>1</td><td>来源溯源</td><td>区分"用户界面手动"、"物理按键"、"HA 自动化"三种来源，给予不同优先级</td></tr>
                  <tr><td>2</td><td>用户覆盖保护 (120s)</td><td>您手动操作某设备后，AI 在 120 秒内不会反向操作该设备</td></tr>
                  <tr><td>3</td><td>自触发保护</td><td>A 设备状态变化触发推理时，AI 不能反过来操作同一设备 A（防死循环）</td></tr>
                  <tr><td>4</td><td>AI 操作跳过窗口 (8s)</td><td>AI 刚操作过设备后，该设备状态变化不触发新一轮推理</td></tr>
                  <tr><td>5</td><td>域白名单 + 危险服务黑名单</td><td>AI 只能操作 light/switch/climate/cover/fan/media_player 等，禁止调用危险服务</td></tr>
                  <tr><td>6</td><td>人员在场守卫</td><td>无人房间 AI 不开灯；有人房间 AI 不关灯（可通过规则配置例外）</td></tr>
                  <tr><td>7</td><td>HA 自动化管辖自动发现</td><td>自动扫描所有 HA 自动化，构建"哪些设备被哪些自动化管控"的映射表</td></tr>
                  <tr><td>8</td><td>自动化触发跳过</td><td>被 HA 自动化触发的设备状态变化，不会触发 AI 推理</td></tr>
                  <tr><td>9</td><td>自动化冲突硬拦截 (30s)</td><td>某 HA 自动化 30 秒内刚执行过，AI 不会操作该自动化管辖的设备</td></tr>
                  <tr><td>10</td><td>Prompt 动态冲突警告</td><td>AI 推理时，Prompt 中自动标注每台设备的关联自动化名称，让 AI 自我规避</td></tr>
                  <tr><td>11</td><td>动作指纹冷却 (120s)</td><td>禁止 120 秒内对同一设备执行相同操作，避免 AI 重复刷屏</td></tr>
                  <tr><td>12</td><td>区域隔离 + 双阶段意图验证</td><td>传感器触发时限制跨区域操控；LLM 动作在执行前经语义防火墙 + 物理验证双重审查，拦截幻觉实体、矛盾指令、越界参数</td></tr>
                </table>
                <div class="help-sub">双阶段意图验证详解</div>
                <p style="font-size:13px;line-height:1.6">LLM 返回动作后、执行前，系统自动运行两阶段验证：</p>
                <div class="help-item">
                  <span class="help-badge red">Stage 1 语义防火墙</span>
                  <p>• 实体不存在（防 LLM 幻觉）→ 拒绝<br>
                  • 同一设备同时 turn_on + turn_off（矛盾指令）→ 拒绝<br>
                  • 有人在场的区域尝试关灯 → 拒绝（用户显式指令豁免）<br>
                  • 传感器触发时跨区域操控 → 拒绝（用户指令/全局命令豁免）</p>
                </div>
                <div class="help-item">
                  <span class="help-badge blue">Stage 2 物理验证</span>
                  <p>• domain 与 entity_id 前缀不匹配 → 拒绝<br>
                  • service 不在白名单（如使用了 set_color_temp 而非 turn_on）→ 拒绝<br>
                  • 参数超出合法范围（brightness_pct &gt; 100、color_temp_kelvin &lt; 1000 等）→ 拒绝</p>
                </div>
                <div class="help-tip">💡 如果日志显示"意图验证后无有效动作"，在系统日志中搜索"[意图验证] 共拒绝"即可看到被拒绝的 entity_id 和具体原因，快速定位问题。</div>
              </div>

              <!-- 行为习惯分析 -->
              <div class="help-section" id="hsec-habits">
                <div class="help-section-title">📊 行为习惯分析</div>
                <p>系统持续记录 <b>365 天</b>的完整设备事件历史，每天凌晨 3:00 自动运行深度分析。</p>
                <div class="help-sub">分析内容</div>
                <div class="help-item">
                  <span class="help-badge">活跃时段</span>
                  <p>统计您在一天各时段（早/午/晚/深夜）的操作频率和设备偏好，形成"作息画像"供 AI 参考。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge orange">用户覆盖记录</span>
                  <p>记录您手动推翻 AI 决策的场景（如 AI 开灯后您关灯）。系统会学习这些模式，下次在相同场景主动降低置信度，避免重复犯错。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge blue">到家时间规律</span>
                  <p>学习您工作日、休息日的回家时间规律。发现固定规律后，提前 30 分钟准备环境（开空调预冷/预热等）。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge green">行为模式摘要</span>
                  <p>将分析结果提炼为文字摘要，在每次 AI 推理时注入 Prompt，让 AI 更了解您的生活习惯。</p>
                </div>
                <div class="help-sub">习惯主动询问</div>
                <p style="font-size:13px;line-height:1.6">开启后，AI 在发现符合历史习惯的场景时，会先发送 HA 通知询问（例如"每天 22 点您会开启卧室空调，是否现在执行？"），等待您点击确认后再执行，而非直接操作。适合不想 AI 过于自主的用户。</p>
                <div class="help-tip">💡 行为习惯分析页面可查看：近 7 天覆盖最多的设备 Top 5、到家时间分布图、当前行为规律文字摘要。</div>
              </div>

              <!-- AI 场景 -->
              <div class="help-section" id="hsec-aiscenes">
                <div class="help-section-title">🎬 AI 场景</div>
                <p>系统通过分析设备联动历史，自动发现您的行为规律并生成候选场景，经您批准后固化为可执行的 HA 场景。</p>
                <div class="help-sub">发现机制</div>
                <p style="font-size:13px;line-height:1.6">系统检测在同一时间窗口内（15 分钟内）频繁同时变化的设备组合，并统计其出现频率、时间段、星期分布。当某个组合出现次数超过阈值时，生成候选场景。</p>
                <div class="help-sub">场景状态</div>
                <div class="help-item">
                  <span class="help-badge gray">候选</span>
                  <p>等待您审批的新场景，系统已识别到规律但尚未生效。推送 HA 通知提醒您处理。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge green">已激活</span>
                  <p>您批准后，系统自动在 HA 中创建 <span class="help-code">scene.ai_xxx</span> 场景实体。此后 AI 在匹配时间段遇到相关设备触发时，会<b>优先调用该场景</b>而非逐设备推理，响应更快更稳定。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge red">已拒绝</span>
                  <p>您拒绝的场景不会再被推荐，对应的 HA 场景实体也会被删除。</p>
                </div>
                <div class="help-sub">场景包含的信息</div>
                <div class="help-item">
                  <span class="help-badge">时间窗口</span>
                  <p>场景适用的时间段（如 21:00-23:00）和星期（如周一至周五）。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge orange">设备列表</span>
                  <p>场景包含的设备及其目标状态（如"卧室灯 on 亮度 30%、卧室空调 on 26°C"）。</p>
                </div>
                <div class="help-tip">💡 批准的场景可以手动触发测试，也可以在此修改场景名称、调整设备参数后再激活。</div>
              </div>

              <!-- 执行记录 -->
              <div class="help-section" id="hsec-transactions">
                <div class="help-section-title">📋 执行记录 & 事务回滚</div>
                <p>每次 AI 执行的多设备动作组会被作为一条<b>事务</b>完整记录，并在执行前拍摄所有目标设备的状态快照。</p>
                <div class="help-sub">事务状态说明</div>
                <table class="help-table">
                  <tr><th>状态</th><th>含义</th></tr>
                  <tr><td><span class="help-badge green">成功</span></td><td>所有目标设备均执行成功，状态验证通过</td></tr>
                  <tr><td><span class="help-badge orange">部分执行</span></td><td>部分设备执行成功，部分被保护机制拦截或失败</td></tr>
                  <tr><td><span class="help-badge blue">已拦截</span></td><td>所有动作均被保护机制拦截（如用户覆盖、自动化冲突）</td></tr>
                  <tr><td><span class="help-badge red">失败</span></td><td>执行过程中出现服务调用错误</td></tr>
                  <tr><td><span class="help-badge gray">已回滚</span></td><td>已手动回滚到执行前状态</td></tr>
                </table>
                <div class="help-item" style="margin-top:8px">
                  <span class="help-badge orange">⏪ 回滚</span>
                  <p>点击"回滚"按钮，系统会读取执行前快照，将事务中所有设备恢复到 AI 操作之前的状态。例如：AI 打开了客厅灯和空调 → 点击回滚 → 灯和空调恢复为之前的关闭状态。</p>
                </div>
                <div class="help-tip">💡 系统保留最近 30 条事务记录，超过 30 天的记录会自动清理。</div>
              </div>

              <!-- 能耗分析 -->
              <div class="help-section" id="hsec-energy">
                <div class="help-section-title">⚡ 能耗分析</div>
                <p>无需功率计量插座，仅通过分析设备状态历史和存在感传感器数据，估算使用时长和无人浪费情况。</p>
                <div class="help-sub">统计指标</div>
                <div class="help-item">
                  <span class="help-badge">开启时长</span>
                  <p>近 7 天内，该设备处于开启状态的累计时间。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge red">浪费时长</span>
                  <p>设备开启期间，房间内<b>没有任何存在感传感器</b>检测到人员的时长。颜色越红表示浪费越严重（红：>50%，橙：>20%，绿：正常）。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge orange">节能建议</span>
                  <p>当某设备无人浪费时长超过 30 分钟时，系统会主动推送 HA 通知，建议为该设备添加存在感自动化或调整 AI 规则。</p>
                </div>
                <div class="help-tip">💡 能耗分析每天凌晨 3:00 自动更新，也可重启集成立即执行一次分析。添加存在感传感器（mmWave 毫米波雷达）后准确度会大幅提升。</div>
              </div>

              <!-- 环境效果反馈 -->
              <div class="help-section" id="hsec-feedback">
                <div class="help-section-title">🌡️ 环境效果反馈闭环</div>
                <p>AI 执行空调操作后，系统会在 <b>10 分钟后</b>自动检查环境传感器，验证设备效果是否达到预期。</p>
                <div class="help-item">
                  <span class="help-badge green">效果正常</span>
                  <p>温度已朝目标方向变化（≥ 0.3°C），记录到系统日志中，不打扰用户。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge red">效果不明显</span>
                  <p>10 分钟后温度未明显变化，系统会推送 HA 通知 + TTS 播报（若已配置），提醒您检查空调是否正常工作、遥控/网关是否在线等。</p>
                </div>
                <div class="help-tip">💡 系统会自动通过房间名关键词匹配温湿度传感器（如 climate.living_room_ac → sensor.*living_room*temp*），无需手动配置。</div>
              </div>

              <!-- 运行模式 -->
              <div class="help-section" id="hsec-modes">
                <div class="help-section-title">🎭 运行模式</div>
                <div class="help-item">
                  <span class="help-badge green">家庭模式</span>
                  <p>默认模式。AI 完整运行所有保护机制，学习用户习惯，保护用户隐私。适合日常居家使用。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge blue">展厅模式</span>
                  <p>专为销售展示设计。可选择预设场景（晨起、晚间休息、影院、到家、离家），AI 会模拟该时间段的智能家居效果，即使白天也可演示夜晚/清晨场景。支持自定义场景描述输入。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge gray">静默学习模式</span>
                  <p>开启后 AI <b>只记录操作日志，不自动执行任何动作</b>。适合：首次安装观察期、调试期间、度假/长期外出时暂停 AI 控制。</p>
                </div>
              </div>

              <!-- TTS 语音播报 -->
              <div class="help-section" id="hsec-tts">
                <div class="help-section-title">🔊 TTS 语音播报配置</div>
                <p>配置完成后，AI 在执行操作或有重要提示时会通过智能音箱播报语音。</p>
                <div class="help-sub">填写方式</div>
                <div class="help-item">
                  <span class="help-badge">TTS 服务</span>
                  <p>格式为 <b>domain.service_name</b>，填写 HA 中已安装的 TTS 集成服务名：<br>
                  • <span class="help-code">tts.piper</span> — 本地离线 TTS（推荐，Piper TTS 集成）<br>
                  • <span class="help-code">tts.cloud_say</span> — Nabu Casa 云端 TTS<br>
                  • <span class="help-code">tts.google_translate_say</span> — Google 翻译 TTS<br>
                  • <span class="help-code">tts.edge_tts</span> — Edge TTS（微软）</p>
                </div>
                <div class="help-item">
                  <span class="help-badge">目标播放器</span>
                  <p>填写要播放语音的 <b>media_player 实体 ID</b>，例如：<br>
                  • <span class="help-code">media_player.bedroom_speaker</span><br>
                  • <span class="help-code">media_player.living_room_echo</span></p>
                </div>
                <div class="help-sub">播报级别</div>
                <table class="help-table">
                  <tr><th>级别</th><th>播报内容</th><th>适用场景</th></tr>
                  <tr><td>0 — 关闭</td><td>无语音播报</td><td>不想被打扰</td></tr>
                  <tr><td>1 — 仅 AI 回复</td><td>AI 决策中的 speak 字段文本</td><td>只听 AI 主动说话</td></tr>
                  <tr><td>2 — 回复+摘要</td><td>speak + "已执行 N 个操作"</td><td>想知道 AI 做了什么</td></tr>
                  <tr><td>3 — 全部</td><td>全部 + 习惯询问通知</td><td>全面语音交互</td></tr>
                </table>
                <div class="help-tip">💡 配置后可点击「测试播报」按钮发送一条测试语音，验证配置是否正确。</div>
              </div>

              <!-- Frigate NVR -->
              <div class="help-section" id="hsec-frigate">
                <div class="help-section-title">📷 Frigate NVR 视觉感知</div>
                <p>可选功能。若您已在另一台主机安装 Frigate NVR 并接入 HA，开启后 SmartAgent 可利用摄像头数据增强 AI 决策。</p>
                <div class="help-sub">功能增强</div>
                <div class="help-item">
                  <span class="help-badge blue">人数注入</span>
                  <p>读取 <span class="help-code">sensor.*_person_count</span> 传感器，将各房间检测到的人数注入 AI 推理的上下文中（如"客厅：2 人在场"），比仅靠 PIR 传感器的 on/off 判断更准确。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge green">低阈值触发</span>
                  <p>普通传感器的变化阈值是 5，但 person_count 从 0→1 的变化（阈值 1）就会触发 AI 推理，实现"有人进入房间"的即时响应。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge orange">占用检测增强</span>
                  <p>人员在场守卫（保护层 6）会同时考虑 PIR 传感器和 Frigate person_count 数据，避免"人走了 PIR 还没归零"导致的误判。</p>
                </div>
                <div class="help-tip">💡 如果您没有 Frigate NVR，保持关闭即可，SmartAgent 会继续使用 PIR/mmWave 传感器判断人员在场，功能完整无影响。</div>
              </div>

              <!-- AI 推理引擎 -->
              <div class="help-section" id="hsec-engine">
                <div class="help-section-title">🤖 AI 推理引擎配置</div>
                <div class="help-item">
                  <span class="help-badge green">本地 Ollama</span>
                  <p>在本机或局域网另一台机器运行 Ollama 服务。<b>隐私最佳，无云端费用</b>，响应速度取决于硬件性能。适合有 GPU 或性能较好的主机。推荐模型：qwen2.5:7b、llama3.2、gemma3:4b。</p>
                </div>
                <div class="help-item">
                  <span class="help-badge blue">云端 API</span>
                  <p>调用云端大模型 API。<b>效果最佳，响应最快</b>，但需要 API Key 并产生调用费用。支持：通义千问（DashScope）、DeepSeek、SiliconFlow、自定义 OpenAI 兼容接口。</p>
                </div>
                <div class="help-sub">引擎选择建议</div>
                <table class="help-table">
                  <tr><th>场景</th><th>推荐</th></tr>
                  <tr><td>隐私优先 / 无公网</td><td>本地 Ollama（qwen2.5:7b 或更大）</td></tr>
                  <tr><td>效果优先 / 有公网</td><td>云端通义千问 qwen-plus 或 DeepSeek</td></tr>
                  <tr><td>低成本体验</td><td>SiliconFlow 免费额度 + qwen2.5-7b-instruct</td></tr>
                  <tr><td>展厅演示</td><td>云端 API（响应快，效果好）</td></tr>
                </table>
                <div class="help-tip">💡 引擎可随时在控制台右上角下拉菜单切换，修改后立即生效，无需重启。</div>
              </div>

              <!-- 使用建议 -->
              <div class="help-section" id="hsec-tips">
                <div class="help-section-title">💡 最佳实践建议</div>
                <div class="help-item">
                  <span class="help-badge green">✅ 推荐做法</span>
                  <p>
                  • 首次安装后开启<b>静默学习模式</b> 2-3 天，观察 AI 的判断质量后再关闭<br>
                  • 为每个房间添加<b>存在感传感器</b>（mmWave 优于 PIR），AI 占用判断会更准确<br>
                  • 已有 HA 自动化管控的设备，管辖域设为"HA 优先"，避免冲突<br>
                  • 画像写得具体（带数字、时间、条件），比模糊描述效果好 10 倍<br>
                  • 定期查看「行为习惯」页面，了解 AI 的学习情况，必要时补充规则</p>
                </div>
                <div class="help-item">
                  <span class="help-badge red">❌ 避免做法</span>
                  <p>
                  • 不要将门锁、报警器、燃气设备等安全设备设为"AI 全权"<br>
                  • 不要同时让 HA 自动化和 AI 操作同一设备（会产生冲突）<br>
                  • 不要将自动执行阈值设得太低（&lt; 70），会导致频繁误操作<br>
                  • 避免画像写得过于模糊，如"保持舒适"——AI 无法量化执行</p>
                </div>
                <div class="help-item">
                  <span class="help-badge orange">🔧 故障排查</span>
                  <p>
                  • <b>AI 不执行</b> → 检查置信度阈值是否太高；看系统日志确认触发原因<br>
                  • <b>AI 频繁误操作</b> → 提高阈值；为相关设备添加更明确的规则<br>
                  • <b>TTS 不播报</b> → 检查 TTS 服务名和播放器 ID 是否正确；点击"测试播报"<br>
                  • <b>AI 场景没有出现</b> → 数据积累不足，需要 7 天以上使用记录<br>
                  • <b>设备操作被拦截</b> → 查看系统日志，确认是哪层保护机制生效<br>
                  • <b>显示"意图验证后无有效动作"</b> → 见下方说明</p>
                </div>
                <div class="help-item">
                  <span class="help-badge red">❓ 意图验证后无有效动作</span>
                  <p>AI 推理成功但所有动作被拒绝，常见原因：</p>
                  <table class="help-table" style="margin-top:6px">
                    <tr><th>拒绝原因</th><th>说明</th><th>处理</th></tr>
                    <tr><td>实体不存在</td><td>LLM 幻觉了不在设备列表的 entity_id</td><td>在画像中补充设备描述，减少 LLM 幻觉</td></tr>
                    <tr><td>区域隔离违规</td><td>传感器触发区与设备区不同</td><td>用语音/面板发出全局指令，或在规则中设置跨区联动</td></tr>
                    <tr><td>有人在场禁止关灯</td><td>存在传感器显示有人，AI 却想关灯</td><td>通常符合预期；若传感器误报请检查其状态</td></tr>
                    <tr><td>参数超出范围</td><td>如亮度 > 100、色温超界</td><td>在画像中说明设备的正确参数范围</td></tr>
                    <tr><td>非法 service</td><td>AI 使用了不支持的服务名</td><td>在画像中添加操作示例（如：调色温用 turn_on + color_temp_kelvin）</td></tr>
                  </table>
                  <p style="margin-top:6px;font-size:12px;color:var(--sa-on-surface-variant)">💡 系统日志搜索「[意图验证] 共拒绝」可看到被拒绝的 entity_id 和具体原因。</p>
                </div>
                <div class="help-warn">⚠️ 系统日志（「系统日志」标签页）是排查所有问题的最佳工具，每次 AI 决策的完整推理过程都会记录在此。</div>
              </div>

            </div><!-- /help-body -->
          </div><!-- /help-layout -->
        </div>
      </div>
      <!-- ── 主导航 Tab ── -->
      <div class="nav-tabs primary-tabs">
        <button class="nav-tab active" data-t="dashboard" data-group="">控制台</button>
        <button class="nav-tab has-sub" data-group="space">📱 设备与空间</button>
        <button class="nav-tab has-sub" data-group="ai">🧠 AI 智能</button>
        <button class="nav-tab has-sub" data-group="data">📊 数据看板</button>
        <button class="nav-tab has-sub" data-group="system">⚙️ 系统管理</button>
        <button class="nav-tab" data-t="syslog" data-group="">系统日志</button>
      </div>
      <!-- ── 子导航 Tab ── -->
      <div class="nav-sub-tabs" id="sub-space" style="display:none">
        <button class="nav-sub-tab active" data-t="devices">设备管理</button>
        <button class="nav-sub-tab" data-t="rooms">房间拓扑</button>
        <button class="nav-sub-tab" data-t="vision">视觉感知</button>
      </div>
      <div class="nav-sub-tabs" id="sub-ai" style="display:none">
        <button class="nav-sub-tab active" data-t="profiles">个性化画像</button>
        <button class="nav-sub-tab" data-t="habits">行为习惯</button>
        <button class="nav-sub-tab" data-t="aiscenes">AI 场景</button>
        <button class="nav-sub-tab" data-t="corrections">纠错学习</button>
      </div>
      <div class="nav-sub-tabs" id="sub-data" style="display:none">
        <button class="nav-sub-tab active" data-t="transactions">AI 看板</button>
        <button class="nav-sub-tab" data-t="energy">能耗分析</button>
      </div>
      <div class="nav-sub-tabs" id="sub-system" style="display:none">
        <button class="nav-sub-tab active" data-t="config">系统配置</button>
        <button class="nav-sub-tab" data-t="patrol">巡检配置</button>
        <button class="nav-sub-tab" data-t="backup">备份/恢复</button>
        <button class="nav-sub-tab" data-t="mcp">MCP 服务</button>
        <button class="nav-sub-tab" data-t="license">License</button>
      </div>
      <div class="batch-fab" id="batchFab">
        <span class="count" id="batchCount">已选 0 项</span>
        <div class="divider"></div>
        <div class="actions" id="batchFabActions">
          <select id="batchFabRoom" class="m3-select-compact" style="width:100px"><option value="">设置房间…</option></select>
          <md-filled-tonal-button id="batchFabAi" style="--md-filled-tonal-button-container-height:32px;font-size:13px">AI全权</md-filled-tonal-button>
          <md-filled-tonal-button id="batchFabHa" style="--md-filled-tonal-button-container-height:32px;font-size:13px">HA优先</md-filled-tonal-button>
          <md-filled-button id="batchFabDel" class="btn-error" style="--md-filled-button-container-height:32px;font-size:13px">删除</md-filled-button>
          <button class="help-close" id="batchFabClear" title="清空选择">${ICO.close}</button>
        </div>
      </div>
      <div class="main">
        <!-- ── 控制台 ── -->
        <div id="view-dashboard" class="tab-view active">
          <div class="stat-grid">
            <div class="stat-card">
              <div class="stat-card-icon">${ICO.device}</div>
              <div class="stat-num" id="dCnt">0</div>
              <div class="stat-lbl">托管设备</div>
          </div>
            <div class="stat-card">
              <div class="stat-card-icon">${ICO.profile}</div>
              <div class="stat-num" id="hCnt">0</div>
              <div class="stat-lbl">画像条数</div>
            </div>
            <div class="stat-card">
              <div class="stat-card-icon">${ICO.rule}</div>
              <div class="stat-num" id="rCnt">0</div>
              <div class="stat-lbl">推理规则</div>
              <div class="stat-sub" id="rCntSub" style="font-size:11px;opacity:0.5;margin-top:2px"></div>
            </div>
          </div>

          <div class="card" id="qualityCard" style="display:none">
            <div class="card-title">${ICO.check} 动作执行质量（近 7 天）</div>
            <div id="qualityStats" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px"></div>
            <div id="qualityFailures" style="margin-top:12px"></div>
          </div>

          <!-- AI 学习进度仪表盘 -->
          <div class="card" id="learningDashCard">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
              <div class="card-title" style="margin:0">${ICO.book} AI 学习进度</div>
              <md-filled-tonal-button id="refreshLearningBtn" class="btn-sm" style="font-size:12px">刷新</md-filled-tonal-button>
            </div>
            <div id="learningStats" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px">
              <div style="text-align:center;padding:16px;color:var(--md-sys-color-outline);font-size:13px;grid-column:1/-1">加载中...</div>
            </div>
            <div id="learningDeviceWarning" style="display:none;margin-top:12px;padding:10px 14px;border-radius:10px;background:var(--md-sys-color-error-container);color:var(--md-sys-color-on-error-container);font-size:13px"></div>
            <div id="learningTrend" style="display:none;margin-top:14px"></div>
            <div id="learningTopCorrected" style="display:none;margin-top:14px"></div>
          </div>

          <div class="card-tonal" style="display:flex;align-items:center;gap:20px">
            <div class="scene-icon-wrap" id="sceneIconWrap">
              ${ICO.home}
            </div>
            <div style="flex:1">
              <div class="label-m" style="opacity:.8;margin-bottom:4px;letter-spacing:0.5px">当前场景分析</div>
              <div class="headline-s" id="sTxt" style="font-size:22px;font-weight:600">正在监控中...</div>
            </div>
            <div id="modeChip" class="chip active" style="height:32px;padding:0 12px;border-radius:10px;background:var(--sa-card);color:var(--sa-primary);border:none;font-weight:600">
              家庭模式
            </div>
          </div>

          <!-- 近期 AI 操作 (带纠正) — 控制台只显示徽章，详情在纠错学习页 -->
          <div class="card" id="recentAiCard" style="display:none">
            <div style="display:flex;align-items:center;justify-content:space-between">
              <div class="card-title" style="margin-bottom:0">${ICO.bolt} 近期 AI 操作</div>
              <md-filled-tonal-button id="goToCorrections" style="--md-filled-tonal-button-container-height:32px;font-size:12px">
                🎯 查看纠错 <span id="corrBadge" style="background:var(--sa-error);color:#fff;border-radius:10px;padding:1px 7px;font-size:11px;font-weight:700">0</span>
              </md-filled-tonal-button>
            </div>
            <div id="recentAiSummary" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:8px"></div>
          </div>

          <div class="card">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
              <div class="card-title" style="margin-bottom:0">
                ${ICO.gauge}
                策略与调节
              </div>
              <div style="display:flex;align-items:center;gap:8px">
                <span id="modeIcon" style="color:var(--sa-primary);display:flex;align-items:center">${ICO.home}</span>
                  <md-outlined-select id="modeSel" style="width:140px">
                    <md-select-option value="home"><div slot="headline">家庭模式</div></md-select-option>
                    <md-select-option value="showroom"><div slot="headline">展厅模式</div></md-select-option>
                  </md-outlined-select>
              </div>
            </div>
            
            <div style="display:flex;flex-direction:column;gap:20px">
              <div style="display:flex;flex-wrap:wrap;gap:12px">
                <div class="mode-card" id="learningModeItem">
                  <div class="mode-card-icon">${ICO.book}</div>
                  <div style="flex:1">
                    <div class="label-l">静默学习模式</div>
                    <div class="body-s">只记录操作，不执行推理</div>
                  </div>
                  <md-switch id="learningModeToggle"></md-switch>
                </div>
                <div class="mode-card" id="habitProactiveItem">
                  <div class="mode-card-icon">${ICO.tips}</div>
                  <div style="flex:1">
                    <div class="label-l">习惯主动询问</div>
                    <div class="body-s">无传感器时主动确认动作</div>
                  </div>
                  <md-switch id="habitProactiveToggle"></md-switch>
                </div>
                <div class="mode-card" id="frigateItem">
                  <div class="mode-card-icon">${ICO.binary_sensor}</div>
                  <div style="flex:1">
                    <div class="label-l">Frigate 视觉感知</div>
                    <div class="body-s">接入摄像头人数感知</div>
                  </div>
                  <md-switch id="frigateToggle"></md-switch>
                </div>
                <div class="mode-card" id="visionItem">
                  <div class="mode-card-icon">${ICO.vision}</div>
                  <div style="flex:1">
                    <div class="label-l">LLMVision 增强</div>
                    <div class="body-s">大模型分析摄像头快照</div>
                  </div>
                  <md-switch id="visionToggle"></md-switch>
                </div>
              </div>

              <div id="showroomPanel" style="display:none;background:var(--sa-primary-container);padding:16px;border-radius:16px;border:1px solid var(--sa-primary)">
                <div class="label-m" style="margin-bottom:12px;color:var(--sa-primary);display:flex;align-items:center;gap:8px">
                  ${ICO.showroom} 展厅场景配置
                </div>
                <div id="showroomSceneBtns" class="chip-row" style="margin-bottom:12px"></div>
                <div id="showroomEditPanel" style="display:none;background:var(--sa-card);padding:16px;border-radius:12px;border:1px solid var(--sa-border);margin-bottom:12px">
                  <div class="label-l" id="editSceneTitle" style="margin-bottom:12px">编辑场景</div>
                  <div style="display:grid;gap:12px">
                    <md-outlined-text-field id="editSceneLabel" placeholder="场景标签" style="width:100%"></md-outlined-text-field>
                    <md-outlined-text-field id="editSceneTime" placeholder="虚拟时间 (HH:MM)" style="width:100%"></md-outlined-text-field>
                    <md-outlined-text-field id="editSceneDesc" type="textarea" rows="2" placeholder="场景描述 (传给 AI)" style="width:100%"></md-outlined-text-field>
                    <md-outlined-text-field id="editSceneHint" type="textarea" rows="2" placeholder="AI 行为要点" style="width:100%"></md-outlined-text-field>
                    <div style="display:flex;gap:8px">
                      <md-filled-button id="editSceneSave" style="--md-filled-button-container-height:32px;font-size:13px">保存修改</md-filled-button>
                      <md-outlined-button id="editSceneCancel" style="--md-outlined-button-container-height:32px;font-size:13px">取消</md-outlined-button>
                    </div>
                  </div>
                </div>
                <div style="display:flex;flex-direction:column;gap:6px">
                  <div style="display:flex;align-items:center;gap:6px">
                    <span style="font-size:11px;color:var(--sa-on-surface-variant);white-space:nowrap">指令模式：</span>
                    <div id="sceneModeToggle" style="display:flex;border:1.5px solid var(--sa-outline-variant);border-radius:20px;overflow:hidden;font-size:12px;cursor:pointer;user-select:none">
                      <div id="sceneModeCmd" data-mode="command"
                        style="padding:3px 12px;background:var(--sa-primary);color:var(--sa-on-primary);font-weight:600;transition:.2s">
                        一次性指令
                      </div>
                      <div id="sceneModePersist" data-mode="persist"
                        style="padding:3px 12px;background:transparent;color:var(--sa-on-surface-variant);transition:.2s">
                        持久模式
                      </div>
                    </div>
                    <span id="sceneModeHint" style="font-size:11px;color:var(--sa-primary)">执行一次后自动清空</span>
                  </div>
                  <md-outlined-text-field id="showroomCustomInput" style="width:100%" placeholder="输入指令，如：打开所有展厅灯...">
                    <md-icon slot="leading-icon"><div style="display:flex;align-items:center;height:100%">${ICO.mic}</div></md-icon>
                    <md-icon-button slot="trailing-icon" id="clearCustomScene" title="清空当前场景">
                      ${ICO.close}
                    </md-icon-button>
                  </md-outlined-text-field>
                </div>
              </div>

              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px">
                <div class="sys-card">
                  <div class="label-m">自动执行阈值</div>
                  <div class="sys-val-row">
                    <span class="sys-val-num" id="numAVal">--</span>
                    <span class="sys-val-unit">/ 100</span>
                  </div>
                  <md-slider id="numA" min="50" max="100" step="5" value="80" ticks labeled></md-slider>
                </div>
                <div class="sys-card">
                  <div class="label-m">通知推送阈值</div>
                  <div class="sys-val-row">
                    <span class="sys-val-num" id="numNVal">--</span>
                    <span class="sys-val-unit">/ 100</span>
                  </div>
                  <md-slider id="numN" min="30" max="100" step="5" value="60" ticks labeled></md-slider>
                </div>
              </div>
            </div>
          </div>

          <div class="card" id="priorityCard" style="display:none">
            <div class="card-title" style="justify-content:space-between">
              <span>${ICO.lock} 动作优先级保护</span>
              <span class="body-s" id="priorityCount" style="opacity:.6;font-weight:400"></span>
            </div>
            <div id="priorityList" style="display:grid;gap:6px"></div>
          </div>

          <div class="card">
            <div class="card-title">${ICO.rule} 决策流水</div>
            <div class="log-box" id="lBox">等待系统指令...</div>
          </div>
        </div>

        <!-- ── 系统配置 ── -->
        <div id="view-config" class="tab-view">
          <div id="configArea"></div>
        </div>

        <!-- ── 设备管理 ── -->
        <div id="view-devices" class="tab-view">
          <div class="card" style="margin-bottom:16px">
            <div class="card-title" style="justify-content:space-between">
              <div style="display:flex;align-items:center;gap:8px">
                <span>${ICO.device} 发现新设备</span>
                <md-icon-button id="discoverBtn" title="扫描新设备">${ICO.refresh}</md-icon-button>
                <md-icon-button id="syncToHaBtn" title="同步房间到 HA">${ICO.upload}</md-icon-button>
              </div>
              <div style="display:flex;align-items:center;gap:12px">
                <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer">
                  <md-checkbox id="showOfflineToggle" touch-target="wrapper" style="--md-checkbox-container-shape:2px"></md-checkbox>
                  <span>显示离线</span>
                </label>
                <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer">
                  <md-checkbox id="showIgnoredToggle" touch-target="wrapper" style="--md-checkbox-container-shape:2px"></md-checkbox>
                  <span>显示已忽略</span>
                </label>
                <span id="nCntLbl" class="label-m" style="opacity:.6"></span>
              </div>
            </div>
            <md-outlined-text-field id="newDevSearch" style="width:100%;margin-bottom:12px;" placeholder="搜索设备名称或实体 ID…">
              <md-icon slot="leading-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
              </md-icon>
            </md-outlined-text-field>
            <div class="chip-row" id="devTypeFilter" style="margin-bottom:16px"></div>
            <div id="nTable"></div>
            <div class="chip-row" id="nPager" style="margin-top:12px;justify-content:center"></div>
          </div>

          <div class="card">
            <div class="card-title" style="justify-content:space-between">
              <div style="display:flex;align-items:center;gap:8px">
                <span>${ICO.check} 已配置设备</span>
                <button class="chip" id="filterNoRoomBtn" style="font-size:11px;padding:2px 10px;cursor:pointer;background:var(--md-sys-color-error-container);color:var(--md-sys-color-on-error-container);border:none;border-radius:12px;display:none">⚠ 未分区</button>
              </div>
              <span id="cCntLbl" class="label-m" style="opacity:.6"></span>
            </div>
            <md-outlined-text-field id="cfgDevSearch" style="width:100%;margin-bottom:12px;" placeholder="搜索已配置设备…">
              <md-icon slot="leading-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
              </md-icon>
            </md-outlined-text-field>
            <div class="chip-row" id="cfgRoomFilter" style="margin-bottom:10px;flex-wrap:wrap"></div>
            <div class="chip-row" id="cfgTypeFilter" style="margin-bottom:16px"></div>
            <div id="cTable"></div>
            <div class="chip-row" id="cPager" style="margin-top:12px;justify-content:center"></div>
          </div>
        </div>

        <!-- ── 视觉感知 ── -->
        <div id="view-vision" class="tab-view">
          <!-- 摄像头列表 -->
          <div class="card" style="margin-bottom:16px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
              <div class="card-title" style="margin:0">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="opacity:.7;vertical-align:middle;margin-right:6px"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg>
                Frigate 摄像头管理
              </div>
              <md-filled-button id="vAddCamBtn" style="--md-filled-button-container-height:32px;font-size:13px">＋ 添加摄像头</md-filled-button>
            </div>
            <div id="vCamList" style="display:flex;flex-direction:column;gap:10px">
              <div style="text-align:center;padding:32px;color:var(--md-sys-color-outline);font-size:13px">
                加载中...
              </div>
            </div>
            <div id="vConfigPathHint" style="margin-top:12px;font-size:12px;color:var(--md-sys-color-outline);display:none">
              配置文件：<span id="vConfigPath" style="font-family:monospace"></span>
            </div>
          </div>

          <!-- 添加/编辑摄像头表单（默认隐藏） -->
          <div class="card" id="vCamFormCard" style="display:none">
            <div class="card-title">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="opacity:.7;vertical-align:middle;margin-right:6px"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
              <span id="vFormTitle">添加摄像头</span>
            </div>
            <input type="hidden" id="vEditCameraId">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px">
              <div style="display:flex;flex-direction:column;gap:6px">
                <md-outlined-text-field id="vFriendlyName" placeholder="如：展厅摄像头、门口监控" style="width:100%"></md-outlined-text-field>
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <div class="label-s">对应房间（AI 区域绑定）*</div>
                <md-outlined-select id="vRoom" style="width:100%">
                  <md-select-option value=""><div slot="headline">-- 选择房间 --</div></md-select-option>
                </md-outlined-select>
              </div>
              <div style="display:flex;flex-direction:column;gap:6px;grid-column:1/-1">
                <md-outlined-text-field id="vRtspUrl" placeholder="rtsp://admin:password@192.168.1.x:554/..." style="width:100%;font-family:monospace"></md-outlined-text-field>
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <label class="label-s">最低置信度（min_score）<span id="vMinScoreVal" style="color:var(--sa-primary);margin-left:8px">0.70</span></label>
                <md-slider id="vMinScore" min="0.3" max="0.9" step="0.05" value="0.7"></md-slider>
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <label class="label-s">追踪阈值（threshold）<span id="vThresholdVal" style="color:var(--sa-primary);margin-left:8px">0.85</span></label>
                <md-slider id="vThreshold" min="0.5" max="0.95" step="0.05" value="0.85"></md-slider>
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <div class="label-s">检测帧率（fps）</div>
                <md-outlined-select id="vFps" style="width:100%">
                  <md-select-option value="3"><div slot="headline">3 fps（低功耗）</div></md-select-option>
                  <md-select-option value="5" selected><div slot="headline">5 fps（推荐）</div></md-select-option>
                  <md-select-option value="10"><div slot="headline">10 fps（高精度）</div></md-select-option>
                </md-outlined-select>
              </div>
              <div style="display:flex;align-items:flex-end;gap:10px">
                <md-filled-button id="vSaveCamBtn" style="flex:1">保存并部署</md-filled-button>
                <md-outlined-button id="vCancelCamBtn">取消</md-outlined-button>
              </div>
            </div>
            <div id="vSaveStatus" style="margin-top:12px;font-size:13px;display:none"></div>
          </div>
        </div>

        <!-- ── 画像与规则 ── -->
        <div id="view-profiles" class="tab-view">
          <!-- 设备名称查询工具 -->
          <div class="card" style="margin-bottom:16px">
            <div style="display:flex;align-items:center;justify-content:space-between;cursor:pointer" id="devLookupToggle">
              <div class="card-title" style="margin:0">
                ${ICO.search} 设备名称查询
                <span style="font-size:12px;font-weight:400;color:var(--md-sys-color-outline);margin-left:8px">
                  写规则时可用中文名，无需记 entity_id
                </span>
              </div>
              <span id="devLookupArrow" style="font-size:18px;transition:transform .2s;color:var(--md-sys-color-outline)">▼</span>
            </div>
            <div id="devLookupPanel" style="display:none;margin-top:12px">
              <div style="display:flex;gap:8px;margin-bottom:10px">
                <input type="text" class="input" id="devLookupInput" placeholder="输入中文名称（如：展厅中间灯、茶台灯光）...">
              </div>
              <div id="devLookupResults" style="font-size:13px;color:var(--md-sys-color-on-surface-variant)">
                <span style="opacity:.6">输入关键词即可搜索</span>
              </div>
              <div style="margin-top:8px;padding:8px 10px;background:var(--md-sys-color-surface-container);border-radius:8px;font-size:12px;line-height:1.7;color:var(--md-sys-color-outline)">
                💡 规则写法示例（直接用中文名，AI 自动对应 entity_id）：<br>
                &nbsp;&nbsp;• <b>展厅中间灯 无人时关闭，其他灯降低亮度至 30%</b><br>
                &nbsp;&nbsp;• <b>茶台灯光 有客人时保持色温 4000K 亮度 80%</b><br>
                &nbsp;&nbsp;• <b>8:30-18:00 前台无人2分钟 → 关闭展厅中间灯，其他灯降亮 30%</b>
              </div>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:20px">
            <div class="card">
              <div class="card-title">${ICO.profile} 用户生活习惯 (P1)</div>
              <div style="display:flex;gap:12px;margin-bottom:16px">
                <md-outlined-text-field id="hInput" style="flex:1" placeholder="描述您的偏好习惯（可用中文设备名）..."></md-outlined-text-field>
                <md-filled-button id="addHBtn" style="--md-filled-button-container-height:32px;font-size:13px;white-space:nowrap">添加</md-filled-button>
              </div>
              <div id="hList" class="m3-list"></div>
            </div>
            <div class="card">
              <div class="card-title">${ICO.rule} 推理增强规则 (P1)</div>
              <div style="display:flex;gap:12px;margin-bottom:16px">
                <md-outlined-text-field id="rInput" style="flex:1" placeholder="设定推理规则（可用中文设备名）..."></md-outlined-text-field>
                <md-filled-button id="addRBtn" style="--md-filled-button-container-height:32px;font-size:13px;white-space:nowrap">添加</md-filled-button>
              </div>
              <div id="rList" class="m3-list"></div>
            </div>
          </div>

          <!-- AI 学习已改为基线偏好学习（device_baseline），不再生成 P3 规则 -->
        </div>

        <!-- ── 行为习惯 ── -->
        <div id="view-habits" class="tab-view">
          <div class="card">
            <div class="hab-page">
              <div class="hab-page-header">
                <div class="hab-title-row">
                  <div class="hab-page-title">
                    ${ICO.schedule} 行为习惯管理
                    <span class="hab-title-badge">AI 自动学习 P2</span>
                  </div>
                  <div id="habitStatRow" class="hab-stat-row"></div>
                </div>

                <div class="hab-toolbar">
                  <md-outlined-text-field id="habSearch" style="flex:1;min-width:160px" placeholder="搜索设备名称或 entity_id...">
                    <md-icon slot="leading-icon">${ICO.search}</md-icon>
                  </md-outlined-text-field>
                  <div class="hab-toolbar-right">
                    <md-outlined-select id="habSort" style="width:140px">
                      <md-select-option value="conf" selected><div slot="headline">置信度↓</div></md-select-option>
                      <md-select-option value="time"><div slot="headline">时间</div></md-select-option>
                      <md-select-option value="name"><div slot="headline">设备名</div></md-select-option>
                    </md-outlined-select>
                    <button id="habGroupBtn" class="hab-group-btn active" title="按设备分组">
                      ${ICO.group} 按设备
                    </button>
            </div>
            </div>

                <div id="habDomainFilter" class="chip-row"></div>
          </div>

              <div class="hab-info-banner">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                <div class="body-s">系统自动提取的规律将在无传感器时作为决策依据。支持按设备分组查看，未来多区域、多设备场景下可按类型筛选。</div>
        </div>

              <div id="habitPatTable"></div>
            </div>
          </div>
        </div>

        <!-- ── AI 场景 ── -->
        <div id="view-aiscenes" class="tab-view">
          <div class="card">
            <div class="card-title" style="justify-content:space-between;flex-wrap:wrap;gap:8px">
              <span id="aiScenesTitle" style="display:flex;align-items:center;gap:8px">AI 场景管理</span>
              <div style="display:flex;align-items:center;gap:8px">
                <md-filled-button id="runAnalysisBtn" style="--md-filled-button-container-height:32px;font-size:13px">
                  🔍 立即分析
                </md-filled-button>
                <span class="body-s" style="opacity:.6">每日凌晨自动更新</span>
              </div>
            </div>
            <div class="hab-info-banner" style="margin-bottom:20px">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
              <div class="body-s">
                AI 从历史行为中挖掘多设备联动规律（需 ≥ 2 天重复出现 ≥ 2 个设备同时动作），达到置信度阈值后生成候选场景。
                <strong>确认</strong>后场景将加入 AI 推理上下文；<strong>拒绝</strong>后不再推荐同名场景。<br>
                <span style="color:var(--sa-primary);font-weight:500">💡 数据积累不足时点击「立即分析」手动触发，无需等到凌晨。</span>
              </div>
            </div>
            <!-- 一句话创建场景 -->
            <div id="aiSceneCreatePanel" style="margin-bottom:20px;border:1px solid var(--sa-border);border-radius:var(--sa-shape-md);overflow:hidden">
              <button id="aiSceneCreateToggle" style="width:100%;padding:10px 16px;background:var(--sa-bg);border:none;cursor:pointer;text-align:left;font-size:13px;font-weight:500;color:var(--sa-primary);display:flex;align-items:center;gap:6px">
                ＋ 用自然语言创建场景
              </button>
              <div id="aiSceneCreateBody" style="display:none;padding:16px;background:var(--sa-card)">
                <div class="body-s" style="color:var(--sa-text-variant);margin-bottom:10px">
                  描述你想要的场景，AI 会自动解析设备、时段和星期。
                </div>
                <textarea id="aiSceneCreateText"
                  placeholder="例如：下午 2 点到 6 点，工作日，打开客厅的灯和空调，亮度 80%，温度 24 度"
                  style="width:100%;min-height:80px;padding:10px;border:1px solid var(--sa-border);border-radius:var(--sa-shape-sm);background:var(--sa-bg);color:var(--sa-text);font-size:13px;resize:vertical;box-sizing:border-box;font-family:inherit"></textarea>
                <div style="display:flex;align-items:center;gap:12px;margin-top:10px;flex-wrap:wrap">
                  <md-filled-button id="aiSceneParseBtn" style="--md-filled-button-container-height:32px;font-size:13px">
                    🤖 AI 解析生成
                  </md-filled-button>
                  <label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;color:var(--sa-text-variant)">
                    <input type="checkbox" id="aiSceneAutoActivate" style="accent-color:var(--sa-primary)">
                    直接激活（跳过审批）
                  </label>
                </div>
                <!-- 解析结果预览 -->
                <div id="aiSceneCreatePreview" style="display:none;margin-top:12px;padding:10px 12px;background:var(--sa-primary-container);border-radius:var(--sa-shape-sm);color:var(--sa-on-primary-container)"></div>
                <div style="display:flex;gap:8px;margin-top:10px">
                  <md-filled-button id="aiSceneConfirmBtn" style="display:none;--md-filled-button-container-height:32px;font-size:13px">
                    ✓ 完成
                  </md-filled-button>
                  <md-outlined-button id="aiSceneCreateCancel" style="display:none;--md-outlined-button-container-height:32px;font-size:13px">
                    ✗ 取消
                  </md-outlined-button>
                </div>
              </div>
            </div>
            <!-- 待确认 -->
            <div style="margin-bottom:24px">
              <div class="label-l" style="margin-bottom:12px;display:flex;align-items:center;gap:8px;color:var(--sa-primary)">
                待确认候选场景
                <span id="aiScenesPendingBadge" class="hab-title-badge" style="background:var(--sa-primary-container);color:var(--sa-primary)">0</span>
              </div>
              <div id="aiScenesPending"></div>
            </div>
            <!-- 已激活 -->
            <div style="margin-bottom:24px">
              <div class="label-l" style="margin-bottom:12px;display:flex;align-items:center;gap:8px;color:var(--sa-succ)">
                已激活场景
                <span id="aiScenesActiveBadge" class="hab-title-badge" style="background:var(--sa-succ-container);color:var(--sa-succ)">0</span>
              </div>
              <div id="aiScenesActive"></div>
            </div>
            <!-- 已拒绝 -->
            <div>
              <div class="label-l" style="margin-bottom:12px;display:flex;align-items:center;gap:8px;color:var(--sa-text-variant)">
                已拒绝场景
                <span id="aiScenesRejectedBadge" class="hab-title-badge">0</span>
              </div>
              <div id="aiScenesRejected"></div>
            </div>
          </div>
        </div>

        <!-- ── 纠错学习 ── -->
        <div id="view-corrections" class="tab-view">
          <div class="card">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px">
              <div class="card-title" style="margin-bottom:0">
                🎯 纠错学习
              </div>
              <div style="display:flex;gap:8px">
                <md-filled-tonal-button id="corrFilterAll" style="--md-filled-tonal-button-container-height:32px;font-size:13px">全部</md-filled-tonal-button>
                <md-filled-tonal-button id="corrFilterFresh" class="dim" style="--md-filled-tonal-button-container-height:32px;font-size:13px">待处理(30分钟)</md-filled-tonal-button>
                <md-outlined-button id="corrClearAll" style="--md-outlined-button-container-height:32px;font-size:13px;color:var(--sa-error)">清空全部</md-outlined-button>
              </div>
            </div>
            <div class="body-s" style="opacity:.6;margin-bottom:16px;line-height:1.6">
              此处记录 AI 最近控制过的设备。点击 <b>🎯 纠正</b> 立即撤销并告知 AI 此操作有误；
              点击 <b>✕ 忽略</b> 表示该操作没问题、不需要纠正。<br>
              <b>超过 30 分钟</b>的记录会自动隐藏（纠正窗口已过期）；纠正操作将直接更新设备使用基线，AI 下次巡检即生效。
            </div>
            <div id="corrList" style="display:flex;flex-direction:column;gap:12px">
              <div style="opacity:.5;text-align:center;padding:32px">正在加载...</div>
            </div>
          </div>
        </div>

        <!-- ── AI 看板（5D-3）── -->
        <div id="view-transactions" class="tab-view">
          <!-- 今日决策统计卡片 -->
          <div class="card" id="decisionStatsCard">
            <div class="card-title" style="justify-content:space-between;flex-wrap:wrap">
              <span>📊 AI 决策看板</span>
              <span class="body-s" style="opacity:.6">今日 AI 决策概览</span>
            </div>
            <div id="decisionStatsContent" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:4px 0 8px">
              <div style="opacity:.5;text-align:center;grid-column:1/-1">加载中...</div>
            </div>
          </div>
          <!-- 按房间推翻率 -->
          <div class="card" id="roomOverturnCard">
            <div class="card-title">📍 按房间推翻率（近30天）</div>
            <div id="roomOverturnList" style="display:flex;flex-direction:column;gap:6px"></div>
          </div>
          <!-- 执行记录（原有内容，保留调试用途） -->
          <div class="card">
            <div class="card-title" style="justify-content:space-between;flex-wrap:wrap">
              <span>📋 执行记录（最近50条）</span>
              <span class="body-s" style="opacity:.6">支持一键回滚</span>
            </div>
            <div id="txnList" style="display:flex;flex-direction:column;gap:10px"></div>
          </div>
        </div>

        <!-- ── 能耗分析 ── -->
        <div id="view-energy" class="tab-view">
          <div class="card">
            <div class="card-title" style="justify-content:space-between;flex-wrap:wrap">
              <span>⚡ 能耗分析（近 7 天）</span>
              <span class="body-s" style="opacity:.6">基于设备状态历史 + 存在感传感器，识别无人浪费</span>
            </div>
            <div id="energyList" style="display:flex;flex-direction:column;gap:10px">
              <div style="opacity:.5;padding:16px 0;text-align:center">加载中...</div>
            </div>
          </div>
        </div>

        <!-- ── 系统日志 ── -->
        <div id="view-syslog" class="tab-view">
          <div class="card">
            <div class="card-title" style="justify-content:space-between;flex-wrap:wrap;gap:8px">
              <span>${ICO.calendar} 系统运行日志流水</span>
              <div class="body-s" id="sysLogInfo" style="opacity:.6;font-weight:400">实时模式 — 自动刷新最近500条</div>
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                  <md-outlined-select id="sysLogDate" style="min-width:220px">
                    <md-select-option value="live"><div slot="headline">实时流水</div></md-select-option>
                  </md-outlined-select>
                <md-outlined-button id="sysLogRefresh" title="刷新日期列表" style="--md-outlined-button-container-height:32px;font-size:13px">${ICO.refresh}</md-outlined-button>
                <md-outlined-button id="sysLogDl" style="--md-outlined-button-container-height:32px;font-size:13px">↓ 下载</md-outlined-button>
              </div>
            </div>
            <!-- 搜索 + 统计条 -->
            <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap">
              <md-outlined-text-field id="sysLogSearch" style="flex:1;min-width:200px" placeholder="关键词搜索（Esc 清除）">
                <md-icon slot="leading-icon"><div style="display:flex;align-items:center;height:100%">${ICO.search}</div></md-icon>
              </md-outlined-text-field>
              <div id="sysLogStats" style="display:flex;gap:6px;align-items:center;font-size:12px;opacity:.8">
                <span id="statTotal" style="color:var(--sa-text-variant)">共 0 条</span>
                <span id="statErr"   style="color:var(--sa-err);display:none">● 错误 0</span>
                <span id="statWarn"  style="color:#f59e0b;display:none">● 警告 0</span>
                <span id="statInfo"  style="color:var(--sa-primary);display:none">● 信息 0</span>
              </div>
            </div>
            <div class="chip-row" style="margin-bottom:12px">
              <md-filter-chip label="全部" selected data-filter="all"></md-filter-chip>
              <md-filter-chip label="INFO" data-filter="INFO"></md-filter-chip>
              <md-filter-chip label="WARN" data-filter="WARN"></md-filter-chip>
              <md-filter-chip label="ERROR" data-filter="ERROR"></md-filter-chip>
              <md-filter-chip label="运行保护" data-filter="protect"></md-filter-chip>
              <md-filter-chip label="传感器事件" data-filter="trigger"></md-filter-chip>
            </div>
            <div class="log-box" id="sysLogBox">正在连接日志服务...</div>
          </div>
        </div>

        <!-- ── 新页面占位（第2批实现） ── -->
        <div id="view-rooms" class="tab-view">
          <div class="empty-state" style="margin-top:40px">
            <div class="empty-state-icon">🗺️</div>
            <div class="empty-state-title">房间拓扑配置</div>
            <div class="empty-state-desc">正在加载...</div>
          </div>
        </div>
        <div id="view-patrol" class="tab-view">
          <div class="empty-state" style="margin-top:40px">
            <div class="empty-state-icon">🔍</div>
            <div class="empty-state-title">巡检配置</div>
            <div class="empty-state-desc">正在加载...</div>
          </div>
        </div>
        <div id="view-backup" class="tab-view">
          <div class="empty-state" style="margin-top:40px">
            <div class="empty-state-icon">💾</div>
            <div class="empty-state-title">备份与恢复</div>
            <div class="empty-state-desc">正在加载...</div>
          </div>
        </div>
        <div id="view-mcp" class="tab-view">
          <div class="empty-state" style="margin-top:40px">
            <div class="empty-state-icon">🔌</div>
            <div class="empty-state-title">MCP 服务</div>
            <div class="empty-state-desc">正在加载...</div>
          </div>
        </div>
        <div id="view-license" class="tab-view">
          <div class="empty-state" style="margin-top:40px">
            <div class="empty-state-icon">🔑</div>
            <div class="empty-state-title">License 管理</div>
            <div class="empty-state-desc">正在加载...</div>
          </div>
        </div>

        <div class="version" id="appVersion">SmartAgent — Material Design 3 Edition</div>
      </div>
      <div id="toast"></div>
      
      <!-- ── M3 通用确认弹窗 (md-dialog) ── -->
      <md-dialog id="m3ConfirmDialog">
        <div slot="headline" id="m3ConfirmTitle">确认操作</div>
        <div slot="content" id="m3ConfirmBody">确认执行此操作吗？</div>
        <div slot="actions">
          <md-text-button id="m3ConfirmCancel">取消</md-text-button>
          <md-filled-tonal-button id="m3ConfirmOk">确定</md-filled-tonal-button>
        </div>
      </md-dialog>

      <!-- ── 设备编辑弹窗 ── -->
      <div class="m3-dialog-overlay" id="m3EditDevOverlay">
        <div class="m3-dialog" style="width:min(440px,92vw);border-radius:20px">
          <div class="m3-dialog-title" style="display:flex;align-items:center;gap:8px">
            ${ICO.edit} 编辑设备信息
          </div>
          <div style="display:flex;flex-direction:column;gap:14px;margin-bottom:20px">
            <div>
              <md-outlined-text-field id="editDevName" style="width:100%"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-l" style="margin-bottom:4px">所属房间</div>
              <div style="display:flex;gap:6px">
                <md-outlined-select id="editDevRoomSel" style="flex:1"></md-outlined-select>
                <md-outlined-text-field id="editDevRoomCustom" placeholder="或手动输入…" style="flex:1"></md-outlined-text-field>
              </div>
            </div>
            <div>
              <div class="label-l" style="margin-bottom:4px">设备类型</div>
              <md-outlined-select id="editDevType" style="width:100%">
                <md-select-option value=""><div slot="headline">自动识别</div></md-select-option>
                <md-select-option value="light"><div slot="headline">灯光 (light)</div></md-select-option>
                <md-select-option value="switch"><div slot="headline">开关 (switch)</div></md-select-option>
                <md-select-option value="climate"><div slot="headline">空调 (climate)</div></md-select-option>
                <md-select-option value="cover"><div slot="headline">窗帘 (cover)</div></md-select-option>
                <md-select-option value="fan"><div slot="headline">风扇 (fan)</div></md-select-option>
                <md-select-option value="sensor"><div slot="headline">传感器 (sensor)</div></md-select-option>
                <md-select-option value="binary_sensor"><div slot="headline">二进制传感器</div></md-select-option>
                <md-select-option value="media_player"><div slot="headline">媒体播放器</div></md-select-option>
              </md-outlined-select>
            </div>
          </div>
          <div class="m3-dialog-actions">
            <md-outlined-button id="m3EditDevCancel" style="--md-outlined-button-container-height:32px;font-size:13px">取消</md-outlined-button>
            <md-filled-button id="m3EditDevSave" style="--md-filled-button-container-height:32px;font-size:13px">保存</md-filled-button>
          </div>
        </div>
      </div>

      <!-- Zone 房间绑定弹窗 — 放在 DOM 最末尾，确保 z-index 覆盖所有内容 -->
      <div class="help-overlay" id="zoneBindOverlay">
        <div style="background:var(--sa-card);border-radius:20px;padding:24px;min-width:340px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.24)">
          <div style="font-size:17px;font-weight:600;margin-bottom:4px">区域房间绑定</div>
          <div id="zoneBindDesc" style="font-size:13px;color:var(--sa-text-variant);margin-bottom:16px"></div>
          <div id="zoneBindRows" style="margin-bottom:4px"></div>
          <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:16px">
            <md-outlined-button id="zoneBindCancel" style="--md-outlined-button-container-height:32px;font-size:13px">取消</md-outlined-button>
            <md-filled-button id="zoneBindSave" style="--md-filled-button-container-height:32px;font-size:13px">保存绑定</md-filled-button>
          </div>
        </div>
      </div>`;

    const _warnReadOnly = () => this._warnHaFallbackReadOnly();
    if (SA_HA_FALLBACK_READONLY) {
      this._disableHaFallbackWriteControls(this.shadowRoot, [
        "#aiBtn",
        "#learningModeToggle",
        "#habitProactiveToggle",
        "#frigateToggle",
        "#visionToggle",
        "#batchFabRoom",
        "#batchFabAi",
        "#batchFabHa",
        "#batchFabDel",
        "#editSceneSave",
        "#modeSel",
        "#numA",
        "#numN",
        "#discoverBtn",
        "#syncToHaBtn",
        "#vAddCamBtn",
        "#vSaveCamBtn",
        "#vCancelCamBtn",
        "#addHBtn",
        "#addRBtn",
        "#runAnalysisBtn",
        "#aiSceneParseBtn",
        "#aiSceneConfirmBtn",
        "#aiSceneCreateCancel",
        "#corrClearAll",
        "#m3EditDevSave",
        "#zoneBindSave",
        ".single-del-btn",
        ".single-edit-btn",
        ".txn-rollback",
        ".corr-correct-btn",
        ".corr-dismiss-btn",
        ".corr-dismiss-scene",
        ".ai-scene-approve",
        ".ai-scene-reject",
        ".ai-scene-trigger",
        ".ai-scene-delete",
        "#writeYaml",
        "[data-action='edit']",
        "[data-action='zones']",
        "[data-action='delete']"
      ].join(","));
    }

    // 主 Tab 事件绑定：有 data-group 的是分组 Tab，有 data-t 的是直接 Tab
    this.shadowRoot.querySelectorAll(".nav-tab").forEach(b => {
      b.onclick = () => {
        if (b.dataset.group) this._setGroup(b.dataset.group);
        else if (b.dataset.t) this._setTab(b.dataset.t);
      };
    });
    // 子 Tab 事件绑定
    this.shadowRoot.querySelectorAll(".nav-sub-tab").forEach(b => {
      b.onclick = () => { if (b.dataset.t) this._setTab(b.dataset.t); };
    });
    this.shadowRoot.querySelectorAll("md-filter-chip[data-filter]").forEach(b => b.addEventListener("click", () => {
      this._sysLogFilter = b.dataset.filter;
      this.shadowRoot.querySelectorAll("md-filter-chip[data-filter]").forEach(x => {
        x.selected = (x.dataset.filter === this._sysLogFilter);
      });
      this._applySysLogFilter();
    }));
    
    $("sysLogDate").onchange = (e) => this._onLogDateChange(e.target.value);
    $("sysLogDl").onclick = () => this._downloadSysLog();
    $("sysLogRefresh").onclick = () => { this._loadLogDates(); this._wsRefreshSysLog(); };
    $("sysLogSearch").oninput = (e) => {
      this._sysLogKeyword = e.target.value.toLowerCase().trim();
      this._applySysLogFilter();
    };
    $("sysLogSearch").onkeydown = (e) => {
      if (e.key === "Escape") {
        e.target.value = "";
        this._sysLogKeyword = "";
        this._applySysLogFilter();
      }
    };
    $("aiBtn").onclick = () => {
      if (SA_HA_FALLBACK_READONLY) {
        _warnReadOnly();
        return;
      }
      this._toggle();
    };

    $("learningModeToggle").addEventListener("change", async (e) => {
      if (SA_HA_FALLBACK_READONLY) {
        e.target.selected = !e.target.selected;
        _warnReadOnly();
        return;
      }
      const on = e.target.selected;
      await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_learning_mode" });
      this._msg(on ? "静默学习模式已开启" : "静默学习模式已关闭");
    });

    $("habitProactiveToggle").addEventListener("change", async (e) => {
      if (SA_HA_FALLBACK_READONLY) {
        e.target.selected = !e.target.selected;
        _warnReadOnly();
        return;
      }
      const on = e.target.selected;
      await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_habit_proactive" });
      this._msg(on ? "习惯主动询问已开启" : "习惯主动询问已关闭");
    });

    $("frigateToggle").addEventListener("change", async (e) => {
      if (SA_HA_FALLBACK_READONLY) {
        e.target.selected = !e.target.selected;
        _warnReadOnly();
        return;
      }
      const on = e.target.selected;
      await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_frigate_enabled" });
      this._msg(on ? "Frigate NVR 视觉感知已启用" : "Frigate NVR 视觉感知已关闭");
    });

    $("visionToggle").addEventListener("change", async (e) => {
      if (SA_HA_FALLBACK_READONLY) {
        e.target.selected = !e.target.selected;
        _warnReadOnly();
        return;
      }
      const on = e.target.selected;
      await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_vision_enabled" });
      this._msg(on ? "LLMVision 视觉增强已开启" : "LLMVision 视觉增强已关闭");
    });

    // 剪贴板兼容辅助函数（非HTTPS或旧浏览器降级方案）
    const _fallbackCopy = (text) => {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.cssText = "position:fixed;left:-9999px;top:-9999px;opacity:0";
        document.body.appendChild(ta);
        ta.focus(); ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      } catch (err) {
        console.warn("SmartAgent: 复制失败", err);
      }
    };

    // ── 视觉感知（Frigate 摄像头管理）逻辑 ───────────────────────

    /** 摄像头列表缓存，供事件委托查找完整摄像头对象 */
    let _visionCamsCache = [];

    /** 渲染摄像头列表 */
    const _renderVisionCams = (cameras, configPath) => {
      _visionCamsCache = cameras || [];
      const list = $("vCamList");
      if (!list) return;
      if (configPath) {
        const hint = $("vConfigPathHint"), pathEl = $("vConfigPath");
        if (hint) hint.style.display = "";
        if (pathEl) pathEl.textContent = configPath;
      }
      if (!_visionCamsCache.length) {
        list.innerHTML = `<div style="text-align:center;padding:32px;color:var(--md-sys-color-outline);font-size:13px">
          暂无摄像头配置，点击「添加摄像头」开始</div>`;
        return;
      }
      list.innerHTML = _visionCamsCache.map(c => {
        const room = c.room || "";
        const roomBadge = room
          ? `<span style="background:var(--sa-primary-container);color:var(--sa-primary);padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600">${this._esc(room)}</span>`
          : `<span style="background:var(--md-sys-color-surface-container);color:var(--md-sys-color-outline);padding:2px 8px;border-radius:12px;font-size:12px">未绑定房间</span>`;
        const rtspMasked = (c.rtsp_url || "").replace(/:([^@]+)@/, ":***@");
        const zoneCount = (c.zones || []).length;
        const zoneHint = zoneCount
          ? `<span style="color:var(--md-sys-color-outline);font-size:12px;margin-left:4px">${zoneCount} 个区域</span>`
          : "";
        return `<div class="m3-item" style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--md-sys-color-surface-container);border-radius:12px">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor" style="color:var(--sa-primary);flex-shrink:0"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg>
          <div class="m3-content" style="flex:1;min-width:0">
            <div class="m3-title" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              ${this._esc(c.friendly_name || c.camera_id)}
              ${roomBadge}
              ${zoneHint}
            </div>
            <div class="m3-subtitle" style="font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(rtspMasked)}</div>
            <div class="body-s" style="margin-top:2px">
              ID: ${this._esc(c.camera_id)} · min_score: ${(c.min_score||0.7).toFixed(2)} · fps: ${c.fps||5}
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
            ${zoneCount ? `<md-outlined-button style="--md-outlined-button-container-height:32px;font-size:13px" data-action="zones" data-cam-id="${this._esc(c.camera_id)}">区域绑定</md-outlined-button>` : ""}
            <md-outlined-button style="--md-outlined-button-container-height:32px;font-size:13px" data-action="edit" data-cam-id="${this._esc(c.camera_id)}">编辑</md-outlined-button>
            <md-filled-button class="btn-error" style="--md-filled-button-container-height:32px;font-size:13px" data-action="delete" data-cam-id="${this._esc(c.camera_id)}">删除</md-filled-button>
          </div>
        </div>`;
      }).join("");
    };

    /** 加载摄像头列表 */
    const _loadVisionCams = async () => {
      try {
        const result = await this._hass.callWS({ type: "smart_agent/get_frigate_cameras" });
        _renderVisionCams(result?.cameras || [], result?.config_path || "");
      } catch (e) {
        const list = $("vCamList");
        if (list) list.innerHTML = `<div style="text-align:center;padding:20px;color:var(--md-sys-color-error);font-size:13px">加载失败，请确认 Frigate 已安装：${e.message||e}</div>`;
      }
    };

    /** 填充房间下拉列表（合并 SmartAgent 已有房间 + HA area_registry） */
    const _populateVisionRooms = (selectedRoom) => {
      const sel = $("vRoom");
      if (!sel) return;
      // 清空旧选项（保留第一个占位项）
      while (sel.options.length > 1) sel.remove(1);
      // SmartAgent 设备中的房间
      const devices = this._wsGet("devices", "devices", []);
      const smRooms = devices.map(d => d.room || "").filter(r => r);
      // HA area_registry 中的区域
      const haAreas = this._hass.areas
        ? Object.values(this._hass.areas).map(a => a.name)
        : [];
      const allRooms = [...new Set([...haAreas, ...smRooms])].sort((a, b) => a.localeCompare(b, "zh"));
      allRooms.forEach(r => {
        const opt = document.createElement("option");
        opt.value = r; opt.textContent = r;
        sel.appendChild(opt);
      });
      if (selectedRoom) sel.value = selectedRoom;
    };

    /** 显示添加/编辑表单 */
    const _showVisionForm = (cam) => {
      const card = $("vCamFormCard");
      if (!card) return;
      card.style.display = "";
      $("vFormTitle").textContent = cam ? "编辑摄像头" : "添加摄像头";
      $("vEditCameraId").value = cam?.camera_id || "";
      $("vFriendlyName").value = cam?.friendly_name || "";
      _populateVisionRooms(cam?.room || "");
      $("vRtspUrl").value = cam?.rtsp_url || "";
      $("vMinScore").value = cam?.min_score ?? 0.7;
      $("vMinScoreVal").textContent = parseFloat(cam?.min_score ?? 0.7).toFixed(2);
      $("vThreshold").value = cam?.threshold ?? 0.85;
      $("vThresholdVal").textContent = parseFloat(cam?.threshold ?? 0.85).toFixed(2);
      $("vFps").value = String(cam?.fps ?? 5);
      const status = $("vSaveStatus");
      if (status) status.style.display = "none";
      card.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    /** 隐藏表单 */
    const _hideVisionForm = () => {
      const card = $("vCamFormCard");
      if (card) card.style.display = "none";
    };

    // 滑块实时更新数值
    if ($("vMinScore")) $("vMinScore").oninput = () => { $("vMinScoreVal").textContent = parseFloat($("vMinScore").value).toFixed(2); };
    if ($("vThreshold")) $("vThreshold").oninput = () => { $("vThresholdVal").textContent = parseFloat($("vThreshold").value).toFixed(2); };

    // 添加按钮
    if ($("vAddCamBtn")) $("vAddCamBtn").onclick = () => _showVisionForm(null);
    // 取消按钮
    if ($("vCancelCamBtn")) $("vCancelCamBtn").onclick = _hideVisionForm;

    // 保存并部署
    if ($("vSaveCamBtn")) $("vSaveCamBtn").onclick = async () => {
      const name = ($("vFriendlyName")?.value || "").trim();
      const rtsp = ($("vRtspUrl")?.value || "").trim();
      const room = ($("vRoom")?.value || "").trim();
      if (!name || !rtsp) { this._msg("请填写摄像头名称和 RTSP 地址"); return; }

      const status = $("vSaveStatus");
      const btn = $("vSaveCamBtn");
      btn.disabled = true;
      btn.textContent = "部署中...";
      if (status) { status.style.display = ""; status.style.color = "var(--md-sys-color-outline)"; status.textContent = "⏳ 正在写入 Frigate 配置并重启 Add-on，约需 10-20 秒..."; }

      try {
        const camId = ($("vEditCameraId")?.value || "").trim();
        await this._callService("smart_agent", "register_frigate_camera", {
          friendly_name: name,
          rtsp_url: rtsp,
          room: room,
          camera_id: camId || undefined,
          min_score: parseFloat($("vMinScore")?.value || "0.7"),
          threshold: parseFloat($("vThreshold")?.value || "0.85"),
          fps: parseInt($("vFps")?.value || "5"),
        });
        if (status) { status.style.color = "var(--md-sys-color-primary)"; status.textContent = "✅ 配置已部署，Frigate 正在重启生效（约 15 秒）"; }
        this._msg(`摄像头「${name}」已部署${room ? "，绑定房间：" + room : ""}`);
        setTimeout(async () => {
          _hideVisionForm();
          await _loadVisionCams();
        }, 2000);
      } catch (e) {
        if (status) { status.style.color = "var(--md-sys-color-error)"; status.textContent = "❌ 部署失败：" + (e.message || e); }
        this._msg("部署失败：" + (e.message || e));
      } finally {
        btn.disabled = false;
        btn.textContent = "保存并部署";
      }
    };

    // ── Zone 房间绑定弹窗 ──────────────────────────────────────────────

    /** 构建房间下拉选项 HTML */
    const _roomOptions = (selected) => {
      const devices = this._wsGet("devices", "devices", []);
      const smRooms = devices.map(d => d.room || "").filter(r => r);
      const haAreas = this._hass.areas
        ? Object.values(this._hass.areas).map(a => a.name)
        : [];
      const allRooms = [...new Set([...haAreas, ...smRooms])].sort((a, b) => a.localeCompare(b, "zh"));
      return `<option value="">-- 未绑定 --</option>` +
        allRooms.map(r => `<option value="${this._esc(r)}"${r === selected ? " selected" : ""}>${this._esc(r)}</option>`).join("");
    };

    /** 显示 zone 绑定弹窗（使用预定义模板节点，与 helpOverlay 同级，确保层级正确） */
    const _zoneOverlay = $("zoneBindOverlay");
    const _zoneDesc = $("zoneBindDesc");
    const _zoneRows = $("zoneBindRows");
    const _zoneSaveBtn = $("zoneBindSave");
    const _zoneCancelBtn = $("zoneBindCancel");

    const _closeZoneOverlay = () => _zoneOverlay?.classList.remove("open");

    if (_zoneCancelBtn) _zoneCancelBtn.onclick = _closeZoneOverlay;
    if (_zoneOverlay) _zoneOverlay.onclick = (ev) => { if (ev.target === _zoneOverlay) _closeZoneOverlay(); };

    const _showZoneBindDialog = async (camId) => {
      const cam = _visionCamsCache.find(c => c.camera_id === camId);
      if (!cam || !_zoneOverlay) return;

      // 尝试从后端获取最新 zone 列表（含已绑定房间）
      let zones = cam.zones || [];
      try {
        const r = await this._hass.callWS({ type: "smart_agent/get_frigate_zones", camera_id: camId });
        if (r?.zones?.length) zones = r.zones;
      } catch (_) {}

      if (!zones.length) {
        this._msg("该摄像头暂无检测区域（zone），请先在 Frigate 中配置 zones");
        return;
      }

      // 填充弹窗内容
      if (_zoneDesc) {
        _zoneDesc.innerHTML = `摄像头：<strong>${this._esc(cam.friendly_name || camId)}</strong>（${this._esc(camId)}）<br>
          为每个检测区域单独指定对应的房间，AI 将按进入的具体区域触发正确房间的设备`;
      }

      if (_zoneRows) {
        _zoneRows.innerHTML = zones.map((z) => {
          const displayName = (z.friendly_name && z.friendly_name !== z.zone_id)
            ? z.friendly_name : z.zone_id;
          const isRawId = !z.friendly_name || z.friendly_name === z.zone_id;
          return `
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
              <div style="flex:0 0 150px;font-size:14px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${this._esc(z.zone_id)}">
                ${this._esc(displayName)}
                ${isRawId
                  ? `<div style="font-size:10px;color:var(--md-sys-color-outline);font-weight:400">未设中文名</div>`
                  : `<div style="font-size:10px;color:var(--md-sys-color-outline)">${this._esc(z.zone_id)}</div>`}
              </div>
              <select data-zone-id="${this._esc(z.zone_id)}" data-zone-name="${this._esc(z.friendly_name || z.zone_id)}"
                style="flex:1;padding:6px 10px;border:1px solid var(--md-sys-color-outline-variant);border-radius:8px;font-size:13px;background:var(--md-sys-color-surface-container);color:var(--md-sys-color-on-surface)">
                ${_roomOptions(z.room || "")}
              </select>
            </div>`;
        }).join("");
      }

      // 绑定保存逻辑（每次打开重新绑定，防止 camId 闭包陈旧）
      if (_zoneSaveBtn) {
        _zoneSaveBtn.onclick = async () => {
          if (this._isHaFallbackReadOnly()) {
            this._warnHaFallbackReadOnly();
            return;
          }
          _zoneSaveBtn.disabled = true;
          _zoneSaveBtn.textContent = "保存中…";
          const rows = _zoneRows.querySelectorAll("[data-zone-id]");
          let ok = 0, fail = 0;
          for (const sel of rows) {
            try {
              await this._hass.callWS({
                type: "smart_agent/save_frigate_zone",
                camera_id: camId,
                zone_id: sel.dataset.zoneId,
                friendly_name: sel.dataset.zoneName,
                room: sel.value,
              });
              ok++;
            } catch (_) { fail++; }
          }
          _zoneSaveBtn.disabled = false;
          _zoneSaveBtn.textContent = "保存绑定";
          _closeZoneOverlay();
          this._msg(fail ? `保存完成（${ok} 成功，${fail} 失败）` : `已保存 ${ok} 个区域绑定`);
          await _loadVisionCams();
        };
      }

      _zoneOverlay.classList.add("open");
    };

    // 编辑/删除/区域绑定按钮点击事件委托
    const visionView = $("view-vision");
    if (visionView) {
      visionView.addEventListener("click", async (e) => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const camId = btn.dataset.camId;
        if (btn.dataset.action === "edit") {
          const cam = _visionCamsCache.find(c => c.camera_id === camId);
          if (cam) _showVisionForm(cam);
        } else if (btn.dataset.action === "zones") {
          await _showZoneBindDialog(camId);
        } else if (btn.dataset.action === "delete") {
          if (!(await this._showConfirm(`确定删除摄像头 ${camId}？此操作会同时从 Frigate 配置文件中移除并重启 Frigate。`))) return;
          try {
            await this._callService("smart_agent", "delete_frigate_camera", { camera_id: camId });
            this._msg("摄像头已删除，Frigate 正在重启");
            await _loadVisionCams();
          } catch (err) {
            this._msg("删除失败：" + (err.message || err));
          }
        }
      });
    }

    // 切换到视觉感知 Tab 时自动加载
    const _origSetTab = this._setTab?.bind(this);
    if (!this._visionTabHooked && _origSetTab) {
      this._visionTabHooked = true;
      const _origSetTabFn = this._setTab;
      this._setTab = (tab) => {
        _origSetTabFn.call(this, tab);
        if (tab === "vision") _loadVisionCams();
      };
    }

    // 帮助弹窗
    const helpOverlay = $("helpOverlay");
    $("helpBtn").onclick = () => {
      helpOverlay.classList.add("open");
      // 默认激活第一个导航项
      const firstNav = helpOverlay.querySelector(".help-nav-item");
      if (firstNav) firstNav.classList.add("active");
    };
    $("helpClose").onclick = () => helpOverlay.classList.remove("open");
    helpOverlay.onclick = (e) => { if (e.target === helpOverlay) helpOverlay.classList.remove("open"); };
    // 导航目录点击
    helpOverlay.querySelectorAll(".help-nav-item").forEach(item => {
      item.onclick = () => {
        helpOverlay.querySelectorAll(".help-nav-item").forEach(i => i.classList.remove("active"));
        item.classList.add("active");
        const sec = item.dataset.sec;
        const target = helpOverlay.querySelector("#hsec-" + sec);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      };
    });
    // 滚动时同步高亮导航
    const helpBody = $("helpBody");
    if (helpBody) {
      helpBody.addEventListener("scroll", () => {
        const sections = helpBody.querySelectorAll(".help-section[id]");
        let current = "";
        sections.forEach(s => {
          if (s.offsetTop - helpBody.scrollTop <= 60) current = s.id.replace("hsec-", "");
        });
        if (current) {
          helpOverlay.querySelectorAll(".help-nav-item").forEach(i => {
            i.classList.toggle("active", i.dataset.sec === current);
          });
        }
      });
    }

    // TTS 保存 (已移至「系统配置」标签页，此处保留空占位避免找不到元素报错)
    // TTS 测试播报
    // License → 去填写 Key（跳转到集成选项页）
    const licGotoBtn = $("licGotoOptionsBtn");
    if (licGotoBtn) {
      licGotoBtn.onclick = () => {
        const url = `/config/integrations/integration/smart_agent`;
        window.location.href = url;
      };
    }

    // License 验证按钮
    const licVerifyBtn = $("licVerifyBtn");
    if (licVerifyBtn) {
      licVerifyBtn.onclick = async () => {
        licVerifyBtn.disabled = true;
        licVerifyBtn.textContent = "验证中…";
        try {
          await this._callService("smart_agent", "verify_license", {});
          this._msg("License 验证请求已发送，请稍候");
        } catch (e) {
          this._msg("验证失败：" + e.message);
        } finally {
          licVerifyBtn.disabled = false;
          licVerifyBtn.textContent = "重新验证";
        }
      };
    }

    this._showOffline = false;
    this._showIgnored = false;
    this._newPage = 0;
    this._cfgPage = 0;
    this._newTypeFilter = "all";
    this._cfgTypeFilter = "all";
    const PAGE_SIZE = 20;

    // ── 下方为 Tab 页面逻辑初始化 ──────────────────────────────────────────
    this.shadowRoot.getElementById("addHBtn").onclick = async () => {
      const inp = this.shadowRoot.getElementById("hInput");
      const v = inp.value.trim();
      if (!v) return;
      inp.value = "";
      this._msg("画像已添加");
      try {
        await this._callService("smart_agent", "add_habit", { content: v });
        // 添加后清缓存并重新拉取，确保列表立即更新
        delete this._wsData["rules"];
        delete this._wsData["habits"];
        await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
          await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
        });
      } catch(e) { this._msg("添加失败: " + e.message); }
    };
    this.shadowRoot.getElementById("addRBtn").onclick = async () => {
      const inp = this.shadowRoot.getElementById("rInput");
      const v = inp.value.trim();
      if (!v) return;
      inp.value = "";
      this._msg("规则已添加");
      try {
        await this._callService("smart_agent", "add_rule", { content: v });
        // 添加后清缓存并重新拉取，确保列表立即更新
        delete this._wsData["rules"];
        delete this._wsData["habits"];
        await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
          await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
        });
      } catch(e) { this._msg("添加失败: " + e.message); }
    };

    // ── 设备名称查询工具 ──────────────────────────────────────────────────────
    const devToggle = this.shadowRoot.getElementById("devLookupToggle");
    const devPanel  = this.shadowRoot.getElementById("devLookupPanel");
    const devArrow  = this.shadowRoot.getElementById("devLookupArrow");
    if (devToggle) {
      devToggle.onclick = () => {
        const open = devPanel.style.display !== "none";
        devPanel.style.display = open ? "none" : "block";
        devArrow.style.transform = open ? "" : "rotate(180deg)";
      };
    }
    const devInput = this.shadowRoot.getElementById("devLookupInput");
    const devResults = this.shadowRoot.getElementById("devLookupResults");
    if (devInput) {
      devInput.oninput = () => {
        const q = devInput.value.trim().toLowerCase();
        if (!q) {
          devResults.innerHTML = '<span style="opacity:.6">输入关键词即可搜索</span>';
          return;
        }
        // 从 HA 状态中搜索所有 light/switch/climate/cover/fan 实体的 friendly_name
        const domains = ["light","switch","climate","cover","fan","binary_sensor","sensor","media_player"];
        const matches = [];
        for (const [eid, state] of Object.entries(this._hass?.states || {})) {
          if (!domains.some(d => eid.startsWith(d + "."))) continue;
          const name = (state.attributes?.friendly_name || "").toLowerCase();
          if (name.includes(q) || eid.toLowerCase().includes(q)) {
            matches.push({ eid, name: state.attributes?.friendly_name || eid });
          }
          if (matches.length >= 20) break;
        }
        if (!matches.length) {
          devResults.innerHTML = '<span style="opacity:.5">未找到匹配设备</span>';
          return;
        }
        devResults.innerHTML = matches.map(m =>
          `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--md-sys-color-outline-variant)">
            <span style="flex:1;font-weight:500">${this._esc(m.name)}</span>
            <code class="dev-search-copy-btn" data-eid="${this._esc(m.eid)}"
              style="font-size:11px;color:var(--md-sys-color-primary);background:var(--md-sys-color-primary-container);padding:2px 6px;border-radius:4px;cursor:pointer"
              title="点击复制">
              ${this._esc(m.eid)}
            </code>
          </div>`
        ).join("");
        // 通过事件委托处理复制，避免 onclick 内嵌 JS 字符串注入
        devResults.querySelectorAll(".dev-search-copy-btn").forEach(el => {
          el.addEventListener("click", function() {
            const eid = this.dataset.eid;
            if (navigator.clipboard) {
              navigator.clipboard.writeText(eid).catch(() => {});
            } else {
              const ta = document.createElement("textarea");
              ta.value = eid; document.body.appendChild(ta);
              ta.select(); document.execCommand("copy"); document.body.removeChild(ta);
            }
            const orig = this.textContent.trim();
            this.textContent = "✅ 已复制";
            setTimeout(() => { this.textContent = orig; }, 1500);
          });
        });
      };
    }
    // ──────────────────────────────────────────────────────────────────────────

    // engSel 已移至「系统配置」标签页，此处通过 HA select 实体来控制引擎
    const engSelEl = this.shadowRoot.getElementById("engSel");
    if (engSelEl) {
      engSelEl.onchange = e => {
        this._callService("select","select_option",{entity_id:"select.smart_agent_engine", option: e.target.value});
        this._msg("推理引擎已切换");
      };
    }
    const numAEl = this.shadowRoot.getElementById("numA");
    if (numAEl) {
      numAEl.addEventListener("input", e => {
        this.shadowRoot.getElementById("numAVal").textContent = e.target.value;
      });
      numAEl.addEventListener("change", e => {
        this._callService("number","set_value",{entity_id:"number.smart_agent_confidence_auto", value: parseFloat(e.target.value)});
      });
    }
    const numNEl = this.shadowRoot.getElementById("numN");
    if (numNEl) {
      numNEl.addEventListener("input", e => {
        this.shadowRoot.getElementById("numNVal").textContent = e.target.value;
      });
      numNEl.addEventListener("change", e => {
        this._callService("number","set_value",{entity_id:"number.smart_agent_confidence_notify", value: parseFloat(e.target.value)});
      });
    }
    const modeSelEl = this.shadowRoot.getElementById("modeSel");
    if (modeSelEl) {
      const modeHandler = async () => {
        const mode = modeSelEl.value;
        if (mode !== "home" && mode !== "showroom") return;
        await this._callService("smart_agent", "set_mode", { mode });
        this._msg(mode === "showroom" ? "已切换为展厅模式" : "已切换为家庭模式");
      };
      modeSelEl.addEventListener("change", modeHandler);
    }
    // 展厅场景按钮区：事件委托（按钮动态渲染，用委托避免重复绑定）
    this.shadowRoot.getElementById("showroomSceneBtns").addEventListener("click", async (e) => {
      const sceneBtn = e.target.closest(".showroom-scene-btn");
      const editBtn  = e.target.closest(".showroom-edit-btn");
      if (sceneBtn) {
        const scene = sceneBtn.dataset.scene;
        const customInput = this.shadowRoot.getElementById("showroomCustomInput");
        if (customInput) customInput.value = "";
        await this._callService("smart_agent", "set_showroom_scene", { scene, custom_prompt: "" });
        this._msg("展厅场景: " + sceneBtn.dataset.label);
      } else if (editBtn) {
        this._openSceneEdit(editBtn.dataset.scene);
      }
    });

    // ── 指令模式切换（一次性指令 / 持久模式）──────────────────────────────────
    const _sceneModeCmd     = this.shadowRoot.getElementById("sceneModeCmd");
    const _sceneModePersist = this.shadowRoot.getElementById("sceneModePersist");
    const _sceneModeHint    = this.shadowRoot.getElementById("sceneModeHint");
    /** @returns {boolean} true = 一次性指令模式 */
    const _isCommandMode = () => !_sceneModeCmd.dataset.inactive;
    const _setSceneMode = (isCmd) => {
      if (isCmd) {
        _sceneModeCmd.style.background     = "var(--sa-primary)";
        _sceneModeCmd.style.color          = "var(--sa-on-primary)";
        _sceneModeCmd.style.fontWeight     = "600";
        _sceneModePersist.style.background = "transparent";
        _sceneModePersist.style.color      = "var(--sa-on-surface-variant)";
        delete _sceneModeCmd.dataset.inactive;
        _sceneModePersist.dataset.inactive = "1";
        _sceneModeHint.textContent         = "执行一次后自动清空，不影响巡检";
        _sceneModeHint.style.color         = "var(--sa-primary)";
      } else {
        _sceneModePersist.style.background = "var(--sa-primary)";
        _sceneModePersist.style.color      = "var(--sa-on-primary)";
        _sceneModePersist.style.fontWeight = "600";
        _sceneModeCmd.style.background     = "transparent";
        _sceneModeCmd.style.color          = "var(--sa-on-surface-variant)";
        delete _sceneModePersist.dataset.inactive;
        _sceneModeCmd.dataset.inactive     = "1";
        _sceneModeHint.textContent         = "持续作为场景背景，每次巡检都生效";
        _sceneModeHint.style.color         = "var(--sa-secondary, #666)";
      }
    };
    _sceneModeCmd.onclick     = () => _setSceneMode(true);
    _sceneModePersist.onclick = () => _setSceneMode(false);
    // 默认：一次性指令模式
    _setSceneMode(true);

    // 自定义场景：Enter 键立即提交，onblur 时检查是否因点击了场景按钮而失焦（BUG-04）
    const customInput = this.shadowRoot.getElementById("showroomCustomInput");
    const clearBtn = this.shadowRoot.getElementById("clearCustomScene");

    if (clearBtn) {
      clearBtn.onclick = async () => {
        customInput.value = "";
        await this._callService("smart_agent", "set_showroom_scene", {
          scene: "", custom_prompt: "", is_command: false,
        });
        this._msg("✨ 已清空展厅自定义场景");
      };
    }

    /** 提交自定义指令/场景 */
    const _submitCustomScene = async () => {
      const v = customInput.value.trim();
      if (!v) return;
      const isCmd = _isCommandMode();
      await this._callService("smart_agent", "set_showroom_scene", {
        scene: "", custom_prompt: v, is_command: isCmd,
      });
      if (isCmd) {
        this._msg("✅ 一次性指令已发送，执行后自动清空");
        customInput.value = "";  // 立即清空输入框
      } else {
        this._msg("💾 持久场景已设置，巡检时持续生效");
      }
    };
    customInput.onkeydown = async (e) => {
      if (e.key !== "Enter") return;
      await _submitCustomScene();
      customInput.blur();
    };
    customInput.onblur = async (e) => {
      // relatedTarget 是获得焦点的元素：若是场景/编辑/模式切换按钮则跳过，防止竞态
      if (e.relatedTarget && (
        e.relatedTarget.classList.contains("showroom-scene-btn") ||
        e.relatedTarget.classList.contains("showroom-edit-btn") ||
        ["editSceneSave","editSceneCancel","sceneModeCmd","sceneModePersist"].includes(e.relatedTarget.id)
      )) return;
      await _submitCustomScene();
    };

    // 展厅场景编辑面板
    this.shadowRoot.getElementById("editSceneSave").onclick = async () => {
      const key = this._editingSceneKey;
      if (!key) return;
      const $ = id => this.shadowRoot.getElementById(id);
      await this._callService("smart_agent", "update_showroom_scene_config", {
        scene_key: key,
        label:      $("editSceneLabel").value.trim() || undefined,
        virtual_time: $("editSceneTime").value.trim() || undefined,
        scene_desc: $("editSceneDesc").value.trim() || undefined,
        hint:       $("editSceneHint").value.trim() || undefined,
      });
      $("showroomEditPanel").style.display = "none";
      this._editingSceneKey = null;
      this._msg("场景配置已保存");
      // 成功后延迟一小段时间拉取最新配置并渲染，确保状态已落库
      setTimeout(() => this._renderConfig(), 500);
    };
    this.shadowRoot.getElementById("editSceneCancel").onclick = () => {
      this.shadowRoot.getElementById("showroomEditPanel").style.display = "none";
      this._editingSceneKey = null;
    };

    // ── 行为习惯工具栏 ──
    const habSearch = this.shadowRoot.getElementById("habSearch");
    if (habSearch) {
      habSearch.oninput = (e) => {
        this._habSearch = e.target.value;
        this._renderHabitPatterns();
      };
    }
    const habSort = this.shadowRoot.getElementById("habSort");
    if (habSort) {
      habSort.onchange = (e) => {
        this._habSort = e.target.value;
        this._renderHabitPatterns();
      };
    }
    const habGroupBtn = this.shadowRoot.getElementById("habGroupBtn");
    if (habGroupBtn) {
      habGroupBtn.onclick = () => {
        this._habGrouped = !this._habGrouped;
        habGroupBtn.classList.toggle("active", this._habGrouped);
        this._renderHabitPatterns();
      };
    }
    // ── AI 学习进度仪表盘加载逻辑 ───────────────────────────────

    /** 渲染学习进度统计 */
    const _renderLearningStats = (data) => {
      const box = $("learningStats");
      if (!box) return;

      const _pill = (label, value, color, icon) => `
        <div style="background:var(--sa-card2);border:1px solid var(--sa-border);border-radius:var(--sa-shape-md);padding:12px;text-align:center;display:flex;flex-direction:column;gap:4px">
          <div style="font-size:12px;color:var(--sa-text-variant)">${icon} ${label}</div>
          <div style="font-size:22px;font-weight:700;color:${color}">${value}</div>
        </div>`;

      const deviceCoverage = data.total_devices > 0
        ? Math.round((1 - data.noroom_devices / data.total_devices) * 100)
        : 0;
      const coverageColor = deviceCoverage >= 90 ? "var(--sa-primary)" : deviceCoverage >= 60 ? "#F59E0B" : "var(--md-sys-color-error)";

      box.innerHTML = [
        _pill("到达基线", data.arrival_baseline || 0, "var(--sa-primary)", "📍"),
        _pill("用户纠正", data.corrections || 0, "#F59E0B", "✏️"),
        _pill("决策缓存", data.decision_cache || 0, "var(--sa-primary)", "⚡"),
        _pill("缓存命中", data.decision_cache_hits || 0, "#10B981", "🎯"),
        _pill("行为模式", data.behavior_patterns || 0, "var(--sa-primary)", "📊"),
        _pill("失败反思", data.reflexion_patterns || 0, "#8B5CF6", "🔄"),
        _pill("区域覆盖", deviceCoverage + "%", coverageColor, "🏠"),
      ].join("");

      // 设备区域警告
      const warn = $("learningDeviceWarning");
      if (warn && data.noroom_devices > 0) {
        warn.style.display = "";
        warn.innerHTML = `⚠️ 有 <b>${data.noroom_devices}</b> 个设备未配置区域（共 ${data.total_devices} 个），AI 无法判断这些设备属于哪个房间。
          <button id="goFixNoRoom" style="margin-left:8px;padding:3px 12px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;font-size:12px">前往修复 →</button>`;
        const fixBtn = $("goFixNoRoom");
        if (fixBtn) fixBtn.onclick = () => {
          this._filterNoRoom = true;
          this._setTab("devices");
        };
      } else if (warn) {
        warn.style.display = "none";
      }

      // 纠正趋势
      const trendBox = $("learningTrend");
      if (trendBox && data.correction_trend && data.correction_trend.length > 0) {
        trendBox.style.display = "";
        const maxCount = Math.max(...data.correction_trend.map(d => d.count), 1);
        trendBox.innerHTML = `
          <div style="font-size:12px;color:var(--md-sys-color-outline);margin-bottom:8px">📈 近 7 天纠正趋势</div>
          <div style="display:flex;align-items:flex-end;gap:4px;height:60px">
            ${data.correction_trend.map(d => {
              const h = Math.max(4, (d.count / maxCount) * 56);
              const dayLabel = d.day ? d.day.slice(5) : "";
              return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px">
                <span style="font-size:10px;color:var(--md-sys-color-outline)">${d.count}</span>
                <div style="width:100%;height:${h}px;background:#F59E0B;border-radius:4px 4px 0 0;min-width:12px"></div>
                <span style="font-size:9px;color:var(--md-sys-color-outline)">${dayLabel}</span>
              </div>`;
            }).join("")}
          </div>`;
      } else if (trendBox) {
        trendBox.style.display = "none";
      }

      // 被纠正最多的设备
      const topBox = $("learningTopCorrected");
      if (topBox && data.top_corrected && data.top_corrected.length > 0) {
        topBox.style.display = "";
        topBox.innerHTML = `
          <div style="font-size:12px;color:var(--md-sys-color-outline);margin-bottom:8px">🔧 被纠正最多的设备 Top-5</div>
          ${data.top_corrected.map(d => {
            const devName = (this._wsGet("devices", "devices", []).find(dev => dev.entity_id === d.entity_id) || {}).name || d.entity_id;
            return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px">
              <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${devName}</span>
              <span style="color:#F59E0B;font-weight:600;flex-shrink:0">${d.count} 次</span>
            </div>`;
          }).join("")}`;
      } else if (topBox) {
        topBox.style.display = "none";
      }
    };

    /** 加载学习进度数据 */
    const _loadLearningStats = async () => {
      try {
        const data = await this._hass.callWS({ type: "smart_agent/get_learning_stats" });
        _renderLearningStats(data);
      } catch (e) {
        const box = $("learningStats");
        if (box) box.innerHTML = `<div style="text-align:center;padding:16px;color:var(--md-sys-color-outline);font-size:13px;grid-column:1/-1">暂无数据</div>`;
      }
    };

    if ($("refreshLearningBtn")) $("refreshLearningBtn").onclick = _loadLearningStats;
    _loadLearningStats();

    this._setTab("dashboard");

    // 渲染完成后应用品牌配置（更新标题栏 & 主题色）
    this._applyBrand();
  }
};
