#!/usr/bin/env python3
"""
Bulk-apply a preset's events to every move matching a pattern.

A move's saved data is a list of *effect blocks* — `{"condition": {...},
"events": [...]}` — one block per gating condition (on_hit, on_contact, ...).
Each preset carries its own `condition`; applying it finds-or-creates the
move's block for that condition and merges the preset's events into it.

Matches against fields from move_cache.json (name, displayName, type, effect,
damage_class, moveCat) and writes/merges into moves/<move_name>.json exactly
like the editor UI would.

Idempotent: each event this script adds is tagged with `"_from_preset":
<preset_id>`. Re-running with the same preset first strips its previously-
applied entries from that block before re-adding fresh copies, so you can
tweak a preset and re-run without piling up duplicates. Anything you added
by hand in the UI (untagged) is left alone.

Usage examples
--------------
List presets:
    python bulk_apply.py --list-presets

Preview which moves match, without writing anything:
    python bulk_apply.py --preset 3 --field effect --pattern "burn" --dry-run

Apply preset 3 to every move whose effect text mentions "burn":
    python bulk_apply.py --preset 3 --field effect --pattern "burn"

Narrow further with --type / --damage-class / --moveCat (ANDed with --pattern):
    python bulk_apply.py --preset 3 --field effect --pattern "poison" --type poison

Match on move name/slug instead of effect text:
    python bulk_apply.py --preset 5 --field name --pattern "^flame-"

Chance injection
----------------
By default, every event this script adds also gets a `chance` param set to
the move's real PokeAPI `effect_chance` (e.g. Ice Beam's freeze event gets
chance=10, Will-O-Wisp's burn event gets chance=100 since it has no listed
chance and therefore always applies on hit). Values are fetched once and
cached in `chance_cache.json`. Use --no-chance to skip this and apply the
preset's events verbatim.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests

BASE_DIR         = Path(__file__).parent
CACHE_PATH       = BASE_DIR / 'move_cache.json'
MOVES_DIR        = BASE_DIR / 'moves'
PRESETS_DIR      = BASE_DIR / 'presets'
CHANCE_CACHE_PATH = BASE_DIR / 'chance_cache.json'

FIELD_CHOICES = ['name', 'displayName', 'effect', 'type', 'damage_class', 'moveCat']


def load_moves() -> list[dict]:
    if not CACHE_PATH.exists():
        sys.exit(f"error: {CACHE_PATH} not found — run server.py once to build the cache.")
    return json.loads(CACHE_PATH.read_text('utf-8'))['moves']


def load_presets() -> dict[int, dict]:
    presets = {}
    for path in PRESETS_DIR.glob('*.json'):
        if not path.stem.isdigit():
            continue
        data = json.loads(path.read_text('utf-8'))
        presets[int(path.stem)] = data
    return presets


def load_chance_cache() -> dict[str, int | None]:
    if CHANCE_CACHE_PATH.exists():
        return json.loads(CHANCE_CACHE_PATH.read_text('utf-8'))
    return {}


def save_chance_cache(cache: dict[str, int | None]) -> None:
    CHANCE_CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + '\n', 'utf-8')


def get_effect_chance(move_name: str, cache: dict[str, int | None]) -> int | None:
    """Real per-move chance (0-100) that the move's secondary effect triggers on hit.

    PokeAPI returns effect_chance=None for moves whose effect always applies
    (e.g. Will-O-Wisp, Thunder Wave) — that means 100%, not "unknown".
    """
    if move_name in cache:
        return cache[move_name]
    try:
        resp = requests.get(f'https://pokeapi.co/api/v2/move/{move_name}', timeout=15)
        resp.raise_for_status()
        chance = resp.json().get('effect_chance')
    except (requests.RequestException, ValueError) as e:
        print(f'  warning: could not fetch effect_chance for {move_name} ({e}); leaving chance unset')
        return None
    chance = 100 if chance is None else chance
    cache[move_name] = chance
    return chance


DEFAULT_CONDITION = {'type': 'on_hit', 'params': []}


def read_move_file(move_name: str) -> dict:
    path = MOVES_DIR / f'{move_name}.json'
    if not path.exists():
        return {'effects': [], 'custom_desc': ''}
    data = json.loads(path.read_text('utf-8'))
    if 'effects' not in data and 'events' in data:
        # Legacy flat shape from before effect blocks existed.
        events = data.get('events', [])
        data = {
            'effects': [{'condition': dict(DEFAULT_CONDITION), 'events': events}] if events else [],
            'custom_desc': data.get('custom_desc', ''),
        }
    return data


def write_move_file(move_name: str, data: dict) -> None:
    MOVES_DIR.mkdir(parents=True, exist_ok=True)
    path = MOVES_DIR / f'{move_name}.json'
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', 'utf-8')


EVENT_TOP_LEVEL_KEYS = {'priority', 'target'}
MOVE_NAME_PLACEHOLDER = '__MOVE_NAME__'
REMOVE_PARAM = object()  # sentinel: delete this key entirely rather than skip/set it


def _find_or_create_block(effects: list, condition: dict) -> dict:
    for block in effects:
        if block.get('condition') == condition:
            return block
    block = {'condition': condition, 'events': []}
    effects.append(block)
    return block


def apply_preset_to_move(move_name: str, preset_id: int, preset: dict, extra_params: dict[str, object],
                          condition_override: dict | None = None) -> bool:
    """Merge preset's events into the move's effect block for the preset's condition.
    Returns True if changed.

    Each preset declares one `condition` (default on_hit — see DEFAULT_CONDITION).
    Applying it finds the move's effect block with a matching condition
    (creating one if it doesn't exist yet) and merges the preset's events in.

    condition_override: apply this preset's events under a different condition
    than the one baked into the preset file (e.g. reusing the "Poison" preset's
    events under on_contact for Baneful Bunker instead of duplicating a whole
    second preset just to change its gate).

    extra_params: {key: value} pairs stamped onto every event this preset adds.
    Keys in EVENT_TOP_LEVEL_KEYS (e.g. "priority") overwrite that field on the
    event itself; any other key overwrites/adds a param of that name. A value
    of None is skipped (nothing to stamp for that move, preset default kept).
    A value of REMOVE_PARAM deletes that param outright (e.g. a preset that
    defaults to a 5-turn duration, applied to a move whose effect is
    persistent rather than timed).

    Any param whose val is the literal string "__MOVE_NAME__" is substituted
    with the move's own slug (e.g. so a shared "Self Protect" preset can tag
    each move's volatile status with its own name: protect, king-shield, ...).
    """
    data = read_move_file(move_name)
    effects = data.setdefault('effects', [])
    condition = condition_override or preset.get('condition') or DEFAULT_CONDITION

    def strip_tagged(items):
        return [i for i in items if i.get('_from_preset') != preset_id]

    def substitute_placeholders(params):
        return [
            {**p, 'val': move_name} if p.get('val') == MOVE_NAME_PLACEHOLDER else p
            for p in params
        ]

    def tagged_event_copies(items):
        out = []
        for item in items:
            copy = json.loads(json.dumps(item))  # deep copy
            copy['_from_preset'] = preset_id
            copy['params'] = substitute_placeholders(copy.get('params', []))
            keys_to_set = {k: v for k, v in extra_params.items() if v is not None}
            top_level = {k: v for k, v in keys_to_set.items() if k in EVENT_TOP_LEVEL_KEYS}
            param_level = {k: v for k, v in keys_to_set.items() if k not in EVENT_TOP_LEVEL_KEYS}
            copy.update({k: v for k, v in top_level.items() if v is not REMOVE_PARAM})
            if param_level:
                params = [p for p in copy['params'] if p.get('key') not in param_level]
                for k, v in param_level.items():
                    if v is not REMOVE_PARAM:
                        params.append({'key': k, 'val': str(v)})
                copy['params'] = params
            out.append(copy)
        return out

    before = json.dumps(data, sort_keys=True)

    block = _find_or_create_block(effects, condition)
    block['events'] = strip_tagged(block.get('events', [])) + tagged_event_copies(preset.get('events', []))
    # Drop the block if this preset was the only thing keeping it non-empty
    # (e.g. a re-run after the preset's events were cleared).
    if not block['events']:
        effects[:] = [b for b in effects if b is not block]

    data['effects'] = effects
    data.setdefault('custom_desc', '')

    after = json.dumps(data, sort_keys=True)
    if before == after:
        return False

    write_move_file(move_name, data)
    return True


def matches(move: dict, args) -> bool:
    if args.pattern is not None:
        value = str(move.get(args.field, ''))
        if not args.regex.search(value):
            return False
    if args.type and move.get('type') != args.type:
        return False
    if args.damage_class and move.get('damage_class') != args.damage_class:
        return False
    if args.moveCat and move.get('moveCat') != args.moveCat:
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--preset', type=int, help='Preset id to apply (see --list-presets)')
    ap.add_argument('--field', choices=FIELD_CHOICES, default='effect',
                     help='Field to match --pattern against (default: effect)')
    ap.add_argument('--pattern', help='Regex, matched case-insensitively against --field')
    ap.add_argument('--type', help='Filter: exact move type (e.g. fire)')
    ap.add_argument('--damage-class', dest='damage_class', help='Filter: physical/special/status')
    ap.add_argument('--moveCat', help='Filter: standard/z/max/partner/etc.')
    ap.add_argument('--dry-run', action='store_true', help='Show matches without writing anything')
    ap.add_argument('--no-chance', action='store_true',
                     help="Don't inject each move's real PokeAPI effect_chance into its events")
    ap.add_argument('--with-power', action='store_true',
                     help="Inject each move's power (from move_cache.json) into its events as a 'power' param")
    ap.add_argument('--with-priority', action='store_true',
                     help="Set each event's own priority to the move's real priority (from move_cache.json)")
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                     help='Stamp an extra literal param on every event this preset adds (repeatable). '
                          'Same value for every matched move — for a per-move value, fetch/compute it '
                          'like --with-power does instead.')
    ap.add_argument('--list-presets', action='store_true', help='List available presets and exit')
    args = ap.parse_args()

    presets = load_presets()

    if args.list_presets:
        if not presets:
            print('No presets found in presets/.')
        for pid, p in sorted(presets.items()):
            cond = p.get('condition') or DEFAULT_CONDITION
            print(f"[{pid}] {p.get('name', '(unnamed)')} "
                  f"— condition={cond.get('type')}, {len(p.get('events', []))} event(s)")
        return

    if args.preset is None:
        ap.error('--preset is required (or use --list-presets)')
    if args.preset not in presets:
        sys.exit(f"error: no preset with id {args.preset}. Run --list-presets to see available ids.")
    if not args.pattern and not (args.type or args.damage_class or args.moveCat):
        ap.error('give at least one filter: --pattern, --type, --damage-class, or --moveCat')

    args.regex = re.compile(args.pattern, re.IGNORECASE) if args.pattern else None

    literal_extras = {}
    for item in args.set:
        if '=' not in item:
            ap.error(f'--set expects KEY=VALUE, got {item!r}')
        k, v = item.split('=', 1)
        literal_extras[k] = v

    preset = presets[args.preset]
    moves = load_moves()
    hits = [m for m in moves if matches(m, args)]

    if not hits:
        print('No moves matched.')
        return

    print(f"Preset [{args.preset}] {preset.get('name')!r} matches {len(hits)} move(s):")
    for m in hits:
        print(f"  {m['name']:35s} ({m.get('type')}, {m.get('damage_class')})")

    if args.dry_run:
        print('\n(dry run — nothing written)')
        return

    chance_cache = {} if args.no_chance else load_chance_cache()
    changed = 0
    for m in hits:
        extra_params = dict(literal_extras)
        if not args.no_chance:
            extra_params['chance'] = get_effect_chance(m['name'], chance_cache)
        if args.with_power:
            if m.get('power') is None:
                print(f"  {m['name']:35s} warning: no fixed power (variable-power move); leaving power unset")
            else:
                extra_params['power'] = m['power']
        if args.with_priority:
            extra_params['priority'] = m.get('priority', 0)
        if extra_params:
            print(f"  {m['name']:35s} " + ', '.join(f'{k}={v}' for k, v in extra_params.items()))
        if apply_preset_to_move(m['name'], args.preset, preset, extra_params):
            changed += 1
    if not args.no_chance:
        save_chance_cache(chance_cache)
    print(f"\nWrote {changed} move file(s) in {MOVES_DIR.relative_to(Path.cwd()) if MOVES_DIR.is_absolute() else MOVES_DIR}.")


if __name__ == '__main__':
    main()
