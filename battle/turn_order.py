from dataclasses import dataclass

from models.action import Action
from models.pokemon import BattlePokemon


@dataclass
class TurnOrder:
    """Ordered list of (action, acting_pokemon) pairs for one turn."""
    actions: list[tuple[Action, BattlePokemon]]

    def __iter__(self):
        return iter(self.actions)
