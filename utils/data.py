import json
from pathlib import Path

from pokemon_sim.utils.constants import NATURES_FILE


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path) as f:
        return json.load(f)


def save_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


with open(NATURES_FILE) as _f:
    NATURE_DB: dict = json.load(_f)


def calc_hp(base: int, iv: int, ev: int, level: int) -> int:
    return int(((2 * base + iv + ev // 4) * level) / 100) + level + 10


def calc_stat(base: int, iv: int, ev: int, level: int, stat_name: str, nature: str) -> int:
    stat = int(((2 * base + iv + ev // 4) * level) / 100) + 5

    nature_info = NATURE_DB.get(nature, {})

    # PokeAPI uses hyphens ("special-attack"); our stat names use underscores.
    normalized = stat_name.replace("_", "-")

    if normalized == nature_info.get("increased_stat"):
        stat = int(stat * 1.1)
    elif normalized == nature_info.get("decreased_stat"):
        stat = int(stat * 0.9)

    return stat
