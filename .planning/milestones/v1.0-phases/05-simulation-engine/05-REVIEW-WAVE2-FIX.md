---
phase: 05-simulation-engine
fixed_at: 2026-04-13T00:00:00Z
review_path: .planning/phases/05-simulation-engine/05-REVIEW-WAVE2.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 05 Wave 2-4: Code Review Fix Report

**Fixed at:** 2026-04-13
**Source review:** .planning/phases/05-simulation-engine/05-REVIEW-WAVE2.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01, WR-02, WR-03, WR-04)
- Fixed: 4
- Skipped: 0
- IN-01, IN-02, IN-03 deferred (see below)

## Fixed Issues

### WR-01: Passive sweep swallows mechanic exceptions silently

**Files modified:** `src/token_world/engine/engine.py`, `tests/test_engine/test_engine_passive_sweep.py`
**Commit:** a7c4cf4
**Applied fix:** In `_run_passive_sweep`, the `except Exception` block now appends a
`TraceNode(mechanic_id=mech.id, ..., mutations=[])` to `sweep_nodes` before `continue`,
mirroring the `check().passed == False` branch. Added regression test
`test_passive_sweep_exception_in_apply_records_trace_node` that installs an involuntary
mechanic whose `apply()` raises, runs a tick, and asserts the failing mechanic's
TraceNode appears in `result.trace` with empty mutations.

### WR-02: TypeError for unhandled Decision type escapes open_tick without a status record

**Files modified:** `src/token_world/engine/engine.py`, `tests/test_engine/test_engine_run_tick.py`
**Commit:** f4256f4
**Applied fix:** Added `tick_ctx.set_summary(status="error", error=f"Unhandled decision type: ...")` before `raise TypeError(...)` in the `else` branch at the end of `run_tick`'s decision dispatch. Added regression test `test_run_tick_unhandled_decision_type_writes_error_summary` that monkeypatches `engine_module.decide` to return an unrecognized Decision type, confirms `TypeError` propagates, and asserts `diagnostics/tick_1/summary.json` contains `status="error"`.

### WR-03: Conservation rollback tick ID collision concern

**Files modified:** `src/token_world/engine/engine.py`, `tests/test_engine/test_engine_run_tick.py`
**Commit:** 2da13f6
**Applied fix:** Investigation (via `scripts/check_wr03_tick_collision.py`) confirmed the
reviewer's concern about the `set_tick(next_tick - 1)` fix suggestion would actually
introduce a collision, not prevent one. The current implementation is correct:
`snapshot(next_tick)` sets `_current_tick = next_tick`; `restore()` sets it back to the
same value; the next `run_tick` computes `next_tick + 1` — no collision.

Resolution: documented the invariant with comments at both conservation rollback sites in
`engine.py`. Added regression test
`test_run_tick_consecutive_conservation_rollbacks_produce_distinct_tick_ids` that runs
two consecutive conservation-violating ticks and asserts both `tick_id` values are
distinct and monotonically increasing.

**Note:** The reviewer's proposed code fix (`self._graph.set_tick(next_tick - 1)`) was NOT
applied because it would cause `next_tick_2 = (next_tick - 1) + 1 = next_tick`, which is
the collision it aimed to prevent. This finding is marked `fixed: requires human
verification` of the invariant reasoning.

### WR-04: MCP -32603 handler leaks internal exception message text

**Files modified:** `src/token_world/mcp_server.py`, `tests/test_universe/test_mcp_tools.py`
**Commit:** f97327f
**Applied fix:** Changed `except Exception as exc:` to `except Exception:` and replaced
`f"Internal error: {exc}"` with the fixed string `"Internal error"`. The full traceback
continues to be written to stderr via `traceback.format_exc()`. Updated the existing test
`test_internal_error_returns_32603_and_no_stack_trace_leak` (renamed to
`test_internal_error_returns_32603_with_generic_message`) to assert `"boom" not in
message` and `message == "Internal error"` rather than checking for exc content presence.

## Deferred Info Findings

### IN-01: observer.py — `full_prompt` variable name misleading

**File:** `src/token_world/engine/observer.py`
**Reason:** Info-level / cosmetic rename. Out of scope per `<CRITICAL_FILE_SCOPE_GUARDRAIL>`
(observer.py is not in allowed files). Low urgency — the code is correct, only the
variable name is misleading. Can be addressed in a future cleanup pass.

### IN-02: Duplicate `_flatten_mutations` across observer.py, summary_writer.py, engine.py

**File:** `src/token_world/engine/summary_writer.py:64-81`, `src/token_world/engine/observer.py:55-64`
**Reason:** Info-level refactor requiring changes to observer.py and summary_writer.py —
both out of scope per guardrail. The three implementations are currently equivalent.
Should be promoted to `token_world.mechanic.trace` in a dedicated cleanup phase.

### IN-03: `_ClassifierDiagnosticsAdapter._maybe_flush` silent no-op on unknown stage names

**File:** `src/token_world/engine/engine.py:97-110`
**Reason:** Deferred. The issue is dormant (classifier.py consistently uses
`stage="classification"`). The fix is low-risk but the warning/assertion is cosmetic until
`classifier.py` adds new stage names. Recommend adding it in the same pass as IN-01/IN-02
cleanup.

---

_Fixed: 2026-04-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
