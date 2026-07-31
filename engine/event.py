from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pokemon_sim.models.pokemon import BattlePokemon


@dataclass
class Event(ABC):
    """Base class for all battle events."""
    priority: int = 0
    speed_source: Optional["BattlePokemon"] = None

    def __lt__(self, other: "Event") -> bool:
        """For priority queue sorting: higher priority first, then by speed."""
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority = "less than" for sorting

        if self.speed_source and other.speed_source:
            return self.speed_source.speed.raw_value > other.speed_source.speed.raw_value

        return False


@dataclass
class DamageEvent(Event):
    """Damage dealt to a Pokémon."""
    target: Optional["BattlePokemon"] = None
    amount: int = 0
    source: Optional["BattlePokemon"] = None  # Who dealt the damage


@dataclass
class TurnStartEvent(Event):
    """Turn has started."""
    turn_number: int = 1


@dataclass
class TurnEndEvent(Event):
    """Turn is ending; end-of-turn effects trigger."""
    turn_number: int = 1


@dataclass
class MoveStartEvent(Event):
    """A move is about to be executed."""
    user: Optional["BattlePokemon"] = None
    target: Optional["BattlePokemon"] = None
    move: Optional["Move"] = None  # noqa: F821
