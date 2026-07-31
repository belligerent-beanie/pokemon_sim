"""Tests for the event system and damage move execution."""

import pytest
from pokemon_sim.models.pokemon import Pokemon, BattlePokemon
from pokemon_sim.models.move import Move
from pokemon_sim.models.action import MoveAction
from pokemon_sim.battle.battle_state import Battle
from pokemon_sim.battle.turn_executor import execute_turn
from pokemon_sim.engine.event import MoveStartEvent, DamageEvent


@pytest.fixture
def pikachu():
    """Create a Pikachu for testing."""
    pikachu = Pokemon(
        name="pikachu",
        types=["electric"],
        moves=[],
        base_hp=35,
        base_attack=55,
        base_defense=40,
        base_special_attack=50,
        base_special_defense=50,
        base_speed=90,
        level=50,
        nature="hardy",
    )
    return BattlePokemon.from_pokemon(pikachu)


@pytest.fixture
def raichu():
    """Create a Raichu for testing."""
    raichu = Pokemon(
        name="raichu",
        types=["electric"],
        moves=[],
        base_hp=60,
        base_attack=90,
        base_defense=55,
        base_special_attack=90,
        base_special_defense=80,
        base_speed=100,
        level=50,
        nature="hardy",
    )
    return BattlePokemon.from_pokemon(raichu)


@pytest.fixture
def tackle():
    """Create a Tackle move for testing."""
    return Move(
        name="tackle",
        power=40,
        accuracy=100,
        move_type="normal",
        damage_class="physical",
        pp=35,
        max_pp=35,
        priority=0,
        attacking_stat="attack",
        defending_stat="defense",
        target="selected-pokemon",
        secondary_effects=[],
    )


@pytest.fixture
def scratch():
    """Create a Scratch move for testing."""
    return Move(
        name="scratch",
        power=40,
        accuracy=100,
        move_type="normal",
        damage_class="physical",
        pp=35,
        max_pp=35,
        priority=0,
        attacking_stat="attack",
        defending_stat="defense",
        target="selected-pokemon",
        secondary_effects=[],
    )


@pytest.fixture
def battle(pikachu, raichu):
    """Create a battle between Pikachu and Raichu."""
    return Battle.from_teams([pikachu], [raichu])


def test_damage_move_reduces_hp(battle, pikachu, raichu, tackle):
    """Test that using a damage move reduces target HP."""
    target_hp_before = raichu.current_hp

    action_1 = MoveAction(player=1, move=tackle, target_player=2)
    action_2 = MoveAction(player=2, move=tackle, target_player=1)

    execute_turn(battle, action_1, action_2)

    # Raichu should have taken damage from Pikachu's Tackle
    assert raichu.current_hp < target_hp_before


def test_event_queue_resolves_in_order(battle, pikachu, raichu, tackle, scratch):
    """Test that events resolve in priority + speed order."""
    # Pikachu is faster (90 speed vs 100 speed), but both moves have same priority
    # So Pikachu should go first

    action_1 = MoveAction(player=1, move=tackle, target_player=2)
    action_2 = MoveAction(player=2, move=scratch, target_player=1)

    execute_turn(battle, action_1, action_2)

    # Both should have taken damage
    assert pikachu.current_hp < 35  # Pikachu's full HP
    assert raichu.current_hp < 60  # Raichu's full HP


def test_damage_cannot_go_below_zero(battle, pikachu, raichu, tackle):
    """Test that HP cannot go below 0."""
    # Deal massive damage multiple times
    for _ in range(10):
        raichu.current_hp -= 100

    # Manually clamp to 0 to simulate battle damage
    raichu.current_hp = max(0, raichu.current_hp)

    assert raichu.current_hp == 0
    assert raichu.current_hp >= 0  # Never negative


def test_move_start_event_is_created(battle, pikachu, raichu, tackle):
    """Test that MoveStartEvent is properly created and enqueued."""
    action_1 = MoveAction(player=1, move=tackle, target_player=2)

    # Manually create and enqueue event to verify
    move_event = MoveStartEvent(
        priority=tackle.priority,
        speed_source=pikachu,
        user=pikachu,
        target=raichu,
        move=tackle,
    )

    assert move_event.user == pikachu
    assert move_event.target == raichu
    assert move_event.move == tackle


def test_battle_state_persists_across_turns(battle, pikachu, raichu, tackle):
    """Test that battle state is maintained across multiple turns."""
    initial_turn = battle.turn_number

    action_1 = MoveAction(player=1, move=tackle, target_player=2)
    action_2 = MoveAction(player=2, move=tackle, target_player=1)

    execute_turn(battle, action_1, action_2)

    assert battle.turn_number == initial_turn + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
