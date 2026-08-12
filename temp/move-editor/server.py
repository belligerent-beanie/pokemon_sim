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
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR   = Path(__file__).parent
CACHE_FILE = BASE_DIR / 'move_cache.json'
DB_FILE    = BASE_DIR / 'move_events.db'

app = Flask(__name__)


# ── Database ──────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS move_data (
                move_name   TEXT PRIMARY KEY,
                events      TEXT NOT NULL DEFAULT '[]',
                conditions  TEXT NOT NULL DEFAULT '[]',
                custom_desc TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS presets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                events      TEXT NOT NULL DEFAULT '[]',
                conditions  TEXT NOT NULL DEFAULT '[]'
            );
        """)


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
    """Move names that have at least one event or condition saved."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT move_name FROM move_data WHERE events != '[]' OR conditions != '[]'"
        ).fetchall()
    return jsonify([r['move_name'] for r in rows])


@app.route('/api/events/<move_name>', methods=['GET'])
def api_get_events(move_name: str):
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM move_data WHERE move_name = ?', (move_name,)
        ).fetchone()
    if row is None:
        return jsonify({'events': [], 'conditions': [], 'custom_desc': ''})
    return jsonify({
        'events':      json.loads(row['events']),
        'conditions':  json.loads(row['conditions']),
        'custom_desc': row['custom_desc'],
    })


@app.route('/api/events/<move_name>', methods=['PUT'])
def api_put_events(move_name: str):
    body = request.get_json(force=True)
    with get_db() as conn:
        conn.execute("""
            INSERT INTO move_data (move_name, events, conditions, custom_desc)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(move_name) DO UPDATE SET
                events      = excluded.events,
                conditions  = excluded.conditions,
                custom_desc = excluded.custom_desc
        """, (
            move_name,
            json.dumps(body.get('events', [])),
            json.dumps(body.get('conditions', [])),
            body.get('custom_desc', ''),
        ))
    return jsonify({'ok': True})


@app.route('/api/presets', methods=['GET'])
def api_get_presets():
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, name, events, conditions FROM presets ORDER BY id'
        ).fetchall()
    return jsonify([{
        'id':         r['id'],
        'name':       r['name'],
        'events':     json.loads(r['events']),
        'conditions': json.loads(r['conditions']),
    } for r in rows])


@app.route('/api/presets', methods=['POST'])
def api_create_preset():
    body = request.get_json(force=True)
    name = (body.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO presets (name, events, conditions) VALUES (?, ?, ?)',
            (name, json.dumps(body.get('events', [])), json.dumps(body.get('conditions', [])))
        )
    return jsonify({'id': cur.lastrowid, 'ok': True})


@app.route('/api/presets/<int:preset_id>', methods=['DELETE'])
def api_delete_preset(preset_id: int):
    with get_db() as conn:
        conn.execute('DELETE FROM presets WHERE id = ?', (preset_id,))
    return jsonify({'ok': True})


@app.route('/api/export')
def api_export():
    with get_db() as conn:
        move_rows   = conn.execute('SELECT * FROM move_data').fetchall()
        preset_rows = conn.execute(
            'SELECT id, name, events, conditions FROM presets ORDER BY id'
        ).fetchall()
    move_data = {
        r['move_name']: {
            'events':      json.loads(r['events']),
            'conds':       json.loads(r['conditions']),
            'customDesc':  r['custom_desc'],
        }
        for r in move_rows
    }
    presets = [{
        'id':    r['id'],
        'name':  r['name'],
        'events': json.loads(r['events']),
        'conds':  json.loads(r['conditions']),
    } for r in preset_rows]
    return jsonify({'moveData': move_data, 'presets': presets})


@app.route('/api/import', methods=['POST'])
def api_import():
    body      = request.get_json(force=True)
    move_data = body.get('moveData', {})
    presets   = body.get('presets', [])
    with get_db() as conn:
        conn.execute('DELETE FROM move_data')
        conn.execute('DELETE FROM presets')
        for move_name, data in move_data.items():
            conn.execute(
                'INSERT INTO move_data (move_name, events, conditions, custom_desc) VALUES (?, ?, ?, ?)',
                (
                    move_name,
                    json.dumps(data.get('events', [])),
                    json.dumps(data.get('conds', [])),
                    data.get('customDesc', ''),
                )
            )
        for p in presets:
            conn.execute(
                'INSERT INTO presets (name, events, conditions) VALUES (?, ?, ?)',
                (p['name'], json.dumps(p.get('events', [])), json.dumps(p.get('conds', [])))
            )
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
    init_db()
    print('─' * 44)
    print('  Move Event Editor')
    print('  http://localhost:5050')
    print('─' * 44)
    app.run(port=5050, debug=False)
