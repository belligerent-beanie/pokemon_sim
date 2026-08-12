import random
from typing import TYPE_CHECKING

from models.events import DamageEvent, MoveResult, StatChangeEvent, StatusEvent
from models.move import Move
from models.pokemon import BattlePokemon
from models.effects import StatChangeEffect, StatusEffect, DrainEffect, RecoilEffect, CritBoostEffect
from battle.damage import DamageContext, calc_damage
from battle.status import apply_status

if TYPE_CHECKING:
    from battle.battle_state import Battle


def resolve_move(
    user: BattlePokemon,
    targets: list[BattlePokemon],
    move: Move,
    battle: "Battle",
) -> MoveResult:

    result = MoveResult(move=move, user=user, targets=targets, success=True)

    # Accuracy check
    if move.accuracy is not None:
        hit_chance = move.accuracy * (user.accuracy.value() / 100) / (user.evasion.value() / 100)
        if random.random() * 100 > hit_chance:
            result.success = False
            result.message = f"{user.pokemon.name}'s attack missed!"
            return result

    # Status moves skip damage calculation
    if move.damage_class == "status":
        _apply_effects(user, targets, move, result, {})
        return result

    # Damaging moves
    damage_dealt: dict[BattlePokemon, int] = {}

    for target in targets:
        is_critical = _check_critical(move)

        type_mult = _type_effectiveness(move.move_type, target.pokemon.types, battle)
        if type_mult == 0.0:
            result.events.append(DamageEvent(
                target=target,
                amount=0,
                message=f"It doesn't affect {target.pokemon.name}!",
            ))
            continue

        ctx = DamageContext(
            attacker=user,
            defender=target,
            move=move,
            level=user.pokemon.level,
            stab=1.5 if move.move_type in user.pokemon.types else 1.0,
            type_effectiveness=type_mult,
            weather_modifier=battle.field.weather_modifier(move.move_type),
            terrain_modifier=battle.field.terrain_modifier(
                move.move_type,
                user_grounded="flying" not in user.pokemon.types,
            ),
            critical=is_critical,
        )

        damage = calc_damage(ctx)
        actual = min(damage, target.current_hp)
        target.current_hp = max(0, target.current_hp - damage)
        damage_dealt[target] = actual

        result.events.append(DamageEvent(target=target, amount=actual, is_critical=is_critical))

    _apply_effects(user, targets, move, result, damage_dealt)
    return result


def _check_critical(move: Move) -> bool:
    crit_stage = sum(e.stages for e in move.effects if isinstance(e, CritBoostEffect))
    thresholds = (24, 8, 2, 1)  # Gen 6+ per-stage crit denominators
    return random.randint(1, thresholds[min(crit_stage, 3)]) == 1


def _type_effectiveness(move_type: str, defender_types: list[str], battle: "Battle") -> float:
    mult = 1.0
    for def_type in defender_types:
        mult *= battle.type_chart.get(move_type, {}).get(def_type, 1.0)
    return mult


def _apply_effects(
    user: BattlePokemon,
    targets: list[BattlePokemon],
    move: Move,
    result: MoveResult,
    damage_dealt: dict[BattlePokemon, int],
) -> None:
    for effect in move.effects:
        if random.random() > effect.chance:
            continue

        eff_targets = [user] if effect.target == "user" else targets

        for t in eff_targets:
            if isinstance(effect, StatChangeEffect):
                stat = t.get_stat(effect.stat)
                old = stat.stage
                stat.stage = max(-6, min(6, stat.stage + effect.stages))
                if stat.stage != old:
                    result.events.append(StatChangeEvent(target=t, stat=effect.stat, stages=effect.stages))

            elif isinstance(effect, StatusEffect):
                if apply_status(t, effect.status):
                    result.events.append(StatusEvent(target=t, status=effect.status))

            elif isinstance(effect, DrainEffect):
                source = targets[0] if t is user else user
                heal = int(damage_dealt.get(source, 0) * effect.fraction)
                user.current_hp = min(user.max_hp, user.current_hp + heal)

            elif isinstance(effect, RecoilEffect):
                total_dmg = sum(damage_dealt.values())
                recoil = int(total_dmg * effect.fraction)
                user.current_hp = max(0, user.current_hp - recoil)
