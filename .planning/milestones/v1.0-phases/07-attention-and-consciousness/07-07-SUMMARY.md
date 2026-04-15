---
phase: 07-attention-and-consciousness
plan: "07"
title: "Drunk seed mechanic — indefinite consciousness state with sobriety threshold + passive sober_up"
subsystem: mechanic-seeds
tags: [long-running-action, consciousness, seed-mechanic, passive, tdd]
requirements: [SIM-10]
decisions: [D-01, D-05, D-13, D-14, D-16, D-18]

dependency_graph:
  requires:
    - 07-01  # MechanicContext.begin_long_action, turns_total=None support
    - 07-02  # ThresholdEvaluator, LongRunningHook infrastructure
    - 07-03  # VisibilityProjector attention_state suppression
    - 07-04  # LongRunningHook post-execute integration in engine
  provides:
    - drunk mechanic (indefinite LRA showcase, turns_total=None, D-16)
    - sober_up mechanic (companion passive TickMatcher, RECOVERY_RATE=0.1/tick)
  affects:
    - registry invariant test (test_registry.py +2 entries: drunk, sober_up)

tech_stack:
  patterns:
    - DrunkMechanic: voluntary VerbMatcher("drink"), checks holds edge + alcohol_content > 0 + D-04 LRA guard
    - SoberUpMechanic: involuntary TickMatcher, _find_drunk_actors_with_room_to_recover helper, no LRA lifecycle ownership
    - RECOVERY_RATE=0.1 module constant (tuning knob)
    - int-ness preservation for sobriety arithmetic (consistent with ConsumeMechanic)

key_files:
  created:
    - src/token_world/mechanic/seeds/drunk.py
    - src/token_world/mechanic/seeds/sober_up.py
    - tests/test_mechanic/test_seeds/test_drunk.py
    - tests/test_mechanic/test_seeds/test_sober_up.py
    - tests/test_engine/test_drunk_integration.py
  modified:
    - tests/test_mechanic/test_registry.py  # +2 entries: drunk, sober_up

decisions:
  - "turns_total=None (D-16): indefinite drunk LRA — only threshold or D-11 cancellation ends it"
  - "RECOVERY_RATE=0.1: gives ~8-tick sober-up for a 0.5-alcohol drink (deterministic for tests)"
  - "SoberUpMechanic owns NO LRA lifecycle: hook clears LRA when sobriety > 0.8 fires (D-01 composition)"
  - "D-11 cancellation preserves graph consciousness properties (is_drunk, sobriety_level); only LRA struct cleared"
  - "Threshold is strictly > 0.8 (not >=): sobriety==0.8 does NOT fire; 0.9 does (verified in test 6)"

metrics:
  duration_minutes: 30
  completed_date: "2026-04-13"
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 1
  tests_added: 51
  tests_baseline: 1568
  tests_final: 1619
---

# Phase 07 Plan 07: Drunk + sober_up passive mechanic pair

**One-liner:** Indefinite-duration drunk LRA (turns_total=None) with companion SoberUpMechanic passive TickMatcher recovering sobriety 0.1/tick until the > 0.8 threshold fires.

## What Was Built

### DrunkMechanic (`src/token_world/mechanic/seeds/drunk.py`)

A voluntary `VerbMatcher("drink")` mechanic. The third and final Phase 7 seed demonstrator, and the one that showcases the `turns_total=None` (indefinite) path:

- **Preconditions:** actor exists, target exists, actor holds target, target has `alcohol_content > 0`, actor has no existing `current_long_action` (D-04 single-active guard)
- **apply mutations (in order):**
  1. `ctx.set(actor, "sobriety_level", max(0.0, current - alcohol_content))` — clamped at 0, defaulting to 1.0 if absent
  2. `ctx.set(actor, "is_drunk", True)`
  3. `ctx.remove_node(target)` — the drink is consumed
  4. `ctx.begin_long_action("drunk", turns_total=None, thresholds=[{alice.sobriety_level > 0.8}], attention_state={suppress: [fine_detail, social_nuance], boost: [aggression_level]})` — D-18 exact

The key distinguisher from sleep and autopilot_travel: `turns_total=None` means the LRA runs indefinitely. No clock. No automatic expiry. Only a threshold firing or D-11 cancellation ends it.

### SoberUpMechanic (`src/token_world/mechanic/seeds/sober_up.py`)

An involuntary `TickMatcher()` passive mechanic — the dual of `autopilot_advance.py`:

- **check:** passes only if at least one agent has `is_drunk=True` AND `sobriety_level < 1.0`
- **apply:** for each such agent, `new_sobriety = min(1.0, current + RECOVERY_RATE)` where `RECOVERY_RATE = 0.1`
- **Does NOT:** clear the LRA, set `is_drunk=False`, or evaluate thresholds — all LRA lifecycle is the hook's responsibility (D-01 composition)

`_find_drunk_actors_with_room_to_recover()` is a pure module-level helper (same pattern as autopilot_advance).

### Integration Test (`tests/test_engine/test_drunk_integration.py`)

Six deterministic tests covering the full lifecycle:

1. **6-tick sober cycle** — drink action tick, 4 continuation ticks (hook+sweep), threshold fires on tick 5 when hook sees sobriety=0.9 > 0.8
2. **D-16 indefinite duration** — without sober_up installed, 10 continuation ticks pass with LRA still active, `turns_total=None` never auto-expires
3. **D-11 cancellation** — new action clears LRA; `is_drunk` and `sobriety_level` remain in graph
4. **attention_state suppression** — `fine_detail` and `social_nuance` absent from projected_state during continuation
5. **D-17 tick summary** — `long_running_action.active=True`, `turns_total=null`, `interrupted=false` in JSON
6. **Strictly > 0.8** — sobriety==0.8 does NOT fire (> operator); sobriety==0.9 does

## Key Design Points

### `turns_total=None` is the central showcase of this plan

Sleep uses `turns_total=8`. Autopilot uses `turns_total=path_length`. Drunk uses `turns_total=None`. This is D-16: indefinite. The hook advances `turns_elapsed` for diagnostics but the completion check (`turns_elapsed >= turns_total`) is skipped when `turns_total` is None. Only a threshold firing ends the state.

### Composition over special-casing (D-01)

Three independent pieces, graph as shared channel:
- `DrunkMechanic` starts the LRA + sets initial graph state
- `SoberUpMechanic` increments `sobriety_level` each tick
- `LongRunningHook` evaluates `sobriety_level > 0.8` threshold and clears LRA when it fires

None of the three pieces knows about the others. No special-case drunk handling anywhere in the engine.

### Tick ordering matters for the 6-tick sequence

The engine runs `LongRunningHook` **before** the passive sweep on continuation ticks, but the passive sweep also runs on the **action tick** immediately after `DrunkMechanic.apply()`:

- Action tick: apply sets sobriety=0.5; passive sweep fires → 0.6
- Cont tick 2: hook sees 0.6 (not fire); sweep → 0.7
- Cont tick 3: hook sees 0.7 (not fire); sweep → 0.8
- Cont tick 4: hook sees 0.8 (not fire — strictly >); sweep → 0.9
- Cont tick 5: hook sees 0.9 (FIRE) → LRA cleared

### RECOVERY_RATE = 0.1 is a tuning knob

A 0.5-alcohol drink takes ~5 continuation ticks to sober up (0.5/0.1 = 5, minus the action-tick passive sweep that advances sobriety immediately after drinking). For deterministic tests, this gives a predictable sober-up sequence without requiring large numbers of ticks.

## Phase 7 Completion: Three Seed Demonstrators

Together, Plans 05, 06, and 07 close D-18 (three seed demonstrators) and SIM-10 (reusable mechanic pattern for consciousness states):

| Mechanic | Duration | Type | Threshold | Attention |
|---|---|---|---|---|
| `sleep` (Plan 05) | Bounded (`turns_total=8`) | Cognitive/rest | `noise_level > 0.7` | suppress visual_detail, smell |
| `autopilot_travel` (Plan 06) | Bounded (path length) | Spatial/movement | `hazard_level > 0.5` | suppress fine_detail |
| `drunk` (Plan 07) | **Indefinite (`turns_total=None`)** | Cognitive/social | `sobriety_level > 0.8` | suppress fine_detail, social_nuance |

The three cover bounded/indefinite, physical/cognitive/spatial, and different threshold types — the full composability proof.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff UP038 — `isinstance(x, (int, float))` must use `X | Y` union syntax**
- **Found during:** Task 1 commit (pre-commit hook)
- **Issue:** `isinstance(alcohol, (int, float))` triggered `UP038` — project uses Python 3.12+ and ruff enforces union-type isinstance syntax
- **Fix:** Changed to `isinstance(alcohol, int | float)` in `drunk.py`
- **Files modified:** `src/token_world/mechanic/seeds/drunk.py`
- **Commit:** Fixed inline before first commit

**2. [Rule 1 - Bug] F841 unused variable in integration test**
- **Found during:** Task 3 lint check
- **Issue:** `sobriety_mid = kg.query("alice", "sobriety_level")` assigned but never used
- **Fix:** Removed the unused assignment
- **Files modified:** `tests/test_engine/test_drunk_integration.py`
- **Commit:** Fixed inline before Task 3 commit

**3. [Rule 2 - Missing] Registry invariant test needed +2 entries**
- **Found during:** Task 3 full suite run
- **Issue:** `test_scan_discovers_seeds` hardcodes the expected sorted list of seed mechanics; adding `drunk` and `sober_up` seeds caused the assertion to fail
- **Fix:** Added `"drunk"` (after `"degrade"`) and `"sober_up"` (after `"sleep"`) to the expected list
- **Files modified:** `tests/test_mechanic/test_registry.py`
- **Note:** Plan's `<files_modified>` listed 5 files; this is a 6th file. The plan preface specifically notes "tests/test_mechanic/test_registry.py will likely need +1 line for registry invariant" — deviation is within scope guidance

## Known Stubs

None — both mechanics are fully wired. The `is_drunk` flag and `sobriety_level` property are set by `DrunkMechanic.apply()`, read by `SoberUpMechanic._find_drunk_actors_with_room_to_recover()`, and the threshold dict references `alice.sobriety_level` which the `ThresholdEvaluator` resolves against the projected state.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. Both mechanics are pure graph-mutation mechanics operating within the existing `MechanicContext` DSL.

## Self-Check: PASSED

Files created:
- `src/token_world/mechanic/seeds/drunk.py` — FOUND
- `src/token_world/mechanic/seeds/sober_up.py` — FOUND
- `tests/test_mechanic/test_seeds/test_drunk.py` — FOUND
- `tests/test_mechanic/test_seeds/test_sober_up.py` — FOUND
- `tests/test_engine/test_drunk_integration.py` — FOUND

Commits:
- `0580688` — feat(07-07): DrunkMechanic — FOUND
- `66ec895` — feat(07-07): SoberUpMechanic — FOUND
- `6e53c90` — test(07-07): drunk integration — FOUND

Test count: 1619 passed (baseline 1568 + 51 new tests)
