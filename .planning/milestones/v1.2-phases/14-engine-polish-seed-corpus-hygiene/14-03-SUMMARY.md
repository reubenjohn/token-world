---
phase: "14"
plan: "03"
subsystem: seed-graph
tags: [seeds, corpus, REQ-V12-SEEDS-01, REQ-V12-TOOLING-02, entities, cli-flag]
dependency_graph:
  requires:
    - "14-02 — _KEEP_MECHANICS frozenset, seed_starter_universe.py baseline"
  provides:
    - "bench entity (weathered=True, furniture subtype) in garden"
    - "chicken_coop entity (chickens_inside=3, door_latched, eggs_today, feed_level) in garden"
    - "broken_gate entity (broken=True, latched=False, repair_progress=0.0) in garden"
    - "--preserve-mechanics argparse flag skips _prune_seed_mechanics()"
    - "Loud stderr WARNING in _prune_seed_mechanics listing files-to-remove before unlink"
  affects:
    - scripts/seed_starter_universe.py
    - tests/test_scripts/test_seed_starter.py (new)
tech_stack:
  added: []
  patterns:
    - "importlib.util.spec_from_file_location for testing scripts/ without __init__.py"
    - "kg.nodes(subtype=..., prop=...) keyword-filter + kg.query(id, prop) for entity assertions"
key_files:
  created:
    - tests/test_scripts/__init__.py
    - tests/test_scripts/test_seed_starter.py
  modified:
    - scripts/seed_starter_universe.py
decisions:
  - "seed() takes preserve_mechanics kwarg; main() passes args.preserve_mechanics — flag wires through cleanly without globals"
  - "_prune_seed_mechanics collects to_remove list first, prints WARNING before any unlink — warning is always accurate"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-14"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 14 Plan 03: SC-3 Entities + SC-4 --preserve-mechanics Flag Summary

Three new garden entities (bench with weathered=True, chicken_coop with livestock hooks, broken_gate with repair hook) added to `_seed_graph()`; `--preserve-mechanics` flag added to argparse so operators can re-seed without accidentally deleting authored mechanics.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add bench, chicken_coop, broken_gate to _seed_graph() | 1f1421c | scripts/seed_starter_universe.py |
| 2 | --preserve-mechanics flag + stderr warning + tests | 1f1421c | scripts/seed_starter_universe.py, tests/test_scripts/test_seed_starter.py |

## Verification

```
uv run pytest tests/test_scripts/test_seed_starter.py -v  → 7 passed
uv run pytest -x -q (excluding pre-existing traceability drift) → 2000 passed, 14 skipped
uv run python scripts/seed_starter_universe.py --help | grep preserve-mechanics → flag shown
uv run ruff check scripts/seed_starter_universe.py → All checks passed
```

## Entity Hook Properties Added

**bench** (garden, subtype=furniture): `weathered=True`, `material="wood"`, `planks_intact=5`
**chicken_coop** (garden, subtype=structure): `chickens_inside=3`, `door_latched=True`, `eggs_today=0`, `feed_level=0.6`
**broken_gate** (garden, subtype=gate): `broken=True`, `latched=False`, `repair_progress=0.0`, `material="wood"`

## Deviations from Plan

None — plan executed exactly as written. `_prune_seed_mechanics` refactored from removing-then-logging to collecting `to_remove` first (enabling the WARNING print before any unlink), which was the plan's stated intent.

## Known Stubs

None — all three entities have real hook property values. No placeholder text flows to observable output.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries.

## Self-Check: PASSED

- `tests/test_scripts/test_seed_starter.py` — FOUND
- `tests/test_scripts/__init__.py` — FOUND
- Commit 1f1421c — FOUND (feat(14-03): SC-3 entities + SC-4 --preserve-mechanics flag)
- bench nodes in _seed_graph(): present (weathered=True confirmed by test)
- chicken_coop nodes: present (chickens_inside=3 confirmed by test)
- broken_gate nodes: present (broken=True confirmed by test)
- --preserve-mechanics in --help output: confirmed
