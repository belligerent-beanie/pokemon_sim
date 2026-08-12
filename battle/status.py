import random

from models.effects import StatusCondition
from models.pokemon import BattlePokemon


def apply_status(target: BattlePokemon, status: StatusCondition) -> bool:
    """Apply a primary status condition. Returns False if already statused or immune."""
    if target.status is not None:
        return False

    # Type-based immunities (Gen 6+ rules)
    if status == StatusCondition.BURN and target.has_type("fire"):
        return False
    if status == StatusCondition.FREEZE and target.has_type("ice"):
        return False
    if status == StatusCondition.PARALYSIS and target.has_type("electric"):
        return False
    if status in (StatusCondition.POISON, StatusCondition.TOXIC) and (
        target.has_type("poison") or target.has_type("steel")
    ):
        return False

    target.status = status
    target.toxic_counter = 1

    # In-battle stat modifiers that persist with the status
    if status == StatusCondition.BURN:
        target.attack.add_modifier("burn", 0.5)
    elif status == StatusCondition.PARALYSIS:
        target.speed.add_modifier("paralysis", 0.5)
    elif status == StatusCondition.SLEEP:
        target.sleep_counter = random.randint(1, 3)

    return True


def remove_status(target: BattlePokemon) -> None:
    """Remove status and its associated modifiers."""
    if target.status == StatusCondition.BURN:
        target.attack.remove_modifier("burn")
    elif target.status == StatusCondition.PARALYSIS:
        target.speed.remove_modifier("paralysis")

    target.status = None
    target.sleep_counter = 0
    target.toxic_counter = 1


def end_of_turn_damage(target: BattlePokemon) -> int:
    """HP lost at end of turn from status condition. Returns 0 if no damage."""
    if target.status == StatusCondition.BURN:
        return max(1, target.max_hp // 8)
    if target.status == StatusCondition.POISON:
        return max(1, target.max_hp // 8)
    if target.status == StatusCondition.TOXIC:
        dmg = max(1, (target.max_hp * target.toxic_counter) // 16)
        target.toxic_counter += 1
        return dmg
    return 0


def can_act(target: BattlePokemon) -> bool:
    """Return True if the pokemon can use a move this turn."""
    if target.status == StatusCondition.SLEEP:
        if target.sleep_counter <= 0:
            remove_status(target)
            return True
        target.sleep_counter -= 1
        return False

    if target.status == StatusCondition.FREEZE:
        if random.random() < 0.20:   # 20% thaw chance per turn
            remove_status(target)
            return True
        return False

    if target.status == StatusCondition.PARALYSIS:
        return random.random() >= 0.25  # 25% fully-paralyzed chance

    return True
