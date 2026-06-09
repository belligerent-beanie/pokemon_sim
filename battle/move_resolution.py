from battle.damage import DamageContext, calc_damage
from models.events import DamageEvent, MoveResult
from models.move import Move
from models.pokemon import BattlePokemon


def use_attack(
    self,
    move: Move,
    targets: list[BattlePokemon],
    battle,
) -> MoveResult:

    result = MoveResult(
        move=move,
        user=self,
        targets=targets,
        success=True,
    )

    for target in targets:

        ctx = DamageContext(
            attacker=self,
            defender=target,

            move=move,

            level=self.pokemon.level,

            stab=(
                1.5
                if move.move_type in self.pokemon.types
                else 1.0
            ),

            type_effectiveness=battle.type_chart.effectiveness(
                move.move_type,
                target.pokemon.types,
            ),

            weather_modifier=battle.weather_modifier(
                move
            ),

            terrain_modifier=battle.terrain_modifier(
                move
            ),
        )

        damage = calc_damage(ctx)

        target.current_hp = max(
            0,
            target.current_hp - damage,
        )

        result.damage_events.append(
            DamageEvent(
                target=target,
                amount=damage,
            )
        )

    return result

def use_status(
    self,
    move: Move,
    targets: list[BattlePokemon],
    battle,
) -> MoveResult:
    raise NotImplementedError

def use_move(
    self,
    move: Move,
    targets: list[BattlePokemon],
    battle,
) -> MoveResult:

    if move.damage_class == "status":
        return self.use_status(
            move,
            targets,
            battle,
        )

    return self.use_attack(
        move,
        targets,
        battle,
    )