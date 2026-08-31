# Event Param Vocabulary

Shared across `move-editor`, `ability-editor`, and `status-editor`. Event
params are free-form `{key, val}` pairs — nothing enforces this list — but
reusing the same key for the same meaning is what keeps effects readable
and comparable across moves/abilities/statuses instead of every entry
inventing its own synonyms. Check here before adding a new key; extend this
file when you genuinely need one that isn't here yet.

`val` is always a string. Numbers, fractions, percentages, and dice all get
written as human-readable text ("1/16 max HP", "25%", "random 1-3") rather
than parsed into a typed shape — this is a design/notes tool, not the
runtime engine, so it optimizes for a person reading it correctly over a
program parsing it automatically.

## Amounts

| key | meaning | example `val` |
|---|---|---|
| `damage` | HP loss dealt by this event | `7% max HP`, `120 power Psychic, calculated at resolution`, `toxic_counter × 7% max HP` |
| `heal` | HP restored by this event | `7% max HP`, `50% of caster max HP, snapshotted when Wish was used` |

Percentage-based DoT/HoT is always written as a whole-percent value, rounded
**up** — never as a fraction. `1/16 max HP` → `7% max HP` (6.25 rounds up),
`1/8 max HP` → `13% max HP` (12.5 rounds up). A counter-scaled amount keeps
the rounded per-step unit and multiplies it: Toxic is `toxic_counter × 7%
max HP`, not `toxic_counter/16 max HP`. Power-based move damage (Future
Sight's `120 power Psychic`) isn't a percentage and is unaffected by this
rule — it stays as written.

## Probability / gating

`chance` is a **structured field on the event itself** — `{target,
priority, chance, params}` — not a loose param, with its own input in the
Create/Edit Event modal (all three editors) and its own badge on the event
card. Leave it blank/omit it for "always happens." This replaced an earlier
free-form `chance`/`effect` param pair; Paralysis and Freeze were migrated
off that shape onto this one.

| field/key | meaning | example `val` |
|---|---|---|
| `chance` *(event field, not a param)* | odds this event fires at all | `"25"`, `"20"` (plain number, % implied) |
| `effect` *(param)* | what happens when the event fires — pairs with `chance`, or stands alone for an unconditional event | `fully prevents the move this turn (full paralysis)` |
| `fail_if` *(param)* | a condition that no-ops an otherwise-certain event | `slot is empty`, `holder is Grass-type` |
| `only_if` *(param)* | restricts *who* the event applies to, as opposed to whether it happens at all | `grounded` |

`chance` (event field) + `effect` (param) is the standard "N% chance of
X" shape — Paralysis, the Freeze thaw roll, and Infatuation all use it
verbatim. `fail_if` describes a precondition on an otherwise-certain event
instead — don't reach for `chance: "100"` where `fail_if` is what's
actually meant.

## Stateful counters

For anything that persists and changes turn over turn (Toxic's climbing
damage, Sleep's countdown) rather than a plain per-turn constant.

| key | meaning | example `val` |
|---|---|---|
| `counter` | names the counter this event reads/writes | `toxic_counter`, `sleep_turns` |
| `set` | initializes the named counter (paired with `counter`) | `1`, `random 1-3` |
| `increment` | the named counter goes up by 1 this tick | `toxic_counter` |
| `decrement` | the named counter goes down by 1 this tick | `sleep_turns` |

`set` belongs in an `on_apply` block; `increment`/`decrement` belong
wherever the counter actually ticks (`on_turn_end`, `on_turn_start`, ...).

## Targeting / binding

For effects whose real target is a field **slot**, not the specific
Pokémon that's there right now — the distinction matters the moment
anyone switches.

| key | meaning | example `val` |
|---|---|---|
| `bind_target` | the event follows this slot, not a Pokémon identity | `seeder_slot` (Leech Seed), `caster_slot` (Wish), `target_slot` (Future Sight/Doom Desire) |

Always pair `bind_target` with a `fail_if: slot is empty` unless the empty
case is truly impossible.

## Switch interaction

| key | meaning | example `val` |
|---|---|---|
| `block_switch` | prevents the holder's own voluntary switch | `true` |
| `block_forced_switch` | grants immunity to being switched out by something else (Roar, Whirlwind, Dragon Tail, Red Card, ...) | `true` |

These are independent — a status can block one without the other.

## Documentation-only (no runtime meaning)

| key | meaning | example `val` |
|---|---|---|
| `tag` | a standing property applied to the holder, for other effects to reference later — not itself an action | `grounded` |
| `note` | free-text caveat/explanation for whoever reads this later; never consumed by anything | `checked once per turn, before the move-block check below` |

## Condition-level params

These live on the *condition*, not on an event — see `block.condition.params`.

| key | meaning | example `val` | used by condition type |
|---|---|---|---|
| `turns` | how many turns until a `delayed_turn` block's events resolve, OR how many turns a `duration_turns` block's status lasts | `2`, `3`, `random 1-3` | `delayed_turn`, `duration_turns` |

Both `delayed_turn` and `duration_turns` have first-class UI support (a
turn-count input, both at block-creation and inline on existing blocks) in
all three editors — see `move-editor/app.js`, `ability-editor/app.js`,
`status-editor/app.js`. The field is text, not a number picker, so it
accepts a range like `random 1-3` (Sleep) as well as a fixed count.

**`delayed_turn` vs `duration_turns`** — same countdown mechanism, opposite
meaning:
- `delayed_turn`: nothing happens until the counter runs out, *then* the
  block's events fire once as a payoff. Wish, Future Sight, Doom Desire.
- `duration_turns`: the effect is active for the whole countdown — usually
  paired with a separate block (`on_move_block_check`, `on_turn_end`, ...)
  that does the actual work each turn it's active — and the
  `duration_turns` block's own events fire once, when the counter runs
  out, to *end* the effect (cure/expire), not to deliver a payoff. Sleep,
  Taunt, Encore, Disable.

## Move-editor conventions established during the audit-and-fix pass

A 10-subagent Haiku audit (comparing every saved move's `effects` against
its real in-game description) turned up ~90 findings; 85 were real, 5 were
false positives from taking PokeAPI's "has a chance to X" boilerplate
literally when the real move guarantees that effect at 100% (Bulldoze,
Chatter, Spirit Break, Stoked Sparksurfer, Struggle Bug) — verify
subagent-suggested chance corrections against known game data before
applying them, don't trust the phrasing alone. Fixing the real 85 pulled
in move-editor's existing conventions (`stat`/`stages`/`chance`,
`status`/`chance`, `volatile`/`chance`, `recoil_fraction`,
`drain_fraction`, `heal_basis`/`amount`, `weather`/`terrain`+`duration`,
`field_effect`) plus new ones documented here for the first time:

| key | meaning | example |
|---|---|---|
| `recharge` | the user cannot act next turn | Hyper Beam, Rock Wrecker |
| `charge_turn` | the move takes a full turn to charge before attacking | Meteor Beam |
| `self_faint` | the user faints regardless of whether the move hits | Self-Destruct |
| `ohko` | bypasses normal damage calc; target faints if the hit lands | Sheer Cold |
| `steal_item` | takes the target's held item if the user holds none | Thief, Covet |
| `remove_item` | destroys the target's item rather than taking it | Knock Off |
| `clear_hazards` | removes entry hazards from the given side | Rapid Spin, Defog |
| `clear_terrain` | ends whatever terrain is active | Ice Spinner, Steel Roller |
| `clear_screens` | removes Reflect/Light Screen/Aurora Veil/Safeguard from the given side | Defog, Psychic Fangs |
| `remove_type` | strips a type from the user | Burn-Up (removes Fire) |
| `steal_stat_boosts` | copies the target's positive stat stages onto the user, then clears them from the target | Spectral Thief |
| `reduce_pp` | cuts the target's last-used move's PP by a fixed amount | Eerie Spell |
| `damage_basis` (+ `amount`) | damage computed from something other than power — e.g. `target_current_hp` | Super Fang (mirrors the existing `heal_basis`/`amount` pair) |
| `damage_basis: user_level` | fixed damage equal to the user's level, `amount: "1"` (100% of level) | Seismic Toss, Night Shade |
| `damage_basis: fixed` (+ `amount` as a flat HP number, not a fraction) | always deals exactly this many HP, unaffected by stats/type effectiveness/STAB/crits | Dragon Rage (`amount: "40"`), Sonic Boom (`amount: "20"`) |
| `heal_basis: target_attack_stat` | heals by a raw stat value read off the target, not a % of HP | Strength Sap |
| `on_contact` (new use) | fires on contact made DURING a charging move's wind-up, before the attack itself resolves | Beak Blast |
| `on_miss` (new condition type) | fires when the move fails to hit its target | Supercell Slam's self-damage |

`tri-attack` also got corrected from three independent per-status events
down to one `status: random one of burn/freeze/paralysis` event at a
single 20% chance — the real mechanic is one roll that then picks among
three outcomes, not three separate rolls (same "one probability, several
possible outcomes" shape as Effect Spore in ability-editor).

**`dire-claw` had the identical bug**, caught after the fact by the user
rather than the audit — three independent 30% events (poison/paralysis/
sleep) instead of one 30% roll picking among the three. A repo-wide grep
for "multiple `status` events on one block, same chance, different
values" turned up only these two, so the pattern is now closed out — but
it's worth grepping for again after any future bulk data import, since
neither the audit's category list nor a human skim caught Dire Claw the
first time.

**`on_miss` also covers Jump Kick and High Jump Kick's crash damage now**,
not just Supercell Slam — all three "deals damage to the user if the move
misses" moves in the games use the identical shape (`damage: 50% max HP`
on a self event under an `on_miss` block).

**A follow-up sweep of the whole move set** (grepping for split-status/
split-volatile patterns and for "miss"/"crash" in every move's official
text) confirmed Dire Claw and Tri Attack were the only two split-status
cases, but turned up one more real `on_miss` gap: **Axe Kick** ("If it
misses, the user takes damage instead") — added, same shape as the other
three.

**Project convention, settled**: this project always targets modern-gen
mechanics over legacy ones when the two diverge. Applied retroactively to
Jump Kick/High Jump Kick/Axe Kick's crash damage (flat `50% max HP`,
Gen 5+, not the older would-be-damage calculation the fetched PokeAPI text
actually describes) — the hedging notes on those three are now resolved,
not open questions. Also caught a real percentage error while verifying
against Bulbapedia directly: **Dire Claw's real chance is 50% total**
(Gen 9 mainline; ~16.67% per status), not the 30% originally guessed by
pattern-matching against Tri Attack's percentage — verified via Bulbapedia
rather than assumed, since Tri Attack's 20% doesn't transfer to a
different move just because the shape (one roll, several possible
outcomes) is the same. A same-named spin-off title (Pokémon Champions)
uses 30% instead — not used here, per the modern-mainline-always rule.

## Verification pass against Showdown's actual source

Grepped every self-flagged hedge ("roughly", "approximate", "commonly
cited", etc.) plus every structured `chance` value across ability-editor,
and cross-checked the core status percentages, against Smogon's own
`pokemon-showdown` repo (`data/abilities.ts`, `data/conditions.ts` — `gh`/
`curl` reach these directly; `WebFetch` truncates the full files, so pull
them locally and grep instead). Real findings:

- **Effect Spore is NOT an equal three-way split**, unlike Dire Claw/Tri
  Attack — it's three separate probability bands in one 100-roll (sleep
  11%, paralysis 10%, poison 9%, summing to 30%). Rebuilt as three
  distinct chance-gated events instead of one "equal chance" event —
  don't assume every "one roll, several statuses" ability shares Dire
  Claw's uniform-split shape.
- **Quick Draw excludes status moves** (`move.category !== "Status"`) —
  missing `fail_if` added.
- **Harvest is guaranteed (100%), not 50%, during harsh sunlight** — the
  50% only applies outside sun. Restructured into two mutually-exclusive
  `fail_if`-gated events rather than leaving a note that contradicted the
  stored `chance` value.
- **Supreme Overlord's numbers were right (+10% per fainted ally, exactly
  linear, capped at 5) but the framing was wrong** — it's a move-power
  multiplier at damage-calc time (`onBasePower`), not a literal Attack/Sp.
  Atk stat boost, even though the net effect on damage looks similar.
- **Toxic Chain's 30% was correct**, but it's also blocked by Shield Dust
  and a held Covert Cloak despite not technically being a move's own
  secondary effect — `fail_if` added.
- **Bound's duration was wrong**: real value is `random(5,7)` = 5-6 turns
  (or fixed 8 with the trapper's Grip Claw), not the "4-5" originally
  guessed. Also missing entirely: **Binding Band** on the trapper changes
  the per-turn damage divisor from 8 to 6 (13% → 17%) — a whole item
  interaction that had no representation at all.
- **Confusion's stated "1-4 turns" turned out to be correct** after
  tracing Showdown's actual decrement-before-check logic — the raw
  `random(2,6)` call looks like a 2-5 range at first glance, but the
  number of turns actually at risk of a self-hit works out to 1-4 once you
  account for the final decrement-to-zero turn resolving with no roll.
  Same off-by-one shape makes Sleep's `random(2,5)` come out to the
  commonly-known "1-3 turns" instead of looking like 2-4. When verifying
  against Showdown source, trace the surrounding control flow, not just
  the bare `random()`/`randomChance()` call.
- **Axe Kick's confusion uses a longer minimum duration** (3 rather than
  2, i.e. 2-4 at-risk turns instead of the usual 1-4) — folded in as a
  `note` on its `volatile: confusion` event. A per-source override baked
  into Showdown's confusion condition itself (`sourceEffect.id ===
  'axekick'`), not something the move's own description text or data
  would ever surface on its own — only found by reading the status
  condition's source, not the move's.

Paralysis (25%), Freeze thaw (20%), and the rest of the plain structured
`chance` values (Static/Flame Body/Poison Point/Cute Charm/Cursed Body at
30%, Stench at 10%, Shed Skin at 33%, Healer at 30%) all checked out
exactly as saved — no changes needed.

## Verification pass: item interaction + form-change gimmicks

Same Showdown-source-of-truth treatment applied to both deferred families
once built. Real corrections:

**Item interaction:**
- **Pickup** — real requirement is stricter than "any used/Flung item ever"
  — it's specifically an ADJACENT Pokémon's item used up THIS turn, chosen
  at random if multiple qualify.
- **Magician** — missing exclusions: doesn't trigger if the holder used a
  Gem this turn or used Fling (both already consume an item as part of
  the move); with multiple targets hit, only steals from the first
  eligible one in speed order.
- **Sticky Hold** — missing the Sticky Barb exception (that item transfers
  via contact despite Sticky Hold).
- **Cud Chew** — missing the exclusion for being forced to eat via an
  opponent's Bug Bite/Pluck (only the holder's own normal eating counts).
- **Ripen** — the "doubles a Berry's effect" framing undersold two
  distinct real facets: (1) the doubling is specifically for true Berries
  — Berry Juice/Leftovers show an activation message but their heal is
  NOT doubled; (2) a damage-reducing Berry (e.g. Occa Berry) additionally
  halves the *next* hit's damage on top of its own reduction — a genuinely
  separate mechanic from the heal/stat doubling, not just "more doubling."

**Form-change gimmicks:**
- **Battle Bond** — was missing its Attack/Sp. Atk/Speed +1 stat boost
  entirely; only the Water Shuriken buff had been captured.
- **Gulp Missile** — needed the exact numbers: recoil is 25% of the
  *attacker's* max HP (not the holder's), the Gulping/Gorging form split
  is exactly at 50% HP, and it has a semi-invulnerable exception (doesn't
  trigger against a Dig/Fly-ing attacker).
- **Power Construct** — threshold wording tightened: triggers at HP ≤ 50%,
  not merely "below" 50% (the exact-50% case was previously ambiguous).
- **Schooling, Shields Down** — both used `on_hit` as their trigger, which
  is wrong: the real trigger is `on_switch_in` **and** `on_turn_end`
  (continuously re-checked), since the form can revert from any HP loss,
  not just from being hit by a move. Also Schooling's threshold was
  off-by-one: strictly ABOVE 25%, not "25% or higher."
- **Zen Mode** — threshold wording tightened: the real check is inclusive
  (HP ≤ 50%), not "below 50%."
- **Ice Face** — restoration was missing an `on_switch_in` check (entering
  battle while Hail/Snow is already active with a broken ice head);
  previously only fired on a live `on_weather_change`.

**Confirmed correct, no change**: Multitype and RKS System correctly use
`passive` (continuously evaluated, so no discrete-trigger threshold bug is
even possible there); Commander's `on_switch_in` is a reasonable
approximation of its real continuously-re-checked trigger.

The `on_hit`-instead-of-`on_switch_in`+`on_turn_end` mistake on Schooling/
Shields Down is a shape worth remembering generally: **any HP-threshold
form-change should be checked continuously (`passive`, `on_calc_damage`,
or paired `on_switch_in`+`on_turn_end` blocks), never as a one-shot
reaction to a single trigger like `on_hit`** — the threshold has to hold
true at every moment it might matter, not just the instant something else
happened to fire.

## Cross-file reuse: abilities applying statuses

An ability that sets a field/side condition (weather, terrain, hazards)
applies the exact status already defined in `status-editor/statuses/` —
via the same `volatile` key move-editor uses to grant a status, e.g.
`{key: 'volatile', val: 'weather-rain'}`. Don't redefine the weather/
terrain/hazard behavior inside the ability; point at the existing status
and only add a `note` where the ability's version genuinely differs from
what a move/item would do with that same status (see Drizzle/Drought/Sand
Stream/Snow Warning below — indefinite duration instead of the status's
normal `duration_turns` timer).

## Precedent so far

- **Constant DoT**: Burn, Poison, Curse (25% max HP, persists until
  switch-out) — single `on_turn_end` block, `damage`, done.
- **Constant DoT riding on another status**: Nightmare — same shape as
  Curse, but has no lifespan of its own; a `fail_if: holder is not
  currently asleep` ties it to Sleep's duration instead of giving it a
  `duration_turns` block. Use this shape whenever an effect's "expiry" is
  really just another status ending, not a countdown of its own.
- **Entry hazard: stacking layers, `on_switch_in` trigger**: Spikes, Toxic
  Spikes — `on_apply` block increments a `counter` (capped, per `note`) each
  time the hazard is (re)applied; a separate `on_switch_in` block reads that
  counter into the payoff (`damage` scaling with layer count for Spikes;
  `effect` choosing Poison vs. Toxic for Toxic Spikes). No `duration_turns`
  — hazards persist until cleared by something else (Rapid Spin, Defog,
  Court Change), not a timer. Toxic Spikes additionally has a second event
  on the same block for its self-clearing exception (a grounded Poison-type
  switching in removes it outright, distinct from just being immune).
- **Entry hazard: effectiveness-scaled, no layering**: Stealth Rock,
  G-Max Steelsurge — single `on_switch_in` block, `damage` written as a
  effectiveness-multiplier table in the `val` text rather than one fixed
  percentage, since the real amount depends on the switching-in Pokémon's
  type matchup against the hazard's type.
- **Entry hazard: stat drop instead of damage/status**: Sticky Web — same
  `on_switch_in` trigger as the rest, `effect` lowers a stat instead.
- **Single-turn, self-clearing, no countdown needed**: Flinch — one
  `on_move_block_check` block, no `chance`, no `duration_turns`. It's
  consumed automatically at end of turn regardless of outcome and has to
  be re-inflicted fresh each time; don't reach for a 1-turn
  `duration_turns` block where "clears itself, no expiry event to model"
  is what's actually meant.
- **No-duration block gated by `fail_if`, not `chance`**: Torment — same
  shape as Paralysis/Infatuation's `on_move_block_check`, but the gate is
  "is this the same move as last turn," not a probability roll.
- **Shared counter across a whole move family**: Protect —
  `on_move_block_check` is what it does this turn; a *separate* `on_apply`
  block maintains `protect_streak`, a counter name written generically on
  purpose because every protection move (Spiky Shield, King's Shield,
  Baneful Bunker, Burning Bulwark, Silk Trap, Obstruct, Detect, Endure,
  Wide Guard, Quick Guard, Crafty Shield, Mat Block) reads/writes the same
  real counter in the games, not one each. When building any of those
  later, reuse `protect_streak` and Protect's `on_apply` block verbatim —
  only the `on_move_block_check` block's `effect` differs per-move (block
  everything vs. block + poison/burn/lower-stat the attacker on contact,
  etc).
- **Ability-tied "persists until X leaves", no timer**: the primal
  weathers (Heavy Rain, Extremely Harsh Sunlight, Strong Winds) — an
  `on_cure` block whose `effect` names the condition in text ("ends when
  the Pokémon that summoned it leaves the field or faints") rather than a
  `duration_turns` block, since there's no turn count to give one. Heavy
  Rain and Extremely Harsh Sunlight also add an `on_move_block_check`
  block that fails the opposing element's moves outright — a hard block,
  not just the usual weather damage multiplier. Strong Winds skips that
  block entirely since its effect (negating Flying's weaknesses) is a
  damage-calc override, not something that blocks a move.
- **Whole move family sharing one status shape**: the protect-move family
  — Detect (identical to Protect), Spiky Shield, King's Shield, Baneful
  Bunker, Burning Bulwark, Silk Trap, Obstruct all reuse Protect's
  `on_apply` `protect_streak` block verbatim, plus the same
  `on_move_block_check` block ("blocks most incoming moves," same
  `fail_if`); only an added `on_hit_holder` block differs per move — the
  contact-reaction payoff (damage/stat-drop/status), each gated with
  `fail_if: the incoming move does not make contact`. Crafty Shield is the
  one exception in the family: `self_side` instead of `self`, blocks status
  moves only (`fail_if: not a status move`) instead of everything, and has
  no `on_hit_holder` block at all since damaging moves reach it unblocked
  and there's nothing to react to — but it still keeps the shared
  `protect_streak` block, since it decays the same real counter in the
  games. Endure is the other true exception: no `on_move_block_check` at
  all — the incoming move connects normally, deals full damage and every
  secondary effect, and Endure only intervenes on the resulting HP loss
  via `on_hit_holder` (`effect: leaves the holder at 1 HP`, `fail_if: this
  hit would not have been lethal anyway`). It still keeps `protect_streak`.
  Wide Guard (blocks spread moves), Quick Guard (blocks priority
  moves), and Mat Block (blocks damaging moves, status moves unaffected)
  round out the side-wide branch of the family alongside Crafty Shield —
  same `self_side` + single `on_move_block_check` + `fail_if` shape, no
  `on_hit_holder` block, still keep `protect_streak`. None of the
  side-wide guards use `delayed_turn`/`duration_turns` — like Protect
  itself, they're single-turn and self-clearing, not a countdown.
- **"Not self" convention for a buffed ally**: Dragon Cheer, Helping Hand —
  both target an ally, not a foe, but the schema only has `self`/
  `opponent`/etc.; written as `opponent` with a `note` clarifying it just
  means "not self" here, since there's no dedicated "ally" target value.
- **Duplicate-effect statuses kept as separate catalog entries**: Foresight
  and Odor Sleuth are mechanically identical (Miracle Eye is the
  Psychic/Dark counterpart) — each still gets its own file since the games
  treat them as distinct moves/statuses, with a `note` cross-referencing
  the duplicate rather than merging them.
- **No turn count — clears on the user's next action, not a timer**:
  Destiny Bond, Grudge — `on_hit_holder` carries the payoff (`effect`,
  gated by `fail_if: this hit did not cause the holder to faint`), and a
  `note` states the real expiry condition instead of a `duration_turns`
  block, since "until the user acts again" isn't a turn count.
- **One-time turn-order/targeting effect, nothing to expire**: After You,
  Quash, Redirect — a single `on_apply` block is the entire effect; no
  second block is needed since nothing persists past the moment this
  turn's order or targeting is resolved.
- **Reactive, single-turn, no `duration_turns` needed**: Magic Coat,
  Snatch, Powder — same "self-clears automatically, don't reach for a
  1-turn duration_turns block" rule as Flinch, just gated by `fail_if` on
  the incoming move's category instead of blocking outright.
- **Weather/terrain-setting ability, ordinary duration**: Electric/Grassy/
  Misty/Psychic Surge, Sand Spit, Seed Sower — `on_switch_in` (or `on_hit`
  for the reactive pair) just applies the matching status via `volatile`,
  no override needed since these behave exactly like the equivalent move.
- **Weather-setting ability, indefinite duration**: Drizzle, Drought, Sand
  Stream, Snow Warning — same `volatile` application, but with a `note`
  overriding the status's normal `duration_turns` timer, since
  ability-summoned ordinary weather lasts indefinitely instead of 5-8
  turns. Primordial Sea/Desolate Land/Delta Stream need no such note —
  those statuses already encode "persists until the holder leaves" on
  their own `on_cure` block, so the ability just applies them as-is.
- **Field-condition setter + conditional self-buff**: Hadron Engine,
  Orichalcum Pulse — two blocks: `on_switch_in` sets the field condition
  (reusing the shape above), and a separate `passive` block `tag`s a stat
  boost gated with `fail_if` on that same condition still being active.
  The two blocks aren't merged because they're checked at different
  times — one at switch-in, one continuously.
- **Contact-punish ability, reuses an existing status**: Static, Flame
  Body, Poison Point, Effect Spore, Cute Charm, Perish Body — `on_hit` +
  `fail_if: the incoming move does not make contact`, applying
  `status`/`volatile` values that already exist (paralysis, burn, poison,
  a three-way random status, infatuation, perish-song). Perish Body is the
  interesting one: it fires two events off the same block, granting
  perish-song to both self and the attacker at once.
- **Contact-punish ability, no existing status to reuse**: Rough Skin,
  Iron Barbs (`damage`), Gooey, Tangling Hair (`effect`: stat drop),
  Pickpocket (`effect`: item theft) — same `on_hit` + `fail_if` shape, but
  the payoff is a plain event rather than a named status.
- **Contact-punish on a different trigger point**: Aftermath uses
  `on_faint`, not `on_hit` — it only matters when the holder is actually
  KO'd, gated by `fail_if: the hit that caused the faint was not a contact
  move`. Don't reach for `on_hit` + a fail_if about fainting; if the real
  condition is "this Pokémon just fainted," that's `on_faint` directly.
- **Ability-change abilities use `on_ability_change`, not `on_hit`**:
  Wandering Spirit, Mummy — the trigger is specifically about an ability
  changing, which contact merely causes; `on_hit` would describe the wrong
  thing even though contact is how it's provoked in both cases.
- **Single-status immunity**: Insomnia, Limber, Water Veil, Magma Armor,
  Immunity, Own Tempo — one `on_status_inflict` block, `effect: blocks X`,
  `fail_if: not X`. Vital Spirit is the same block as Insomnia with a
  `note` pointing at the duplicate rather than re-deriving it.
- **Side-wide status immunity**: Sweet Veil, Pastel Veil, Flower Veil —
  same shape, `self_side` instead of `self`, usually with an extra
  `fail_if` narrowing *which* allies it covers (Flower Veil: Grass-type
  only). Pastel Veil adds a second `on_switch_in` block for its
  switch-in cure, which the short PokeAPI description doesn't mention but
  the real games do — verified from known behavior, flagged with a `note`
  rather than silently added.
- **Conditional status immunity**: Leaf Guard — same block shape, but
  `fail_if` gates on a field condition (harsh sunlight) rather than the
  incoming status type.
- **Blanket status immunity + unrelated damage-calc perk**: Purifying Salt
  — two unrelated blocks on one ability: `on_status_inflict` (blocks
  everything) and a separate `on_calc_damage` `tag` (halves Ghost damage).
  Don't merge unrelated mechanics onto one block just because they're on
  the same ability.
- **Standing property PLUS the immunity that falls out of it**: Comatose —
  a `passive` block `tag`s "always treated as asleep," and a *separate*
  `on_status_inflict` block blocks everything else, with a `note`
  explaining the immunity is a consequence of the tag, not an independent
  mechanic.
- **Blocks a move's secondary effect, broader than status alone**: Shield
  Dust — `on_hit`, `effect` blocks stat-drop/flinch/status chances alike
  while the move's direct damage/primary effect still lands. Related to
  the status-immunity family but not itself gated on a specific status.
- **Field-wide switch-in stat drop**: Intimidate — `on_switch_in` targeting
  `opponent_side`, `note` clarifying it's a one-time effect hitting every
  currently-active foe, not a persistent side condition (don't confuse
  this with the screens/hazards `self_side`/`opponent_side` blocks, which
  genuinely persist).
- **KO-triggered boost, no dedicated trigger exists**: Moxie, Beast Boost,
  Grim Neigh — `on_deal_damage` + `fail_if: this hit did not knock out the
  target`, since there's no "opponent fainted from this hit" condition
  type. Distinct from Soul-Heart below, which needed an actual new
  condition rather than a fail_if workaround.
- **Custom condition type for "any faint, anywhere"**: Soul-Heart — none
  of `on_deal_damage`/`on_faint`/`on_ally_faint` mean "any Pokémon on
  either side faints, regardless of who caused it," so this uses a
  custom type (`on_any_faint`) via the Add Condition Block modal's
  Custom… option rather than stretching an existing one to fit.
- **HP-threshold-crossing trigger**: Berserk, Anger Shell — `on_hit` +
  `fail_if` describing the crossing (above-half to at-or-below-half), with
  a `note` that it only fires on the crossing turn, not every subsequent
  hit while already below half.
- **Stat-drop-triggered boost**: Competitive, Defiant — `on_stat_change` +
  `fail_if: not a decrease to the holder's own stats`, `note` that this
  includes self-inflicted drops (Overheat, Leaf Storm) and Intimidate, not
  just an opponent's move.
- **Fetched effect text was wrong**: Cotton Down — PokeAPI's `effect`
  string for this one is garbled/mismatched with another ability; written
  from known game mechanics instead, with a `note` flagging the source
  data was unusable rather than silently overriding it.
- **First real use of `on_type_effectiveness`**: the whole absorb/redirect/
  immunity family — Levitate, Well-Baked Body, Volt/Water/Earth Absorb,
  Motor Drive, Sap Sipper, Lightning Rod, Storm Drain, Wonder Guard, Flash
  Fire, Wind Rider all gate an `effect`/`heal` payoff with `fail_if: not
  [type]-type`. Wonder Guard inverts the usual direction — `fail_if` gates
  on the move BEING super-effective, since that's the one case where it
  does nothing.
- **`on_type_effectiveness` stretched to a move flag, not a type**:
  Soundproof, Bulletproof, Overcoat's powder block — `fail_if: not flagged
  as sound/bullet/powder-based` rather than a type check. Flagged with a
  `note` each time since the condition's name implies type, not flag —
  still the closest existing trigger for "check something about the
  incoming move before it lands," so reused rather than inventing a
  sibling condition for just three abilities.
- **Redirect + absorb as two separate blocks**: Lightning Rod, Storm Drain
  — a `passive` block `tag`s the redirect behavior (which happens whether
  or not the move ends up hitting the holder), and a separate
  `on_type_effectiveness` block handles the absorb once it does. Redirect
  itself isn't modeled as its own event since it's a targeting-phase
  effect, not a damage-phase one.
- **Multi-facet ability, one block per unrelated mechanic**: Dry Skin —
  three blocks for three genuinely separate rules (weather chip/heal via
  `on_turn_end`, Water absorb via `on_type_effectiveness`, Fire
  vulnerability via `on_calc_damage`), same "don't merge unrelated
  mechanics" rule as Purifying Salt/Comatose earlier. Overcoat is the same
  shape: weather-damage immunity and powder-move immunity are unrelated
  enough to stay on two blocks.
- **`on_calc_damage` as a pure multiplier, `tag` + `fail_if`**: the whole
  damage-calc family — Multiscale, Solid Rock, Filter, Thick Fat, Ice
  Scales (defensive); Technician, Sniper, Tinted Lens, Analytic, Sheer
  Force, Reckless, Iron Fist, Tough Claws, Strong Jaw, Mega Launcher
  (offensive). Every one of these is a single `on_calc_damage` block, one
  `tag` describing the multiplier in plain text, one `fail_if` gating when
  it applies. No new shape needed once the trigger existed — this is the
  payoff of adding `on_calc_damage` up front instead of improvising it
  mid-batch.
- **Same trigger, both directions, still two blocks**: Punk Rock, Fluffy,
  Water Bubble, Sand Force — damage taken and damage dealt are both
  `on_calc_damage`, but kept as separate blocks per the same "don't merge
  unrelated facets" rule as Dry Skin/Purifying Salt, even though here the
  facets share a trigger type. Water Bubble adds a third, unrelated block
  (`on_status_inflict` blocking Burn) — three genuinely different
  mechanics, three blocks.
- **Ability modifies what an existing status already does, not a new
  status**: Heatproof — instead of a fourth copy of "halves Burn's
  own tick," an `on_turn_end` block with an `effect` that explicitly
  cross-references Burn's own `on_turn_end` `damage` value via a `note`,
  making clear this modifies the status rather than redefining it.
- **`on_priority_check` beyond a flat +1**: Prankster, Gale Wings, Triage
  (raise priority for a move category, `fail_if` on that category), Quick
  Draw (`chance`-gated tie-break within the *same* bracket — not an actual
  priority stage change), Stall/Mycelium Might (the guaranteed-last
  mirror of Quick Draw). The `note` on each spells out explicitly whether
  it changes the priority stage or just the tie-break within one, since
  those look similar in text but aren't the same mechanic.
- **`on_ability_change` for a copy, not just a swap**: Trace — same
  condition type as Wandering Spirit/Mummy, but the trigger here is
  switch-in, not contact. Receiver/Power of Alchemy reuse `on_ally_faint`
  for the same "copy an ability" idea, one trigger point earlier
  established, no new condition needed.
- **`passive` `tag` covering the whole field, not just the holder**:
  Neutralizing Gas — a `tag` describing suppression of every *other*
  Pokémon's ability, not a `fail_if`-gated event, since there's no single
  incoming trigger to gate on — it's just "true, continuously, while
  active."
- **`on_move_used` for type/power conversion**: Protean, Libero, Normalize,
  Aerilate/Pixilate/Refrigerate/Galvanize, Liquid Voice — the type-change
  family use this trigger since the effect has to resolve before the
  move's type is even locked in for damage calc. Note the real per-ability
  multiplier varies (1.3× for most, but Galvanize is 1.2× per its actual
  PokeAPI text) — checked individually rather than assumed uniform.
- **Same status-editor-style duplicate-entry pattern, for abilities**:
  Receiver/Power of Alchemy, Protean/Libero — mechanically identical
  pairs kept as separate files with a `note` cross-referencing the twin,
  same treatment Foresight/Odor Sleuth got in the status batch.
- **`on_stat_change` for blocking/reflecting/warping, not reacting**: Clear
  Body/White Smoke/Full-Metal Body (block all decreases), Hyper Cutter/
  Keen Eye/Big Pecks (block one specific stat), Mirror Armor (reflect
  instead of block), Contrary (invert direction), Simple (double
  magnitude) — same condition type as Competitive/Defiant from family 4,
  but the ability changes what happens to the incoming change instead of
  firing a separate reactive boost.
- **Stat modifiers ignored at calc time, not blocked at apply time**:
  Unaware — deliberately NOT `on_stat_change`, since it doesn't stop
  anyone's stats from changing; it's `on_calc_damage`, ignoring both
  sides' existing stat stages when damage/accuracy gets computed. Don't
  reach for `on_stat_change` just because "stats" are in the name — ask
  whether the change itself is being intercepted, or just its
  consequences.
- **Three unrelated facets, three blocks**: Mind's Eye — accuracy-drop
  immunity (`on_stat_change`), ignoring opposing evasion (`passive`
  `tag`), and Ghost-type immunity bypass (`passive` `tag`, same effect as
  Scrappy) all on one ability, kept separate per the standing "don't merge
  unrelated mechanics" rule.
- **HP-threshold type boost**: Blaze/Torrent/Overgrow/Swarm — same
  `on_calc_damage` `tag`+`fail_if` shape as family 6, gated on the
  holder's own HP fraction instead of the incoming move.
- **Status-conditional stat boost that REPLACES the status's own
  drawback, not stacks with it**: Guts (Attack, replaces Burn's
  Attack-halving), Quick Feet (Speed, replaces Paralysis's Speed cut) —
  the `tag` text says "REPLACES... rather than stacking" explicitly,
  since the naive reading ("+50% Attack while burned") would double-count
  against Burn's own penalty if implemented literally on top of it.
- **Speed boost uses `passive`, not `on_calc_damage`**: Quick Feet — Speed
  isn't consulted during damage calculation, it's read during turn-order
  resolution, so it doesn't belong on the same trigger as a damage
  multiplier even though the `tag` shape looks identical.
- **Inverse of the family — a threshold PENALTY**: Defeatist — same shape,
  `fail_if` just excludes the healthy case instead of the low-HP case.
- **Weather boost + separate upkeep cost**: Solar Power — two blocks, not
  one: `on_calc_damage` for the Sp. Atk boost, `on_turn_end` for the HP
  cost, both gated on the same field condition independently rather than
  bundled into a single block.
- **Field-conditional passive boost, `passive` + `tag` + `fail_if`**:
  Chlorophyll, Swift Swim, Surge-Surfer, Slush Rush (Speed), Sand Veil/
  Snow-Cloak (evasion), Grass Pelt (Defense) — direct reuse of family 1's
  statuses via `fail_if: [status] is not currently active`, same shape as
  Hadron Engine/Orichalcum Pulse's self-buff block from family 1, just
  without the setter half since these abilities only react to a field
  condition rather than also creating one.
- **Field-conditional boost + matching weather-damage immunity**: Sand
  Rush, Sand Veil, Snow Cloak — the boost and the immunity are two
  unrelated triggers (`passive`/`tag` vs `on_turn_end`/`effect`), so two
  blocks each, not one. Slush Rush pointedly does NOT get the immunity
  block — checked the real mechanic rather than assuming symmetry with
  its Sandstorm counterpart.
- **Field-conditional boost extended to the whole side**: Flower Gift —
  same `passive`/`tag`/`fail_if` shape as Grass Pelt, just targeting
  `self_side` instead of `self`.
- **Field-conditional heal + immunity as two events on ONE block**: Ice
  Body — unlike Sand Rush/Sand Veil above, the heal and the immunity share
  the same `on_turn_end` trigger point here (both are per-turn things),
  so they're two events on one block rather than two separate blocks.
  Rain Dish is the same shape minus the immunity clause (Rain doesn't deal
  chip damage to begin with, so there's nothing to be immune to).
- **`block_switch` applied to the OPPONENT, not self**: Arena Trap, Shadow
  Tag, Magnet Pull — every prior use of `block_switch` (Ingrain, Bound)
  applied it to the holder's own `self`; these apply it to `opponent_side`
  instead, since the ability traps the *other* Pokémon. Same key, target
  reversed — worth remembering `block_switch`/`block_forced_switch` aren't
  inherently self-only.
- **`block_forced_switch` alone, no `block_switch`**: Suction Cups, Guard
  Dog — the other half of Ingrain's original pairing, used on its own this
  time. Immunity to being pulled out (Roar, Red Card) without restricting
  the holder's own voluntary switch, which the `note` makes explicit since
  it's easy to assume both halves travel together.
- **Two unrelated facets on one ability, one shared with another
  ability**: Guard Dog — `on_stat_change` (Intimidate-specific Attack
  boost) and `block_forced_switch` (identical to Suction Cups) as two
  separate blocks, since they're unrelated triggers that happen to
  coexist on this one ability.
- **`on_status_inflict` reflecting back at the inflicter, not blocking**:
  Synchronize — same condition type as the whole status-immunity family,
  but instead of a `fail_if`-gated block, it fires the identical status
  back at `opponent` (whoever caused it). A `note` narrows which statuses
  qualify (major statuses only, not Sleep/Freeze) and excludes
  self-inflicted cases.
- **Contact-punish shape reused verbatim for a new status**: Poison Touch
  — exactly Static/Flame Body/Poison Point's `on_hit` + `fail_if: not
  contact` + `chance` shape from family 2, just a different `status`
  value. Zero new design needed once the shape existed.
- **Same status, different gate — worth telling apart**: Toxic Chain vs.
  Poison Touch — both inflict a poison-family status on a `chance`, but
  Toxic Chain is `on_deal_damage` (any landing move) with no contact/type
  gate, while Poison Touch is contact-only. Easy to conflate since both
  read as "X% chance to poison on hit" — the trigger point is what
  actually differs.
- **Crit guaranteed against a status, not a stat/type**: Merciless — same
  `on_calc_damage` shape as the whole damage-calc family, but `fail_if`
  gates on the target's status rather than a type matchup or the holder's
  own HP.
- **Bypasses a type immunity, not a status/move block**: Corrosion — a
  `passive` `tag`, since there's no single incoming trigger to hang a
  `fail_if` on; it's a standing exception to the normal
  Poison/Steel-immune-to-poison rule wherever poison application is
  checked.
- **`on_switch_out` for a cure/heal payoff, not a lock**: Natural Cure,
  Regenerator — the only prior use of `on_switch_out` was Ingrain
  restricting the switch itself; here it's just "something happens
  exactly at the moment of switching out," no `block_switch` involved.
  Same condition type, unrelated purpose.
- **Chance-gated turn-end cure, three variants of the same idea**:
  Hydration (`fail_if` on a field condition instead of `chance`), Healer
  (`chance` + targets `self_side` for the ally case, `note` flags it's a
  doubles-only mechanic), Shed Skin (plain `chance`, no gate). All three
  reuse `effect: cures any major status condition` verbatim rather than
  re-describing the cure each time.
- **Modifies another status's own counter, not a new mechanic**: Early
  Bird — same "cross-reference instead of redefine" treatment Heatproof
  got for Burn's tick; here it's Sleep's `duration_turns` counter that
  gets referenced, not duplicated.
- **`on_status_inflict` for a REACTION, not a block**: Steadfast — same
  condition type as Inner Focus (which blocks Flinch outright), but
  Steadfast lets Flinch land and adds a Speed boost as a consequence.
  `fail_if` narrows which status triggers it either way; whether the
  block *blocks* is a separate design choice, not implied by the
  condition type.
- **`on_deal_damage` inflicting a volatile as a secondary chance**: Stench
  — same `chance` + status-value shape as the contact-punish family, but
  `on_deal_damage` instead of `on_hit` since it's the holder's own
  offense causing it, not a reaction to being hit. `note` clarifies it
  stacks with a move's own listed flinch chance rather than replacing it.
- **PokeAPI text omitting the actual multiplier**: Transistor, Dragon's
  Maw, Rocky Payload — the fetched `effect` string just says "Powers up X
  moves" with no number, unlike most of this family. Filled in from known
  real values (and Transistor's post-Gen-9-nerf value specifically, not
  its original one) with an explicit `note` each time, same discipline as
  Cotton Down's garbled text back in family 4 — never silently invent a
  number the source didn't give.
- **Ally-boosting excludes the holder's own moves**: Steely-Spirit,
  Battery, Power Spot — `self_side` `fail_if` has to explicitly exclude
  "belongs to the holder," not just "belongs to an ally," since
  `self_side` includes the holder itself. Battery adds a second
  restriction (special moves only) that the generic PokeAPI wording
  doesn't convey — checked against known mechanics rather than trusting
  the text.
- **Field-wide boost, not side-wide**: Dark Aura, Fairy Aura — `target:
  field`, since these boost the given type for EVERY Pokémon in the
  battle, friend and foe alike, unlike the ally-only trio above.
- **Ability that inverts another ability's field-wide effect**: Aura
  Break — a `passive` `tag` on `field`, `fail_if` gated on Dark Aura/Fairy
  Aura actually being present; doesn't redefine what those abilities do,
  just flips the sign while active, same cross-reference discipline as
  Heatproof/Early Bird modifying an existing status.
- **Field-conditional self-buff PLUS an item-triggered override path**:
  Protosynthesis, Quark Drive — same `passive`/`tag`/`fail_if` shape as
  Hadron Engine/Orichalcum Pulse, plus a second `on_switch_in` block for
  the Booster Energy activation, described in plain-language `effect`
  text rather than a structured item vocabulary (deferred family 13
  hasn't been built yet). Doing this now rather than waiting for that
  family, since the item interaction is core to what these abilities
  *are* — not an optional extra bolted onto a field-reactive ability like
  Guard Dog's Intimidate reaction was.
- **`on_priority_check` blocking, not granting**: Armor Tail, Dazzling,
  Queenly Majesty — same condition type as Prankster/Gale Wings/Quick
  Draw from family 7, but `target: opponent` and the payoff is an outright
  block rather than a boost. Three near-identical entries kept separate
  with cross-referencing `note`s, same treatment as every other
  mechanically-duplicate trio so far (Battle Armor/Shell Armor, Clear
  Body/White Smoke/Full-Metal Body).
- **Field-wide passive multiplier that looks like a stat drop but isn't**:
  the Ruin quartet — deliberately `on_calc_damage`, not `on_stat_change`,
  even though "lowers X of all Pokémon" reads exactly like the trigger
  Defiant/Competitive from family 4 react to. It's a damage-calc-time
  ×0.75 multiplier with no actual stage change behind it — doesn't show a
  stage arrow, doesn't trigger stat-drop-reactive abilities, and multiple
  Ruin abilities on the field stack independently rather than colliding.
  Same "don't reach for on_stat_change just because a stat is mentioned"
  lesson as Unaware from family 8, from the opposite direction this time.
- **Ability-bypass, one condition covering "any hindering ability"**:
  Mold Breaker, Teravolt, Turboblaze — a single `passive` `tag` describing
  the bypass generically (with examples) rather than enumerating every
  ability it could apply to; a `note` draws the line at abilities that
  react to being hit rather than abilities that hinder the move itself
  (Rough Skin still triggers; Water Absorb doesn't).
- **One-off grab bag, batch 1 (damage/immunity-adjacent)**: 26 abilities
  (Adaptability, Huge Power, Pure Power, Prism Armor, Shadow Shield, Tera
  Shell, Neuroforce, Fur Coat, Friend Guard, Sturdy, Disguise, Magic
  Guard, No Guard, Compound Eyes, Super Luck, Serene Grace, Scrappy,
  Tangled Feet, Telepathy, Damp, Magic Bounce, Screen Cleaner, Infiltrator,
  Wonder Skin, Unseen Fist, Piercing Drill) — no new shapes, every single
  one slotted into an existing pattern (`on_calc_damage`/`tag`/`fail_if`,
  `passive`, `on_hit_holder`, `on_move_block_check`). Several are exact
  duplicates of abilities from earlier families (Prism Armor = Solid
  Rock/Filter, Shadow Shield = Multiscale, Magic Bounce = the Magic Coat
  status but always-on) — cross-referenced with a `note` rather than
  re-explained. This batch is the clearest evidence the family-first
  approach paid off: nothing here needed new design, just applying what
  already existed.
- **One-off grab bag, batch 2 (stat/turn-order/detection/misc)**: 28
  abilities. Two needed genuinely new custom condition types — Dancer
  (`on_dance_move_used`: reacting to *any* Pokémon using a dance move, not
  just the holder — `on_move_used` only covers the holder's own moves) and
  Opportunist (`on_opponent_stat_raise`: reacting to an *opponent* raising
  its own stat, the mirror image of `on_stat_change`, which is documented
  "(Self)"). Both used the Custom… option rather than stretching an
  existing type, same discipline as Soul-Heart's `on_any_faint` back in
  family 4.
- **Purely informational abilities get a `note` saying so explicitly**:
  Anticipation, Forewarn, Frisk, Illuminate, Ball Fetch — rather than
  skipping them (leaving a gap an audit pass would later flag as
  "missing") or inventing a mechanical effect that doesn't exist, each
  gets a real block whose only content is "no mechanical effect, here's
  what it reveals/does instead."
- **Ability modifies another status's behavior, not a new mechanic**:
  Poison Heal — same cross-reference treatment as Heatproof/Early Bird;
  explicitly "REPLACES" Poison/Toxic's own tick rather than adding a
  second heal on top of the existing damage.
- **One-off grab bag, batch 3 — final (23 abilities)**: closes out every
  ability that isn't item-interaction or a form-change gimmick. Slow Start
  reuses the `duration_turns` + separate `passive`-facet shape (a fixed
  lifespan block for the expiry, a standing-effect block gated on that
  lifespan not having run out yet) rather than inventing anything new —
  same pattern Ingrain and the field-condition statuses established. No
  other new shapes needed in this batch either.
- **First real use of `on_item_consumed` vs. `on_item_removed`**: the
  whole item-interaction family. The split matters concretely for
  Harvest — it sets `harvest_eligible` only from `on_item_consumed`
  (self-eaten), never from `on_item_removed` (Knock Off, Thief, Covet),
  so a stolen Berry can never come back but an eaten one can. Sticky Hold
  is the mirror case: it hooks `on_item_removed` only and explicitly does
  not touch `on_item_consumed` — it blocks theft, not self-use.
- **Background volatile from a counter/flag, not a status file**:
  Unburden — `on_item_consumed`/`on_item_removed` both `set` the same
  `unburden_active` counter to 1, `on_switch_out` resets it to 0, and a
  `passive` block reads it with `fail_if`. Same shape as Guts/Marvel
  Scale's status-conditional boost, just gated on an item-loss flag
  instead of a status name.
- **Modifier on another mechanic, not a trigger of its own**: Gluttony
  (changes a Berry's own HP-threshold), Ripen (changes a Berry's own
  potency) — both `passive` `tag`s with a `note` explicit that they do
  nothing without a qualifying Berry already in play, same "cross-
  reference instead of redefine" discipline as Heatproof/Early Bird/Aura
  Break.
- **Delayed replay of a consumed effect**: Cud Chew — `on_item_consumed`
  remembers the Berry, then `delayed_turn` (1 turn) replays its effect
  without re-consuming anything. Textbook application of the existing
  `delayed_turn` shape to a new domain.
- **Verifying an instruction against source data, not just following it**:
  Pickup (does have an in-battle pickup effect, contrary to being lumped
  in with Honey Gather's post-battle-only behavior) and Magician (no
  contact requirement — triggers off any damaging move) — both built per
  the actual fetched `effect` text after it diverged from what was
  initially assumed, with the correction flagged rather than silently
  substituted.
- **Form-change gimmicks, the final family (22 abilities)**: mostly
  bespoke single-Pokémon mechanics, but nearly every one still landed on
  an existing condition type — `on_hit`/`on_turn_end` for HP-threshold
  form changes (Zen Mode, Schooling, Power Construct, Shields Down),
  `on_deal_damage` for the KO-triggered ones (Eelevate — same shape as
  Beast Boost), `on_weather_change` for the weather-reactive ones
  (Forecast, Ice Face's restoration half), `on_move_used` for pre-move
  transforms (Stance Change). As One (Glastrier/Spectrier) are literally
  two other abilities glued together — built as two blocks each,
  cross-referencing Unnerve/Chilling Neigh/Grim Neigh by name rather than
  re-deriving them.
- **Terastallizing needed a genuinely new custom condition**: Embody
  Aspect, Teraform Zero — `on_terastallize`, since nothing in the existing
  vocabulary covers that moment. Third custom condition type overall,
  alongside `on_any_faint` (Soul-Heart) and `on_dance_move_used`/
  `on_opponent_stat_raise` (Dancer/Opportunist).
- **An ability reacting to an ALLY's item, caught on the closing sweep**:
  Symbiosis — missed in the first item-interaction pass, caught by a
  final with-data audit against the full catalog rather than assuming the
  batch was complete. Needed its own custom condition
  (`on_ally_item_consumed`) since `on_item_consumed` is specifically
  self-scoped and doesn't cover reacting to what an ally does.
- **Flagged uncertainty rather than faked confidence**: Mega-Sol — an
  unfamiliar, likely newer ability with a terse PokeAPI description;
  built from the fetched text at face value with an explicit `note`
  asking for verification against actual in-game behavior, rather than
  presenting a guess as settled fact.
- **Self-inflicted downside from using a move**: Glaive Rush — `on_apply`
  `tag`s the vulnerability (double damage taken, always hit), paired with
  a `duration_turns: 1` block that just clears it. Same shape as Laser
  Focus/Lock-On, but a cost instead of a benefit — the `tag` pattern
  doesn't care which direction the effect points.
- **Parameterized `set` amount, reused by a different source**: Substitute
  — `set` is written as "N% of max HP" rather than hardcoded to
  Substitute's usual 25%, specifically so Shed Tail's identical
  `substitute_hp` counter at a 50% cost reuses the exact same three-block
  shape (`on_apply` set+pay, `on_hit_holder` absorb, `on_switch_out` lose
  it) with only the number changing at the point of creation. This is the
  general move whenever two sources create the "same" status at different
  strengths — parameterize the amount in the shared status, don't fork the
  status definition per source.
- **Climbing DoT**: Toxic — `on_apply` sets a `counter`, `on_turn_end` reads
  it into `damage` and `increment`s it.
- **Chance-gated move-block**: Paralysis, Infatuation — single
  `on_move_block_check` block, one event with `chance` set and an `effect`
  param. Infatuation additionally uses `fail_if` to no-op once the
  infatuating Pokémon is gone.
- **Two-stage move-block gate, chance-cured**: Freeze — `on_turn_start`
  chance-gated thaw roll may cure it before the always-on
  `on_move_block_check` block is even reached.
- **Fixed-lifespan move-block gate**: Sleep, Taunt, Encore, Disable — a
  `duration_turns` block (Sleep: `random 1-3`; the others: a fixed count)
  whose own events just cure/expire the status, running alongside an
  always-on `on_move_block_check` block that does the actual blocking each
  turn while it's active. Taunt/Disable use `fail_if` to restrict *which*
  moves get blocked (status moves only; one specific move) rather than
  blocking outright; Encore instead overrides move selection entirely
  (`effect: forces the repeat of...`) and adds its own `fail_if` for
  running out of PP as a second, timer-independent way out.
  `duration_turns` replaced Sleep's earlier hand-rolled
  `on_apply`(`set`)+`on_turn_start`(`decrement`) pair — same idea, now one
  block instead of two.
- **Slot-bound delayed payoff**: Wish, Future Sight, Doom Desire —
  `delayed_turn` condition + `bind_target` + `fail_if: slot is empty`.
- **Plain delayed payoff (no slot-binding needed)**: Yawn — `delayed_turn`
  (1 turn), payoff is `effect: applies Sleep` rather than damage/heal, plus
  a `fail_if` for the usual sleep-blocking exceptions.
- **Chance-gated move-block, twin catalog entries**: Attract mirrors
  Infatuation's block exactly — same in-game mechanic, two names in the
  catalog (move/status name vs. effect name).
- **Two-sided per-turn tick**: Leech Seed — one `on_turn_end` block, two
  events (`damage` to self, `heal` to `opponent` with `bind_target`).
- **Standing property + switch lock**: Ingrain — `on_apply` (`tag`),
  `on_turn_end` (`heal`), `on_switch_out` (`block_switch` +
  `block_forced_switch`).
- **`duration_turns` + per-turn tick**: Bound (self-damage, `block_switch`
  only — unlike Ingrain, forced switches still work), Sea of Fire /
  G-Max Wildfire·Cannonade·Vine Lash·Volcalith (side-targeted damage,
  `fail_if` gating the immune type instead of `only_if` gating who's
  affected). Same three-block shape as Toxic/Leech Seed's tick, with a
  `duration_turns` block added for the fixed lifespan.
- **`duration_turns` + `chance`, different trigger points**: Confusion —
  the lifespan (`random 1-4`) is on one block; the per-turn self-hit roll
  (33%) is on a separate `on_move_block_check` block. The two aren't the
  same countdown — don't conflate a status's overall duration with a
  chance that re-rolls every turn it's active.
- **`duration_turns` with a non-cure payoff**: Perish Song — the block's
  own event at expiry is `effect: faints`, not a cure. `duration_turns`
  doesn't imply "ends peacefully," just "this many turns, then one thing
  happens."
- **Passive field/side property, documented via `tag`**: Reflect/Light
  Screen/Aurora Veil, Tailwind, Rainbow/Swamp, Weather (Rain/Sun/Sand/
  Hail), Terrain (Electric/Misty/Psychic), Gravity, Trick Room — an
  `on_apply` block whose only event is a `tag` describing the standing
  effect (the actual per-hit/per-move modifier lives in damage-calc/move
  logic elsewhere, not as an event here), plus a `duration_turns` block
  whose event fires the expiry/clear. Sand and Hail additionally combine
  this with the per-turn-tick shape above (constant field damage, `fail_if`
  gating the immune types). This is the standard shape for "X is active for
  N turns and does something passive the whole time, with no per-turn
  event of its own to model."

## Verification pass: full status-editor sweep (all 93 statuses)

Every status not already covered by the Confusion/Paralysis/Freeze/Bound
verification was cross-checked against Showdown's actual `conditions.ts`
and the setter move's own `condition:` block in `moves.ts` (most
volatile/side/field statuses are defined inline on their setter move
rather than in `conditions.ts`, which only holds the handful of
globally-shared conditions — major statuses, confusion, weather). Real
findings, grouped by theme:

**Systemic gap — Heavy Duty Boots**: every entry-hazard status (Spikes,
Stealth Rock, Toxic Spikes, Sticky Web, G-Max Steelsurge) was missing the
Heavy Duty Boots exception entirely — none of them had it, and nothing
else in the repo mentioned it. Added a `fail_if` to all five. Worth
grepping for again if any new hazard-like status is ever added.

**Systemic gap — the protect family's `blockStatus` flag**: Showdown's
shared bypass check (`checkMoveBypassesProtect(move, source, target,
blockStatus)`) takes a boolean for whether status moves are blocked too.
King's Shield, Burning Bulwark, Silk Trap, and Obstruct all pass `false`
(i.e. **don't** block status moves, only damaging ones) but were stored as
"blocks most incoming moves" with no such carve-out — all four corrected.
Mat Block already had this nuance right; Protect/Detect/Spiky Shield/
Baneful Bunker/Endure genuinely do block everything (or have no
move-block at all, for Endure) so needed no change. King's Shield's
Attack-drop payoff was also wrong at -2 stages — verified directly against
source (`boost({atk: -1}, ...)`) as -1; -2 was the pre-Gen-8 value.

**Rounding-rule violations caught**: Stealth Rock's and G-Max Steelsurge's
0.25x-effectiveness row was stored as 3% (1/32 max HP = 3.125%, rounded
*down*) instead of the project's own round-**up** rule (→4%). G-Max
Steelsurge was also missing its 4x-effectiveness row (Ice/Fairy targets)
entirely, incorrectly claiming no 4x case exists.

**Off-by-one delayed-payoff timing, same shape as the Sleep/Confusion
worked example**: Wish's `delayed_turn` was stored as 2 turns; tracing
Showdown's actual `onStart`/`onResidual` control flow shows the heal lands
at the end of the very next turn — a 1-turn delay, the same shape already
correctly captured for Yawn. Corrected. Laser Focus had the same class of
error (stored as 2, corrected to 1, consistent with Lock-On/Mind Reader's
already-correct 1).

**A hedge that violated the modern-mainline-only rule**: Hail/Snow was
previously written as a hedge between legacy Hail (per-turn chip damage)
and modern Gen 9 Snow (no chip damage, +50% Ice-type Defense instead) with
a note asking whoever read it to pick one. Verified Showdown's actual
`snowscape` condition has no damage hook at all — rewrote to modern Snow
only, removing the per-turn damage block entirely.

**Missing blocks, not just missing numbers**: Grassy Terrain was missing
its `on_apply` tag block and `duration_turns` block *entirely* — only the
per-turn heal was ever built. Added the Grass-move power boost, the
Earthquake/Bulldoze/Magnitude halving vs. grounded targets, and the
missing duration block. Misty Terrain was missing its Confusion-block
clause and its Dragon-move damage halving vs. grounded targets. Gravity
was missing its accuracy-multiplier number and its move-block behavior
(Fly/Bounce/Sky Drop/Splash/Magnet Rise/Telekinesis/Jump Kick/High Jump
Kick all disabled outright) — previously just said "boosts accuracy" with
nothing else.

**Real mechanic quietly wrong, not just under-documented — Toxic's own
counter**: the stored note claimed the badly-poisoned damage counter
"persists across switches," but Showdown's `tox` condition has an explicit
`onSwitchIn() { this.effectState.stage = 0; }` — the counter resets to
stage 1 every time the holder switches out and back in, even though the
poisoned status itself isn't cured by switching. This is the opposite of
what was documented and is a commonly-misunderstood mechanic (people
assume it climbs forever through switches). Corrected, and documented the
15-stage cap that was also missing.

**Real exclusions found by reading past the top-line effect**: Sleep now
excludes Sleep Talk/Snore (both flagged `sleepUsable` in source — the
sleeping Pokémon can still use these two moves). Substitute was missing
the "Shedinja clause" (fails outright at 1 max HP, a separate hard check
from the generic 25%-HP-threshold logic) and had an incomplete `bypasssub`
example. Stockpile was missing that ending it reverses the Def/SpD boosts
it granted. Octolock's trap/effect ends early if the Octolock user itself
leaves the field. Attract/Infatuation were missing the opposite-gender
precondition entirely (genderless Pokémon can neither cause nor receive
it). Destiny Bond/Grudge only pay off when the faint is caused directly by
an opposing move on that exact hit — not residual/indirect damage, and not
future-sight-type moves. Lock-On/Mind Reader's guarantee also bypasses
semi-invulnerable states (Fly/Dig), not just normal evasion. Redirect
(Follow Me / Rage Powder) turned out not to be as symmetric as the two
shared catalog entries implied: Rage Powder is blocked by powder-immunity
(Grass-types, Overcoat, Safety Goggles) and Follow Me isn't.

**Confirmed correct, no change** (the majority of the sweep): weather-rain,
weather-sand, weather-strong-winds, trick-room, tailwind, protect, detect,
spiky-shield, baneful-bunker, endure, crafty-shield (plus a precision
note), wide-guard, quick-guard, mat-block, rainbow, sea-of-fire, swamp,
all four G-Max side-damage moves, taunt, encore, disable (confirmed at a
flat 4 turns, modern-gen — the "random range" people associate with it is
a legacy-gens-only mechanic), torment, perish-song, glaive-rush, yawn,
magnet-rise, telekinesis, magic-coat, snatch, helping-hand, powder,
quash, foresight, miracle-eye, odor-sleuth, focus-energy, dragon-cheer
(its Dragon-type-ally +2 vs. +1 asymmetry was already correctly captured,
not the naive symmetric guess one might expect).

This closes out status-editor: all 93 statuses have now been individually
cross-checked against Showdown source, not just PokeAPI text or general
knowledge.

## Verification pass: local manual sweep, 2026-08-31 (session-driven, not the scheduled task)

Context: the scheduled-task automation for this sweep turned out to be non-functional
(fired twice, reported success, produced zero commits — root cause was git push
credentials/repo-authorization, not the verification logic itself). This pass was done
directly in an interactive session instead, working straight against the local clone as
source of truth (commits are local-only until pushed).

- **Scope discovery**: 60 of the 373 cached abilities are `is_main_series: false`
  (Pokémon Conquest spin-off abilities — e.g. `daze`, `black-hole`, `conqueror`,
  `bonanza`). These have no Showdown implementation at all, so "verify against Showdown"
  doesn't apply to them. Split them into `temp/verification_progress/abilities_out_of_scope.txt`
  (51 remaining after removing ones that happened to already be in batch 1's done range)
  rather than leaving them stuck in the todo queue.
- **dark-aura**: confirmed the ×1.33 field-wide Dark-type damage boost (chainModify
  [5448,4096]), but the existing entry was missing the Aura Break interaction — when
  Aura Break is also active anywhere on the field, the multiplier flips to ×0.75
  ([3072,4096]) instead of ×1.33 (the aura is reversed, not cancelled). Added.
- **dazzling**: existing entry scoped the priority-move block to "the holder only." Real
  scope is the holder AND its allies (`source.isAlly(dazzlingHolder)` check) — a
  whole-side protection, same as Armor Tail/Queenly Majesty. Also added the
  target==='foeSide' / all-target exception list (Perish Song, Flower Shield, Rototiller
  are not blocked). Fixed.
- **dauntless-shield**: confirmed correct as-is (once-per-battle +1 Def on switch-in via
  the `shieldBoost` flag, matches source exactly). No change.

## Non-mainline abilities removed from the catalog entirely, 2026-08-31

Rather than tracking the 60 Conquest-only (`is_main_series: false`) abilities in a
separate out-of-scope file, they were removed outright from
`temp/ability-editor/ability_cache.json` (373 → 313 abilities) so the editor UI and any
future verification pass never surfaces them at all. In the process, 9 of them
(aqua-boost, black-hole, bodyguard, bonanza, calming, celebrate, climber, confidence,
conqueror) were found to have been marked "done" in the checkpoint tracker purely
because they fell alphabetically inside the batch-1 range (adaptability–dancer) — they
were never actually reviewed. Removed from abilities_done.txt along with the rest.
Checkpoint totals now reconcile exactly: 75 done + 238 todo = 313 (the full trimmed
catalog). Moves and the curated status list were checked and have no non-mainline
entries to begin with.

## Checkpoint reconciliation against prior EVENT_VOCAB.md verification passes, 2026-08-31

The original task description (the scheduled task's prompt) referenced three
already-verified ability families that predate this checkpoint system entirely: a
"chance-value batch of 13," an "item-interaction batch of 12," and a "form-change-
gimmick batch of ~22." Cross-referenced those against this file's own earlier
sections ("Verification pass against Showdown's actual source" and "Verification
pass: item interaction + form-change gimmicks") and marked every individually-named
ability as done WITHOUT re-verifying it — trusting the prior write-up rather than
re-spending budget on abilities already checked:

- Chance-value batch: effect-spore, quick-draw, harvest, supreme-overlord,
  toxic-chain, static, flame-body, poison-point, cute-charm, cursed-body, stench,
  shed-skin, healer (13/13, full batch named individually — matches the claimed size).
- Item-interaction family: pickup, magician, sticky-hold, cud-chew, ripen (5 of the
  claimed 12 — only 5 were individually named with a finding; the other 7 aren't
  identifiable by name from this file alone).
- Form-change-gimmick family: battle-bond, gulp-missile, power-construct, schooling,
  shields-down, zen-mode, ice-face, multitype, rks-system, commander (10 of the
  claimed ~22 — same gap, only the ones with a finding or explicit "confirmed
  correct" note got named).

Honest gap: roughly 19 abilities across the item-interaction and form-change families
were apparently reviewed as part of those batches (per the original task's count) but
never individually named in this file — likely confirmed-correct-as-is with no
note-worthy finding, the same pattern as verification batch 1's unnamed 37. They are
NOT marked done here, since there's no way to identify which specific abilities they
were without guessing. If that original batch accounting turns out to be trustworthy,
this checkpoint is conservatively under-crediting by ~19 abilities; if it turns out
to be wrong, nothing was falsely marked verified.

Also moved axe-kick to moves_done — its confusion-duration override was verified and
documented in the "Verification pass against Showdown's actual source" section above.

Checkpoint totals after reconciliation: abilities 95 done / 218 todo (of 313 total,
post non-mainline removal); moves 1 done / 894 todo; statuses 93/93 done.

## Verification pass: run 2, 2026-08-31 (defeatist–download)

- **defeatist**: confirmed correct as-is (halves both Atk and SpA at ≤50% HP). No change.
- **defiant**: real bug, same shape as batch-1's Competitive fix — the existing note
  claimed it triggers on self-inflicted stat drops (Overheat, Leaf Storm); Showdown's
  `onAfterEachBoost` explicitly skips when there's no source or the source is an ally
  of the target, so only an opponent-caused drop triggers the +2 Atk. Fixed.
- **delta-stream** / **desolate-land**: both were missing the two mechanics shared by
  the "strong weather" trio (with Primordial Sea) — (1) immune to being overridden by
  anything except one of the other two strong weathers, (2) persists after the holder
  switches out as long as another same-ability holder is still active, only truly
  clearing when none remain. Added to both.
- **disguise**: previously described generically; missing three real details —
  hard-gated to Mimikyu/Mimikyu-Totem species specifically (does nothing if copied
  onto another species via Trace/Skill Swap), deals real 1/8-max-HP damage on
  breaking (not just cosmetic), and doesn't break if the hit lands on Substitute
  instead of the holder. Fixed.
- **download**: confirmed correct as-is (sums foes' Def vs SpD, boosts SpA on a tie
  or when Def is the higher/equal stat, Atk otherwise). No change.

## Verification pass: run 3, 2026-08-31 (dragonize–eelevate, + a batch-1 correction)

- **dragonize**: was only excluding non-Normal moves from the type-change; missing the
  fixed exclusion list of moves with their own dynamic typing (Judgment, Multi-Attack,
  Natural Gift, Revelation Dance, Techno Blast, Terrain Pulse, Weather Ball — unless
  used as a Max Move), plus Z-move and Terastallized-Tera-Blast exceptions. Fixed. Also
  noted: Showdown flags it `isNonstandard: "Future"` — not yet released in any mainline
  game as of this data pull.
- **dragons-maw**: confirmed correct (1.5× Atk/SpA on Dragon moves, exact value from
  source, not a guess). No change.
- **drizzle** / **drought**: both missing their primal-reversion exception — Kyogre+Blue
  Orb (Drizzle) / Groudon+Red Orb (Drought) don't set weather themselves, since the
  primal-reverted form's own ability (Primordial Sea / Desolate Land) handles it, avoiding
  a double-trigger. Added to both.
- **dry-skin**: corrected the weather-tick heal/damage from "13%" to the exact 1/8
  (12.5%) max HP; added the Utility Umbrella exception (only applies to the holder's own
  *effective* weather, so a Utility Umbrella holder is unaffected even in active rain/sun).
- **early-bird**, **earth-eater**: both confirmed correct as-is. No change.
- **eelevate**: the "raises highest stat by 1 stage" framing was wrong — Showdown's
  `onSourceAfterFaint(length, ...)` boosts by `length`, the actual count of Pokémon KO'd
  by that one hit (matters for spread moves double-KOing in doubles). Fixed. Also flagged
  `isNonstandard: "Future"`, same as Dragonize (sequential ability numbers, 312/313).
- **beast-boost** (batch-1 correction, not part of this run's todo queue): found to have
  the exact same "+1 stage" oversimplification while verifying eelevate — identical
  source code shape (`onSourceAfterFaint(length, ...)`). Fixed even though it was already
  marked done; batch 1 apparently didn't check the `length` parameter on this one.

## Verification pass: run 4, 2026-08-31 (electric-surge–flare-boost)

- **electric-surge**: confirmed correct (sets terrain, no special persistence logic
  unlike the weather-setters — terrain-setting abilities don't get the
  indefinite-while-active treatment Drizzle/Drought/etc. get). No change.
- **electromorphosis**: condition type was `on_hit` (offensive/holder's-move-lands
  direction) but Showdown's `onDamagingHit` is a defensive hook — the holder being hit
  triggers this, not the holder hitting something. Corrected to `on_hit_holder`
  (matches Disguise's established precedent for this exact defensive-trigger shape).
- **embody-aspect**: added two missing details — each mask variant is individually
  species-locked to its exact Ogerpon Tera-form (same species-lock shape as Disguise —
  copied via an ability-swap effect, it would do nothing), and it's gated by a
  one-time-per-battle flag, not a re-check on every switch-in.
- **emergency-exit**: added an explicit fail_if for "no valid replacement" / "holder is
  trapped" — previously only implied by the effect text's "if one is available," not
  actually gated as a condition.
- **fairy-aura**: same Aura Break interaction gap as Dark Aura before it — added the
  ×0.75-instead-of-×1.33 reversal when Aura Break is also active on the field.
- **filter**: confirmed correct (×0.75 on super-effective hits, matches Solid
  Rock/Prism Armor's shape). No change.
- **fire-mane**: confirmed the ×1.5 Atk+SpA boost; noted `isNonstandard: "Future"` like
  Dragonize/Eelevate (not yet released in a mainline game).
- **flare-boost**: same framing bug as Supreme Overlord from an earlier pass — it's a
  move base-power multiplier at damage-calc time (`onBasePower`), not a literal Special
  Attack stat boost. Reframed accordingly.

## Verification pass: run 5, 2026-08-31 (flash-fire–grassy-surge)

- **flash-fire**: confirmed correct (immune + persistent Atk/SpA boost on both stats).
  Noted: flagged `noCopy`, so this state is NOT passed along by Baton Pass.
- **flower-gift**: ADDED the missing Cherrim species-lock (same shape as
  Disguise/Embody Aspect) and a second effect this entry was entirely missing --
  while in active sun, the holder itself forme-changes Cherrim -> Cherrim-Sunshine
  (reverting when sun ends), re-checked on switch-in and on any weather change.
- **flower-veil**: ADDED (1) Yawn is blocked via a separate volatile-add hook,
  distinct from the major-status path; (2) a self-inflicted exception -- a Grass-type
  ally's own stat drop (e.g. Overheat recoil) is NOT blocked, only externally-caused
  effects are (same shape as Defiant/Competitive's opponent-only trigger).
- **fluffy**: added a note that the contact ×0.5 and Fire-type ×2 modifiers are
  separate multiplicative chainModify calls, so a contact Fire move nets ×1 overall,
  not double or half -- both effect blocks must compose multiplicatively.
- **forecast**: ADDED the Castform species-lock (same shape as Disguise/Flower
  Gift/Embody Aspect); also re-checked on switch-in as well as live weather changes.
- **forewarn**: CORRECTED from a plain "highest base-power move" framing --
  Status moves are never revealed (ranked 0); OHKO moves rank as 150 bp, Counter/
  Metal Burst/Mirror Coat as 120 bp; a variable-power non-Status move with no listed
  power ranks as 80; ties are broken randomly among all qualifying moves.
- **frisk**: CORRECTED from singular framing -- reveals ALL active foes' held items
  (relevant in doubles with two foes), not just one.
- **fur-coat**: CORRECTED framing -- this is `onModifyDef` (doubles the holder's raw
  Defense stat value pre-calc), not a "damage from physical moves is halved" effect.
  The two are usually equivalent under the standard formula but differ for anything
  reading the holder's raw Defense directly (e.g. the holder's own Body Press). Same
  class of correction as Supreme Overlord/Flare Boost.
- **galvanize**: same missing exclusion list as Dragonize -- ADDED the
  dynamic-typing-move exclusions (Judgment, Multi-Attack, Natural Gift, Revelation
  Dance, Techno Blast, Terrain Pulse, Weather Ball unless used as a Max Move) plus
  Z-move/Terastallized-Tera-Blast exceptions. Unlike Dragonize, not `isNonstandard`.
- **good-as-gold**: added the self-targeted-status-move exclusion -- only blocks
  status moves coming from another Pokémon, not the holder's own status move.
- **friend-guard**: confirmed correct as-is (reduces damage taken by an ally by
  ×0.75; does not apply to the holder's own damage taken). No change.
- **full-metal-body**: confirmed correct as-is (blocks stat drops from other
  Pokémon, self-inflicted drops go through; identical shape to Clear Body). No change.
- **gale-wings**: confirmed correct as-is (+1 priority to Flying moves, full-HP gated
  since Gen 7). No change.
- **gluttony**: confirmed correct as-is (halves the auto-eat HP threshold for Berries
  from 1/4 to 1/2 max HP; does nothing without a qualifying Berry held). No change.
- **gooey**: confirmed correct as-is (contact punish, -1 Speed to the attacker).
  No change.
- **gorilla-tactics**: ADDED two missing details -- (1) the flat ×1.5 Atk boost is
  suppressed entirely while the holder is Dynamaxed; (2) Struggle and any
  Z-move/Max-powered move are exempt from the choice-lock in both directions
  (using one doesn't set/change the lock, and the lock never blocks using one).
  Functionally identical choice-lock shape to the Choice items, just tied to the
  ability instead of a held item (so it survives item removal/Trick).
- **grass-pelt**: confirmed correct as-is (×1.5 Def only during Grassy Terrain).
  No change.
- **grassy-surge**: confirmed correct as-is (sets Grassy Terrain on switch-in).
  No change.
