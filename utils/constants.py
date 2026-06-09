from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Paths

DATA_DIR = PROJECT_ROOT / "data"

GENERATED_DATA_DIR = DATA_DIR / "generated"
RAW_DATA_DIR = DATA_DIR / "raw"


POKEMON_FILE = GENERATED_DATA_DIR / "pokemon.json"
MOVE_NAMES_FILE = GENERATED_DATA_DIR / "move_names.json"
MOVE_DATA_FILE = GENERATED_DATA_DIR / "move_data.json"
TYPES_FILE = GENERATED_DATA_DIR / "types.json"
TYPE_CHART_FILE = GENERATED_DATA_DIR / "type_chart.json"
NATURES_FILE = GENERATED_DATA_DIR / "natures.json"


GENS = {
    1: (1, 151),
    2: (152, 251),
    3: (252, 386),
    4: (387, 493),
    5: (494, 649),
    6: (650, 721),
    7: (722, 809),
    8: (810, 905),
    9: (906, 1025),
}

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"
