# Pokemon Simulator — Progress Tracker

**Last Updated:** 2026-07-31  
**Current Phase:** Phase 1 (Foundation) — In Progress

---

## Overview

Tracks implementation progress against the roadmap and success criteria defined in INTENT.md and pokemon-battle-engine-design-doc.md.

---

## Phase 1: Foundation (Core Battle Engine)

**Status:** 🔄 In Progress

### Core Event System
- [x] Event queue (priority + speed resolution) — engine/queue.py
- [x] Listener registry (register abilities, moves, items) — engine/listener.py
- [x] Event dispatch and listener invocation — engine/queue.py
- [x] Event spawning from listeners — engine/move_listener.py
- [x] Move listener for damage moves — engine/move_listener.py (DamageMoveListener, DamageApplicationListener)
- [x] Turn executor for event orchestration — battle/turn_executor.py
- [x] Tests for event system — tests/test_event_system.py

### Damage Calculation
- [x] DamageContext pattern — models/damage.py
- [x] `calc_damage()` function — battle/damage.py
- [x] Formula: `(((2 * level / 5) + 2) * power * atk / def) / 50 + 2`
- [x] STAB multiplier (1.5x)
- [x] Type effectiveness integration
- [x] Critical hit multiplier (1.5x)
- [x] Damage variance (0.85-1.0)

### Move Types & Execution
- [x] Move base class — models/move.py
- [ ] Move subclasses (PhysicalMove, SpecialMove, StatusMove) with type-based dispatch — **TODO**
- [x] Basic move data model (power, accuracy, pp, priority, type) — models/move.py
- [ ] Move resolution pipeline — battle/move_resolution.py (partial)

### Stat Changes & Buffs
- [x] BattleStat value holder (raw_value + stage) — models/battlestat.py
- [ ] Buffs class (centralized stat stages) — **TODO** (currently per-stat on BattleStat)
- [x] Multiplier calculation (stage → multiplier) — models/battlestat.py
- [ ] Stage clamping (-6, +6) — **TODO** (not enforced yet)
- [ ] Reset on switch-out — **TODO**

### Data Model
- [x] BaseStats wrapper (hp, atk, def, spa, spd, spe, eva) — data.py
- [x] Pokemon class (species data) — models/pokemon.py
- [x] BattlePokemon class (battle-time state) — models/pokemon.py
- [x] BattleStat class (raw_value + stage) — models/battlestat.py
- [x] Stat calculation functions (`calc_hp`, `calc_stat`) — utils/data.py
- [x] Type data model & type chart — data/generated/type_chart.json
- [x] Effect classes (StatChangeEffect, StatusEffect, VolatileStatusEffect, etc.) — models/effects.py
- [x] Action classes (MoveAction, SwitchAction) — models/action.py
- [x] Field & FieldSide classes (weather, terrain, entry hazards, screens) — models/field.py
- [x] StatusCondition & VolatileStatus enums — models/effects.py

### Success Criteria: Phase 1
- [x] Can initialize battle from two teams — battle_state.py
- [x] Can execute a full turn (move selection → resolution → end-of-turn) — turn_executor.py
- [x] Damage calculation matches official formula — battle/damage.py (existing)
- [ ] Stat stages apply correct multipliers — **TODO** (need Buffs class integration)

---

## Phase 2: UI Layer for Testing

**Status:** ⏳ Not Started

- [ ] Team builder UI (Flask/web or CLI)
- [ ] Battle viewer UI (show Pokémon, moves, log)
- [ ] Team save/load
- [ ] Predefined team templates

---

## Phase 3: Stateful Effects

**Status:** ⏳ Not Started

- [ ] VolatileStatus class with Interactions
- [ ] Multiple volatile statuses per Pokémon
- [ ] Non-volatile status (Burn, Poison, Sleep, Freeze, Paralysis)
- [ ] Weather effects (Hail, Rain, Sun, Sandstorm)
- [ ] Terrain effects (Grassy, Misty, Electric, Psychic)
- [ ] End-of-turn resolution (weather damage, Leech Seed, status ticks)
- [ ] Extensive move/ability coverage (~100+ moves, ~20+ abilities)

---

## Phase 4: Abilities & Items

**Status:** ⏳ Not Started

- [ ] Ability base class & listener integration
- [ ] Core abilities (Flash Fire, Intimidate, Regenerator, etc.)
- [ ] Item base class
- [ ] Item holder logic
- [ ] Critical item effects (Life Orb, Choice items, etc.)

---

## Phase 5: Bot System & Training

**Status:** ⏳ Not Started

- [ ] Bot abstraction (interface for move selection & team creation)
- [ ] Random bot (random moves, random team gen)
- [ ] Heuristic bot (smart move selection, type matchup scoring)
- [ ] Bot team generation (Pokémon Showdown-inspired)
- [ ] Bot learning (analyze battles, improve team composition)
- [ ] Adversarial mode (bots know player team, build counters)
- [ ] Batch simulation (headless, high-speed for training)
- [ ] Tournament orchestration

---

## Phase 6: Polish, Optimization & Testing

**Status:** ⏳ Not Started

- [ ] Performance optimization (target 1000+ battles/sec)
- [ ] Comprehensive test suite
- [ ] Battle replay/serialization
- [ ] Documentation & examples
- [ ] UI refinement

---

## Data Collection Status

**Status:** ✅ Complete

- [x] Gen 1 Pokémon data collected (final forms only)
- [x] Move data with current types (Bite = Dark, Fairy moves included)
- [x] Nature data (stat modifiers)
- [x] Type chart (effectiveness)
- [x] Files generated in `pokemon_sim/data/generated/`

**Files:**
- `pokemon.json` — Gen 1 final forms + stats + types + moves
- `move_data.json` — Move details (power, accuracy, pp, priority, type, etc.)
- `natures.json` — Nature stat modifiers
- `type_chart.json` — Type effectiveness matrix

---

## Known Issues & Blockers

1. **Import paths fixed** (2026-07-31) — Collection scripts now use absolute imports (`from pokemon_sim.utils...`)
2. **Pikachu missing from Gen 1 roster** — Intentional; code collects final forms only (Pikachu → Raichu). Can add exceptions if needed.
3. **No UI yet** — Testing the engine will require manual verification or a CLI runner initially.

---

## Next Steps

1. Implement core event system (queue + listener dispatch)
2. Implement damage calculation (DamageContext + calc_damage)
3. Wire up BattleStat & Buffs
4. Build Phase 2 UI for testing
5. Iterate on event resolution logic with real battles

---

## Notes

- Speed target: 1000+ battles/sec (critical for bot training)
- Determinism: Same input → same output (seeded RNG)
- Architecture: Event-driven; listeners react to events, not procedural branching
