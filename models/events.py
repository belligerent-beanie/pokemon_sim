from dataclasses import dataclass, field
from typing import Optional

from models.move import Move
from models.pokemon import BattlePokemon
from models.effects import StatusCondition


@dataclass
class Event:
    target: BattlePokemon
    message: str = ""


@dataclass
class DamageEvent(Event):
    amount: int = 0
    is_critical: bool = False


@dataclass
class HealEvent(Event):
    amount: int = 0


@dataclass
class StatChangeEvent(Event):
    stat: str = ""
    stages: int = 0


@dataclass
class StatusEvent(Event):
    status: StatusCondition = StatusCondition.BURN
    chance: float = 1.0


@dataclass
class FaintEvent(Event):
    pass


@dataclass
class MoveResult:
    move: Move
    user: BattlePokemon
    targets: list[BattlePokemon]
    success: bool
    events: list[Event] = field(default_factory=list)
    message: str = ""
