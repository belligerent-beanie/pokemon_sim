# Status Event Editor

Sibling of `../move-editor`, same file-backed event/condition/preset system,
applied to named statuses (major status conditions, volatile statuses, and
field/side conditions). See that README for the general shape of the data
model and the multi-machine git workflow — this file only calls out what's
different.

## Setup

```
pip install flask
cd temp/status-editor
python server.py
```

Then open **http://localhost:5052**.

## Differences from move-editor

- There's no PokeAPI endpoint for statuses, so the catalog is a curated list
  baked into `server.py` (`STATUSES`) — edit it there to add/remove/rename a
  status. Each entry has a `category` (`major`, `volatile`, `side`, or
  `field`) and a `default_duration` shown until you override it.
- Each status carries an editable **Duration** field alongside its
  description — e.g. "3 turns", "until switch-out", "until cured" — stored
  separately from `custom_desc`.
- The condition vocabulary is status-shaped: `on_apply`, `on_turn_end`
  (the per-turn tick, e.g. burn/poison damage), `on_turn_start`,
  `on_expire` (duration counter hits zero), `on_cure`, `on_damage_taken`
  (holder takes damage while afflicted), `on_move_block_check` (paralysis/
  sleep/freeze-style "can this Pokémon even move" gate), `on_switch_out`,
  `on_switch_in`, `on_hit_holder`. Every option is always offered, plus
  "Custom…" for a trigger not listed yet.
- Files live in `statuses/<status_name>.json` instead of `moves/`.

## File format

```jsonc
// statuses/<status_name>.json
{
  "effects":     [ /* [{condition:{type,params}, events:[...]}] */ ],
  "custom_desc": "",
  "duration":    ""
}
```

Presets and the export/import shape ({ statusData, presets }) otherwise
mirror move-editor exactly.

## Event param vocabulary

See [`../EVENT_VOCAB.md`](../EVENT_VOCAB.md) — the same key should mean the
same thing across moves, abilities, and statuses. Check there before
inventing a new one.
