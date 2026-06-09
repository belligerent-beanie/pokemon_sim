import json
from pathlib import Path


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