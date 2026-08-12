from dataclasses import dataclass, field
from typing import Optional

from models.effects import Effect, StatChangeEffect

_STAT_NAME_MAP: dict[str, str] = {
    "special-attack": "special_attack",
    "special-defense": "special_defense",
    "attack": "attack",
    "defense": "defense",
    "speed": "speed",
    "accuracy": "accuracy",
    "evasion": "evasion",
}

_TARGET_MAP: dict[str, str] = {
    "selected-pokemon": "target",
    "user": "user",
    "all-opponents": "all_opponents",
    "all-other-pokemon": "all_others",
    "random-opponent": "random",
    "all-pokemon": "all",
    "entire-field": "field",
    "user-or-ally": "user_or_ally",
    "users-field": "user_side",
    "opponents-field": "opponent_side",
    "ally": "ally",
    "all-allies": "all_allies",
    "user-and-allies": "user_and_allies",
    "fainting-pokemon": "target",
    "selected-pokemon-me-first": "target",
}


@dataclass
class Move:
    name: str
    move_type: str
    damage_class: str       # "physical", "special", "status"

    power: Optional[int]
    accuracy: Optional[int]
    pp: int
    priority: int

    attacking_stat: Optional[str]   # "attack" | "special_attack" | None for status
    defending_stat: Optional[str]   # "defense" | "special_defense" | None for status

    target: str = "target"
    effects: list[Effect] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)

    @classmethod
    def from_json(cls, data: dict) -> "Move":
        damage_class = data["damage_class"]

        if damage_class == "physical":
            attacking_stat, defending_stat = "attack", "defense"
        elif damage_class == "special":
            attacking_stat, defending_stat = "special_attack", "special_defense"
        else:
            attacking_stat, defending_stat = None, None

        target = _TARGET_MAP.get(data.get("target", "selected-pokemon"), "target")

        # Convert PokeAPI stat_changes to StatChangeEffect objects.
        # Convention: positive stages → self-boost (user); negative → debuff (target).
        # Self-targeting moves always affect the user.
        # NOTE: self-debuff moves like Close Combat need a secondary-effects database
        # to be handled correctly; this heuristic covers the common cases.
        effects: list[Effect] = []
        for change in data.get("stat_changes", []):
            raw_stat = change["stat"]["name"]
            stat = _STAT_NAME_MAP.get(raw_stat, raw_stat.replace("-", "_"))
            stages = change["change"]
            effect_target = "user" if (stages > 0 or target == "user") else "target"
            effects.append(StatChangeEffect(stat=stat, stages=stages, target=effect_target))

        return cls(
            name=data["name"],
            move_type=data["type"],
            damage_class=damage_class,
            power=data.get("power"),
            accuracy=data.get("accuracy"),
            pp=data.get("pp", 1),
            priority=data.get("priority", 0),
            attacking_stat=attacking_stat,
            defending_stat=defending_stat,
            target=target,
            effects=effects,
        )
