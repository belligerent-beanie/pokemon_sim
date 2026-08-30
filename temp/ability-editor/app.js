'use strict';

// ── Constants ────────────────────────────────────────────────────────────────

const PENCIL_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`;
const TRASH_SVG  = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>`;

// Condition vocabulary: the trigger points an ability can hook. This is a
// starting menu, not a closed set — "Custom…" in the Add Condition Block
// modal accepts any string, so an ability can gate on a trigger point not
// listed here yet.
const CONDITION_LABELS = {
  on_switch_in:       'On Switch In',
  on_switch_out:      'On Switch Out',
  on_hit:             'On Being Hit',
  on_contact:         'On Being Hit (Contact)',
  on_deal_damage:     'On Dealing Damage',
  on_faint:           'On Faint (Self)',
  on_ally_faint:      'On Ally Faint',
  on_turn_end:        'On Turn End',
  on_status_inflict:  'On Status Inflicted (Self)',
  on_stat_change:     'On Stat Change (Self)',
  on_weather_change:  'On Weather Change',
  on_terrain_change:  'On Terrain Change',
  on_crit:            'On Critical Hit Taken',
  on_move_used:       'On Move Used (Self)',
  // Damage-multiplier abilities (Multiscale, Filter/Solid Rock, Technician,
  // Sniper, Thick Fat, Punk Rock, ...) hook here rather than on_hit/
  // on_deal_damage — this fires specifically during damage calculation, so
  // its events describe a multiplier via `tag`, not an actual damage/heal
  // event of their own.
  on_calc_damage:     'On Damage Calculation',
  // Type-immunity and redirect abilities (Levitate, Flash Fire, Volt
  // Absorb, Lightning Rod, Storm Drain, Wonder Guard) — fires when an
  // incoming move's type is checked against the holder, before normal
  // damage calc even happens. Distinct from on_calc_damage: this can
  // cancel the hit outright (or redirect its target), not just scale it.
  on_type_effectiveness: 'On Type Effectiveness Check',
  // Priority-granting abilities (Prankster, Gale Wings, Triage, Quick
  // Draw) — fires when the game determines what priority bracket a move
  // falls into, before turn order is decided.
  on_priority_check:  'On Priority Check',
  // Ability copy/swap/suppress abilities (Trace, Mummy, Wandering Spirit,
  // Neutralizing Gas) — fires when the holder's or another Pokémon's
  // ability itself is about to change.
  on_ability_change:  'On Ability Change',
  // The holder's own held item gets used up — a Berry eaten, a Gem
  // consumed, etc. Distinct from on_item_removed: this is self-triggered
  // consumption, not something another Pokémon did to the holder. The
  // distinction matters for Harvest, which only restores a Berry it
  // consumed itself — not one Knock Off took.
  on_item_consumed:   'On Item Consumed (Self)',
  // The holder's held item is taken away by someone/something else —
  // Knock Off, Thief, Covet, Trick, Corrosive Gas, etc. Distinct from
  // on_item_consumed: this is external removal, not the holder using its
  // own item up.
  on_item_removed:    'On Item Removed (By Other)',
  passive:            'Passive (Always Active)',
  // Fires once, N turns after the block's condition is created — same shape
  // as the status-editor's Delayed Turn (used there for Wish) and the
  // move-editor's (for Future Sight / Doom Desire). Less common for
  // abilities, but e.g. a hypothetical "banks up over N turns" ability
  // could use it.
  delayed_turn:       'Delayed Turn',
  // Same countdown as Delayed Turn, inverted meaning: the effect is active
  // for the whole countdown and expires when it runs out (see
  // ../status-editor/app.js for where this is used most — Sleep, Taunt,
  // Encore). Rare for abilities, but a hypothetical timed ability
  // (post-Mega/terastallize windows, etc.) could use it.
  duration_turns:     'Lasts N Turns',
};
const getTurns = c => (c?.params || []).find(p => p.key === 'turns')?.val || '2';
const TURN_COUNT_CONDITIONS = ['delayed_turn', 'duration_turns'];
const condLabel = c => {
  const base = CONDITION_LABELS[c?.type] || c?.type || 'passive';
  if (c?.type === 'delayed_turn')   return `${base} (${getTurns(c)} turns)`;
  if (c?.type === 'duration_turns') return `${base}: ${getTurns(c)} turns`;
  return base;
};

// Every trigger point is always offered — unlike moves, an ability isn't
// gated by a descriptive move flag, so there's no "only show On Contact if
// this move already has X" restriction to apply here.
function availableConditionTypes() {
  return Object.keys(CONDITION_LABELS);
}
const sameCondition = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ── App state ─────────────────────────────────────────────────────────────────

let allAbilities = [];
let filtered     = [];
let selectedItem = null;
let curEffects   = [];
let curDesc      = '';
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
    condition: { type: block.condition?.type || 'passive', params: (block.condition?.params || []).map(p => ({ ...p })) },
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
  const gen = document.getElementById('genFilter').value;

  filtered = allAbilities.filter(a => {
    if (gen !== 'all' && a.generation !== parseInt(gen)) return false;
    if (q && !a.name.includes(q) && !a.displayName.toLowerCase().includes(q)) return false;
    return true;
  });

  renderList();
}

// ── List rendering ───────────────────────────────────────────────────────────

function renderList() {
  const listEl = document.getElementById('moveList');
  document.getElementById('moveCount').textContent =
    `${filtered.length} abilit${filtered.length !== 1 ? 'ies' : 'y'}`;

  if (filtered.length === 0) {
    listEl.innerHTML = '<div class="loading-state">No abilities found.</div>';
    return;
  }

  listEl.innerHTML = '';
  for (const a of filtered) {
    const isActive = selectedItem && a.name === selectedItem.name;
    const hasDot   = itemHasData(a.name);

    const row = document.createElement('div');
    row.className = 'move-row' + (isActive ? ' active' : '');
    row.innerHTML = `
      <div class="type-tab" style="background:#4a3d1c"></div>
      <div class="row-info">
        <div class="name">${esc(a.displayName)}</div>
        <div class="meta">GEN ${a.generation}</div>
      </div>
      ${hasDot ? '<div class="row-dot" title="Has saved effects"></div>' : ''}
    `;
    row.addEventListener('click', async () => selectItem(a));
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
    curEffects = deepCloneEffects(data.effects || []);
    curDesc    = data.custom_desc || item.effect || '';
  } catch (err) {
    console.error('Failed to load ability data:', err);
    curEffects = [];
    curDesc    = item.effect || '';
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
  const a = selectedItem;

  document.getElementById('editorPanel').innerHTML = `
    <div class="move-header">
      <div class="move-title-block">
        <h2>${esc(a.displayName)}</h2>
        <div class="badge-row">
          <span class="type-badge" style="background:#4a3d1c">Gen ${a.generation}</span>
        </div>
      </div>
    </div>

    <div class="field-block">
      <label>Description / Notes</label>
      <textarea class="desc" id="descBox">${esc(curDesc)}</textarea>
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
  sel.value = 'passive';
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
  const condition = p.condition || { type: 'passive', params: [] };
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
    a.download = 'ability_event_data.json';
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
      if (typeof imported !== 'object' || (!imported.abilityData && !imported.presets)) {
        alert('Invalid data file — expected { abilityData, presets }.'); return;
      }
      await apiPost('/api/import', imported);
      [withDataSet, presets] = await Promise.all([
        apiGet('/api/abilities/with-data').then(r => new Set(r)),
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

  const idx = selectedItem ? filtered.findIndex(a => a.name === selectedItem.name) : -1;
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

document.getElementById('searchInput').addEventListener('input',  applyFilters);
document.getElementById('genFilter').addEventListener('change',   applyFilters);

// ── Boot ──────────────────────────────────────────────────────────────────────

async function boot() {
  try {
    const [abilities, withData, presetData] = await Promise.all([
      apiGet('/api/abilities'),
      apiGet('/api/abilities/with-data'),
      apiGet('/api/presets'),
    ]);

    withDataSet  = new Set(withData);
    presets      = presetData;
    allAbilities = abilities;
    applyFilters();
    if (filtered.length > 0) await selectItem(filtered[0]);
  } catch (err) {
    document.getElementById('moveList').innerHTML = `
      <div class="loading-state">
        Could not reach the server.<br>
        <div class="loading-progress">
          Run <code>python server.py</code> in the
          <code>ability-editor</code> folder, then reload.
        </div>
      </div>
    `;
    console.error(err);
  }
}

boot();
