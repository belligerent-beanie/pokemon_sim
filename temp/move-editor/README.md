# Move Event Editor

Development tool for associating pub-sub events and conditions with Pokémon moves.
Data is stored in SQLite — queryable directly from the battle engine.

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

| File              | Contents                                              | Commit? |
|-------------------|-------------------------------------------------------|---------|
| `move_cache.json` | Processed move data from PokeAPI                      | ✅ Yes  |
| `move_events.db`  | SQLite — events, conditions, presets per move         | ❌ No   |

Add `move_events.db` to `.gitignore`. The Export JSON button is the portable backup.

## Reading from Python (pub-sub system)

```python
import sqlite3, json

DB = 'temp/move-editor/move_events.db'

def get_move_events(move_name: str) -> dict:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    row = con.execute(
        'SELECT * FROM move_data WHERE move_name = ?', (move_name,)
    ).fetchone()
    if row is None:
        return {'events': [], 'conditions': []}
    return {
        'events':     json.loads(row['events']),
        'conditions': json.loads(row['conditions']),
    }

def get_all_move_events() -> dict:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM move_data WHERE events != '[]'"
    ).fetchall()
    return {
        r['move_name']: {
            'events':     json.loads(r['events']),
            'conditions': json.loads(r['conditions']),
        }
        for r in rows
    }
```

## Schema

```sql
-- Per-move event/condition data
CREATE TABLE move_data (
    move_name   TEXT PRIMARY KEY,
    events      TEXT NOT NULL DEFAULT '[]',   -- JSON array
    conditions  TEXT NOT NULL DEFAULT '[]',   -- JSON array
    custom_desc TEXT NOT NULL DEFAULT ''
);

-- Reusable preset combinations
CREATE TABLE presets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    events     TEXT NOT NULL DEFAULT '[]',
    conditions TEXT NOT NULL DEFAULT '[]'
);
```
