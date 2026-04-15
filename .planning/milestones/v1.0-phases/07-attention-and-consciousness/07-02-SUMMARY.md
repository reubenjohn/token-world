---
phase: 07-attention-and-consciousness
plan: 02
subsystem: engine
tags: [visibility, attention, projection, perception, suppress, boost]

# Dependency graph
requires:
  - phase: 05-simulation-engine
    provides: VisibilityProjector with 4-stage pipeline (D-14)
  - phase: 07-attention-and-consciousness
    provides: 07-01 LongRunningAction/ThresholdSpec/ThresholdEvaluator foundation
provides:
  - VisibilityProjector.project_for extended with backward-compatible attention_state kwarg
  - _apply_attention_state pure helper implementing suppress-then-boost Stage 5
  - Module-level project_for convenience function updated to accept attention_state
  - 21 deterministic tests covering all attention_state edge cases
affects:
  - 07-04 (engine hook — will pass attention_state from actor.current_long_action.payload)
  - 07-05, 07-06, 07-07 (seed mechanics — will author attention_state payloads)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stage 5 attention modulation: suppress-then-boost order in _apply_attention_state"
    - "attention_boosted top-level key on projected node entries (separate from properties)"
    - "Defensive-copy pattern in Stage 5 matches Stages 2-4 (no input mutation)"

key-files:
  created:
    - tests/test_engine/test_visibility_attention.py
  modified:
    - src/token_world/engine/visibility.py

key-decisions:
  - "attention_state=None (default) and attention_state={} both skip Stage 5 entirely — falsy guard ensures byte-for-byte backward compatibility"
  - "Suppress runs before boost (deterministic order): boosting a suppressed key yields no attention_boosted entry"
  - "attention_boosted is a separate top-level key, NOT inside properties — Observer can reference both the property (still in properties) and its prominence marker (attention_boosted)"
  - "Unknown top-level keys in attention_state silently ignored (forward-compat with future stages)"
  - "Stage 5 is a pure function (_apply_attention_state): takes projection dict, returns new dict, no mutations"

patterns-established:
  - "attention_state dict shape: {suppress: list[str], boost: list[str]} — other keys silently ignored"
  - "Projection stages are pure transforms returning new dicts; Stage 5 follows same defensive-copy pattern"

requirements-completed:
  - SIM-10

# Metrics
duration: 15min
completed: 2026-04-13
---

# Phase 07 Plan 02: VisibilityProjector attention_state extension (Stage 5) Summary

**Backward-compatible attention_state kwarg on VisibilityProjector.project_for: suppress removes properties from projection, boost copies them to a separate attention_boosted top-level key, with suppress-first deterministic ordering**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-13T00:00:00Z
- **Completed:** 2026-04-13T00:15:00Z
- **Tasks:** 2 (TDD task 1: RED+GREEN; task 2: full-suite lint+type verification)
- **Files modified:** 2

## Accomplishments

- Extended `VisibilityProjector.project_for` with `attention_state: dict | None = None` — all 3 existing engine.py call sites continue to work unchanged
- Implemented `_apply_attention_state` as a pure Stage 5 helper: suppress removes property keys from all nodes, boost copies post-suppression values to `attention_boosted` top-level key
- Updated module-level `project_for` convenience function to forward `attention_state`
- 21 new deterministic tests covering all specified behaviors: default compat, suppress, boost, combined, suppress-wins-over-boost, empty dicts, unknown keys, missing props, mutation safety, multi-node application, module-level function

## Task Commits

1. **Task 1+2: attention_state extension + full verification** - `d135ce1` (feat)

**Plan metadata commit:** (included in state update commit below)

## Files Created/Modified

- `src/token_world/engine/visibility.py` — extended `project_for` signature, added `_apply_attention_state` Stage 5 method, updated module-level function
- `tests/test_engine/test_visibility_attention.py` — 21 new tests across 7 test classes

## Decisions Made

- **Suppress-then-boost order:** Boost reads the post-suppression projection, so boosting a key that was also suppressed yields no `attention_boosted` entry for that key. This is deterministic and consistent with grounding (can't boost what you can't see).
- **attention_boosted as a separate top-level key:** Not nested inside `properties`. This keeps the grounding constraint clean — the property still appears in `properties` for reference, but the Observer prompt can call out boosted properties as especially salient.
- **Falsy guard for Stage 5:** `if attention_state:` skips Stage 5 for both `None` and `{}`, preserving byte-for-byte backward compatibility with pre-Phase-7 output.
- **Forward-compat with unknown keys:** Unrecognized top-level keys in `attention_state` are silently ignored, so future stages can extend the dict schema without breaking existing callers.

## Deviations from Plan

None — plan executed exactly as written. Ruff auto-fixed 3 style issues in the test file (unused `pytest` import) during the pre-commit hook; this is normal hook behavior, not a deviation.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `VisibilityProjector.project_for(actor_id, attention_state=...)` is ready for Plan 04 (engine hook) to consume
- Plan 04 will read `attention_state` from `actor.current_long_action.payload` and pass it to the projector
- Plans 05-07 (seed mechanics: sleep, autopilot_travel, drunk) will author `attention_state` dicts in their `LongRunningAction` payloads
- All 1431 tests pass; ruff + mypy clean on visibility.py

## Self-Check

- [x] `src/token_world/engine/visibility.py` exists and has `_apply_attention_state`
- [x] `tests/test_engine/test_visibility_attention.py` exists with 21 tests
- [x] Commit `d135ce1` exists
- [x] `uv run pytest tests/ -x -q` → 1431 passed, 14 skipped, 36 deselected
- [x] `git diff ccf36a0..HEAD --stat` shows only the 2 scope files

---
*Phase: 07-attention-and-consciousness*
*Completed: 2026-04-13*
