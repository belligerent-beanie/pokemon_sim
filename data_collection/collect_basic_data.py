# Gets all final forms, all types and all move names learned by those pokemon.

import requests
from tqdm import tqdm
from pokemon_sim.utils.data import save_json
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from pokemon_sim.utils.constants import GENS, MOVE_NAMES_FILE, POKEAPI_BASE_URL, POKEMON_FILE, TYPES_FILE

def collect_family_species(node, family_species: set[str]):
    family_species.add(node["species"]["name"])

    for child in node["evolves_to"]:
        collect_family_species(child, family_species)


def collect_final_species(node, finals: set[str]):
    if not node["evolves_to"]:
        finals.add(node["species"]["name"])

    for child in node["evolves_to"]:
        collect_final_species(child, finals)


def get_final_species_and_families(gen: int) -> tuple[set[str], dict[str, set[str]]]:

    low, high = GENS[gen]

    final_species = set()
    families = {}

    seen_chains = set()

    for species_id in tqdm(range(low, high + 1), desc="Evolution chains"):

        species = requests.get(f"{POKEAPI_BASE_URL}/pokemon-species/{species_id}/").json()

        chain_url = species["evolution_chain"]["url"]

        if chain_url in seen_chains:
            continue

        seen_chains.add(chain_url)

        chain = requests.get(chain_url).json()

        family_species = set()

        collect_family_species(chain["chain"], family_species)

        chain_finals = set()

        collect_final_species(chain["chain"], chain_finals)

        final_species.update(chain_finals)

        for final in chain_finals:
            families[final] = family_species

    return final_species, families


def get_varieties(species_name: str) -> list[str]:

    species = requests.get(f"{POKEAPI_BASE_URL}/pokemon-species/{species_name}").json()

    return [variety["pokemon"]["name"] for variety in species["varieties"]]


def get_final_forms(gen: int) -> tuple[list[str], dict[str, set[str]]]:

    final_species, families = get_final_species_and_families(gen)

    roster = set()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(get_varieties,species_name): species_name 
                    for species_name in final_species}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Finding forms"):
            roster.update(future.result())

    return sorted(roster), families

def get_species_move_pool(species_name: str) -> set[str]:

    species = requests.get(f"{POKEAPI_BASE_URL}/pokemon-species/{species_name}").json()

    moves = set()

    for variety in species["varieties"]:
        form_name = variety["pokemon"]["name"]

        pokemon = requests.get(f"{POKEAPI_BASE_URL}/pokemon/{form_name}").json()

        moves.update(move["move"]["name"] for move in pokemon["moves"])

    return moves


def get_pokemon_data(name: str, family_moves: set[str]) -> dict:

    pokemon = requests.get(f"{POKEAPI_BASE_URL}/pokemon/{name}").json()

    stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon["stats"]}

    types = [t["type"]["name"] for t in pokemon["types"]]

    return {
        "name": pokemon["name"],
        "hp": stats["hp"],
        "attack": stats["attack"],
        "defense": stats["defense"],
        "special_attack": stats["special-attack"],
        "special_defense": stats["special-defense"],
        "speed": stats["speed"],
        "types": types,
        "moves": sorted(family_moves),
    }


def main():

    final_forms, families = get_final_forms(1)

    pokemon_db = {}
    all_moves = set()
    all_types = set()

    #
    # Build species move cache
    #

    all_species = set()

    for family in families.values():
        all_species.update(family)

    species_move_pool = {}

    with ThreadPoolExecutor(max_workers=20) as executor:

        futures = {executor.submit(get_species_move_pool,species_name): species_name for species_name in all_species}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Building move pools"):
            species_name = futures[future]
            species_move_pool[species_name] = future.result()

    #
    # Build form -> family move pool
    #

    form_move_pools = {}

    for final_species, family in families.items():

        family_moves = set()

        for species_name in family:
            family_moves.update(species_move_pool[species_name])

        for form_name in get_varieties(final_species):
            form_move_pools[form_name] = family_moves

    #
    # Build pokemon database
    #

    with ThreadPoolExecutor(max_workers=20) as executor:

        futures = {
            executor.submit(get_pokemon_data, pokemon_name, form_move_pools[pokemon_name ]):pokemon_name
            for pokemon_name in final_forms}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Collecting Pokémon"):
            pokemon = future.result()

            pokemon_db[pokemon["name"]] = pokemon

            all_moves.update(pokemon["moves"])

            all_types.update(pokemon["types"])

    save_json(dict(sorted(pokemon_db.items())), POKEMON_FILE)

    save_json(sorted(all_types), TYPES_FILE)

    save_json(sorted(all_moves), MOVE_NAMES_FILE)


if __name__ == "__main__":
    main()