import requests
from tqdm import tqdm
from utils.constants import TYPES_FILE, POKEAPI_BASE_URL, TYPE_CHART_FILE
from utils.data import load_json, save_json



try:
    all_types = load_json(TYPES_FILE)

except FileNotFoundError as e:
    raise FileNotFoundError(
        f"{TYPES_FILE} not found. "
        "Run collect_basic_data.py first."
    ) from e

type_chart = {}

for attack_type in tqdm(all_types,desc="Building type chart"):
    data = requests.get(
        f"{POKEAPI_BASE_URL}/type/{attack_type}"
    ).json()

    chart = {def_type: 1.0 for def_type in all_types}

    relations = data["damage_relations"]

    for t in relations["double_damage_to"]:
        chart[t["name"]] = 2.0

    for t in relations["half_damage_to"]:
        chart[t["name"]] = 0.5

    for t in relations["no_damage_to"]:
        chart[t["name"]] = 0.0

    type_chart[attack_type] = chart

save_json(type_chart, TYPE_CHART_FILE)
