# Ability Event Editor

Sibling of `../move-editor`, same file-backed event/condition/preset system,
applied to abilities. See that README for the general shape of the data
model and the multi-machine git workflow — this file only calls out what's
different.

## Setup

```
pip install flask requests
cd temp/ability-editor
python server.py
```

Then open **http://localhost:5051**.

## Differences from move-editor

- Catalog comes from PokeAPI's `/ability` endpoint (cached to
  `ability_cache.json`) instead of `/move`. No type/power/PP/priority —
  abilities only carry a generation and an effect description.
- The condition ("when does this trigger") vocabulary is ability-shaped:
  `on_switch_in`, `on_hit`, `on_contact`, `on_deal_damage`, `on_faint`,
  `on_ally_faint`, `on_turn_end`, `on_status_inflict`, `on_stat_change`,
  `on_weather_change`, `on_terrain_change`, `on_crit`, `on_move_used`, and
  `passive` for always-on abilities (Levitate, Huge Power, etc). Every
  option is always offered — abilities aren't gated by a move flag the way
  On Contact is for moves — plus "Custom…" for one not listed yet.
- Files live in `abilities/<ability_name>.json` instead of `moves/`.

## File format

```jsonc
// abilities/<ability_name>.json
{
  "effects": [ /* [{condition:{type,params}, events:[...]}] */ ],
  "custom_desc": ""
}
```

Presets and the export/import shape ({ abilityData, presets }) otherwise
mirror move-editor exactly.

## Event param vocabulary

See [`../EVENT_VOCAB.md`](../EVENT_VOCAB.md) — the same key should mean the
same thing across moves, abilities, and statuses. Check there before
inventing a new one.
