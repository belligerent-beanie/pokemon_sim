'use strict';

// ── Constants ────────────────────────────────────────────────────────────────

const PENCIL_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`;
const TRASH_SVG  = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>`;

const CATEGORY_COLORS = {
  major:    '#C03028',
  volatile: '#A040A0',
  side:     '#6890F0',
  field:    '#78C850',
};
const CATEGORY_LABELS = {
  major: 'Major Status', volatile: 'Volatile', side: 'Side Condition', field: 'Field Condition',
};

// Condition vocabulary: the trigger points a status can hook. Starting menu,
// not closed — "Custom…" accepts any string for a trigger not listed yet.
const CONDITION_LABELS = {
  on_apply:            'On Apply',
  on_turn_end:         'On Turn End (Tick)',
  on_turn_start:       'On Turn Start',
  on_expire:           'On Expire (Duration Out)',
  on_cure:             'On Cure/Removal',
  on_damage_taken:     'On Damage Taken (Holder)',
  on_move_block_check: 'On Move-Use Check (may block)',
  on_switch_out:       'On Switch Out',
  on_switch_in:        'On Switch In',
  on_hit_holder:       'On Holder Hit By Move',
  // Fires once, N turns after the status is applied — the counter starts
  // the moment the block's condition is created, and the block's events
  // resolve when it hits zero. One block covers what used to take two
  // (an on_apply snapshot + an on_expire payout): the turn count and the
  // payout live together. The same shape works for any move/status with a
  // delayed payoff — Future Sight and Doom Desire chief among them.
  delayed_turn:        'Delayed Turn',
  // Same countdown mechanism as Delayed Turn, but the meaning is inverted:
  // the status itself is active for the whole countdown, and the block's
  // events fire once, when it runs out, to cure/expire it — not to deliver
  // a payoff. This is the shape for anything with a flat lifespan: Sleep
  // (random 1-3), Taunt/Encore/Disable (fixed 3-4). Accepts a range
  // ("random 1-3") in the turns field, not just a fixed number.
  duration_turns:      'Lasts N Turns',
};
const getTurns = c => (c?.params || []).find(p => p.key === 'turns')?.val || '2';
const TURN_COUNT_CONDITIONS = ['delayed_turn', 'duration_turns'];
const condLabel = c => {
  const base = CONDITION_LABELS[c?.type] || c?.type || 'on_apply';
  if (c?.type === 'delayed_turn')   return `${base} (${getTurns(c)} turns)`;
  if (c?.type === 'duration_turns') return `${base}: ${getTurns(c)} turns`;
  return base;
};

function availableConditionTypes() {
  return Object.keys(CONDITION_LABELS);
}
const sameCondition = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ── App state ─────────────────────────────────────────────────────────────────

let allStatuses  = [];
let filtered     = [];
let selectedItem = null;
let curEffects   = [];
let curDesc      = '';
let curDuration  = '';
let withDataSet  = new Set();
let presets      = [];

// ── Helpers ───────────────────────────────────────────────────────────────────

const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const esc = s => String(s ?? '')
  .replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;');

function deepClone(arr) {
  return arr.map(item => ({
    ...item,
    params: (item.params || []).map(p => ({ ...p })),
  }));
}

function deepCloneEffects(effects) {
  return (effects || []).map(block => ({
    condition: { type: block.condition?.type || 'on_apply', params: (block.condition?.params || []).map(p => ({ ...p })) },
    events: deepClone(block.events || []),
  }));
}

function itemHasData(name) {
  return withDataSet.has(name);
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}
async function apiPut(path, body) {
  const res = await fetch(path, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`PUT ${path} → ${res.status}`);
  return res.json();
}
async function apiPost(path, body) {
  const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
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
  const cat = document.getElementById('catFilter').value;

  filtered = allStatuses.filter(s => {
    if (cat !== 'all' && s.category !== cat) return false;
    if (q && !s.name.includes(q) && !s.displayName.toLowerCase().includes(q)) return false;
    return true;
  });

  renderList();
}

// ── List rendering ───────────────────────────────────────────────────────────

function renderList() {
  const listEl = document.getElementById('moveList');
  document.getElementById('moveCount').textContent =
    `${filtered.length} status${filtered.length !== 1 ? 'es' : ''}`;

  if (filtered.length === 0) {
    listEl.innerHTML = '<div class="loading-state">No statuses found.</div>';
    return;
  }

  listEl.innerHTML = '';
  for (const s of filtered) {
    const color    = CATEGORY_COLORS[s.category] || '#888';
    const isActive = selectedItem && s.name === selectedItem.name;
    const hasDot   = itemHasData(s.name);

    const row = document.createElement('div');
    row.className = 'move-row' + (isActive ? ' active' : '');
    row.innerHTML = `
      <div class="type-tab" style="background:${color}"></div>
      <div class="row-info">
        <div class="name">${esc(s.displayName)}</div>
        <div class="meta">${esc((CATEGORY_LABELS[s.category] || s.category).toUpperCase())}</div>
      </div>
      ${hasDot ? '<div class="row-dot" title="Has saved effects"></div>' : ''}
    `;
    row.addEventListener('click', async () => selectItem(s));
    listEl.appendChild(row);
  }

  const activeEl = listEl.querySelector('.move-row.active');
  if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
}

// ── Selection ─────────────────────────────────────────────────────────────────

async function selectItem(item) {
  selectedItem = item;
  try {
    const data = await apiGet(`/api/events/${encodeURIComponent(item.name)}`);
    curEffects  = deepCloneEffects(data.effects || []);
    curDesc     = data.custom_desc || item.effect || '';
    curDuration = data.duration || item.default_duration || '';
  } catch (err) {
    console.error('Failed to load status data:', err);
    curEffects  = [];
    curDesc     = item.effect || '';
    curDuration = item.default_duration || '';
  }
  renderEditor();
  renderList();
}

// ── Persist ──────────────────────────────────────────────────────────────────

async function persistCurrent() {
  if (!selectedItem) return;
  try {
    const payload = curEffects.filter(b => b.events.length > 0);
    await apiPut(`/api/events/${encodeURIComponent(selectedItem.name)}`, {
      effects:     payload,
      custom_desc: curDesc,
      duration:    curDuration,
    });
    const hasData = payload.length > 0;
    if (hasData) withDataSet.add(selectedItem.name);
    else         withDataSet.delete(selectedItem.name);
    _updateRowDot();
  } catch (err) {
    console.error('Failed to save:', err);
  }
}

function _updateRowDot() {
  const listEl = document.getElementById('moveList');
  const active = listEl?.querySelector('.move-row.active');
  if (!active) return;
  const hasDot = itemHasData(selectedItem.name);
  let dot = active.querySelector('.row-dot');
  if (hasDot && !dot) {
    dot = document.createElement('div');
    dot.className = 'row-dot';
    dot.title = 'Has saved effects';
    active.appendChild(dot);
  } else if (!hasDot && dot) {
    dot.remove();
  }
}

// ── Editor rendering ──────────────────────────────────────────────────────────

function renderEditor() {
  const s     = selectedItem;
  const color = CATEGORY_COLORS[s.category] || '#888';

  document.getElementById('editorPanel').innerHTML = `
    <div class="move-header">
      <div class="move-title-block">
        <h2>${esc(s.displayName)}</h2>
        <div class="badge-row">
          <span class="type-badge" style="background:${color}">${esc(CATEGORY_LABELS[s.category] || s.category)}</span>
        </div>
      </div>
    </div>

    <div class="field-block">
      <label>Description / Notes</label>
      <textarea class="desc" id="descBox">${esc(curDesc)}</textarea>
    </div>

    <div class="field-block">
      <label>Duration</label>
      <input type="text" class="desc" id="durationBox" style="height:auto;padding:10px 12px" value="${esc(curDuration)}" placeholder="e.g. 3 turns, until switch-out, until cured">
    </div>

    <div class="section">
      <div class="section-head">
        <h3>Effects</h3>
        <span class="count" id="effectCount">0</span>
        <div class="spacer"></div>
        <button class="presets-trigger" id="presetsTrigger">Presets ▾</button>
        <div class="presets-panel" id="presetsPanel">
          <div class="ph">Available Presets</div>
          <div id="presetsList"></div>
        </div>
        <button class="btn btn-primary btn-sm" id="addBlockBtn">+ Add Condition Block</button>
      </div>
      <div class="section-body" id="effectsBody"></div>
    </div>
  `;

  bindEditorListeners();
  renderEffects();
}

function bindEditorListeners() {
  let descTimer = null;
  document.getElementById('descBox').addEventListener('input', e => {
    curDesc = e.target.value;
    clearTimeout(descTimer);
    descTimer = setTimeout(() => persistCurrent(), 600);
  });

  let durTimer = null;
  document.getElementById('durationBox').addEventListener('input', e => {
    curDuration = e.target.value;
    clearTimeout(durTimer);
    durTimer = setTimeout(() => persistCurrent(), 600);
  });

  document.getElementById('addBlockBtn').addEventListener('click', () => openCondModal());

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

// ── Effects section ────────────────────────────────────────────────────────

function renderEffects() {
  const countEl = document.getElementById('effectCount');
  const body    = document.getElementById('effectsBody');
  if (!countEl || !body) return;
  const totalEvents = curEffects.reduce((n, b) => n + b.events.length, 0);
  countEl.textContent = totalEvents;

  if (curEffects.length === 0) {
    body.innerHTML = '<div class="empty-row">No effects yet. Click "+ Add Condition Block" or apply a preset.</div>';
    return;
  }

  body.innerHTML = '';
  curEffects.forEach((block, blockIdx) => body.appendChild(renderBlock(block, blockIdx)));
}

function renderBlock(block, blockIdx) {
  const wrap = document.createElement('div');
  wrap.className = 'effect-block';

  const allowed = availableConditionTypes();
  const options = allowed.includes(block.condition.type)
    ? allowed
    : [block.condition.type, ...allowed];

  wrap.innerHTML = `
    <div class="effect-block-head">
      <select class="condition-tag" data-block="${blockIdx}">
        ${options.map(t => `<option value="${esc(t)}" ${t === block.condition.type ? 'selected' : ''}>${esc(CONDITION_LABELS[t] || t)}</option>`).join('')}
      </select>
      ${TURN_COUNT_CONDITIONS.includes(block.condition.type) ? `<input type="text" class="delay-turns-input" value="${esc(getTurns(block.condition))}" title="${block.condition.type === 'duration_turns' ? 'How many turns this lasts' : 'Turns until this fires'}" style="width:90px;margin-left:6px">` : ''}
      <span class="count">${block.events.length}</span>
      <div class="spacer"></div>
      <button class="btn btn-gold btn-sm" data-act="save-preset">Save as Preset</button>
      <button class="btn btn-primary btn-sm" data-act="add-event">+ Add Event</button>
      <button class="icon-btn danger" title="Delete block" data-act="del-block">${TRASH_SVG}</button>
    </div>
    <div class="section-body" data-role="events"></div>
  `;

  wrap.querySelector('.condition-tag').addEventListener('change', async e => {
    const newType = e.target.value;
    let params = block.condition.params || [];
    if (TURN_COUNT_CONDITIONS.includes(newType) && !params.some(p => p.key === 'turns')) {
      params = [...params, { key: 'turns', val: '2' }];
    }
    const newCondition = { type: newType, params };
    const collision = curEffects.find((b, i) => i !== blockIdx && sameCondition(b.condition, newCondition));
    if (collision) {
      collision.events.push(...block.events);
      curEffects.splice(blockIdx, 1);
    } else {
      block.condition = newCondition;
    }
    await persistCurrent();
    renderEffects();
  });

  const turnsInput = wrap.querySelector('.delay-turns-input');
  if (turnsInput) {
    turnsInput.addEventListener('change', async e => {
      const params = (block.condition.params || []).filter(p => p.key !== 'turns');
      params.push({ key: 'turns', val: e.target.value || '2' });
      block.condition = { type: block.condition.type, params };
      await persistCurrent();
      renderEffects();
    });
  }

  wrap.querySelector('[data-act="add-event"]').addEventListener('click', () => openEventModal(blockIdx, null));
  wrap.querySelector('[data-act="save-preset"]').addEventListener('click', () => openPresetModal(blockIdx));
  wrap.querySelector('[data-act="del-block"]').addEventListener('click', async () => {
    curEffects.splice(blockIdx, 1);
    await persistCurrent();
    renderEffects();
  });

  const eventsBody = wrap.querySelector('[data-role="events"]');
  if (block.events.length === 0) {
    eventsBody.innerHTML = '<div class="empty-row">No events in this block yet.</div>';
  } else {
    block.events.forEach((ev, i) => eventsBody.appendChild(renderEventCard(ev, i, blockIdx)));
  }

  return wrap;
}

function renderEventCard(ev, i, blockIdx) {
  const tags = ev.params.slice(0, 3)
    .map(p => `<span class="mini-tag">${esc(p.key)}: ${esc(p.val)}</span>`).join('');
  const chanceBadge = ev.chance ? `<span class="chance-badge">${esc(ev.chance)}% chance</span>` : '';
  const card = document.createElement('div');
  card.className = 'item-card';
  card.innerHTML = `
    <div class="idx">${String(i + 1).padStart(2, '0')}</div>
    <div class="main">
      <div class="t1">${chanceBadge}Target: ${esc(ev.target)}</div>
      <div class="t2">priority ${esc(String(ev.priority))} · ${ev.params.length} param${ev.params.length !== 1 ? 's' : ''}</div>
    </div>
    <div class="tags">${tags}</div>
    <button class="icon-btn" title="Edit">${PENCIL_SVG}</button>
    <button class="icon-btn danger" title="Delete">${TRASH_SVG}</button>
  `;
  card.querySelectorAll('.icon-btn')[0].addEventListener('click', () => openEventModal(blockIdx, i));
  card.querySelectorAll('.icon-btn')[1].addEventListener('click', async () => {
    curEffects[blockIdx].events.splice(i, 1);
    await persistCurrent();
    renderEffects();
  });
  return card;
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

let evtParams       = [];
let editingEvtIdx    = null;
let editingBlockIdx  = null;

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

function openEventModal(blockIdx, editIdx) {
  editingBlockIdx = blockIdx;
  editingEvtIdx   = editIdx;
  if (editIdx === null) {
    document.getElementById('eventModalTitle').textContent = 'Create Event';
    document.getElementById('targetSelect').value          = 'self';
    document.getElementById('eventPriority').value         = 0;
    document.getElementById('eventChance').value            = '';
    evtParams = [];
  } else {
    const ev = curEffects[blockIdx].events[editIdx];
    document.getElementById('eventModalTitle').textContent = 'Edit Event';
    document.getElementById('targetSelect').value          = ev.target;
    document.getElementById('eventPriority').value         = ev.priority;
    document.getElementById('eventChance').value            = ev.chance ?? '';
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
  const chanceRaw = document.getElementById('eventChance').value.trim();
  const record = {
    target:   document.getElementById('targetSelect').value,
    priority: document.getElementById('eventPriority').value,
    ...(chanceRaw !== '' ? { chance: chanceRaw } : {}),
    params:   evtParams.filter(p => p.key.trim() !== ''),
  };
  const events = curEffects[editingBlockIdx].events;
  if (editingEvtIdx === null) events.push(record);
  else                        events[editingEvtIdx] = record;
  await persistCurrent();
  renderEffects();
  closeModal('eventModal');
});

// ── Add Condition Block modal ─────────────────────────────────────────────────

document.getElementById('newBlockConditionType').addEventListener('change', e => {
  document.getElementById('newBlockCustomRow').style.display =
    e.target.value === '__custom__' ? 'block' : 'none';
  document.getElementById('newBlockTurnsRow').style.display =
    TURN_COUNT_CONDITIONS.includes(e.target.value) ? 'block' : 'none';
  document.getElementById('newBlockTurnsLabel').textContent =
    e.target.value === 'duration_turns' ? 'Turns this lasts' : 'Turns until it fires';
});

function openCondModal() {
  const sel = document.getElementById('newBlockConditionType');
  const allowed = availableConditionTypes();
  sel.innerHTML = allowed.map(t => `<option value="${esc(t)}">${esc(CONDITION_LABELS[t] || t)}</option>`).join('')
    + '<option value="__custom__">Custom…</option>';
  sel.value = 'on_apply';
  document.getElementById('newBlockCustomRow').style.display = 'none';
  document.getElementById('newBlockCustomType').value = '';
  document.getElementById('newBlockTurnsRow').style.display = 'none';
  document.getElementById('newBlockTurns').value = 2;
  openModal('condModal');
}

document.getElementById('saveCondBtn').addEventListener('click', async () => {
  const sel = document.getElementById('newBlockConditionType').value;
  const type = sel === '__custom__'
    ? document.getElementById('newBlockCustomType').value.trim()
    : sel;
  if (!type) return;
  const params = TURN_COUNT_CONDITIONS.includes(type)
    ? [{ key: 'turns', val: document.getElementById('newBlockTurns').value || '2' }]
    : [];
  const condition = { type, params };
  const existing = curEffects.find(b => sameCondition(b.condition, condition));
  if (!existing) {
    curEffects.push({ condition, events: [] });
    renderEffects();
  }
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
        <div class="pname">${esc(p.name)} <span class="mini-tag">${esc(condLabel(p.condition))}</span></div>
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
  const p = presets[i];
  const condition = p.condition || { type: 'on_apply', params: [] };
  let block = curEffects.find(b => sameCondition(b.condition, condition));
  if (!block) {
    block = { condition, events: [] };
    curEffects.push(block);
  }
  block.events.push(...deepClone(p.events));
  await persistCurrent();
  renderEffects();
  const panel = document.getElementById('presetsPanel');
  if (panel) panel.classList.remove('open');
}

// ── Save-preset modal ─────────────────────────────────────────────────────────

let presetSourceBlockIdx = null;

function openPresetModal(blockIdx) {
  presetSourceBlockIdx = blockIdx;
  const block = curEffects[blockIdx];

  document.getElementById('presetNameInput').value = '';
  document.getElementById('presetNameInput').classList.remove('input-error');
  document.getElementById('presetNameError').style.display = 'none';

  document.getElementById('presetConditionChip').innerHTML =
    `<span class="chip cond">${esc(condLabel(block.condition))}</span>`;

  document.getElementById('presetEventChips').innerHTML = block.events.length
    ? block.events.map(ev => `<span class="chip evt">${esc(ev.target)}</span>`).join('')
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
  const block = curEffects[presetSourceBlockIdx];
  try {
    const result = await apiPost('/api/presets', {
      name,
      condition: block.condition,
      events:    deepClone(block.events),
    });
    presets.push({
      id:        result.id,
      name,
      condition: block.condition,
      events:    deepClone(block.events),
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
    a.download = 'status_event_data.json';
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
      if (typeof imported !== 'object' || (!imported.statusData && !imported.presets)) {
        alert('Invalid data file — expected { statusData, presets }.'); return;
      }
      await apiPost('/api/import', imported);
      [withDataSet, presets] = await Promise.all([
        apiGet('/api/statuses/with-data').then(r => new Set(r)),
        apiGet('/api/presets'),
      ]);
      if (selectedItem) await selectItem(selectedItem);
      renderList();
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

  const idx = selectedItem ? filtered.findIndex(s => s.name === selectedItem.name) : -1;
  if ((e.key === 'ArrowDown' || e.key === 'j') && idx < filtered.length - 1) {
    e.preventDefault();
    await selectItem(filtered[idx + 1]);
  }
  if ((e.key === 'ArrowUp' || e.key === 'k') && idx > 0) {
    e.preventDefault();
    await selectItem(filtered[idx - 1]);
  }
});

// ── Filter wire-up ────────────────────────────────────────────────────────────

document.getElementById('searchInput').addEventListener('input', applyFilters);
document.getElementById('catFilter').addEventListener('change',  applyFilters);

// ── Boot ──────────────────────────────────────────────────────────────────────

async function boot() {
  try {
    const [statuses, withData, presetData] = await Promise.all([
      apiGet('/api/statuses'),
      apiGet('/api/statuses/with-data'),
      apiGet('/api/presets'),
    ]);

    withDataSet = new Set(withData);
    presets     = presetData;
    allStatuses = statuses;
    applyFilters();
    if (filtered.length > 0) await selectItem(filtered[0]);
  } catch (err) {
    document.getElementById('moveList').innerHTML = `
      <div class="loading-state">
        Could not reach the server.<br>
        <div class="loading-progress">
          Run <code>python server.py</code> in the
          <code>status-editor</code> folder, then reload.
        </div>
      </div>
    `;
    console.error(err);
  }
}

boot();
