
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BattleStat:
    raw_value: int

    stage: int = 0

    modifiers: dict[str, float] = field(default_factory=dict) # Rain and such

    def value(
        self,
        ignore_stage: bool = False,
        ignored_modifiers: Optional[set[str]] = None,
    ) -> float:

        ignored_modifiers = ignored_modifiers or set()

        value = self.raw_value

        if not ignore_stage:
            value *= self._apply_modifier()

        for source, modifier in self.modifiers.items():
            if source not in ignored_modifiers:
                value *= modifier

        return value

    def add_modifier(
        self,
        source: str,
        multiplier: float,
    ):
        self.modifiers[source] = multiplier

    def remove_modifier(
        self,
        source: str,
    ):
        self.modifiers.pop(source, None)

    def reset_stage(self):
        self.stage = 0

    def _apply_modifier(self) -> float:
        if self.stage >= 0:
            return (2 + self.stage) / 2
        return 2 / (2 - self.stage)