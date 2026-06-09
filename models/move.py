from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Move:
    name: str

    power: Optional[int]
    accuracy: Optional[int]

    move_type: str
    damage_class: str

    pp: int
    priority: int

    attacking_stat: str
    defending_stat: str

    stat_changes: list[dict] = field(default_factory=list)

    target: str = "selected-pokemon"

    tags: set[str] = field(default_factory=set)


