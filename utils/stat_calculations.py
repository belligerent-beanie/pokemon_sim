from models.pokemon import BattleStat, Pokemon


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
    nature: str,
    nature_db: dict,
) -> int:

    stat = int(
        ((2 * base + iv + ev // 4) * level) / 100
    ) + 5

    nature_info = nature_db[nature]

    if stat_name == nature_info["increased_stat"]:
        stat = int(stat * 1.1)

    elif stat_name == nature_info["decreased_stat"]:
        stat = int(stat * 0.9)

    return stat

def get_battle_stats(
    pokemon: Pokemon,
    nature_db: dict,
) -> tuple[int, dict[str, BattleStat]]:

    hp = calc_hp(
        pokemon.base_hp,
        pokemon.ivs.get("hp", 31),
        pokemon.evs.get("hp", 0),
        pokemon.level,
    )

    stats = {
        "attack": BattleStat(
            raw_value=calc_stat(
                pokemon.base_attack,
                pokemon.ivs.get("attack", 31),
                pokemon.evs.get("attack", 0),
                pokemon.level,
                "attack",
                pokemon.nature,
                nature_db,
            )
        ),
        "defense": BattleStat(
            raw_value=calc_stat(
                pokemon.base_defense,
                pokemon.ivs.get("defense", 31),
                pokemon.evs.get("defense", 0),
                pokemon.level,
                "defense",
                pokemon.nature,
                nature_db,
            )
        ),
        "special_attack": BattleStat(
            raw_value=calc_stat(
                pokemon.base_special_attack,
                pokemon.ivs.get("special_attack", 31),
                pokemon.evs.get("special_attack", 0),
                pokemon.level,
                "special_attack",
                pokemon.nature,
                nature_db,
            )
        ),
        "special_defense": BattleStat(
            raw_value=calc_stat(
                pokemon.base_special_defense,
                pokemon.ivs.get("special_defense", 31),
                pokemon.evs.get("special_defense", 0),
                pokemon.level,
                "special_defense",
                pokemon.nature,
                nature_db,
            )
        ),
        "speed": BattleStat(
            raw_value=calc_stat(
                pokemon.base_speed,
                pokemon.ivs.get("speed", 31),
                pokemon.evs.get("speed", 0),
                pokemon.level,
                "speed",
                pokemon.nature,
                nature_db,
            )
        ),
    }

    return hp, stats
    




