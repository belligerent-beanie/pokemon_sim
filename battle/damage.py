import random
from dataclasses import dataclass, field

from models.move import Move
from models.pokemon import BattlePokemon


@dataclass
class DamageContext:
    attacker: BattlePokemon
    defender: BattlePokemon

    move: Move

    level: int

    stab: float = 1.0
    type_effectiveness: float = 1.0

    critical: bool = False

    weather_modifier: float = 1.0
    terrain_modifier: float = 1.0

    damage_modifiers: list[float] = field(
        default_factory=list
    )

def calc_damage(
    ctx: DamageContext,
) -> int:

    if ctx.move.power is None:
        raise ValueError(
            f"{ctx.move.name} is not a damaging move"
        )

    power = ctx.move.power

    attack_stat = getattr(
        ctx.attacker,
        ctx.move.attacking_stat,
    ).value()

    defense_stat = getattr(
        ctx.defender,
        ctx.move.defending_stat,
    ).value()

    damage = (
        (((2 * ctx.level) / 5) + 2)
        * power
        * attack_stat
        / defense_stat
    )

    damage = damage / 50 + 2

    damage *= ctx.stab
    damage *= ctx.type_effectiveness

    damage *= ctx.weather_modifier
    damage *= ctx.terrain_modifier

    if ctx.critical:
        damage *= 1.5

    for modifier in ctx.damage_modifiers:
        damage *= modifier

    damage *= random.uniform(0.85, 1.0)

    return max(1, int(damage))