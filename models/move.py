from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Move:
    name: str

    power: Optional[int]
    accuracy: Optional[int]

    move_type: str
    damage_class: str

    pp: Optional[int]
    max_pp: int
    priority: int

    attacking_stat: str
    defending_stat: str

    secondary_effects: list[dict] = field(default_factory=list)

    target: str = "selected-pokemon" # selected-pokemon, user, all-opponents, field

    tags: set[str] = field(default_factory=set) # Freeze-dry, Body Press, Sound, Biting


