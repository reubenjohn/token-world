---
phase: 07-attention-and-consciousness
plan: 04
subsystem: engine
tags: [long-running-actions, engine-hook, tick-pipeline, playtest-runner, phase7]
dependency_graph:
  requires: [07-01, 07-02, 07-03]
  provides: [engine-lra-hook, run-tick-continuation, tick-summary-lra-field, runner-lra-integration]
  affects: [engine, playtest-runner, observer]
tech_stack:
  added: []
  patterns:
    - LongRunningHook class pattern (frozen HookResult dataclass, stateless process() method)
    - run_tick(str | None) continuation routing pattern
    - is True guard for MagicMock-safe boolean check
key_files:
  created:
    - src/token_world/engine/long_running_hook.py
    - tests/test_engine/test_long_running_hook.py
    - tests/test_engine/test_engine_long_running_integration.py
    - tests/test_playtest/test_runner_long_running.py
  modified:
    - src/token_world/engine/engine.py
    - src/token_world/engine/models.py
    - src/token_world/engine/summary_writer.py
    - src/token_world/engine/__init__.py
    - src/token_world/engine/observer.py
    - src/token_world/playtest/runner.py
decisions:
  - D-06: LongRunningHook called only on _handle_long_running_tick path (post-execute, pre-passive-sweep position is moot since hook skips execute stage entirely)
  - D-07: run_tick(None, actor) routes to synthetic continuation path; classifier/matcher/decider entirely skipped
  - D-11: Real action_text + active LRA → clear current_long_action before classifier runs (implicit cancellation)
  - D-17: TickSummary.long_running_action optional field added; schema_version stays 1
  - D-22: "Time passes. You continue {action_text}." static template for continuing case (no LLM call)
  - Pitfall 1 mitigation: hook only runs on continuation path, never on _handle_execute tick where begin_long_action just fired
  - MagicMock-safe bool check: `_lra_check(actor) is True` instead of truthy check to avoid breaking existing MagicMock-based engine tests
metrics:
  duration: ~45 minutes
  completed: 2026-04-13T19:12:43Z
  tasks_completed: 3
  tasks_total: 3
  files_modified: 10
  tests_added: 42
  baseline_tests: 1443
  final_tests: 1485
---

# Phase 07 Plan 04: Engine tick hook + synthetic action routing + tick summary extension + runner integration — Summary

Engine + PlaytestRunner wired to the Phase 7 long-running action infrastructure. After this plan, an LRA written by a mechanic's `begin_long_action()` call will automatically skip the classifier/matcher/decider on subsequent ticks, advance `turns_elapsed`, evaluate interruption thresholds against the projected state, and produce a grounded or static observation — without any mechanic code changes required.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | LongRunningHook + HookResult + Observer.interruption_context | fff6f83 | long_running_hook.py, observer.py, __init__.py, test_long_running_hook.py |
| 2 | Engine run_tick LRA detection + _handle_long_running_tick + tick summary extension | 813dec5 | engine.py, models.py, summary_writer.py, test_engine_long_running_integration.py |
| 3 | PlaytestRunner skips agent.run_turn during LRA continuations | d48cb6f | runner.py, test_runner_long_running.py |

## What Was Built

### LongRunningHook (`long_running_hook.py`)

Stateless class with a single `process(actor, projection, graph, tick_id_str, observer, tick_diag_ctx) -> HookResult` method. The five steps:

1. Graceful no-op if actor missing or has no `current_long_action` dict on graph (Pitfall 3)
2. Advance `turns_elapsed` by 1 via `graph.set()` (Pitfall 1: increment BEFORE threshold evaluation)
3. Evaluate thresholds via `ThresholdEvaluator.evaluate()` — if one fires, clear LRA and call `observer.synthesize()` with `interruption_context` (D-10)
4. If `turns_total is not None and turns_elapsed >= turns_total` — clear LRA, call observer for completion narrative
5. Otherwise: return static `"Time passes. You continue {action_text}."` (D-22)

`HookResult` is a frozen dataclass: `active, interrupted, completed, continuing, fired_threshold, observation, attention_state, action_text`.

### Observer.synthesize() extension

Added `interruption_context: dict | None = None` kwarg (D-10, D-21). When non-None, a context block is prepended to the Sonnet prompt describing the interruption cause (triggered threshold + action) or completion. Backward-compatible — all existing callers omit the kwarg.

### Engine changes (`engine.py`)

**`has_active_long_action(actor) -> bool`**: Public accessor for PlaytestRunner. Returns `True` only when `current_long_action` is a dict (not None, not missing).

**`run_tick(action_text: str | None, actor: str)`**: Signature changed from `str` to `str | None`. At the top (before Stage 1 Classify):
- If actor has active LRA AND `action_text is None or empty` → `_handle_long_running_tick()`
- If actor has active LRA AND `action_text` is a real string → D-11 implicit cancellation (clear LRA, continue with normal pipeline)
- If no LRA AND `action_text is None` → `ValueError` (invalid call)

**`_handle_long_running_tick()`**: The new synthetic continuation path:
1. Read attention_state from LRA payload
2. Single `project_for(actor, attention_state=...)` call (reused for hook + summary)
3. `LongRunningHook.process()` → `HookResult`
4. `_run_passive_sweep()` with empty primary_mutations (world keeps changing — D-06 Pitfall 6)
5. Build D-17 `long_running_action` summary field; call `_write_summary()`
6. Return `TickResult.ok(observation=hook_result.observation)`

### TickSummary extension (`models.py`, `summary_writer.py`)

`TickSummary` gains `long_running_action: dict[str, Any] | None = None` (D-17). Schema `{"active": True, "turns_elapsed": int, "turns_total": int|None, "threshold_fired": dict|None, "interrupted": bool}`. Field is additive and optional — `schema_version` stays `1`.

### PlaytestRunner integration (`runner.py`)

Before `_determine_action()` each turn, the runner checks `engine.has_active_long_action(agent_id) is True`. On active LRA:
- Sets `action = None`, `action_for_memory = "[long_running_continuation]"`
- Calls `engine.run_tick(None, actor=agent_id)` — skips one Sonnet LLM call per LRA tick
- Uses `action_for_memory` for `memory.store_turn()`, scoring, `TurnRecord`, and progress output

The `is True` guard (rather than truthy) prevents MagicMock-based test fakes from accidentally triggering the LRA path in unrelated tests.

## Pitfall Resolutions

| Pitfall | Resolution |
|---------|-----------|
| Pitfall 1: insta-cancel | Hook only runs on `_handle_long_running_tick` path; the tick where `begin_long_action` runs goes through `_handle_execute` and hook is never called there |
| Pitfall 2: agent flooded with prompts | PlaytestRunner skips `agent.run_turn()` during LRA ticks; only static template or one observer call (interruption/completion) per continuation tick |
| Pitfall 3: actor removed mid-LRA | Hook returns `HookResult.inactive()` gracefully |
| Pitfall 5: cancellation order | D-11 cancellation at top of `run_tick`, before classifier sees the action |
| Pitfall 6: passive mechanics skip | `_run_passive_sweep(primary_mutations=[])` called inside `_handle_long_running_tick` |
| MagicMock bool | `_lra_check(agent_id) is True` — MagicMock returns truthy MagicMock, not `True` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MagicMock boolean interference in PlaytestRunner check**
- **Found during:** Task 3 full test suite regression
- **Issue:** `hasattr(engine, "has_active_long_action") and engine.has_active_long_action(...)` evaluated `True` for all existing MagicMock engine fakes (MagicMock auto-creates any attribute, returns truthy MagicMock), causing all turns to become LRA continuations in 29 existing playtest tests.
- **Fix:** Changed check to `getattr(engine, "has_active_long_action", None) is not None and _lra_check(agent_id) is True`. The real `SimulationEngine.has_active_long_action()` returns a Python `bool`, so `is True` works correctly. MagicMock returns MagicMock (not `True`), so it falls through.
- **Files modified:** `src/token_world/playtest/runner.py`
- **Commit:** d48cb6f

**2. [Rule 1 - Bug] Wrong edge kwarg in integration tests**
- **Found during:** Task 2 test run
- **Issue:** Tests used `kg.add_edge("alice", "bedroom", edge_type="location")` but `KnowledgeGraph.add_edge` takes `**props` so the edge type must be `type="location"`. The edge was stored as `type="edge_type"` not `type="location"`, so the projector never found the location.
- **Fix:** Changed `edge_type=` to `type=` in three test locations.
- **Files modified:** `tests/test_engine/test_engine_long_running_integration.py`
- **Commit:** 813dec5

**3. [Rule 2 - Missing functionality] KG fixture needed SQLite backing**
- **Found during:** Task 2 — first test run hit `RuntimeError: Cannot snapshot without persistence`
- **Issue:** Integration tests need snapshot/restore capability, which requires a db-backed KG. The conftest `kg` fixture uses `db_path=None` (in-memory only).
- **Fix:** Added a local `kg` fixture override in `test_engine_long_running_integration.py` using `tmp_path / "engine_lra_test.db"` (same pattern as `test_engine_run_tick.py`).
- **Files modified:** `tests/test_engine/test_engine_long_running_integration.py`
- **Commit:** 813dec5

## Known Stubs

None. All data flows through real graph operations and real hook logic. The `"[long_running_continuation]"` marker in PlaytestRunner is intentional (not a stub) — it preserves the memory rolling window without carrying semantic meaning.

## Threat Flags

None. This plan adds no new network endpoints, auth paths, or file access patterns. The `observer.synthesize()` extension adds a new kwarg that passes structured context to the LLM prompt, which is within the existing grounded synthesis contract (D-15).

## Self-Check: PASSED

Files created/exist:
- src/token_world/engine/long_running_hook.py: FOUND
- tests/test_engine/test_long_running_hook.py: FOUND
- tests/test_engine/test_engine_long_running_integration.py: FOUND
- tests/test_playtest/test_runner_long_running.py: FOUND

Commits exist:
- fff6f83: FOUND (Task 1)
- 813dec5: FOUND (Task 2)
- d48cb6f: FOUND (Task 3)

Test counts: 1443 baseline → 1485 final (42 new tests, 0 regressions)
