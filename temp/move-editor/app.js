'use strict';

// ── Constants ────────────────────────────────────────────────────────────────

const TYPE_COLORS = {
  normal:'#A8A878',  fire:'#F08030',   water:'#6890F0',   electric:'#F8D030',
  grass:'#78C850',   ice:'#98D8D8',    fighting:'#C03028', poison:'#A040A0',
  ground:'#E0C068',  flying:'#A890F0', psychic:'#F85888',  bug:'#A8B820',
  rock:'#B8A038',    ghost:'#705898',  dragon:'#7038F8',   dark:'#705848',
  steel:'#B8B8D0',   fairy:'#EE99AC',
};

const _IMG = (slug, label) =>
  `<img src="https://img.pokemondb.net/images/icons/move-${slug}.png" width="22" height="20" style="vertical-align:-4px" alt="${label}" title="${label}">`;

const DMG_ICON = {
  physical: _IMG('physical', 'Physical'),
  special:  _IMG('special',  'Special'),
  status:   _IMG('status',   'Status'),
  both:     _IMG('physical', 'Physical') + ' / ' + _IMG('special', 'Special'),
};

const PENCIL_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`;
const TRASH_SVG  = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>`;

// ── App state ─────────────────────────────────────────────────────────────────

let allMoves     = [];
let filtered     = [];
let selectedMove = null;
let curEvents    = [];
let curConds     = [];
let curDesc      = '';
let withDataSet  = new Set();  // move names with saved events/conditions
let presets      = [];         // full preset list, kept in sync with API

// ── Helpers ───────────────────────────────────────────────────────────────────

const cap     = s => s.charAt(0).toUpperCase() + s.slice(1);
const esc     = s => String(s ?? '')
  .replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;');

function deepClone(arr) {
  return arr.map(item => ({
    ...item,
    params: (item.params || []).map(p => ({ ...p })),
  }));
}

function moveHasData(name) {
  return withDataSet.has(name);
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function apiPut(path, body) {
  const res = await fetch(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT ${path} → ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(path, { method: 'DELETE' });
  if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`);
  return res.json();
}

// ── Filtering ─────────────────────────────────────────────────────────────────

function applyFilters() {
  const q   = document.getElementById('searchInput').value.toLowerCase();
  const gen = document.getElementById('genFilter').value;
  const typ = document.getElementById('typeFilter').value;
  const cat = document.getElementById('catFilter').value;

  filtered = allMoves.filter(m => {
    if (gen !== 'all' && m.generation !== parseInt(gen)) return false;
    if (typ !== 'all' && m.type !== typ)                 return false;
    if      (cat === 'z')       { if (m.moveCat !== 'z')       return false; }
    else if (cat === 'max')     { if (m.moveCat !== 'max')     return false; }
    else if (cat === 'partner') { if (m.moveCat !== 'partner') return false; }
    else if (cat === 'standard'){ if (m.moveCat !== 'standard')return false; }
    if (q && !m.name.includes(q) && !m.displayName.toLowerCase().includes(q) && !m.type.includes(q))
      return false;
    return true;
  });

  renderMoveList();
}

// ── Move list rendering ───────────────────────────────────────────────────────

function renderMoveList() {
  const listEl = document.getElementById('moveList');
  document.getElementById('moveCount').textContent =
    `${filtered.length} move${filtered.length !== 1 ? 's' : ''}`;

  if (filtered.length === 0) {
    listEl.innerHTML = '<div class="loading-state">No moves found.</div>';
    return;
  }

  listEl.innerHTML = '';
  for (const m of filtered) {
    const color    = TYPE_COLORS[m.type] || '#888';
    const isActive = selectedMove && m.name === selectedMove.name;
    const hasDot   = moveHasData(m.name);

    const row = document.createElement('div');
    row.className = 'move-row' + (isActive ? ' active' : '');
    row.innerHTML = `
      <div class="type-tab" style="background:${color}"></div>
      <div class="row-info">
        <div class="name">${esc(m.displayName)}</div>
        <div class="meta">${m.type.toUpperCase()} · ${m.damage_class === 'both' ? 'PHYS / SPEC' : m.damage_class.toUpperCase()}</div>
      </div>
      ${hasDot ? '<div class="row-dot" title="Has saved events/conditions"></div>' : ''}
    `;
    row.addEventListener('click', async () => selectMove(m));
    listEl.appendChild(row);
  }

  const activeEl = listEl.querySelector('.move-row.active');
  if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
}

// ── Move selection ────────────────────────────────────────────────────────────

async function selectMove(move) {
  selectedMove = move;
  try {
    const data = await apiGet(`/api/events/${encodeURIComponent(move.name)}`);
    curEvents   = deepClone(data.events     || []);
    curConds    = deepClone(data.conditions || []);
    // Use saved custom desc if non-empty, otherwise fall back to PokeAPI effect text
    curDesc     = data.custom_desc || move.effect || '';
  } catch (err) {
    console.error('Failed to load move data:', err);
    curEvents = [];
    curConds  = [];
    curDesc   = move.effect || '';
  }
  renderEditor();
  renderMoveList();
}

// ── Persist current state to per-move/preset JSON files ──────────────────────────────────────────

async function persistCurrent() {
  if (!selectedMove) return;
  try {
    await apiPut(`/api/events/${encodeURIComponent(selectedMove.name)}`, {
      events:      curEvents,
      conditions:  curConds,
      custom_desc: curDesc,
    });
    const hasData = curEvents.length > 0 || curConds.length > 0;
    if (hasData) withDataSet.add(selectedMove.name);
    else         withDataSet.delete(selectedMove.name);
    _updateRowDot();
  } catch (err) {
    console.error('Failed to save:', err);
  }
}

function _updateRowDot() {
  const listEl = document.getElementById('moveList');
  const active = listEl?.querySelector('.move-row.active');
  if (!active) return;
  const hasDot = moveHasData(selectedMove.name);
  let dot = active.querySelector('.row-dot');
  if (hasDot && !dot) {
    dot = document.createElement('div');
    dot.className = 'row-dot';
    dot.title = 'Has saved events/conditions';
    active.appendChild(dot);
  } else if (!hasDot && dot) {
    dot.remove();
  }
}

// ── Editor rendering ──────────────────────────────────────────────────────────

function renderEditor() {
  const m     = selectedMove;
  const color = TYPE_COLORS[m.type] || '#888';

  document.getElementById('editorPanel').innerHTML = `
    <div class="move-header">
      <div class="move-title-block">
        <h2>${esc(m.displayName)}</h2>
        <div class="badge-row">
          <span class="type-badge" style="background:${color}">${esc(cap(m.type))}</span>
          <span class="cat-badge" title="${esc(cap(m.damage_class))}" style="padding:3px 7px">${DMG_ICON[m.damage_class] ?? esc(cap(m.damage_class))}</span>
          ${m.moveCat === 'z'       ? `<span class="cat-badge" style="border-color:#4a3d1c;color:var(--gold)">Z-Move</span>`   : ''}
          ${m.moveCat === 'max'     ? `<span class="cat-badge" style="border-color:#4a3d1c;color:var(--gold)">Max</span>`      : ''}
          ${m.moveCat === 'partner' ? `<span class="cat-badge" style="border-color:#3a5a3a;color:var(--ok)">Partner</span>`    : ''}
        </div>
      </div>
      <div class="stat-grid">
        <div class="stat">
          <div class="val">${m.power != null ? m.power : '—'}</div>
          <div class="lbl">Power</div>
        </div>
        <div class="stat">
          <div class="val">${m.pp ?? '—'}</div>
          <div class="lbl">PP</div>
        </div>
        <div class="stat">
          <div class="val">${m.priority > 0 ? '+' + m.priority : m.priority}</div>
          <div class="lbl">Priority</div>
        </div>
      </div>
    </div>

    <div class="field-block">
      <label>Description / Notes</label>
      <textarea class="desc" id="descBox">${esc(curDesc)}</textarea>
    </div>

    <!-- Events section -->
    <div class="section">
      <div class="section-head">
        <h3>Events</h3>
        <span class="count" id="eventCount">0</span>
        <div class="spacer"></div>
        <button class="presets-trigger" id="presetsTrigger">Presets ▾</button>
        <div class="presets-panel" id="presetsPanel">
          <div class="ph">Available Presets</div>
          <div id="presetsList"></div>
        </div>
        <button class="btn btn-primary btn-sm" id="addEventBtn">+ Add Event</button>
      </div>
      <div class="section-body" id="eventsBody"></div>
    </div>

    <!-- Conditions section -->
    <div class="section">
      <div class="section-head">
        <h3>Conditions</h3>
        <span class="count" id="condCount">0</span>
        <div class="spacer"></div>
        <button class="btn btn-gold btn-sm" id="savePresetBtn">Save as Preset</button>
        <button class="btn btn-primary btn-sm" id="addCondBtn">+ Add Condition</button>
      </div>
      <div class="section-body" id="condBody"></div>
    </div>
  `;

  bindEditorListeners();
  renderEvents();
  renderConds();
}

function bindEditorListeners() {
  let descTimer = null;
  document.getElementById('descBox').addEventListener('input', e => {
    curDesc = e.target.value;
    clearTimeout(descTimer);
    descTimer = setTimeout(() => persistCurrent(), 600);
  });

  document.getElementById('addEventBtn').addEventListener('click', () => openEventModal(null));
  document.getElementById('addCondBtn').addEventListener('click',  () => openCondModal(null));
  document.getElementById('savePresetBtn').addEventListener('click', openPresetModal);

  const trigger = document.getElementById('presetsTrigger');
  const panel   = document.getElementById('presetsPanel');
  trigger.addEventListener('click', e => {
    e.stopPropagation();
    renderPresetsList();
    panel.classList.toggle('open');
  });
}

document.addEventListener('click', () => {
  const panel = document.getElementById('presetsPanel');
  if (panel) panel.classList.remove('open');
});

// ── Events section ────────────────────────────────────────────────────────────

function renderEvents() {
  const countEl = document.getElementById('eventCount');
  const body    = document.getElementById('eventsBody');
  if (!countEl || !body) return;
  countEl.textContent = curEvents.length;

  if (curEvents.length === 0) {
    body.innerHTML = '<div class="empty-row">No events yet. Click "+ Add Event" or apply a preset.</div>';
    return;
  }

  body.innerHTML = '';
  curEvents.forEach((ev, i) => {
    const tags = ev.params.slice(0, 3)
      .map(p => `<span class="mini-tag">${esc(p.key)}: ${esc(p.val)}</span>`).join('');
    const card = document.createElement('div');
    card.className = 'item-card';
    card.innerHTML = `
      <div class="idx">${String(i + 1).padStart(2, '0')}</div>
      <div class="main">
        <div class="t1">Target: ${esc(ev.target)}</div>
        <div class="t2">priority ${esc(String(ev.priority))} · ${ev.params.length} param${ev.params.length !== 1 ? 's' : ''}</div>
      </div>
      <div class="tags">${tags}</div>
      <button class="icon-btn" title="Edit">${PENCIL_SVG}</button>
      <button class="icon-btn danger" title="Delete">${TRASH_SVG}</button>
    `;
    card.querySelectorAll('.icon-btn')[0].addEventListener('click', () => openEventModal(i));
    card.querySelectorAll('.icon-btn')[1].addEventListener('click', async () => {
      curEvents.splice(i, 1);
      await persistCurrent();
      renderEvents();
    });
    body.appendChild(card);
  });
}

// ── Conditions section ────────────────────────────────────────────────────────

function renderConds() {
  const countEl = document.getElementById('condCount');
  const body    = document.getElementById('condBody');
  if (!countEl || !body) return;
  countEl.textContent = curConds.length;

  if (curConds.length === 0) {
    body.innerHTML = '<div class="empty-row">No conditions yet. Click "+ Add Condition".</div>';
    return;
  }

  body.innerHTML = '';
  curConds.forEach((c, i) => {
    const tags = c.params.slice(0, 3)
      .map(p => `<span class="mini-tag">${esc(p.key)}: ${esc(p.val)}</span>`).join('');
    const card = document.createElement('div');
    card.className = 'item-card';
    card.innerHTML = `
      <div class="idx">${String(i + 1).padStart(2, '0')}</div>
      <div class="main">
        <div class="t1">Condition ${i + 1}</div>
        <div class="t2">${c.params.length} param${c.params.length !== 1 ? 's' : ''}</div>
      </div>
      <div class="tags">${tags}</div>
      <button class="icon-btn" title="Edit">${PENCIL_SVG}</button>
      <button class="icon-btn danger" title="Delete">${TRASH_SVG}</button>
    `;
    card.querySelectorAll('.icon-btn')[0].addEventListener('click', () => openCondModal(i));
    card.querySelectorAll('.icon-btn')[1].addEventListener('click', async () => {
      curConds.splice(i, 1);
      await persistCurrent();
      renderConds();
    });
    body.appendChild(card);
  });
}

// ── Modal helpers ─────────────────────────────────────────────────────────────

function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

document.addEventListener('click', e => {
  if (e.target.dataset.close) { closeModal(e.target.dataset.close); return; }
  if (e.target.classList.contains('modal-overlay')) { e.target.classList.remove('open'); }
});

document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const open = document.querySelector('.modal-overlay.open');
  if (open) open.classList.remove('open');
});

// ── Event modal ───────────────────────────────────────────────────────────────

let evtParams     = [];
let editingEvtIdx = null;

function renderEvtParamRows() {
  const container = document.getElementById('eventParamRows');
  container.innerHTML = '';
  evtParams.forEach((p, i) => {
    const row = document.createElement('div');
    row.className = 'param-row';
    row.innerHTML = `
      <input type="text" placeholder="Key (e.g. Type)" value="${esc(p.key)}" data-field="key" data-i="${i}">
      <input type="text" placeholder="Value"           value="${esc(p.val)}" data-field="val" data-i="${i}">
      <button class="rm">&times;</button>
    `;
    row.querySelectorAll('input').forEach(inp =>
      inp.addEventListener('input', e => {
        evtParams[e.target.dataset.i][e.target.dataset.field] = e.target.value;
      })
    );
    row.querySelector('.rm').addEventListener('click', () => {
      evtParams.splice(i, 1);
      renderEvtParamRows();
    });
    container.appendChild(row);
  });
}

function openEventModal(editIdx) {
  editingEvtIdx = editIdx;
  if (editIdx === null) {
    document.getElementById('eventModalTitle').textContent = 'Create Event';
    document.getElementById('targetSelect').value          = 'Self';
    document.getElementById('eventPriority').value         = 0;
    evtParams = [];
  } else {
    const ev = curEvents[editIdx];
    document.getElementById('eventModalTitle').textContent = 'Edit Event';
    document.getElementById('targetSelect').value          = ev.target;
    document.getElementById('eventPriority').value         = ev.priority;
    evtParams = ev.params.map(p => ({ ...p }));
  }
  renderEvtParamRows();
  openModal('eventModal');
}

document.getElementById('addEventParamBtn').addEventListener('click', () => {
  evtParams.push({ key: '', val: '' });
  renderEvtParamRows();
});

document.getElementById('saveEventBtn').addEventListener('click', async () => {
  const record = {
    target:   document.getElementById('targetSelect').value,
    priority: document.getElementById('eventPriority').value,
    params:   evtParams.filter(p => p.key.trim() !== ''),
  };
  if (editingEvtIdx === null) curEvents.push(record);
  else                        curEvents[editingEvtIdx] = record;
  await persistCurrent();
  renderEvents();
  closeModal('eventModal');
});

// ── Condition modal ───────────────────────────────────────────────────────────

let condParams     = [];
let editingCondIdx = null;

function renderCondParamRows() {
  const container = document.getElementById('condParamRows');
  container.innerHTML = '';
  condParams.forEach((p, i) => {
    const row = document.createElement('div');
    row.className = 'param-row';
    row.innerHTML = `
      <input type="text" placeholder="Key (e.g. Weather)" value="${esc(p.key)}" data-field="key" data-i="${i}">
      <input type="text" placeholder="Value"              value="${esc(p.val)}" data-field="val" data-i="${i}">
      <button class="rm">&times;</button>
    `;
    row.querySelectorAll('input').forEach(inp =>
      inp.addEventListener('input', e => {
        condParams[e.target.dataset.i][e.target.dataset.field] = e.target.value;
      })
    );
    row.querySelector('.rm').addEventListener('click', () => {
      condParams.splice(i, 1);
      renderCondParamRows();
    });
    container.appendChild(row);
  });
}

function openCondModal(editIdx) {
  editingCondIdx = editIdx;
  if (editIdx === null) {
    document.getElementById('condModalTitle').textContent = 'Create Condition';
    condParams = [];
  } else {
    document.getElementById('condModalTitle').textContent = 'Edit Condition';
    condParams = curConds[editIdx].params.map(p => ({ ...p }));
  }
  renderCondParamRows();
  openModal('condModal');
}

document.getElementById('addCondParamBtn').addEventListener('click', () => {
  condParams.push({ key: '', val: '' });
  renderCondParamRows();
});

document.getElementById('saveCondBtn').addEventListener('click', async () => {
  const record = { params: condParams.filter(p => p.key.trim() !== '') };
  if (editingCondIdx === null) curConds.push(record);
  else                         curConds[editingCondIdx] = record;
  await persistCurrent();
  renderConds();
  closeModal('condModal');
});

// ── Presets popover ───────────────────────────────────────────────────────────

function renderPresetsList() {
  const list = document.getElementById('presetsList');
  if (!list) return;

  if (presets.length === 0) {
    list.innerHTML = '<div class="preset-empty">No presets saved yet.</div>';
    return;
  }

  list.innerHTML = '';
  presets.forEach((p, i) => {
    const chips = p.events.length
      ? p.events.map(ev => `<span class="mini-tag">${esc(ev.target)}</span>`).join('')
      : '<span class="mini-tag">no events</span>';

    const item = document.createElement('div');
    item.className = 'preset-item';
    item.innerHTML = `
      <div class="preset-content">
        <div class="pname">${esc(p.name)}</div>
        <div class="ptags">${chips}</div>
      </div>
      <button class="preset-del" title="Delete preset">&times;</button>
    `;

    item.querySelector('.preset-content').addEventListener('click', () => applyPreset(i));
    item.querySelector('.preset-del').addEventListener('click', async e => {
      e.stopPropagation();
      await apiDelete(`/api/presets/${p.id}`);
      presets.splice(i, 1);
      renderPresetsList();
    });

    list.appendChild(item);
  });
}

async function applyPreset(i) {
  const p   = presets[i];
  curEvents = deepClone(p.events);
  curConds  = deepClone(p.conditions || []);
  await persistCurrent();
  renderEvents();
  renderConds();
  const panel = document.getElementById('presetsPanel');
  if (panel) panel.classList.remove('open');
}

// ── Save-preset modal ─────────────────────────────────────────────────────────

function openPresetModal() {
  document.getElementById('presetNameInput').value = '';
  document.getElementById('presetNameInput').classList.remove('input-error');
  document.getElementById('presetNameError').style.display = 'none';

  document.getElementById('presetEventChips').innerHTML = curEvents.length
    ? curEvents.map(ev => `<span class="chip evt">${esc(ev.target)}</span>`).join('')
    : '<span class="chip">none</span>';

  document.getElementById('presetCondChips').innerHTML = curConds.length
    ? curConds.map((_, i) => `<span class="chip cond">Condition ${i + 1}</span>`).join('')
    : '<span class="chip">none</span>';

  openModal('presetModal');
  setTimeout(() => document.getElementById('presetNameInput').focus(), 50);
}

document.getElementById('presetNameInput').addEventListener('input', e => {
  if (e.target.value.trim()) {
    e.target.classList.remove('input-error');
    document.getElementById('presetNameError').style.display = 'none';
  }
});

document.getElementById('confirmPresetBtn').addEventListener('click', async () => {
  const nameInput = document.getElementById('presetNameInput');
  const name      = nameInput.value.trim();
  if (!name) {
    nameInput.classList.add('input-error');
    document.getElementById('presetNameError').style.display = 'block';
    nameInput.focus();
    return;
  }
  try {
    const result = await apiPost('/api/presets', {
      name,
      events:     deepClone(curEvents),
      conditions: deepClone(curConds),
    });
    presets.push({
      id:         result.id,
      name,
      events:     deepClone(curEvents),
      conditions: deepClone(curConds),
    });
    closeModal('presetModal');
  } catch (err) {
    console.error('Failed to save preset:', err);
  }
});

// ── Export / Import ───────────────────────────────────────────────────────────

document.getElementById('exportBtn').addEventListener('click', async () => {
  try {
    const data = await apiGet('/api/export');
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = 'move_event_data.json';
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  } catch (err) {
    console.error('Export failed:', err);
  }
});

document.getElementById('importFile').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async ev => {
    try {
      const imported = JSON.parse(ev.target.result);
      if (typeof imported !== 'object' || (!imported.moveData && !imported.presets)) {
        alert('Invalid data file — expected { moveData, presets }.'); return;
      }
      await apiPost('/api/import', imported);
      // Refresh in-memory state
      [withDataSet, presets] = await Promise.all([
        apiGet('/api/moves/with-data').then(r => new Set(r)),
        apiGet('/api/presets'),
      ]);
      if (selectedMove) await selectMove(selectedMove);
      renderMoveList();
      alert('Data imported successfully!');
    } catch (err) {
      alert('Failed to import: ' + err.message);
    }
  };
  reader.readAsText(file);
  e.target.value = '';
});

// ── Keyboard navigation ───────────────────────────────────────────────────────

document.addEventListener('keydown', async e => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
  if (document.querySelector('.modal-overlay.open')) return;
  if (!filtered.length) return;

  const idx = selectedMove ? filtered.findIndex(m => m.name === selectedMove.name) : -1;
  if ((e.key === 'ArrowDown' || e.key === 'j') && idx < filtered.length - 1) {
    e.preventDefault();
    await selectMove(filtered[idx + 1]);
  }
  if ((e.key === 'ArrowUp' || e.key === 'k') && idx > 0) {
    e.preventDefault();
    await selectMove(filtered[idx - 1]);
  }
});

// ── Filter wire-up ────────────────────────────────────────────────────────────

document.getElementById('searchInput').addEventListener('input',  applyFilters);
document.getElementById('genFilter').addEventListener('change',   applyFilters);
document.getElementById('typeFilter').addEventListener('change',  applyFilters);
document.getElementById('catFilter').addEventListener('change',   applyFilters);

// ── Boot ──────────────────────────────────────────────────────────────────────

async function boot() {
  try {
    // Fetch moves, with-data set, and presets in parallel
    const [moves, withData, presetData] = await Promise.all([
      apiGet('/api/moves'),
      apiGet('/api/moves/with-data'),
      apiGet('/api/presets'),
    ]);

    withDataSet = new Set(withData);
    presets     = presetData;

    // Populate type filter
    const types = [...new Set(moves.map(m => m.type))].sort();
    const tf    = document.getElementById('typeFilter');
    for (const t of types) {
      const o = document.createElement('option');
      o.value = t;
      o.textContent = t.charAt(0).toUpperCase() + t.slice(1);
      tf.appendChild(o);
    }

    allMoves = moves;
    applyFilters();
    if (filtered.length > 0) await selectMove(filtered[0]);
  } catch (err) {
    document.getElementById('moveList').innerHTML = `
      <div class="loading-state">
        Could not reach the server.<br>
        <div class="loading-progress">
          Run <code>python server.py</code> in the
          <code>move-editor</code> folder, then reload.
        </div>
      </div>
    `;
    console.error(err);
  }
}

boot();
