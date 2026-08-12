from dataclasses import dataclass
from enum import Enum
from typing import Literal


class StatusCondition(str, Enum):
    BURN = "burn"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    POISON = "poison"
    TOXIC = "toxic"


class VolatileStatus(str, Enum):
    CONFUSION = "confusion"
    FLINCH = "flinch"
    INFATUATION = "infatuation"
    ENCORE = "encore"
    TAUNT = "taunt"
    LEECH_SEED = "leech_seed"
    BOUND = "bound"
    DROWSY = "drowsy"


EffectTarget = Literal["user", "target", "all_opponents", "user_side", "opponent_side", "field"]


@dataclass
class Effect:
    chance: float = 1.0
    target: EffectTarget = "target"


@dataclass
class StatChangeEffect(Effect):
    stat: str = ""
    stages: int = 0


@dataclass
class StatusEffect(Effect):
    status: StatusCondition = StatusCondition.BURN


@dataclass
class VolatileStatusEffect(Effect):
    status: VolatileStatus = VolatileStatus.CONFUSION


@dataclass
class HealEffect(Effect):
    fraction: float = 0.5
    target: EffectTarget = "user"


@dataclass
class RecoilEffect(Effect):
    """Recoil to the user as a fraction of damage dealt."""
    fraction: float = 0.25
    target: EffectTarget = "user"


@dataclass
class DrainEffect(Effect):
    """Drain HP from target; user recovers a fraction of damage dealt."""
    fraction: float = 0.5
    target: EffectTarget = "user"


@dataclass
class CritBoostEffect(Effect):
    """Raise the critical hit stage for this move."""
    stages: int = 1
    target: EffectTarget = "user"
