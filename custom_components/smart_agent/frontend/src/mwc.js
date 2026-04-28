/**
 * Material Web 组件按需注册
 *
 * HA 2024.1+ 全局注册了部分 @material/web 组件（button、switch、checkbox 等），
 * 但 text-field、select、slider、dialog、circular-progress、filter-chip 等
 * 并未全局注册，需要在此显式导入。
 *
 * 使用条件注册（检查 customElements.get）避免与 HA 已注册的组件冲突。
 */

// ── Text Field ──
import { MdOutlinedTextField } from "@material/web/textfield/outlined-text-field.js";
if (!customElements.get("md-outlined-text-field")) {
  customElements.define("md-outlined-text-field", MdOutlinedTextField);
}

// ── Select ──
import { MdOutlinedSelect } from "@material/web/select/outlined-select.js";
if (!customElements.get("md-outlined-select")) {
  customElements.define("md-outlined-select", MdOutlinedSelect);
}
import { MdSelectOption } from "@material/web/select/select-option.js";
if (!customElements.get("md-select-option")) {
  customElements.define("md-select-option", MdSelectOption);
}

// ── Dialog ──
import { MdDialog } from "@material/web/dialog/dialog.js";
if (!customElements.get("md-dialog")) {
  customElements.define("md-dialog", MdDialog);
}

// ── Slider ──
import { MdSlider } from "@material/web/slider/slider.js";
if (!customElements.get("md-slider")) {
  customElements.define("md-slider", MdSlider);
}

// ── Circular Progress ──
import { MdCircularProgress } from "@material/web/progress/circular-progress.js";
if (!customElements.get("md-circular-progress")) {
  customElements.define("md-circular-progress", MdCircularProgress);
}

// ── Filter Chip ──
import { MdFilterChip } from "@material/web/chips/filter-chip.js";
if (!customElements.get("md-filter-chip")) {
  customElements.define("md-filter-chip", MdFilterChip);
}

// ── 以下组件 HA 通常已注册，仅作兜底 ──
import { MdFilledButton } from "@material/web/button/filled-button.js";
if (!customElements.get("md-filled-button")) {
  customElements.define("md-filled-button", MdFilledButton);
}

import { MdFilledTonalButton } from "@material/web/button/filled-tonal-button.js";
if (!customElements.get("md-filled-tonal-button")) {
  customElements.define("md-filled-tonal-button", MdFilledTonalButton);
}

import { MdOutlinedButton } from "@material/web/button/outlined-button.js";
if (!customElements.get("md-outlined-button")) {
  customElements.define("md-outlined-button", MdOutlinedButton);
}

import { MdTextButton } from "@material/web/button/text-button.js";
if (!customElements.get("md-text-button")) {
  customElements.define("md-text-button", MdTextButton);
}

import { MdIconButton } from "@material/web/iconbutton/icon-button.js";
if (!customElements.get("md-icon-button")) {
  customElements.define("md-icon-button", MdIconButton);
}

import { MdCheckbox } from "@material/web/checkbox/checkbox.js";
if (!customElements.get("md-checkbox")) {
  customElements.define("md-checkbox", MdCheckbox);
}

import { MdSwitch } from "@material/web/switch/switch.js";
if (!customElements.get("md-switch")) {
  customElements.define("md-switch", MdSwitch);
}
