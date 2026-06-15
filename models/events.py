from dataclasses import dataclass
from typing import Optional

from models.move import Move
from models.pokemon import BattlePokemon

# TODO: Maybe make field events a separate thing, same with player events (switching)
# Maybe make a subset 

@dataclass
class Event:
    target: BattlePokemon
    message:str

@dataclass
class DamageEvent(Event):
    amount: int


@dataclass
class StatChangeEvent(Event):
    stat: str
    stages: int
    chance: Optional[float]


@dataclass
class StatusEvent(Event):
    status: str
    chance: Optional[float]

@dataclass
class MoveResult(Event):
    move: Move

    user: BattlePokemon
    success: bool
    events: list[Event]
