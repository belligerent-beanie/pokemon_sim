# Pokemon Battle Simulator — Intent Document

## Purpose

Build an **application that lets users create Pokémon teams and compete in simulated tournaments against AI bots** that adapt to player strategies. The core is a **deterministic, extensible battle engine** that correctly resolves turn-based combat and produces repeatable results. Bots can:
- Create and evolve their own teams.
- Learn from battles to improve team composition and move selection.
- Know the player's team in advance and build counters.

The application has two layers:
1. **Battle Engine**: Pure simulation, no UI, deterministic, fast (1000+ battles/sec).
2. **UI Layer**: Pokémon Showdown-inspired interface for team building and tournament play. Simple graphics with sprites; no complex animations.

---

## Design Philosophy

**Event-driven architecture.** Battle resolution is fundamentally a sequence of discrete events (moves, stat changes, weather effects, ability triggers). By modeling these as first-class events with a listener/trigger system, we gain:
- **Composability**: New effects (abilities, items) are listeners, not special cases in branching logic.
- **Determinism**: Turn resolution follows a fixed priority + speed order; randomness is seeded and controlled.
- **Testability**: Each event can be tested in isolation; battles can be replayed from a saved state.

**Simplicity over cleverness, but not at the cost of speed.** Prioritize correct, readable code. Avoid premature micro-optimization, but design with performance in mind. Target: **1000+ battles per second**. This enables bot training, tournament simulations, and interactive testing without waiting.

---

## Scope

### In Scope

**Battle Engine:**
- Move execution, stat changes, type effectiveness, damage calculation, ability/item interactions.
- Battle state management: Pokémon, movesets, buffs, volatile/non-volatile status, held items, abilities.
- Deterministic simulation: Same input (team, moves, RNG seed) → identical output.
- Comprehensive move/ability coverage: Implement a broad set of moves and abilities (not just the basics).
- Team legality validation: Ensure teams are legal (moves learnable, stat limits, etc.).

**Bot System:**
- Bot creation: Figure out how bots build teams and decide moves during battle.
- Bot team generation: Seeded system for bots to create competitive teams (Pokémon Showdown-inspired).
- Bot learning: Bots can analyze battle results and evolve team composition/strategy over time.
- Adversarial play: Bots know the player's team in advance and can build specific counters.
- Batch simulation: Run many bot vs. bot battles (headless, no UI) for training.

**UI Layer:**
- Pokémon Showdown-esque interface: Team builder, tournament bracket, battle viewer.
- Simple graphics: Sprites for Pokémon, moves, status effects. No complex animations.
- Real-time battle UI: Player selects moves during battle; see results update.
- Tournament system: Organize and run tournaments, track results.

**Team Building & Management:**
- User can create teams (select Pokémon, moves, ability, nature, EVs, IVs, item).
- Save/load teams.
- Browse and select from predefined/common team templates.

### Out of Scope
- **No networking/online play**: Local simulator only; no server, no multiplayer in real-time, no battle pass.
- **No game progression within battles**: No level-up, no item pickup, no evolution. Pokémon state is frozen during battle.
- **No complex animations**: UI is simple; sprites are static or minimally animated.
- **No official completeness**: Not all Pokémon species, moves, or abilities will be implemented (see success criteria for scope).
- **No real-time simultaneous execution**: In UI mode, players take turns selecting moves (though simulation mode runs headless and can be fast).

---

## Success Criteria

### Core Battle Engine Works
- [ ] Can initialize a battle from two teams of Pokémon.
- [ ] Can execute a full turn: both players select moves → moves resolve in priority/speed order → end-of-turn effects fire → turn increments.
- [ ] Damage calculation matches official formula (level, stats, STAB, type effectiveness, critical hits, random variance).
- [ ] Stat stage changes apply correct multipliers; can reset on switch-out.
- [ ] Move/ability coverage: Implements at least 100+ unique moves and 20+ abilities with correct interactions.

### Event System is Functional
- [ ] Events are queued and resolved in priority + speed order.
- [ ] Listeners (abilities, moves, items) can react to events and emit new events.
- [ ] A single move can trigger multiple downstream events (e.g., Tackle → damage → flinch check → HP update).

### Data Model is Clean
- [ ] Static data (Pokémon, moves, abilities) is separate from battle state.
- [ ] Battle state can be serialized and deserialized (for replay/testing).
- [ ] Adding a new ability or move does not require refactoring core battle logic.

### Volatile Status System Works
- [ ] Pokémon can have multiple volatile statuses (e.g., Leech Seed + Taunt).
- [ ] Each volatile status has interactions that modify behavior (disable moves, apply stat drops, etc.).
- [ ] Volatile statuses clear on switch-out; non-volatile status persists.

### Determinism is Guaranteed
- [ ] Same input (teams, move sequence, RNG seed) always produces identical damage/outcome.
- [ ] Battles can be replayed by storing and re-executing move selections.
- [ ] Randomness is explicit (crit rolls, accuracy checks) and seeded from a single source.

### Performance Target Met
- [ ] Single 6v6 battle completes in ~1ms (on average).
- [ ] Can run 1000+ complete battles per second.
- [ ] Bot team generation is fast (seeded randomness, not exhaustive search).

### Team Creation & Management Works
- [ ] User can create a team by selecting Pokémon, moves, ability, nature, EVs, IVs, and held item.
- [ ] System validates team legality (moves learnable, nature exists, EVs/IVs in valid range).
- [ ] User can save/load teams; browse predefined templates.

### UI Layer Works
- [ ] Can view team builder (Pokémon Showdown-esque).
- [ ] Can play a battle via UI: see Pokémon sprites, select moves, watch battle resolve.
- [ ] Can browse and organize tournament brackets.
- [ ] **Testing benefit**: UI provides visual feedback for battle engine correctness; easy to spot logic errors.

### Bot System Works
- [ ] Bots can create competitive teams (Pokémon Showdown-inspired).
- [ ] Bots can select moves during battle (random, heuristic, or learned strategy).
- [ ] Bots can analyze battle results and improve team composition over time.
- [ ] Bots can know player's team in advance and build specific counters.
- [ ] Can run tournaments (user vs. bots, bot vs. bot) and track results.
- [ ] Can simulate many bot battles headless (no UI) for training.

---

## Non-Goals

- **Online/Multiplayer**: No server infrastructure, no connection management, no latency handling.
- **Competitive format rules**: Focuses on core mechanics; format-specific rules (Smogon bans, VGC restrictions) are out of scope initially.
- **Doubles battles** (for now): Will support 1v1 only initially; doubles can be added later.
- **Complex UI animations**: Sprites and simple effects only; no elaborate move animations or cinematics.
- **Full official Pokédex/moveset coverage**: Will implement a representative subset; edge cases deferred.

---

## Roadmap (Phases)

**Phase 1: Foundation (Core Battle Engine)**
- Core event system (queue, listener registry, priority resolution).
- Damage calculation (DamageContext, calc_damage).
- Stat changes and Buffs.
- Move types (Physical, Special, Status) and basic move execution.
- Type effectiveness and STAB.
- Basic Pokémon species and move data (representative subset).

**Phase 2: UI Layer for Testing**
- Team builder UI (Pokémon Showdown-inspired): select species, moves, EVs, IVs, nature, ability, item.
- Battle viewer UI: see Pokémon sprites, move selection interface, battle log.
- Team save/load.
- Predefined team templates.
- *Benefit: Visual feedback helps catch engine bugs early; easier to test complex battles manually.*

**Phase 3: Stateful Effects**
- Volatile status system (VolatileStatus, Interactions).
- Non-volatile status (Burn, Poison, etc.) as listeners.
- Weather and terrain as field effects.
- End-of-turn resolution (weather damage, Leech Seed, status ticks, faint checks).
- Extensive move/ability coverage (~100+ moves, ~20+ abilities).

**Phase 4: Abilities & Items**
- Ability base class and listener integration.
- Core abilities (Flash Fire, Intimidate, Regenerator, etc.).
- Item base class and holder logic.
- Critical abilities/items that affect core mechanics.

**Phase 5: Bot System & Training**
- Bot abstraction (interface for team creation and move selection).
- Random bot (random team generation, random move selection).
- Heuristic bot (team counter-building, smart move selection).
- Bot team generation (Pokémon Showdown-inspired with legal movesets).
- Bot learning: Analyze battle results → adjust team composition and move priorities.
- Adversarial mode: Bots know player team in advance and build counters.
- Batch simulation (headless, high-speed battles for training).
- Tournament orchestration (bracket management, result tracking).

**Phase 6: Polish, Optimization & Testing**
- Performance optimization (target 1000+ battles/sec).
- Comprehensive test suite (damage, stat changes, volatile interactions, turn flow, team legality).
- Battle replay/serialization.
- Documentation and examples.
- UI refinement (performance, UX).

**Future (Post-Launch):**
- Doubles battle support.
- Expanded move/ability/item coverage.
- Advanced bot training (reinforcement learning, evolution strategies).
- Competitive format rules (Smogon bans, VGC restrictions).

---

## Principles

1. **Event-driven first**: When in doubt, model it as an event, not a special case.
2. **Correctness + speed + readability**: In that priority order. A correct, fast engine that's readable beats everything else. Optimize only when profiling shows bottlenecks.
3. **Determinism by design**: Randomness is explicit and seeded; same input = same output.
4. **Listeners, not branches**: Abilities/moves/items are listeners that react to events, not special logic branches.
5. **Data-driven config**: Pokémon stats, move data, abilities should be externalized (JSON/YAML), not hardcoded.
6. **Performance-aware design**: Favor efficient data structures (avoid unnecessary copying, allocations, listener dispatch). Target 1000+ battles/sec from the start; don't defer optimization to the end.
