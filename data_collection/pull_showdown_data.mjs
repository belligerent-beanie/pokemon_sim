// pull_showdown_data.mjs
//
// Pulls pure STATIC data (no battle logic) from Pokemon Showdown's own repo
// (github.com/smogon/pokemon-showdown) and rebuilds this project's
// data/generated/*.json files.
//
// IMPORTANT — SCOPE: this script pulls DATA ONLY. Showdown's .ts source files
// contain both static data (stats, PP, types, ...) and battle-logic hooks
// (onModifyDamage, onHit, etc. — plain JS functions). Every value that
// survives `JSON.stringify()` after the .ts -> .cjs conversion is, by
// construction, non-function data — the conversion step is what keeps this a
// pure-data pull. Battle logic for moves/abilities/statuses is authored by
// hand elsewhere in this project (temp/move-editor, temp/ability-editor,
// temp/status-editor) and this script must never touch that.
//
// Requires: Node 18+ (global fetch), network access to
// raw.githubusercontent.com, and npm access to install esbuild into a scratch
// dir (esbuild is NOT a project dependency — it's fetched fresh into an OS
// temp directory on each run and discarded afterward).
//
// Usage:  node data_collection/pull_showdown_data.mjs
// Writes: data/generated/{pokemon,items,move_data,move_names,natures,type_chart}.json
// Also emits a JSON report object on stdout (redirect to a file if you want
// to build a report doc from it, e.g. SHOWDOWN_PULL_REPORT.md).

import { writeFileSync, readFileSync, existsSync, mkdtempSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..'); // pokemon_sim/
const GEN_DIR = path.join(REPO_ROOT, 'data', 'generated');

const SHOWDOWN_BASE = 'https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data';
// abilities.ts is fetched per spec but intentionally NOT incorporated into
// any output file below — none of the 6 target schemas have an abilities
// field, and ability battle-logic is explicitly out of scope (see header).
const FILES = ['pokedex', 'items', 'moves', 'abilities', 'natures', 'typechart', 'learnsets'];
const EXPORT_NAMES = {
  pokedex: 'Pokedex',
  items: 'Items',
  moves: 'Moves',
  abilities: 'Abilities',
  natures: 'Natures',
  typechart: 'TypeChart',
  learnsets: 'Learnsets',
};

const CODE_TO_MULTIPLIER = { 0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0 };
const NATURE_STAT_NAMES = {
  atk: 'attack',
  def: 'defense',
  spa: 'special-attack',
  spd: 'special-defense',
  spe: 'speed',
};

function log(...args) {
  console.error('[pull_showdown_data]', ...args);
}

// This project's id convention: lowercase, strip apostrophes/periods
// entirely (no hyphen inserted for them), replace remaining runs of
// non-alphanumeric characters with a single hyphen, trim leading/trailing
// hyphens. e.g. "Farfetch'd" -> "farfetchd", "Mr. Mime" -> "mr-mime".
function slugify(name) {
  let s = name.toLowerCase();
  // Strip apostrophes and periods entirely (no hyphen inserted for them).
  // Showdown's own source data is inconsistent about which apostrophe
  // character it uses — species names use the curly U+2019 ('Sirfetch’d')
  // while move names use a plain ASCII apostrophe ("King's Shield") — so both
  // (plus the left-curly variant, for safety) are stripped here.
  s = s.replace(/['’‘.]/g, '');
  s = s.replace(/[^a-z0-9]+/g, '-');
  s = s.replace(/^-+|-+$/g, '');
  return s;
}

// Fully-collapsed alphanumeric-only key, used to detect "same real-world
// species/move" across different slugging conventions (this project's ids
// vs. Showdown's own ids vs. a freshly computed slug). Conveniently, this is
// identical to Showdown's own toID() output, so it equals the dictionary key
// Showdown already uses for that entry.
function looseKey(s) {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function jsonWrite(filePath, data) {
  writeFileSync(filePath, JSON.stringify(data, null, 4) + '\n', 'utf8');
}

function sortedDict(obj) {
  const out = {};
  for (const k of Object.keys(obj).sort()) out[k] = obj[k];
  return out;
}

function run(cmd, args, opts) {
  const r = spawnSync(cmd, args, { encoding: 'utf8', shell: true, ...opts });
  if (r.status !== 0) {
    throw new Error(
      `Command failed: ${cmd} ${args.join(' ')}\nSTDOUT:\n${r.stdout}\nSTDERR:\n${r.stderr}`
    );
  }
  return r;
}

async function fetchTs(name, destDir) {
  const url = `${SHOWDOWN_BASE}/${name}.ts`;
  log('fetching', url);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: HTTP ${res.status}`);
  const text = await res.text();
  const dest = path.join(destDir, `${name}.ts`);
  writeFileSync(dest, text, 'utf8');
  return dest;
}

// --- Custom type_chart.json writer -----------------------------------------
// Matches this project's existing float style (1.0 / 0.5 / 2.0 / 0.0) which
// plain JSON.stringify would collapse to integers (1 / 2 / 0) for whole
// values. Small enough (19x19) to hand-format.
function writeTypeChart(filePath, typeChart) {
  const attackTypes = Object.keys(typeChart).sort();
  const lines = ['{'];
  attackTypes.forEach((atk, i) => {
    lines.push(`    "${atk}": {`);
    const defendTypes = Object.keys(typeChart[atk]).sort();
    defendTypes.forEach((def, j) => {
      const val = typeChart[atk][def].toFixed(1);
      const comma = j < defendTypes.length - 1 ? ',' : '';
      lines.push(`        "${def}": ${val}${comma}`);
    });
    lines.push(`    }${i < attackTypes.length - 1 ? ',' : ''}`);
  });
  lines.push('}');
  writeFileSync(filePath, lines.join('\n') + '\n', 'utf8');
}

async function main() {
  const tmp = mkdtempSync(path.join(os.tmpdir(), 'showdown-pull-'));
  log('scratch dir:', tmp);

  const report = {
    counts: {},
    reusedIds: [], // { kind, computedSlug, reusedId }
    targetShapeChanged: [], // move ids where target vocabulary changed
    droppedFromOld: { pokemon: [], moves: [] }, // in old data, not found in Showdown pull
    newInPull: { pokemon: 0, moves: 0 }, // just counts; full dex, expected to be large
    excluded: { pokemonCapOrJoke: [] }, // num<=0 Pokedex entries excluded from "Full National Dex"
    notes: [],
  };

  try {
    // 1. Fetch all 7 source files.
    for (const f of FILES) {
      await fetchTs(f, tmp);
    }

    // 2. Install esbuild fresh into the scratch dir (not a project dependency).
    log('installing esbuild into scratch dir...');
    run('npm', ['install', 'esbuild', '--no-save'], { cwd: tmp });
    const esbuildBin = path.join(
      tmp,
      'node_modules',
      '.bin',
      process.platform === 'win32' ? 'esbuild.cmd' : 'esbuild'
    );

    // 3. Convert each .ts -> .cjs and require() it.
    const modules = {};
    for (const f of FILES) {
      const tsPath = path.join(tmp, `${f}.ts`);
      const cjsPath = path.join(tmp, `${f}.cjs`);
      run(esbuildBin, [tsPath, '--format=cjs', `--outfile=${cjsPath}`], { cwd: tmp });
      const mod = await import(`file://${cjsPath.replace(/\\/g, '/')}`);
      modules[f] = mod.default ? mod.default[EXPORT_NAMES[f]] : mod[EXPORT_NAMES[f]];
      if (!modules[f]) {
        // esbuild cjs output under ESM import lands the whole module.exports
        // under `.default` in some Node/esbuild combinations; try both.
        modules[f] = (mod.default || mod)[EXPORT_NAMES[f]];
      }
      if (!modules[f]) throw new Error(`Could not find export ${EXPORT_NAMES[f]} in ${f}.cjs`);
    }

    const Pokedex = modules.pokedex;
    const Items = modules.items;
    const Moves = modules.moves;
    const Natures = modules.natures;
    const TypeChart = modules.typechart;
    const Learnsets = modules.learnsets;

    // 4. Load OLD generated files (for id-reuse + effect/stat_changes carryover).
    const oldPokemon = JSON.parse(readFileSync(path.join(GEN_DIR, 'pokemon.json'), 'utf8'));
    const oldMoveData = JSON.parse(readFileSync(path.join(GEN_DIR, 'move_data.json'), 'utf8'));

    const oldPokemonLoose = new Map(); // looseKey -> old id
    for (const id of Object.keys(oldPokemon)) oldPokemonLoose.set(looseKey(id), id);
    const oldMoveLoose = new Map();
    for (const id of Object.keys(oldMoveData)) oldMoveLoose.set(looseKey(id), id);

    function resolveId(kind, showdownId, displayName, computedSlugOverride) {
      const computedSlug = computedSlugOverride || slugify(displayName);
      const loose = looseKey(showdownId); // == looseKey(computedSlug)
      const oldMap = kind === 'pokemon' ? oldPokemonLoose : oldMoveLoose;
      const existing = oldMap.get(loose);
      if (existing) {
        if (existing !== computedSlug) {
          report.reusedIds.push({ kind, computedSlug, reusedId: existing });
        }
        return existing;
      }
      return computedSlug;
    }

    // 5. Build pokemon.json
    const pokemonOut = {};
    let excludedCapCount = 0;
    for (const [showdownId, mon] of Object.entries(Pokedex)) {
      if (mon.num <= 0) {
        // CAP-project / joke entries (MissingNo., Syclant, ...) are not part
        // of the real National Dex — excluded. See report.excluded.
        excludedCapCount++;
        report.excluded.pokemonCapOrJoke.push(mon.name);
        continue;
      }
      if (!mon.baseStats) {
        report.notes.push(`Species "${showdownId}" (${mon.name}, num=${mon.num}) has no baseStats — skipped. Raw: ${JSON.stringify(mon)}`);
        continue;
      }
      const id = resolveId('pokemon', showdownId, mon.name);

      let learnset = Learnsets[showdownId]?.learnset;
      if (!learnset && mon.baseSpecies) {
        const baseId = looseKey(mon.baseSpecies);
        learnset = Learnsets[baseId]?.learnset;
      }
      const moveIds = learnset
        ? [...new Set(Object.keys(learnset).map((mv) => resolveId('move', mv, Moves[mv]?.name || mv)))].sort()
        : [];
      if (!learnset) {
        report.notes.push(`Species "${id}" (${mon.name}) has no learnset entry (own or via baseSpecies) — moves list is empty.`);
      }

      pokemonOut[id] = {
        name: mon.name,
        hp: mon.baseStats.hp,
        attack: mon.baseStats.atk,
        defense: mon.baseStats.def,
        special_attack: mon.baseStats.spa,
        special_defense: mon.baseStats.spd,
        speed: mon.baseStats.spe,
        types: mon.types.map((t) => t.toLowerCase()),
        moves: moveIds,
      };
    }

    // 6. Build move_data.json
    const moveDataOut = {};
    for (const [showdownId, mv] of Object.entries(Moves)) {
      const id = resolveId('move', showdownId, mv.name);
      const existingOld = oldMoveData[id];

      const oldTarget = existingOld?.target;
      if (existingOld && oldTarget !== mv.target) {
        report.targetShapeChanged.push({ id, oldTarget: oldTarget ?? null, newTarget: mv.target });
      }

      const entry = {
        accuracy: mv.accuracy === true ? null : mv.accuracy,
        damage_class: (mv.category || '').toLowerCase(),
        effect: existingOld ? existingOld.effect : '',
        name: id,
        power: typeof mv.basePower === 'number' && mv.basePower > 0 ? mv.basePower : (mv.basePower === 0 ? null : (mv.basePower ?? null)),
        pp: mv.pp,
        priority: mv.priority,
        stat_changes: existingOld ? existingOld.stat_changes : [],
        target: mv.target,
        type: (mv.type || '').toLowerCase(),
      };
      if (mv.secondary) entry.secondary = mv.secondary;
      moveDataOut[id] = entry;
    }

    // 7. move_names.json
    const moveNamesOut = Object.keys(moveDataOut).sort();

    // 8. natures.json
    const naturesOut = {};
    for (const [id, nat] of Object.entries(Natures)) {
      naturesOut[id] = {
        increased_stat: nat.plus ? NATURE_STAT_NAMES[nat.plus] : null,
        decreased_stat: nat.minus ? NATURE_STAT_NAMES[nat.minus] : null,
      };
    }

    // 9. type_chart.json — TypeChart[defendingType].damageTaken[AttackingType]
    // is inverted into result[attackingType][defendingType] = multiplier.
    const validTypes = Object.keys(TypeChart).map((t) => t.toLowerCase());
    const typeChartOut = {};
    for (const atk of validTypes) typeChartOut[atk] = {};
    for (const defendType of Object.keys(TypeChart)) {
      const def = defendType.toLowerCase();
      const damageTaken = TypeChart[defendType].damageTaken || {};
      for (const [atkKeyRaw, code] of Object.entries(damageTaken)) {
        const atk = atkKeyRaw.toLowerCase();
        if (!validTypes.includes(atk)) continue; // skip status-immunity flags (par/brn/...)
        typeChartOut[atk][def] = CODE_TO_MULTIPLIER[code];
      }
    }
    // Sanity check called out explicitly in the task spec.
    if (typeChartOut.fire.grass !== 2.0 || typeChartOut.grass.fire !== 0.5) {
      throw new Error(
        `type_chart orientation check FAILED: fire->grass=${typeChartOut.fire.grass}, grass->fire=${typeChartOut.grass.fire} (expected 2.0 / 0.5)`
      );
    }

    // 10. items.json
    const itemsOut = {};
    for (const [showdownId, item] of Object.entries(Items)) {
      const id = slugify(item.name); // no existing items.json to reuse ids from
      const { name, num, gen, fling, isChoice, isBerry, boosts, naturalGift, ignoreKlutz, ...rest } = item;
      const out = { name, num, gen };
      if (fling !== undefined) out.fling = fling;
      if (isChoice !== undefined) out.isChoice = isChoice;
      if (isBerry !== undefined) out.isBerry = isBerry;
      if (boosts !== undefined) out.boosts = boosts;
      if (naturalGift !== undefined) out.naturalGift = naturalGift;
      if (ignoreKlutz !== undefined) out.ignoreKlutz = ignoreKlutz;
      // Pass through any other surviving static fields verbatim too.
      for (const [k, v] of Object.entries(rest)) {
        if (v !== undefined) out[k] = v;
      }
      itemsOut[id] = out;
    }

    // 11. Diff old vs new (dropped-from-old check, required by spec).
    const newPokemonLoose = new Set(Object.keys(pokemonOut).map(looseKey));
    for (const oldId of Object.keys(oldPokemon)) {
      if (!newPokemonLoose.has(looseKey(oldId))) report.droppedFromOld.pokemon.push(oldId);
    }
    const newMoveLoose = new Set(Object.keys(moveDataOut).map(looseKey));
    for (const oldId of Object.keys(oldMoveData)) {
      if (!newMoveLoose.has(looseKey(oldId))) report.droppedFromOld.moves.push(oldId);
    }
    report.newInPull.pokemon = Object.keys(pokemonOut).length - Object.keys(oldPokemon).length;
    report.newInPull.moves = Object.keys(moveDataOut).length - Object.keys(oldMoveData).length;

    report.counts = {
      pokemon: { old: Object.keys(oldPokemon).length, new: Object.keys(pokemonOut).length },
      move_data: { old: Object.keys(oldMoveData).length, new: Object.keys(moveDataOut).length },
      move_names: { old: Object.keys(oldMoveData).length, new: moveNamesOut.length },
      natures: { old: 25, new: Object.keys(naturesOut).length },
      type_chart: { old: 18, new: Object.keys(typeChartOut).length },
      items: { old: 0, new: Object.keys(itemsOut).length },
      excludedCapOrJoke: excludedCapCount,
    };

    // 12. Write output files.
    jsonWrite(path.join(GEN_DIR, 'pokemon.json'), sortedDict(pokemonOut));
    jsonWrite(path.join(GEN_DIR, 'move_data.json'), sortedDict(moveDataOut));
    jsonWrite(path.join(GEN_DIR, 'move_names.json'), moveNamesOut);
    jsonWrite(path.join(GEN_DIR, 'natures.json'), sortedDict(naturesOut));
    writeTypeChart(path.join(GEN_DIR, 'type_chart.json'), typeChartOut);
    jsonWrite(path.join(GEN_DIR, 'items.json'), sortedDict(itemsOut));

    log('done. Files written to', GEN_DIR);
    console.log(JSON.stringify(report, null, 2));
  } finally {
    try {
      rmSync(tmp, { recursive: true, force: true });
    } catch (e) {
      log('warning: failed to clean up scratch dir', tmp, e.message);
    }
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
