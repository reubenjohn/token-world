---
phase: "14"
plan: "02"
subsystem: mechanic-seeds
tags: [seeds, corpus, REQ-V12-SEEDS-01, inventory, social, observation, craft]
dependency_graph:
  requires: []
  provides:
    - examine.py — ExamineMechanic (actor.last_examined property snapshot)
    - pet.py — PetMechanic (mood ladder on animal entities)
    - sharpen.py — SharpenMechanic (sharpness float increment on tool entities)
    - hum.py — HumMechanic (actor.humming=True toggle)
    - drop.py — DropMechanic (carrying edge removal + room contains edge)
  affects:
    - scripts/seed_starter_universe.py (_KEEP_MECHANICS frozenset)
    - tests/test_mechanic/test_registry.py (seed corpus inventory list)
    - tests/test_cli/test_scaffold_mechanic.py (scaffold collision guard)
tech_stack:
  added: []
  patterns:
    - Mechanic subclass pattern (look.py template)
    - Mood ladder with string key lookup + clamp
    - AST-based frozenset membership assertion in tests
key_files:
  created:
    - src/token_world/mechanic/seeds/examine.py
    - src/token_world/mechanic/seeds/pet.py
    - src/token_world/mechanic/seeds/sharpen.py
    - src/token_world/mechanic/seeds/hum.py
    - src/token_world/mechanic/seeds/drop.py
    - tests/test_mechanic/test_seed_mechanics.py
  modified:
    - scripts/seed_starter_universe.py
    - tests/test_mechanic/test_registry.py
    - tests/test_cli/test_scaffold_mechanic.py
decisions:
  - "Drop mechanic uses 'carrying' relation (not 'holds') to remain independent of pickup.py — unification deferred to future refactor"
  - "Sharpen target fallback: ctx.target first, then actor carrying neighbor, then first non-whetstone tool in room"
  - "Examine fall-through: if target not co-located or not provided, examines the room itself — ensures mechanic always produces a mutation"
  - "pet.py mood default is 'neutral' for entities missing the property"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-14"
  tasks_completed: 2
  files_created: 6
  files_modified: 3
---

# Phase 14 Plan 02: Seed Corpus Expansion (examine, pet, sharpen, hum, drop) Summary

5 framework-level seed mechanics promoted from Willowbrook overnight run into `src/token_world/mechanic/seeds/`, all registered in `_KEEP_MECHANICS` so new universes ship without yielding on these common verbs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write 5 seed mechanic files | 16a36e5 | examine.py, pet.py, sharpen.py, hum.py, drop.py |
| 2 (RED) | Importability + _KEEP_MECHANICS tests | 4c4627e | tests/test_mechanic/test_seed_mechanics.py |
| 2 (GREEN) | Register in _KEEP_MECHANICS + fix collateral breakage | 197415e | seed_starter_universe.py, test_registry.py, test_scaffold_mechanic.py |

## Mechanic Summaries

**examine.py** — ExamineMechanic: reads visible node properties and writes `actor.last_examined = {"target": id, "props": snapshot}`. Falls back to examining the room when no valid target is named.

**pet.py** — PetMechanic: boosts first animal entity's `mood` one step up a fixed ladder (hostile→wary→neutral→content→purring, clamped). Requires `subtype="animal"` in actor's room.

**sharpen.py** — SharpenMechanic: increments target's `sharpness` float by 0.1, clamped at 1.0. Requires a whetstone (`subtype="tool"`, `material="stone"`) in actor's room. Target selection: ctx.target → carrying neighbor → first non-whetstone tool in room.

**hum.py** — HumMechanic: sets `actor.humming = True`. No preconditions beyond actor existence — always passes `check()`.

**drop.py** — DropMechanic: removes `actor --[carrying]--> item` edge and adds `room --[contains]--> item` edge. Requires at least one outgoing "carrying" edge (T-14-04 mitigation: check() enforces this).

## Verification

```
uv run pytest tests/test_mechanic/test_seed_mechanics.py -v  → 11 passed
uv run pytest -x -q (excluding pre-existing traceability drift) → 1993 passed, 14 skipped
python -c "from token_world.mechanic.seeds.examine import ExamineMechanic; print(ExamineMechanic.id)"  → "examine"
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_scaffold_mechanic used --id drop which now collides with seed**
- **Found during:** Task 2 (full suite run)
- **Issue:** `test_scaffolded_module_passes_validation` called `scaffold-mechanic --id drop`; since `drop.py` now ships with every scaffolded universe, the scaffold CLI refused with "already exists"
- **Fix:** Changed `--id drop` to `--id toss` (a non-seed name); updated the docstring to explain why
- **Files modified:** `tests/test_cli/test_scaffold_mechanic.py`
- **Commit:** 197415e

**2. [Rule 1 - Bug] TestSeedUniverse.test_scan_discovers_seeds had a hardcoded seed list**
- **Found during:** Task 2 (full suite run)
- **Issue:** `test_registry.py::TestSeedUniverse::test_scan_discovers_seeds` compared against a hardcoded sorted list of mechanic IDs missing the 5 new ones
- **Fix:** Added `"drop"`, `"examine"`, `"hum"`, `"pet"`, `"sharpen"` in sorted position to the expected list
- **Files modified:** `tests/test_mechanic/test_registry.py`
- **Commit:** 197415e

### Pre-existing Issues (out of scope, logged)

- `tests/test_meta/test_requirements_traceability.py::test_no_traceability_drift[active-milestone]` was already failing before this plan (drift spans phases 13–19 across REQUIREMENTS.md vs ROADMAP.md; confirmed by git stash check). Deferred to whichever plan addresses REQUIREMENTS.md for v1.2.

## Known Stubs

None — all 5 mechanics produce real graph mutations from graph state. No hardcoded empty values or placeholder text flow to observable output.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries introduced.

## Self-Check: PASSED

- `src/token_world/mechanic/seeds/examine.py` — FOUND
- `src/token_world/mechanic/seeds/pet.py` — FOUND
- `src/token_world/mechanic/seeds/sharpen.py` — FOUND
- `src/token_world/mechanic/seeds/hum.py` — FOUND
- `src/token_world/mechanic/seeds/drop.py` — FOUND
- `tests/test_mechanic/test_seed_mechanics.py` — FOUND
- Commit 16a36e5 — FOUND (feat: 5 seed files)
- Commit 4c4627e — FOUND (test: RED gate)
- Commit 197415e — FOUND (feat: GREEN gate + collateral fixes)
