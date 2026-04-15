---
phase: 07-attention-and-consciousness
plan: "05"
title: "Sleep seed mechanic — bounded sleep with noise/health interruption thresholds"
subsystem: mechanic-seeds
tags: [sleep, long-running-action, seed-mechanic, attention-state, thresholds, tdd]
dependency_graph:
  requires:
    - 07-01  # LongRunningAction primitives + ThresholdEvaluator
    - 07-02  # VisibilityProjector attention_state extension
    - 07-03  # MechanicContext.begin_long_action helper
    - 07-04  # LongRunningHook engine integration
  provides:
    - sleep seed mechanic (reference implementation for 07-06 autopilot_travel, 07-07 drunk)
  affects:
    - tests/test_mechanic/test_registry.py (seed ID list updated)
tech_stack:
  added: []
  patterns:
    - Regular Mechanic returning list[Mutation] includes ctx.begin_long_action() call
    - Location property + type=location edge both needed: property for mechanic, edge for projector
    - Graceful threshold fallback: missing room node → omit noise threshold, no crash
key_files:
  created:
    - src/token_world/mechanic/seeds/sleep.py
    - tests/test_mechanic/test_seeds/test_sleep.py
    - tests/test_engine/test_sleep_integration.py
  modified:
    - tests/test_mechanic/test_registry.py
decisions:
  - "Location detection uses actor_props.get('location') (property) matching MovementMechanic convention"
  - "Noise threshold omitted gracefully when room missing — location-fallback policy (Q8)"
  - "Integration tests use location property + type=location edge for correct projector inclusion"
metrics:
  duration_minutes: 6
  completed_date: "2026-04-13"
  tasks_completed: 2
  tasks_total: 2
  new_tests: 31
  files_created: 3
  files_modified: 1
---

# Phase 07 Plan 05: Sleep Seed Mechanic Summary

**One-liner:** SleepMechanic — 8-tick bounded LRA with noise/health thresholds and attention suppression of visual_detail/smell, authoring the composable long-running action pattern in under 50 lines.

## What Was Built

### `src/token_world/mechanic/seeds/sleep.py` (< 50 lines of logic)

`SleepMechanic(Mechanic)` — a plain `Mechanic` subclass that demonstrates the D-01 composable pattern:

- `id='sleep'`, `voluntary=True`, `tags=['rest', 'long_running']`
- `watches()` returns `[VerbMatcher(verb='sleep')]`
- `check()`: refuses if actor missing OR `current_long_action` is already a dict (D-04 single-active-per-agent)
- `apply()`: two mutations in order:
  1. `ctx.set(actor, 'is_sleeping', True)`
  2. `ctx.begin_long_action(action_text='sleeping', turns_total=8, thresholds=..., attention_state={suppress:[visual_detail,smell], boost:[noise_level]})`

The mechanic is the skeleton. The engine's `LongRunningHook` (Plan 04) does all the work: advancing `turns_elapsed`, evaluating thresholds, synthesising interruption/completion narratives.

**The whole pattern in one look:**

```python
def apply(self, ctx: MechanicContext) -> list[Mutation]:
    thresholds = [{"property": f"{ctx.actor}.health", "op": "<", "value": 0.2}]
    location_id = ctx.query_node(ctx.actor).get("location")
    if isinstance(location_id, str) and ctx.has_node(location_id):
        thresholds.insert(0, {"property": f"{location_id}.noise_level", "op": ">", "value": 0.7})
    return [
        ctx.set(ctx.actor, "is_sleeping", True),
        ctx.begin_long_action(
            action_text="sleeping", turns_total=8,
            thresholds=thresholds,
            attention_state={"suppress": ["visual_detail", "smell"], "boost": ["noise_level"]},
        ),
    ]
```

Plans 06 (`autopilot_travel`) and 07 (`drunk`) follow this exact skeleton with different `turns_total`, `thresholds`, and `attention_state`.

### Tests (31 total)

**Unit tests** (`tests/test_mechanic/test_seeds/test_sleep.py`, 25 tests):
- Class attrs, `watches()`, `check()` (5 cases), `apply()` mutations order/shape, LRA field values, threshold construction with/without location, fallback with ghost room node

**Integration tests** (`tests/test_engine/test_sleep_integration.py`, 6 tests):
- `test_sleep_then_continue_then_wake_on_noise`: full 3-step cycle (start → quiet continuation → noise trigger)
- `test_sleep_continuation_tick_summary_has_long_running_action_field`: D-17 tick summary schema
- `test_sleep_completes_after_turns_total_ticks`: 8-tick natural completion
- `test_sleep_cancelled_by_new_agent_action`: D-11 implicit cancellation
- `test_sleep_continuation_does_not_call_classifier`: D-07 no LLM call on `run_tick(None)`
- `test_sleep_attention_state_suppresses_visual_detail`: D-12 attention modulation in projection

## Key Architectural Insight

**The mechanic is thin on purpose.** The 50-line limit isn't a coincidence — it proves the engine infrastructure (Plans 01-04) carries all the complexity. `SleepMechanic.apply()` does three things:

1. Read `actor.location` (existing property convention)
2. Build threshold dicts (plain Python)
3. Return `[ctx.set(is_sleeping), ctx.begin_long_action(...)]`

Everything else — threshold evaluation, `turns_elapsed` advancement, narrative synthesis, tick summary population, passive sweep scheduling — is handled by existing components unchanged.

## Location Detection Convention

The mechanic reads `actor_props.get("location")` (graph property, same convention as `MovementMechanic`). The integration tests add **both**:
- `kg.set("alice", "location", "bedroom")` — for the mechanic to read
- `kg.add_edge("alice", "bedroom", type="location")` — for `VisibilityProjector._get_actor_location()` to include bedroom in the projection (required for threshold evaluation against `bedroom.noise_level`)

Without the edge, bedroom is absent from the projection dict and the threshold never fires.

## Location-Fallback Policy (Q8 Decision)

If `actor.location` is absent, not a string, or references a non-existent node, the noise threshold is **silently omitted** — only the health threshold remains. The mechanic does not crash and does not refuse. Rationale: agents without a room may still need rest; graceful degradation is more composable than strict enforcement. Documented in the module docstring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Add 'sleep' to test_registry.py seed ID list**
- **Found during:** Task 2 full suite run
- **Issue:** `TestSeedUniverse.test_scan_discovers_seeds` hardcodes the sorted list of all seed mechanic IDs; adding `sleep.py` to the seeds directory caused it to fail
- **Fix:** Added `"sleep"` at the correct alphabetical position (between `"position_sync"` and `"speak"`)
- **Files modified:** `tests/test_mechanic/test_registry.py`
- **Commit:** `b8627f1`

**2. [Rule 1 - Bug] Integration test graph setup required location edge + property**
- **Found during:** Task 2 first test run (noise threshold never fired)
- **Issue:** `_setup_alice_in_bedroom` only set `kg.set("alice", "location", "bedroom")` (property). `VisibilityProjector._get_actor_location()` uses the outgoing `type=location` **edge** to find the room node; without the edge, bedroom is absent from the projection and the threshold against `bedroom.noise_level` evaluates to `False`
- **Fix:** Added `kg.add_edge("alice", "bedroom", type="location")` alongside the property set. Both are now required and documented in the helper's docstring
- **Files modified:** `tests/test_engine/test_sleep_integration.py`

**3. [Rule 1 - Bug] Classifier call counter test used wrong object reference**
- **Found during:** Task 2 (AttributeError on `SimulationEngine.messages`)
- **Issue:** Test tried `e.messages.calls` on the engine object; `messages` is on the `MockAnthropicClient`, not `SimulationEngine`
- **Fix:** Created `MockAnthropicClient` outside `_make_engine` and passed it directly; verified `client.messages.calls == []` after each tick
- **Files modified:** `tests/test_engine/test_sleep_integration.py`

## No Engine Code Touched

Confirmed: this plan did NOT modify `engine.py`, `visibility.py`, `long_running.py`, `long_running_hook.py`, or `context.py`. All were already in place from Plans 01-04. The scope boundary held exactly.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Known Stubs

None — the mechanic is fully wired. All thresholds derive from graph state at `apply()` time (D-09 grounding).

## Self-Check: PASSED

- `src/token_world/mechanic/seeds/sleep.py` — exists, 103 lines
- `tests/test_mechanic/test_seeds/test_sleep.py` — exists, 25 tests pass
- `tests/test_engine/test_sleep_integration.py` — exists, 6 tests pass
- `c75015e` — Task 1 commit (SleepMechanic + unit tests)
- `b8627f1` — Task 2 commit (integration tests + registry fix)
- Full suite: 1516 passed, 14 skipped (was 1485 + 31 new)
- `git diff 8762405..HEAD --stat` — 4 files, all in scope or documented deviation
