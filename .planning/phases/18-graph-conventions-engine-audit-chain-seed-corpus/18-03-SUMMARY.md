---
phase: 18
plan: "03"
subsystem: mechanic/seeds
tags: [chain-mechanics, PropertyChangeMatcher, EdgeMatcher, seed-corpus]
key-files:
  created:
    - src/token_world/mechanic/seeds/mood_change_watcher.py
    - src/token_world/mechanic/seeds/contains_edge_watcher.py
    - src/token_world/mechanic/seeds/temperature_watcher.py
    - tests/test_mechanic/test_seeds/test_chain_seed_mechanics.py
  modified:
    - tests/test_mechanic/test_registry.py
decisions:
  - "mood_change_watcher writes previous_mood rather than the post-change value, enabling downstream mechanics to see the full transition"
  - "contains_edge_watcher uses ctx.neighbors(relation='contains') for item count — no ctx.edges() API needed"
  - "temperature_watcher uses threshold classification table, distinct from environmental_reaction which handles fire spread side-effects"
metrics:
  duration: "~15 min"
  completed: "2026-04-14"
  tasks: 3
  files: 5
---

# Phase 18 Plan 03: Chain Seed Mechanics — Summary

Three new involuntary seed mechanics demonstrating PropertyChangeMatcher and EdgeMatcher
patterns for REQ-V12-DASHBOARD-06.

## One-liner

Adds mood_change_watcher (PropertyChangeMatcher/mood), contains_edge_watcher (EdgeMatcher/contains), and temperature_watcher (PropertyChangeMatcher/temperature) with 37 passing tests and registry auto-discovery audit.

## Mechanics added

| Mechanic | Matcher | Trigger | Side Effect |
|---|---|---|---|
| `mood_change_watcher` | PropertyChangeMatcher(mood) | Any mood property change | Writes `previous_mood` for chain triggers |
| `contains_edge_watcher` | EdgeMatcher(contains, add+remove) | Item enters/leaves container | Writes `item_count` on container |
| `temperature_watcher` | PropertyChangeMatcher(temperature) | Temperature property change | Classifies to `temp_state` label |

## Deviations from Plan

### Auto-fix: `ctx.edges()` does not exist

Found during implementation that `MechanicContext` has no `edges()` method. Used `ctx.neighbors(relation="contains")` instead — equivalent result, correct API.

### Auto-fix: `add_edge` takes **kwargs not dict

Tests initially called `kg.add_edge(src, dst, {"relation": "contains"})` — API uses `**kwargs`. Fixed to `kg.add_edge(src, dst, relation="contains")`.

### Auto-fix: `MechanicRegistry.has()` does not exist

Registry audit tests initially used `reg.has(id)` — method doesn't exist. Fixed to `{m.id for m in reg.list_mechanics()}`.

### Auto-fix: ruff UP038 — `isinstance` tuple syntax

Fixed `isinstance(temp, (int, float))` to `isinstance(temp, int | float)` per modern Python union syntax.
