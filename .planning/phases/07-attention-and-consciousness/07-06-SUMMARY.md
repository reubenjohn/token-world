---
phase: 07-attention-and-consciousness
plan: "06"
title: "Autopilot-travel seed mechanic + per-tick advance"
subsystem: mechanic/seeds
tags: [spatial, long_running, passive, bfs, composability]
one_liner: "Two-mechanic autopilot split: AutopilotTravelMechanic starts a BFS-routed bounded LRA; AutopilotAdvanceMechanic (involuntary TickMatcher) advances location one hop per passive sweep tick"
completed: "2026-04-13T19:37:00Z"
duration_seconds: 647

dependency_graph:
  requires:
    - 07-01  # long_running.py dataclasses
    - 07-02  # LongRunningHook + threshold evaluator
    - 07-03  # ctx.begin_long_action helper
    - 07-04  # engine hook + passive sweep integration
  provides:
    - autopilot_travel seed mechanic (voluntary VerbMatcher travel)
    - autopilot_advance seed mechanic (involuntary TickMatcher passive)
    - BFS _find_path helper (pure, depth-capped, unit-tested independently)
  affects:
    - tests/test_mechanic/test_registry.py (registry invariant +2 entries)

tech_stack:
  added: []
  patterns:
    - "2-step begin-then-augment: ctx.begin_long_action then ctx.set to add route/next_index to payload without modifying Plan 03 helper"
    - "Involuntary TickMatcher passive mechanic scanning graph.nodes() internally (same as decay/weather pattern)"
    - "Location-edge update alongside location-property update so VisibilityProjector follows actor to new room"

key_files:
  created:
    - src/token_world/mechanic/seeds/autopilot_travel.py
    - src/token_world/mechanic/seeds/autopilot_advance.py
    - tests/test_mechanic/test_seeds/test_autopilot_travel.py
    - tests/test_mechanic/test_seeds/test_autopilot_advance.py
    - tests/test_engine/test_autopilot_integration.py
  modified:
    - tests/test_mechanic/test_registry.py

decisions:
  - "Location-edge update in advance mechanic (Rule 1): AutopilotAdvanceMechanic updates both the location property AND the type=location edge so VisibilityProjector includes the new room in its projection for threshold evaluation. Without the edge update, hazard_level thresholds would silently never fire (D-09: missing nodes evaluate as None)."
  - "Passive sweep runs on action tick too: the engine runs the passive sweep after every tick including the travel-start action tick. So after 'travel to room_d', alice is already in room_b (one hop advanced). Tests were corrected to assert next_index=2 (not 1) after the action tick."

metrics:
  tasks_completed: 3
  tests_added: 52
  files_created: 5
  files_modified: 1
---

# Phase 07 Plan 06: Autopilot-Travel Seed Mechanic + Per-Tick Advance — Summary

**One-liner:** Two-mechanic autopilot split: AutopilotTravelMechanic starts a BFS-routed bounded LRA; AutopilotAdvanceMechanic (involuntary TickMatcher) advances location one hop per passive sweep tick.

## What Was Built

### AutopilotTravelMechanic (`seeds/autopilot_travel.py`)

Voluntary mechanic (VerbMatcher `travel`) that:

1. Computes the shortest path from actor's current location to target via BFS
   (`_find_path` pure helper, max_depth=32, unit-tested independently).
2. Refuses when: actor/target missing, target==current location, actor already in
   LRA (D-04), or no path found.
3. Returns 3 mutations via the **2-step begin-then-augment pattern**:
   - `ctx.set(actor, 'is_traveling', True)`
   - `ctx.begin_long_action(action_text=f'traveling to {target}', turns_total=len(path)-1, thresholds=<one per room>, attention_state=D-18)`
   - `ctx.set(actor, 'current_long_action', <augmented dict with route + next_index=1>)`

   The augment step merges `route` and `next_index` into the payload without touching
   Plan 03's `begin_long_action` helper API.

4. Hazard thresholds: `{property: f'{room}.hazard_level', op: '>', value: 0.5}` for
   every room in the route. Harmless for rooms not in projection (D-09 safe defaults).

5. Attention state (D-18): `suppress: [fine_detail], boost: [hazard_level]`.

### AutopilotAdvanceMechanic (`seeds/autopilot_advance.py`)

Involuntary passive mechanic (TickMatcher, `voluntary=False`) that:

1. `check()`: scans all graph nodes for agents with a `traveling` LRA and an
   unfinished route (next_index < len(route)). Refuses if none found.
2. `apply()`: for each qualifying agent —
   - Sets `actor.location = route[next_index]`
   - Removes the old `type=location` edge and adds a new one to the new room
     (required so `VisibilityProjector` includes the new room in threshold evaluation)
   - Increments `next_index` in the LRA payload
   - Returns all mutations

### Composability Demonstrated (D-01)

Each piece is under 160 lines and knows nothing about the other:

| Piece | Knows about |
|-------|-------------|
| `AutopilotTravelMechanic` | graph BFS, LRA setup, route storage |
| `AutopilotAdvanceMechanic` | route payload, location mutation |
| `LongRunningHook` (Plan 04) | turns_elapsed, threshold evaluation, observation |

The graph is the only shared state.

## Test Coverage

| File | Tests | Focus |
|------|-------|-------|
| `test_autopilot_travel.py` | 27 | Class attrs, check refusals, apply shape, BFS helper |
| `test_autopilot_advance.py` | 19 | Class attrs, check, apply advance/no-op/multi-traveler |
| `test_autopilot_integration.py` | 6 | 4-room traversal, hazard interruption, attention_state, D-11 cancellation |

**Total new tests:** 52 (baseline 1516 → 1568 passed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Location edge not updated on actor advance**

- **Found during:** Task 3 integration test (hazard interruption test failing)
- **Issue:** `AutopilotAdvanceMechanic.apply()` updated `actor.location` property but
  not the `actor → room (type=location)` edge. The `VisibilityProjector` follows
  `type=location` edges to determine which room to include in the projection. Without
  the edge update, threshold specs like `room_b.hazard_level > 0.5` silently evaluated
  to `False` (D-09: missing nodes return None) even when alice was physically in room_b.
- **Fix:** Added edge removal (prev room) + edge addition (new room) in advance mechanic.
  Used `route[next_index - 1]` as prev_room (deterministic from route; no neighbor scan).
  Used `contextlib.suppress(Exception)` for best-effort removal (SIM105 compliance).
- **Files modified:** `src/token_world/mechanic/seeds/autopilot_advance.py`
- **Commit:** `198bba3`

**2. [Rule 2 - Missing critical functionality] Registry invariant update**

- **Found during:** Task 1 (same pattern as Plan 07-05)
- **Issue:** `test_registry.py::TestSeedUniverse::test_scan_discovers_seeds` enumerates
  all seed IDs; adding new seeds without updating it would break the invariant test.
- **Fix:** Added `autopilot_advance` and `autopilot_travel` to the expected sorted list.
- **Files modified:** `tests/test_mechanic/test_registry.py`
- **Commit:** `b60c950`

**3. [Rule 1 - Bug] Passive sweep runs on action tick too**

- **Found during:** Task 3 integration test debugging
- **Issue:** The plan spec implied next_index=1 after the action tick (travel start). In
  reality the engine's `_handle_execute` also triggers the passive sweep, so
  `AutopilotAdvanceMechanic` fires on the action tick and advances alice immediately.
  Tests were written expecting next_index=1; actual value was 2.
- **Fix:** Corrected test assertions to match real engine behaviour:
  - After action tick: next_index=2, alice.location=room_b
  - After continuation 1: next_index=3, alice.location=room_c
  - After continuation 2: next_index=4, alice.location=room_d
  - After continuation 3: LRA completed, cleared
- **Files modified:** `tests/test_engine/test_autopilot_integration.py`
- **Commit:** `198bba3`

## Key Patterns for Future Mechanics

### 2-Step Begin-Then-Augment

When `ctx.begin_long_action` does not support all payload keys needed:

```python
ctx.begin_long_action(action_text=..., turns_total=..., thresholds=..., attention_state=...)
stored = ctx.query_node(ctx.actor, "current_long_action")
augmented = dict(stored)
augmented["payload"] = {**augmented.get("payload", {}), "route": path, "next_index": 1}
ctx.set(ctx.actor, "current_long_action", augmented)
```

This keeps Plan 03's helper API minimal while allowing per-mechanic payload extensions.

### Location Edge + Property Together

Any mechanic that moves an actor must update BOTH:
- `actor.location` property (for mechanic logic)
- `actor → room (type=location)` edge (for VisibilityProjector projection)

### Passive Mechanic Self-Scan Pattern

Involuntary TickMatcher mechanics receive a sentinel actor from the engine. They must
scan `ctx.find_nodes()` themselves to find real targets:

```python
def check(self, ctx):
    if _find_traveling_actors(ctx):
        return CheckResult(passed=True)
    return CheckResult(passed=False, reasons=["..."])
```

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `src/token_world/mechanic/seeds/autopilot_travel.py` | FOUND |
| `src/token_world/mechanic/seeds/autopilot_advance.py` | FOUND |
| `tests/test_mechanic/test_seeds/test_autopilot_travel.py` | FOUND |
| `tests/test_mechanic/test_seeds/test_autopilot_advance.py` | FOUND |
| `tests/test_engine/test_autopilot_integration.py` | FOUND |
| commit `b60c950` (Task 1) | FOUND |
| commit `ec07643` (Task 2) | FOUND |
| commit `198bba3` (Task 3) | FOUND |
| `uv run pytest tests/ -x -q` | 1568 passed, 14 skipped (baseline was 1516)
