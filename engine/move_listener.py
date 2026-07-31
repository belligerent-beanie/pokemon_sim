"""Move listeners that handle move execution."""

from typing import Type

from pokemon_sim.engine.event import Event, MoveStartEvent, DamageEvent
from pokemon_sim.engine.listener import Listener
from pokemon_sim.battle.damage import DamageContext, calc_damage
from pokemon_sim.models.move import Move


class DamageMoveListener(Listener):
    """Listener for damage-dealing moves (Scratch, Tackle, etc.)."""

    def __init__(self, battle):
        self.battle = battle

    def listens_to(self, event_type: Type[Event]) -> bool:
        """Listen to MoveStartEvent."""
        return event_type == MoveStartEvent

    def resolve(self, event: Event) -> list[Event]:
        """Execute a move and return damage event."""
        if not isinstance(event, MoveStartEvent):
            return []

        if event.move is None or event.user is None or event.target is None:
            return []

        move = event.move
        user = event.user
        target = event.target

        # Only handle moves with power (damage moves)
        if move.power is None:
            return []

        # Create damage context
        ctx = DamageContext(
            attacker=user,
            defender=target,
            move=move,
            level=user.pokemon.level,
            stab=1.5 if move.move_type in user.pokemon.types else 1.0,
            type_effectiveness=self.battle.type_chart.get(move.move_type, {}).get(
                target.pokemon.types[0], 1.0
            ),  # Simplified: only check first type
            weather_modifier=self.battle.field.weather_modifier(move.move_type),
            terrain_modifier=self.battle.field.terrain_modifier(move.move_type, False),
            critical=False,  # TODO: Implement crit rolls
            damage_modifiers=[],  # TODO: Add ability/item modifiers
        )

        # Calculate damage
        damage = calc_damage(ctx)

        # Return damage event
        return [
            DamageEvent(
                priority=0,
                speed_source=None,
                target=target,
                amount=damage,
                source=user,
            )
        ]


class DamageApplicationListener(Listener):
    """Listener that applies damage to a Pokémon."""

    def listens_to(self, event_type: Type[Event]) -> bool:
        """Listen to DamageEvent."""
        return event_type == DamageEvent

    def resolve(self, event: Event) -> list[Event]:
        """Apply damage to target."""
        if not isinstance(event, DamageEvent):
            return []

        if event.target is None:
            return []

        # Apply damage
        event.target.current_hp = max(0, event.target.current_hp - event.amount)

        # TODO: Check for faint, trigger faint checks, switch-ins

        return []
