var _SmartAgentPanel = (() => {
  // custom_components/smart_agent/frontend/src/icons.js
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

  // custom_components/smart_agent/frontend/node_modules/tslib/tslib.es6.mjs
  function __decorate(decorators, target, key, desc) {
    var c5 = arguments.length, r9 = c5 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d3;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function")
      r9 = Reflect.decorate(decorators, target, key, desc);
    else
      for (var i8 = decorators.length - 1; i8 >= 0; i8--)
        if (d3 = decorators[i8])
          r9 = (c5 < 3 ? d3(r9) : c5 > 3 ? d3(target, key, r9) : d3(target, key)) || r9;
    return c5 > 3 && r9 && Object.defineProperty(target, key, r9), r9;
  }

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/custom-element.js
  var t = (t6) => (e9, o10) => {
    void 0 !== o10 ? o10.addInitializer(() => {
      customElements.define(t6, e9);
    }) : customElements.define(t6, e9);
  };

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/css-tag.js
  var t2 = globalThis;
  var e = t2.ShadowRoot && (void 0 === t2.ShadyCSS || t2.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
  var s = Symbol();
  var o = /* @__PURE__ */ new WeakMap();
  var n = class {
    constructor(t6, e9, o10) {
      if (this._$cssResult$ = true, o10 !== s)
        throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
      this.cssText = t6, this.t = e9;
    }
    get styleSheet() {
      let t6 = this.o;
      const s4 = this.t;
      if (e && void 0 === t6) {
        const e9 = void 0 !== s4 && 1 === s4.length;
        e9 && (t6 = o.get(s4)), void 0 === t6 && ((this.o = t6 = new CSSStyleSheet()).replaceSync(this.cssText), e9 && o.set(s4, t6));
      }
      return t6;
    }
    toString() {
      return this.cssText;
    }
  };
  var r = (t6) => new n("string" == typeof t6 ? t6 : t6 + "", void 0, s);
  var i = (t6, ...e9) => {
    const o10 = 1 === t6.length ? t6[0] : e9.reduce((e10, s4, o11) => e10 + ((t7) => {
      if (true === t7._$cssResult$)
        return t7.cssText;
      if ("number" == typeof t7)
        return t7;
      throw Error("Value passed to 'css' function must be a 'css' function result: " + t7 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
    })(s4) + t6[o11 + 1], t6[0]);
    return new n(o10, t6, s);
  };
  var S = (s4, o10) => {
    if (e)
      s4.adoptedStyleSheets = o10.map((t6) => t6 instanceof CSSStyleSheet ? t6 : t6.styleSheet);
    else
      for (const e9 of o10) {
        const o11 = document.createElement("style"), n9 = t2.litNonce;
        void 0 !== n9 && o11.setAttribute("nonce", n9), o11.textContent = e9.cssText, s4.appendChild(o11);
      }
  };
  var c = e ? (t6) => t6 : (t6) => t6 instanceof CSSStyleSheet ? ((t7) => {
    let e9 = "";
    for (const s4 of t7.cssRules)
      e9 += s4.cssText;
    return r(e9);
  })(t6) : t6;

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/reactive-element.js
  var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
  var a = globalThis;
  var c2 = a.trustedTypes;
  var l = c2 ? c2.emptyScript : "";
  var p = a.reactiveElementPolyfillSupport;
  var d = (t6, s4) => t6;
  var u = { toAttribute(t6, s4) {
    switch (s4) {
      case Boolean:
        t6 = t6 ? l : null;
        break;
      case Object:
      case Array:
        t6 = null == t6 ? t6 : JSON.stringify(t6);
    }
    return t6;
  }, fromAttribute(t6, s4) {
    let i8 = t6;
    switch (s4) {
      case Boolean:
        i8 = null !== t6;
        break;
      case Number:
        i8 = null === t6 ? null : Number(t6);
        break;
      case Object:
      case Array:
        try {
          i8 = JSON.parse(t6);
        } catch (t7) {
          i8 = null;
        }
    }
    return i8;
  } };
  var f = (t6, s4) => !i2(t6, s4);
  var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
  Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), a.litPropertyMetadata ?? (a.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
  var y = class extends HTMLElement {
    static addInitializer(t6) {
      this._$Ei(), (this.l ?? (this.l = [])).push(t6);
    }
    static get observedAttributes() {
      return this.finalize(), this._$Eh && [...this._$Eh.keys()];
    }
    static createProperty(t6, s4 = b) {
      if (s4.state && (s4.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t6) && ((s4 = Object.create(s4)).wrapped = true), this.elementProperties.set(t6, s4), !s4.noAccessor) {
        const i8 = Symbol(), h3 = this.getPropertyDescriptor(t6, i8, s4);
        void 0 !== h3 && e2(this.prototype, t6, h3);
      }
    }
    static getPropertyDescriptor(t6, s4, i8) {
      const { get: e9, set: r9 } = h(this.prototype, t6) ?? { get() {
        return this[s4];
      }, set(t7) {
        this[s4] = t7;
      } };
      return { get: e9, set(s5) {
        const h3 = e9 == null ? void 0 : e9.call(this);
        r9 == null ? void 0 : r9.call(this, s5), this.requestUpdate(t6, h3, i8);
      }, configurable: true, enumerable: true };
    }
    static getPropertyOptions(t6) {
      return this.elementProperties.get(t6) ?? b;
    }
    static _$Ei() {
      if (this.hasOwnProperty(d("elementProperties")))
        return;
      const t6 = n2(this);
      t6.finalize(), void 0 !== t6.l && (this.l = [...t6.l]), this.elementProperties = new Map(t6.elementProperties);
    }
    static finalize() {
      if (this.hasOwnProperty(d("finalized")))
        return;
      if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
        const t7 = this.properties, s4 = [...r2(t7), ...o2(t7)];
        for (const i8 of s4)
          this.createProperty(i8, t7[i8]);
      }
      const t6 = this[Symbol.metadata];
      if (null !== t6) {
        const s4 = litPropertyMetadata.get(t6);
        if (void 0 !== s4)
          for (const [t7, i8] of s4)
            this.elementProperties.set(t7, i8);
      }
      this._$Eh = /* @__PURE__ */ new Map();
      for (const [t7, s4] of this.elementProperties) {
        const i8 = this._$Eu(t7, s4);
        void 0 !== i8 && this._$Eh.set(i8, t7);
      }
      this.elementStyles = this.finalizeStyles(this.styles);
    }
    static finalizeStyles(s4) {
      const i8 = [];
      if (Array.isArray(s4)) {
        const e9 = new Set(s4.flat(1 / 0).reverse());
        for (const s5 of e9)
          i8.unshift(c(s5));
      } else
        void 0 !== s4 && i8.push(c(s4));
      return i8;
    }
    static _$Eu(t6, s4) {
      const i8 = s4.attribute;
      return false === i8 ? void 0 : "string" == typeof i8 ? i8 : "string" == typeof t6 ? t6.toLowerCase() : void 0;
    }
    constructor() {
      super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
    }
    _$Ev() {
      var _a3;
      this._$ES = new Promise((t6) => this.enableUpdating = t6), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (_a3 = this.constructor.l) == null ? void 0 : _a3.forEach((t6) => t6(this));
    }
    addController(t6) {
      var _a3;
      (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(t6), void 0 !== this.renderRoot && this.isConnected && ((_a3 = t6.hostConnected) == null ? void 0 : _a3.call(t6));
    }
    removeController(t6) {
      var _a3;
      (_a3 = this._$EO) == null ? void 0 : _a3.delete(t6);
    }
    _$E_() {
      const t6 = /* @__PURE__ */ new Map(), s4 = this.constructor.elementProperties;
      for (const i8 of s4.keys())
        this.hasOwnProperty(i8) && (t6.set(i8, this[i8]), delete this[i8]);
      t6.size > 0 && (this._$Ep = t6);
    }
    createRenderRoot() {
      const t6 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
      return S(t6, this.constructor.elementStyles), t6;
    }
    connectedCallback() {
      var _a3;
      this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(true), (_a3 = this._$EO) == null ? void 0 : _a3.forEach((t6) => {
        var _a4;
        return (_a4 = t6.hostConnected) == null ? void 0 : _a4.call(t6);
      });
    }
    enableUpdating(t6) {
    }
    disconnectedCallback() {
      var _a3;
      (_a3 = this._$EO) == null ? void 0 : _a3.forEach((t6) => {
        var _a4;
        return (_a4 = t6.hostDisconnected) == null ? void 0 : _a4.call(t6);
      });
    }
    attributeChangedCallback(t6, s4, i8) {
      this._$AK(t6, i8);
    }
    _$ET(t6, s4) {
      var _a3;
      const i8 = this.constructor.elementProperties.get(t6), e9 = this.constructor._$Eu(t6, i8);
      if (void 0 !== e9 && true === i8.reflect) {
        const h3 = (void 0 !== ((_a3 = i8.converter) == null ? void 0 : _a3.toAttribute) ? i8.converter : u).toAttribute(s4, i8.type);
        this._$Em = t6, null == h3 ? this.removeAttribute(e9) : this.setAttribute(e9, h3), this._$Em = null;
      }
    }
    _$AK(t6, s4) {
      var _a3, _b;
      const i8 = this.constructor, e9 = i8._$Eh.get(t6);
      if (void 0 !== e9 && this._$Em !== e9) {
        const t7 = i8.getPropertyOptions(e9), h3 = "function" == typeof t7.converter ? { fromAttribute: t7.converter } : void 0 !== ((_a3 = t7.converter) == null ? void 0 : _a3.fromAttribute) ? t7.converter : u;
        this._$Em = e9;
        const r9 = h3.fromAttribute(s4, t7.type);
        this[e9] = r9 ?? ((_b = this._$Ej) == null ? void 0 : _b.get(e9)) ?? r9, this._$Em = null;
      }
    }
    requestUpdate(t6, s4, i8, e9 = false, h3) {
      var _a3;
      if (void 0 !== t6) {
        const r9 = this.constructor;
        if (false === e9 && (h3 = this[t6]), i8 ?? (i8 = r9.getPropertyOptions(t6)), !((i8.hasChanged ?? f)(h3, s4) || i8.useDefault && i8.reflect && h3 === ((_a3 = this._$Ej) == null ? void 0 : _a3.get(t6)) && !this.hasAttribute(r9._$Eu(t6, i8))))
          return;
        this.C(t6, s4, i8);
      }
      false === this.isUpdatePending && (this._$ES = this._$EP());
    }
    C(t6, s4, { useDefault: i8, reflect: e9, wrapped: h3 }, r9) {
      i8 && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(t6) && (this._$Ej.set(t6, r9 ?? s4 ?? this[t6]), true !== h3 || void 0 !== r9) || (this._$AL.has(t6) || (this.hasUpdated || i8 || (s4 = void 0), this._$AL.set(t6, s4)), true === e9 && this._$Em !== t6 && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(t6));
    }
    async _$EP() {
      this.isUpdatePending = true;
      try {
        await this._$ES;
      } catch (t7) {
        Promise.reject(t7);
      }
      const t6 = this.scheduleUpdate();
      return null != t6 && await t6, !this.isUpdatePending;
    }
    scheduleUpdate() {
      return this.performUpdate();
    }
    performUpdate() {
      var _a3;
      if (!this.isUpdatePending)
        return;
      if (!this.hasUpdated) {
        if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
          for (const [t8, s5] of this._$Ep)
            this[t8] = s5;
          this._$Ep = void 0;
        }
        const t7 = this.constructor.elementProperties;
        if (t7.size > 0)
          for (const [s5, i8] of t7) {
            const { wrapped: t8 } = i8, e9 = this[s5];
            true !== t8 || this._$AL.has(s5) || void 0 === e9 || this.C(s5, void 0, i8, e9);
          }
      }
      let t6 = false;
      const s4 = this._$AL;
      try {
        t6 = this.shouldUpdate(s4), t6 ? (this.willUpdate(s4), (_a3 = this._$EO) == null ? void 0 : _a3.forEach((t7) => {
          var _a4;
          return (_a4 = t7.hostUpdate) == null ? void 0 : _a4.call(t7);
        }), this.update(s4)) : this._$EM();
      } catch (s5) {
        throw t6 = false, this._$EM(), s5;
      }
      t6 && this._$AE(s4);
    }
    willUpdate(t6) {
    }
    _$AE(t6) {
      var _a3;
      (_a3 = this._$EO) == null ? void 0 : _a3.forEach((t7) => {
        var _a4;
        return (_a4 = t7.hostUpdated) == null ? void 0 : _a4.call(t7);
      }), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t6)), this.updated(t6);
    }
    _$EM() {
      this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
    }
    get updateComplete() {
      return this.getUpdateComplete();
    }
    getUpdateComplete() {
      return this._$ES;
    }
    shouldUpdate(t6) {
      return true;
    }
    update(t6) {
      this._$Eq && (this._$Eq = this._$Eq.forEach((t7) => this._$ET(t7, this[t7]))), this._$EM();
    }
    updated(t6) {
    }
    firstUpdated(t6) {
    }
  };
  y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = /* @__PURE__ */ new Map(), y[d("finalized")] = /* @__PURE__ */ new Map(), p == null ? void 0 : p({ ReactiveElement: y }), (a.reactiveElementVersions ?? (a.reactiveElementVersions = [])).push("2.1.2");

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/property.js
  var o3 = { attribute: true, type: String, converter: u, reflect: false, hasChanged: f };
  var r3 = (t6 = o3, e9, r9) => {
    const { kind: n9, metadata: i8 } = r9;
    let s4 = globalThis.litPropertyMetadata.get(i8);
    if (void 0 === s4 && globalThis.litPropertyMetadata.set(i8, s4 = /* @__PURE__ */ new Map()), "setter" === n9 && ((t6 = Object.create(t6)).wrapped = true), s4.set(r9.name, t6), "accessor" === n9) {
      const { name: o10 } = r9;
      return { set(r10) {
        const n10 = e9.get.call(this);
        e9.set.call(this, r10), this.requestUpdate(o10, n10, t6, true, r10);
      }, init(e10) {
        return void 0 !== e10 && this.C(o10, void 0, t6, e10), e10;
      } };
    }
    if ("setter" === n9) {
      const { name: o10 } = r9;
      return function(r10) {
        const n10 = this[o10];
        e9.call(this, r10), this.requestUpdate(o10, n10, t6, true, r10);
      };
    }
    throw Error("Unsupported decorator location: " + n9);
  };
  function n3(t6) {
    return (e9, o10) => "object" == typeof o10 ? r3(t6, e9, o10) : ((t7, e10, o11) => {
      const r9 = e10.hasOwnProperty(o11);
      return e10.constructor.createProperty(o11, t7), r9 ? Object.getOwnPropertyDescriptor(e10, o11) : void 0;
    })(t6, e9, o10);
  }

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/state.js
  function r4(r9) {
    return n3({ ...r9, state: true, attribute: false });
  }

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/base.js
  var e3 = (e9, t6, c5) => (c5.configurable = true, c5.enumerable = true, Reflect.decorate && "object" != typeof t6 && Object.defineProperty(e9, t6, c5), c5);

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/query.js
  function e4(e9, r9) {
    return (n9, s4, i8) => {
      const o10 = (t6) => {
        var _a3;
        return ((_a3 = t6.renderRoot) == null ? void 0 : _a3.querySelector(e9)) ?? null;
      };
      if (r9) {
        const { get: e10, set: r10 } = "object" == typeof s4 ? n9 : i8 ?? (() => {
          const t6 = Symbol();
          return { get() {
            return this[t6];
          }, set(e11) {
            this[t6] = e11;
          } };
        })();
        return e3(n9, s4, { get() {
          let t6 = e10.call(this);
          return void 0 === t6 && (t6 = o10(this), (null !== t6 || this.hasUpdated) && r10.call(this, t6)), t6;
        } });
      }
      return e3(n9, s4, { get() {
        return o10(this);
      } });
    };
  }

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/query-all.js
  var e5;
  function r5(r9) {
    return (n9, o10) => e3(n9, o10, { get() {
      return (this.renderRoot ?? (e5 ?? (e5 = document.createDocumentFragment()))).querySelectorAll(r9);
    } });
  }

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/query-async.js
  function r6(r9) {
    return (n9, e9) => e3(n9, e9, { async get() {
      var _a3;
      return await this.updateComplete, ((_a3 = this.renderRoot) == null ? void 0 : _a3.querySelector(r9)) ?? null;
    } });
  }

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/query-assigned-elements.js
  function o4(o10) {
    return (e9, n9) => {
      const { slot: r9, selector: s4 } = o10 ?? {}, c5 = "slot" + (r9 ? `[name=${r9}]` : ":not([name])");
      return e3(e9, n9, { get() {
        var _a3;
        const t6 = (_a3 = this.renderRoot) == null ? void 0 : _a3.querySelector(c5), e10 = (t6 == null ? void 0 : t6.assignedElements(o10)) ?? [];
        return void 0 === s4 ? e10 : e10.filter((t7) => t7.matches(s4));
      } });
    };
  }

  // custom_components/smart_agent/frontend/node_modules/@lit/reactive-element/decorators/query-assigned-nodes.js
  function n4(n9) {
    return (o10, r9) => {
      const { slot: e9 } = n9 ?? {}, s4 = "slot" + (e9 ? `[name=${e9}]` : ":not([name])");
      return e3(o10, r9, { get() {
        var _a3;
        const t6 = (_a3 = this.renderRoot) == null ? void 0 : _a3.querySelector(s4);
        return (t6 == null ? void 0 : t6.assignedNodes(n9)) ?? [];
      } });
    };
  }

  // custom_components/smart_agent/frontend/node_modules/lit-html/lit-html.js
  var t3 = globalThis;
  var i3 = (t6) => t6;
  var s2 = t3.trustedTypes;
  var e6 = s2 ? s2.createPolicy("lit-html", { createHTML: (t6) => t6 }) : void 0;
  var h2 = "$lit$";
  var o5 = `lit$${Math.random().toFixed(9).slice(2)}$`;
  var n5 = "?" + o5;
  var r7 = `<${n5}>`;
  var l2 = document;
  var c3 = () => l2.createComment("");
  var a2 = (t6) => null === t6 || "object" != typeof t6 && "function" != typeof t6;
  var u2 = Array.isArray;
  var d2 = (t6) => u2(t6) || "function" == typeof (t6 == null ? void 0 : t6[Symbol.iterator]);
  var f2 = "[ 	\n\f\r]";
  var v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
  var _ = /-->/g;
  var m = />/g;
  var p2 = RegExp(`>|${f2}(?:([^\\s"'>=/]+)(${f2}*=${f2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
  var g = /'/g;
  var $ = /"/g;
  var y2 = /^(?:script|style|textarea|title)$/i;
  var x = (t6) => (i8, ...s4) => ({ _$litType$: t6, strings: i8, values: s4 });
  var b2 = x(1);
  var w = x(2);
  var T = x(3);
  var E = Symbol.for("lit-noChange");
  var A = Symbol.for("lit-nothing");
  var C = /* @__PURE__ */ new WeakMap();
  var P = l2.createTreeWalker(l2, 129);
  function V(t6, i8) {
    if (!u2(t6) || !t6.hasOwnProperty("raw"))
      throw Error("invalid template strings array");
    return void 0 !== e6 ? e6.createHTML(i8) : i8;
  }
  var N = (t6, i8) => {
    const s4 = t6.length - 1, e9 = [];
    let n9, l5 = 2 === i8 ? "<svg>" : 3 === i8 ? "<math>" : "", c5 = v;
    for (let i9 = 0; i9 < s4; i9++) {
      const s5 = t6[i9];
      let a4, u4, d3 = -1, f3 = 0;
      for (; f3 < s5.length && (c5.lastIndex = f3, u4 = c5.exec(s5), null !== u4); )
        f3 = c5.lastIndex, c5 === v ? "!--" === u4[1] ? c5 = _ : void 0 !== u4[1] ? c5 = m : void 0 !== u4[2] ? (y2.test(u4[2]) && (n9 = RegExp("</" + u4[2], "g")), c5 = p2) : void 0 !== u4[3] && (c5 = p2) : c5 === p2 ? ">" === u4[0] ? (c5 = n9 ?? v, d3 = -1) : void 0 === u4[1] ? d3 = -2 : (d3 = c5.lastIndex - u4[2].length, a4 = u4[1], c5 = void 0 === u4[3] ? p2 : '"' === u4[3] ? $ : g) : c5 === $ || c5 === g ? c5 = p2 : c5 === _ || c5 === m ? c5 = v : (c5 = p2, n9 = void 0);
      const x2 = c5 === p2 && t6[i9 + 1].startsWith("/>") ? " " : "";
      l5 += c5 === v ? s5 + r7 : d3 >= 0 ? (e9.push(a4), s5.slice(0, d3) + h2 + s5.slice(d3) + o5 + x2) : s5 + o5 + (-2 === d3 ? i9 : x2);
    }
    return [V(t6, l5 + (t6[s4] || "<?>") + (2 === i8 ? "</svg>" : 3 === i8 ? "</math>" : "")), e9];
  };
  var S2 = class _S {
    constructor({ strings: t6, _$litType$: i8 }, e9) {
      let r9;
      this.parts = [];
      let l5 = 0, a4 = 0;
      const u4 = t6.length - 1, d3 = this.parts, [f3, v2] = N(t6, i8);
      if (this.el = _S.createElement(f3, e9), P.currentNode = this.el.content, 2 === i8 || 3 === i8) {
        const t7 = this.el.content.firstChild;
        t7.replaceWith(...t7.childNodes);
      }
      for (; null !== (r9 = P.nextNode()) && d3.length < u4; ) {
        if (1 === r9.nodeType) {
          if (r9.hasAttributes())
            for (const t7 of r9.getAttributeNames())
              if (t7.endsWith(h2)) {
                const i9 = v2[a4++], s4 = r9.getAttribute(t7).split(o5), e10 = /([.?@])?(.*)/.exec(i9);
                d3.push({ type: 1, index: l5, name: e10[2], strings: s4, ctor: "." === e10[1] ? I : "?" === e10[1] ? L : "@" === e10[1] ? z : H }), r9.removeAttribute(t7);
              } else
                t7.startsWith(o5) && (d3.push({ type: 6, index: l5 }), r9.removeAttribute(t7));
          if (y2.test(r9.tagName)) {
            const t7 = r9.textContent.split(o5), i9 = t7.length - 1;
            if (i9 > 0) {
              r9.textContent = s2 ? s2.emptyScript : "";
              for (let s4 = 0; s4 < i9; s4++)
                r9.append(t7[s4], c3()), P.nextNode(), d3.push({ type: 2, index: ++l5 });
              r9.append(t7[i9], c3());
            }
          }
        } else if (8 === r9.nodeType)
          if (r9.data === n5)
            d3.push({ type: 2, index: l5 });
          else {
            let t7 = -1;
            for (; -1 !== (t7 = r9.data.indexOf(o5, t7 + 1)); )
              d3.push({ type: 7, index: l5 }), t7 += o5.length - 1;
          }
        l5++;
      }
    }
    static createElement(t6, i8) {
      const s4 = l2.createElement("template");
      return s4.innerHTML = t6, s4;
    }
  };
  function M(t6, i8, s4 = t6, e9) {
    var _a3, _b;
    if (i8 === E)
      return i8;
    let h3 = void 0 !== e9 ? (_a3 = s4._$Co) == null ? void 0 : _a3[e9] : s4._$Cl;
    const o10 = a2(i8) ? void 0 : i8._$litDirective$;
    return (h3 == null ? void 0 : h3.constructor) !== o10 && ((_b = h3 == null ? void 0 : h3._$AO) == null ? void 0 : _b.call(h3, false), void 0 === o10 ? h3 = void 0 : (h3 = new o10(t6), h3._$AT(t6, s4, e9)), void 0 !== e9 ? (s4._$Co ?? (s4._$Co = []))[e9] = h3 : s4._$Cl = h3), void 0 !== h3 && (i8 = M(t6, h3._$AS(t6, i8.values), h3, e9)), i8;
  }
  var R = class {
    constructor(t6, i8) {
      this._$AV = [], this._$AN = void 0, this._$AD = t6, this._$AM = i8;
    }
    get parentNode() {
      return this._$AM.parentNode;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    u(t6) {
      const { el: { content: i8 }, parts: s4 } = this._$AD, e9 = ((t6 == null ? void 0 : t6.creationScope) ?? l2).importNode(i8, true);
      P.currentNode = e9;
      let h3 = P.nextNode(), o10 = 0, n9 = 0, r9 = s4[0];
      for (; void 0 !== r9; ) {
        if (o10 === r9.index) {
          let i9;
          2 === r9.type ? i9 = new k(h3, h3.nextSibling, this, t6) : 1 === r9.type ? i9 = new r9.ctor(h3, r9.name, r9.strings, this, t6) : 6 === r9.type && (i9 = new Z(h3, this, t6)), this._$AV.push(i9), r9 = s4[++n9];
        }
        o10 !== (r9 == null ? void 0 : r9.index) && (h3 = P.nextNode(), o10++);
      }
      return P.currentNode = l2, e9;
    }
    p(t6) {
      let i8 = 0;
      for (const s4 of this._$AV)
        void 0 !== s4 && (void 0 !== s4.strings ? (s4._$AI(t6, s4, i8), i8 += s4.strings.length - 2) : s4._$AI(t6[i8])), i8++;
    }
  };
  var k = class _k {
    get _$AU() {
      var _a3;
      return ((_a3 = this._$AM) == null ? void 0 : _a3._$AU) ?? this._$Cv;
    }
    constructor(t6, i8, s4, e9) {
      this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t6, this._$AB = i8, this._$AM = s4, this.options = e9, this._$Cv = (e9 == null ? void 0 : e9.isConnected) ?? true;
    }
    get parentNode() {
      let t6 = this._$AA.parentNode;
      const i8 = this._$AM;
      return void 0 !== i8 && 11 === (t6 == null ? void 0 : t6.nodeType) && (t6 = i8.parentNode), t6;
    }
    get startNode() {
      return this._$AA;
    }
    get endNode() {
      return this._$AB;
    }
    _$AI(t6, i8 = this) {
      t6 = M(this, t6, i8), a2(t6) ? t6 === A || null == t6 || "" === t6 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t6 !== this._$AH && t6 !== E && this._(t6) : void 0 !== t6._$litType$ ? this.$(t6) : void 0 !== t6.nodeType ? this.T(t6) : d2(t6) ? this.k(t6) : this._(t6);
    }
    O(t6) {
      return this._$AA.parentNode.insertBefore(t6, this._$AB);
    }
    T(t6) {
      this._$AH !== t6 && (this._$AR(), this._$AH = this.O(t6));
    }
    _(t6) {
      this._$AH !== A && a2(this._$AH) ? this._$AA.nextSibling.data = t6 : this.T(l2.createTextNode(t6)), this._$AH = t6;
    }
    $(t6) {
      var _a3;
      const { values: i8, _$litType$: s4 } = t6, e9 = "number" == typeof s4 ? this._$AC(t6) : (void 0 === s4.el && (s4.el = S2.createElement(V(s4.h, s4.h[0]), this.options)), s4);
      if (((_a3 = this._$AH) == null ? void 0 : _a3._$AD) === e9)
        this._$AH.p(i8);
      else {
        const t7 = new R(e9, this), s5 = t7.u(this.options);
        t7.p(i8), this.T(s5), this._$AH = t7;
      }
    }
    _$AC(t6) {
      let i8 = C.get(t6.strings);
      return void 0 === i8 && C.set(t6.strings, i8 = new S2(t6)), i8;
    }
    k(t6) {
      u2(this._$AH) || (this._$AH = [], this._$AR());
      const i8 = this._$AH;
      let s4, e9 = 0;
      for (const h3 of t6)
        e9 === i8.length ? i8.push(s4 = new _k(this.O(c3()), this.O(c3()), this, this.options)) : s4 = i8[e9], s4._$AI(h3), e9++;
      e9 < i8.length && (this._$AR(s4 && s4._$AB.nextSibling, e9), i8.length = e9);
    }
    _$AR(t6 = this._$AA.nextSibling, s4) {
      var _a3;
      for ((_a3 = this._$AP) == null ? void 0 : _a3.call(this, false, true, s4); t6 !== this._$AB; ) {
        const s5 = i3(t6).nextSibling;
        i3(t6).remove(), t6 = s5;
      }
    }
    setConnected(t6) {
      var _a3;
      void 0 === this._$AM && (this._$Cv = t6, (_a3 = this._$AP) == null ? void 0 : _a3.call(this, t6));
    }
  };
  var H = class {
    get tagName() {
      return this.element.tagName;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    constructor(t6, i8, s4, e9, h3) {
      this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t6, this.name = i8, this._$AM = e9, this.options = h3, s4.length > 2 || "" !== s4[0] || "" !== s4[1] ? (this._$AH = Array(s4.length - 1).fill(new String()), this.strings = s4) : this._$AH = A;
    }
    _$AI(t6, i8 = this, s4, e9) {
      const h3 = this.strings;
      let o10 = false;
      if (void 0 === h3)
        t6 = M(this, t6, i8, 0), o10 = !a2(t6) || t6 !== this._$AH && t6 !== E, o10 && (this._$AH = t6);
      else {
        const e10 = t6;
        let n9, r9;
        for (t6 = h3[0], n9 = 0; n9 < h3.length - 1; n9++)
          r9 = M(this, e10[s4 + n9], i8, n9), r9 === E && (r9 = this._$AH[n9]), o10 || (o10 = !a2(r9) || r9 !== this._$AH[n9]), r9 === A ? t6 = A : t6 !== A && (t6 += (r9 ?? "") + h3[n9 + 1]), this._$AH[n9] = r9;
      }
      o10 && !e9 && this.j(t6);
    }
    j(t6) {
      t6 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t6 ?? "");
    }
  };
  var I = class extends H {
    constructor() {
      super(...arguments), this.type = 3;
    }
    j(t6) {
      this.element[this.name] = t6 === A ? void 0 : t6;
    }
  };
  var L = class extends H {
    constructor() {
      super(...arguments), this.type = 4;
    }
    j(t6) {
      this.element.toggleAttribute(this.name, !!t6 && t6 !== A);
    }
  };
  var z = class extends H {
    constructor(t6, i8, s4, e9, h3) {
      super(t6, i8, s4, e9, h3), this.type = 5;
    }
    _$AI(t6, i8 = this) {
      if ((t6 = M(this, t6, i8, 0) ?? A) === E)
        return;
      const s4 = this._$AH, e9 = t6 === A && s4 !== A || t6.capture !== s4.capture || t6.once !== s4.once || t6.passive !== s4.passive, h3 = t6 !== A && (s4 === A || e9);
      e9 && this.element.removeEventListener(this.name, this, s4), h3 && this.element.addEventListener(this.name, this, t6), this._$AH = t6;
    }
    handleEvent(t6) {
      var _a3;
      "function" == typeof this._$AH ? this._$AH.call(((_a3 = this.options) == null ? void 0 : _a3.host) ?? this.element, t6) : this._$AH.handleEvent(t6);
    }
  };
  var Z = class {
    constructor(t6, i8, s4) {
      this.element = t6, this.type = 6, this._$AN = void 0, this._$AM = i8, this.options = s4;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(t6) {
      M(this, t6);
    }
  };
  var j = { M: h2, P: o5, A: n5, C: 1, L: N, R, D: d2, V: M, I: k, H, N: L, U: z, B: I, F: Z };
  var B = t3.litHtmlPolyfillSupport;
  B == null ? void 0 : B(S2, k), (t3.litHtmlVersions ?? (t3.litHtmlVersions = [])).push("3.3.2");
  var D = (t6, i8, s4) => {
    const e9 = (s4 == null ? void 0 : s4.renderBefore) ?? i8;
    let h3 = e9._$litPart$;
    if (void 0 === h3) {
      const t7 = (s4 == null ? void 0 : s4.renderBefore) ?? null;
      e9._$litPart$ = h3 = new k(i8.insertBefore(c3(), t7), t7, void 0, s4 ?? {});
    }
    return h3._$AI(t6), h3;
  };

  // custom_components/smart_agent/frontend/node_modules/lit-element/lit-element.js
  var s3 = globalThis;
  var i4 = class extends y {
    constructor() {
      super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
    }
    createRenderRoot() {
      var _a3;
      const t6 = super.createRenderRoot();
      return (_a3 = this.renderOptions).renderBefore ?? (_a3.renderBefore = t6.firstChild), t6;
    }
    update(t6) {
      const r9 = this.render();
      this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t6), this._$Do = D(r9, this.renderRoot, this.renderOptions);
    }
    connectedCallback() {
      var _a3;
      super.connectedCallback(), (_a3 = this._$Do) == null ? void 0 : _a3.setConnected(true);
    }
    disconnectedCallback() {
      var _a3;
      super.disconnectedCallback(), (_a3 = this._$Do) == null ? void 0 : _a3.setConnected(false);
    }
    render() {
      return E;
    }
  };
  var _a;
  i4._$litElement$ = true, i4["finalized"] = true, (_a = s3.litElementHydrateSupport) == null ? void 0 : _a.call(s3, { LitElement: i4 });
  var o6 = s3.litElementPolyfillSupport;
  o6 == null ? void 0 : o6({ LitElement: i4 });
  (s3.litElementVersions ?? (s3.litElementVersions = [])).push("4.2.2");

  // custom_components/smart_agent/frontend/node_modules/lit-html/is-server.js
  var o7 = false;

  // custom_components/smart_agent/frontend/node_modules/lit-html/directive.js
  var t4 = { ATTRIBUTE: 1, CHILD: 2, PROPERTY: 3, BOOLEAN_ATTRIBUTE: 4, EVENT: 5, ELEMENT: 6 };
  var e7 = (t6) => (...e9) => ({ _$litDirective$: t6, values: e9 });
  var i5 = class {
    constructor(t6) {
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AT(t6, e9, i8) {
      this._$Ct = t6, this._$AM = e9, this._$Ci = i8;
    }
    _$AS(t6, e9) {
      return this.update(t6, e9);
    }
    update(t6, e9) {
      return this.render(...e9);
    }
  };

  // custom_components/smart_agent/frontend/node_modules/lit-html/directives/class-map.js
  var e8 = e7(class extends i5 {
    constructor(t6) {
      var _a3;
      if (super(t6), t6.type !== t4.ATTRIBUTE || "class" !== t6.name || ((_a3 = t6.strings) == null ? void 0 : _a3.length) > 2)
        throw Error("`classMap()` can only be used in the `class` attribute and must be the only part in the attribute.");
    }
    render(t6) {
      return " " + Object.keys(t6).filter((s4) => t6[s4]).join(" ") + " ";
    }
    update(s4, [i8]) {
      var _a3, _b;
      if (void 0 === this.st) {
        this.st = /* @__PURE__ */ new Set(), void 0 !== s4.strings && (this.nt = new Set(s4.strings.join(" ").split(/\s/).filter((t6) => "" !== t6)));
        for (const t6 in i8)
          i8[t6] && !((_a3 = this.nt) == null ? void 0 : _a3.has(t6)) && this.st.add(t6);
        return this.render(i8);
      }
      const r9 = s4.element.classList;
      for (const t6 of this.st)
        t6 in i8 || (r9.remove(t6), this.st.delete(t6));
      for (const t6 in i8) {
        const s5 = !!i8[t6];
        s5 === this.st.has(t6) || ((_b = this.nt) == null ? void 0 : _b.has(t6)) || (s5 ? (r9.add(t6), this.st.add(t6)) : (r9.remove(t6), this.st.delete(t6)));
      }
      return E;
    }
  });

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/motion/animation.js
  var EASING = {
    STANDARD: "cubic-bezier(0.2, 0, 0, 1)",
    STANDARD_ACCELERATE: "cubic-bezier(.3,0,1,1)",
    STANDARD_DECELERATE: "cubic-bezier(0,0,0,1)",
    EMPHASIZED: "cubic-bezier(.3,0,0,1)",
    EMPHASIZED_ACCELERATE: "cubic-bezier(.3,0,.8,.15)",
    EMPHASIZED_DECELERATE: "cubic-bezier(.05,.7,.1,1)"
  };
  function createAnimationSignal() {
    let animationAbortController = null;
    return {
      start() {
        animationAbortController == null ? void 0 : animationAbortController.abort();
        animationAbortController = new AbortController();
        return animationAbortController.signal;
      },
      finish() {
        animationAbortController = null;
      }
    };
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/field/internal/field.js
  var Field = class extends i4 {
    constructor() {
      super(...arguments);
      this.disabled = false;
      this.error = false;
      this.focused = false;
      this.label = "";
      this.noAsterisk = false;
      this.populated = false;
      this.required = false;
      this.resizable = false;
      this.supportingText = "";
      this.errorText = "";
      this.count = -1;
      this.max = -1;
      this.hasStart = false;
      this.hasEnd = false;
      this.isAnimating = false;
      this.refreshErrorAlert = false;
      this.disableTransitions = false;
    }
    get counterText() {
      const countAsNumber = this.count ?? -1;
      const maxAsNumber = this.max ?? -1;
      if (countAsNumber < 0 || maxAsNumber <= 0) {
        return "";
      }
      return `${countAsNumber} / ${maxAsNumber}`;
    }
    get supportingOrErrorText() {
      return this.error && this.errorText ? this.errorText : this.supportingText;
    }
    /**
     * Re-announces the field's error supporting text to screen readers.
     *
     * Error text announces to screen readers anytime it is visible and changes.
     * Use the method to re-announce the message when the text has not changed,
     * but announcement is still needed (such as for `reportValidity()`).
     */
    reannounceError() {
      this.refreshErrorAlert = true;
    }
    update(props) {
      const isDisabledChanging = props.has("disabled") && props.get("disabled") !== void 0;
      if (isDisabledChanging) {
        this.disableTransitions = true;
      }
      if (this.disabled && this.focused) {
        props.set("focused", true);
        this.focused = false;
      }
      this.animateLabelIfNeeded({
        wasFocused: props.get("focused"),
        wasPopulated: props.get("populated")
      });
      super.update(props);
    }
    render() {
      var _a3, _b, _c, _d;
      const floatingLabel = this.renderLabel(
        /*isFloating*/
        true
      );
      const restingLabel = this.renderLabel(
        /*isFloating*/
        false
      );
      const outline = (_a3 = this.renderOutline) == null ? void 0 : _a3.call(this, floatingLabel);
      const classes = {
        "disabled": this.disabled,
        "disable-transitions": this.disableTransitions,
        "error": this.error && !this.disabled,
        "focused": this.focused,
        "with-start": this.hasStart,
        "with-end": this.hasEnd,
        "populated": this.populated,
        "resizable": this.resizable,
        "required": this.required,
        "no-label": !this.label
      };
      return b2`
      <div class="field ${e8(classes)}">
        <div class="container-overflow">
          ${(_b = this.renderBackground) == null ? void 0 : _b.call(this)}
          <slot name="container"></slot>
          ${(_c = this.renderStateLayer) == null ? void 0 : _c.call(this)} ${(_d = this.renderIndicator) == null ? void 0 : _d.call(this)} ${outline}
          <div class="container">
            <div class="start">
              <slot name="start"></slot>
            </div>
            <div class="middle">
              <div class="label-wrapper">
                ${restingLabel} ${outline ? A : floatingLabel}
              </div>
              <div class="content">
                <slot></slot>
              </div>
            </div>
            <div class="end">
              <slot name="end"></slot>
            </div>
          </div>
        </div>
        ${this.renderSupportingText()}
      </div>
    `;
    }
    updated(changed) {
      if (changed.has("supportingText") || changed.has("errorText") || changed.has("count") || changed.has("max")) {
        this.updateSlottedAriaDescribedBy();
      }
      if (this.refreshErrorAlert) {
        requestAnimationFrame(() => {
          this.refreshErrorAlert = false;
        });
      }
      if (this.disableTransitions) {
        requestAnimationFrame(() => {
          this.disableTransitions = false;
        });
      }
    }
    renderSupportingText() {
      const { supportingOrErrorText, counterText } = this;
      if (!supportingOrErrorText && !counterText) {
        return A;
      }
      const start = b2`<span>${supportingOrErrorText}</span>`;
      const end = counterText ? b2`<span class="counter">${counterText}</span>` : A;
      const shouldErrorAnnounce = this.error && this.errorText && !this.refreshErrorAlert;
      const role = shouldErrorAnnounce ? "alert" : A;
      return b2`
      <div class="supporting-text" role=${role}>${start}${end}</div>
      <slot
        name="aria-describedby"
        @slotchange=${this.updateSlottedAriaDescribedBy}></slot>
    `;
    }
    updateSlottedAriaDescribedBy() {
      for (const element of this.slottedAriaDescribedBy) {
        D(b2`${this.supportingOrErrorText} ${this.counterText}`, element);
        element.setAttribute("hidden", "");
      }
    }
    renderLabel(isFloating) {
      if (!this.label) {
        return A;
      }
      let visible;
      if (isFloating) {
        visible = this.focused || this.populated || this.isAnimating;
      } else {
        visible = !this.focused && !this.populated && !this.isAnimating;
      }
      const classes = {
        "hidden": !visible,
        "floating": isFloating,
        "resting": !isFloating
      };
      const labelText = `${this.label}${this.required && !this.noAsterisk ? "*" : ""}`;
      return b2`
      <span class="label ${e8(classes)}" aria-hidden=${!visible}
        >${labelText}</span
      >
    `;
    }
    animateLabelIfNeeded({ wasFocused, wasPopulated }) {
      var _a3, _b, _c;
      if (!this.label) {
        return;
      }
      wasFocused ?? (wasFocused = this.focused);
      wasPopulated ?? (wasPopulated = this.populated);
      const wasFloating = wasFocused || wasPopulated;
      const shouldBeFloating = this.focused || this.populated;
      if (wasFloating === shouldBeFloating) {
        return;
      }
      this.isAnimating = true;
      (_a3 = this.labelAnimation) == null ? void 0 : _a3.cancel();
      this.labelAnimation = (_b = this.floatingLabelEl) == null ? void 0 : _b.animate(this.getLabelKeyframes(), { duration: 150, easing: EASING.STANDARD });
      (_c = this.labelAnimation) == null ? void 0 : _c.addEventListener("finish", () => {
        this.isAnimating = false;
      });
    }
    getLabelKeyframes() {
      const { floatingLabelEl, restingLabelEl } = this;
      if (!floatingLabelEl || !restingLabelEl) {
        return [];
      }
      const { x: floatingX, y: floatingY, height: floatingHeight } = floatingLabelEl.getBoundingClientRect();
      const { x: restingX, y: restingY, height: restingHeight } = restingLabelEl.getBoundingClientRect();
      const floatingScrollWidth = floatingLabelEl.scrollWidth;
      const restingScrollWidth = restingLabelEl.scrollWidth;
      const scale = restingScrollWidth / floatingScrollWidth;
      const xDelta = restingX - floatingX;
      const yDelta = restingY - floatingY + Math.round((restingHeight - floatingHeight * scale) / 2);
      const restTransform = `translateX(${xDelta}px) translateY(${yDelta}px) scale(${scale})`;
      const floatTransform = `translateX(0) translateY(0) scale(1)`;
      const restingClientWidth = restingLabelEl.clientWidth;
      const isRestingClipped = restingScrollWidth > restingClientWidth;
      const width = isRestingClipped ? `${restingClientWidth / scale}px` : "";
      if (this.focused || this.populated) {
        return [
          { transform: restTransform, width },
          { transform: floatTransform, width }
        ];
      }
      return [
        { transform: floatTransform, width },
        { transform: restTransform, width }
      ];
    }
    getSurfacePositionClientRect() {
      return this.containerEl.getBoundingClientRect();
    }
  };
  __decorate([
    n3({ type: Boolean })
  ], Field.prototype, "disabled", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Field.prototype, "error", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Field.prototype, "focused", void 0);
  __decorate([
    n3()
  ], Field.prototype, "label", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-asterisk" })
  ], Field.prototype, "noAsterisk", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Field.prototype, "populated", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Field.prototype, "required", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Field.prototype, "resizable", void 0);
  __decorate([
    n3({ attribute: "supporting-text" })
  ], Field.prototype, "supportingText", void 0);
  __decorate([
    n3({ attribute: "error-text" })
  ], Field.prototype, "errorText", void 0);
  __decorate([
    n3({ type: Number })
  ], Field.prototype, "count", void 0);
  __decorate([
    n3({ type: Number })
  ], Field.prototype, "max", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "has-start" })
  ], Field.prototype, "hasStart", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "has-end" })
  ], Field.prototype, "hasEnd", void 0);
  __decorate([
    o4({ slot: "aria-describedby" })
  ], Field.prototype, "slottedAriaDescribedBy", void 0);
  __decorate([
    r4()
  ], Field.prototype, "isAnimating", void 0);
  __decorate([
    r4()
  ], Field.prototype, "refreshErrorAlert", void 0);
  __decorate([
    r4()
  ], Field.prototype, "disableTransitions", void 0);
  __decorate([
    e4(".label.floating")
  ], Field.prototype, "floatingLabelEl", void 0);
  __decorate([
    e4(".label.resting")
  ], Field.prototype, "restingLabelEl", void 0);
  __decorate([
    e4(".container")
  ], Field.prototype, "containerEl", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/field/internal/outlined-field.js
  var OutlinedField = class extends Field {
    renderOutline(floatingLabel) {
      return b2`
      <div class="outline">
        <div class="outline-start"></div>
        <div class="outline-notch">
          <div class="outline-panel-inactive"></div>
          <div class="outline-panel-active"></div>
          <div class="outline-label">${floatingLabel}</div>
        </div>
        <div class="outline-end"></div>
      </div>
    `;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/field/internal/outlined-styles.js
  var styles = i`@layer styles{:host{--_bottom-space: var(--md-outlined-field-bottom-space, 16px);--_content-color: var(--md-outlined-field-content-color, var(--md-sys-color-on-surface, #1d1b20));--_content-font: var(--md-outlined-field-content-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));--_content-line-height: var(--md-outlined-field-content-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));--_content-size: var(--md-outlined-field-content-size, var(--md-sys-typescale-body-large-size, 1rem));--_content-space: var(--md-outlined-field-content-space, 16px);--_content-weight: var(--md-outlined-field-content-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));--_disabled-content-color: var(--md-outlined-field-disabled-content-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-content-opacity: var(--md-outlined-field-disabled-content-opacity, 0.38);--_disabled-label-text-color: var(--md-outlined-field-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-label-text-opacity: var(--md-outlined-field-disabled-label-text-opacity, 0.38);--_disabled-leading-content-color: var(--md-outlined-field-disabled-leading-content-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-leading-content-opacity: var(--md-outlined-field-disabled-leading-content-opacity, 0.38);--_disabled-outline-color: var(--md-outlined-field-disabled-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-outline-opacity: var(--md-outlined-field-disabled-outline-opacity, 0.12);--_disabled-outline-width: var(--md-outlined-field-disabled-outline-width, 1px);--_disabled-supporting-text-color: var(--md-outlined-field-disabled-supporting-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-supporting-text-opacity: var(--md-outlined-field-disabled-supporting-text-opacity, 0.38);--_disabled-trailing-content-color: var(--md-outlined-field-disabled-trailing-content-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-trailing-content-opacity: var(--md-outlined-field-disabled-trailing-content-opacity, 0.38);--_error-content-color: var(--md-outlined-field-error-content-color, var(--md-sys-color-on-surface, #1d1b20));--_error-focus-content-color: var(--md-outlined-field-error-focus-content-color, var(--md-sys-color-on-surface, #1d1b20));--_error-focus-label-text-color: var(--md-outlined-field-error-focus-label-text-color, var(--md-sys-color-error, #b3261e));--_error-focus-leading-content-color: var(--md-outlined-field-error-focus-leading-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_error-focus-outline-color: var(--md-outlined-field-error-focus-outline-color, var(--md-sys-color-error, #b3261e));--_error-focus-supporting-text-color: var(--md-outlined-field-error-focus-supporting-text-color, var(--md-sys-color-error, #b3261e));--_error-focus-trailing-content-color: var(--md-outlined-field-error-focus-trailing-content-color, var(--md-sys-color-error, #b3261e));--_error-hover-content-color: var(--md-outlined-field-error-hover-content-color, var(--md-sys-color-on-surface, #1d1b20));--_error-hover-label-text-color: var(--md-outlined-field-error-hover-label-text-color, var(--md-sys-color-on-error-container, #410e0b));--_error-hover-leading-content-color: var(--md-outlined-field-error-hover-leading-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_error-hover-outline-color: var(--md-outlined-field-error-hover-outline-color, var(--md-sys-color-on-error-container, #410e0b));--_error-hover-supporting-text-color: var(--md-outlined-field-error-hover-supporting-text-color, var(--md-sys-color-error, #b3261e));--_error-hover-trailing-content-color: var(--md-outlined-field-error-hover-trailing-content-color, var(--md-sys-color-on-error-container, #410e0b));--_error-label-text-color: var(--md-outlined-field-error-label-text-color, var(--md-sys-color-error, #b3261e));--_error-leading-content-color: var(--md-outlined-field-error-leading-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_error-outline-color: var(--md-outlined-field-error-outline-color, var(--md-sys-color-error, #b3261e));--_error-supporting-text-color: var(--md-outlined-field-error-supporting-text-color, var(--md-sys-color-error, #b3261e));--_error-trailing-content-color: var(--md-outlined-field-error-trailing-content-color, var(--md-sys-color-error, #b3261e));--_focus-content-color: var(--md-outlined-field-focus-content-color, var(--md-sys-color-on-surface, #1d1b20));--_focus-label-text-color: var(--md-outlined-field-focus-label-text-color, var(--md-sys-color-primary, #6750a4));--_focus-leading-content-color: var(--md-outlined-field-focus-leading-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_focus-outline-color: var(--md-outlined-field-focus-outline-color, var(--md-sys-color-primary, #6750a4));--_focus-outline-width: var(--md-outlined-field-focus-outline-width, 3px);--_focus-supporting-text-color: var(--md-outlined-field-focus-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_focus-trailing-content-color: var(--md-outlined-field-focus-trailing-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-content-color: var(--md-outlined-field-hover-content-color, var(--md-sys-color-on-surface, #1d1b20));--_hover-label-text-color: var(--md-outlined-field-hover-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_hover-leading-content-color: var(--md-outlined-field-hover-leading-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-outline-color: var(--md-outlined-field-hover-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_hover-outline-width: var(--md-outlined-field-hover-outline-width, 1px);--_hover-supporting-text-color: var(--md-outlined-field-hover-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-trailing-content-color: var(--md-outlined-field-hover-trailing-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_label-text-color: var(--md-outlined-field-label-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_label-text-font: var(--md-outlined-field-label-text-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-outlined-field-label-text-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));--_label-text-padding-bottom: var(--md-outlined-field-label-text-padding-bottom, 8px);--_label-text-populated-line-height: var(--md-outlined-field-label-text-populated-line-height, var(--md-sys-typescale-body-small-line-height, 1rem));--_label-text-populated-size: var(--md-outlined-field-label-text-populated-size, var(--md-sys-typescale-body-small-size, 0.75rem));--_label-text-size: var(--md-outlined-field-label-text-size, var(--md-sys-typescale-body-large-size, 1rem));--_label-text-weight: var(--md-outlined-field-label-text-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));--_leading-content-color: var(--md-outlined-field-leading-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_leading-space: var(--md-outlined-field-leading-space, 16px);--_outline-color: var(--md-outlined-field-outline-color, var(--md-sys-color-outline, #79747e));--_outline-label-padding: var(--md-outlined-field-outline-label-padding, 4px);--_outline-width: var(--md-outlined-field-outline-width, 1px);--_supporting-text-color: var(--md-outlined-field-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_supporting-text-font: var(--md-outlined-field-supporting-text-font, var(--md-sys-typescale-body-small-font, var(--md-ref-typeface-plain, Roboto)));--_supporting-text-leading-space: var(--md-outlined-field-supporting-text-leading-space, 16px);--_supporting-text-line-height: var(--md-outlined-field-supporting-text-line-height, var(--md-sys-typescale-body-small-line-height, 1rem));--_supporting-text-size: var(--md-outlined-field-supporting-text-size, var(--md-sys-typescale-body-small-size, 0.75rem));--_supporting-text-top-space: var(--md-outlined-field-supporting-text-top-space, 4px);--_supporting-text-trailing-space: var(--md-outlined-field-supporting-text-trailing-space, 16px);--_supporting-text-weight: var(--md-outlined-field-supporting-text-weight, var(--md-sys-typescale-body-small-weight, var(--md-ref-typeface-weight-regular, 400)));--_top-space: var(--md-outlined-field-top-space, 16px);--_trailing-content-color: var(--md-outlined-field-trailing-content-color, var(--md-sys-color-on-surface-variant, #49454f));--_trailing-space: var(--md-outlined-field-trailing-space, 16px);--_with-leading-content-leading-space: var(--md-outlined-field-with-leading-content-leading-space, 12px);--_with-trailing-content-trailing-space: var(--md-outlined-field-with-trailing-content-trailing-space, 12px);--_container-shape-start-start: var(--md-outlined-field-container-shape-start-start, var(--md-outlined-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_container-shape-start-end: var(--md-outlined-field-container-shape-start-end, var(--md-outlined-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_container-shape-end-end: var(--md-outlined-field-container-shape-end-end, var(--md-outlined-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_container-shape-end-start: var(--md-outlined-field-container-shape-end-start, var(--md-outlined-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)))}.outline{border-color:var(--_outline-color);border-radius:inherit;display:flex;pointer-events:none;height:100%;position:absolute;width:100%;z-index:1}.outline-start::before,.outline-start::after,.outline-panel-inactive::before,.outline-panel-inactive::after,.outline-panel-active::before,.outline-panel-active::after,.outline-end::before,.outline-end::after{border:inherit;content:"";inset:0;position:absolute}.outline-start,.outline-end{border:inherit;border-radius:inherit;box-sizing:border-box;position:relative}.outline-start::before,.outline-start::after,.outline-end::before,.outline-end::after{border-bottom-style:solid;border-top-style:solid}.outline-start::after,.outline-end::after{opacity:0;transition:opacity 150ms cubic-bezier(0.2, 0, 0, 1)}.focused .outline-start::after,.focused .outline-end::after{opacity:1}.outline-start::before,.outline-start::after{border-inline-start-style:solid;border-inline-end-style:none;border-start-start-radius:inherit;border-start-end-radius:0;border-end-start-radius:inherit;border-end-end-radius:0;margin-inline-end:var(--_outline-label-padding)}.outline-end{flex-grow:1;margin-inline-start:calc(-1*var(--_outline-label-padding))}.outline-end::before,.outline-end::after{border-inline-start-style:none;border-inline-end-style:solid;border-start-start-radius:0;border-start-end-radius:inherit;border-end-start-radius:0;border-end-end-radius:inherit}.outline-notch{align-items:flex-start;border:inherit;display:flex;margin-inline-start:calc(-1*var(--_outline-label-padding));margin-inline-end:var(--_outline-label-padding);max-width:calc(100% - var(--_leading-space) - var(--_trailing-space));padding:0 var(--_outline-label-padding);position:relative}.no-label .outline-notch{display:none}.outline-panel-inactive,.outline-panel-active{border:inherit;border-bottom-style:solid;inset:0;position:absolute}.outline-panel-inactive::before,.outline-panel-inactive::after,.outline-panel-active::before,.outline-panel-active::after{border-top-style:solid;border-bottom:none;bottom:auto;transform:scaleX(1);transition:transform 150ms cubic-bezier(0.2, 0, 0, 1)}.outline-panel-inactive::before,.outline-panel-active::before{right:50%;transform-origin:top left}.outline-panel-inactive::after,.outline-panel-active::after{left:50%;transform-origin:top right}.populated .outline-panel-inactive::before,.populated .outline-panel-inactive::after,.populated .outline-panel-active::before,.populated .outline-panel-active::after,.focused .outline-panel-inactive::before,.focused .outline-panel-inactive::after,.focused .outline-panel-active::before,.focused .outline-panel-active::after{transform:scaleX(0)}.outline-panel-active{opacity:0;transition:opacity 150ms cubic-bezier(0.2, 0, 0, 1)}.focused .outline-panel-active{opacity:1}.outline-label{display:flex;max-width:100%;transform:translateY(calc(-100% + var(--_label-text-padding-bottom)))}.outline-start,.field:not(.with-start) .content ::slotted(*){padding-inline-start:max(var(--_leading-space),max(var(--_container-shape-start-start),var(--_container-shape-end-start)) + var(--_outline-label-padding))}.field:not(.with-start) .label-wrapper{margin-inline-start:max(var(--_leading-space),max(var(--_container-shape-start-start),var(--_container-shape-end-start)) + var(--_outline-label-padding))}.field:not(.with-end) .content ::slotted(*){padding-inline-end:max(var(--_trailing-space),max(var(--_container-shape-start-end),var(--_container-shape-end-end)))}.field:not(.with-end) .label-wrapper{margin-inline-end:max(var(--_trailing-space),max(var(--_container-shape-start-end),var(--_container-shape-end-end)))}.outline-start::before,.outline-end::before,.outline-panel-inactive,.outline-panel-inactive::before,.outline-panel-inactive::after{border-width:var(--_outline-width)}:hover .outline{border-color:var(--_hover-outline-color);color:var(--_hover-outline-color)}:hover .outline-start::before,:hover .outline-end::before,:hover .outline-panel-inactive,:hover .outline-panel-inactive::before,:hover .outline-panel-inactive::after{border-width:var(--_hover-outline-width)}.focused .outline{border-color:var(--_focus-outline-color);color:var(--_focus-outline-color)}.outline-start::after,.outline-end::after,.outline-panel-active,.outline-panel-active::before,.outline-panel-active::after{border-width:var(--_focus-outline-width)}.disabled .outline{border-color:var(--_disabled-outline-color);color:var(--_disabled-outline-color)}.disabled .outline-start,.disabled .outline-end,.disabled .outline-panel-inactive{opacity:var(--_disabled-outline-opacity)}.disabled .outline-start::before,.disabled .outline-end::before,.disabled .outline-panel-inactive,.disabled .outline-panel-inactive::before,.disabled .outline-panel-inactive::after{border-width:var(--_disabled-outline-width)}.error .outline{border-color:var(--_error-outline-color);color:var(--_error-outline-color)}.error:hover .outline{border-color:var(--_error-hover-outline-color);color:var(--_error-hover-outline-color)}.error.focused .outline{border-color:var(--_error-focus-outline-color);color:var(--_error-focus-outline-color)}.resizable .container{bottom:var(--_focus-outline-width);inset-inline-end:var(--_focus-outline-width);clip-path:inset(var(--_focus-outline-width) 0 0 var(--_focus-outline-width))}.resizable .container>*{top:var(--_focus-outline-width);inset-inline-start:var(--_focus-outline-width)}.resizable .container:dir(rtl){clip-path:inset(var(--_focus-outline-width) var(--_focus-outline-width) 0 0)}}@layer hcm{@media(forced-colors: active){.disabled .outline{border-color:GrayText;color:GrayText}.disabled :is(.outline-start,.outline-end,.outline-panel-inactive){opacity:1}}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/field/internal/shared-styles.js
  var styles2 = i`:host{display:inline-flex;resize:both}.field{display:flex;flex:1;flex-direction:column;writing-mode:horizontal-tb;max-width:100%}.container-overflow{border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-end-radius:var(--_container-shape-end-end);border-end-start-radius:var(--_container-shape-end-start);display:flex;height:100%;position:relative}.container{align-items:center;border-radius:inherit;display:flex;flex:1;max-height:100%;min-height:100%;min-width:min-content;position:relative}.field,.container-overflow{resize:inherit}.resizable:not(.disabled) .container{resize:inherit;overflow:hidden}.disabled{pointer-events:none}slot[name=container]{border-radius:inherit}slot[name=container]::slotted(*){border-radius:inherit;inset:0;pointer-events:none;position:absolute}@layer styles{.start,.middle,.end{display:flex;box-sizing:border-box;height:100%;position:relative}.start{color:var(--_leading-content-color)}.end{color:var(--_trailing-content-color)}.start,.end{align-items:center;justify-content:center}.with-start .start{margin-inline:var(--_with-leading-content-leading-space) var(--_content-space)}.with-end .end{margin-inline:var(--_content-space) var(--_with-trailing-content-trailing-space)}.middle{align-items:stretch;align-self:baseline;flex:1}.content{color:var(--_content-color);display:flex;flex:1;opacity:0;transition:opacity 83ms cubic-bezier(0.2, 0, 0, 1)}.no-label .content,.focused .content,.populated .content{opacity:1;transition-delay:67ms}:is(.disabled,.disable-transitions) .content{transition:none}.content ::slotted(*){all:unset;color:currentColor;font-family:var(--_content-font);font-size:var(--_content-size);line-height:var(--_content-line-height);font-weight:var(--_content-weight);width:100%;overflow-wrap:revert;white-space:revert}.content ::slotted(:not(textarea)){padding-top:var(--_top-space);padding-bottom:var(--_bottom-space)}.content ::slotted(textarea){margin-top:var(--_top-space);margin-bottom:var(--_bottom-space)}:hover .content{color:var(--_hover-content-color)}:hover .start{color:var(--_hover-leading-content-color)}:hover .end{color:var(--_hover-trailing-content-color)}.focused .content{color:var(--_focus-content-color)}.focused .start{color:var(--_focus-leading-content-color)}.focused .end{color:var(--_focus-trailing-content-color)}.disabled .content{color:var(--_disabled-content-color)}.disabled.no-label .content,.disabled.focused .content,.disabled.populated .content{opacity:var(--_disabled-content-opacity)}.disabled .start{color:var(--_disabled-leading-content-color);opacity:var(--_disabled-leading-content-opacity)}.disabled .end{color:var(--_disabled-trailing-content-color);opacity:var(--_disabled-trailing-content-opacity)}.error .content{color:var(--_error-content-color)}.error .start{color:var(--_error-leading-content-color)}.error .end{color:var(--_error-trailing-content-color)}.error:hover .content{color:var(--_error-hover-content-color)}.error:hover .start{color:var(--_error-hover-leading-content-color)}.error:hover .end{color:var(--_error-hover-trailing-content-color)}.error.focused .content{color:var(--_error-focus-content-color)}.error.focused .start{color:var(--_error-focus-leading-content-color)}.error.focused .end{color:var(--_error-focus-trailing-content-color)}}@layer hcm{@media(forced-colors: active){.disabled :is(.start,.content,.end){color:GrayText;opacity:1}}}@layer styles{.label{box-sizing:border-box;color:var(--_label-text-color);overflow:hidden;max-width:100%;text-overflow:ellipsis;white-space:nowrap;z-index:1;font-family:var(--_label-text-font);font-size:var(--_label-text-size);line-height:var(--_label-text-line-height);font-weight:var(--_label-text-weight);width:min-content}.label-wrapper{inset:0;pointer-events:none;position:absolute}.label.resting{position:absolute;top:var(--_top-space)}.label.floating{font-size:var(--_label-text-populated-size);line-height:var(--_label-text-populated-line-height);transform-origin:top left}.label.hidden{opacity:0}.no-label .label{display:none}.label-wrapper{inset:0;position:absolute;text-align:initial}:hover .label{color:var(--_hover-label-text-color)}.focused .label{color:var(--_focus-label-text-color)}.disabled .label{color:var(--_disabled-label-text-color)}.disabled .label:not(.hidden){opacity:var(--_disabled-label-text-opacity)}.error .label{color:var(--_error-label-text-color)}.error:hover .label{color:var(--_error-hover-label-text-color)}.error.focused .label{color:var(--_error-focus-label-text-color)}}@layer hcm{@media(forced-colors: active){.disabled .label:not(.hidden){color:GrayText;opacity:1}}}@layer styles{.supporting-text{color:var(--_supporting-text-color);display:flex;font-family:var(--_supporting-text-font);font-size:var(--_supporting-text-size);line-height:var(--_supporting-text-line-height);font-weight:var(--_supporting-text-weight);gap:16px;justify-content:space-between;padding-inline-start:var(--_supporting-text-leading-space);padding-inline-end:var(--_supporting-text-trailing-space);padding-top:var(--_supporting-text-top-space)}.supporting-text :nth-child(2){flex-shrink:0}:hover .supporting-text{color:var(--_hover-supporting-text-color)}.focus .supporting-text{color:var(--_focus-supporting-text-color)}.disabled .supporting-text{color:var(--_disabled-supporting-text-color);opacity:var(--_disabled-supporting-text-opacity)}.error .supporting-text{color:var(--_error-supporting-text-color)}.error:hover .supporting-text{color:var(--_error-hover-supporting-text-color)}.error.focus .supporting-text{color:var(--_error-focus-supporting-text-color)}}@layer hcm{@media(forced-colors: active){.disabled .supporting-text{color:GrayText;opacity:1}}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/field/outlined-field.js
  var MdOutlinedField = class MdOutlinedField2 extends OutlinedField {
  };
  MdOutlinedField.styles = [styles2, styles];
  if (!customElements.get("md-outlined-field")) {
    MdOutlinedField = __decorate([
      t("md-outlined-field")
    ], MdOutlinedField);
  }

  // custom_components/smart_agent/frontend/node_modules/lit-html/static.js
  var a3 = Symbol.for("");
  var o8 = (t6) => {
    if ((t6 == null ? void 0 : t6.r) === a3)
      return t6 == null ? void 0 : t6._$litStatic$;
  };
  var i6 = (t6, ...r9) => ({ _$litStatic$: r9.reduce((r10, e9, a4) => r10 + ((t7) => {
    if (void 0 !== t7._$litStatic$)
      return t7._$litStatic$;
    throw Error(`Value passed to 'literal' function must be a 'literal' result: ${t7}. Use 'unsafeStatic' to pass non-literal values, but
            take care to ensure page security.`);
  })(e9) + t6[a4 + 1], t6[0]), r: a3 });
  var l3 = /* @__PURE__ */ new Map();
  var n6 = (t6) => (r9, ...e9) => {
    const a4 = e9.length;
    let s4, i8;
    const n9 = [], u4 = [];
    let c5, $3 = 0, f3 = false;
    for (; $3 < a4; ) {
      for (c5 = r9[$3]; $3 < a4 && void 0 !== (i8 = e9[$3], s4 = o8(i8)); )
        c5 += s4 + r9[++$3], f3 = true;
      $3 !== a4 && u4.push(i8), n9.push(c5), $3++;
    }
    if ($3 === a4 && n9.push(r9[a4]), f3) {
      const t7 = n9.join("$$lit$$");
      void 0 === (r9 = l3.get(t7)) && (n9.raw = n9, l3.set(t7, r9 = n9)), e9 = u4;
    }
    return t6(r9, ...e9);
  };
  var u3 = n6(b2);
  var c4 = n6(w);
  var $2 = n6(T);

  // custom_components/smart_agent/frontend/node_modules/@material/web/textfield/internal/outlined-styles.js
  var styles3 = i`:host{--_caret-color: var(--md-outlined-text-field-caret-color, var(--md-sys-color-primary, #6750a4));--_disabled-input-text-color: var(--md-outlined-text-field-disabled-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-input-text-opacity: var(--md-outlined-text-field-disabled-input-text-opacity, 0.38);--_disabled-label-text-color: var(--md-outlined-text-field-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-label-text-opacity: var(--md-outlined-text-field-disabled-label-text-opacity, 0.38);--_disabled-leading-icon-color: var(--md-outlined-text-field-disabled-leading-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-leading-icon-opacity: var(--md-outlined-text-field-disabled-leading-icon-opacity, 0.38);--_disabled-outline-color: var(--md-outlined-text-field-disabled-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-outline-opacity: var(--md-outlined-text-field-disabled-outline-opacity, 0.12);--_disabled-outline-width: var(--md-outlined-text-field-disabled-outline-width, 1px);--_disabled-supporting-text-color: var(--md-outlined-text-field-disabled-supporting-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-supporting-text-opacity: var(--md-outlined-text-field-disabled-supporting-text-opacity, 0.38);--_disabled-trailing-icon-color: var(--md-outlined-text-field-disabled-trailing-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-trailing-icon-opacity: var(--md-outlined-text-field-disabled-trailing-icon-opacity, 0.38);--_error-focus-caret-color: var(--md-outlined-text-field-error-focus-caret-color, var(--md-sys-color-error, #b3261e));--_error-focus-input-text-color: var(--md-outlined-text-field-error-focus-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_error-focus-label-text-color: var(--md-outlined-text-field-error-focus-label-text-color, var(--md-sys-color-error, #b3261e));--_error-focus-leading-icon-color: var(--md-outlined-text-field-error-focus-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_error-focus-outline-color: var(--md-outlined-text-field-error-focus-outline-color, var(--md-sys-color-error, #b3261e));--_error-focus-supporting-text-color: var(--md-outlined-text-field-error-focus-supporting-text-color, var(--md-sys-color-error, #b3261e));--_error-focus-trailing-icon-color: var(--md-outlined-text-field-error-focus-trailing-icon-color, var(--md-sys-color-error, #b3261e));--_error-hover-input-text-color: var(--md-outlined-text-field-error-hover-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_error-hover-label-text-color: var(--md-outlined-text-field-error-hover-label-text-color, var(--md-sys-color-on-error-container, #410e0b));--_error-hover-leading-icon-color: var(--md-outlined-text-field-error-hover-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_error-hover-outline-color: var(--md-outlined-text-field-error-hover-outline-color, var(--md-sys-color-on-error-container, #410e0b));--_error-hover-supporting-text-color: var(--md-outlined-text-field-error-hover-supporting-text-color, var(--md-sys-color-error, #b3261e));--_error-hover-trailing-icon-color: var(--md-outlined-text-field-error-hover-trailing-icon-color, var(--md-sys-color-on-error-container, #410e0b));--_error-input-text-color: var(--md-outlined-text-field-error-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_error-label-text-color: var(--md-outlined-text-field-error-label-text-color, var(--md-sys-color-error, #b3261e));--_error-leading-icon-color: var(--md-outlined-text-field-error-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_error-outline-color: var(--md-outlined-text-field-error-outline-color, var(--md-sys-color-error, #b3261e));--_error-supporting-text-color: var(--md-outlined-text-field-error-supporting-text-color, var(--md-sys-color-error, #b3261e));--_error-trailing-icon-color: var(--md-outlined-text-field-error-trailing-icon-color, var(--md-sys-color-error, #b3261e));--_focus-input-text-color: var(--md-outlined-text-field-focus-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_focus-label-text-color: var(--md-outlined-text-field-focus-label-text-color, var(--md-sys-color-primary, #6750a4));--_focus-leading-icon-color: var(--md-outlined-text-field-focus-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_focus-outline-color: var(--md-outlined-text-field-focus-outline-color, var(--md-sys-color-primary, #6750a4));--_focus-outline-width: var(--md-outlined-text-field-focus-outline-width, 3px);--_focus-supporting-text-color: var(--md-outlined-text-field-focus-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_focus-trailing-icon-color: var(--md-outlined-text-field-focus-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-input-text-color: var(--md-outlined-text-field-hover-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_hover-label-text-color: var(--md-outlined-text-field-hover-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_hover-leading-icon-color: var(--md-outlined-text-field-hover-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-outline-color: var(--md-outlined-text-field-hover-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_hover-outline-width: var(--md-outlined-text-field-hover-outline-width, 1px);--_hover-supporting-text-color: var(--md-outlined-text-field-hover-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-trailing-icon-color: var(--md-outlined-text-field-hover-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_input-text-color: var(--md-outlined-text-field-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_input-text-font: var(--md-outlined-text-field-input-text-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));--_input-text-line-height: var(--md-outlined-text-field-input-text-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));--_input-text-placeholder-color: var(--md-outlined-text-field-input-text-placeholder-color, var(--md-sys-color-on-surface-variant, #49454f));--_input-text-prefix-color: var(--md-outlined-text-field-input-text-prefix-color, var(--md-sys-color-on-surface-variant, #49454f));--_input-text-size: var(--md-outlined-text-field-input-text-size, var(--md-sys-typescale-body-large-size, 1rem));--_input-text-suffix-color: var(--md-outlined-text-field-input-text-suffix-color, var(--md-sys-color-on-surface-variant, #49454f));--_input-text-weight: var(--md-outlined-text-field-input-text-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));--_label-text-color: var(--md-outlined-text-field-label-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_label-text-font: var(--md-outlined-text-field-label-text-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-outlined-text-field-label-text-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));--_label-text-populated-line-height: var(--md-outlined-text-field-label-text-populated-line-height, var(--md-sys-typescale-body-small-line-height, 1rem));--_label-text-populated-size: var(--md-outlined-text-field-label-text-populated-size, var(--md-sys-typescale-body-small-size, 0.75rem));--_label-text-size: var(--md-outlined-text-field-label-text-size, var(--md-sys-typescale-body-large-size, 1rem));--_label-text-weight: var(--md-outlined-text-field-label-text-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));--_leading-icon-color: var(--md-outlined-text-field-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_leading-icon-size: var(--md-outlined-text-field-leading-icon-size, 24px);--_outline-color: var(--md-outlined-text-field-outline-color, var(--md-sys-color-outline, #79747e));--_outline-width: var(--md-outlined-text-field-outline-width, 1px);--_supporting-text-color: var(--md-outlined-text-field-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_supporting-text-font: var(--md-outlined-text-field-supporting-text-font, var(--md-sys-typescale-body-small-font, var(--md-ref-typeface-plain, Roboto)));--_supporting-text-line-height: var(--md-outlined-text-field-supporting-text-line-height, var(--md-sys-typescale-body-small-line-height, 1rem));--_supporting-text-size: var(--md-outlined-text-field-supporting-text-size, var(--md-sys-typescale-body-small-size, 0.75rem));--_supporting-text-weight: var(--md-outlined-text-field-supporting-text-weight, var(--md-sys-typescale-body-small-weight, var(--md-ref-typeface-weight-regular, 400)));--_trailing-icon-color: var(--md-outlined-text-field-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_trailing-icon-size: var(--md-outlined-text-field-trailing-icon-size, 24px);--_container-shape-start-start: var(--md-outlined-text-field-container-shape-start-start, var(--md-outlined-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_container-shape-start-end: var(--md-outlined-text-field-container-shape-start-end, var(--md-outlined-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_container-shape-end-end: var(--md-outlined-text-field-container-shape-end-end, var(--md-outlined-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_container-shape-end-start: var(--md-outlined-text-field-container-shape-end-start, var(--md-outlined-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_icon-input-space: var(--md-outlined-text-field-icon-input-space, 16px);--_leading-space: var(--md-outlined-text-field-leading-space, 16px);--_trailing-space: var(--md-outlined-text-field-trailing-space, 16px);--_top-space: var(--md-outlined-text-field-top-space, 16px);--_bottom-space: var(--md-outlined-text-field-bottom-space, 16px);--_input-text-prefix-trailing-space: var(--md-outlined-text-field-input-text-prefix-trailing-space, 2px);--_input-text-suffix-leading-space: var(--md-outlined-text-field-input-text-suffix-leading-space, 2px);--_focus-caret-color: var(--md-outlined-text-field-focus-caret-color, var(--md-sys-color-primary, #6750a4));--_with-leading-icon-leading-space: var(--md-outlined-text-field-with-leading-icon-leading-space, 12px);--_with-trailing-icon-trailing-space: var(--md-outlined-text-field-with-trailing-icon-trailing-space, 12px);--md-outlined-field-bottom-space: var(--_bottom-space);--md-outlined-field-container-shape-end-end: var(--_container-shape-end-end);--md-outlined-field-container-shape-end-start: var(--_container-shape-end-start);--md-outlined-field-container-shape-start-end: var(--_container-shape-start-end);--md-outlined-field-container-shape-start-start: var(--_container-shape-start-start);--md-outlined-field-content-color: var(--_input-text-color);--md-outlined-field-content-font: var(--_input-text-font);--md-outlined-field-content-line-height: var(--_input-text-line-height);--md-outlined-field-content-size: var(--_input-text-size);--md-outlined-field-content-space: var(--_icon-input-space);--md-outlined-field-content-weight: var(--_input-text-weight);--md-outlined-field-disabled-content-color: var(--_disabled-input-text-color);--md-outlined-field-disabled-content-opacity: var(--_disabled-input-text-opacity);--md-outlined-field-disabled-label-text-color: var(--_disabled-label-text-color);--md-outlined-field-disabled-label-text-opacity: var(--_disabled-label-text-opacity);--md-outlined-field-disabled-leading-content-color: var(--_disabled-leading-icon-color);--md-outlined-field-disabled-leading-content-opacity: var(--_disabled-leading-icon-opacity);--md-outlined-field-disabled-outline-color: var(--_disabled-outline-color);--md-outlined-field-disabled-outline-opacity: var(--_disabled-outline-opacity);--md-outlined-field-disabled-outline-width: var(--_disabled-outline-width);--md-outlined-field-disabled-supporting-text-color: var(--_disabled-supporting-text-color);--md-outlined-field-disabled-supporting-text-opacity: var(--_disabled-supporting-text-opacity);--md-outlined-field-disabled-trailing-content-color: var(--_disabled-trailing-icon-color);--md-outlined-field-disabled-trailing-content-opacity: var(--_disabled-trailing-icon-opacity);--md-outlined-field-error-content-color: var(--_error-input-text-color);--md-outlined-field-error-focus-content-color: var(--_error-focus-input-text-color);--md-outlined-field-error-focus-label-text-color: var(--_error-focus-label-text-color);--md-outlined-field-error-focus-leading-content-color: var(--_error-focus-leading-icon-color);--md-outlined-field-error-focus-outline-color: var(--_error-focus-outline-color);--md-outlined-field-error-focus-supporting-text-color: var(--_error-focus-supporting-text-color);--md-outlined-field-error-focus-trailing-content-color: var(--_error-focus-trailing-icon-color);--md-outlined-field-error-hover-content-color: var(--_error-hover-input-text-color);--md-outlined-field-error-hover-label-text-color: var(--_error-hover-label-text-color);--md-outlined-field-error-hover-leading-content-color: var(--_error-hover-leading-icon-color);--md-outlined-field-error-hover-outline-color: var(--_error-hover-outline-color);--md-outlined-field-error-hover-supporting-text-color: var(--_error-hover-supporting-text-color);--md-outlined-field-error-hover-trailing-content-color: var(--_error-hover-trailing-icon-color);--md-outlined-field-error-label-text-color: var(--_error-label-text-color);--md-outlined-field-error-leading-content-color: var(--_error-leading-icon-color);--md-outlined-field-error-outline-color: var(--_error-outline-color);--md-outlined-field-error-supporting-text-color: var(--_error-supporting-text-color);--md-outlined-field-error-trailing-content-color: var(--_error-trailing-icon-color);--md-outlined-field-focus-content-color: var(--_focus-input-text-color);--md-outlined-field-focus-label-text-color: var(--_focus-label-text-color);--md-outlined-field-focus-leading-content-color: var(--_focus-leading-icon-color);--md-outlined-field-focus-outline-color: var(--_focus-outline-color);--md-outlined-field-focus-outline-width: var(--_focus-outline-width);--md-outlined-field-focus-supporting-text-color: var(--_focus-supporting-text-color);--md-outlined-field-focus-trailing-content-color: var(--_focus-trailing-icon-color);--md-outlined-field-hover-content-color: var(--_hover-input-text-color);--md-outlined-field-hover-label-text-color: var(--_hover-label-text-color);--md-outlined-field-hover-leading-content-color: var(--_hover-leading-icon-color);--md-outlined-field-hover-outline-color: var(--_hover-outline-color);--md-outlined-field-hover-outline-width: var(--_hover-outline-width);--md-outlined-field-hover-supporting-text-color: var(--_hover-supporting-text-color);--md-outlined-field-hover-trailing-content-color: var(--_hover-trailing-icon-color);--md-outlined-field-label-text-color: var(--_label-text-color);--md-outlined-field-label-text-font: var(--_label-text-font);--md-outlined-field-label-text-line-height: var(--_label-text-line-height);--md-outlined-field-label-text-populated-line-height: var(--_label-text-populated-line-height);--md-outlined-field-label-text-populated-size: var(--_label-text-populated-size);--md-outlined-field-label-text-size: var(--_label-text-size);--md-outlined-field-label-text-weight: var(--_label-text-weight);--md-outlined-field-leading-content-color: var(--_leading-icon-color);--md-outlined-field-leading-space: var(--_leading-space);--md-outlined-field-outline-color: var(--_outline-color);--md-outlined-field-outline-width: var(--_outline-width);--md-outlined-field-supporting-text-color: var(--_supporting-text-color);--md-outlined-field-supporting-text-font: var(--_supporting-text-font);--md-outlined-field-supporting-text-line-height: var(--_supporting-text-line-height);--md-outlined-field-supporting-text-size: var(--_supporting-text-size);--md-outlined-field-supporting-text-weight: var(--_supporting-text-weight);--md-outlined-field-top-space: var(--_top-space);--md-outlined-field-trailing-content-color: var(--_trailing-icon-color);--md-outlined-field-trailing-space: var(--_trailing-space);--md-outlined-field-with-leading-content-leading-space: var(--_with-leading-icon-leading-space);--md-outlined-field-with-trailing-content-trailing-space: var(--_with-trailing-icon-trailing-space)}
`;

  // custom_components/smart_agent/frontend/node_modules/lit-html/directive-helpers.js
  var { I: t5 } = j;
  var r8 = (o10) => void 0 === o10.strings;
  var m2 = {};
  var p3 = (o10, t6 = m2) => o10._$AH = t6;

  // custom_components/smart_agent/frontend/node_modules/lit-html/directives/live.js
  var l4 = e7(class extends i5 {
    constructor(r9) {
      if (super(r9), r9.type !== t4.PROPERTY && r9.type !== t4.ATTRIBUTE && r9.type !== t4.BOOLEAN_ATTRIBUTE)
        throw Error("The `live` directive is not allowed on child or event bindings");
      if (!r8(r9))
        throw Error("`live` bindings can only contain a single expression");
    }
    render(r9) {
      return r9;
    }
    update(i8, [t6]) {
      if (t6 === E || t6 === A)
        return t6;
      const o10 = i8.element, l5 = i8.name;
      if (i8.type === t4.PROPERTY) {
        if (t6 === o10[l5])
          return E;
      } else if (i8.type === t4.BOOLEAN_ATTRIBUTE) {
        if (!!t6 === o10.hasAttribute(l5))
          return E;
      } else if (i8.type === t4.ATTRIBUTE && o10.getAttribute(l5) === t6 + "")
        return E;
      return p3(i8), t6;
    }
  });

  // custom_components/smart_agent/frontend/node_modules/lit-html/directives/style-map.js
  var n7 = "important";
  var i7 = " !" + n7;
  var o9 = e7(class extends i5 {
    constructor(t6) {
      var _a3;
      if (super(t6), t6.type !== t4.ATTRIBUTE || "style" !== t6.name || ((_a3 = t6.strings) == null ? void 0 : _a3.length) > 2)
        throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.");
    }
    render(t6) {
      return Object.keys(t6).reduce((e9, r9) => {
        const s4 = t6[r9];
        return null == s4 ? e9 : e9 + `${r9 = r9.includes("-") ? r9 : r9.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g, "-$&").toLowerCase()}:${s4};`;
      }, "");
    }
    update(e9, [r9]) {
      const { style: s4 } = e9.element;
      if (void 0 === this.ft)
        return this.ft = new Set(Object.keys(r9)), this.render(r9);
      for (const t6 of this.ft)
        null == r9[t6] && (this.ft.delete(t6), t6.includes("-") ? s4.removeProperty(t6) : s4[t6] = null);
      for (const t6 in r9) {
        const e10 = r9[t6];
        if (null != e10) {
          this.ft.add(t6);
          const r10 = "string" == typeof e10 && e10.endsWith(i7);
          t6.includes("-") || r10 ? s4.setProperty(t6, r10 ? e10.slice(0, -11) : e10, r10 ? n7 : "") : s4[t6] = e10;
        }
      }
      return E;
    }
  });

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/aria/aria.js
  var ARIA_PROPERTIES = [
    "role",
    "ariaAtomic",
    "ariaAutoComplete",
    "ariaBusy",
    "ariaChecked",
    "ariaColCount",
    "ariaColIndex",
    "ariaColSpan",
    "ariaCurrent",
    "ariaDisabled",
    "ariaExpanded",
    "ariaHasPopup",
    "ariaHidden",
    "ariaInvalid",
    "ariaKeyShortcuts",
    "ariaLabel",
    "ariaLevel",
    "ariaLive",
    "ariaModal",
    "ariaMultiLine",
    "ariaMultiSelectable",
    "ariaOrientation",
    "ariaPlaceholder",
    "ariaPosInSet",
    "ariaPressed",
    "ariaReadOnly",
    "ariaRequired",
    "ariaRoleDescription",
    "ariaRowCount",
    "ariaRowIndex",
    "ariaRowSpan",
    "ariaSelected",
    "ariaSetSize",
    "ariaSort",
    "ariaValueMax",
    "ariaValueMin",
    "ariaValueNow",
    "ariaValueText"
  ];
  var ARIA_ATTRIBUTES = ARIA_PROPERTIES.map(ariaPropertyToAttribute);
  function isAriaAttribute(attribute) {
    return ARIA_ATTRIBUTES.includes(attribute);
  }
  function ariaPropertyToAttribute(property) {
    return property.replace("aria", "aria-").replace(/Elements?/g, "").toLowerCase();
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/aria/delegate.js
  var privateIgnoreAttributeChangesFor = Symbol("privateIgnoreAttributeChangesFor");
  function mixinDelegatesAria(base) {
    var _a3;
    if (o7) {
      return base;
    }
    class WithDelegatesAriaElement extends base {
      constructor() {
        super(...arguments);
        this[_a3] = /* @__PURE__ */ new Set();
      }
      attributeChangedCallback(name, oldValue, newValue) {
        if (!isAriaAttribute(name)) {
          super.attributeChangedCallback(name, oldValue, newValue);
          return;
        }
        if (this[privateIgnoreAttributeChangesFor].has(name)) {
          return;
        }
        this[privateIgnoreAttributeChangesFor].add(name);
        this.removeAttribute(name);
        this[privateIgnoreAttributeChangesFor].delete(name);
        const dataProperty = ariaAttributeToDataProperty(name);
        if (newValue === null) {
          delete this.dataset[dataProperty];
        } else {
          this.dataset[dataProperty] = newValue;
        }
        this.requestUpdate(ariaAttributeToDataProperty(name), oldValue);
      }
      getAttribute(name) {
        if (isAriaAttribute(name)) {
          return super.getAttribute(ariaAttributeToDataAttribute(name));
        }
        return super.getAttribute(name);
      }
      removeAttribute(name) {
        super.removeAttribute(name);
        if (isAriaAttribute(name)) {
          super.removeAttribute(ariaAttributeToDataAttribute(name));
          this.requestUpdate();
        }
      }
    }
    _a3 = privateIgnoreAttributeChangesFor;
    setupDelegatesAriaProperties(WithDelegatesAriaElement);
    return WithDelegatesAriaElement;
  }
  function setupDelegatesAriaProperties(ctor) {
    for (const ariaProperty of ARIA_PROPERTIES) {
      const ariaAttribute = ariaPropertyToAttribute(ariaProperty);
      const dataAttribute = ariaAttributeToDataAttribute(ariaAttribute);
      const dataProperty = ariaAttributeToDataProperty(ariaAttribute);
      ctor.createProperty(ariaProperty, {
        attribute: ariaAttribute,
        noAccessor: true
      });
      ctor.createProperty(Symbol(dataAttribute), {
        attribute: dataAttribute,
        noAccessor: true
      });
      Object.defineProperty(ctor.prototype, ariaProperty, {
        configurable: true,
        enumerable: true,
        get() {
          return this.dataset[dataProperty] ?? null;
        },
        set(value) {
          const prevValue = this.dataset[dataProperty] ?? null;
          if (value === prevValue) {
            return;
          }
          if (value === null) {
            delete this.dataset[dataProperty];
          } else {
            this.dataset[dataProperty] = value;
          }
          this.requestUpdate(ariaProperty, prevValue);
        }
      });
    }
  }
  function ariaAttributeToDataAttribute(ariaAttribute) {
    return `data-${ariaAttribute}`;
  }
  function ariaAttributeToDataProperty(ariaAttribute) {
    return ariaAttribute.replace(/-\w/, (dashLetter) => dashLetter[1].toUpperCase());
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/controller/string-converter.js
  var stringConverter = {
    fromAttribute(value) {
      return value ?? "";
    },
    toAttribute(value) {
      return value || null;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/events/redispatch-event.js
  function redispatchEvent(element, event) {
    if (event.bubbles && (!element.shadowRoot || event.composed)) {
      event.stopPropagation();
    }
    const copy = Reflect.construct(event.constructor, [event.type, event]);
    const dispatched = element.dispatchEvent(copy);
    if (!dispatched) {
      event.preventDefault();
    }
    return dispatched;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/element-internals.js
  var internals = Symbol("internals");
  var privateInternals = Symbol("privateInternals");
  function mixinElementInternals(base) {
    class WithElementInternalsElement extends base {
      get [internals]() {
        if (!this[privateInternals]) {
          this[privateInternals] = this.attachInternals();
        }
        return this[privateInternals];
      }
    }
    return WithElementInternalsElement;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/constraint-validation.js
  var createValidator = Symbol("createValidator");
  var getValidityAnchor = Symbol("getValidityAnchor");
  var privateValidator = Symbol("privateValidator");
  var privateSyncValidity = Symbol("privateSyncValidity");
  var privateCustomValidationMessage = Symbol("privateCustomValidationMessage");
  function mixinConstraintValidation(base) {
    var _a3;
    class ConstraintValidationElement extends base {
      constructor() {
        super(...arguments);
        this[_a3] = "";
      }
      get validity() {
        this[privateSyncValidity]();
        return this[internals].validity;
      }
      get validationMessage() {
        this[privateSyncValidity]();
        return this[internals].validationMessage;
      }
      get willValidate() {
        this[privateSyncValidity]();
        return this[internals].willValidate;
      }
      checkValidity() {
        this[privateSyncValidity]();
        return this[internals].checkValidity();
      }
      reportValidity() {
        this[privateSyncValidity]();
        return this[internals].reportValidity();
      }
      setCustomValidity(error) {
        this[privateCustomValidationMessage] = error;
        this[privateSyncValidity]();
      }
      requestUpdate(name, oldValue, options) {
        super.requestUpdate(name, oldValue, options);
        this[privateSyncValidity]();
      }
      firstUpdated(changed) {
        super.firstUpdated(changed);
        this[privateSyncValidity]();
      }
      [(_a3 = privateCustomValidationMessage, privateSyncValidity)]() {
        if (o7) {
          return;
        }
        if (!this[privateValidator]) {
          this[privateValidator] = this[createValidator]();
        }
        const { validity, validationMessage: nonCustomValidationMessage } = this[privateValidator].getValidity();
        const customError = !!this[privateCustomValidationMessage];
        const validationMessage = this[privateCustomValidationMessage] || nonCustomValidationMessage;
        this[internals].setValidity({ ...validity, customError }, validationMessage, this[getValidityAnchor]() ?? void 0);
      }
      [createValidator]() {
        throw new Error("Implement [createValidator]");
      }
      [getValidityAnchor]() {
        throw new Error("Implement [getValidityAnchor]");
      }
    }
    return ConstraintValidationElement;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/form-associated.js
  var getFormValue = Symbol("getFormValue");
  var getFormState = Symbol("getFormState");
  function mixinFormAssociated(base) {
    class FormAssociatedElement extends base {
      get form() {
        return this[internals].form;
      }
      get labels() {
        return this[internals].labels;
      }
      // Use @property for the `name` and `disabled` properties to add them to the
      // `observedAttributes` array and trigger `attributeChangedCallback()`.
      //
      // We don't use Lit's default getter/setter (`noAccessor: true`) because
      // the attributes need to be updated synchronously to work with synchronous
      // form APIs, and Lit updates attributes async by default.
      get name() {
        return this.getAttribute("name") ?? "";
      }
      set name(name) {
        this.setAttribute("name", name);
      }
      get disabled() {
        return this.hasAttribute("disabled");
      }
      set disabled(disabled) {
        this.toggleAttribute("disabled", disabled);
      }
      attributeChangedCallback(name, old, value) {
        if (name === "name" || name === "disabled") {
          const oldValue = name === "disabled" ? old !== null : old;
          this.requestUpdate(name, oldValue);
          return;
        }
        super.attributeChangedCallback(name, old, value);
      }
      requestUpdate(name, oldValue, options) {
        super.requestUpdate(name, oldValue, options);
        this[internals].setFormValue(this[getFormValue](), this[getFormState]());
      }
      [getFormValue]() {
        throw new Error("Implement [getFormValue]");
      }
      [getFormState]() {
        return this[getFormValue]();
      }
      formDisabledCallback(disabled) {
        this.disabled = disabled;
      }
    }
    FormAssociatedElement.formAssociated = true;
    __decorate([
      n3({ noAccessor: true })
    ], FormAssociatedElement.prototype, "name", null);
    __decorate([
      n3({ type: Boolean, noAccessor: true })
    ], FormAssociatedElement.prototype, "disabled", null);
    return FormAssociatedElement;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/on-report-validity.js
  var onReportValidity = Symbol("onReportValidity");
  var privateCleanupFormListeners = Symbol("privateCleanupFormListeners");
  var privateDoNotReportInvalid = Symbol("privateDoNotReportInvalid");
  var privateIsSelfReportingValidity = Symbol("privateIsSelfReportingValidity");
  var privateCallOnReportValidity = Symbol("privateCallOnReportValidity");
  function mixinOnReportValidity(base) {
    var _a3, _b, _c;
    class OnReportValidityElement extends base {
      // Mixins must have a constructor with `...args: any[]`
      // tslint:disable-next-line:no-any
      constructor(...args) {
        super(...args);
        this[_a3] = new AbortController();
        this[_b] = false;
        this[_c] = false;
        if (o7) {
          return;
        }
        this.addEventListener("invalid", (invalidEvent) => {
          if (this[privateDoNotReportInvalid] || !invalidEvent.isTrusted) {
            return;
          }
          this.addEventListener("invalid", () => {
            this[privateCallOnReportValidity](invalidEvent);
          }, { once: true });
        }, {
          // Listen during the capture phase, which will happen before the
          // bubbling phase. That way, we can add a final event listener that
          // will run after other event listeners, and we can check if it was
          // default prevented. This works because invalid does not bubble.
          capture: true
        });
      }
      checkValidity() {
        this[privateDoNotReportInvalid] = true;
        const valid = super.checkValidity();
        this[privateDoNotReportInvalid] = false;
        return valid;
      }
      reportValidity() {
        this[privateIsSelfReportingValidity] = true;
        const valid = super.reportValidity();
        if (valid) {
          this[privateCallOnReportValidity](null);
        }
        this[privateIsSelfReportingValidity] = false;
        return valid;
      }
      [(_a3 = privateCleanupFormListeners, _b = privateDoNotReportInvalid, _c = privateIsSelfReportingValidity, privateCallOnReportValidity)](invalidEvent) {
        const wasCanceled = invalidEvent == null ? void 0 : invalidEvent.defaultPrevented;
        if (wasCanceled) {
          return;
        }
        this[onReportValidity](invalidEvent);
        const implementationCanceledFocus = !wasCanceled && (invalidEvent == null ? void 0 : invalidEvent.defaultPrevented);
        if (!implementationCanceledFocus) {
          return;
        }
        if (this[privateIsSelfReportingValidity] || isFirstInvalidControlInForm(this[internals].form, this)) {
          this.focus();
        }
      }
      [onReportValidity](invalidEvent) {
        throw new Error("Implement [onReportValidity]");
      }
      formAssociatedCallback(form) {
        if (super.formAssociatedCallback) {
          super.formAssociatedCallback(form);
        }
        this[privateCleanupFormListeners].abort();
        if (!form) {
          return;
        }
        this[privateCleanupFormListeners] = new AbortController();
        addFormReportValidListener(this, form, () => {
          this[privateCallOnReportValidity](null);
        }, this[privateCleanupFormListeners].signal);
      }
    }
    return OnReportValidityElement;
  }
  function addFormReportValidListener(control, form, onControlValid, cleanup) {
    const validateHooks = getFormValidateHooks(form);
    let controlFiredInvalid = false;
    let cleanupInvalidListener;
    let isNextSubmitFromHook = false;
    validateHooks.addEventListener("before", () => {
      isNextSubmitFromHook = true;
      cleanupInvalidListener = new AbortController();
      controlFiredInvalid = false;
      control.addEventListener("invalid", () => {
        controlFiredInvalid = true;
      }, {
        signal: cleanupInvalidListener.signal
      });
    }, { signal: cleanup });
    validateHooks.addEventListener("after", () => {
      isNextSubmitFromHook = false;
      cleanupInvalidListener == null ? void 0 : cleanupInvalidListener.abort();
      if (controlFiredInvalid) {
        return;
      }
      onControlValid();
    }, { signal: cleanup });
    form.addEventListener("submit", () => {
      if (isNextSubmitFromHook) {
        return;
      }
      onControlValid();
    }, {
      signal: cleanup
    });
  }
  var FORM_VALIDATE_HOOKS = /* @__PURE__ */ new WeakMap();
  function getFormValidateHooks(form) {
    if (!FORM_VALIDATE_HOOKS.has(form)) {
      const hooks = new EventTarget();
      FORM_VALIDATE_HOOKS.set(form, hooks);
      for (const methodName of ["reportValidity", "requestSubmit"]) {
        const superMethod = form[methodName];
        form[methodName] = function() {
          hooks.dispatchEvent(new Event("before"));
          const result = Reflect.apply(superMethod, this, arguments);
          hooks.dispatchEvent(new Event("after"));
          return result;
        };
      }
    }
    return FORM_VALIDATE_HOOKS.get(form);
  }
  function isFirstInvalidControlInForm(form, control) {
    if (!form) {
      return true;
    }
    let firstInvalidControl;
    for (const element of form.elements) {
      if (element.matches(":invalid")) {
        firstInvalidControl = element;
        break;
      }
    }
    return firstInvalidControl === control;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/validators/validator.js
  var Validator = class {
    /**
     * Creates a new validator.
     *
     * @param getCurrentState A callback that returns the current state of
     *     constraint validation-related properties.
     */
    constructor(getCurrentState) {
      this.getCurrentState = getCurrentState;
      this.currentValidity = {
        validity: {},
        validationMessage: ""
      };
    }
    /**
     * Returns the current `ValidityStateFlags` and validation message for the
     * validator.
     *
     * If the constraint validation state has not changed, this will return a
     * cached result. This is important since `getValidity()` can be called
     * frequently in response to synchronous property changes.
     *
     * @return The current validity and validation message.
     */
    getValidity() {
      const state = this.getCurrentState();
      const hasStateChanged = !this.prevState || !this.equals(this.prevState, state);
      if (!hasStateChanged) {
        return this.currentValidity;
      }
      const { validity, validationMessage } = this.computeValidity(state);
      this.prevState = this.copy(state);
      this.currentValidity = {
        validationMessage,
        validity: {
          // Change any `ValidityState` instances into `ValidityStateFlags` since
          // `ValidityState` cannot be easily `{...spread}`.
          badInput: validity.badInput,
          customError: validity.customError,
          patternMismatch: validity.patternMismatch,
          rangeOverflow: validity.rangeOverflow,
          rangeUnderflow: validity.rangeUnderflow,
          stepMismatch: validity.stepMismatch,
          tooLong: validity.tooLong,
          tooShort: validity.tooShort,
          typeMismatch: validity.typeMismatch,
          valueMissing: validity.valueMissing
        }
      };
      return this.currentValidity;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/validators/text-field-validator.js
  var TextFieldValidator = class extends Validator {
    computeValidity({ state, renderedControl }) {
      let inputOrTextArea = renderedControl;
      if (isInputState(state) && !inputOrTextArea) {
        inputOrTextArea = this.inputControl || document.createElement("input");
        this.inputControl = inputOrTextArea;
      } else if (!inputOrTextArea) {
        inputOrTextArea = this.textAreaControl || document.createElement("textarea");
        this.textAreaControl = inputOrTextArea;
      }
      const input = isInputState(state) ? inputOrTextArea : null;
      if (input) {
        input.type = state.type;
      }
      if (inputOrTextArea.value !== state.value) {
        inputOrTextArea.value = state.value;
      }
      inputOrTextArea.required = state.required;
      if (input) {
        const inputState = state;
        if (inputState.pattern) {
          input.pattern = inputState.pattern;
        } else {
          input.removeAttribute("pattern");
        }
        if (inputState.min) {
          input.min = inputState.min;
        } else {
          input.removeAttribute("min");
        }
        if (inputState.max) {
          input.max = inputState.max;
        } else {
          input.removeAttribute("max");
        }
        if (inputState.step) {
          input.step = inputState.step;
        } else {
          input.removeAttribute("step");
        }
      }
      if ((state.minLength ?? -1) > -1) {
        inputOrTextArea.setAttribute("minlength", String(state.minLength));
      } else {
        inputOrTextArea.removeAttribute("minlength");
      }
      if ((state.maxLength ?? -1) > -1) {
        inputOrTextArea.setAttribute("maxlength", String(state.maxLength));
      } else {
        inputOrTextArea.removeAttribute("maxlength");
      }
      return {
        validity: inputOrTextArea.validity,
        validationMessage: inputOrTextArea.validationMessage
      };
    }
    equals({ state: prev }, { state: next }) {
      const inputOrTextAreaEqual = prev.type === next.type && prev.value === next.value && prev.required === next.required && prev.minLength === next.minLength && prev.maxLength === next.maxLength;
      if (!isInputState(prev) || !isInputState(next)) {
        return inputOrTextAreaEqual;
      }
      return inputOrTextAreaEqual && prev.pattern === next.pattern && prev.min === next.min && prev.max === next.max && prev.step === next.step;
    }
    copy({ state }) {
      return {
        state: isInputState(state) ? this.copyInput(state) : this.copyTextArea(state),
        renderedControl: null
      };
    }
    copyInput(state) {
      const { type, pattern, min, max, step } = state;
      return {
        ...this.copySharedState(state),
        type,
        pattern,
        min,
        max,
        step
      };
    }
    copyTextArea(state) {
      return {
        ...this.copySharedState(state),
        type: state.type
      };
    }
    copySharedState({ value, required, minLength, maxLength }) {
      return { value, required, minLength, maxLength };
    }
  };
  function isInputState(state) {
    return state.type !== "textarea";
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/textfield/internal/text-field.js
  var textFieldBaseClass = mixinDelegatesAria(mixinOnReportValidity(mixinConstraintValidation(mixinFormAssociated(mixinElementInternals(i4)))));
  var TextField = class extends textFieldBaseClass {
    constructor() {
      super(...arguments);
      this.error = false;
      this.errorText = "";
      this.label = "";
      this.noAsterisk = false;
      this.required = false;
      this.value = "";
      this.prefixText = "";
      this.suffixText = "";
      this.hasLeadingIcon = false;
      this.hasTrailingIcon = false;
      this.supportingText = "";
      this.textDirection = "";
      this.rows = 2;
      this.cols = 20;
      this.inputMode = "";
      this.max = "";
      this.maxLength = -1;
      this.min = "";
      this.minLength = -1;
      this.noSpinner = false;
      this.pattern = "";
      this.placeholder = "";
      this.readOnly = false;
      this.multiple = false;
      this.step = "";
      this.type = "text";
      this.autocomplete = "";
      this.dirty = false;
      this.focused = false;
      this.nativeError = false;
      this.nativeErrorText = "";
    }
    /**
     * Gets or sets the direction in which selection occurred.
     */
    get selectionDirection() {
      return this.getInputOrTextarea().selectionDirection;
    }
    set selectionDirection(value) {
      this.getInputOrTextarea().selectionDirection = value;
    }
    /**
     * Gets or sets the end position or offset of a text selection.
     */
    get selectionEnd() {
      return this.getInputOrTextarea().selectionEnd;
    }
    set selectionEnd(value) {
      this.getInputOrTextarea().selectionEnd = value;
    }
    /**
     * Gets or sets the starting position or offset of a text selection.
     */
    get selectionStart() {
      return this.getInputOrTextarea().selectionStart;
    }
    set selectionStart(value) {
      this.getInputOrTextarea().selectionStart = value;
    }
    /**
     * The text field's value as a number.
     */
    get valueAsNumber() {
      const input = this.getInput();
      if (!input) {
        return NaN;
      }
      return input.valueAsNumber;
    }
    set valueAsNumber(value) {
      const input = this.getInput();
      if (!input) {
        return;
      }
      input.valueAsNumber = value;
      this.value = input.value;
    }
    /**
     * The text field's value as a Date.
     */
    get valueAsDate() {
      const input = this.getInput();
      if (!input) {
        return null;
      }
      return input.valueAsDate;
    }
    set valueAsDate(value) {
      const input = this.getInput();
      if (!input) {
        return;
      }
      input.valueAsDate = value;
      this.value = input.value;
    }
    get hasError() {
      return this.error || this.nativeError;
    }
    /**
     * Selects all the text in the text field.
     *
     * https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/select
     */
    select() {
      this.getInputOrTextarea().select();
    }
    setRangeText(...args) {
      this.getInputOrTextarea().setRangeText(...args);
      this.value = this.getInputOrTextarea().value;
    }
    /**
     * Sets the start and end positions of a selection in the text field.
     *
     * https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/setSelectionRange
     *
     * @param start The offset into the text field for the start of the selection.
     * @param end The offset into the text field for the end of the selection.
     * @param direction The direction in which the selection is performed.
     */
    setSelectionRange(start, end, direction) {
      this.getInputOrTextarea().setSelectionRange(start, end, direction);
    }
    /**
     * Shows the browser picker for an input element of type "date", "time", etc.
     *
     * For a full list of supported types, see:
     * https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/showPicker#browser_compatibility
     *
     * https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/showPicker
     */
    showPicker() {
      const input = this.getInput();
      if (!input) {
        return;
      }
      input.showPicker();
    }
    /**
     * Decrements the value of a numeric type text field by `step` or `n` `step`
     * number of times.
     *
     * https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/stepDown
     *
     * @param stepDecrement The number of steps to decrement, defaults to 1.
     */
    stepDown(stepDecrement) {
      const input = this.getInput();
      if (!input) {
        return;
      }
      input.stepDown(stepDecrement);
      this.value = input.value;
    }
    /**
     * Increments the value of a numeric type text field by `step` or `n` `step`
     * number of times.
     *
     * https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/stepUp
     *
     * @param stepIncrement The number of steps to increment, defaults to 1.
     */
    stepUp(stepIncrement) {
      const input = this.getInput();
      if (!input) {
        return;
      }
      input.stepUp(stepIncrement);
      this.value = input.value;
    }
    /**
     * Reset the text field to its default value.
     */
    reset() {
      this.dirty = false;
      this.value = this.getAttribute("value") ?? "";
      this.nativeError = false;
      this.nativeErrorText = "";
    }
    attributeChangedCallback(attribute, newValue, oldValue) {
      if (attribute === "value" && this.dirty) {
        return;
      }
      super.attributeChangedCallback(attribute, newValue, oldValue);
    }
    render() {
      const classes = {
        "disabled": this.disabled,
        "error": !this.disabled && this.hasError,
        "textarea": this.type === "textarea",
        "no-spinner": this.noSpinner
      };
      return b2`
      <span class="text-field ${e8(classes)}">
        ${this.renderField()}
      </span>
    `;
    }
    updated(changedProperties) {
      const value = this.getInputOrTextarea().value;
      if (this.value !== value) {
        this.value = value;
      }
    }
    renderField() {
      return u3`<${this.fieldTag}
      class="field"
      count=${this.value.length}
      ?disabled=${this.disabled}
      ?error=${this.hasError}
      error-text=${this.getErrorText()}
      ?focused=${this.focused}
      ?has-end=${this.hasTrailingIcon}
      ?has-start=${this.hasLeadingIcon}
      label=${this.label}
      ?no-asterisk=${this.noAsterisk}
      max=${this.maxLength}
      ?populated=${!!this.value}
      ?required=${this.required}
      ?resizable=${this.type === "textarea"}
      supporting-text=${this.supportingText}
    >
      ${this.renderLeadingIcon()}
      ${this.renderInputOrTextarea()}
      ${this.renderTrailingIcon()}
      <div id="description" slot="aria-describedby"></div>
      <slot name="container" slot="container"></slot>
    </${this.fieldTag}>`;
    }
    renderLeadingIcon() {
      return b2`
      <span class="icon leading" slot="start">
        <slot name="leading-icon" @slotchange=${this.handleIconChange}></slot>
      </span>
    `;
    }
    renderTrailingIcon() {
      return b2`
      <span class="icon trailing" slot="end">
        <slot name="trailing-icon" @slotchange=${this.handleIconChange}></slot>
      </span>
    `;
    }
    renderInputOrTextarea() {
      const style = { "direction": this.textDirection };
      const ariaLabel = this.ariaLabel || this.label || A;
      const autocomplete = this.autocomplete;
      const hasMaxLength = (this.maxLength ?? -1) > -1;
      const hasMinLength = (this.minLength ?? -1) > -1;
      if (this.type === "textarea") {
        return b2`
        <textarea
          class="input"
          style=${o9(style)}
          aria-describedby="description"
          aria-invalid=${this.hasError}
          aria-label=${ariaLabel}
          autocomplete=${autocomplete || A}
          name=${this.name || A}
          ?disabled=${this.disabled}
          maxlength=${hasMaxLength ? this.maxLength : A}
          minlength=${hasMinLength ? this.minLength : A}
          placeholder=${this.placeholder || A}
          ?readonly=${this.readOnly}
          ?required=${this.required}
          rows=${this.rows}
          cols=${this.cols}
          .value=${l4(this.value)}
          @change=${this.redispatchEvent}
          @focus=${this.handleFocusChange}
          @blur=${this.handleFocusChange}
          @input=${this.handleInput}
          @select=${this.redispatchEvent}></textarea>
      `;
      }
      const prefix = this.renderPrefix();
      const suffix = this.renderSuffix();
      const inputMode = this.inputMode;
      return b2`
      <div class="input-wrapper">
        ${prefix}
        <input
          class="input"
          style=${o9(style)}
          aria-describedby="description"
          aria-invalid=${this.hasError}
          aria-label=${ariaLabel}
          autocomplete=${autocomplete || A}
          name=${this.name || A}
          ?disabled=${this.disabled}
          inputmode=${inputMode || A}
          max=${this.max || A}
          maxlength=${hasMaxLength ? this.maxLength : A}
          min=${this.min || A}
          minlength=${hasMinLength ? this.minLength : A}
          pattern=${this.pattern || A}
          placeholder=${this.placeholder || A}
          ?readonly=${this.readOnly}
          ?required=${this.required}
          ?multiple=${this.multiple}
          step=${this.step || A}
          type=${this.type}
          .value=${l4(this.value)}
          @change=${this.redispatchEvent}
          @focus=${this.handleFocusChange}
          @blur=${this.handleFocusChange}
          @input=${this.handleInput}
          @select=${this.redispatchEvent} />
        ${suffix}
      </div>
    `;
    }
    renderPrefix() {
      return this.renderAffix(
        this.prefixText,
        /* isSuffix */
        false
      );
    }
    renderSuffix() {
      return this.renderAffix(
        this.suffixText,
        /* isSuffix */
        true
      );
    }
    renderAffix(text, isSuffix) {
      if (!text) {
        return A;
      }
      const classes = {
        "suffix": isSuffix,
        "prefix": !isSuffix
      };
      return b2`<span class="${e8(classes)}">${text}</span>`;
    }
    getErrorText() {
      return this.error ? this.errorText : this.nativeErrorText;
    }
    handleFocusChange() {
      var _a3;
      this.focused = ((_a3 = this.inputOrTextarea) == null ? void 0 : _a3.matches(":focus")) ?? false;
    }
    handleInput(event) {
      this.dirty = true;
      this.value = event.target.value;
    }
    redispatchEvent(event) {
      redispatchEvent(this, event);
    }
    getInputOrTextarea() {
      if (!this.inputOrTextarea) {
        this.connectedCallback();
        this.scheduleUpdate();
      }
      if (this.isUpdatePending) {
        this.scheduleUpdate();
      }
      return this.inputOrTextarea;
    }
    getInput() {
      if (this.type === "textarea") {
        return null;
      }
      return this.getInputOrTextarea();
    }
    handleIconChange() {
      this.hasLeadingIcon = this.leadingIcons.length > 0;
      this.hasTrailingIcon = this.trailingIcons.length > 0;
    }
    [getFormValue]() {
      return this.value;
    }
    formResetCallback() {
      this.reset();
    }
    formStateRestoreCallback(state) {
      this.value = state;
    }
    focus() {
      this.getInputOrTextarea().focus();
    }
    [createValidator]() {
      return new TextFieldValidator(() => ({
        state: this,
        renderedControl: this.inputOrTextarea
      }));
    }
    [getValidityAnchor]() {
      return this.inputOrTextarea;
    }
    [onReportValidity](invalidEvent) {
      var _a3;
      invalidEvent == null ? void 0 : invalidEvent.preventDefault();
      const prevMessage = this.getErrorText();
      this.nativeError = !!invalidEvent;
      this.nativeErrorText = this.validationMessage;
      if (prevMessage === this.getErrorText()) {
        (_a3 = this.field) == null ? void 0 : _a3.reannounceError();
      }
    }
  };
  TextField.shadowRootOptions = {
    ...i4.shadowRootOptions,
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], TextField.prototype, "error", void 0);
  __decorate([
    n3({ attribute: "error-text" })
  ], TextField.prototype, "errorText", void 0);
  __decorate([
    n3()
  ], TextField.prototype, "label", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-asterisk" })
  ], TextField.prototype, "noAsterisk", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], TextField.prototype, "required", void 0);
  __decorate([
    n3()
  ], TextField.prototype, "value", void 0);
  __decorate([
    n3({ attribute: "prefix-text" })
  ], TextField.prototype, "prefixText", void 0);
  __decorate([
    n3({ attribute: "suffix-text" })
  ], TextField.prototype, "suffixText", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "has-leading-icon" })
  ], TextField.prototype, "hasLeadingIcon", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "has-trailing-icon" })
  ], TextField.prototype, "hasTrailingIcon", void 0);
  __decorate([
    n3({ attribute: "supporting-text" })
  ], TextField.prototype, "supportingText", void 0);
  __decorate([
    n3({ attribute: "text-direction" })
  ], TextField.prototype, "textDirection", void 0);
  __decorate([
    n3({ type: Number })
  ], TextField.prototype, "rows", void 0);
  __decorate([
    n3({ type: Number })
  ], TextField.prototype, "cols", void 0);
  __decorate([
    n3({ reflect: true })
  ], TextField.prototype, "inputMode", void 0);
  __decorate([
    n3()
  ], TextField.prototype, "max", void 0);
  __decorate([
    n3({ type: Number })
  ], TextField.prototype, "maxLength", void 0);
  __decorate([
    n3()
  ], TextField.prototype, "min", void 0);
  __decorate([
    n3({ type: Number })
  ], TextField.prototype, "minLength", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-spinner" })
  ], TextField.prototype, "noSpinner", void 0);
  __decorate([
    n3()
  ], TextField.prototype, "pattern", void 0);
  __decorate([
    n3({ reflect: true, converter: stringConverter })
  ], TextField.prototype, "placeholder", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], TextField.prototype, "readOnly", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], TextField.prototype, "multiple", void 0);
  __decorate([
    n3()
  ], TextField.prototype, "step", void 0);
  __decorate([
    n3({ reflect: true })
  ], TextField.prototype, "type", void 0);
  __decorate([
    n3({ reflect: true })
  ], TextField.prototype, "autocomplete", void 0);
  __decorate([
    r4()
  ], TextField.prototype, "dirty", void 0);
  __decorate([
    r4()
  ], TextField.prototype, "focused", void 0);
  __decorate([
    r4()
  ], TextField.prototype, "nativeError", void 0);
  __decorate([
    r4()
  ], TextField.prototype, "nativeErrorText", void 0);
  __decorate([
    e4(".input")
  ], TextField.prototype, "inputOrTextarea", void 0);
  __decorate([
    e4(".field")
  ], TextField.prototype, "field", void 0);
  __decorate([
    o4({ slot: "leading-icon" })
  ], TextField.prototype, "leadingIcons", void 0);
  __decorate([
    o4({ slot: "trailing-icon" })
  ], TextField.prototype, "trailingIcons", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/textfield/internal/outlined-text-field.js
  var OutlinedTextField = class extends TextField {
    constructor() {
      super(...arguments);
      this.fieldTag = i6`md-outlined-field`;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/textfield/internal/shared-styles.js
  var styles4 = i`:host{display:inline-flex;outline:none;resize:both;text-align:start;-webkit-tap-highlight-color:rgba(0,0,0,0)}.text-field,.field{width:100%}.text-field{display:inline-flex}.field{cursor:text}.disabled .field{cursor:default}.text-field,.textarea .field{resize:inherit}slot[name=container]{border-radius:inherit}.icon{color:currentColor;display:flex;align-items:center;justify-content:center;fill:currentColor;position:relative}.icon ::slotted(*){display:flex;position:absolute}[has-start] .icon.leading{font-size:var(--_leading-icon-size);height:var(--_leading-icon-size);width:var(--_leading-icon-size)}[has-end] .icon.trailing{font-size:var(--_trailing-icon-size);height:var(--_trailing-icon-size);width:var(--_trailing-icon-size)}.input-wrapper{display:flex}.input-wrapper>*{all:inherit;padding:0}.input{caret-color:var(--_caret-color);overflow-x:hidden;text-align:inherit}.input::placeholder{color:currentColor;opacity:1}.input::-webkit-calendar-picker-indicator{display:none}.input::-webkit-search-decoration,.input::-webkit-search-cancel-button{display:none}@media(forced-colors: active){.input{background:none}}.no-spinner .input::-webkit-inner-spin-button,.no-spinner .input::-webkit-outer-spin-button{display:none}.no-spinner .input[type=number]{-moz-appearance:textfield}:focus-within .input{caret-color:var(--_focus-caret-color)}.error:focus-within .input{caret-color:var(--_error-focus-caret-color)}.text-field:not(.disabled) .prefix{color:var(--_input-text-prefix-color)}.text-field:not(.disabled) .suffix{color:var(--_input-text-suffix-color)}.text-field:not(.disabled) .input::placeholder{color:var(--_input-text-placeholder-color)}.prefix,.suffix{text-wrap:nowrap;width:min-content}.prefix{padding-inline-end:var(--_input-text-prefix-trailing-space)}.suffix{padding-inline-start:var(--_input-text-suffix-leading-space)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/textfield/outlined-text-field.js
  var MdOutlinedTextField = class MdOutlinedTextField2 extends OutlinedTextField {
    constructor() {
      super(...arguments);
      this.fieldTag = i6`md-outlined-field`;
    }
  };
  MdOutlinedTextField.styles = [styles4, styles3];
  if (!customElements.get("md-outlined-text-field")) {
    MdOutlinedTextField = __decorate([
      t("md-outlined-text-field")
    ], MdOutlinedTextField);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/elevation/internal/elevation.js
  var Elevation = class extends i4 {
    connectedCallback() {
      super.connectedCallback();
      this.setAttribute("aria-hidden", "true");
    }
    render() {
      return b2`<span class="shadow"></span>`;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/elevation/internal/elevation-styles.js
  var styles5 = i`:host,.shadow,.shadow::before,.shadow::after{border-radius:inherit;inset:0;position:absolute;transition-duration:inherit;transition-property:inherit;transition-timing-function:inherit}:host{display:flex;pointer-events:none;transition-property:box-shadow,opacity}.shadow::before,.shadow::after{content:"";transition-property:box-shadow,opacity;--_level: var(--md-elevation-level, 0);--_shadow-color: var(--md-elevation-shadow-color, var(--md-sys-color-shadow, #000))}.shadow::before{box-shadow:0px calc(1px*(clamp(0,var(--_level),1) + clamp(0,var(--_level) - 3,1) + 2*clamp(0,var(--_level) - 4,1))) calc(1px*(2*clamp(0,var(--_level),1) + clamp(0,var(--_level) - 2,1) + clamp(0,var(--_level) - 4,1))) 0px var(--_shadow-color);opacity:.3}.shadow::after{box-shadow:0px calc(1px*(clamp(0,var(--_level),1) + clamp(0,var(--_level) - 1,1) + 2*clamp(0,var(--_level) - 2,3))) calc(1px*(3*clamp(0,var(--_level),2) + 2*clamp(0,var(--_level) - 2,3))) calc(1px*(clamp(0,var(--_level),4) + 2*clamp(0,var(--_level) - 4,1))) var(--_shadow-color);opacity:.15}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/elevation/elevation.js
  var MdElevation = class MdElevation2 extends Elevation {
  };
  MdElevation.styles = [styles5];
  if (!customElements.get("md-elevation")) {
    MdElevation = __decorate([
      t("md-elevation")
    ], MdElevation);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/controller/attachable-controller.js
  var ATTACHABLE_CONTROLLER = Symbol("attachableController");
  var FOR_ATTRIBUTE_OBSERVER;
  if (!o7) {
    FOR_ATTRIBUTE_OBSERVER = new MutationObserver((records) => {
      var _a3;
      for (const record of records) {
        (_a3 = record.target[ATTACHABLE_CONTROLLER]) == null ? void 0 : _a3.hostConnected();
      }
    });
  }
  var AttachableController = class {
    get htmlFor() {
      return this.host.getAttribute("for");
    }
    set htmlFor(htmlFor) {
      if (htmlFor === null) {
        this.host.removeAttribute("for");
      } else {
        this.host.setAttribute("for", htmlFor);
      }
    }
    get control() {
      if (this.host.hasAttribute("for")) {
        if (!this.htmlFor || !this.host.isConnected) {
          return null;
        }
        return this.host.getRootNode().querySelector(`#${this.htmlFor}`);
      }
      return this.currentControl || this.host.parentElement;
    }
    set control(control) {
      if (control) {
        this.attach(control);
      } else {
        this.detach();
      }
    }
    /**
     * Creates a new controller for an `Attachable` element.
     *
     * @param host The `Attachable` element.
     * @param onControlChange A callback with two parameters for the previous and
     *     next control. An `Attachable` element may perform setup or teardown
     *     logic whenever the control changes.
     */
    constructor(host, onControlChange) {
      this.host = host;
      this.onControlChange = onControlChange;
      this.currentControl = null;
      host.addController(this);
      host[ATTACHABLE_CONTROLLER] = this;
      FOR_ATTRIBUTE_OBSERVER == null ? void 0 : FOR_ATTRIBUTE_OBSERVER.observe(host, { attributeFilter: ["for"] });
    }
    attach(control) {
      if (control === this.currentControl) {
        return;
      }
      this.setCurrentControl(control);
      this.host.removeAttribute("for");
    }
    detach() {
      this.setCurrentControl(null);
      this.host.setAttribute("for", "");
    }
    /** @private */
    hostConnected() {
      this.setCurrentControl(this.control);
    }
    /** @private */
    hostDisconnected() {
      this.setCurrentControl(null);
    }
    setCurrentControl(control) {
      this.onControlChange(this.currentControl, control);
      this.currentControl = control;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/focus/internal/focus-ring.js
  var EVENTS = ["focusin", "focusout", "pointerdown"];
  var FocusRing = class extends i4 {
    constructor() {
      super(...arguments);
      this.visible = false;
      this.inward = false;
      this.attachableController = new AttachableController(this, this.onControlChange.bind(this));
    }
    get htmlFor() {
      return this.attachableController.htmlFor;
    }
    set htmlFor(htmlFor) {
      this.attachableController.htmlFor = htmlFor;
    }
    get control() {
      return this.attachableController.control;
    }
    set control(control) {
      this.attachableController.control = control;
    }
    attach(control) {
      this.attachableController.attach(control);
    }
    detach() {
      this.attachableController.detach();
    }
    connectedCallback() {
      super.connectedCallback();
      this.setAttribute("aria-hidden", "true");
    }
    /** @private */
    handleEvent(event) {
      var _a3;
      if (event[HANDLED_BY_FOCUS_RING]) {
        return;
      }
      switch (event.type) {
        default:
          return;
        case "focusin":
          this.visible = ((_a3 = this.control) == null ? void 0 : _a3.matches(":focus-visible")) ?? false;
          break;
        case "focusout":
        case "pointerdown":
          this.visible = false;
          break;
      }
      event[HANDLED_BY_FOCUS_RING] = true;
    }
    onControlChange(prev, next) {
      if (o7)
        return;
      for (const event of EVENTS) {
        prev == null ? void 0 : prev.removeEventListener(event, this);
        next == null ? void 0 : next.addEventListener(event, this);
      }
    }
    update(changed) {
      if (changed.has("visible")) {
        this.dispatchEvent(new Event("visibility-changed"));
      }
      super.update(changed);
    }
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], FocusRing.prototype, "visible", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], FocusRing.prototype, "inward", void 0);
  var HANDLED_BY_FOCUS_RING = Symbol("handledByFocusRing");

  // custom_components/smart_agent/frontend/node_modules/@material/web/focus/internal/focus-ring-styles.js
  var styles6 = i`:host{animation-delay:0s,calc(var(--md-focus-ring-duration, 600ms)*.25);animation-duration:calc(var(--md-focus-ring-duration, 600ms)*.25),calc(var(--md-focus-ring-duration, 600ms)*.75);animation-timing-function:cubic-bezier(0.2, 0, 0, 1);box-sizing:border-box;color:var(--md-focus-ring-color, var(--md-sys-color-secondary, #625b71));display:none;pointer-events:none;position:absolute}:host([visible]){display:flex}:host(:not([inward])){animation-name:outward-grow,outward-shrink;border-end-end-radius:calc(var(--md-focus-ring-shape-end-end, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) + var(--md-focus-ring-outward-offset, 2px));border-end-start-radius:calc(var(--md-focus-ring-shape-end-start, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) + var(--md-focus-ring-outward-offset, 2px));border-start-end-radius:calc(var(--md-focus-ring-shape-start-end, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) + var(--md-focus-ring-outward-offset, 2px));border-start-start-radius:calc(var(--md-focus-ring-shape-start-start, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) + var(--md-focus-ring-outward-offset, 2px));inset:calc(-1*var(--md-focus-ring-outward-offset, 2px));outline:var(--md-focus-ring-width, 3px) solid currentColor}:host([inward]){animation-name:inward-grow,inward-shrink;border-end-end-radius:calc(var(--md-focus-ring-shape-end-end, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) - var(--md-focus-ring-inward-offset, 0px));border-end-start-radius:calc(var(--md-focus-ring-shape-end-start, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) - var(--md-focus-ring-inward-offset, 0px));border-start-end-radius:calc(var(--md-focus-ring-shape-start-end, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) - var(--md-focus-ring-inward-offset, 0px));border-start-start-radius:calc(var(--md-focus-ring-shape-start-start, var(--md-focus-ring-shape, var(--md-sys-shape-corner-full, 9999px))) - var(--md-focus-ring-inward-offset, 0px));border:var(--md-focus-ring-width, 3px) solid currentColor;inset:var(--md-focus-ring-inward-offset, 0px)}@keyframes outward-grow{from{outline-width:0}to{outline-width:var(--md-focus-ring-active-width, 8px)}}@keyframes outward-shrink{from{outline-width:var(--md-focus-ring-active-width, 8px)}}@keyframes inward-grow{from{border-width:0}to{border-width:var(--md-focus-ring-active-width, 8px)}}@keyframes inward-shrink{from{border-width:var(--md-focus-ring-active-width, 8px)}}@media(prefers-reduced-motion){:host{animation:none}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/focus/md-focus-ring.js
  var MdFocusRing = class MdFocusRing2 extends FocusRing {
  };
  MdFocusRing.styles = [styles6];
  if (!customElements.get("md-focus-ring")) {
    MdFocusRing = __decorate([
      t("md-focus-ring")
    ], MdFocusRing);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/list/internal/list-navigation-helpers.js
  function activateFirstItem(items, isActivatable = isItemNotDisabled) {
    const firstItem = getFirstActivatableItem(items, isActivatable);
    if (firstItem) {
      firstItem.tabIndex = 0;
      firstItem.focus();
    }
    return firstItem;
  }
  function activateLastItem(items, isActivatable = isItemNotDisabled) {
    const lastItem = getLastActivatableItem(items, isActivatable);
    if (lastItem) {
      lastItem.tabIndex = 0;
      lastItem.focus();
    }
    return lastItem;
  }
  function getActiveItem(items, isActivatable = isItemNotDisabled) {
    for (let i8 = 0; i8 < items.length; i8++) {
      const item = items[i8];
      if (item.tabIndex === 0 && isActivatable(item)) {
        return {
          item,
          index: i8
        };
      }
    }
    return null;
  }
  function getFirstActivatableItem(items, isActivatable = isItemNotDisabled) {
    for (const item of items) {
      if (isActivatable(item)) {
        return item;
      }
    }
    return null;
  }
  function getLastActivatableItem(items, isActivatable = isItemNotDisabled) {
    for (let i8 = items.length - 1; i8 >= 0; i8--) {
      const item = items[i8];
      if (isActivatable(item)) {
        return item;
      }
    }
    return null;
  }
  function getNextItem(items, index, isActivatable = isItemNotDisabled, wrap = true) {
    for (let i8 = 1; i8 < items.length; i8++) {
      const nextIndex = (i8 + index) % items.length;
      if (nextIndex < index && !wrap) {
        return null;
      }
      const item = items[nextIndex];
      if (isActivatable(item)) {
        return item;
      }
    }
    return items[index] ? items[index] : null;
  }
  function getPrevItem(items, index, isActivatable = isItemNotDisabled, wrap = true) {
    for (let i8 = 1; i8 < items.length; i8++) {
      const prevIndex = (index - i8 + items.length) % items.length;
      if (prevIndex > index && !wrap) {
        return null;
      }
      const item = items[prevIndex];
      if (isActivatable(item)) {
        return item;
      }
    }
    return items[index] ? items[index] : null;
  }
  function activateNextItem(items, activeItemRecord, isActivatable = isItemNotDisabled, wrap = true) {
    if (activeItemRecord) {
      const next = getNextItem(items, activeItemRecord.index, isActivatable, wrap);
      if (next) {
        next.tabIndex = 0;
        next.focus();
      }
      return next;
    } else {
      return activateFirstItem(items, isActivatable);
    }
  }
  function activatePreviousItem(items, activeItemRecord, isActivatable = isItemNotDisabled, wrap = true) {
    if (activeItemRecord) {
      const prev = getPrevItem(items, activeItemRecord.index, isActivatable, wrap);
      if (prev) {
        prev.tabIndex = 0;
        prev.focus();
      }
      return prev;
    } else {
      return activateLastItem(items, isActivatable);
    }
  }
  function isItemNotDisabled(item) {
    return !item.disabled;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/list/internal/list-controller.js
  var NavigableKeys = {
    ArrowDown: "ArrowDown",
    ArrowLeft: "ArrowLeft",
    ArrowUp: "ArrowUp",
    ArrowRight: "ArrowRight",
    Home: "Home",
    End: "End"
  };
  var ListController = class {
    constructor(config) {
      this.handleKeydown = (event) => {
        const key = event.key;
        if (event.defaultPrevented || !this.isNavigableKey(key)) {
          return;
        }
        const items = this.items;
        if (!items.length) {
          return;
        }
        const activeItemRecord = getActiveItem(items, this.isActivatable);
        event.preventDefault();
        const isRtl3 = this.isRtl();
        const inlinePrevious = isRtl3 ? NavigableKeys.ArrowRight : NavigableKeys.ArrowLeft;
        const inlineNext = isRtl3 ? NavigableKeys.ArrowLeft : NavigableKeys.ArrowRight;
        let nextActiveItem = null;
        switch (key) {
          case NavigableKeys.ArrowDown:
          case inlineNext:
            nextActiveItem = activateNextItem(items, activeItemRecord, this.isActivatable, this.wrapNavigation());
            break;
          case NavigableKeys.ArrowUp:
          case inlinePrevious:
            nextActiveItem = activatePreviousItem(items, activeItemRecord, this.isActivatable, this.wrapNavigation());
            break;
          case NavigableKeys.Home:
            nextActiveItem = activateFirstItem(items, this.isActivatable);
            break;
          case NavigableKeys.End:
            nextActiveItem = activateLastItem(items, this.isActivatable);
            break;
          default:
            break;
        }
        if (nextActiveItem && activeItemRecord && activeItemRecord.item !== nextActiveItem) {
          activeItemRecord.item.tabIndex = -1;
        }
      };
      this.onDeactivateItems = () => {
        const items = this.items;
        for (const item of items) {
          this.deactivateItem(item);
        }
      };
      this.onRequestActivation = (event) => {
        this.onDeactivateItems();
        const target = event.target;
        this.activateItem(target);
        target.focus();
      };
      this.onSlotchange = () => {
        const items = this.items;
        let encounteredActivated = false;
        for (const item of items) {
          const isActivated = !item.disabled && item.tabIndex > -1;
          if (isActivated && !encounteredActivated) {
            encounteredActivated = true;
            item.tabIndex = 0;
            continue;
          }
          item.tabIndex = -1;
        }
        if (encounteredActivated) {
          return;
        }
        const firstActivatableItem = getFirstActivatableItem(items, this.isActivatable);
        if (!firstActivatableItem) {
          return;
        }
        firstActivatableItem.tabIndex = 0;
      };
      const { isItem, getPossibleItems, isRtl: isRtl2, deactivateItem, activateItem, isNavigableKey, isActivatable, wrapNavigation } = config;
      this.isItem = isItem;
      this.getPossibleItems = getPossibleItems;
      this.isRtl = isRtl2;
      this.deactivateItem = deactivateItem;
      this.activateItem = activateItem;
      this.isNavigableKey = isNavigableKey;
      this.isActivatable = isActivatable;
      this.wrapNavigation = wrapNavigation ?? (() => true);
    }
    /**
     * The items being managed by the list. Additionally, attempts to see if the
     * object has a sub-item in the `.item` property.
     */
    get items() {
      const maybeItems = this.getPossibleItems();
      const items = [];
      for (const itemOrParent of maybeItems) {
        const isItem = this.isItem(itemOrParent);
        if (isItem) {
          items.push(itemOrParent);
          continue;
        }
        const subItem = itemOrParent.item;
        if (subItem && this.isItem(subItem)) {
          items.push(subItem);
        }
      }
      return items;
    }
    /**
     * Activates the next item in the list. If at the end of the list, the first
     * item will be activated.
     *
     * @return The activated list item or `null` if there are no items.
     */
    activateNextItem() {
      const items = this.items;
      const activeItemRecord = getActiveItem(items, this.isActivatable);
      if (activeItemRecord) {
        activeItemRecord.item.tabIndex = -1;
      }
      return activateNextItem(items, activeItemRecord, this.isActivatable, this.wrapNavigation());
    }
    /**
     * Activates the previous item in the list. If at the start of the list, the
     * last item will be activated.
     *
     * @return The activated list item or `null` if there are no items.
     */
    activatePreviousItem() {
      const items = this.items;
      const activeItemRecord = getActiveItem(items, this.isActivatable);
      if (activeItemRecord) {
        activeItemRecord.item.tabIndex = -1;
      }
      return activatePreviousItem(items, activeItemRecord, this.isActivatable, this.wrapNavigation());
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/internal/controllers/shared.js
  function createCloseMenuEvent(initiator, reason) {
    return new CustomEvent("close-menu", {
      bubbles: true,
      composed: true,
      detail: { initiator, reason, itemPath: [initiator] }
    });
  }
  var createDefaultCloseMenuEvent = createCloseMenuEvent;
  var SelectionKey = {
    SPACE: "Space",
    ENTER: "Enter"
  };
  var CloseReason = {
    CLICK_SELECTION: "click-selection",
    KEYDOWN: "keydown"
  };
  var KeydownCloseKey = {
    ESCAPE: "Escape",
    SPACE: SelectionKey.SPACE,
    ENTER: SelectionKey.ENTER
  };
  function isClosableKey(code) {
    return Object.values(KeydownCloseKey).some((value) => value === code);
  }
  function isSelectableKey(code) {
    return Object.values(SelectionKey).some((value) => value === code);
  }
  function isElementInSubtree(target, container) {
    const focusEv = new Event("md-contains", { bubbles: true, composed: true });
    let composedPath = [];
    const listener = (ev) => {
      composedPath = ev.composedPath();
    };
    container.addEventListener("md-contains", listener);
    target.dispatchEvent(focusEv);
    container.removeEventListener("md-contains", listener);
    const isContained = composedPath.length > 0;
    return isContained;
  }
  var FocusState = {
    NONE: "none",
    LIST_ROOT: "list-root",
    FIRST_ITEM: "first-item",
    LAST_ITEM: "last-item"
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/internal/controllers/surfacePositionController.js
  var Corner = {
    END_START: "end-start",
    END_END: "end-end",
    START_START: "start-start",
    START_END: "start-end"
  };
  var SurfacePositionController = class {
    /**
     * @param host The host to connect the controller to.
     * @param getProperties A function that returns the properties for the
     * controller.
     */
    constructor(host, getProperties) {
      this.host = host;
      this.getProperties = getProperties;
      this.surfaceStylesInternal = {
        "display": "none"
      };
      this.lastValues = {
        isOpen: false
      };
      this.host.addController(this);
    }
    /**
     * The StyleInfo map to apply to the surface via Lit's stylemap
     */
    get surfaceStyles() {
      return this.surfaceStylesInternal;
    }
    /**
     * Calculates the surface's new position required so that the surface's
     * `surfaceCorner` aligns to the anchor's `anchorCorner` while keeping the
     * surface inside the window viewport. This positioning also respects RTL by
     * checking `getComputedStyle()` on the surface element.
     */
    async position() {
      const { surfaceEl, anchorEl, anchorCorner: anchorCornerRaw, surfaceCorner: surfaceCornerRaw, positioning, xOffset, yOffset, disableBlockFlip, disableInlineFlip, repositionStrategy } = this.getProperties();
      const anchorCorner = anchorCornerRaw.toLowerCase().trim();
      const surfaceCorner = surfaceCornerRaw.toLowerCase().trim();
      if (!surfaceEl || !anchorEl) {
        return;
      }
      const windowInnerWidth = window.innerWidth;
      const windowInnerHeight = window.innerHeight;
      const div = document.createElement("div");
      div.style.opacity = "0";
      div.style.position = "fixed";
      div.style.display = "block";
      div.style.inset = "0";
      document.body.appendChild(div);
      const scrollbarTestRect = div.getBoundingClientRect();
      div.remove();
      const blockScrollbarHeight = window.innerHeight - scrollbarTestRect.bottom;
      const inlineScrollbarWidth = window.innerWidth - scrollbarTestRect.right;
      this.surfaceStylesInternal = {
        "display": "block",
        "opacity": "0"
      };
      this.host.requestUpdate();
      await this.host.updateComplete;
      if (surfaceEl.popover && surfaceEl.isConnected) {
        surfaceEl.showPopover();
      }
      const surfaceRect = surfaceEl.getSurfacePositionClientRect ? surfaceEl.getSurfacePositionClientRect() : surfaceEl.getBoundingClientRect();
      const anchorRect = anchorEl.getSurfacePositionClientRect ? anchorEl.getSurfacePositionClientRect() : anchorEl.getBoundingClientRect();
      const [surfaceBlock, surfaceInline] = surfaceCorner.split("-");
      const [anchorBlock, anchorInline] = anchorCorner.split("-");
      const isLTR = getComputedStyle(surfaceEl).direction === "ltr";
      let { blockInset, blockOutOfBoundsCorrection, surfaceBlockProperty } = this.calculateBlock({
        surfaceRect,
        anchorRect,
        anchorBlock,
        surfaceBlock,
        yOffset,
        positioning,
        windowInnerHeight,
        blockScrollbarHeight
      });
      if (blockOutOfBoundsCorrection && !disableBlockFlip) {
        const flippedSurfaceBlock = surfaceBlock === "start" ? "end" : "start";
        const flippedAnchorBlock = anchorBlock === "start" ? "end" : "start";
        const flippedBlock = this.calculateBlock({
          surfaceRect,
          anchorRect,
          anchorBlock: flippedAnchorBlock,
          surfaceBlock: flippedSurfaceBlock,
          yOffset,
          positioning,
          windowInnerHeight,
          blockScrollbarHeight
        });
        if (blockOutOfBoundsCorrection > flippedBlock.blockOutOfBoundsCorrection) {
          blockInset = flippedBlock.blockInset;
          blockOutOfBoundsCorrection = flippedBlock.blockOutOfBoundsCorrection;
          surfaceBlockProperty = flippedBlock.surfaceBlockProperty;
        }
      }
      let { inlineInset, inlineOutOfBoundsCorrection, surfaceInlineProperty } = this.calculateInline({
        surfaceRect,
        anchorRect,
        anchorInline,
        surfaceInline,
        xOffset,
        positioning,
        isLTR,
        windowInnerWidth,
        inlineScrollbarWidth
      });
      if (inlineOutOfBoundsCorrection && !disableInlineFlip) {
        const flippedSurfaceInline = surfaceInline === "start" ? "end" : "start";
        const flippedAnchorInline = anchorInline === "start" ? "end" : "start";
        const flippedInline = this.calculateInline({
          surfaceRect,
          anchorRect,
          anchorInline: flippedAnchorInline,
          surfaceInline: flippedSurfaceInline,
          xOffset,
          positioning,
          isLTR,
          windowInnerWidth,
          inlineScrollbarWidth
        });
        if (Math.abs(inlineOutOfBoundsCorrection) > Math.abs(flippedInline.inlineOutOfBoundsCorrection)) {
          inlineInset = flippedInline.inlineInset;
          inlineOutOfBoundsCorrection = flippedInline.inlineOutOfBoundsCorrection;
          surfaceInlineProperty = flippedInline.surfaceInlineProperty;
        }
      }
      if (repositionStrategy === "move") {
        blockInset = blockInset - blockOutOfBoundsCorrection;
        inlineInset = inlineInset - inlineOutOfBoundsCorrection;
      }
      this.surfaceStylesInternal = {
        "display": "block",
        "opacity": "1",
        [surfaceBlockProperty]: `${blockInset}px`,
        [surfaceInlineProperty]: `${inlineInset}px`
      };
      if (repositionStrategy === "resize") {
        if (blockOutOfBoundsCorrection) {
          this.surfaceStylesInternal["height"] = `${surfaceRect.height - blockOutOfBoundsCorrection}px`;
        }
        if (inlineOutOfBoundsCorrection) {
          this.surfaceStylesInternal["width"] = `${surfaceRect.width - inlineOutOfBoundsCorrection}px`;
        }
      }
      this.host.requestUpdate();
    }
    /**
     * Calculates the css property, the inset, and the out of bounds correction
     * for the surface in the block direction.
     */
    calculateBlock(config) {
      const { surfaceRect, anchorRect, anchorBlock, surfaceBlock, yOffset, positioning, windowInnerHeight, blockScrollbarHeight } = config;
      const relativeToWindow = positioning === "fixed" || positioning === "document" ? 1 : 0;
      const relativeToDocument = positioning === "document" ? 1 : 0;
      const isSurfaceBlockStart = surfaceBlock === "start" ? 1 : 0;
      const isSurfaceBlockEnd = surfaceBlock === "end" ? 1 : 0;
      const isOneBlockEnd = anchorBlock !== surfaceBlock ? 1 : 0;
      const blockAnchorOffset = isOneBlockEnd * anchorRect.height + yOffset;
      const blockTopLayerOffset = isSurfaceBlockStart * anchorRect.top + isSurfaceBlockEnd * (windowInnerHeight - anchorRect.bottom - blockScrollbarHeight);
      const blockDocumentOffset = isSurfaceBlockStart * window.scrollY - isSurfaceBlockEnd * window.scrollY;
      const blockOutOfBoundsCorrection = Math.abs(Math.min(0, windowInnerHeight - blockTopLayerOffset - blockAnchorOffset - surfaceRect.height));
      const blockInset = relativeToWindow * blockTopLayerOffset + relativeToDocument * blockDocumentOffset + blockAnchorOffset;
      const surfaceBlockProperty = surfaceBlock === "start" ? "inset-block-start" : "inset-block-end";
      return { blockInset, blockOutOfBoundsCorrection, surfaceBlockProperty };
    }
    /**
     * Calculates the css property, the inset, and the out of bounds correction
     * for the surface in the inline direction.
     */
    calculateInline(config) {
      const { isLTR: isLTRBool, surfaceInline, anchorInline, anchorRect, surfaceRect, xOffset, positioning, windowInnerWidth, inlineScrollbarWidth } = config;
      const relativeToWindow = positioning === "fixed" || positioning === "document" ? 1 : 0;
      const relativeToDocument = positioning === "document" ? 1 : 0;
      const isLTR = isLTRBool ? 1 : 0;
      const isRTL = isLTRBool ? 0 : 1;
      const isSurfaceInlineStart = surfaceInline === "start" ? 1 : 0;
      const isSurfaceInlineEnd = surfaceInline === "end" ? 1 : 0;
      const isOneInlineEnd = anchorInline !== surfaceInline ? 1 : 0;
      const inlineAnchorOffset = isOneInlineEnd * anchorRect.width + xOffset;
      const inlineTopLayerOffsetLTR = isSurfaceInlineStart * anchorRect.left + isSurfaceInlineEnd * (windowInnerWidth - anchorRect.right - inlineScrollbarWidth);
      const inlineTopLayerOffsetRTL = isSurfaceInlineStart * (windowInnerWidth - anchorRect.right - inlineScrollbarWidth) + isSurfaceInlineEnd * anchorRect.left;
      const inlineTopLayerOffset = isLTR * inlineTopLayerOffsetLTR + isRTL * inlineTopLayerOffsetRTL;
      const inlineDocumentOffsetLTR = isSurfaceInlineStart * window.scrollX - isSurfaceInlineEnd * window.scrollX;
      const inlineDocumentOffsetRTL = isSurfaceInlineEnd * window.scrollX - isSurfaceInlineStart * window.scrollX;
      const inlineDocumentOffset = isLTR * inlineDocumentOffsetLTR + isRTL * inlineDocumentOffsetRTL;
      const inlineOutOfBoundsCorrection = Math.abs(Math.min(0, windowInnerWidth - inlineTopLayerOffset - inlineAnchorOffset - surfaceRect.width));
      const inlineInset = relativeToWindow * inlineTopLayerOffset + inlineAnchorOffset + relativeToDocument * inlineDocumentOffset;
      let surfaceInlineProperty = surfaceInline === "start" ? "inset-inline-start" : "inset-inline-end";
      if (positioning === "document" || positioning === "fixed") {
        if (surfaceInline === "start" && isLTRBool || surfaceInline === "end" && !isLTRBool) {
          surfaceInlineProperty = "left";
        } else {
          surfaceInlineProperty = "right";
        }
      }
      return {
        inlineInset,
        inlineOutOfBoundsCorrection,
        surfaceInlineProperty
      };
    }
    hostUpdate() {
      this.onUpdate();
    }
    hostUpdated() {
      this.onUpdate();
    }
    /**
     * Checks whether the properties passed into the controller have changed since
     * the last positioning. If so, it will reposition if the surface is open or
     * close it if the surface should close.
     */
    async onUpdate() {
      const props = this.getProperties();
      let hasChanged = false;
      for (const [key, value] of Object.entries(props)) {
        hasChanged = hasChanged || value !== this.lastValues[key];
        if (hasChanged)
          break;
      }
      const openChanged = this.lastValues.isOpen !== props.isOpen;
      const hasAnchor = !!props.anchorEl;
      const hasSurface = !!props.surfaceEl;
      if (hasChanged && hasAnchor && hasSurface) {
        this.lastValues.isOpen = props.isOpen;
        if (props.isOpen) {
          this.lastValues = props;
          await this.position();
          props.onOpen();
        } else if (openChanged) {
          await props.beforeClose();
          this.close();
          props.onClose();
        }
      }
    }
    /**
     * Hides the surface.
     */
    close() {
      this.surfaceStylesInternal = {
        "display": "none"
      };
      this.host.requestUpdate();
      const surfaceEl = this.getProperties().surfaceEl;
      if ((surfaceEl == null ? void 0 : surfaceEl.popover) && (surfaceEl == null ? void 0 : surfaceEl.isConnected)) {
        surfaceEl.hidePopover();
      }
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/internal/controllers/typeaheadController.js
  var TYPEAHEAD_RECORD = {
    INDEX: 0,
    ITEM: 1,
    TEXT: 2
  };
  var TypeaheadController = class {
    /**
     * @param getProperties A function that returns the options of the typeahead
     * controller:
     *
     * {
     *   getItems: A function that returns an array of menu items to be searched.
     *   typeaheadBufferTime: The maximum time between each keystroke to keep the
     *       current type buffer alive.
     * }
     */
    constructor(getProperties) {
      this.getProperties = getProperties;
      this.typeaheadRecords = [];
      this.typaheadBuffer = "";
      this.cancelTypeaheadTimeout = 0;
      this.isTypingAhead = false;
      this.lastActiveRecord = null;
      this.onKeydown = (event) => {
        if (this.isTypingAhead) {
          this.typeahead(event);
        } else {
          this.beginTypeahead(event);
        }
      };
      this.endTypeahead = () => {
        this.isTypingAhead = false;
        this.typaheadBuffer = "";
        this.typeaheadRecords = [];
      };
    }
    get items() {
      return this.getProperties().getItems();
    }
    get active() {
      return this.getProperties().active;
    }
    /**
     * Sets up typingahead
     */
    beginTypeahead(event) {
      if (!this.active) {
        return;
      }
      if (event.code === "Space" || event.code === "Enter" || event.code.startsWith("Arrow") || event.code === "Escape") {
        return;
      }
      this.isTypingAhead = true;
      this.typeaheadRecords = this.items.map((el, index) => [
        index,
        el,
        el.typeaheadText.trim().toLowerCase()
      ]);
      this.lastActiveRecord = this.typeaheadRecords.find((record) => record[TYPEAHEAD_RECORD.ITEM].tabIndex === 0) ?? null;
      if (this.lastActiveRecord) {
        this.lastActiveRecord[TYPEAHEAD_RECORD.ITEM].tabIndex = -1;
      }
      this.typeahead(event);
    }
    /**
     * Performs the typeahead. Based on the normalized items and the current text
     * buffer, finds the _next_ item with matching text and activates it.
     *
     * @example
     *
     * items: Apple, Banana, Olive, Orange, Cucumber
     * buffer: ''
     * user types: o
     *
     * activates Olive
     *
     * @example
     *
     * items: Apple, Banana, Olive (active), Orange, Cucumber
     * buffer: 'o'
     * user types: l
     *
     * activates Olive
     *
     * @example
     *
     * items: Apple, Banana, Olive (active), Orange, Cucumber
     * buffer: ''
     * user types: o
     *
     * activates Orange
     *
     * @example
     *
     * items: Apple, Banana, Olive, Orange (active), Cucumber
     * buffer: ''
     * user types: o
     *
     * activates Olive
     */
    typeahead(event) {
      if (event.defaultPrevented)
        return;
      clearTimeout(this.cancelTypeaheadTimeout);
      if (event.code === "Enter" || event.code.startsWith("Arrow") || event.code === "Escape") {
        this.endTypeahead();
        if (this.lastActiveRecord) {
          this.lastActiveRecord[TYPEAHEAD_RECORD.ITEM].tabIndex = -1;
        }
        return;
      }
      if (event.code === "Space") {
        event.preventDefault();
      }
      this.cancelTypeaheadTimeout = setTimeout(this.endTypeahead, this.getProperties().typeaheadBufferTime);
      this.typaheadBuffer += event.key.toLowerCase();
      const lastActiveIndex = this.lastActiveRecord ? this.lastActiveRecord[TYPEAHEAD_RECORD.INDEX] : -1;
      const numRecords = this.typeaheadRecords.length;
      const rebaseIndexOnActive = (record) => {
        return (record[TYPEAHEAD_RECORD.INDEX] + numRecords - lastActiveIndex) % numRecords;
      };
      const matchingRecords = this.typeaheadRecords.filter((record) => !record[TYPEAHEAD_RECORD.ITEM].disabled && record[TYPEAHEAD_RECORD.TEXT].startsWith(this.typaheadBuffer)).sort((a4, b3) => rebaseIndexOnActive(a4) - rebaseIndexOnActive(b3));
      if (matchingRecords.length === 0) {
        clearTimeout(this.cancelTypeaheadTimeout);
        if (this.lastActiveRecord) {
          this.lastActiveRecord[TYPEAHEAD_RECORD.ITEM].tabIndex = -1;
        }
        this.endTypeahead();
        return;
      }
      const isNewQuery = this.typaheadBuffer.length === 1;
      let nextRecord;
      if (this.lastActiveRecord === matchingRecords[0] && isNewQuery) {
        nextRecord = matchingRecords[1] ?? matchingRecords[0];
      } else {
        nextRecord = matchingRecords[0];
      }
      if (this.lastActiveRecord) {
        this.lastActiveRecord[TYPEAHEAD_RECORD.ITEM].tabIndex = -1;
      }
      this.lastActiveRecord = nextRecord;
      nextRecord[TYPEAHEAD_RECORD.ITEM].tabIndex = 0;
      nextRecord[TYPEAHEAD_RECORD.ITEM].focus();
      return;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/internal/menu.js
  var DEFAULT_TYPEAHEAD_BUFFER_TIME = 200;
  var submenuNavKeys = /* @__PURE__ */ new Set([
    NavigableKeys.ArrowDown,
    NavigableKeys.ArrowUp,
    NavigableKeys.Home,
    NavigableKeys.End
  ]);
  var menuNavKeys = /* @__PURE__ */ new Set([
    NavigableKeys.ArrowLeft,
    NavigableKeys.ArrowRight,
    ...submenuNavKeys
  ]);
  function getFocusedElement(activeDoc = document) {
    var _a3;
    let activeEl = activeDoc.activeElement;
    while (activeEl && ((_a3 = activeEl == null ? void 0 : activeEl.shadowRoot) == null ? void 0 : _a3.activeElement)) {
      activeEl = activeEl.shadowRoot.activeElement;
    }
    return activeEl;
  }
  var Menu = class extends i4 {
    /**
     * Whether the menu is animating upwards or downwards when opening. This is
     * helpful for calculating some animation calculations.
     */
    get openDirection() {
      const menuCornerBlock = this.menuCorner.split("-")[0];
      return menuCornerBlock === "start" ? "DOWN" : "UP";
    }
    /**
     * The element which the menu should align to. If `anchor` is set to a
     * non-empty idref string, then `anchorEl` will resolve to the element with
     * the given id in the same root node. Otherwise, `null`.
     */
    get anchorElement() {
      if (this.anchor) {
        return this.getRootNode().querySelector(`#${this.anchor}`);
      }
      return this.currentAnchorElement;
    }
    set anchorElement(element) {
      this.currentAnchorElement = element;
      this.requestUpdate("anchorElement");
    }
    constructor() {
      super();
      this.anchor = "";
      this.positioning = "absolute";
      this.quick = false;
      this.hasOverflow = false;
      this.open = false;
      this.xOffset = 0;
      this.yOffset = 0;
      this.noHorizontalFlip = false;
      this.noVerticalFlip = false;
      this.typeaheadDelay = DEFAULT_TYPEAHEAD_BUFFER_TIME;
      this.anchorCorner = Corner.END_START;
      this.menuCorner = Corner.START_START;
      this.stayOpenOnOutsideClick = false;
      this.stayOpenOnFocusout = false;
      this.skipRestoreFocus = false;
      this.defaultFocus = FocusState.FIRST_ITEM;
      this.noNavigationWrap = false;
      this.typeaheadActive = true;
      this.isSubmenu = false;
      this.pointerPath = [];
      this.isRepositioning = false;
      this.openCloseAnimationSignal = createAnimationSignal();
      this.listController = new ListController({
        isItem: (maybeItem) => {
          return maybeItem.hasAttribute("md-menu-item");
        },
        getPossibleItems: () => this.slotItems,
        isRtl: () => getComputedStyle(this).direction === "rtl",
        deactivateItem: (item) => {
          item.selected = false;
          item.tabIndex = -1;
        },
        activateItem: (item) => {
          item.selected = true;
          item.tabIndex = 0;
        },
        isNavigableKey: (key) => {
          if (!this.isSubmenu) {
            return menuNavKeys.has(key);
          }
          const isRtl2 = getComputedStyle(this).direction === "rtl";
          const arrowOpen = isRtl2 ? NavigableKeys.ArrowLeft : NavigableKeys.ArrowRight;
          if (key === arrowOpen) {
            return true;
          }
          return submenuNavKeys.has(key);
        },
        wrapNavigation: () => !this.noNavigationWrap
      });
      this.lastFocusedElement = null;
      this.typeaheadController = new TypeaheadController(() => {
        return {
          getItems: () => this.items,
          typeaheadBufferTime: this.typeaheadDelay,
          active: this.typeaheadActive
        };
      });
      this.currentAnchorElement = null;
      this.internals = // Cast needed for closure
      this.attachInternals();
      this.menuPositionController = new SurfacePositionController(this, () => {
        return {
          anchorCorner: this.anchorCorner,
          surfaceCorner: this.menuCorner,
          surfaceEl: this.surfaceEl,
          anchorEl: this.anchorElement,
          positioning: this.positioning === "popover" ? "document" : this.positioning,
          isOpen: this.open,
          xOffset: this.xOffset,
          yOffset: this.yOffset,
          disableBlockFlip: this.noVerticalFlip,
          disableInlineFlip: this.noHorizontalFlip,
          onOpen: this.onOpened,
          beforeClose: this.beforeClose,
          onClose: this.onClosed,
          // We can't resize components that have overflow like menus with
          // submenus because the overflow-y will show menu items / content
          // outside the bounds of the menu. Popover API fixes this because each
          // submenu is hoisted to the top-layer and are not considered overflow
          // content.
          repositionStrategy: this.hasOverflow && this.positioning !== "popover" ? "move" : "resize"
        };
      });
      this.onWindowResize = () => {
        if (this.isRepositioning || this.positioning !== "document" && this.positioning !== "fixed" && this.positioning !== "popover") {
          return;
        }
        this.isRepositioning = true;
        this.reposition();
        this.isRepositioning = false;
      };
      this.handleFocusout = async (event) => {
        const anchorEl = this.anchorElement;
        if (this.stayOpenOnFocusout || !this.open || this.pointerPath.includes(anchorEl)) {
          return;
        }
        if (event.relatedTarget) {
          if (isElementInSubtree(event.relatedTarget, this) || this.pointerPath.length !== 0 && isElementInSubtree(event.relatedTarget, anchorEl)) {
            return;
          }
        } else if (this.pointerPath.includes(this)) {
          return;
        }
        const oldRestoreFocus = this.skipRestoreFocus;
        this.skipRestoreFocus = true;
        this.close();
        await this.updateComplete;
        this.skipRestoreFocus = oldRestoreFocus;
      };
      this.onOpened = async () => {
        this.lastFocusedElement = getFocusedElement();
        const items = this.items;
        const activeItemRecord = getActiveItem(items);
        if (activeItemRecord && this.defaultFocus !== FocusState.NONE) {
          activeItemRecord.item.tabIndex = -1;
        }
        let animationAborted = !this.quick;
        if (this.quick) {
          this.dispatchEvent(new Event("opening"));
        } else {
          animationAborted = !!await this.animateOpen();
        }
        switch (this.defaultFocus) {
          case FocusState.FIRST_ITEM:
            const first = getFirstActivatableItem(items);
            if (first) {
              first.tabIndex = 0;
              first.focus();
              await first.updateComplete;
            }
            break;
          case FocusState.LAST_ITEM:
            const last = getLastActivatableItem(items);
            if (last) {
              last.tabIndex = 0;
              last.focus();
              await last.updateComplete;
            }
            break;
          case FocusState.LIST_ROOT:
            this.focus();
            break;
          default:
          case FocusState.NONE:
            break;
        }
        if (!animationAborted) {
          this.dispatchEvent(new Event("opened"));
        }
      };
      this.beforeClose = async () => {
        var _a3, _b;
        this.open = false;
        if (!this.skipRestoreFocus) {
          (_b = (_a3 = this.lastFocusedElement) == null ? void 0 : _a3.focus) == null ? void 0 : _b.call(_a3);
        }
        if (!this.quick) {
          await this.animateClose();
        }
      };
      this.onClosed = () => {
        if (this.quick) {
          this.dispatchEvent(new Event("closing"));
          this.dispatchEvent(new Event("closed"));
        }
      };
      this.onWindowPointerdown = (event) => {
        this.pointerPath = event.composedPath();
      };
      this.onDocumentClick = (event) => {
        if (!this.open) {
          return;
        }
        const path = event.composedPath();
        if (!this.stayOpenOnOutsideClick && !path.includes(this) && !path.includes(this.anchorElement)) {
          this.open = false;
        }
      };
      if (!o7) {
        this.internals.role = "menu";
        this.addEventListener("keydown", this.handleKeydown);
        this.addEventListener("keydown", this.captureKeydown, { capture: true });
        this.addEventListener("focusout", this.handleFocusout);
      }
    }
    /**
     * The menu items associated with this menu. The items must be `MenuItem`s and
     * have both the `md-menu-item` and `md-list-item` attributes.
     */
    get items() {
      return this.listController.items;
    }
    willUpdate(changed) {
      if (!changed.has("open")) {
        return;
      }
      if (this.open) {
        this.removeAttribute("aria-hidden");
        return;
      }
      this.setAttribute("aria-hidden", "true");
    }
    update(changed) {
      if (changed.has("open")) {
        if (this.open) {
          this.setUpGlobalEventListeners();
        } else {
          this.cleanUpGlobalEventListeners();
        }
      }
      if (changed.has("positioning") && this.positioning === "popover" && // type required for Google JS conformance
      !this.showPopover) {
        this.positioning = "fixed";
      }
      super.update(changed);
    }
    connectedCallback() {
      super.connectedCallback();
      if (this.open) {
        this.setUpGlobalEventListeners();
      }
    }
    disconnectedCallback() {
      super.disconnectedCallback();
      this.cleanUpGlobalEventListeners();
    }
    getBoundingClientRect() {
      if (!this.surfaceEl) {
        return super.getBoundingClientRect();
      }
      return this.surfaceEl.getBoundingClientRect();
    }
    getClientRects() {
      if (!this.surfaceEl) {
        return super.getClientRects();
      }
      return this.surfaceEl.getClientRects();
    }
    render() {
      return this.renderSurface();
    }
    /**
     * Renders the positionable surface element and its contents.
     */
    renderSurface() {
      return b2`
      <div
        class="menu ${e8(this.getSurfaceClasses())}"
        style=${o9(this.menuPositionController.surfaceStyles)}
        popover=${this.positioning === "popover" ? "manual" : A}>
        ${this.renderElevation()}
        <div class="items">
          <div class="item-padding"> ${this.renderMenuItems()} </div>
        </div>
      </div>
    `;
    }
    /**
     * Renders the menu items' slot
     */
    renderMenuItems() {
      return b2`<slot
      @close-menu=${this.onCloseMenu}
      @deactivate-items=${this.onDeactivateItems}
      @request-activation=${this.onRequestActivation}
      @deactivate-typeahead=${this.handleDeactivateTypeahead}
      @activate-typeahead=${this.handleActivateTypeahead}
      @stay-open-on-focusout=${this.handleStayOpenOnFocusout}
      @close-on-focusout=${this.handleCloseOnFocusout}
      @slotchange=${this.listController.onSlotchange}></slot>`;
    }
    /**
     * Renders the elevation component.
     */
    renderElevation() {
      return b2`<md-elevation part="elevation"></md-elevation>`;
    }
    getSurfaceClasses() {
      return {
        open: this.open,
        fixed: this.positioning === "fixed",
        "has-overflow": this.hasOverflow
      };
    }
    captureKeydown(event) {
      if (event.target === this && !event.defaultPrevented && isClosableKey(event.code)) {
        event.preventDefault();
        this.close();
      }
      this.typeaheadController.onKeydown(event);
    }
    /**
     * Performs the opening animation:
     *
     * https://direct.googleplex.com/#/spec/295000003+271060003
     *
     * @return A promise that resolve to `true` if the animation was aborted,
     *     `false` if it was not aborted.
     */
    async animateOpen() {
      const surfaceEl = this.surfaceEl;
      const slotEl = this.slotEl;
      if (!surfaceEl || !slotEl)
        return true;
      const openDirection = this.openDirection;
      this.dispatchEvent(new Event("opening"));
      surfaceEl.classList.toggle("animating", true);
      const signal = this.openCloseAnimationSignal.start();
      const height = surfaceEl.offsetHeight;
      const openingUpwards = openDirection === "UP";
      const children = this.items;
      const FULL_DURATION = 500;
      const SURFACE_OPACITY_DURATION = 50;
      const ITEM_OPACITY_DURATION = 250;
      const DELAY_BETWEEN_ITEMS = (FULL_DURATION - ITEM_OPACITY_DURATION) / children.length;
      const surfaceHeightAnimation = surfaceEl.animate([{ height: "0px" }, { height: `${height}px` }], {
        duration: FULL_DURATION,
        easing: EASING.EMPHASIZED
      });
      const upPositionCorrectionAnimation = slotEl.animate([
        { transform: openingUpwards ? `translateY(-${height}px)` : "" },
        { transform: "" }
      ], { duration: FULL_DURATION, easing: EASING.EMPHASIZED });
      const surfaceOpacityAnimation = surfaceEl.animate([{ opacity: 0 }, { opacity: 1 }], SURFACE_OPACITY_DURATION);
      const childrenAnimations = [];
      for (let i8 = 0; i8 < children.length; i8++) {
        const directionalIndex = openingUpwards ? children.length - 1 - i8 : i8;
        const child = children[directionalIndex];
        const animation = child.animate([{ opacity: 0 }, { opacity: 1 }], {
          duration: ITEM_OPACITY_DURATION,
          delay: DELAY_BETWEEN_ITEMS * i8
        });
        child.classList.toggle("md-menu-hidden", true);
        animation.addEventListener("finish", () => {
          child.classList.toggle("md-menu-hidden", false);
        });
        childrenAnimations.push([child, animation]);
      }
      let resolveAnimation = (value) => {
      };
      const animationFinished = new Promise((resolve) => {
        resolveAnimation = resolve;
      });
      signal.addEventListener("abort", () => {
        surfaceHeightAnimation.cancel();
        upPositionCorrectionAnimation.cancel();
        surfaceOpacityAnimation.cancel();
        childrenAnimations.forEach(([child, animation]) => {
          child.classList.toggle("md-menu-hidden", false);
          animation.cancel();
        });
        resolveAnimation(true);
      });
      surfaceHeightAnimation.addEventListener("finish", () => {
        surfaceEl.classList.toggle("animating", false);
        this.openCloseAnimationSignal.finish();
        resolveAnimation(false);
      });
      return await animationFinished;
    }
    /**
     * Performs the closing animation:
     *
     * https://direct.googleplex.com/#/spec/295000003+271060003
     */
    animateClose() {
      let resolve;
      const animationEnded = new Promise((res) => {
        resolve = res;
      });
      const surfaceEl = this.surfaceEl;
      const slotEl = this.slotEl;
      if (!surfaceEl || !slotEl) {
        resolve(false);
        return animationEnded;
      }
      const openDirection = this.openDirection;
      const closingDownwards = openDirection === "UP";
      this.dispatchEvent(new Event("closing"));
      surfaceEl.classList.toggle("animating", true);
      const signal = this.openCloseAnimationSignal.start();
      const height = surfaceEl.offsetHeight;
      const children = this.items;
      const FULL_DURATION = 150;
      const SURFACE_OPACITY_DURATION = 50;
      const SURFACE_OPACITY_DELAY = FULL_DURATION - SURFACE_OPACITY_DURATION;
      const ITEM_OPACITY_DURATION = 50;
      const ITEM_OPACITY_INITIAL_DELAY = 50;
      const END_HEIGHT_PERCENTAGE = 0.35;
      const DELAY_BETWEEN_ITEMS = (FULL_DURATION - ITEM_OPACITY_INITIAL_DELAY - ITEM_OPACITY_DURATION) / children.length;
      const surfaceHeightAnimation = surfaceEl.animate([
        { height: `${height}px` },
        { height: `${height * END_HEIGHT_PERCENTAGE}px` }
      ], {
        duration: FULL_DURATION,
        easing: EASING.EMPHASIZED_ACCELERATE
      });
      const downPositionCorrectionAnimation = slotEl.animate([
        { transform: "" },
        {
          transform: closingDownwards ? `translateY(-${height * (1 - END_HEIGHT_PERCENTAGE)}px)` : ""
        }
      ], { duration: FULL_DURATION, easing: EASING.EMPHASIZED_ACCELERATE });
      const surfaceOpacityAnimation = surfaceEl.animate([{ opacity: 1 }, { opacity: 0 }], { duration: SURFACE_OPACITY_DURATION, delay: SURFACE_OPACITY_DELAY });
      const childrenAnimations = [];
      for (let i8 = 0; i8 < children.length; i8++) {
        const directionalIndex = closingDownwards ? i8 : children.length - 1 - i8;
        const child = children[directionalIndex];
        const animation = child.animate([{ opacity: 1 }, { opacity: 0 }], {
          duration: ITEM_OPACITY_DURATION,
          delay: ITEM_OPACITY_INITIAL_DELAY + DELAY_BETWEEN_ITEMS * i8
        });
        animation.addEventListener("finish", () => {
          child.classList.toggle("md-menu-hidden", true);
        });
        childrenAnimations.push([child, animation]);
      }
      signal.addEventListener("abort", () => {
        surfaceHeightAnimation.cancel();
        downPositionCorrectionAnimation.cancel();
        surfaceOpacityAnimation.cancel();
        childrenAnimations.forEach(([child, animation]) => {
          animation.cancel();
          child.classList.toggle("md-menu-hidden", false);
        });
        resolve(false);
      });
      surfaceHeightAnimation.addEventListener("finish", () => {
        surfaceEl.classList.toggle("animating", false);
        childrenAnimations.forEach(([child]) => {
          child.classList.toggle("md-menu-hidden", false);
        });
        this.openCloseAnimationSignal.finish();
        this.dispatchEvent(new Event("closed"));
        resolve(true);
      });
      return animationEnded;
    }
    handleKeydown(event) {
      this.pointerPath = [];
      this.listController.handleKeydown(event);
    }
    setUpGlobalEventListeners() {
      document.addEventListener("click", this.onDocumentClick, { capture: true });
      window.addEventListener("pointerdown", this.onWindowPointerdown);
      document.addEventListener("resize", this.onWindowResize, { passive: true });
      window.addEventListener("resize", this.onWindowResize, { passive: true });
    }
    cleanUpGlobalEventListeners() {
      document.removeEventListener("click", this.onDocumentClick, {
        capture: true
      });
      window.removeEventListener("pointerdown", this.onWindowPointerdown);
      document.removeEventListener("resize", this.onWindowResize);
      window.removeEventListener("resize", this.onWindowResize);
    }
    onCloseMenu() {
      this.close();
    }
    onDeactivateItems(event) {
      event.stopPropagation();
      this.listController.onDeactivateItems();
    }
    onRequestActivation(event) {
      event.stopPropagation();
      this.listController.onRequestActivation(event);
    }
    handleDeactivateTypeahead(event) {
      event.stopPropagation();
      this.typeaheadActive = false;
    }
    handleActivateTypeahead(event) {
      event.stopPropagation();
      this.typeaheadActive = true;
    }
    handleStayOpenOnFocusout(event) {
      event.stopPropagation();
      this.stayOpenOnFocusout = true;
    }
    handleCloseOnFocusout(event) {
      event.stopPropagation();
      this.stayOpenOnFocusout = false;
    }
    close() {
      this.open = false;
      const maybeSubmenu = this.slotItems;
      maybeSubmenu.forEach((item) => {
        var _a3;
        (_a3 = item.close) == null ? void 0 : _a3.call(item);
      });
    }
    show() {
      this.open = true;
    }
    /**
     * Activates the next item in the menu. If at the end of the menu, the first
     * item will be activated.
     *
     * @return The activated menu item or `null` if there are no items.
     */
    activateNextItem() {
      return this.listController.activateNextItem() ?? null;
    }
    /**
     * Activates the previous item in the menu. If at the start of the menu, the
     * last item will be activated.
     *
     * @return The activated menu item or `null` if there are no items.
     */
    activatePreviousItem() {
      return this.listController.activatePreviousItem() ?? null;
    }
    /**
     * Repositions the menu if it is open.
     *
     * Useful for the case where document or window-positioned menus have their
     * anchors moved while open.
     */
    reposition() {
      if (this.open) {
        this.menuPositionController.position();
      }
    }
  };
  __decorate([
    e4(".menu")
  ], Menu.prototype, "surfaceEl", void 0);
  __decorate([
    e4("slot")
  ], Menu.prototype, "slotEl", void 0);
  __decorate([
    n3()
  ], Menu.prototype, "anchor", void 0);
  __decorate([
    n3()
  ], Menu.prototype, "positioning", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Menu.prototype, "quick", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "has-overflow" })
  ], Menu.prototype, "hasOverflow", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], Menu.prototype, "open", void 0);
  __decorate([
    n3({ type: Number, attribute: "x-offset" })
  ], Menu.prototype, "xOffset", void 0);
  __decorate([
    n3({ type: Number, attribute: "y-offset" })
  ], Menu.prototype, "yOffset", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-horizontal-flip" })
  ], Menu.prototype, "noHorizontalFlip", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-vertical-flip" })
  ], Menu.prototype, "noVerticalFlip", void 0);
  __decorate([
    n3({ type: Number, attribute: "typeahead-delay" })
  ], Menu.prototype, "typeaheadDelay", void 0);
  __decorate([
    n3({ attribute: "anchor-corner" })
  ], Menu.prototype, "anchorCorner", void 0);
  __decorate([
    n3({ attribute: "menu-corner" })
  ], Menu.prototype, "menuCorner", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "stay-open-on-outside-click" })
  ], Menu.prototype, "stayOpenOnOutsideClick", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "stay-open-on-focusout" })
  ], Menu.prototype, "stayOpenOnFocusout", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "skip-restore-focus" })
  ], Menu.prototype, "skipRestoreFocus", void 0);
  __decorate([
    n3({ attribute: "default-focus" })
  ], Menu.prototype, "defaultFocus", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-navigation-wrap" })
  ], Menu.prototype, "noNavigationWrap", void 0);
  __decorate([
    o4({ flatten: true })
  ], Menu.prototype, "slotItems", void 0);
  __decorate([
    r4()
  ], Menu.prototype, "typeaheadActive", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/internal/menu-styles.js
  var styles7 = i`:host{--md-elevation-level: var(--md-menu-container-elevation, 2);--md-elevation-shadow-color: var(--md-menu-container-shadow-color, var(--md-sys-color-shadow, #000));min-width:112px;color:unset;display:contents}md-focus-ring{--md-focus-ring-shape: var(--md-menu-container-shape, var(--md-sys-shape-corner-extra-small, 4px))}.menu{border-radius:var(--md-menu-container-shape, var(--md-sys-shape-corner-extra-small, 4px));display:none;inset:auto;border:none;padding:0px;overflow:visible;background-color:rgba(0,0,0,0);color:inherit;opacity:0;z-index:20;position:absolute;user-select:none;max-height:inherit;height:inherit;min-width:inherit;max-width:inherit;scrollbar-width:inherit}.menu::backdrop{display:none}.fixed{position:fixed}.items{display:block;list-style-type:none;margin:0;outline:none;box-sizing:border-box;background-color:var(--md-menu-container-color, var(--md-sys-color-surface-container, #f3edf7));height:inherit;max-height:inherit;overflow:auto;min-width:inherit;max-width:inherit;border-radius:inherit;scrollbar-width:inherit}.item-padding{padding-block:var(--md-menu-top-space, 8px) var(--md-menu-bottom-space, 8px)}.has-overflow:not([popover]) .items{overflow:visible}.has-overflow.animating .items,.animating .items{overflow:hidden}.has-overflow.animating .items{pointer-events:none}.animating ::slotted(.md-menu-hidden){opacity:0}slot{display:block;height:inherit;max-height:inherit}::slotted(:is(md-divider,[role=separator])){margin:8px 0}@media(forced-colors: active){.menu{border-style:solid;border-color:CanvasText;border-width:1px}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/menu.js
  var MdMenu = class MdMenu2 extends Menu {
  };
  MdMenu.styles = [styles7];
  if (!customElements.get("md-menu")) {
    MdMenu = __decorate([
      t("md-menu")
    ], MdMenu);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/validators/select-validator.js
  var SelectValidator = class extends Validator {
    computeValidity(state) {
      if (!this.selectControl) {
        this.selectControl = document.createElement("select");
      }
      D(b2`<option value=${state.value}></option>`, this.selectControl);
      this.selectControl.value = state.value;
      this.selectControl.required = state.required;
      return {
        validity: this.selectControl.validity,
        validationMessage: this.selectControl.validationMessage
      };
    }
    equals(prev, next) {
      return prev.value === next.value && prev.required === next.required;
    }
    copy({ value, required }) {
      return { value, required };
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/internal/shared.js
  function getSelectedItems(items) {
    const selectedItemRecords = [];
    for (let i8 = 0; i8 < items.length; i8++) {
      const item = items[i8];
      if (item.selected) {
        selectedItemRecords.push([item, i8]);
      }
    }
    return selectedItemRecords;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/internal/select.js
  var _a2;
  var VALUE = Symbol("value");
  var selectBaseClass = mixinDelegatesAria(mixinOnReportValidity(mixinConstraintValidation(mixinFormAssociated(mixinElementInternals(i4)))));
  var Select = class extends selectBaseClass {
    /**
     * The value of the currently selected option.
     *
     * Note: For SSR, set `[selected]` on the requested option and `displayText`
     * rather than setting `value` setting `value` will incur a DOM query.
     */
    get value() {
      return this[VALUE];
    }
    set value(value) {
      if (o7)
        return;
      this.lastUserSetValue = value;
      this.select(value);
    }
    get options() {
      var _a3;
      return ((_a3 = this.menu) == null ? void 0 : _a3.items) ?? [];
    }
    /**
     * The index of the currently selected option.
     *
     * Note: For SSR, set `[selected]` on the requested option and `displayText`
     * rather than setting `selectedIndex` setting `selectedIndex` will incur a
     * DOM query.
     */
    get selectedIndex() {
      const [_option, index] = (this.getSelectedOptions() ?? [])[0] ?? [];
      return index ?? -1;
    }
    set selectedIndex(index) {
      this.lastUserSetSelectedIndex = index;
      this.selectIndex(index);
    }
    /**
     * Returns an array of selected options.
     *
     * NOTE: md-select only supports single selection.
     */
    get selectedOptions() {
      return (this.getSelectedOptions() ?? []).map(([option]) => option);
    }
    get hasError() {
      return this.error || this.nativeError;
    }
    constructor() {
      super();
      this.quick = false;
      this.required = false;
      this.errorText = "";
      this.label = "";
      this.noAsterisk = false;
      this.supportingText = "";
      this.error = false;
      this.menuPositioning = "popover";
      this.clampMenuWidth = false;
      this.typeaheadDelay = DEFAULT_TYPEAHEAD_BUFFER_TIME;
      this.hasLeadingIcon = false;
      this.displayText = "";
      this.menuAlign = "start";
      this[_a2] = "";
      this.lastUserSetValue = null;
      this.lastUserSetSelectedIndex = null;
      this.lastSelectedOption = null;
      this.lastSelectedOptionRecords = [];
      this.nativeError = false;
      this.nativeErrorText = "";
      this.focused = false;
      this.open = false;
      this.defaultFocus = FocusState.NONE;
      this.prevOpen = this.open;
      this.selectWidth = 0;
      if (o7) {
        return;
      }
      this.addEventListener("focus", this.handleFocus.bind(this));
      this.addEventListener("blur", this.handleBlur.bind(this));
    }
    /**
     * Selects an option given the value of the option, and updates MdSelect's
     * value.
     */
    select(value) {
      const optionToSelect = this.options.find((option) => option.value === value);
      if (optionToSelect) {
        this.selectItem(optionToSelect);
      }
    }
    /**
     * Selects an option given the index of the option, and updates MdSelect's
     * value.
     */
    selectIndex(index) {
      const optionToSelect = this.options[index];
      if (optionToSelect) {
        this.selectItem(optionToSelect);
      }
    }
    /**
     * Reset the select to its default value.
     */
    reset() {
      for (const option of this.options) {
        option.selected = option.hasAttribute("selected");
      }
      this.updateValueAndDisplayText();
      this.nativeError = false;
      this.nativeErrorText = "";
    }
    /** Shows the picker. If it's already open, this is a no-op. */
    showPicker() {
      this.open = true;
    }
    [(_a2 = VALUE, onReportValidity)](invalidEvent) {
      var _a3;
      invalidEvent == null ? void 0 : invalidEvent.preventDefault();
      const prevMessage = this.getErrorText();
      this.nativeError = !!invalidEvent;
      this.nativeErrorText = this.validationMessage;
      if (prevMessage === this.getErrorText()) {
        (_a3 = this.field) == null ? void 0 : _a3.reannounceError();
      }
    }
    update(changed) {
      if (!this.hasUpdated) {
        this.initUserSelection();
      }
      if (this.prevOpen !== this.open && this.open) {
        const selectRect = this.getBoundingClientRect();
        this.selectWidth = selectRect.width;
      }
      this.prevOpen = this.open;
      super.update(changed);
    }
    render() {
      return b2`
      <span
        class="select ${e8(this.getRenderClasses())}"
        @focusout=${this.handleFocusout}>
        ${this.renderField()} ${this.renderMenu()}
      </span>
    `;
    }
    async firstUpdated(changed) {
      var _a3;
      await ((_a3 = this.menu) == null ? void 0 : _a3.updateComplete);
      if (!this.lastSelectedOptionRecords.length) {
        this.initUserSelection();
      }
      if (!this.lastSelectedOptionRecords.length && !o7 && !this.options.length) {
        setTimeout(() => {
          this.updateValueAndDisplayText();
        });
      }
      super.firstUpdated(changed);
    }
    getRenderClasses() {
      return {
        "disabled": this.disabled,
        "error": this.error,
        "open": this.open
      };
    }
    renderField() {
      const ariaLabel = this.ariaLabel || this.label;
      return u3`
      <${this.fieldTag}
          aria-haspopup="listbox"
          role="combobox"
          part="field"
          id="field"
          tabindex=${this.disabled ? "-1" : "0"}
          aria-label=${ariaLabel || A}
          aria-describedby="description"
          aria-expanded=${this.open ? "true" : "false"}
          aria-controls="listbox"
          class="field"
          label=${this.label}
          ?no-asterisk=${this.noAsterisk}
          .focused=${this.focused || this.open}
          .populated=${!!this.displayText}
          .disabled=${this.disabled}
          .required=${this.required}
          .error=${this.hasError}
          ?has-start=${this.hasLeadingIcon}
          has-end
          supporting-text=${this.supportingText}
          error-text=${this.getErrorText()}
          @keydown=${this.handleKeydown}
          @click=${this.handleClick}>
         ${this.renderFieldContent()}
         <div id="description" slot="aria-describedby"></div>
      </${this.fieldTag}>`;
    }
    renderFieldContent() {
      return [
        this.renderLeadingIcon(),
        this.renderLabel(),
        this.renderTrailingIcon()
      ];
    }
    renderLeadingIcon() {
      return b2`
      <span class="icon leading" slot="start">
        <slot name="leading-icon" @slotchange=${this.handleIconChange}></slot>
      </span>
    `;
    }
    renderTrailingIcon() {
      return b2`
      <span class="icon trailing" slot="end">
        <slot name="trailing-icon" @slotchange=${this.handleIconChange}>
          <svg height="5" viewBox="7 10 10 5" focusable="false">
            <polygon
              class="down"
              stroke="none"
              fill-rule="evenodd"
              points="7 10 12 15 17 10"></polygon>
            <polygon
              class="up"
              stroke="none"
              fill-rule="evenodd"
              points="7 15 12 10 17 15"></polygon>
          </svg>
        </slot>
      </span>
    `;
    }
    renderLabel() {
      return b2`<div id="label">${this.displayText || b2`&nbsp;`}</div>`;
    }
    renderMenu() {
      const ariaLabel = this.label || this.ariaLabel;
      return b2`<div class="menu-wrapper">
      <md-menu
        id="listbox"
        .defaultFocus=${this.defaultFocus}
        role="listbox"
        tabindex="-1"
        aria-label=${ariaLabel || A}
        stay-open-on-focusout
        part="menu"
        exportparts="focus-ring: menu-focus-ring"
        anchor="field"
        style=${o9({
        "--__menu-min-width": `${this.selectWidth}px`,
        "--__menu-max-width": this.clampMenuWidth ? `${this.selectWidth}px` : void 0
      })}
        no-navigation-wrap
        .open=${this.open}
        .quick=${this.quick}
        .positioning=${this.menuPositioning}
        .typeaheadDelay=${this.typeaheadDelay}
        .anchorCorner=${this.menuAlign === "start" ? "end-start" : "end-end"}
        .menuCorner=${this.menuAlign === "start" ? "start-start" : "start-end"}
        @opening=${this.handleOpening}
        @opened=${this.redispatchEvent}
        @closing=${this.redispatchEvent}
        @closed=${this.handleClosed}
        @close-menu=${this.handleCloseMenu}
        @request-selection=${this.handleRequestSelection}
        @request-deselection=${this.handleRequestDeselection}>
        ${this.renderMenuContent()}
      </md-menu>
    </div>`;
    }
    renderMenuContent() {
      return b2`<slot></slot>`;
    }
    /**
     * Handles opening the select on keydown and typahead selection when the menu
     * is closed.
     */
    handleKeydown(event) {
      var _a3, _b;
      if (this.open || this.disabled || !this.menu) {
        return;
      }
      const typeaheadController = this.menu.typeaheadController;
      const isOpenKey = event.code === "Space" || event.code === "ArrowDown" || event.code === "ArrowUp" || event.code === "End" || event.code === "Home" || event.code === "Enter";
      if (!typeaheadController.isTypingAhead && isOpenKey) {
        event.preventDefault();
        this.open = true;
        switch (event.code) {
          case "Space":
          case "ArrowDown":
          case "Enter":
            this.defaultFocus = FocusState.NONE;
            break;
          case "End":
            this.defaultFocus = FocusState.LAST_ITEM;
            break;
          case "ArrowUp":
          case "Home":
            this.defaultFocus = FocusState.FIRST_ITEM;
            break;
          default:
            break;
        }
        return;
      }
      const isPrintableKey = event.key.length === 1;
      if (isPrintableKey) {
        typeaheadController.onKeydown(event);
        event.preventDefault();
        const { lastActiveRecord } = typeaheadController;
        if (!lastActiveRecord) {
          return;
        }
        (_b = (_a3 = this.labelEl) == null ? void 0 : _a3.setAttribute) == null ? void 0 : _b.call(_a3, "aria-live", "polite");
        const hasChanged = this.selectItem(lastActiveRecord[TYPEAHEAD_RECORD.ITEM]);
        if (hasChanged) {
          this.dispatchInteractionEvents();
        }
      }
    }
    handleClick() {
      this.open = !this.open;
    }
    handleFocus() {
      this.focused = true;
    }
    handleBlur() {
      this.focused = false;
    }
    /**
     * Handles closing the menu when the focus leaves the select's subtree.
     */
    handleFocusout(event) {
      if (event.relatedTarget && isElementInSubtree(event.relatedTarget, this)) {
        return;
      }
      this.open = false;
    }
    /**
     * Gets a list of all selected select options as a list item record array.
     *
     * @return An array of selected list option records.
     */
    getSelectedOptions() {
      if (!this.menu) {
        this.lastSelectedOptionRecords = [];
        return null;
      }
      const items = this.menu.items;
      this.lastSelectedOptionRecords = getSelectedItems(items);
      return this.lastSelectedOptionRecords;
    }
    async getUpdateComplete() {
      var _a3;
      await ((_a3 = this.menu) == null ? void 0 : _a3.updateComplete);
      return super.getUpdateComplete();
    }
    /**
     * Gets the selected options from the DOM, and updates the value and display
     * text to the first selected option's value and headline respectively.
     *
     * @return Whether or not the selected option has changed since last update.
     */
    updateValueAndDisplayText() {
      const selectedOptions = this.getSelectedOptions() ?? [];
      let hasSelectedOptionChanged = false;
      if (selectedOptions.length) {
        const [firstSelectedOption] = selectedOptions[0];
        hasSelectedOptionChanged = this.lastSelectedOption !== firstSelectedOption;
        this.lastSelectedOption = firstSelectedOption;
        this[VALUE] = firstSelectedOption.value;
        this.displayText = firstSelectedOption.displayText;
      } else {
        hasSelectedOptionChanged = this.lastSelectedOption !== null;
        this.lastSelectedOption = null;
        this[VALUE] = "";
        this.displayText = "";
      }
      return hasSelectedOptionChanged;
    }
    /**
     * Focuses and activates the last selected item upon opening, and resets other
     * active items.
     */
    async handleOpening(e9) {
      var _a3, _b, _c;
      (_b = (_a3 = this.labelEl) == null ? void 0 : _a3.removeAttribute) == null ? void 0 : _b.call(_a3, "aria-live");
      this.redispatchEvent(e9);
      if (this.defaultFocus !== FocusState.NONE) {
        return;
      }
      const items = this.menu.items;
      const activeItem = (_c = getActiveItem(items)) == null ? void 0 : _c.item;
      let [selectedItem] = this.lastSelectedOptionRecords[0] ?? [null];
      if (activeItem && activeItem !== selectedItem) {
        activeItem.tabIndex = -1;
      }
      selectedItem = selectedItem ?? items[0];
      if (selectedItem) {
        selectedItem.tabIndex = 0;
        selectedItem.focus();
      }
    }
    redispatchEvent(e9) {
      redispatchEvent(this, e9);
    }
    handleClosed(e9) {
      this.open = false;
      this.redispatchEvent(e9);
    }
    /**
     * Determines the reason for closing, and updates the UI accordingly.
     */
    handleCloseMenu(event) {
      const reason = event.detail.reason;
      const item = event.detail.itemPath[0];
      this.open = false;
      let hasChanged = false;
      if (reason.kind === "click-selection") {
        hasChanged = this.selectItem(item);
      } else if (reason.kind === "keydown" && isSelectableKey(reason.key)) {
        hasChanged = this.selectItem(item);
      } else {
        item.tabIndex = -1;
        item.blur();
      }
      if (hasChanged) {
        this.dispatchInteractionEvents();
      }
    }
    /**
     * Selects a given option, deselects other options, and updates the UI.
     *
     * @return Whether the last selected option has changed.
     */
    selectItem(item) {
      const selectedOptions = this.getSelectedOptions() ?? [];
      selectedOptions.forEach(([option]) => {
        if (item !== option) {
          option.selected = false;
        }
      });
      item.selected = true;
      return this.updateValueAndDisplayText();
    }
    /**
     * Handles updating selection when an option element requests selection via
     * property / attribute change.
     */
    handleRequestSelection(event) {
      const requestingOptionEl = event.target;
      if (this.lastSelectedOptionRecords.some(([option]) => option === requestingOptionEl)) {
        return;
      }
      this.selectItem(requestingOptionEl);
    }
    /**
     * Handles updating selection when an option element requests deselection via
     * property / attribute change.
     */
    handleRequestDeselection(event) {
      const requestingOptionEl = event.target;
      if (!this.lastSelectedOptionRecords.some(([option]) => option === requestingOptionEl)) {
        return;
      }
      this.updateValueAndDisplayText();
    }
    /**
     * Attempts to initialize the selected option from user-settable values like
     * SSR, setting `value`, or `selectedIndex` at startup.
     */
    initUserSelection() {
      if (this.lastUserSetValue && !this.lastSelectedOptionRecords.length) {
        this.select(this.lastUserSetValue);
      } else if (this.lastUserSetSelectedIndex !== null && !this.lastSelectedOptionRecords.length) {
        this.selectIndex(this.lastUserSetSelectedIndex);
      } else {
        this.updateValueAndDisplayText();
      }
    }
    handleIconChange() {
      this.hasLeadingIcon = this.leadingIcons.length > 0;
    }
    /**
     * Dispatches the `input` and `change` events.
     */
    dispatchInteractionEvents() {
      this.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
      this.dispatchEvent(new Event("change", { bubbles: true }));
    }
    getErrorText() {
      return this.error ? this.errorText : this.nativeErrorText;
    }
    [getFormValue]() {
      return this.value;
    }
    formResetCallback() {
      this.reset();
    }
    formStateRestoreCallback(state) {
      this.value = state;
    }
    click() {
      var _a3;
      (_a3 = this.field) == null ? void 0 : _a3.click();
    }
    [createValidator]() {
      return new SelectValidator(() => this);
    }
    [getValidityAnchor]() {
      return this.field;
    }
  };
  Select.shadowRootOptions = {
    ...i4.shadowRootOptions,
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean })
  ], Select.prototype, "quick", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Select.prototype, "required", void 0);
  __decorate([
    n3({ type: String, attribute: "error-text" })
  ], Select.prototype, "errorText", void 0);
  __decorate([
    n3()
  ], Select.prototype, "label", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-asterisk" })
  ], Select.prototype, "noAsterisk", void 0);
  __decorate([
    n3({ type: String, attribute: "supporting-text" })
  ], Select.prototype, "supportingText", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], Select.prototype, "error", void 0);
  __decorate([
    n3({ attribute: "menu-positioning" })
  ], Select.prototype, "menuPositioning", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "clamp-menu-width" })
  ], Select.prototype, "clampMenuWidth", void 0);
  __decorate([
    n3({ type: Number, attribute: "typeahead-delay" })
  ], Select.prototype, "typeaheadDelay", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "has-leading-icon" })
  ], Select.prototype, "hasLeadingIcon", void 0);
  __decorate([
    n3({ attribute: "display-text" })
  ], Select.prototype, "displayText", void 0);
  __decorate([
    n3({ attribute: "menu-align" })
  ], Select.prototype, "menuAlign", void 0);
  __decorate([
    n3()
  ], Select.prototype, "value", null);
  __decorate([
    n3({ type: Number, attribute: "selected-index" })
  ], Select.prototype, "selectedIndex", null);
  __decorate([
    r4()
  ], Select.prototype, "nativeError", void 0);
  __decorate([
    r4()
  ], Select.prototype, "nativeErrorText", void 0);
  __decorate([
    r4()
  ], Select.prototype, "focused", void 0);
  __decorate([
    r4()
  ], Select.prototype, "open", void 0);
  __decorate([
    r4()
  ], Select.prototype, "defaultFocus", void 0);
  __decorate([
    e4(".field")
  ], Select.prototype, "field", void 0);
  __decorate([
    e4("md-menu")
  ], Select.prototype, "menu", void 0);
  __decorate([
    e4("#label")
  ], Select.prototype, "labelEl", void 0);
  __decorate([
    o4({ slot: "leading-icon", flatten: true })
  ], Select.prototype, "leadingIcons", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/internal/outlined-select.js
  var OutlinedSelect = class extends Select {
    constructor() {
      super(...arguments);
      this.fieldTag = i6`md-outlined-field`;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/internal/outlined-select-styles.js
  var styles8 = i`:host{--_text-field-disabled-input-text-color: var(--md-outlined-select-text-field-disabled-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-disabled-input-text-opacity: var(--md-outlined-select-text-field-disabled-input-text-opacity, 0.38);--_text-field-disabled-label-text-color: var(--md-outlined-select-text-field-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-disabled-label-text-opacity: var(--md-outlined-select-text-field-disabled-label-text-opacity, 0.38);--_text-field-disabled-leading-icon-color: var(--md-outlined-select-text-field-disabled-leading-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-disabled-leading-icon-opacity: var(--md-outlined-select-text-field-disabled-leading-icon-opacity, 0.38);--_text-field-disabled-outline-color: var(--md-outlined-select-text-field-disabled-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-disabled-outline-opacity: var(--md-outlined-select-text-field-disabled-outline-opacity, 0.12);--_text-field-disabled-outline-width: var(--md-outlined-select-text-field-disabled-outline-width, 1px);--_text-field-disabled-supporting-text-color: var(--md-outlined-select-text-field-disabled-supporting-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-disabled-supporting-text-opacity: var(--md-outlined-select-text-field-disabled-supporting-text-opacity, 0.38);--_text-field-disabled-trailing-icon-color: var(--md-outlined-select-text-field-disabled-trailing-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-disabled-trailing-icon-opacity: var(--md-outlined-select-text-field-disabled-trailing-icon-opacity, 0.38);--_text-field-error-focus-input-text-color: var(--md-outlined-select-text-field-error-focus-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-error-focus-label-text-color: var(--md-outlined-select-text-field-error-focus-label-text-color, var(--md-sys-color-error, #b3261e));--_text-field-error-focus-leading-icon-color: var(--md-outlined-select-text-field-error-focus-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-error-focus-outline-color: var(--md-outlined-select-text-field-error-focus-outline-color, var(--md-sys-color-error, #b3261e));--_text-field-error-focus-supporting-text-color: var(--md-outlined-select-text-field-error-focus-supporting-text-color, var(--md-sys-color-error, #b3261e));--_text-field-error-focus-trailing-icon-color: var(--md-outlined-select-text-field-error-focus-trailing-icon-color, var(--md-sys-color-error, #b3261e));--_text-field-error-hover-input-text-color: var(--md-outlined-select-text-field-error-hover-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-error-hover-label-text-color: var(--md-outlined-select-text-field-error-hover-label-text-color, var(--md-sys-color-on-error-container, #410e0b));--_text-field-error-hover-leading-icon-color: var(--md-outlined-select-text-field-error-hover-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-error-hover-outline-color: var(--md-outlined-select-text-field-error-hover-outline-color, var(--md-sys-color-on-error-container, #410e0b));--_text-field-error-hover-supporting-text-color: var(--md-outlined-select-text-field-error-hover-supporting-text-color, var(--md-sys-color-error, #b3261e));--_text-field-error-hover-trailing-icon-color: var(--md-outlined-select-text-field-error-hover-trailing-icon-color, var(--md-sys-color-on-error-container, #410e0b));--_text-field-error-input-text-color: var(--md-outlined-select-text-field-error-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-error-label-text-color: var(--md-outlined-select-text-field-error-label-text-color, var(--md-sys-color-error, #b3261e));--_text-field-error-leading-icon-color: var(--md-outlined-select-text-field-error-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-error-outline-color: var(--md-outlined-select-text-field-error-outline-color, var(--md-sys-color-error, #b3261e));--_text-field-error-supporting-text-color: var(--md-outlined-select-text-field-error-supporting-text-color, var(--md-sys-color-error, #b3261e));--_text-field-error-trailing-icon-color: var(--md-outlined-select-text-field-error-trailing-icon-color, var(--md-sys-color-error, #b3261e));--_text-field-focus-input-text-color: var(--md-outlined-select-text-field-focus-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-focus-label-text-color: var(--md-outlined-select-text-field-focus-label-text-color, var(--md-sys-color-primary, #6750a4));--_text-field-focus-leading-icon-color: var(--md-outlined-select-text-field-focus-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-focus-outline-color: var(--md-outlined-select-text-field-focus-outline-color, var(--md-sys-color-primary, #6750a4));--_text-field-focus-outline-width: var(--md-outlined-select-text-field-focus-outline-width, 3px);--_text-field-focus-supporting-text-color: var(--md-outlined-select-text-field-focus-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-focus-trailing-icon-color: var(--md-outlined-select-text-field-focus-trailing-icon-color, var(--md-sys-color-primary, #6750a4));--_text-field-hover-input-text-color: var(--md-outlined-select-text-field-hover-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-hover-label-text-color: var(--md-outlined-select-text-field-hover-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-hover-leading-icon-color: var(--md-outlined-select-text-field-hover-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-hover-outline-color: var(--md-outlined-select-text-field-hover-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-hover-outline-width: var(--md-outlined-select-text-field-hover-outline-width, 1px);--_text-field-hover-supporting-text-color: var(--md-outlined-select-text-field-hover-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-hover-trailing-icon-color: var(--md-outlined-select-text-field-hover-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-input-text-color: var(--md-outlined-select-text-field-input-text-color, var(--md-sys-color-on-surface, #1d1b20));--_text-field-input-text-font: var(--md-outlined-select-text-field-input-text-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));--_text-field-input-text-line-height: var(--md-outlined-select-text-field-input-text-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));--_text-field-input-text-size: var(--md-outlined-select-text-field-input-text-size, var(--md-sys-typescale-body-large-size, 1rem));--_text-field-input-text-weight: var(--md-outlined-select-text-field-input-text-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));--_text-field-label-text-color: var(--md-outlined-select-text-field-label-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-label-text-font: var(--md-outlined-select-text-field-label-text-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));--_text-field-label-text-line-height: var(--md-outlined-select-text-field-label-text-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));--_text-field-label-text-populated-line-height: var(--md-outlined-select-text-field-label-text-populated-line-height, var(--md-sys-typescale-body-small-line-height, 1rem));--_text-field-label-text-populated-size: var(--md-outlined-select-text-field-label-text-populated-size, var(--md-sys-typescale-body-small-size, 0.75rem));--_text-field-label-text-size: var(--md-outlined-select-text-field-label-text-size, var(--md-sys-typescale-body-large-size, 1rem));--_text-field-label-text-weight: var(--md-outlined-select-text-field-label-text-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));--_text-field-leading-icon-color: var(--md-outlined-select-text-field-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-leading-icon-size: var(--md-outlined-select-text-field-leading-icon-size, 24px);--_text-field-outline-color: var(--md-outlined-select-text-field-outline-color, var(--md-sys-color-outline, #79747e));--_text-field-outline-width: var(--md-outlined-select-text-field-outline-width, 1px);--_text-field-supporting-text-color: var(--md-outlined-select-text-field-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-supporting-text-font: var(--md-outlined-select-text-field-supporting-text-font, var(--md-sys-typescale-body-small-font, var(--md-ref-typeface-plain, Roboto)));--_text-field-supporting-text-line-height: var(--md-outlined-select-text-field-supporting-text-line-height, var(--md-sys-typescale-body-small-line-height, 1rem));--_text-field-supporting-text-size: var(--md-outlined-select-text-field-supporting-text-size, var(--md-sys-typescale-body-small-size, 0.75rem));--_text-field-supporting-text-weight: var(--md-outlined-select-text-field-supporting-text-weight, var(--md-sys-typescale-body-small-weight, var(--md-ref-typeface-weight-regular, 400)));--_text-field-trailing-icon-color: var(--md-outlined-select-text-field-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_text-field-trailing-icon-size: var(--md-outlined-select-text-field-trailing-icon-size, 24px);--_text-field-container-shape-start-start: var(--md-outlined-select-text-field-container-shape-start-start, var(--md-outlined-select-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_text-field-container-shape-start-end: var(--md-outlined-select-text-field-container-shape-start-end, var(--md-outlined-select-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_text-field-container-shape-end-end: var(--md-outlined-select-text-field-container-shape-end-end, var(--md-outlined-select-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--_text-field-container-shape-end-start: var(--md-outlined-select-text-field-container-shape-end-start, var(--md-outlined-select-text-field-container-shape, var(--md-sys-shape-corner-extra-small, 4px)));--md-outlined-field-container-shape-end-end: var(--_text-field-container-shape-end-end);--md-outlined-field-container-shape-end-start: var(--_text-field-container-shape-end-start);--md-outlined-field-container-shape-start-end: var(--_text-field-container-shape-start-end);--md-outlined-field-container-shape-start-start: var(--_text-field-container-shape-start-start);--md-outlined-field-content-color: var(--_text-field-input-text-color);--md-outlined-field-content-font: var(--_text-field-input-text-font);--md-outlined-field-content-line-height: var(--_text-field-input-text-line-height);--md-outlined-field-content-size: var(--_text-field-input-text-size);--md-outlined-field-content-weight: var(--_text-field-input-text-weight);--md-outlined-field-disabled-content-color: var(--_text-field-disabled-input-text-color);--md-outlined-field-disabled-content-opacity: var(--_text-field-disabled-input-text-opacity);--md-outlined-field-disabled-label-text-color: var(--_text-field-disabled-label-text-color);--md-outlined-field-disabled-label-text-opacity: var(--_text-field-disabled-label-text-opacity);--md-outlined-field-disabled-leading-content-color: var(--_text-field-disabled-leading-icon-color);--md-outlined-field-disabled-leading-content-opacity: var(--_text-field-disabled-leading-icon-opacity);--md-outlined-field-disabled-outline-color: var(--_text-field-disabled-outline-color);--md-outlined-field-disabled-outline-opacity: var(--_text-field-disabled-outline-opacity);--md-outlined-field-disabled-outline-width: var(--_text-field-disabled-outline-width);--md-outlined-field-disabled-supporting-text-color: var(--_text-field-disabled-supporting-text-color);--md-outlined-field-disabled-supporting-text-opacity: var(--_text-field-disabled-supporting-text-opacity);--md-outlined-field-disabled-trailing-content-color: var(--_text-field-disabled-trailing-icon-color);--md-outlined-field-disabled-trailing-content-opacity: var(--_text-field-disabled-trailing-icon-opacity);--md-outlined-field-error-content-color: var(--_text-field-error-input-text-color);--md-outlined-field-error-focus-content-color: var(--_text-field-error-focus-input-text-color);--md-outlined-field-error-focus-label-text-color: var(--_text-field-error-focus-label-text-color);--md-outlined-field-error-focus-leading-content-color: var(--_text-field-error-focus-leading-icon-color);--md-outlined-field-error-focus-outline-color: var(--_text-field-error-focus-outline-color);--md-outlined-field-error-focus-supporting-text-color: var(--_text-field-error-focus-supporting-text-color);--md-outlined-field-error-focus-trailing-content-color: var(--_text-field-error-focus-trailing-icon-color);--md-outlined-field-error-hover-content-color: var(--_text-field-error-hover-input-text-color);--md-outlined-field-error-hover-label-text-color: var(--_text-field-error-hover-label-text-color);--md-outlined-field-error-hover-leading-content-color: var(--_text-field-error-hover-leading-icon-color);--md-outlined-field-error-hover-outline-color: var(--_text-field-error-hover-outline-color);--md-outlined-field-error-hover-supporting-text-color: var(--_text-field-error-hover-supporting-text-color);--md-outlined-field-error-hover-trailing-content-color: var(--_text-field-error-hover-trailing-icon-color);--md-outlined-field-error-label-text-color: var(--_text-field-error-label-text-color);--md-outlined-field-error-leading-content-color: var(--_text-field-error-leading-icon-color);--md-outlined-field-error-outline-color: var(--_text-field-error-outline-color);--md-outlined-field-error-supporting-text-color: var(--_text-field-error-supporting-text-color);--md-outlined-field-error-trailing-content-color: var(--_text-field-error-trailing-icon-color);--md-outlined-field-focus-content-color: var(--_text-field-focus-input-text-color);--md-outlined-field-focus-label-text-color: var(--_text-field-focus-label-text-color);--md-outlined-field-focus-leading-content-color: var(--_text-field-focus-leading-icon-color);--md-outlined-field-focus-outline-color: var(--_text-field-focus-outline-color);--md-outlined-field-focus-outline-width: var(--_text-field-focus-outline-width);--md-outlined-field-focus-supporting-text-color: var(--_text-field-focus-supporting-text-color);--md-outlined-field-focus-trailing-content-color: var(--_text-field-focus-trailing-icon-color);--md-outlined-field-hover-content-color: var(--_text-field-hover-input-text-color);--md-outlined-field-hover-label-text-color: var(--_text-field-hover-label-text-color);--md-outlined-field-hover-leading-content-color: var(--_text-field-hover-leading-icon-color);--md-outlined-field-hover-outline-color: var(--_text-field-hover-outline-color);--md-outlined-field-hover-outline-width: var(--_text-field-hover-outline-width);--md-outlined-field-hover-supporting-text-color: var(--_text-field-hover-supporting-text-color);--md-outlined-field-hover-trailing-content-color: var(--_text-field-hover-trailing-icon-color);--md-outlined-field-label-text-color: var(--_text-field-label-text-color);--md-outlined-field-label-text-font: var(--_text-field-label-text-font);--md-outlined-field-label-text-line-height: var(--_text-field-label-text-line-height);--md-outlined-field-label-text-populated-line-height: var(--_text-field-label-text-populated-line-height);--md-outlined-field-label-text-populated-size: var(--_text-field-label-text-populated-size);--md-outlined-field-label-text-size: var(--_text-field-label-text-size);--md-outlined-field-label-text-weight: var(--_text-field-label-text-weight);--md-outlined-field-leading-content-color: var(--_text-field-leading-icon-color);--md-outlined-field-outline-color: var(--_text-field-outline-color);--md-outlined-field-outline-width: var(--_text-field-outline-width);--md-outlined-field-supporting-text-color: var(--_text-field-supporting-text-color);--md-outlined-field-supporting-text-font: var(--_text-field-supporting-text-font);--md-outlined-field-supporting-text-line-height: var(--_text-field-supporting-text-line-height);--md-outlined-field-supporting-text-size: var(--_text-field-supporting-text-size);--md-outlined-field-supporting-text-weight: var(--_text-field-supporting-text-weight);--md-outlined-field-trailing-content-color: var(--_text-field-trailing-icon-color)}[has-start] .icon.leading{font-size:var(--_text-field-leading-icon-size);height:var(--_text-field-leading-icon-size);width:var(--_text-field-leading-icon-size)}.icon.trailing{font-size:var(--_text-field-trailing-icon-size);height:var(--_text-field-trailing-icon-size);width:var(--_text-field-trailing-icon-size)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/internal/shared-styles.js
  var styles9 = i`:host{color:unset;min-width:210px;display:flex}.field{cursor:default;outline:none}.select{position:relative;flex-direction:column}.icon.trailing svg,.icon ::slotted(*){fill:currentColor}.icon ::slotted(*){width:inherit;height:inherit;font-size:inherit}.icon slot{display:flex;height:100%;width:100%;align-items:center;justify-content:center}.icon.trailing :is(.up,.down){opacity:0;transition:opacity 75ms linear 75ms}.select:not(.open) .down,.select.open .up{opacity:1}.field,.select,md-menu{min-width:inherit;width:inherit;max-width:inherit;display:flex}md-menu{min-width:var(--__menu-min-width);max-width:var(--__menu-max-width, inherit)}.menu-wrapper{width:0px;height:0px;max-width:inherit}md-menu ::slotted(:not[disabled]){cursor:pointer}.field,.select{width:100%}:host{display:inline-flex}:host([disabled]){pointer-events:none}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/outlined-select.js
  var MdOutlinedSelect = class MdOutlinedSelect2 extends OutlinedSelect {
  };
  MdOutlinedSelect.styles = [styles9, styles8];
  if (!customElements.get("md-outlined-select")) {
    MdOutlinedSelect = __decorate([
      t("md-outlined-select")
    ], MdOutlinedSelect);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/internal/menuitem/menu-item-styles.js
  var styles10 = i`:host{display:flex;--md-ripple-hover-color: var(--md-menu-item-hover-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-hover-opacity: var(--md-menu-item-hover-state-layer-opacity, 0.08);--md-ripple-pressed-color: var(--md-menu-item-pressed-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-pressed-opacity: var(--md-menu-item-pressed-state-layer-opacity, 0.12)}:host([disabled]){opacity:var(--md-menu-item-disabled-opacity, 0.3);pointer-events:none}md-focus-ring{z-index:1;--md-focus-ring-shape: 8px}a,button,li{background:none;border:none;padding:0;margin:0;text-align:unset;text-decoration:none}.list-item{border-radius:inherit;display:flex;flex:1;max-width:inherit;min-width:inherit;outline:none;-webkit-tap-highlight-color:rgba(0,0,0,0)}.list-item:not(.disabled){cursor:pointer}[slot=container]{pointer-events:none}md-ripple{border-radius:inherit}md-item{border-radius:inherit;flex:1;color:var(--md-menu-item-label-text-color, var(--md-sys-color-on-surface, #1d1b20));font-family:var(--md-menu-item-label-text-font, var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto)));font-size:var(--md-menu-item-label-text-size, var(--md-sys-typescale-body-large-size, 1rem));line-height:var(--md-menu-item-label-text-line-height, var(--md-sys-typescale-body-large-line-height, 1.5rem));font-weight:var(--md-menu-item-label-text-weight, var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400)));min-height:var(--md-menu-item-one-line-container-height, 56px);padding-top:var(--md-menu-item-top-space, 12px);padding-bottom:var(--md-menu-item-bottom-space, 12px);padding-inline-start:var(--md-menu-item-leading-space, 16px);padding-inline-end:var(--md-menu-item-trailing-space, 16px)}md-item[multiline]{min-height:var(--md-menu-item-two-line-container-height, 72px)}[slot=supporting-text]{color:var(--md-menu-item-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));font-family:var(--md-menu-item-supporting-text-font, var(--md-sys-typescale-body-medium-font, var(--md-ref-typeface-plain, Roboto)));font-size:var(--md-menu-item-supporting-text-size, var(--md-sys-typescale-body-medium-size, 0.875rem));line-height:var(--md-menu-item-supporting-text-line-height, var(--md-sys-typescale-body-medium-line-height, 1.25rem));font-weight:var(--md-menu-item-supporting-text-weight, var(--md-sys-typescale-body-medium-weight, var(--md-ref-typeface-weight-regular, 400)))}[slot=trailing-supporting-text]{color:var(--md-menu-item-trailing-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));font-family:var(--md-menu-item-trailing-supporting-text-font, var(--md-sys-typescale-label-small-font, var(--md-ref-typeface-plain, Roboto)));font-size:var(--md-menu-item-trailing-supporting-text-size, var(--md-sys-typescale-label-small-size, 0.6875rem));line-height:var(--md-menu-item-trailing-supporting-text-line-height, var(--md-sys-typescale-label-small-line-height, 1rem));font-weight:var(--md-menu-item-trailing-supporting-text-weight, var(--md-sys-typescale-label-small-weight, var(--md-ref-typeface-weight-medium, 500)))}:is([slot=start],[slot=end])::slotted(*){fill:currentColor}[slot=start]{color:var(--md-menu-item-leading-icon-color, var(--md-sys-color-on-surface-variant, #49454f))}[slot=end]{color:var(--md-menu-item-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f))}.list-item{background-color:var(--md-menu-item-container-color, transparent)}.list-item.selected{background-color:var(--md-menu-item-selected-container-color, var(--md-sys-color-secondary-container, #e8def8))}.selected:not(.disabled) ::slotted(*){color:var(--md-menu-item-selected-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b))}@media(forced-colors: active){:host([disabled]),:host([disabled]) slot{color:GrayText;opacity:1}.list-item{position:relative}.list-item.selected::before{content:"";position:absolute;inset:0;box-sizing:border-box;border-radius:inherit;pointer-events:none;border:3px double CanvasText}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/item/internal/item.js
  var Item = class extends i4 {
    constructor() {
      super(...arguments);
      this.multiline = false;
    }
    render() {
      return b2`
      <slot name="container"></slot>
      <slot class="non-text" name="start"></slot>
      <div class="text">
        <slot name="overline" @slotchange=${this.handleTextSlotChange}></slot>
        <slot
          class="default-slot"
          @slotchange=${this.handleTextSlotChange}></slot>
        <slot name="headline" @slotchange=${this.handleTextSlotChange}></slot>
        <slot
          name="supporting-text"
          @slotchange=${this.handleTextSlotChange}></slot>
      </div>
      <slot class="non-text" name="trailing-supporting-text"></slot>
      <slot class="non-text" name="end"></slot>
    `;
    }
    handleTextSlotChange() {
      let isMultiline = false;
      let slotsWithContent = 0;
      for (const slot of this.textSlots) {
        if (slotHasContent(slot)) {
          slotsWithContent += 1;
        }
        if (slotsWithContent > 1) {
          isMultiline = true;
          break;
        }
      }
      this.multiline = isMultiline;
    }
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], Item.prototype, "multiline", void 0);
  __decorate([
    r5(".text slot")
  ], Item.prototype, "textSlots", void 0);
  function slotHasContent(slot) {
    var _a3;
    for (const node of slot.assignedNodes({ flatten: true })) {
      const isElement = node.nodeType === Node.ELEMENT_NODE;
      const isTextWithContent = node.nodeType === Node.TEXT_NODE && ((_a3 = node.textContent) == null ? void 0 : _a3.match(/\S/));
      if (isElement || isTextWithContent) {
        return true;
      }
    }
    return false;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/item/internal/item-styles.js
  var styles11 = i`:host{color:var(--md-sys-color-on-surface, #1d1b20);font-family:var(--md-sys-typescale-body-large-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-body-large-size, 1rem);font-weight:var(--md-sys-typescale-body-large-weight, var(--md-ref-typeface-weight-regular, 400));line-height:var(--md-sys-typescale-body-large-line-height, 1.5rem);align-items:center;box-sizing:border-box;display:flex;gap:16px;min-height:56px;overflow:hidden;padding:12px 16px;position:relative;text-overflow:ellipsis}:host([multiline]){min-height:72px}[name=overline]{color:var(--md-sys-color-on-surface-variant, #49454f);font-family:var(--md-sys-typescale-label-small-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-label-small-size, 0.6875rem);font-weight:var(--md-sys-typescale-label-small-weight, var(--md-ref-typeface-weight-medium, 500));line-height:var(--md-sys-typescale-label-small-line-height, 1rem)}[name=supporting-text]{color:var(--md-sys-color-on-surface-variant, #49454f);font-family:var(--md-sys-typescale-body-medium-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-body-medium-size, 0.875rem);font-weight:var(--md-sys-typescale-body-medium-weight, var(--md-ref-typeface-weight-regular, 400));line-height:var(--md-sys-typescale-body-medium-line-height, 1.25rem)}[name=trailing-supporting-text]{color:var(--md-sys-color-on-surface-variant, #49454f);font-family:var(--md-sys-typescale-label-small-font, var(--md-ref-typeface-plain, Roboto));font-size:var(--md-sys-typescale-label-small-size, 0.6875rem);font-weight:var(--md-sys-typescale-label-small-weight, var(--md-ref-typeface-weight-medium, 500));line-height:var(--md-sys-typescale-label-small-line-height, 1rem)}[name=container]::slotted(*){inset:0;position:absolute}.default-slot{display:inline}.default-slot,.text ::slotted(*){overflow:hidden;text-overflow:ellipsis}.text{display:flex;flex:1;flex-direction:column;overflow:hidden}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/item/item.js
  var MdItem = class MdItem2 extends Item {
  };
  MdItem.styles = [styles11];
  if (!customElements.get("md-item")) {
    MdItem = __decorate([
      t("md-item")
    ], MdItem);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/ripple/internal/ripple.js
  var PRESS_GROW_MS = 450;
  var MINIMUM_PRESS_MS = 225;
  var INITIAL_ORIGIN_SCALE = 0.2;
  var PADDING = 10;
  var SOFT_EDGE_MINIMUM_SIZE = 75;
  var SOFT_EDGE_CONTAINER_RATIO = 0.35;
  var PRESS_PSEUDO = "::after";
  var ANIMATION_FILL = "forwards";
  var State;
  (function(State2) {
    State2[State2["INACTIVE"] = 0] = "INACTIVE";
    State2[State2["TOUCH_DELAY"] = 1] = "TOUCH_DELAY";
    State2[State2["HOLDING"] = 2] = "HOLDING";
    State2[State2["WAITING_FOR_CLICK"] = 3] = "WAITING_FOR_CLICK";
  })(State || (State = {}));
  var EVENTS2 = [
    "click",
    "contextmenu",
    "pointercancel",
    "pointerdown",
    "pointerenter",
    "pointerleave",
    "pointerup"
  ];
  var TOUCH_DELAY_MS = 150;
  var FORCED_COLORS = o7 ? null : window.matchMedia("(forced-colors: active)");
  var Ripple = class extends i4 {
    constructor() {
      super(...arguments);
      this.disabled = false;
      this.hovered = false;
      this.pressed = false;
      this.rippleSize = "";
      this.rippleScale = "";
      this.initialSize = 0;
      this.state = State.INACTIVE;
      this.attachableController = new AttachableController(this, this.onControlChange.bind(this));
    }
    get htmlFor() {
      return this.attachableController.htmlFor;
    }
    set htmlFor(htmlFor) {
      this.attachableController.htmlFor = htmlFor;
    }
    get control() {
      return this.attachableController.control;
    }
    set control(control) {
      this.attachableController.control = control;
    }
    attach(control) {
      this.attachableController.attach(control);
    }
    detach() {
      this.attachableController.detach();
    }
    connectedCallback() {
      super.connectedCallback();
      this.setAttribute("aria-hidden", "true");
    }
    render() {
      const classes = {
        "hovered": this.hovered,
        "pressed": this.pressed
      };
      return b2`<div class="surface ${e8(classes)}"></div>`;
    }
    update(changedProps) {
      if (changedProps.has("disabled") && this.disabled) {
        this.hovered = false;
        this.pressed = false;
      }
      super.update(changedProps);
    }
    /**
     * TODO(b/269799771): make private
     * @private only public for slider
     */
    handlePointerenter(event) {
      if (!this.shouldReactToEvent(event)) {
        return;
      }
      this.hovered = true;
    }
    /**
     * TODO(b/269799771): make private
     * @private only public for slider
     */
    handlePointerleave(event) {
      if (!this.shouldReactToEvent(event)) {
        return;
      }
      this.hovered = false;
      if (this.state !== State.INACTIVE) {
        this.endPressAnimation();
      }
    }
    handlePointerup(event) {
      if (!this.shouldReactToEvent(event)) {
        return;
      }
      if (this.state === State.HOLDING) {
        this.state = State.WAITING_FOR_CLICK;
        return;
      }
      if (this.state === State.TOUCH_DELAY) {
        this.state = State.WAITING_FOR_CLICK;
        this.startPressAnimation(this.rippleStartEvent);
        return;
      }
    }
    async handlePointerdown(event) {
      if (!this.shouldReactToEvent(event)) {
        return;
      }
      this.rippleStartEvent = event;
      if (!this.isTouch(event)) {
        this.state = State.WAITING_FOR_CLICK;
        this.startPressAnimation(event);
        return;
      }
      this.state = State.TOUCH_DELAY;
      await new Promise((resolve) => {
        setTimeout(resolve, TOUCH_DELAY_MS);
      });
      if (this.state !== State.TOUCH_DELAY) {
        return;
      }
      this.state = State.HOLDING;
      this.startPressAnimation(event);
    }
    handleClick() {
      if (this.disabled) {
        return;
      }
      if (this.state === State.WAITING_FOR_CLICK) {
        this.endPressAnimation();
        return;
      }
      if (this.state === State.INACTIVE) {
        this.startPressAnimation();
        this.endPressAnimation();
      }
    }
    handlePointercancel(event) {
      if (!this.shouldReactToEvent(event)) {
        return;
      }
      this.endPressAnimation();
    }
    handleContextmenu() {
      if (this.disabled) {
        return;
      }
      this.endPressAnimation();
    }
    determineRippleSize() {
      const { height, width } = this.getBoundingClientRect();
      const maxDim = Math.max(height, width);
      const softEdgeSize = Math.max(SOFT_EDGE_CONTAINER_RATIO * maxDim, SOFT_EDGE_MINIMUM_SIZE);
      const zoom = this.currentCSSZoom ?? 1;
      const initialSize = Math.floor(maxDim * INITIAL_ORIGIN_SCALE / zoom);
      const hypotenuse = Math.sqrt(width ** 2 + height ** 2);
      const maxRadius = hypotenuse + PADDING;
      this.initialSize = initialSize;
      const maybeZoomedScale = (maxRadius + softEdgeSize) / initialSize;
      this.rippleScale = `${maybeZoomedScale / zoom}`;
      this.rippleSize = `${initialSize}px`;
    }
    getNormalizedPointerEventCoords(pointerEvent) {
      const { scrollX, scrollY } = window;
      const { left, top } = this.getBoundingClientRect();
      const documentX = scrollX + left;
      const documentY = scrollY + top;
      const { pageX, pageY } = pointerEvent;
      const zoom = this.currentCSSZoom ?? 1;
      return {
        x: (pageX - documentX) / zoom,
        y: (pageY - documentY) / zoom
      };
    }
    getTranslationCoordinates(positionEvent) {
      const { height, width } = this.getBoundingClientRect();
      const zoom = this.currentCSSZoom ?? 1;
      const endPoint = {
        x: (width / zoom - this.initialSize) / 2,
        y: (height / zoom - this.initialSize) / 2
      };
      let startPoint;
      if (positionEvent instanceof PointerEvent) {
        startPoint = this.getNormalizedPointerEventCoords(positionEvent);
      } else {
        startPoint = {
          x: width / zoom / 2,
          y: height / zoom / 2
        };
      }
      startPoint = {
        x: startPoint.x - this.initialSize / 2,
        y: startPoint.y - this.initialSize / 2
      };
      return { startPoint, endPoint };
    }
    startPressAnimation(positionEvent) {
      var _a3;
      if (!this.mdRoot) {
        return;
      }
      this.pressed = true;
      (_a3 = this.growAnimation) == null ? void 0 : _a3.cancel();
      this.determineRippleSize();
      const { startPoint, endPoint } = this.getTranslationCoordinates(positionEvent);
      const translateStart = `${startPoint.x}px, ${startPoint.y}px`;
      const translateEnd = `${endPoint.x}px, ${endPoint.y}px`;
      this.growAnimation = this.mdRoot.animate({
        top: [0, 0],
        left: [0, 0],
        height: [this.rippleSize, this.rippleSize],
        width: [this.rippleSize, this.rippleSize],
        transform: [
          `translate(${translateStart}) scale(1)`,
          `translate(${translateEnd}) scale(${this.rippleScale})`
        ]
      }, {
        pseudoElement: PRESS_PSEUDO,
        duration: PRESS_GROW_MS,
        easing: EASING.STANDARD,
        fill: ANIMATION_FILL
      });
    }
    async endPressAnimation() {
      this.rippleStartEvent = void 0;
      this.state = State.INACTIVE;
      const animation = this.growAnimation;
      let pressAnimationPlayState = Infinity;
      if (typeof (animation == null ? void 0 : animation.currentTime) === "number") {
        pressAnimationPlayState = animation.currentTime;
      } else if (animation == null ? void 0 : animation.currentTime) {
        pressAnimationPlayState = animation.currentTime.to("ms").value;
      }
      if (pressAnimationPlayState >= MINIMUM_PRESS_MS) {
        this.pressed = false;
        return;
      }
      await new Promise((resolve) => {
        setTimeout(resolve, MINIMUM_PRESS_MS - pressAnimationPlayState);
      });
      if (this.growAnimation !== animation) {
        return;
      }
      this.pressed = false;
    }
    /**
     * Returns `true` if
     *  - the ripple element is enabled
     *  - the pointer is primary for the input type
     *  - the pointer is the pointer that started the interaction, or will start
     * the interaction
     *  - the pointer is a touch, or the pointer state has the primary button
     * held, or the pointer is hovering
     */
    shouldReactToEvent(event) {
      if (this.disabled || !event.isPrimary) {
        return false;
      }
      if (this.rippleStartEvent && this.rippleStartEvent.pointerId !== event.pointerId) {
        return false;
      }
      if (event.type === "pointerenter" || event.type === "pointerleave") {
        return !this.isTouch(event);
      }
      const isPrimaryButton = event.buttons === 1;
      return this.isTouch(event) || isPrimaryButton;
    }
    isTouch({ pointerType }) {
      return pointerType === "touch";
    }
    /** @private */
    async handleEvent(event) {
      if (FORCED_COLORS == null ? void 0 : FORCED_COLORS.matches) {
        return;
      }
      switch (event.type) {
        case "click":
          this.handleClick();
          break;
        case "contextmenu":
          this.handleContextmenu();
          break;
        case "pointercancel":
          this.handlePointercancel(event);
          break;
        case "pointerdown":
          await this.handlePointerdown(event);
          break;
        case "pointerenter":
          this.handlePointerenter(event);
          break;
        case "pointerleave":
          this.handlePointerleave(event);
          break;
        case "pointerup":
          this.handlePointerup(event);
          break;
        default:
          break;
      }
    }
    onControlChange(prev, next) {
      if (o7)
        return;
      for (const event of EVENTS2) {
        prev == null ? void 0 : prev.removeEventListener(event, this);
        next == null ? void 0 : next.addEventListener(event, this);
      }
    }
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], Ripple.prototype, "disabled", void 0);
  __decorate([
    r4()
  ], Ripple.prototype, "hovered", void 0);
  __decorate([
    r4()
  ], Ripple.prototype, "pressed", void 0);
  __decorate([
    e4(".surface")
  ], Ripple.prototype, "mdRoot", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/ripple/internal/ripple-styles.js
  var styles12 = i`:host{display:flex;margin:auto;pointer-events:none}:host([disabled]){display:none}@media(forced-colors: active){:host{display:none}}:host,.surface{border-radius:inherit;position:absolute;inset:0;overflow:hidden}.surface{-webkit-tap-highlight-color:rgba(0,0,0,0)}.surface::before,.surface::after{content:"";opacity:0;position:absolute}.surface::before{background-color:var(--md-ripple-hover-color, var(--md-sys-color-on-surface, #1d1b20));inset:0;transition:opacity 15ms linear,background-color 15ms linear}.surface::after{background:radial-gradient(closest-side, var(--md-ripple-pressed-color, var(--md-sys-color-on-surface, #1d1b20)) max(100% - 70px, 65%), transparent 100%);transform-origin:center center;transition:opacity 375ms linear}.hovered::before{background-color:var(--md-ripple-hover-color, var(--md-sys-color-on-surface, #1d1b20));opacity:var(--md-ripple-hover-opacity, 0.08)}.pressed::after{opacity:var(--md-ripple-pressed-opacity, 0.12);transition-duration:105ms}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/ripple/ripple.js
  var MdRipple = class MdRipple2 extends Ripple {
  };
  MdRipple.styles = [styles12];
  if (!customElements.get("md-ripple")) {
    MdRipple = __decorate([
      t("md-ripple")
    ], MdRipple);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/menu/internal/controllers/menuItemController.js
  var MenuItemController = class {
    /**
     * @param host The MenuItem in which to attach this controller to.
     * @param config The object that configures this controller's behavior.
     */
    constructor(host, config) {
      this.host = host;
      this.internalTypeaheadText = null;
      this.onClick = () => {
        if (this.host.keepOpen)
          return;
        this.host.dispatchEvent(createDefaultCloseMenuEvent(this.host, {
          kind: CloseReason.CLICK_SELECTION
        }));
      };
      this.onKeydown = (event) => {
        if (this.host.href && event.code === "Enter") {
          const interactiveElement = this.getInteractiveElement();
          if (interactiveElement instanceof HTMLAnchorElement) {
            interactiveElement.click();
          }
        }
        if (event.defaultPrevented)
          return;
        const keyCode = event.code;
        if (this.host.keepOpen && keyCode !== "Escape")
          return;
        if (isClosableKey(keyCode)) {
          event.preventDefault();
          this.host.dispatchEvent(createDefaultCloseMenuEvent(this.host, {
            kind: CloseReason.KEYDOWN,
            key: keyCode
          }));
        }
      };
      this.getHeadlineElements = config.getHeadlineElements;
      this.getSupportingTextElements = config.getSupportingTextElements;
      this.getDefaultElements = config.getDefaultElements;
      this.getInteractiveElement = config.getInteractiveElement;
      this.host.addController(this);
    }
    /**
     * The text that is selectable via typeahead. If not set, defaults to the
     * innerText of the item slotted into the `"headline"` slot, and if there are
     * no slotted elements into headline, then it checks the _default_ slot, and
     * then the `"supporting-text"` slot if nothing is in _default_.
     */
    get typeaheadText() {
      if (this.internalTypeaheadText !== null) {
        return this.internalTypeaheadText;
      }
      const headlineElements = this.getHeadlineElements();
      const textParts = [];
      headlineElements.forEach((headlineElement) => {
        if (headlineElement.textContent && headlineElement.textContent.trim()) {
          textParts.push(headlineElement.textContent.trim());
        }
      });
      if (textParts.length === 0) {
        this.getDefaultElements().forEach((defaultElement) => {
          if (defaultElement.textContent && defaultElement.textContent.trim()) {
            textParts.push(defaultElement.textContent.trim());
          }
        });
      }
      if (textParts.length === 0) {
        this.getSupportingTextElements().forEach((supportingTextElement) => {
          if (supportingTextElement.textContent && supportingTextElement.textContent.trim()) {
            textParts.push(supportingTextElement.textContent.trim());
          }
        });
      }
      return textParts.join(" ");
    }
    /**
     * The recommended tag name to render as the list item.
     */
    get tagName() {
      const type = this.host.type;
      switch (type) {
        case "link":
          return "a";
        case "button":
          return "button";
        default:
        case "menuitem":
        case "option":
          return "li";
      }
    }
    /**
     * The recommended role of the menu item.
     */
    get role() {
      return this.host.type === "option" ? "option" : "menuitem";
    }
    hostConnected() {
      this.host.toggleAttribute("md-menu-item", true);
    }
    hostUpdate() {
      if (this.host.href) {
        this.host.type = "link";
      }
    }
    /**
     * Use to set the typeaheadText when it changes.
     */
    setTypeaheadText(text) {
      this.internalTypeaheadText = text;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/internal/selectoption/selectOptionController.js
  function createRequestSelectionEvent() {
    return new Event("request-selection", {
      bubbles: true,
      composed: true
    });
  }
  function createRequestDeselectionEvent() {
    return new Event("request-deselection", {
      bubbles: true,
      composed: true
    });
  }
  var SelectOptionController = class {
    /**
     * The recommended role of the select option.
     */
    get role() {
      return this.menuItemController.role;
    }
    /**
     * The text that is selectable via typeahead. If not set, defaults to the
     * innerText of the item slotted into the `"headline"` slot, and if there are
     * no slotted elements into headline, then it checks the _default_ slot, and
     * then the `"supporting-text"` slot if nothing is in _default_.
     */
    get typeaheadText() {
      return this.menuItemController.typeaheadText;
    }
    setTypeaheadText(text) {
      this.menuItemController.setTypeaheadText(text);
    }
    /**
     * The text that is displayed in the select field when selected. If not set,
     * defaults to the textContent of the item slotted into the `"headline"` slot,
     * and if there are no slotted elements into headline, then it checks the
     * _default_ slot, and then the `"supporting-text"` slot if nothing is in
     * _default_.
     */
    get displayText() {
      if (this.internalDisplayText !== null) {
        return this.internalDisplayText;
      }
      return this.menuItemController.typeaheadText;
    }
    setDisplayText(text) {
      this.internalDisplayText = text;
    }
    /**
     * @param host The SelectOption in which to attach this controller to.
     * @param config The object that configures this controller's behavior.
     */
    constructor(host, config) {
      this.host = host;
      this.internalDisplayText = null;
      this.firstUpdate = true;
      this.onClick = () => {
        this.menuItemController.onClick();
      };
      this.onKeydown = (e9) => {
        this.menuItemController.onKeydown(e9);
      };
      this.lastSelected = this.host.selected;
      this.menuItemController = new MenuItemController(host, config);
      host.addController(this);
    }
    hostUpdate() {
      if (this.lastSelected !== this.host.selected) {
        this.host.ariaSelected = this.host.selected ? "true" : "false";
      }
    }
    hostUpdated() {
      if (this.lastSelected !== this.host.selected && !this.firstUpdate) {
        if (this.host.selected) {
          this.host.dispatchEvent(createRequestSelectionEvent());
        } else {
          this.host.dispatchEvent(createRequestDeselectionEvent());
        }
      }
      this.lastSelected = this.host.selected;
      this.firstUpdate = false;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/internal/selectoption/select-option.js
  var selectOptionBaseClass = mixinDelegatesAria(i4);
  var SelectOptionEl = class extends selectOptionBaseClass {
    constructor() {
      super(...arguments);
      this.disabled = false;
      this.isMenuItem = true;
      this.selected = false;
      this.value = "";
      this.type = "option";
      this.selectOptionController = new SelectOptionController(this, {
        getHeadlineElements: () => {
          return this.headlineElements;
        },
        getSupportingTextElements: () => {
          return this.supportingTextElements;
        },
        getDefaultElements: () => {
          return this.defaultElements;
        },
        getInteractiveElement: () => this.listItemRoot
      });
    }
    /**
     * The text that is selectable via typeahead. If not set, defaults to the
     * innerText of the item slotted into the `"headline"` slot.
     */
    get typeaheadText() {
      return this.selectOptionController.typeaheadText;
    }
    set typeaheadText(text) {
      this.selectOptionController.setTypeaheadText(text);
    }
    /**
     * The text that is displayed in the select field when selected. If not set,
     * defaults to the textContent of the item slotted into the `"headline"` slot.
     */
    get displayText() {
      return this.selectOptionController.displayText;
    }
    set displayText(text) {
      this.selectOptionController.setDisplayText(text);
    }
    render() {
      return this.renderListItem(b2`
      <md-item>
        <div slot="container">
          ${this.renderRipple()} ${this.renderFocusRing()}
        </div>
        <slot name="start" slot="start"></slot>
        <slot name="end" slot="end"></slot>
        ${this.renderBody()}
      </md-item>
    `);
    }
    /**
     * Renders the root list item.
     *
     * @param content the child content of the list item.
     */
    renderListItem(content) {
      return b2`
      <li
        id="item"
        tabindex=${this.disabled ? -1 : 0}
        role=${this.selectOptionController.role}
        aria-label=${this.ariaLabel || A}
        aria-selected=${this.ariaSelected || A}
        aria-checked=${this.ariaChecked || A}
        aria-expanded=${this.ariaExpanded || A}
        aria-haspopup=${this.ariaHasPopup || A}
        class="list-item ${e8(this.getRenderClasses())}"
        @click=${this.selectOptionController.onClick}
        @keydown=${this.selectOptionController.onKeydown}
        >${content}</li
      >
    `;
    }
    /**
     * Handles rendering of the ripple element.
     */
    renderRipple() {
      return b2` <md-ripple
      part="ripple"
      for="item"
      ?disabled=${this.disabled}></md-ripple>`;
    }
    /**
     * Handles rendering of the focus ring.
     */
    renderFocusRing() {
      return b2` <md-focus-ring
      part="focus-ring"
      for="item"
      inward></md-focus-ring>`;
    }
    /**
     * Classes applied to the list item root.
     */
    getRenderClasses() {
      return {
        "disabled": this.disabled,
        "selected": this.selected
      };
    }
    /**
     * Handles rendering the headline and supporting text.
     */
    renderBody() {
      return b2`
      <slot></slot>
      <slot name="overline" slot="overline"></slot>
      <slot name="headline" slot="headline"></slot>
      <slot name="supporting-text" slot="supporting-text"></slot>
      <slot
        name="trailing-supporting-text"
        slot="trailing-supporting-text"></slot>
    `;
    }
    focus() {
      var _a3;
      (_a3 = this.listItemRoot) == null ? void 0 : _a3.focus();
    }
  };
  SelectOptionEl.shadowRootOptions = {
    ...i4.shadowRootOptions,
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], SelectOptionEl.prototype, "disabled", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "md-menu-item", reflect: true })
  ], SelectOptionEl.prototype, "isMenuItem", void 0);
  __decorate([
    n3({ type: Boolean })
  ], SelectOptionEl.prototype, "selected", void 0);
  __decorate([
    n3()
  ], SelectOptionEl.prototype, "value", void 0);
  __decorate([
    e4(".list-item")
  ], SelectOptionEl.prototype, "listItemRoot", void 0);
  __decorate([
    o4({ slot: "headline" })
  ], SelectOptionEl.prototype, "headlineElements", void 0);
  __decorate([
    o4({ slot: "supporting-text" })
  ], SelectOptionEl.prototype, "supportingTextElements", void 0);
  __decorate([
    n4({ slot: "" })
  ], SelectOptionEl.prototype, "defaultElements", void 0);
  __decorate([
    n3({ attribute: "typeahead-text" })
  ], SelectOptionEl.prototype, "typeaheadText", null);
  __decorate([
    n3({ attribute: "display-text" })
  ], SelectOptionEl.prototype, "displayText", null);

  // custom_components/smart_agent/frontend/node_modules/@material/web/select/select-option.js
  var MdSelectOption = class MdSelectOption2 extends SelectOptionEl {
  };
  MdSelectOption.styles = [styles10];
  if (!customElements.get("md-select-option")) {
    MdSelectOption = __decorate([
      t("md-select-option")
    ], MdSelectOption);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/divider/internal/divider.js
  var Divider = class extends i4 {
    constructor() {
      super(...arguments);
      this.inset = false;
      this.insetStart = false;
      this.insetEnd = false;
    }
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], Divider.prototype, "inset", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true, attribute: "inset-start" })
  ], Divider.prototype, "insetStart", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true, attribute: "inset-end" })
  ], Divider.prototype, "insetEnd", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/divider/internal/divider-styles.js
  var styles13 = i`:host{box-sizing:border-box;color:var(--md-divider-color, var(--md-sys-color-outline-variant, #cac4d0));display:flex;height:var(--md-divider-thickness, 1px);width:100%}:host([inset]),:host([inset-start]){padding-inline-start:16px}:host([inset]),:host([inset-end]){padding-inline-end:16px}:host::before{background:currentColor;content:"";height:100%;width:100%}@media(forced-colors: active){:host::before{background:CanvasText}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/divider/divider.js
  var MdDivider = class MdDivider2 extends Divider {
  };
  MdDivider.styles = [styles13];
  if (!customElements.get("md-divider")) {
    MdDivider = __decorate([
      t("md-divider")
    ], MdDivider);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/dialog/internal/animations.js
  var DIALOG_DEFAULT_OPEN_ANIMATION = {
    dialog: [
      [
        // Dialog slide down
        [{ "transform": "translateY(-50px)" }, { "transform": "translateY(0)" }],
        { duration: 500, easing: EASING.EMPHASIZED }
      ]
    ],
    scrim: [
      [
        // Scrim fade in
        [{ "opacity": 0 }, { "opacity": 0.32 }],
        { duration: 500, easing: "linear" }
      ]
    ],
    container: [
      [
        // Container fade in
        [{ "opacity": 0 }, { "opacity": 1 }],
        { duration: 50, easing: "linear", pseudoElement: "::before" }
      ],
      [
        // Container grow
        // Note: current spec says to grow from 0dp->100% and shrink from
        // 100%->35%. We change this to 35%->100% to simplify the animation that
        // is supposed to clip content as it grows. From 0dp it's possible to see
        // text/actions appear before the container has fully grown.
        [{ "height": "35%" }, { "height": "100%" }],
        { duration: 500, easing: EASING.EMPHASIZED, pseudoElement: "::before" }
      ]
    ],
    headline: [
      [
        // Headline fade in
        [{ "opacity": 0 }, { "opacity": 0, offset: 0.2 }, { "opacity": 1 }],
        { duration: 250, easing: "linear", fill: "forwards" }
      ]
    ],
    content: [
      [
        // Content fade in
        [{ "opacity": 0 }, { "opacity": 0, offset: 0.2 }, { "opacity": 1 }],
        { duration: 250, easing: "linear", fill: "forwards" }
      ]
    ],
    actions: [
      [
        // Actions fade in
        [{ "opacity": 0 }, { "opacity": 0, offset: 0.5 }, { "opacity": 1 }],
        { duration: 300, easing: "linear", fill: "forwards" }
      ]
    ]
  };
  var DIALOG_DEFAULT_CLOSE_ANIMATION = {
    dialog: [
      [
        // Dialog slide up
        [{ "transform": "translateY(0)" }, { "transform": "translateY(-50px)" }],
        { duration: 150, easing: EASING.EMPHASIZED_ACCELERATE }
      ]
    ],
    scrim: [
      [
        // Scrim fade out
        [{ "opacity": 0.32 }, { "opacity": 0 }],
        { duration: 150, easing: "linear" }
      ]
    ],
    container: [
      [
        // Container shrink
        [{ "height": "100%" }, { "height": "35%" }],
        {
          duration: 150,
          easing: EASING.EMPHASIZED_ACCELERATE,
          pseudoElement: "::before"
        }
      ],
      [
        // Container fade out
        [{ "opacity": "1" }, { "opacity": "0" }],
        { delay: 100, duration: 50, easing: "linear", pseudoElement: "::before" }
      ]
    ],
    headline: [
      [
        // Headline fade out
        [{ "opacity": 1 }, { "opacity": 0 }],
        { duration: 100, easing: "linear", fill: "forwards" }
      ]
    ],
    content: [
      [
        // Content fade out
        [{ "opacity": 1 }, { "opacity": 0 }],
        { duration: 100, easing: "linear", fill: "forwards" }
      ]
    ],
    actions: [
      [
        // Actions fade out
        [{ "opacity": 1 }, { "opacity": 0 }],
        { duration: 100, easing: "linear", fill: "forwards" }
      ]
    ]
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/dialog/internal/dialog.js
  var dialogBaseClass = mixinDelegatesAria(i4);
  var Dialog = class extends dialogBaseClass {
    // We do not use `delegatesFocus: true` due to a Chromium bug with
    // selecting text.
    // See https://bugs.chromium.org/p/chromium/issues/detail?id=950357
    /**
     * Opens the dialog when set to `true` and closes it when set to `false`.
     */
    get open() {
      return this.isOpen;
    }
    set open(open) {
      if (open === this.isOpen) {
        return;
      }
      this.isOpen = open;
      if (open) {
        this.setAttribute("open", "");
        this.show();
      } else {
        this.removeAttribute("open");
        this.close();
      }
    }
    constructor() {
      super();
      this.quick = false;
      this.returnValue = "";
      this.noFocusTrap = false;
      this.getOpenAnimation = () => DIALOG_DEFAULT_OPEN_ANIMATION;
      this.getCloseAnimation = () => DIALOG_DEFAULT_CLOSE_ANIMATION;
      this.isOpen = false;
      this.isOpening = false;
      this.isConnectedPromise = this.getIsConnectedPromise();
      this.isAtScrollTop = false;
      this.isAtScrollBottom = false;
      this.nextClickIsFromContent = false;
      this.hasHeadline = false;
      this.hasActions = false;
      this.hasIcon = false;
      this.escapePressedWithoutCancel = false;
      this.treewalker = o7 ? null : document.createTreeWalker(this, NodeFilter.SHOW_ELEMENT);
      if (!o7) {
        this.addEventListener("submit", this.handleSubmit);
      }
    }
    /**
     * Opens the dialog and fires a cancelable `open` event. After a dialog's
     * animation, an `opened` event is fired.
     *
     * Add an `autofocus` attribute to a child of the dialog that should
     * receive focus after opening.
     *
     * @return A Promise that resolves after the animation is finished and the
     *     `opened` event was fired.
     */
    async show() {
      var _a3;
      this.isOpening = true;
      await this.isConnectedPromise;
      await this.updateComplete;
      const dialog = this.dialog;
      if (dialog.open || !this.isOpening) {
        this.isOpening = false;
        return;
      }
      const preventOpen = !this.dispatchEvent(new Event("open", { cancelable: true }));
      if (preventOpen) {
        this.open = false;
        this.isOpening = false;
        return;
      }
      dialog.showModal();
      this.open = true;
      if (this.scroller) {
        this.scroller.scrollTop = 0;
      }
      (_a3 = this.querySelector("[autofocus]")) == null ? void 0 : _a3.focus();
      await this.animateDialog(this.getOpenAnimation());
      this.dispatchEvent(new Event("opened"));
      this.isOpening = false;
    }
    /**
     * Closes the dialog and fires a cancelable `close` event. After a dialog's
     * animation, a `closed` event is fired.
     *
     * @param returnValue A return value usually indicating which button was used
     *     to close a dialog. If a dialog is canceled by clicking the scrim or
     *     pressing Escape, it will not change the return value after closing.
     * @return A Promise that resolves after the animation is finished and the
     *     `closed` event was fired.
     */
    async close(returnValue = this.returnValue) {
      this.isOpening = false;
      if (!this.isConnected) {
        this.open = false;
        return;
      }
      await this.updateComplete;
      const dialog = this.dialog;
      if (!dialog.open || this.isOpening) {
        this.open = false;
        return;
      }
      const prevReturnValue = this.returnValue;
      this.returnValue = returnValue;
      const preventClose = !this.dispatchEvent(new Event("close", { cancelable: true }));
      if (preventClose) {
        this.returnValue = prevReturnValue;
        return;
      }
      await this.animateDialog(this.getCloseAnimation());
      dialog.close(returnValue);
      this.open = false;
      this.dispatchEvent(new Event("closed"));
    }
    connectedCallback() {
      super.connectedCallback();
      this.isConnectedPromiseResolve();
    }
    disconnectedCallback() {
      super.disconnectedCallback();
      this.isConnectedPromise = this.getIsConnectedPromise();
    }
    render() {
      const scrollable = this.open && !(this.isAtScrollTop && this.isAtScrollBottom);
      const classes = {
        "has-headline": this.hasHeadline,
        "has-actions": this.hasActions,
        "has-icon": this.hasIcon,
        "scrollable": scrollable,
        "show-top-divider": scrollable && !this.isAtScrollTop,
        "show-bottom-divider": scrollable && !this.isAtScrollBottom
      };
      const showFocusTrap = this.open && !this.noFocusTrap;
      const focusTrap = b2`
      <div
        class="focus-trap"
        tabindex="0"
        aria-hidden="true"
        @focus=${this.handleFocusTrapFocus}></div>
    `;
      const { ariaLabel } = this;
      return b2`
      <div class="scrim"></div>
      <dialog
        class=${e8(classes)}
        aria-label=${ariaLabel || A}
        aria-labelledby=${this.hasHeadline ? "headline" : A}
        role=${this.type === "alert" ? "alertdialog" : A}
        @cancel=${this.handleCancel}
        @click=${this.handleDialogClick}
        @close=${this.handleClose}
        @keydown=${this.handleKeydown}
        .returnValue=${this.returnValue || A}>
        ${showFocusTrap ? focusTrap : A}
        <div class="container" @click=${this.handleContentClick}>
          <div class="headline">
            <div class="icon" aria-hidden="true">
              <slot name="icon" @slotchange=${this.handleIconChange}></slot>
            </div>
            <h2 id="headline" aria-hidden=${!this.hasHeadline || A}>
              <slot
                name="headline"
                @slotchange=${this.handleHeadlineChange}></slot>
            </h2>
            <md-divider></md-divider>
          </div>
          <div class="scroller">
            <div class="content">
              <div class="top anchor"></div>
              <slot name="content"></slot>
              <div class="bottom anchor"></div>
            </div>
          </div>
          <div class="actions">
            <md-divider></md-divider>
            <slot name="actions" @slotchange=${this.handleActionsChange}></slot>
          </div>
        </div>
        ${showFocusTrap ? focusTrap : A}
      </dialog>
    `;
    }
    firstUpdated() {
      this.intersectionObserver = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          this.handleAnchorIntersection(entry);
        }
      }, { root: this.scroller });
      this.intersectionObserver.observe(this.topAnchor);
      this.intersectionObserver.observe(this.bottomAnchor);
    }
    handleDialogClick() {
      if (this.nextClickIsFromContent) {
        this.nextClickIsFromContent = false;
        return;
      }
      const preventDefault = !this.dispatchEvent(new Event("cancel", { cancelable: true }));
      if (preventDefault) {
        return;
      }
      this.close();
    }
    handleContentClick() {
      this.nextClickIsFromContent = true;
    }
    handleSubmit(event) {
      const form = event.target;
      const { submitter } = event;
      if (form.getAttribute("method") !== "dialog" || !submitter) {
        return;
      }
      this.close(submitter.getAttribute("value") ?? this.returnValue);
    }
    handleCancel(event) {
      if (event.target !== this.dialog) {
        return;
      }
      this.escapePressedWithoutCancel = false;
      const preventDefault = !redispatchEvent(this, event);
      event.preventDefault();
      if (preventDefault) {
        return;
      }
      this.close();
    }
    handleClose() {
      var _a3;
      if (!this.escapePressedWithoutCancel) {
        return;
      }
      this.escapePressedWithoutCancel = false;
      (_a3 = this.dialog) == null ? void 0 : _a3.dispatchEvent(new Event("cancel", { cancelable: true }));
    }
    handleKeydown(event) {
      if (event.key !== "Escape") {
        return;
      }
      this.escapePressedWithoutCancel = true;
      setTimeout(() => {
        this.escapePressedWithoutCancel = false;
      });
    }
    async animateDialog(animation) {
      var _a3;
      (_a3 = this.cancelAnimations) == null ? void 0 : _a3.abort();
      this.cancelAnimations = new AbortController();
      if (this.quick) {
        return;
      }
      const { dialog, scrim, container, headline, content, actions } = this;
      if (!dialog || !scrim || !container || !headline || !content || !actions) {
        return;
      }
      const { container: containerAnimate, dialog: dialogAnimate, scrim: scrimAnimate, headline: headlineAnimate, content: contentAnimate, actions: actionsAnimate } = animation;
      const elementAndAnimation = [
        [dialog, dialogAnimate ?? []],
        [scrim, scrimAnimate ?? []],
        [container, containerAnimate ?? []],
        [headline, headlineAnimate ?? []],
        [content, contentAnimate ?? []],
        [actions, actionsAnimate ?? []]
      ];
      const animations = [];
      for (const [element, animation2] of elementAndAnimation) {
        for (const animateArgs of animation2) {
          const animation3 = element.animate(...animateArgs);
          this.cancelAnimations.signal.addEventListener("abort", () => {
            animation3.cancel();
          });
          animations.push(animation3);
        }
      }
      await Promise.all(animations.map((animation2) => animation2.finished.catch(() => {
      })));
    }
    handleHeadlineChange(event) {
      const slot = event.target;
      this.hasHeadline = slot.assignedElements().length > 0;
    }
    handleActionsChange(event) {
      const slot = event.target;
      this.hasActions = slot.assignedElements().length > 0;
    }
    handleIconChange(event) {
      const slot = event.target;
      this.hasIcon = slot.assignedElements().length > 0;
    }
    handleAnchorIntersection(entry) {
      const { target, isIntersecting } = entry;
      if (target === this.topAnchor) {
        this.isAtScrollTop = isIntersecting;
      }
      if (target === this.bottomAnchor) {
        this.isAtScrollBottom = isIntersecting;
      }
    }
    getIsConnectedPromise() {
      return new Promise((resolve) => {
        this.isConnectedPromiseResolve = resolve;
      });
    }
    handleFocusTrapFocus(event) {
      var _a3;
      const [firstFocusableChild, lastFocusableChild] = this.getFirstAndLastFocusableChildren();
      if (!firstFocusableChild || !lastFocusableChild) {
        (_a3 = this.dialog) == null ? void 0 : _a3.focus();
        return;
      }
      const isFirstFocusTrap = event.target === this.firstFocusTrap;
      const isLastFocusTrap = !isFirstFocusTrap;
      const focusCameFromFirstChild = event.relatedTarget === firstFocusableChild;
      const focusCameFromLastChild = event.relatedTarget === lastFocusableChild;
      const focusCameFromOutsideDialog = !focusCameFromFirstChild && !focusCameFromLastChild;
      const shouldFocusFirstChild = isLastFocusTrap && focusCameFromLastChild || isFirstFocusTrap && focusCameFromOutsideDialog;
      if (shouldFocusFirstChild) {
        firstFocusableChild.focus();
        return;
      }
      const shouldFocusLastChild = isFirstFocusTrap && focusCameFromFirstChild || isLastFocusTrap && focusCameFromOutsideDialog;
      if (shouldFocusLastChild) {
        lastFocusableChild.focus();
        return;
      }
    }
    getFirstAndLastFocusableChildren() {
      if (!this.treewalker) {
        return [null, null];
      }
      let firstFocusableChild = null;
      let lastFocusableChild = null;
      this.treewalker.currentNode = this.treewalker.root;
      while (this.treewalker.nextNode()) {
        const nextChild = this.treewalker.currentNode;
        if (!isFocusable(nextChild)) {
          continue;
        }
        if (!firstFocusableChild) {
          firstFocusableChild = nextChild;
        }
        lastFocusableChild = nextChild;
      }
      return [firstFocusableChild, lastFocusableChild];
    }
  };
  __decorate([
    n3({ type: Boolean })
  ], Dialog.prototype, "open", null);
  __decorate([
    n3({ type: Boolean })
  ], Dialog.prototype, "quick", void 0);
  __decorate([
    n3({ attribute: false })
  ], Dialog.prototype, "returnValue", void 0);
  __decorate([
    n3()
  ], Dialog.prototype, "type", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "no-focus-trap" })
  ], Dialog.prototype, "noFocusTrap", void 0);
  __decorate([
    e4("dialog")
  ], Dialog.prototype, "dialog", void 0);
  __decorate([
    e4(".scrim")
  ], Dialog.prototype, "scrim", void 0);
  __decorate([
    e4(".container")
  ], Dialog.prototype, "container", void 0);
  __decorate([
    e4(".headline")
  ], Dialog.prototype, "headline", void 0);
  __decorate([
    e4(".content")
  ], Dialog.prototype, "content", void 0);
  __decorate([
    e4(".actions")
  ], Dialog.prototype, "actions", void 0);
  __decorate([
    r4()
  ], Dialog.prototype, "isAtScrollTop", void 0);
  __decorate([
    r4()
  ], Dialog.prototype, "isAtScrollBottom", void 0);
  __decorate([
    e4(".scroller")
  ], Dialog.prototype, "scroller", void 0);
  __decorate([
    e4(".top.anchor")
  ], Dialog.prototype, "topAnchor", void 0);
  __decorate([
    e4(".bottom.anchor")
  ], Dialog.prototype, "bottomAnchor", void 0);
  __decorate([
    e4(".focus-trap")
  ], Dialog.prototype, "firstFocusTrap", void 0);
  __decorate([
    r4()
  ], Dialog.prototype, "hasHeadline", void 0);
  __decorate([
    r4()
  ], Dialog.prototype, "hasActions", void 0);
  __decorate([
    r4()
  ], Dialog.prototype, "hasIcon", void 0);
  function isFocusable(element) {
    var _a3;
    const knownFocusableElements = ":is(button,input,select,textarea,object,:is(a,area)[href],[tabindex],[contenteditable=true])";
    const notDisabled = ":not(:disabled,[disabled])";
    const notNegativeTabIndex = ':not([tabindex^="-"])';
    if (element.matches(knownFocusableElements + notDisabled + notNegativeTabIndex)) {
      return true;
    }
    const isCustomElement = element.localName.includes("-");
    if (!isCustomElement) {
      return false;
    }
    if (!element.matches(notDisabled)) {
      return false;
    }
    return ((_a3 = element.shadowRoot) == null ? void 0 : _a3.delegatesFocus) ?? false;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/dialog/internal/dialog-styles.js
  var styles14 = i`:host{border-start-start-radius:var(--md-dialog-container-shape-start-start, var(--md-dialog-container-shape, var(--md-sys-shape-corner-extra-large, 28px)));border-start-end-radius:var(--md-dialog-container-shape-start-end, var(--md-dialog-container-shape, var(--md-sys-shape-corner-extra-large, 28px)));border-end-end-radius:var(--md-dialog-container-shape-end-end, var(--md-dialog-container-shape, var(--md-sys-shape-corner-extra-large, 28px)));border-end-start-radius:var(--md-dialog-container-shape-end-start, var(--md-dialog-container-shape, var(--md-sys-shape-corner-extra-large, 28px)));display:contents;margin:auto;max-height:min(560px,100% - 48px);max-width:min(560px,100% - 48px);min-height:140px;min-width:280px;position:fixed;height:fit-content;width:fit-content}dialog{background:rgba(0,0,0,0);border:none;border-radius:inherit;flex-direction:column;height:inherit;margin:inherit;max-height:inherit;max-width:inherit;min-height:inherit;min-width:inherit;outline:none;overflow:visible;padding:0;width:inherit}dialog[open]{display:flex}::backdrop{background:none}.scrim{background:var(--md-sys-color-scrim, #000);display:none;inset:0;opacity:32%;pointer-events:none;position:fixed;z-index:1}:host([open]) .scrim{display:flex}h2{all:unset;align-self:stretch}.headline{align-items:center;color:var(--md-dialog-headline-color, var(--md-sys-color-on-surface, #1d1b20));display:flex;flex-direction:column;font-family:var(--md-dialog-headline-font, var(--md-sys-typescale-headline-small-font, var(--md-ref-typeface-brand, Roboto)));font-size:var(--md-dialog-headline-size, var(--md-sys-typescale-headline-small-size, 1.5rem));line-height:var(--md-dialog-headline-line-height, var(--md-sys-typescale-headline-small-line-height, 2rem));font-weight:var(--md-dialog-headline-weight, var(--md-sys-typescale-headline-small-weight, var(--md-ref-typeface-weight-regular, 400)));position:relative}slot[name=headline]::slotted(*){align-items:center;align-self:stretch;box-sizing:border-box;display:flex;gap:8px;padding:24px 24px 0}.icon{display:flex}slot[name=icon]::slotted(*){color:var(--md-dialog-icon-color, var(--md-sys-color-secondary, #625b71));fill:currentColor;font-size:var(--md-dialog-icon-size, 24px);margin-top:24px;height:var(--md-dialog-icon-size, 24px);width:var(--md-dialog-icon-size, 24px)}.has-icon slot[name=headline]::slotted(*){justify-content:center;padding-top:16px}.scrollable slot[name=headline]::slotted(*){padding-bottom:16px}.scrollable.has-headline slot[name=content]::slotted(*){padding-top:8px}.container{border-radius:inherit;display:flex;flex-direction:column;flex-grow:1;overflow:hidden;position:relative;transform-origin:top}.container::before{background:var(--md-dialog-container-color, var(--md-sys-color-surface-container-high, #ece6f0));border-radius:inherit;content:"";inset:0;position:absolute}.scroller{display:flex;flex:1;flex-direction:column;overflow:hidden;z-index:1}.scrollable .scroller{overflow-y:scroll}.content{color:var(--md-dialog-supporting-text-color, var(--md-sys-color-on-surface-variant, #49454f));font-family:var(--md-dialog-supporting-text-font, var(--md-sys-typescale-body-medium-font, var(--md-ref-typeface-plain, Roboto)));font-size:var(--md-dialog-supporting-text-size, var(--md-sys-typescale-body-medium-size, 0.875rem));line-height:var(--md-dialog-supporting-text-line-height, var(--md-sys-typescale-body-medium-line-height, 1.25rem));flex:1;font-weight:var(--md-dialog-supporting-text-weight, var(--md-sys-typescale-body-medium-weight, var(--md-ref-typeface-weight-regular, 400)));height:min-content;position:relative}slot[name=content]::slotted(*){box-sizing:border-box;padding:24px}.anchor{position:absolute}.top.anchor{top:0}.bottom.anchor{bottom:0}.actions{position:relative}slot[name=actions]::slotted(*){box-sizing:border-box;display:flex;gap:8px;justify-content:flex-end;padding:16px 24px 24px}.has-actions slot[name=content]::slotted(*){padding-bottom:8px}md-divider{display:none;position:absolute}.has-headline.show-top-divider .headline md-divider,.has-actions.show-bottom-divider .actions md-divider{display:flex}.headline md-divider{bottom:0}.actions md-divider{top:0}@media(forced-colors: active){dialog{outline:2px solid WindowText}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/dialog/dialog.js
  var MdDialog = class MdDialog2 extends Dialog {
  };
  MdDialog.styles = [styles14];
  if (!customElements.get("md-dialog")) {
    MdDialog = __decorate([
      t("md-dialog")
    ], MdDialog);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/slider/internal/forced-colors-styles.js
  var styles15 = i`@media(forced-colors: active){:host{--md-slider-active-track-color: CanvasText;--md-slider-disabled-active-track-color: GrayText;--md-slider-disabled-active-track-opacity: 1;--md-slider-disabled-handle-color: GrayText;--md-slider-disabled-inactive-track-color: GrayText;--md-slider-disabled-inactive-track-opacity: 1;--md-slider-focus-handle-color: CanvasText;--md-slider-handle-color: CanvasText;--md-slider-handle-shadow-color: Canvas;--md-slider-hover-handle-color: CanvasText;--md-slider-hover-state-layer-color: Canvas;--md-slider-hover-state-layer-opacity: 1;--md-slider-inactive-track-color: Canvas;--md-slider-label-container-color: Canvas;--md-slider-label-text-color: CanvasText;--md-slider-pressed-handle-color: CanvasText;--md-slider-pressed-state-layer-color: Canvas;--md-slider-pressed-state-layer-opacity: 1;--md-slider-with-overlap-handle-outline-color: CanvasText}.label,.label::before{border:var(--_with-overlap-handle-outline-color) solid var(--_with-overlap-handle-outline-width)}:host(:not([disabled])) .track::before{border:1px solid var(--_active-track-color)}.tickmarks::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='CanvasText'%3E%3Ccircle cx='2' cy='2'  r='1'/%3E%3C/svg%3E")}.tickmarks::after{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='Canvas'%3E%3Ccircle cx='2' cy='2' r='1'/%3E%3C/svg%3E")}:host([disabled]) .tickmarks::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='Canvas'%3E%3Ccircle cx='2' cy='2'  r='1'/%3E%3C/svg%3E")}}
`;

  // custom_components/smart_agent/frontend/node_modules/lit-html/directives/when.js
  function n8(n9, r9, t6) {
    return n9 ? r9(n9) : t6 == null ? void 0 : t6(n9);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/events/form-label-activation.js
  function dispatchActivationClick(element) {
    const event = new MouseEvent("click", { bubbles: true });
    element.dispatchEvent(event);
    return event;
  }
  function isActivationClick(event) {
    if (event.currentTarget !== event.target) {
      return false;
    }
    if (event.composedPath()[0] !== event.target) {
      return false;
    }
    if (event.target.disabled) {
      return false;
    }
    return !squelchEvent(event);
  }
  function squelchEvent(event) {
    const squelched = isSquelchingEvents;
    if (squelched) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
    squelchEventsForMicrotask();
    return squelched;
  }
  var isSquelchingEvents = false;
  async function squelchEventsForMicrotask() {
    isSquelchingEvents = true;
    await null;
    isSquelchingEvents = false;
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/slider/internal/slider.js
  var sliderBaseClass = mixinDelegatesAria(mixinFormAssociated(mixinElementInternals(i4)));
  var Slider = class extends sliderBaseClass {
    /**
     * The HTML name to use in form submission for a range slider's starting
     * value. Use `name` instead if both the start and end values should use the
     * same name.
     */
    get nameStart() {
      return this.getAttribute("name-start") ?? this.name;
    }
    set nameStart(name) {
      this.setAttribute("name-start", name);
    }
    /**
     * The HTML name to use in form submission for a range slider's ending value.
     * Use `name` instead if both the start and end values should use the same
     * name.
     */
    get nameEnd() {
      return this.getAttribute("name-end") ?? this.nameStart;
    }
    set nameEnd(name) {
      this.setAttribute("name-end", name);
    }
    // Note: start aria-* properties are only applied when range=true, which is
    // why they do not need to handle both cases.
    get renderAriaLabelStart() {
      const { ariaLabel } = this;
      return this.ariaLabelStart || ariaLabel && `${ariaLabel} start` || this.valueLabelStart || String(this.valueStart);
    }
    get renderAriaValueTextStart() {
      return this.ariaValueTextStart || this.valueLabelStart || String(this.valueStart);
    }
    // Note: end aria-* properties are applied for single and range sliders, which
    // is why it needs to handle `this.range` (while start aria-* properties do
    // not).
    get renderAriaLabelEnd() {
      const { ariaLabel } = this;
      if (this.range) {
        return this.ariaLabelEnd || ariaLabel && `${ariaLabel} end` || this.valueLabelEnd || String(this.valueEnd);
      }
      return ariaLabel || this.valueLabel || String(this.value);
    }
    get renderAriaValueTextEnd() {
      if (this.range) {
        return this.ariaValueTextEnd || this.valueLabelEnd || String(this.valueEnd);
      }
      const { ariaValueText } = this;
      return ariaValueText || this.valueLabel || String(this.value);
    }
    constructor() {
      super();
      this.min = 0;
      this.max = 100;
      this.valueLabel = "";
      this.valueLabelStart = "";
      this.valueLabelEnd = "";
      this.ariaLabelStart = "";
      this.ariaValueTextStart = "";
      this.ariaLabelEnd = "";
      this.ariaValueTextEnd = "";
      this.step = 1;
      this.ticks = false;
      this.labeled = false;
      this.range = false;
      this.handleStartHover = false;
      this.handleEndHover = false;
      this.startOnTop = false;
      this.handlesOverlapping = false;
      this.ripplePointerId = 1;
      this.isRedispatchingEvent = false;
      if (!o7) {
        this.addEventListener("click", (event) => {
          if (!isActivationClick(event) || !this.inputEnd) {
            return;
          }
          this.focus();
          dispatchActivationClick(this.inputEnd);
        });
      }
    }
    focus() {
      var _a3;
      (_a3 = this.inputEnd) == null ? void 0 : _a3.focus();
    }
    willUpdate(changed) {
      var _a3, _b;
      this.renderValueStart = changed.has("valueStart") ? this.valueStart : (_a3 = this.inputStart) == null ? void 0 : _a3.valueAsNumber;
      const endValueChanged = changed.has("valueEnd") && this.range || changed.has("value");
      this.renderValueEnd = endValueChanged ? this.range ? this.valueEnd : this.value : (_b = this.inputEnd) == null ? void 0 : _b.valueAsNumber;
      if (changed.get("handleStartHover") !== void 0) {
        this.toggleRippleHover(this.rippleStart, this.handleStartHover);
      } else if (changed.get("handleEndHover") !== void 0) {
        this.toggleRippleHover(this.rippleEnd, this.handleEndHover);
      }
    }
    updated(changed) {
      var _a3, _b;
      if (this.range) {
        this.renderValueStart = this.inputStart.valueAsNumber;
      }
      this.renderValueEnd = this.inputEnd.valueAsNumber;
      if (this.range) {
        const segment = (this.max - this.min) / 3;
        if (this.valueStart === void 0) {
          this.inputStart.valueAsNumber = this.min + segment;
          const v2 = this.inputStart.valueAsNumber;
          this.valueStart = this.renderValueStart = v2;
        }
        if (this.valueEnd === void 0) {
          this.inputEnd.valueAsNumber = this.min + 2 * segment;
          const v2 = this.inputEnd.valueAsNumber;
          this.valueEnd = this.renderValueEnd = v2;
        }
      } else {
        this.value ?? (this.value = this.renderValueEnd);
      }
      if (changed.has("range") || changed.has("renderValueStart") || changed.has("renderValueEnd") || this.isUpdatePending) {
        const startNub = (_a3 = this.handleStart) == null ? void 0 : _a3.querySelector(".handleNub");
        const endNub = (_b = this.handleEnd) == null ? void 0 : _b.querySelector(".handleNub");
        this.handlesOverlapping = isOverlapping(startNub, endNub);
      }
      this.performUpdate();
    }
    render() {
      const step = this.step === 0 ? 1 : this.step;
      const range = Math.max(this.max - this.min, step);
      const startFraction = this.range ? ((this.renderValueStart ?? this.min) - this.min) / range : 0;
      const endFraction = ((this.renderValueEnd ?? this.min) - this.min) / range;
      const containerStyles = {
        // for clipping inputs and active track.
        "--_start-fraction": String(startFraction),
        "--_end-fraction": String(endFraction),
        // for generating tick marks
        "--_tick-count": String(range / step)
      };
      const containerClasses = { ranged: this.range };
      const labelStart = this.valueLabelStart || String(this.renderValueStart);
      const labelEnd = (this.range ? this.valueLabelEnd : this.valueLabel) || String(this.renderValueEnd);
      const inputStartProps = {
        start: true,
        value: this.renderValueStart,
        ariaLabel: this.renderAriaLabelStart,
        ariaValueText: this.renderAriaValueTextStart,
        ariaMin: this.min,
        ariaMax: this.valueEnd ?? this.max
      };
      const inputEndProps = {
        start: false,
        value: this.renderValueEnd,
        ariaLabel: this.renderAriaLabelEnd,
        ariaValueText: this.renderAriaValueTextEnd,
        ariaMin: this.range ? this.valueStart ?? this.min : this.min,
        ariaMax: this.max
      };
      const handleStartProps = {
        start: true,
        hover: this.handleStartHover,
        label: labelStart
      };
      const handleEndProps = {
        start: false,
        hover: this.handleEndHover,
        label: labelEnd
      };
      const handleContainerClasses = {
        hover: this.handleStartHover || this.handleEndHover
      };
      return b2` <div
      class="container ${e8(containerClasses)}"
      style=${o9(containerStyles)}>
      ${n8(this.range, () => this.renderInput(inputStartProps))}
      ${this.renderInput(inputEndProps)} ${this.renderTrack()}
      <div class="handleContainerPadded">
        <div class="handleContainerBlock">
          <div class="handleContainer ${e8(handleContainerClasses)}">
            ${n8(this.range, () => this.renderHandle(handleStartProps))}
            ${this.renderHandle(handleEndProps)}
          </div>
        </div>
      </div>
    </div>`;
    }
    renderTrack() {
      return b2`
      <div class="track"></div>
      ${this.ticks ? b2`<div class="tickmarks"></div>` : A}
    `;
    }
    renderLabel(value) {
      return b2`<div class="label" aria-hidden="true">
      <span class="labelContent" part="label">${value}</span>
    </div>`;
    }
    renderHandle({ start, hover, label }) {
      const onTop = !this.disabled && start === this.startOnTop;
      const isOverlapping2 = !this.disabled && this.handlesOverlapping;
      const name = start ? "start" : "end";
      return b2`<div
      class="handle ${e8({
        [name]: true,
        hover,
        onTop,
        isOverlapping: isOverlapping2
      })}">
      <md-focus-ring part="focus-ring" for=${name}></md-focus-ring>
      <md-ripple
        for=${name}
        class=${name}
        ?disabled=${this.disabled}></md-ripple>
      <div class="handleNub">
        <md-elevation part="elevation"></md-elevation>
      </div>
      ${n8(this.labeled, () => this.renderLabel(label))}
    </div>`;
    }
    renderInput({ start, value, ariaLabel, ariaValueText, ariaMin, ariaMax }) {
      const name = start ? `start` : `end`;
      return b2`<input
      type="range"
      class="${e8({
        start,
        end: !start
      })}"
      @focus=${this.handleFocus}
      @pointerdown=${this.handleDown}
      @pointerup=${this.handleUp}
      @pointerenter=${this.handleEnter}
      @pointermove=${this.handleMove}
      @pointerleave=${this.handleLeave}
      @keydown=${this.handleKeydown}
      @keyup=${this.handleKeyup}
      @input=${this.handleInput}
      @change=${this.handleChange}
      id=${name}
      .disabled=${this.disabled}
      .min=${String(this.min)}
      aria-valuemin=${ariaMin}
      .max=${String(this.max)}
      aria-valuemax=${ariaMax}
      .step=${String(this.step)}
      .value=${String(value)}
      .tabIndex=${start ? 1 : 0}
      aria-label=${ariaLabel || A}
      aria-valuetext=${ariaValueText} />`;
    }
    async toggleRippleHover(ripple, hovering) {
      const rippleEl = await ripple;
      if (!rippleEl) {
        return;
      }
      if (hovering) {
        rippleEl.handlePointerenter(new PointerEvent("pointerenter", {
          isPrimary: true,
          pointerId: this.ripplePointerId
        }));
      } else {
        rippleEl.handlePointerleave(new PointerEvent("pointerleave", {
          isPrimary: true,
          pointerId: this.ripplePointerId
        }));
      }
    }
    handleFocus(event) {
      this.updateOnTop(event.target);
    }
    startAction(event) {
      const target = event.target;
      const fixed = target === this.inputStart ? this.inputEnd : this.inputStart;
      this.action = {
        canFlip: event.type === "pointerdown",
        flipped: false,
        target,
        fixed,
        values: /* @__PURE__ */ new Map([
          [target, target.valueAsNumber],
          [fixed, fixed == null ? void 0 : fixed.valueAsNumber]
        ])
      };
    }
    finishAction(event) {
      this.action = void 0;
    }
    handleKeydown(event) {
      this.startAction(event);
    }
    handleKeyup(event) {
      this.finishAction(event);
    }
    handleDown(event) {
      this.startAction(event);
      this.ripplePointerId = event.pointerId;
      const isStart = event.target === this.inputStart;
      this.handleStartHover = !this.disabled && isStart && Boolean(this.handleStart);
      this.handleEndHover = !this.disabled && !isStart && Boolean(this.handleEnd);
    }
    async handleUp(event) {
      if (!this.action) {
        return;
      }
      const { target, values, flipped } = this.action;
      await new Promise(requestAnimationFrame);
      if (target !== void 0) {
        target.focus();
        if (flipped && target.valueAsNumber !== values.get(target)) {
          target.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      this.finishAction(event);
    }
    /**
     * The move handler tracks handle hovering to facilitate proper ripple
     * behavior on the slider handle. This is needed because user interaction with
     * the native input is leveraged to position the handle. Because the separate
     * displayed handle element has pointer events disabled (to allow interaction
     * with the input) and the input's handle is a pseudo-element, neither can be
     * the ripple's interactive element. Therefore the input is the ripple's
     * interactive element and has a `ripple` directive; however the ripple
     * is gated on the handle being hovered. In addition, because the ripple
     * hover state is being specially handled, it must be triggered independent
     * of the directive. This is done based on the hover state when the
     * slider is updated.
     */
    handleMove(event) {
      this.handleStartHover = !this.disabled && inBounds(event, this.handleStart);
      this.handleEndHover = !this.disabled && inBounds(event, this.handleEnd);
    }
    handleEnter(event) {
      this.handleMove(event);
    }
    handleLeave() {
      this.handleStartHover = false;
      this.handleEndHover = false;
    }
    updateOnTop(input) {
      this.startOnTop = input.classList.contains("start");
    }
    needsClamping() {
      if (!this.action) {
        return false;
      }
      const { target, fixed } = this.action;
      const isStart = target === this.inputStart;
      return isStart ? target.valueAsNumber > fixed.valueAsNumber : target.valueAsNumber < fixed.valueAsNumber;
    }
    // if start/end start coincident and the first drag input would e.g. move
    // start > end, avoid clamping and "flip" to use the other input
    // as the action target.
    isActionFlipped() {
      const { action } = this;
      if (!action) {
        return false;
      }
      const { target, fixed, values } = action;
      if (action.canFlip) {
        const coincident = values.get(target) === values.get(fixed);
        if (coincident && this.needsClamping()) {
          action.canFlip = false;
          action.flipped = true;
          action.target = fixed;
          action.fixed = target;
        }
      }
      return action.flipped;
    }
    // when flipped, apply the drag input to the flipped target and reset
    // the actual target.
    flipAction() {
      if (!this.action) {
        return false;
      }
      const { target, fixed, values } = this.action;
      const changed = target.valueAsNumber !== fixed.valueAsNumber;
      target.valueAsNumber = fixed.valueAsNumber;
      fixed.valueAsNumber = values.get(fixed);
      return changed;
    }
    // clamp such that start does not move beyond end and visa versa.
    clampAction() {
      if (!this.needsClamping() || !this.action) {
        return false;
      }
      const { target, fixed } = this.action;
      target.valueAsNumber = fixed.valueAsNumber;
      return true;
    }
    handleInput(event) {
      if (this.isRedispatchingEvent) {
        return;
      }
      let stopPropagation = false;
      let redispatch = false;
      if (this.range) {
        if (this.isActionFlipped()) {
          stopPropagation = true;
          redispatch = this.flipAction();
        }
        if (this.clampAction()) {
          stopPropagation = true;
          redispatch = false;
        }
      }
      const target = event.target;
      this.updateOnTop(target);
      if (this.range) {
        this.valueStart = this.inputStart.valueAsNumber;
        this.valueEnd = this.inputEnd.valueAsNumber;
      } else {
        this.value = this.inputEnd.valueAsNumber;
      }
      if (stopPropagation) {
        event.stopPropagation();
      }
      if (redispatch) {
        this.isRedispatchingEvent = true;
        redispatchEvent(target, event);
        this.isRedispatchingEvent = false;
      }
    }
    handleChange(event) {
      const changeTarget = event.target;
      const { target, values } = this.action ?? {};
      const squelch = target && target.valueAsNumber === values.get(changeTarget);
      if (!squelch) {
        redispatchEvent(this, event);
      }
      this.finishAction(event);
    }
    [getFormValue]() {
      if (this.range) {
        const data = new FormData();
        data.append(this.nameStart, String(this.valueStart));
        data.append(this.nameEnd, String(this.valueEnd));
        return data;
      }
      return String(this.value);
    }
    formResetCallback() {
      if (this.range) {
        const valueStart = this.getAttribute("value-start");
        this.valueStart = valueStart !== null ? Number(valueStart) : void 0;
        const valueEnd = this.getAttribute("value-end");
        this.valueEnd = valueEnd !== null ? Number(valueEnd) : void 0;
        return;
      }
      const value = this.getAttribute("value");
      this.value = value !== null ? Number(value) : void 0;
    }
    formStateRestoreCallback(state) {
      if (Array.isArray(state)) {
        const [[, valueStart], [, valueEnd]] = state;
        this.valueStart = Number(valueStart);
        this.valueEnd = Number(valueEnd);
        this.range = true;
        return;
      }
      this.value = Number(state);
      this.range = false;
    }
  };
  Slider.shadowRootOptions = {
    ...i4.shadowRootOptions,
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Number })
  ], Slider.prototype, "min", void 0);
  __decorate([
    n3({ type: Number })
  ], Slider.prototype, "max", void 0);
  __decorate([
    n3({ type: Number })
  ], Slider.prototype, "value", void 0);
  __decorate([
    n3({ type: Number, attribute: "value-start" })
  ], Slider.prototype, "valueStart", void 0);
  __decorate([
    n3({ type: Number, attribute: "value-end" })
  ], Slider.prototype, "valueEnd", void 0);
  __decorate([
    n3({ attribute: "value-label" })
  ], Slider.prototype, "valueLabel", void 0);
  __decorate([
    n3({ attribute: "value-label-start" })
  ], Slider.prototype, "valueLabelStart", void 0);
  __decorate([
    n3({ attribute: "value-label-end" })
  ], Slider.prototype, "valueLabelEnd", void 0);
  __decorate([
    n3({ attribute: "aria-label-start" })
  ], Slider.prototype, "ariaLabelStart", void 0);
  __decorate([
    n3({ attribute: "aria-valuetext-start" })
  ], Slider.prototype, "ariaValueTextStart", void 0);
  __decorate([
    n3({ attribute: "aria-label-end" })
  ], Slider.prototype, "ariaLabelEnd", void 0);
  __decorate([
    n3({ attribute: "aria-valuetext-end" })
  ], Slider.prototype, "ariaValueTextEnd", void 0);
  __decorate([
    n3({ type: Number })
  ], Slider.prototype, "step", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Slider.prototype, "ticks", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Slider.prototype, "labeled", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Slider.prototype, "range", void 0);
  __decorate([
    e4("input.start")
  ], Slider.prototype, "inputStart", void 0);
  __decorate([
    e4(".handle.start")
  ], Slider.prototype, "handleStart", void 0);
  __decorate([
    r6("md-ripple.start")
  ], Slider.prototype, "rippleStart", void 0);
  __decorate([
    e4("input.end")
  ], Slider.prototype, "inputEnd", void 0);
  __decorate([
    e4(".handle.end")
  ], Slider.prototype, "handleEnd", void 0);
  __decorate([
    r6("md-ripple.end")
  ], Slider.prototype, "rippleEnd", void 0);
  __decorate([
    r4()
  ], Slider.prototype, "handleStartHover", void 0);
  __decorate([
    r4()
  ], Slider.prototype, "handleEndHover", void 0);
  __decorate([
    r4()
  ], Slider.prototype, "startOnTop", void 0);
  __decorate([
    r4()
  ], Slider.prototype, "handlesOverlapping", void 0);
  __decorate([
    r4()
  ], Slider.prototype, "renderValueStart", void 0);
  __decorate([
    r4()
  ], Slider.prototype, "renderValueEnd", void 0);
  function inBounds({ x: x2, y: y3 }, element) {
    if (!element) {
      return false;
    }
    const { top, left, bottom, right } = element.getBoundingClientRect();
    return x2 >= left && x2 <= right && y3 >= top && y3 <= bottom;
  }
  function isOverlapping(elA, elB) {
    if (!(elA && elB)) {
      return false;
    }
    const a4 = elA.getBoundingClientRect();
    const b3 = elB.getBoundingClientRect();
    return !(a4.top > b3.bottom || a4.right < b3.left || a4.bottom < b3.top || a4.left > b3.right);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/slider/internal/slider-styles.js
  var styles16 = i`:host{--_active-track-color: var(--md-slider-active-track-color, var(--md-sys-color-primary, #6750a4));--_active-track-height: var(--md-slider-active-track-height, 4px);--_active-track-shape: var(--md-slider-active-track-shape, var(--md-sys-shape-corner-full, 9999px));--_disabled-active-track-color: var(--md-slider-disabled-active-track-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-active-track-opacity: var(--md-slider-disabled-active-track-opacity, 0.38);--_disabled-handle-color: var(--md-slider-disabled-handle-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-handle-elevation: var(--md-slider-disabled-handle-elevation, 0);--_disabled-inactive-track-color: var(--md-slider-disabled-inactive-track-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-inactive-track-opacity: var(--md-slider-disabled-inactive-track-opacity, 0.12);--_focus-handle-color: var(--md-slider-focus-handle-color, var(--md-sys-color-primary, #6750a4));--_handle-color: var(--md-slider-handle-color, var(--md-sys-color-primary, #6750a4));--_handle-elevation: var(--md-slider-handle-elevation, 1);--_handle-height: var(--md-slider-handle-height, 20px);--_handle-shadow-color: var(--md-slider-handle-shadow-color, var(--md-sys-color-shadow, #000));--_handle-shape: var(--md-slider-handle-shape, var(--md-sys-shape-corner-full, 9999px));--_handle-width: var(--md-slider-handle-width, 20px);--_hover-handle-color: var(--md-slider-hover-handle-color, var(--md-sys-color-primary, #6750a4));--_hover-state-layer-color: var(--md-slider-hover-state-layer-color, var(--md-sys-color-primary, #6750a4));--_hover-state-layer-opacity: var(--md-slider-hover-state-layer-opacity, 0.08);--_inactive-track-color: var(--md-slider-inactive-track-color, var(--md-sys-color-surface-container-highest, #e6e0e9));--_inactive-track-height: var(--md-slider-inactive-track-height, 4px);--_inactive-track-shape: var(--md-slider-inactive-track-shape, var(--md-sys-shape-corner-full, 9999px));--_label-container-color: var(--md-slider-label-container-color, var(--md-sys-color-primary, #6750a4));--_label-container-height: var(--md-slider-label-container-height, 28px);--_pressed-handle-color: var(--md-slider-pressed-handle-color, var(--md-sys-color-primary, #6750a4));--_pressed-state-layer-color: var(--md-slider-pressed-state-layer-color, var(--md-sys-color-primary, #6750a4));--_pressed-state-layer-opacity: var(--md-slider-pressed-state-layer-opacity, 0.12);--_state-layer-size: var(--md-slider-state-layer-size, 40px);--_with-overlap-handle-outline-color: var(--md-slider-with-overlap-handle-outline-color, var(--md-sys-color-on-primary, #fff));--_with-overlap-handle-outline-width: var(--md-slider-with-overlap-handle-outline-width, 1px);--_with-tick-marks-active-container-color: var(--md-slider-with-tick-marks-active-container-color, var(--md-sys-color-on-primary, #fff));--_with-tick-marks-container-size: var(--md-slider-with-tick-marks-container-size, 2px);--_with-tick-marks-disabled-container-color: var(--md-slider-with-tick-marks-disabled-container-color, var(--md-sys-color-on-surface, #1d1b20));--_with-tick-marks-inactive-container-color: var(--md-slider-with-tick-marks-inactive-container-color, var(--md-sys-color-on-surface-variant, #49454f));--_label-text-color: var(--md-slider-label-text-color, var(--md-sys-color-on-primary, #fff));--_label-text-font: var(--md-slider-label-text-font, var(--md-sys-typescale-label-medium-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-slider-label-text-line-height, var(--md-sys-typescale-label-medium-line-height, 1rem));--_label-text-size: var(--md-slider-label-text-size, var(--md-sys-typescale-label-medium-size, 0.75rem));--_label-text-weight: var(--md-slider-label-text-weight, var(--md-sys-typescale-label-medium-weight, var(--md-ref-typeface-weight-medium, 500)));--_start-fraction: 0;--_end-fraction: 0;--_tick-count: 0;display:inline-flex;vertical-align:middle;min-inline-size:200px;--md-elevation-level: var(--_handle-elevation);--md-elevation-shadow-color: var(--_handle-shadow-color)}md-focus-ring{height:48px;inset:unset;width:48px}md-elevation{transition-duration:250ms}@media(prefers-reduced-motion){.label{transition-duration:0}}:host([disabled]){opacity:var(--_disabled-active-track-opacity);--md-elevation-level: var(--_disabled-handle-elevation)}.container{flex:1;display:flex;align-items:center;position:relative;block-size:var(--_state-layer-size);pointer-events:none;touch-action:none}.track,.tickmarks{position:absolute;inset:0;display:flex;align-items:center}.track::before,.tickmarks::before,.track::after,.tickmarks::after{position:absolute;content:"";inset-inline-start:calc(var(--_state-layer-size)/2 - var(--_with-tick-marks-container-size));inset-inline-end:calc(var(--_state-layer-size)/2 - var(--_with-tick-marks-container-size));background-size:calc((100% - var(--_with-tick-marks-container-size)*2)/var(--_tick-count)) 100%}.track::before,.tickmarks::before{block-size:var(--_inactive-track-height);border-radius:var(--_inactive-track-shape)}.track::before{background:var(--_inactive-track-color)}.tickmarks::before{background-image:radial-gradient(circle at var(--_with-tick-marks-container-size) center, var(--_with-tick-marks-inactive-container-color) 0, var(--_with-tick-marks-inactive-container-color) calc(var(--_with-tick-marks-container-size) / 2), transparent calc(var(--_with-tick-marks-container-size) / 2))}:host([disabled]) .track::before{opacity:calc(1/var(--_disabled-active-track-opacity)*var(--_disabled-inactive-track-opacity));background:var(--_disabled-inactive-track-color)}.track::after,.tickmarks::after{block-size:var(--_active-track-height);border-radius:var(--_active-track-shape);clip-path:inset(0 calc(var(--_with-tick-marks-container-size) * min((1 - var(--_end-fraction)) * 1000000000, 1) + (100% - var(--_with-tick-marks-container-size) * 2) * (1 - var(--_end-fraction))) 0 calc(var(--_with-tick-marks-container-size) * min(var(--_start-fraction) * 1000000000, 1) + (100% - var(--_with-tick-marks-container-size) * 2) * var(--_start-fraction)))}.track::after{background:var(--_active-track-color)}.tickmarks::after{background-image:radial-gradient(circle at var(--_with-tick-marks-container-size) center, var(--_with-tick-marks-active-container-color) 0, var(--_with-tick-marks-active-container-color) calc(var(--_with-tick-marks-container-size) / 2), transparent calc(var(--_with-tick-marks-container-size) / 2))}.track:dir(rtl)::after{clip-path:inset(0 calc(var(--_with-tick-marks-container-size) * min(var(--_start-fraction) * 1000000000, 1) + (100% - var(--_with-tick-marks-container-size) * 2) * var(--_start-fraction)) 0 calc(var(--_with-tick-marks-container-size) * min((1 - var(--_end-fraction)) * 1000000000, 1) + (100% - var(--_with-tick-marks-container-size) * 2) * (1 - var(--_end-fraction))))}.tickmarks:dir(rtl)::after{clip-path:inset(0 calc(var(--_with-tick-marks-container-size) * min(var(--_start-fraction) * 1000000000, 1) + (100% - var(--_with-tick-marks-container-size) * 2) * var(--_start-fraction)) 0 calc(var(--_with-tick-marks-container-size) * min((1 - var(--_end-fraction)) * 1000000000, 1) + (100% - var(--_with-tick-marks-container-size) * 2) * (1 - var(--_end-fraction))))}:host([disabled]) .track::after{background:var(--_disabled-active-track-color)}:host([disabled]) .tickmarks::before{background-image:radial-gradient(circle at var(--_with-tick-marks-container-size) center, var(--_with-tick-marks-disabled-container-color) 0, var(--_with-tick-marks-disabled-container-color) calc(var(--_with-tick-marks-container-size) / 2), transparent calc(var(--_with-tick-marks-container-size) / 2))}.handleContainerPadded{position:relative;block-size:100%;inline-size:100%;padding-inline:calc(var(--_state-layer-size)/2)}.handleContainerBlock{position:relative;block-size:100%;inline-size:100%}.handleContainer{position:absolute;inset-block-start:0;inset-block-end:0;inset-inline-start:calc(100%*var(--_start-fraction));inline-size:calc(100%*(var(--_end-fraction) - var(--_start-fraction)))}.handle{position:absolute;block-size:var(--_state-layer-size);inline-size:var(--_state-layer-size);border-radius:var(--_handle-shape);display:flex;place-content:center;place-items:center}.handleNub{position:absolute;height:var(--_handle-height);width:var(--_handle-width);border-radius:var(--_handle-shape);background:var(--_handle-color)}:host([disabled]) .handleNub{background:var(--_disabled-handle-color)}input.end:focus~.handleContainerPadded .handle.end>.handleNub,input.start:focus~.handleContainerPadded .handle.start>.handleNub{background:var(--_focus-handle-color)}.container>.handleContainerPadded .handle.hover>.handleNub{background:var(--_hover-handle-color)}:host(:not([disabled])) input.end:active~.handleContainerPadded .handle.end>.handleNub,:host(:not([disabled])) input.start:active~.handleContainerPadded .handle.start>.handleNub{background:var(--_pressed-handle-color)}.onTop.isOverlapping .label,.onTop.isOverlapping .label::before{outline:var(--_with-overlap-handle-outline-color) solid var(--_with-overlap-handle-outline-width)}.onTop.isOverlapping .handleNub{border:var(--_with-overlap-handle-outline-color) solid var(--_with-overlap-handle-outline-width)}.handle.start{inset-inline-start:calc(0px - var(--_state-layer-size)/2)}.handle.end{inset-inline-end:calc(0px - var(--_state-layer-size)/2)}.label{position:absolute;box-sizing:border-box;display:flex;padding:4px;place-content:center;place-items:center;border-radius:var(--md-sys-shape-corner-full, 9999px);color:var(--_label-text-color);font-family:var(--_label-text-font);font-size:var(--_label-text-size);line-height:var(--_label-text-line-height);font-weight:var(--_label-text-weight);inset-block-end:100%;min-inline-size:var(--_label-container-height);min-block-size:var(--_label-container-height);background:var(--_label-container-color);transition:transform 100ms cubic-bezier(0.2, 0, 0, 1);transform-origin:center bottom;transform:scale(0)}:host(:focus-within) .label,.handleContainer.hover .label,:where(:has(input:active)) .label{transform:scale(1)}.label::before,.label::after{position:absolute;display:block;content:"";background:inherit}.label::before{inline-size:calc(var(--_label-container-height)/2);block-size:calc(var(--_label-container-height)/2);bottom:calc(var(--_label-container-height)/-10);transform:rotate(45deg)}.label::after{inset:0px;border-radius:inherit}.labelContent{z-index:1}input[type=range]{opacity:0;-webkit-tap-highlight-color:rgba(0,0,0,0);position:absolute;box-sizing:border-box;height:100%;width:100%;margin:0;background:rgba(0,0,0,0);cursor:pointer;pointer-events:auto;appearance:none}input[type=range]:focus{outline:none}::-webkit-slider-runnable-track{-webkit-appearance:none}::-moz-range-track{appearance:none}::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;block-size:var(--_handle-height);inline-size:var(--_handle-width);opacity:0;z-index:2}input.end::-webkit-slider-thumb{--_track-and-knob-padding: calc( (var(--_state-layer-size) - var(--_handle-width)) / 2 );--_x-translate: calc( var(--_track-and-knob-padding) - 2 * var(--_end-fraction) * var(--_track-and-knob-padding) );transform:translateX(var(--_x-translate))}input.end:dir(rtl)::-webkit-slider-thumb{transform:translateX(calc(-1 * var(--_x-translate)))}input.start::-webkit-slider-thumb{--_track-and-knob-padding: calc( (var(--_state-layer-size) - var(--_handle-width)) / 2 );--_x-translate: calc( var(--_track-and-knob-padding) - 2 * var(--_start-fraction) * var(--_track-and-knob-padding) );transform:translateX(var(--_x-translate))}input.start:dir(rtl)::-webkit-slider-thumb{transform:translateX(calc(-1 * var(--_x-translate)))}::-moz-range-thumb{appearance:none;block-size:var(--_state-layer-size);inline-size:var(--_state-layer-size);transform:scaleX(0);opacity:0;z-index:2}.ranged input.start{clip-path:inset(0 calc(100% - (var(--_state-layer-size) / 2 + (100% - var(--_state-layer-size)) * (var(--_start-fraction) + (var(--_end-fraction) - var(--_start-fraction)) / 2))) 0 0)}.ranged input.start:dir(rtl){clip-path:inset(0 0 0 calc(100% - (var(--_state-layer-size) / 2 + (100% - var(--_state-layer-size)) * (var(--_start-fraction) + (var(--_end-fraction) - var(--_start-fraction)) / 2))))}.ranged input.end{clip-path:inset(0 0 0 calc(var(--_state-layer-size) / 2 + (100% - var(--_state-layer-size)) * (var(--_start-fraction) + (var(--_end-fraction) - var(--_start-fraction)) / 2)))}.ranged input.end:dir(rtl){clip-path:inset(0 calc(var(--_state-layer-size) / 2 + (100% - var(--_state-layer-size)) * (var(--_start-fraction) + (var(--_end-fraction) - var(--_start-fraction)) / 2)) 0 0)}.onTop{z-index:1}.handle{--md-ripple-hover-color: var(--_hover-state-layer-color);--md-ripple-hover-opacity: var(--_hover-state-layer-opacity);--md-ripple-pressed-color: var(--_pressed-state-layer-color);--md-ripple-pressed-opacity: var(--_pressed-state-layer-opacity)}md-ripple{border-radius:50%;height:var(--_state-layer-size);width:var(--_state-layer-size)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/slider/slider.js
  var MdSlider = class MdSlider2 extends Slider {
  };
  MdSlider.styles = [styles16, styles15];
  if (!customElements.get("md-slider")) {
    MdSlider = __decorate([
      t("md-slider")
    ], MdSlider);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/progress/internal/progress.js
  var progressBaseClass = mixinDelegatesAria(i4);
  var Progress = class extends progressBaseClass {
    constructor() {
      super(...arguments);
      this.value = 0;
      this.max = 1;
      this.indeterminate = false;
      this.fourColor = false;
    }
    render() {
      const { ariaLabel } = this;
      return b2`
      <div
        class="progress ${e8(this.getRenderClasses())}"
        role="progressbar"
        aria-label="${ariaLabel || A}"
        aria-valuemin="0"
        aria-valuemax=${this.max}
        aria-valuenow=${this.indeterminate ? A : this.value}
        >${this.renderIndicator()}</div
      >
    `;
    }
    getRenderClasses() {
      return {
        "indeterminate": this.indeterminate,
        "four-color": this.fourColor
      };
    }
  };
  __decorate([
    n3({ type: Number })
  ], Progress.prototype, "value", void 0);
  __decorate([
    n3({ type: Number })
  ], Progress.prototype, "max", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Progress.prototype, "indeterminate", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "four-color" })
  ], Progress.prototype, "fourColor", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/progress/internal/circular-progress.js
  var CircularProgress = class extends Progress {
    renderIndicator() {
      if (this.indeterminate) {
        return this.renderIndeterminateContainer();
      }
      return this.renderDeterminateContainer();
    }
    // Determinate mode is rendered with an svg so the progress arc can be
    // easily animated via stroke-dashoffset.
    renderDeterminateContainer() {
      const dashOffset = (1 - this.value / this.max) * 100;
      return b2`
      <svg viewBox="0 0 4800 4800">
        <circle class="track" pathLength="100"></circle>
        <circle
          class="active-track"
          pathLength="100"
          stroke-dashoffset=${dashOffset}></circle>
      </svg>
    `;
    }
    // Indeterminate mode rendered with 2 bordered-divs. The borders are
    // clipped into half circles by their containers. The divs are then carefully
    // animated to produce changes to the spinner arc size.
    // This approach has 4.5x the FPS of rendering via svg on Chrome 111.
    // See https://lit.dev/playground/#gist=febb773565272f75408ab06a0eb49746.
    renderIndeterminateContainer() {
      return b2` <div class="spinner">
      <div class="left">
        <div class="circle"></div>
      </div>
      <div class="right">
        <div class="circle"></div>
      </div>
    </div>`;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/progress/internal/circular-progress-styles.js
  var styles17 = i`:host{--_active-indicator-color: var(--md-circular-progress-active-indicator-color, var(--md-sys-color-primary, #6750a4));--_active-indicator-width: var(--md-circular-progress-active-indicator-width, 10);--_four-color-active-indicator-four-color: var(--md-circular-progress-four-color-active-indicator-four-color, var(--md-sys-color-tertiary-container, #ffd8e4));--_four-color-active-indicator-one-color: var(--md-circular-progress-four-color-active-indicator-one-color, var(--md-sys-color-primary, #6750a4));--_four-color-active-indicator-three-color: var(--md-circular-progress-four-color-active-indicator-three-color, var(--md-sys-color-tertiary, #7d5260));--_four-color-active-indicator-two-color: var(--md-circular-progress-four-color-active-indicator-two-color, var(--md-sys-color-primary-container, #eaddff));--_size: var(--md-circular-progress-size, 48px);display:inline-flex;vertical-align:middle;width:var(--_size);height:var(--_size);position:relative;align-items:center;justify-content:center;contain:strict;content-visibility:auto}.progress{flex:1;align-self:stretch;margin:4px}.progress,.spinner,.left,.right,.circle,svg,.track,.active-track{position:absolute;inset:0}svg{transform:rotate(-90deg)}circle{cx:50%;cy:50%;r:calc(50%*(1 - var(--_active-indicator-width)/100));stroke-width:calc(var(--_active-indicator-width)*1%);stroke-dasharray:100;fill:rgba(0,0,0,0)}.active-track{transition:stroke-dashoffset 500ms cubic-bezier(0, 0, 0.2, 1);stroke:var(--_active-indicator-color)}.track{stroke:rgba(0,0,0,0)}.progress.indeterminate{animation:linear infinite linear-rotate;animation-duration:1568.2352941176ms}.spinner{animation:infinite both rotate-arc;animation-duration:5332ms;animation-timing-function:cubic-bezier(0.4, 0, 0.2, 1)}.left{overflow:hidden;inset:0 50% 0 0}.right{overflow:hidden;inset:0 0 0 50%}.circle{box-sizing:border-box;border-radius:50%;border:solid calc(var(--_active-indicator-width)/100*(var(--_size) - 8px));border-color:var(--_active-indicator-color) var(--_active-indicator-color) rgba(0,0,0,0) rgba(0,0,0,0);animation:expand-arc;animation-iteration-count:infinite;animation-fill-mode:both;animation-duration:1333ms,5332ms;animation-timing-function:cubic-bezier(0.4, 0, 0.2, 1)}.four-color .circle{animation-name:expand-arc,four-color}.left .circle{rotate:135deg;inset:0 -100% 0 0}.right .circle{rotate:100deg;inset:0 0 0 -100%;animation-delay:-666.5ms,0ms}@media(forced-colors: active){.active-track{stroke:CanvasText}.circle{border-color:CanvasText CanvasText Canvas Canvas}}@keyframes expand-arc{0%{transform:rotate(265deg)}50%{transform:rotate(130deg)}100%{transform:rotate(265deg)}}@keyframes rotate-arc{12.5%{transform:rotate(135deg)}25%{transform:rotate(270deg)}37.5%{transform:rotate(405deg)}50%{transform:rotate(540deg)}62.5%{transform:rotate(675deg)}75%{transform:rotate(810deg)}87.5%{transform:rotate(945deg)}100%{transform:rotate(1080deg)}}@keyframes linear-rotate{to{transform:rotate(360deg)}}@keyframes four-color{0%{border-top-color:var(--_four-color-active-indicator-one-color);border-right-color:var(--_four-color-active-indicator-one-color)}15%{border-top-color:var(--_four-color-active-indicator-one-color);border-right-color:var(--_four-color-active-indicator-one-color)}25%{border-top-color:var(--_four-color-active-indicator-two-color);border-right-color:var(--_four-color-active-indicator-two-color)}40%{border-top-color:var(--_four-color-active-indicator-two-color);border-right-color:var(--_four-color-active-indicator-two-color)}50%{border-top-color:var(--_four-color-active-indicator-three-color);border-right-color:var(--_four-color-active-indicator-three-color)}65%{border-top-color:var(--_four-color-active-indicator-three-color);border-right-color:var(--_four-color-active-indicator-three-color)}75%{border-top-color:var(--_four-color-active-indicator-four-color);border-right-color:var(--_four-color-active-indicator-four-color)}90%{border-top-color:var(--_four-color-active-indicator-four-color);border-right-color:var(--_four-color-active-indicator-four-color)}100%{border-top-color:var(--_four-color-active-indicator-one-color);border-right-color:var(--_four-color-active-indicator-one-color)}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/progress/circular-progress.js
  var MdCircularProgress = class MdCircularProgress2 extends CircularProgress {
  };
  MdCircularProgress.styles = [styles17];
  if (!customElements.get("md-circular-progress")) {
    MdCircularProgress = __decorate([
      t("md-circular-progress")
    ], MdCircularProgress);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/elevated-styles.js
  var styles18 = i`.elevated{--md-elevation-level: var(--_elevated-container-elevation);--md-elevation-shadow-color: var(--_elevated-container-shadow-color)}.elevated::before{background:var(--_elevated-container-color)}.elevated:hover{--md-elevation-level: var(--_elevated-hover-container-elevation)}.elevated:focus-within{--md-elevation-level: var(--_elevated-focus-container-elevation)}.elevated:active{--md-elevation-level: var(--_elevated-pressed-container-elevation)}.elevated.disabled{--md-elevation-level: var(--_elevated-disabled-container-elevation)}.elevated.disabled::before{background:var(--_elevated-disabled-container-color);opacity:var(--_elevated-disabled-container-opacity)}@media(forced-colors: active){.elevated md-elevation{border:1px solid CanvasText}.elevated.disabled md-elevation{border-color:GrayText}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/chip.js
  var chipBaseClass = mixinDelegatesAria(i4);
  var Chip = class extends chipBaseClass {
    /**
     * Whether or not the primary ripple is disabled (defaults to `disabled`).
     * Some chip actions such as links cannot be disabled.
     */
    get rippleDisabled() {
      return this.disabled || this.softDisabled;
    }
    constructor() {
      super();
      this.disabled = false;
      this.softDisabled = false;
      this.alwaysFocusable = false;
      this.label = "";
      this.hasIcon = false;
      if (!o7) {
        this.addEventListener("click", this.handleClick.bind(this));
      }
    }
    focus(options) {
      if (this.disabled && !this.alwaysFocusable) {
        return;
      }
      super.focus(options);
    }
    render() {
      return b2`
      <div class="container ${e8(this.getContainerClasses())}">
        ${this.renderContainerContent()}
      </div>
    `;
    }
    updated(changed) {
      if (changed.has("disabled") && changed.get("disabled") !== void 0) {
        this.dispatchEvent(new Event("update-focus", { bubbles: true }));
      }
    }
    getContainerClasses() {
      return {
        "disabled": this.disabled || this.softDisabled,
        "has-icon": this.hasIcon
      };
    }
    renderContainerContent() {
      return b2`
      ${this.renderOutline()}
      <md-focus-ring part="focus-ring" for=${this.primaryId}></md-focus-ring>
      <md-ripple
        for=${this.primaryId}
        ?disabled=${this.rippleDisabled}></md-ripple>
      ${this.renderPrimaryAction(this.renderPrimaryContent())}
    `;
    }
    renderOutline() {
      return b2`<span class="outline"></span>`;
    }
    renderLeadingIcon() {
      return b2`<slot name="icon" @slotchange=${this.handleIconChange}></slot>`;
    }
    renderPrimaryContent() {
      return b2`
      <span class="leading icon" aria-hidden="true">
        ${this.renderLeadingIcon()}
      </span>
      <span class="label">
        <span class="label-text" id="label">
          ${this.label ? this.label : b2`<slot></slot>`}
        </span>
      </span>
      <span class="touch"></span>
    `;
    }
    handleIconChange(event) {
      const slot = event.target;
      this.hasIcon = slot.assignedElements({ flatten: true }).length > 0;
    }
    handleClick(event) {
      if (this.softDisabled || this.disabled && this.alwaysFocusable) {
        event.stopImmediatePropagation();
        event.preventDefault();
        return;
      }
    }
  };
  Chip.shadowRootOptions = {
    ...i4.shadowRootOptions,
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], Chip.prototype, "disabled", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "soft-disabled", reflect: true })
  ], Chip.prototype, "softDisabled", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "always-focusable" })
  ], Chip.prototype, "alwaysFocusable", void 0);
  __decorate([
    n3()
  ], Chip.prototype, "label", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true, attribute: "has-icon" })
  ], Chip.prototype, "hasIcon", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/multi-action-chip.js
  var ARIA_LABEL_REMOVE = "aria-label-remove";
  var MultiActionChip = class extends Chip {
    get ariaLabelRemove() {
      if (this.hasAttribute(ARIA_LABEL_REMOVE)) {
        return this.getAttribute(ARIA_LABEL_REMOVE);
      }
      const { ariaLabel } = this;
      if (ariaLabel || this.label) {
        return `Remove ${ariaLabel || this.label}`;
      }
      return null;
    }
    set ariaLabelRemove(ariaLabel) {
      const prev = this.ariaLabelRemove;
      if (ariaLabel === prev) {
        return;
      }
      if (ariaLabel === null) {
        this.removeAttribute(ARIA_LABEL_REMOVE);
      } else {
        this.setAttribute(ARIA_LABEL_REMOVE, ariaLabel);
      }
      this.requestUpdate();
    }
    constructor() {
      super();
      this.handleTrailingActionFocus = this.handleTrailingActionFocus.bind(this);
      if (!o7) {
        this.addEventListener("keydown", this.handleKeyDown.bind(this));
      }
    }
    focus(options) {
      const isFocusable2 = this.alwaysFocusable || !this.disabled;
      if (isFocusable2 && (options == null ? void 0 : options.trailing) && this.trailingAction) {
        this.trailingAction.focus(options);
        return;
      }
      super.focus(options);
    }
    renderContainerContent() {
      return b2`
      ${super.renderContainerContent()}
      ${this.renderTrailingAction(this.handleTrailingActionFocus)}
    `;
    }
    handleKeyDown(event) {
      var _a3, _b;
      const isLeft = event.key === "ArrowLeft";
      const isRight = event.key === "ArrowRight";
      if (!isLeft && !isRight) {
        return;
      }
      if (!this.primaryAction || !this.trailingAction) {
        return;
      }
      const isRtl2 = getComputedStyle(this).direction === "rtl";
      const forwards = isRtl2 ? isLeft : isRight;
      const isPrimaryFocused = (_a3 = this.primaryAction) == null ? void 0 : _a3.matches(":focus-within");
      const isTrailingFocused = (_b = this.trailingAction) == null ? void 0 : _b.matches(":focus-within");
      if (forwards && isTrailingFocused || !forwards && isPrimaryFocused) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const actionToFocus = forwards ? this.trailingAction : this.primaryAction;
      actionToFocus.focus();
    }
    handleTrailingActionFocus() {
      const { primaryAction, trailingAction } = this;
      if (!primaryAction || !trailingAction) {
        return;
      }
      primaryAction.tabIndex = -1;
      trailingAction.addEventListener("focusout", () => {
        primaryAction.tabIndex = 0;
      }, { once: true });
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/trailing-icons.js
  function renderRemoveButton({ ariaLabel, disabled, focusListener, tabbable = false }) {
    return b2`
    <span id="remove-label" hidden aria-hidden="true">Remove</span>
    <button
      class="trailing action"
      aria-label=${ariaLabel || A}
      aria-labelledby=${!ariaLabel ? "remove-label label" : A}
      tabindex=${!tabbable ? -1 : A}
      @click=${handleRemoveClick}
      @focus=${focusListener}>
      <md-focus-ring part="trailing-focus-ring"></md-focus-ring>
      <md-ripple ?disabled=${disabled}></md-ripple>
      <span class="trailing icon" aria-hidden="true">
        <slot name="remove-trailing-icon">
          <svg viewBox="0 96 960 960">
            <path
              d="m249 849-42-42 231-231-231-231 42-42 231 231 231-231 42 42-231 231 231 231-42 42-231-231-231 231Z" />
          </svg>
        </slot>
      </span>
      <span class="touch"></span>
    </button>
  `;
  }
  function handleRemoveClick(event) {
    if (this.disabled || this.softDisabled) {
      return;
    }
    event.stopPropagation();
    const preventDefault = !this.dispatchEvent(new Event("remove", { cancelable: true }));
    if (preventDefault) {
      return;
    }
    this.remove();
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/filter-chip.js
  var FilterChip = class extends MultiActionChip {
    constructor() {
      super(...arguments);
      this.elevated = false;
      this.removable = false;
      this.selected = false;
      this.hasSelectedIcon = false;
    }
    get primaryId() {
      return "button";
    }
    getContainerClasses() {
      return {
        ...super.getContainerClasses(),
        elevated: this.elevated,
        selected: this.selected,
        "has-trailing": this.removable,
        "has-icon": this.hasIcon || this.selected
      };
    }
    renderPrimaryAction(content) {
      const { ariaLabel } = this;
      return b2`
      <button
        class="primary action"
        id="button"
        aria-label=${ariaLabel || A}
        aria-pressed=${this.selected}
        aria-disabled=${this.softDisabled || A}
        ?disabled=${this.disabled && !this.alwaysFocusable}
        @click=${this.handleClickOnChild}
        >${content}</button
      >
    `;
    }
    renderLeadingIcon() {
      if (!this.selected) {
        return super.renderLeadingIcon();
      }
      return b2`
      <slot name="selected-icon">
        <svg class="checkmark" viewBox="0 0 18 18" aria-hidden="true">
          <path
            d="M6.75012 12.1274L3.62262 8.99988L2.55762 10.0574L6.75012 14.2499L15.7501 5.24988L14.6926 4.19238L6.75012 12.1274Z" />
        </svg>
      </slot>
    `;
    }
    renderTrailingAction(focusListener) {
      if (this.removable) {
        return renderRemoveButton({
          focusListener,
          ariaLabel: this.ariaLabelRemove,
          disabled: this.disabled || this.softDisabled
        });
      }
      return A;
    }
    renderOutline() {
      if (this.elevated) {
        return b2`<md-elevation part="elevation"></md-elevation>`;
      }
      return super.renderOutline();
    }
    handleClickOnChild(event) {
      if (this.disabled || this.softDisabled) {
        return;
      }
      const prevValue = this.selected;
      this.selected = !this.selected;
      const preventDefault = !redispatchEvent(this, event);
      if (preventDefault) {
        this.selected = prevValue;
        return;
      }
    }
  };
  __decorate([
    n3({ type: Boolean })
  ], FilterChip.prototype, "elevated", void 0);
  __decorate([
    n3({ type: Boolean })
  ], FilterChip.prototype, "removable", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], FilterChip.prototype, "selected", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true, attribute: "has-selected-icon" })
  ], FilterChip.prototype, "hasSelectedIcon", void 0);
  __decorate([
    e4(".primary.action")
  ], FilterChip.prototype, "primaryAction", void 0);
  __decorate([
    e4(".trailing.action")
  ], FilterChip.prototype, "trailingAction", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/filter-styles.js
  var styles19 = i`:host{--_container-height: var(--md-filter-chip-container-height, 32px);--_disabled-label-text-color: var(--md-filter-chip-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-label-text-opacity: var(--md-filter-chip-disabled-label-text-opacity, 0.38);--_elevated-container-elevation: var(--md-filter-chip-elevated-container-elevation, 1);--_elevated-container-shadow-color: var(--md-filter-chip-elevated-container-shadow-color, var(--md-sys-color-shadow, #000));--_elevated-disabled-container-color: var(--md-filter-chip-elevated-disabled-container-color, var(--md-sys-color-on-surface, #1d1b20));--_elevated-disabled-container-elevation: var(--md-filter-chip-elevated-disabled-container-elevation, 0);--_elevated-disabled-container-opacity: var(--md-filter-chip-elevated-disabled-container-opacity, 0.12);--_elevated-focus-container-elevation: var(--md-filter-chip-elevated-focus-container-elevation, 1);--_elevated-hover-container-elevation: var(--md-filter-chip-elevated-hover-container-elevation, 2);--_elevated-pressed-container-elevation: var(--md-filter-chip-elevated-pressed-container-elevation, 1);--_elevated-selected-container-color: var(--md-filter-chip-elevated-selected-container-color, var(--md-sys-color-secondary-container, #e8def8));--_label-text-font: var(--md-filter-chip-label-text-font, var(--md-sys-typescale-label-large-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-filter-chip-label-text-line-height, var(--md-sys-typescale-label-large-line-height, 1.25rem));--_label-text-size: var(--md-filter-chip-label-text-size, var(--md-sys-typescale-label-large-size, 0.875rem));--_label-text-weight: var(--md-filter-chip-label-text-weight, var(--md-sys-typescale-label-large-weight, var(--md-ref-typeface-weight-medium, 500)));--_selected-focus-label-text-color: var(--md-filter-chip-selected-focus-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-hover-label-text-color: var(--md-filter-chip-selected-hover-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-hover-state-layer-color: var(--md-filter-chip-selected-hover-state-layer-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-hover-state-layer-opacity: var(--md-filter-chip-selected-hover-state-layer-opacity, 0.08);--_selected-label-text-color: var(--md-filter-chip-selected-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-pressed-label-text-color: var(--md-filter-chip-selected-pressed-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-pressed-state-layer-color: var(--md-filter-chip-selected-pressed-state-layer-color, var(--md-sys-color-on-surface-variant, #49454f));--_selected-pressed-state-layer-opacity: var(--md-filter-chip-selected-pressed-state-layer-opacity, 0.12);--_elevated-container-color: var(--md-filter-chip-elevated-container-color, var(--md-sys-color-surface-container-low, #f7f2fa));--_disabled-outline-color: var(--md-filter-chip-disabled-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-outline-opacity: var(--md-filter-chip-disabled-outline-opacity, 0.12);--_disabled-selected-container-color: var(--md-filter-chip-disabled-selected-container-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-selected-container-opacity: var(--md-filter-chip-disabled-selected-container-opacity, 0.12);--_focus-outline-color: var(--md-filter-chip-focus-outline-color, var(--md-sys-color-on-surface-variant, #49454f));--_outline-color: var(--md-filter-chip-outline-color, var(--md-sys-color-outline, #79747e));--_outline-width: var(--md-filter-chip-outline-width, 1px);--_selected-container-color: var(--md-filter-chip-selected-container-color, var(--md-sys-color-secondary-container, #e8def8));--_selected-outline-width: var(--md-filter-chip-selected-outline-width, 0px);--_focus-label-text-color: var(--md-filter-chip-focus-label-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-label-text-color: var(--md-filter-chip-hover-label-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-state-layer-color: var(--md-filter-chip-hover-state-layer-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-state-layer-opacity: var(--md-filter-chip-hover-state-layer-opacity, 0.08);--_label-text-color: var(--md-filter-chip-label-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-label-text-color: var(--md-filter-chip-pressed-label-text-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-state-layer-color: var(--md-filter-chip-pressed-state-layer-color, var(--md-sys-color-on-secondary-container, #1d192b));--_pressed-state-layer-opacity: var(--md-filter-chip-pressed-state-layer-opacity, 0.12);--_icon-size: var(--md-filter-chip-icon-size, 18px);--_disabled-leading-icon-color: var(--md-filter-chip-disabled-leading-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-leading-icon-opacity: var(--md-filter-chip-disabled-leading-icon-opacity, 0.38);--_selected-focus-leading-icon-color: var(--md-filter-chip-selected-focus-leading-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-hover-leading-icon-color: var(--md-filter-chip-selected-hover-leading-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-leading-icon-color: var(--md-filter-chip-selected-leading-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-pressed-leading-icon-color: var(--md-filter-chip-selected-pressed-leading-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_focus-leading-icon-color: var(--md-filter-chip-focus-leading-icon-color, var(--md-sys-color-primary, #6750a4));--_hover-leading-icon-color: var(--md-filter-chip-hover-leading-icon-color, var(--md-sys-color-primary, #6750a4));--_leading-icon-color: var(--md-filter-chip-leading-icon-color, var(--md-sys-color-primary, #6750a4));--_pressed-leading-icon-color: var(--md-filter-chip-pressed-leading-icon-color, var(--md-sys-color-primary, #6750a4));--_disabled-trailing-icon-color: var(--md-filter-chip-disabled-trailing-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-trailing-icon-opacity: var(--md-filter-chip-disabled-trailing-icon-opacity, 0.38);--_selected-focus-trailing-icon-color: var(--md-filter-chip-selected-focus-trailing-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-hover-trailing-icon-color: var(--md-filter-chip-selected-hover-trailing-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-pressed-trailing-icon-color: var(--md-filter-chip-selected-pressed-trailing-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_selected-trailing-icon-color: var(--md-filter-chip-selected-trailing-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_focus-trailing-icon-color: var(--md-filter-chip-focus-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-trailing-icon-color: var(--md-filter-chip-hover-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-trailing-icon-color: var(--md-filter-chip-pressed-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_trailing-icon-color: var(--md-filter-chip-trailing-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_container-shape-start-start: var(--md-filter-chip-container-shape-start-start, var(--md-filter-chip-container-shape, var(--md-sys-shape-corner-small, 8px)));--_container-shape-start-end: var(--md-filter-chip-container-shape-start-end, var(--md-filter-chip-container-shape, var(--md-sys-shape-corner-small, 8px)));--_container-shape-end-end: var(--md-filter-chip-container-shape-end-end, var(--md-filter-chip-container-shape, var(--md-sys-shape-corner-small, 8px)));--_container-shape-end-start: var(--md-filter-chip-container-shape-end-start, var(--md-filter-chip-container-shape, var(--md-sys-shape-corner-small, 8px)));--_leading-space: var(--md-filter-chip-leading-space, 16px);--_trailing-space: var(--md-filter-chip-trailing-space, 16px);--_icon-label-space: var(--md-filter-chip-icon-label-space, 8px);--_with-leading-icon-leading-space: var(--md-filter-chip-with-leading-icon-leading-space, 8px);--_with-trailing-icon-trailing-space: var(--md-filter-chip-with-trailing-icon-trailing-space, 8px)}.selected.elevated::before{background:var(--_elevated-selected-container-color)}.checkmark{height:var(--_icon-size);width:var(--_icon-size)}.disabled .checkmark{opacity:var(--_disabled-leading-icon-opacity)}@media(forced-colors: active){.disabled .checkmark{opacity:1}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/selectable-styles.js
  var styles20 = i`.selected{--md-ripple-hover-color: var(--_selected-hover-state-layer-color);--md-ripple-hover-opacity: var(--_selected-hover-state-layer-opacity);--md-ripple-pressed-color: var(--_selected-pressed-state-layer-color);--md-ripple-pressed-opacity: var(--_selected-pressed-state-layer-opacity)}:where(.selected)::before{background:var(--_selected-container-color)}:where(.selected) .outline{border-width:var(--_selected-outline-width)}:where(.selected.disabled)::before{background:var(--_disabled-selected-container-color);opacity:var(--_disabled-selected-container-opacity)}:where(.selected) .label{color:var(--_selected-label-text-color)}:where(.selected:hover) .label{color:var(--_selected-hover-label-text-color)}:where(.selected:focus) .label{color:var(--_selected-focus-label-text-color)}:where(.selected:active) .label{color:var(--_selected-pressed-label-text-color)}:where(.selected) .leading.icon{color:var(--_selected-leading-icon-color)}:where(.selected:hover) .leading.icon{color:var(--_selected-hover-leading-icon-color)}:where(.selected:focus) .leading.icon{color:var(--_selected-focus-leading-icon-color)}:where(.selected:active) .leading.icon{color:var(--_selected-pressed-leading-icon-color)}@media(forced-colors: active){:where(.selected:not(.elevated))::before{border:1px solid CanvasText}:where(.selected) .outline{border-width:1px}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/shared-styles.js
  var styles21 = i`:host{border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-start-radius:var(--_container-shape-end-start);border-end-end-radius:var(--_container-shape-end-end);display:inline-flex;height:var(--_container-height);cursor:pointer;-webkit-tap-highlight-color:rgba(0,0,0,0);--md-ripple-hover-color: var(--_hover-state-layer-color);--md-ripple-hover-opacity: var(--_hover-state-layer-opacity);--md-ripple-pressed-color: var(--_pressed-state-layer-color);--md-ripple-pressed-opacity: var(--_pressed-state-layer-opacity)}:host(:is([disabled],[soft-disabled])){pointer-events:none}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--_container-height))/2) 0}md-focus-ring{--md-focus-ring-shape-start-start: var(--_container-shape-start-start);--md-focus-ring-shape-start-end: var(--_container-shape-start-end);--md-focus-ring-shape-end-end: var(--_container-shape-end-end);--md-focus-ring-shape-end-start: var(--_container-shape-end-start)}.container{border-radius:inherit;box-sizing:border-box;display:flex;height:100%;position:relative;width:100%}.container::before{border-radius:inherit;content:"";inset:0;pointer-events:none;position:absolute}.container:not(.disabled){cursor:pointer}.container.disabled{pointer-events:none}.cell{display:flex}.action{align-items:baseline;appearance:none;background:none;border:none;border-radius:inherit;display:flex;outline:none;padding:0;position:relative;text-decoration:none}.primary.action{min-width:0;padding-inline-start:var(--_leading-space);padding-inline-end:var(--_trailing-space)}.has-icon .primary.action{padding-inline-start:var(--_with-leading-icon-leading-space)}.touch{height:48px;inset:50% 0 0;position:absolute;transform:translateY(-50%);width:100%}:host([touch-target=none]) .touch{display:none}.outline{border:var(--_outline-width) solid var(--_outline-color);border-radius:inherit;inset:0;pointer-events:none;position:absolute}:where(:focus) .outline{border-color:var(--_focus-outline-color)}:where(.disabled) .outline{border-color:var(--_disabled-outline-color);opacity:var(--_disabled-outline-opacity)}md-ripple{border-radius:inherit}.label,.icon,.touch{z-index:1}.label{align-items:center;color:var(--_label-text-color);display:flex;font-family:var(--_label-text-font);font-size:var(--_label-text-size);font-weight:var(--_label-text-weight);height:100%;line-height:var(--_label-text-line-height);overflow:hidden;user-select:none}.label-text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}:where(:hover) .label{color:var(--_hover-label-text-color)}:where(:focus) .label{color:var(--_focus-label-text-color)}:where(:active) .label{color:var(--_pressed-label-text-color)}:where(.disabled) .label{color:var(--_disabled-label-text-color);opacity:var(--_disabled-label-text-opacity)}.icon{align-self:center;display:flex;fill:currentColor;position:relative}.icon ::slotted(:first-child){font-size:var(--_icon-size);height:var(--_icon-size);width:var(--_icon-size)}.leading.icon{color:var(--_leading-icon-color)}.leading.icon ::slotted(*),.leading.icon svg{margin-inline-end:var(--_icon-label-space)}:where(:hover) .leading.icon{color:var(--_hover-leading-icon-color)}:where(:focus) .leading.icon{color:var(--_focus-leading-icon-color)}:where(:active) .leading.icon{color:var(--_pressed-leading-icon-color)}:where(.disabled) .leading.icon{color:var(--_disabled-leading-icon-color);opacity:var(--_disabled-leading-icon-opacity)}@media(forced-colors: active){:where(.disabled) :is(.label,.outline,.leading.icon){color:GrayText;opacity:1}}a,button{text-transform:inherit}a,button:not(:disabled,[aria-disabled=true]){cursor:inherit}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/internal/trailing-icon-styles.js
  var styles22 = i`.trailing.action{align-items:center;justify-content:center;padding-inline-start:var(--_icon-label-space);padding-inline-end:var(--_with-trailing-icon-trailing-space)}.trailing.action :is(md-ripple,md-focus-ring){border-radius:50%;height:calc(1.3333333333*var(--_icon-size));width:calc(1.3333333333*var(--_icon-size))}.trailing.action md-focus-ring{inset:unset}.has-trailing .primary.action{padding-inline-end:0}.trailing.icon{color:var(--_trailing-icon-color);height:var(--_icon-size);width:var(--_icon-size)}:where(:hover) .trailing.icon{color:var(--_hover-trailing-icon-color)}:where(:focus) .trailing.icon{color:var(--_focus-trailing-icon-color)}:where(:active) .trailing.icon{color:var(--_pressed-trailing-icon-color)}:where(.disabled) .trailing.icon{color:var(--_disabled-trailing-icon-color);opacity:var(--_disabled-trailing-icon-opacity)}:where(.selected) .trailing.icon{color:var(--_selected-trailing-icon-color)}:where(.selected:hover) .trailing.icon{color:var(--_selected-hover-trailing-icon-color)}:where(.selected:focus) .trailing.icon{color:var(--_selected-focus-trailing-icon-color)}:where(.selected:active) .trailing.icon{color:var(--_selected-pressed-trailing-icon-color)}@media(forced-colors: active){.trailing.icon{color:ButtonText}:where(.disabled) .trailing.icon{color:GrayText;opacity:1}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/chips/filter-chip.js
  var MdFilterChip = class MdFilterChip2 extends FilterChip {
  };
  MdFilterChip.styles = [
    styles21,
    styles18,
    styles22,
    styles20,
    styles19
  ];
  if (!customElements.get("md-filter-chip")) {
    MdFilterChip = __decorate([
      t("md-filter-chip")
    ], MdFilterChip);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/controller/form-submitter.js
  function setupFormSubmitter(ctor) {
    if (o7) {
      return;
    }
    ctor.addInitializer((instance) => {
      const submitter = instance;
      submitter.addEventListener("click", async (event) => {
        const { type, [internals]: elementInternals } = submitter;
        const { form } = elementInternals;
        if (!form || type === "button") {
          return;
        }
        await new Promise((resolve) => {
          setTimeout(resolve);
        });
        if (event.defaultPrevented) {
          return;
        }
        if (type === "reset") {
          form.reset();
          return;
        }
        form.addEventListener("submit", (submitEvent) => {
          Object.defineProperty(submitEvent, "submitter", {
            configurable: true,
            enumerable: true,
            get: () => submitter
          });
        }, { capture: true, once: true });
        elementInternals.setFormValue(submitter.value);
        form.requestSubmit();
      });
    });
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/button.js
  var buttonBaseClass = mixinDelegatesAria(mixinElementInternals(i4));
  var Button = class extends buttonBaseClass {
    get name() {
      return this.getAttribute("name") ?? "";
    }
    set name(name) {
      this.setAttribute("name", name);
    }
    /**
     * The associated form element with which this element's value will submit.
     */
    get form() {
      return this[internals].form;
    }
    constructor() {
      super();
      this.disabled = false;
      this.softDisabled = false;
      this.href = "";
      this.download = "";
      this.target = "";
      this.trailingIcon = false;
      this.hasIcon = false;
      this.type = "submit";
      this.value = "";
      if (!o7) {
        this.addEventListener("click", this.handleClick.bind(this));
      }
    }
    focus() {
      var _a3;
      (_a3 = this.buttonElement) == null ? void 0 : _a3.focus();
    }
    blur() {
      var _a3;
      (_a3 = this.buttonElement) == null ? void 0 : _a3.blur();
    }
    render() {
      var _a3;
      const isRippleDisabled = this.disabled || this.softDisabled;
      const buttonOrLink = this.href ? this.renderLink() : this.renderButton();
      const buttonId = this.href ? "link" : "button";
      return b2`
      ${(_a3 = this.renderElevationOrOutline) == null ? void 0 : _a3.call(this)}
      <div class="background"></div>
      <md-focus-ring part="focus-ring" for=${buttonId}></md-focus-ring>
      <md-ripple
        part="ripple"
        for=${buttonId}
        ?disabled="${isRippleDisabled}"></md-ripple>
      ${buttonOrLink}
    `;
    }
    renderButton() {
      const { ariaLabel, ariaHasPopup, ariaExpanded } = this;
      return b2`<button
      id="button"
      class="button"
      ?disabled=${this.disabled}
      aria-disabled=${this.softDisabled || A}
      aria-label="${ariaLabel || A}"
      aria-haspopup="${ariaHasPopup || A}"
      aria-expanded="${ariaExpanded || A}">
      ${this.renderContent()}
    </button>`;
    }
    renderLink() {
      const { ariaLabel, ariaHasPopup, ariaExpanded } = this;
      return b2`<a
      id="link"
      class="button"
      aria-label="${ariaLabel || A}"
      aria-haspopup="${ariaHasPopup || A}"
      aria-expanded="${ariaExpanded || A}"
      aria-disabled=${this.disabled || this.softDisabled || A}
      tabindex="${this.disabled && !this.softDisabled ? -1 : A}"
      href=${this.href}
      download=${this.download || A}
      target=${this.target || A}
      >${this.renderContent()}
    </a>`;
    }
    renderContent() {
      const icon = b2`<slot
      name="icon"
      @slotchange="${this.handleSlotChange}"></slot>`;
      return b2`
      <span class="touch"></span>
      ${this.trailingIcon ? A : icon}
      <span class="label"><slot></slot></span>
      ${this.trailingIcon ? icon : A}
    `;
    }
    handleClick(event) {
      if (this.softDisabled || this.disabled && this.href) {
        event.stopImmediatePropagation();
        event.preventDefault();
        return;
      }
      if (!isActivationClick(event) || !this.buttonElement) {
        return;
      }
      this.focus();
      dispatchActivationClick(this.buttonElement);
    }
    handleSlotChange() {
      this.hasIcon = this.assignedIcons.length > 0;
    }
  };
  (() => {
    setupFormSubmitter(Button);
  })();
  Button.formAssociated = true;
  Button.shadowRootOptions = {
    mode: "open",
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], Button.prototype, "disabled", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "soft-disabled", reflect: true })
  ], Button.prototype, "softDisabled", void 0);
  __decorate([
    n3()
  ], Button.prototype, "href", void 0);
  __decorate([
    n3()
  ], Button.prototype, "download", void 0);
  __decorate([
    n3()
  ], Button.prototype, "target", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "trailing-icon", reflect: true })
  ], Button.prototype, "trailingIcon", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "has-icon", reflect: true })
  ], Button.prototype, "hasIcon", void 0);
  __decorate([
    n3()
  ], Button.prototype, "type", void 0);
  __decorate([
    n3({ reflect: true })
  ], Button.prototype, "value", void 0);
  __decorate([
    e4(".button")
  ], Button.prototype, "buttonElement", void 0);
  __decorate([
    o4({ slot: "icon", flatten: true })
  ], Button.prototype, "assignedIcons", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/filled-button.js
  var FilledButton = class extends Button {
    renderElevationOrOutline() {
      return b2`<md-elevation part="elevation"></md-elevation>`;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/filled-styles.js
  var styles23 = i`:host{--_container-color: var(--md-filled-button-container-color, var(--md-sys-color-primary, #6750a4));--_container-elevation: var(--md-filled-button-container-elevation, 0);--_container-height: var(--md-filled-button-container-height, 40px);--_container-shadow-color: var(--md-filled-button-container-shadow-color, var(--md-sys-color-shadow, #000));--_disabled-container-color: var(--md-filled-button-disabled-container-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-container-elevation: var(--md-filled-button-disabled-container-elevation, 0);--_disabled-container-opacity: var(--md-filled-button-disabled-container-opacity, 0.12);--_disabled-label-text-color: var(--md-filled-button-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-label-text-opacity: var(--md-filled-button-disabled-label-text-opacity, 0.38);--_focus-container-elevation: var(--md-filled-button-focus-container-elevation, 0);--_focus-label-text-color: var(--md-filled-button-focus-label-text-color, var(--md-sys-color-on-primary, #fff));--_hover-container-elevation: var(--md-filled-button-hover-container-elevation, 1);--_hover-label-text-color: var(--md-filled-button-hover-label-text-color, var(--md-sys-color-on-primary, #fff));--_hover-state-layer-color: var(--md-filled-button-hover-state-layer-color, var(--md-sys-color-on-primary, #fff));--_hover-state-layer-opacity: var(--md-filled-button-hover-state-layer-opacity, 0.08);--_label-text-color: var(--md-filled-button-label-text-color, var(--md-sys-color-on-primary, #fff));--_label-text-font: var(--md-filled-button-label-text-font, var(--md-sys-typescale-label-large-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-filled-button-label-text-line-height, var(--md-sys-typescale-label-large-line-height, 1.25rem));--_label-text-size: var(--md-filled-button-label-text-size, var(--md-sys-typescale-label-large-size, 0.875rem));--_label-text-weight: var(--md-filled-button-label-text-weight, var(--md-sys-typescale-label-large-weight, var(--md-ref-typeface-weight-medium, 500)));--_pressed-container-elevation: var(--md-filled-button-pressed-container-elevation, 0);--_pressed-label-text-color: var(--md-filled-button-pressed-label-text-color, var(--md-sys-color-on-primary, #fff));--_pressed-state-layer-color: var(--md-filled-button-pressed-state-layer-color, var(--md-sys-color-on-primary, #fff));--_pressed-state-layer-opacity: var(--md-filled-button-pressed-state-layer-opacity, 0.12);--_disabled-icon-color: var(--md-filled-button-disabled-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-icon-opacity: var(--md-filled-button-disabled-icon-opacity, 0.38);--_focus-icon-color: var(--md-filled-button-focus-icon-color, var(--md-sys-color-on-primary, #fff));--_hover-icon-color: var(--md-filled-button-hover-icon-color, var(--md-sys-color-on-primary, #fff));--_icon-color: var(--md-filled-button-icon-color, var(--md-sys-color-on-primary, #fff));--_icon-size: var(--md-filled-button-icon-size, 18px);--_pressed-icon-color: var(--md-filled-button-pressed-icon-color, var(--md-sys-color-on-primary, #fff));--_container-shape-start-start: var(--md-filled-button-container-shape-start-start, var(--md-filled-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-start-end: var(--md-filled-button-container-shape-start-end, var(--md-filled-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-end: var(--md-filled-button-container-shape-end-end, var(--md-filled-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-start: var(--md-filled-button-container-shape-end-start, var(--md-filled-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_leading-space: var(--md-filled-button-leading-space, 24px);--_trailing-space: var(--md-filled-button-trailing-space, 24px);--_with-leading-icon-leading-space: var(--md-filled-button-with-leading-icon-leading-space, 16px);--_with-leading-icon-trailing-space: var(--md-filled-button-with-leading-icon-trailing-space, 24px);--_with-trailing-icon-leading-space: var(--md-filled-button-with-trailing-icon-leading-space, 24px);--_with-trailing-icon-trailing-space: var(--md-filled-button-with-trailing-icon-trailing-space, 16px)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/shared-elevation-styles.js
  var styles24 = i`md-elevation{transition-duration:280ms}:host(:is([disabled],[soft-disabled])) md-elevation{transition:none}md-elevation{--md-elevation-level: var(--_container-elevation);--md-elevation-shadow-color: var(--_container-shadow-color)}:host(:focus-within) md-elevation{--md-elevation-level: var(--_focus-container-elevation)}:host(:hover) md-elevation{--md-elevation-level: var(--_hover-container-elevation)}:host(:active) md-elevation{--md-elevation-level: var(--_pressed-container-elevation)}:host(:is([disabled],[soft-disabled])) md-elevation{--md-elevation-level: var(--_disabled-container-elevation)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/shared-styles.js
  var styles25 = i`:host{border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-start-radius:var(--_container-shape-end-start);border-end-end-radius:var(--_container-shape-end-end);box-sizing:border-box;cursor:pointer;display:inline-flex;gap:8px;min-height:var(--_container-height);outline:none;padding-block:calc((var(--_container-height) - max(var(--_label-text-line-height),var(--_icon-size)))/2);padding-inline-start:var(--_leading-space);padding-inline-end:var(--_trailing-space);place-content:center;place-items:center;position:relative;font-family:var(--_label-text-font);font-size:var(--_label-text-size);line-height:var(--_label-text-line-height);font-weight:var(--_label-text-weight);text-overflow:ellipsis;text-wrap:nowrap;user-select:none;-webkit-tap-highlight-color:rgba(0,0,0,0);vertical-align:top;--md-ripple-hover-color: var(--_hover-state-layer-color);--md-ripple-pressed-color: var(--_pressed-state-layer-color);--md-ripple-hover-opacity: var(--_hover-state-layer-opacity);--md-ripple-pressed-opacity: var(--_pressed-state-layer-opacity)}md-focus-ring{--md-focus-ring-shape-start-start: var(--_container-shape-start-start);--md-focus-ring-shape-start-end: var(--_container-shape-start-end);--md-focus-ring-shape-end-end: var(--_container-shape-end-end);--md-focus-ring-shape-end-start: var(--_container-shape-end-start)}:host(:is([disabled],[soft-disabled])){cursor:default;pointer-events:none}.button{border-radius:inherit;cursor:inherit;display:inline-flex;align-items:center;justify-content:center;border:none;outline:none;-webkit-appearance:none;vertical-align:middle;background:rgba(0,0,0,0);text-decoration:none;min-width:calc(64px - var(--_leading-space) - var(--_trailing-space));width:100%;z-index:0;height:100%;font:inherit;color:var(--_label-text-color);padding:0;gap:inherit;text-transform:inherit}.button::-moz-focus-inner{padding:0;border:0}:host(:hover) .button{color:var(--_hover-label-text-color)}:host(:focus-within) .button{color:var(--_focus-label-text-color)}:host(:active) .button{color:var(--_pressed-label-text-color)}.background{background:var(--_container-color);border-radius:inherit;inset:0;position:absolute}.label{overflow:hidden}:is(.button,.label,.label slot),.label ::slotted(*){text-overflow:inherit}:host(:is([disabled],[soft-disabled])) .label{color:var(--_disabled-label-text-color);opacity:var(--_disabled-label-text-opacity)}:host(:is([disabled],[soft-disabled])) .background{background:var(--_disabled-container-color);opacity:var(--_disabled-container-opacity)}@media(forced-colors: active){.background{border:1px solid CanvasText}:host(:is([disabled],[soft-disabled])){--_disabled-icon-color: GrayText;--_disabled-icon-opacity: 1;--_disabled-container-opacity: 1;--_disabled-label-text-color: GrayText;--_disabled-label-text-opacity: 1}}:host([has-icon]:not([trailing-icon])){padding-inline-start:var(--_with-leading-icon-leading-space);padding-inline-end:var(--_with-leading-icon-trailing-space)}:host([has-icon][trailing-icon]){padding-inline-start:var(--_with-trailing-icon-leading-space);padding-inline-end:var(--_with-trailing-icon-trailing-space)}::slotted([slot=icon]){display:inline-flex;position:relative;writing-mode:horizontal-tb;fill:currentColor;flex-shrink:0;color:var(--_icon-color);font-size:var(--_icon-size);inline-size:var(--_icon-size);block-size:var(--_icon-size)}:host(:hover) ::slotted([slot=icon]){color:var(--_hover-icon-color)}:host(:focus-within) ::slotted([slot=icon]){color:var(--_focus-icon-color)}:host(:active) ::slotted([slot=icon]){color:var(--_pressed-icon-color)}:host(:is([disabled],[soft-disabled])) ::slotted([slot=icon]){color:var(--_disabled-icon-color);opacity:var(--_disabled-icon-opacity)}.touch{position:absolute;top:50%;height:48px;left:0;right:0;transform:translateY(-50%)}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--_container-height))/2) 0}:host([touch-target=none]) .touch{display:none}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/filled-button.js
  var MdFilledButton = class MdFilledButton2 extends FilledButton {
  };
  MdFilledButton.styles = [
    styles25,
    styles24,
    styles23
  ];
  if (!customElements.get("md-filled-button")) {
    MdFilledButton = __decorate([
      t("md-filled-button")
    ], MdFilledButton);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/filled-tonal-button.js
  var FilledTonalButton = class extends Button {
    renderElevationOrOutline() {
      return b2`<md-elevation part="elevation"></md-elevation>`;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/filled-tonal-styles.js
  var styles26 = i`:host{--_container-color: var(--md-filled-tonal-button-container-color, var(--md-sys-color-secondary-container, #e8def8));--_container-elevation: var(--md-filled-tonal-button-container-elevation, 0);--_container-height: var(--md-filled-tonal-button-container-height, 40px);--_container-shadow-color: var(--md-filled-tonal-button-container-shadow-color, var(--md-sys-color-shadow, #000));--_disabled-container-color: var(--md-filled-tonal-button-disabled-container-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-container-elevation: var(--md-filled-tonal-button-disabled-container-elevation, 0);--_disabled-container-opacity: var(--md-filled-tonal-button-disabled-container-opacity, 0.12);--_disabled-label-text-color: var(--md-filled-tonal-button-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-label-text-opacity: var(--md-filled-tonal-button-disabled-label-text-opacity, 0.38);--_focus-container-elevation: var(--md-filled-tonal-button-focus-container-elevation, 0);--_focus-label-text-color: var(--md-filled-tonal-button-focus-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_hover-container-elevation: var(--md-filled-tonal-button-hover-container-elevation, 1);--_hover-label-text-color: var(--md-filled-tonal-button-hover-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_hover-state-layer-color: var(--md-filled-tonal-button-hover-state-layer-color, var(--md-sys-color-on-secondary-container, #1d192b));--_hover-state-layer-opacity: var(--md-filled-tonal-button-hover-state-layer-opacity, 0.08);--_label-text-color: var(--md-filled-tonal-button-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_label-text-font: var(--md-filled-tonal-button-label-text-font, var(--md-sys-typescale-label-large-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-filled-tonal-button-label-text-line-height, var(--md-sys-typescale-label-large-line-height, 1.25rem));--_label-text-size: var(--md-filled-tonal-button-label-text-size, var(--md-sys-typescale-label-large-size, 0.875rem));--_label-text-weight: var(--md-filled-tonal-button-label-text-weight, var(--md-sys-typescale-label-large-weight, var(--md-ref-typeface-weight-medium, 500)));--_pressed-container-elevation: var(--md-filled-tonal-button-pressed-container-elevation, 0);--_pressed-label-text-color: var(--md-filled-tonal-button-pressed-label-text-color, var(--md-sys-color-on-secondary-container, #1d192b));--_pressed-state-layer-color: var(--md-filled-tonal-button-pressed-state-layer-color, var(--md-sys-color-on-secondary-container, #1d192b));--_pressed-state-layer-opacity: var(--md-filled-tonal-button-pressed-state-layer-opacity, 0.12);--_disabled-icon-color: var(--md-filled-tonal-button-disabled-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-icon-opacity: var(--md-filled-tonal-button-disabled-icon-opacity, 0.38);--_focus-icon-color: var(--md-filled-tonal-button-focus-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_hover-icon-color: var(--md-filled-tonal-button-hover-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_icon-color: var(--md-filled-tonal-button-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_icon-size: var(--md-filled-tonal-button-icon-size, 18px);--_pressed-icon-color: var(--md-filled-tonal-button-pressed-icon-color, var(--md-sys-color-on-secondary-container, #1d192b));--_container-shape-start-start: var(--md-filled-tonal-button-container-shape-start-start, var(--md-filled-tonal-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-start-end: var(--md-filled-tonal-button-container-shape-start-end, var(--md-filled-tonal-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-end: var(--md-filled-tonal-button-container-shape-end-end, var(--md-filled-tonal-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-start: var(--md-filled-tonal-button-container-shape-end-start, var(--md-filled-tonal-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_leading-space: var(--md-filled-tonal-button-leading-space, 24px);--_trailing-space: var(--md-filled-tonal-button-trailing-space, 24px);--_with-leading-icon-leading-space: var(--md-filled-tonal-button-with-leading-icon-leading-space, 16px);--_with-leading-icon-trailing-space: var(--md-filled-tonal-button-with-leading-icon-trailing-space, 24px);--_with-trailing-icon-leading-space: var(--md-filled-tonal-button-with-trailing-icon-leading-space, 24px);--_with-trailing-icon-trailing-space: var(--md-filled-tonal-button-with-trailing-icon-trailing-space, 16px)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/filled-tonal-button.js
  var MdFilledTonalButton = class MdFilledTonalButton2 extends FilledTonalButton {
  };
  MdFilledTonalButton.styles = [
    styles25,
    styles24,
    styles26
  ];
  if (!customElements.get("md-filled-tonal-button")) {
    MdFilledTonalButton = __decorate([
      t("md-filled-tonal-button")
    ], MdFilledTonalButton);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/outlined-button.js
  var OutlinedButton = class extends Button {
    renderElevationOrOutline() {
      return b2`<div class="outline"></div>`;
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/outlined-styles.js
  var styles27 = i`:host{--_container-height: var(--md-outlined-button-container-height, 40px);--_disabled-label-text-color: var(--md-outlined-button-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-label-text-opacity: var(--md-outlined-button-disabled-label-text-opacity, 0.38);--_disabled-outline-color: var(--md-outlined-button-disabled-outline-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-outline-opacity: var(--md-outlined-button-disabled-outline-opacity, 0.12);--_focus-label-text-color: var(--md-outlined-button-focus-label-text-color, var(--md-sys-color-primary, #6750a4));--_hover-label-text-color: var(--md-outlined-button-hover-label-text-color, var(--md-sys-color-primary, #6750a4));--_hover-state-layer-color: var(--md-outlined-button-hover-state-layer-color, var(--md-sys-color-primary, #6750a4));--_hover-state-layer-opacity: var(--md-outlined-button-hover-state-layer-opacity, 0.08);--_label-text-color: var(--md-outlined-button-label-text-color, var(--md-sys-color-primary, #6750a4));--_label-text-font: var(--md-outlined-button-label-text-font, var(--md-sys-typescale-label-large-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-outlined-button-label-text-line-height, var(--md-sys-typescale-label-large-line-height, 1.25rem));--_label-text-size: var(--md-outlined-button-label-text-size, var(--md-sys-typescale-label-large-size, 0.875rem));--_label-text-weight: var(--md-outlined-button-label-text-weight, var(--md-sys-typescale-label-large-weight, var(--md-ref-typeface-weight-medium, 500)));--_outline-color: var(--md-outlined-button-outline-color, var(--md-sys-color-outline, #79747e));--_outline-width: var(--md-outlined-button-outline-width, 1px);--_pressed-label-text-color: var(--md-outlined-button-pressed-label-text-color, var(--md-sys-color-primary, #6750a4));--_pressed-outline-color: var(--md-outlined-button-pressed-outline-color, var(--md-sys-color-outline, #79747e));--_pressed-state-layer-color: var(--md-outlined-button-pressed-state-layer-color, var(--md-sys-color-primary, #6750a4));--_pressed-state-layer-opacity: var(--md-outlined-button-pressed-state-layer-opacity, 0.12);--_disabled-icon-color: var(--md-outlined-button-disabled-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-icon-opacity: var(--md-outlined-button-disabled-icon-opacity, 0.38);--_focus-icon-color: var(--md-outlined-button-focus-icon-color, var(--md-sys-color-primary, #6750a4));--_hover-icon-color: var(--md-outlined-button-hover-icon-color, var(--md-sys-color-primary, #6750a4));--_icon-color: var(--md-outlined-button-icon-color, var(--md-sys-color-primary, #6750a4));--_icon-size: var(--md-outlined-button-icon-size, 18px);--_pressed-icon-color: var(--md-outlined-button-pressed-icon-color, var(--md-sys-color-primary, #6750a4));--_container-shape-start-start: var(--md-outlined-button-container-shape-start-start, var(--md-outlined-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-start-end: var(--md-outlined-button-container-shape-start-end, var(--md-outlined-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-end: var(--md-outlined-button-container-shape-end-end, var(--md-outlined-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-start: var(--md-outlined-button-container-shape-end-start, var(--md-outlined-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_leading-space: var(--md-outlined-button-leading-space, 24px);--_trailing-space: var(--md-outlined-button-trailing-space, 24px);--_with-leading-icon-leading-space: var(--md-outlined-button-with-leading-icon-leading-space, 16px);--_with-leading-icon-trailing-space: var(--md-outlined-button-with-leading-icon-trailing-space, 24px);--_with-trailing-icon-leading-space: var(--md-outlined-button-with-trailing-icon-leading-space, 24px);--_with-trailing-icon-trailing-space: var(--md-outlined-button-with-trailing-icon-trailing-space, 16px);--_container-color: none;--_disabled-container-color: none;--_disabled-container-opacity: 0}.outline{inset:0;border-style:solid;position:absolute;box-sizing:border-box;border-color:var(--_outline-color);border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-start-radius:var(--_container-shape-end-start);border-end-end-radius:var(--_container-shape-end-end)}:host(:active) .outline{border-color:var(--_pressed-outline-color)}:host(:is([disabled],[soft-disabled])) .outline{border-color:var(--_disabled-outline-color);opacity:var(--_disabled-outline-opacity)}@media(forced-colors: active){:host(:is([disabled],[soft-disabled])) .background{border-color:GrayText}:host(:is([disabled],[soft-disabled])) .outline{opacity:1}}.outline,md-ripple{border-width:var(--_outline-width)}md-ripple{inline-size:calc(100% - 2*var(--_outline-width));block-size:calc(100% - 2*var(--_outline-width));border-style:solid;border-color:rgba(0,0,0,0)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/outlined-button.js
  var MdOutlinedButton = class MdOutlinedButton2 extends OutlinedButton {
  };
  MdOutlinedButton.styles = [styles25, styles27];
  if (!customElements.get("md-outlined-button")) {
    MdOutlinedButton = __decorate([
      t("md-outlined-button")
    ], MdOutlinedButton);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/text-button.js
  var TextButton = class extends Button {
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/internal/text-styles.js
  var styles28 = i`:host{--_container-height: var(--md-text-button-container-height, 40px);--_disabled-label-text-color: var(--md-text-button-disabled-label-text-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-label-text-opacity: var(--md-text-button-disabled-label-text-opacity, 0.38);--_focus-label-text-color: var(--md-text-button-focus-label-text-color, var(--md-sys-color-primary, #6750a4));--_hover-label-text-color: var(--md-text-button-hover-label-text-color, var(--md-sys-color-primary, #6750a4));--_hover-state-layer-color: var(--md-text-button-hover-state-layer-color, var(--md-sys-color-primary, #6750a4));--_hover-state-layer-opacity: var(--md-text-button-hover-state-layer-opacity, 0.08);--_label-text-color: var(--md-text-button-label-text-color, var(--md-sys-color-primary, #6750a4));--_label-text-font: var(--md-text-button-label-text-font, var(--md-sys-typescale-label-large-font, var(--md-ref-typeface-plain, Roboto)));--_label-text-line-height: var(--md-text-button-label-text-line-height, var(--md-sys-typescale-label-large-line-height, 1.25rem));--_label-text-size: var(--md-text-button-label-text-size, var(--md-sys-typescale-label-large-size, 0.875rem));--_label-text-weight: var(--md-text-button-label-text-weight, var(--md-sys-typescale-label-large-weight, var(--md-ref-typeface-weight-medium, 500)));--_pressed-label-text-color: var(--md-text-button-pressed-label-text-color, var(--md-sys-color-primary, #6750a4));--_pressed-state-layer-color: var(--md-text-button-pressed-state-layer-color, var(--md-sys-color-primary, #6750a4));--_pressed-state-layer-opacity: var(--md-text-button-pressed-state-layer-opacity, 0.12);--_disabled-icon-color: var(--md-text-button-disabled-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-icon-opacity: var(--md-text-button-disabled-icon-opacity, 0.38);--_focus-icon-color: var(--md-text-button-focus-icon-color, var(--md-sys-color-primary, #6750a4));--_hover-icon-color: var(--md-text-button-hover-icon-color, var(--md-sys-color-primary, #6750a4));--_icon-color: var(--md-text-button-icon-color, var(--md-sys-color-primary, #6750a4));--_icon-size: var(--md-text-button-icon-size, 18px);--_pressed-icon-color: var(--md-text-button-pressed-icon-color, var(--md-sys-color-primary, #6750a4));--_container-shape-start-start: var(--md-text-button-container-shape-start-start, var(--md-text-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-start-end: var(--md-text-button-container-shape-start-end, var(--md-text-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-end: var(--md-text-button-container-shape-end-end, var(--md-text-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_container-shape-end-start: var(--md-text-button-container-shape-end-start, var(--md-text-button-container-shape, var(--md-sys-shape-corner-full, 9999px)));--_leading-space: var(--md-text-button-leading-space, 12px);--_trailing-space: var(--md-text-button-trailing-space, 12px);--_with-leading-icon-leading-space: var(--md-text-button-with-leading-icon-leading-space, 12px);--_with-leading-icon-trailing-space: var(--md-text-button-with-leading-icon-trailing-space, 16px);--_with-trailing-icon-leading-space: var(--md-text-button-with-trailing-icon-leading-space, 16px);--_with-trailing-icon-trailing-space: var(--md-text-button-with-trailing-icon-trailing-space, 12px);--_container-color: none;--_disabled-container-color: none;--_disabled-container-opacity: 0}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/button/text-button.js
  var MdTextButton = class MdTextButton2 extends TextButton {
  };
  MdTextButton.styles = [styles25, styles28];
  if (!customElements.get("md-text-button")) {
    MdTextButton = __decorate([
      t("md-text-button")
    ], MdTextButton);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/controller/is-rtl.js
  function isRtl(el, shouldCheck = true) {
    return shouldCheck && getComputedStyle(el).getPropertyValue("direction").trim() === "rtl";
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/iconbutton/internal/icon-button.js
  var iconButtonBaseClass = mixinDelegatesAria(mixinElementInternals(i4));
  var IconButton = class extends iconButtonBaseClass {
    get name() {
      return this.getAttribute("name") ?? "";
    }
    set name(name) {
      this.setAttribute("name", name);
    }
    /**
     * The associated form element with which this element's value will submit.
     */
    get form() {
      return this[internals].form;
    }
    /**
     * The labels this element is associated with.
     */
    get labels() {
      return this[internals].labels;
    }
    constructor() {
      super();
      this.disabled = false;
      this.softDisabled = false;
      this.flipIconInRtl = false;
      this.href = "";
      this.download = "";
      this.target = "";
      this.ariaLabelSelected = "";
      this.toggle = false;
      this.selected = false;
      this.type = "submit";
      this.value = "";
      this.flipIcon = isRtl(this, this.flipIconInRtl);
      if (!o7) {
        this.addEventListener("click", this.handleClick.bind(this));
      }
    }
    willUpdate() {
      if (this.href) {
        this.disabled = false;
        this.softDisabled = false;
      }
    }
    render() {
      const tag = this.href ? i6`div` : i6`button`;
      const { ariaLabel, ariaHasPopup, ariaExpanded } = this;
      const hasToggledAriaLabel = ariaLabel && this.ariaLabelSelected;
      const ariaPressedValue = !this.toggle ? A : this.selected;
      let ariaLabelValue = A;
      if (!this.href) {
        ariaLabelValue = hasToggledAriaLabel && this.selected ? this.ariaLabelSelected : ariaLabel;
      }
      return u3`<${tag}
        class="icon-button ${e8(this.getRenderClasses())}"
        id="button"
        aria-label="${ariaLabelValue || A}"
        aria-haspopup="${!this.href && ariaHasPopup || A}"
        aria-expanded="${!this.href && ariaExpanded || A}"
        aria-pressed="${ariaPressedValue}"
        aria-disabled=${!this.href && this.softDisabled || A}
        ?disabled="${!this.href && this.disabled}"
        @click="${this.handleClickOnChild}">
        ${this.renderFocusRing()}
        ${this.renderRipple()}
        ${!this.selected ? this.renderIcon() : A}
        ${this.selected ? this.renderSelectedIcon() : A}
        ${this.href ? this.renderLink() : this.renderTouchTarget()}
  </${tag}>`;
    }
    renderLink() {
      const { ariaLabel } = this;
      return b2`
      <a
        class="link"
        id="link"
        href="${this.href}"
        download="${this.download || A}"
        target="${this.target || A}"
        aria-label="${ariaLabel || A}">
        ${this.renderTouchTarget()}
      </a>
    `;
    }
    getRenderClasses() {
      return {
        "flip-icon": this.flipIcon,
        "selected": this.toggle && this.selected
      };
    }
    renderIcon() {
      return b2`<span class="icon"><slot></slot></span>`;
    }
    renderSelectedIcon() {
      return b2`<span class="icon icon--selected"
      ><slot name="selected"><slot></slot></slot
    ></span>`;
    }
    renderTouchTarget() {
      return b2`<span class="touch"></span>`;
    }
    renderFocusRing() {
      return b2`<md-focus-ring
      part="focus-ring"
      for=${this.href ? "link" : "button"}></md-focus-ring>`;
    }
    renderRipple() {
      const isRippleDisabled = !this.href && (this.disabled || this.softDisabled);
      return b2`<md-ripple
      for=${this.href ? "link" : A}
      ?disabled="${isRippleDisabled}"></md-ripple>`;
    }
    connectedCallback() {
      this.flipIcon = isRtl(this, this.flipIconInRtl);
      super.connectedCallback();
    }
    /** Handles a click on this element. */
    handleClick(event) {
      if (!this.href && this.softDisabled) {
        event.stopImmediatePropagation();
        event.preventDefault();
        return;
      }
    }
    /**
     * Handles a click on the child <div> or <button> element within this
     * element's shadow DOM.
     */
    async handleClickOnChild(event) {
      await 0;
      if (!this.toggle || this.disabled || this.softDisabled || event.defaultPrevented) {
        return;
      }
      this.selected = !this.selected;
      this.dispatchEvent(new InputEvent("input", { bubbles: true, composed: true }));
      this.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };
  (() => {
    setupFormSubmitter(IconButton);
  })();
  IconButton.formAssociated = true;
  IconButton.shadowRootOptions = {
    mode: "open",
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], IconButton.prototype, "disabled", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "soft-disabled", reflect: true })
  ], IconButton.prototype, "softDisabled", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "flip-icon-in-rtl" })
  ], IconButton.prototype, "flipIconInRtl", void 0);
  __decorate([
    n3()
  ], IconButton.prototype, "href", void 0);
  __decorate([
    n3()
  ], IconButton.prototype, "download", void 0);
  __decorate([
    n3()
  ], IconButton.prototype, "target", void 0);
  __decorate([
    n3({ attribute: "aria-label-selected" })
  ], IconButton.prototype, "ariaLabelSelected", void 0);
  __decorate([
    n3({ type: Boolean })
  ], IconButton.prototype, "toggle", void 0);
  __decorate([
    n3({ type: Boolean, reflect: true })
  ], IconButton.prototype, "selected", void 0);
  __decorate([
    n3()
  ], IconButton.prototype, "type", void 0);
  __decorate([
    n3({ reflect: true })
  ], IconButton.prototype, "value", void 0);
  __decorate([
    r4()
  ], IconButton.prototype, "flipIcon", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/iconbutton/internal/shared-styles.js
  var styles29 = i`:host{display:inline-flex;outline:none;-webkit-tap-highlight-color:rgba(0,0,0,0);height:var(--_container-height);width:var(--_container-width);justify-content:center}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--_container-height))/2) max(0px,(48px - var(--_container-width))/2)}md-focus-ring{--md-focus-ring-shape-start-start: var(--_container-shape-start-start);--md-focus-ring-shape-start-end: var(--_container-shape-start-end);--md-focus-ring-shape-end-end: var(--_container-shape-end-end);--md-focus-ring-shape-end-start: var(--_container-shape-end-start)}:host(:is([disabled],[soft-disabled])){pointer-events:none}.icon-button{place-items:center;background:none;border:none;box-sizing:border-box;cursor:pointer;display:flex;place-content:center;outline:none;padding:0;position:relative;text-decoration:none;user-select:none;z-index:0;flex:1;border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-start-radius:var(--_container-shape-end-start);border-end-end-radius:var(--_container-shape-end-end)}.icon ::slotted(*){font-size:var(--_icon-size);height:var(--_icon-size);width:var(--_icon-size);font-weight:inherit}md-ripple{z-index:-1;border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-start-radius:var(--_container-shape-end-start);border-end-end-radius:var(--_container-shape-end-end)}.flip-icon .icon{transform:scaleX(-1)}.icon{display:inline-flex}.link{display:grid;height:100%;outline:none;place-items:center;position:absolute;width:100%}.touch{position:absolute;height:max(48px,100%);width:max(48px,100%)}:host([touch-target=none]) .touch{display:none}@media(forced-colors: active){:host(:is([disabled],[soft-disabled])){--_disabled-icon-color: GrayText;--_disabled-icon-opacity: 1}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/iconbutton/internal/standard-styles.js
  var styles30 = i`:host{--_disabled-icon-color: var(--md-icon-button-disabled-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-icon-opacity: var(--md-icon-button-disabled-icon-opacity, 0.38);--_icon-size: var(--md-icon-button-icon-size, 24px);--_selected-focus-icon-color: var(--md-icon-button-selected-focus-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-hover-icon-color: var(--md-icon-button-selected-hover-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-hover-state-layer-color: var(--md-icon-button-selected-hover-state-layer-color, var(--md-sys-color-primary, #6750a4));--_selected-hover-state-layer-opacity: var(--md-icon-button-selected-hover-state-layer-opacity, 0.08);--_selected-icon-color: var(--md-icon-button-selected-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-pressed-icon-color: var(--md-icon-button-selected-pressed-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-pressed-state-layer-color: var(--md-icon-button-selected-pressed-state-layer-color, var(--md-sys-color-primary, #6750a4));--_selected-pressed-state-layer-opacity: var(--md-icon-button-selected-pressed-state-layer-opacity, 0.12);--_state-layer-height: var(--md-icon-button-state-layer-height, 40px);--_state-layer-shape: var(--md-icon-button-state-layer-shape, var(--md-sys-shape-corner-full, 9999px));--_state-layer-width: var(--md-icon-button-state-layer-width, 40px);--_focus-icon-color: var(--md-icon-button-focus-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-icon-color: var(--md-icon-button-hover-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-state-layer-color: var(--md-icon-button-hover-state-layer-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-state-layer-opacity: var(--md-icon-button-hover-state-layer-opacity, 0.08);--_icon-color: var(--md-icon-button-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-icon-color: var(--md-icon-button-pressed-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-state-layer-color: var(--md-icon-button-pressed-state-layer-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-state-layer-opacity: var(--md-icon-button-pressed-state-layer-opacity, 0.12);--_container-shape-start-start: 0;--_container-shape-start-end: 0;--_container-shape-end-end: 0;--_container-shape-end-start: 0;--_container-height: 0;--_container-width: 0;height:var(--_state-layer-height);width:var(--_state-layer-width)}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--_state-layer-height))/2) max(0px,(48px - var(--_state-layer-width))/2)}md-focus-ring{--md-focus-ring-shape-start-start: var(--_state-layer-shape);--md-focus-ring-shape-start-end: var(--_state-layer-shape);--md-focus-ring-shape-end-end: var(--_state-layer-shape);--md-focus-ring-shape-end-start: var(--_state-layer-shape)}.standard{background-color:rgba(0,0,0,0);color:var(--_icon-color);--md-ripple-hover-color: var(--_hover-state-layer-color);--md-ripple-hover-opacity: var(--_hover-state-layer-opacity);--md-ripple-pressed-color: var(--_pressed-state-layer-color);--md-ripple-pressed-opacity: var(--_pressed-state-layer-opacity)}.standard:hover{color:var(--_hover-icon-color)}.standard:focus{color:var(--_focus-icon-color)}.standard:active{color:var(--_pressed-icon-color)}.standard:is(:disabled,[aria-disabled=true]){color:var(--_disabled-icon-color)}md-ripple{border-radius:var(--_state-layer-shape)}.standard:is(:disabled,[aria-disabled=true]){opacity:var(--_disabled-icon-opacity)}.selected:not(:disabled,[aria-disabled=true]){color:var(--_selected-icon-color)}.selected:not(:disabled,[aria-disabled=true]):hover{color:var(--_selected-hover-icon-color)}.selected:not(:disabled,[aria-disabled=true]):focus{color:var(--_selected-focus-icon-color)}.selected:not(:disabled,[aria-disabled=true]):active{color:var(--_selected-pressed-icon-color)}.selected{--md-ripple-hover-color: var(--_selected-hover-state-layer-color);--md-ripple-hover-opacity: var(--_selected-hover-state-layer-opacity);--md-ripple-pressed-color: var(--_selected-pressed-state-layer-color);--md-ripple-pressed-opacity: var(--_selected-pressed-state-layer-opacity)}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/iconbutton/icon-button.js
  var MdIconButton = class MdIconButton2 extends IconButton {
    getRenderClasses() {
      return {
        ...super.getRenderClasses(),
        "standard": true
      };
    }
  };
  MdIconButton.styles = [styles29, styles30];
  if (!customElements.get("md-icon-button")) {
    MdIconButton = __decorate([
      t("md-icon-button")
    ], MdIconButton);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/labs/behaviors/validators/checkbox-validator.js
  var CheckboxValidator = class extends Validator {
    computeValidity(state) {
      if (!this.checkboxControl) {
        this.checkboxControl = document.createElement("input");
        this.checkboxControl.type = "checkbox";
      }
      this.checkboxControl.checked = state.checked;
      this.checkboxControl.required = state.required;
      return {
        validity: this.checkboxControl.validity,
        validationMessage: this.checkboxControl.validationMessage
      };
    }
    equals(prev, next) {
      return prev.checked === next.checked && prev.required === next.required;
    }
    copy({ checked, required }) {
      return { checked, required };
    }
  };

  // custom_components/smart_agent/frontend/node_modules/@material/web/checkbox/internal/checkbox.js
  var checkboxBaseClass = mixinDelegatesAria(mixinConstraintValidation(mixinFormAssociated(mixinElementInternals(i4))));
  var Checkbox = class extends checkboxBaseClass {
    constructor() {
      super();
      this.checked = false;
      this.indeterminate = false;
      this.required = false;
      this.value = "on";
      this.prevChecked = false;
      this.prevDisabled = false;
      this.prevIndeterminate = false;
      if (!o7) {
        this.addEventListener("click", (event) => {
          if (!isActivationClick(event) || !this.input) {
            return;
          }
          this.focus();
          dispatchActivationClick(this.input);
        });
      }
    }
    update(changed) {
      if (changed.has("checked") || changed.has("disabled") || changed.has("indeterminate")) {
        this.prevChecked = changed.get("checked") ?? this.checked;
        this.prevDisabled = changed.get("disabled") ?? this.disabled;
        this.prevIndeterminate = changed.get("indeterminate") ?? this.indeterminate;
      }
      super.update(changed);
    }
    render() {
      const prevNone = !this.prevChecked && !this.prevIndeterminate;
      const prevChecked = this.prevChecked && !this.prevIndeterminate;
      const prevIndeterminate = this.prevIndeterminate;
      const isChecked = this.checked && !this.indeterminate;
      const isIndeterminate = this.indeterminate;
      const containerClasses = e8({
        "disabled": this.disabled,
        "selected": isChecked || isIndeterminate,
        "unselected": !isChecked && !isIndeterminate,
        "checked": isChecked,
        "indeterminate": isIndeterminate,
        "prev-unselected": prevNone,
        "prev-checked": prevChecked,
        "prev-indeterminate": prevIndeterminate,
        "prev-disabled": this.prevDisabled
      });
      const { ariaLabel, ariaInvalid } = this;
      return b2`
      <div class="container ${containerClasses}">
        <input
          type="checkbox"
          id="input"
          aria-checked=${isIndeterminate ? "mixed" : A}
          aria-label=${ariaLabel || A}
          aria-invalid=${ariaInvalid || A}
          ?disabled=${this.disabled}
          ?required=${this.required}
          .indeterminate=${this.indeterminate}
          .checked=${this.checked}
          @input=${this.handleInput}
          @change=${this.handleChange} />

        <div class="outline"></div>
        <div class="background"></div>
        <md-focus-ring part="focus-ring" for="input"></md-focus-ring>
        <md-ripple for="input" ?disabled=${this.disabled}></md-ripple>
        <svg class="icon" viewBox="0 0 18 18" aria-hidden="true">
          <rect class="mark short" />
          <rect class="mark long" />
        </svg>
      </div>
    `;
    }
    handleInput(event) {
      const target = event.target;
      this.checked = target.checked;
      this.indeterminate = target.indeterminate;
    }
    handleChange(event) {
      redispatchEvent(this, event);
    }
    [getFormValue]() {
      if (!this.checked || this.indeterminate) {
        return null;
      }
      return this.value;
    }
    [getFormState]() {
      return String(this.checked);
    }
    formResetCallback() {
      this.checked = this.hasAttribute("checked");
    }
    formStateRestoreCallback(state) {
      this.checked = state === "true";
    }
    [createValidator]() {
      return new CheckboxValidator(() => this);
    }
    [getValidityAnchor]() {
      return this.input;
    }
  };
  Checkbox.shadowRootOptions = {
    ...i4.shadowRootOptions,
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean })
  ], Checkbox.prototype, "checked", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Checkbox.prototype, "indeterminate", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Checkbox.prototype, "required", void 0);
  __decorate([
    n3()
  ], Checkbox.prototype, "value", void 0);
  __decorate([
    r4()
  ], Checkbox.prototype, "prevChecked", void 0);
  __decorate([
    r4()
  ], Checkbox.prototype, "prevDisabled", void 0);
  __decorate([
    r4()
  ], Checkbox.prototype, "prevIndeterminate", void 0);
  __decorate([
    e4("input")
  ], Checkbox.prototype, "input", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/checkbox/internal/checkbox-styles.js
  var styles31 = i`:host{border-start-start-radius:var(--md-checkbox-container-shape-start-start, var(--md-checkbox-container-shape, 2px));border-start-end-radius:var(--md-checkbox-container-shape-start-end, var(--md-checkbox-container-shape, 2px));border-end-end-radius:var(--md-checkbox-container-shape-end-end, var(--md-checkbox-container-shape, 2px));border-end-start-radius:var(--md-checkbox-container-shape-end-start, var(--md-checkbox-container-shape, 2px));display:inline-flex;height:var(--md-checkbox-container-size, 18px);position:relative;vertical-align:top;width:var(--md-checkbox-container-size, 18px);-webkit-tap-highlight-color:rgba(0,0,0,0);cursor:pointer}:host([disabled]){cursor:default}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--md-checkbox-container-size, 18px))/2)}md-focus-ring{height:44px;inset:unset;width:44px}input{appearance:none;height:48px;margin:0;opacity:0;outline:none;position:absolute;width:48px;z-index:1;cursor:inherit}:host([touch-target=none]) input{height:100%;width:100%}.container{border-radius:inherit;display:flex;height:100%;place-content:center;place-items:center;position:relative;width:100%}.outline,.background,.icon{inset:0;position:absolute}.outline,.background{border-radius:inherit}.outline{border-color:var(--md-checkbox-outline-color, var(--md-sys-color-on-surface-variant, #49454f));border-style:solid;border-width:var(--md-checkbox-outline-width, 2px);box-sizing:border-box}.background{background-color:var(--md-checkbox-selected-container-color, var(--md-sys-color-primary, #6750a4))}.background,.icon{opacity:0;transition-duration:150ms,50ms;transition-property:transform,opacity;transition-timing-function:cubic-bezier(0.3, 0, 0.8, 0.15),linear;transform:scale(0.6)}:where(.selected) :is(.background,.icon){opacity:1;transition-duration:350ms,50ms;transition-timing-function:cubic-bezier(0.05, 0.7, 0.1, 1),linear;transform:scale(1)}md-ripple{border-radius:var(--md-checkbox-state-layer-shape, var(--md-sys-shape-corner-full, 9999px));height:var(--md-checkbox-state-layer-size, 40px);inset:unset;width:var(--md-checkbox-state-layer-size, 40px);--md-ripple-hover-color: var(--md-checkbox-hover-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-hover-opacity: var(--md-checkbox-hover-state-layer-opacity, 0.08);--md-ripple-pressed-color: var(--md-checkbox-pressed-state-layer-color, var(--md-sys-color-primary, #6750a4));--md-ripple-pressed-opacity: var(--md-checkbox-pressed-state-layer-opacity, 0.12)}.selected md-ripple{--md-ripple-hover-color: var(--md-checkbox-selected-hover-state-layer-color, var(--md-sys-color-primary, #6750a4));--md-ripple-hover-opacity: var(--md-checkbox-selected-hover-state-layer-opacity, 0.08);--md-ripple-pressed-color: var(--md-checkbox-selected-pressed-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-pressed-opacity: var(--md-checkbox-selected-pressed-state-layer-opacity, 0.12)}.icon{fill:var(--md-checkbox-selected-icon-color, var(--md-sys-color-on-primary, #fff));height:var(--md-checkbox-icon-size, 18px);width:var(--md-checkbox-icon-size, 18px)}.mark.short{height:2px;transition-property:transform,height;width:2px}.mark.long{height:2px;transition-property:transform,width;width:10px}.mark{animation-duration:150ms;animation-timing-function:cubic-bezier(0.3, 0, 0.8, 0.15);transition-duration:150ms;transition-timing-function:cubic-bezier(0.3, 0, 0.8, 0.15)}.selected .mark{animation-duration:350ms;animation-timing-function:cubic-bezier(0.05, 0.7, 0.1, 1);transition-duration:350ms;transition-timing-function:cubic-bezier(0.05, 0.7, 0.1, 1)}.checked .mark,.prev-checked.unselected .mark{transform:scaleY(-1) translate(7px, -14px) rotate(45deg)}.checked .mark.short,.prev-checked.unselected .mark.short{height:5.6568542495px}.checked .mark.long,.prev-checked.unselected .mark.long{width:11.313708499px}.indeterminate .mark,.prev-indeterminate.unselected .mark{transform:scaleY(-1) translate(4px, -10px) rotate(0deg)}.prev-unselected .mark{transition-property:none}.prev-unselected.checked .mark.long{animation-name:prev-unselected-to-checked}@keyframes prev-unselected-to-checked{from{width:0}}:where(:hover) .outline{border-color:var(--md-checkbox-hover-outline-color, var(--md-sys-color-on-surface, #1d1b20));border-width:var(--md-checkbox-hover-outline-width, 2px)}:where(:hover) .background{background:var(--md-checkbox-selected-hover-container-color, var(--md-sys-color-primary, #6750a4))}:where(:hover) .icon{fill:var(--md-checkbox-selected-hover-icon-color, var(--md-sys-color-on-primary, #fff))}:where(:focus-within) .outline{border-color:var(--md-checkbox-focus-outline-color, var(--md-sys-color-on-surface, #1d1b20));border-width:var(--md-checkbox-focus-outline-width, 2px)}:where(:focus-within) .background{background:var(--md-checkbox-selected-focus-container-color, var(--md-sys-color-primary, #6750a4))}:where(:focus-within) .icon{fill:var(--md-checkbox-selected-focus-icon-color, var(--md-sys-color-on-primary, #fff))}:where(:active) .outline{border-color:var(--md-checkbox-pressed-outline-color, var(--md-sys-color-on-surface, #1d1b20));border-width:var(--md-checkbox-pressed-outline-width, 2px)}:where(:active) .background{background:var(--md-checkbox-selected-pressed-container-color, var(--md-sys-color-primary, #6750a4))}:where(:active) .icon{fill:var(--md-checkbox-selected-pressed-icon-color, var(--md-sys-color-on-primary, #fff))}:where(.disabled,.prev-disabled) :is(.background,.icon,.mark){animation-duration:0s;transition-duration:0s}:where(.disabled) .outline{border-color:var(--md-checkbox-disabled-outline-color, var(--md-sys-color-on-surface, #1d1b20));border-width:var(--md-checkbox-disabled-outline-width, 2px);opacity:var(--md-checkbox-disabled-container-opacity, 0.38)}:where(.selected.disabled) .outline{visibility:hidden}:where(.selected.disabled) .background{background:var(--md-checkbox-selected-disabled-container-color, var(--md-sys-color-on-surface, #1d1b20));opacity:var(--md-checkbox-selected-disabled-container-opacity, 0.38)}:where(.disabled) .icon{fill:var(--md-checkbox-selected-disabled-icon-color, var(--md-sys-color-surface, #fef7ff))}@media(forced-colors: active){.background{background-color:CanvasText}.selected.disabled .background{background-color:GrayText;opacity:1}.outline{border-color:CanvasText}.disabled .outline{border-color:GrayText;opacity:1}.icon{fill:Canvas}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/checkbox/checkbox.js
  var MdCheckbox = class MdCheckbox2 extends Checkbox {
  };
  MdCheckbox.styles = [styles31];
  if (!customElements.get("md-checkbox")) {
    MdCheckbox = __decorate([
      t("md-checkbox")
    ], MdCheckbox);
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/internal/events/dispatch-hooks.js
  var dispatchHooks = Symbol("dispatchHooks");
  function afterDispatch(event, callback) {
    const hooks = event[dispatchHooks];
    if (!hooks) {
      throw new Error(`'${event.type}' event needs setupDispatchHooks().`);
    }
    hooks.addEventListener("after", callback);
  }
  var ELEMENT_DISPATCH_HOOK_TYPES = /* @__PURE__ */ new WeakMap();
  function setupDispatchHooks(element, ...eventTypes) {
    let typesAlreadySetUp = ELEMENT_DISPATCH_HOOK_TYPES.get(element);
    if (!typesAlreadySetUp) {
      typesAlreadySetUp = /* @__PURE__ */ new Set();
      ELEMENT_DISPATCH_HOOK_TYPES.set(element, typesAlreadySetUp);
    }
    for (const eventType of eventTypes) {
      if (typesAlreadySetUp.has(eventType)) {
        continue;
      }
      let isRedispatching = false;
      element.addEventListener(eventType, (event) => {
        if (isRedispatching) {
          return;
        }
        event.stopImmediatePropagation();
        const eventCopy = Reflect.construct(event.constructor, [
          event.type,
          event
        ]);
        const hooks = new EventTarget();
        eventCopy[dispatchHooks] = hooks;
        isRedispatching = true;
        const dispatched = element.dispatchEvent(eventCopy);
        isRedispatching = false;
        if (!dispatched) {
          event.preventDefault();
        }
        hooks.dispatchEvent(new Event("after"));
      }, {
        // Ensure this listener runs before other listeners.
        // `setupDispatchHooks()` should be called in constructors to also
        // ensure they run before any other externally-added capture listeners.
        capture: true
      });
      typesAlreadySetUp.add(eventType);
    }
  }

  // custom_components/smart_agent/frontend/node_modules/@material/web/switch/internal/switch.js
  var switchBaseClass = mixinDelegatesAria(mixinConstraintValidation(mixinFormAssociated(mixinElementInternals(i4))));
  var Switch = class extends switchBaseClass {
    constructor() {
      super();
      this.selected = false;
      this.icons = false;
      this.showOnlySelectedIcon = false;
      this.required = false;
      this.value = "on";
      if (o7) {
        return;
      }
      this.addEventListener("click", (event) => {
        if (!isActivationClick(event) || !this.input) {
          return;
        }
        this.focus();
        dispatchActivationClick(this.input);
      });
      setupDispatchHooks(this, "keydown");
      this.addEventListener("keydown", (event) => {
        afterDispatch(event, () => {
          const ignoreEvent = event.defaultPrevented || event.key !== "Enter";
          if (ignoreEvent || this.disabled || !this.input) {
            return;
          }
          this.input.click();
        });
      });
    }
    render() {
      return b2`
      <div class="switch ${e8(this.getRenderClasses())}">
        <input
          id="switch"
          class="touch"
          type="checkbox"
          role="switch"
          aria-label=${this.ariaLabel || A}
          ?checked=${this.selected}
          ?disabled=${this.disabled}
          ?required=${this.required}
          @input=${this.handleInput}
          @change=${this.handleChange} />

        <md-focus-ring part="focus-ring" for="switch"></md-focus-ring>
        <span class="track"> ${this.renderHandle()} </span>
      </div>
    `;
    }
    getRenderClasses() {
      return {
        "selected": this.selected,
        "unselected": !this.selected,
        "disabled": this.disabled
      };
    }
    renderHandle() {
      const classes = {
        "with-icon": this.showOnlySelectedIcon ? this.selected : this.icons
      };
      return b2`
      ${this.renderTouchTarget()}
      <span class="handle-container">
        <md-ripple for="switch" ?disabled="${this.disabled}"></md-ripple>
        <span class="handle ${e8(classes)}">
          ${this.shouldShowIcons() ? this.renderIcons() : b2``}
        </span>
      </span>
    `;
    }
    renderIcons() {
      return b2`
      <div class="icons">
        ${this.renderOnIcon()}
        ${this.showOnlySelectedIcon ? b2`` : this.renderOffIcon()}
      </div>
    `;
    }
    /**
     * https://fonts.google.com/icons?selected=Material%20Symbols%20Outlined%3Acheck%3AFILL%400%3Bwght%40500%3BGRAD%400%3Bopsz%4024
     */
    renderOnIcon() {
      return b2`
      <slot class="icon icon--on" name="on-icon">
        <svg viewBox="0 0 24 24">
          <path
            d="M9.55 18.2 3.65 12.3 5.275 10.675 9.55 14.95 18.725 5.775 20.35 7.4Z" />
        </svg>
      </slot>
    `;
    }
    /**
     * https://fonts.google.com/icons?selected=Material%20Symbols%20Outlined%3Aclose%3AFILL%400%3Bwght%40500%3BGRAD%400%3Bopsz%4024
     */
    renderOffIcon() {
      return b2`
      <slot class="icon icon--off" name="off-icon">
        <svg viewBox="0 0 24 24">
          <path
            d="M6.4 19.2 4.8 17.6 10.4 12 4.8 6.4 6.4 4.8 12 10.4 17.6 4.8 19.2 6.4 13.6 12 19.2 17.6 17.6 19.2 12 13.6Z" />
        </svg>
      </slot>
    `;
    }
    renderTouchTarget() {
      return b2`<span class="touch"></span>`;
    }
    shouldShowIcons() {
      return this.icons || this.showOnlySelectedIcon;
    }
    handleInput(event) {
      const target = event.target;
      this.selected = target.checked;
    }
    handleChange(event) {
      redispatchEvent(this, event);
    }
    [getFormValue]() {
      return this.selected ? this.value : null;
    }
    [getFormState]() {
      return String(this.selected);
    }
    formResetCallback() {
      this.selected = this.hasAttribute("selected");
    }
    formStateRestoreCallback(state) {
      this.selected = state === "true";
    }
    [createValidator]() {
      return new CheckboxValidator(() => ({
        checked: this.selected,
        required: this.required
      }));
    }
    [getValidityAnchor]() {
      return this.input;
    }
  };
  Switch.shadowRootOptions = {
    mode: "open",
    delegatesFocus: true
  };
  __decorate([
    n3({ type: Boolean })
  ], Switch.prototype, "selected", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Switch.prototype, "icons", void 0);
  __decorate([
    n3({ type: Boolean, attribute: "show-only-selected-icon" })
  ], Switch.prototype, "showOnlySelectedIcon", void 0);
  __decorate([
    n3({ type: Boolean })
  ], Switch.prototype, "required", void 0);
  __decorate([
    n3()
  ], Switch.prototype, "value", void 0);
  __decorate([
    e4("input")
  ], Switch.prototype, "input", void 0);

  // custom_components/smart_agent/frontend/node_modules/@material/web/switch/internal/switch-styles.js
  var styles32 = i`@layer styles, hcm;@layer styles{:host{display:inline-flex;outline:none;vertical-align:top;-webkit-tap-highlight-color:rgba(0,0,0,0);cursor:pointer}:host([disabled]){cursor:default}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--md-switch-track-height, 32px))/2) 0px}md-focus-ring{--md-focus-ring-shape-start-start: var(--md-switch-track-shape-start-start, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)));--md-focus-ring-shape-start-end: var(--md-switch-track-shape-start-end, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)));--md-focus-ring-shape-end-end: var(--md-switch-track-shape-end-end, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)));--md-focus-ring-shape-end-start: var(--md-switch-track-shape-end-start, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)))}.switch{align-items:center;display:inline-flex;flex-shrink:0;position:relative;width:var(--md-switch-track-width, 52px);height:var(--md-switch-track-height, 32px);border-start-start-radius:var(--md-switch-track-shape-start-start, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)));border-start-end-radius:var(--md-switch-track-shape-start-end, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)));border-end-end-radius:var(--md-switch-track-shape-end-end, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)));border-end-start-radius:var(--md-switch-track-shape-end-start, var(--md-switch-track-shape, var(--md-sys-shape-corner-full, 9999px)))}input{appearance:none;height:max(100%,var(--md-switch-touch-target-size, 48px));outline:none;margin:0;position:absolute;width:max(100%,var(--md-switch-touch-target-size, 48px));z-index:1;cursor:inherit;top:50%;left:50%;transform:translate(-50%, -50%)}:host([touch-target=none]) input{display:none}}@layer styles{.track{position:absolute;width:100%;height:100%;box-sizing:border-box;border-radius:inherit;display:flex;justify-content:center;align-items:center}.track::before{content:"";display:flex;position:absolute;height:100%;width:100%;border-radius:inherit;box-sizing:border-box;transition-property:opacity,background-color;transition-timing-function:linear;transition-duration:67ms}.disabled .track{background-color:rgba(0,0,0,0);border-color:rgba(0,0,0,0)}.disabled .track::before,.disabled .track::after{transition:none;opacity:var(--md-switch-disabled-track-opacity, 0.12)}.disabled .track::before{background-clip:content-box}.selected .track::before{background-color:var(--md-switch-selected-track-color, var(--md-sys-color-primary, #6750a4))}.selected:hover .track::before{background-color:var(--md-switch-selected-hover-track-color, var(--md-sys-color-primary, #6750a4))}.selected:focus-within .track::before{background-color:var(--md-switch-selected-focus-track-color, var(--md-sys-color-primary, #6750a4))}.selected:active .track::before{background-color:var(--md-switch-selected-pressed-track-color, var(--md-sys-color-primary, #6750a4))}.selected.disabled .track{background-clip:border-box}.selected.disabled .track::before{background-color:var(--md-switch-disabled-selected-track-color, var(--md-sys-color-on-surface, #1d1b20))}.unselected .track::before{background-color:var(--md-switch-track-color, var(--md-sys-color-surface-container-highest, #e6e0e9));border-color:var(--md-switch-track-outline-color, var(--md-sys-color-outline, #79747e));border-style:solid;border-width:var(--md-switch-track-outline-width, 2px)}.unselected:hover .track::before{background-color:var(--md-switch-hover-track-color, var(--md-sys-color-surface-container-highest, #e6e0e9));border-color:var(--md-switch-hover-track-outline-color, var(--md-sys-color-outline, #79747e))}.unselected:focus-visible .track::before{background-color:var(--md-switch-focus-track-color, var(--md-sys-color-surface-container-highest, #e6e0e9));border-color:var(--md-switch-focus-track-outline-color, var(--md-sys-color-outline, #79747e))}.unselected:active .track::before{background-color:var(--md-switch-pressed-track-color, var(--md-sys-color-surface-container-highest, #e6e0e9));border-color:var(--md-switch-pressed-track-outline-color, var(--md-sys-color-outline, #79747e))}.unselected.disabled .track::before{background-color:var(--md-switch-disabled-track-color, var(--md-sys-color-surface-container-highest, #e6e0e9));border-color:var(--md-switch-disabled-track-outline-color, var(--md-sys-color-on-surface, #1d1b20))}}@layer hcm{@media(forced-colors: active){.selected .track::before{background:ButtonText;border-color:ButtonText}.disabled .track::before{border-color:GrayText;opacity:1}.disabled.selected .track::before{background:GrayText}}}@layer styles{.handle-container{display:flex;place-content:center;place-items:center;position:relative;transition:margin 300ms cubic-bezier(0.175, 0.885, 0.32, 1.275)}.selected .handle-container{margin-inline-start:calc(var(--md-switch-track-width, 52px) - var(--md-switch-track-height, 32px))}.unselected .handle-container{margin-inline-end:calc(var(--md-switch-track-width, 52px) - var(--md-switch-track-height, 32px))}.disabled .handle-container{transition:none}.handle{border-start-start-radius:var(--md-switch-handle-shape-start-start, var(--md-switch-handle-shape, var(--md-sys-shape-corner-full, 9999px)));border-start-end-radius:var(--md-switch-handle-shape-start-end, var(--md-switch-handle-shape, var(--md-sys-shape-corner-full, 9999px)));border-end-end-radius:var(--md-switch-handle-shape-end-end, var(--md-switch-handle-shape, var(--md-sys-shape-corner-full, 9999px)));border-end-start-radius:var(--md-switch-handle-shape-end-start, var(--md-switch-handle-shape, var(--md-sys-shape-corner-full, 9999px)));height:var(--md-switch-handle-height, 16px);width:var(--md-switch-handle-width, 16px);transform-origin:center;transition-property:height,width;transition-duration:250ms,250ms;transition-timing-function:cubic-bezier(0.2, 0, 0, 1),cubic-bezier(0.2, 0, 0, 1);z-index:0}.handle::before{content:"";display:flex;inset:0;position:absolute;border-radius:inherit;box-sizing:border-box;transition:background-color 67ms linear}.disabled .handle,.disabled .handle::before{transition:none}.selected .handle{height:var(--md-switch-selected-handle-height, 24px);width:var(--md-switch-selected-handle-width, 24px)}.handle.with-icon{height:var(--md-switch-with-icon-handle-height, 24px);width:var(--md-switch-with-icon-handle-width, 24px)}.selected:not(.disabled):active .handle,.unselected:not(.disabled):active .handle{height:var(--md-switch-pressed-handle-height, 28px);width:var(--md-switch-pressed-handle-width, 28px);transition-timing-function:linear;transition-duration:100ms}.selected .handle::before{background-color:var(--md-switch-selected-handle-color, var(--md-sys-color-on-primary, #fff))}.selected:hover .handle::before{background-color:var(--md-switch-selected-hover-handle-color, var(--md-sys-color-primary-container, #eaddff))}.selected:focus-within .handle::before{background-color:var(--md-switch-selected-focus-handle-color, var(--md-sys-color-primary-container, #eaddff))}.selected:active .handle::before{background-color:var(--md-switch-selected-pressed-handle-color, var(--md-sys-color-primary-container, #eaddff))}.selected.disabled .handle::before{background-color:var(--md-switch-disabled-selected-handle-color, var(--md-sys-color-surface, #fef7ff));opacity:var(--md-switch-disabled-selected-handle-opacity, 1)}.unselected .handle::before{background-color:var(--md-switch-handle-color, var(--md-sys-color-outline, #79747e))}.unselected:hover .handle::before{background-color:var(--md-switch-hover-handle-color, var(--md-sys-color-on-surface-variant, #49454f))}.unselected:focus-within .handle::before{background-color:var(--md-switch-focus-handle-color, var(--md-sys-color-on-surface-variant, #49454f))}.unselected:active .handle::before{background-color:var(--md-switch-pressed-handle-color, var(--md-sys-color-on-surface-variant, #49454f))}.unselected.disabled .handle::before{background-color:var(--md-switch-disabled-handle-color, var(--md-sys-color-on-surface, #1d1b20));opacity:var(--md-switch-disabled-handle-opacity, 0.38)}md-ripple{border-radius:var(--md-switch-state-layer-shape, var(--md-sys-shape-corner-full, 9999px));height:var(--md-switch-state-layer-size, 40px);inset:unset;width:var(--md-switch-state-layer-size, 40px)}.selected md-ripple{--md-ripple-hover-color: var(--md-switch-selected-hover-state-layer-color, var(--md-sys-color-primary, #6750a4));--md-ripple-pressed-color: var(--md-switch-selected-pressed-state-layer-color, var(--md-sys-color-primary, #6750a4));--md-ripple-hover-opacity: var(--md-switch-selected-hover-state-layer-opacity, 0.08);--md-ripple-pressed-opacity: var(--md-switch-selected-pressed-state-layer-opacity, 0.12)}.unselected md-ripple{--md-ripple-hover-color: var(--md-switch-hover-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-pressed-color: var(--md-switch-pressed-state-layer-color, var(--md-sys-color-on-surface, #1d1b20));--md-ripple-hover-opacity: var(--md-switch-hover-state-layer-opacity, 0.08);--md-ripple-pressed-opacity: var(--md-switch-pressed-state-layer-opacity, 0.12)}}@layer hcm{@media(forced-colors: active){.unselected .handle::before{background:ButtonText}.disabled .handle::before{opacity:1}.disabled.unselected .handle::before{background:GrayText}}}@layer styles{.icons{position:relative;height:100%;width:100%}.icon{position:absolute;inset:0;margin:auto;display:flex;align-items:center;justify-content:center;fill:currentColor;transition:fill 67ms linear,opacity 33ms linear,transform 167ms cubic-bezier(0.2, 0, 0, 1);opacity:0}.disabled .icon{transition:none}.selected .icon--on,.unselected .icon--off{opacity:1}.unselected .handle:not(.with-icon) .icon--on{transform:rotate(-45deg)}.icon--off{width:var(--md-switch-icon-size, 16px);height:var(--md-switch-icon-size, 16px);color:var(--md-switch-icon-color, var(--md-sys-color-surface-container-highest, #e6e0e9))}.unselected:hover .icon--off{color:var(--md-switch-hover-icon-color, var(--md-sys-color-surface-container-highest, #e6e0e9))}.unselected:focus-within .icon--off{color:var(--md-switch-focus-icon-color, var(--md-sys-color-surface-container-highest, #e6e0e9))}.unselected:active .icon--off{color:var(--md-switch-pressed-icon-color, var(--md-sys-color-surface-container-highest, #e6e0e9))}.unselected.disabled .icon--off{color:var(--md-switch-disabled-icon-color, var(--md-sys-color-surface-container-highest, #e6e0e9));opacity:var(--md-switch-disabled-icon-opacity, 0.38)}.icon--on{width:var(--md-switch-selected-icon-size, 16px);height:var(--md-switch-selected-icon-size, 16px);color:var(--md-switch-selected-icon-color, var(--md-sys-color-on-primary-container, #21005d))}.selected:hover .icon--on{color:var(--md-switch-selected-hover-icon-color, var(--md-sys-color-on-primary-container, #21005d))}.selected:focus-within .icon--on{color:var(--md-switch-selected-focus-icon-color, var(--md-sys-color-on-primary-container, #21005d))}.selected:active .icon--on{color:var(--md-switch-selected-pressed-icon-color, var(--md-sys-color-on-primary-container, #21005d))}.selected.disabled .icon--on{color:var(--md-switch-disabled-selected-icon-color, var(--md-sys-color-on-surface, #1d1b20));opacity:var(--md-switch-disabled-selected-icon-opacity, 0.38)}}@layer hcm{@media(forced-colors: active){.icon--off{fill:Canvas}.icon--on{fill:ButtonText}.disabled.unselected .icon--off,.disabled.selected .icon--on{opacity:1}.disabled .icon--on{fill:GrayText}}}
`;

  // custom_components/smart_agent/frontend/node_modules/@material/web/switch/switch.js
  var MdSwitch = class MdSwitch2 extends Switch {
  };
  MdSwitch.styles = [styles32];
  if (!customElements.get("md-switch")) {
    MdSwitch = __decorate([
      t("md-switch")
    ], MdSwitch);
  }

  // custom_components/smart_agent/frontend/src/mwc.js
  if (!customElements.get("md-outlined-text-field")) {
    customElements.define("md-outlined-text-field", MdOutlinedTextField);
  }
  if (!customElements.get("md-outlined-select")) {
    customElements.define("md-outlined-select", MdOutlinedSelect);
  }
  if (!customElements.get("md-select-option")) {
    customElements.define("md-select-option", MdSelectOption);
  }
  if (!customElements.get("md-dialog")) {
    customElements.define("md-dialog", MdDialog);
  }
  if (!customElements.get("md-slider")) {
    customElements.define("md-slider", MdSlider);
  }
  if (!customElements.get("md-circular-progress")) {
    customElements.define("md-circular-progress", MdCircularProgress);
  }
  if (!customElements.get("md-filter-chip")) {
    customElements.define("md-filter-chip", MdFilterChip);
  }
  if (!customElements.get("md-filled-button")) {
    customElements.define("md-filled-button", MdFilledButton);
  }
  if (!customElements.get("md-filled-tonal-button")) {
    customElements.define("md-filled-tonal-button", MdFilledTonalButton);
  }
  if (!customElements.get("md-outlined-button")) {
    customElements.define("md-outlined-button", MdOutlinedButton);
  }
  if (!customElements.get("md-text-button")) {
    customElements.define("md-text-button", MdTextButton);
  }
  if (!customElements.get("md-icon-button")) {
    customElements.define("md-icon-button", MdIconButton);
  }
  if (!customElements.get("md-checkbox")) {
    customElements.define("md-checkbox", MdCheckbox);
  }
  if (!customElements.get("md-switch")) {
    customElements.define("md-switch", MdSwitch);
  }

  // custom_components/smart_agent/frontend/src/styles.js
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

  // custom_components/smart_agent/frontend/src/render/main.js
  var renderMethods = {
    _render() {
      var _a3;
      const SA_HA_FALLBACK_READONLY = this._isHaFallbackReadOnly();
      const $3 = (id) => this.shadowRoot.getElementById(id);
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
      this.shadowRoot.querySelectorAll(".nav-tab").forEach((b3) => {
        b3.onclick = () => {
          if (b3.dataset.group)
            this._setGroup(b3.dataset.group);
          else if (b3.dataset.t)
            this._setTab(b3.dataset.t);
        };
      });
      this.shadowRoot.querySelectorAll(".nav-sub-tab").forEach((b3) => {
        b3.onclick = () => {
          if (b3.dataset.t)
            this._setTab(b3.dataset.t);
        };
      });
      this.shadowRoot.querySelectorAll("md-filter-chip[data-filter]").forEach((b3) => b3.addEventListener("click", () => {
        this._sysLogFilter = b3.dataset.filter;
        this.shadowRoot.querySelectorAll("md-filter-chip[data-filter]").forEach((x2) => {
          x2.selected = x2.dataset.filter === this._sysLogFilter;
        });
        this._applySysLogFilter();
      }));
      $3("sysLogDate").onchange = (e9) => this._onLogDateChange(e9.target.value);
      $3("sysLogDl").onclick = () => this._downloadSysLog();
      $3("sysLogRefresh").onclick = () => {
        this._loadLogDates();
        this._wsRefreshSysLog();
      };
      $3("sysLogSearch").oninput = (e9) => {
        this._sysLogKeyword = e9.target.value.toLowerCase().trim();
        this._applySysLogFilter();
      };
      $3("sysLogSearch").onkeydown = (e9) => {
        if (e9.key === "Escape") {
          e9.target.value = "";
          this._sysLogKeyword = "";
          this._applySysLogFilter();
        }
      };
      $3("aiBtn").onclick = () => {
        if (SA_HA_FALLBACK_READONLY) {
          _warnReadOnly();
          return;
        }
        this._toggle();
      };
      $3("learningModeToggle").addEventListener("change", async (e9) => {
        if (SA_HA_FALLBACK_READONLY) {
          e9.target.selected = !e9.target.selected;
          _warnReadOnly();
          return;
        }
        const on = e9.target.selected;
        await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_learning_mode" });
        this._msg(on ? "静默学习模式已开启" : "静默学习模式已关闭");
      });
      $3("habitProactiveToggle").addEventListener("change", async (e9) => {
        if (SA_HA_FALLBACK_READONLY) {
          e9.target.selected = !e9.target.selected;
          _warnReadOnly();
          return;
        }
        const on = e9.target.selected;
        await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_habit_proactive" });
        this._msg(on ? "习惯主动询问已开启" : "习惯主动询问已关闭");
      });
      $3("frigateToggle").addEventListener("change", async (e9) => {
        if (SA_HA_FALLBACK_READONLY) {
          e9.target.selected = !e9.target.selected;
          _warnReadOnly();
          return;
        }
        const on = e9.target.selected;
        await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_frigate_enabled" });
        this._msg(on ? "Frigate NVR 视觉感知已启用" : "Frigate NVR 视觉感知已关闭");
      });
      $3("visionToggle").addEventListener("change", async (e9) => {
        if (SA_HA_FALLBACK_READONLY) {
          e9.target.selected = !e9.target.selected;
          _warnReadOnly();
          return;
        }
        const on = e9.target.selected;
        await this._callService("switch", on ? "turn_on" : "turn_off", { entity_id: "switch.smart_agent_vision_enabled" });
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
        const list = $3("vCamList");
        if (!list)
          return;
        if (configPath) {
          const hint = $3("vConfigPathHint"), pathEl = $3("vConfigPath");
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
        list.innerHTML = _visionCamsCache.map((c5) => {
          const room = c5.room || "";
          const roomBadge = room ? `<span style="background:var(--sa-primary-container);color:var(--sa-primary);padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600">${this._esc(room)}</span>` : `<span style="background:var(--md-sys-color-surface-container);color:var(--md-sys-color-outline);padding:2px 8px;border-radius:12px;font-size:12px">未绑定房间</span>`;
          const rtspMasked = (c5.rtsp_url || "").replace(/:([^@]+)@/, ":***@");
          const zoneCount = (c5.zones || []).length;
          const zoneHint = zoneCount ? `<span style="color:var(--md-sys-color-outline);font-size:12px;margin-left:4px">${zoneCount} 个区域</span>` : "";
          return `<div class="m3-item" style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--md-sys-color-surface-container);border-radius:12px">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor" style="color:var(--sa-primary);flex-shrink:0"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg>
          <div class="m3-content" style="flex:1;min-width:0">
            <div class="m3-title" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              ${this._esc(c5.friendly_name || c5.camera_id)}
              ${roomBadge}
              ${zoneHint}
            </div>
            <div class="m3-subtitle" style="font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(rtspMasked)}</div>
            <div class="body-s" style="margin-top:2px">
              ID: ${this._esc(c5.camera_id)} · min_score: ${(c5.min_score || 0.7).toFixed(2)} · fps: ${c5.fps || 5}
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
            ${zoneCount ? `<md-outlined-button style="--md-outlined-button-container-height:32px;font-size:13px" data-action="zones" data-cam-id="${this._esc(c5.camera_id)}">区域绑定</md-outlined-button>` : ""}
            <md-outlined-button style="--md-outlined-button-container-height:32px;font-size:13px" data-action="edit" data-cam-id="${this._esc(c5.camera_id)}">编辑</md-outlined-button>
            <md-filled-button class="btn-error" style="--md-filled-button-container-height:32px;font-size:13px" data-action="delete" data-cam-id="${this._esc(c5.camera_id)}">删除</md-filled-button>
          </div>
        </div>`;
        }).join("");
      };
      const _loadVisionCams = async () => {
        try {
          const result = await this._hass.callWS({ type: "smart_agent/get_frigate_cameras" });
          _renderVisionCams((result == null ? void 0 : result.cameras) || [], (result == null ? void 0 : result.config_path) || "");
        } catch (e9) {
          const list = $3("vCamList");
          if (list)
            list.innerHTML = `<div style="text-align:center;padding:20px;color:var(--md-sys-color-error);font-size:13px">加载失败，请确认 Frigate 已安装：${e9.message || e9}</div>`;
        }
      };
      const _populateVisionRooms = (selectedRoom) => {
        const sel = $3("vRoom");
        if (!sel)
          return;
        while (sel.options.length > 1)
          sel.remove(1);
        const devices = this._wsGet("devices", "devices", []);
        const smRooms = devices.map((d3) => d3.room || "").filter((r9) => r9);
        const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a4) => a4.name) : [];
        const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort((a4, b3) => a4.localeCompare(b3, "zh"));
        allRooms.forEach((r9) => {
          const opt = document.createElement("option");
          opt.value = r9;
          opt.textContent = r9;
          sel.appendChild(opt);
        });
        if (selectedRoom)
          sel.value = selectedRoom;
      };
      const _showVisionForm = (cam) => {
        const card = $3("vCamFormCard");
        if (!card)
          return;
        card.style.display = "";
        $3("vFormTitle").textContent = cam ? "编辑摄像头" : "添加摄像头";
        $3("vEditCameraId").value = (cam == null ? void 0 : cam.camera_id) || "";
        $3("vFriendlyName").value = (cam == null ? void 0 : cam.friendly_name) || "";
        _populateVisionRooms((cam == null ? void 0 : cam.room) || "");
        $3("vRtspUrl").value = (cam == null ? void 0 : cam.rtsp_url) || "";
        $3("vMinScore").value = (cam == null ? void 0 : cam.min_score) ?? 0.7;
        $3("vMinScoreVal").textContent = parseFloat((cam == null ? void 0 : cam.min_score) ?? 0.7).toFixed(2);
        $3("vThreshold").value = (cam == null ? void 0 : cam.threshold) ?? 0.85;
        $3("vThresholdVal").textContent = parseFloat((cam == null ? void 0 : cam.threshold) ?? 0.85).toFixed(2);
        $3("vFps").value = String((cam == null ? void 0 : cam.fps) ?? 5);
        const status = $3("vSaveStatus");
        if (status)
          status.style.display = "none";
        card.scrollIntoView({ behavior: "smooth", block: "start" });
      };
      const _hideVisionForm = () => {
        const card = $3("vCamFormCard");
        if (card)
          card.style.display = "none";
      };
      if ($3("vMinScore"))
        $3("vMinScore").oninput = () => {
          $3("vMinScoreVal").textContent = parseFloat($3("vMinScore").value).toFixed(2);
        };
      if ($3("vThreshold"))
        $3("vThreshold").oninput = () => {
          $3("vThresholdVal").textContent = parseFloat($3("vThreshold").value).toFixed(2);
        };
      if ($3("vAddCamBtn"))
        $3("vAddCamBtn").onclick = () => _showVisionForm(null);
      if ($3("vCancelCamBtn"))
        $3("vCancelCamBtn").onclick = _hideVisionForm;
      if ($3("vSaveCamBtn"))
        $3("vSaveCamBtn").onclick = async () => {
          var _a4, _b, _c, _d, _e, _f, _g;
          const name = (((_a4 = $3("vFriendlyName")) == null ? void 0 : _a4.value) || "").trim();
          const rtsp = (((_b = $3("vRtspUrl")) == null ? void 0 : _b.value) || "").trim();
          const room = (((_c = $3("vRoom")) == null ? void 0 : _c.value) || "").trim();
          if (!name || !rtsp) {
            this._msg("请填写摄像头名称和 RTSP 地址");
            return;
          }
          const status = $3("vSaveStatus");
          const btn = $3("vSaveCamBtn");
          btn.disabled = true;
          btn.textContent = "部署中...";
          if (status) {
            status.style.display = "";
            status.style.color = "var(--md-sys-color-outline)";
            status.textContent = "⏳ 正在写入 Frigate 配置并重启 Add-on，约需 10-20 秒...";
          }
          try {
            const camId = (((_d = $3("vEditCameraId")) == null ? void 0 : _d.value) || "").trim();
            await this._callService("smart_agent", "register_frigate_camera", {
              friendly_name: name,
              rtsp_url: rtsp,
              room,
              camera_id: camId || void 0,
              min_score: parseFloat(((_e = $3("vMinScore")) == null ? void 0 : _e.value) || "0.7"),
              threshold: parseFloat(((_f = $3("vThreshold")) == null ? void 0 : _f.value) || "0.85"),
              fps: parseInt(((_g = $3("vFps")) == null ? void 0 : _g.value) || "5")
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
          } catch (e9) {
            if (status) {
              status.style.color = "var(--md-sys-color-error)";
              status.textContent = "❌ 部署失败：" + (e9.message || e9);
            }
            this._msg("部署失败：" + (e9.message || e9));
          } finally {
            btn.disabled = false;
            btn.textContent = "保存并部署";
          }
        };
      const _roomOptions = (selected) => {
        const devices = this._wsGet("devices", "devices", []);
        const smRooms = devices.map((d3) => d3.room || "").filter((r9) => r9);
        const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a4) => a4.name) : [];
        const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort((a4, b3) => a4.localeCompare(b3, "zh"));
        return `<option value="">-- 未绑定 --</option>` + allRooms.map((r9) => `<option value="${this._esc(r9)}"${r9 === selected ? " selected" : ""}>${this._esc(r9)}</option>`).join("");
      };
      const _zoneOverlay = $3("zoneBindOverlay");
      const _zoneDesc = $3("zoneBindDesc");
      const _zoneRows = $3("zoneBindRows");
      const _zoneSaveBtn = $3("zoneBindSave");
      const _zoneCancelBtn = $3("zoneBindCancel");
      const _closeZoneOverlay = () => _zoneOverlay == null ? void 0 : _zoneOverlay.classList.remove("open");
      if (_zoneCancelBtn)
        _zoneCancelBtn.onclick = _closeZoneOverlay;
      if (_zoneOverlay)
        _zoneOverlay.onclick = (ev) => {
          if (ev.target === _zoneOverlay)
            _closeZoneOverlay();
        };
      const _showZoneBindDialog = async (camId) => {
        var _a4;
        const cam = _visionCamsCache.find((c5) => c5.camera_id === camId);
        if (!cam || !_zoneOverlay)
          return;
        let zones = cam.zones || [];
        try {
          const r9 = await this._hass.callWS({ type: "smart_agent/get_frigate_zones", camera_id: camId });
          if ((_a4 = r9 == null ? void 0 : r9.zones) == null ? void 0 : _a4.length)
            zones = r9.zones;
        } catch (_2) {
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
          _zoneRows.innerHTML = zones.map((z2) => {
            const displayName = z2.friendly_name && z2.friendly_name !== z2.zone_id ? z2.friendly_name : z2.zone_id;
            const isRawId = !z2.friendly_name || z2.friendly_name === z2.zone_id;
            return `
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
              <div style="flex:0 0 150px;font-size:14px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${this._esc(z2.zone_id)}">
                ${this._esc(displayName)}
                ${isRawId ? `<div style="font-size:10px;color:var(--md-sys-color-outline);font-weight:400">未设中文名</div>` : `<div style="font-size:10px;color:var(--md-sys-color-outline)">${this._esc(z2.zone_id)}</div>`}
              </div>
              <select data-zone-id="${this._esc(z2.zone_id)}" data-zone-name="${this._esc(z2.friendly_name || z2.zone_id)}"
                style="flex:1;padding:6px 10px;border:1px solid var(--md-sys-color-outline-variant);border-radius:8px;font-size:13px;background:var(--md-sys-color-surface-container);color:var(--md-sys-color-on-surface)">
                ${_roomOptions(z2.room || "")}
              </select>
            </div>`;
          }).join("");
        }
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
                  room: sel.value
                });
                ok++;
              } catch (_2) {
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
      const visionView = $3("view-vision");
      if (visionView) {
        visionView.addEventListener("click", async (e9) => {
          const btn = e9.target.closest("[data-action]");
          if (!btn)
            return;
          const camId = btn.dataset.camId;
          if (btn.dataset.action === "edit") {
            const cam = _visionCamsCache.find((c5) => c5.camera_id === camId);
            if (cam)
              _showVisionForm(cam);
          } else if (btn.dataset.action === "zones") {
            await _showZoneBindDialog(camId);
          } else if (btn.dataset.action === "delete") {
            if (!await this._showConfirm(`确定删除摄像头 ${camId}？此操作会同时从 Frigate 配置文件中移除并重启 Frigate。`))
              return;
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
      const _origSetTab = (_a3 = this._setTab) == null ? void 0 : _a3.bind(this);
      if (!this._visionTabHooked && _origSetTab) {
        this._visionTabHooked = true;
        const _origSetTabFn = this._setTab;
        this._setTab = (tab) => {
          _origSetTabFn.call(this, tab);
          if (tab === "vision")
            _loadVisionCams();
        };
      }
      const helpOverlay = $3("helpOverlay");
      $3("helpBtn").onclick = () => {
        helpOverlay.classList.add("open");
        const firstNav = helpOverlay.querySelector(".help-nav-item");
        if (firstNav)
          firstNav.classList.add("active");
      };
      $3("helpClose").onclick = () => helpOverlay.classList.remove("open");
      helpOverlay.onclick = (e9) => {
        if (e9.target === helpOverlay)
          helpOverlay.classList.remove("open");
      };
      helpOverlay.querySelectorAll(".help-nav-item").forEach((item) => {
        item.onclick = () => {
          helpOverlay.querySelectorAll(".help-nav-item").forEach((i8) => i8.classList.remove("active"));
          item.classList.add("active");
          const sec = item.dataset.sec;
          const target = helpOverlay.querySelector("#hsec-" + sec);
          if (target)
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        };
      });
      const helpBody = $3("helpBody");
      if (helpBody) {
        helpBody.addEventListener("scroll", () => {
          const sections = helpBody.querySelectorAll(".help-section[id]");
          let current = "";
          sections.forEach((s4) => {
            if (s4.offsetTop - helpBody.scrollTop <= 60)
              current = s4.id.replace("hsec-", "");
          });
          if (current) {
            helpOverlay.querySelectorAll(".help-nav-item").forEach((i8) => {
              i8.classList.toggle("active", i8.dataset.sec === current);
            });
          }
        });
      }
      const licGotoBtn = $3("licGotoOptionsBtn");
      if (licGotoBtn) {
        licGotoBtn.onclick = () => {
          const url = `/config/integrations/integration/smart_agent`;
          window.location.href = url;
        };
      }
      const licVerifyBtn = $3("licVerifyBtn");
      if (licVerifyBtn) {
        licVerifyBtn.onclick = async () => {
          licVerifyBtn.disabled = true;
          licVerifyBtn.textContent = "验证中…";
          try {
            await this._callService("smart_agent", "verify_license", {});
            this._msg("License 验证请求已发送，请稍候");
          } catch (e9) {
            this._msg("验证失败：" + e9.message);
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
        const v2 = inp.value.trim();
        if (!v2)
          return;
        inp.value = "";
        this._msg("画像已添加");
        try {
          await this._callService("smart_agent", "add_habit", { content: v2 });
          delete this._wsData["rules"];
          delete this._wsData["habits"];
          await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
            await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
          });
        } catch (e9) {
          this._msg("添加失败: " + e9.message);
        }
      };
      this.shadowRoot.getElementById("addRBtn").onclick = async () => {
        const inp = this.shadowRoot.getElementById("rInput");
        const v2 = inp.value.trim();
        if (!v2)
          return;
        inp.value = "";
        this._msg("规则已添加");
        try {
          await this._callService("smart_agent", "add_rule", { content: v2 });
          delete this._wsData["rules"];
          delete this._wsData["habits"];
          await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
            await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
          });
        } catch (e9) {
          this._msg("添加失败: " + e9.message);
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
          var _a4, _b, _c;
          const q = devInput.value.trim().toLowerCase();
          if (!q) {
            devResults.innerHTML = '<span style="opacity:.6">输入关键词即可搜索</span>';
            return;
          }
          const domains = ["light", "switch", "climate", "cover", "fan", "binary_sensor", "sensor", "media_player"];
          const matches = [];
          for (const [eid, state] of Object.entries(((_a4 = this._hass) == null ? void 0 : _a4.states) || {})) {
            if (!domains.some((d3) => eid.startsWith(d3 + ".")))
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
            (m3) => `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--md-sys-color-outline-variant)">
            <span style="flex:1;font-weight:500">${this._esc(m3.name)}</span>
            <code class="dev-search-copy-btn" data-eid="${this._esc(m3.eid)}"
              style="font-size:11px;color:var(--md-sys-color-primary);background:var(--md-sys-color-primary-container);padding:2px 6px;border-radius:4px;cursor:pointer"
              title="点击复制">
              ${this._esc(m3.eid)}
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
        engSelEl.onchange = (e9) => {
          this._callService("select", "select_option", { entity_id: "select.smart_agent_engine", option: e9.target.value });
          this._msg("推理引擎已切换");
        };
      }
      const numAEl = this.shadowRoot.getElementById("numA");
      if (numAEl) {
        numAEl.addEventListener("input", (e9) => {
          this.shadowRoot.getElementById("numAVal").textContent = e9.target.value;
        });
        numAEl.addEventListener("change", (e9) => {
          this._callService("number", "set_value", { entity_id: "number.smart_agent_confidence_auto", value: parseFloat(e9.target.value) });
        });
      }
      const numNEl = this.shadowRoot.getElementById("numN");
      if (numNEl) {
        numNEl.addEventListener("input", (e9) => {
          this.shadowRoot.getElementById("numNVal").textContent = e9.target.value;
        });
        numNEl.addEventListener("change", (e9) => {
          this._callService("number", "set_value", { entity_id: "number.smart_agent_confidence_notify", value: parseFloat(e9.target.value) });
        });
      }
      const modeSelEl = this.shadowRoot.getElementById("modeSel");
      if (modeSelEl) {
        const modeHandler = async () => {
          const mode = modeSelEl.value;
          if (mode !== "home" && mode !== "showroom")
            return;
          await this._callService("smart_agent", "set_mode", { mode });
          this._msg(mode === "showroom" ? "已切换为展厅模式" : "已切换为家庭模式");
        };
        modeSelEl.addEventListener("change", modeHandler);
      }
      this.shadowRoot.getElementById("showroomSceneBtns").addEventListener("click", async (e9) => {
        const sceneBtn = e9.target.closest(".showroom-scene-btn");
        const editBtn = e9.target.closest(".showroom-edit-btn");
        if (sceneBtn) {
          const scene = sceneBtn.dataset.scene;
          const customInput2 = this.shadowRoot.getElementById("showroomCustomInput");
          if (customInput2)
            customInput2.value = "";
          await this._callService("smart_agent", "set_showroom_scene", { scene, custom_prompt: "" });
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
          await this._callService("smart_agent", "set_showroom_scene", {
            scene: "",
            custom_prompt: "",
            is_command: false
          });
          this._msg("✨ 已清空展厅自定义场景");
        };
      }
      const _submitCustomScene = async () => {
        const v2 = customInput.value.trim();
        if (!v2)
          return;
        const isCmd = _isCommandMode();
        await this._callService("smart_agent", "set_showroom_scene", {
          scene: "",
          custom_prompt: v2,
          is_command: isCmd
        });
        if (isCmd) {
          this._msg("✅ 一次性指令已发送，执行后自动清空");
          customInput.value = "";
        } else {
          this._msg("💾 持久场景已设置，巡检时持续生效");
        }
      };
      customInput.onkeydown = async (e9) => {
        if (e9.key !== "Enter")
          return;
        await _submitCustomScene();
        customInput.blur();
      };
      customInput.onblur = async (e9) => {
        if (e9.relatedTarget && (e9.relatedTarget.classList.contains("showroom-scene-btn") || e9.relatedTarget.classList.contains("showroom-edit-btn") || ["editSceneSave", "editSceneCancel", "sceneModeCmd", "sceneModePersist"].includes(e9.relatedTarget.id)))
          return;
        await _submitCustomScene();
      };
      this.shadowRoot.getElementById("editSceneSave").onclick = async () => {
        const key = this._editingSceneKey;
        if (!key)
          return;
        const $4 = (id) => this.shadowRoot.getElementById(id);
        await this._callService("smart_agent", "update_showroom_scene_config", {
          scene_key: key,
          label: $4("editSceneLabel").value.trim() || void 0,
          virtual_time: $4("editSceneTime").value.trim() || void 0,
          scene_desc: $4("editSceneDesc").value.trim() || void 0,
          hint: $4("editSceneHint").value.trim() || void 0
        });
        $4("showroomEditPanel").style.display = "none";
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
        habSearch.oninput = (e9) => {
          this._habSearch = e9.target.value;
          this._renderHabitPatterns();
        };
      }
      const habSort = this.shadowRoot.getElementById("habSort");
      if (habSort) {
        habSort.onchange = (e9) => {
          this._habSort = e9.target.value;
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
        const box = $3("learningStats");
        if (!box)
          return;
        const _pill = (label, value, color, icon) => `
        <div style="background:var(--sa-card2);border:1px solid var(--sa-border);border-radius:var(--sa-shape-md);padding:12px;text-align:center;display:flex;flex-direction:column;gap:4px">
          <div style="font-size:12px;color:var(--sa-text-variant)">${icon} ${label}</div>
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
        const warn = $3("learningDeviceWarning");
        if (warn && data.noroom_devices > 0) {
          warn.style.display = "";
          warn.innerHTML = `⚠️ 有 <b>${data.noroom_devices}</b> 个设备未配置区域（共 ${data.total_devices} 个），AI 无法判断这些设备属于哪个房间。
          <button id="goFixNoRoom" style="margin-left:8px;padding:3px 12px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;font-size:12px">前往修复 →</button>`;
          const fixBtn = $3("goFixNoRoom");
          if (fixBtn)
            fixBtn.onclick = () => {
              this._filterNoRoom = true;
              this._setTab("devices");
            };
        } else if (warn) {
          warn.style.display = "none";
        }
        const trendBox = $3("learningTrend");
        if (trendBox && data.correction_trend && data.correction_trend.length > 0) {
          trendBox.style.display = "";
          const maxCount = Math.max(...data.correction_trend.map((d3) => d3.count), 1);
          trendBox.innerHTML = `
          <div style="font-size:12px;color:var(--md-sys-color-outline);margin-bottom:8px">📈 近 7 天纠正趋势</div>
          <div style="display:flex;align-items:flex-end;gap:4px;height:60px">
            ${data.correction_trend.map((d3) => {
            const h3 = Math.max(4, d3.count / maxCount * 56);
            const dayLabel = d3.day ? d3.day.slice(5) : "";
            return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px">
                <span style="font-size:10px;color:var(--md-sys-color-outline)">${d3.count}</span>
                <div style="width:100%;height:${h3}px;background:#F59E0B;border-radius:4px 4px 0 0;min-width:12px"></div>
                <span style="font-size:9px;color:var(--md-sys-color-outline)">${dayLabel}</span>
              </div>`;
          }).join("")}
          </div>`;
        } else if (trendBox) {
          trendBox.style.display = "none";
        }
        const topBox = $3("learningTopCorrected");
        if (topBox && data.top_corrected && data.top_corrected.length > 0) {
          topBox.style.display = "";
          topBox.innerHTML = `
          <div style="font-size:12px;color:var(--md-sys-color-outline);margin-bottom:8px">🔧 被纠正最多的设备 Top-5</div>
          ${data.top_corrected.map((d3) => {
            const devName = (this._wsGet("devices", "devices", []).find((dev) => dev.entity_id === d3.entity_id) || {}).name || d3.entity_id;
            return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px">
              <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${devName}</span>
              <span style="color:#F59E0B;font-weight:600;flex-shrink:0">${d3.count} 次</span>
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
        } catch (e9) {
          const box = $3("learningStats");
          if (box)
            box.innerHTML = `<div style="text-align:center;padding:16px;color:var(--md-sys-color-outline);font-size:13px;grid-column:1/-1">暂无数据</div>`;
        }
      };
      if ($3("refreshLearningBtn"))
        $3("refreshLearningBtn").onclick = _loadLearningStats;
      _loadLearningStats();
      this._setTab("dashboard");
      this._applyBrand();
    }
  };

  // custom_components/smart_agent/frontend/src/render/syslog.js
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
      } catch (e9) {
        if (box)
          box.innerHTML = `<span style="opacity:.5;color:var(--sa-error)">日志服务暂不可用：${this._esc(String(e9.message || e9))}</span>`;
      } finally {
        this._sysLogRefreshing = false;
      }
    },
    _applySysLogFilter() {
      const box = this.shadowRoot.getElementById("sysLogBox");
      if (!box)
        return;
      const rows = box.querySelectorAll(".sl-row");
      const f3 = this._sysLogFilter || "all";
      const kw = (this._sysLogKeyword || "").toLowerCase();
      let total = 0, errs = 0, warns = 0, infos = 0;
      rows.forEach((row) => {
        const lvl = row.getAttribute("data-level") || "";
        const txt = row.textContent || "";
        const txtLow = txt.toLowerCase();
        let levelMatch = true;
        if (f3 === "INFO")
          levelMatch = lvl === "sl-i";
        else if (f3 === "WARN")
          levelMatch = lvl === "sl-w";
        else if (f3 === "ERROR")
          levelMatch = lvl === "sl-e";
        else if (f3 === "protect")
          levelMatch = txt.includes("保护") || txt.includes("冷却") || txt.includes("过滤");
        else if (f3 === "trigger")
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
        stInfo.style.display = infos && f3 !== "all" ? "" : "none";
      }
    },
    _downloadSysLog() {
      const box = this.shadowRoot.getElementById("sysLogBox");
      if (!box)
        return;
      const rows = box.querySelectorAll(".sl-row");
      const lines = [];
      rows.forEach((r9) => lines.push(r9.textContent));
      const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a4 = document.createElement("a");
      a4.href = url;
      const dateSuffix = this._sysLogMode === "live" ? (/* @__PURE__ */ new Date()).toISOString().slice(0, 10) : this._sysLogMode;
      a4.download = `smart_agent_log_${dateSuffix}.txt`;
      a4.click();
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
        } catch (_2) {
          infos = null;
        }
        const currentVal = sel.value;
        sel.innerHTML = '<md-select-option value="live"><div slot="headline">⚡ 实时流水</div></md-select-option>';
        if (Array.isArray(infos) && infos.length > 0) {
          infos.forEach((item) => {
            const opt = document.createElement("md-select-option");
            opt.value = item.date;
            const sizeStr = item.size_kb > 0 ? ` · ${item.size_kb}KB` : "";
            const errStr = item.errors > 0 ? ` ⚠${item.errors}` : "";
            const label = item.today ? `📅 ${item.date} 今天${sizeStr}${errStr}` : `${item.date}${sizeStr}${errStr}`;
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
            const today = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
            dates.forEach((d3) => {
              const opt = document.createElement("md-select-option");
              opt.value = d3;
              opt.innerHTML = `<div slot="headline">${d3 === today ? `📅 ${d3} 今天` : d3}</div>`;
              sel.appendChild(opt);
            });
          }
        }
        if (currentVal && [...sel.options].some((o10) => o10.value === currentVal)) {
          sel.value = currentVal;
        }
      } catch (e9) {
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
        const lines = content.split("\n").filter((l5) => l5.trim());
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
      } catch (e9) {
        if (box)
          box.innerHTML = `<span style="color:var(--sa-err)">加载失败: ${this._esc(e9.message || String(e9))}</span>`;
        if (info)
          info.textContent = `${val} — 加载失败`;
      }
    }
  };

  // custom_components/smart_agent/frontend/src/constants.js
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

  // custom_components/smart_agent/frontend/src/render/habits.js
  var habitsMethods = {
    _renderHabitPatterns() {
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const patterns = this._wsGet("behavior_patterns", "patterns", []);
      const statRow = $3("habitStatRow");
      const tbl = $3("habitPatTable");
      if (!tbl)
        return;
      const ICO = this._getIcons();
      const total = patterns.length;
      const active = patterns.filter((p4) => p4.confidence >= 60).length;
      const avgConf = total ? Math.round(patterns.reduce((s4, p4) => s4 + p4.confidence, 0) / total) : 0;
      const deviceCount = total ? new Set(patterns.map((p4) => p4.entity_id)).size : 0;
      if (statRow) {
        statRow.innerHTML = [
          `<span class="hab-stat-chip">${ICO.schedule} ${total} 条规律</span>`,
          total ? `<span class="hab-stat-chip">${ICO.device} ${deviceCount} 个设备</span>` : "",
          total ? `<span class="hab-stat-chip" style="color:var(--sa-succ);border-color:rgba(20,108,46,.2);background:var(--sa-succ-bg)">${ICO.check} ${active} 条激活</span>` : "",
          total ? `<span class="hab-stat-chip">${ICO.gauge} 平均置信度 ${avgConf}%</span>` : ""
        ].join("");
      }
      if (!total) {
        const domFilterEl2 = $3("habDomainFilter");
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
      const domains = [...new Set(patterns.map((p4) => (p4.entity_id || "").split(".")[0]))].sort();
      const domFilterEl = $3("habDomainFilter");
      if (domFilterEl) {
        const df = this._habDomainFilter || "all";
        domFilterEl.innerHTML = ["all", ...domains].map((d3) => {
          const cnt = d3 === "all" ? total : patterns.filter((p4) => (p4.entity_id || "").split(".")[0] === d3).length;
          const lbl = d3 === "all" ? "全部" : DOMAIN_LABELS[d3] || this._esc(d3);
          return `<md-filter-chip class="hab-df-btn" ${df === d3 ? "selected" : ""} data-d="${this._esc(d3)}" label="${lbl} (${cnt})"></md-filter-chip>`;
        }).join("");
        domFilterEl.querySelectorAll(".hab-df-btn").forEach((b3) => {
          b3.onclick = () => {
            this._habDomainFilter = b3.dataset.d;
            this._renderHabitPatterns();
          };
        });
      }
      const search = (this._habSearch || "").toLowerCase().trim();
      const domFilt = this._habDomainFilter || "all";
      let filtered = patterns.filter((p4) => {
        if (domFilt !== "all" && (p4.entity_id || "").split(".")[0] !== domFilt)
          return false;
        if (search) {
          const n9 = (p4.name || p4.entity_id || "").toLowerCase();
          const e9 = (p4.entity_id || "").toLowerCase();
          if (!n9.includes(search) && !e9.includes(search))
            return false;
        }
        return true;
      });
      const sortKey = this._habSort || "conf";
      if (sortKey === "conf")
        filtered.sort((a4, b3) => b3.confidence - a4.confidence);
      else if (sortKey === "time")
        filtered.sort((a4, b3) => (a4.time_label || "").localeCompare(b3.time_label || ""));
      else if (sortKey === "name")
        filtered.sort(
          (a4, b3) => (a4.name || a4.entity_id || "").localeCompare(b3.name || b3.entity_id || "")
        );
      if (!filtered.length) {
        tbl.innerHTML = `<div class="body-s" style="text-align:center;padding:32px;opacity:.5">无匹配结果，请调整搜索条件</div>`;
        return;
      }
      const ON_STATES = /* @__PURE__ */ new Set(["on", "open", "playing", "heat", "cool", "auto", "fan_only"]);
      const confFillClass = (c5) => c5 >= 80 ? "hab-conf-high" : c5 >= 60 ? "hab-conf-mid" : "hab-conf-low";
      const confColor = (c5) => c5 >= 80 ? "var(--sa-succ)" : c5 >= 60 ? "var(--sa-primary)" : "var(--sa-text2)";
      const domainIcon = (eid) => {
        const d3 = (eid || "").split(".")[0];
        return ICO[d3] || ICO.device;
      };
      const stateChipCls = (s4) => ON_STATES.has(s4) ? "hab-chip hab-chip-on" : "hab-chip hab-chip-off";
      const stateIco = (s4) => ON_STATES.has(s4) ? ICO.check : ICO.close;
      const confChip = (p4) => `
      <span class="hab-conf-chip">
        <span class="hab-conf-track"><span class="hab-conf-fill ${confFillClass(p4.confidence)}" style="width:${p4.confidence}%"></span></span>
        <span class="hab-conf-val" style="color:${confColor(p4.confidence)}">${p4.confidence}%</span>
      </span>`;
      let h3 = "";
      if (this._habGrouped) {
        const groups = /* @__PURE__ */ new Map();
        filtered.forEach((p4) => {
          const key = p4.entity_id || "unknown";
          if (!groups.has(key)) {
            groups.set(key, { name: p4.name || p4.entity_id, eid: p4.entity_id, items: [] });
          }
          groups.get(key).items.push(p4);
        });
        h3 += `<div class="hab-list">`;
        for (const [, g2] of groups) {
          h3 += `
          <div class="hab-dev-section">
            <div class="hab-dev-header">
              <div class="hab-dev-icon">${domainIcon(g2.eid)}</div>
              <div style="flex:1;min-width:0">
                <div class="hab-dev-name">${this._esc(g2.name)}</div>
                <div class="hab-dev-eid">${this._esc(g2.eid)}</div>
              </div>
              <span class="hab-dev-badge">${g2.items.length} 条规律</span>
            </div>
            <div class="hab-dev-rows">`;
          g2.items.forEach((p4) => {
            const isActive = p4.confidence >= 60;
            const st = (p4.expected_state || "").toLowerCase();
            h3 += `
              <div class="hab-row-compact${isActive ? "" : " hab-inactive"}">
                <span class="${stateChipCls(st)}">${stateIco(st)} ${this._esc(p4.state_cn || p4.expected_state)}</span>
                <span class="hab-chip">${ICO.schedule} ${this._esc(p4.time_label)}</span>
                <span class="hab-chip">${ICO.calendar} ${this._esc(p4.weekday)}</span>
                ${confChip(p4)}
                <md-icon-button class="hab-del-btn" data-id="${p4.id}" title="删除此规律" style="color:var(--sa-text-variant)">${ICO.delete}</md-icon-button>
              </div>`;
          });
          h3 += `
            </div>
          </div>`;
        }
        h3 += `</div>`;
      } else {
        h3 += `<div class="hab-list">`;
        filtered.forEach((p4) => {
          const isActive = p4.confidence >= 60;
          const st = (p4.expected_state || "").toLowerCase();
          h3 += `
          <div class="hab-item${isActive ? "" : " hab-inactive"}">
            <div class="hab-icon-wrap ${ON_STATES.has(st) ? "state-on" : "state-off"}">${domainIcon(p4.entity_id)}</div>
            <div class="hab-body">
              <div class="hab-name">${this._esc(p4.name || p4.entity_id)}</div>
              <div class="hab-eid">${this._esc(p4.entity_id)}</div>
              <div class="hab-chips">
                <span class="${stateChipCls(st)}">${stateIco(st)} ${this._esc(p4.state_cn || p4.expected_state)}</span>
                <span class="hab-chip">${ICO.schedule} ${this._esc(p4.time_label)}</span>
                <span class="hab-chip">${ICO.calendar} ${this._esc(p4.weekday)}</span>
                ${confChip(p4)}
              </div>
            </div>
            <md-icon-button class="hab-del-btn" data-id="${p4.id}" title="删除此规律" style="color:var(--sa-text-variant)">${ICO.delete}</md-icon-button>
          </div>`;
        });
        h3 += `</div>`;
      }
      tbl.innerHTML = h3;
      tbl.querySelectorAll(".hab-del-btn").forEach((b3) => {
        b3.onclick = async () => {
          if (!await this._showConfirm("确定删除此行为习惯规律？"))
            return;
          try {
            await this._callService("smart_agent", "delete_behavior_pattern", {
              id: parseInt(b3.dataset.id)
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

  // custom_components/smart_agent/frontend/src/render/aiscenes.js
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
            await this._callService("smart_agent", "run_pattern_analysis", {});
            this._msg("行为分析已启动，约 15-30 秒后自动刷新");
            setTimeout(() => {
              this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
            }, 15e3);
          } catch (e9) {
            this._msg("分析失败: " + e9.message);
          } finally {
            runBtn.disabled = false;
            runBtn.innerHTML = `🔍 立即分析`;
          }
        };
      }
      const pending = scenes.filter((s4) => s4.status === "pending");
      const active = scenes.filter((s4) => s4.status === "active");
      const rejected = scenes.filter((s4) => s4.status === "rejected");
      const $3 = (id) => this.shadowRoot.getElementById(id);
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(this.shadowRoot, [
          "#runAnalysisBtn",
          "#aiSceneParseBtn",
          "#aiSceneConfirmBtn",
          "#aiSceneCreateCancel",
          ".ai-scene-approve",
          ".ai-scene-reject",
          ".ai-scene-trigger",
          ".ai-scene-delete",
          "#writeYaml"
        ].join(","));
      }
      const pendingBadge = $3("aiScenesPendingBadge");
      if (pendingBadge)
        pendingBadge.textContent = pending.length;
      const activeBadge = $3("aiScenesActiveBadge");
      if (activeBadge)
        activeBadge.textContent = active.length;
      const rejectedBadge = $3("aiScenesRejectedBadge");
      if (rejectedBadge)
        rejectedBadge.textContent = rejected.length;
      const confMeta = (c5) => {
        if (c5 >= 85)
          return { cls: "conf-high", label: "高置信", color: "var(--sa-succ)" };
        if (c5 >= 70)
          return { cls: "conf-med", label: "中置信", color: "var(--sa-primary)" };
        return { cls: "conf-low", label: "低置信", color: "var(--sa-text-variant)" };
      };
      const parseJsonArray = (value) => {
        try {
          const parsed = JSON.parse(value || "[]");
          return Array.isArray(parsed) ? parsed : [];
        } catch {
          return [];
        }
      };
      const renderEntities = (entities_json, actions_json, limit = 6) => {
        const entities = parseJsonArray(entities_json);
        const actions = parseJsonArray(actions_json);
        const actionMap = /* @__PURE__ */ new Map();
        for (const a4 of actions) {
          const eid = a4 == null ? void 0 : a4.entity_id;
          if (!eid)
            continue;
          actionMap.set(eid, a4);
        }
        const summarizeParams = (entity, action) => {
          const p4 = action && typeof action.params === "object" && action.params || {};
          const merged = { ...entity || {}, ...p4 };
          const parts = [];
          if (merged.brightness_pct != null)
            parts.push(`${merged.brightness_pct}%`);
          else if (merged.brightness != null) {
            const pct = Math.round(Number(merged.brightness) / 255 * 100);
            if (!Number.isNaN(pct))
              parts.push(`${pct}%`);
          }
          if (merged.color_temp_kelvin != null)
            parts.push(`${merged.color_temp_kelvin}K`);
          else if (merged.color_temp != null)
            parts.push(`CT:${merged.color_temp}`);
          if (merged.temperature != null)
            parts.push(`${merged.temperature}°C`);
          if (merged.position != null)
            parts.push(`位置${merged.position}%`);
          if (merged.tilt_position != null)
            parts.push(`倾角${merged.tilt_position}%`);
          if (merged.hvac_mode)
            parts.push(`${merged.hvac_mode}`);
          if (merged.fan_mode)
            parts.push(`风速:${merged.fan_mode}`);
          return parts.join(" · ");
        };
        const source = actions.length ? actions.map((a4) => {
          var _a3, _b;
          return {
            entity_id: a4.entity_id,
            state: ((_a3 = a4.service) == null ? void 0 : _a3.includes("off")) || ((_b = a4.service) == null ? void 0 : _b.includes("close")) ? "off" : "on",
            _action: a4
          };
        }) : entities;
        const visible = source.slice(0, limit);
        const more = source.length - visible.length;
        const chips = visible.map((e9) => {
          const stOn = ["on", "open", "heat", "cool", "auto"].includes(e9.state);
          const dot = stOn ? `<span style="width:6px;height:6px;border-radius:50%;background:var(--sa-succ);flex-shrink:0"></span>` : `<span style="width:6px;height:6px;border-radius:50%;background:var(--sa-border);flex-shrink:0"></span>`;
          const domain = (e9.entity_id || "").split(".")[0];
          const dIco = ICO[domain] || ICO.device;
          const name = (e9.entity_id || "").split(".")[1] || e9.entity_id;
          const action = e9._action || actionMap.get(e9.entity_id) || null;
          const summary = summarizeParams(e9, action);
          return `<span title="${this._esc(e9.entity_id)}" style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px 3px 6px;
                  border-radius:20px;background:rgba(128,128,128,.1);font-size:11px;max-width:260px;overflow:hidden;
                  white-space:nowrap;text-overflow:ellipsis">
                  ${dot}${dIco}<span style="overflow:hidden;text-overflow:ellipsis">${this._esc(name)}${summary ? ` · ${this._esc(summary)}` : ""}</span>
                </span>`;
        }).join("");
        const extra = more > 0 ? `<span style="font-size:11px;opacity:.55;padding:3px 6px">+${more} 个</span>` : "";
        return chips + extra;
      };
      const renderCard = (s4, { showApprove = false, showReject = false, showTrigger = false, dimmed = false } = {}) => {
        const cm = confMeta(s4.confidence);
        const actions = parseJsonArray(s4.actions_json);
        const entities = actions.length ? [] : parseJsonArray(s4.entities_json);
        const entCount = actions.length ? actions.length : entities.length;
        const borderColor = dimmed ? "var(--sa-border)" : cm.color;
        return `
      <div class="scene-card ${dimmed ? "scene-card--dimmed" : ""}"
           data-scene-id="${s4.id}"
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
                ${this._esc(s4.name)}
              </span>
            </div>
            <span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;
                         background:${cm.color}1a;color:${cm.color};font-size:11px;font-weight:600;flex-shrink:0;white-space:nowrap">
              ${ICO.gauge} ${s4.confidence}% · ${cm.label}
            </span>
          </div>

          <!-- 描述 -->
          <div class="body-s" style="opacity:.75;margin-bottom:10px;line-height:1.5">
            ${this._esc(s4.description || "")}
          </div>

          <!-- 元数据行 -->
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap">
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              ${ICO.schedule} ${this._esc(s4.trigger_context || "—")}
            </span>
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              📊 历史触发 ${s4.hit_count} 次
            </span>
            <span class="body-s" style="opacity:.6;display:inline-flex;align-items:center;gap:4px">
              💡 ${entCount} 个设备
            </span>
          </div>

          <!-- 实体芯片 -->
          <div style="display:flex;flex-wrap:wrap;gap:5px">
            ${renderEntities(s4.entities_json, s4.actions_json)}
          </div>
        </div>

        <!-- 操作按钮行 -->
        <div style="display:flex;align-items:center;gap:8px;padding:8px 16px 12px;border-top:1px solid var(--sa-border);flex-wrap:wrap">
          ${showApprove ? `<md-filled-button class="ai-scene-approve" data-id="${s4.id}"
              style="--md-filled-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.check} 确认启用</md-filled-button>` : ""}
          ${showTrigger ? `<md-filled-tonal-button class="ai-scene-trigger" data-id="${s4.id}"
              style="--md-filled-tonal-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.play} 立即触发</md-filled-tonal-button>` : ""}
          <md-outlined-button class="ai-scene-yaml" data-id="${s4.id}"
              style="--md-outlined-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px">
              ${ICO.yaml} 导出 YAML</md-outlined-button>
          ${showReject ? `<md-outlined-button class="ai-scene-reject" data-id="${s4.id}"
              style="--md-outlined-button-container-height:32px;font-size:13px;display:inline-flex;align-items:center;gap:5px;color:var(--sa-text-variant)">
              ${ICO.close} 拒绝</md-outlined-button>` : ""}
          <span style="flex:1"></span>
          <md-icon-button class="ai-scene-delete" data-id="${s4.id}"
              title="删除场景" style="color:var(--sa-error);opacity:.7">
              ${ICO.delete}</md-icon-button>
        </div>
      </div>`;
      };
      const createPanel = $3("aiSceneCreatePanel");
      if (createPanel && !createPanel._bound) {
        createPanel._bound = true;
        const toggleBtn = $3("aiSceneCreateToggle");
        const body = $3("aiSceneCreateBody");
        const textarea = $3("aiSceneCreateText");
        const autoChk = $3("aiSceneAutoActivate");
        const parseBtn = $3("aiSceneParseBtn");
        const confirmBtn = $3("aiSceneConfirmBtn");
        const cancelBtn = $3("aiSceneCreateCancel");
        const preview = $3("aiSceneCreatePreview");
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
            clearTimeout(eventTimeout);
            if (typeof unsubSceneCreated === "function")
              unsubSceneCreated();
            parseBtn.disabled = false;
            parseBtn.textContent = "🤖 AI 解析生成";
            const d3 = ev.data || ev.detail || {};
            if (!d3.success) {
              this._msg("解析失败：" + (d3.error || "未知错误"));
              return;
            }
            preview.innerHTML = `
            <div style="font-size:13px;color:var(--sa-text-variant);margin-bottom:6px">解析结果预览</div>
            <div style="font-weight:600;margin-bottom:4px">📋 ${d3.name || "新场景"}</div>
            <div style="font-size:12px;color:var(--sa-text-variant)">
              状态：${d3.status === "active" ? "✅ 已直接激活" : "⏳ 待确认"}
            </div>`;
            preview.style.display = "block";
            confirmBtn.style.display = "inline-flex";
            cancelBtn.style.display = "inline-flex";
            confirmBtn.dataset.sceneId = d3.scene_id;
            confirmBtn.dataset.status = d3.status;
            if (d3.status === "active") {
              this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
            }
          };
          let eventTimeout = null;
          let unsubSceneCreated = null;
          try {
            unsubSceneCreated = await this._hass.connection.subscribeEvents(onCreated, "smart_agent_scene_created");
            eventTimeout = setTimeout(() => {
              if (typeof unsubSceneCreated === "function")
                unsubSceneCreated();
              parseBtn.disabled = false;
              parseBtn.textContent = "🤖 AI 解析生成";
              this._msg("解析超时，请稍后重试");
            }, 3e4);
            await this._callService("smart_agent", "create_scene_from_text", {
              text,
              auto_activate: autoChk ? autoChk.checked : false
            });
          } catch (e9) {
            if (eventTimeout)
              clearTimeout(eventTimeout);
            if (typeof unsubSceneCreated === "function")
              unsubSceneCreated();
            parseBtn.disabled = false;
            parseBtn.textContent = "🤖 AI 解析生成";
            this._msg("调用失败: " + e9.message);
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
      $3("aiScenesPending").innerHTML = pending.length ? pending.map((s4) => renderCard(s4, { showApprove: true, showReject: true })).join("") : `<div class="empty-state">
           <div class="empty-state-icon">🔮</div>
           <div class="empty-state-title">暂无待确认候选场景</div>
           <div class="empty-state-desc">每日凌晨行为分析后自动生成，或点击「立即分析」手动触发</div>
         </div>`;
      $3("aiScenesActive").innerHTML = active.length ? active.map((s4) => renderCard(s4, { showTrigger: true })).join("") : `<div class="empty-state">
           <div class="empty-state-icon">✨</div>
           <div class="empty-state-title">暂无已激活场景</div>
           <div class="empty-state-desc">审批通过的场景将在此显示</div>
         </div>`;
      $3("aiScenesRejected").innerHTML = rejected.length ? rejected.map((s4) => renderCard(s4, { showApprove: true, dimmed: true })).join("") : `<div class="empty-state">
           <div class="empty-state-icon">🗂️</div>
           <div class="empty-state-title">暂无已拒绝场景</div>
         </div>`;
      const view = this.shadowRoot.getElementById("view-aiscenes");
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(view, ".ai-scene-approve,.ai-scene-reject,.ai-scene-trigger,.ai-scene-delete,#writeYaml");
      }
      view.querySelectorAll(".ai-scene-approve").forEach((b3) => {
        b3.onclick = async () => {
          b3.disabled = true;
          try {
            await this._callService("smart_agent", "approve_ai_scene", { id: parseInt(b3.dataset.id) });
            this._msg("场景已激活，将加入 AI 推理上下文");
            await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          } catch (e9) {
            this._msg("操作失败: " + e9.message);
            b3.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-reject").forEach((b3) => {
        b3.onclick = async () => {
          if (!await this._showConfirm("拒绝后该场景不再自动推荐，确认吗？"))
            return;
          b3.disabled = true;
          try {
            await this._callService("smart_agent", "reject_ai_scene", { id: parseInt(b3.dataset.id) });
            this._msg("已拒绝场景");
            await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          } catch (e9) {
            this._msg("操作失败: " + e9.message);
            b3.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-trigger").forEach((b3) => {
        b3.onclick = async () => {
          if (!await this._showConfirm("立即触发此场景？将批量执行场景内所有设备动作。"))
            return;
          b3.disabled = true;
          try {
            await this._callService("smart_agent", "trigger_ai_scene", { id: parseInt(b3.dataset.id) });
            this._msg("场景触发指令已发送");
          } catch (e9) {
            this._msg("触发失败: " + e9.message);
          } finally {
            b3.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-delete").forEach((b3) => {
        b3.onclick = async () => {
          if (!await this._showConfirm("确定删除此 AI 场景？"))
            return;
          b3.disabled = true;
          try {
            await this._callService("smart_agent", "delete_ai_scene", { id: parseInt(b3.dataset.id) });
            this._msg("已删除 AI 场景");
            await this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
          } catch (e9) {
            this._msg("删除失败: " + e9.message);
            b3.disabled = false;
          }
        };
      });
      view.querySelectorAll(".ai-scene-yaml").forEach((b3) => {
        b3.onclick = async () => {
          const id = b3.dataset.id;
          b3.disabled = true;
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
            overlay.onclick = (e9) => {
              if (e9.target === overlay)
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
              if (this._isHaFallbackReadOnly()) {
                this._warnHaFallbackReadOnly();
                return;
              }
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
          } catch (e9) {
            this._msg("导出失败: " + e9.message);
          } finally {
            b3.disabled = false;
          }
        };
      });
    }
  };

  // custom_components/smart_agent/frontend/src/render/corrections.js
  var correctionsMethods = {
    _renderCorrections() {
      const raw = this._wsGet("ai_actions", "actions", []);
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const ICO = this._getIcons();
      const box = $3("corrList");
      if (!box)
        return;
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(this.shadowRoot, "#corrClearAll,.corr-correct-btn,.corr-dismiss-btn,.corr-dismiss-scene");
      }
      const now = Date.now() / 1e3;
      const FRESH_SEC = 30 * 60;
      const ALL_SEC = 8 * 3600;
      const WARN_SEC = 5 * 60;
      const filterMode = this._corrFilter || "all";
      const visible = raw.filter((a4) => {
        if (!a4.time)
          return true;
        if (filterMode === "fresh")
          return now - a4.time < FRESH_SEC;
        return now - a4.time < ALL_SEC;
      });
      const btnAll = $3("corrFilterAll"), btnFresh = $3("corrFilterFresh");
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
      const btnClearAll = $3("corrClearAll");
      if (btnClearAll && !btnClearAll._bound) {
        btnClearAll._bound = true;
        btnClearAll.onclick = async () => {
          if (!await this._showConfirm("确定清空全部近期操作记录吗？"))
            return;
          try {
            await this._callService("smart_agent", "dismiss_ai_action", {});
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
      visible.forEach((a4) => {
        const key = a4.scene || "(未知场景)";
        if (!groups.has(key))
          groups.set(key, []);
        groups.get(key).push(a4);
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
        items.forEach((a4) => {
          var _a3;
          const name = ((_a3 = this._hass.states[a4.entity_id]) == null ? void 0 : _a3.attributes.friendly_name) || a4.entity_id;
          const stateColor = a4.state === "on" ? "var(--sa-succ,#4caf50)" : "var(--sa-text-variant,#888)";
          html += `
          <div style="padding:10px 14px;display:flex;align-items:center;gap:12px;border-top:1px solid var(--sa-border)">
            <div style="width:28px;height:28px;border-radius:8px;background:var(--sa-primary-container);color:var(--sa-primary);display:flex;align-items:center;justify-content:center;flex-shrink:0">
              ${ICO[a4.entity_id.split(".")[0]] || ICO.device}
            </div>
            <div style="flex:1;min-width:0">
              <div class="body-m" style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(name)}</div>
              <div class="body-s" style="opacity:.6">设为 <b style="color:${stateColor}">${this._esc(String(a4.state ?? ""))}</b>
                <span style="font-size:11px;opacity:.5;margin-left:4px">${this._esc(a4.entity_id)}</span></div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0">
              ${expired ? "" : `
              <md-filled-tonal-button class="corr-correct-btn" data-eid="${this._esc(a4.entity_id)}"
                style="--md-filled-tonal-button-container-height:28px;font-size:11px;background:var(--sa-error-container);color:var(--sa-error)">
                🎯 纠正
              </md-filled-tonal-button>`}
              <md-outlined-button class="corr-dismiss-btn" data-eid="${this._esc(a4.entity_id)}"
                style="--md-outlined-button-container-height:28px;font-size:11px;opacity:.7">
                ✕ 忽略
              </md-outlined-button>
            </div>
          </div>`;
        });
        html += `</div></div>`;
      });
      box.innerHTML = html;
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(box, ".corr-correct-btn,.corr-dismiss-btn,.corr-dismiss-scene");
      }
      const _refreshCorrList = () => {
        delete this._wsLoading["ai_actions"];
        this._wsRefresh("smart_agent/get_ai_actions", "ai_actions", () => this._renderCorrections());
      };
      box.querySelectorAll(".corr-correct-btn").forEach((btn) => {
        btn.onclick = async () => {
          var _a3;
          const eid = btn.dataset.eid;
          if (!await this._showConfirm(`确定纠正对 ${eid} 的操作吗？将撤销并记录学习。`))
            return;
          btn.disabled = true;
          btn.textContent = "处理中...";
          try {
            const cur = (_a3 = this._hass.states[eid]) == null ? void 0 : _a3.state;
            const domain = eid.split(".")[0];
            const svc = domain === "cover" ? cur === "open" ? "close_cover" : "open_cover" : cur === "on" ? "turn_off" : "turn_on";
            await this._callService(domain, svc, { entity_id: eid });
            await new Promise((r9) => setTimeout(r9, 500));
            await this._callService("smart_agent", "report_correction", { entity_id: eid });
            this._msg(`已纠正 ${eid}，AI 将学习此偏好`);
            _refreshCorrList();
          } catch (e9) {
            this._msg("纠正失败: " + e9.message);
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
            await this._callService("smart_agent", "dismiss_ai_action", { entity_id: eid });
            this._msg(`已忽略 ${eid}`);
            _refreshCorrList();
          } catch (e9) {
            this._msg("操作失败: " + e9.message);
            btn.disabled = false;
            btn.textContent = "✕ 忽略";
          }
        };
      });
      box.querySelectorAll(".corr-dismiss-scene").forEach((btn) => {
        btn.onclick = async () => {
          const scene = btn.dataset.scene;
          const targets = visible.filter((a4) => (a4.scene || "(未知场景)") === scene);
          btn.disabled = true;
          btn.textContent = "处理中...";
          try {
            for (const a4 of targets) {
              await this._callService("smart_agent", "dismiss_ai_action", {
                entity_id: a4.entity_id
              });
            }
            this._msg(`已忽略「${scene}」的全部操作`);
            _refreshCorrList();
          } catch (e9) {
            this._msg("操作失败: " + e9.message);
            btn.disabled = false;
            btn.textContent = "全部忽略";
          }
        };
      });
    }
  };

  // custom_components/smart_agent/frontend/src/render/transactions.js
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
      } catch (e9) {
        const errMsg = this._esc(String(e9.message || "未知错误"));
        statsBox.innerHTML = `<div style="opacity:.5;grid-column:1/-1;text-align:center">统计加载失败: ${errMsg}</div>`;
        roomBox.innerHTML = "";
        return;
      }
      const today_inferences = Number(data.today_inferences ?? 0);
      const today_corrections = Number(data.today_corrections ?? 0);
      const room_overturn_rates = Array.isArray(data.room_overturn_rates) ? data.room_overturn_rates : [];
      const overturnRate = today_inferences > 0 ? Math.round(today_corrections / today_inferences * 100) : 0;
      const statCardStyle = "background:var(--sa-card);border:1px solid var(--sa-border);border-radius:var(--sa-shape-md);padding:12px;text-align:center";
      const overturnColor = overturnRate > 30 ? "var(--sa-err)" : overturnRate > 15 ? "var(--sa-state-warning)" : "var(--sa-succ)";
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
        const validRates = room_overturn_rates.filter((r9) => typeof r9.rate === "number" && !isNaN(r9.rate));
        const maxRate = validRates.length ? Math.max(...validRates.map((r9) => r9.rate), 1) : 1;
        roomBox.innerHTML = validRates.sort((a4, b3) => b3.rate - a4.rate).map((r9) => {
          const barW = Math.round(r9.rate / Math.max(maxRate, 1) * 100);
          const color = r9.rate > 30 ? "var(--sa-err)" : r9.rate > 15 ? "var(--sa-state-warning)" : "var(--sa-succ)";
          const rateStr = this._esc(String(r9.rate));
          const corrStr = this._esc(String(r9.corrections ?? 0));
          const infStr = this._esc(String(r9.inferences ?? 0));
          return `
          <div style="display:flex;align-items:center;gap:10px;padding:4px 0">
            <div style="width:64px;font-size:12px;font-weight:500;flex-shrink:0">${this._esc(String(r9.room ?? ""))}</div>
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
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(this.shadowRoot, ".txn-rollback");
      }
      if (!box)
        return;
      const STATUS_META = {
        success: { label: "成功", color: "var(--sa-succ, #4caf50)" },
        partial: { label: "部分执行", color: "var(--sa-state-warning, #ff9800)" },
        blocked: { label: "已拦截", color: "var(--sa-secondary, #2196f3)" },
        failed: { label: "失败", color: "var(--sa-err, #f44336)" },
        pending: { label: "执行中", color: "var(--sa-text-variant, #9e9e9e)" },
        rolled_back: { label: "已回滚", color: "var(--sa-tertiary, #9c27b0)" }
      };
      if (!list.length) {
        box.innerHTML = '<div style="opacity:.5;padding:16px 0;text-align:center">暂无执行记录</div>';
        return;
      }
      box.innerHTML = list.map((t6) => {
        const meta = STATUS_META[t6.status] || { label: this._esc(String(t6.status ?? "")), color: "#888" };
        const canRollback = ["success", "partial", "failed"].includes(t6.status);
        const failBadge = t6.failed_count > 0 ? `<span style="color:var(--error-color,#f44336);font-size:11px"> · ${t6.failed_count}失败</span>` : "";
        const blockedBadge = t6.blocked_count > 0 ? `<span style="color:var(--info-color,#2196f3);font-size:11px"> · ${t6.blocked_count}拦截</span>` : "";
        return `
        <div style="background:var(--sa-card,var(--card-background-color));border:1px solid var(--sa-border,var(--divider-color));
                    border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:6px">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px">
            <div style="display:flex;align-items:center;gap:8px">
              <span style="background:${meta.color};color:#fff;border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600">
                ${meta.label}
              </span>
              <span class="body-s" style="opacity:.6">${this._esc(t6.time || "")}</span>
            </div>
            <div style="display:flex;gap:6px">
              ${canRollback ? `<md-outlined-button class="txn-rollback" data-id="${t6.id}"
                  style="--md-outlined-button-container-height:28px;font-size:11px">⏪ 回滚</md-outlined-button>` : ""}
            </div>
          </div>
          <div style="font-size:13px;font-weight:500;color:var(--primary-text-color)">${this._esc(t6.scene_desc || "(无场景描述)")}</div>
          <div class="body-s" style="opacity:.6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${this._esc(t6.trigger_summary || "")}
          </div>
          <div style="display:flex;gap:12px;font-size:11px;opacity:.7">
            <span>动作 ${t6.action_count || 0}</span>
            <span style="color:${meta.color}">执行 ${t6.dispatched_count || 0}</span>
            ${failBadge}${blockedBadge}
            <span style="opacity:.5">置信度 ${t6.confidence || 0}%</span>
            <span style="opacity:.5">#${t6.id}</span>
          </div>
        </div>`;
      }).join("");
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(box, ".txn-rollback");
      }
      box.querySelectorAll(".txn-rollback").forEach((b3) => {
        b3.onclick = async () => {
          const id = parseInt(b3.dataset.id);
          if (!await this._showConfirm(`确定回滚事务 #${id}？将把相关设备恢复到执行前的状态。`))
            return;
          b3.disabled = true;
          b3.textContent = "回滚中…";
          try {
            await this._callService("smart_agent", "rollback_transaction", { transaction_id: id });
            this._msg(`事务 #${id} 回滚指令已发送`);
            this._wsRefresh(
              "smart_agent/get_transactions",
              "transactions",
              () => this._renderTransactions()
            );
          } catch (e9) {
            this._msg("回滚失败: " + e9.message);
            b3.disabled = false;
            b3.textContent = "⏪ 回滚";
          }
        };
      });
    }
  };

  // custom_components/smart_agent/frontend/src/render/energy.js
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
      const maxOn = Math.max(...list.map((s4) => s4.on_minutes), 1);
      box.innerHTML = list.map((s4) => {
        const name = s4.entity_id.replace(/^[^.]+\./, "").replace(/_/g, " ");
        const onH = Math.floor(s4.on_minutes / 60), onM = Math.round(s4.on_minutes % 60);
        const wasteH = Math.floor(s4.waste_minutes / 60), wasteM = Math.round(s4.waste_minutes % 60);
        const onLabel = onH ? `${onH}h ${onM}m` : `${onM}m`;
        const wasteLabel = s4.waste_minutes < 1 ? "无浪费" : wasteH ? `${wasteH}h ${wasteM}m` : `${wasteM}m`;
        const wasteRatio = s4.on_minutes > 0 ? Math.round(s4.waste_minutes / s4.on_minutes * 100) : 0;
        const barColor = wasteRatio > 50 ? "#f44336" : wasteRatio > 20 ? "#ff9800" : "var(--sa-primary,#6750a4)";
        const barWaste = s4.on_minutes > 0 ? Math.round(s4.waste_minutes / s4.on_minutes * 100) : 0;
        const barOn = Math.round(s4.on_minutes / maxOn * 100);
        return `
        <div style="background:var(--sa-card,var(--card-background-color));border:1px solid var(--sa-border,var(--divider-color));
                    border-radius:12px;padding:14px 16px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:4px">
            <div style="font-size:13px;font-weight:500">${this._esc(name)}</div>
            <div style="font-size:11px;opacity:.6">${this._esc(s4.entity_id)}</div>
          </div>
          <div style="margin:8px 0 4px;display:flex;gap:16px;font-size:12px">
            <span>开启 <b>${onLabel}</b></span>
            <span style="color:${barColor}">空房间浪费 <b>${wasteLabel}</b>
              ${wasteRatio > 0 ? `<span style="opacity:.6">(${wasteRatio}%)</span>` : ""}
            </span>
            <span style="opacity:.5">开启 ${s4.on_count} 次</span>
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

  // custom_components/smart_agent/frontend/src/render/profiles.js
  var profilesMethods = {
    _renderProfs() {
      const allRules = this._wsGet("rules", "rules", []);
      const h3 = this.shadowRoot.getElementById("hList"), r9 = this.shadowRoot.getElementById("rList");
      if (!this._wsData["habits"]) {
        this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
        return;
      }
      const allHabits = this._wsGet("habits", "habits", []);
      const userRules = allRules.filter((i8) => !i8.is_ai);
      h3.innerHTML = this._drawList(allHabits, "habit");
      r9.innerHTML = this._drawList(userRules, "rule");
      this.shadowRoot.querySelectorAll(".prof-lock").forEach((b3) => {
        b3.onclick = async () => {
          try {
            await this._callService("smart_agent", "toggle_" + b3.dataset.t + "_lock", {
              content: b3.dataset.c
            });
            this._msg(b3.dataset.lk === "1" ? "配置已解锁" : "配置已锁定");
            delete this._wsData["rules"];
            delete this._wsData["habits"];
            await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
              await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
            });
          } catch (e9) {
            this._msg("操作失败: " + e9.message);
          }
        };
      });
      this.shadowRoot.querySelectorAll(".prof-del").forEach((b3) => {
        b3.onclick = async () => {
          if (b3.disabled)
            return;
          try {
            await this._callService("smart_agent", "delete_" + b3.dataset.t, {
              content: b3.dataset.c
            });
            this._msg("已删除");
            delete this._wsData["rules"];
            delete this._wsData["habits"];
            await this._wsRefresh("smart_agent/get_rules", "rules", async () => {
              await this._wsRefresh("smart_agent/get_habits", "habits", () => this._renderProfs());
            });
          } catch (e9) {
            this._msg("删除失败: " + e9.message);
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
      items.forEach((i8) => {
        const ec = this._esc(i8.content);
        const itemBg = i8.locked ? "background:var(--sa-secondary-container);opacity:.8" : "";
        html += `
        <div class="m3-item" style="${itemBg}">
          <div class="m3-content">
            <div class="body-m" style="word-break:break-all">${ec}</div>
          </div>
          <div style="display:flex;gap:4px">
            <md-icon-button class="prof-lock" style="${i8.locked ? "background:var(--sa-secondary-container)" : ""}"
              data-t="${type}" data-c="${ec}" data-lk="${i8.locked ? "1" : "0"}"
              title="${i8.locked ? "解锁（允许 AI 自动修改）" : "锁定（防止 AI 反向操作）"}">
              ${i8.locked ? lockIco : unlockIco}
            </md-icon-button>
            <md-icon-button class="prof-del" style="color:var(--sa-error)" data-t="${type}" data-c="${ec}"
              ${i8.locked ? "disabled" : ""} title="删除">
              ${delIco}
            </md-icon-button>
          </div>
        </div>`;
      });
      return html + `</div>`;
    }
  };

  // custom_components/smart_agent/frontend/src/render/config.js
  var configMethods = {
    _renderConfig() {
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const ICO = this._getIcons();
      const cfg = this._cfg.attributes || {};
      const container = $3("configArea");
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
                <md-outlined-text-field id="cfg_brand_logo"
                  value="${this._esc(cfg.brand_logo_url || "")}"
                  placeholder="https://example.com/logo.png"></md-outlined-text-field>
                <div class="body-s" style="opacity:.55;margin-top:3px">支持 PNG/SVG，建议 64×64 以上，留空使用默认图标</div>
              </div>
            </div>

            <div>
              <div class="label-s">品牌名称</div>
              <md-outlined-text-field id="cfg_brand_name"
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
                  placeholder="#6750A4" maxlength="7"></md-outlined-text-field>
              </div>
              <div class="body-s" style="opacity:.55;margin-top:3px">作用于按钮、选中状态、高亮元素</div>
            </div>

            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-s">部署点标识名</div>
              <md-outlined-text-field id="cfg_deploy_name"
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
                <md-outlined-text-field id="cfg_ollama_url" value="${this._esc(cfg.ollama_url || "")}" placeholder="http://127.0.0.1:11434"></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">Ollama 模型名称</div>
                <md-outlined-text-field id="cfg_ollama_model" value="${this._esc(cfg.ollama_model || "")}" placeholder="qwen3-smarthome"></md-outlined-text-field>
              </div>
            </div>
            <div id="cfg_online_group" style="display:${cfg.engine === "online" ? "grid" : "none"};gap:12px">
              <div>
                <div class="label-s">API Base URL</div>
                <md-outlined-text-field id="cfg_online_base_url" value="${this._esc(cfg.online_base_url || "")}" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">API Key</div>
                <md-outlined-text-field id="cfg_online_api_key" type="password" value="${this._esc(cfg.online_api_key || "")}" placeholder="sk-xxxx..."></md-outlined-text-field>
              </div>
              <div>
                <div class="label-s">模型名称</div>
                <md-outlined-text-field id="cfg_online_model" value="${this._esc(cfg.online_model || "")}" placeholder="qwen-turbo"></md-outlined-text-field>
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
              <md-outlined-text-field id="cfg_tts_service" value="${this._esc(cfg.tts_service || "")}" placeholder="tts.google_translate_say"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">目标媒体播放器</div>
              <md-outlined-text-field id="cfg_tts_target" value="${this._esc(cfg.tts_target || "")}" placeholder="media_player.bedroom_speaker"></md-outlined-text-field>
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
              <md-outlined-text-field id="cfg_vision_model" value="${this._esc(cfg.vision_model || "")}" placeholder="qwen-vl-max"></md-outlined-text-field>
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
              <md-outlined-text-field id="cfg_qweather_api_key" type="password" value="${this._esc(cfg.qweather_api_key || "")}" placeholder="用于获取精准天气预报"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">SearXNG URL</div>
              <md-outlined-text-field id="cfg_searxng_url" value="${this._esc(cfg.searxng_url || "")}" placeholder="用于 AI 联网搜索"></md-outlined-text-field>
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
              <md-outlined-text-field id="cfg_cooldown" type="number" value="${cfg.cooldown || 60}"></md-outlined-text-field>
            </div>
            <div style="padding-top:8px;border-top:1px solid var(--sa-border)">
              <div class="label-m">${ICO.calendar} 日志保留天数</div>
              <div class="body-s" style="margin:4px 0 8px">文件日志每天零点轮转，超期自动删除（最小 3 天，最大 90 天）</div>
              <md-outlined-text-field id="cfg_log_retention" type="number" min="3" max="90" value="${cfg.log_retention_days || 30}"></md-outlined-text-field>
            </div>
            <div>
              <div class="label-s">License Key</div>
              <md-outlined-text-field id="cfg_license_key" type="password" value="${this._esc(cfg.license_key || "")}" placeholder="企业版/商业授权码"></md-outlined-text-field>
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
      const engSel = $3("cfg_engine");
      if (engSel)
        engSel.onchange = () => {
          $3("cfg_local_group").style.display = engSel.value === "local" ? "grid" : "none";
          $3("cfg_online_group").style.display = engSel.value === "online" ? "grid" : "none";
        };
      $3("cfgSaveBtn").onclick = () => this._saveSystemConfig();
      $3("cfgTestTts").onclick = () => this._callService("smart_agent", "tts_test", {}).catch(
        (e9) => this._msg("TTS 测试失败: " + String(e9.message || e9))
      );
      const screenUrl = `${location.origin}/smart_agent_screen/index.html`;
      const pairUrlEl = $3("pairUrl");
      if (pairUrlEl)
        pairUrlEl.textContent = screenUrl;
      const pairCopyBtn = $3("pairCopyBtn");
      if (pairCopyBtn) {
        pairCopyBtn.onclick = () => {
          var _a3;
          (_a3 = navigator.clipboard) == null ? void 0 : _a3.writeText(screenUrl).then(() => {
            pairCopyBtn.textContent = "✅ 已复制";
            setTimeout(() => {
              pairCopyBtn.textContent = "复制";
            }, 2e3);
          });
        };
      }
      const pairBtn = $3("pairBtn");
      if (pairBtn) {
        pairBtn.onclick = () => this._startPairing();
      }
      this._updateBizStatus();
      this._initZoneRoleUI(cfg);
      this._initSensorConfigUI();
      const colorPicker = $3("cfg_brand_color");
      const colorHex = $3("cfg_brand_color_hex");
      const logoInput = $3("cfg_brand_logo");
      const logoPreview = $3("brandLogoPreview");
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
      var _a3, _b;
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const pairBtn = $3("pairBtn");
      const pairStatus = $3("pairStatus");
      const pairCountdown = $3("pairCountdown");
      if (!pairBtn || !pairStatus || !pairCountdown)
        return;
      pairBtn.disabled = true;
      pairBtn.textContent = "正在生成配对凭证...";
      try {
        if (this._isHaFallbackReadOnly()) {
          this._warnHaFallbackReadOnly();
          pairBtn.disabled = false;
          pairBtn.textContent = "📱 开启极速配对（60 秒）";
          return;
        }
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
        const errMsg = (err == null ? void 0 : err.message) || ((_a3 = err == null ? void 0 : err.body) == null ? void 0 : _a3.message) || ((_b = err == null ? void 0 : err.body) == null ? void 0 : _b.error) || ((err == null ? void 0 : err.statusCode) ? `HTTP ${err.statusCode}` : null) || (typeof err === "string" ? err : null) || JSON.stringify(err) || "未知错误";
        this._msg("❌ 配对请求失败：" + errMsg);
        console.error("[SmartAgent] 配对失败详情:", err);
        pairBtn.disabled = false;
        pairBtn.textContent = "📱 开启极速配对（60 秒）";
      }
    },
    async _saveSystemConfig() {
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const timeToMin = (t6) => {
        if (!t6)
          return null;
        const [h3, m3] = t6.split(":").map(Number);
        return h3 * 60 + (m3 || 0);
      };
      const data = {
        engine: $3("cfg_engine").value,
        ollama_url: $3("cfg_ollama_url").value,
        ollama_model: $3("cfg_ollama_model").value,
        online_base_url: $3("cfg_online_base_url").value,
        online_model: $3("cfg_online_model").value,
        tts_service: $3("cfg_tts_service").value,
        tts_target: $3("cfg_tts_target").value,
        tts_level: parseInt($3("cfg_tts_level").value),
        vision_engine: $3("cfg_vision_engine").value,
        vision_model: $3("cfg_vision_model").value,
        searxng_url: $3("cfg_searxng_url").value,
        cloud_fallback: $3("cfg_cloud_fallback").checked,
        cooldown: parseInt($3("cfg_cooldown").value),
        log_retention_days: Math.max(3, Math.min(90, parseInt($3("cfg_log_retention").value) || 30)),
        license_key: $3("cfg_license_key").value
      };
      const onlineApiKey = $3("cfg_online_api_key").value.trim();
      const qweatherApiKey = $3("cfg_qweather_api_key").value.trim();
      if (onlineApiKey && !onlineApiKey.includes("****"))
        data.online_api_key = onlineApiKey;
      if (qweatherApiKey && !qweatherApiKey.includes("****"))
        data.qweather_api_key = qweatherApiKey;
      const brandName = $3("cfg_brand_name");
      const brandColor = $3("cfg_brand_color_hex");
      const brandLogo = $3("cfg_brand_logo");
      const deployName = $3("cfg_deploy_name");
      if (brandName)
        data.brand_name = brandName.value.trim() || "SmartAgent";
      if (brandColor)
        data.brand_primary_color = brandColor.value.trim() || "#6750A4";
      if (brandLogo)
        data.brand_logo_url = brandLogo.value.trim();
      if (deployName)
        data.deploy_name = deployName.value.trim();
      const bizStart = $3("cfg_biz_start");
      const bizEnd = $3("cfg_biz_end");
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
          var _a3, _b, _c;
          const areaVal = (_b = (_a3 = row.querySelector(".zone-area-select")) == null ? void 0 : _a3.value) == null ? void 0 : _b.trim();
          const role = (_c = row.querySelector(".zone-role-select")) == null ? void 0 : _c.value;
          if (areaVal && role)
            zoneMap[areaVal] = role;
        });
      }
      data.showroom_zone_map = JSON.stringify(zoneMap);
      try {
        await this._callService("smart_agent", "update_config", data);
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
      const haAreaNames = new Set(Object.values(rawAreas).map((a4) => a4.name));
      const idToName = {};
      Object.entries(rawAreas).forEach(([id, a4]) => {
        idToName[id] = a4.name;
      });
      const haAreas = Object.values(rawAreas).sort((a4, b3) => a4.name.localeCompare(b3.name, "zh-CN")).map((a4) => ({ id: a4.name, label: a4.name }));
      const haAreaIds = haAreaNames;
      const ROLE_OPTIONS = [
        { value: "display", label: "🏬 展示区" },
        { value: "experience", label: "✨ 体验区" },
        { value: "work", label: "💼 工作区" }
      ];
      const getSelected = () => {
        const sel = [];
        list.querySelectorAll(".zone-area-select").forEach((s4) => {
          if (s4.value)
            sel.push(s4.value);
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
          const ph = document.createElement("md-select-option");
          ph.value = "";
          ph.innerHTML = '<div slot="headline">请选择区域…</div>';
          sel.appendChild(ph);
          haAreas.forEach((a4) => {
            if (selected.includes(a4.id) && a4.id !== cur)
              return;
            const o10 = document.createElement("md-select-option");
            o10.value = a4.id;
            o10.innerHTML = `<div slot="headline">${a4.label}</div>`;
            if (a4.id === cur)
              o10.selected = true;
            sel.appendChild(o10);
          });
          if (!cur)
            sel.value = "";
        });
      };
      const createRow = (areaName = "", role = "experience") => {
        const row = document.createElement("div");
        row.className = "zone-role-row";
        row.style.cssText = "display:flex;align-items:center;gap:8px";
        const areaSelect = document.createElement("md-outlined-select");
        areaSelect.className = "zone-area-select";
        areaSelect.style.cssText = "flex:1;min-width:0;height:36px;font-size:13px";
        const ph = document.createElement("md-select-option");
        ph.value = "";
        ph.innerHTML = '<div slot="headline">请选择区域…</div>';
        areaSelect.appendChild(ph);
        const nameInList = haAreas.some((a4) => a4.id === areaName);
        if (areaName && !nameInList) {
          const kept = document.createElement("md-select-option");
          kept.value = areaName;
          kept.innerHTML = `<div slot="headline">${areaName}</div>`;
          kept.selected = true;
          areaSelect.appendChild(kept);
        }
        haAreas.forEach((a4) => {
          const o10 = document.createElement("md-select-option");
          o10.value = a4.id;
          o10.innerHTML = `<div slot="headline">${a4.label}</div>`;
          if (a4.id === areaName)
            o10.selected = true;
          areaSelect.appendChild(o10);
        });
        areaSelect.onchange = () => refreshAllAreaSelects();
        const roleSelect = document.createElement("md-outlined-select");
        roleSelect.className = "zone-role-select";
        roleSelect.style.cssText = "width:152px;flex-shrink:0;height:36px;font-size:13px";
        ROLE_OPTIONS.forEach((opt) => {
          const o10 = document.createElement("md-select-option");
          o10.value = opt.value;
          o10.innerHTML = `<div slot="headline">${opt.label}</div>`;
          if (opt.value === role)
            o10.selected = true;
          roleSelect.appendChild(o10);
        });
        const delBtn = document.createElement("md-icon-button");
        delBtn.className = "help-close";
        delBtn.title = "删除此区域";
        delBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
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
      } catch (_2) {
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
        var _a3, _b;
        list.appendChild(createRow());
        refreshAllAreaSelects();
        (_b = (_a3 = list.lastElementChild) == null ? void 0 : _a3.querySelector(".zone-area-select")) == null ? void 0 : _b.focus();
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
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const tabType = $3("sensorTabType");
      const tabFusion = $3("sensorTabFusion");
      const panelType = $3("sensorPanelType");
      const panelFusion = $3("sensorPanelFusion");
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
        const loading = $3("sensorTypeLoading");
        if (loading)
          loading.textContent = "❌ 加载失败: " + String(err.message || err);
        return;
      }
      this._sensorData = sensorData;
      this._renderSensorTypeList(sensorData.sensors);
      this._renderFusionScopes(sensorData.fusion_config, sensorData.rooms, sensorData.sensors);
    },
    _renderSensorTypeList(sensors) {
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const loading = $3("sensorTypeLoading");
      const list = $3("sensorTypeList");
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
      sensors.forEach((s4) => {
        const row = document.createElement("div");
        row.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;background:var(--sa-card);border:1px solid var(--sa-border)";
        const dot = s4.state === "on" ? "#4caf50" : s4.state === "off" ? "#9e9e9e" : "#ff9800";
        const inSaBadge = s4.in_sa ? `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:var(--sa-primary-container);color:var(--sa-primary)">SA已注册</span>` : `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:rgba(0,0,0,.07);color:var(--sa-text-variant)">未注册</span>`;
        const fusionBadge = s4.fusion_scope ? `<span style="font-size:10px;padding:1px 6px;border-radius:6px;background:var(--sa-secondary-container,rgba(100,180,255,.15));color:var(--sa-secondary,#1565c0)">
            融合域: ${this._esc(s4.fusion_scope)}</span>` : "";
        const selId = `stype_${s4.entity_id.replace(/\./g, "_")}`;
        const opts = SENSOR_TYPE_OPTIONS.map(
          (o10) => `<option value="${o10.value}" ${s4.sensor_type === o10.value ? "selected" : ""}>${o10.label}</option>`
        ).join("");
        row.innerHTML = `
        <span style="width:10px;height:10px;border-radius:50%;background:${dot};flex-shrink:0"></span>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${this._esc(s4.name)}
            <span style="font-size:11px;font-weight:400;margin-left:6px;opacity:.6">${this._esc(s4.room || "未分区")}</span>
          </div>
          <div style="font-size:11px;font-family:monospace;opacity:.5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${this._esc(s4.entity_id)}
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:3px">${inSaBadge}${fusionBadge}</div>
        </div>
        <md-outlined-select id="${selId}" style="width:160px;flex-shrink:0;font-size:12px">
          ${opts}
        </md-outlined-select>
        <md-filled-tonal-button class="stype-save-btn" data-eid="${this._esc(s4.entity_id)}" data-sel="${selId}"
          style="flex-shrink:0;--md-filled-tonal-button-container-height:32px;font-size:12px">保存</md-filled-tonal-button>
      `;
        list.appendChild(row);
      });
      list.addEventListener("click", async (e9) => {
        const btn = e9.target.closest(".stype-save-btn");
        if (!btn)
          return;
        if (this._isHaFallbackReadOnly()) {
          this._warnHaFallbackReadOnly();
          return;
        }
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
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const scopeList = $3("fusionScopeList");
      const addBtn = $3("addFusionScopeBtn");
      if (!scopeList || !addBtn)
        return;
      const sensorMap = new Map((sensors || []).map((s4) => [s4.entity_id, s4]));
      const roomList = Array.isArray(rooms) ? [...rooms] : [];
      const normalizeMember = (member) => {
        if (typeof member === "string") {
          return {
            entity_id: member,
            can_enter_trigger: true,
            can_leave_evidence: true,
            priority: 50,
            confidence: 1
          };
        }
        if (!member || typeof member !== "object") {
          return {
            entity_id: "",
            can_enter_trigger: true,
            can_leave_evidence: true,
            priority: 50,
            confidence: 1
          };
        }
        return {
          entity_id: String(member.entity_id || ""),
          can_enter_trigger: member.can_enter_trigger !== false,
          can_leave_evidence: member.can_leave_evidence !== false,
          priority: Number.isFinite(Number(member.priority)) ? Number(member.priority) : 50,
          confidence: Number.isFinite(Number(member.confidence)) ? Number(member.confidence) : 1
        };
      };
      const normalizeScope = (scope) => {
        const rawMembers = Array.isArray(scope == null ? void 0 : scope.members) ? scope.members : [];
        return {
          scope_id: String((scope == null ? void 0 : scope.scope_id) || ""),
          name: String((scope == null ? void 0 : scope.name) || ""),
          strategy: (scope == null ? void 0 : scope.strategy) === "vacant_and" ? "vacant_and" : "occupied_or",
          rooms: Array.isArray(scope == null ? void 0 : scope.rooms) ? scope.rooms.map((r9) => String(r9)).filter(Boolean) : [],
          members: rawMembers.map(normalizeMember).filter((m3) => m3.entity_id),
          enter_hold_secs: Number.isFinite(Number(scope == null ? void 0 : scope.enter_hold_secs)) ? Number(scope.enter_hold_secs) : 3,
          vacant_hold_secs: Number.isFinite(Number(scope == null ? void 0 : scope.vacant_hold_secs)) ? Number(scope.vacant_hold_secs) : 60
        };
      };
      let scopes = Array.isArray(fusionConfig) ? fusionConfig.map(normalizeScope) : [];
      const _save = async () => {
        try {
          await this._callService("smart_agent", "update_config", {
            presence_fusion: JSON.stringify(scopes)
          });
          this._msg("✅ 融合域配置已保存");
        } catch (err) {
          this._msg("❌ 保存失败: " + String(err.message || err));
        }
      };
      const memberName = (m3) => {
        const meta = sensorMap.get(m3.entity_id);
        return (meta == null ? void 0 : meta.name) || m3.entity_id.split(".").pop() || m3.entity_id;
      };
      const memberSummary = (members) => {
        const total = members.length;
        const enterCount = members.filter((m3) => m3.can_enter_trigger).length;
        const leaveCount = members.filter((m3) => m3.can_leave_evidence).length;
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
          const topMembers = sc.members.slice(0, 3).map((m3) => {
            const enter = m3.can_enter_trigger ? "入" : "";
            const leave = m3.can_leave_evidence ? "离" : "";
            return `${memberName(m3)}(${enter || "-"}/${leave || "-"})`;
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
        const sc = isNew ? {
          scope_id: "",
          name: "",
          strategy: "occupied_or",
          rooms: [],
          members: [],
          enter_hold_secs: 3,
          vacant_hold_secs: 60
        } : normalizeScope(scopes[idx]);
        const defaultPrimary = sc.rooms[0] || roomList[0] || "";
        const defaultNeighbors = sc.rooms.slice(1);
        const roomOptions = roomList.map((r9) => `<option value="${this._esc(r9)}">${this._esc(r9)}</option>`).join("");
        const sensorRows = (sensors || []).map((s4) => {
          const existing = sc.members.find((m4) => m4.entity_id === s4.entity_id);
          const m3 = existing || {
            entity_id: s4.entity_id,
            can_enter_trigger: true,
            can_leave_evidence: true,
            priority: 50,
            confidence: 1
          };
          const checked = existing ? "checked" : "";
          const roomTag = s4.room ? `<span style="opacity:.6">${this._esc(s4.room)}</span>` : '<span style="opacity:.4">未分区</span>';
          return `
          <div class="fe-member-row" data-eid="${this._esc(s4.entity_id)}" style="display:grid;grid-template-columns:minmax(160px,1fr) 84px 84px 92px 92px;gap:8px;align-items:center;padding:8px;border:1px solid var(--sa-border);border-radius:8px">
            <label style="display:flex;align-items:center;gap:8px;min-width:0">
              <input type="checkbox" class="fe-member-enable" ${checked}>
              <span style="display:flex;flex-direction:column;min-width:0">
                <span style="font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(s4.name)}</span>
                <span style="font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this._esc(s4.entity_id)} · ${roomTag}</span>
              </span>
            </label>
            <label style="font-size:11px;display:flex;align-items:center;gap:4px"><input type="checkbox" class="fe-member-enter" ${m3.can_enter_trigger ? "checked" : ""}>入场</label>
            <label style="font-size:11px;display:flex;align-items:center;gap:4px"><input type="checkbox" class="fe-member-leave" ${m3.can_leave_evidence ? "checked" : ""}>离场</label>
            <input class="fe-member-priority" type="number" min="0" max="100" value="${m3.priority}" style="width:100%;border:1px solid var(--sa-border);border-radius:6px;padding:6px;font-size:12px" title="优先级 0-100">
            <input class="fe-member-confidence" type="number" min="0" max="1" step="0.05" value="${m3.confidence}" style="width:100%;border:1px solid var(--sa-border);border-radius:6px;padding:6px;font-size:12px" title="置信度 0-1">
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
          const selected = new Set([...neighborSel.selectedOptions].map((o10) => o10.value));
          neighborSel.innerHTML = "";
          roomList.filter((r9) => r9 !== primary).forEach((r9) => {
            const op = document.createElement("option");
            op.value = r9;
            op.textContent = r9;
            if (selected.has(r9))
              op.selected = true;
            neighborSel.appendChild(op);
          });
        };
        const applyRoomSelection = (primary, neighbors) => {
          primarySel.value = primary || "";
          refreshNeighborOptions();
          const wanted = new Set((neighbors || []).filter((r9) => r9 !== primary));
          [...neighborSel.options].forEach((op) => {
            op.selected = wanted.has(op.value);
          });
        };
        const guessPreset = (pairs) => {
          const all = roomList;
          const pick = (patterns) => all.find((r9) => patterns.some((p4) => p4.test(r9)));
          for (const [aPatterns, bPatterns] of pairs) {
            const a4 = pick(aPatterns);
            const b3 = pick(bPatterns);
            if (a4 && b3 && a4 !== b3)
              return { primary: a4, neighbors: [b3] };
          }
          return null;
        };
        primarySel.onchange = () => refreshNeighborOptions();
        applyRoomSelection(defaultPrimary, defaultNeighbors);
        overlay.querySelector("#fe_preset_living").onclick = () => {
          const picked = guessPreset([
            [[/客厅/, /living/i], [/餐厅/, /dining/i]],
            [[/客餐/, /open/i], [/走廊/, /hall/i]]
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
            [[/卧室/, /bed/i], [/卫生间/, /bath/i]]
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
          const neighbors = [...neighborSel.selectedOptions].map((o10) => o10.value).filter(Boolean);
          const roomsSel = primary ? [primary, ...neighbors.filter((r9) => r9 !== primary)] : [];
          const members = [];
          overlay.querySelectorAll(".fe-member-row").forEach((row) => {
            var _a3, _b, _c, _d, _e;
            const enabled = (_a3 = row.querySelector(".fe-member-enable")) == null ? void 0 : _a3.checked;
            if (!enabled)
              return;
            const entityId = row.dataset.eid || "";
            if (!entityId)
              return;
            const priority = Number((_b = row.querySelector(".fe-member-priority")) == null ? void 0 : _b.value);
            const confidence = Number((_c = row.querySelector(".fe-member-confidence")) == null ? void 0 : _c.value);
            members.push({
              entity_id: entityId,
              can_enter_trigger: !!((_d = row.querySelector(".fe-member-enter")) == null ? void 0 : _d.checked),
              can_leave_evidence: !!((_e = row.querySelector(".fe-member-leave")) == null ? void 0 : _e.checked),
              priority: Number.isFinite(priority) ? Math.max(0, Math.min(100, priority)) : 50,
              confidence: Number.isFinite(confidence) ? Math.max(0, Math.min(1, confidence)) : 1
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
          if (!members.some((m3) => m3.can_enter_trigger)) {
            this._msg("至少需要一个可触发入场的成员");
            return;
          }
          if (!members.some((m3) => m3.can_leave_evidence)) {
            this._msg("至少需要一个可作为离场证据的成员");
            return;
          }
          const scopeId = sc.scope_id || nameVal.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, "_") || `scope_${Date.now()}`;
          const newScope = {
            scope_id: scopeId,
            name: nameVal,
            strategy,
            rooms: roomsSel,
            members,
            enter_hold_secs: enterHoldSecs,
            vacant_hold_secs: holdSecs
          };
          if (isNew)
            scopes.push(newScope);
          else
            scopes[idx] = newScope;
          _close();
          await _save();
          _render();
        };
      };
      scopeList.addEventListener("click", async (e9) => {
        var _a3;
        const editBtn = e9.target.closest(".fusion-edit-btn");
        const delBtn = e9.target.closest(".fusion-del-btn");
        if (editBtn)
          _showEditor(parseInt(editBtn.dataset.idx, 10));
        if (delBtn) {
          const i8 = parseInt(delBtn.dataset.idx, 10);
          if (!await this._showConfirm(`确认删除融合域「${((_a3 = scopes[i8]) == null ? void 0 : _a3.name) || i8}」？`))
            return;
          scopes.splice(i8, 1);
          _save().then(() => _render());
        }
      });
      addBtn.onclick = () => _showEditor(-1);
      _render();
    }
  };

  // custom_components/smart_agent/frontend/src/render/devices.js
  var devicesMethods = {
    _renderDevs() {
      const PAGE_SIZE = 20;
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const ICO = this._getIcons();
      const configured = new Set(this._wsGet("devices", "devices", []).map((d3) => d3.entity_id));
      const offlineToggle = $3("showOfflineToggle");
      if (offlineToggle && !offlineToggle._bound) {
        offlineToggle._bound = true;
        offlineToggle.checked = !!this._showOffline;
        offlineToggle.onchange = () => {
          this._showOffline = offlineToggle.checked;
          this._renderDevs();
        };
      }
      const ignoredToggle = $3("showIgnoredToggle");
      if (ignoredToggle && !ignoredToggle._bound) {
        ignoredToggle._bound = true;
        ignoredToggle.checked = !!this._showIgnored;
        ignoredToggle.onchange = () => {
          this._showIgnored = ignoredToggle.checked;
          this._renderDevs();
        };
      }
      const discoverBtn = $3("discoverBtn");
      if (discoverBtn && !discoverBtn._bound) {
        discoverBtn._bound = true;
        discoverBtn.onclick = async () => {
          discoverBtn.classList.add("loading");
          try {
            await this._callService("smart_agent", "discover_devices", {});
            this._msg("扫描完成，正在刷新列表...");
            delete this._wsData["devices"];
            await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
          } catch (e9) {
            this._msg("扫描失败: " + e9.message);
          } finally {
            setTimeout(() => discoverBtn.classList.remove("loading"), 500);
          }
        };
      }
      const syncToHaBtn = $3("syncToHaBtn");
      if (syncToHaBtn && !syncToHaBtn._bound) {
        syncToHaBtn._bound = true;
        syncToHaBtn.onclick = async () => {
          syncToHaBtn.classList.add("loading");
          try {
            await this._callService("smart_agent", "sync_rooms_to_ha", {});
            this._msg("同步完成！AI 分区已应用到 HA 区域注册表。");
            this._renderDevs();
          } catch (e9) {
            this._msg("同步失败: " + e9.message);
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
        return ["_detect", "_motion", "_improve_contrast", "_autotracking"].some((s4) => obj.endsWith(s4));
      };
      let allNew = Object.values(this._hass.states).filter((s4) => {
        var _a3;
        const d3 = s4.entity_id.split(".")[0];
        if (!TARGET_DOMAINS.includes(d3))
          return false;
        if (!showIgnored) {
          if (SKIP_KW.some((k2) => s4.entity_id.includes(k2)))
            return false;
          if (_isFrigateControl(s4.entity_id))
            return false;
          const n9 = ((_a3 = s4.attributes) == null ? void 0 : _a3.friendly_name) || "";
          if (SKIP_NAME_KW.some((k2) => n9.toLowerCase().includes(k2.toLowerCase())))
            return false;
        }
        return !configured.has(s4.entity_id);
      }).map((s4) => ({
        id: s4.entity_id,
        n: s4.attributes.friendly_name || s4.entity_id,
        d: s4.entity_id.split(".")[0],
        s: s4.state,
        area: _haAreaMap[s4.entity_id] || "",
        unavail: ["unavailable", "unknown"].includes(s4.state)
      }));
      const showOffline = this._showOffline || false;
      const filteredNew = showOffline ? allNew : allNew.filter((i8) => !i8.unavail);
      const newTypes = [...new Set(allNew.map((i8) => i8.d))].sort();
      const dtf = $3("devTypeFilter");
      const activeNT = this._newTypeFilter || "all";
      const newSearchEl = $3("newDevSearch");
      if (newSearchEl && !newSearchEl._bound) {
        newSearchEl._bound = true;
        newSearchEl.oninput = () => {
          this._newSearchKw = newSearchEl.value;
          this._newPage = 0;
          this._renderDevs();
        };
      }
      const newKw = (this._newSearchKw || "").trim().toLowerCase();
      dtf.innerHTML = ["all", ...newTypes].map((t6) => {
        const cnt = t6 === "all" ? filteredNew.length : filteredNew.filter((i8) => i8.d === t6).length;
        if (t6 !== "all" && cnt === 0)
          return "";
        const label = t6 === "all" ? "全部" : DOMAIN_LABELS[t6] || this._esc(t6);
        return `<md-filter-chip class="ntf-btn" ${activeNT === t6 ? "selected" : ""} data-t="${this._esc(t6)}" label="${label} (${cnt})"></md-filter-chip>`;
      }).join("");
      dtf.querySelectorAll(".ntf-btn").forEach((b3) => b3.onclick = () => {
        this._newTypeFilter = b3.dataset.t;
        this._newPage = 0;
        this._renderDevs();
      });
      const typeFiltered0 = activeNT === "all" ? filteredNew : filteredNew.filter((i8) => i8.d === activeNT);
      const typeFiltered = newKw ? typeFiltered0.filter((i8) => i8.n.toLowerCase().includes(newKw) || i8.id.toLowerCase().includes(newKw)) : typeFiltered0;
      const totalNew = typeFiltered.length;
      const totalNewPages = Math.ceil(totalNew / PAGE_SIZE) || 1;
      if (this._newPage >= totalNewPages)
        this._newPage = totalNewPages - 1;
      const pageItems = typeFiltered.slice(this._newPage * PAGE_SIZE, (this._newPage + 1) * PAGE_SIZE);
      $3("nCntLbl").textContent = this._selectedNew.size ? `${this._selectedNew.size} 已选` : `${totalNew} 个新设备`;
      const nt = $3("nTable");
      if (!typeFiltered.length) {
        nt.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">📡</div>
        <div class="empty-state-title">暂无发现新设备</div>
        <div class="empty-state-desc">所有可用设备已添加，或点击「扫描」重新发现</div>
      </div>`;
      } else {
        let html = `<div class="m3-list">`;
        pageItems.forEach((i8) => {
          const isSelected = this._selectedNew.has(i8.id);
          html += `
          <div class="m3-item dev-row ${isSelected ? "selected" : ""} ${i8.unavail ? "dev-unavail" : ""}" data-id="${this._esc(i8.id)}" data-type="new" style="cursor:pointer">
            <md-checkbox ${isSelected ? "checked" : ""} aria-checked="${isSelected}"></md-checkbox>
            <div class="m3-icon">${ICO[i8.d] || ICO.device}</div>
            <div class="m3-content">
              <div class="m3-title">${this._esc(i8.n)}</div>
              <div class="m3-subtitle">${this._esc(i8.id)}${i8.area ? ` · <span style="color:var(--sa-primary)">${this._esc(i8.area)}</span>` : ""}</div>
            </div>
            <div class="body-s" style="text-align:right;flex-shrink:0">${i8.unavail ? '<span style="color:var(--sa-state-offline)">离线</span>' : this._esc(i8.s)}</div>
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
      this._renderPager($3("nPager"), this._newPage, totalNewPages, (p4) => {
        this._newPage = p4;
        this._renderDevs();
      });
      const cAll = this._wsGet("devices", "devices", []);
      const cfgRooms = [
        ...new Set(cAll.map((i8) => i8.room || "（未分区）"))
      ].sort((a4, b3) => {
        if (a4 === "（未分区）")
          return 1;
        if (b3 === "（未分区）")
          return -1;
        return a4.localeCompare(b3, "zh");
      });
      const activeRoom = this._cfgRoomFilter || "all";
      const noRoomCnt = cAll.filter((d3) => !d3.room).length;
      const rrf = $3("cfgRoomFilter");
      if (rrf) {
        rrf.innerHTML = [
          { key: "all", label: `全部房间`, cnt: cAll.length },
          ...cfgRooms.map((r9) => ({
            key: r9,
            label: r9 === "（未分区）" ? `⚠ 未分区` : r9,
            cnt: cAll.filter((i8) => (i8.room || "（未分区）") === r9).length
          }))
        ].map(({ key, label, cnt }) => {
          const isUnassigned = key === "（未分区）";
          const isActive = activeRoom === key;
          const baseStyle = isUnassigned && !isActive ? "--md-filter-chip-container-color:var(--sa-err-container);--md-filter-chip-label-text-color:var(--sa-err);" : "";
          return `<md-filter-chip class="crf-btn" ${isActive ? "selected" : ""}
          data-r="${this._esc(key)}" label="${this._esc(label)} (${cnt})" style="${baseStyle}">
        </md-filter-chip>`;
        }).join("");
        rrf.querySelectorAll(".crf-btn").forEach((b3) => b3.onclick = () => {
          var _a3;
          const newRoom = b3.dataset.r;
          if (newRoom !== (this._cfgRoomFilter || "all")) {
            this._cfgTypeFilter = "all";
            this._selectedCfg.clear();
            (_a3 = this._updateBatchFab) == null ? void 0 : _a3.call(this);
          }
          this._cfgRoomFilter = newRoom;
          this._cfgPage = 0;
          this._renderDevs();
        });
        if (noRoomCnt === 0) {
          rrf.querySelectorAll(".crf-btn").forEach((b3) => {
            if (b3.dataset.r === "（未分区）")
              b3.style.display = "none";
          });
        }
      }
      const noRoomBtn = $3("filterNoRoomBtn");
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
      const cAllRoom = activeRoom === "all" ? cAll : cAll.filter((i8) => (i8.room || "（未分区）") === activeRoom);
      const cfgTypes = [...new Set(cAllRoom.map((i8) => i8.type || "其他"))].sort();
      const ctf = $3("cfgTypeFilter");
      const activeCT = this._cfgTypeFilter || "all";
      const cfgSearchEl = $3("cfgDevSearch");
      if (cfgSearchEl && !cfgSearchEl._bound) {
        cfgSearchEl._bound = true;
        cfgSearchEl.oninput = () => {
          this._cfgSearchKw = cfgSearchEl.value;
          this._cfgPage = 0;
          this._renderDevs();
        };
      }
      const cfgKw = (this._cfgSearchKw || "").trim().toLowerCase();
      ctf.innerHTML = ["all", ...cfgTypes].map((t6) => {
        const cnt = t6 === "all" ? cAllRoom.length : cAllRoom.filter((i8) => (i8.type || "其他") === t6).length;
        if (t6 !== "all" && cnt === 0)
          return "";
        const label = t6 === "all" ? "全部类型" : DOMAIN_LABELS[t6] || this._esc(t6);
        return `<md-filter-chip class="ctf-btn" ${activeCT === t6 ? "selected" : ""} data-t="${this._esc(t6)}" label="${label} (${cnt})"></md-filter-chip>`;
      }).join("");
      ctf.querySelectorAll(".ctf-btn").forEach((b3) => b3.onclick = () => {
        this._cfgTypeFilter = b3.dataset.t;
        this._cfgPage = 0;
        this._renderDevs();
      });
      let cfgFiltered0 = cAllRoom;
      if (activeCT !== "all")
        cfgFiltered0 = cfgFiltered0.filter((i8) => (i8.type || "其他") === activeCT);
      const cfgFiltered = cfgKw ? cfgFiltered0.filter((i8) => (i8.name || "").toLowerCase().includes(cfgKw) || (i8.entity_id || "").toLowerCase().includes(cfgKw) || (i8.room || "").toLowerCase().includes(cfgKw)) : cfgFiltered0;
      const totalCfg = cfgFiltered.length;
      const totalCfgPages = Math.ceil(totalCfg / PAGE_SIZE) || 1;
      if (this._cfgPage >= totalCfgPages)
        this._cfgPage = totalCfgPages - 1;
      const cfgPageSlice = cfgFiltered.slice(this._cfgPage * PAGE_SIZE, (this._cfgPage + 1) * PAGE_SIZE);
      const _hasFilter = activeRoom !== "all" || activeCT !== "all" || cfgKw;
      $3("cCntLbl").textContent = this._selectedCfg.size ? `${this._selectedCfg.size} 已选` : _hasFilter ? `${totalCfg} / ${cAll.length} 个已托管` : `${totalCfg} 个已托管`;
      const ct = $3("cTable");
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
            const s4 = $3("cfgDevSearch");
            if (s4)
              s4.value = "";
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
          var _a3, _b, _c;
          const st = (((_a3 = this._hass) == null ? void 0 : _a3.states) || {})[entityId];
          if (!st)
            return null;
          const s4 = st.state;
          if (["unavailable", "unknown"].includes(s4))
            return { text: "离线", ok: false };
          const domain = entityId.split(".")[0];
          if (domain === "light" || domain === "switch" || domain === "fan") {
            return { text: s4 === "on" ? "开" : "关", ok: s4 === "on" };
          }
          if (domain === "binary_sensor") {
            return { text: s4 === "on" ? "触发" : "正常", ok: s4 === "on" };
          }
          if (domain === "climate") {
            const temp = (_b = st.attributes) == null ? void 0 : _b.current_temperature;
            return { text: temp != null ? `${temp}℃` : s4 === "off" ? "关" : s4, ok: s4 !== "off" };
          }
          if (domain === "cover") {
            return { text: s4 === "open" ? "开" : s4 === "closed" ? "关" : s4, ok: s4 === "open" };
          }
          if (domain === "sensor") {
            const unit = ((_c = st.attributes) == null ? void 0 : _c.unit_of_measurement) || "";
            return { text: `${s4}${unit}`.substring(0, 10), ok: true };
          }
          return { text: String(s4).substring(0, 10), ok: true };
        };
        const roomGroups = {};
        cfgPageSlice.forEach((i8) => {
          const room = i8.room || "（未分区）";
          if (!roomGroups[room])
            roomGroups[room] = [];
          roomGroups[room].push(i8);
        });
        const sortedRooms = Object.keys(roomGroups).sort((a4, b3) => {
          if (a4 === "（未分区）")
            return 1;
          if (b3 === "（未分区）")
            return -1;
          return a4.localeCompare(b3, "zh");
        });
        let html = "";
        sortedRooms.forEach((room) => {
          const items = roomGroups[room];
          const isUnassigned = room === "（未分区）";
          const typeCounts = {};
          items.forEach((i8) => {
            const t6 = i8.type || "其他";
            typeCounts[t6] = (typeCounts[t6] || 0) + 1;
          });
          const typeBreakdown = Object.entries(typeCounts).map(([t6, n9]) => `<span style="font-size:11px;padding:1px 7px;border-radius:8px;
            background:var(--sa-primary-container);color:var(--sa-on-primary-container)">${this._esc(t6)} ${n9}</span>`).join("");
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
          items.forEach((i8) => {
            const domain = (i8.entity_id || "").split(".")[0];
            const mode = i8.control_mode || "shared";
            const modeCfg = MODE_CFG[mode] || MODE_CFG.shared;
            const isSelected = this._selectedCfg.has(i8.entity_id);
            const stLabel = _stateLabel(i8.entity_id);
            const isOnline = stLabel ? stLabel.ok !== false && stLabel.text !== "离线" : null;
            const eidDisplay = i8.entity_id.length > 40 ? `…${i8.entity_id.slice(-38)}` : i8.entity_id;
            html += `
              <div class="dev-row" data-id="${this._esc(i8.entity_id)}" data-type="cfg"
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
                              text-overflow:ellipsis">${this._esc(i8.name)}</div>
                  <div style="font-size:11px;color:var(--sa-text-variant);font-family:monospace;
                              white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                              margin-top:1px" title="${this._esc(i8.entity_id)}">${this._esc(eidDisplay)}</div>
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
                <md-icon-button class="help-close single-edit-btn"
                  data-id="${this._esc(i8.entity_id)}"
                  data-name="${this._esc(i8.name)}"
                  data-room="${this._esc(i8.room || "")}"
                  data-type="${this._esc(i8.type || "")}"
                  title="编辑" style="flex-shrink:0;color:var(--sa-text-variant)">
                  ${ICO.edit}
                </md-icon-button>
                <md-icon-button class="help-close single-del-btn"
                  data-id="${this._esc(i8.entity_id)}"
                  data-name="${this._esc(i8.name)}"
                  title="停止托管" style="flex-shrink:0;color:var(--sa-text-variant)">
                  ${ICO.delete}
                </md-icon-button>
              </div>`;
          });
          html += `</div></div>`;
        });
        ct.innerHTML = html;
        ct.querySelectorAll(".dev-row").forEach((el) => {
          el.onclick = (e9) => {
            if (e9.target.closest(".single-del-btn") || e9.target.closest(".single-edit-btn"))
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
          btn.onclick = async (e9) => {
            e9.stopPropagation();
            const id = btn.dataset.id, name = btn.dataset.name;
            if (!await this._showConfirm(`确定要停止托管设备「${name || id}」吗？`))
              return;
            try {
              await this._callService("smart_agent", "delete_device", { entity_id: id });
              this._msg("已停止托管该设备");
              delete this._wsData["devices"];
              await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
            } catch (err) {
              this._msg("操作失败: " + err.message);
            }
          };
        });
        ct.querySelectorAll(".single-edit-btn").forEach((btn) => {
          btn.onclick = async (e9) => {
            e9.stopPropagation();
            await this._showEditDevDialog(
              btn.dataset.id,
              btn.dataset.name,
              btn.dataset.room,
              btn.dataset.type
            );
          };
        });
      }
      this._renderPager($3("cPager"), this._cfgPage, totalCfgPages, (p4) => {
        this._cfgPage = p4;
        this._renderDevs();
      });
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(this.shadowRoot, "#discoverBtn,#syncToHaBtn,.single-del-btn,.single-edit-btn");
      }
    }
  };

  // custom_components/smart_agent/frontend/src/render/rooms.js
  var roomsMethods = {
    _renderRooms() {
      const view = this.shadowRoot.getElementById("view-rooms");
      if (!view)
        return;
      const ADJ_SEP = "||";
      const adjKey = (a4, b3) => a4 < b3 ? `${a4}${ADJ_SEP}${b3}` : `${b3}${ADJ_SEP}${a4}`;
      const parseAdjKey = (key) => {
        const idx = key.indexOf(ADJ_SEP);
        return idx < 0 ? ["", ""] : [key.slice(0, idx), key.slice(idx + ADJ_SEP.length)];
      };
      const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a4) => a4.name) : [];
      const devices = this._wsGet("devices", "devices", []);
      const devRooms = devices.map((d3) => d3.room || "").filter((r9) => r9);
      const customRooms = Array.isArray(this._customRooms) ? this._customRooms : [];
      const rooms = [.../* @__PURE__ */ new Set([...haAreas, ...devRooms, ...customRooms])].filter((r9) => r9 && r9.trim()).sort((a4, b3) => a4.localeCompare(b3, "zh"));
      if (!this._roomAdj)
        this._roomAdj = {};
      const adj = this._roomAdj;
      const isAdj = (a4, b3) => !!adj[adjKey(a4, b3)];
      const setAdj = (a4, b3, val) => {
        const key = adjKey(a4, b3);
        if (val)
          adj[key] = true;
        else
          delete adj[key];
      };
      const clearAdj = () => {
        Object.keys(adj).forEach((k2) => delete adj[k2]);
      };
      const neighborMap = new Map(rooms.map((r9) => [r9, []]));
      Object.keys(adj).forEach((k2) => {
        const [a4, b3] = parseAdjKey(k2);
        if (!adj[k2] || !a4 || !b3 || !neighborMap.has(a4) || !neighborMap.has(b3))
          return;
        neighborMap.get(a4).push(b3);
        neighborMap.get(b3).push(a4);
      });
      const neighborsOf = (r9) => neighborMap.get(r9) || [];
      const editorRoom = this._roomEditorRoom && rooms.includes(this._roomEditorRoom) ? this._roomEditorRoom : rooms[0] || "";
      this._roomEditorRoom = editorRoom;
      const editorIdx = rooms.indexOf(editorRoom);
      const sortedPairs = [];
      for (let i8 = 0; i8 < rooms.length - 1; i8++)
        sortedPairs.push([i8, i8 + 1]);
      const applyPreset = (preset) => {
        clearAdj();
        if (!rooms.length)
          return;
        if (preset === "chain") {
          sortedPairs.forEach(([a4, b3]) => setAdj(rooms[a4], rooms[b3], true));
          this._msg("已应用示例：线性串联关系");
        } else if (preset === "star") {
          const hub = editorRoom || rooms[0];
          rooms.forEach((r9) => {
            if (r9 !== hub)
              setAdj(r9, hub, true);
          });
          this._msg(`已应用示例：以“${hub}”为核心的广播式关系`);
        } else {
          this._msg("已应用示例：全部隔离");
        }
        this._renderRooms();
      };
      view.innerHTML = `
      <div class="main">
        <div class="card">
          <div class="card-title">房间拓扑配置</div>
          <div class="body-s" style="margin-top:4px;opacity:.7;line-height:1.6">
            配置房间相邻关系，AI 推理跨房间场景时会参考拓扑，避免“某些区域不该越界”的误触发。
          </div>
        </div>

        <div class="card">
          <div class="card-title">3 步就能配好</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;">
            <div style="padding:10px;border:1px solid var(--sa-border);border-radius:10px;background:var(--sa-bg)">
              <div style="font-weight:700;margin-bottom:4px">1. 先同步房间</div>
              <div class="body-s">从 HA 同步区域后会自动带入现有房间名；或手动添加自定义房间。</div>
            </div>
            <div style="padding:10px;border:1px solid var(--sa-border);border-radius:10px;background:var(--sa-bg)">
              <div style="font-weight:700;margin-bottom:4px">2. 按房间设置邻接</div>
              <div class="body-s">选择左侧“当前房间”，只需勾选与它直接相邻的房间。</div>
            </div>
            <div style="padding:10px;border:1px solid var(--sa-border);border-radius:10px;background:var(--sa-bg)">
              <div style="font-weight:700;margin-bottom:4px">3. 点保存立即生效</div>
              <div class="body-s">编辑后直接保存即可让 AI 推理使用新的邻接规则。</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:280px 1fr;gap:16px;align-items:start">
          <div class="card">
            <div class="card-title">房间列表 <span style="font-weight:400;opacity:.6">(${rooms.length})</span></div>
            <div id="roomList" style="display:flex;flex-direction:column;gap:8px;">
              ${rooms.map((r9, idx) => `
                <button
                  class="btn ${editorRoom === r9 ? "btn-filled" : "btn-tonal"} btn-sm"
                  style="justify-content:space-between;display:flex;align-items:center"
                  data-edit-room="${idx}">
                  <span>${this._esc(r9)}</span>
                  <span class="body-s" style="opacity:.7">${neighborsOf(r9).length} 相邻</span>
                </button>
              `).join("")}
              ${rooms.length === 0 ? `<div class="empty-state">暂无房间，请先同步区域或手动添加</div>` : ""}
            </div>

            <div style="margin-top:12px;display:flex;gap:8px">
              <md-outlined-text-field id="newRoomInput" label="添加自定义房间" style="flex:1"></md-outlined-text-field>
              <md-icon-button id="addRoomBtn" title="添加房间">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              </md-icon-button>
            </div>
          </div>

          <div class="card">
            <div class="card-title">当前房间：${this._esc(editorRoom || "未选择")}</div>
            <div class="body-s" style="margin:6px 0 10px;opacity:.7">
              勾选为当前房间设置“可连通”关系。勾选是双向生效的。
            </div>

            ${!editorRoom ? '<div class="empty-state">请先从左侧选择一个房间</div>' : `
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px">
                ${rooms.map((r9, idx) => r9 === editorRoom ? "" : `
                  <label class="btn btn-soft" style="justify-content:flex-start;display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:10px">
                    <md-checkbox
                      data-editor
                      data-a="${editorIdx}"
                      data-b="${idx}"
                      ${isAdj(editorRoom, r9) ? "checked" : ""}
                    ></md-checkbox>
                    <span>${this._esc(r9)}</span>
                  </label>
                `).join("")}
              </div>

              <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
                <md-filled-button id="roomClearCurrentBtn">清空当前房间关系</md-filled-button>
                <md-filled-button id="roomClearAllBtn">清空全部关系</md-filled-button>
              </div>
            `}

            <div style="margin-top:16px;padding:10px;border-radius:10px;border:1px dashed var(--sa-border);">
              <div style="font-weight:600;margin-bottom:8px">一键示例</div>
              <div class="body-s" style="margin-bottom:8px;opacity:.7">点击可快速填充常见布局用于参考，再按实际调整。</div>
              <div style="display:flex;gap:8px;flex-wrap:wrap">
                <md-outlined-button data-preset="isolation">示例1：全部隔离</md-outlined-button>
                <md-outlined-button data-preset="chain">示例2：线性串联</md-outlined-button>
                <md-outlined-button data-preset="star">示例3：以当前房间为核心</md-outlined-button>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">拓扑摘要</div>
          <div id="roomTopoSummary" style="display:flex;flex-wrap:wrap;gap:8px">
            ${this._buildTopoSummary(rooms, adj)}
          </div>
        </div>

        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:10px">
          <md-outlined-button id="roomSyncHaBtn">从 HA 同步区域</md-outlined-button>
          <md-filled-button id="roomSaveBtn">保存拓扑</md-filled-button>
        </div>
      </div>`;
      const $3 = (id) => view.querySelector("#" + id);
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(view, "[data-edit-room],md-checkbox[data-editor],[data-preset],#roomClearCurrentBtn,#roomClearAllBtn,#roomSaveBtn,#roomSyncHaBtn,#addRoomBtn,#newRoomInput");
      }
      view.querySelectorAll("[data-edit-room]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = parseInt(btn.dataset.editRoom, 10);
          this._roomEditorRoom = rooms[idx];
          this._renderRooms();
        });
      });
      view.querySelectorAll("md-checkbox[data-editor]").forEach((cb) => {
        cb.addEventListener("change", () => {
          const aIdx = parseInt(cb.dataset.a, 10);
          const bIdx = parseInt(cb.dataset.b, 10);
          const a4 = rooms[aIdx];
          const b3 = rooms[bIdx];
          setAdj(a4, b3, cb.checked);
          const summary = view.querySelector("#roomTopoSummary");
          if (summary)
            summary.innerHTML = this._buildTopoSummary(rooms, adj);
          const roomList = view.querySelector("#roomList");
          if (roomList) {
            roomList.querySelectorAll("button[data-edit-room]").forEach((rowBtn) => {
              const r9 = rooms[parseInt(rowBtn.dataset.editRoom, 10)];
              if (r9 && r9 !== a4 && r9 !== b3)
                return;
              const label = rowBtn.querySelector("span:last-child");
              if (label)
                label.textContent = `${neighborsOf(r9).length} 相邻`;
            });
          }
        });
      });
      view.querySelectorAll("[data-preset]").forEach((btn) => {
        btn.addEventListener("click", () => {
          applyPreset(btn.dataset.preset);
        });
      });
      const clearBtn = $3("roomClearAllBtn");
      if (clearBtn) {
        clearBtn.onclick = async () => {
          if (!await this._showConfirm("确定清空全部相邻关系？"))
            return;
          clearAdj();
          this._renderRooms();
        };
      }
      const clearCurrent = $3("roomClearCurrentBtn");
      if (clearCurrent && editorRoom) {
        clearCurrent.onclick = async () => {
          const toDelete = Object.keys(adj).filter((k2) => {
            const [a4, b3] = parseAdjKey(k2);
            return a4 === editorRoom || b3 === editorRoom;
          });
          toDelete.forEach((k2) => delete adj[k2]);
          this._renderRooms();
        };
      }
      $3("roomSaveBtn").onclick = async () => {
        try {
          const topology = Object.keys(adj).map((k2) => {
            const [a4, b3] = parseAdjKey(k2);
            return { room_a: a4, room_b: b3, relation: "adjacent" };
          }).filter((it) => it.room_a && it.room_b);
          await this._callService("smart_agent", "save_room_topology", { topology });
          this._msg("房间拓扑已保存");
        } catch (e9) {
          this._msg("保存失败: " + e9.message);
        }
      };
      $3("roomSyncHaBtn").onclick = async () => {
        try {
          await this._callService("smart_agent", "sync_rooms_to_ha");
          this._msg("已同步 HA 区域");
          this._renderRooms();
        } catch (e9) {
          this._msg("同步失败: " + e9.message);
        }
      };
      $3("addRoomBtn").onclick = () => {
        var _a3;
        const input = $3("newRoomInput");
        const name = (_a3 = input == null ? void 0 : input.value) == null ? void 0 : _a3.trim();
        if (!name)
          return;
        if (!this._customRooms)
          this._customRooms = [];
        if (!this._customRooms.includes(name)) {
          this._customRooms.push(name);
          this._roomEditorRoom = name;
          this._renderRooms();
        }
        if (input)
          input.value = "";
      };
      $3("newRoomInput").onkeydown = (e9) => {
        if (e9.key === "Enter")
          $3("addRoomBtn").click();
      };
    },
    _buildTopoSummary(rooms, adj) {
      const ADJ_SEP = "||";
      const parseAdjKey = (key) => {
        const idx = key.indexOf(ADJ_SEP);
        return idx < 0 ? ["", ""] : [key.slice(0, idx), key.slice(idx + ADJ_SEP.length)];
      };
      const neighborMap = new Map(rooms.map((r9) => [r9, []]));
      Object.keys(adj).forEach((k2) => {
        const [a4, b3] = parseAdjKey(k2);
        if (!adj[k2] || !a4 || !b3 || !neighborMap.has(a4) || !neighborMap.has(b3))
          return;
        neighborMap.get(a4).push(b3);
        neighborMap.get(b3).push(a4);
      });
      const lines = rooms.map((r9) => {
        const neighbors = neighborMap.get(r9) || [];
        if (!neighbors.length)
          return "";
        return `<div style="padding:6px 12px;background:var(--sa-bg);border-radius:8px;
        border:1px solid var(--sa-border);font-size:13px">
        <b>${this._esc(r9)}</b> ↔ ${neighbors.map((n9) => this._esc(n9)).join("、")}
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
      } catch (e9) {
        this._roomAdj = {};
        this._msg("加载房间拓扑失败: " + e9.message);
      }
    }
  };

  // custom_components/smart_agent/frontend/src/render/backup.js
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
      ].map(({ v: v2, label, desc }) => `
                  <label style="display:flex;align-items:center;gap:10px;padding:10px 16px;
                    border-radius:12px;border:2px solid var(--sa-border);cursor:pointer;
                    transition:.15s" data-level="${v2}">
                    <input type="radio" name="backupLevel" value="${v2}" ${v2 === "full" ? "checked" : ""}
                      style="display:none">
                    <div>
                      <div style="font-weight:600;font-size:14px">${label}</div>
                      <div class="body-s">${desc}</div>
                    </div>
                  </label>`).join("")}
              </div>
            </div>
            <md-outlined-text-field id="backupNote"
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
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(view, [
          "#backupCreateBtn",
          "#backupCancelBtn",
          "#backupConfirmBtn",
          "#restoreConfirmBtn",
          ".backup-restore-btn",
          ".backup-delete-btn"
        ].join(","));
      }
      this._bindBackupEvents(view);
      this._loadBackupList(view);
    },
    _bindBackupEvents(view) {
      const $3 = (id) => view.querySelector("#" + id);
      view.querySelectorAll("[data-level]").forEach((label) => {
        label.onclick = () => {
          view.querySelectorAll("[data-level]").forEach((l5) => {
            l5.style.borderColor = "var(--sa-border)";
            l5.style.background = "";
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
      $3("backupCreateBtn").onclick = () => {
        const panel = $3("backupCreatePanel");
        panel.style.display = panel.style.display === "none" ? "block" : "none";
      };
      $3("backupCancelBtn").onclick = () => {
        $3("backupCreatePanel").style.display = "none";
      };
      $3("backupConfirmBtn").onclick = async () => {
        var _a3, _b, _c;
        const level = ((_a3 = view.querySelector("input[name='backupLevel']:checked")) == null ? void 0 : _a3.value) || "full";
        const note = ((_c = (_b = $3("backupNote")) == null ? void 0 : _b.value) == null ? void 0 : _c.trim()) || "";
        const btn = $3("backupConfirmBtn");
        btn.disabled = true;
        btn.textContent = "备份中...";
        try {
          await this._callService("smart_agent", "create_backup", { level, note });
          this._msg("备份创建成功");
          $3("backupCreatePanel").style.display = "none";
          await this._loadBackupList(view);
        } catch (e9) {
          this._msg("备份失败: " + e9.message);
        } finally {
          btn.disabled = false;
          btn.textContent = "开始备份";
        }
      };
      $3("backupRefreshBtn").onclick = () => this._loadBackupList(view);
      const dlg = $3("backupRestoreDialog");
      $3("restoreCancelBtn").onclick = () => dlg.close();
      $3("restoreConfirmBtn").onclick = async () => {
        const backupId = dlg.dataset.backupId;
        dlg.close();
        try {
          await this._callService("smart_agent", "restore_backup", { backup_id: backupId });
          this._msg("恢复指令已发送，系统即将重启");
        } catch (e9) {
          this._msg("恢复失败: " + e9.message);
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
        ${backups.map((b3) => `
          <div style="display:flex;align-items:center;gap:12px;padding:14px 16px;
            border-radius:12px;border:1px solid var(--sa-border);background:var(--sa-bg)">
            <div style="width:44px;height:44px;border-radius:10px;flex-shrink:0;
              background:var(--sa-primary-container);
              display:flex;align-items:center;justify-content:center;font-size:22px">📦</div>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span class="title-s">${this._esc(b3.note || "备份")}</span>
                <span style="padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;
                  background:var(--sa-primary-container);color:${levelColors[b3.level] || "var(--sa-primary)"}">
                  ${levelLabels[b3.level] || b3.level}
                </span>
              </div>
              <div class="body-s" style="margin-top:2px;opacity:.7">
                ${this._esc(b3.created_at || "")} · ${b3.size_kb ? b3.size_kb + " KB" : ""}
              </div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0">
              <md-outlined-button class="backup-restore-btn" data-id="${this._esc(b3.id)}"
                data-note="${this._esc(b3.note || b3.id)}"
                style="--md-outlined-button-container-height:32px;font-size:12px">
                恢复
              </md-outlined-button>
              <md-icon-button class="backup-delete-btn" data-id="${this._esc(b3.id)}" title="删除">
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
              await this._callService("smart_agent", "delete_backup", { backup_id: btn.dataset.id });
              this._msg("备份已删除");
              await this._loadBackupList(view);
            } catch (e9) {
              this._msg("删除失败: " + e9.message);
            }
          };
        });
      } catch (e9) {
        area.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">加载失败</div>
        <div class="empty-state-desc">${this._esc(e9.message)}</div>
      </div>`;
      }
    }
  };

  // custom_components/smart_agent/frontend/src/render/patrol.js
  var patrolMethods = {
    _renderPatrol() {
      var _a3;
      const view = this.shadowRoot.getElementById("view-patrol");
      if (!view)
        return;
      const cfg = ((_a3 = this._cfg) == null ? void 0 : _a3.attributes) || {};
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
      const $3 = (id) => view.querySelector("#" + id);
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(view, "#patrolEnabled,#patrolActiveInterval,#patrolNightInterval,#patrolActiveStart,#patrolActiveEnd,#patrolCheckAbnormal,#patrolCheckEnergy,#patrolCheckHabits,#patrolTriggerBtn,#patrolSaveBtn");
      }
      $3("patrolActiveInterval").oninput = (e9) => {
        $3("patrolActiveIntervalVal").textContent = e9.target.value + " 分钟";
      };
      $3("patrolNightInterval").oninput = (e9) => {
        $3("patrolNightIntervalVal").textContent = e9.target.value + " 分钟";
      };
      $3("patrolTriggerBtn").onclick = async () => {
        const btn = $3("patrolTriggerBtn");
        btn.disabled = true;
        btn.textContent = "巡检中...";
        try {
          await this._callService("smart_agent", "trigger_patrol", {});
          this._msg("巡检指令已发送");
        } catch (e9) {
          this._msg("触发失败: " + e9.message);
        } finally {
          btn.disabled = false;
          btn.textContent = "▶ 立即巡检";
        }
      };
      $3("patrolSaveBtn").onclick = async () => {
        const data = {
          patrol_enabled: $3("patrolEnabled").selected,
          patrol_active_interval: parseInt($3("patrolActiveInterval").value),
          patrol_night_interval: parseInt($3("patrolNightInterval").value),
          patrol_active_start: $3("patrolActiveStart").value,
          patrol_active_end: $3("patrolActiveEnd").value
        };
        try {
          await this._callService("smart_agent", "update_config", data);
          this._msg("巡检配置已保存");
        } catch (e9) {
          this._msg("保存失败: " + e9.message);
        }
      };
    }
  };

  // custom_components/smart_agent/frontend/src/render/mcp.js
  var mcpMethods = {
    _renderMcp() {
      var _a3;
      const view = this.shadowRoot.getElementById("view-mcp");
      if (!view)
        return;
      const cfg = ((_a3 = this._cfg) == null ? void 0 : _a3.attributes) || {};
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
      ].map((t6) => `
              <div style="display:flex;align-items:center;gap:12px;padding:12px 14px;
                border-radius:10px;border:1px solid var(--sa-border);background:var(--sa-bg)">
                <span style="font-size:22px">${t6.icon}</span>
                <div style="flex:1">
                  <div style="font-size:13px;font-weight:600;font-family:monospace">${t6.name}</div>
                  <div class="body-s">${t6.desc}</div>
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
      const $3 = (id) => view.querySelector("#" + id);
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(view, "#mcpEnabledSwitch");
      }
      $3("mcpCopyBtn").onclick = () => {
        var _a4;
        (_a4 = navigator.clipboard) == null ? void 0 : _a4.writeText(mcpUrl).then(() => this._msg("地址已复制"));
      };
      $3("mcpEnabledSwitch").addEventListener("change", async (e9) => {
        try {
          await this._callService("smart_agent", "update_config", { mcp_enabled: e9.target.selected });
          this._msg(e9.target.selected ? "MCP 服务已启用" : "MCP 服务已禁用");
        } catch (err) {
          this._msg("设置失败: " + err.message);
        }
      });
    }
  };

  // custom_components/smart_agent/frontend/src/render/license.js
  var licenseMethods = {
    _renderLicensePage() {
      var _a3;
      const view = this.shadowRoot.getElementById("view-license");
      if (!view)
        return;
      const cfg = ((_a3 = this._cfg) == null ? void 0 : _a3.attributes) || {};
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
      ].map((r9, i8) => `
                  <tr style="border-bottom:1px solid var(--sa-border);
                    ${i8 % 2 === 0 ? "background:var(--sa-bg)" : ""}">
                    <td style="padding:8px 12px;font-weight:500">${r9.tier}</td>
                    <td style="padding:8px 12px;text-align:center">${r9.quota}</td>
                    <td style="padding:8px 12px;text-align:center">${r9.scene}</td>
                    <td style="padding:8px 12px;text-align:center">${r9.backup}</td>
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
      const $3 = (id) => view.querySelector("#" + id);
      if (this._isHaFallbackReadOnly()) {
        this._disableHaFallbackWriteControls(view, "#licenseVerifyBtn");
      }
      $3("licenseVerifyBtn").onclick = async () => {
        const btn = $3("licenseVerifyBtn");
        btn.disabled = true;
        btn.textContent = "验证中...";
        try {
          await this._callService("smart_agent", "verify_license", {});
          this._msg("License 验证完成，请刷新页面查看结果");
        } catch (e9) {
          this._msg("验证失败: " + e9.message);
        } finally {
          btn.disabled = false;
          btn.textContent = "🔄 重新验证";
        }
      };
      $3("licenseHelpBtn").onclick = () => {
        window.open("https://smartagent.ai/license", "_blank");
      };
    }
  };

  // custom_components/smart_agent/frontend/src/update.js
  var updateMethods = {
    _update() {
      var _a3, _b, _c, _d;
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const c5 = this._cfg.attributes || {}, s4 = this._sts.attributes || {};
      if ($3("dCnt"))
        $3("dCnt").textContent = c5.device_count || 0;
      if ($3("hCnt"))
        $3("hCnt").textContent = c5.habit_count || 0;
      if ($3("rCnt"))
        $3("rCnt").textContent = c5.rule_count || 0;
      if ($3("rCntSub")) {
        const total = c5.rule_count || 0;
        const aiCount = c5.ai_rule_count || 0;
        const userCount = total - aiCount;
        if (total > 0) {
          $3("rCntSub").textContent = `用户 ${userCount} · AI ${aiCount}`;
        }
      }
      if ($3("sTxt"))
        $3("sTxt").textContent = s4.full_text || "正在监控中...";
      const aq = c5.action_quality || {};
      const qCard = $3("qualityCard");
      if (qCard) {
        if (aq.total > 0) {
          qCard.style.display = "block";
          const rateColor = aq.rate >= 95 ? "var(--sa-succ)" : aq.rate >= 80 ? "#d29922" : "#f85149";
          $3("qualityStats").innerHTML = `
          <div class="sys-card"><div class="label-m">总执行次数</div><div class="stat-num" style="font-size:28px">${aq.total}</div></div>
          <div class="sys-card"><div class="label-m">成功率</div><div class="stat-num" style="font-size:28px;color:${rateColor}">${aq.rate}%</div></div>
          <div class="sys-card"><div class="label-m">失败次数</div><div class="stat-num" style="font-size:28px;color:${aq.failed ? "#f85149" : "var(--sa-succ)"}">${aq.failed}</div></div>
          <div class="sys-card"><div class="label-m">自动重试</div><div class="stat-num" style="font-size:28px">${aq.retry_total}</div></div>
          <div class="sys-card"><div class="label-m">平均验证延迟</div><div class="stat-num" style="font-size:28px">${aq.avg_latency_ms}<span style="font-size:12px;opacity:.6">ms</span></div></div>
        `;
          const tf = aq.top_failures || [];
          if (tf.length) {
            $3("qualityFailures").innerHTML = `<div class="label-m" style="margin-bottom:8px;color:#f85149">失败最多的设备 Top ${tf.length}</div>` + tf.map((f3) => `<div class="body-s" style="padding:4px 0;display:flex;justify-content:space-between"><span>${this._esc(f3.entity_id)}</span><span style="color:#f85149;font-weight:600">${f3.count} 次</span></div>`).join("");
          } else {
            $3("qualityFailures").innerHTML = "";
          }
        } else {
          qCard.style.display = "none";
        }
      }
      const guards = c5.priority_guards || [];
      const priCard = $3("priorityCard");
      const priList = $3("priorityList");
      const priCount = $3("priorityCount");
      if (priCard && priList) {
        if (guards.length > 0) {
          priCard.style.display = "block";
          if (priCount)
            priCount.textContent = `${guards.length} 个设备受保护`;
          const priColors = { 0: "#ef4444", 1: "#f59e0b", 2: "#3b82f6", 3: "#8b5cf6", 4: "var(--sa-text-variant)" };
          priList.innerHTML = guards.map((g2) => {
            const color = priColors[g2.priority] || "var(--sa-text-variant)";
            const mins = Math.ceil(g2.remaining_sec / 60);
            const timeStr = g2.remaining_sec > 60 ? `${mins}分钟` : `${g2.remaining_sec}秒`;
            return `<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;background:var(--sa-bg);border:1px solid var(--sa-border)">
            <span style="color:${color};font-weight:700;font-size:12px;white-space:nowrap">${this._esc(g2.priority_label)}</span>
            <span style="flex:1;font-size:13px">${this._esc(g2.name)}<span style="opacity:.5;font-size:11px;margin-left:4px">${this._esc(g2.entity_id)}</span></span>
            <span style="font-size:12px;opacity:.7">← ${this._esc(g2.source_label)}</span>
            <span style="font-size:11px;color:${color};font-weight:600;white-space:nowrap">${timeStr}</span>
          </div>`;
          }).join("");
        } else {
          priCard.style.display = "none";
        }
      }
      const numA = $3("numA"), numN = $3("numN");
      if (numA && this._numA.state) {
        numA.value = parseFloat(this._numA.state);
        $3("numAVal").textContent = this._numA.state;
      }
      if (numN && this._numN.state) {
        numN.value = parseFloat(this._numN.state);
        $3("numNVal").textContent = this._numN.state;
      }
      const modeSel = $3("modeSel"), showroomPanel = $3("showroomPanel"), modeIcon = $3("modeIcon");
      const modeChip = $3("modeChip"), sceneIconWrap = $3("sceneIconWrap");
      const ICO = this._getIcons();
      this._uiCache = this._uiCache || {};
      const recentAi = s4.recent_ai_actions || [];
      const now = Date.now() / 1e3;
      const FRESH_SEC = 30 * 60;
      const freshAi = recentAi.filter((a4) => a4.time && now - a4.time < FRESH_SEC);
      const aiCard = $3("recentAiCard");
      if (aiCard) {
        if (recentAi.length > 0) {
          aiCard.style.display = "block";
          const badge = $3("corrBadge");
          if (badge) {
            badge.textContent = freshAi.length > 0 ? freshAi.length : recentAi.length;
            badge.style.background = freshAi.length > 0 ? "" : "var(--sa-border, #555)";
            badge.title = freshAi.length > 0 ? `${freshAi.length} 个设备在 30 分钟内被 AI 操作，可纠正` : `${recentAi.length} 个设备有历史 AI 操作记录（已超过 30 分钟）`;
          }
          const groups = /* @__PURE__ */ new Map();
          recentAi.forEach((a4) => {
            const key = a4.scene || "(未知场景)";
            if (!groups.has(key))
              groups.set(key, 0);
            groups.set(key, groups.get(key) + 1);
          });
          const summary = $3("recentAiSummary");
          if (summary) {
            let h3 = "";
            groups.forEach((cnt, scene) => {
              h3 += `<span class="chip" style="font-size:11px;cursor:pointer;max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
              title="${this._esc(scene)}" data-goto-corr="1">
              ${ICO.bolt} ${this._esc(scene.length > 20 ? scene.slice(0, 20) + "…" : scene)} · ${cnt} 设备</span>`;
            });
            summary.innerHTML = h3;
            summary.querySelectorAll("[data-goto-corr]").forEach((el) => {
              el.onclick = () => this._setTab("corrections");
            });
          }
        } else {
          aiCard.style.display = "none";
        }
      }
      const goBtn = $3("goToCorrections");
      if (goBtn)
        goBtn.onclick = () => this._setTab("corrections");
      const isShowroom = c5.mode === "showroom";
      if (this._uiCache.mode !== c5.mode) {
        this._uiCache.mode = c5.mode;
        if (modeSel && !modeSel.matches(":focus-within"))
          modeSel.value = c5.mode || "home";
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
      }
      const sceneBtns = $3("showroomSceneBtns");
      if (sceneBtns && Array.isArray(c5.showroom_scenes)) {
        const activeScene = c5.showroom_scene || "";
        const hasCustom = !!(c5.showroom_custom_prompt || "");
        sceneBtns.innerHTML = c5.showroom_scenes.map((s5) => {
          const isActive = activeScene === s5.key && !hasCustom;
          return `
          <div style="display:flex;align-items:center;gap:4px">
            <button class="chip ${isActive ? "active" : ""} showroom-scene-btn" 
              data-scene="${this._esc(s5.key)}" data-label="${this._esc(s5.label)}">
              ${this._esc(s5.label)}
            </button>
            <button class="showroom-edit-btn" data-scene="${this._esc(s5.key)}" 
              style="background:none;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:4px;border-radius:50%;transition:.2s" 
              title="编辑">
              <span style="opacity:.5">${ICO.edit}</span>
            </button>
        </div>`;
        }).join("");
      }
      const customInput = $3("showroomCustomInput");
      if (customInput && !customInput.matches(":focus") && (c5.showroom_custom_prompt || "")) {
        customInput.value = c5.showroom_custom_prompt;
      }
      const b3 = $3("aiBtn"), isOn = this._sw.state === "on";
      b3.className = isOn ? "btn btn-tonal btn-sm" : "btn btn-error btn-sm";
      b3.textContent = isOn ? "托管中" : "已暂停";
      const learnSt = (_a3 = this._hass) == null ? void 0 : _a3.states["switch.smart_agent_learning_mode"];
      const learnOn = (learnSt == null ? void 0 : learnSt.state) === "on";
      const learnToggle = $3("learningModeToggle");
      if (learnToggle)
        learnToggle.selected = learnOn;
      const learnItem = $3("learningModeItem");
      if (learnItem)
        learnItem.classList.toggle("active", learnOn);
      const habitSt = (_b = this._hass) == null ? void 0 : _b.states["switch.smart_agent_habit_proactive"];
      const habitOn = (habitSt == null ? void 0 : habitSt.state) === "on";
      const habitToggle = $3("habitProactiveToggle");
      if (habitToggle)
        habitToggle.selected = habitOn;
      const habitItem = $3("habitProactiveItem");
      if (habitItem)
        habitItem.classList.toggle("active", habitOn);
      const frigateSt = (_c = this._hass) == null ? void 0 : _c.states["switch.smart_agent_frigate_enabled"];
      const frigateOn = (frigateSt == null ? void 0 : frigateSt.state) === "on";
      const frigateToggle = $3("frigateToggle");
      if (frigateToggle)
        frigateToggle.selected = frigateOn;
      const frigateItem = $3("frigateItem");
      if (frigateItem)
        frigateItem.classList.toggle("active", frigateOn);
      const visionSt = (_d = this._hass) == null ? void 0 : _d.states["switch.smart_agent_vision_enabled"];
      const visionOn = (visionSt == null ? void 0 : visionSt.state) === "on";
      const visionToggle = $3("visionToggle");
      if (visionToggle)
        visionToggle.selected = visionOn;
      const visionItem = $3("visionItem");
      if (visionItem)
        visionItem.classList.toggle("active", visionOn);
      this._renderLicenseStatus(c5.license);
      if (this._tab === "syslog" && this._sysLogMode === "live") {
        this._wsRefreshSysLog();
      }
      if (c5.brand_name || c5.brand_primary_color) {
        this._applyBrand();
      }
    }
  };

  // custom_components/smart_agent/frontend/src/utils/helpers.js
  var helperMethods = {
    /** HTML 转义，防止 XSS */
    _esc(s4) {
      return String(s4).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    },
    /** 轻量 Toast 提示 */
    _msg(m3) {
      const t6 = this.shadowRoot.getElementById("toast");
      t6.textContent = m3;
      t6.className = "show";
      setTimeout(() => t6.className = "", 3e3);
    },
    _isHaFallbackReadOnly() {
      return true;
    },
    _warnHaFallbackReadOnly() {
      this._msg("HA 面板已降级为只读/应急兜底，请前往 SmartAgent UI v2 执行写操作");
    },
    _disableHaFallbackWriteControls(root, selectors = "") {
      if (!this._isHaFallbackReadOnly() || !root || !selectors)
        return;
      root.querySelectorAll(selectors).forEach((el) => {
        if (!el)
          return;
        el.disabled = true;
        el.setAttribute("disabled", "");
        el.setAttribute("aria-disabled", "true");
        el.style.pointerEvents = "none";
        el.style.opacity = "0.55";
        if (!el.title) {
          el.title = "HA 面板兜底模式：请使用 SmartAgent UI v2 主控制台执行写操作";
        }
      });
    },
    _callService(domain, service, serviceData = {}) {
      if (this._isHaFallbackReadOnly()) {
        this._warnHaFallbackReadOnly();
        throw new Error("HA 面板只读");
      }
      return this._hass.callService(domain, service, serviceData);
    },
    /**
     * M3 风格通用确认弹窗 — 使用自绘 overlay，避免 md-dialog 在 HA 宿主环境中定位异常
     * @param {string} msg 提示内容
     * @param {string} title 标题（可选）
     * @returns {Promise<boolean>}
     */
    _showConfirm(msg, title = "确认操作") {
      const host = this.shadowRoot;
      let ov = host.getElementById("m3ConfirmOverlay");
      if (!ov) {
        ov = document.createElement("div");
        ov.id = "m3ConfirmOverlay";
        ov.className = "m3-dialog-overlay";
        ov.innerHTML = `
        <div class="m3-dialog" style="width:min(440px,92vw);border-radius:20px">
          <div class="m3-dialog-title" id="m3ConfirmTitle"></div>
          <div id="m3ConfirmBody" style="font-size:14px;line-height:1.7;color:var(--sa-text-variant)"></div>
          <div class="m3-dialog-actions">
            <md-outlined-button id="m3ConfirmCancel" style="--md-outlined-button-container-height:36px">取消</md-outlined-button>
            <md-filled-button id="m3ConfirmOk" style="--md-filled-button-container-height:36px">确定</md-filled-button>
          </div>
        </div>`;
        host.appendChild(ov);
      }
      const titleEl = ov.querySelector("#m3ConfirmTitle");
      const bodyEl = ov.querySelector("#m3ConfirmBody");
      const ok = ov.querySelector("#m3ConfirmOk");
      const cl = ov.querySelector("#m3ConfirmCancel");
      titleEl.textContent = title;
      bodyEl.textContent = msg;
      return new Promise((resolve) => {
        const done = (val) => {
          ov.classList.remove("open");
          ok.onclick = null;
          cl.onclick = null;
          ov.onclick = null;
          resolve(val);
        };
        ok.onclick = (e9) => {
          e9.stopPropagation();
          done(true);
        };
        cl.onclick = (e9) => {
          e9.stopPropagation();
          done(false);
        };
        ov.onclick = (e9) => {
          if (e9.target === ov)
            done(false);
        };
        ov.classList.add("open");
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
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const ov = $3("m3EditDevOverlay");
      const nameEl = $3("editDevName");
      const roomSel = $3("editDevRoomSel");
      const roomCustom = $3("editDevRoomCustom");
      const typeEl = $3("editDevType");
      const saveBtn = $3("m3EditDevSave");
      const cancelBtn = $3("m3EditDevCancel");
      nameEl.value = currentName || "";
      typeEl.value = currentType || "";
      roomCustom.value = "";
      while (roomSel.options.length > 1)
        roomSel.remove(1);
      const cAll = this._wsGet("devices", "devices", []);
      const smRooms = cAll.map((i8) => i8.room || "").filter((r9) => r9);
      const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a4) => a4.name) : [];
      const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort(
        (a4, b3) => a4.localeCompare(b3, "zh")
      );
      const firstOpt = document.createElement("option");
      firstOpt.value = "";
      firstOpt.textContent = "选择房间…";
      roomSel.innerHTML = "";
      roomSel.appendChild(firstOpt);
      allRooms.forEach((r9) => {
        const opt = document.createElement("option");
        opt.value = r9;
        opt.textContent = r9;
        if (r9 === currentRoom)
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
            await this._callService("smart_agent", "update_device", payload);
            this._msg(`设备「${newName}」已更新`);
            delete this._wsData["devices"];
            await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
            close();
          } catch (err) {
            this._msg("保存失败: " + err.message);
          }
        };
        cancelBtn.onclick = () => close();
        ov.onclick = (e9) => {
          if (e9.target === ov)
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
      } catch (e9) {
        console.warn("[SmartAgent] WS fetch failed:", type, e9);
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
      var _a3;
      const s4 = this._hass.states[id];
      if ((_a3 = s4 == null ? void 0 : s4.attributes) == null ? void 0 : _a3.friendly_name)
        return s4.attributes.friendly_name;
      const cfgList = this._wsGet("devices", "devices", []);
      const found = cfgList.find((d3) => d3.entity_id === id);
      if (found == null ? void 0 : found.name)
        return found.name;
      return id;
    }
  };

  // custom_components/smart_agent/frontend/src/panel-core.js
  var coreMethods = {
    _toggle() {
      const s4 = this._sw;
      if (!s4.entity_id)
        return;
      this._callService(
        "switch",
        s4.state === "on" ? "turn_off" : "turn_on",
        { entity_id: s4.entity_id }
      );
    },
    _openSceneEdit(key) {
      var _a3;
      const c5 = ((_a3 = this._cfg) == null ? void 0 : _a3.attributes) || {};
      const scenes = Array.isArray(c5.showroom_scenes) ? c5.showroom_scenes : [];
      const scene = scenes.find((s4) => s4.key === key);
      if (!scene)
        return;
      this._editingSceneKey = key;
      const $3 = (id) => this.shadowRoot.getElementById(id);
      $3("editSceneTitle").textContent = `编辑场景: ${scene.label}`;
      $3("editSceneLabel").value = scene.label;
      $3("editSceneTime").value = scene.virtual_time;
      $3("editSceneDesc").value = scene.scene_desc;
      $3("editSceneHint").value = scene.hint;
      $3("showroomEditPanel").style.display = "block";
      $3("editSceneLabel").focus();
    },
    // 主 Tab 分组映射
    _GROUP_TABS: {
      space: ["devices", "rooms", "vision"],
      ai: ["profiles", "habits", "aiscenes", "corrections"],
      data: ["transactions", "energy"],
      system: ["config", "patrol", "backup", "mcp", "license"]
    },
    _setTab(t6) {
      var _a3, _b, _c, _d, _e;
      if (this._tab === t6)
        return;
      this._tab = t6;
      const groupMap = this._GROUP_TABS;
      let activeGroup = "";
      for (const [g2, tabs] of Object.entries(groupMap)) {
        if (tabs.includes(t6)) {
          activeGroup = g2;
          break;
        }
      }
      this.shadowRoot.querySelectorAll(".nav-tab").forEach((b3) => {
        if (b3.dataset.t) {
          b3.classList.toggle("active", b3.dataset.t === t6);
        } else if (b3.dataset.group) {
          b3.classList.toggle("active", b3.dataset.group === activeGroup);
        }
      });
      ["space", "ai", "data", "system"].forEach((g2) => {
        const el = this.shadowRoot.getElementById("sub-" + g2);
        if (el)
          el.style.display = g2 === activeGroup ? "flex" : "none";
      });
      if (activeGroup) {
        const subBar = this.shadowRoot.getElementById("sub-" + activeGroup);
        if (subBar) {
          subBar.querySelectorAll(".nav-sub-tab").forEach(
            (b3) => b3.classList.toggle("active", b3.dataset.t === t6)
          );
          this._lastSubTab = this._lastSubTab || {};
          this._lastSubTab[activeGroup] = t6;
        }
      }
      this.shadowRoot.querySelectorAll(".tab-view").forEach(
        (v2) => v2.classList.toggle("active", v2.id === "view-" + t6)
      );
      if (t6 === "syslog") {
        this._loadLogDates();
        this._wsRefreshSysLog();
      }
      if (t6 === "config")
        this._renderConfig();
      if (t6 === "devices")
        this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
      if (t6 === "profiles")
        this._wsRefresh("smart_agent/get_rules", "rules", () => this._renderProfs());
      if (t6 === "habits")
        this._wsRefresh("smart_agent/get_behavior_patterns", "behavior_patterns", () => this._renderHabitPatterns());
      if (t6 === "aiscenes")
        this._wsRefresh("smart_agent/get_ai_scenes", "ai_scenes", () => this._renderAiScenes());
      if (t6 === "corrections")
        this._wsRefresh("smart_agent/get_ai_actions", "ai_actions", () => this._renderCorrections());
      if (t6 === "transactions")
        this._wsRefresh("smart_agent/get_transactions", "transactions", () => this._renderTransactions());
      if (t6 === "energy")
        this._wsRefresh("smart_agent/get_energy_stats", "energy_stats", () => this._renderEnergy());
      if (t6 === "rooms") {
        (_a3 = this._loadRoomTopology) == null ? void 0 : _a3.call(this).then(() => {
          var _a4;
          return (_a4 = this._renderRooms) == null ? void 0 : _a4.call(this);
        });
      }
      if (t6 === "patrol")
        (_b = this._renderPatrol) == null ? void 0 : _b.call(this);
      if (t6 === "backup")
        (_c = this._renderBackup) == null ? void 0 : _c.call(this);
      if (t6 === "mcp")
        (_d = this._renderMcp) == null ? void 0 : _d.call(this);
      if (t6 === "license")
        (_e = this._renderLicensePage) == null ? void 0 : _e.call(this);
      this._startTerminalLogPoll(t6 === "dashboard");
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
        } catch (_2) {
        } finally {
          _polling = false;
        }
      };
      poll();
      this._terminalPollTimer = setInterval(poll, 3e3);
    },
    _renderLicenseStatus(lic) {
      var _a3;
      const area = (_a3 = this.shadowRoot) == null ? void 0 : _a3.getElementById("licenseStatusArea");
      if (!area)
        return;
      if (!lic) {
        area.innerHTML = '<span style="opacity:.5">暂无数据</span>';
        return;
      }
      const tierColors = { free: "var(--sa-outline)", basic: "var(--sa-secondary)", pro: "var(--sa-succ)", business: "var(--sa-state-warning)" };
      const color = tierColors[lic.tier] || "var(--sa-outline)";
      const validBadge = lic.valid ? `<span style="color:var(--sa-succ);font-weight:600">✅ 已激活</span>` : lic.has_key ? `<span style="color:var(--sa-err);font-weight:600">❌ 验证失败</span>` : `<span style="color:var(--sa-outline)">⚪ 未激活（免费版）</span>`;
      const limitStr = lic.daily_limit === -1 ? "无限制" : `${lic.daily_limit} 次/天`;
      const usedStr = lic.daily_limit === -1 ? `今日已用 ${lic.daily_used} 次` : `今日已用 ${lic.daily_used} / ${lic.daily_limit} 次`;
      const progressPct = lic.daily_limit === -1 ? 0 : Math.min(100, Math.round(lic.daily_used / lic.daily_limit * 100));
      const progressColor = progressPct >= 90 ? "var(--sa-err)" : progressPct >= 70 ? "var(--sa-state-warning)" : "var(--sa-succ)";
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
        <div style="padding:8px 10px;background:var(--sa-err-container);border-radius:var(--sa-shape-sm);font-size:12px;color:var(--sa-err);margin-top:4px">
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
      let h3 = `<button class="pager-btn" ${curPage === 0 ? "disabled" : ""} data-p="${curPage - 1}">‹</button>`;
      if (start > 0)
        h3 += `<button class="pager-btn" data-p="0">1</button><span class="pager-info">…</span>`;
      for (let i8 = start; i8 <= end; i8++) {
        h3 += `<button class="pager-btn ${i8 === curPage ? "active" : ""}" data-p="${i8}">${i8 + 1}</button>`;
      }
      if (end < totalPages - 1)
        h3 += `<span class="pager-info">…</span><button class="pager-btn" data-p="${totalPages - 1}">${totalPages}</button>`;
      h3 += `<button class="pager-btn" ${curPage === totalPages - 1 ? "disabled" : ""} data-p="${curPage + 1}">›</button>`;
      h3 += `<span class="pager-info">${curPage + 1} / ${totalPages} 页</span>`;
      container.innerHTML = h3;
      container.querySelectorAll("[data-p]").forEach(
        (b3) => b3.onclick = () => onPage(parseInt(b3.dataset.p))
      );
    },
    _updateBatchFab() {
      const $3 = (id) => this.shadowRoot.getElementById(id);
      const fab = $3("batchFab");
      if (!fab)
        return;
      const totalSelected = this._selectedNew.size + this._selectedCfg.size;
      if (totalSelected > 0) {
        fab.classList.add("show");
        $3("batchCount").textContent = `已选 ${totalSelected} 项`;
        const hasCfg = this._selectedCfg.size > 0;
        const hasNew = this._selectedNew.size > 0;
        $3("batchFabClear").onclick = () => {
          this._selectedNew.clear();
          this._selectedCfg.clear();
          this._renderDevs();
          this._updateBatchFab();
        };
        $3("batchFabAi").onclick = () => this._batchUpdateMode("ai");
        $3("batchFabHa").onclick = () => this._batchUpdateMode("ha");
        $3("batchFabDel").onclick = () => {
          if (this._selectedNew.size > 0)
            this._batchAdd();
          else
            this._batchDelete();
        };
        $3("batchFabRoom").onchange = (e9) => {
          if (e9.target.value)
            this._batchUpdateRoom(e9.target.value);
          e9.target.value = "";
        };
        $3("batchFabAi").style.display = hasCfg ? "block" : "none";
        $3("batchFabHa").style.display = hasCfg ? "block" : "none";
        $3("batchFabRoom").style.display = hasCfg ? "block" : "none";
        if (hasNew) {
          $3("batchFabDel").textContent = "添加选中";
          $3("batchFabDel").className = "btn btn-filled btn-sm";
        } else {
          $3("batchFabDel").textContent = "停止托管";
          $3("batchFabDel").className = "btn btn-error btn-sm";
        }
        const roomSel = $3("batchFabRoom");
        if (roomSel) {
          while (roomSel.children.length > 1)
            roomSel.removeChild(roomSel.lastChild);
          const cAll = this._wsGet("devices", "devices", []);
          const smRooms = cAll.map((i8) => i8.room || "").filter((r9) => r9);
          const haAreas = this._hass.areas ? Object.values(this._hass.areas).map((a4) => a4.name) : [];
          const allRooms = [.../* @__PURE__ */ new Set([...haAreas, ...smRooms])].sort(
            (a4, b3) => a4.localeCompare(b3, "zh")
          );
          allRooms.forEach((r9) => {
            const opt = document.createElement("md-select-option");
            opt.value = r9;
            opt.innerHTML = `<div slot="headline">${r9}</div>`;
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
          await this._callService("smart_agent", "update_device", { entity_id: id, room });
        }
        this._selectedCfg.clear();
        this._msg("批量房间设置成功");
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e9) {
        this._msg("操作失败: " + e9.message);
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
          await this._callService("smart_agent", "set_device_control_mode", { entity_id: id, mode });
        }
        this._selectedCfg.clear();
        this._msg(`批量模式设置成功 -> ${labels[mode]}`);
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e9) {
        this._msg("操作失败: " + e9.message);
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
          await this._callService("smart_agent", "delete_device", { entity_id: id });
        }
        this._selectedCfg.clear();
        this._msg("批量删除成功");
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e9) {
        this._msg("操作失败: " + e9.message);
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
        await this._callService("smart_agent", "batch_add_devices", {
          entities: ids.join(",")
        });
        this._selectedNew.clear();
        this._msg("批量添加成功");
        delete this._wsData["devices"];
        await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        this._updateBatchFab();
      } catch (e9) {
        this._msg("添加失败: " + e9.message);
      }
    },
    _selAll(s4) {
      if (s4) {
        const configured = new Set(this._wsGet("devices", "devices", []).map((d3) => d3.entity_id));
        const activeType = this._newTypeFilter || "all";
        const kw = (this._newSearchKw || "").trim().toLowerCase();
        const showIgnored = this._showIgnored || false;
        const showOffline = this._showOffline || false;
        Object.values(this._hass.states).forEach((st) => {
          var _a3, _b;
          const d3 = st.entity_id.split(".")[0];
          if (!TARGET_DOMAINS.includes(d3))
            return;
          if (!showIgnored) {
            if (SKIP_KW.some((k2) => st.entity_id.includes(k2)))
              return;
            const n10 = ((_a3 = st.attributes) == null ? void 0 : _a3.friendly_name) || "";
            if (SKIP_NAME_KW.some((k2) => n10.toLowerCase().includes(k2.toLowerCase())))
              return;
          }
          if (configured.has(st.entity_id))
            return;
          const unavail = ["unavailable", "unknown"].includes(st.state);
          if (!showOffline && unavail)
            return;
          if (activeType !== "all" && d3 !== activeType)
            return;
          const n9 = ((_b = st.attributes) == null ? void 0 : _b.friendly_name) || "";
          if (kw && !n9.toLowerCase().includes(kw) && !st.entity_id.toLowerCase().includes(kw))
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
      const toMin = (s4) => {
        const [h3, m3] = (s4 || "").split(":").map(Number);
        return (h3 || 0) * 60 + (m3 || 0);
      };
      const startMin = toMin(startStr);
      const endMin = toMin(endStr);
      const isOpen = nowMin >= startMin && nowMin < endMin;
      if (isOpen) {
        badge.textContent = "🟢 营业中";
        badge.style.background = "var(--sa-succ-container)";
        badge.style.color = "var(--sa-succ)";
        tip.textContent = `营业时间 ${startStr}–${endStr}，AI 处于积极展示模式`;
      } else {
        badge.textContent = "🌙 已打烊";
        badge.style.background = "var(--sa-tertiary-container)";
        badge.style.color = "var(--sa-tertiary)";
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
      } catch (e9) {
      }
    },
    /** 显示决策气泡通知。 */
    _showDecisionBubble(data) {
      var _a3;
      this._dismissDecisionBubble(true);
      const ICO = this._getIcons();
      const scene = this._esc(data.scene || "AI 自动操作");
      const _confRaw = data.confidence != null ? parseInt(data.confidence, 10) : NaN;
      const conf = !isNaN(_confRaw) ? `${_confRaw}%` : "";
      const acts = Array.isArray(data.actions) ? data.actions : [];
      const txnId = data.txn_id != null ? data.txn_id : "";
      const actHtml = acts.length ? `<div class="bubble-actions-list">${acts.map((a4) => `· ${this._esc(a4)}`).join("<br>")}</div>` : "";
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
      (_a3 = el.querySelector(".bubble-dismiss")) == null ? void 0 : _a3.addEventListener("click", () => this._dismissDecisionBubble());
      const undoBtn = el.querySelector(".bubble-undo");
      if (undoBtn) {
        undoBtn.addEventListener("click", async () => {
          const txn = undoBtn.dataset.txn;
          if (txn) {
            try {
              await this._callService("smart_agent", "rollback_transaction", { transaction_id: Number(txn) });
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
      } catch (e9) {
      }
    },
    /** 显示确认气泡（AI 不确定，请用户二次确认后再通过 one_off_prompt 重新触发）。 */
    _showConfirmBubble(data) {
      var _a3;
      this._dismissConfirmBubble(true);
      const ICO = this._getIcons();
      const scene = this._esc(data.scene || "AI 推理结果");
      const intentLabel = this._esc(data.intent_label || data.intent || "");
      const _confRaw2 = data.confidence != null ? parseInt(data.confidence, 10) : NaN;
      const conf = !isNaN(_confRaw2) ? `${_confRaw2}%` : "";
      const reply = this._esc((data.reply || "").substring(0, 80));
      const acts = Array.isArray(data.actions) ? data.actions : [];
      const actCount = Number(data.action_count ?? acts.length) || 0;
      const actHtml = acts.length ? `<div class="bubble-actions-list" style="font-size:11px;opacity:.75">${acts.map((a4) => `· ${this._esc(String(a4))}`).join("<br>")}</div>` : "";
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
      (_a3 = el.querySelector(".bubble-dismiss")) == null ? void 0 : _a3.addEventListener("click", () => this._dismissConfirmBubble());
      const okBtn = el.querySelector(".bubble-confirm-ok");
      if (okBtn) {
        okBtn.addEventListener("click", async () => {
          this._dismissConfirmBubble();
          try {
            await this._callService("smart_agent", "process_command", {
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
            var _a3;
            return (_a3 = this._confirmEl) == null ? void 0 : _a3.remove();
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
            var _a3;
            return (_a3 = this._bubbleEl) == null ? void 0 : _a3.remove();
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

  // custom_components/smart_agent/frontend/src/index.js
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
      var _a3;
      return Object.values(((_a3 = this._hass) == null ? void 0 : _a3.states) || {}).find(match) || {};
    }
    get _cfg() {
      var _a3;
      return ((_a3 = this._hass) == null ? void 0 : _a3.states["sensor.smart_agent_config"]) || this._get((s4) => {
        var _a4;
        return ((_a4 = s4.attributes) == null ? void 0 : _a4.device_count) !== void 0;
      });
    }
    get _sts() {
      var _a3;
      return ((_a3 = this._hass) == null ? void 0 : _a3.states["sensor.smart_agent_status"]) || this._get((s4) => {
        var _a4;
        return ((_a4 = s4.attributes) == null ? void 0 : _a4.full_text) !== void 0;
      });
    }
    get _sw() {
      var _a3;
      return ((_a3 = this._hass) == null ? void 0 : _a3.states["switch.smart_agent_paused"]) || {};
    }
    get _eng() {
      var _a3;
      return ((_a3 = this._hass) == null ? void 0 : _a3.states["select.smart_agent_engine"]) || {};
    }
    get _numA() {
      var _a3;
      return ((_a3 = this._hass) == null ? void 0 : _a3.states["number.smart_agent_confidence_auto"]) || {};
    }
    get _numN() {
      var _a3;
      return ((_a3 = this._hass) == null ? void 0 : _a3.states["number.smart_agent_confidence_notify"]) || {};
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
