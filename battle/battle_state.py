from dataclasses import dataclass, field
from typing import Optional

from models.move import Move
from models.pokemon import BattlePokemon

@dataclass
class Battle:

    team_1: list[BattlePokemon]
    team_2: list[BattlePokemon]

    active_1: BattlePokemon
    active_2: BattlePokemon

    weather: Optional[str] = None
    terrain: Optional[str] = None

    turn_number: int = 1

    winner: Optional[int] = None
    

    def weather_modifier(
        self,
        move,
    ) -> float:
        return 1.0


    def terrain_modifier(
        self,
        move,
    ) -> float:
        return 1.0
    
    def get_active(
        self,
        player: int,
    ) -> BattlePokemon:

        if player == 1:
            return self.active_1

        return self.active_2
    
    def set_active(
    self,
    player: int,
    pokemon: BattlePokemon,
    ):

        if player == 1:
            self.active_1 = pokemon
        else:
            self.active_2 = pokemon
    
    def check_winner(self) -> Optional[int]:

        team_1_alive = any(
            pokemon.current_hp > 0
            for pokemon in self.team_1
        )

        team_2_alive = any(
            pokemon.current_hp > 0
            for pokemon in self.team_2
        )

        if not team_1_alive:
            self.winner = 2

        elif not team_2_alive:
            self.winner = 1

        return self.winner
    
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
        )
    
    def determine_order(self, move_1: Move, move_2: Move):
        pokemon_1 = self.active_1
        pokemon_2 = self.active_2

        if move_1.priority != move_2.priority:
            first = (pokemon_1, pokemon_2, move_1) if move_1.priority > move_2.priority else (pokemon_2, pokemon_1, move_2)

        elif (
            pokemon_1.speed.value()
            >=
            pokemon_2.speed.value()
        ):
            first = (
                pokemon_1,
                pokemon_2,
                move_1,
            )
        else:
            first = (
                pokemon_2,
                pokemon_1,
                move_2,
            )

        second = (
            pokemon_2,
            pokemon_1,
            move_2,
        ) if first[0] is pokemon_1 else (
            pokemon_1,
            pokemon_2,
            move_1,
        )

        return [first, second]