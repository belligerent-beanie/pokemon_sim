from utils.constants import POKEMON_FILE
from models.pokemon import Pokemon, BattlePokemon

import json

with open(POKEMON_FILE) as f:
    all_pokemon = json.load(f)

print(len(all_pokemon))