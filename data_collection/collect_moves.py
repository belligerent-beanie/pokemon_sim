import requests
from tqdm import tqdm

from pokemon_sim.utils.data import load_json, save_json
from pokemon_sim.utils.constants import MOVE_DATA_FILE, MOVE_NAMES_FILE, POKEAPI_BASE_URL

try:
    all_moves = load_json(MOVE_NAMES_FILE)

except FileNotFoundError as e:
    raise FileNotFoundError(
        f"{MOVE_NAMES_FILE} not found. "
        "Run collect_basic_data.py first."
    ) from e



move_db = {}

for move_name in tqdm(all_moves, desc="Collecting move data"):
    move = requests.get(
        f"{POKEAPI_BASE_URL}/move/{move_name}"
    ).json()

    move_db[move_name] = {
        "accuracy": move["accuracy"],
        "damage_class": move["damage_class"]["name"],
        "name": move["name"],
        "power": move["power"],
        "pp": move["pp"],
        "priority": move["priority"],
        "stat_changes": move["stat_changes"],
        "target": move["target"]["name"],
        "type": move["type"]["name"],
    }

save_json(move_db, MOVE_DATA_FILE)