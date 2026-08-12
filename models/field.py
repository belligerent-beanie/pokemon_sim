from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FieldSide:
    spikes: int = 0           # 0–3 layers
    stealth_rock: bool = False
    toxic_spikes: int = 0     # 0–2 layers
    sticky_web: bool = False

    light_screen: int = 0     # turns remaining
    reflect: int = 0
    aurora_veil: int = 0

    tailwind: int = 0         # turns remaining


@dataclass
class Field:
    side_1: FieldSide = field(default_factory=FieldSide)
    side_2: FieldSide = field(default_factory=FieldSide)

    weather: Optional[str] = None      # "rain", "sun", "sand", "hail", "snow"
    weather_turns: int = 0

    terrain: Optional[str] = None     # "electric", "grassy", "misty", "psychic"
    terrain_turns: int = 0

    trick_room: bool = False
    trick_room_turns: int = 0
    magic_room: bool = False
    wonder_room: bool = False

    def get_side(self, player: int) -> FieldSide:
        return self.side_1 if player == 1 else self.side_2

    def weather_modifier(self, move_type: str) -> float:
        if self.weather == "rain":
            if move_type == "water":
                return 1.5
            if move_type == "fire":
                return 0.5
        elif self.weather == "sun":
            if move_type == "fire":
                return 1.5
            if move_type == "water":
                return 0.5
        return 1.0

    def terrain_modifier(self, move_type: str, user_grounded: bool) -> float:
        if not user_grounded:
            return 1.0
        if self.terrain == "electric" and move_type == "electric":
            return 1.3
        if self.terrain == "grassy" and move_type == "grass":
            return 1.3
        if self.terrain == "psychic" and move_type == "psychic":
            return 1.3
        return 1.0

    def tick(self) -> None:
        """Decrement all turn counters at end of turn."""
        if self.weather_turns > 0:
            self.weather_turns -= 1
            if self.weather_turns == 0:
                self.weather = None

        if self.terrain_turns > 0:
            self.terrain_turns -= 1
            if self.terrain_turns == 0:
                self.terrain = None

        if self.trick_room_turns > 0:
            self.trick_room_turns -= 1
            if self.trick_room_turns == 0:
                self.trick_room = False

        for side in (self.side_1, self.side_2):
            if side.light_screen > 0:
                side.light_screen -= 1
            if side.reflect > 0:
                side.reflect -= 1
            if side.aurora_veil > 0:
                side.aurora_veil -= 1
            if side.tailwind > 0:
                side.tailwind -= 1
