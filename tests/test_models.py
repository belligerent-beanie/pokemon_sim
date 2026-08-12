"""Core model tests. Run from pokemon_sim/: python -m pytest tests/"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from utils.constants import POKEMON_FILE, MOVE_DATA_FILE
from utils.data import load_json, calc_hp, calc_stat, NATURE_DB
from models.pokemon import Pokemon, BattlePokemon
from models.move import Move
from models.effects import StatChangeEffect, StatusCondition


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pokemon_db():
    return load_json(POKEMON_FILE)


@pytest.fixture(scope="module")
def move_db():
    return load_json(MOVE_DATA_FILE)


@pytest.fixture(scope="module")
def charizard(pokemon_db):
    return pokemon_db["charizard"]


# ── Pokemon.from_json ─────────────────────────────────────────────────────────

def test_from_json_base_stats(charizard):
    pkmn = Pokemon.from_json(charizard)
    assert pkmn.name == "charizard"
    assert pkmn.base_hp == 78
    assert pkmn.base_attack == 84
    assert pkmn.base_speed == 100
    assert "fire" in pkmn.types
    assert "flying" in pkmn.types


def test_from_json_with_moves(charizard, move_db):
    move_names = ["flamethrower", "earthquake", "air-slash", "dragon-dance"]
    moves = [Move.from_json(move_db[m]) for m in move_names if m in move_db]
    pkmn = Pokemon.from_json(charizard, moves)
    assert len(pkmn.moves) == len(move_names)
    assert pkmn.moves[0].name == "flamethrower"


# ── BattlePokemon ─────────────────────────────────────────────────────────────

def test_battle_pokemon_full_hp(charizard):
    pkmn = Pokemon.from_json(charizard)
    bp = BattlePokemon.from_pokemon(pkmn)
    assert bp.current_hp == bp.max_hp
    assert bp.max_hp > 0
    assert bp.status is None
    assert len(bp.volatile_statuses) == 0


def test_battle_pokemon_stats_positive(charizard):
    pkmn = Pokemon.from_json(charizard)
    bp = BattlePokemon.from_pokemon(pkmn)
    for attr in ("attack", "defense", "special_attack", "special_defense", "speed"):
        assert bp.get_stat(attr).value() > 0, f"{attr} should be > 0"


# ── Nature stat bonus ─────────────────────────────────────────────────────────

def test_nature_boost_speed(charizard):
    neutral = Pokemon.from_json(charizard)
    neutral.nature = "hardy"
    _, neutral_stats = neutral.get_battle_stats()

    timid = Pokemon.from_json(charizard)
    timid.nature = "timid"
    _, timid_stats = timid.get_battle_stats()

    assert timid_stats["speed"].value() > neutral_stats["speed"].value()
    assert timid_stats["attack"].value() < neutral_stats["attack"].value()


def test_nature_boost_special_attack(charizard):
    neutral = Pokemon.from_json(charizard)
    neutral.nature = "hardy"
    _, neutral_stats = neutral.get_battle_stats()

    modest = Pokemon.from_json(charizard)
    modest.nature = "modest"
    _, modest_stats = modest.get_battle_stats()

    assert modest_stats["special_attack"].value() > neutral_stats["special_attack"].value()
    assert modest_stats["attack"].value() < neutral_stats["attack"].value()


def test_neutral_natures_no_change(charizard):
    for nature in ("hardy", "docile", "serious", "bashful", "quirky"):
        neutral = Pokemon.from_json(charizard)
        neutral.nature = "hardy"
        _, base_stats = neutral.get_battle_stats()

        pkmn = Pokemon.from_json(charizard)
        pkmn.nature = nature
        _, stats = pkmn.get_battle_stats()

        for stat_name in ("attack", "defense", "special_attack", "special_defense", "speed"):
            assert stats[stat_name].value() == base_stats[stat_name].value(), \
                f"Neutral nature {nature} should not change {stat_name}"


# ── EVs and IVs ───────────────────────────────────────────────────────────────

def test_max_evs_raise_stat(charizard):
    low = Pokemon.from_json(charizard)
    low.ivs = {"speed": 0}
    low.evs = {"speed": 0}

    high = Pokemon.from_json(charizard)
    high.ivs = {"speed": 31}
    high.evs = {"speed": 252}

    _, low_stats = low.get_battle_stats()
    _, high_stats = high.get_battle_stats()

    assert high_stats["speed"].value() > low_stats["speed"].value()


# ── Move.from_json ────────────────────────────────────────────────────────────

def test_move_physical(move_db):
    mv = Move.from_json(move_db["earthquake"])
    assert mv.move_type == "ground"
    assert mv.damage_class == "physical"
    assert mv.attacking_stat == "attack"
    assert mv.defending_stat == "defense"
    assert mv.power == 100


def test_move_special(move_db):
    mv = Move.from_json(move_db["flamethrower"])
    assert mv.move_type == "fire"
    assert mv.damage_class == "special"
    assert mv.attacking_stat == "special_attack"
    assert mv.defending_stat == "special_defense"
    assert mv.power == 90


def test_move_status_with_effect(move_db):
    swords_dance = Move.from_json(move_db["swords-dance"])
    assert swords_dance.damage_class == "status"
    assert swords_dance.attacking_stat is None
    assert len(swords_dance.effects) == 1
    eff = swords_dance.effects[0]
    assert isinstance(eff, StatChangeEffect)
    assert eff.stat == "attack"
    assert eff.stages == 2


def test_move_stat_names_no_hyphens(move_db):
    """All stat names in Move effects should use underscores, not hyphens."""
    for move_name, data in move_db.items():
        mv = Move.from_json(data)
        for eff in mv.effects:
            if isinstance(eff, StatChangeEffect):
                assert "-" not in eff.stat, \
                    f"{move_name} effect has hyphenated stat name: '{eff.stat}'"


# ── BattleStat stages ─────────────────────────────────────────────────────────

def test_battlestat_stage_boosts(charizard):
    bp = BattlePokemon.from_pokemon(Pokemon.from_json(charizard))
    base = bp.attack.value()

    bp.attack.stage = 1
    assert abs(bp.attack.value() - base * 1.5) < 1

    bp.attack.stage = 2
    assert abs(bp.attack.value() - base * 2.0) < 1

    bp.attack.stage = -1
    assert abs(bp.attack.value() - base * (2 / 3)) < 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
