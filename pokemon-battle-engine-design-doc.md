# Pokemon Battle Engine — Technical Design Doc

*Restructured from raw design notes. Fields/behavior marked **(proposed)** are inferred scaffolding, not explicitly in the original notes — flag these for discussion.*

---

## 1. Design Philosophy

The battle system is **turn-based**, which means the engine should be built to be **event-driven**.

- User decisions (move selection, switching, etc.) create **triggers**.
- **Listeners** (abilities, moves, items, field conditions) wait on those triggers and resolve into new **events**.
- A Battle, at its core, is just a large set of listeners resolving events that are a consequence of either field conditions or user decisions (e.g. chip damage vs. move damage).

The engine's job is to let any part of the battle — a move, an ability, an item, the field itself — create events, and then resolve all of them in the correct order.

---

## 2. Static Data Model

These classes describe a Pokémon or Move as a *definition* — independent of any specific battle.

### 2.1 `BaseStats`

Base stats are wrapped in a single dataclass for clarity and batch operations. All seven stats are always present.

```python
@dataclass
class BaseStats:
    hp: int
    atk: int
    def_: int  # avoid keyword collision
    spa: int
    spd: int
    spe: int
    eva: int
```

Grouping these together makes serialization, initialization, and bulk operations (e.g., copying base stats) cleaner than loose fields.

### 2.2 Stat Calculation Functions

**Note:** These are implementation details, not part of the type system. They belong in a `utils` module and are called at initialization time to fold EVs/IVs into the battle stat.

```python
def calc_hp(base: int, iv: int, ev: int, level: int) -> int:
    return int(((2 * base + iv + ev // 4) * level) / 100) + level + 10

def calc_stat(base: int, iv: int, ev: int, level: int, stat_name: str, nature: str) -> int:
    stat = int(((2 * base + iv + ev // 4) * level) / 100) + 5
    nature_info = NATURE_DB[nature]
    
    if stat_name == nature_info["increased_stat"]:
        stat = int(stat * 1.1)
    elif stat_name == nature_info["decreased_stat"]:
        stat = int(stat * 0.9)
    
    return stat
```

HP and non-HP stats have different formulas. Nature applies a ±10% multiplier. These functions produce the `raw_value` that gets stored in a `BattleStat`.

### 2.4 `Pokemon`

```python
@dataclass
class Pokemon:
    base_stats: BaseStats
    abilities: list[Ability]
    learnable_moves: list[Move]
    available_natures: list[Nature]
    primary_type: Type
    secondary_type: Type
    tertiary_type: Type | None = None
```

### 2.5 `Move` (base class)

```python
@dataclass
class Move(ABC):
    move_type: Type
    accuracy: int
    pp: int
    max_pp: int
    target: TargetType
    category: MoveCategory   # Biting, Punching, Slashing (different from Physical/Special/Status)
    priority: int            # range (-7, +7)
    crit_chance: int         # range (-6, +6)
```

Note: `category` refers to move mechanic (Biting, Punching, Slashing) — distinct from the Physical/Special/Status classification below. Keep these concepts visually distinct in code to avoid conflation.

### 2.7 Move Subclasses

Subclasses exist to enable type-based dispatch for listeners. An ability like Infiltrator reacts specifically to damaging moves; the subclass distinction makes this check clean (`isinstance(move, PhysicalMove)` or `isinstance(move, SpecialMove)`).

```python
@dataclass
class PhysicalMove(Move):
    power: int
    contact: bool
    attack_stat: StatName    # e.g., "atk"
    defense_stat: StatName   # e.g., "def"

@dataclass
class SpecialMove(Move):
    power: int
    contact: bool
    attack_stat: StatName    # e.g., "spa"
    defense_stat: StatName   # e.g., "spd"

@dataclass
class StatusMove(Move):
    pass  # no power or contact — effects defined entirely by listeners/events
```

### 2.8 `FieldEffect` (shared base)

Both `Buffs` and `VolatileStatus` share one trait: they only exist while a Pokémon is active on the field, and are wiped entirely on switch-out. Beyond that lifecycle, they're fairly different beasts — `Buffs` is a fixed set of numeric multiplier stacks, while `VolatileStatus` needs to model a much wider variety of interactions. So they share a thin common base rather than deep shared behavior.

```
class FieldEffect:
    """
    Common base for Buffs and VolatileStatus.
    Cleared entirely when the owning Pokemon switches out.
    """
    pass
```

### 2.9 `Buffs` (stat stages)

Stat stage changes (buffs/debuffs) are stored in a centralized `Buffs` object on `BattlePokemon`. This allows for bulk operations (reset all on switch-out, query all at once, etc.). Each stage is always a **pure multiplier** and nothing else — effects like weather are applied at event resolution time, not stored here.

```python
enum StatName:
    ATK, DEF, SPA, SPD, SPE, EVA, ACC, CRIT

@dataclass
class Buffs(FieldEffect):
    atk: int = 0
    def_: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0
    eva: int = 0
    acc: int = 0
    crit_ratio: int = 0
    # all values clamped to range (-6, +6)

    def get_multiplier(self, stat: StatName) -> float:
        stage = getattr(self, stat.value)
        if stage >= 0:
            return (2 + stage) / 2
        else:
            return 2 / (2 - stage)
        # +1 -> (2+1)/2 = 1.5x
        # -1 -> 2/(2-(-1)) = 2/3 = 0.67x
```

All fields are clamped to the range (-6, +6).

### 2.10 `VolatileStatus`

Volatile statuses are condition effects that exist only while a Pokémon is active in battle, and are wiped entirely on switch-out. They have rich, varied behaviors — some disable moves, others inflict stat drops, accuracy checks, or redirect incoming moves. Each `VolatileStatus` holds a list of `Interaction`s describing what it does.

A Pokémon can have **multiple volatile statuses simultaneously** (e.g., both Leech Seed and Substitute), but only **one non-volatile status** (Poison, Burn, Paralysis, Sleep, Freeze).

```python
enum InteractionScope:
    SELF       # affects the afflicted Pokémon's own actions/move choices
    INCOMING   # affects moves or effects directed at the afflicted Pokémon

enum InteractionType:
    DISABLE_MOVE_CATEGORY
    DISABLE_MOVE
    STAT_DROP
    ACCURACY_CHECK
    INFLICT_STATUS
    REDIRECT_INCOMING_MOVES
    # extend as new effects are designed

@dataclass
class Interaction:
    interaction_type: InteractionType
    scope: InteractionScope
    target: MoveCategory | Move | StatName | None
    # e.g., Taunt -> target = MoveCategory.STATUS
    # e.g., Disable -> target = <specific Move instance>

@dataclass
class VolatileStatus(FieldEffect):
    name: str
    duration: int   # concrete turn count; any randomness is rolled once at creation
    interactions: list[Interaction]
```

**Example — Taunt:**

```python
taunt = VolatileStatus(
    name="Taunt",
    duration=random.randint(3, 6),
    interactions=[
        Interaction(
            interaction_type=InteractionType.DISABLE_MOVE_CATEGORY,
            scope=InteractionScope.SELF,
            target=MoveCategory.STATUS,
        )
    ],
)
```

Behavior: Taunt disables Status moves for the afflicted Pokémon. This is enforced at two points:
1. Move selection: Status moves are filtered out of the user's legal move choices.
2. Move execution: If a Status move is forced through another mechanism, it fails on execution.

---

## 3. Battle-Time Model

These represent a Pokémon *as it exists inside a specific battle instance* — built on top of the static model.

### 3.1 `BattleStat`

A `BattleStat` is a simple value holder for a single battle stat (e.g., Speed, Attack). It stores the raw calculated value and the current stage (from Buffs). It does **not** store environmental modifiers like weather or terrain — those are applied at event resolution time.

```python
@dataclass
class BattleStat:
    raw_value: int  # calculated from base_stats + EVs/IVs/level/nature
    stage: int = 0  # buff/debuff from Buffs; range (-6, +6)
    
    def value_with_buffs(self, buffs: Buffs, stat_name: StatName) -> int:
        """Apply buff stage multiplier."""
        multiplier = buffs.get_multiplier(stat_name)
        return int(self.raw_value * multiplier)
```

Note: Weather/terrain modifiers are **not** stored here. They are applied contextually during event resolution (e.g., when computing damage, when resolving a move, etc.).

### 3.2 `BattlePokemon`

```python
@dataclass
class BattlePokemon:
    pokemon: Pokemon
    
    current_hp: int
    max_hp: int
    
    stats: dict[StatName, BattleStat]
    buffs: Buffs
    
    ability: Ability
    moveset: list[Move]  # always 4 moves
    
    non_volatile_status: Optional[str] = None  # "burn", "poison", etc. (only one)
    volatile_statuses: list[VolatileStatus] = field(default_factory=list)  # multiple allowed
    
    def get_stat(self, stat_name: StatName, buffs: Optional[Buffs] = None) -> int:
        """Get the effective stat value, applying buffs if provided."""
        buffs = buffs or self.buffs
        return self.stats[stat_name].value_with_buffs(buffs, stat_name)
```

EVs/IVs are baked in at `Pokemon` creation time and folded into each `BattleStat.raw_value` — they don't live on `BattlePokemon`.

### 3.3 Pokemon Creation

EVs and IVs are provided at `Pokemon` creation time. The stat calculation functions (§2.2) use these to compute raw stat values, which are then stored in `BattleStat.raw_value` when the Pokémon enters a battle.

```python
@dataclass
class Pokemon:
    # ... existing fields ...
    evs: dict[StatName, int]  # effort values
    ivs: dict[StatName, int]  # individual values
```

---

## 4. Engine Architecture: Events, Listeners, Triggers

### 4.1 `DamageContext`

When a damaging move is resolved, damage calculation involves many factors (STAB, type effectiveness, crit, buffs, weather, terrain, etc.). `DamageContext` isolates this calculation into a single deterministic object, making it testable and clear.

```python
@dataclass
class DamageContext:
    attacker: BattlePokemon
    defender: BattlePokemon
    move: PhysicalMove | SpecialMove
    level: int
    
    stab: float = 1.0                # 1.5 if move type matches Pokémon type(s)
    type_effectiveness: float = 1.0  # effectiveness of move type vs. defender's types
    weather_modifier: float = 1.0    # applied at event resolution
    terrain_modifier: float = 1.0    # applied at event resolution
    
    critical: bool = False
    damage_modifiers: list[float] = field(default_factory=list)  # abilities, items, etc.

def calc_damage(ctx: DamageContext) -> int:
    """Calculate final damage for a move using the context."""
    power = ctx.move.power
    attack_stat = ctx.attacker.get_stat(ctx.move.attack_stat, ctx.attacker.buffs)
    defense_stat = ctx.defender.get_stat(ctx.move.defense_stat, ctx.defender.buffs)
    
    damage = (((2 * ctx.level / 5) + 2) * power * attack_stat / defense_stat) / 50 + 2
    
    damage *= ctx.stab
    damage *= ctx.type_effectiveness
    damage *= ctx.weather_modifier
    damage *= ctx.terrain_modifier
    
    if ctx.critical:
        damage *= 1.5
    
    for modifier in ctx.damage_modifiers:
        damage *= modifier
    
    damage *= random.uniform(0.85, 1.0)  # damage variance
    
    return max(1, int(damage))
```

When a damaging move fires, the calling code creates a `DamageContext`, calls `calc_damage()`, and emits a `DamageEvent` with the result. Weather/terrain modifiers are computed from the current battle state at event resolution time, not pre-stored.

### 4.3 `Event`

```python
@dataclass
class Event(ABC):
    """Base class for all events. Subclasses define specific event types."""
    priority: int  # primary sort key (higher priority resolves first)
    speed_source: BattlePokemon | None = None  # used to break ties
```

`speed_source` is a live reference to a Pokémon, not a snapshot. If that Pokémon's speed changes mid-turn (via a buff), the event's tie-breaking order reflects it immediately.

### 4.5 Event Taxonomy

- **Active** — discrete occurrences: `DamageEvent`, `StatChangeEvent`, `TurnStartEvent`, `TurnEndEvent`, `SwitchEvent`, `MoveStartEvent`.
- **MetaEvent** — events that trigger listeners to validate or correct other events (e.g., a move is selected but is disabled by Taunt; a MetaEvent is emitted to filter the move selection).

### 4.6 Listeners

Listeners = abilities, moves, items, field conditions.

A listener subscribes to one or more event types. When an event is resolved, all listeners for that event type are invoked. They may emit new events in response (which are queued and resolved later).

Example: **Flash Fire** ability is a pure listener. It listens for `DamageEvent` from a Fire-type move. When triggered, it emits a `StatChangeEvent` (boost Fire-type moves).

### 4.7 Trigger / Resolution Model

- Resolving one event can spawn new events (e.g., a `StatChangeEvent` for a stat drop may spawn a `DamageEvent` if the drop triggers Chip Damage-style effects).
- Volatile statuses are listeners. A `VolatileStatus` with `STAT_DROP` interaction listens to certain triggers and emits a `StatChangeEvent`.
- End-of-turn effects (Leech Seed, weather damage, status ticks) are triggered by `TurnEndEvent`.

---

## 5. Turn Resolution Flow

1. **Game receives inputs** from all players (move selections, switches).
2. **Inputs create initial events** (SwitchEvent, MoveStartEvent, etc.).
3. **Events are queued** and **resolved in order** (sorted by priority, then speed).
   - Each event is dequeued.
   - Listeners for that event type are invoked.
   - New events emitted by listeners are appended to the queue.
4. **Once the queue is empty**, `TurnEndEvent` fires, triggering end-of-turn effects (weather damage, Leech Seed, status ticks, faint checks).
5. **Input unlocks** for the next turn.
6. Repeat.

Example sequence:
```
User inputs: A uses Tackle, B uses Growl
↓
[MoveStartEvent(A, Tackle), MoveStartEvent(B, Growl)]
↓
MoveStartEvent(A, Tackle) resolves
  → Listeners fire (priority checks, Prankster, etc.)
  → DamageContext created, calc_damage() called
  → DamageEvent(target=B, amount=42) emitted
↓
MoveStartEvent(B, Growl) resolves
  → StatChangeEvent(target=A, stat=ATK, stage=-1) emitted
↓
DamageEvent(B, 42) resolves
  → Listeners fire (abilities like Regenerator, on-hit triggers)
  → HP updated
↓
StatChangeEvent(A, ATK, -1) resolves
  → Buffs updated
  → Listeners fire (stat drop interactions)
↓
Queue empty → TurnEndEvent fires
  → Weather damage, Leech Seed ticks, burn damage, etc.
  → Faint checks and switch-in logic
```

---

## 6. Worked Example: Pokémon A vs. Pokémon B

Setup: A and B are both on the field. A is faster than B.
Selected moves: `A → Tackle`, `B → Growl`.

Event queue resolution:
1. `MoveStartEvent(A, Tackle, B)` — priority 0, speed = A's speed
   - Listeners fire (Prankster, priority checks, etc.)
   - Create DamageContext(attacker=A, defender=B, move=Tackle, stab=1.5, type_eff=1.0, ...)
   - calc_damage(ctx) → 42 damage
   - Emit `DamageEvent(target=B, amount=42)`
2. `MoveStartEvent(B, Growl, A)` — priority 0, speed = B's speed (lower than A)
   - Listeners fire
   - Emit `StatChangeEvent(target=A, stat=ATK, stage=-1)`
3. `DamageEvent(B, 42)` — resolved in event order
   - B's HP decreases by 42
   - Listeners fire (Regenerator, on-damage abilities, etc.)
4. `StatChangeEvent(A, ATK, -1)` — resolved in event order
   - A's Buffs.atk decreases by 1
   - Listeners fire (interaction checks, etc.)
5. Queue empty → `TurnEndEvent` fires
   - Weather listeners (Sandstorm, Hail damage)
   - Entry hazard listeners (Stealth Rock)
   - Faint checks
   - Switch-in processing

---

## 7. Design Decisions Log

Resolutions to earlier open questions, kept here for traceability:

- **BaseStats as a wrapper:** All base stats grouped in a single dataclass for cleaner serialization, initialization, and batch operations.
- **BattleStat separated from Buffs:** BattleStat stores only `raw_value` and `stage` from Buffs. Weather/terrain modifiers are applied at event resolution time (DamageContext), not stored on the stat. This keeps raw stats pure and modifiers contextual.
- **Multiple volatile statuses:** A Pokémon can have multiple VolatileStatus objects simultaneously, but only one non-volatile status (Poison, Burn, etc.).
- **Move subclasses (Physical/Special/Status):** Enable type-based dispatch for listeners. Abilities check `isinstance(move, PhysicalMove)` instead of string branching.
- **VolatileStatus interactions:** Modeled as a class holding `Interaction` objects, not a flat enum — supports the variety of effects (disabling moves, stat drops, accuracy checks, redirecting moves, etc.).
- **DamageContext isolation:** Damage calculation is a pure function over a context object, making it testable and deterministic. Weather/terrain modifiers are computed from battle state at event resolution time.
- **Event queue model:** Inputs create events; listeners may spawn new events; all events resolve in priority + speed order. This replaces procedural branching with a declarative, composable system.

## 8. Deferred / Future Work

- **Event queue and listener registry:** Core plumbing for the event-driven system. On the roadmap but not yet designed in detail. Will include: priority-based event resolution, listener registration/dispatch, and integration with battle flow (§5).
- **Ability base class:** Abilities are listeners but don't yet have a formal base class. Design needed: how to register abilities, what methods they expose, how they hook into listener dispatch.
- **Item base class:** Items are listed as listeners alongside abilities and moves, and likely warrant their own base class. Defer until core event/listener engine is stable.
- **Non-volatile status effects:** Status conditions (Burn, Poison, Sleep, etc.) need modeling as listeners or events. Currently just a string field. Defer until volatile status system is tested.
