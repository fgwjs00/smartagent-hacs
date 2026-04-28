/**
 * patch-mwc.js
 * 给 @material/web 所有组件注册加条件保护，防止与 HA 已注册的组件冲突。
 * 在 npm install 后自动执行（postinstall），或手动运行：node patch-mwc.js
 */
const fs = require('fs');

const files = [
  'node_modules/@material/web/button/elevated-button.js',
  'node_modules/@material/web/button/filled-button.js',
  'node_modules/@material/web/button/filled-tonal-button.js',
  'node_modules/@material/web/button/outlined-button.js',
  'node_modules/@material/web/button/text-button.js',
  'node_modules/@material/web/checkbox/checkbox.js',
  'node_modules/@material/web/chips/assist-chip.js',
  'node_modules/@material/web/chips/chip-set.js',
  'node_modules/@material/web/chips/filter-chip.js',
  'node_modules/@material/web/chips/input-chip.js',
  'node_modules/@material/web/chips/suggestion-chip.js',
  'node_modules/@material/web/dialog/dialog.js',
  'node_modules/@material/web/divider/divider.js',
  'node_modules/@material/web/elevation/elevation.js',
  'node_modules/@material/web/fab/branded-fab.js',
  'node_modules/@material/web/fab/fab.js',
  'node_modules/@material/web/field/filled-field.js',
  'node_modules/@material/web/field/outlined-field.js',
  'node_modules/@material/web/focus/md-focus-ring.js',
  'node_modules/@material/web/icon/icon.js',
  'node_modules/@material/web/iconbutton/filled-icon-button.js',
  'node_modules/@material/web/iconbutton/filled-tonal-icon-button.js',
  'node_modules/@material/web/iconbutton/icon-button.js',
  'node_modules/@material/web/iconbutton/outlined-icon-button.js',
  'node_modules/@material/web/list/list-item.js',
  'node_modules/@material/web/list/list.js',
  'node_modules/@material/web/menu/menu-item.js',
  'node_modules/@material/web/menu/menu.js',
  'node_modules/@material/web/menu/sub-menu.js',
  'node_modules/@material/web/progress/circular-progress.js',
  'node_modules/@material/web/progress/linear-progress.js',
  'node_modules/@material/web/radio/radio.js',
  'node_modules/@material/web/ripple/ripple.js',
  'node_modules/@material/web/select/filled-select.js',
  'node_modules/@material/web/select/outlined-select.js',
  'node_modules/@material/web/select/select-option.js',
  'node_modules/@material/web/slider/slider.js',
  'node_modules/@material/web/switch/switch.js',
  'node_modules/@material/web/tabs/primary-tab.js',
  'node_modules/@material/web/tabs/secondary-tab.js',
  'node_modules/@material/web/tabs/tabs.js',
  'node_modules/@material/web/textfield/filled-text-field.js',
  'node_modules/@material/web/textfield/outlined-text-field.js',
  'node_modules/@material/web/labs/item/item.js',
];

let patched = 0;
files.forEach(f => {
  if (!fs.existsSync(f)) return;
  let content = fs.readFileSync(f, 'utf8');
  if (content.includes('customElements.get(')) return; // already patched
  content = content.replace(
    /(\w+ = __decorate\(\[\s*customElement\('(md-[^']+)'\)\s*\],\s*\w+\);)/,
    (m, full, tag) => `if (!customElements.get('${tag}')) {\n    ${full}\n}`
  );
  fs.writeFileSync(f, content, 'utf8');
  patched++;
});
console.log(`[patch-mwc] ${patched} files patched.`);
