---
phase: 06-resident-agent-end-to-end-loop
plan: "00"
subsystem: engine
tags: [tick-result, dataclass, groundedness, scoring, visibility-projector]

requires:
  - phase: 05-simulation-engine
    provides: SimulationEngine.run_tick, TickResult dataclass, VisibilityProjector.project_for

provides:
  - TickResult.projected_state field (dict | None) on the ok path
  - TickResult.ok() classmethod accepts projected_state keyword arg
  - Wave-1 plans (06-05 TurnScorer) can read result.projected_state without private-attribute access

affects:
  - 06-05-PLAN.md (TurnScorer reads result.projected_state for observation_groundedness metric)

tech-stack:
  added: []
  patterns:
    - "Minimal field extension: add default-None fields to frozen dataclasses for backward compat"
    - "Reuse already-computed values: pass projection dict through to TickResult rather than re-projecting"

key-files:
  created:
    - tests/test_engine/test_engine_projected_state.py
  modified:
    - src/token_world/engine/engine.py

key-decisions:
  - "projected_state is the exact projection dict already passed to Observer.synthesize — reused, not re-computed"
  - "Field defaults to None so all Phase 5 TickResult construction (ok/yielded/refused) stays backwards-compatible"
  - "Only the ok path populates projected_state; yield/refuse paths have None (no observer call on those paths)"
  - "engine/__init__.py required no changes: TickResult was already exported and the new field is transparent"

patterns-established:
  - "Frozen-dataclass extension: appending an Optional field with None default preserves positional call-sites"

requirements-completed:
  - AUTO-06

duration: 18min
completed: 2026-04-13
---

# Phase 06 Plan 00: Wave-0 Prep — TickResult.projected_state Summary

**TickResult gains a `projected_state: dict | None` field populated on the execute path, exposing the VisibilityProjector output used by Observer.synthesize so Phase 6 Plan 05 (TurnScorer) can compute observation_groundedness without private-attribute access or duplicate projection work.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-13T15:06:00Z
- **Completed:** 2026-04-13T15:24:00Z
- **Tasks:** 1 (TDD)
- **Files modified:** 2

## Accomplishments

- Added `projected_state: dict | None = None` as the last field on the `TickResult` frozen dataclass — backwards-compatible with all Phase 5 test helpers.
- Extended `TickResult.ok()` classmethod to accept `projected_state` as an optional keyword argument and pass it through to the constructor.
- Wired `_handle_execute` to pass `projected_state=projection` to `TickResult.ok(...)` reusing the dict already computed for `Observer.synthesize` — no extra projector call, no potential drift.
- Verified yield and refuse paths leave `projected_state=None` by default (no code change needed on those paths).
- 4 new tests, 0 regressions (1223 passed vs 1219 baseline).

## Task Commits

1. **Task 1: Add projected_state field to TickResult + populate on EXECUTE path** — `40a91a6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/token_world/engine/engine.py` — Added `projected_state` field to `TickResult` dataclass; extended `ok()` classmethod; wired populate in `_handle_execute`
- `tests/test_engine/test_engine_projected_state.py` — 4 tests covering ok/yield/refuse paths and pure classmethod unit test

## Decisions Made

- `projected_state` reuses the `projection` local variable already in `_handle_execute` (assigned at line `projection = self._projector.project_for(actor)`). This means the scorer sees exactly the same snapshot the observer synthesized against — no drift, no extra cost.
- The `TickResult.ok()` signature change makes `trace` accept `None` (typed as `ExecutionTrace | None` rather than `ExecutionTrace`) to match actual usage patterns discovered in the test suite. This is a minor correctness improvement consistent with the field's existing Optional-like usage on the engine_error refusal path.
- `engine/__init__.py` unchanged — `TickResult` was already in `__all__`; the new field is transparent to all importers.

## Deviations from Plan

None — plan executed exactly as written. The `engine/__init__.py` no-change prediction in the plan's action list was confirmed correct.

## Issues Encountered

None. Pre-existing ruff warnings in unrelated test files (test_models.py, test_use_cases.py, etc.) were confirmed out-of-scope and not touched.

## Known Stubs

None — no placeholder values or wired-but-empty data flows introduced.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or trust-boundary schema changes.

## Next Phase Readiness

Wave-1 plans (06-01 ResidentAgent, 06-02 AgentMemory, 06-03 TickCompressor, 06-04 PlaytestRunner, 06-05 TurnScorer) are all unblocked. Specifically:
- **06-05 TurnScorer** can read `result.projected_state.keys()` for `observation_groundedness` metric (D-12 #2) without private-attribute access to `engine._projector`.
- All Phase 5 engine tests continue to pass; no downstream breakage.

---
*Phase: 06-resident-agent-end-to-end-loop*
*Completed: 2026-04-13*
