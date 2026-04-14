---
phase: "14"
plan: "01"
subsystem: engine/refusal
tags: [bug-fix, tdd, refusal, engine-polish]
dependency_graph:
  requires: []
  provides: [idempotent-refusal-rendering]
  affects: [src/token_world/engine/refusal.py]
tech_stack:
  added: []
  patterns: [idempotent-strip helper, TDD RED/GREEN]
key_files:
  created:
    - tests/test_engine/test_refusal_wrapper.py
  modified:
    - src/token_world/engine/refusal.py
decisions:
  - "Strip 'You try, but ' prefix from reason kwarg before format_map substitution — affects all templates using {reason}, safe for those that don't"
  - "Use module-level _strip_wrapper() helper with while-loop to collapse arbitrary nesting depth"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-14"
  tasks_completed: 2
  files_changed: 2
---

# Phase 14 Plan 01: Double-Wrapper Refusal Fix Summary

Idempotent refusal rendering via `_strip_wrapper()` — strips all leading "You try, but " prefixes from mechanic reason strings before templating, so `RefusalTemplate.render()` never produces a doubled wrapper.

## What Was Done

- **`_strip_wrapper(s)`** added as module-level helper in `refusal.py`: collapses any number of leading "You try, but " prefixes, then strips residual ". " padding.
- **`RefusalTemplate.render()`** applies `_strip_wrapper` to `format_map["reason"]` before `template.format_map()`, making the render idempotent for all templates that use `{reason}`.
- **`tests/test_engine/test_refusal_wrapper.py`** added: 9 test cases covering clean reason, pre-wrapped reason, doubly-nested reason, non-mechanic_check_failed path, and parametrized single-wrapper invariant across 5 reason variants. RED phase confirmed 5 failures before fix; GREEN phase confirmed all 25 tests pass (9 new + 16 existing in `test_refusal.py`).
- Full engine suite: **406 passed, 0 failures**.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 0498084 | fix(14-01): strip doubled 'You try, but' wrapper in RefusalTemplate (ENGINE-05) |

## Self-Check: PASSED

- `tests/test_engine/test_refusal_wrapper.py` — exists, 9 tests pass
- `src/token_world/engine/refusal.py` — modified, lint clean
- Commit `0498084` present in git log
