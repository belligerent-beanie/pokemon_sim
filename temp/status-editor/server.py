#!/usr/bin/env python3
"""
Status Event Editor - development server.

Same file-backed event/condition/preset system as ../move-editor and
../ability-editor, applied to named statuses (major status conditions,
volatile statuses, and field/side conditions). There's no PokeAPI endpoint
for statuses, so the catalog is a curated list baked into this file — edit
STATUSES below to add/remove one.

Run:
    pip install flask
    python server.py

Then open http://localhost:5052
"""

import json
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR    = Path(__file__).parent
STATUS_DIR  = BASE_DIR / 'statuses'
PRESETS_DIR = BASE_DIR / 'presets'

app = Flask(__name__)

NAME_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')


def init_storage() -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str | None:
    return name if NAME_RE.match(name) else None


def _status_path(name: str) -> Path | None:
    safe = _safe_name(name)
    return (STATUS_DIR / f'{safe}.json') if safe else None


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text('utf-8'))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', 'utf-8')


DEFAULT_CONDITION = {'type': 'on_apply', 'params': []}


def _load_status_data(name: str) -> dict:
    data = _read_json(_status_path(name)) or {}
    return {
        'effects':     data.get('effects', []),
        'custom_desc': data.get('custom_desc', ''),
        'duration':    data.get('duration', ''),
    }


def _iter_preset_files():
    return sorted(PRESETS_DIR.glob('*.json'), key=lambda p: int(p.stem))


def _next_preset_id() -> int:
    ids = [int(p.stem) for p in PRESETS_DIR.glob('*.json') if p.stem.isdigit()]
    return (max(ids) + 1) if ids else 1


# ── Status catalog ─────────────────────────────────────────────────────────────
# category: 'major' (one at a time, cured by e.g. Full Heal), 'volatile'
# (cleared on switch-out, stack freely alongside a major status), or
# 'field'/'side' (battlefield or team-side conditions like Spikes/Reflect).

STATUSES = [
    # Major status conditions
    {'name': 'burn',            'displayName': 'Burn',              'category': 'major',
     'effect': 'Deals damage each turn and halves physical Attack.', 'default_duration': 'Until cured'},
    {'name': 'paralysis',       'displayName': 'Paralysis',         'category': 'major',
     'effect': 'Cuts Speed and has a chance to prevent the Pokémon from moving.', 'default_duration': 'Until cured'},
    {'name': 'poison',          'displayName': 'Poison',            'category': 'major',
     'effect': 'Deals damage each turn.', 'default_duration': 'Until cured'},
    {'name': 'toxic',           'displayName': 'Badly Poisoned',    'category': 'major',
     'effect': 'Deals increasing damage each turn.', 'default_duration': 'Until cured'},
    {'name': 'sleep',           'displayName': 'Sleep',             'category': 'major',
     'effect': "Prevents the Pokémon from acting.", 'default_duration': '1-3 turns'},
    {'name': 'freeze',          'displayName': 'Freeze',            'category': 'major',
     'effect': 'Prevents the Pokémon from acting until thawed.', 'default_duration': 'Until thawed'},
    # Volatile statuses
    {'name': 'confusion',       'displayName': 'Confusion',         'category': 'volatile',
     'effect': 'Chance to hurt itself in confusion instead of executing a move.', 'default_duration': '1-4 turns'},
    {'name': 'flinch',          'displayName': 'Flinch',            'category': 'volatile',
     'effect': 'Prevents the Pokémon from acting this turn.', 'default_duration': '1 turn'},
    {'name': 'infatuation',     'displayName': 'Infatuation',       'category': 'volatile',
     'effect': 'Chance to prevent the Pokémon from acting.', 'default_duration': 'Until cured/switch-out'},
    {'name': 'leech-seed',      'displayName': 'Leech Seed',        'category': 'volatile',
     'effect': "Drains HP each turn into the seeder.", 'default_duration': 'Until switch-out'},
    {'name': 'aqua-ring',       'displayName': 'Aqua Ring',         'category': 'volatile',
     'effect': 'Heals the holder a flat fraction of max HP each turn.', 'default_duration': 'Until switch-out'},
    {'name': 'ingrain',         'displayName': 'Ingrain',           'category': 'volatile',
     'effect': 'Heals the holder each turn; roots it in place (cannot switch/be forced out, immune to gravity-style removal).', 'default_duration': 'Until switch-out'},
    {'name': 'curse',           'displayName': 'Curse (Ghost)',     'category': 'volatile',
     'effect': 'Deals damage each turn.', 'default_duration': 'Until switch-out'},
    {'name': 'taunt',           'displayName': 'Taunt',             'category': 'volatile',
     'effect': 'Prevents using status moves.', 'default_duration': '3 turns'},
    {'name': 'encore',          'displayName': 'Encore',            'category': 'volatile',
     'effect': 'Forces the repeat of its last move.', 'default_duration': '3 turns'},
    {'name': 'torment',         'displayName': 'Torment',           'category': 'volatile',
     'effect': 'Prevents using the same move twice in a row.', 'default_duration': 'Until switch-out'},
    {'name': 'disable',         'displayName': 'Disable',           'category': 'volatile',
     'effect': "Prevents using the target's last move.", 'default_duration': '4 turns'},
    {'name': 'attract',         'displayName': 'Attract',           'category': 'volatile',
     'effect': 'See Infatuation.', 'default_duration': 'Until cured/switch-out'},
    {'name': 'yawn',            'displayName': 'Yawn (Drowsy)',     'category': 'volatile',
     'effect': 'Causes sleep at the end of the next turn.', 'default_duration': '1 turn, then Sleep'},
    {'name': 'perish-song',     'displayName': 'Perish Song',       'category': 'volatile',
     'effect': 'Faints the Pokémon when the counter reaches zero.', 'default_duration': '3 turns'},
    {'name': 'endure',          'displayName': 'Endure',            'category': 'volatile',
     'effect': "Guarantees the holder survives this turn's hit with at least 1 HP.", 'default_duration': '1 turn'},
    {'name': 'substitute',      'displayName': 'Substitute',        'category': 'volatile',
     'effect': 'Absorbs damage/status in place of the Pokémon.', 'default_duration': 'Until broken/switch-out'},
    {'name': 'protect',         'displayName': 'Protect',           'category': 'volatile',
     'effect': 'Blocks most moves this turn.', 'default_duration': '1 turn'},
    {'name': 'detect',          'displayName': 'Detect',            'category': 'volatile',
     'effect': 'Blocks most moves this turn (identical to Protect).', 'default_duration': '1 turn'},
    {'name': 'spiky-shield',    'displayName': 'Spiky Shield',      'category': 'volatile',
     'effect': 'Blocks most moves; damages the attacker on contact.', 'default_duration': '1 turn'},
    {'name': 'kings-shield',    'displayName': "King's Shield",     'category': 'volatile',
     "effect": "Blocks most moves; sharply lowers the attacker's Attack on contact.", 'default_duration': '1 turn'},
    {'name': 'baneful-bunker',  'displayName': 'Baneful Bunker',    'category': 'volatile',
     'effect': 'Blocks most moves; poisons the attacker on contact.', 'default_duration': '1 turn'},
    {'name': 'burning-bulwark', 'displayName': 'Burning Bulwark',   'category': 'volatile',
     'effect': 'Blocks most moves; burns the attacker on contact.', 'default_duration': '1 turn'},
    {'name': 'silk-trap',       'displayName': 'Silk Trap',         'category': 'volatile',
     "effect": "Blocks most moves; lowers the attacker's Speed on contact.", 'default_duration': '1 turn'},
    {'name': 'obstruct',        'displayName': 'Obstruct',          'category': 'volatile',
     "effect": "Blocks most moves; sharply lowers the attacker's Defense on contact.", 'default_duration': '1 turn'},
    {'name': 'crafty-shield',   'displayName': 'Crafty Shield',     'category': 'side',
     'effect': "Blocks status moves targeting the user's side this turn (does not block damaging moves, no contact reaction).", 'default_duration': '1 turn'},
    {'name': 'wide-guard',      'displayName': 'Wide Guard',        'category': 'side',
     'effect': "Blocks moves that target multiple Pokémon (spread moves) targeting the user's side this turn.", 'default_duration': '1 turn'},
    {'name': 'quick-guard',     'displayName': 'Quick Guard',       'category': 'side',
     'effect': "Blocks priority moves targeting the user's side this turn.", 'default_duration': '1 turn'},
    {'name': 'mat-block',       'displayName': 'Mat Block',         'category': 'side',
     'effect': "Blocks damaging moves targeting the user's side this turn (status moves unaffected); usable only as the user's first move after switching in.", 'default_duration': '1 turn'},
    {'name': 'max-guard',       'displayName': 'Max Guard',         'category': 'volatile',
     'effect': 'Blocks most moves this turn (identical to Protect); usable only while Dynamaxed.', 'default_duration': '1 turn'},
    {'name': 'focus-energy',    'displayName': 'Focus Energy',      'category': 'volatile',
     'effect': "Raises the user's critical-hit ratio.", 'default_duration': 'Until switch-out'},
    {'name': 'dragon-cheer',    'displayName': 'Dragon Cheer',      'category': 'volatile',
     'effect': "Raises an ally's critical-hit ratio (more for Dragon-types).", 'default_duration': 'Until switch-out'},
    {'name': 'foresight',       'displayName': 'Foresight',         'category': 'volatile',
     'effect': "Negates the target's evasion boosts; lets Normal/Fighting hit a Ghost-type target.", 'default_duration': 'Until switch-out'},
    {'name': 'miracle-eye',     'displayName': 'Miracle Eye',       'category': 'volatile',
     'effect': "Negates the target's evasion boosts; lets Psychic hit a Dark-type target.", 'default_duration': 'Until switch-out'},
    {'name': 'odor-sleuth',     'displayName': 'Odor Sleuth',       'category': 'volatile',
     'effect': "Negates the target's evasion boosts; lets Normal/Fighting hit a Ghost-type target (identical to Foresight).", 'default_duration': 'Until switch-out'},
    {'name': 'imprison',        'displayName': 'Imprison',          'category': 'volatile',
     'effect': "Prevents opponents from using any move the user also knows.", 'default_duration': 'Until switch-out'},
    {'name': 'magnet-rise',     'displayName': 'Magnet Rise',       'category': 'volatile',
     'effect': 'Grants immunity to Ground-type moves.', 'default_duration': '5 turns'},
    {'name': 'telekinesis',     'displayName': 'Telekinesis',       'category': 'volatile',
     'effect': 'Lifts the target off the ground; moves against it (almost) never miss.', 'default_duration': '3 turns'},
    {'name': 'laser-focus',     'displayName': 'Laser Focus',       'category': 'volatile',
     'effect': "Guarantees the user's next move is a critical hit.", 'default_duration': '2 turns'},
    {'name': 'lock-on',         'displayName': 'Lock-On',           'category': 'volatile',
     'effect': "Guarantees the user's next move against the locked target will not miss.", 'default_duration': "Until the user's next move"},
    {'name': 'mind-reader',     'displayName': 'Mind Reader',       'category': 'volatile',
     'effect': "Guarantees the user's next move against the locked target will not miss (identical to Lock-On).", 'default_duration': "Until the user's next move"},
    {'name': 'destiny-bond',    'displayName': 'Destiny Bond',      'category': 'volatile',
     'effect': "If the user faints this turn, whatever knocked it out faints too.", 'default_duration': "Until the user's next move"},
    {'name': 'grudge',          'displayName': 'Grudge',            'category': 'volatile',
     'effect': "If the user faints this turn, the move that did it loses all its PP.", 'default_duration': "Until the user's next move"},
    {'name': 'glaive-rush',     'displayName': 'Glaive Rush',       'category': 'volatile',
     'effect': "Self-inflicted after use: takes double damage and is always hit until the user's next turn.", 'default_duration': "1 turn"},
    {'name': 'stockpile',       'displayName': 'Stockpile',         'category': 'volatile',
     'effect': 'Stacks up to 3 times, boosting Defense/Sp. Def per stack; consumed by Spit Up/Swallow.', 'default_duration': 'Until switch-out or consumed'},
    {'name': 'octolock',        'displayName': 'Octolock',          'category': 'volatile',
     'effect': "Traps the target and lowers its Defense and Sp. Def every turn.", 'default_duration': 'Until switch-out'},
    {'name': 'salt-cure',       'displayName': 'Salt Cure',         'category': 'volatile',
     'effect': 'Damages the holder every turn (more against Water/Steel-types).', 'default_duration': 'Until switch-out'},
    {'name': 'tar-shot',        'displayName': 'Tar Shot',          'category': 'volatile',
     'effect': "Lowers Speed and doubles the holder's weakness to Fire-type moves.", 'default_duration': 'Until switch-out'},
    {'name': 'syrup-bomb',      'displayName': 'Syrup Bomb',        'category': 'volatile',
     'effect': "Lowers the target's Speed every turn.", 'default_duration': '3 turns'},
    {'name': 'magic-coat',      'displayName': 'Magic Coat',        'category': 'volatile',
     'effect': 'Reflects the next status move used against the holder back at its user.', 'default_duration': '1 turn'},
    {'name': 'snatch',          'displayName': 'Snatch',            'category': 'volatile',
     'effect': "Steals the next status move used by anyone this turn.", 'default_duration': '1 turn'},
    {'name': 'helping-hand',    'displayName': 'Helping Hand',      'category': 'volatile',
     'effect': "Boosts an ally's move power this turn.", 'default_duration': '1 turn'},
    {'name': 'powder',          'displayName': 'Powder',            'category': 'volatile',
     'effect': 'Punishes the holder for using a Fire-type move this turn.', 'default_duration': '1 turn'},
    {'name': 'after-you',       'displayName': 'After You',         'category': 'volatile',
     'effect': "Makes the target move immediately after the user this turn.", 'default_duration': '1 turn (instant)'},
    {'name': 'quash',           'displayName': 'Quash',             'category': 'volatile',
     'effect': "Pushes the target's move to occur last this turn.", 'default_duration': '1 turn (instant)'},
    {'name': 'redirect',        'displayName': 'Redirect (Follow Me / Rage Powder)', 'category': 'volatile',
     'effect': "Draws single-target opposing moves to the user this turn.", 'default_duration': '1 turn'},
    {'name': 'bound',           'displayName': 'Bound (Trapped)',   'category': 'volatile',
     'effect': "Deals damage each turn and prevents switching.", 'default_duration': '4-5 turns'},
    {'name': 'nightmare',       'displayName': 'Nightmare',         'category': 'volatile',
     'effect': 'Deals damage each turn while asleep.', 'default_duration': 'Until woken/cured'},
    # Field / side conditions
    {'name': 'wish',            'displayName': 'Wish',              'category': 'side',
     'effect': "Heals whichever Pokémon occupies the user's slot when it lands, two turns later.", 'default_duration': '2 turns, then resolves once'},
    {'name': 'spikes',          'displayName': 'Spikes',            'category': 'side',
     'effect': 'Damages grounded Pokémon switching in.', 'default_duration': 'Until cleared'},
    {'name': 'stealth-rock',    'displayName': 'Stealth Rock',      'category': 'side',
     'effect': 'Damages Pokémon switching in based on Rock effectiveness.', 'default_duration': 'Until cleared'},
    {'name': 'toxic-spikes',    'displayName': 'Toxic Spikes',      'category': 'side',
     'effect': 'Poisons grounded Pokémon switching in.', 'default_duration': 'Until cleared'},
    {'name': 'sticky-web',      'displayName': 'Sticky Web',        'category': 'side',
     'effect': 'Lowers Speed of grounded Pokémon switching in.', 'default_duration': 'Until cleared'},
    {'name': 'g-max-steelsurge','displayName': 'G-Max Steelsurge (Hazard)', 'category': 'side',
     'effect': 'Steel-type entry hazard; damages Pokémon switching in based on Steel effectiveness.', 'default_duration': 'Until cleared'},
    {'name': 'rainbow',         'displayName': 'Rainbow (Pledge Combo)', 'category': 'side',
     'effect': 'Water Pledge + Fire Pledge combo: doubles the chance of secondary effects for the side that set it.', 'default_duration': '4 turns'},
    {'name': 'sea-of-fire',     'displayName': 'Sea of Fire (Pledge Combo)', 'category': 'side',
     'effect': 'Fire Pledge + Grass Pledge combo: damages non-Fire-types on the target side each turn.', 'default_duration': '4 turns'},
    {'name': 'swamp',           'displayName': 'Swamp (Pledge Combo)', 'category': 'side',
     'effect': 'Water Pledge + Grass Pledge combo: quarters the Speed of Pokémon on the target side.', 'default_duration': '4 turns'},
    {'name': 'g-max-wildfire',  'displayName': 'G-Max Wildfire',    'category': 'side',
     'effect': 'Damages non-Fire-types on the target side each turn.', 'default_duration': '4 turns'},
    {'name': 'g-max-cannonade', 'displayName': 'G-Max Cannonade',   'category': 'side',
     'effect': 'Damages non-Water-types on the target side each turn.', 'default_duration': '4 turns'},
    {'name': 'g-max-vine-lash', 'displayName': 'G-Max Vine Lash',   'category': 'side',
     'effect': 'Damages non-Grass-types on the target side each turn.', 'default_duration': '4 turns'},
    {'name': 'g-max-volcalith', 'displayName': 'G-Max Volcalith',   'category': 'side',
     'effect': 'Damages non-Rock-types on the target side each turn.', 'default_duration': '4 turns'},
    {'name': 'reflect',         'displayName': 'Reflect',           'category': 'side',
     'effect': 'Halves incoming physical damage.', 'default_duration': '5-8 turns'},
    {'name': 'light-screen',    'displayName': 'Light Screen',      'category': 'side',
     'effect': 'Halves incoming special damage.', 'default_duration': '5-8 turns'},
    {'name': 'aurora-veil',     'displayName': 'Aurora Veil',       'category': 'side',
     'effect': 'Halves incoming physical and special damage.', 'default_duration': '5-8 turns'},
    {'name': 'tailwind',        'displayName': 'Tailwind',          'category': 'side',
     'effect': "Doubles the side's Speed.", 'default_duration': '4 turns'},
    {'name': 'weather-rain',    'displayName': 'Rain',              'category': 'field',
     'effect': 'Boosts Water moves, weakens Fire moves.', 'default_duration': '5-8 turns'},
    {'name': 'weather-sun',     'displayName': 'Harsh Sunlight',    'category': 'field',
     'effect': 'Boosts Fire moves, weakens Water moves.', 'default_duration': '5-8 turns'},
    {'name': 'weather-sand',    'displayName': 'Sandstorm',         'category': 'field',
     'effect': 'Damages non-Rock/Ground/Steel types each turn.', 'default_duration': '5-8 turns'},
    {'name': 'weather-hail',    'displayName': 'Hail / Snow',       'category': 'field',
     'effect': 'Damages (or boosts Defense of Ice-types) each turn.', 'default_duration': '5-8 turns'},
    {'name': 'weather-heavy-rain', 'displayName': 'Heavy Rain (Primal)', 'category': 'field',
     'effect': 'Rain that cannot be changed/ended by moves or abilities while active; Fire moves fail outright.', 'default_duration': 'Until primal weather ends'},
    {'name': 'weather-extreme-sun', 'displayName': 'Extremely Harsh Sunlight (Primal)', 'category': 'field',
     'effect': 'Sun that cannot be changed/ended by moves or abilities while active; Water moves fail outright.', 'default_duration': 'Until primal weather ends'},
    {'name': 'weather-strong-winds', 'displayName': 'Strong Winds (Delta Stream)', 'category': 'field',
     'effect': "Negates Flying-type's weaknesses; cannot be changed/ended by moves or abilities while active.", 'default_duration': 'Until Delta Stream holder leaves'},
    {'name': 'terrain-electric','displayName': 'Electric Terrain',  'category': 'field',
     'effect': 'Boosts Electric moves for grounded Pokémon, blocks sleep.', 'default_duration': '5-8 turns'},
    {'name': 'terrain-grassy',  'displayName': 'Grassy Terrain',    'category': 'field',
     'effect': 'Boosts Grass moves, heals grounded Pokémon each turn.', 'default_duration': '5-8 turns'},
    {'name': 'terrain-misty',   'displayName': 'Misty Terrain',     'category': 'field',
     'effect': 'Blocks status conditions for grounded Pokémon.', 'default_duration': '5-8 turns'},
    {'name': 'terrain-psychic', 'displayName': 'Psychic Terrain',   'category': 'field',
     'effect': 'Boosts Psychic moves, blocks priority moves on grounded Pokémon.', 'default_duration': '5-8 turns'},
    {'name': 'gravity',         'displayName': 'Gravity',           'category': 'field',
     'effect': 'Grounds all Pokémon and boosts accuracy.', 'default_duration': '5 turns'},
    {'name': 'trick-room',      'displayName': 'Trick Room',        'category': 'field',
     'effect': 'Reverses turn order (slower moves first).', 'default_duration': '5 turns'},
]


def get_statuses() -> list:
    return sorted(STATUSES, key=lambda s: s['name'])


# ── REST API ──────────────────────────────────────────────────────────────────

@app.route('/api/statuses')
def api_statuses():
    return jsonify(get_statuses())


@app.route('/api/statuses/with-data')
def api_with_data():
    names = []
    for path in STATUS_DIR.glob('*.json'):
        data = _read_json(path)
        if data and data.get('effects'):
            names.append(path.stem)
    return jsonify(names)


@app.route('/api/events/<name>', methods=['GET'])
def api_get_events(name: str):
    if _safe_name(name) is None:
        return jsonify({'error': 'invalid status name'}), 400
    return jsonify(_load_status_data(name))


@app.route('/api/events/<name>', methods=['PUT'])
def api_put_events(name: str):
    path = _status_path(name)
    if path is None:
        return jsonify({'error': 'invalid status name'}), 400
    body = request.get_json(force=True)
    _write_json(path, {
        'effects':     body.get('effects', []),
        'custom_desc': body.get('custom_desc', ''),
        'duration':    body.get('duration', ''),
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
    status_data = {}
    for path in STATUS_DIR.glob('*.json'):
        data = _read_json(path)
        if data is None:
            continue
        status_data[path.stem] = {
            'effects':    data.get('effects', []),
            'customDesc': data.get('custom_desc', ''),
            'duration':   data.get('duration', ''),
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
    return jsonify({'statusData': status_data, 'presets': presets})


@app.route('/api/import', methods=['POST'])
def api_import():
    body        = request.get_json(force=True)
    status_data = body.get('statusData', {})
    presets     = body.get('presets', [])

    for path in STATUS_DIR.glob('*.json'):
        path.unlink()
    for path in PRESETS_DIR.glob('*.json'):
        path.unlink()

    for name, data in status_data.items():
        path = _status_path(name)
        if path is None:
            continue
        _write_json(path, {
            'effects':     data.get('effects', []),
            'custom_desc': data.get('customDesc', ''),
            'duration':    data.get('duration', ''),
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
    print('  Status Event Editor')
    print('  http://localhost:5052')
    print('─' * 44)
    app.run(port=5052, debug=False)
