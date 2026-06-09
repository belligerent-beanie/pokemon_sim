from dataclasses import dataclass, field
from typing import Optional

from models.move import Move


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


@dataclass
class BattleStat:
    raw_value: int

    stage: int = 0

    modifiers: dict[str, float] = field(
        default_factory=dict
    )

    def value(
        self,
        ignore_stage: bool = False,
        ignored_modifiers: Optional[set[str]] = None,
    ) -> float:

        ignored_modifiers = ignored_modifiers or set()

        value = self.raw_value

        if not ignore_stage:
            value *= self._apply_modifier()

        for source, modifier in self.modifiers.items():
            if source not in ignored_modifiers:
                value *= modifier

        return value

    def add_modifier(
        self,
        source: str,
        multiplier: float,
    ):
        self.modifiers[source] = multiplier

    def remove_modifier(
        self,
        source: str,
    ):
        self.modifiers.pop(source, None)

    def reset_stage(self):
        self.stage = 0

    def _apply_modifier(self) -> float:
        if self.stage >= 0:
            return (2 + self.stage) / 2
        return 2 / (2 - self.stage)


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
        nature_db: dict,
    ):
        hp, stats = get_battle_stats(
            pokemon,
            nature_db,
        )

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
        

