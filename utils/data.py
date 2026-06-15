import json
from pathlib import Path
from utils.constants import NATURES_FILE


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)

    with open(path) as f:
        return json.load(f)


def save_json(data, path: Path):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(path, "w") as f:
        json.dump(
            data,
            f,
            indent=4,
        )

NATURE_DB = json.load(open(NATURES_FILE))

def calc_hp(
    base: int,
    iv: int,
    ev: int,
    level: int,
) -> int:
    return int(
        ((2 * base + iv + ev // 4) * level) / 100
    ) + level + 10


def calc_stat(
    base: int,
    iv: int,
    ev: int,
    level: int,
    stat_name: str,
    nature: str
) -> int:

    stat = int(((2 * base + iv + ev // 4) * level) / 100) + 5

    nature_info = NATURE_DB[nature]

    if stat_name == nature_info["increased_stat"]:
        stat = int(stat * 1.1)

    elif stat_name == nature_info["decreased_stat"]:
        stat = int(stat * 0.9)

    return stat

