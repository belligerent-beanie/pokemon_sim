'use strict';

// ── Constants ──────────────────────────────────────────────────────────────

const STATS = ['hp', 'attack', 'defense', 'special_attack', 'special_defense', 'speed'];

const STAT_LABEL = {
  hp: 'HP', attack: 'Atk', defense: 'Def',
  special_attack: 'SpA', special_defense: 'SpD', speed: 'Spe',
};

// CSS variable names for each stat
const STAT_COLOR = {
  hp:              'var(--c-hp)',
  attack:          'var(--c-atk)',
  defense:         'var(--c-def)',
  special_attack:  'var(--c-spa)',
  special_defense: 'var(--c-spd)',
  speed:           'var(--c-spe)',
};

// Map underscore stat names → PokeAPI hyphen names for nature comparison
const STAT_TO_NATURE_KEY = {
  attack:          'attack',
  defense:         'defense',
  special_attack:  'special-attack',
  special_defense: 'special-defense',
  speed:           'speed',
};

const MAX_EV_TOTAL  = 510;
const MAX_EV_STAT   = 252;
const BAR_MAX       = 400; // stat value at which the bar is considered "full"

// ── State ──────────────────────────────────────────────────────────────────

let pokemonDb  = {};   // { name: { hp, attack, ..., types, moves } }
let natures    = {};   // { name: { increased_stat, decreased_stat } }
let allNames   = [];   // sorted list of pokemon names
let current    = null; // currently selected pokemon data object
let ivs        = {};   // { stat: 0-31 }
let evs        = {};   // { stat: 0-252 }

// ── Stat calculation ───────────────────────────────────────────────────────

function calcHP(base, iv, ev, level) {
  return Math.floor(((2 * base + iv + Math.floor(ev / 4)) * level) / 100) + level + 10;
}

function calcStat(base, iv, ev, level, statName, nature) {
  let val = Math.floor(((2 * base + iv + Math.floor(ev / 4)) * level) / 100) + 5;
  const nat = natures[nature];
  if (nat) {
    const key = STAT_TO_NATURE_KEY[statName] || statName;
    if (key === nat.increased_stat) val = Math.floor(val * 1.1);
    else if (key === nat.decreased_stat) val = Math.floor(val * 0.9);
  }
  return val;
}

function computeAllStats() {
  if (!current) return {};
  const level  = parseInt(document.getElementById('level').value) || 100;
  const nature = document.getElementById('nature').value;
  const out    = {};
  for (const s of STATS) {
    const base = current[s === 'hp' ? 'hp' : s];
    const iv   = ivs[s] ?? 31;
    const ev   = evs[s] ?? 0;
    out[s] = s === 'hp'
      ? calcHP(base, iv, ev, level)
      : calcStat(base, iv, ev, level, s, nature);
  }
  return out;
}

// ── DOM helpers ────────────────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function updateStatDisplay() {
  const computed = computeAllStats();
  for (const s of STATS) {
    const val  = computed[s];
    const pct  = Math.min(100, (val / BAR_MAX) * 100).toFixed(1);
    const totEl = document.querySelector(`.stat-total[data-stat="${s}"]`);
    const barEl = document.querySelector(`.bar-fill[data-stat="${s}"]`);
    if (totEl) totEl.textContent = val;
    if (barEl) barEl.style.width = pct + '%';
  }
  refreshEvTotal();
}

function refreshEvTotal() {
  const total   = STATS.reduce((sum, s) => sum + (evs[s] ?? 0), 0);
  const el      = $('ev-count');
  el.textContent = total;
  el.classList.toggle('over', total > MAX_EV_TOTAL);
}

// ── Nature dropdown ────────────────────────────────────────────────────────

function populateNatures() {
  const sel = $('nature');
  sel.innerHTML = '';
  for (const [name, data] of Object.entries(natures)) {
    const opt  = document.createElement('option');
    opt.value  = name;
    let label  = name.charAt(0).toUpperCase() + name.slice(1);
    if (data.increased_stat) {
      const fmt = k => k.replace('special-attack', 'SpA')
                        .replace('special-defense', 'SpD')
                        .replace('attack', 'Atk')
                        .replace('defense', 'Def')
                        .replace('speed', 'Spe');
      label += ` (+${fmt(data.increased_stat)} / −${fmt(data.decreased_stat)})`;
    }
    opt.textContent = label;
    sel.appendChild(opt);
  }
  sel.value = 'hardy';
  sel.addEventListener('change', updateStatDisplay);
}

// ── Stat rows ──────────────────────────────────────────────────────────────

function buildStatRows(data) {
  const container = $('stats-rows');
  container.innerHTML = '';

  for (const s of STATS) {
    const base  = data[s === 'hp' ? 'hp' : s];
    const iv    = ivs[s] ?? 31;
    const ev    = evs[s] ?? 0;
    const color = STAT_COLOR[s];
    const label = STAT_LABEL[s];

    const row  = document.createElement('div');
    row.className = 'stat-row';
    row.innerHTML = `
      <span class="stat-label" style="color:${color}">${label}</span>
      <span class="stat-base">${base}</span>

      <div class="iv-cell">
        <input class="iv-input" type="number" min="0" max="31" value="${iv}"
               data-stat="${s}">
      </div>

      <div class="ev-cell">
        <input class="stat-slider" type="range" min="0" max="${MAX_EV_STAT}" step="1" value="${ev}"
               data-stat="${s}" data-kind="ev" style="color:${color}">
        <span class="slider-val ev-val" data-stat="${s}">${ev}</span>
      </div>

      <span class="stat-total" data-stat="${s}">—</span>

      <div class="bar-cell">
        <div class="bar-bg">
          <div class="bar-fill" data-stat="${s}" style="background:${color}; width:0%"></div>
        </div>
      </div>
    `;
    container.appendChild(row);
  }

  // IV number inputs
  container.querySelectorAll('.iv-input').forEach(input => {
    input.addEventListener('input', () => {
      const s   = input.dataset.stat;
      let val   = parseInt(input.value);
      if (isNaN(val)) return;
      val       = Math.max(0, Math.min(31, val));
      ivs[s]    = val;
      input.value = val;
      updateStatDisplay();
    });
  });

  // EV sliders
  container.querySelectorAll('.stat-slider').forEach(slider => {
    slider.addEventListener('input', () => {
      const s          = slider.dataset.stat;
      const val        = parseInt(slider.value);
      const otherTotal = STATS.filter(x => x !== s).reduce((sum, x) => sum + (evs[x] ?? 0), 0);
      const capped     = Math.min(val, MAX_EV_TOTAL - otherTotal, MAX_EV_STAT);
      evs[s]           = capped;
      slider.value     = capped;
      document.querySelector(`.ev-val[data-stat="${s}"]`).textContent = capped;
      updateStatDisplay();
    });
  });

  updateStatDisplay();
}

// ── Sidebar list ───────────────────────────────────────────────────────────

function renderList(names) {
  const ul = $('pokemon-list');
  ul.innerHTML = '';
  for (const name of names) {
    const li       = document.createElement('li');
    li.textContent = name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    li.dataset.name = name;
    li.addEventListener('click', () => selectPokemon(name));
    ul.appendChild(li);
  }
}

// ── Abilities ──────────────────────────────────────────────────────────────

async function loadAbilities(name) {
  const sel = $('ability');
  sel.innerHTML = '<option value="">Loading…</option>';
  try {
    const abilities = await fetch(`/api/abilities/${name}`).then(r => r.json());
    sel.innerHTML = '';
    for (const ab of abilities) {
      const opt = document.createElement('option');
      opt.value = ab.name;
      let label = ab.name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      if (ab.hidden) label += ' (Hidden)';
      opt.textContent = label;
      sel.appendChild(opt);
    }
    if (!sel.options.length) sel.innerHTML = '<option value="">—</option>';
  } catch {
    sel.innerHTML = '<option value="">—</option>';
  }
}

// ── Select a pokemon ───────────────────────────────────────────────────────

function selectPokemon(name) {
  const data = pokemonDb[name];
  if (!data) return;

  current = data;
  ivs     = {};
  evs     = {};

  // Show card
  $('empty-state').classList.add('hidden');
  $('pokemon-card').classList.remove('hidden');

  // Name
  $('pokemon-name').textContent =
    name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  // Sprite from Showdown CDN
  const sprite = $('sprite');
  sprite.src   = `https://play.pokemonshowdown.com/sprites/dex/${name}.png`;
  sprite.onerror = () => { sprite.removeAttribute('src'); };

  // Type badges
  $('type-badges').innerHTML = data.types
    .map(t => `<span class="type-badge type-${t}">${t}</span>`)
    .join('');

  // Build stat sliders
  buildStatRows(data);

  // Fetch abilities (async, fire-and-forget)
  loadAbilities(name);

  // Highlight in sidebar
  document.querySelectorAll('#pokemon-list li').forEach(li => {
    li.classList.toggle('active', li.dataset.name === name);
  });

  // Scroll active item into view
  const activeEl = document.querySelector('#pokemon-list li.active');
  if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
}

// ── Search ─────────────────────────────────────────────────────────────────

$('search').addEventListener('input', e => {
  const q      = e.target.value.toLowerCase().replace(/\s+/g, '-');
  const filtered = allNames.filter(n => n.includes(q));
  renderList(filtered);
});

$('level').addEventListener('input', updateStatDisplay);

// ── Boot ───────────────────────────────────────────────────────────────────

async function init() {
  // Fetch pokemon + natures in parallel
  const [pkmnData, natData] = await Promise.all([
    fetch('/api/pokemon').then(r => r.json()),
    fetch('/api/natures').then(r => r.json()),
  ]);

  pokemonDb = pkmnData;
  natures   = natData;
  allNames  = Object.keys(pkmnData).sort();

  populateNatures();
  renderList(allNames);
}

init().catch(err => console.error('Init failed:', err));
