---
phase: 05-simulation-engine
plan: "02"
title: "Deterministic matcher + WorldPropertyMatcher / DecayMatcher / TickMatcher"
subsystem: engine
tags:
  - engine
  - matcher
  - deterministic
  - involuntary-mechanics
  - pydantic
dependency_graph:
  requires:
    - "05-01 (ClassifiedAction, MatchedResult, NoMatchResult Pydantic models)"
    - "04-mechanic-framework (Mechanic ABC, MechanicRegistry, matchers.py)"
  provides:
    - "DeterministicMatcher.match(classified, registry, graph) → MatchResult"
    - "score_mechanic helper (+3 verb, +2 target type, +1 actor type)"
    - "VerbMatcher(verb) for voluntary mechanic verb declaration"
    - "WorldPropertyMatcher(property_name) for world-level property reactions"
    - "DecayMatcher() for per-tick node decay sweep"
    - "TickMatcher() for unconditional per-tick passive invocation"
    - "MechanicRegistry.voluntary_mechanics() and involuntary_mechanics()"
  affects:
    - "05-03 Decider (consumes MatchResult from DeterministicMatcher)"
    - "05-07 Passive Sweep (consumes DecayMatcher, TickMatcher, WorldPropertyMatcher)"
    - "05-08 Engine Orchestrator (wires DeterministicMatcher into pipeline)"
tech_stack:
  added: []
  patterns:
    - "Frozen dataclass matchers with match(mutation) instance methods"
    - "_node_type_matches checks both 'type' and 'subtype' independently (not as fallback)"
    - "Alphabetical tie-breaking via sort key=(-score, mechanic_id)"
    - "Matcher union type extended; existing Phase 2 matchers preserved"
key_files:
  created:
    - src/token_world/engine/matcher.py
    - tests/test_engine/test_matcher.py
    - tests/test_mechanic/test_matchers_world_decay_tick.py
  modified:
    - src/token_world/mechanic/matchers.py (added VerbMatcher + 3 Phase-5 matchers)
    - src/token_world/mechanic/__init__.py (exported new matchers)
    - src/token_world/mechanic/registry.py (added voluntary_mechanics / involuntary_mechanics)
decisions:
  - "Used _node_type_matches checking both 'type' and 'subtype' independently instead of 'type or subtype' short-circuit — graph stores node_type as type='entity'/'agent' which would shadow subtype='container' with the fallback pattern"
  - "candidates field belongs to NoMatchResult only (per models.py contract); MatchedResult does not carry it — plan pseudocode that built candidates in the matched path was removed as unused dead code"
metrics:
  duration_minutes: 35
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 3
  tests_added: 30
  completed_date: "2026-04-13"
---

# Phase 5 Plan 02: Deterministic Matcher Summary

Matcher infrastructure for the Phase 5 simulation engine pipeline. Plans 05-03 (Decider), 05-07 (Passive Sweep), and 05-08 (Engine Orchestrator) can now consume this output.

## One-liner

Deterministic mechanic scorer (+3 verb, +2 target type, +1 actor type) with alphabetical tie-breaking, plus three passive-sweep matcher primitives (WorldPropertyMatcher, DecayMatcher, TickMatcher) and the VerbMatcher used by voluntary mechanics.

## What Was Built

### Task 1: New matcher primitives (d66dc7c)

Added four new matchers to `src/token_world/mechanic/matchers.py`, extending the existing `Matcher` union type:

- `VerbMatcher(verb)` — declares a verb for voluntary mechanic dispatch (D-09). The `DeterministicMatcher` inspects `mechanic.watches()` for VerbMatcher instances to compute the verb-match score component.
- `WorldPropertyMatcher(property_name)` — event-driven matcher that returns True for `set_property` mutations on the `_world` sentinel node for the declared property (D-10, GAP-ENG09 closure).
- `DecayMatcher()` — not event-driven; `match()` always returns False. Passive sweep calls `matches_node(node_props)` to identify nodes with `decay_period` (D-17).
- `TickMatcher()` — not event-driven; `match()` always returns False. Passive sweep dispatches these mechanics unconditionally once per tick (D-17).

All four are frozen dataclasses following the existing Phase 2 pattern. The `Matcher` union type was extended to include all seven matcher types. `mechanic/__init__.py` exports all new matchers.

14 tests in `tests/test_mechanic/test_matchers_world_decay_tick.py`.

### Task 2: DeterministicMatcher + registry split (3aaaa39)

Created `src/token_world/engine/matcher.py` with:

- `score_mechanic(mechanic, classified, graph) → int`: scores a single voluntary mechanic. Checks `watches()` for `VerbMatcher` (+3), checks both `type` and `subtype` node properties against `target_types`/`actor_types` attrs and `tags` (+2 target, +1 actor). The `_node_type_matches` helper evaluates both fields independently so `subtype="container"` is not shadowed by the graph's built-in `type="entity"`.

- `DeterministicMatcher.match(classified, registry, graph) → MatchResult`: calls `registry.voluntary_mechanics()`, scores each, sorts by `(-score, mechanic_id)` for deterministic tie-breaking, returns `MatchedResult` (winner) or `NoMatchResult` (all-zero). Reasoning field distinguishes "clear winner" vs "tie-break vs <other_id>".

Added to `MechanicRegistry`:
- `voluntary_mechanics()` — returns instances of all mechanics with `voluntary=True`
- `involuntary_mechanics()` — returns instances of all mechanics with `voluntary=False`

16 tests in `tests/test_engine/test_matcher.py`. mypy: zero errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _node_type_matches checks type and subtype independently**
- **Found during:** Task 2 — 4 tests failed because `score_mechanic` used `target_props.get("type") or target_props.get("subtype")` which short-circuits on the graph's built-in `type="entity"`, never reaching `subtype="container"`.
- **Fix:** Replaced with `_node_type_matches()` helper that loops over both `"type"` and `"subtype"` keys and checks each against `accepted = set(tags) | set(hints)`.
- **Files modified:** `src/token_world/engine/matcher.py`
- **Commit:** 3aaaa39

**2. [Rule 1 - Bug] Removed unused candidates dead code in MatchedResult path**
- **Found during:** Task 2 — ruff F841 flagged `candidates` variable built in the matched success path. `MatchedResult` has no `candidates` field (per models.py). The plan's pseudocode built candidates for the matched path but the actual Pydantic model doesn't carry it — candidates belong to `NoMatchResult` only.
- **Fix:** Removed the dead `candidates = [...]` line from the matched path; test updated to verify `NoMatchResult.candidates` is the correct location.
- **Files modified:** `src/token_world/engine/matcher.py`, `tests/test_engine/test_matcher.py`
- **Commit:** 3aaaa39

**3. [Rule 1 - Bug] Test helper actor_type test used wrong props**
- **Found during:** Task 2 — `_make_graph(actor_props={"type": "agent"})` caused `TypeError: got multiple values for keyword argument 'type'` because `add_node(node_type="agent")` already stores `type="agent"` and the prop collision crashed the test.
- **Fix:** Updated `test_actor_type_match_adds_1` to not pass `type` in actor_props — the graph's built-in `type="agent"` from `node_type` is sufficient and already matched correctly.
- **Files modified:** `tests/test_engine/test_matcher.py`
- **Commit:** 3aaaa39

## Known Stubs

None. All functionality is fully implemented.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or trust boundary schema changes introduced.

## Self-Check: PASSED

All key files exist. Both task commits found in git log. 30 tests pass across new test files. Full suite: 1037 passed, 14 skipped, 0 failures.
