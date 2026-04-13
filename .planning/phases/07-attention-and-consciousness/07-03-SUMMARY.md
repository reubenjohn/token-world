---
phase: 07-attention-and-consciousness
plan: "03"
title: "MechanicContext.begin_long_action() helper — mechanic-facing API"
subsystem: mechanic-context
tags: [long-running-action, mechanic-api, graph-property, tdd]
requires: [07-01]
provides: [begin_long_action-helper]
affects: [mechanic-context, frozen-surface-test]
tech_stack:
  added: []
  patterns: [tdd-red-green, frozen-surface-registry]
key_files:
  created:
    - tests/test_mechanic/test_context_begin_long_action.py
  modified:
    - src/token_world/mechanic/context.py
    - tests/test_mechanic/test_context_api.py
decisions:
  - id: D-05
    summary: "begin_long_action returns a Mutation — no new apply() return type; mechanics append it to list[Mutation]"
  - id: D-15
    summary: "No import of long_running module from context.py; loose coupling via plain dict storage"
  - id: D-02
    summary: "current_long_action stored as graph property on actor node via kg.set()"
  - id: D-04
    summary: "Overwrites existing current_long_action — single active action per agent; conflict-refusal is mechanic check() responsibility"
metrics:
  duration_minutes: 15
  completed: "2026-04-13T18:54:31Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
---

# Phase 7 Plan 03: MechanicContext.begin_long_action() helper — Summary

**One-liner:** `ctx.begin_long_action()` writes canonical `current_long_action` dict to actor graph node, returning a `Mutation` that slots into the existing `list[Mutation]` protocol without any engine-layer changes.

## What Was Built

`MechanicContext.begin_long_action(action_text, turns_total, thresholds, attention_state=None) -> Mutation` — the single-line authoring API that seed mechanics (Plans 05-07) call to initiate any long-running action (sleep, drunk, autopilot travel).

### Stored Dict Schema (canonical on-graph contract)

This is the exact shape the engine hook (Plan 04) reads from the actor node:

```python
{
    "action_text": str,          # human-readable label for observations
    "turns_total": int | None,   # None = indefinite (D-16: drunkenness, etc.)
    "turns_elapsed": 0,          # always 0 on creation; hook advances each tick
    "thresholds": [              # list of plain dicts (no ThresholdSpec instances)
        {"property": "<node_id>.<prop>", "op": "<op>", "value": <json-safe>},
        ...
    ],
    "payload": {                 # mechanic extras; always present (empty dict if none)
        "attention_state": {...} # optional; present only when attention_state != None
    }
}
```

Key invariants:
- `turns_elapsed` is always `0` on creation — the Plan 04 hook is the sole advancer
- `payload` is always present (never absent) — `{}` when `attention_state=None`
- `thresholds` is always a `list` (defensive copy of caller's input)
- All values are JSON-serializable (satisfies `ALLOWED_PROPERTY_TYPES`)

### Why begin_long_action Returns a Mutation (D-05)

The `ChainExecutionEngine.execute()` protocol expects `apply()` to return `list[Mutation]`. Rather than introducing a new return type or a new `Mechanic` subclass, `begin_long_action` returns the `Mutation` produced by `kg.set(actor, "current_long_action", stored)`. Mechanics simply append it:

```python
def apply(self, ctx):
    return [
        ctx.set(ctx.actor, "is_sleeping", True),
        ctx.begin_long_action("sleeping", 8, thresholds=[...], attention_state={...}),
    ]
```

No engine changes required. The long-running action state is observable in diagnostics via the normal mutation log.

### Overwrite Behavior (D-04)

Calling `begin_long_action` when `current_long_action` is already set overwrites it silently. Single-active-action-per-agent is enforced by this design. If a mechanic needs to refuse on conflict (e.g., "you can't sleep while already sleeping"), it checks `ctx.query_node(ctx.actor, "current_long_action")` in its `check()` method. This is explicitly NOT begin_long_action's concern.

### Loose Coupling (D-15)

`context.py` does NOT import from `engine/long_running.py`. The helper writes plain Python dicts — no `ThresholdSpec` instances, no `LongRunningAction` dataclass. The `LongRunningAction.from_dict()` method in Plan 01 is the inverse (engine-side reconstruction). This keeps mechanic authoring simple: no dataclass imports needed.

## Tasks Executed

| Task | Description | Commit | Result |
|------|-------------|--------|--------|
| 1 | Implement begin_long_action (TDD RED→GREEN) + frozen surface update | f70c103 | 11 new tests green |
| 2 | Regression suite + lint + type check | (verification only) | 1443 passed, mypy clean |

## Test Coverage

`tests/test_mechanic/test_context_begin_long_action.py` — 11 tests:

- `test_begin_long_action_writes_to_actor_node` — full schema assertion
- `test_turns_total_none_stored_as_none` — indefinite action (D-16)
- `test_attention_state_none_yields_empty_payload` — consistent payload shape
- `test_empty_thresholds_list_stored` — no-threshold actions
- `test_returns_mutation_with_set_property_kind` — Mutation protocol (D-05)
- `test_overwrites_existing_current_long_action` — D-04 overwrite + old_value check
- `test_json_round_trip_through_graph_storage` — ALLOWED_PROPERTY_TYPES validation
- `test_thresholds_defensive_copy` — caller mutation safety
- `test_writes_to_actor_not_target` — D-02 actor-only write
- `test_attention_state_lives_under_payload_attention_state` — D-12 nesting
- `test_turns_elapsed_always_starts_at_zero` — hook contract clarification

`tests/test_mechanic/test_context_api.py` — `EXPECTED_CALLABLES` extended with `begin_long_action` entry (frozen surface registry).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test using kg.query() for absent property**
- **Found during:** Task 1 GREEN run
- **Issue:** `test_writes_to_actor_not_target` called `kg.query("bedroom", "current_long_action")` expecting `None`, but `KnowledgeGraph.query(node_id, property)` raises `KeyError` when the property is absent
- **Fix:** Changed to `kg.query("bedroom")` (returns all props dict) and asserted `"current_long_action" not in bedroom_props`
- **Files modified:** `tests/test_mechanic/test_context_begin_long_action.py`
- **Commit:** f70c103

**2. [Rule 1 - Bug] Removed unused variable flagged by ruff F841**
- **Found during:** Pre-commit hook
- **Issue:** `first_mutation = ctx.begin_long_action(...)` in overwrite test — variable unused (only `first_stored` from the graph query was needed)
- **Fix:** Replaced with inline call `ctx.begin_long_action(...)` (return value discarded)
- **Files modified:** `tests/test_mechanic/test_context_begin_long_action.py`
- **Commit:** f70c103

## Ready For

- **Plan 04** (engine hook): reads `current_long_action` dict off actor node using exactly this schema
- **Plans 05-07** (seed mechanics): call `ctx.begin_long_action(...)` as the single-line LRA initiation API

## Known Stubs

None. The helper is fully wired — writes to graph, returns Mutation. No placeholder values.

## Threat Flags

None. `begin_long_action` only writes to a single graph property on the actor node via the existing `kg.set()` path. No new network surface, no new auth paths, no new file access.

## Self-Check: PASSED

- `src/token_world/mechanic/context.py` — modified (begin_long_action method added) ✓
- `tests/test_mechanic/test_context_begin_long_action.py` — created (11 tests) ✓
- `tests/test_mechanic/test_context_api.py` — modified (EXPECTED_CALLABLES updated) ✓
- Commit `f70c103` exists ✓
- `uv run pytest tests/ -x -q` — 1443 passed (baseline 1431 + 11 new + 1 parametrize) ✓
- `uv run mypy src/token_world/mechanic/` — Success: no issues ✓
