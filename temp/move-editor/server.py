#!/usr/bin/env python3
"""
Move Event Editor - development server.

Run:
    pip install flask requests
    python server.py

Then open http://localhost:5050
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR    = Path(__file__).parent
CACHE_FILE  = BASE_DIR / 'move_cache.json'
MOVES_DIR   = BASE_DIR / 'moves'
PRESETS_DIR = BASE_DIR / 'presets'

app = Flask(__name__)


# ── File-backed storage ──────────────────────────────────────────────────────
#
# Each move's saved events/conditions/custom_desc live in their own JSON file
# under moves/, and each preset lives in its own JSON file under presets/.
# One file per record keeps git diffs small and lets edits made on different
# machines merge (and sync) cleanly instead of colliding inside a single
# binary SQLite file.

NAME_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')


def init_storage() -> None:
    MOVES_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_move_name(move_name: str) -> str | None:
    """Validate a move name is a plain slug before it's used to build a path."""
    return move_name if NAME_RE.match(move_name) else None


def _move_path(move_name: str) -> Path | None:
    safe = _safe_move_name(move_name)
    return (MOVES_DIR / f'{safe}.json') if safe else None


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text('utf-8'))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', 'utf-8')


DEFAULT_CONDITION = {'type': 'on_hit', 'params': []}


def _load_move_data(move_name: str) -> dict:
    """A move's saved data is a list of effect blocks: {condition, events}[],
    one block per gating condition (on_hit, on_contact, ...)."""
    path = _move_path(move_name)
    data = _read_json(path) or {}
    if 'effects' not in data and data.get('events'):
        # Legacy flat shape from before effect blocks existed.
        data = {'effects': [{'condition': dict(DEFAULT_CONDITION), 'events': data['events']}],
                'custom_desc': data.get('custom_desc', '')}
    return {
        'effects':     data.get('effects', []),
        'custom_desc': data.get('custom_desc', ''),
    }


def _iter_preset_files():
    return sorted(PRESETS_DIR.glob('*.json'), key=lambda p: int(p.stem))


def _next_preset_id() -> int:
    ids = [int(p.stem) for p in PRESETS_DIR.glob('*.json') if p.stem.isdigit()]
    return (max(ids) + 1) if ids else 1


# ── Move category constants ───────────────────────────────────────────────────

GEN_MAP = {
    'generation-i': 1, 'generation-ii': 2, 'generation-iii': 3,
    'generation-iv': 4, 'generation-v': 5, 'generation-vi': 6,
    'generation-vii': 7, 'generation-viii': 8, 'generation-ix': 9,
}

Z_MOVES = {
    'breakneck-blitz', 'all-out-pummeling', 'supersonic-skystrike', 'acid-downpour',
    'tectonic-rage', 'continental-crush', 'savage-spin-out', 'never-ending-nightmare',
    'corkscrew-crash', 'inferno-overdrive', 'hydro-vortex', 'bloom-doom',
    'gigavolt-havoc', 'shattered-psyche', 'subzero-slammer', 'devastating-drake',
    'black-hole-eclipse', 'twinkle-tackle', 'catastropika', '10-000-000-volt-thunderbolt',
    'stoked-sparksurfer', 'extreme-evoboost', 'pulverizing-pancake', 'genesis-supernova',
    'sinister-arrow-raid', 'malicious-moonsault', 'oceanic-operetta', 'guardian-of-alola',
    'soul-stealing-7-star-strike', 'searing-sunraze-smash', 'menacing-moonraze-maelstrom',
    'lets-snuggle-forever', 'splintered-stormshards', 'clangorous-soulblaze',
    'light-that-burns-the-sky',
}

MAX_MOVES = {
    'max-airstream', 'max-darkness', 'max-flare', 'max-flutterby', 'max-geyser', 'max-guard',
    'max-hailstorm', 'max-knuckle', 'max-lightning', 'max-mindstorm', 'max-ooze',
    'max-overgrowth', 'max-phantasm', 'max-quake', 'max-rockfall', 'max-starfall',
    'max-steelspike', 'max-strike', 'max-wyrmwind',
    'g-max-befuddle', 'g-max-cannonade', 'g-max-centiferno', 'g-max-chi-strike',
    'g-max-cuddle', 'g-max-depletion', 'g-max-drum-solo', 'g-max-finale', 'g-max-fireball',
    'g-max-foam-burst', 'g-max-gold-rush', 'g-max-gravitas', 'g-max-hydrosnipe',
    'g-max-malodor', 'g-max-meltdown', 'g-max-one-blow', 'g-max-rapid-flow',
    'g-max-replenish', 'g-max-resonance', 'g-max-sandblast', 'g-max-smite', 'g-max-snooze',
    'g-max-steelsurge', 'g-max-stonesurge', 'g-max-stun-shock', 'g-max-sweetness',
    'g-max-tartness', 'g-max-terror', 'g-max-vine-lash', 'g-max-volcalith',
    'g-max-volt-crash', 'g-max-wildfire', 'g-max-wind-rage',
}

PARTNER_MOVES = {
    'zippy-zap', 'splishy-splash', 'floaty-fall', 'pika-papow',
    'bouncy-bubble', 'buzzy-buzz', 'sizzly-slide', 'glitzy-glow',
    'baddy-bad', 'sappy-seed', 'freezy-frost', 'sparkly-swirl', 'veevee-volley',
}

VARIANT_RE = re.compile(r'-{1,2}(physical|special)$')


# ── PokeAPI helpers ───────────────────────────────────────────────────────────

def _fmt_name(name: str) -> str:
    return ' '.join(w.capitalize() for w in name.split('-'))


def _get_move_category(name: str) -> str:
    if name in Z_MOVES:        return 'z'
    if name in MAX_MOVES:      return 'max'
    if name in PARTNER_MOVES:  return 'partner'
    base = VARIANT_RE.sub('', name)
    if base != name and base in Z_MOVES:
        return 'z'
    return 'standard'


def _fetch_one(url: str) -> dict | None:
    try:
        data   = requests.get(url, timeout=15).json()
        name   = data['name']
        type_  = (data.get('type') or {}).get('name', 'normal')
        effect = ''
        for entry in data.get('effect_entries', []):
            if entry.get('language', {}).get('name') == 'en':
                effect = entry.get('short_effect') or entry.get('effect', '')
                break
        if not effect.strip():
            # Some newer (Gen 9 DLC-era) moves have no effect_entries at all yet.
            # Fall back to the most recent English flavor text (Pokedex-style
            # description) rather than leaving the move undescribed.
            flavor_entries = [e for e in data.get('flavor_text_entries', [])
                              if e.get('language', {}).get('name') == 'en']
            if flavor_entries:
                effect = flavor_entries[-1].get('flavor_text', '').replace('\n', ' ').replace('\x0c', ' ')
        return {
            'name':         name,
            'displayName':  _fmt_name(name),
            'type':         type_,
            'power':        data.get('power'),
            'pp':           data.get('pp'),
            'priority':     data.get('priority', 0),
            'damage_class': (data.get('damage_class') or {}).get('name', 'status'),
            'effect':       effect,
            'generation':   GEN_MAP.get((data.get('generation') or {}).get('name', ''), 1),
            'moveCat':      _get_move_category(name),
        }
    except Exception:
        return None


def _merge_z_variants(moves: list) -> list:
    groups: dict = {}
    result: list = []
    for m in moves:
        if m['moveCat'] != 'z':
            result.append(m)
            continue
        if not VARIANT_RE.search(m['name']):
            result.append(m)   # unique z-move (e.g. catastropika), no pair
            continue
        base = VARIANT_RE.sub('', m['name'])
        groups.setdefault(base, []).append(m)
    for base, variants in groups.items():
        ref = variants[0]
        result.append({
            'name':         base,
            'displayName':  _fmt_name(base),
            'type':         ref['type'],
            'power':        ref['power'],
            'pp':           ref['pp'],
            'priority':     ref['priority'],
            'damage_class': 'both',
            'effect':       ref['effect'],
            'generation':   ref['generation'],
            'moveCat':      'z',
        })
    return sorted(result, key=lambda m: m['name'])


def _fetch_from_pokeapi() -> tuple[int, list]:
    index = requests.get('https://pokeapi.co/api/v2/move?limit=10000', timeout=30).json()
    urls  = [e['url'] for e in index['results']]
    count = index['count']
    print(f'[cache] Fetching {len(urls)} moves from PokeAPI…')
    moves = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(_fetch_one, url): url for url in urls}
        done = 0
        for f in as_completed(futures):
            result = f.result()
            if result:
                moves.append(result)
            done += 1
            if done % 100 == 0:
                print(f'  {done}/{len(urls)}')
    print(f'[cache] Done — {len(moves)} moves fetched.')
    return count, _merge_z_variants(moves)


def get_moves() -> list:
    """Return processed moves from disk cache, re-fetching only if PokeAPI count changed."""
    api_count = None
    try:
        api_count = requests.get(
            'https://pokeapi.co/api/v2/move/?limit=1', timeout=8
        ).json()['count']
    except Exception as e:
        print(f'[cache] PokeAPI unreachable: {e}')

    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text('utf-8'))
        if api_count is None or cache.get('count') == api_count:
            print(f'[cache] Serving {len(cache["moves"])} moves from cache.')
            return cache['moves']
        print(f'[cache] Count changed ({cache.get("count")} → {api_count}), re-fetching…')

    count, moves = _fetch_from_pokeapi()
    CACHE_FILE.write_text(json.dumps({'count': count, 'moves': moves}), 'utf-8')
    print(f'[cache] Wrote move_cache.json ({len(moves)} moves).')
    return moves


# ── REST API ──────────────────────────────────────────────────────────────────

@app.route('/api/moves')
def api_moves():
    return jsonify(get_moves())


@app.route('/api/moves/with-data')
def api_with_data():
    """Move names that have at least one effect block saved."""
    names = []
    for path in MOVES_DIR.glob('*.json'):
        data = _read_json(path)
        if data and (data.get('effects') or data.get('events')):
            names.append(path.stem)
    return jsonify(names)


@app.route('/api/events/<move_name>', methods=['GET'])
def api_get_events(move_name: str):
    if _safe_move_name(move_name) is None:
        return jsonify({'error': 'invalid move name'}), 400
    return jsonify(_load_move_data(move_name))


@app.route('/api/events/<move_name>', methods=['PUT'])
def api_put_events(move_name: str):
    path = _move_path(move_name)
    if path is None:
        return jsonify({'error': 'invalid move name'}), 400
    body = request.get_json(force=True)
    _write_json(path, {
        'effects':     body.get('effects', []),
        'custom_desc': body.get('custom_desc', ''),
    })
    return jsonify({'ok': True})


@app.route('/api/presets', methods=['GET'])
def api_get_presets():
    presets = []
    for path in _iter_preset_files():
        data = _read_json(path)
        if data is None:
            continue
        presets.append({
            'id':        int(path.stem),
            'name':      data.get('name', ''),
            'condition': data.get('condition') or dict(DEFAULT_CONDITION),
            'events':    data.get('events', []),
        })
    return jsonify(presets)


@app.route('/api/presets', methods=['POST'])
def api_create_preset():
    body = request.get_json(force=True)
    name = (body.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400
    preset_id = _next_preset_id()
    _write_json(PRESETS_DIR / f'{preset_id}.json', {
        'name':      name,
        'condition': body.get('condition') or dict(DEFAULT_CONDITION),
        'events':    body.get('events', []),
    })
    return jsonify({'id': preset_id, 'ok': True})


@app.route('/api/presets/<int:preset_id>', methods=['DELETE'])
def api_delete_preset(preset_id: int):
    (PRESETS_DIR / f'{preset_id}.json').unlink(missing_ok=True)
    return jsonify({'ok': True})


@app.route('/api/export')
def api_export():
    move_data = {}
    for path in MOVES_DIR.glob('*.json'):
        data = _read_json(path)
        if data is None:
            continue
        move_data[path.stem] = {
            'effects':    data.get('effects', []),
            'customDesc': data.get('custom_desc', ''),
        }
    presets = []
    for path in _iter_preset_files():
        data = _read_json(path)
        if data is None:
            continue
        presets.append({
            'id':        int(path.stem),
            'name':      data.get('name', ''),
            'condition': data.get('condition') or dict(DEFAULT_CONDITION),
            'events':    data.get('events', []),
        })
    return jsonify({'moveData': move_data, 'presets': presets})


@app.route('/api/import', methods=['POST'])
def api_import():
    body      = request.get_json(force=True)
    move_data = body.get('moveData', {})
    presets   = body.get('presets', [])

    for path in MOVES_DIR.glob('*.json'):
        path.unlink()
    for path in PRESETS_DIR.glob('*.json'):
        path.unlink()

    for move_name, data in move_data.items():
        path = _move_path(move_name)
        if path is None:
            continue
        _write_json(path, {
            'effects':     data.get('effects', []),
            'custom_desc': data.get('customDesc', ''),
        })

    for i, p in enumerate(presets, start=1):
        preset_id = p.get('id') or i
        _write_json(PRESETS_DIR / f'{preset_id}.json', {
            'name':      p.get('name', ''),
            'condition': p.get('condition') or dict(DEFAULT_CONDITION),
            'events':    p.get('events', []),
        })

    return jsonify({'ok': True})


# ── Static files ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(str(BASE_DIR), 'index.html')


@app.route('/<path:filename>')
def static_files(filename: str):
    return send_from_directory(str(BASE_DIR), filename)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_storage()
    print('─' * 44)
    print('  Move Event Editor')
    print('  http://localhost:5050')
    print('─' * 44)
    app.run(port=5050, debug=False)
