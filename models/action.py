from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.move import Move
    from models.pokemon import BattlePokemon


@dataclass
class Action:
    player: int  # 1 or 2


@dataclass
class MoveAction(Action):
    move: "Move"
    target_player: int  # which player's active slot to target


@dataclass
class SwitchAction(Action):
    switch_in: "BattlePokemon"
