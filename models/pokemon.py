from dataclasses import dataclass, field
from typing import Optional

from models.move import Move
from models.battlestat import BattleStat
from models.effects import StatusCondition
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
    nature: str = "hardy"
    sprite: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict, selected_moves: list[Move] = None) -> "Pokemon":
        """Create a Pokemon from a pokemon.json entry."""
        return cls(
            name=data["name"],
            types=data["types"],
            moves=selected_moves or [],
            base_hp=data["hp"],
            base_attack=data["attack"],
            base_defense=data["defense"],
            base_special_attack=data["special_attack"],
            base_special_defense=data["special_defense"],
            base_speed=data["speed"],
        )

    def get_battle_stats(self) -> tuple[int, dict[str, BattleStat]]:
        hp = calc_hp(
            self.base_hp,
            self.ivs.get("hp", 31),
            self.evs.get("hp", 0),
            self.level,
        )

        stats: dict[str, BattleStat] = {}
        for stat_name, base in [
            ("attack", self.base_attack),
            ("defense", self.base_defense),
            ("special_attack", self.base_special_attack),
            ("special_defense", self.base_special_defense),
            ("speed", self.base_speed),
        ]:
            stats[stat_name] = BattleStat(
                raw_value=calc_stat(
                    base,
                    self.ivs.get(stat_name, 31),
                    self.evs.get(stat_name, 0),
                    self.level,
                    stat_name,
                    self.nature,
                )
            )

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

    accuracy: BattleStat = field(default_factory=lambda: BattleStat(raw_value=100))
    evasion: BattleStat = field(default_factory=lambda: BattleStat(raw_value=100))

    status: Optional[StatusCondition] = None
    volatile_statuses: set = field(default_factory=set)

    toxic_counter: int = 1
    sleep_counter: int = 0

    def get_stat(self, stat_name: str) -> BattleStat:
        return getattr(self, stat_name)

    def has_type(self, type_name: str) -> bool:
        return type_name in self.pokemon.types

    def is_fainted(self) -> bool:
        return self.current_hp <= 0

    @classmethod
    def from_pokemon(cls, pokemon: Pokemon) -> "BattlePokemon":
        hp, stats = pokemon.get_battle_stats()
        return cls(
            pokemon=pokemon,
            current_hp=hp,
            max_hp=hp,
            attack=stats["attack"],
            defense=stats["defense"],
            special_attack=stats["special_attack"],
            special_defense=stats["special_defense"],
            speed=stats["speed"],
        )
