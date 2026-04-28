/**
 * SmartAgent Panel — 通用工具方法 mixin
 * 通过 Object.assign(SmartAgentPanel.prototype, helperMethods) 挂载
 */

export const helperMethods = {
  /** HTML 转义，防止 XSS */
  _esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  },

  /** 轻量 Toast 提示 */
  _msg(m) {
    const t = this.shadowRoot.getElementById("toast");
    t.textContent = m;
    t.className = "show";
    setTimeout(() => (t.className = ""), 3000);
  },

  _isHaFallbackReadOnly() {
    return true;
  },

  _warnHaFallbackReadOnly() {
    this._msg("HA 面板已降级为只读/应急兜底，请前往 SmartAgent UI v2 执行写操作");
  },

  _disableHaFallbackWriteControls(root, selectors = "") {
    if (!this._isHaFallbackReadOnly() || !root || !selectors) return;
    root.querySelectorAll(selectors).forEach(el => {
      if (!el) return;
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

    return new Promise(resolve => {
      const done = val => {
        ov.classList.remove("open");
        ok.onclick = null;
        cl.onclick = null;
        ov.onclick = null;
        resolve(val);
      };
      ok.onclick = e => {
        e.stopPropagation();
        done(true);
      };
      cl.onclick = e => {
        e.stopPropagation();
        done(false);
      };
      ov.onclick = e => {
        if (e.target === ov) done(false);
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
    const $ = id => this.shadowRoot.getElementById(id);
    const ov       = $("m3EditDevOverlay");
    const nameEl   = $("editDevName");
    const roomSel  = $("editDevRoomSel");
    const roomCustom = $("editDevRoomCustom");
    const typeEl   = $("editDevType");
    const saveBtn  = $("m3EditDevSave");
    const cancelBtn = $("m3EditDevCancel");

    nameEl.value = currentName || "";
    typeEl.value = currentType || "";
    roomCustom.value = "";

    // 重建房间下拉（合并 HA 区域 + 已配置设备的房间）
    while (roomSel.options.length > 1) roomSel.remove(1);
    const cAll = this._wsGet("devices", "devices", []);
    const smRooms = cAll.map(i => i.room || "").filter(r => r);
    const haAreas = this._hass.areas
      ? Object.values(this._hass.areas).map(a => a.name)
      : [];
    const allRooms = [...new Set([...haAreas, ...smRooms])].sort((a, b) =>
      a.localeCompare(b, "zh")
    );

    const firstOpt = document.createElement("option");
    firstOpt.value = "";
    firstOpt.textContent = "选择房间…";
    roomSel.innerHTML = "";
    roomSel.appendChild(firstOpt);

    allRooms.forEach(r => {
      const opt = document.createElement("option");
      opt.value = r;
      opt.textContent = r;
      if (r === currentRoom) opt.selected = true;
      roomSel.appendChild(opt);
    });

    if (currentRoom && !allRooms.includes(currentRoom)) {
      roomCustom.value = currentRoom;
    }

    ov.classList.add("open");

    return new Promise(resolve => {
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
          setTimeout(() => (nameEl.style.borderColor = ""), 1200);
          return;
        }

        try {
          const payload = { entity_id: entityId };
          if (newName) payload.name = newName;
          if (newRoom) payload.room = newRoom;
          if (newType) payload.dev_type = newType;
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
      ov.onclick = e => { if (e.target === ov) close(); };
    });
  },

  /**
   * 通过 WebSocket 拉取数据并存入 _wsData，完成后回调渲染函数。
   * @param {string} type  WS 命令类型，如 "smart_agent/get_devices"
   * @param {string} key   _wsData 的缓存 key
   * @param {Function} cb  数据就绪后的渲染回调
   */
  async _wsRefresh(type, key, cb) {
    if (this._wsLoading[key]) return;
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
    const s = this._hass.states[id];
    if (s?.attributes?.friendly_name) return s.attributes.friendly_name;
    const cfgList = this._wsGet("devices", "devices", []);
    const found = cfgList.find(d => d.entity_id === id);
    if (found?.name) return found.name;
    return id;
  },
};
