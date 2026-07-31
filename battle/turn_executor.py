"""Turn execution using the event system."""

from pokemon_sim.engine.event import MoveStartEvent, TurnStartEvent, TurnEndEvent
from pokemon_sim.engine.move_listener import DamageMoveListener, DamageApplicationListener
from pokemon_sim.models.action import MoveAction


def execute_turn(battle, action_1: MoveAction, action_2: MoveAction) -> None:
    """
    Execute a single turn.

    Args:
        battle: Battle instance
        action_1: Action from player 1
        action_2: Action from player 2
    """
    # Register default listeners
    battle.listener_registry.clear()
    battle.listener_registry.register(DamageMoveListener(battle))
    battle.listener_registry.register(DamageApplicationListener())

    # Reset event queue
    battle.event_queue.clear()

    # Queue turn start
    battle.event_queue.enqueue(TurnStartEvent(turn_number=battle.turn_number))
    battle.event_queue.resolve_all()

    # Determine move order (priority + speed)
    ordered_actions = battle.determine_order(action_1, action_2)

    # Queue moves in order
    for action, pokemon in ordered_actions:
        if isinstance(action, MoveAction):
            battle.event_queue.enqueue(
                MoveStartEvent(
                    priority=action.move.priority,
                    speed_source=pokemon,
                    user=pokemon,
                    target=battle.get_active(3 - int(pokemon == battle.active_1) - 1),  # Get opponent
                    move=action.move,
                )
            )

    # Resolve all move events
    battle.event_queue.resolve_all()

    # Queue turn end
    battle.event_queue.enqueue(TurnEndEvent(turn_number=battle.turn_number))
    battle.event_queue.resolve_all()

    # Increment turn
    battle.turn_number += 1

    # Check for winner
    battle.check_winner()
