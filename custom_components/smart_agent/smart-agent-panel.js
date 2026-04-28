var _SmartAgentPanel = (() => {
  // src/icons.js
  function getIcons() {
    return {
      settings: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.81,11.69,4.81,12c0,0.31,0.02,0.65,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>`,
      schedule: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>`,
      calendar: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M20 3h-1V1h-2v2H7V1H5v2H4c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 18H4V8h16v13z"/></svg>`,
      delete: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>`,
      check: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>`,
      close: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>`,
      light: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.87-3.13-7-7-7z"/></svg>`,
      switch: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17 7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h10c2.76 0 5-2.24 5-5s-2.24-5-5-5zm0 8c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z"/></svg>`,
      climate: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M22 11h-4.17l3.24-3.24-1.41-1.42L15 11h-2V9l4.66-4.66-1.42-1.41L13 6.17V2h-2v4.17L7.76 2.93 6.34 4.34 11 9v2H9L4.34 6.34 2.93 7.76 6.17 11H2v2h4.17l-3.24 3.24 1.41 1.42L9 13h2v2l-4.66 4.66 1.42 1.41L11 17.83V22h2v-4.17l3.24 3.24 1.42-1.41L13 15v-2h2l4.66 4.66 1.41-1.42L17.83 13H22v-2z"/></svg>`,
      cover: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M20 19V7H4v12H2v2h20v-2h-2zM11 7h2v10h-2V7zM7 7h2v10H7V7zm8 0h2v10h-2V7z"/></svg>`,
      fan: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M12.5 13.5c.4 2.2-1.1 4.2-3.3 4.7-2.2.4-4.3-1.1-4.7-3.3-.3-1.5.3-3 1.3-3.9L4 9.2C2.8 10.5 2 12.3 2 14.3 2 18.6 5.4 22 9.7 22c3.7 0 6.8-2.6 7.5-6.1-.5.4-1 .7-1.6 1-.7.2-1.5.3-2.1-.4z"/></svg>`,
      device: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17 1H7c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-2-2-2zm0 18H7V5h10v14z"/></svg>`,
      sensor: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>`,
      binary_sensor: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34 3-3-3z"/></svg>`,
      home: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>`,
      showroom: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M7 2V1h10v1h3v12h-1v8h-4v-1h-6v1H5v-8H4V2h3zm11 2H6v8h12V4zm-2 14v-4h-8v4h8z"/></svg>`,
      book: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/></svg>`,
      tips: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.87-3.13-7-7-7z"/></svg>`,
      mic: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.39 6.43 5.5 6.92V21h3v-3.08c3.11-.49 5.5-3.39 5.5-6.92h-2z"/></svg>`,
      expand: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M7 10l5 5 5-5z"/></svg>`,
      edit: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>`,
      bolt: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M7 2v11h3v9l7-12h-4l4-8z"/></svg>`,
      profile: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08s5.97 1.09 6 3.08c-1.29 1.94-3.5 3.22-6 3.22z"/></svg>`,
      rule: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>`,
      gauge: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2.05v3.03c3.39.49 6 3.39 6 6.92 0 .9-.18 1.75-.48 2.54l2.6 1.53c.56-1.24.88-2.62.88-4.07 0-5.18-3.95-9.45-9-9.95z"/></svg>`,
      lock: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>`,
      unlock: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6h1.9c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm0 12H6V10h12v10z"/></svg>`,
      search: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>`,
      group: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M2 7h20v2H2V7zm0 4h20v2H2v-2zm0 4h20v2H2v-2z"/></svg>`,
      sort: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h6v-2H3v2zM3 6v2h18V6H3zm0 7h12v-2H3v2z"/></svg>`,
      spark: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9l1.25-2.75L23 5l-2.75-1.25L19 1l-1.25 2.75L15 5l2.75 1.25L19 9zm-7.5.5L9 4 6.5 9.5 1 12l5.5 2.5L9 20l2.5-5.5L17 12l-5.5-2.5zM19 15l-1.25 2.75L15 19l2.75 1.25L19 23l1.25-2.75L23 19l-2.75-1.25L19 15z"/></svg>`,
      play: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`,
      pending: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>`,
      vision: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34 3-3-3z"/></svg>`,
      refresh: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>`,
      upload: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/></svg>`,
      yaml: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M14,2H6C4.9,2,4,2.9,4,4v16c0,1.1,0.9,2,2,2h12c1.1,0,2-0.9,2-2V8L14,2z M18,20H6V4h7v5h5V20z M8,15h2v3H8V15z M11,15h2v3h-2V15z M14,15h2v3h-2V15z M8,11h8v2H8V11z"/></svg>`
    };
  }

  // src/styles.js
  var M3_CSS = `
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
/* 保留 .btn-sm 用于尺寸覆盖 */
md-filled-button, md-filled-tonal-button, md-outlined-button, md-text-button {
  --md-filled-button-container-height: 40px;
  --md-outlined-button-container-height: 40px;
  font-family: 'Google Sans', Roboto, system-ui, sans-serif;
}
md-filled-button.btn-sm, md-outlined-button.btn-sm, md-filled-tonal-button.btn-sm {
  --md-filled-button-container-height: 32px;
  --md-outlined-button-container-height: 32px;
  font-size: 13px;
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

  // src/render/main.js
  var renderMethods = {
    _render() {
      var _a;
      const $ = (id) => this.shadowRoot.getElementById(id);
      const ICO = this._getIcons();
      this.shadowRoot.innerHTML = `<style>${M3_CSS}</style>
      <div class="app-bar">
        <h1 id="appBarTitle"><span style="color:var(--sa-primary);display:flex;align-items:center">${ICO.bolt}</span> SmartAgent</h1>
        <div style="display:flex;gap:12px;align-items:center">
          <md-outlined-button id="helpBtn" style="--md-outlined-button-container-height:32px;font-size:13px">
            <svg slot="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            使用说明
          </md-outlined-button>
          <md-filled-tonal-button id="aiBtn"></md-filled-tonal-button>
        </div>
      </div>

      <!-- ── 使用说明弹窗 ── -->
      <div class="help-overlay" id="helpOverlay">
        <div class="help-dialog">
          <div class="help-header">
            <h2>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              SmartAgent 完整使用说明
            </h2>
            <button class="help-close" id="helpClose">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
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
              <md-filled-tonal-button id="refreshLearningBtn" style="--md-filled-tonal-button-container-height:32px;font-size:12px">刷新</md-filled-tonal-button>
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
                <md-outlined-select id="modeSel" style="min-width:128px;--md-outlined-select-text-field-container-shape:var(--sa-shape-md)">
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
                    <input id="editSceneLabel" class="input" placeholder="场景标签">
                    <input id="editSceneTime" class="input" placeholder="虚拟时间 (HH:MM)">
                    <textarea id="editSceneDesc" class="input" rows="2" placeholder="场景描述 (传给 AI)"></textarea>
                    <textarea id="editSceneHint" class="input" rows="2" placeholder="AI 行为要点"></textarea>
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
                  <div class="input-with-icon" style="position:relative">
                    ${ICO.mic}
                    <input type="text" id="showroomCustomInput" class="input" style="padding-right:60px" placeholder="输入指令，如：打开所有展厅灯...">
                    <md-icon-button id="clearCustomScene" title="清空当前场景"
                      style="position:absolute;right:8px;top:50%;transform:translateY(-50%);opacity:.5">
                      ${ICO.close}
                    </md-icon-button>
                  </div>
                </div>
              </div>

              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px">
                <div class="sys-card">
                  <div class="label-m">自动执行阈值</div>
                  <div class="sys-val-row">
                    <span class="sys-val-num" id="numAVal">--</span>
                    <span class="sys-val-unit">/ 100</span>
                  </div>
                  <input type="range" id="numA" min="50" max="100" step="5" class="range-input">
                </div>
                <div class="sys-card">
                  <div class="label-m">通知推送阈值</div>
                  <div class="sys-val-row">
                    <span class="sys-val-num" id="numNVal">--</span>
                    <span class="sys-val-unit">/ 100</span>
                  </div>
                  <input type="range" id="numN" min="30" max="100" step="5" class="range-input">
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
            <div style="position:relative;margin-bottom:12px">
              <svg style="position:absolute;left:10px;top:50%;transform:translateY(-50%);opacity:.45;pointer-events:none" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
              <input type="text" id="newDevSearch" class="input" placeholder="搜索设备名称或实体 ID…" style="padding-left:34px;width:100%">
            </div>
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
            <div style="position:relative;margin-bottom:12px">
              <svg style="position:absolute;left:10px;top:50%;transform:translateY(-50%);opacity:.45;pointer-events:none" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
              <input type="text" id="cfgDevSearch" class="input" placeholder="搜索已配置设备…" style="padding-left:34px;width:100%">
            </div>
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
                <label class="label-s">摄像头名称 *</label>
                <input type="text" id="vFriendlyName" placeholder="如：展厅摄像头、门口监控" class="m3-select-compact" style="height:40px;padding:0 12px">
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <label class="label-s">对应房间（AI 区域绑定）*</label>
                <select id="vRoom" class="m3-select-compact" style="height:40px;padding:0 12px">
                  <option value="">-- 选择房间 --</option>
                </select>
              </div>
              <div style="display:flex;flex-direction:column;gap:6px;grid-column:1/-1">
                <label class="label-s">RTSP 地址 *</label>
                <input type="text" id="vRtspUrl" placeholder="rtsp://admin:password@192.168.1.x:554/..." class="m3-select-compact" style="height:40px;padding:0 12px;font-family:monospace;font-size:12px">
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <label class="label-s">最低置信度（min_score）<span id="vMinScoreVal" style="color:var(--sa-primary)">0.70</span></label>
                <input type="range" id="vMinScore" min="0.3" max="0.9" step="0.05" value="0.7" style="accent-color:var(--sa-primary)">
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <label class="label-s">追踪阈值（threshold）<span id="vThresholdVal" style="color:var(--sa-primary)">0.85</span></label>
                <input type="range" id="vThreshold" min="0.5" max="0.95" step="0.05" value="0.85" style="accent-color:var(--sa-primary)">
              </div>
              <div style="display:flex;flex-direction:column;gap:6px">
                <label class="label-s">检测帧率（fps）</label>
                <select id="vFps" class="m3-select-compact" style="height:40px;padding:0 12px">
                  <option value="3">3 fps（低功耗）</option>
                  <option value="5" selected>5 fps（推荐）</option>
                  <option value="10">10 fps（高精度）</option>
                </select>
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
                <input type="text" class="input" id="hInput" placeholder="描述您的偏好习惯（可用中文设备名）...">
                <md-filled-button id="addHBtn" style="--md-filled-button-container-height:32px;font-size:13px;white-space:nowrap">添加</md-filled-button>
              </div>
              <div id="hList" class="m3-list"></div>
            </div>
            <div class="card">
              <div class="card-title">${ICO.rule} 推理增强规则 (P1)</div>
              <div style="display:flex;gap:12px;margin-bottom:16px">
                <input type="text" class="input" id="rInput" placeholder="设定推理规则（可用中文设备名）...">
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
                  <div class="hab-search-wrap">
                    ${ICO.search}
                    <input type="text" id="habSearch" class="hab-search" placeholder="搜索设备名称或 entity_id...">
                  </div>
                  <div class="hab-toolbar-right">
                    <div class="m3-select-wrap" style="min-width:110px">
                      <div style="display:flex;align-items:center;gap:4px;pointer-events:none;position:absolute;left:12px">${ICO.sort}</div>
                      <select id="habSort" class="m3-select" style="padding-left:30px">
                        <option value="conf">置信度↓</option>
                        <option value="time">时间</option>
                        <option value="name">设备名</option>
                </select>
                      <div class="m3-select-arrow">${ICO.expand}</div>
              </div>
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
                <div class="m3-select-wrap" style="min-width:220px">
                  <select id="sysLogDate" class="m3-select">
                    <option value="live">实时流水</option>
                  </select>
                  <div class="m3-select-arrow">${ICO.expand}</div>
                </div>
                <md-outlined-button id="sysLogRefresh" title="刷新日期列表" style="--md-outlined-button-container-height:32px;font-size:13px">${ICO.refresh}</md-outlined-button>
                <md-outlined-button id="sysLogDl" style="--md-outlined-button-container-height:32px;font-size:13px">↓ 下载</md-outlined-button>
              </div>
            </div>
            <!-- 搜索 + 统计条 -->
            <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap">
              <div class="input-with-icon" style="flex:1;min-width:200px">
                ${ICO.search}
                <input id="sysLogSearch" class="input" placeholder="关键词搜索（Esc 清除）" style="padding-left:44px;height:36px;font-size:13px">
              </div>
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
              <div class="label-l" style="margin-bottom:4px">显示名称</div>
              <input id="editDevName" class="input" type="text" style="width:100%">
            </div>
            <div>
              <div class="label-l" style="margin-bottom:4px">所属房间</div>
              <div style="display:flex;gap:6px">
                <select id="editDevRoomSel" class="m3-select-compact" style="flex:1;height:38px;padding:0 8px"></select>
                <input id="editDevRoomCustom" class="input" type="text" placeholder="或手动输入…" style="flex:1">
              </div>
            </div>
            <div>
              <div class="label-l" style="margin-bottom:4px">设备类型</div>
              <select id="editDevType" class="m3-select-compact" style="width:100%;height:38px;padding:0 8px">
                <option value="">自动识别</option>
                <option value="light">灯光 (light)</option>
                <option value="switch">开关 (switch)</option>
                <option value="climate">空调 (climate)</option>
                <option value="cover">窗帘 (cover)</option>
                <option value="fan">风扇 (fan)</option>
                <option value="sensor">传感器 (sensor)</option>
                <option value="binary_sensor">二进制传感器</option>
                <option value="media_player">媒体播放器</option>
              </select>
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
      this.shadowRoot.querySelectorAll(".nav-tab").forEach((b) => {
        b.onclick = () => {
          if (b.dataset.group)
            this._setGroup(b.dataset.group);
          else if (b.dataset.t)
            this._setTab(b.dataset.t);
        };
      });
      this.shadowRoot.querySelectorAll(".nav-sub-tab").forEach((b) => {
        b.onclick = () => {
          if (b.dataset.t)
            this._setTab(b.dataset.t);
        };
      });
      this.shadowRoot.querySelectorAll("md-filter-chip[data-filter]").forEach((b) => b.addEventListener("click", () => {
        this._sysLogFilter = b.dataset.filter;
        this.shadowRoot.querySelectorAll("md-filter-chip[data-filter]").forEach((x) => {
          x.selected = x.dataset.filter === this._sysLogFilter;
        });
        this._applySysLogFilter();
      }));
      $("sysLogDate").onchange = (e) => this._onLogDateChange(e.target.value);
      $("sysLogDl").onclick = () => this._downloadSysLog();
      $("sysLogRefresh").onclick = () => {
        this._loadLogDates();
        this._wsRefreshSysLog();
      };
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
      $("aiBtn").onclick = () => this._toggle();
      $("learningModeToggle").addEventListener("change", async (e) => {
        const on = e.target.selected;
        await this._hass.callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_learning_mode" });
        this._msg(on ? "静默学习模式已开启" : "静默学习模式已关闭");
      });
      $("habitProactiveToggle").addEventListener("change", async (e) => {
        const on = e.target.selected;
        await this._hass.callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_habit_proactive" });
        this._msg(on ? "习惯主动询问已开启" : "习惯主动询问已关闭");
      });
      $("frigateToggle").addEventListener("change", async (e) => {
        const on = e.target.selected;
        await this._hass.callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_frigate_enabled" });
        this._msg(on ? "Frigate NVR 视觉感知已启用" : "Frigate NVR 视觉感知已关闭");
      });
      $("visionToggle").addEventListener("change", async (e) => {
        const on = e.target.selected;
        await this._hass.callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_vision_enabled" });
        this._msg(on ? "LLMVision 视觉增强已开启" : "LLMVision 视觉增强已关闭");
      });
      const _fallbackCopy = (text) => {
        try {
          const ta = document.createElement("textarea");
          ta.value = text;
          ta.style.cssText = "position:fixed;left:-9999px;top:-9999px;opacity:0";
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        } catch (err) {
          console.warn("SmartAgent: 复制失败", err);
        }
      };
      let _visionCamsCache = [];
      const _renderVisionCams = (cameras, configPath) => {
        _visionCamsCache = cameras || [];
        const list = $("vCamList");
        if (!list)
          return;
        if (configPath) {
          const hint = $("vConfigPathHint"), pathEl = $("vConfigPath");
          if (hint)
            hint.style.display = "";
          if (pathEl)
            pathEl.textContent = configPath;
        }
        if (!_visionCamsCache.length) {
          list.innerHTML = `<div style="text-align:center;padding:32px;color:var(--md-sys-color-outline);font-size:13px">
          暂无摄像头配置，点击「添加摄像头」开始</div>`;
          return;
        }
        list.innerHTML = _visionCamsCache.map((c) => {
          const room = c.room || "";
          const roomBadge = room ? `<span style="background:var(--sa-primary-container);color:var(--sa-primary);padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600">${this._esc(room)}</span>` : `<span style="background:var(--md-sys-color-surface-container);color:var(--md-sys-color-outline);padding:2px 8px;border-radius:12px;font-size:12px">未绑定房间</span>`;
          const rtspMasked = (c.rtsp_url || "").replace(/:([^@]+)@/, ":***@");
          const zoneCount = (c.zones || []).length;
          const zoneHint = zoneCount ? `<span style="color:var(--md-sys-color-outline);font-size:12px;margin-left:4px">${zoneCount} 个区域</span>` : "";
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
              ID: ${this._esc(c.camera_id)} · min_score: ${(c.min_score || 0.7).toFixed(2)} · fps: ${c.fps || 5}
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
      const _loadVisionCams = async () => {
        try {
          const result = await this._hass.callWS({ type: "smart_agent/get_frigate_cameras" });
          _renderVisionCams((result == null ? void 0 : result.cameras) || [], (result == null ? void 0 : result.config_path) || "");
        } catch (e) {
          const list = $("vCamList");
          if (list)
            list.innerHTML = `<div style="text-align:center;padding:20px;color:var(--md-sys-color-error);font-size:13px">加载失败，请确认 Frigate 已安装：${e.message || e}</div>`;
        }
      };
      const _populateVisionRooms = (selectedRoom) => {
        const sel = $("vRoom");
        if (!sel)
          return;
        while (sel.options.length > 1)
          sel.remove(1);
        const devices = this._wsGet("devices", "devices", []);
        const smRooms = devices.map((d) => d.room || "").filter((r) => r);
        const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a) => a.name) : [];
        const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort((a, b) => a.localeCompare(b, "zh"));
        allRooms.forEach((r) => {
          const opt = document.createElement("option");
          opt.value = r;
          opt.textContent = r;
          sel.appendChild(opt);
        });
        if (selectedRoom)
          sel.value = selectedRoom;
      };
      const _showVisionForm = (cam) => {
        const card = $("vCamFormCard");
        if (!card)
          return;
        card.style.display = "";
        $("vFormTitle").textContent = cam ? "编辑摄像头" : "添加摄像头";
        $("vEditCameraId").value = (cam == null ? void 0 : cam.camera_id) || "";
        $("vFriendlyName").value = (cam == null ? void 0 : cam.friendly_name) || "";
        _populateVisionRooms((cam == null ? void 0 : cam.room) || "");
        $("vRtspUrl").value = (cam == null ? void 0 : cam.rtsp_url) || "";
        $("vMinScore").value = (cam == null ? void 0 : cam.min_score) ?? 0.7;
        $("vMinScoreVal").textContent = parseFloat((cam == null ? void 0 : cam.min_score) ?? 0.7).toFixed(2);
        $("vThreshold").value = (cam == null ? void 0 : cam.threshold) ?? 0.85;
        $("vThresholdVal").textContent = parseFloat((cam == null ? void 0 : cam.threshold) ?? 0.85).toFixed(2);
        $("vFps").value = String((cam == null ? void 0 : cam.fps) ?? 5);
        const status = $("vSaveStatus");
        if (status)
          status.style.display = "none";
        card.scrollIntoView({ behavior: "smooth", block: "start" });
      };
      const _hideVisionForm = () => {
        const card = $("vCamFormCard");
        if (card)
          card.style.display = "none";
      };
      if ($("vMinScore"))
        $("vMinScore").oninput = () => {
          $("vMinScoreVal").textContent = parseFloat($("vMinScore").value).toFixed(2);
        };
      if ($("vThreshold"))
        $("vThreshold").oninput = () => {
          $("vThresholdVal").textContent = parseFloat($("vThreshold").value).toFixed(2);
        };
      if ($("vAddCamBtn"))
        $("vAddCamBtn").onclick = () => _showVisionForm(null);
      if ($("vCancelCamBtn"))
        $("vCancelCamBtn").onclick = _hideVisionForm;
      if ($("vSaveCamBtn"))
        $("vSaveCamBtn").onclick = async () => {
          var _a2, _b, _c, _d, _e, _f, _g;
          const name = (((_a2 = $("vFriendlyName")) == null ? void 0 : _a2.value) || "").trim();
          const rtsp = (((_b = $("vRtspUrl")) == null ? void 0 : _b.value) || "").trim();
          const room = (((_c = $("vRoom")) == null ? void 0 : _c.value) || "").trim();
          if (!name || !rtsp) {
            this._msg("请填写摄像头名称和 RTSP 地址");
            return;
          }
          const status = $("vSaveStatus");
          const btn = $("vSaveCamBtn");
          btn.disabled = true;
          btn.textContent = "部署中...";
          if (status) {
            status.style.display = "";
            status.style.color = "var(--md-sys-color-outline)";
            status.textContent = "⏳ 正在写入 Frigate 配置并重启 Add-on，约需 10-20 秒...";
          }
          try {
            const camId = (((_d = $("vEditCameraId")) == null ? void 0 : _d.value) || "").trim();
            await this._hass.callService("smart_agent", "register_frigate_camera", {
              friendly_name: name,
              rtsp_url: rtsp,
              room,
              camera_id: camId || void 0,
              min_score: parseFloat(((_e = $("vMinScore")) == null ? void 0 : _e.value) || "0.7"),
              threshold: parseFloat(((_f = $("vThreshold")) == null ? void 0 : _f.value) || "0.85"),
              fps: parseInt(((_g = $("vFps")) == null ? void 0 : _g.value) || "5")
            });
            if (status) {
              status.style.color = "var(--md-sys-color-primary)";
              status.textContent = "✅ 配置已部署，Frigate 正在重启生效（约 15 秒）";
            }
            this._msg(`摄像头「${name}」已部署${room ? "，绑定房间：" + room : ""}`);
            setTimeout(async () => {
              _hideVisionForm();
              await _loadVisionCams();
            }, 2e3);
          } catch (e) {
            if (status) {
              status.style.color = "var(--md-sys-color-error)";
              status.textContent = "❌ 部署失败：" + (e.message || e);
            }
            this._msg("部署失败：" + (e.message || e));
          } finally {
            btn.disabled = false;
            btn.textContent = "保存并部署";
          }
        };
      const _roomOptions = (selected) => {
        const devices = this._wsGet("devices", "devices", []);
        const smRooms = devices.map((d) => d.room || "").filter((r) => r);
        const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a) => a.name) : [];
        const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort((a, b) => a.localeCompare(b, "zh"));
        return `<option value="">-- 未绑定 --</option>` + allRooms.map((r) => `<option value="${this._esc(r)}"${r === selected ? " selected" : ""}>${this._esc(r)}</option>`).join("");
      };
      const _zoneOverlay = $("zoneBindOverlay");
      const _zoneDesc = $("zoneBindDesc");
      const _zoneRows = $("zoneBindRows");
      const _zoneSaveBtn = $("zoneBindSave");
      const _zoneCancelBtn = $("zoneBindCancel");
      const _closeZoneOverlay = () => _zoneOverlay == null ? void 0 : _zoneOverlay.classList.remove("open");
      if (_zoneCancelBtn)
        _zoneCancelBtn.onclick = _closeZoneOverlay;
      if (_zoneOverlay)
        _zoneOverlay.onclick = (ev) => {
          if (ev.target === _zoneOverlay)
            _closeZoneOverlay();
        };
      const _showZoneBindDialog = async (camId) => {
        var _a2;
        const cam = _visionCamsCache.find((c) => c.camera_id === camId);
        if (!cam || !_zoneOverlay)
          return;
        let zones = cam.zones || [];
        try {
          const r = await this._hass.callWS({ type: "smart_agent/get_frigate_zones", camera_id: camId });
          if ((_a2 = r == null ? void 0 : r.zones) == null ? void 0 : _a2.length)
            zones = r.zones;
        } catch (_) {
        }
        if (!zones.length) {
          this._msg("该摄像头暂无检测区域（zone），请先在 Frigate 中配置 zones");
          return;
        }
        if (_zoneDesc) {
          _zoneDesc.innerHTML = `摄像头：<strong>${this._esc(cam.friendly_name || camId)}</strong>（${this._esc(camId)}）<br>
          为每个检测区域单独指定对应的房间，AI 将按进入的具体区域触发正确房间的设备`;
        }
        if (_zoneRows) {
          _zoneRows.innerHTML = zones.map((z) => {
            const displayName = z.friendly_name && z.friendly_name !== z.zone_id ? z.friendly_name : z.zone_id;
            const isRawId = !z.friendly_name || z.friendly_name === z.zone_id;
            return `
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
              <div style="flex:0 0 150px;font-size:14px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${this._esc(z.zone_id)}">
                ${this._esc(displayName)}
                ${isRawId ? `<div style="font-size:10px;color:var(--md-sys-color-outline);font-weight:400">未设中文名</div>` : `<div style="font-size:10px;color:var(--md-sys-color-outline)">${this._esc(z.zone_id)}</div>`}
              </div>
              <select data-zone-id="${this._esc(z.zone_id)}" data-zone-name="${this._esc(z.friendly_name || z.zone_id)}"
                style="flex:1;padding:6px 10px;border:1px solid var(--md-sys-color-outline-variant);border-radius:8px;font-size:13px;background:var(--md-sys-color-surface-container);color:var(--md-sys-color-on-surface)">
                ${_roomOptions(z.room || "")}
              </select>
            </div>`;
          }).join("");
        }
        if (_zoneSaveBtn) {
          _zoneSaveBtn.onclick = async () => {
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
                  room: sel.value
                });
                ok++;
              } catch (_) {
                fail++;
              }
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
      const visionView = $("view-vision");
      if (visionView) {
        visionView.addEventListener("click", async (e) => {
          const btn = e.target.closest("[data-action]");
          if (!btn)
            return;
          const camId = btn.dataset.camId;
          if (btn.dataset.action === "edit") {
            const cam = _visionCamsCache.find((c) => c.camera_id === camId);
            if (cam)
              _showVisionForm(cam);
          } else if (btn.dataset.action === "zones") {
            await _showZoneBindDialog(camId);
          } else if (btn.dataset.action === "delete") {
            if (!await this._showConfirm(`确定删除摄像头 ${camId}？此操作会同时从 Frigate 配置文件中移除并重启 Frigate。`))
              return;
            try {
              await this._hass.callService("smart_agent", "delete_frigate_camera", { camera_id: camId });
              this._msg("摄像头已删除，Frigate 正在重启");
              await _loadVisionCams();
            } catch (err) {
              this._msg("删除失败：" + (err.message || err));
            }
          }
        });
      }
      const _origSetTab = (_a = this._setTab) == null ? void 0 : _a.bind(this);
      if (!this._visionTabHooked && _origSetTab) {
        this._visionTabHooked = true;
        const _origSetTabFn = this._setTab;
        this._setTab = (tab) => {
          _origSetTabFn.call(this, tab);
          if (tab === "vision")
            _loadVisionCams();
        };
      }
      const helpOverlay = $("helpOverlay");
      $("helpBtn").onclick = () => {
        helpOverlay.classList.add("open");
        const firstNav = helpOverlay.querySelector(".help-nav-item");
        if (firstNav)
          firstNav.classList.add("active");
      };
      $("helpClose").onclick = () => helpOverlay.classList.remove("open");
      helpOverlay.onclick = (e) => {
        if (e.target === helpOverlay)
          helpOverlay.classList.remove("open");
      };
      helpOverlay.querySelectorAll(".help-nav-item").forEach((item) => {
        item.onclick = () => {
          helpOverlay.querySelectorAll(".help-nav-item").forEach((i) => i.classList.remove("active"));
          item.classList.add("active");
          const sec = item.dataset.sec;
          const target = helpOverlay.querySelector("#hsec-" + sec);
          if (target)
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        };
      });
      const helpBody = $("helpBody");
      if (helpBody) {
        helpBody.addEventListener("scroll", () => {
          const sections = helpBody.querySelectorAll(".help-section[id]");
          let current = "";
          sections.forEach((s) => {
            if (s.offsetTop - helpBody.scrollTop <= 60)
              current = s.id.replace("hsec-", "");
          });
          if (current) {
            helpOverlay.querySelectorAll(".help-nav-item").forEach((i) => {
              i.classList.toggle("active", i.dataset.sec === current);
            });
          }
        });
      }
      const licGotoBtn = $("licGotoOptionsBtn");
      if (licGotoBtn) {
        licGotoBtn.onclick = () => {
          const url = `/config/integrations/integration/smart_agent`;
          window.location.href = url;
        };
      }
      const licVerifyBtn = $("licVerifyBtn");
      if (licVerifyBtn) {
        licVerifyBtn.onclick = async () => {
          licVerifyBtn.disabled = true;
          licVerifyBtn.textContent = "验证中…";
          try {
            await this._hass.callService("smart_agent", "verify_license", {});
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
      this.shadowRoot.getElementById("addHBtn").onclick = async () => {
        const inp = this.shadowRoot.getElementById("hInput");
        const v = inp.value.trim();
        if (!v)
          return;
        inp.value = "";
        this._msg("画像已添加");
        try {
          await this._hass.callService("smart_agent", "add_habit", { content: v });
          delete this._wsData["rules"];
          delete this._wsData["habits"];
          await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
            await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
          });
        } catch (e) {
          this._msg("添加失败: " + e.message);
        }
      };
      this.shadowRoot.getElementById("addRBtn").onclick = async () => {
        const inp = this.shadowRoot.getElementById("rInput");
        const v = inp.value.trim();
        if (!v)
          return;
        inp.value = "";
        this._msg("规则已添加");
        try {
          await this._hass.callService("smart_agent", "add_rule", { content: v });
          delete this._wsData["rules"];
          delete this._wsData["habits"];
          await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
            await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
          });
        } catch (e) {
          this._msg("添加失败: " + e.message);
        }
      };
      const devToggle = this.shadowRoot.getElementById("devLookupToggle");
      const devPanel = this.shadowRoot.getElementById("devLookupPanel");
      const devArrow = this.shadowRoot.getElementById("devLookupArrow");
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
          var _a2, _b, _c;
          const q = devInput.value.trim().toLowerCase();
          if (!q) {
            devResults.innerHTML = '<span style="opacity:.6">输入关键词即可搜索</span>';
            return;
          }
          const domains = ["light", "switch", "climate", "cover", "fan", "binary_sensor", "sensor", "media_player"];
          const matches = [];
          for (const [eid, state] of Object.entries(((_a2 = this._hass) == null ? void 0 : _a2.states) || {})) {
            if (!domains.some((d) => eid.startsWith(d + ".")))
              continue;
            const name = (((_b = state.attributes) == null ? void 0 : _b.friendly_name) || "").toLowerCase();
            if (name.includes(q) || eid.toLowerCase().includes(q)) {
              matches.push({ eid, name: ((_c = state.attributes) == null ? void 0 : _c.friendly_name) || eid });
            }
            if (matches.length >= 20)
              break;
          }
          if (!matches.length) {
            devResults.innerHTML = '<span style="opacity:.5">未找到匹配设备</span>';
            return;
          }
          devResults.innerHTML = matches.map(
            (m) => `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--md-sys-color-outline-variant)">
            <span style="flex:1;font-weight:500">${this._esc(m.name)}</span>
            <code class="dev-search-copy-btn" data-eid="${this._esc(m.eid)}"
              style="font-size:11px;color:var(--md-sys-color-primary);background:var(--md-sys-color-primary-container);padding:2px 6px;border-radius:4px;cursor:pointer"
              title="点击复制">
              ${this._esc(m.eid)}
            </code>
          </div>`
          ).join("");
          devResults.querySelectorAll(".dev-search-copy-btn").forEach((el) => {
            el.addEventListener("click", function() {
              const eid = this.dataset.eid;
              if (navigator.clipboard) {
                navigator.clipboard.writeText(eid).catch(() => {
                });
              } else {
                const ta = document.createElement("textarea");
                ta.value = eid;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand("copy");
                document.body.removeChild(ta);
              }
              const orig = this.textContent.trim();
              this.textContent = "✅ 已复制";
              setTimeout(() => {
                this.textContent = orig;
              }, 1500);
            });
          });
        };
      }
      const engSelEl = this.shadowRoot.getElementById("engSel");
      if (engSelEl) {
        engSelEl.onchange = (e) => {
          this._hass.callService("select", "select_option", { entity_id: "select.smart_agent_engine", option: e.target.value });
          this._msg("推理引擎已切换");
        };
      }
      const numAEl = this.shadowRoot.getElementById("numA");
      if (numAEl) {
        numAEl.addEventListener("input", (e) => {
          this.shadowRoot.getElementById("numAVal").textContent = e.target.value;
        });
        numAEl.addEventListener("change", (e) => {
          this._hass.callService("number", "set_value", { entity_id: "number.smart_agent_confidence_auto", value: parseFloat(e.target.value) });
        });
      }
      const numNEl = this.shadowRoot.getElementById("numN");
      if (numNEl) {
        numNEl.addEventListener("input", (e) => {
          this.shadowRoot.getElementById("numNVal").textContent = e.target.value;
        });
        numNEl.addEventListener("change", (e) => {
          this._hass.callService("number", "set_value", { entity_id: "number.smart_agent_confidence_notify", value: parseFloat(e.target.value) });
        });
      }
      const modeSelEl = this.shadowRoot.getElementById("modeSel");
      if (modeSelEl) {
        modeSelEl.addEventListener("change", async (e) => {
          const mode = e.target.value;
          if (mode !== "home" && mode !== "showroom")
            return;
          await this._hass.callService("smart_agent", "set_mode", { mode });
          this._msg(mode === "showroom" ? "已切换为展厅模式" : "已切换为家庭模式");
        });
      }
      this.shadowRoot.getElementById("showroomSceneBtns").addEventListener("click", async (e) => {
        const sceneBtn = e.target.closest(".showroom-scene-btn");
        const editBtn = e.target.closest(".showroom-edit-btn");
        if (sceneBtn) {
          const scene = sceneBtn.dataset.scene;
          const customInput2 = this.shadowRoot.getElementById("showroomCustomInput");
          if (customInput2)
            customInput2.value = "";
          await this._hass.callService("smart_agent", "set_showroom_scene", { scene, custom_prompt: "" });
          this._msg("展厅场景: " + sceneBtn.dataset.label);
        } else if (editBtn) {
          this._openSceneEdit(editBtn.dataset.scene);
        }
      });
      const _sceneModeCmd = this.shadowRoot.getElementById("sceneModeCmd");
      const _sceneModePersist = this.shadowRoot.getElementById("sceneModePersist");
      const _sceneModeHint = this.shadowRoot.getElementById("sceneModeHint");
      const _isCommandMode = () => !_sceneModeCmd.dataset.inactive;
      const _setSceneMode = (isCmd) => {
        if (isCmd) {
          _sceneModeCmd.style.background = "var(--sa-primary)";
          _sceneModeCmd.style.color = "var(--sa-on-primary)";
          _sceneModeCmd.style.fontWeight = "600";
          _sceneModePersist.style.background = "transparent";
          _sceneModePersist.style.color = "var(--sa-on-surface-variant)";
          delete _sceneModeCmd.dataset.inactive;
          _sceneModePersist.dataset.inactive = "1";
          _sceneModeHint.textContent = "执行一次后自动清空，不影响巡检";
          _sceneModeHint.style.color = "var(--sa-primary)";
        } else {
          _sceneModePersist.style.background = "var(--sa-primary)";
          _sceneModePersist.style.color = "var(--sa-on-primary)";
          _sceneModePersist.style.fontWeight = "600";
          _sceneModeCmd.style.background = "transparent";
          _sceneModeCmd.style.color = "var(--sa-on-surface-variant)";
          delete _sceneModePersist.dataset.inactive;
          _sceneModeCmd.dataset.inactive = "1";
          _sceneModeHint.textContent = "持续作为场景背景，每次巡检都生效";
          _sceneModeHint.style.color = "var(--sa-secondary, #666)";
        }
      };
      _sceneModeCmd.onclick = () => _setSceneMode(true);
      _sceneModePersist.onclick = () => _setSceneMode(false);
      _setSceneMode(true);
      const customInput = this.shadowRoot.getElementById("showroomCustomInput");
      const clearBtn = this.shadowRoot.getElementById("clearCustomScene");
      if (clearBtn) {
        clearBtn.onclick = async () => {
          customInput.value = "";
          await this._hass.callService("smart_agent", "set_showroom_scene", {
            scene: "",
            custom_prompt: "",
            is_command: false
          });
          this._msg("✨ 已清空展厅自定义场景");
        };
      }
      const _submitCustomScene = async () => {
        const v = customInput.value.trim();
        if (!v)
          return;
        const isCmd = _isCommandMode();
        await this._hass.callService("smart_agent", "set_showroom_scene", {
          scene: "",
          custom_prompt: v,
          is_command: isCmd
        });
        if (isCmd) {
          this._msg("✅ 一次性指令已发送，执行后自动清空");
          customInput.value = "";
        } else {
          this._msg("💾 持久场景已设置，巡检时持续生效");
        }
      };
      customInput.onkeydown = async (e) => {
        if (e.key !== "Enter")
          return;
        await _submitCustomScene();
        customInput.blur();
      };
      customInput.onblur = async (e) => {
        if (e.relatedTarget && (e.relatedTarget.classList.contains("showroom-scene-btn") || e.relatedTarget.classList.contains("showroom-edit-btn") || ["editSceneSave", "editSceneCancel", "sceneModeCmd", "sceneModePersist"].includes(e.relatedTarget.id)))
          return;
        await _submitCustomScene();
      };
      this.shadowRoot.getElementById("editSceneSave").onclick = async () => {
        const key = this._editingSceneKey;
        if (!key)
          return;
        const $2 = (id) => this.shadowRoot.getElementById(id);
        await this._hass.callService("smart_agent", "update_showroom_scene_config", {
          scene_key: key,
          label: $2("editSceneLabel").value.trim() || void 0,
          virtual_time: $2("editSceneTime").value.trim() || void 0,
          scene_desc: $2("editSceneDesc").value.trim() || void 0,
          hint: $2("editSceneHint").value.trim() || void 0
        });
        $2("showroomEditPanel").style.display = "none";
        this._editingSceneKey = null;
        this._msg("场景配置已保存");
        setTimeout(() => this._renderConfig(), 500);
      };
      this.shadowRoot.getElementById("editSceneCancel").onclick = () => {
        this.shadowRoot.getElementById("showroomEditPanel").style.display = "none";
        this._editingSceneKey = null;
      };
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
      const _renderLearningStats = (data) => {
        const box = $("learningStats");
        if (!box)
          return;
        const _pill = (label, value, color, icon) => `
        <div style="background:var(--md-sys-color-surface-container);border-radius:12px;padding:12px;text-align:center;display:flex;flex-direction:column;gap:4px">
          <div style="font-size:11px;color:var(--md-sys-color-outline)">${icon} ${label}</div>
          <div style="font-size:22px;font-weight:700;color:${color}">${value}</div>
        </div>`;
        const deviceCoverage = data.total_devices > 0 ? Math.round((1 - data.noroom_devices / data.total_devices) * 100) : 0;
        const coverageColor = deviceCoverage >= 90 ? "var(--sa-primary)" : deviceCoverage >= 60 ? "#F59E0B" : "var(--md-sys-color-error)";
        box.innerHTML = [
          _pill("到达基线", data.arrival_baseline || 0, "var(--sa-primary)", "📍"),
          _pill("用户纠正", data.corrections || 0, "#F59E0B", "✏️"),
          _pill("决策缓存", data.decision_cache || 0, "var(--sa-primary)", "⚡"),
          _pill("缓存命中", data.decision_cache_hits || 0, "#10B981", "🎯"),
          _pill("行为模式", data.behavior_patterns || 0, "var(--sa-primary)", "📊"),
          _pill("失败反思", data.reflexion_patterns || 0, "#8B5CF6", "🔄"),
          _pill("区域覆盖", deviceCoverage + "%", coverageColor, "🏠")
        ].join("");
        const warn = $("learningDeviceWarning");
        if (warn && data.noroom_devices > 0) {
          warn.style.display = "";
          warn.innerHTML = `⚠️ 有 <b>${data.noroom_devices}</b> 个设备未配置区域（共 ${data.total_devices} 个），AI 无法判断这些设备属于哪个房间。
          <button id="goFixNoRoom" style="margin-left:8px;padding:3px 12px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;font-size:12px">前往修复 →</button>`;
          const fixBtn = $("goFixNoRoom");
          if (fixBtn)
            fixBtn.onclick = () => {
              this._filterNoRoom = true;
              this._setTab("devices");
            };
        } else if (warn) {
          warn.style.display = "none";
        }
        const trendBox = $("learningTrend");
        if (trendBox && data.correction_trend && data.correction_trend.length > 0) {
          trendBox.style.display = "";
          const maxCount = Math.max(...data.correction_trend.map((d) => d.count), 1);
          trendBox.innerHTML = `
          <div style="font-size:12px;color:var(--md-sys-color-outline);margin-bottom:8px">📈 近 7 天纠正趋势</div>
          <div style="display:flex;align-items:flex-end;gap:4px;height:60px">
            ${data.correction_trend.map((d) => {
            const h = Math.max(4, d.count / maxCount * 56);
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
        const topBox = $("learningTopCorrected");
        if (topBox && data.top_corrected && data.top_corrected.length > 0) {
          topBox.style.display = "";
          topBox.innerHTML = `
          <div style="font-size:12px;color:var(--md-sys-color-outline);margin-bottom:8px">🔧 被纠正最多的设备 Top-5</div>
          ${data.top_corrected.map((d) => {
            const devName = (this._wsGet("devices", "devices", []).find((dev) => dev.entity_id === d.entity_id) || {}).name || d.entity_id;
            return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px">
              <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${devName}</span>
              <span style="color:#F59E0B;font-weight:600;flex-shrink:0">${d.count} 次</span>
            </div>`;
          }).join("")}`;
        } else if (topBox) {
          topBox.style.display = "none";
        }
      };
      const _loadLearningStats = async () => {
        try {
          const data = await this._hass.callWS({ type: "smart_agent/get_learning_stats" });
          _renderLearningStats(data);
        } catch (e) {
          const box = $("learningStats");
          if (box)
            box.innerHTML = `<div style="text-align:center;padding:16px;color:var(--md-sys-color-outline);font-size:13px;grid-column:1/-1">暂无数据</div>`;
        }
      };
      if ($("refreshLearningBtn"))
        $("refreshLearningBtn").onclick = _loadLearningStats;
      _loadLearningStats();
      this._setTab("dashboard");
      this._applyBrand();
    }
  };

  // src/render/syslog.js
  var syslogMethods = {
    async _wsRefreshSysLog() {
      if (this._sysLogMode !== "live")
        return;
      if (this._sysLogRefreshing)
        return;
      this._sysLogRefreshing = true;
      const box = this.shadowRoot.getElementById("sysLogBox");
      try {
        const result = await this._hass.callWS({ type: "smart_agent/get_sys_log" });
        const html = (result == null ? void 0 : result.html) || "";
        if (box) {
          if (html) {
            box.innerHTML = html;
            this._applySysLogFilter();
          } else {
            box.innerHTML = '<span style="opacity:.5">暂无系统日志（等待 HA 产生日志后自动显示）</span>';
          }
        }
      } catch (e) {
        if (box)
          box.innerHTML = `<span style="opacity:.5;color:var(--sa-error)">日志服务暂不可用：${this._esc(String(e.message || e))}</span>`;
      } finally {
        this._sysLogRefreshing = false;
      }
    },
    _applySysLogFilter() {
      const box = this.shadowRoot.getElementById("sysLogBox");
      if (!box)
        return;
      const rows = box.querySelectorAll(".sl-row");
      const f = this._sysLogFilter || "all";
      const kw = (this._sysLogKeyword || "").toLowerCase();
      let total = 0, errs = 0, warns = 0, infos = 0;
      rows.forEach((row) => {
        const lvl = row.getAttribute("data-level") || "";
        const txt = row.textContent || "";
        const txtLow = txt.toLowerCase();
        let levelMatch = true;
        if (f === "INFO")
          levelMatch = lvl === "sl-i";
        else if (f === "WARN")
          levelMatch = lvl === "sl-w";
        else if (f === "ERROR")
          levelMatch = lvl === "sl-e";
        else if (f === "protect")
          levelMatch = txt.includes("保护") || txt.includes("冷却") || txt.includes("过滤");
        else if (f === "trigger")
          levelMatch = txt.includes("触发") || txt.includes("事件") || txt.includes("调度");
        const kwMatch = !kw || txtLow.includes(kw);
        const visible = levelMatch && kwMatch;
        row.style.display = visible ? "" : "none";
        if (visible) {
          total++;
          if (lvl === "sl-e")
            errs++;
          else if (lvl === "sl-w")
            warns++;
          else
            infos++;
        }
      });
      const el = (id) => this.shadowRoot.getElementById(id);
      const stTotal = el("statTotal");
      const stErr = el("statErr");
      const stWarn = el("statWarn");
      const stInfo = el("statInfo");
      if (stTotal)
        stTotal.textContent = `共 ${total} 条`;
      if (stErr) {
        stErr.textContent = `● 错误 ${errs}`;
        stErr.style.display = errs ? "" : "none";
      }
      if (stWarn) {
        stWarn.textContent = `● 警告 ${warns}`;
        stWarn.style.display = warns ? "" : "none";
      }
      if (stInfo) {
        stInfo.textContent = `● 信息 ${infos}`;
        stInfo.style.display = infos && f !== "all" ? "" : "none";
      }
    },
    _downloadSysLog() {
      const box = this.shadowRoot.getElementById("sysLogBox");
      if (!box)
        return;
      const rows = box.querySelectorAll(".sl-row");
      const lines = [];
      rows.forEach((r) => lines.push(r.textContent));
      const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const dateSuffix = this._sysLogMode === "live" ? (/* @__PURE__ */ new Date()).toISOString().slice(0, 10) : this._sysLogMode;
      a.download = `smart_agent_log_${dateSuffix}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    },
    async _loadLogDates() {
      const sel = this.shadowRoot.getElementById("sysLogDate");
      if (!sel)
        return;
      const refreshBtn = this.shadowRoot.getElementById("sysLogRefresh");
      if (refreshBtn)
        refreshBtn.disabled = true;
      try {
        let infos = null;
        try {
          infos = await this._hass.callApi("GET", "smart_agent/log_info");
        } catch (_) {
          infos = null;
        }
        const currentVal = sel.value;
        sel.innerHTML = '<option value="live">⚡ 实时流水</option>';
        if (Array.isArray(infos) && infos.length > 0) {
          infos.forEach((item) => {
            const opt = document.createElement("option");
            opt.value = item.date;
            const sizeStr = item.size_kb > 0 ? ` · ${item.size_kb}KB` : "";
            const errStr = item.errors > 0 ? ` ⚠${item.errors}` : "";
            const label = item.today ? `📅 ${item.date} 今天${sizeStr}${errStr}` : `${item.date}${sizeStr}${errStr}`;
            opt.textContent = label;
            sel.appendChild(opt);
          });
          const info = this.shadowRoot.getElementById("sysLogInfo");
          if (info && this._sysLogMode === "live") {
            info.title = `共 ${infos.length} 天历史记录，最大保留 30 天`;
          }
        } else {
          const dates = await this._hass.callApi("GET", "smart_agent/log_dates");
          if (Array.isArray(dates)) {
            const today = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
            dates.forEach((d) => {
              const opt = document.createElement("option");
              opt.value = d;
              opt.textContent = d === today ? `📅 ${d} 今天` : d;
              sel.appendChild(opt);
            });
          }
        }
        if (currentVal && [...sel.options].some((o) => o.value === currentVal)) {
          sel.value = currentVal;
        }
      } catch (e) {
      } finally {
        if (refreshBtn)
          refreshBtn.disabled = false;
      }
    },
    async _onLogDateChange(val) {
      const box = this.shadowRoot.getElementById("sysLogBox");
      const info = this.shadowRoot.getElementById("sysLogInfo");
      if (val === "live") {
        this._sysLogMode = "live";
        if (info)
          info.textContent = "实时模式 — 自动刷新最近500条 | 历史文件保留7天";
        this._wsRefreshSysLog();
        return;
      }
      this._sysLogMode = val;
      if (info)
        info.textContent = `查看历史日志: ${val} — 加载中...`;
      if (box)
        box.innerHTML = '<span style="opacity:.5">加载中...</span>';
      try {
        const resp = await this._hass.callApi("GET", `smart_agent/log_content?date=${val}`);
        const content = (resp == null ? void 0 : resp.content) || "";
        if (!content) {
          if (box)
            box.innerHTML = '<span style="opacity:.5">该日期无日志记录</span>';
          if (info)
            info.textContent = `${val} — 无记录`;
          return;
        }
        const lines = content.split("\n").filter((l) => l.trim());
        const lineCount = lines.length;
        if (info)
          info.textContent = `${val} — 共 ${lineCount} 条记录`;
        if (box) {
          const html = lines.reverse().map((line) => {
            let cls = "sl-i";
            if (line.includes("[WARNING]") || line.includes("[WARN]"))
              cls = "sl-w";
            else if (line.includes("[ERROR]"))
              cls = "sl-e";
            const escaped = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            return `<div class="sl-row ${cls}" data-level="${cls}">${escaped}</div>`;
          }).join("");
          box.innerHTML = html;
          this._applySysLogFilter();
        }
      } catch (e) {
        if (box)
          box.innerHTML = `<span style="color:var(--sa-err)">加载失败: ${this._esc(e.message || String(e))}</span>`;
        if (info)
          info.textContent = `${val} — 加载失败`;
      }
    }
  };

  // src/constants.js
  var TARGET_DOMAINS = [
    "light",
    "switch",
    "binary_sensor",
    "sensor",
    "climate",
    "cover",
    "media_player",
    "device_tracker",
    "fan"
  ];
  var SKIP_KW = [
    // HA 系统内置
    "sun.sun",
    "sensor.sun_next_",
    "zigbee2mqtt_bridge",
    "zone.",
    "persistent_notification",
    "script.",
    "automation.",
    "scene.",
    "input_",
    "timer.",
    "counter.",
    "schedule.",
    "weather.",
    "image.",
    "update.",
    "smart_agent",
    "backup.",
    "sensor.backup_",
    // 电池 / 信号 / 硬件诊断
    "_battery",
    "_battery_level",
    "_battery_low",
    "_lqi",
    "_rssi",
    "_linkquality",
    "_tamper",
    // HA 平台内部辅助
    "number.",
    "button.",
    "select.",
    "text.",
    "camera.",
    // Frigate 噪声实体（缩略图/调试）
    "_thumbnail",
    "_snapshot",
    "_debug",
    "frigate_version",
    // Frigate 统计计数传感器（纯数字，无动作价值）
    // 注意：_person_occupancy / _all_occupancy 不在此处过滤——
    //       binary_sensor.{zone}_person_occupancy 是布尔占用传感器，AI 可用作触发源
    "_all_count",
    "_all_active_count",
    "_person_count",
    "_person_active_count",
    "_review_alerts",
    "_review_detections",
    // Frigate 录像控制（不应被 AI 托管）
    "_recordings",
    // LeMesh 遥控器 MAC 传感器（仅透传按键，非受控设备）
    "_wy0c09_remote_",
    // 其他遥控器按键上报
    "_remote_on_off",
    "_remote_dim"
  ];
  var SKIP_NAME_KW = [
    "电量",
    "电池",
    "信号",
    "rssi",
    "lqi",
    "tamper",
    "篡改",
    "备份",
    "backup",
    "遥控器",
    "remote key",
    "按键上报"
  ];
  var DOMAIN_LABELS = {
    light: "灯光",
    switch: "开关",
    binary_sensor: "传感器",
    sensor: "数值",
    climate: "空调",
    cover: "窗帘",
    media_player: "媒体",
    device_tracker: "位置",
    fan: "风扇"
  };

  // src/render/habits.js
  var habitsMethods = {
    _renderHabitPatterns() {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const patterns = this._wsGet("behavior_patterns", "patterns", []);
      const statRow = $("habitStatRow");
      const tbl = $("habitPatTable");
      if (!tbl)
        return;
      const ICO = this._getIcons();
      const total = patterns.length;
      const active = patterns.filter((p) => p.confidence >= 60).length;
      const avgConf = total ? Math.round(patterns.reduce((s, p) => s + p.confidence, 0) / total) : 0;
      const deviceCount = total ? new Set(patterns.map((p) => p.entity_id)).size : 0;
      if (statRow) {
        statRow.innerHTML = [
          `<span class="hab-stat-chip">${ICO.schedule} ${total} 条规律</span>`,
          total ? `<span class="hab-stat-chip">${ICO.device} ${deviceCount} 个设备</span>` : "",
          total ? `<span class="hab-stat-chip" style="color:var(--sa-succ);border-color:rgba(20,108,46,.2);background:var(--sa-succ-bg)">${ICO.check} ${active} 条激活</span>` : "",
          total ? `<span class="hab-stat-chip">${ICO.gauge} 平均置信度 ${avgConf}%</span>` : ""
        ].join("");
      }
      if (!total) {
        const domFilterEl2 = $("habDomainFilter");
        if (domFilterEl2)
          domFilterEl2.innerHTML = "";
        tbl.innerHTML = `
        <div class="hab-empty">
          <div class="hab-empty-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="currentColor"><path d="M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z"/></svg>
          </div>
          <div class="hab-empty-title">暂无行为规律</div>
          <div class="hab-empty-desc">开启「静默学习模式」，记录一段时间的日常操作后，系统会自动分析并提取您的行为习惯规律。</div>
        </div>`;
        return;
      }
      const domains = [...new Set(patterns.map((p) => (p.entity_id || "").split(".")[0]))].sort();
      const domFilterEl = $("habDomainFilter");
      if (domFilterEl) {
        const df = this._habDomainFilter || "all";
        domFilterEl.innerHTML = ["all", ...domains].map((d) => {
          const cnt = d === "all" ? total : patterns.filter((p) => (p.entity_id || "").split(".")[0] === d).length;
          const lbl = d === "all" ? "全部" : DOMAIN_LABELS[d] || this._esc(d);
          return `<button class="chip hab-df-btn ${df === d ? "active" : ""}" data-d="${this._esc(d)}">${lbl} (${cnt})</button>`;
        }).join("");
        domFilterEl.querySelectorAll(".hab-df-btn").forEach((b) => {
          b.onclick = () => {
            this._habDomainFilter = b.dataset.d;
            this._renderHabitPatterns();
          };
        });
      }
      const search = (this._habSearch || "").toLowerCase().trim();
      const domFilt = this._habDomainFilter || "all";
      let filtered = patterns.filter((p) => {
        if (domFilt !== "all" && (p.entity_id || "").split(".")[0] !== domFilt)
          return false;
        if (search) {
          const n = (p.name || p.entity_id || "").toLowerCase();
          const e = (p.entity_id || "").toLowerCase();
          if (!n.includes(search) && !e.includes(search))
            return false;
        }
        return true;
      });
      const sortKey = this._habSort || "conf";
      if (sortKey === "conf")
        filtered.sort((a, b) => b.confidence - a.confidence);
      else if (sortKey === "time")
        filtered.sort((a, b) => (a.time_label || "").localeCompare(b.time_label || ""));
      else if (sortKey === "name")
        filtered.sort(
          (a, b) => (a.name || a.entity_id || "").localeCompare(b.name || b.entity_id || "")
        );
      if (!filtered.length) {
        tbl.innerHTML = `<div class="body-s" style="text-align:center;padding:32px;opacity:.5">无匹配结果，请调整搜索条件</div>`;
        return;
      }
      const ON_STATES = /* @__PURE__ */ new Set(["on", "open", "playing", "heat", "cool", "auto", "fan_only"]);
      const confFillClass = (c) => c >= 80 ? "hab-conf-high" : c >= 60 ? "hab-conf-mid" : "hab-conf-low";
      const confColor = (c) => c >= 80 ? "var(--sa-succ)" : c >= 60 ? "var(--sa-primary)" : "var(--sa-text2)";
      const domainIcon = (eid) => {
        const d = (eid || "").split(".")[0];
        return ICO[d] || ICO.device;
      };
      const stateChipCls = (s) => ON_STATES.has(s) ? "hab-chip hab-chip-on" : "hab-chip hab-chip-off";
      const stateIco = (s) => ON_STATES.has(s) ? ICO.check : ICO.close;
      const confChip = (p) => `
      <span class="hab-conf-chip">
        <span class="hab-conf-track"><span class="hab-conf-fill ${confFillClass(p.confidence)}" style="width:${p.confidence}%"></span></span>
        <span class="hab-conf-val" style="color:${confColor(p.confidence)}">${p.confidence}%</span>
      </span>`;
      let h = "";
      if (this._habGrouped) {
        const groups = /* @__PURE__ */ new Map();
        filtered.forEach((p) => {
          const key = p.entity_id || "unknown";
          if (!groups.has(key)) {
            groups.set(key, { name: p.name || p.entity_id, eid: p.entity_id, items: [] });
          }
          groups.get(key).items.push(p);
        });
        h += `<div class="hab-list">`;
        for (const [, g] of groups) {
          h += `
          <div class="hab-dev-section">
            <div class="hab-dev-header">
              <div class="hab-dev-icon">${domainIcon(g.eid)}</div>
              <div style="flex:1;min-width:0">
                <div class="hab-dev-name">${this._esc(g.name)}</div>
                <div class="hab-dev-eid">${this._esc(g.eid)}</div>
              </div>
              <span class="hab-dev-badge">${g.items.length} 条规律</span>
            </div>
            <div class="hab-dev-rows">`;
          g.items.forEach((p) => {
            const isActive = p.confidence >= 60;
            const st = (p.expected_state || "").toLowerCase();
            h += `
              <div class="hab-row-compact${isActive ? "" : " hab-inactive"}">
                <span class="${stateChipCls(st)}">${stateIco(st)} ${this._esc(p.state_cn || p.expected_state)}</span>
                <span class="hab-chip">${ICO.schedule} ${this._esc(p.time_label)}</span>
                <span class="hab-chip">${ICO.calendar} ${this._esc(p.weekday)}</span>
                ${confChip(p)}
                <button class="hab-del-btn" data-id="${p.id}" title="删除此规律">${ICO.delete}</button>
              </div>`;
          });
          h += `
            </div>
          </div>`;
        }
        h += `</div>`;
      } else {
        h += `<div class="hab-list">`;
        filtered.forEach((p) => {
          const isActive = p.confidence >= 60;
          const st = (p.expected_state || "").toLowerCase();
          h += `
          <div class="hab-item${isActive ? "" : " hab-inactive"}">
            <div class="hab-icon-wrap ${ON_STATES.has(st) ? "state-on" : "state-off"}">${domainIcon(p.entity_id)}</div>
            <div class="hab-body">
              <div class="hab-name">${this._esc(p.name || p.entity_id)}</div>
              <div class="hab-eid">${this._esc(p.entity_id)}</div>
              <div class="hab-chips">
                <span class="${stateChipCls(st)}">${stateIco(st)} ${this._esc(p.state_cn || p.expected_state)}</span>
                <span class="hab-chip">${ICO.schedule} ${this._esc(p.time_label)}</span>
                <span class="hab-chip">${ICO.calendar} ${this._esc(p.weekday)}</span>
                ${confChip(p)}
              </div>
            </div>
            <button class="hab-del-btn" data-id="${p.id}" title="删除此规律">${ICO.delete}</button>
          </div>`;
        });
        h += `</div>`;
      }
      tbl.innerHTML = h;
      tbl.querySelectorAll(".hab-del-btn").forEach((b) => {
        b.onclick = async () => {
          if (!await this._showConfirm("确定删除此行为习惯规律？"))
            return;
          try {
            await this._hass.callService("smart_agent", "delete_behavior_pattern", {
              id: parseInt(b.dataset.id)
            });
            this._msg("已删除行为规律");
            await this._wsRefresh(
              "smart_agent/get_behavior_patterns",
              "behavior_patterns",
              () => this._renderHabitPatterns()
            );
          } catch (err) {
            this._msg("删除失败: " + String(err.message || err));
          }
        };
      });
    }
  };

  // src/render/aiscenes.js
  var aiscenesMethods = {
    _renderAiScenes() {
      const ICO = this._getIcons();
      const scenes = this._wsGet("ai_scenes", "scenes", []);
      const runBtn = this.shadowRoot.getElementById("runAnalysisBtn");
      if (runBtn && !runBtn._bound) {
        runBtn._bound = true;
        runBtn.onclick = async () => {
          runBtn.disabled = true;
          runBtn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px">⏳ 分析中...</span>`;
          try {
            await this._hass.callService("smart_agent", "run_pattern_analysis", {});
            this._msg("行为分析已启动，约 15-30 秒后自动刷新");
            setTimeout(() => {
              this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
            }, 15e3);
          } catch (e) {
            this._msg("分析失败: " + e.message);
          } finally {
            runBtn.disabled = false;
            runBtn.innerHTML = `🔍 立即分析`;
          }
        };
      }
      const pending = scenes.filter((s) => s.status === "pending");
      const active = scenes.filter((s) => s.status === "active");
      const rejected = scenes.filter((s) => s.status === "rejected");
      const $ = (id) => this.shadowRoot.getElementById(id);
      $("aiScenesPendingBadge").textContent = pending.length;
      $("aiScenesActiveBadge").textContent = active.length;
      $("aiScenesRejectedBadge").textContent = rejected.length;
      const confMeta = (c) => {
        if (c >= 85)
          return { cls: "conf-high", label: "高置信", color: "var(--sa-succ)" };
        if (c >= 70)
          return { cls: "conf-med", label: "中置信", color: "var(--sa-primary)" };
        return { cls: "conf-low", label: "低置信", color: "var(--sa-text-variant)" };
      };
      const renderEntities = (entities_json, limit = 6) => {
        let entities = [];
        try {
          entities = JSON.parse(entities_json || "[]");
        } catch {
          return "";
        }
        const visible = entities.slice(0, limit);
        const more = entities.length - visible.length;
        const chips = visible.map((e) => {
          const stOn = ["on", "open", "heat", "cool", "auto"].includes(e.state);
          const dot = stOn ? `<span style="width:6px;height:6px;border-radius:50%;background:var(--sa-succ);flex-shrink:0"></span>` : `<span style="width:6px;height:6px;border-radius:50%;background:var(--sa-border);flex-shrink:0"></span>`;
          const domain = (e.entity_id || "").split(".")[0];
          const dIco = ICO[domain] || ICO.device;
          const name = (e.entity_id || "").split(".")[1] || e.entity_id;
          return `<span title="${this._esc(e.entity_id)}" style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px 3px 6px;
                  border-radius:20px;background:rgba(128,128,128,.1);font-size:11px;max-width:180px;overflow:hidden;
                  white-space:nowrap;text-overflow:ellipsis;gap:5px">
                  ${dot}${dIco}<span style="overflow:hidden;text-overflow:ellipsis">${this._esc(name)}</span>
                </span>`;
        }).join("");
        const extra = more > 0 ? `<span style="font-size:11px;opacity:.55;padding:3px 6px">+${more} 个</span>` : "";
        return chips + extra;
      };
      const renderCard = (s, { showApprove = false, showReject = false, showTrigger = false, dimmed = false } = {}) => {
        const cm = confMeta(s.confidence);
        const entCount = (() => {
          try {
            return JSON.parse(s.entities_json || "[]").length;
          } catch {
            return 0;
          }
        })();
        const borderColor = dimmed ? "var(--sa-border)" : cm.color;
        return `
      <div class="scene-card ${dimmed ? "scene-card--dimmed" : ""}"
           data-scene-id="${s.id}"
           style="border-left: 3px solid ${borderColor};margin-bottom:10px;border-radius:0 14px 14px 0;
                  background:var(--sa-card);border-top:1px solid var(--sa-border);
                  border-right:1px solid var(--sa-border);border-bottom:1px solid var(--sa-border);">

        <!-- 卡片主体 -->
        <div style="padding:14px 16px 10px">

          <!-- 标题行 -->
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:6px">
            <div style="display:flex;align-items:center;gap:7px;min-width:0;flex:1">
              <span style="color:${cm.color};flex-shrink:0">${ICO.spark}</span>
              <span class="label-l" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">
                ${this._esc(s.name)}
              </span>
            </div>
            <span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;
                         background:${cm.color}1a;color:${cm.color};font-size:11px;font-weight:600;flex-shrink:0;white-space:nowrap">
              ${ICO.gauge} ${s.confidence}% · ${cm.label}
            </span>
          </div>

          <!-- 描述 -->
          <div class="body-s" style="opacity:.75;margin-bottom:10px;line-height:1.5">
            ${this._esc(s.description || "")}
          </div>

          <!-- 元数据行 -->
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap">
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              ${ICO.schedule} ${this._esc(s.trigger_context || "—")}
            </span>
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              📊 历史触发 ${s.hit_count} 次
            </span>
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              💡 ${entCount} 个设备
            </span>
          </div>

          <!-- 实体芯片 -->
          <div style="display:flex;flex-wrap:wrap;gap:5px">
            ${renderEntities(s.entities_json)}
          </div>
        </div>

        <!-- 操作按钮行 -->
        <div style="display:flex;align-items:center;gap:8px;padding:8px 16px 12px;border-top:1px solid var(--sa-border);flex-wrap:wrap">
          ${showApprove ? `<md-filled-button class="ai-scene-approve" data-id="${s.id}"
              style="--md-filled-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.check} 确认启用</md-filled-button>` : ""}
          ${showTrigger ? `<md-filled-tonal-button class="ai-scene-trigger" data-id="${s.id}"
              style="--md-filled-tonal-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.play} 立即触发</md-filled-tonal-button>` : ""}
          <md-outlined-button class="ai-scene-yaml" data-id="${s.id}"
              style="--md-outlined-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.yaml} 导出 YAML</md-outlined-button>
          ${showReject ? `<md-outlined-button class="ai-scene-reject" data-id="${s.id}"
              style="--md-outlined-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px;color:var(--sa-text-variant)">
              ${ICO.close} 拒绝</md-outlined-button>` : ""}
          <span style="flex:1"></span>
          <md-icon-button class="ai-scene-delete" data-id="${s.id}"
              title="删除场景" style="color:var(--sa-error);opacity:.7">
              ${ICO.delete}</md-icon-button>
        </div>
      </div>`;
      };
      const createPanel = $("aiSceneCreatePanel");
      if (createPanel && !createPanel._bound) {
        createPanel._bound = true;
        const toggleBtn = $("aiSceneCreateToggle");
        const body = $("aiSceneCreateBody");
        const textarea = $("aiSceneCreateText");
        const autoChk = $("aiSceneAutoActivate");
        const parseBtn = $("aiSceneParseBtn");
        const confirmBtn = $("aiSceneConfirmBtn");
        const cancelBtn = $("aiSceneCreateCancel");
        const preview = $("aiSceneCreatePreview");
        toggleBtn.onclick = () => {
          const open = body.style.display !== "none";
          body.style.display = open ? "none" : "block";
          toggleBtn.textContent = open ? "＋ 用自然语言创建场景" : "－ 收起";
        };
        cancelBtn.onclick = () => {
          textarea.value = "";
          preview.style.display = "none";
          confirmBtn.style.display = "none";
          cancelBtn.style.display = "none";
        };
        parseBtn.onclick = async () => {
          const text = textarea.value.trim();
          if (!text) {
            this._msg("请先输入场景描述");
            return;
          }
          parseBtn.disabled = true;
          parseBtn.textContent = "⏳ AI 解析中...";
          preview.style.display = "none";
          confirmBtn.style.display = "none";
          cancelBtn.style.display = "none";
          const onCreated = (ev) => {
            this._hass.connection.removeEventListener("smart_agent_scene_created", onCreated);
            parseBtn.disabled = false;
            parseBtn.textContent = "🤖 AI 解析生成";
            const d = ev.data || ev.detail || {};
            if (!d.success) {
              this._msg("解析失败：" + (d.error || "未知错误"));
              return;
            }
            preview.innerHTML = `
            <div style="font-size:13px;color:var(--sa-text-variant);margin-bottom:6px">解析结果预览</div>
            <div style="font-weight:600;margin-bottom:4px">📋 ${d.name || "新场景"}</div>
            <div style="font-size:12px;color:var(--sa-text-variant)">
              状态：${d.status === "active" ? "✅ 已直接激活" : "⏳ 待确认"}
            </div>`;
            preview.style.display = "block";
            confirmBtn.style.display = "inline-flex";
            cancelBtn.style.display = "inline-flex";
            confirmBtn.dataset.sceneId = d.scene_id;
            confirmBtn.dataset.status = d.status;
            if (d.status === "active") {
              this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
            }
          };
          try {
            this._hass.connection.addEventListener("smart_agent_scene_created", onCreated);
            await this._hass.callService("smart_agent", "create_scene_from_text", {
              text,
              auto_activate: autoChk ? autoChk.checked : false
            });
          } catch (e) {
            this._hass.connection.removeEventListener("smart_agent_scene_created", onCreated);
            parseBtn.disabled = false;
            parseBtn.textContent = "🤖 AI 解析生成";
            this._msg("调用失败: " + e.message);
          }
        };
        confirmBtn.onclick = async () => {
          const status = confirmBtn.dataset.status;
          if (status !== "active") {
            this._msg("场景已创建，请在「待确认」区审批激活");
          }
          textarea.value = "";
          preview.style.display = "none";
          confirmBtn.style.display = "none";
          cancelBtn.style.display = "none";
          await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
        };
      }
      $("aiScenesPending").innerHTML = pending.length ? pending.map((s) => renderCard(s, { showApprove: true, showReject: true })).join("") : `<div class="empty-state">
           <div class="empty-state-icon">🔮</div>
           <div class="empty-state-title">暂无待确认候选场景</div>
           <div class="empty-state-desc">每日凌晨行为分析后自动生成，或点击「立即分析」手动触发</div>
         </div>`;
      $("aiScenesActive").innerHTML = active.length ? active.map((s) => renderCard(s, { showTrigger: true })).join("") : `<div class="empty-state">
           <div class="empty-state-icon">✨</div>
           <div class="empty-state-title">暂无已激活场景</div>
           <div class="empty-state-desc">审批通过的场景将在此显示</div>
         </div>`;
      $("aiScenesRejected").innerHTML = rejected.length ? rejected.map((s) => renderCard(s, { showApprove: true, dimmed: true })).join("") : `<div class="empty-state">
           <div class="empty-state-icon">🗂️</div>
           <div class="empty-state-title">暂无已拒绝场景</div>
         </div>`;
      const view = this.shadowRoot.getElementById("view-aiscenes");
      view.querySelectorAll(".ai-scene-approve").forEach((b) => {
        b.onclick = async () => {
          b.disabled = true;
          try {
            await this._hass.callService("smart_agent", "approve_ai_scene", { id: parseInt(b.dataset.id) });
            this._msg("场景已激活，将加入 AI 推理上下文");
            await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          } catch (e) {
            this._msg("操作失败: " + e.message);
            b.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-reject").forEach((b) => {
        b.onclick = async () => {
          if (!await this._showConfirm("拒绝后该场景不再自动推荐，确认吗？"))
            return;
          b.disabled = true;
          try {
            await this._hass.callService("smart_agent", "reject_ai_scene", { id: parseInt(b.dataset.id) });
            this._msg("已拒绝场景");
            await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          } catch (e) {
            this._msg("操作失败: " + e.message);
            b.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-trigger").forEach((b) => {
        b.onclick = async () => {
          if (!await this._showConfirm("立即触发此场景？将批量执行场景内所有设备动作。"))
            return;
          b.disabled = true;
          try {
            await this._hass.callService("smart_agent", "trigger_ai_scene", { id: parseInt(b.dataset.id) });
            this._msg("场景触发指令已发送");
          } catch (e) {
            this._msg("触发失败: " + e.message);
          } finally {
            b.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-delete").forEach((b) => {
        b.onclick = async () => {
          if (!await this._showConfirm("确定删除此 AI 场景？"))
            return;
          b.disabled = true;
          try {
            await this._hass.callService("smart_agent", "delete_ai_scene", { id: parseInt(b.dataset.id) });
            this._msg("已删除 AI 场景");
            await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          } catch (e) {
            this._msg("删除失败: " + e.message);
            b.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-yaml").forEach((b) => {
        b.onclick = async () => {
          const id = b.dataset.id;
          b.disabled = true;
          try {
            const resp = await this._hass.fetchWithAuth(`/api/smart_agent/export_scene_yaml?scene_id=${id}`);
            const data = await resp.json();
            if (data.error) {
              this._msg("导出失败: " + data.error);
              return;
            }
            const overlay = document.createElement("div");
            overlay.style = `position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.65);
                           z-index:9999;display:flex;align-items:center;justify-content:center;
                           padding:20px;backdrop-filter:blur(6px)`;
            const dialog = document.createElement("div");
            dialog.style = `background:var(--sa-card);width:100%;max-width:600px;border-radius:24px;
                          padding:24px;box-shadow:0 16px 48px rgba(0,0,0,0.45);display:flex;flex-direction:column;gap:16px`;
            dialog.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center">
              <h3 style="margin:0;font-size:17px;display:flex;align-items:center;gap:8px">${ICO.yaml} 自动化 YAML 导出</h3>
              <md-icon-button id="closeYaml" style="background:transparent">${ICO.close}</md-icon-button>
            </div>
            <div style="font-size:12px;opacity:0.65;line-height:1.6">
              复制到 HA 的 <code style="background:rgba(128,128,128,.15);padding:1px 5px;border-radius:4px">automations.yaml</code>，
              或点击「写入 HA」自动追加。首次使用需在 <code style="background:rgba(128,128,128,.15);padding:1px 5px;border-radius:4px">configuration.yaml</code>
              的 <code>automation:</code> 段加入 <code>!include smart_agent_automations.yaml</code> 并重启一次。
            </div>
            <textarea id="yamlText" readonly style="width:100%;height:280px;background:var(--sa-bg);color:var(--sa-text);
                      border:1px solid var(--sa-border);border-radius:12px;padding:12px;font-family:monospace;
                      font-size:12px;resize:vertical;box-sizing:border-box">${this._esc(data.yaml)}</textarea>
            <div style="display:flex;gap:10px">
              <md-filled-tonal-button id="copyYaml" style="flex:1">复制到剪贴板</md-filled-tonal-button>
              <md-filled-button id="writeYaml" style="flex:1">写入 HA 自动化</md-filled-button>
            </div>`;
            overlay.appendChild(dialog);
            this.shadowRoot.appendChild(overlay);
            const close = dialog.querySelector("#closeYaml");
            const copy = dialog.querySelector("#copyYaml");
            const write = dialog.querySelector("#writeYaml");
            const area = dialog.querySelector("#yamlText");
            close.onclick = () => this.shadowRoot.removeChild(overlay);
            overlay.onclick = (e) => {
              if (e.target === overlay)
                close.onclick();
            };
            copy.onclick = () => {
              area.select();
              document.execCommand("copy");
              copy.textContent = "✅ 已复制";
              setTimeout(() => {
                copy.textContent = "复制到剪贴板";
              }, 2e3);
            };
            write.onclick = async () => {
              write.disabled = true;
              write.textContent = "写入中...";
              try {
                const wr = await this._hass.fetchWithAuth(`/api/smart_agent/export_scene_yaml`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ scene_id: parseInt(id) })
                });
                const wd = await wr.json();
                if (wd.success) {
                  write.textContent = "✅ 已写入";
                  this._msg(`已写入 smart_agent_automations.yaml（共 ${wd.automation_count} 条）${wd.reload_ok ? "，HA 已重载" : "，请手动重启 HA 一次"}`);
                } else {
                  write.disabled = false;
                  write.textContent = "写入 HA 自动化";
                  this._msg("写入失败: " + (wd.error || "未知错误"));
                }
              } catch (err) {
                write.disabled = false;
                write.textContent = "写入 HA 自动化";
                this._msg("写入失败: " + err.message);
              }
            };
          } catch (e) {
            this._msg("导出失败: " + e.message);
          } finally {
            b.disabled = false;
          }
        };
      });
    }
  };

  // src/render/corrections.js
  var correctionsMethods = {
    _renderCorrections() {
      const raw = this._wsGet("ai_actions", "actions", []);
      const $ = (id) => this.shadowRoot.getElementById(id);
      const ICO = this._getIcons();
      const box = $("corrList");
      if (!box)
        return;
      const now = Date.now() / 1e3;
      const FRESH_SEC = 30 * 60;
      const ALL_SEC = 8 * 3600;
      const WARN_SEC = 5 * 60;
      const filterMode = this._corrFilter || "all";
      const visible = raw.filter((a) => {
        if (!a.time)
          return true;
        if (filterMode === "fresh")
          return now - a.time < FRESH_SEC;
        return now - a.time < ALL_SEC;
      });
      const btnAll = $("corrFilterAll"), btnFresh = $("corrFilterFresh");
      if (btnAll)
        btnAll.classList.toggle("dim", filterMode !== "all");
      if (btnFresh)
        btnFresh.classList.toggle("dim", filterMode !== "fresh");
      if (btnAll && !btnAll._bound) {
        btnAll._bound = true;
        btnAll.onclick = () => {
          this._corrFilter = "all";
          this._renderCorrections();
        };
      }
      if (btnFresh && !btnFresh._bound) {
        btnFresh._bound = true;
        btnFresh.onclick = () => {
          this._corrFilter = "fresh";
          this._renderCorrections();
        };
      }
      const btnClearAll = $("corrClearAll");
      if (btnClearAll && !btnClearAll._bound) {
        btnClearAll._bound = true;
        btnClearAll.onclick = async () => {
          if (!await this._showConfirm("确定清空全部近期操作记录吗？"))
            return;
          try {
            await this._hass.callService("smart_agent", "dismiss_ai_action", {});
            this._msg("已清空全部操作记录");
          } catch (err) {
            this._msg("清空失败: " + String(err.message || err));
          }
        };
      }
      if (!visible.length) {
        box.innerHTML = `<div style="opacity:.5;text-align:center;padding:32px">
        ${filterMode === "fresh" ? "没有待处理的操作（30分钟内无新 AI 动作），或已全部处理完毕 ✅" : "最近 8 小时内无 AI 动作记录（记录在 8 小时后自动清理）"}
      </div>`;
        return;
      }
      const groups = /* @__PURE__ */ new Map();
      visible.forEach((a) => {
        const key = a.scene || "(未知场景)";
        if (!groups.has(key))
          groups.set(key, []);
        groups.get(key).push(a);
      });
      let html = "";
      groups.forEach((items, scene) => {
        const oldest = items[0];
        const age = oldest.time ? now - oldest.time : 0;
        const expired = age > FRESH_SEC;
        const warn = !expired && age > WARN_SEC;
        const timeStr = oldest.time ? new Date(oldest.time * 1e3).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
        const ageMin = Math.floor(age / 60);
        const ageLbl = age > 0 ? ageMin >= 60 ? `${Math.floor(ageMin / 60)}h${ageMin % 60}m前` : `${ageMin}m前` : "";
        const headerBg = expired ? "var(--sa-bg)" : "var(--sa-primary-container)";
        const headerColor = expired ? "var(--sa-text2,#666)" : "var(--sa-primary)";
        html += `
        <div style="background:var(--sa-card);border:1px solid ${expired ? "var(--sa-border)" : "var(--sa-primary)"};border-radius:14px;overflow:hidden;${expired ? "opacity:.6" : ""}">
          <div style="padding:10px 14px;display:flex;align-items:center;gap:8px;background:${headerBg}">
            ${expired ? `<span style="font-size:11px">⏰</span>` : ICO.bolt}
            <span style="flex:1;font-size:12px;font-weight:600;color:${headerColor};white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
              title="${this._esc(scene)}">${this._esc(scene)}</span>
            <span style="font-size:11px;opacity:.6">${timeStr} ${ageLbl}</span>
            ${expired ? `<span style="font-size:10px;background:#ff980020;color:#e65100;border-radius:6px;padding:2px 6px">已过期</span>` : warn ? `<span style="font-size:10px;background:#ff980020;color:#e65100;border-radius:6px;padding:2px 6px">即将过期</span>` : ""}
            <md-outlined-button class="corr-dismiss-scene" data-scene="${this._esc(scene)}"
              style="--md-outlined-button-container-height:24px;font-size:11px;opacity:.7">
              全部忽略
            </md-outlined-button>
          </div>
          <div style="display:flex;flex-direction:column;gap:1px">`;
        items.forEach((a) => {
          var _a;
          const name = ((_a = this._hass.states[a.entity_id]) == null ? void 0 : _a.attributes.friendly_name) || a.entity_id;
          const stateColor = a.state === "on" ? "var(--sa-succ,#4caf50)" : "var(--sa-text-variant,#888)";
          html += `
          <div style="padding:10px 14px;display:flex;align-items:center;gap:12px;border-top:1px solid var(--sa-border)">
            <div style="width:28px;height:28px;border-radius:8px;background:var(--sa-primary-container);color:var(--sa-primary);display:flex;align-items:center;justify-content:center;flex-shrink:0">
              ${ICO[a.entity_id.split(".")[0]] || ICO.device}
            </div>
            <div style="flex:1;min-width:0">
              <div class="body-m" style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(name)}</div>
              <div class="body-s" style="opacity:.6">设为 <b style="color:${stateColor}">${this._esc(String(a.state ?? ""))}</b>
                <span style="font-size:11px;opacity:.5;margin-left:4px">${this._esc(a.entity_id)}</span></div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0">
              ${expired ? "" : `
              <md-filled-tonal-button class="corr-correct-btn" data-eid="${this._esc(a.entity_id)}"
                style="--md-filled-tonal-button-container-height:28px;font-size:11px;background:var(--sa-error-container);color:var(--sa-error)">
                🎯 纠正
              </md-filled-tonal-button>`}
              <md-outlined-button class="corr-dismiss-btn" data-eid="${this._esc(a.entity_id)}"
                style="--md-outlined-button-container-height:28px;font-size:11px;opacity:.7">
                ✕ 忽略
              </md-outlined-button>
            </div>
          </div>`;
        });
        html += `</div></div>`;
      });
      box.innerHTML = html;
      const _refreshCorrList = () => {
        delete this._wsLoading["ai_actions"];
        this._wsRefresh("smart_agent/get_ai_actions", "ai_actions", () => this._renderCorrections());
      };
      box.querySelectorAll(".corr-correct-btn").forEach((btn) => {
        btn.onclick = async () => {
          var _a;
          const eid = btn.dataset.eid;
          if (!await this._showConfirm(`确定纠正对 ${eid} 的操作吗？将撤销并记录学习。`))
            return;
          btn.disabled = true;
          btn.textContent = "处理中...";
          try {
            const cur = (_a = this._hass.states[eid]) == null ? void 0 : _a.state;
            const domain = eid.split(".")[0];
            const svc = domain === "cover" ? cur === "open" ? "close_cover" : "open_cover" : cur === "on" ? "turn_off" : "turn_on";
            await this._hass.callService(domain, svc, { entity_id: eid });
            await new Promise((r) => setTimeout(r, 500));
            await this._hass.callService("smart_agent", "report_correction", { entity_id: eid });
            this._msg(`已纠正 ${eid}，AI 将学习此偏好`);
            _refreshCorrList();
          } catch (e) {
            this._msg("纠正失败: " + e.message);
            btn.disabled = false;
            btn.textContent = "🎯 纠正";
          }
        };
      });
      box.querySelectorAll(".corr-dismiss-btn").forEach((btn) => {
        btn.onclick = async () => {
          const eid = btn.dataset.eid;
          btn.disabled = true;
          btn.textContent = "忽略中...";
          try {
            await this._hass.callService("smart_agent", "dismiss_ai_action", { entity_id: eid });
            this._msg(`已忽略 ${eid}`);
            _refreshCorrList();
          } catch (e) {
            this._msg("操作失败: " + e.message);
            btn.disabled = false;
            btn.textContent = "✕ 忽略";
          }
        };
      });
      box.querySelectorAll(".corr-dismiss-scene").forEach((btn) => {
        btn.onclick = async () => {
          const scene = btn.dataset.scene;
          const targets = visible.filter((a) => (a.scene || "(未知场景)") === scene);
          btn.disabled = true;
          btn.textContent = "处理中...";
          try {
            for (const a of targets) {
              await this._hass.callService("smart_agent", "dismiss_ai_action", {
                entity_id: a.entity_id
              });
            }
            this._msg(`已忽略「${scene}」的全部操作`);
            _refreshCorrList();
          } catch (e) {
            this._msg("操作失败: " + e.message);
            btn.disabled = false;
            btn.textContent = "全部忽略";
          }
        };
      });
    }
  };

  // src/render/transactions.js
  var transactionsMethods = {
    /** 渲染 AI 看板：今日统计 + 房间推翻率 + 执行记录 */
    _renderTransactions() {
      this._renderDecisionStats();
      this._renderTxnList();
    },
    /** 5D-3: 今日决策统计卡片 + 房间推翻率 */
    async _renderDecisionStats() {
      const statsBox = this.shadowRoot.getElementById("decisionStatsContent");
      const roomBox = this.shadowRoot.getElementById("roomOverturnList");
      if (!statsBox || !roomBox)
        return;
      let data;
      try {
        data = await this._hass.connection.sendMessagePromise({
          type: "smart_agent/get_decision_stats"
        });
        if (!data || typeof data !== "object")
          throw new Error("返回数据为空");
      } catch (e) {
        const errMsg = this._esc(String(e.message || "未知错误"));
        statsBox.innerHTML = `<div style="opacity:.5;grid-column:1/-1;text-align:center">统计加载失败: ${errMsg}</div>`;
        roomBox.innerHTML = "";
        return;
      }
      const today_inferences = Number(data.today_inferences ?? 0);
      const today_corrections = Number(data.today_corrections ?? 0);
      const room_overturn_rates = Array.isArray(data.room_overturn_rates) ? data.room_overturn_rates : [];
      const overturnRate = today_inferences > 0 ? Math.round(today_corrections / today_inferences * 100) : 0;
      const statCardStyle = "background:var(--sa-card,var(--card-background-color));border:1px solid var(--sa-border,var(--divider-color));border-radius:12px;padding:12px;text-align:center";
      statsBox.innerHTML = `
      <div style="${statCardStyle}">
        <div style="font-size:24px;font-weight:700;color:var(--sa-primary)">${today_inferences}</div>
        <div class="body-s" style="opacity:.6;margin-top:4px">今日决策</div>
      </div>
      <div style="${statCardStyle}">
        <div style="font-size:24px;font-weight:700;color:var(--warning-color,#ff9800)">${today_corrections}</div>
        <div class="body-s" style="opacity:.6;margin-top:4px">今日纠正</div>
      </div>
      <div style="${statCardStyle}">
        <div style="font-size:24px;font-weight:700;color:${overturnRate > 30 ? "var(--error-color,#f44336)" : overturnRate > 15 ? "var(--warning-color,#ff9800)" : "var(--success-color,#4caf50)"}">
          ${overturnRate}%
        </div>
        <div class="body-s" style="opacity:.6;margin-top:4px">今日推翻率</div>
      </div>
    `;
      if (!room_overturn_rates.length) {
        roomBox.innerHTML = '<div style="opacity:.5;padding:8px 0;text-align:center">暂无房间统计</div>';
      } else {
        const validRates = room_overturn_rates.filter((r) => typeof r.rate === "number" && !isNaN(r.rate));
        const maxRate = validRates.length ? Math.max(...validRates.map((r) => r.rate), 1) : 1;
        roomBox.innerHTML = validRates.sort((a, b) => b.rate - a.rate).map((r) => {
          const barW = Math.round(r.rate / Math.max(maxRate, 1) * 100);
          const color = r.rate > 30 ? "var(--error-color,#f44336)" : r.rate > 15 ? "var(--warning-color,#ff9800)" : "var(--success-color,#4caf50)";
          const rateStr = this._esc(String(r.rate));
          const corrStr = this._esc(String(r.corrections ?? 0));
          const infStr = this._esc(String(r.inferences ?? 0));
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
        }).join("");
      }
    },
    /** 执行记录列表（原有内容） */
    _renderTxnList() {
      const list = this._wsGet("transactions", "transactions", []);
      const box = this.shadowRoot.getElementById("txnList");
      if (!box)
        return;
      const STATUS_META = {
        success: { label: "成功", color: "var(--success-color, #4caf50)" },
        partial: { label: "部分执行", color: "var(--warning-color, #ff9800)" },
        blocked: { label: "已拦截", color: "var(--info-color, #2196f3)" },
        failed: { label: "失败", color: "var(--error-color, #f44336)" },
        pending: { label: "执行中", color: "var(--secondary-text-color, #9e9e9e)" },
        rolled_back: { label: "已回滚", color: "#9c27b0" }
      };
      if (!list.length) {
        box.innerHTML = '<div style="opacity:.5;padding:16px 0;text-align:center">暂无执行记录</div>';
        return;
      }
      box.innerHTML = list.map((t) => {
        const meta = STATUS_META[t.status] || { label: this._esc(String(t.status ?? "")), color: "#888" };
        const canRollback = ["success", "partial", "failed"].includes(t.status);
        const failBadge = t.failed_count > 0 ? `<span style="color:var(--error-color,#f44336);font-size:11px"> · ${t.failed_count}失败</span>` : "";
        const blockedBadge = t.blocked_count > 0 ? `<span style="color:var(--info-color,#2196f3);font-size:11px"> · ${t.blocked_count}拦截</span>` : "";
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
      }).join("");
      box.querySelectorAll(".txn-rollback").forEach((b) => {
        b.onclick = async () => {
          const id = parseInt(b.dataset.id);
          if (!await this._showConfirm(`确定回滚事务 #${id}？将把相关设备恢复到执行前的状态。`))
            return;
          b.disabled = true;
          b.textContent = "回滚中…";
          try {
            await this._hass.callService("smart_agent", "rollback_transaction", { id });
            this._msg(`事务 #${id} 回滚指令已发送`);
            this._wsRefresh(
              "smart_agent/get_transactions",
              "transactions",
              () => this._renderTransactions()
            );
          } catch (e) {
            this._msg("回滚失败: " + e.message);
            b.disabled = false;
            b.textContent = "⏪ 回滚";
          }
        };
      });
    }
  };

  // src/render/energy.js
  var energyMethods = {
    _renderEnergy() {
      const list = this._wsGet("energy_stats", "stats", []);
      const box = this.shadowRoot.getElementById("energyList");
      if (!box)
        return;
      if (!list.length) {
        box.innerHTML = '<div style="opacity:.5;padding:16px 0;text-align:center">暂无能耗数据（每天凌晨 3:00 自动分析一次，也可重启集成立即生成）</div>';
        return;
      }
      const maxOn = Math.max(...list.map((s) => s.on_minutes), 1);
      box.innerHTML = list.map((s) => {
        const name = s.entity_id.replace(/^[^.]+\./, "").replace(/_/g, " ");
        const onH = Math.floor(s.on_minutes / 60), onM = Math.round(s.on_minutes % 60);
        const wasteH = Math.floor(s.waste_minutes / 60), wasteM = Math.round(s.waste_minutes % 60);
        const onLabel = onH ? `${onH}h ${onM}m` : `${onM}m`;
        const wasteLabel = s.waste_minutes < 1 ? "无浪费" : wasteH ? `${wasteH}h ${wasteM}m` : `${wasteM}m`;
        const wasteRatio = s.on_minutes > 0 ? Math.round(s.waste_minutes / s.on_minutes * 100) : 0;
        const barColor = wasteRatio > 50 ? "#f44336" : wasteRatio > 20 ? "#ff9800" : "var(--sa-primary,#6750a4)";
        const barWaste = s.on_minutes > 0 ? Math.round(s.waste_minutes / s.on_minutes * 100) : 0;
        const barOn = Math.round(s.on_minutes / maxOn * 100);
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
      }).join("");
    }
  };

  // src/render/profiles.js
  var profilesMethods = {
    _renderProfs() {
      const allRules = this._wsGet("rules", "rules", []);
      const h = this.shadowRoot.getElementById("hList"), r = this.shadowRoot.getElementById("rList");
      if (!this._wsData["habits"]) {
        this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
        return;
      }
      const allHabits = this._wsGet("habits", "habits", []);
      const userRules = allRules.filter((i) => !i.is_ai);
      h.innerHTML = this._drawList(allHabits, "habit");
      r.innerHTML = this._drawList(userRules, "rule");
      this.shadowRoot.querySelectorAll(".prof-lock").forEach((b) => {
        b.onclick = async () => {
          try {
            await this._hass.callService("smart_agent", "toggle_" + b.dataset.t + "_lock", {
              content: b.dataset.c
            });
            this._msg(b.dataset.lk === "1" ? "配置已解锁" : "配置已锁定");
            delete this._wsData["rules"];
            delete this._wsData["habits"];
            await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
              await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
            });
          } catch (e) {
            this._msg("操作失败: " + e.message);
          }
        };
      });
      this.shadowRoot.querySelectorAll(".prof-del").forEach((b) => {
        b.onclick = async () => {
          if (b.disabled)
            return;
          try {
            await this._hass.callService("smart_agent", "delete_" + b.dataset.t, {
              content: b.dataset.c
            });
            this._msg("已删除");
            delete this._wsData["rules"];
            delete this._wsData["habits"];
            await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
              await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
            });
          } catch (e) {
            this._msg("删除失败: " + e.message);
          }
        };
      });
    },
    _drawList(items, type) {
      if (!items.length) {
        return `<div class="body-s" style="padding:20px;text-align:center;opacity:.5">暂无条目</div>`;
      }
      const lockIco = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>`;
      const unlockIco = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6-9h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6h1.9c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm0 12H6V10h12v10z"/></svg>`;
      const delIco = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>`;
      let html = `<div class="m3-list">`;
      items.forEach((i) => {
        const ec = this._esc(i.content);
        const itemBg = i.locked ? "background:var(--sa-secondary-container);opacity:.8" : "";
        html += `
        <div class="m3-item" style="${itemBg}">
          <div class="m3-content">
            <div class="body-m" style="word-break:break-all">${ec}</div>
          </div>
          <div style="display:flex;gap:4px">
            ${i.locked ? `<md-filled-tonal-button class="prof-lock" data-t="${type}" data-c="${ec}" data-lk="1"
                  style="--md-filled-tonal-button-container-height:32px;font-size:13px"
                  title="解锁（允许 AI 自动修改）">${lockIco}</md-filled-tonal-button>` : `<md-outlined-button class="prof-lock" data-t="${type}" data-c="${ec}" data-lk="0"
                  style="--md-outlined-button-container-height:32px;font-size:13px"
                  title="锁定（防止 AI 反向操作）">${unlockIco}</md-outlined-button>`}
            <md-filled-button class="btn-error prof-del" data-t="${type}" data-c="${ec}"
              ${i.locked ? "disabled" : ""} title="删除"
              style="--md-filled-button-container-height:32px;font-size:13px${i.locked ? ";opacity:.3" : ""}">
              ${delIco}
            </md-filled-button>
          </div>
        </div>`;
      });
      return html + `</div>`;
    }
  };

  // src/render/config.js
  var configMethods = {
    _renderConfig() {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const ICO = this._getIcons();
      const cfg = this._cfg.attributes || {};
      const container = $("configArea");
      if (!container)
        return;
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
                ${cfg.brand_logo_url ? `<img src="${this._esc(cfg.brand_logo_url)}" style="width:100%;height:100%;object-fit:cover">` : `<span style="font-size:24px">${ICO.bolt}</span>`}
              </div>
              <div style="flex:1">
                <div class="label-s">Logo 图片 URL</div>
                <md-outlined-text-field id="cfg_brand_logo" label="Logo 图片 URL"
                  value="${this._esc(cfg.brand_logo_url || "")}"
                  placeholder="https://example.com/logo.png"></md-outlined-text-field>
                <div class="body-s" style="opacity:.55;margin-top:3px">支持 PNG/SVG，建议 64×64 以上，留空使用默认图标</div>
              </div>
            </div>

            <div>
              <div class="label-s">品牌名称</div>
              <md-outlined-text-field id="cfg_brand_name" label="品牌名称"
                value="${this._esc(cfg.brand_name || "SmartAgent")}"
                placeholder="SmartAgent"></md-outlined-text-field>
              <div class="body-s" style="opacity:.55;margin-top:3px">显示在面板标题栏、页脚和帮助页面</div>
            </div>

            <div>
              <div class="label-s">主题色</div>
              <div style="display:flex;align-items:center;gap:10px">
                <input id="cfg_brand_color" type="color"
                  value="${cfg.brand_primary_color || "#6750A4"}"
                  style="width:52px;height:40px;padding:2px 4px;cursor:pointer;border:1px solid var(--sa-border);border-radius:8px">
                <md-outlined-text-field id="cfg_brand_color_hex" style="flex:1"
                  value="${this._esc(cfg.brand_primary_color || "#6750A4")}"
                  label="Hex 颜色" placeholder="#6750A4" maxlength="7"></md-outlined-text-field>
              </div>
              <div class="body-s" style="opacity:.55;margin-top:3px">作用于按钮、选中状态、高亮元素</div>
            </div>

            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-s">部署点标识名</div>
              <md-outlined-text-field id="cfg_deploy_name" label="部署点标识名"
                value="${this._esc(cfg.deploy_name || "")}"
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
                <md-select-option value="local" ${cfg.engine === "local" ? "selected" : ""}>本地 Ollama (推荐)</md-select-option>
                <md-select-option value="online" ${cfg.engine === "online" ? "selected" : ""}>云端 OpenAI 兼容 API</md-select-option>
              </md-outlined-select>
            </div>
            <div id="cfg_local_group" style="display:${cfg.engine === "local" ? "grid" : "none"};gap:12px">
              <div>
                <div class="label-s">Ollama 服务地址</div>
                <md-outlined-text-field id="cfg_ollama_url" label="Ollama 服务地址" value="${this._esc(cfg.ollama_url || "")}" placeholder="http://127.0.0.1:11434"></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">Ollama 模型名称</div>
                <md-outlined-text-field id="cfg_ollama_model" label="Ollama 模型名称" value="${this._esc(cfg.ollama_model || "")}" placeholder="qwen3-smarthome"></md-outlined-text-field>
              </div>
            </div>
            <div id="cfg_online_group" style="display:${cfg.engine === "online" ? "grid" : "none"};gap:12px">
              <div>
                <div class="label-s">API Base URL</div>
                <md-outlined-text-field id="cfg_online_base_url" label="API Base URL" value="${this._esc(cfg.online_base_url || "")}" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">API Key</div>
                <md-outlined-text-field id="cfg_online_api_key" type="password" label="API Key" value="${this._esc(cfg.online_api_key || "")}" placeholder="sk-xxxx..."></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">模型名称</div>
                <md-outlined-text-field id="cfg_online_model" label="模型名称" value="${this._esc(cfg.online_model || "")}" placeholder="qwen-turbo"></md-outlined-text-field>
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
              <md-outlined-text-field id="cfg_tts_service" label="TTS 服务 (domain.service)" value="${this._esc(cfg.tts_service || "")}" placeholder="tts.google_translate_say"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">目标媒体播放器</div>
              <md-outlined-text-field id="cfg_tts_target" label="目标媒体播放器" value="${this._esc(cfg.tts_target || "")}" placeholder="media_player.bedroom_speaker"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">TTS 播报级别</div>
              <md-outlined-select id="cfg_tts_level">
                <md-select-option value="0" ${cfg.tts_level === 0 ? "selected" : ""}>关闭</md-select-option>
                <md-select-option value="1" ${cfg.tts_level === 1 ? "selected" : ""}>仅 AI 回复</md-select-option>
                <md-select-option value="2" ${cfg.tts_level === 2 ? "selected" : ""}>回复 + 执行摘要</md-select-option>
                <md-select-option value="3" ${cfg.tts_level === 3 ? "selected" : ""}>全部 (含系统提示)</md-select-option>
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
                <md-select-option value="local" ${cfg.vision_engine === "local" ? "selected" : ""}>本地 (Ollama/Llava)</md-select-option>
                <md-select-option value="online" ${cfg.vision_engine === "online" ? "selected" : ""}>在线 (Qwen-VL/Gemini)</md-select-option>
              </md-outlined-select>
            </div>
            <div>
              <div class="label-s">视觉模型名称</div>
              <md-outlined-text-field id="cfg_vision_model" label="视觉模型名称" value="${this._esc(cfg.vision_model || "")}" placeholder="qwen-vl-max"></md-outlined-text-field>
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
                  value="${cfg.showroom_biz_start || "09:00"}"></md-outlined-text-field>
                <div class="body-s" style="opacity:.55;margin-top:4px">AI 开始主动展示的时间</div>
              </div>
              <div>
                <div class="label-s">营业结束时间</div>
                <md-outlined-text-field id="cfg_biz_end" type="time"
                  value="${cfg.showroom_biz_end || "21:00"}"></md-outlined-text-field>
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
              <md-outlined-text-field id="cfg_qweather_api_key" type="password" label="和风天气 API Key" value="${this._esc(cfg.qweather_api_key || "")}" placeholder="用于获取精准天气预报"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">SearXNG URL</div>
              <md-outlined-text-field id="cfg_searxng_url" label="SearXNG URL" value="${this._esc(cfg.searxng_url || "")}" placeholder="用于 AI 联网搜索"></md-outlined-text-field>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between">
              <div>
                <div class="label-m">云端降级开关</div>
                <div class="body-s">本地引擎失效时自动切换云端</div>
              </div>
              <md-switch id="cfg_cloud_fallback" ${cfg.cloud_fallback ? "selected" : ""}></md-switch>
            </div>
            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-s">设备冷却时间 (秒)</div>
              <md-outlined-text-field id="cfg_cooldown" type="number" label="设备冷却时间 (秒)" value="${cfg.cooldown || 60}"></md-outlined-text-field>
            </div>
            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-m">${ICO.calendar} 日志保留天数</div>
              <div class="body-s" style="margin:4px 0 8px">文件日志每天零点轮转，超期自动删除（最小 3 天，最大 90 天）</div>
              <md-outlined-text-field id="cfg_log_retention" type="number" label="日志保留天数" min="3" max="90" value="${cfg.log_retention_days || 30}"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">License Key</div>
              <md-outlined-text-field id="cfg_license_key" type="password" label="License Key" value="${this._esc(cfg.license_key || "")}" placeholder="企业版/商业授权码"></md-outlined-text-field>
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
      const engSel = $("cfg_engine");
      if (engSel)
        engSel.onchange = () => {
          $("cfg_local_group").style.display = engSel.value === "local" ? "grid" : "none";
          $("cfg_online_group").style.display = engSel.value === "online" ? "grid" : "none";
        };
      $("cfgSaveBtn").onclick = () => this._saveSystemConfig();
      $("cfgTestTts").onclick = () => this._hass.callService("smart_agent", "tts_test", {}).catch(
        (e) => this._msg("TTS 测试失败: " + String(e.message || e))
      );
      const screenUrl = `${location.origin}/smart_agent_screen/index.html`;
      const pairUrlEl = $("pairUrl");
      if (pairUrlEl)
        pairUrlEl.textContent = screenUrl;
      const pairCopyBtn = $("pairCopyBtn");
      if (pairCopyBtn) {
        pairCopyBtn.onclick = () => {
          var _a;
          (_a = navigator.clipboard) == null ? void 0 : _a.writeText(screenUrl).then(() => {
            pairCopyBtn.textContent = "✅ 已复制";
            setTimeout(() => {
              pairCopyBtn.textContent = "复制";
            }, 2e3);
          });
        };
      }
      const pairBtn = $("pairBtn");
      if (pairBtn) {
        pairBtn.onclick = () => this._startPairing();
      }
      this._updateBizStatus();
      this._initZoneRoleUI(cfg);
      this._initSensorConfigUI();
      const colorPicker = $("cfg_brand_color");
      const colorHex = $("cfg_brand_color_hex");
      const logoInput = $("cfg_brand_logo");
      const logoPreview = $("brandLogoPreview");
      const ICO2 = this._getIcons();
      if (colorPicker && colorHex) {
        colorPicker.oninput = () => {
          colorHex.value = colorPicker.value;
        };
        colorHex.oninput = () => {
          if (/^#[0-9A-Fa-f]{6}$/.test(colorHex.value))
            colorPicker.value = colorHex.value;
        };
      }
      if (logoInput && logoPreview) {
        logoInput.oninput = () => {
          const url = logoInput.value.trim();
          logoPreview.innerHTML = url ? `<img src="${this._esc(url)}" style="width:100%;height:100%;object-fit:cover">` : `<span style="font-size:24px">${ICO2.bolt}</span>`;
        };
      }
    },
    async _startPairing() {
      var _a, _b;
      const $ = (id) => this.shadowRoot.getElementById(id);
      const pairBtn = $("pairBtn");
      const pairStatus = $("pairStatus");
      const pairCountdown = $("pairCountdown");
      if (!pairBtn || !pairStatus || !pairCountdown)
        return;
      pairBtn.disabled = true;
      pairBtn.textContent = "正在生成配对凭证...";
      try {
        const data = await this._hass.callApi("POST", "smart_agent/pair/create");
        if (!data || !data.ok) {
          const reason = (data == null ? void 0 : data.error) || (data == null ? void 0 : data.message) || JSON.stringify(data) || "未知错误";
          this._msg("❌ 配对失败：" + reason);
          pairBtn.disabled = false;
          pairBtn.textContent = "📱 开启极速配对（60 秒）";
          return;
        }
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
        }, 1e3);
        this._msg("✅ 配对已开启，请在 60 秒内用平板打开中控屏地址");
      } catch (err) {
        const errMsg = (err == null ? void 0 : err.message) || ((_a = err == null ? void 0 : err.body) == null ? void 0 : _a.message) || ((_b = err == null ? void 0 : err.body) == null ? void 0 : _b.error) || ((err == null ? void 0 : err.statusCode) ? `HTTP ${err.statusCode}` : null) || (typeof err === "string" ? err : null) || JSON.stringify(err) || "未知错误";
        this._msg("❌ 配对请求失败：" + errMsg);
        console.error("[SmartAgent] 配对失败详情:", err);
        pairBtn.disabled = false;
        pairBtn.textContent = "📱 开启极速配对（60 秒）";
      }
    },
    async _saveSystemConfig() {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const timeToMin = (t) => {
        if (!t)
          return null;
        const [h, m] = t.split(":").map(Number);
        return h * 60 + (m || 0);
      };
      const data = {
        engine: $("cfg_engine").value,
        ollama_url: $("cfg_ollama_url").value,
        ollama_model: $("cfg_ollama_model").value,
        online_base_url: $("cfg_online_base_url").value,
        online_api_key: $("cfg_online_api_key").value,
        online_model: $("cfg_online_model").value,
        tts_service: $("cfg_tts_service").value,
        tts_target: $("cfg_tts_target").value,
        tts_level: parseInt($("cfg_tts_level").value),
        vision_engine: $("cfg_vision_engine").value,
        vision_model: $("cfg_vision_model").value,
        qweather_api_key: $("cfg_qweather_api_key").value,
        searxng_url: $("cfg_searxng_url").value,
        cloud_fallback: $("cfg_cloud_fallback").checked,
        cooldown: parseInt($("cfg_cooldown").value),
        log_retention_days: Math.max(3, Math.min(90, parseInt($("cfg_log_retention").value) || 30)),
        license_key: $("cfg_license_key").value
      };
      const brandName = $("cfg_brand_name");
      const brandColor = $("cfg_brand_color_hex");
      const brandLogo = $("cfg_brand_logo");
      const deployName = $("cfg_deploy_name");
      if (brandName)
        data.brand_name = brandName.value.trim() || "SmartAgent";
      if (brandColor)
        data.brand_primary_color = brandColor.value.trim() || "#6750A4";
      if (brandLogo)
        data.brand_logo_url = brandLogo.value.trim();
      if (deployName)
        data.deploy_name = deployName.value.trim();
      const bizStart = $("cfg_biz_start");
      const bizEnd = $("cfg_biz_end");
      if (bizStart) {
        const startMin = timeToMin(bizStart.value);
        const endMin = timeToMin(bizEnd ? bizEnd.value : null);
        if (startMin !== null)
          data.showroom_biz_start = startMin;
        if (endMin !== null)
          data.showroom_biz_end = endMin;
      }
      const zoneMap = {};
      const zoneList = this.shadowRoot.getElementById("zoneRoleList");
      if (zoneList) {
        zoneList.querySelectorAll(".zone-role-row").forEach((row) => {
          var _a, _b, _c;
          const areaVal = (_b = (_a = row.querySelector(".zone-area-select")) == null ? void 0 : _a.value) == null ? void 0 : _b.trim();
          const role = (_c = row.querySelector(".zone-role-select")) == null ? void 0 : _c.value;
          if (areaVal && role)
            zoneMap[areaVal] = role;
        });
      }
      data.showroom_zone_map = JSON.stringify(zoneMap);
      try {
        await this._hass.callService("smart_agent", "update_config", data);
        this._msg("✅ 系统配置已保存并生效");
        this._updateBizStatus();
        if (data.brand_name || data.brand_primary_color) {
          this._applyBrand({
            brand_name: data.brand_name,
            brand_primary_color: data.brand_primary_color,
            brand_logo_url: data.brand_logo_url,
            deploy_name: data.deploy_name
          });
        }
      } catch (err) {
        this._msg("❌ 保存失败: " + String(err.message || err));
      }
    },
    _initZoneRoleUI(cfg) {
      const list = this.shadowRoot.getElementById("zoneRoleList");
      const addBtn = this.shadowRoot.getElementById("addZoneRoleBtn");
      const clearBtn = this.shadowRoot.getElementById("clearZoneRoleBtn");
      if (!list || !addBtn)
        return;
      const rawAreas = this._hass.areas || {};
      const haAreaNames = new Set(Object.values(rawAreas).map((a) => a.name));
      const idToName = {};
      Object.entries(rawAreas).forEach(([id, a]) => {
        idToName[id] = a.name;
      });
      const haAreas = Object.values(rawAreas).sort((a, b) => a.name.localeCompare(b.name, "zh-CN")).map((a) => ({ id: a.name, label: a.name }));
      const haAreaIds = haAreaNames;
      const ROLE_OPTIONS = [
        { value: "display", label: "🏬 展示区" },
        { value: "experience", label: "✨ 体验区" },
        { value: "work", label: "💼 工作区" }
      ];
      const getSelected = () => {
        const sel = [];
        list.querySelectorAll(".zone-area-select").forEach((s) => {
          if (s.value)
            sel.push(s.value);
        });
        return sel;
      };
      const refreshAllAreaSelects = () => {
        const selected = getSelected();
        list.querySelectorAll(".zone-role-row").forEach((row) => {
          const sel = row.querySelector(".zone-area-select");
          if (!sel)
            return;
          const cur = sel.value;
          sel.innerHTML = "";
          const ph = document.createElement("option");
          ph.value = "";
          ph.textContent = "请选择区域…";
          sel.appendChild(ph);
          haAreas.forEach((a) => {
            if (selected.includes(a.id) && a.id !== cur)
              return;
            const o = document.createElement("option");
            o.value = a.id;
            o.textContent = a.label;
            if (a.id === cur)
              o.selected = true;
            sel.appendChild(o);
          });
          if (!cur)
            sel.value = "";
        });
      };
      const createRow = (areaName = "", role = "experience") => {
        const row = document.createElement("div");
        row.className = "zone-role-row";
        row.style.cssText = "display:flex;align-items:center;gap:8px";
        const areaSelect = document.createElement("select");
        areaSelect.className = "md-outlined-select zone-area-select";
        areaSelect.style.cssText = "flex:1;min-width:0;height:36px;font-size:13px";
        const ph = document.createElement("option");
        ph.value = "";
        ph.textContent = "请选择区域…";
        areaSelect.appendChild(ph);
        const nameInList = haAreas.some((a) => a.id === areaName);
        if (areaName && !nameInList) {
          const kept = document.createElement("option");
          kept.value = areaName;
          kept.textContent = areaName;
          kept.selected = true;
          areaSelect.appendChild(kept);
        }
        haAreas.forEach((a) => {
          const o = document.createElement("option");
          o.value = a.id;
          o.textContent = a.label;
          if (a.id === areaName)
            o.selected = true;
          areaSelect.appendChild(o);
        });
        areaSelect.onchange = () => refreshAllAreaSelects();
        const roleSelect = document.createElement("select");
        roleSelect.className = "md-outlined-select zone-role-select";
        roleSelect.style.cssText = "width:152px;flex-shrink:0;height:36px;font-size:13px";
        ROLE_OPTIONS.forEach((opt) => {
          const o = document.createElement("option");
          o.value = opt.value;
          o.textContent = opt.label;
          if (opt.value === role)
            o.selected = true;
          roleSelect.appendChild(o);
        });
        const delBtn = document.createElement("button");
        delBtn.className = "btn-sm-mwc";
        delBtn.style.cssText = "height:36px;width:36px;padding:0;opacity:.6;flex-shrink:0";
        delBtn.title = "删除此区域";
        delBtn.innerHTML = "✕";
        delBtn.onclick = () => {
          row.remove();
          refreshAllAreaSelects();
        };
        row.appendChild(areaSelect);
        row.appendChild(roleSelect);
        row.appendChild(delBtn);
        return row;
      };
      list.innerHTML = "";
      let rawZoneMap = {};
      try {
        const raw = cfg.showroom_zone_map;
        if (typeof raw === "string" && raw) {
          rawZoneMap = JSON.parse(raw);
        } else if (raw && typeof raw === "object") {
          rawZoneMap = raw;
        }
      } catch (_) {
      }
      const areasAvailable = haAreaNames.size > 0;
      const zoneMap = {};
      Object.entries(rawZoneMap).forEach(([key, role]) => {
        if (!key || typeof key !== "string")
          return;
        if (!areasAvailable) {
          if (!zoneMap[key])
            zoneMap[key] = role;
          return;
        }
        if (haAreaNames.has(key)) {
          if (!zoneMap[key])
            zoneMap[key] = role;
          return;
        }
        const migrated = idToName[key];
        if (migrated) {
          if (!zoneMap[migrated])
            zoneMap[migrated] = role;
          return;
        }
      });
      Object.entries(zoneMap).forEach(([name, role]) => {
        list.appendChild(createRow(name, role));
      });
      refreshAllAreaSelects();
      addBtn.onclick = () => {
        var _a, _b;
        list.appendChild(createRow());
        refreshAllAreaSelects();
        (_b = (_a = list.lastElementChild) == null ? void 0 : _a.querySelector(".zone-area-select")) == null ? void 0 : _b.focus();
      };
      if (clearBtn) {
        clearBtn.onclick = async () => {
          if (!await this._showConfirm("确认清空所有区域角色配置？"))
            return;
          list.innerHTML = "";
        };
      }
    },
    // ── 传感器配置 UI（Phase 12.1）────────────────────────────────────────────
    async _initSensorConfigUI() {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const tabType = $("sensorTabType");
      const tabFusion = $("sensorTabFusion");
      const panelType = $("sensorPanelType");
      const panelFusion = $("sensorPanelFusion");
      if (!tabType || !panelType)
        return;
      const _activateTab = (which) => {
        const isType = which === "type";
        tabType.style.background = isType ? "var(--sa-primary-container)" : "transparent";
        tabType.style.color = isType ? "var(--sa-primary)" : "var(--sa-text-variant)";
        tabType.style.fontWeight = isType ? "700" : "400";
        tabFusion.style.background = isType ? "transparent" : "var(--sa-primary-container)";
        tabFusion.style.color = isType ? "var(--sa-text-variant)" : "var(--sa-primary)";
        tabFusion.style.fontWeight = isType ? "400" : "700";
        panelType.style.display = isType ? "" : "none";
        panelFusion.style.display = isType ? "none" : "";
      };
      tabType.onclick = () => _activateTab("type");
      tabFusion.onclick = () => _activateTab("fusion");
      let sensorData = { sensors: [], fusion_config: [], rooms: [] };
      try {
        sensorData = await this._hass.connection.sendMessagePromise({
          type: "smart_agent/get_presence_sensors"
        });
      } catch (err) {
        const loading = $("sensorTypeLoading");
        if (loading)
          loading.textContent = "❌ 加载失败: " + String(err.message || err);
        return;
      }
      this._sensorData = sensorData;
      this._renderSensorTypeList(sensorData.sensors);
      this._renderFusionScopes(sensorData.fusion_config, sensorData.rooms, sensorData.sensors);
    },
    _renderSensorTypeList(sensors) {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const loading = $("sensorTypeLoading");
      const list = $("sensorTypeList");
      if (!list)
        return;
      if (loading)
        loading.style.display = "none";
      const SENSOR_TYPE_OPTIONS = [
        { value: "", label: "自动识别" },
        { value: "pir", label: "🟡 PIR 红外" },
        { value: "mmwave", label: "🔵 mmWave 毫米波" },
        { value: "frigate", label: "📷 Frigate 摄像头" }
      ];
      if (!sensors.length) {
        list.innerHTML = `<div class="body-s" style="opacity:.5;padding:16px 0;text-align:center">
        HA 中未找到存在类传感器（occupancy / presence / motion / person_occupancy）
      </div>`;
        return;
      }
      list.innerHTML = "";
      sensors.forEach((s) => {
        const row = document.createElement("div");
        row.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;background:var(--sa-card);border:1px solid var(--sa-border)";
        const dot = s.state === "on" ? "#4caf50" : s.state === "off" ? "#9e9e9e" : "#ff9800";
        const inSaBadge = s.in_sa ? `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:var(--sa-primary-container);color:var(--sa-primary)">SA已注册</span>` : `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:rgba(0,0,0,.07);color:var(--sa-text-variant)">未注册</span>`;
        const fusionBadge = s.fusion_scope ? `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:var(--sa-secondary-container,rgba(100,180,255,.15));color:var(--sa-secondary,#1565c0)">
            融合域: ${this._esc(s.fusion_scope)}</span>` : "";
        const selId = `stype_${s.entity_id.replace(/\./g, "_")}`;
        const opts = SENSOR_TYPE_OPTIONS.map(
          (o) => `<option value="${o.value}" ${s.sensor_type === o.value ? "selected" : ""}>${o.label}</option>`
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
      list.addEventListener("click", async (e) => {
        const btn = e.target.closest(".stype-save-btn");
        if (!btn)
          return;
        const eid = btn.dataset.eid;
        const selEl = this.shadowRoot.getElementById(btn.dataset.sel);
        if (!selEl)
          return;
        const s_type = selEl.value;
        btn.disabled = true;
        btn.textContent = "…";
        try {
          await this._hass.connection.sendMessagePromise({
            type: "smart_agent/save_sensor_type",
            entity_id: eid,
            sensor_type: s_type
          });
          btn.textContent = "✅";
          setTimeout(() => {
            btn.disabled = false;
            btn.textContent = "保存";
          }, 1500);
        } catch (err) {
          btn.disabled = false;
          btn.textContent = "❌";
          this._msg("保存失败: " + String(err.message || err));
        }
      });
    },
    _renderFusionScopes(fusionConfig, rooms, sensors) {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const scopeList = $("fusionScopeList");
      const addBtn = $("addFusionScopeBtn");
      if (!scopeList || !addBtn)
        return;
      let scopes = Array.isArray(fusionConfig) ? JSON.parse(JSON.stringify(fusionConfig)) : [];
      const _save = async () => {
        try {
          await this._hass.callService("smart_agent", "update_config", {
            presence_fusion: JSON.stringify(scopes)
          });
          this._msg("✅ 融合域配置已保存");
        } catch (err) {
          this._msg("❌ 保存失败: " + String(err.message || err));
        }
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
          const memberNames = (sc.members || []).map((m) => {
            const found = (sensors || []).find((s) => s.entity_id === m);
            return found ? found.name : m.split(".").pop();
          }).join("、");
          const roomsStr = (sc.rooms || []).join("、");
          card.innerHTML = `
          <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--sa-surface-2)">
            <div style="flex:1;min-width:0">
              <div style="font-weight:700;font-size:13px">${this._esc(sc.name || sc.scope_id || "未命名域")}</div>
              <div class="body-s" style="opacity:.6;margin-top:2px">
                覆盖房间: ${this._esc(roomsStr || "—")} &nbsp;·&nbsp;
                策略: ${this._esc(strategyLabel)} &nbsp;·&nbsp;
                无人确认: ${sc.vacant_hold_secs ?? 60}s
              </div>
              <div class="body-s" style="opacity:.55;margin-top:2px;word-break:break-all">
                传感器: ${this._esc(memberNames || "—")}
              </div>
            </div>
            <md-filled-tonal-button class="fusion-edit-btn" data-idx="${idx}" style="flex-shrink:0;--md-filled-tonal-button-container-height:32px;font-size:13px">编辑</md-filled-tonal-button>
            <md-filled-tonal-button class="fusion-del-btn" data-idx="${idx}"
              style="flex-shrink:0;--md-filled-tonal-button-container-height:32px;font-size:13px;color:var(--sa-error);opacity:.8">删除</md-filled-tonal-button>
          </div>
        `;
          scopeList.appendChild(card);
        });
      };
      const _showEditor = (idx) => {
        const isNew = idx === -1;
        const sc = isNew ? { scope_id: "", name: "", strategy: "occupied_or", rooms: [], members: [], vacant_hold_secs: 60 } : JSON.parse(JSON.stringify(scopes[idx]));
        const roomOpts = (rooms || []).map(
          (r) => `<option value="${this._esc(r)}" ${(sc.rooms || []).includes(r) ? "selected" : ""}>${this._esc(r)}</option>`
        ).join("");
        const memberOpts = (sensors || []).map(
          (s) => `<option value="${this._esc(s.entity_id)}" ${(sc.members || []).includes(s.entity_id) ? "selected" : ""}>
          ${this._esc(s.name)} (${this._esc(s.room || "未分区")})
        </option>`
        ).join("");
        const overlay = document.createElement("div");
        overlay.style.cssText = `
        position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;
        display:flex;align-items:center;justify-content:center;padding:20px`;
        overlay.innerHTML = `
        <div style="background:var(--sa-card);border-radius:16px;padding:24px;
                    width:min(560px,100%);max-height:80vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.3)">
          <div style="font-size:16px;font-weight:700;margin-bottom:16px">
            ${isNew ? "新建融合域" : "编辑融合域"}
          </div>
          <div style="display:grid;gap:14px">
            <div>
              <div class="label-s">显示名称 <span style="opacity:.5">（如：客餐厅开间）</span></div>
              <md-outlined-text-field id="fe_name" label="显示名称" value="${this._esc(sc.name || "")}" placeholder="客餐厅开间"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">覆盖的房间 <span style="opacity:.5">（可多选，Ctrl/Cmd）</span></div>
              <select id="fe_rooms" multiple size="4"
                style="height:auto;min-height:80px;width:100%;border:1px solid var(--sa-border);border-radius:8px;padding:4px">
                ${roomOpts || '<option value="" disabled>暂无可用房间（请先在设备管理中分配房间）</option>'}
              </select>
            </div>
            <div>
              <div class="label-s">成员传感器 <span style="opacity:.5">（可多选，Ctrl/Cmd）</span></div>
              <select id="fe_members" multiple size="5"
                style="height:auto;min-height:100px;width:100%;border:1px solid var(--sa-border);border-radius:8px;padding:4px">
                ${memberOpts || '<option value="" disabled>暂无可用传感器</option>'}
              </select>
            </div>
            <div>
              <div class="label-s">融合策略</div>
              <md-outlined-select id="fe_strategy">
                <md-select-option value="occupied_or" ${sc.strategy !== "vacant_and" ? "selected" : ""}>任一有人即有人（推荐，大开间）</md-select-option>
                <md-select-option value="vacant_and"  ${sc.strategy === "vacant_and" ? "selected" : ""}>全员无人才关灯（更保守）</md-select-option>
              </md-outlined-select>
            </div>
            <div>
              <div class="label-s">无人确认时长（秒）<span style="opacity:.5">全员无人持续此时长才触发离开</span></div>
              <md-outlined-text-field id="fe_hold" type="number" label="无人确认时长（秒）" min="10" max="600"
                value="${sc.vacant_hold_secs ?? 60}"></md-outlined-text-field>
            </div>
          </div>
          <div style="display:flex;gap:10px;margin-top:20px;justify-content:flex-end">
            <md-outlined-button id="fe_cancel">取消</md-outlined-button>
            <md-filled-button id="fe_confirm">${isNew ? "创建" : "保存修改"}</md-filled-button>
          </div>
        </div>
      `;
        this.shadowRoot.appendChild(overlay);
        const _close = () => overlay.remove();
        overlay.querySelector("#fe_cancel").onclick = _close;
        overlay.querySelector("#fe_confirm").onclick = async () => {
          const nameVal = overlay.querySelector("#fe_name").value.trim();
          const roomsSel = [...overlay.querySelector("#fe_rooms").selectedOptions].map((o) => o.value);
          const membersSel = [...overlay.querySelector("#fe_members").selectedOptions].map((o) => o.value);
          const strategy = overlay.querySelector("#fe_strategy").value;
          const holdSecs = parseInt(overlay.querySelector("#fe_hold").value, 10) || 60;
          if (!nameVal) {
            this._msg("请填写显示名称");
            return;
          }
          if (!membersSel.length) {
            this._msg("请至少选择一个传感器成员");
            return;
          }
          const scopeId = nameVal.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, "_") || `scope_${Date.now()}`;
          const newScope = {
            scope_id: isNew ? scopeId : sc.scope_id || scopeId,
            name: nameVal,
            strategy,
            rooms: roomsSel,
            members: membersSel,
            vacant_hold_secs: holdSecs
          };
          if (isNew) {
            scopes.push(newScope);
          } else {
            scopes[idx] = newScope;
          }
          _close();
          await _save();
          _render();
        };
      };
      scopeList.addEventListener("click", async (e) => {
        var _a;
        const editBtn = e.target.closest(".fusion-edit-btn");
        const delBtn = e.target.closest(".fusion-del-btn");
        if (editBtn)
          _showEditor(parseInt(editBtn.dataset.idx, 10));
        if (delBtn) {
          const i = parseInt(delBtn.dataset.idx, 10);
          if (!await this._showConfirm(`确认删除融合域「${((_a = scopes[i]) == null ? void 0 : _a.name) || i}」？`))
            return;
          scopes.splice(i, 1);
          _save().then(() => _render());
        }
      });
      addBtn.onclick = () => _showEditor(-1);
      _render();
    }
  };

  // src/render/devices.js
  var devicesMethods = {
    _renderDevs() {
      const PAGE_SIZE = 20;
      const $ = (id) => this.shadowRoot.getElementById(id);
      const ICO = this._getIcons();
      const configured = new Set(this._wsGet("devices", "devices", []).map((d) => d.entity_id));
      const offlineToggle = $("showOfflineToggle");
      if (offlineToggle && !offlineToggle._bound) {
        offlineToggle._bound = true;
        offlineToggle.checked = !!this._showOffline;
        offlineToggle.onchange = () => {
          this._showOffline = offlineToggle.checked;
          this._renderDevs();
        };
      }
      const ignoredToggle = $("showIgnoredToggle");
      if (ignoredToggle && !ignoredToggle._bound) {
        ignoredToggle._bound = true;
        ignoredToggle.checked = !!this._showIgnored;
        ignoredToggle.onchange = () => {
          this._showIgnored = ignoredToggle.checked;
          this._renderDevs();
        };
      }
      const discoverBtn = $("discoverBtn");
      if (discoverBtn && !discoverBtn._bound) {
        discoverBtn._bound = true;
        discoverBtn.onclick = async () => {
          discoverBtn.classList.add("loading");
          try {
            await this._hass.callService("smart_agent", "discover_devices", {});
            this._msg("扫描完成，正在刷新列表...");
            delete this._wsData["devices"];
            await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
          } catch (e) {
            this._msg("扫描失败: " + e.message);
          } finally {
            setTimeout(() => discoverBtn.classList.remove("loading"), 500);
          }
        };
      }
      const syncToHaBtn = $("syncToHaBtn");
      if (syncToHaBtn && !syncToHaBtn._bound) {
        syncToHaBtn._bound = true;
        syncToHaBtn.onclick = async () => {
          syncToHaBtn.classList.add("loading");
          try {
            await this._hass.callService("smart_agent", "sync_rooms_to_ha", {});
            this._msg("同步完成！AI 分区已应用到 HA 区域注册表。");
            this._renderDevs();
          } catch (e) {
            this._msg("同步失败: " + e.message);
          } finally {
            setTimeout(() => syncToHaBtn.classList.remove("loading"), 500);
          }
        };
      }
      const _haAreaMap = {};
      if (this._hass.entities && this._hass.areas) {
        const areasById = this._hass.areas;
        Object.values(this._hass.entities).forEach((ent) => {
          const areaId = ent.area_id;
          if (areaId && areasById[areaId]) {
            _haAreaMap[ent.entity_id] = areasById[areaId].name;
          }
        });
      }
      const showIgnored = this._showIgnored || false;
      const _isFrigateControl = (eid) => {
        const obj = eid.includes(".") ? eid.split(".")[1] : eid;
        if (!obj.startsWith("cam_"))
          return false;
        return ["_detect", "_motion", "_improve_contrast", "_autotracking"].some((s) => obj.endsWith(s));
      };
      let allNew = Object.values(this._hass.states).filter((s) => {
        var _a;
        const d = s.entity_id.split(".")[0];
        if (!TARGET_DOMAINS.includes(d))
          return false;
        if (!showIgnored) {
          if (SKIP_KW.some((k) => s.entity_id.includes(k)))
            return false;
          if (_isFrigateControl(s.entity_id))
            return false;
          const n = ((_a = s.attributes) == null ? void 0 : _a.friendly_name) || "";
          if (SKIP_NAME_KW.some((k) => n.toLowerCase().includes(k.toLowerCase())))
            return false;
        }
        return !configured.has(s.entity_id);
      }).map((s) => ({
        id: s.entity_id,
        n: s.attributes.friendly_name || s.entity_id,
        d: s.entity_id.split(".")[0],
        s: s.state,
        area: _haAreaMap[s.entity_id] || "",
        unavail: ["unavailable", "unknown"].includes(s.state)
      }));
      const showOffline = this._showOffline || false;
      const filteredNew = showOffline ? allNew : allNew.filter((i) => !i.unavail);
      const newTypes = [...new Set(allNew.map((i) => i.d))].sort();
      const dtf = $("devTypeFilter");
      const activeNT = this._newTypeFilter || "all";
      const newSearchEl = $("newDevSearch");
      if (newSearchEl && !newSearchEl._bound) {
        newSearchEl._bound = true;
        newSearchEl.oninput = () => {
          this._newSearchKw = newSearchEl.value;
          this._newPage = 0;
          this._renderDevs();
        };
      }
      const newKw = (this._newSearchKw || "").trim().toLowerCase();
      dtf.innerHTML = ["all", ...newTypes].map((t) => {
        const cnt = t === "all" ? filteredNew.length : filteredNew.filter((i) => i.d === t).length;
        if (t !== "all" && cnt === 0)
          return "";
        const label = t === "all" ? "全部" : DOMAIN_LABELS[t] || this._esc(t);
        return `<button class="chip ntf-btn ${activeNT === t ? "active" : ""}" data-t="${this._esc(t)}">${label} (${cnt})</button>`;
      }).join("");
      dtf.querySelectorAll(".ntf-btn").forEach((b) => b.onclick = () => {
        this._newTypeFilter = b.dataset.t;
        this._newPage = 0;
        this._renderDevs();
      });
      const typeFiltered0 = activeNT === "all" ? filteredNew : filteredNew.filter((i) => i.d === activeNT);
      const typeFiltered = newKw ? typeFiltered0.filter((i) => i.n.toLowerCase().includes(newKw) || i.id.toLowerCase().includes(newKw)) : typeFiltered0;
      const totalNew = typeFiltered.length;
      const totalNewPages = Math.ceil(totalNew / PAGE_SIZE) || 1;
      if (this._newPage >= totalNewPages)
        this._newPage = totalNewPages - 1;
      const pageItems = typeFiltered.slice(this._newPage * PAGE_SIZE, (this._newPage + 1) * PAGE_SIZE);
      $("nCntLbl").textContent = this._selectedNew.size ? `${this._selectedNew.size} 已选` : `${totalNew} 个新设备`;
      const nt = $("nTable");
      if (!typeFiltered.length) {
        nt.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">📡</div>
        <div class="empty-state-title">暂无发现新设备</div>
        <div class="empty-state-desc">所有可用设备已添加，或点击「扫描」重新发现</div>
      </div>`;
      } else {
        let html = `<div class="m3-list">`;
        pageItems.forEach((i) => {
          const isSelected = this._selectedNew.has(i.id);
          html += `
          <div class="m3-item dev-row ${isSelected ? "selected" : ""} ${i.unavail ? "dev-unavail" : ""}" data-id="${this._esc(i.id)}" data-type="new" style="cursor:pointer">
            <md-checkbox ${isSelected ? "checked" : ""} aria-checked="${isSelected}"></md-checkbox>
            <div class="m3-icon">${ICO[i.d] || ICO.device}</div>
            <div class="m3-content">
              <div class="m3-title">${this._esc(i.n)}</div>
              <div class="m3-subtitle">${this._esc(i.id)}${i.area ? ` · <span style="color:var(--sa-primary)">${this._esc(i.area)}</span>` : ""}</div>
            </div>
            <div class="body-s" style="text-align:right;flex-shrink:0">${i.unavail ? '<span style="color:var(--sa-state-offline)">离线</span>' : this._esc(i.s)}</div>
          </div>`;
        });
        nt.innerHTML = html + `</div>`;
        nt.querySelectorAll(".dev-row").forEach((el) => el.onclick = () => {
          const id = el.dataset.id;
          this._selectedCfg.clear();
          if (this._selectedNew.has(id))
            this._selectedNew.delete(id);
          else
            this._selectedNew.add(id);
          this._renderDevs();
          this._updateBatchFab();
        });
      }
      this._renderPager($("nPager"), this._newPage, totalNewPages, (p) => {
        this._newPage = p;
        this._renderDevs();
      });
      const cAll = this._wsGet("devices", "devices", []);
      const cfgRooms = [
        ...new Set(cAll.map((i) => i.room || "（未分区）"))
      ].sort((a, b) => {
        if (a === "（未分区）")
          return 1;
        if (b === "（未分区）")
          return -1;
        return a.localeCompare(b, "zh");
      });
      const activeRoom = this._cfgRoomFilter || "all";
      const noRoomCnt = cAll.filter((d) => !d.room).length;
      const rrf = $("cfgRoomFilter");
      if (rrf) {
        rrf.innerHTML = [
          { key: "all", label: `全部房间`, cnt: cAll.length },
          ...cfgRooms.map((r) => ({
            key: r,
            label: r === "（未分区）" ? `⚠ 未分区` : r,
            cnt: cAll.filter((i) => (i.room || "（未分区）") === r).length
          }))
        ].map(({ key, label, cnt }) => {
          const isUnassigned = key === "（未分区）";
          const isActive = activeRoom === key;
          const baseStyle = isUnassigned && !isActive ? "background:var(--sa-err-container);color:var(--sa-err);border:1px solid transparent" : "";
          return `<button class="chip crf-btn ${isActive ? "active" : ""}"
          data-r="${this._esc(key)}" style="${baseStyle}">
          ${this._esc(label)} <span style="opacity:.65">${cnt}</span>
        </button>`;
        }).join("");
        rrf.querySelectorAll(".crf-btn").forEach((b) => b.onclick = () => {
          var _a;
          const newRoom = b.dataset.r;
          if (newRoom !== (this._cfgRoomFilter || "all")) {
            this._cfgTypeFilter = "all";
            this._selectedCfg.clear();
            (_a = this._updateBatchFab) == null ? void 0 : _a.call(this);
          }
          this._cfgRoomFilter = newRoom;
          this._cfgPage = 0;
          this._renderDevs();
        });
        if (noRoomCnt === 0) {
          rrf.querySelectorAll(".crf-btn").forEach((b) => {
            if (b.dataset.r === "（未分区）")
              b.style.display = "none";
          });
        }
      }
      const noRoomBtn = $("filterNoRoomBtn");
      if (noRoomBtn) {
        if (noRoomCnt > 0) {
          noRoomBtn.style.display = "";
          noRoomBtn.textContent = `⚠ ${noRoomCnt} 个未分区`;
          if (!noRoomBtn._bound) {
            noRoomBtn._bound = true;
            noRoomBtn.onclick = () => {
              this._cfgRoomFilter = this._cfgRoomFilter === "（未分区）" ? "all" : "（未分区）";
              this._cfgPage = 0;
              this._renderDevs();
            };
          }
        } else {
          noRoomBtn.style.display = "none";
          if (this._cfgRoomFilter === "（未分区）")
            this._cfgRoomFilter = "all";
        }
      }
      const cAllRoom = activeRoom === "all" ? cAll : cAll.filter((i) => (i.room || "（未分区）") === activeRoom);
      const cfgTypes = [...new Set(cAllRoom.map((i) => i.type || "其他"))].sort();
      const ctf = $("cfgTypeFilter");
      const activeCT = this._cfgTypeFilter || "all";
      const cfgSearchEl = $("cfgDevSearch");
      if (cfgSearchEl && !cfgSearchEl._bound) {
        cfgSearchEl._bound = true;
        cfgSearchEl.oninput = () => {
          this._cfgSearchKw = cfgSearchEl.value;
          this._cfgPage = 0;
          this._renderDevs();
        };
      }
      const cfgKw = (this._cfgSearchKw || "").trim().toLowerCase();
      ctf.innerHTML = ["all", ...cfgTypes].map((t) => {
        const cnt = t === "all" ? cAllRoom.length : cAllRoom.filter((i) => (i.type || "其他") === t).length;
        if (t !== "all" && cnt === 0)
          return "";
        const label = t === "all" ? "全部类型" : DOMAIN_LABELS[t] || this._esc(t);
        return `<button class="chip ctf-btn ${activeCT === t ? "active" : ""}" data-t="${this._esc(t)}">${label} (${cnt})</button>`;
      }).join("");
      ctf.querySelectorAll(".ctf-btn").forEach((b) => b.onclick = () => {
        this._cfgTypeFilter = b.dataset.t;
        this._cfgPage = 0;
        this._renderDevs();
      });
      let cfgFiltered0 = cAllRoom;
      if (activeCT !== "all")
        cfgFiltered0 = cfgFiltered0.filter((i) => (i.type || "其他") === activeCT);
      const cfgFiltered = cfgKw ? cfgFiltered0.filter((i) => (i.name || "").toLowerCase().includes(cfgKw) || (i.entity_id || "").toLowerCase().includes(cfgKw) || (i.room || "").toLowerCase().includes(cfgKw)) : cfgFiltered0;
      const totalCfg = cfgFiltered.length;
      const totalCfgPages = Math.ceil(totalCfg / PAGE_SIZE) || 1;
      if (this._cfgPage >= totalCfgPages)
        this._cfgPage = totalCfgPages - 1;
      const cfgPageSlice = cfgFiltered.slice(this._cfgPage * PAGE_SIZE, (this._cfgPage + 1) * PAGE_SIZE);
      const _hasFilter = activeRoom !== "all" || activeCT !== "all" || cfgKw;
      $("cCntLbl").textContent = this._selectedCfg.size ? `${this._selectedCfg.size} 已选` : _hasFilter ? `${totalCfg} / ${cAll.length} 个已托管` : `${totalCfg} 个已托管`;
      const ct = $("cTable");
      if (!cAll.length) {
        ct.innerHTML = `<div class="body-s" style="text-align:center;padding:40px;opacity:.5">尚未添加任何托管设备</div>`;
      } else if (!cfgFiltered.length) {
        const filterDesc = [
          activeRoom !== "all" ? `房间「${activeRoom}」` : "",
          activeCT !== "all" ? `类型「${DOMAIN_LABELS[activeCT] || activeCT}」` : "",
          cfgKw ? `关键字「${cfgKw}」` : ""
        ].filter(Boolean).join(" + ");
        ct.innerHTML = `
        <div style="text-align:center;padding:40px;opacity:.7">
          <div style="font-size:32px;margin-bottom:12px">🔍</div>
          <div class="label-m" style="margin-bottom:6px">当前筛选无结果</div>
          <div class="body-s">${this._esc(filterDesc)}</div>
          <md-filled-tonal-button style="--md-filled-tonal-button-container-height:32px;font-size:13px;margin-top:16px" id="cfgClearFilter">清除筛选</md-filled-tonal-button>
        </div>`;
        const clearBtn = ct.querySelector("#cfgClearFilter");
        if (clearBtn)
          clearBtn.onclick = () => {
            this._cfgRoomFilter = "all";
            this._cfgTypeFilter = "all";
            this._cfgSearchKw = "";
            const s = $("cfgDevSearch");
            if (s)
              s.value = "";
            this._cfgPage = 0;
            this._renderDevs();
          };
      } else {
        const MODE_CFG = {
          ai: { label: "AI全权", bg: "rgba(103,80,164,.13)", color: "var(--sa-primary)" },
          ha: { label: "HA优先", bg: "rgba(25,118,210,.12)", color: "#1976d2" },
          shared: { label: "共享", bg: "rgba(80,80,80,.1)", color: "var(--sa-text-variant)" }
        };
        const _stateLabel = (entityId) => {
          var _a, _b, _c;
          const st = (((_a = this._hass) == null ? void 0 : _a.states) || {})[entityId];
          if (!st)
            return null;
          const s = st.state;
          if (["unavailable", "unknown"].includes(s))
            return { text: "离线", ok: false };
          const domain = entityId.split(".")[0];
          if (domain === "light" || domain === "switch" || domain === "fan") {
            return { text: s === "on" ? "开" : "关", ok: s === "on" };
          }
          if (domain === "binary_sensor") {
            return { text: s === "on" ? "触发" : "正常", ok: s === "on" };
          }
          if (domain === "climate") {
            const temp = (_b = st.attributes) == null ? void 0 : _b.current_temperature;
            return { text: temp != null ? `${temp}℃` : s === "off" ? "关" : s, ok: s !== "off" };
          }
          if (domain === "cover") {
            return { text: s === "open" ? "开" : s === "closed" ? "关" : s, ok: s === "open" };
          }
          if (domain === "sensor") {
            const unit = ((_c = st.attributes) == null ? void 0 : _c.unit_of_measurement) || "";
            return { text: `${s}${unit}`.substring(0, 10), ok: true };
          }
          return { text: String(s).substring(0, 10), ok: true };
        };
        const roomGroups = {};
        cfgPageSlice.forEach((i) => {
          const room = i.room || "（未分区）";
          if (!roomGroups[room])
            roomGroups[room] = [];
          roomGroups[room].push(i);
        });
        const sortedRooms = Object.keys(roomGroups).sort((a, b) => {
          if (a === "（未分区）")
            return 1;
          if (b === "（未分区）")
            return -1;
          return a.localeCompare(b, "zh");
        });
        let html = "";
        sortedRooms.forEach((room) => {
          const items = roomGroups[room];
          const isUnassigned = room === "（未分区）";
          const typeCounts = {};
          items.forEach((i) => {
            const t = i.type || "其他";
            typeCounts[t] = (typeCounts[t] || 0) + 1;
          });
          const typeBreakdown = Object.entries(typeCounts).map(([t, n]) => `<span style="font-size:11px;padding:1px 7px;border-radius:8px;
            background:var(--sa-primary-container);color:var(--sa-on-primary-container)">${this._esc(t)} ${n}</span>`).join("");
          html += `
          <div style="margin-bottom:20px">
            <!-- 房间分组标题 -->
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;
                        padding:8px 12px;border-radius:10px;
                        background:${isUnassigned ? "var(--sa-err-container)" : "var(--sa-primary-container)"};
                        border-left:3px solid ${isUnassigned ? "var(--sa-err)" : "var(--sa-primary)"}">
              <span style="font-size:13px;font-weight:700;
                           color:${isUnassigned ? "var(--sa-err)" : "var(--sa-primary)"}">
                ${isUnassigned ? "⚠ 未分区" : this._esc(room)}
              </span>
              <span style="font-size:11px;background:rgba(0,0,0,.1);border-radius:8px;
                           padding:1px 8px;color:inherit;font-weight:500">${items.length} 台</span>
              <div style="display:flex;flex-wrap:wrap;gap:4px;margin-left:4px">${typeBreakdown}</div>
            </div>
            <!-- 设备卡片列表 -->
            <div style="display:flex;flex-direction:column;gap:6px">`;
          items.forEach((i) => {
            const domain = (i.entity_id || "").split(".")[0];
            const mode = i.control_mode || "shared";
            const modeCfg = MODE_CFG[mode] || MODE_CFG.shared;
            const isSelected = this._selectedCfg.has(i.entity_id);
            const stLabel = _stateLabel(i.entity_id);
            const isOnline = stLabel ? stLabel.ok !== false && stLabel.text !== "离线" : null;
            const eidDisplay = i.entity_id.length > 40 ? `…${i.entity_id.slice(-38)}` : i.entity_id;
            html += `
              <div class="dev-row" data-id="${this._esc(i.entity_id)}" data-type="cfg"
                   style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:12px;
                          cursor:pointer;transition:background .15s;
                          background:${isSelected ? "var(--sa-primary-container)" : "var(--sa-card)"};
                          border:1px solid ${isSelected ? "var(--sa-primary)" : "var(--sa-border)"}">
                <!-- 勾选框 -->
                <md-checkbox ${isSelected ? "checked" : ""} style="flex-shrink:0"></md-checkbox>
                <!-- 图标 + 状态点 -->
                <div style="position:relative;flex-shrink:0;width:36px;height:36px;
                            border-radius:10px;background:var(--sa-primary-container);
                            display:flex;align-items:center;justify-content:center;font-size:18px">
                  ${ICO[domain] || ICO.device}
                  ${stLabel ? `<span style="position:absolute;bottom:1px;right:1px;width:8px;height:8px;
                    border-radius:50%;border:1.5px solid var(--sa-card);
                    background:${isOnline ? "#4caf50" : "#9e9e9e"}"></span>` : ""}
                </div>
                <!-- 设备信息 -->
                <div style="flex:1;min-width:0">
                  <div style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;
                              text-overflow:ellipsis">${this._esc(i.name)}</div>
                  <div style="font-size:11px;color:var(--sa-text-variant);font-family:monospace;
                              white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                              margin-top:1px" title="${this._esc(i.entity_id)}">${this._esc(eidDisplay)}</div>
                </div>
                <!-- 当前状态 -->
                ${stLabel ? `
                <div style="flex-shrink:0;font-size:11px;font-weight:600;padding:2px 8px;
                            border-radius:8px;white-space:nowrap;
                            background:${isOnline ? "rgba(76,175,80,.12)" : "rgba(0,0,0,.07)"};
                            color:${isOnline ? "#388e3c" : "var(--sa-text-variant)"}">
                  ${this._esc(stLabel.text)}
                </div>` : ""}
                <!-- 控制模式 -->
                <div style="flex-shrink:0;font-size:11px;font-weight:600;padding:2px 10px;
                            border-radius:8px;white-space:nowrap;
                            background:${modeCfg.bg};color:${modeCfg.color}">
                  ${modeCfg.label}
                </div>
                <!-- 操作按钮 -->
                <button class="help-close single-edit-btn"
                  data-id="${this._esc(i.entity_id)}"
                  data-name="${this._esc(i.name)}"
                  data-room="${this._esc(i.room || "")}"
                  data-type="${this._esc(i.type || "")}"
                  title="编辑" style="flex-shrink:0;padding:6px;border-radius:8px;color:var(--sa-text-variant)">
                  ${ICO.edit}
                </button>
                <button class="help-close single-del-btn"
                  data-id="${this._esc(i.entity_id)}"
                  data-name="${this._esc(i.name)}"
                  title="停止托管" style="flex-shrink:0;padding:6px;border-radius:8px;color:var(--sa-text-variant)">
                  ${ICO.delete}
                </button>
              </div>`;
          });
          html += `</div></div>`;
        });
        ct.innerHTML = html;
        ct.querySelectorAll(".dev-row").forEach((el) => {
          el.onclick = (e) => {
            if (e.target.closest(".single-del-btn") || e.target.closest(".single-edit-btn"))
              return;
            const id = el.dataset.id;
            this._selectedNew.clear();
            if (this._selectedCfg.has(id))
              this._selectedCfg.delete(id);
            else
              this._selectedCfg.add(id);
            this._renderDevs();
            this._updateBatchFab();
          };
          el.onmouseenter = () => {
            if (!this._selectedCfg.has(el.dataset.id))
              el.style.background = "var(--sa-primary-container)";
          };
          el.onmouseleave = () => {
            if (!this._selectedCfg.has(el.dataset.id))
              el.style.background = "var(--sa-card)";
          };
        });
        ct.querySelectorAll(".single-del-btn").forEach((btn) => {
          btn.onclick = async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id, name = btn.dataset.name;
            if (!await this._showConfirm(`确定要停止托管设备「${name || id}」吗？`))
              return;
            try {
              await this._hass.callService("smart_agent", "delete_device", { entity_id: id });
              this._msg("已停止托管该设备");
              delete this._wsData["devices"];
              await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
            } catch (err) {
              this._msg("操作失败: " + err.message);
            }
          };
        });
        ct.querySelectorAll(".single-edit-btn").forEach((btn) => {
          btn.onclick = async (e) => {
            e.stopPropagation();
            await this._showEditDevDialog(
              btn.dataset.id,
              btn.dataset.name,
              btn.dataset.room,
              btn.dataset.type
            );
          };
        });
      }
      this._renderPager($("cPager"), this._cfgPage, totalCfgPages, (p) => {
        this._cfgPage = p;
        this._renderDevs();
      });
    }
  };

  // src/render/rooms.js
  var roomsMethods = {
    _renderRooms() {
      const view = this.shadowRoot.getElementById("view-rooms");
      if (!view)
        return;
      const ICO = this._getIcons();
      const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a) => a.name) : [];
      const devices = this._wsGet("devices", "devices", []);
      const devRooms = devices.map((d) => d.room || "").filter((r) => r);
      const rooms = [.../* @__PURE__ */ new Set([...haAreas, ...devRooms, ...this._customRooms || []])].sort((a, b) => a.localeCompare(b, "zh"));
      if (!this._roomAdj)
        this._roomAdj = {};
      const adj = this._roomAdj;
      const adjCount = (r) => Object.keys(adj).filter(
        (k) => (k === r || k.split("||")[0] === r || k.split("||")[1] === r) && adj[k]
      ).length;
      const isAdj = (a, b) => {
        const key = [a, b].sort().join("||");
        return !!adj[key];
      };
      const setAdj = (a, b, val) => {
        const key = [a, b].sort().join("||");
        if (val)
          adj[key] = true;
        else
          delete adj[key];
      };
      view.innerHTML = `
      <div class="main">
        <!-- 页头 -->
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
          <div>
            <div class="title-l">房间拓扑配置</div>
            <div class="body-s" style="margin-top:4px;opacity:.7">
              配置房间相邻关系，AI 推理跨房间场景时会参考此拓扑，避免区域隔离误拦截
            </div>
          </div>
          <div style="display:flex;gap:8px">
            <md-outlined-button id="roomSyncHaBtn">从 HA 同步区域</md-outlined-button>
            <md-filled-button id="roomSaveBtn">保存拓扑</md-filled-button>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:260px 1fr;gap:20px;align-items:start">
          <!-- 左栏：房间列表 -->
          <div class="card">
            <div class="card-title">房间列表 <span style="font-weight:400;opacity:.6">(${rooms.length})</span></div>
            <div id="roomList" style="display:flex;flex-direction:column;gap:6px">
              ${rooms.map((r) => `
                <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
                  border-radius:10px;background:var(--sa-bg);border:1px solid var(--sa-border)">
                  <span style="flex:1;font-size:14px;font-weight:500">${this._esc(r)}</span>
                  <span class="body-s" style="opacity:.6" id="adj-cnt-${this._esc(r)}">
                    ${adjCount(r)} 相邻
                  </span>
                </div>`).join("")}
            </div>
            <!-- 添加自定义房间 -->
            <div style="margin-top:12px;display:flex;gap:8px">
              <md-outlined-text-field id="newRoomInput" label="添加自定义房间" style="flex:1"></md-outlined-text-field>
              <md-icon-button id="addRoomBtn" title="添加">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              </md-icon-button>
            </div>
          </div>

          <!-- 右栏：相邻关系矩阵 -->
          <div class="card">
            <div class="card-title">相邻关系矩阵</div>
            <div class="body-s" style="margin-bottom:12px;opacity:.7">
              勾选表示两个房间相邻，AI 推理时视为可连通。对角线为同一房间，不可勾选。
            </div>
            ${rooms.length < 2 ? `
              <div class="empty-state">
                <div class="empty-state-icon">🏠</div>
                <div class="empty-state-title">暂无房间数据</div>
                <div class="empty-state-desc">请先在 HA 中配置区域，或点击「从 HA 同步区域」</div>
              </div>` : `
            <div style="overflow-x:auto">
              <table id="roomMatrix" style="border-collapse:collapse;font-size:13px;min-width:100%">
                <thead>
                  <tr>
                    <th style="min-width:90px;padding:6px 8px;text-align:left;font-weight:500;opacity:.6">房间</th>
                    ${rooms.map((r) => `
                      <th style="padding:4px 2px;min-width:36px;max-width:48px;text-align:center">
                        <div style="writing-mode:vertical-rl;text-orientation:mixed;
                          font-size:12px;font-weight:500;padding:4px 0;white-space:nowrap">
                          ${this._esc(r)}
                        </div>
                      </th>`).join("")}
                  </tr>
                </thead>
                <tbody>
                  ${rooms.map((ra) => `
                    <tr>
                      <td style="padding:6px 8px;font-weight:500;white-space:nowrap;font-size:13px">
                        ${this._esc(ra)}
                      </td>
                      ${rooms.map(
        (rb) => ra === rb ? `<td style="text-align:center;background:var(--sa-border);opacity:.3">—</td>` : `<td style="text-align:center;padding:4px 2px">
                            <md-checkbox
                              data-a="${this._esc(ra)}"
                              data-b="${this._esc(rb)}"
                              ${isAdj(ra, rb) ? "checked" : ""}
                            ></md-checkbox>
                          </td>`
      ).join("")}
                    </tr>`).join("")}
                </tbody>
              </table>
            </div>
            <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
              <md-outlined-button id="roomClearAllBtn">清空所有关系</md-outlined-button>
            </div>`}
          </div>
        </div>

        <!-- 拓扑摘要 -->
        <div class="card" id="roomTopoSummaryCard">
          <div class="card-title">拓扑摘要</div>
          <div id="roomTopoSummary" style="display:flex;flex-wrap:wrap;gap:8px">
            ${this._buildTopoSummary(rooms, adj)}
          </div>
        </div>
      </div>`;
      const $ = (id) => view.querySelector("#" + id);
      view.querySelectorAll("md-checkbox[data-a]").forEach((cb) => {
        cb.addEventListener("change", () => {
          setAdj(cb.dataset.a, cb.dataset.b, cb.checked);
          const mirror = view.querySelector(`md-checkbox[data-a="${cb.dataset.b}"][data-b="${cb.dataset.a}"]`);
          if (mirror)
            mirror.checked = cb.checked;
          const summary = view.querySelector("#roomTopoSummary");
          if (summary)
            summary.innerHTML = this._buildTopoSummary(rooms, adj);
        });
      });
      $("roomSaveBtn").onclick = async () => {
        try {
          const topology = Object.keys(adj).map((k) => {
            const [a, b] = k.split("||");
            return { room_a: a, room_b: b, relation: "adjacent" };
          });
          await this._hass.callService("smart_agent", "save_room_topology", { topology });
          this._msg("房间拓扑已保存");
        } catch (e) {
          this._msg("保存失败: " + e.message);
        }
      };
      $("roomSyncHaBtn").onclick = async () => {
        try {
          await this._hass.callService("smart_agent", "sync_rooms_to_ha");
          this._msg("已同步 HA 区域");
          this._renderRooms();
        } catch (e) {
          this._msg("同步失败: " + e.message);
        }
      };
      const clearBtn = $("roomClearAllBtn");
      if (clearBtn)
        clearBtn.onclick = async () => {
          if (!await this._showConfirm("确定清空所有房间相邻关系？"))
            return;
          this._roomAdj = {};
          this._renderRooms();
        };
      $("addRoomBtn").onclick = () => {
        var _a;
        const input = $("newRoomInput");
        const name = (_a = input == null ? void 0 : input.value) == null ? void 0 : _a.trim();
        if (!name)
          return;
        if (!this._customRooms)
          this._customRooms = [];
        if (!this._customRooms.includes(name)) {
          this._customRooms.push(name);
          this._renderRooms();
        }
      };
    },
    _buildTopoSummary(rooms, adj) {
      const lines = rooms.map((r) => {
        const neighbors = rooms.filter((b) => b !== r && adj[[r, b].sort().join("||")]);
        if (!neighbors.length)
          return "";
        return `<div style="padding:6px 12px;background:var(--sa-bg);border-radius:8px;
        border:1px solid var(--sa-border);font-size:13px">
        <b>${this._esc(r)}</b> ↔ ${neighbors.map((n) => this._esc(n)).join("、")}
      </div>`;
      }).filter(Boolean);
      return lines.length ? lines.join("") : `<div class="body-s" style="opacity:.5">暂无相邻关系，请在矩阵中勾选</div>`;
    },
    // 加载已保存的拓扑数据
    async _loadRoomTopology() {
      try {
        const result = await this._hass.callWS({ type: "smart_agent/get_room_topology" });
        this._roomAdj = {};
        ((result == null ? void 0 : result.topology) || []).forEach(({ room_a, room_b }) => {
          const key = [room_a, room_b].sort().join("||");
          this._roomAdj[key] = true;
        });
      } catch (e) {
        this._roomAdj = {};
      }
    }
  };

  // src/render/backup.js
  var backupMethods = {
    _renderBackup() {
      const view = this.shadowRoot.getElementById("view-backup");
      if (!view)
        return;
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
        { v: "full", label: "完整备份", desc: "配置 + 数据 + 习惯" },
        { v: "config", label: "配置备份", desc: "仅系统配置" },
        { v: "data", label: "数据备份", desc: "设备 + 画像 + 规则" }
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
            <md-outlined-text-field id="backupNote" label="备注（可选）"
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
      this._bindBackupEvents(view);
      this._loadBackupList(view);
    },
    _bindBackupEvents(view) {
      const $ = (id) => view.querySelector("#" + id);
      view.querySelectorAll("[data-level]").forEach((label) => {
        label.onclick = () => {
          view.querySelectorAll("[data-level]").forEach((l) => {
            l.style.borderColor = "var(--sa-border)";
            l.style.background = "";
          });
          label.style.borderColor = "var(--sa-primary)";
          label.style.background = "var(--sa-primary-container)";
          label.querySelector("input").checked = true;
        };
      });
      const fullLabel = view.querySelector("[data-level='full']");
      if (fullLabel) {
        fullLabel.style.borderColor = "var(--sa-primary)";
        fullLabel.style.background = "var(--sa-primary-container)";
      }
      $("backupCreateBtn").onclick = () => {
        const panel = $("backupCreatePanel");
        panel.style.display = panel.style.display === "none" ? "block" : "none";
      };
      $("backupCancelBtn").onclick = () => {
        $("backupCreatePanel").style.display = "none";
      };
      $("backupConfirmBtn").onclick = async () => {
        var _a, _b, _c;
        const level = ((_a = view.querySelector("input[name='backupLevel']:checked")) == null ? void 0 : _a.value) || "full";
        const note = ((_c = (_b = $("backupNote")) == null ? void 0 : _b.value) == null ? void 0 : _c.trim()) || "";
        const btn = $("backupConfirmBtn");
        btn.disabled = true;
        btn.textContent = "备份中...";
        try {
          await this._hass.callService("smart_agent", "create_backup", { level, note });
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
      $("backupRefreshBtn").onclick = () => this._loadBackupList(view);
      const dlg = $("backupRestoreDialog");
      $("restoreCancelBtn").onclick = () => dlg.close();
      $("restoreConfirmBtn").onclick = async () => {
        const backupId = dlg.dataset.backupId;
        dlg.close();
        try {
          await this._hass.callService("smart_agent", "restore_backup", { backup_id: backupId });
          this._msg("恢复指令已发送，系统即将重启");
        } catch (e) {
          this._msg("恢复失败: " + e.message);
        }
      };
    },
    async _loadBackupList(view) {
      const area = view.querySelector("#backupListArea");
      if (!area)
        return;
      area.innerHTML = `<div style="text-align:center;padding:32px">
      <md-circular-progress indeterminate></md-circular-progress>
      <div class="body-s" style="margin-top:8px">加载备份列表...</div>
    </div>`;
      try {
        const result = await this._hass.callWS({ type: "smart_agent/list_backups" });
        const backups = (result == null ? void 0 : result.backups) || [];
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
        ${backups.map((b) => `
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
        area.querySelectorAll(".backup-restore-btn").forEach((btn) => {
          btn.onclick = () => {
            const dlg = view.querySelector("#backupRestoreDialog");
            dlg.dataset.backupId = btn.dataset.id;
            view.querySelector("#restoreTargetName").textContent = btn.dataset.note;
            dlg.show();
          };
        });
        area.querySelectorAll(".backup-delete-btn").forEach((btn) => {
          btn.onclick = async () => {
            if (!await this._showConfirm("确定删除此备份？"))
              return;
            try {
              await this._hass.callService("smart_agent", "delete_backup", { backup_id: btn.dataset.id });
              this._msg("备份已删除");
              await this._loadBackupList(view);
            } catch (e) {
              this._msg("删除失败: " + e.message);
            }
          };
        });
      } catch (e) {
        area.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">加载失败</div>
        <div class="empty-state-desc">${this._esc(e.message)}</div>
      </div>`;
      }
    }
  };

  // src/render/patrol.js
  var patrolMethods = {
    _renderPatrol() {
      var _a;
      const view = this.shadowRoot.getElementById("view-patrol");
      if (!view)
        return;
      const cfg = ((_a = this._cfg) == null ? void 0 : _a.attributes) || {};
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
                  <input id="patrolActiveInterval" type="range" min="5" max="120" step="5"
                    value="${activeInterval}" class="range-input" style="flex:1">
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
                  <input id="patrolNightInterval" type="range" min="30" max="240" step="30"
                    value="${nightInterval}" class="range-input" style="flex:1">
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
                    <input type="time" id="patrolActiveStart" value="${activeStart}"
                      style="padding:8px 12px;border:1px solid var(--sa-border);border-radius:8px;
                      background:var(--sa-card);color:var(--sa-text);font-size:14px;outline:none">
                  </div>
                  <span style="opacity:.5;margin-top:16px">—</span>
                  <div>
                    <div class="label-s">结束时间</div>
                    <input type="time" id="patrolActiveEnd" value="${activeEnd}"
                      style="padding:8px 12px;border:1px solid var(--sa-border);border-radius:8px;
                      background:var(--sa-card);color:var(--sa-text);font-size:14px;outline:none">
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
        { id: "patrolCheckEnergy", label: "能耗巡检", desc: "统计设备开启时长" },
        { id: "patrolCheckHabits", label: "习惯分析", desc: "定期分析行为规律" }
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
                <span class="sys-val-num" style="color:${(cfg.patrol_anomaly_today || 0) > 0 ? "var(--sa-err)" : "var(--sa-succ)"}">
                  ${cfg.patrol_anomaly_today || 0}
                </span>
                <span class="sys-val-unit">项</span>
              </div>
            </div>
          </div>
        </div>
      </div>`;
      const $ = (id) => view.querySelector("#" + id);
      $("patrolActiveInterval").oninput = (e) => {
        $("patrolActiveIntervalVal").textContent = e.target.value + " 分钟";
      };
      $("patrolNightInterval").oninput = (e) => {
        $("patrolNightIntervalVal").textContent = e.target.value + " 分钟";
      };
      $("patrolTriggerBtn").onclick = async () => {
        const btn = $("patrolTriggerBtn");
        btn.disabled = true;
        btn.textContent = "巡检中...";
        try {
          await this._hass.callService("smart_agent", "trigger_patrol", {});
          this._msg("巡检指令已发送");
        } catch (e) {
          this._msg("触发失败: " + e.message);
        } finally {
          btn.disabled = false;
          btn.textContent = "▶ 立即巡检";
        }
      };
      $("patrolSaveBtn").onclick = async () => {
        const data = {
          patrol_enabled: $("patrolEnabled").selected,
          patrol_active_interval: parseInt($("patrolActiveInterval").value),
          patrol_night_interval: parseInt($("patrolNightInterval").value),
          patrol_active_start: $("patrolActiveStart").value,
          patrol_active_end: $("patrolActiveEnd").value
        };
        try {
          await this._hass.callService("smart_agent", "update_config", data);
          this._msg("巡检配置已保存");
        } catch (e) {
          this._msg("保存失败: " + e.message);
        }
      };
    }
  };

  // src/render/mcp.js
  var mcpMethods = {
    _renderMcp() {
      var _a;
      const view = this.shadowRoot.getElementById("view-mcp");
      if (!view)
        return;
      const cfg = ((_a = this._cfg) == null ? void 0 : _a.attributes) || {};
      const mcpEnabled = cfg.mcp_enabled !== false;
      const mcpUrl = `${window.location.origin}/api/smart_agent/mcp`;
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
        { name: "smart_control", desc: "控制智能家居设备（开关灯、调节温度等）", icon: "⚡" },
        { name: "smart_device_list", desc: "获取已托管设备列表及当前状态", icon: "📋" },
        { name: "smart_query", desc: "查询设备状态、房间信息、AI 决策历史", icon: "🔍" },
        { name: "smart_scene", desc: "触发 AI 场景或自定义场景", icon: "🎬" }
      ].map((t) => `
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
      const $ = (id) => view.querySelector("#" + id);
      $("mcpCopyBtn").onclick = () => {
        var _a2;
        (_a2 = navigator.clipboard) == null ? void 0 : _a2.writeText(mcpUrl).then(() => this._msg("地址已复制"));
      };
      $("mcpEnabledSwitch").addEventListener("change", async (e) => {
        try {
          await this._hass.callService("smart_agent", "update_config", { mcp_enabled: e.target.selected });
          this._msg(e.target.selected ? "MCP 服务已启用" : "MCP 服务已禁用");
        } catch (err) {
          this._msg("设置失败: " + err.message);
        }
      });
    }
  };

  // src/render/license.js
  var licenseMethods = {
    _renderLicensePage() {
      var _a;
      const view = this.shadowRoot.getElementById("view-license");
      if (!view)
        return;
      const cfg = ((_a = this._cfg) == null ? void 0 : _a.attributes) || {};
      const lic = cfg.license || {};
      const tierColors = { free: "#888", basic: "#2196f3", pro: "#4caf50", business: "#ff9800" };
      const tierColor = tierColors[lic.tier] || "#888";
      const progressPct = lic.daily_limit > 0 ? Math.min(100, Math.round(lic.daily_used / lic.daily_limit * 100)) : 0;
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
            ${lic.valid ? `<span style="color:var(--sa-succ);font-weight:600">✅ 已激活</span>` : lic.has_key ? `<span style="color:var(--sa-err);font-weight:600">❌ 验证失败</span>` : `<span style="opacity:.5">⚪ 未激活</span>`}
            ${lic.expires ? `<span class="body-s" style="opacity:.6">到期：${this._esc(String(lic.expires))}</span>` : ""}
          </div>

          <!-- 配额进度 -->
          <div style="margin-bottom:16px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
              <span class="label-s">今日 AI 推理配额</span>
              <span class="body-s">
                ${lic.daily_limit === -1 ? `已用 ${lic.daily_used || 0} 次（无限制）` : `${lic.daily_used || 0} / ${lic.daily_limit || 0} 次`}
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
        { tier: "免费版", quota: "30 次", scene: "✅", backup: "❌" },
        { tier: "基础版", quota: "200 次", scene: "✅", backup: "✅" },
        { tier: "专业版", quota: "无限制", scene: "✅", backup: "✅" },
        { tier: "商业版", quota: "无限制", scene: "✅", backup: "✅" }
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
      const $ = (id) => view.querySelector("#" + id);
      $("licenseVerifyBtn").onclick = async () => {
        const btn = $("licenseVerifyBtn");
        btn.disabled = true;
        btn.textContent = "验证中...";
        try {
          await this._hass.callService("smart_agent", "verify_license", {});
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
    }
  };

  // src/update.js
  var updateMethods = {
    _update() {
      var _a, _b, _c, _d;
      const $ = (id) => this.shadowRoot.getElementById(id);
      const c = this._cfg.attributes || {}, s = this._sts.attributes || {};
      if ($("dCnt"))
        $("dCnt").textContent = c.device_count || 0;
      if ($("hCnt"))
        $("hCnt").textContent = c.habit_count || 0;
      if ($("rCnt"))
        $("rCnt").textContent = c.rule_count || 0;
      if ($("rCntSub")) {
        const total = c.rule_count || 0;
        const aiCount = c.ai_rule_count || 0;
        const userCount = total - aiCount;
        if (total > 0) {
          $("rCntSub").textContent = `用户 ${userCount} · AI ${aiCount}`;
        }
      }
      if ($("sTxt"))
        $("sTxt").textContent = s.full_text || "正在监控中...";
      const aq = c.action_quality || {};
      const qCard = $("qualityCard");
      if (qCard) {
        if (aq.total > 0) {
          qCard.style.display = "block";
          const rateColor = aq.rate >= 95 ? "var(--sa-succ)" : aq.rate >= 80 ? "#d29922" : "#f85149";
          $("qualityStats").innerHTML = `
          <div class="sys-card"><div class="label-m">总执行次数</div><div class="stat-num" style="font-size:28px">${aq.total}</div></div>
          <div class="sys-card"><div class="label-m">成功率</div><div class="stat-num" style="font-size:28px;color:${rateColor}">${aq.rate}%</div></div>
          <div class="sys-card"><div class="label-m">失败次数</div><div class="stat-num" style="font-size:28px;color:${aq.failed ? "#f85149" : "var(--sa-succ)"}">${aq.failed}</div></div>
          <div class="sys-card"><div class="label-m">自动重试</div><div class="stat-num" style="font-size:28px">${aq.retry_total}</div></div>
          <div class="sys-card"><div class="label-m">平均验证延迟</div><div class="stat-num" style="font-size:28px">${aq.avg_latency_ms}<span style="font-size:12px;opacity:.6">ms</span></div></div>
        `;
          const tf = aq.top_failures || [];
          if (tf.length) {
            $("qualityFailures").innerHTML = `<div class="label-m" style="margin-bottom:8px;color:#f85149">失败最多的设备 Top ${tf.length}</div>` + tf.map((f) => `<div class="body-s" style="padding:4px 0;display:flex;justify-content:space-between"><span>${this._esc(f.entity_id)}</span><span style="color:#f85149;font-weight:600">${f.count} 次</span></div>`).join("");
          } else {
            $("qualityFailures").innerHTML = "";
          }
        } else {
          qCard.style.display = "none";
        }
      }
      const guards = c.priority_guards || [];
      const priCard = $("priorityCard");
      const priList = $("priorityList");
      const priCount = $("priorityCount");
      if (priCard && priList) {
        if (guards.length > 0) {
          priCard.style.display = "block";
          if (priCount)
            priCount.textContent = `${guards.length} 个设备受保护`;
          const priColors = { 0: "#ef4444", 1: "#f59e0b", 2: "#3b82f6", 3: "#8b5cf6", 4: "var(--sa-text-variant)" };
          priList.innerHTML = guards.map((g) => {
            const color = priColors[g.priority] || "var(--sa-text-variant)";
            const mins = Math.ceil(g.remaining_sec / 60);
            const timeStr = g.remaining_sec > 60 ? `${mins}分钟` : `${g.remaining_sec}秒`;
            return `<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;background:var(--sa-bg);border:1px solid var(--sa-border)">
            <span style="color:${color};font-weight:700;font-size:12px;white-space:nowrap">${this._esc(g.priority_label)}</span>
            <span style="flex:1;font-size:13px">${this._esc(g.name)}<span style="opacity:.5;font-size:11px;margin-left:4px">${this._esc(g.entity_id)}</span></span>
            <span style="font-size:12px;opacity:.7">← ${this._esc(g.source_label)}</span>
            <span style="font-size:11px;color:${color};font-weight:600;white-space:nowrap">${timeStr}</span>
          </div>`;
          }).join("");
        } else {
          priCard.style.display = "none";
        }
      }
      const numA = $("numA"), numN = $("numN");
      if (numA && this._numA.state) {
        numA.value = parseFloat(this._numA.state);
        $("numAVal").textContent = this._numA.state;
      }
      if (numN && this._numN.state) {
        numN.value = parseFloat(this._numN.state);
        $("numNVal").textContent = this._numN.state;
      }
      const modeSel = $("modeSel"), showroomPanel = $("showroomPanel"), modeIcon = $("modeIcon");
      const modeChip = $("modeChip"), sceneIconWrap = $("sceneIconWrap");
      const ICO = this._getIcons();
      const recentAi = s.recent_ai_actions || [];
      const now = Date.now() / 1e3;
      const FRESH_SEC = 30 * 60;
      const freshAi = recentAi.filter((a) => a.time && now - a.time < FRESH_SEC);
      const aiCard = $("recentAiCard");
      if (aiCard) {
        if (recentAi.length > 0) {
          aiCard.style.display = "block";
          const badge = $("corrBadge");
          if (badge) {
            badge.textContent = freshAi.length > 0 ? freshAi.length : recentAi.length;
            badge.style.background = freshAi.length > 0 ? "" : "var(--sa-border, #555)";
            badge.title = freshAi.length > 0 ? `${freshAi.length} 个设备在 30 分钟内被 AI 操作，可纠正` : `${recentAi.length} 个设备有历史 AI 操作记录（已超过 30 分钟）`;
          }
          const groups = /* @__PURE__ */ new Map();
          recentAi.forEach((a) => {
            const key = a.scene || "(未知场景)";
            if (!groups.has(key))
              groups.set(key, 0);
            groups.set(key, groups.get(key) + 1);
          });
          const summary = $("recentAiSummary");
          if (summary) {
            let h = "";
            groups.forEach((cnt, scene) => {
              h += `<span class="chip" style="font-size:11px;cursor:pointer;max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
              title="${this._esc(scene)}" data-goto-corr="1">
              ${ICO.bolt} ${this._esc(scene.length > 20 ? scene.slice(0, 20) + "…" : scene)} · ${cnt} 设备</span>`;
            });
            summary.innerHTML = h;
            summary.querySelectorAll("[data-goto-corr]").forEach((el) => {
              el.onclick = () => this._setTab("corrections");
            });
          }
        } else {
          aiCard.style.display = "none";
        }
      }
      const goBtn = $("goToCorrections");
      if (goBtn)
        goBtn.onclick = () => this._setTab("corrections");
      const isShowroom = c.mode === "showroom";
      if (modeSel)
        modeSel.value = c.mode || "home";
      if (modeIcon)
        modeIcon.innerHTML = isShowroom ? ICO.showroom : ICO.home;
      if (modeChip) {
        modeChip.textContent = isShowroom ? "展厅模式" : "家庭模式";
        modeChip.classList.toggle("active", isShowroom);
      }
      if (sceneIconWrap)
        sceneIconWrap.innerHTML = isShowroom ? ICO.showroom : ICO.home;
      if (showroomPanel)
        showroomPanel.style.display = isShowroom ? "block" : "none";
      const sceneBtns = $("showroomSceneBtns");
      if (sceneBtns && Array.isArray(c.showroom_scenes)) {
        const activeScene = c.showroom_scene || "";
        const hasCustom = !!(c.showroom_custom_prompt || "");
        sceneBtns.innerHTML = c.showroom_scenes.map((s2) => {
          const isActive = activeScene === s2.key && !hasCustom;
          return `
          <div style="display:flex;align-items:center;gap:4px">
            <button class="chip ${isActive ? "active" : ""} showroom-scene-btn" 
              data-scene="${this._esc(s2.key)}" data-label="${this._esc(s2.label)}">
              ${this._esc(s2.label)}
            </button>
            <button class="showroom-edit-btn" data-scene="${this._esc(s2.key)}" 
              style="background:none;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:4px;border-radius:50%;transition:.2s" 
              title="编辑">
              <span style="opacity:.5">${ICO.edit}</span>
            </button>
        </div>`;
        }).join("");
      }
      const customInput = $("showroomCustomInput");
      if (customInput && !customInput.matches(":focus") && (c.showroom_custom_prompt || "")) {
        customInput.value = c.showroom_custom_prompt;
      }
      const b = $("aiBtn"), isOn = this._sw.state === "on";
      b.classList.toggle("btn-error", !isOn);
      b.classList.remove("btn", "btn-filled");
      b.textContent = isOn ? "托管中" : "已暂停";
      const learnSt = (_a = this._hass) == null ? void 0 : _a.states["switch.smart_agent_learning_mode"];
      const learnOn = (learnSt == null ? void 0 : learnSt.state) === "on";
      const learnToggle = $("learningModeToggle");
      if (learnToggle)
        learnToggle.checked = learnOn;
      const learnItem = $("learningModeItem");
      if (learnItem)
        learnItem.classList.toggle("active", learnOn);
      const habitSt = (_b = this._hass) == null ? void 0 : _b.states["switch.smart_agent_habit_proactive"];
      const habitOn = (habitSt == null ? void 0 : habitSt.state) === "on";
      const habitToggle = $("habitProactiveToggle");
      if (habitToggle)
        habitToggle.checked = habitOn;
      const habitItem = $("habitProactiveItem");
      if (habitItem)
        habitItem.classList.toggle("active", habitOn);
      const frigateSt = (_c = this._hass) == null ? void 0 : _c.states["switch.smart_agent_frigate_enabled"];
      const frigateOn = (frigateSt == null ? void 0 : frigateSt.state) === "on";
      const frigateToggle = $("frigateToggle");
      if (frigateToggle)
        frigateToggle.checked = frigateOn;
      const frigateItem = $("frigateItem");
      if (frigateItem)
        frigateItem.classList.toggle("active", frigateOn);
      const visionSt = (_d = this._hass) == null ? void 0 : _d.states["switch.smart_agent_vision_enabled"];
      const visionOn = (visionSt == null ? void 0 : visionSt.state) === "on";
      const visionToggle = $("visionToggle");
      if (visionToggle)
        visionToggle.checked = visionOn;
      const visionItem = $("visionItem");
      if (visionItem)
        visionItem.classList.toggle("active", visionOn);
      this._renderLicenseStatus(c.license);
      if (this._tab === "syslog" && this._sysLogMode === "live") {
        this._wsRefreshSysLog();
      }
      if (c.brand_name || c.brand_primary_color) {
        this._applyBrand();
      }
    }
  };

  // src/utils/helpers.js
  var helperMethods = {
    /** HTML 转义，防止 XSS */
    _esc(s) {
      return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    },
    /** 轻量 Toast 提示 */
    _msg(m) {
      const t = this.shadowRoot.getElementById("toast");
      t.textContent = m;
      t.className = "show";
      setTimeout(() => t.className = "", 3e3);
    },
    /**
     * M3 风格通用确认弹窗 — 使用 md-dialog
     * @param {string} msg 提示内容
     * @param {string} title 标题（可选）
     * @returns {Promise<boolean>}
     */
    _showConfirm(msg, title = "确认操作") {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const dlg = $("m3ConfirmDialog");
      const ok = $("m3ConfirmOk");
      const cl = $("m3ConfirmCancel");
      $("m3ConfirmTitle").textContent = title;
      $("m3ConfirmBody").textContent = msg;
      return new Promise((resolve) => {
        const done = (val) => {
          dlg.close();
          ok.onclick = null;
          cl.onclick = null;
          resolve(val);
        };
        ok.onclick = () => done(true);
        cl.onclick = () => done(false);
        dlg.addEventListener("cancel", () => done(false), { once: true });
        dlg.show();
      });
    },
    /**
     * 显示设备编辑弹窗，支持修改名称、房间、设备类型
     * @param {string} entityId 设备实体 ID
     * @param {string} currentName 当前显示名称
     * @param {string} currentRoom 当前所属房间
     * @param {string} currentType 当前设备类型
     * @returns {Promise<void>}
     */
    async _showEditDevDialog(entityId, currentName, currentRoom, currentType) {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const ov = $("m3EditDevOverlay");
      const nameEl = $("editDevName");
      const roomSel = $("editDevRoomSel");
      const roomCustom = $("editDevRoomCustom");
      const typeEl = $("editDevType");
      const saveBtn = $("m3EditDevSave");
      const cancelBtn = $("m3EditDevCancel");
      nameEl.value = currentName || "";
      typeEl.value = currentType || "";
      roomCustom.value = "";
      while (roomSel.options.length > 1)
        roomSel.remove(1);
      const cAll = this._wsGet("devices", "devices", []);
      const smRooms = cAll.map((i) => i.room || "").filter((r) => r);
      const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a) => a.name) : [];
      const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort(
        (a, b) => a.localeCompare(b, "zh")
      );
      const firstOpt = document.createElement("option");
      firstOpt.value = "";
      firstOpt.textContent = "选择房间…";
      roomSel.innerHTML = "";
      roomSel.appendChild(firstOpt);
      allRooms.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r;
        opt.textContent = r;
        if (r === currentRoom)
          opt.selected = true;
        roomSel.appendChild(opt);
      });
      if (currentRoom && !allRooms.includes(currentRoom)) {
        roomCustom.value = currentRoom;
      }
      ov.classList.add("open");
      return new Promise((resolve) => {
        const close = () => {
          ov.classList.remove("open");
          saveBtn.onclick = null;
          cancelBtn.onclick = null;
          ov.onclick = null;
          resolve();
        };
        saveBtn.onclick = async () => {
          const newName = nameEl.value.trim();
          const newRoom = roomCustom.value.trim() || roomSel.value || "";
          const newType = typeEl.value;
          if (!newName) {
            nameEl.focus();
            nameEl.style.borderColor = "var(--error, #B00020)";
            setTimeout(() => nameEl.style.borderColor = "", 1200);
            return;
          }
          try {
            const payload = { entity_id: entityId };
            if (newName)
              payload.name = newName;
            if (newRoom)
              payload.room = newRoom;
            if (newType)
              payload.dev_type = newType;
            await this._hass.callService("smart_agent", "update_device", payload);
            this._msg(`设备「${newName}」已更新`);
            delete this._wsData["devices"];
            await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
            close();
          } catch (err) {
            this._msg("保存失败: " + err.message);
          }
        };
        cancelBtn.onclick = () => close();
        ov.onclick = (e) => {
          if (e.target === ov)
            close();
        };
      });
    },
    /**
     * 通过 WebSocket 拉取数据并存入 _wsData，完成后回调渲染函数。
     * @param {string} type  WS 命令类型，如 "smart_agent/get_devices"
     * @param {string} key   _wsData 的缓存 key
     * @param {Function} cb  数据就绪后的渲染回调
     */
    async _wsRefresh(type, key, cb) {
      if (this._wsLoading[key])
        return;
      this._wsLoading[key] = true;
      try {
        const result = await this._hass.callWS({ type });
        this._wsData[key] = result;
        cb();
      } catch (e) {
        console.warn("[SmartAgent] WS fetch failed:", type, e);
      } finally {
        this._wsLoading[key] = false;
      }
    },
    /**
     * 读取 WS 缓存数据（安全取值，找不到返回空数组或空对象）。
     * @param {string} key    _wsData 的缓存 key
     * @param {string} field  result 中的字段名
     * @param {*} fallback    默认值
     */
    _wsGet(key, field, fallback = []) {
      return (this._wsData[key] || {})[field] ?? fallback;
    },
    /**
     * 获取实体友好名称（先查 HA states，再查 WS 设备列表）
     * @param {string} id  entity_id
     * @returns {string}
     */
    _getFriendlyName(id) {
      var _a;
      const s = this._hass.states[id];
      if ((_a = s == null ? void 0 : s.attributes) == null ? void 0 : _a.friendly_name)
        return s.attributes.friendly_name;
      const cfgList = this._wsGet("devices", "devices", []);
      const found = cfgList.find((d) => d.entity_id === id);
      if (found == null ? void 0 : found.name)
        return found.name;
      return id;
    }
  };

  // src/panel-core.js
  var coreMethods = {
    _toggle() {
      const s = this._sw;
      if (!s.entity_id)
        return;
      this._hass.callService(
        "switch",
        s.state === "on" ? "turn_off" : "turn_on",
        { entity_id: s.entity_id }
      );
    },
    _openSceneEdit(key) {
      var _a;
      const c = ((_a = this._cfg) == null ? void 0 : _a.attributes) || {};
      const scenes = Array.isArray(c.showroom_scenes) ? c.showroom_scenes : [];
      const scene = scenes.find((s) => s.key === key);
      if (!scene)
        return;
      this._editingSceneKey = key;
      const $ = (id) => this.shadowRoot.getElementById(id);
      $("editSceneTitle").textContent = `编辑场景: ${scene.label}`;
      $("editSceneLabel").value = scene.label;
      $("editSceneTime").value = scene.virtual_time;
      $("editSceneDesc").value = scene.scene_desc;
      $("editSceneHint").value = scene.hint;
      $("showroomEditPanel").style.display = "block";
      $("editSceneLabel").focus();
    },
    // 主 Tab 分组映射
    _GROUP_TABS: {
      space: ["devices", "rooms", "vision"],
      ai: ["profiles", "habits", "aiscenes", "corrections"],
      data: ["transactions", "energy"],
      system: ["config", "patrol", "backup", "mcp", "license"]
    },
    _setTab(t) {
      var _a, _b, _c, _d, _e;
      this._tab = t;
      const groupMap = this._GROUP_TABS;
      let activeGroup = "";
      for (const [g, tabs] of Object.entries(groupMap)) {
        if (tabs.includes(t)) {
          activeGroup = g;
          break;
        }
      }
      this.shadowRoot.querySelectorAll(".nav-tab").forEach((b) => {
        if (b.dataset.t) {
          b.classList.toggle("active", b.dataset.t === t);
        } else if (b.dataset.group) {
          b.classList.toggle("active", b.dataset.group === activeGroup);
        }
      });
      ["space", "ai", "data", "system"].forEach((g) => {
        const el = this.shadowRoot.getElementById("sub-" + g);
        if (el)
          el.style.display = g === activeGroup ? "flex" : "none";
      });
      if (activeGroup) {
        const subBar = this.shadowRoot.getElementById("sub-" + activeGroup);
        if (subBar) {
          subBar.querySelectorAll(".nav-sub-tab").forEach(
            (b) => b.classList.toggle("active", b.dataset.t === t)
          );
          this._lastSubTab = this._lastSubTab || {};
          this._lastSubTab[activeGroup] = t;
        }
      }
      this.shadowRoot.querySelectorAll(".tab-view").forEach(
        (v) => v.classList.toggle("active", v.id === "view-" + t)
      );
      if (t === "syslog") {
        this._loadLogDates();
        this._wsRefreshSysLog();
      }
      if (t === "config")
        this._renderConfig();
      if (t === "devices")
        this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
      if (t === "profiles")
        this._wsRefresh("smart_agent/get_rules", "rules", () => this._renderProfs());
      if (t === "habits")
        this._wsRefresh("smart_agent/get_behavior_patterns", "behavior_patterns", () => this._renderHabitPatterns());
      if (t === "aiscenes")
        this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
      if (t === "corrections")
        this._wsRefresh("smart_agent/get_ai_actions", "ai_actions", () => this._renderCorrections());
      if (t === "transactions")
        this._wsRefresh("smart_agent/get_transactions", "transactions", () => this._renderTransactions());
      if (t === "energy")
        this._wsRefresh("smart_agent/get_energy_stats", "energy_stats", () => this._renderEnergy());
      if (t === "rooms")
        (_a = this._renderRooms) == null ? void 0 : _a.call(this);
      if (t === "patrol")
        (_b = this._renderPatrol) == null ? void 0 : _b.call(this);
      if (t === "backup")
        (_c = this._renderBackup) == null ? void 0 : _c.call(this);
      if (t === "mcp")
        (_d = this._renderMcp) == null ? void 0 : _d.call(this);
      if (t === "license")
        (_e = this._renderLicensePage) == null ? void 0 : _e.call(this);
      this._startTerminalLogPoll(t === "dashboard");
      this._update();
    },
    // 点击分组主 Tab 时，跳转到该组上次访问的子页面（或默认第一个）
    _setGroup(group) {
      const groupMap = this._GROUP_TABS;
      const tabs = groupMap[group] || [];
      const last = (this._lastSubTab || {})[group];
      const target = last && tabs.includes(last) ? last : tabs[0];
      if (target)
        this._setTab(target);
    },
    _startTerminalLogPoll(active) {
      if (this._terminalPollTimer) {
        clearInterval(this._terminalPollTimer);
        this._terminalPollTimer = null;
      }
      if (!active)
        return;
      let _polling = false;
      const poll = async () => {
        if (_polling)
          return;
        _polling = true;
        try {
          const result = await this._hass.callWS({ type: "smart_agent/get_terminal_log" });
          const html = (result == null ? void 0 : result.html) || "";
          const box = this.shadowRoot.getElementById("lBox");
          if (box && box.innerHTML !== html) {
            box.innerHTML = html || "等待系统指令...";
          }
        } catch (_) {
        } finally {
          _polling = false;
        }
      };
      poll();
      this._terminalPollTimer = setInterval(poll, 3e3);
    },
    _renderLicenseStatus(lic) {
      var _a;
      const area = (_a = this.shadowRoot) == null ? void 0 : _a.getElementById("licenseStatusArea");
      if (!area)
        return;
      if (!lic) {
        area.innerHTML = '<span style="opacity:.5">暂无数据</span>';
        return;
      }
      const tierColors = { free: "#888", basic: "#2196f3", pro: "#4caf50", business: "#ff9800" };
      const color = tierColors[lic.tier] || "#888";
      const validBadge = lic.valid ? `<span style="color:#4caf50;font-weight:600">✅ 已激活</span>` : lic.has_key ? `<span style="color:#f44336;font-weight:600">❌ 验证失败</span>` : `<span style="color:#888">⚪ 未激活（免费版）</span>`;
      const limitStr = lic.daily_limit === -1 ? "无限制" : `${lic.daily_limit} 次/天`;
      const usedStr = lic.daily_limit === -1 ? `今日已用 ${lic.daily_used} 次` : `今日已用 ${lic.daily_used} / ${lic.daily_limit} 次`;
      const progressPct = lic.daily_limit === -1 ? 0 : Math.min(100, Math.round(lic.daily_used / lic.daily_limit * 100));
      const progressColor = progressPct >= 90 ? "#f44336" : progressPct >= 70 ? "#ff9800" : "#4caf50";
      area.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
        <span style="font-size:18px;font-weight:700;color:${color}">${this._esc(lic.tier_label)}</span>
        ${validBadge}
        ${lic.expires ? `<span style="opacity:.6;font-size:12px">到期：${this._esc(String(lic.expires))}</span>` : ""}
      </div>
      <div style="margin-bottom:6px;color:var(--md-sys-color-on-surface-variant)">${usedStr}（${limitStr}）</div>
      ${lic.daily_limit !== -1 ? `
        <div style="height:6px;background:var(--md-sys-color-surface-container-highest);border-radius:3px;overflow:hidden;margin-bottom:8px">
          <div style="height:100%;width:${progressPct}%;background:${progressColor};border-radius:3px;transition:width .3s"></div>
        </div>` : ""}
      ${!lic.valid && lic.has_key ? `
        <div style="padding:8px 10px;background:#fff3e0;border-radius:8px;font-size:12px;color:#e65100;margin-top:4px">
          ⚠️ License Key 验证失败，系统已降级到免费版限制。请检查 Key 是否正确，或联系开发者。
        </div>` : ""}
      ${!lic.has_key ? `
        <div style="padding:8px 10px;background:var(--md-sys-color-surface-container);border-radius:8px;font-size:12px;color:var(--md-sys-color-outline);margin-top:4px">
          💡 填写 License Key 步骤：<br>
          &nbsp;&nbsp;① 进入 <b>HA 设置 → 设备与服务</b><br>
          &nbsp;&nbsp;② 找到 <b>AI SmartAgent</b> → 点击 <b>⋮ 三点菜单 → 选项</b><br>
          &nbsp;&nbsp;③ 滚动到底部，找到 <b>License Key</b> 字段填入<br>
          &nbsp;&nbsp;④ 点击提交保存，返回此页面点击「重新验证」
        </div>` : ""}
    `;
    },
    _renderPager(container, curPage, totalPages, onPage) {
      if (!container)
        return;
      if (totalPages <= 1) {
        container.innerHTML = "";
        return;
      }
      const start = Math.max(0, curPage - 2);
      const end = Math.min(totalPages - 1, curPage + 2);
      let h = `<button class="pager-btn" ${curPage === 0 ? "disabled" : ""} data-p="${curPage - 1}">‹</button>`;
      if (start > 0)
        h += `<button class="pager-btn" data-p="0">1</button><span class="pager-info">…</span>`;
      for (let i = start; i <= end; i++) {
        h += `<button class="pager-btn ${i === curPage ? "active" : ""}" data-p="${i}">${i + 1}</button>`;
      }
      if (end < totalPages - 1)
        h += `<span class="pager-info">…</span><button class="pager-btn" data-p="${totalPages - 1}">${totalPages}</button>`;
      h += `<button class="pager-btn" ${curPage === totalPages - 1 ? "disabled" : ""} data-p="${curPage + 1}">›</button>`;
      h += `<span class="pager-info">${curPage + 1} / ${totalPages} 页</span>`;
      container.innerHTML = h;
      container.querySelectorAll("[data-p]").forEach(
        (b) => b.onclick = () => onPage(parseInt(b.dataset.p))
      );
    },
    _updateBatchFab() {
      const $ = (id) => this.shadowRoot.getElementById(id);
      const fab = $("batchFab");
      if (!fab)
        return;
      const totalSelected = this._selectedNew.size + this._selectedCfg.size;
      if (totalSelected > 0) {
        fab.classList.add("show");
        $("batchCount").textContent = `已选 ${totalSelected} 项`;
        const hasCfg = this._selectedCfg.size > 0;
        const hasNew = this._selectedNew.size > 0;
        $("batchFabClear").onclick = () => {
          this._selectedNew.clear();
          this._selectedCfg.clear();
          this._renderDevs();
          this._updateBatchFab();
        };
        $("batchFabAi").onclick = () => this._batchUpdateMode("ai");
        $("batchFabHa").onclick = () => this._batchUpdateMode("ha");
        $("batchFabDel").onclick = () => {
          if (this._selectedNew.size > 0)
            this._batchAdd();
          else
            this._batchDelete();
        };
        $("batchFabRoom").onchange = (e) => {
          if (e.target.value)
            this._batchUpdateRoom(e.target.value);
          e.target.value = "";
        };
        $("batchFabAi").style.display = hasCfg ? "block" : "none";
        $("batchFabHa").style.display = hasCfg ? "block" : "none";
        $("batchFabRoom").style.display = hasCfg ? "block" : "none";
        if (hasNew) {
          $("batchFabDel").textContent = "添加选中";
          $("batchFabDel").className = "btn btn-filled btn-sm";
        } else {
          $("batchFabDel").textContent = "停止托管";
          $("batchFabDel").className = "btn btn-error btn-sm";
        }
        const roomSel = $("batchFabRoom");
        if (roomSel) {
          while (roomSel.options.length > 1)
            roomSel.remove(1);
          const cAll = this._wsGet("devices", "devices", []);
          const smRooms = cAll.map((i) => i.room || "").filter((r) => r);
          const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a) => a.name) : [];
          const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort(
            (a, b) => a.localeCompare(b, "zh")
          );
          allRooms.forEach((r) => {
            const opt = document.createElement("option");
            opt.value = r;
            opt.textContent = r;
            roomSel.appendChild(opt);
          });
        }
      } else {
        fab.classList.remove("show");
      }
    },
    async _batchUpdateRoom(room) {
      const ids = Array.from(this._selectedCfg);
      if (!ids.length)
        return;
      const desc = ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
      if (!await this._showConfirm(`确认将选中的 ${desc} 批量移动到「${room}」房间？`))
        return;
      try {
        for (const id of ids) {
          await this._hass.callService("smart_agent", "update_device", { entity_id: id, room });
        }
        this._selectedCfg.clear();
        this._msg("批量房间设置成功");
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e) {
        this._msg("操作失败: " + e.message);
      }
    },
    async _batchUpdateMode(mode) {
      const ids = Array.from(this._selectedCfg);
      if (!ids.length)
        return;
      const labels = { ai: "AI全权", ha: "HA优先", shared: "共享" };
      const desc = ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
      if (!await this._showConfirm(`确认将选中的 ${desc} 批量设为「${labels[mode]}」模式？`))
        return;
      try {
        for (const id of ids) {
          await this._hass.callService("smart_agent", "set_device_control_mode", { entity_id: id, mode });
        }
        this._selectedCfg.clear();
        this._msg(`批量模式设置成功 -> ${labels[mode]}`);
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e) {
        this._msg("操作失败: " + e.message);
      }
    },
    async _batchDelete() {
      const ids = Array.from(this._selectedCfg);
      if (!ids.length)
        return;
      const desc = ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
      if (!await this._showConfirm(`警告：确定停止托管选中的 ${desc} 吗？`))
        return;
      try {
        for (const id of ids) {
          await this._hass.callService("smart_agent", "delete_device", { entity_id: id });
        }
        this._selectedCfg.clear();
        this._msg("批量删除成功");
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e) {
        this._msg("操作失败: " + e.message);
      }
    },
    async _batchAdd() {
      const ids = Array.from(this._selectedNew);
      if (!ids.length)
        return;
      const desc = ids.length === 1 ? `设备「${this._getFriendlyName(ids[0])}」` : `${ids.length} 个设备`;
      if (!await this._showConfirm(`确认批量添加 ${desc} 到 SmartAgent 托管？`))
        return;
      try {
        await this._hass.callService("smart_agent", "batch_add_devices", {
          entities: ids.join(",")
        });
        this._selectedNew.clear();
        this._msg("批量添加成功");
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e) {
        this._msg("添加失败: " + e.message);
      }
    },
    _selAll(s) {
      if (s) {
        const configured = new Set(this._wsGet("devices", "devices", []).map((d) => d.entity_id));
        const activeType = this._newTypeFilter || "all";
        const kw = (this._newSearchKw || "").trim().toLowerCase();
        const showIgnored = this._showIgnored || false;
        const showOffline = this._showOffline || false;
        Object.values(this._hass.states).forEach((st) => {
          var _a, _b;
          const d = st.entity_id.split(".")[0];
          if (!TARGET_DOMAINS.includes(d))
            return;
          if (!showIgnored) {
            if (SKIP_KW.some((k) => st.entity_id.includes(k)))
              return;
            const n2 = ((_a = st.attributes) == null ? void 0 : _a.friendly_name) || "";
            if (SKIP_NAME_KW.some((k) => n2.toLowerCase().includes(k.toLowerCase())))
              return;
          }
          if (configured.has(st.entity_id))
            return;
          const unavail = ["unavailable", "unknown"].includes(st.state);
          if (!showOffline && unavail)
            return;
          if (activeType !== "all" && d !== activeType)
            return;
          const n = ((_b = st.attributes) == null ? void 0 : _b.friendly_name) || "";
          if (kw && !n.toLowerCase().includes(kw) && !st.entity_id.toLowerCase().includes(kw))
            return;
          this._selectedNew.add(st.entity_id);
        });
      } else {
        this._selectedNew.clear();
      }
      this._renderDevs();
    },
    _updateBizStatus() {
      const cfg = this._cfg.attributes || {};
      const badge = this.shadowRoot.getElementById("bizStatusBadge");
      const tip = this.shadowRoot.getElementById("bizStatusTip");
      if (!badge || !tip)
        return;
      const startStr = cfg.showroom_biz_start || "09:00";
      const endStr = cfg.showroom_biz_end || "21:00";
      const now = /* @__PURE__ */ new Date();
      const nowMin = now.getHours() * 60 + now.getMinutes();
      const toMin = (s) => {
        const [h, m] = (s || "").split(":").map(Number);
        return (h || 0) * 60 + (m || 0);
      };
      const startMin = toMin(startStr);
      const endMin = toMin(endStr);
      const isOpen = nowMin >= startMin && nowMin < endMin;
      if (isOpen) {
        badge.textContent = "🟢 营业中";
        badge.style.background = "#e8f5e9";
        badge.style.color = "#2e7d32";
        tip.textContent = `营业时间 ${startStr}–${endStr}，AI 处于积极展示模式`;
      } else {
        badge.textContent = "🌙 已打烊";
        badge.style.background = "#ede7f6";
        badge.style.color = "#512da8";
        tip.textContent = `营业时间 ${startStr}–${endStr}，AI 进入节能待机模式`;
      }
    },
    // ── 5A-3: 决策气泡通知 ─────────────────────────────────────────────────
    /** 订阅 HA smart_agent_decision_bubble 事件，初始化时调用一次。 */
    _initDecisionBubble() {
      if (this._bubbleUnsub)
        return;
      try {
        this._bubbleUnsub = this._hass.connection.subscribeEvents(
          (evt) => this._showDecisionBubble(evt.data),
          "smart_agent_decision_bubble"
        );
      } catch (e) {
      }
    },
    /** 显示决策气泡通知。 */
    _showDecisionBubble(data) {
      var _a;
      this._dismissDecisionBubble(true);
      const ICO = this._getIcons();
      const scene = this._esc(data.scene || "AI 自动操作");
      const _confRaw = data.confidence != null ? parseInt(data.confidence, 10) : NaN;
      const conf = !isNaN(_confRaw) ? `${_confRaw}%` : "";
      const acts = Array.isArray(data.actions) ? data.actions : [];
      const txnId = data.txn_id != null ? data.txn_id : "";
      const actHtml = acts.length ? `<div class="bubble-actions-list">${acts.map((a) => `· ${this._esc(a)}`).join("<br>")}</div>` : "";
      const el = document.createElement("div");
      el.className = "decision-bubble";
      el.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-icon">${ICO.bolt || "⚡"}</span>
        <span class="bubble-scene">${scene}</span>
        ${conf ? `<span class="bubble-conf">${this._esc(conf)}</span>` : ""}
      </div>
      ${actHtml}
      <div class="bubble-footer">
        ${txnId != null && txnId !== "" ? `<button class="bubble-btn bubble-undo" data-txn="${this._esc(String(txnId))}">撤销</button>` : ""}
        <button class="bubble-btn bubble-dismiss">关闭</button>
      </div>`;
      this.shadowRoot.appendChild(el);
      this._bubbleEl = el;
      (_a = el.querySelector(".bubble-dismiss")) == null ? void 0 : _a.addEventListener("click", () => this._dismissDecisionBubble());
      const undoBtn = el.querySelector(".bubble-undo");
      if (undoBtn) {
        undoBtn.addEventListener("click", async () => {
          const txn = undoBtn.dataset.txn;
          if (txn) {
            try {
              await this._hass.callService("smart_agent", "rollback_transaction", { transaction_id: Number(txn) });
            } catch (err) {
              console.warn("[SmartAgent] 撤销失败:", err);
            }
          }
          this._dismissDecisionBubble();
        });
      }
      this._bubbleTimer = setTimeout(() => this._dismissDecisionBubble(), 8e3);
    },
    // ── 5B-2: 确认气泡（need_confirm=true 时用户手动确认执行）─────────────────
    /** 订阅 smart_agent_confirm_required 事件。 */
    _initConfirmBubble() {
      if (this._confirmUnsub)
        return;
      try {
        this._confirmUnsub = this._hass.connection.subscribeEvents(
          (evt) => this._showConfirmBubble(evt.data),
          "smart_agent_confirm_required"
        );
      } catch (e) {
      }
    },
    /** 显示确认气泡（AI 不确定，请用户二次确认后再通过 one_off_prompt 重新触发）。 */
    _showConfirmBubble(data) {
      var _a;
      this._dismissConfirmBubble(true);
      const ICO = this._getIcons();
      const scene = this._esc(data.scene || "AI 推理结果");
      const intentLabel = this._esc(data.intent_label || data.intent || "");
      const _confRaw2 = data.confidence != null ? parseInt(data.confidence, 10) : NaN;
      const conf = !isNaN(_confRaw2) ? `${_confRaw2}%` : "";
      const reply = this._esc((data.reply || "").substring(0, 80));
      const acts = Array.isArray(data.actions) ? data.actions : [];
      const actCount = Number(data.action_count ?? acts.length) || 0;
      const actHtml = acts.length ? `<div class="bubble-actions-list" style="font-size:11px;opacity:.75">${acts.map((a) => `· ${this._esc(String(a))}`).join("<br>")}</div>` : "";
      const el = document.createElement("div");
      el.className = "decision-bubble confirm-bubble";
      el.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-icon">${ICO.help || "❓"}</span>
        <span class="bubble-scene">${scene}</span>
        ${conf ? `<span class="bubble-conf" style="background:rgba(234,108,31,.15);color:#e06c1f">${this._esc(conf)}</span>` : ""}
      </div>
      ${intentLabel ? `<div class="bubble-actions-list" style="color:var(--sa-text)">意图: ${intentLabel}</div>` : ""}
      ${reply ? `<div class="bubble-actions-list" style="font-style:italic;opacity:.8">"${reply}"</div>` : ""}
      ${actHtml}
      <div class="bubble-actions-list" style="color:var(--sa-text-variant)">
        ${actCount ? `${actCount} 个动作待执行，` : ""}请确认后 AI 将重新执行此决策
      </div>
      <div class="bubble-footer">
        <button class="bubble-btn bubble-confirm-ok">确认执行</button>
        <button class="bubble-btn bubble-dismiss">取消</button>
      </div>`;
      this.shadowRoot.appendChild(el);
      this._confirmEl = el;
      (_a = el.querySelector(".bubble-dismiss")) == null ? void 0 : _a.addEventListener("click", () => this._dismissConfirmBubble());
      const okBtn = el.querySelector(".bubble-confirm-ok");
      if (okBtn) {
        okBtn.addEventListener("click", async () => {
          this._dismissConfirmBubble();
          try {
            await this._hass.callService("smart_agent", "process_command", {
              text: `[用户确认] ${data.intent_label || data.scene || "执行AI推理"}`
            });
          } catch (err) {
            console.warn("[SmartAgent] 确认执行失败:", err);
          }
        });
      }
      this._confirmTimer = setTimeout(() => this._dismissConfirmBubble(), 2e4);
    },
    /** 移除确认气泡。 */
    _dismissConfirmBubble(silent = false) {
      if (this._confirmTimer) {
        clearTimeout(this._confirmTimer);
        this._confirmTimer = null;
      }
      if (this._confirmEl) {
        if (!silent) {
          this._confirmEl.classList.add("bubble-out");
          setTimeout(() => {
            var _a;
            return (_a = this._confirmEl) == null ? void 0 : _a.remove();
          }, 350);
        } else {
          this._confirmEl.remove();
        }
        this._confirmEl = null;
      }
    },
    /** 移除决策气泡。 */
    _dismissDecisionBubble(silent = false) {
      if (this._bubbleTimer) {
        clearTimeout(this._bubbleTimer);
        this._bubbleTimer = null;
      }
      if (this._bubbleEl) {
        if (!silent) {
          this._bubbleEl.classList.add("bubble-out");
          setTimeout(() => {
            var _a;
            return (_a = this._bubbleEl) == null ? void 0 : _a.remove();
          }, 350);
        } else {
          this._bubbleEl.remove();
        }
        this._bubbleEl = null;
      }
    },
    _applyBrand(brand = {}) {
      const cfg = Object.assign({}, this._cfg ? this._cfg.attributes : {}, brand);
      const name = cfg.brand_name || "SmartAgent";
      const color = cfg.brand_primary_color || "#6750A4";
      const logo = cfg.brand_logo_url || "";
      const deploy = cfg.deploy_name ? ` · ${cfg.deploy_name}` : "";
      this.style.setProperty("--sa-primary", color);
      this.style.setProperty("--sa-on-primary-container", color);
      this.style.setProperty("--sa-on-primary", "#ffffff");
      const h1 = this.shadowRoot.querySelector(".app-bar h1");
      if (h1) {
        const ICO = this._getIcons();
        const logoHtml = logo ? `<img src="${this._esc(logo)}" style="width:28px;height:28px;border-radius:6px;object-fit:cover;margin-right:2px">` : `<span style="color:var(--sa-primary);display:flex;align-items:center">${ICO.bolt}</span>`;
        h1.innerHTML = `${logoHtml} ${this._esc(name)}${this._esc(deploy)}`;
      }
      const ver = this.shadowRoot.querySelector(".version");
      if (ver)
        ver.textContent = `${name}${deploy} — Material Design 3 Edition`;
      const preview = this.shadowRoot.getElementById("brandLogoPreview");
      if (preview) {
        const ICO = this._getIcons();
        preview.innerHTML = logo ? `<img src="${this._esc(logo)}" style="width:100%;height:100%;object-fit:cover">` : `<span style="font-size:24px">${ICO.bolt}</span>`;
      }
    }
  };

  // src/index.js
  var SmartAgentPanel = class extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._tab = "dashboard";
      this._selectedNew = /* @__PURE__ */ new Set();
      this._selectedCfg = /* @__PURE__ */ new Set();
      this._init = false;
      this._editingSceneKey = null;
      this._sysLogMode = "live";
      this._sysLogFilter = "all";
      this._sysLogKeyword = "";
      this._habSearch = "";
      this._habDomainFilter = "all";
      this._habSort = "conf";
      this._habGrouped = true;
      this._wsData = {};
      this._wsLoading = {};
    }
    set hass(hass) {
      this._hass = hass;
      if (!this._init) {
        this._render();
        this._init = true;
        this._initDecisionBubble();
        this._initConfirmBubble();
      }
      this._update();
    }
    /* ── Getters ── */
    _get(match) {
      var _a;
      return Object.values(((_a = this._hass) == null ? void 0 : _a.states) || {}).find(match) || {};
    }
    get _cfg() {
      var _a;
      return ((_a = this._hass) == null ? void 0 : _a.states["sensor.smart_agent_config"]) || this._get((s) => {
        var _a2;
        return ((_a2 = s.attributes) == null ? void 0 : _a2.device_count) !== void 0;
      });
    }
    get _sts() {
      var _a;
      return ((_a = this._hass) == null ? void 0 : _a.states["sensor.smart_agent_status"]) || this._get((s) => {
        var _a2;
        return ((_a2 = s.attributes) == null ? void 0 : _a2.full_text) !== void 0;
      });
    }
    get _sw() {
      var _a;
      return ((_a = this._hass) == null ? void 0 : _a.states["switch.smart_agent_paused"]) || {};
    }
    get _eng() {
      var _a;
      return ((_a = this._hass) == null ? void 0 : _a.states["select.smart_agent_engine"]) || {};
    }
    get _numA() {
      var _a;
      return ((_a = this._hass) == null ? void 0 : _a.states["number.smart_agent_confidence_auto"]) || {};
    }
    get _numN() {
      var _a;
      return ((_a = this._hass) == null ? void 0 : _a.states["number.smart_agent_confidence_notify"]) || {};
    }
    /** 图标访问器（各模块通过 this._getIcons() 调用） */
    _getIcons() {
      return getIcons();
    }
  };
  Object.assign(
    SmartAgentPanel.prototype,
    // 工具层（最先混入，其他模块方法可能依赖）
    helperMethods,
    // 核心层
    coreMethods,
    // 状态同步
    updateMethods,
    // 主模板
    renderMethods,
    // 渲染层（各 tab）
    configMethods,
    devicesMethods,
    syslogMethods,
    habitsMethods,
    aiscenesMethods,
    correctionsMethods,
    transactionsMethods,
    energyMethods,
    profilesMethods,
    roomsMethods,
    backupMethods,
    patrolMethods,
    mcpMethods,
    licenseMethods
  );
  customElements.define("smart-agent-panel", SmartAgentPanel);
})();
