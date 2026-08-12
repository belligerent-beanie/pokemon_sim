"""
Demo: load one Pokémon from the dataset and convert it to Pokemon → BattlePokemon.
Run from the pokemon_sim/ directory: python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.constants import POKEMON_FILE, MOVE_DATA_FILE
from utils.data import load_json
from models.move import Move
from models.pokemon import Pokemon, BattlePokemon


def load_one(name: str, move_names: list[str] = None) -> tuple[Pokemon, BattlePokemon]:
    pokemon_db = load_json(POKEMON_FILE)
    move_db = load_json(MOVE_DATA_FILE)

    if name not in pokemon_db:
        raise ValueError(f"'{name}' not found — is the data generated? Run build_data.py first.")

    data = pokemon_db[name]

    moves: list[Move] = []
    for mn in (move_names or []):
        if mn in move_db:
            moves.append(Move.from_json(move_db[mn]))
        else:
            print(f"  [warn] move '{mn}' not in database, skipping")

    pokemon = Pokemon.from_json(data, moves)
    battle_pokemon = BattlePokemon.from_pokemon(pokemon)

    return pokemon, battle_pokemon


if __name__ == "__main__":
    NAME = "charizard"
    MOVES = ["flamethrower", "earthquake", "air-slash", "dragon-dance"]

    print(f"Loading {NAME}...")
    pkmn, bp = load_one(NAME, MOVES)

    print(f"\n{'=' * 30}")
    print(f"  {pkmn.name.upper()}")
    print(f"{'=' * 30}")
    print(f"  Types  : {', '.join(pkmn.types)}")
    print(f"  Level  : {pkmn.level}")
    print(f"  Nature : {pkmn.nature}")

    print(f"\n  Base Stats:")
    for label, base in [
        ("HP ", pkmn.base_hp),
        ("Atk", pkmn.base_attack),
        ("Def", pkmn.base_defense),
        ("SpA", pkmn.base_special_attack),
        ("SpD", pkmn.base_special_defense),
        ("Spe", pkmn.base_speed),
    ]:
        bar = "#" * (base // 10)
        print(f"  {label}  {base:>3}  {bar}")

    print(f"\n  Battle Stats  (Lv{pkmn.level}, 31 IVs, 0 EVs, {pkmn.nature}):")
    print(f"  HP   {bp.max_hp:>3}  ({bp.current_hp} current)")
    for label, attr in [
        ("Atk", "attack"),
        ("Def", "defense"),
        ("SpA", "special_attack"),
        ("SpD", "special_defense"),
        ("Spe", "speed"),
    ]:
        val = int(bp.get_stat(attr).value())
        print(f"  {label}  {val:>3}")

    if pkmn.moves:
        print(f"\n  Moveset:")
        for mv in pkmn.moves:
            pwr = str(mv.power) if mv.power else "--"
            acc = str(mv.accuracy) if mv.accuracy else "--"
            fx = f"  ({len(mv.effects)} effect{'s' if len(mv.effects) != 1 else ''})" if mv.effects else ""
            print(f"    {mv.name:<22} {mv.move_type:<10} {mv.damage_class:<10} pwr {pwr:>4}  acc {acc:>4}{fx}")

    print()

    # Prove BattlePokemon.from_pokemon round-trip
    assert bp.current_hp == bp.max_hp, "Fresh BattlePokemon should be at full HP"
    assert bp.status is None, "Fresh BattlePokemon should have no status"
    print("  OK  Pokemon -> BattlePokemon conversion successful")
