/**
 * SmartAgent Panel — 设备管理 tab 渲染模块
 * 包含新设备发现列表、已托管设备列表（分页+分组+搜索+批量操作）。
 */
import { TARGET_DOMAINS, SKIP_KW, SKIP_NAME_KW, DOMAIN_LABELS } from "../constants.js";

export const devicesMethods = {
  _renderDevs() {
    const PAGE_SIZE = 20;
    const $ = id => this.shadowRoot.getElementById(id);
    const ICO = this._getIcons();

    // ── 发现新设备 ──────────────────────────────────────────
    const configured = new Set(this._wsGet("devices", "devices", []).map(d => d.entity_id));

    // 绑定设置按钮（只绑一次）
    const offlineToggle = $("showOfflineToggle");
    if (offlineToggle && !offlineToggle._bound) {
      offlineToggle._bound = true;
      offlineToggle.checked = !!this._showOffline;
      offlineToggle.onchange = () => { this._showOffline = offlineToggle.checked; this._renderDevs(); };
    }
    const ignoredToggle = $("showIgnoredToggle");
    if (ignoredToggle && !ignoredToggle._bound) {
      ignoredToggle._bound = true;
      ignoredToggle.checked = !!this._showIgnored;
      ignoredToggle.onchange = () => { this._showIgnored = ignoredToggle.checked; this._renderDevs(); };
    }

    const discoverBtn = $("discoverBtn");
    if (discoverBtn && !discoverBtn._bound) {
      discoverBtn._bound = true;
      discoverBtn.onclick = async () => {
        discoverBtn.classList.add("loading");
        try {
          await this._callService("smart_agent", "discover_devices", {});
          this._msg("扫描完成，正在刷新列表...");
          // 扫描后清除 WS 设备缓存，触发重新拉取
          delete this._wsData["devices"];
          await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
        } catch(e) { this._msg("扫描失败: " + e.message); }
        finally { setTimeout(() => discoverBtn.classList.remove("loading"), 500); }
      };
    }

    const syncToHaBtn = $("syncToHaBtn");
    if (syncToHaBtn && !syncToHaBtn._bound) {
      syncToHaBtn._bound = true;
      syncToHaBtn.onclick = async () => {
        syncToHaBtn.classList.add("loading");
        try {
          await this._callService("smart_agent", "sync_rooms_to_ha", {});
          this._msg("同步完成！AI 分区已应用到 HA 区域注册表。");
          // 同步后立即重新渲染设备列表，反映最新的 HA 区域名称
          this._renderDevs();
        } catch(e) { this._msg("同步失败: " + e.message); }
        finally { setTimeout(() => syncToHaBtn.classList.remove("loading"), 500); }
      };
    }

    // 构建 entity_id -> HA area 名称映射（通过 hass.entities + hass.areas）
    const _haAreaMap = {};
    if (this._hass.entities && this._hass.areas) {
      const areasById = this._hass.areas; // { area_id: { area_id, name, ... } }
      Object.values(this._hass.entities).forEach(ent => {
        const areaId = ent.area_id;
        if (areaId && areasById[areaId]) {
          _haAreaMap[ent.entity_id] = areasById[areaId].name;
        }
      });
    }

    const showIgnored = this._showIgnored || false;
    /** 精确判断 Frigate 摄像头控制开关（同 Python 侧 _is_frigate_control_entity） */
    const _isFrigateControl = (eid) => {
      const obj = eid.includes(".") ? eid.split(".")[1] : eid;
      if (!obj.startsWith("cam_")) return false;
      return ["_detect","_motion","_improve_contrast","_autotracking"].some(s => obj.endsWith(s));
    };

    let allNew = Object.values(this._hass.states).filter(s => {
      const d = s.entity_id.split(".")[0];
      if (!TARGET_DOMAINS.includes(d)) return false;
      if (!showIgnored) {
        if (SKIP_KW.some(k => s.entity_id.includes(k))) return false;
        if (_isFrigateControl(s.entity_id)) return false;
        const n = s.attributes?.friendly_name || "";
        if (SKIP_NAME_KW.some(k => n.toLowerCase().includes(k.toLowerCase()))) return false;
      }
      return !configured.has(s.entity_id);
    }).map(s => ({
      id: s.entity_id,
      n: s.attributes.friendly_name || s.entity_id,
      d: s.entity_id.split(".")[0],
      s: s.state,
      area: _haAreaMap[s.entity_id] || "",
      unavail: ["unavailable","unknown"].includes(s.state)
    }));

    const showOffline = this._showOffline || false;
    const filteredNew = showOffline ? allNew : allNew.filter(i => !i.unavail);
    const newTypes = [...new Set(allNew.map(i => i.d))].sort();
    const dtf = $("devTypeFilter");
    const activeNT = this._newTypeFilter || "all";

    // 搜索框绑定（只绑一次，避免重复注册）
    const newSearchEl = $("newDevSearch");
    if (newSearchEl && !newSearchEl._bound) {
      newSearchEl._bound = true;
      newSearchEl.oninput = () => { this._newSearchKw = newSearchEl.value; this._newPage = 0; this._renderDevs(); };
    }
    const newKw = (this._newSearchKw || "").trim().toLowerCase();
    
    dtf.innerHTML = ["all", ...newTypes].map(t => {
      const cnt = t === "all" ? filteredNew.length : filteredNew.filter(i => i.d === t).length;
      if (t !== "all" && cnt === 0) return ""; // 过滤掉零计数芯片（离线隐藏时）
      const label = t === "all" ? "全部" : (DOMAIN_LABELS[t] || this._esc(t));
      return `<md-filter-chip class="ntf-btn" ${activeNT===t?'selected':''} data-t="${this._esc(t)}" label="${label} (${cnt})"></md-filter-chip>`;
    }).join("");
    
    dtf.querySelectorAll(".ntf-btn").forEach(b => b.onclick = () => {
      this._newTypeFilter = b.dataset.t;
      this._newPage = 0;
      this._renderDevs();
    });

    const typeFiltered0 = (activeNT === "all") ? filteredNew : filteredNew.filter(i => i.d === activeNT);
    const typeFiltered = newKw
      ? typeFiltered0.filter(i => i.n.toLowerCase().includes(newKw) || i.id.toLowerCase().includes(newKw))
      : typeFiltered0;
    const totalNew = typeFiltered.length;
    const totalNewPages = Math.ceil(totalNew / PAGE_SIZE) || 1;
    if (this._newPage >= totalNewPages) this._newPage = totalNewPages - 1;
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
      pageItems.forEach(i => {
        const isSelected = this._selectedNew.has(i.id);
        html += `
          <div class="m3-item dev-row ${isSelected?'selected':''} ${i.unavail?'dev-unavail':''}" data-id="${this._esc(i.id)}" data-type="new" style="cursor:pointer">
            <md-checkbox ${isSelected?'checked':''} aria-checked="${isSelected}"></md-checkbox>
            <div class="m3-icon">${ICO[i.d] || ICO.device}</div>
            <div class="m3-content">
              <div class="m3-title">${this._esc(i.n)}</div>
              <div class="m3-subtitle">${this._esc(i.id)}${i.area ? ` · <span style="color:var(--sa-primary)">${this._esc(i.area)}</span>` : ''}</div>
            </div>
            <div class="body-s" style="text-align:right;flex-shrink:0">${i.unavail ? '<span style="color:var(--sa-state-offline)">离线</span>' : this._esc(i.s)}</div>
          </div>`;
      });
      nt.innerHTML = html + `</div>`;
      nt.querySelectorAll(".dev-row").forEach(el => el.onclick = () => {
        const id = el.dataset.id;
        // 互斥选择：点击新设备时，清空已配置设备的选择
        this._selectedCfg.clear();
        
        if (this._selectedNew.has(id)) this._selectedNew.delete(id);
        else this._selectedNew.add(id);
        this._renderDevs();
        this._updateBatchFab();
      });
    }
    this._renderPager($("nPager"), this._newPage, totalNewPages, p => { this._newPage = p; this._renderDevs(); });

    // ── 已配置设备 ──────────────────────────────────────────
    const cAll = this._wsGet("devices", "devices", []);

    // ── 房间筛选器 ──────────────────────────────────────────
    const cfgRooms = [
      ...new Set(cAll.map(i => i.room || "（未分区）"))
    ].sort((a, b) => {
      if (a === "（未分区）") return 1;
      if (b === "（未分区）") return -1;
      return a.localeCompare(b, "zh");
    });
    const activeRoom = this._cfgRoomFilter || "all";
    const noRoomCnt  = cAll.filter(d => !d.room).length;

    const rrf = $("cfgRoomFilter");
    if (rrf) {
      rrf.innerHTML = [
        { key: "all", label: `全部房间`, cnt: cAll.length },
        ...cfgRooms.map(r => ({
          key: r,
          label: r === "（未分区）" ? `⚠ 未分区` : r,
          cnt: cAll.filter(i => (i.room || "（未分区）") === r).length,
        })),
      ].map(({ key, label, cnt }) => {
        const isUnassigned = key === "（未分区）";
        const isActive     = activeRoom === key;
        const baseStyle    = isUnassigned && !isActive
          ? "--md-filter-chip-container-color:var(--sa-err-container);--md-filter-chip-label-text-color:var(--sa-err);"
          : "";
        return `<md-filter-chip class="crf-btn" ${isActive ? "selected" : ""}
          data-r="${this._esc(key)}" label="${this._esc(label)} (${cnt})" style="${baseStyle}">
        </md-filter-chip>`;
      }).join("");
      rrf.querySelectorAll(".crf-btn").forEach(b => b.onclick = () => {
        const newRoom = b.dataset.r;
        if (newRoom !== (this._cfgRoomFilter || "all")) {
          // 切换房间时重置类型筛选，避免"灯"在新房间无效而显示空列表
          this._cfgTypeFilter = "all";
          // 清空跨房间的选中状态，避免 FAB 显示不可见设备的选中数
          this._selectedCfg.clear();
          this._updateBatchFab?.();
        }
        this._cfgRoomFilter = newRoom;
        this._cfgPage = 0;
        this._renderDevs();
      });
      // 未分区按钮隐藏/显示
      if (noRoomCnt === 0) {
        rrf.querySelectorAll(".crf-btn").forEach(b => {
          if (b.dataset.r === "（未分区）") b.style.display = "none";
        });
      }
    }

    // 「未分区」快捷筛选按钮（标题栏旁边，保留但与房间筛选器联动）
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
        if (this._cfgRoomFilter === "（未分区）") this._cfgRoomFilter = "all";
      }
    }

    // ── 类型筛选器 ──────────────────────────────────────────
    // 类型数量基于当前房间筛选后的结果
    const cAllRoom = activeRoom === "all"
      ? cAll
      : cAll.filter(i => (i.room || "（未分区）") === activeRoom);
    const cfgTypes = [...new Set(cAllRoom.map(i => i.type || "其他"))].sort();
    const ctf      = $("cfgTypeFilter");
    const activeCT = this._cfgTypeFilter || "all";

    const cfgSearchEl = $("cfgDevSearch");
    if (cfgSearchEl && !cfgSearchEl._bound) {
      cfgSearchEl._bound = true;
      cfgSearchEl.oninput = () => { this._cfgSearchKw = cfgSearchEl.value; this._cfgPage = 0; this._renderDevs(); };
    }
    const cfgKw = (this._cfgSearchKw || "").trim().toLowerCase();

    ctf.innerHTML = ["all", ...cfgTypes].map(t => {
      const cnt = t === "all"
        ? cAllRoom.length
        : cAllRoom.filter(i => (i.type || "其他") === t).length;
      if (t !== "all" && cnt === 0) return ""; // 隐藏零计数的类型芯片
      const label = t === "all" ? "全部类型" : (DOMAIN_LABELS[t] || this._esc(t));
      return `<md-filter-chip class="ctf-btn" ${activeCT === t ? "selected" : ""} data-t="${this._esc(t)}" label="${label} (${cnt})"></md-filter-chip>`;
    }).join("");
    ctf.querySelectorAll(".ctf-btn").forEach(b => b.onclick = () => {
      this._cfgTypeFilter = b.dataset.t;
      this._cfgPage = 0;
      this._renderDevs();
    });

    // 应用：房间 → 类型 → 搜索 三级过滤
    let cfgFiltered0 = cAllRoom;
    if (activeCT !== "all") cfgFiltered0 = cfgFiltered0.filter(i => (i.type || "其他") === activeCT);
    const cfgFiltered = cfgKw
      ? cfgFiltered0.filter(i =>
          (i.name||"").toLowerCase().includes(cfgKw) ||
          (i.entity_id||"").toLowerCase().includes(cfgKw) ||
          (i.room||"").toLowerCase().includes(cfgKw))
      : cfgFiltered0;
    const totalCfg = cfgFiltered.length;
    const totalCfgPages = Math.ceil(totalCfg / PAGE_SIZE) || 1;
    if (this._cfgPage >= totalCfgPages) this._cfgPage = totalCfgPages - 1;
    const cfgPageSlice = cfgFiltered.slice(this._cfgPage * PAGE_SIZE, (this._cfgPage + 1) * PAGE_SIZE);

    // 计数标签：有选中 → "N 已选"，有筛选 → "N / 总 已托管"，无筛选 → "N 个已托管"
    const _hasFilter = (activeRoom !== "all") || (activeCT !== "all") || cfgKw;
    $("cCntLbl").textContent = this._selectedCfg.size
      ? `${this._selectedCfg.size} 已选`
      : _hasFilter
        ? `${totalCfg} / ${cAll.length} 个已托管`
        : `${totalCfg} 个已托管`;
    
    const ct = $("cTable");
    if (!cAll.length) {
      ct.innerHTML = `<div class="body-s" style="text-align:center;padding:40px;opacity:.5">尚未添加任何托管设备</div>`;
    } else if (!cfgFiltered.length) {
      // 有设备但筛选后为空 → 提示用户而非空白页面
      const filterDesc = [
        activeRoom !== "all" ? `房间「${activeRoom}」` : "",
        activeCT   !== "all" ? `类型「${DOMAIN_LABELS[activeCT] || activeCT}」` : "",
        cfgKw ? `关键字「${cfgKw}」` : "",
      ].filter(Boolean).join(" + ");
      ct.innerHTML = `
        <div style="text-align:center;padding:40px;opacity:.7">
          <div style="font-size:32px;margin-bottom:12px">🔍</div>
          <div class="label-m" style="margin-bottom:6px">当前筛选无结果</div>
          <div class="body-s">${this._esc(filterDesc)}</div>
          <md-filled-tonal-button style="--md-filled-tonal-button-container-height:32px;font-size:13px;margin-top:16px" id="cfgClearFilter">清除筛选</md-filled-tonal-button>
        </div>`;
      const clearBtn = ct.querySelector("#cfgClearFilter");
      if (clearBtn) clearBtn.onclick = () => {
        this._cfgRoomFilter = "all";
        this._cfgTypeFilter = "all";
        this._cfgSearchKw   = "";
        const s = $("cfgDevSearch");
        if (s) s.value = "";
        this._cfgPage = 0;
        this._renderDevs();
      };
    } else {
      const MODE_CFG = {
        ai:     { label: "AI全权", bg: "rgba(103,80,164,.13)", color: "var(--sa-primary)" },
        ha:     { label: "HA优先", bg: "rgba(25,118,210,.12)", color: "#1976d2" },
        shared: { label: "共享",   bg: "rgba(80,80,80,.1)",   color: "var(--sa-text-variant)" },
      };

      /** 从 HA states 取简短的中文状态文本 */
      const _stateLabel = (entityId) => {
        const st = (this._hass?.states || {})[entityId];
        if (!st) return null;
        const s = st.state;
        if (["unavailable","unknown"].includes(s)) return { text: "离线", ok: false };
        const domain = entityId.split(".")[0];
        if (domain === "light" || domain === "switch" || domain === "fan") {
          return { text: s === "on" ? "开" : "关", ok: s === "on" };
        }
        if (domain === "binary_sensor") {
          return { text: s === "on" ? "触发" : "正常", ok: s === "on" };
        }
        if (domain === "climate") {
          const temp = st.attributes?.current_temperature;
          return { text: temp != null ? `${temp}℃` : (s === "off" ? "关" : s), ok: s !== "off" };
        }
        if (domain === "cover") {
          return { text: s === "open" ? "开" : s === "closed" ? "关" : s, ok: s === "open" };
        }
        if (domain === "sensor") {
          const unit = st.attributes?.unit_of_measurement || "";
          return { text: `${s}${unit}`.substring(0, 10), ok: true };
        }
        return { text: String(s).substring(0, 10), ok: true };
      };

      // 按房间分组（cfgPageSlice 已经过搜索/类型过滤）
      const roomGroups = {};
      cfgPageSlice.forEach(i => {
        const room = i.room || "（未分区）";
        if (!roomGroups[room]) roomGroups[room] = [];
        roomGroups[room].push(i);
      });
      const sortedRooms = Object.keys(roomGroups).sort((a, b) => {
        if (a === "（未分区）") return 1;
        if (b === "（未分区）") return -1;
        return a.localeCompare(b, "zh");
      });

      let html = "";
      sortedRooms.forEach(room => {
        const items = roomGroups[room];
        const isUnassigned = room === "（未分区）";

        // 房间内设备类型统计（用 type 字段，已存为中文）
        const typeCounts = {};
        items.forEach(i => { const t = i.type || "其他"; typeCounts[t] = (typeCounts[t] || 0) + 1; });
        const typeBreakdown = Object.entries(typeCounts)
          .map(([t, n]) => `<span style="font-size:11px;padding:1px 7px;border-radius:8px;
            background:var(--sa-primary-container);color:var(--sa-on-primary-container)">${this._esc(t)} ${n}</span>`)
          .join("");

        html += `
          <div style="margin-bottom:20px">
            <!-- 房间分组标题 -->
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;
                        padding:8px 12px;border-radius:10px;
                        background:${isUnassigned ? 'var(--sa-err-container)' : 'var(--sa-primary-container)'};
                        border-left:3px solid ${isUnassigned ? 'var(--sa-err)' : 'var(--sa-primary)'}">
              <span style="font-size:13px;font-weight:700;
                           color:${isUnassigned ? 'var(--sa-err)' : 'var(--sa-primary)'}">
                ${isUnassigned ? '⚠ 未分区' : this._esc(room)}
              </span>
              <span style="font-size:11px;background:rgba(0,0,0,.1);border-radius:8px;
                           padding:1px 8px;color:inherit;font-weight:500">${items.length} 台</span>
              <div style="display:flex;flex-wrap:wrap;gap:4px;margin-left:4px">${typeBreakdown}</div>
            </div>
            <!-- 设备卡片列表 -->
            <div style="display:flex;flex-direction:column;gap:6px">`;

        items.forEach(i => {
          const domain     = (i.entity_id || "").split(".")[0];
          const mode       = i.control_mode || "shared";
          const modeCfg    = MODE_CFG[mode] || MODE_CFG.shared;
          const isSelected = this._selectedCfg.has(i.entity_id);
          const stLabel    = _stateLabel(i.entity_id);
          const isOnline   = stLabel ? stLabel.ok !== false && stLabel.text !== "离线" : null;
          // 截断过长的 entity_id：取最后 40 字符并加省略号前缀
          const eidDisplay = i.entity_id.length > 40
            ? `…${i.entity_id.slice(-38)}`
            : i.entity_id;

          html += `
              <div class="dev-row" data-id="${this._esc(i.entity_id)}" data-type="cfg"
                   style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:12px;
                          cursor:pointer;transition:background .15s;
                          background:${isSelected ? 'var(--sa-primary-container)' : 'var(--sa-card)'};
                          border:1px solid ${isSelected ? 'var(--sa-primary)' : 'var(--sa-border)'}">
                <!-- 勾选框 -->
                <md-checkbox ${isSelected ? 'checked' : ''} style="flex-shrink:0"></md-checkbox>
                <!-- 图标 + 状态点 -->
                <div style="position:relative;flex-shrink:0;width:36px;height:36px;
                            border-radius:10px;background:var(--sa-primary-container);
                            display:flex;align-items:center;justify-content:center;font-size:18px">
                  ${ICO[domain] || ICO.device}
                  ${stLabel ? `<span style="position:absolute;bottom:1px;right:1px;width:8px;height:8px;
                    border-radius:50%;border:1.5px solid var(--sa-card);
                    background:${isOnline ? '#4caf50' : '#9e9e9e'}"></span>` : ""}
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
                            background:${isOnline ? 'rgba(76,175,80,.12)' : 'rgba(0,0,0,.07)'};
                            color:${isOnline ? '#388e3c' : 'var(--sa-text-variant)'}">
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
                  data-id="${this._esc(i.entity_id)}"
                  data-name="${this._esc(i.name)}"
                  data-room="${this._esc(i.room || '')}"
                  data-type="${this._esc(i.type || '')}"
                  title="编辑" style="flex-shrink:0;color:var(--sa-text-variant)">
                  ${ICO.edit}
                </md-icon-button>
                <md-icon-button class="help-close single-del-btn"
                  data-id="${this._esc(i.entity_id)}"
                  data-name="${this._esc(i.name)}"
                  title="停止托管" style="flex-shrink:0;color:var(--sa-text-variant)">
                  ${ICO.delete}
                </md-icon-button>
              </div>`;
        });
        html += `</div></div>`;
      });
      ct.innerHTML = html;

      // 绑定整行点击选中
      ct.querySelectorAll(".dev-row").forEach(el => {
        el.onclick = (e) => {
          if (e.target.closest(".single-del-btn") || e.target.closest(".single-edit-btn")) return;
          const id = el.dataset.id;
          this._selectedNew.clear();
          if (this._selectedCfg.has(id)) this._selectedCfg.delete(id);
          else this._selectedCfg.add(id);
          this._renderDevs();
          this._updateBatchFab();
        };
        // 悬停高亮
        el.onmouseenter = () => {
          if (!this._selectedCfg.has(el.dataset.id))
            el.style.background = "var(--sa-primary-container)";
        };
        el.onmouseleave = () => {
          if (!this._selectedCfg.has(el.dataset.id))
            el.style.background = "var(--sa-card)";
        };
      });

      // 绑定删除按钮
      ct.querySelectorAll(".single-del-btn").forEach(btn => {
        btn.onclick = async (e) => {
          e.stopPropagation();
          const id = btn.dataset.id, name = btn.dataset.name;
          if (!(await this._showConfirm(`确定要停止托管设备「${name || id}」吗？`))) return;
          try {
            await this._callService("smart_agent", "delete_device", { entity_id: id });
            this._msg("已停止托管该设备");
            delete this._wsData["devices"];
            await this._wsRefresh("smart_agent/get_devices", "devices", () => this._renderDevs());
          } catch(err) { this._msg("操作失败: " + err.message); }
        };
      });

      // 绑定编辑按钮
      ct.querySelectorAll(".single-edit-btn").forEach(btn => {
        btn.onclick = async (e) => {
          e.stopPropagation();
          await this._showEditDevDialog(
            btn.dataset.id, btn.dataset.name, btn.dataset.room, btn.dataset.type,
          );
        };
      });
    }
    this._renderPager($("cPager"), this._cfgPage, totalCfgPages, p => { this._cfgPage = p; this._renderDevs(); });

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(this.shadowRoot, "#discoverBtn,#syncToHaBtn,.single-del-btn,.single-edit-btn");
    }
  }
};
