/**
 * SmartAgent Panel — 房间拓扑配置页
 * 可视化编辑房间相邻/连通关系，AI 推理跨房间场景时参考此拓扑
 */

export const roomsMethods = {
  _renderRooms() {
    const view = this.shadowRoot.getElementById("view-rooms");
    if (!view) return;

    const ADJ_SEP = "||";
    const adjKey = (a, b) => (a < b ? `${a}${ADJ_SEP}${b}` : `${b}${ADJ_SEP}${a}`);
    const parseAdjKey = key => {
      const idx = key.indexOf(ADJ_SEP);
      return idx < 0 ? ["", ""] : [key.slice(0, idx), key.slice(idx + ADJ_SEP.length)];
    };

    const haAreas = this._hass.areas
      ? Object.values(this._hass.areas).map(a => a.name)
      : [];
    const devices = this._wsGet("devices", "devices", []);
    const devRooms = devices.map(d => d.room || "").filter(r => r);
    const customRooms = Array.isArray(this._customRooms) ? this._customRooms : [];
    const rooms = [...new Set([...haAreas, ...devRooms, ...customRooms])].filter(r => r && r.trim())
      .sort((a, b) => a.localeCompare(b, "zh"));

    if (!this._roomAdj) this._roomAdj = {};
    const adj = this._roomAdj;

    const isAdj = (a, b) => !!adj[adjKey(a, b)];

    const setAdj = (a, b, val) => {
      const key = adjKey(a, b);
      if (val) adj[key] = true;
      else delete adj[key];
    };

    const clearAdj = () => {
      Object.keys(adj).forEach(k => delete adj[k]);
    };

    const neighborMap = new Map(rooms.map(r => [r, []]));
    Object.keys(adj).forEach(k => {
      const [a, b] = parseAdjKey(k);
      if (!adj[k] || !a || !b || !neighborMap.has(a) || !neighborMap.has(b)) return;
      neighborMap.get(a).push(b);
      neighborMap.get(b).push(a);
    });
    const neighborsOf = r => neighborMap.get(r) || [];

    const editorRoom = (this._roomEditorRoom && rooms.includes(this._roomEditorRoom))
      ? this._roomEditorRoom
      : rooms[0] || "";
    this._roomEditorRoom = editorRoom;
    const editorIdx = rooms.indexOf(editorRoom);

    const sortedPairs = [];
    for (let i = 0; i < rooms.length - 1; i++) sortedPairs.push([i, i + 1]);

    const applyPreset = preset => {
      clearAdj();
      if (!rooms.length) return;
      if (preset === "chain") {
        sortedPairs.forEach(([a, b]) => setAdj(rooms[a], rooms[b], true));
        this._msg("已应用示例：线性串联关系");
      } else if (preset === "star") {
        const hub = editorRoom || rooms[0];
        rooms.forEach(r => { if (r !== hub) setAdj(r, hub, true); });
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
              ${rooms.map((r, idx) => `
                <button
                  class="btn ${editorRoom === r ? "btn-filled" : "btn-tonal"} btn-sm"
                  style="justify-content:space-between;display:flex;align-items:center"
                  data-edit-room="${idx}">
                  <span>${this._esc(r)}</span>
                  <span class="body-s" style="opacity:.7">${neighborsOf(r).length} 相邻</span>
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
                ${rooms.map((r, idx) => r === editorRoom ? "" : `
                  <label class="btn btn-soft" style="justify-content:flex-start;display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:10px">
                    <md-checkbox
                      data-editor
                      data-a="${editorIdx}"
                      data-b="${idx}"
                      ${isAdj(editorRoom, r) ? "checked" : ""}
                    ></md-checkbox>
                    <span>${this._esc(r)}</span>
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

    const $ = id => view.querySelector("#" + id);

    if (this._isHaFallbackReadOnly()) {
      this._disableHaFallbackWriteControls(view, "[data-edit-room],md-checkbox[data-editor],[data-preset],#roomClearCurrentBtn,#roomClearAllBtn,#roomSaveBtn,#roomSyncHaBtn,#addRoomBtn,#newRoomInput");
    }

    view.querySelectorAll("[data-edit-room]").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.editRoom, 10);
        this._roomEditorRoom = rooms[idx];
        this._renderRooms();
      });
    });

    view.querySelectorAll("md-checkbox[data-editor]").forEach(cb => {
      cb.addEventListener("change", () => {
        const aIdx = parseInt(cb.dataset.a, 10);
        const bIdx = parseInt(cb.dataset.b, 10);
        const a = rooms[aIdx];
        const b = rooms[bIdx];
        setAdj(a, b, cb.checked);
        const summary = view.querySelector("#roomTopoSummary");
        if (summary) summary.innerHTML = this._buildTopoSummary(rooms, adj);

        const roomList = view.querySelector("#roomList");
        if (roomList) {
          roomList.querySelectorAll("button[data-edit-room]").forEach(rowBtn => {
            const r = rooms[parseInt(rowBtn.dataset.editRoom, 10)];
            if (r && r !== a && r !== b) return;
            const label = rowBtn.querySelector("span:last-child");
            if (label) label.textContent = `${neighborsOf(r).length} 相邻`;
          });
        }
      });
    });

    view.querySelectorAll("[data-preset]").forEach(btn => {
      btn.addEventListener("click", () => {
        applyPreset(btn.dataset.preset);
      });
    });

    const clearBtn = $("roomClearAllBtn");
    if (clearBtn) {
      clearBtn.onclick = async () => {
        if (!(await this._showConfirm("确定清空全部相邻关系？"))) return;
        clearAdj();
        this._renderRooms();
      };
    }

    const clearCurrent = $("roomClearCurrentBtn");
    if (clearCurrent && editorRoom) {
      clearCurrent.onclick = async () => {
        const toDelete = Object.keys(adj).filter(k => {
          const [a, b] = parseAdjKey(k);
          return a === editorRoom || b === editorRoom;
        });
        toDelete.forEach(k => delete adj[k]);
        this._renderRooms();
      };
    }

    $("roomSaveBtn").onclick = async () => {
      try {
        const topology = Object.keys(adj).map(k => {
          const [a, b] = parseAdjKey(k);
          return { room_a: a, room_b: b, relation: "adjacent" };
        }).filter(it => it.room_a && it.room_b);
        await this._callService("smart_agent", "save_room_topology", { topology });
        this._msg("房间拓扑已保存");
      } catch (e) {
        this._msg("保存失败: " + e.message);
      }
    };

    $("roomSyncHaBtn").onclick = async () => {
      try {
        await this._callService("smart_agent", "sync_rooms_to_ha");
        this._msg("已同步 HA 区域");
        this._renderRooms();
      } catch (e) {
        this._msg("同步失败: " + e.message);
      }
    };

    $("addRoomBtn").onclick = () => {
      const input = $("newRoomInput");
      const name = input?.value?.trim();
      if (!name) return;
      if (!this._customRooms) this._customRooms = [];
      if (!this._customRooms.includes(name)) {
        this._customRooms.push(name);
        this._roomEditorRoom = name;
        this._renderRooms();
      }
      if (input) input.value = "";
    };

    $("newRoomInput").onkeydown = e => {
      if (e.key === "Enter") $("addRoomBtn").click();
    };
  },

  _buildTopoSummary(rooms, adj) {
    const ADJ_SEP = "||";
    const parseAdjKey = key => {
      const idx = key.indexOf(ADJ_SEP);
      return idx < 0 ? ["", ""] : [key.slice(0, idx), key.slice(idx + ADJ_SEP.length)];
    };

    const neighborMap = new Map(rooms.map(r => [r, []]));
    Object.keys(adj).forEach(k => {
      const [a, b] = parseAdjKey(k);
      if (!adj[k] || !a || !b || !neighborMap.has(a) || !neighborMap.has(b)) return;
      neighborMap.get(a).push(b);
      neighborMap.get(b).push(a);
    });

    const lines = rooms.map(r => {
      const neighbors = neighborMap.get(r) || [];
      if (!neighbors.length) return "";
      return `<div style="padding:6px 12px;background:var(--sa-bg);border-radius:8px;
        border:1px solid var(--sa-border);font-size:13px">
        <b>${this._esc(r)}</b> ↔ ${neighbors.map(n => this._esc(n)).join("、")}
      </div>`;
    }).filter(Boolean);
    return lines.length
      ? lines.join("")
      : `<div class="body-s" style="opacity:.5">暂无相邻关系，请在矩阵中勾选</div>`;
  },

  // 加载已保存的拓扑数据
  async _loadRoomTopology() {
    try {
      const result = await this._hass.callWS({ type: "smart_agent/get_room_topology" });
      this._roomAdj = {};
      (result?.topology || []).forEach(({ room_a, room_b }) => {
        const key = [room_a, room_b].sort().join("||");
        this._roomAdj[key] = true;
      });
    } catch (e) {
      this._roomAdj = {};
      this._msg("加载房间拓扑失败: " + e.message);
    }
  },
};
