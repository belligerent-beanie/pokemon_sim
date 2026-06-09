import requests
from tqdm import tqdm
from utils.io import save_json
from utils.constants import POKEAPI_BASE_URL, NATURES_FILE

natures = requests.get(
    f"{POKEAPI_BASE_URL}/nature?limit=100"
).json()["results"]

nature_db = {}

for nature_ref in tqdm(natures,desc="Collecting natures"):
    nature = requests.get(nature_ref["url"]).json()

    nature_db[nature["name"]] = {
        "increased_stat": (
            nature["increased_stat"]["name"]
            if nature["increased_stat"]
            else None
        ),
        "decreased_stat": (
            nature["decreased_stat"]["name"]
            if nature["decreased_stat"]
            else None
        ),
    }
save_json(nature_db, NATURES_FILE)