# Move Event Editor

Development tool for associating pub-sub events and conditions with Pokémon moves.
Data is stored as one JSON file per move (and per preset) — plain text, so it
diffs and syncs cleanly through git.

## Setup

```
pip install flask requests
cd temp/move-editor
python server.py
```

Then open **http://localhost:5050**.

## First run

The server makes one cheap request to PokeAPI to check the current move count,
then compares it to the local `move_cache.json`. If the cache is missing or the
count has changed, it fetches all moves in parallel (takes ~60–90 seconds).
Every subsequent launch serves from the cache instantly.

## Files

| Path                      | Contents                                          | Commit? |
|----------------------------|---------------------------------------------------|---------|
| `move_cache.json`          | Processed move data from PokeAPI                  | ✅ Yes  |
| `moves/<move_name>.json`   | Events, conditions, custom description for a move | ✅ Yes  |
| `presets/<id>.json`        | One reusable event/condition preset               | ✅ Yes  |

`moves/` and `presets/` are created automatically on first launch. Only moves
you've actually edited get a file — untouched moves have no entry.

## Working across multiple machines

Because each move and preset is its own tracked JSON file, syncing across
machines is just normal git: commit `moves/` and `presets/` along with your
other changes, then `git pull` on the other machine and restart `server.py`.
If you and someone else edit different moves, git merges them without any
conflict; edits to the *same* move on two machines behave like any other
text-file merge conflict — resolve it like you would any JSON file.

The **Export JSON** / **Import JSON** buttons in the editor still work as a
manual bulk export/import if you ever want a single-file snapshot (e.g. for a
backup, or to hand data to someone outside git).

## Reading from Python (pub-sub system)

```python
import json
from pathlib import Path

MOVES_DIR = Path('temp/move-editor/moves')

def get_move_events(move_name: str) -> dict:
    path = MOVES_DIR / f'{move_name}.json'
    if not path.exists():
        return {'events': [], 'conditions': []}
    data = json.loads(path.read_text('utf-8'))
    return {
        'events':     data.get('events', []),
        'conditions': data.get('conditions', []),
    }

def get_all_move_events() -> dict:
    result = {}
    for path in MOVES_DIR.glob('*.json'):
        data = json.loads(path.read_text('utf-8'))
        if data.get('events'):
            result[path.stem] = {
                'events':     data.get('events', []),
                'conditions': data.get('conditions', []),
            }
    return result
```

## File format

```jsonc
// moves/<move_name>.json
{
  "events": [ /* JSON array */ ],
  "conditions": [ /* JSON array */ ],
  "custom_desc": ""
}
```

```jsonc
// presets/<id>.json
{
  "name": "Preset name",
  "events": [ /* JSON array */ ],
  "conditions": [ /* JSON array */ ]
}
```
