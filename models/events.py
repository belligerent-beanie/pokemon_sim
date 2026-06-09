from dataclasses import dataclass, field

from models.move import Move
from models.pokemon import BattlePokemon


@dataclass
class DamageEvent:
    target: BattlePokemon
    amount: int


@dataclass
class StatChangeEvent:
    target: BattlePokemon
    stat: str
    stages: int


@dataclass
class StatusEvent:
    target: BattlePokemon
    status: str
    

@dataclass
class MoveResult:
    move: Move

    user: BattlePokemon
    targets: list[BattlePokemon]

    success: bool

    damage_events: list[DamageEvent] = field(
        default_factory=list
    )

    stat_change_events: list[StatChangeEvent] = field(
        default_factory=list
    )

    status_events: list[StatusEvent] = field(
        default_factory=list
    )

    messages: list[str] = field(
        default_factory=list
    )