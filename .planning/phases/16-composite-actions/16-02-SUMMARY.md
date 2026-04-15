---
phase: 16-composite-actions
plan: "02"
subsystem: engine/composite-actions
tags: [composite-actions, engine, iteration-loop, tick-summary, tdd]
dependency_graph:
  requires: [16-01]
  provides: [engine-composite-iteration, classified_actions-tick-field, SC-3-regression-suite]
  affects: [engine.py, models.py, summary_writer.py, yield_signal.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, per-sub-action-iteration, refuse-continues-policy, first-yield-wins]
key_files:
  created:
    - tests/test_engine/test_composite_actions.py
  modified:
    - src/token_world/engine/engine.py
    - src/token_world/engine/models.py
    - src/token_world/engine/summary_writer.py
    - src/token_world/operator/yield_signal.py
decisions:
  - "refuse-continues: a check-failed sub-action does not block subsequent sub-actions (multi-action only)"
  - "first-yield-wins: first no-match sub-action halts tick, subsequent sub-actions not evaluated"
  - "§E6 preserved for single-sub-action: if all sub-actions fail check(), returns mechanic_check_failed (not ok)"
  - "conservation check runs once on all combined mutations (T-16-04 mitigation)"
  - "_handle_execute_composite introduced; _handle_execute retained for LRA + error paths"
metrics:
  duration: ~35 minutes
  completed: 2026-04-14
  tasks_completed: 2
  files_modified: 5
---

# Phase 16 Plan 02: Composite Action Engine Wiring + Test Suite Summary

`run_tick` now iterates `verdict.actions` list, executing each sub-action independently through match → decide → execute with first-yield-wins and refuse-continues policies; `TickSummary` gains a `classified_actions` list field; 6-test SC-3 regression suite added.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| T1 | Write composite-action regression tests (TDD RED) | 552c1e5 | tests/test_engine/test_composite_actions.py |
| T2 | Wire engine + summary schema for composite actions | 552c1e5 | engine.py, models.py, summary_writer.py, yield_signal.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored §E6 check-failed refusal for single-sub-action case**
- **Found during:** Task 2 verification (`uv run pytest tests/test_engine/ -x -q`)
- **Issue:** `_handle_execute_composite` treated check-failed sub-actions as "refuse-continues" and returned `ok` when only one sub-action existed and its check() failed. Broke `test_run_tick_primary_check_failed_is_honest_refusal`.
- **Fix:** Added post-loop guard: if `all_primary_mutations` is empty AND all sub-traces have `check_result.passed == False`, return `refused` with `reason_code="mechanic_check_failed"`.
- **Files modified:** `src/token_world/engine/engine.py`
- **Commit:** 552c1e5

**2. [Rule 1 - Bug] Added unhandled-decision type guard for non-VerdictOk path**
- **Found during:** Task 2 verification
- **Issue:** Old code had an `else: raise TypeError("Unhandled Decision type")` branch after the execute/yield/refuse if-chain. New code replaced that with direct `_handle_refuse` call, breaking `test_run_tick_unhandled_decision_type_writes_error_summary` which patches `decide()` to return an unknown type.
- **Fix:** Added `isinstance(decision, RefuseDecision)` check before `_handle_refuse`; raises `TypeError` with `tick_ctx.set_summary(status="error")` if not a `RefuseDecision`.
- **Files modified:** `src/token_world/engine/engine.py`
- **Commit:** 552c1e5

**3. [Rule 2 - Style] Ruff E501 lines in test file**
- **Found during:** Pre-commit hook
- **Fix:** Wrapped long assert message strings into parenthesized multi-line form.
- **Commit:** 552c1e5

## Test Results

- 6/6 composite-action tests pass (SC-3 regression suite)
- 417/417 engine tests pass (full back-compat)
- 2022 passed, 14 skipped (full suite excluding pre-existing traceability drift)
- 1 pre-existing failure: `tests/test_meta/test_requirements_traceability.py` — phase 19 traceability drift, unrelated (confirmed pre-existing from Wave 1)
- Ruff clean: `All checks passed!`
- mypy clean: `Success: no issues found in 16 source files`

## Key Policy Implementations

| Policy | Implementation |
|--------|---------------|
| First-yield-wins | First `NoMatchResult` sub-action → immediate `_handle_yield`; loop breaks |
| Refuse-continues | `RefuseDecision` sub-action logged at DEBUG; loop continues to next sub-action |
| All-refused | After loop, if `sub_execute_decisions` empty → re-run `decide()` on first CA → `_handle_refuse` |
| §E6 check-failed | After execute loop, if no mutations AND all traces check-failed → return `refused` |
| Conservation | Single `verify()` call on all combined mutations after loop (T-16-04) |

## Known Stubs

None — all changes are complete and wired. `classified_actions` list field is fully populated from `verdict.actions` for every composite tick.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary surfaces introduced. T-16-04 (double-count) mitigated by single conservation check after all sub-actions complete.

## Self-Check: PASSED

- `tests/test_engine/test_composite_actions.py` exists with 6 test functions ✓
- `for classified_action in verdict.actions` in engine.py ✓
- `classified_actions` field in TickSummary (models.py) ✓
- `classified_actions` kwarg in build_tick_summary (summary_writer.py) ✓
- `yield_signal.py` docstring notes per-sub-action contract ✓
- Commit 552c1e5 exists ✓
- SC-3: `test_multi_verb_two_mechanics` passes ✓
- SC-3: `test_multi_verb_first_sub_refused_second_runs` passes ✓
- SC-3: `test_multi_verb_first_sub_yields_halts_tick` passes ✓
- SC-4: `SCHEMA_VERSION = 2.0` ✓
- SC-2 back-compat: `v.classified.verb == 'x'` ✓
