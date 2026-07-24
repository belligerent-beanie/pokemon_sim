from dataclasses import dataclass, field
from typing import Optional

from models.pokemon import BattlePokemon
from models.field import Field
from utils.data import load_json
from utils.constants import TYPE_CHART_FILE


@dataclass
class Battle:
    team_1: list[BattlePokemon]
    team_2: list[BattlePokemon]

    active_1: BattlePokemon
    active_2: BattlePokemon

    field: Field = field(default_factory=Field)
    type_chart: dict = field(default_factory=dict)

    turn_number: int = 1
    winner: Optional[int] = None

    def get_active(self, player: int) -> BattlePokemon:
        return self.active_1 if player == 1 else self.active_2

    def set_active(self, player: int, pokemon: BattlePokemon) -> None:
        if player == 1:
            self.active_1 = pokemon
        else:
            self.active_2 = pokemon

    def check_winner(self) -> Optional[int]:
        team_1_alive = any(p.current_hp > 0 for p in self.team_1)
        team_2_alive = any(p.current_hp > 0 for p in self.team_2)

        if not team_1_alive:
            self.winner = 2
        elif not team_2_alive:
            self.winner = 1

        return self.winner

    def determine_order(self, action_1, action_2) -> list:
        from models.action import MoveAction, SwitchAction

        # Switches always go before moves
        a1_switch = isinstance(action_1, SwitchAction)
        a2_switch = isinstance(action_2, SwitchAction)

        if a1_switch and not a2_switch:
            return [(action_1, self.active_1), (action_2, self.active_2)]
        if a2_switch and not a1_switch:
            return [(action_2, self.active_2), (action_1, self.active_1)]

        # Priority bracket
        p1 = action_1.move.priority if isinstance(action_1, MoveAction) else 0
        p2 = action_2.move.priority if isinstance(action_2, MoveAction) else 0

        if p1 != p2:
            if p1 > p2:
                return [(action_1, self.active_1), (action_2, self.active_2)]
            return [(action_2, self.active_2), (action_1, self.active_1)]

        # Speed tiebreak (Trick Room reverses order)
        spd_1 = self.active_1.speed.value()
        spd_2 = self.active_2.speed.value()
        first_player_faster = (spd_1 <= spd_2) if self.field.trick_room else (spd_1 >= spd_2)

        if first_player_faster:
            return [(action_1, self.active_1), (action_2, self.active_2)]
        return [(action_2, self.active_2), (action_1, self.active_1)]

    @classmethod
    def from_teams(
        cls,
        team_1: list[BattlePokemon],
        team_2: list[BattlePokemon],
    ) -> "Battle":
        return cls(
            team_1=team_1,
            team_2=team_2,
            active_1=team_1[0],
            active_2=team_2[0],
            type_chart=load_json(TYPE_CHART_FILE),
        )
