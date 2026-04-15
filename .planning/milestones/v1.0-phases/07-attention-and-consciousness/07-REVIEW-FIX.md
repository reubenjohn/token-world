---
phase: 07-attention-and-consciousness
fixed_at: 2026-04-13T22:30:00Z
review_path: .planning/phases/07-attention-and-consciousness/07-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-04-13T22:30:00Z
**Source review:** .planning/phases/07-attention-and-consciousness/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### WR-01: `is_sleeping`, `is_traveling`, and `is_drunk` flags never cleared on LRA termination

**Files modified:**
`src/token_world/engine/long_running_hook.py`,
`src/token_world/mechanic/context.py`,
`src/token_world/mechanic/seeds/sleep.py`,
`src/token_world/mechanic/seeds/drunk.py`,
`src/token_world/mechanic/seeds/autopilot_travel.py`,
`tests/test_engine/test_long_running_hook.py`,
`tests/test_mechanic/test_seeds/test_sleep.py`,
`tests/test_mechanic/test_seeds/test_drunk.py`,
`tests/test_mechanic/test_seeds/test_autopilot_travel.py`,
`tests/test_mechanic/test_context_api.py`

**Commit:** 24ba293 (hook + IN-01), ee28559 (seed mechanics), bc23f79 (frozen surface)

**Applied fix:**
- Added `_apply_clear_on_end()` helper to `LongRunningHook` that reads `payload["clear_on_end"]` and applies each property mutation on both the interrupt and completion paths.
- Extended `ctx.begin_long_action()` with an optional `clear_on_end: dict | None = None` parameter that stores the dict in the LRA payload.
- Updated `sleep.py` to pass `clear_on_end={"is_sleeping": False}`.
- Updated `drunk.py` to pass `clear_on_end={"is_drunk": False}`.
- Updated `autopilot_travel.py` to add `clear_on_end={"is_traveling": False}` in the 2-step payload augment.
- Regression tests: 7 new hook tests covering interrupt/completion/continuing cases for clear_on_end, plus per-mechanic payload shape tests.

### WR-02: `assert` used for control flow in production path in `autopilot_travel.py`

**Files modified:**
`src/token_world/mechanic/seeds/autopilot_travel.py`,
`tests/test_mechanic/test_seeds/test_autopilot_travel.py`

**Commit:** ee28559

**Applied fix:**
Replaced `assert path is not None and len(path) >= 2` with an explicit `if path is None or len(path) < 2: return []` guard. The guard is silent (graceful degradation) since `check()` guarantees this path is unreachable in correct usage, matching the reviewer's recommended approach.
Regression tests: 3 new tests — `apply()` returns `[]` when path is None, when path has one node, and does not raise `AssertionError`/`AttributeError`.

### WR-03: TOCTOU / empty LRA observation fallback in `engine.py`

**Files modified:**
`src/token_world/engine/engine.py`,
`tests/test_engine/test_engine_long_running_integration.py`

**Commit:** 2e0a6be

**Applied fix:**
Added an explicit `if not lra:` guard after the `or {}` fallback in `_handle_long_running_tick`. When triggered, it logs a `WARNING` with `"LRA disappeared between has_active_long_action check and _handle_long_running_tick for actor=..."` and falls through to the hook (which returns `HookResult.inactive()`). This documents the TOCTOU condition clearly in logs without crashing.
Regression test: calls `_handle_long_running_tick` directly with `current_long_action=None` and asserts the warning is logged.

### IN-01: Redundant `KeyError` in `except (KeyError, Exception)` in `long_running_hook.py`

**Files modified:** `src/token_world/engine/long_running_hook.py`

**Commit:** 24ba293

**Applied fix:**
Changed `except (KeyError, Exception):` to `except Exception:` — `KeyError` is a subtype of `Exception` so the original clause was redundant. No test needed; pure refactor.

### IN-02: `sober_up` does not clear `is_drunk` flag when sobriety reaches 1.0

**Files modified:**
`src/token_world/mechanic/seeds/sober_up.py`,
`tests/test_mechanic/test_seeds/test_sober_up.py`

**Commit:** ee28559

**Applied fix:**
Added `if new_sobriety >= 1.0: mutations.append(ctx.set(actor_id, "is_drunk", False))` in `sober_up.apply()`. This stops the `_find_drunk_actors_with_room_to_recover` filter from matching fully-sober actors on subsequent ticks, and clears the stale flag from projections.
Regression tests: 5 new tests covering the clear at 1.0, exact 1.0, no-clear below 1.0, and mutation counts.

### IN-03: `autopilot_advance` silently accepts `next_index=0`

**Files modified:**
`src/token_world/mechanic/seeds/autopilot_advance.py`,
`tests/test_mechanic/test_seeds/test_autopilot_advance.py`

**Commit:** 6a8c0f2

**Applied fix:**
Added `if next_index <= 0:` guard before the main advance logic. When triggered, logs `WARNING: autopilot_advance: next_index=0 for actor {id}; skipping (likely corrupt LRA payload)` and `continue`s without producing any mutations.
Regression tests: 3 new tests — returns `[]`, no location mutation, warning logged.

---

_Fixed: 2026-04-13T22:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
