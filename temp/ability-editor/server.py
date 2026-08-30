#!/usr/bin/env python3
"""
Ability Event Editor - development server.

Same file-backed event/condition/preset system as ../move-editor, applied to
abilities instead of moves. See ../move-editor/README.md for the general
shape of the data model — this file only differs in its data source
(PokeAPI /ability instead of /move) and the default condition vocabulary.

Run:
    pip install flask requests
    python server.py

Then open http://localhost:5051
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR      = Path(__file__).parent
CACHE_FILE    = BASE_DIR / 'ability_cache.json'
ABILITIES_DIR = BASE_DIR / 'abilities'
PRESETS_DIR   = BASE_DIR / 'presets'

app = Flask(__name__)

NAME_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')


def init_storage() -> None:
    ABILITIES_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str | None:
    return name if NAME_RE.match(name) else None


def _ability_path(name: str) -> Path | None:
    safe = _safe_name(name)
    return (ABILITIES_DIR / f'{safe}.json') if safe else None


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text('utf-8'))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', 'utf-8')


DEFAULT_CONDITION = {'type': 'on_switch_in', 'params': []}


def _load_ability_data(name: str) -> dict:
    path = _read_json(_ability_path(name)) or {}
    return {
        'effects':     path.get('effects', []),
        'custom_desc': path.get('custom_desc', ''),
    }


def _iter_preset_files():
    return sorted(PRESETS_DIR.glob('*.json'), key=lambda p: int(p.stem))


def _next_preset_id() -> int:
    ids = [int(p.stem) for p in PRESETS_DIR.glob('*.json') if p.stem.isdigit()]
    return (max(ids) + 1) if ids else 1


GEN_MAP = {
    'generation-i': 1, 'generation-ii': 2, 'generation-iii': 3,
    'generation-iv': 4, 'generation-v': 5, 'generation-vi': 6,
    'generation-vii': 7, 'generation-viii': 8, 'generation-ix': 9,
}


def _fmt_name(name: str) -> str:
    return ' '.join(w.capitalize() for w in name.split('-'))


def _fetch_one(url: str) -> dict | None:
    try:
        data   = requests.get(url, timeout=15).json()
        name   = data['name']
        effect = ''
        for entry in data.get('effect_entries', []):
            if entry.get('language', {}).get('name') == 'en':
                effect = entry.get('short_effect') or entry.get('effect', '')
                break
        if not effect.strip():
            flavor_entries = [e for e in data.get('flavor_text_entries', [])
                              if e.get('language', {}).get('name') == 'en']
            if flavor_entries:
                effect = flavor_entries[-1].get('flavor_text', '').replace('\n', ' ').replace('\x0c', ' ')
        return {
            'name':          name,
            'displayName':   _fmt_name(name),
            'effect':        effect,
            'generation':    GEN_MAP.get((data.get('generation') or {}).get('name', ''), 1),
            'is_main_series': data.get('is_main_series', True),
        }
    except Exception:
        return None


def _fetch_from_pokeapi() -> tuple[int, list]:
    index = requests.get('https://pokeapi.co/api/v2/ability?limit=10000', timeout=30).json()
    urls  = [e['url'] for e in index['results']]
    count = index['count']
    print(f'[cache] Fetching {len(urls)} abilities from PokeAPI…')
    abilities = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(_fetch_one, url): url for url in urls}
        done = 0
        for f in as_completed(futures):
            result = f.result()
            if result:
                abilities.append(result)
            done += 1
            if done % 100 == 0:
                print(f'  {done}/{len(urls)}')
    print(f'[cache] Done — {len(abilities)} abilities fetched.')
    abilities.sort(key=lambda a: a['name'])
    return count, abilities


def get_abilities() -> list:
    api_count = None
    try:
        api_count = requests.get(
            'https://pokeapi.co/api/v2/ability/?limit=1', timeout=8
        ).json()['count']
    except Exception as e:
        print(f'[cache] PokeAPI unreachable: {e}')

    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text('utf-8'))
        if api_count is None or cache.get('count') == api_count:
            print(f'[cache] Serving {len(cache["abilities"])} abilities from cache.')
            return cache['abilities']
        print(f'[cache] Count changed ({cache.get("count")} → {api_count}), re-fetching…')

    count, abilities = _fetch_from_pokeapi()
    CACHE_FILE.write_text(json.dumps({'count': count, 'abilities': abilities}), 'utf-8')
    print(f'[cache] Wrote ability_cache.json ({len(abilities)} abilities).')
    return abilities


# ── REST API ──────────────────────────────────────────────────────────────────

@app.route('/api/abilities')
def api_abilities():
    return jsonify(get_abilities())


@app.route('/api/abilities/with-data')
def api_with_data():
    names = []
    for path in ABILITIES_DIR.glob('*.json'):
        data = _read_json(path)
        if data and data.get('effects'):
            names.append(path.stem)
    return jsonify(names)


@app.route('/api/events/<name>', methods=['GET'])
def api_get_events(name: str):
    if _safe_name(name) is None:
        return jsonify({'error': 'invalid ability name'}), 400
    return jsonify(_load_ability_data(name))


@app.route('/api/events/<name>', methods=['PUT'])
def api_put_events(name: str):
    path = _ability_path(name)
    if path is None:
        return jsonify({'error': 'invalid ability name'}), 400
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
    ability_data = {}
    for path in ABILITIES_DIR.glob('*.json'):
        data = _read_json(path)
        if data is None:
            continue
        ability_data[path.stem] = {
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
    return jsonify({'abilityData': ability_data, 'presets': presets})


@app.route('/api/import', methods=['POST'])
def api_import():
    body         = request.get_json(force=True)
    ability_data = body.get('abilityData', {})
    presets      = body.get('presets', [])

    for path in ABILITIES_DIR.glob('*.json'):
        path.unlink()
    for path in PRESETS_DIR.glob('*.json'):
        path.unlink()

    for name, data in ability_data.items():
        path = _ability_path(name)
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


if __name__ == '__main__':
    init_storage()
    print('─' * 44)
    print('  Ability Event Editor')
    print('  http://localhost:5051')
    print('─' * 44)
    app.run(port=5051, debug=False)
