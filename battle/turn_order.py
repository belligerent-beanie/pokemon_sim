from dataclasses import dataclass
from models.move import Move
from models.pokemon import BattlePokemon


@dataclass
class TurnAction:
    attacker: BattlePokemon
    defender: BattlePokemon
    move: Move