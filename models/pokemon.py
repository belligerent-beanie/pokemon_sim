from dataclasses import dataclass, field
from typing import Optional

from models.move import Move
from models.battlestat import BattleStat
from utils.data import calc_hp, calc_stat


@dataclass
class Pokemon:
    name: str

    types: list[str]
    moves: list[Move]

    base_hp: int
    base_attack: int
    base_defense: int
    base_special_attack: int
    base_special_defense: int
    base_speed: int

    ivs: dict[str, int] = field(default_factory=dict)
    evs: dict[str, int] = field(default_factory=dict)

    level: int = 100

    sprite: Optional[str] = None
    nature: str = "hardy"
    
    def get_battle_stats(self) -> tuple[int, dict[str, BattleStat]]:

        hp = calc_hp(
            self.base_hp,
            self.ivs.get("hp", 31),
            self.evs.get("hp", 0),
            self.level,
        )

        stats = {
            "attack": BattleStat(
                raw_value=calc_stat(
                    self.base_attack,
                    self.ivs.get("attack", 31),
                    self.evs.get("attack", 0),
                    self.level,
                    "attack",
                    self.nature
                )
            ),
            "defense": BattleStat(raw_value=calc_stat(self.base_defense, self.ivs.get("defense", 31), self.evs.get("defense", 0), self.level, "defense", self.nature)),
            "special_attack": BattleStat(raw_value=calc_stat(self.base_special_attack, self.ivs.get("special_attack", 31), self.evs.get("special_attack", 0), self.level, "special_attack", self.nature)),
            "special_defense": BattleStat(raw_value=calc_stat(self.base_special_defense, self.ivs.get("special_defense", 31), self.evs.get("special_defense", 0), self.level, "special_defense", self.nature)),
            "speed": BattleStat(raw_value=calc_stat(self.base_speed,self.ivs.get("speed", 31),self.evs.get("speed", 0),self.level,"speed",self.nature)),
        }

        return hp, stats



@dataclass
class BattlePokemon:
    pokemon: Pokemon

    current_hp: int
    max_hp: int

    attack: BattleStat
    defense: BattleStat

    special_attack: BattleStat
    special_defense: BattleStat

    speed: BattleStat

    accuracy: BattleStat = field(
        default_factory=lambda: BattleStat(raw_value=100)
    )

    evasion: BattleStat = field(
        default_factory=lambda: BattleStat(raw_value=100)
    )

    status: Optional[str] = None

    def get_stat(self, stat_name: str) -> BattleStat:
        return getattr(self, stat_name)

    @classmethod
    def from_pokemon(
        cls,
        pokemon: Pokemon,
    ):
        hp, stats = pokemon.get_battle_stats()

        return cls(
            pokemon=pokemon,

            current_hp=hp,
            max_hp=hp,

            attack=stats["attack"],
            defense=stats["defense"],
            special_attack=stats["special_attack"],
            special_defense=stats["special_defense"],
            speed=stats["speed"]
        )

