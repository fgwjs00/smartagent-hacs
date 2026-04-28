/**
 * SmartAgent Panel — Material Design 3 样式
 * 包含全部 CSS 自定义属性、组件样式和布局
 */

export const M3_CSS = `
:host {
  --sa-primary:      var(--primary-color, #6750A4);
  --sa-on-primary:   var(--text-primary-color, #FFFFFF);
  --sa-primary-container: rgba(var(--rgb-primary-color, 103,80,164), 0.12);
  --sa-on-primary-container: var(--primary-color, #6750A4);
  --sa-secondary-container: var(--secondary-background-color, #E8DEF8);
  --sa-bg:           var(--primary-background-color, #FAFAFA);
  --sa-card:         var(--card-background-color, #FFFFFF);
  --sa-card-outline: var(--divider-color, rgba(0,0,0,0.12));
  --sa-text:         var(--primary-text-color, #1C1B1F);
  --sa-text-variant: var(--secondary-text-color, #49454F);
  --sa-err:          var(--error-color, #B3261E);
  --sa-err-container: rgba(179, 38, 30, 0.12);
  --sa-succ:         var(--success-color, #146C2E);
  --sa-succ-container: rgba(20, 108, 46, 0.12);
  --sa-border:       var(--divider-color, rgba(0,0,0,0.12));

  /* M3 语义别名 — 模板全局使用，必须在此定义 */
  --sa-text2:              var(--secondary-text-color, #49454F);
  --sa-card2:              var(--secondary-background-color, #F7F2FA);
  --sa-primary-bg:         rgba(var(--rgb-primary-color, 103,80,164), 0.08);
  --sa-primary-bg2:        rgba(var(--rgb-primary-color, 103,80,164), 0.20);
  --sa-succ-bg:            rgba(20, 108, 46, 0.08);
  --sa-err-bg:             rgba(179, 38, 30, 0.08);
  --sa-surface:            var(--card-background-color, #FFFFFF);
  --sa-surface-variant:    var(--secondary-background-color, #E7E0EC);
  --sa-error:              var(--error-color, #B3261E);
  /* 以下变量被 config.js / update.js / panel-core.js 等使用，不可省略 */
  --sa-on-surface-variant: var(--secondary-text-color, #49454F);
  --sa-secondary:          var(--primary-color, #6750A4);
  --sa-surface-2:          rgba(var(--rgb-primary-color, 103,80,164), 0.05);
  --sa-shadow-lg:          0 8px 24px rgba(0,0,0,0.14), 0 3px 8px rgba(0,0,0,0.10);

  /* M3 扩展色彩 Token */
  --sa-tertiary:          #7D5260;
  --sa-tertiary-container: rgba(125, 82, 96, 0.12);
  --sa-outline:           var(--divider-color, #79747E);
  --sa-outline-variant:   rgba(121, 116, 126, 0.35);
  --sa-scrim:             rgba(0, 0, 0, 0.32);
  --sa-state-online:      #4CAF50;
  --sa-state-offline:     #9E9E9E;
  --sa-state-warning:     #FF9800;

  /* M3 Shape Token */
  --sa-shape-xs:   4px;
  --sa-shape-sm:   8px;
  --sa-shape-md:   12px;
  --sa-shape-lg:   16px;
  --sa-shape-xl:   28px;
  --sa-shape-full: 9999px;

  /* M3 Elevation Token */
  --sa-elev-1: 0 1px 2px rgba(0,0,0,0.10), 0 1px 3px rgba(0,0,0,0.08);
  --sa-elev-2: 0 2px 6px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08);
  --sa-elev-3: 0 4px 12px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08);
  --sa-elev-4: 0 8px 24px rgba(0,0,0,0.14), 0 3px 8px rgba(0,0,0,0.08);

  /* M3 间距 Token */
  --sa-sp-xs: 4px;
  --sa-sp-sm: 8px;
  --sa-sp-md: 12px;
  --sa-sp-lg: 16px;
  --sa-sp-xl: 24px;
  --sa-sp-2xl: 32px;

  /* Material Web CSS 系统 Token 映射 */
  --md-sys-color-primary:            var(--sa-primary);
  --md-sys-color-on-primary:         var(--sa-on-primary);
  --md-sys-color-primary-container:  var(--sa-primary-container);
  --md-sys-color-on-primary-container: var(--sa-on-primary-container);
  --md-sys-color-secondary-container: var(--sa-secondary-container);
  --md-sys-color-surface:            var(--sa-card);
  --md-sys-color-on-surface:         var(--sa-text);
  --md-sys-color-on-surface-variant: var(--sa-text-variant);
  --md-sys-color-surface-container:          var(--sa-bg);
  --md-sys-color-surface-container-low:      var(--sa-card);
  --md-sys-color-surface-container-high:     var(--sa-card2);
  --md-sys-color-surface-container-highest:  var(--sa-surface-variant);
  --md-sys-color-surface-variant:            var(--sa-surface-variant);
  --md-sys-color-on-surface-variant:         var(--sa-on-surface-variant);
  --md-sys-color-secondary:                  var(--sa-secondary);
  --md-sys-color-outline:                    var(--sa-outline, var(--sa-border));
  --md-sys-color-outline-variant:            var(--sa-outline-variant, var(--sa-border));
  --md-sys-color-error:                      var(--sa-err);
  --md-sys-color-on-error:                   #FFFFFF;
  --md-sys-color-error-container:            var(--sa-err-container);
  --md-sys-color-on-error-container:         var(--sa-err);
  --md-sys-color-tertiary:                   var(--sa-tertiary, #7D5260);
  --md-sys-color-scrim:                      var(--sa-scrim, rgba(0,0,0,0.32));

  /* Material Web 字体 */
  --md-sys-typescale-body-medium-font: 'Google Sans', Roboto, system-ui, sans-serif;
  --md-sys-typescale-label-large-font: 'Google Sans', Roboto, system-ui, sans-serif;

  display: block; font-family: 'Google Sans', Roboto, system-ui, sans-serif;
  background: var(--sa-bg); color: var(--sa-text); min-height: 100vh;
}
* { box-sizing: border-box; margin: 0; padding: 0; }

/* ── M3 FAB (Floating Action Bar) ── */
.batch-fab {
  position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%) translateY(120px);
  background: var(--sa-card); color: var(--sa-text);
  height: 64px; padding: 0 16px 0 24px; border-radius: 32px;
  display: flex; align-items: center; gap: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  z-index: 1000; transition: transform .4s cubic-bezier(0.05, 0.7, 0.1, 1);
  border: 1px solid var(--sa-border);
}
.batch-fab.show { transform: translateX(-50%) translateY(0); }
.batch-fab .divider { width: 1px; height: 24px; background: var(--sa-border); }
.batch-fab .count { font-weight: 700; font-size: 14px; color: var(--sa-primary); }
.batch-fab .actions { display: flex; gap: 8px; align-items: center; }

/* ── Chips — 已由 md-filter-chip / md-assist-chip 替代 ── */
md-filter-chip, md-assist-chip {
  --md-filter-chip-container-shape: var(--sa-shape-full);
  --md-assist-chip-container-shape: var(--sa-shape-full);
}
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; }

/* ── Select — 已由 md-outlined-select 替代 ── */
md-outlined-select {
  --md-outlined-select-text-field-container-shape: var(--sa-shape-md);
  min-width: 160px;
}
md-select-option { font-family: 'Google Sans', Roboto, system-ui, sans-serif; }

/* ── M3 Select compact（保留用于紧凑场景）── */
.m3-select-compact {
  height: 36px; padding: 0 12px; border-radius: 12px; font-size: 13px;
  background: var(--sa-bg); border: 1px solid var(--sa-border);
  color: var(--sa-text); cursor: pointer; outline: none;
}
.m3-select-compact:focus { border-color: var(--sa-primary); }

/* ── M3 Checkbox — 已由 md-checkbox 替代 ── */
md-checkbox { --md-checkbox-container-shape: 2px; }

/* ── M3 Dialog — 已由 md-dialog 替代 ── */
md-dialog {
  --md-dialog-container-shape: var(--sa-shape-xl);
  --md-dialog-container-color: var(--sa-card);
  --md-dialog-headline-color: var(--sa-text);
  --md-dialog-supporting-text-color: var(--sa-text-variant);
}
md-dialog:not([open]) { display: none; }

/* ── M3 Switch — 已由 md-switch 替代 ── */
md-switch { --md-switch-track-shape: var(--sa-shape-full); }

.headline-s { font-size: 18px; font-weight: 500; }
.headline-m { font-size: 24px; font-weight: 400; line-height: 1.33; }
.headline-l { font-size: 32px; font-weight: 400; line-height: 1.25; }
.title-l { font-size: 22px; font-weight: 500; line-height: 1.27; }
.title-m { font-size: 16px; font-weight: 500; line-height: 1.5; }
.title-s { font-size: 14px; font-weight: 500; line-height: 1.43; }
.label-l { font-size: 14px; font-weight: 500; }
.label-m { font-size: 12px; font-weight: 500; }
.label-s { font-size: 12px; font-weight: 500; color: var(--sa-text-variant); margin-bottom: 4px; display: block; }
.body-l { font-size: 16px; line-height: 1.5; }
.body-m { font-size: 14px; line-height: 1.5; }
.body-s { font-size: 12px; line-height: 1.4; color: var(--sa-text-variant); }

/* ── Layout ── */
.app-bar {
  position: sticky; top: 0; z-index: 100; height: 64px; padding: 0 24px;
  background: var(--sa-card); display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid var(--sa-border);
  box-shadow: var(--sa-elev-1);
}
.app-bar h1 { font-size: 22px; font-weight: 400; display: flex; align-items: center; gap: 10px; letter-spacing: -0.01em; }

.migration-badge {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-primary);
  background: var(--sa-primary-container);
  border: 1px solid var(--sa-outline-variant, var(--sa-border));
}

/* ── 帮助弹窗 ── */
.help-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center;
  opacity: 0; pointer-events: none; transition: opacity .2s;
}
.help-overlay.open { opacity: 1; pointer-events: auto; }
.help-dialog {
  background: var(--sa-card); border-radius: 20px; width: min(900px, 97vw);
  max-height: 88vh; display: flex; flex-direction: column;
  box-shadow: 0 8px 32px rgba(0,0,0,.22); overflow: hidden;
  transform: translateY(24px); transition: transform .25s;
}
.help-overlay.open .help-dialog { transform: translateY(0); }
.help-header {
  padding: 16px 20px 14px; border-bottom: 1px solid var(--sa-border);
  display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
}
.help-header h2 { font-size: 17px; font-weight: 600; color: var(--sa-primary); display:flex;align-items:center;gap:8px; }
.help-close {
  background: none; border: none; cursor: pointer; padding: 6px; border-radius: 50%;
  display: flex; align-items: center; color: var(--sa-text-variant); transition: background .15s;
}
.help-close:hover { background: var(--sa-primary-container); }
.help-layout { display: flex; flex: 1; overflow: hidden; }
.help-nav {
  width: 190px; flex-shrink: 0; overflow-y: auto; padding: 12px 8px;
  border-right: 1px solid var(--sa-border); background: var(--sa-bg);
}
.help-nav-item {
  display: flex; align-items: center; gap: 7px; padding: 7px 10px;
  border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer;
  color: var(--sa-text-variant); transition: background .15s, color .15s; white-space: nowrap;
}
.help-nav-item:hover { background: var(--sa-primary-container); color: var(--sa-primary); }
.help-nav-item.active { background: var(--sa-primary-container); color: var(--sa-primary); font-weight: 700; }
.help-nav-group { font-size: 10px; font-weight: 700; color: var(--sa-text-variant); letter-spacing: .06em;
  padding: 10px 10px 4px; text-transform: uppercase; opacity: .6; }
.help-body { flex: 1; overflow-y: auto; padding: 20px 24px 32px; display: flex; flex-direction: column; gap: 28px; }
.help-section { display: flex; flex-direction: column; gap: 10px; scroll-margin-top: 8px; }
.help-section-title {
  font-size: 15px; font-weight: 700; color: var(--sa-primary);
  display: flex; align-items: center; gap: 8px;
  padding-bottom: 8px; border-bottom: 2px solid var(--sa-primary-container);
}
.help-sub { font-size: 12px; font-weight: 700; color: var(--sa-text-variant); letter-spacing: .03em;
  margin: 4px 0 2px; }
.help-item { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; align-items: start; margin-bottom:2px; }
.help-badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 600;
  background: var(--sa-primary-container); color: var(--sa-on-primary-container);
  white-space: nowrap; margin-top: 1px;
}
.help-badge.green  { background: var(--sa-succ-container,rgba(20,108,46,.12)); color: var(--sa-succ,#146c2e); }
.help-badge.orange { background: rgba(255,152,0,.15); color: #e65100; }
.help-badge.blue   { background: rgba(33,150,243,.12); color: #1565c0; }
.help-badge.red    { background: var(--sa-err-container,rgba(179,38,30,.12)); color: var(--sa-err,#b3261e); }
.help-badge.gray   { background: rgba(0,0,0,.08); color: var(--sa-text-variant); }
.help-item p, .help-body > p, .help-section > p { font-size: 13px; line-height: 1.7; color: var(--sa-text); }
.help-item p b { color: var(--sa-primary); }
.help-tip {
  background: var(--sa-primary-container); border-radius: 10px; padding: 10px 14px;
  font-size: 12px; line-height: 1.6; color: var(--sa-on-primary-container);
}
.help-warn {
  background: rgba(255,152,0,.12); border-radius: 10px; padding: 10px 14px;
  font-size: 12px; line-height: 1.6; color: #7a4500; border-left: 3px solid #ff9800;
}
.help-code {
  background: var(--sa-bg,#f5f5f5); border: 1px solid var(--sa-border); border-radius: 6px;
  padding: 2px 6px; font-family: monospace; font-size: 12px; color: var(--sa-primary);
}
.help-flow {
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px;
  background: var(--sa-bg); border-radius: 10px; padding: 10px 14px; font-size: 12px;
}
.help-flow-step {
  background: var(--sa-primary-container); color: var(--sa-on-primary-container);
  border-radius: 8px; padding: 4px 10px; font-weight: 600; white-space: nowrap;
}
.help-flow-arrow { color: var(--sa-text-variant); font-size: 14px; }
.help-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.help-table th { background: var(--sa-primary-container); color: var(--sa-on-primary-container);
  padding: 6px 10px; text-align: left; font-weight: 600; }
.help-table td { padding: 6px 10px; border-bottom: 1px solid var(--sa-border); }
.help-table tr:last-child td { border-bottom: none; }
.help-table tr:hover td { background: var(--sa-primary-container); opacity: .7; }

.nav-tabs {
  background: var(--sa-card); display: flex; padding: 0 8px;
  border-bottom: 1px solid var(--sa-border); overflow-x: auto;
  scrollbar-width: none;
}
.nav-tabs::-webkit-scrollbar { display: none; }
.nav-tab {
  padding: 0 16px; height: 56px; border: none; background: none;
  font-size: 13px; font-weight: 500; letter-spacing: 0.01em;
  color: var(--sa-text-variant); cursor: pointer; position: relative; transition: color .2s;
  white-space: nowrap; display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0;
}
.nav-tab:hover { color: var(--sa-primary); }
.nav-tab.active { color: var(--sa-primary); font-weight: 600; }
.nav-tab::after {
  content: ''; position: absolute; bottom: 0; left: 12px; right: 12px; height: 3px;
  background: var(--sa-primary); border-radius: 3px 3px 0 0;
  opacity: 0; transition: opacity .2s;
}
.nav-tab.active::after { opacity: 1; }
.nav-tab:hover::after { opacity: .4; }

/* ── 子 Tab 导航栏 ── */
.nav-sub-tabs {
  background: var(--sa-bg); display: flex; padding: 0 12px;
  border-bottom: 1px solid var(--sa-border); overflow-x: auto; gap: 2px;
  scrollbar-width: none;
}
.nav-sub-tabs::-webkit-scrollbar { display: none; }
.nav-sub-tab {
  padding: 0 14px; height: 44px; border: none; background: none;
  font-size: 12px; font-weight: 500; color: var(--sa-text-variant);
  cursor: pointer; position: relative; transition: .15s;
  white-space: nowrap; display: inline-flex; align-items: center; border-radius: 0; flex-shrink: 0;
}
.nav-sub-tab:hover { color: var(--sa-primary); }
.nav-sub-tab.active { color: var(--sa-primary); font-weight: 600; }
.nav-sub-tab::after {
  content: ''; position: absolute; bottom: 0; left: 8px; right: 8px; height: 2px;
  background: var(--sa-primary); border-radius: 2px 2px 0 0;
  opacity: 0; transition: opacity .2s;
}
.nav-sub-tab.active::after { opacity: 1; }

.main { max-width: 1040px; margin: 0 auto; padding: 20px 24px 32px; display: flex; flex-direction: column; gap: 16px; }
.tab-view { display: flex; flex-direction: column; gap: 16px; }
.tab-view:not(.active) { display: none !important; }

/* ── Cards — M3 Outlined Card ── */
.card { 
  background: var(--sa-card); border-radius: var(--sa-shape-lg); padding: 20px; 
  border: 1px solid var(--sa-card-outline);
  box-shadow: var(--sa-elev-1);
}
/* M3 Filled Card — 使用 surface-container 背景 */
.card-filled {
  background: var(--sa-card2); border-radius: var(--sa-shape-lg); padding: 20px;
}
/* M3 Elevated Card — 无边框，纯阴影 */
.card-elevated {
  background: var(--sa-card); border-radius: var(--sa-shape-lg); padding: 20px;
  box-shadow: var(--sa-elev-2);
}
.card-tonal {
  background: var(--sa-primary-container); border-radius: 20px; padding: 20px;
  color: var(--sa-on-primary-container);
}
.scene-icon-wrap {
  width: 64px; height: 64px; border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  background: var(--sa-card); color: var(--sa-primary);
  box-shadow: var(--sa-elev-2);
}
.card-title { 
  font-size: 14px; font-weight: 600; color: var(--sa-text-variant); 
  margin-bottom: 16px; display: flex; align-items: center; gap: 8px; 
}

/* ── Stats — M3 Filled Card 风格 ── */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
.stat-card {
  background: var(--sa-card); border-radius: var(--sa-shape-lg); padding: 18px 16px;
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  border: 1px solid var(--sa-card-outline);
  box-shadow: var(--sa-elev-1);
  transition: box-shadow .2s, transform .2s;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--sa-elev-2); }
.stat-card-icon { 
  width: 44px; height: 44px; border-radius: var(--sa-shape-md);
  background: var(--sa-primary-container); color: var(--sa-primary);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 2px;
}
.stat-num { font-size: 28px; font-weight: 700; color: var(--sa-primary); line-height: 1.1; }
.stat-lbl { font-size: 12px; font-weight: 500; color: var(--sa-text-variant); text-align: center; }

/* ── Toast ── */
#toast { 
  position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%) translateY(80px);
  background: #313033; color: #F4EFF4; padding: 12px 24px; border-radius: 24px;
  transition: transform .3s cubic-bezier(0.05, 0.7, 0.1, 1.0), opacity .3s; opacity: 0; z-index: 1000; 
  box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 14px; font-weight: 500;
  display: flex; align-items: center; gap: 8px; pointer-events: none;
  white-space: nowrap;
}
#toast.show { transform: translateX(-50%) translateY(0); opacity: 1; }

/* ── Buttons — 已由 md-filled-button / md-outlined-button 等替代 ── */
/* 保留原生 .btn 类用于不支持 Material Web 的场景 */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 0 24px; height: 40px; border-radius: 20px;
  border: none; font-size: 14px; font-weight: 500; cursor: pointer; transition: .2s;
  font-family: 'Google Sans', Roboto, system-ui, sans-serif;
}
.btn-filled { background: var(--sa-primary); color: var(--sa-on-primary); }
.btn-tonal  { background: var(--sa-primary-container); color: var(--sa-on-primary-container); }
.btn-outline { background: transparent; border: 1px solid var(--sa-border); color: var(--sa-primary); }
.btn-error  { background: var(--sa-err-container); color: var(--sa-err); }
.btn:hover  { filter: brightness(0.95); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.btn:disabled { opacity: .4; cursor: default; pointer-events: none; }
.btn-sm     { height: 32px; padding: 0 16px; font-size: 13px; }
.btn-icon   { width: 36px; height: 36px; padding: 0; border-radius: 18px; background: transparent; border: none; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; color: var(--sa-text-variant); transition: .2s; }
.btn-icon:hover { background: var(--sa-primary-container); color: var(--sa-primary); }
.btn.loading { opacity: .6; pointer-events: none; }
md-filled-button, md-outlined-button, md-filled-tonal-button, md-text-button {
  --md-filled-button-container-height: 40px;
  --md-outlined-button-container-height: 40px;
  --md-filled-tonal-button-container-height: 40px;
  --md-text-button-container-height: 40px;
  /* Spacing Variables */
  --md-filled-button-leading-space: 20px;
  --md-filled-button-trailing-space: 20px;
  --md-outlined-button-leading-space: 20px;
  --md-outlined-button-trailing-space: 20px;
  --md-filled-tonal-button-leading-space: 20px;
  --md-filled-tonal-button-trailing-space: 20px;
  --md-text-button-leading-space: 12px;
  --md-text-button-trailing-space: 12px;
  
  font-family: 'Google Sans', Roboto, system-ui, sans-serif;
  flex-shrink: 0;
  min-width: 80px;
}
md-icon-button {
  flex-shrink: 0;
}
md-filter-chip, md-assist-chip {
  flex-shrink: 0;
  --md-filter-chip-leading-space: 12px;
  --md-filter-chip-trailing-space: 12px;
}
md-outlined-button {
  --md-outlined-button-label-text-color: var(--sa-primary);
  --md-outlined-button-hover-label-text-color: var(--sa-primary);
  --md-outlined-button-pressed-label-text-color: var(--sa-primary);
  --md-outlined-button-outline-color: var(--sa-primary);
  --md-outlined-button-hover-outline-color: var(--sa-primary);
}
md-filled-tonal-button {
  --md-filled-tonal-button-container-color: var(--sa-primary-container);
  --md-filled-tonal-button-label-text-color: var(--sa-on-primary-container);
  --md-filled-tonal-button-hover-label-text-color: var(--sa-on-primary-container);
}
md-filled-button {
  --md-filled-button-container-color: var(--sa-primary);
  --md-filled-button-label-text-color: var(--sa-on-primary);
}
md-text-button {
  --md-text-button-label-text-color: var(--sa-primary);
}
md-filled-button.btn-sm, md-outlined-button.btn-sm, md-filled-tonal-button.btn-sm {
  --md-filled-button-container-height: 32px;
  --md-outlined-button-container-height: 32px;
  --md-filled-tonal-button-container-height: 32px;
  --md-filled-button-leading-space: 12px;
  --md-filled-button-trailing-space: 12px;
  --md-outlined-button-leading-space: 12px;
  --md-outlined-button-trailing-space: 12px;
  --md-filled-tonal-button-leading-space: 12px;
  --md-filled-tonal-button-trailing-space: 12px;
  height: auto; padding: 0; font-size: 13px;
  min-width: 64px;
}
md-filled-button.btn-error {
  --md-filled-button-container-color: var(--sa-err);
  --md-filled-button-label-text-color: #fff;
}
md-filled-tonal-button.btn-error {
  --md-filled-tonal-button-container-color: var(--sa-err);
  --md-filled-tonal-button-label-text-color: #fff;
  --md-filled-tonal-button-hover-container-color: var(--sa-err);
}
md-icon-button { color: var(--sa-text-variant); }

/* ── Form Elements — 已由 md-outlined-text-field 替代 ── */
md-outlined-text-field {
  width: 100%;
  --md-outlined-text-field-container-shape: var(--sa-shape-md);
}
md-outlined-text-field.input-sm {
  --md-outlined-text-field-container-height: 40px;
}

/* ── M3 Input (基础输入框) ── */
.input {
  height: 40px; padding: 0 16px;
  border-radius: var(--sa-shape-sm);
  border: 1px solid var(--sa-outline);
  background: transparent; color: var(--sa-text);
  font-size: 14px; font-family: inherit; outline: none;
  transition: border-color .2s; width: 100%;
}
.input:focus { border-color: var(--sa-primary); border-width: 2px; }
.input::placeholder { color: var(--sa-text-variant); opacity: .7; }
textarea.input { height: auto; padding: 12px 16px; resize: vertical; line-height: 1.5; }

/* ── M3 Select Wrap (自定义 select 容器) ── */
.m3-select-wrap {
  position: relative; display: flex; align-items: center;
  border: 1px solid var(--sa-outline); border-radius: var(--sa-shape-md);
  background: transparent; transition: border-color .2s, border-width .1s;
  overflow: hidden;
}
.m3-select-wrap:focus-within { border-color: var(--sa-primary); border-width: 2px; }
.m3-select {
  appearance: none; -webkit-appearance: none; flex: 1;
  height: 100%; min-height: 40px; padding: 0 40px 0 16px;
  background: transparent; border: none; outline: none;
  font-size: 14px; font-family: inherit; color: var(--sa-text); cursor: pointer;
}
.m3-select-arrow {
  position: absolute; right: 10px; pointer-events: none;
  color: var(--sa-text-variant); display: flex; align-items: center;
}

/* ── M3 风格 Range Slider（原生 input[type=range]）── */
.range-input {
  -webkit-appearance: none; appearance: none;
  width: 100%; height: 4px; cursor: pointer;
  border-radius: 2px; outline: none; margin: 14px 0;
  background: var(--sa-outline-variant);
  accent-color: var(--sa-primary);
}
.range-input::-webkit-slider-runnable-track {
  height: 4px; border-radius: 2px;
  background: var(--sa-outline-variant);
}
.range-input::-webkit-slider-thumb {
  -webkit-appearance: none; width: 20px; height: 20px;
  border-radius: 50%; background: var(--sa-primary);
  margin-top: -8px; cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.25); transition: transform .15s, box-shadow .15s;
}
.range-input::-webkit-slider-thumb:hover { transform: scale(1.15); box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.range-input:active::-webkit-slider-thumb { transform: scale(1.25); }
.range-input::-moz-range-track {
  height: 4px; border-radius: 2px; background: var(--sa-outline-variant);
}
.range-input::-moz-range-thumb {
  width: 20px; height: 20px; border-radius: 50%;
  background: var(--sa-primary); border: none;
  cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.25);
}
.range-input:focus { outline: none; }

/* ── M3 List Items ── */
.m3-list { display: flex; flex-direction: column; gap: 8px; }
.m3-item {
  display: flex; align-items: center; gap: 16px; padding: 12px 16px;
  border-radius: 16px; transition: .2s; cursor: default;
  border: 1px solid var(--sa-border); background: var(--sa-card);
}
.m3-item:hover { border-color: var(--sa-primary); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.m3-icon {
  width: 44px; height: 44px; border-radius: 12px; background: var(--sa-secondary-container);
  display: flex; align-items: center; justify-content: center; color: var(--sa-primary);
  flex-shrink: 0;
}
.m3-content { flex: 1; min-width: 0; }
.m3-title { font-size: 15px; font-weight: 500; color: var(--sa-text); }
.m3-subtitle { font-size: 12px; color: var(--sa-text-variant); margin-top: 2px; }

/* ── 设备管辖域标签 ── */
.ctrl-mode-wrap { display: flex; gap: 4px; flex-shrink: 0; }
.ctrl-mode-btn {
  padding: 3px 10px; border-radius: 16px; font-size: 11px; font-weight: 600;
  border: 1.5px solid transparent; cursor: pointer; transition: .18s; white-space: nowrap;
  background: transparent; color: var(--sa-text2);
}
.ctrl-mode-btn:hover { border-color: var(--sa-primary); color: var(--sa-primary); }
.ctrl-mode-btn.active-ai {
  background: var(--sa-primary-bg); color: var(--sa-primary);
  border-color: var(--sa-primary-bg2);
}
.ctrl-mode-btn.active-ha {
  background: rgba(230,81,0,.10); color: #e65100;
  border-color: rgba(230,81,0,.25);
}
.ctrl-mode-btn.active-shared {
  background: var(--sa-succ-bg); color: var(--sa-succ);
  border-color: rgba(20,108,46,.25);
}

/* ── Chips ── */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  padding: 6px 14px; border-radius: 16px; font-size: 12px; font-weight: 500;
  display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--sa-border);
  background: var(--sa-card); color: var(--sa-text-variant); cursor: pointer; transition: .2s;
}
.chip.active { background: var(--sa-primary-container); color: var(--sa-primary); border-color: var(--sa-primary); }

/* ── Pager ── */
.pager-btn {
  min-width: 32px; height: 32px; padding: 0 8px; border-radius: 8px; border: 1px solid var(--sa-border);
  background: var(--sa-card); color: var(--sa-text); cursor: pointer; font-size: 13px; transition: .15s;
}
.pager-btn:hover:not(:disabled) { background: var(--sa-primary-container); border-color: var(--sa-primary); }
.pager-btn.active { background: var(--sa-primary); color: var(--sa-on-primary); border-color: var(--sa-primary); }
.pager-btn:disabled { opacity: .35; cursor: default; }
.pager-info { font-size: 12px; color: var(--sa-text-variant); align-self: center; padding: 0 4px; }

/* ── Logs ── */
.log-box {
  background: #0D1117; color: #c9d1d9; border-radius: 16px; padding: 16px;
  font-family: 'Roboto Mono', 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.7;
  max-height: 480px; overflow-y: auto; border: 1px solid #30363d;
  scrollbar-width: thin; scrollbar-color: #30363d #0D1117;
}
.log-box::-webkit-scrollbar { width: 6px; }
.log-box::-webkit-scrollbar-track { background: transparent; }
.log-box::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
.log-box::-webkit-scrollbar-thumb:hover { background: #484f58; }
.log-box .sl-row { 
  padding: 5px 10px; margin: 3px 0; border-radius: 6px; 
  border-left: 3px solid transparent; display: flex; align-items: flex-start; gap: 0;
  word-break: break-all; line-height: 1.6;
}
.log-box .sl-i { color: #8b949e; border-left-color: #30363d; }
.log-box .sl-i:hover { background: rgba(255,255,255,0.04); color: #c9d1d9; }
.log-box .sl-w { 
  color: #d29922; border-left-color: #d29922; 
  background: rgba(210,153,34,0.08);
}
.log-box .sl-w:hover { background: rgba(210,153,34,0.15); }
.log-box .sl-e { 
  color: #f85149; border-left-color: #f85149; 
  background: rgba(248,81,73,0.1); font-weight: 600;
}
.log-box .sl-e:hover { background: rgba(248,81,73,0.18); }
.log-box .sl-ts { color: #484f58; margin-right: 6px; font-size: 11px; flex-shrink: 0; }
.log-box .sl-tag { 
  display: inline-flex; align-items: center; padding: 1px 7px; border-radius: 4px; 
  font-size: 10px; font-weight: 700; margin: 0 5px 0 2px; letter-spacing: 0.5px;
  text-transform: uppercase; vertical-align: middle;
}
.log-box .sl-tag-protect { background: rgba(210,153,34,0.2); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
.log-box .sl-tag-trigger { background: rgba(35,209,139,0.15); color: #23d18b; border: 1px solid rgba(35,209,139,0.25); }
.log-box .sl-tag-infer { background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid rgba(88,166,255,0.25); }
.log-box .sl-tag-exec { background: rgba(188,130,252,0.15); color: #bc82fc; border: 1px solid rgba(188,130,252,0.25); }
.log-box .sl-tag-patrol { background: rgba(121,192,255,0.12); color: #79c0ff; border: 1px solid rgba(121,192,255,0.2); }

/* ── M3 Custom Dialog Overlay ── */
.m3-dialog-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: var(--sa-scrim); display: flex; align-items: center; justify-content: center;
  opacity: 0; pointer-events: none; transition: opacity .2s;
}
.m3-dialog-overlay.open { opacity: 1; pointer-events: auto; }
.m3-dialog {
  background: var(--sa-card); border-radius: var(--sa-shape-xl);
  padding: 24px; max-height: 90vh; overflow-y: auto;
  box-shadow: var(--sa-elev-4);
  transform: translateY(24px) scale(.96);
  transition: transform .3s cubic-bezier(0.05, 0.7, 0.1, 1);
}
.m3-dialog-overlay.open .m3-dialog { transform: translateY(0) scale(1); }
.m3-dialog-title {
  font-size: 22px; font-weight: 400; color: var(--sa-text);
  margin-bottom: 20px; display: flex; align-items: center; gap: 8px; line-height: 1.3;
}
.m3-dialog-actions {
  display: flex; gap: 8px; justify-content: flex-end; padding-top: 20px;
}

/* ── md-slider 令牌映射 ── */
md-slider {
  width: 100%;
  --md-slider-active-track-color: var(--sa-primary);
  --md-slider-handle-color: var(--sa-primary);
  --md-slider-inactive-track-color: var(--sa-outline-variant);
  --md-slider-with-tick-marks-active-container-color: var(--sa-on-primary);
  --md-slider-label-container-color: var(--sa-primary);
  --md-slider-label-label-text-color: var(--sa-on-primary);
}

/* ── Mode Switches — M3 List Item 风格 ── */
.mode-card {
  display: flex; align-items: center; gap: 16px; padding: 14px 16px;
  border-radius: var(--sa-shape-lg); border: 1.5px solid var(--sa-card-outline);
  background: var(--sa-card); transition: border-color .2s, box-shadow .2s, background .2s;
  cursor: pointer; flex: 1; min-width: 220px;
  box-shadow: var(--sa-elev-1);
}
.mode-card:hover { border-color: var(--sa-primary); box-shadow: var(--sa-elev-2); }
.mode-card.active {
  border-color: var(--sa-primary); background: var(--sa-primary-container);
  box-shadow: none;
}
.mode-card-icon {
  width: 44px; height: 44px; border-radius: var(--sa-shape-md); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--sa-primary-container); color: var(--sa-primary);
  transition: background .2s;
}
.mode-card.active .mode-card-icon { background: var(--sa-primary); color: var(--sa-on-primary); }

/* ── M3 Tonal Button 状态切换 ── */
md-filled-tonal-button.dim {
  --md-filled-tonal-button-container-color: var(--sa-card2);
  --md-filled-tonal-button-label-text-color: var(--sa-text-variant);
}

/* ── m3-switch / m3-select-wrap — 已由 md-switch / md-outlined-select 替代 ── */

.input-with-icon {
  position: relative; display: flex; align-items: center;
}
.input-with-icon svg { position: absolute; left: 16px; color: var(--sa-primary); opacity: .7; z-index: 1; }
.input-with-icon .input { padding-left: 44px; }
.input-with-icon .input:focus { padding-left: 43px; }

.sys-card {
  background: var(--sa-card2); border-radius: var(--sa-shape-lg);
  padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.sys-icon { font-size: 24px; line-height: 1; }
.sys-card-label { font-size: 13px; font-weight: 600; color: var(--sa-text-variant); }
.sys-val-row { display: flex; align-items: baseline; gap: 4px; }
.sys-val-num { font-size: 28px; font-weight: 700; color: var(--sa-primary); line-height: 1; }
.sys-val-unit { font-size: 13px; color: var(--sa-text-variant); }
.sys-hint { font-size: 11px; color: var(--sa-text-variant); opacity: .7; }

/* 展厅场景 */
.showroom-scene-row { display: flex; align-items: center; gap: 4px; }
.showroom-scene-btn {
  display: flex; align-items: center; gap: 6px; padding: 8px 16px;
  border-radius: 12px; border: 1px solid var(--sa-border); background: var(--sa-card);
  color: var(--sa-text); cursor: pointer; font-size: 13px; transition: .2s;
}
.showroom-scene-btn:hover { border-color: var(--sa-primary); background: var(--sa-primary-container); }
.showroom-edit-btn { background: none; border: none; cursor: pointer; padding: 2px 5px; border-radius: 6px; font-size: 13px; color: var(--sa-text2); opacity: .65; transition: .15s; line-height: 1; }
.showroom-edit-btn:hover { opacity: 1; background: var(--sa-primary-bg); color: var(--sa-primary); }
.showroom-edit-panel { padding: 14px; background: var(--sa-bg); border-radius: 10px; border: 1px solid var(--sa-border); margin: 10px 0; }
.showroom-edit-panel label { font-size: 11px; font-weight: 500; color: var(--sa-text2); display: block; margin-bottom: 4px; margin-top: 8px; }
.showroom-edit-panel label:first-child { margin-top: 0; }

/* ── 行为习惯页 M3 样式 ── */
.hab-page { display: flex; flex-direction: column; gap: 16px; }
.hab-page-header { display: flex; flex-direction: column; gap: 12px; }
.hab-title-row {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
}
.hab-page-title {
  display: flex; align-items: center; gap: 10px;
  font-size: 20px; font-weight: 500; color: var(--sa-text);
}
.hab-page-title svg { color: var(--sa-primary); flex-shrink: 0; }
.hab-title-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--sa-primary-bg); color: var(--sa-primary);
  border: 1px solid var(--sa-primary-bg2); border-radius: 20px;
  padding: 2px 10px; font-size: 11px; font-weight: 600;
}
.hab-stat-row { display: flex; gap: 10px; flex-wrap: wrap; }
.hab-stat-chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--sa-card2); color: var(--sa-text2);
  border: 1px solid var(--sa-border); border-radius: 20px;
  padding: 4px 12px; font-size: 12px; font-weight: 500;
}
.hab-stat-chip svg { width: 14px; height: 14px; opacity: .7; }
.hab-toolbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.hab-search-wrap {
  flex: 1; min-width: 160px; display: flex; align-items: center; gap: 8px;
  background: var(--sa-card2); border: 1px solid var(--sa-border);
  border-radius: 28px; padding: 6px 14px; transition: border-color .2s;
}
.hab-search-wrap:focus-within { border-color: var(--sa-primary); }
.hab-search-wrap svg { color: var(--sa-text2); flex-shrink: 0; width: 16px; height: 16px; }
.hab-search {
  border: none; background: transparent; outline: none;
  font-size: 13px; color: var(--sa-text); width: 100%;
}
.hab-search::placeholder { color: var(--sa-text2); opacity: .6; }
.hab-toolbar-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.hab-group-btn {
  display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
  font-size: 12px; font-weight: 500; color: var(--sa-text2);
  padding: 6px 14px; border-radius: 20px; border: 1px solid var(--sa-border);
  background: var(--sa-card2); user-select: none; transition: .2s; white-space: nowrap;
}
.hab-group-btn:hover { border-color: var(--sa-primary); color: var(--sa-primary); }
.hab-group-btn.active {
  background: var(--sa-primary-bg); color: var(--sa-primary);
  border-color: var(--sa-primary-bg2);
}
.hab-group-btn svg { width: 14px; height: 14px; }
.hab-info-banner {
  display: flex; align-items: flex-start; gap: 10px;
  background: var(--sa-primary-bg); border-radius: 12px;
  padding: 12px 16px; font-size: 12px; line-height: 1.7; color: var(--sa-text2);
  border: 1px solid var(--sa-primary-bg2);
}
.hab-info-banner svg { flex-shrink: 0; color: var(--sa-primary); margin-top: 1px; }
.hab-list { display: flex; flex-direction: column; gap: 8px; }
.hab-item {
  display: flex; align-items: center; gap: 14px;
  background: var(--sa-card); border: 1px solid var(--sa-border);
  border-radius: 16px; padding: 14px 16px; transition: box-shadow .2s, border-color .2s;
  cursor: default;
}
.hab-item:hover {
  border-color: var(--sa-primary-bg2);
  box-shadow: 0 2px 8px rgba(var(--rgb-primary-color,103,80,164),.12);
}
.hab-item.hab-inactive { opacity: .5; }
.hab-icon-wrap {
  width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; transition: .2s;
}
.hab-icon-wrap.state-on  { background: var(--sa-succ-bg);    color: var(--sa-succ); }
.hab-icon-wrap.state-off { background: var(--sa-card2);      color: var(--sa-text2); }
.hab-icon-wrap.state-other { background: var(--sa-primary-bg); color: var(--sa-primary); }
.hab-body { flex: 1; min-width: 0; }
.hab-name {
  font-size: 14px; font-weight: 500; color: var(--sa-text);
  margin-bottom: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.hab-eid { font-size: 11px; color: var(--sa-text2); opacity: .55; margin-bottom: 8px; }
.hab-chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.hab-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 500;
  border: 1px solid var(--sa-border); color: var(--sa-text2); background: var(--sa-card2);
  white-space: nowrap;
}
.hab-chip svg { width: 13px; height: 13px; }
.hab-chip-on  { background: var(--sa-succ-bg);  color: var(--sa-succ);  border-color: rgba(20,108,46,.25); }
.hab-chip-off { background: var(--sa-card2);     color: var(--sa-text2); }
.hab-chip-heat { background: rgba(230,81,0,.1); color: #e65100; border-color: rgba(230,81,0,.25); }
.hab-conf-chip {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 3px 10px 3px 8px; border-radius: 20px;
  border: 1px solid var(--sa-border); background: var(--sa-card2);
}
.hab-conf-track {
  width: 48px; height: 4px; border-radius: 2px;
  background: var(--sa-border); overflow: hidden; flex-shrink: 0;
}
.hab-conf-fill { height: 100%; border-radius: 2px; transition: width .5s; }
.hab-conf-high { background: var(--sa-succ); }
.hab-conf-mid  { background: var(--sa-primary); }
.hab-conf-low  { background: var(--sa-text2); }
.hab-conf-val  { font-size: 12px; font-weight: 700; }
.hab-del-btn {
  width: 40px; height: 40px; border-radius: 20px; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  background: transparent; color: var(--sa-text2); transition: .2s;
}
.hab-del-btn:hover { background: var(--sa-err-bg); color: var(--sa-err); }
.hab-dev-section {
  border: 1px solid var(--sa-border); border-radius: 16px;
  background: var(--sa-card); overflow: hidden;
  transition: border-color .2s;
}
.hab-dev-section:hover { border-color: var(--sa-primary-bg2); }
.hab-dev-header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px; border-bottom: 1px solid var(--sa-border);
  background: var(--sa-card2);
}
.hab-dev-icon {
  width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--sa-primary-bg); color: var(--sa-primary);
}
.hab-dev-name { font-size: 14px; font-weight: 600; color: var(--sa-text); }
.hab-dev-eid { font-size: 11px; color: var(--sa-text2); opacity: .5; margin-top: 1px; }
.hab-dev-badge {
  margin-left: auto; flex-shrink: 0;
  background: var(--sa-primary-bg); color: var(--sa-primary);
  border: 1px solid var(--sa-primary-bg2); border-radius: 12px;
  padding: 2px 10px; font-size: 11px; font-weight: 700;
}
.hab-dev-rows {
  display: flex; flex-direction: column; gap: 0;
}
.hab-row-compact {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 10px 16px 10px 68px; transition: background .15s;
  border-top: 1px solid var(--sa-border);
}
.hab-dev-rows .hab-row-compact:first-child { border-top: none; }
.hab-row-compact:hover { background: var(--sa-card2); }
.hab-row-compact.hab-inactive { opacity: .5; }
.hab-row-compact .hab-conf-chip { margin-left: auto; }
.hab-row-compact .hab-del-btn { width: 32px; height: 32px; border-radius: 16px; flex-shrink: 0; }
.hab-empty {
  display: flex; flex-direction: column; align-items: center; padding: 56px 24px;
  text-align: center; color: var(--sa-text2); border-radius: 16px;
  background: var(--sa-card); border: 1.5px dashed var(--sa-border);
}
.hab-empty-icon { margin-bottom: 16px; opacity: .35; color: var(--sa-primary); }
.hab-empty-title { font-size: 15px; font-weight: 500; color: var(--sa-text); margin-bottom: 8px; }
.hab-empty-desc { font-size: 12px; line-height: 1.7; max-width: 340px; }

/* 版本信息 */
.version {
  text-align: center; font-size: 11px; color: var(--sa-text-variant); 
  opacity: .4; padding: 8px 0 4px;
}

/* ── 5A-3: 决策气泡通知 ── */
.decision-bubble {
  position: fixed; bottom: 24px; right: 24px; z-index: 9999;
  background: var(--sa-card, #fff);
  border: 1.5px solid var(--sa-primary-container, rgba(103,80,164,.22));
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,.18);
  padding: 14px 16px 12px;
  min-width: 240px; max-width: 320px;
  display: flex; flex-direction: column; gap: 8px;
  animation: bubble-in .25s cubic-bezier(.34,1.56,.64,1);
  transition: opacity .3s, transform .3s;
}
.decision-bubble.bubble-out {
  opacity: 0; transform: translateY(16px) scale(.96); pointer-events: none;
}
@keyframes bubble-in {
  from { opacity: 0; transform: translateY(20px) scale(.92); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
.bubble-header {
  display: flex; align-items: center; gap: 8px;
}
.bubble-icon {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--sa-primary-container, rgba(103,80,164,.15));
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; color: var(--sa-primary, #6750A4);
}
.bubble-scene {
  font-size: 13px; font-weight: 600; color: var(--sa-text);
  flex: 1; line-height: 1.3;
}
.bubble-conf {
  font-size: 11px; color: var(--sa-primary, #6750A4);
  background: var(--sa-primary-container, rgba(103,80,164,.1));
  border-radius: 10px; padding: 2px 8px; white-space: nowrap;
}
.bubble-actions-list {
  font-size: 11px; color: var(--sa-text-variant);
  line-height: 1.6; padding-left: 4px;
}
.bubble-footer {
  display: flex; gap: 8px; justify-content: flex-end;
}
.bubble-btn {
  font-size: 12px; font-weight: 600; border: none; cursor: pointer;
  padding: 5px 14px; border-radius: 20px; transition: opacity .15s;
}
.bubble-btn:hover { opacity: .8; }
.bubble-undo {
  background: var(--sa-primary, #6750A4); color: #fff;
}
.bubble-dismiss {
  background: var(--sa-card-outline, rgba(0,0,0,.08)); color: var(--sa-text-variant);
}
/* 5B-2: 确认气泡专用样式 */
.confirm-bubble {
  border-color: rgba(234,108,31,.35);
}
.bubble-confirm-ok {
  background: #e06c1f; color: #fff;
}

/* ── M3 空状态组件 ── */
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  padding: 56px 24px; text-align: center;
  border-radius: var(--sa-shape-lg); background: var(--sa-card);
  border: 1.5px dashed var(--sa-border);
}
.empty-state-icon { font-size: 44px; margin-bottom: 16px; opacity: 0.35; line-height: 1; }
.empty-state-title {
  font-size: 16px; font-weight: 500; color: var(--sa-text); margin-bottom: 8px;
}
.empty-state-desc {
  font-size: 13px; line-height: 1.7; color: var(--sa-text-variant); max-width: 340px;
}

/* ── M3 状态指示点 ── */
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; display: inline-block;
}
.status-dot.online  { background: var(--sa-state-online); box-shadow: 0 0 0 2px rgba(76,175,80,.2); }
.status-dot.offline { background: var(--sa-state-offline); }
.status-dot.warning { background: var(--sa-state-warning); box-shadow: 0 0 0 2px rgba(255,152,0,.2); }

/* ── M3 Skeleton 加载占位 ── */
.skeleton {
  background: linear-gradient(90deg, var(--sa-border) 25%, var(--sa-secondary-container) 50%, var(--sa-border) 75%);
  background-size: 200% 100%;
  animation: sa-skeleton 1.4s ease infinite;
  border-radius: var(--sa-shape-sm);
}
@keyframes sa-skeleton { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ── AI 场景卡片 ── */
.scene-card {
  background: var(--sa-card);
  border-radius: 0 var(--sa-shape-lg) var(--sa-shape-lg) 0;
  border-top: 1px solid var(--sa-border);
  border-right: 1px solid var(--sa-border);
  border-bottom: 1px solid var(--sa-border);
  margin-bottom: 10px;
  transition: box-shadow .2s;
}
.scene-card:hover { box-shadow: var(--sa-elev-2); }
.scene-card--dimmed { opacity: .6; }

/* ── 设备列表选中 & 离线状态 ── */
.m3-item.dev-row.selected {
  background: var(--sa-primary-container);
  border-color: var(--sa-primary);
}
.m3-item.dev-unavail { opacity: .55; }

/* ── 高对比度模式 ── */
@media (prefers-contrast: more) {
  .btn-outline { border-width: 2px; }
  .chip { border-width: 2px; }
  .m3-item { border-width: 2px; }
  .input { border-width: 2px; }
}

/* ── 减少动画模式 ── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}
`;
