---
phase: 03-design-validation
plan: 13
subsystem: testing
tags: [mypy, typing, sqlite, snapshot, type-safety, gap-closure]

# Dependency graph
requires:
  - phase: 03-design-validation
    provides: Phase 01 graph module snapshot API (save_snapshot / list_snapshots)
provides:
  - mypy-clean `src/token_world/graph/` (0 errors, warn_return_any honoured)
  - Typed return paths on `GraphPersistence.save_snapshot` and `.list_snapshots`
    so downstream callers see concrete types instead of `Any`
  - Regression test `tests/test_graph/test_mypy_clean.py` that shells out to
    mypy and fails if a new `no-any-return` leaks in
affects: [phase-04-llm-mechanic-generation, phase-04.1-operator-agent-harness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "typing.cast at trust boundaries (Any-typed attribute -> concrete type) instead of # type: ignore"
    - "Subprocess-based mypy smoke test guarded by shutil.which(), skipped when toolchain absent"

key-files:
  created:
    - tests/test_graph/test_mypy_clean.py
  modified:
    - src/token_world/graph/persistence.py
    - src/token_world/graph/knowledge_graph.py

key-decisions:
  - "Apply typing.cast at knowledge_graph.py call sites rather than retyping self._persistence attribute — minimal-surface fix that stays within plan acceptance criteria and leaves the lazy-init Any pattern untouched for other methods"
  - "Replace existing # type: ignore[return-value] on GraphPersistence.save_snapshot with typing.cast(int, cursor.lastrowid) — tightens the check instead of silencing it"
  - "Regression guard shells out to mypy via subprocess (not mypy.api) — avoids importing mypy into the test runtime and skips cleanly when mypy is not on PATH"

patterns-established:
  - "Cast at the trust boundary: when crossing from an Any-typed attribute (e.g. self._persistence: Any) into a typed return, wrap the call in typing.cast rather than broadcasting the Any further"
  - "CI-enforced type-check contract: per-module mypy smoke test lives alongside the module's behavioural tests, so regressions fail pytest and don't wait for UAT"

requirements-completed: [DVAL-01]

# Metrics
duration: 8min
completed: 2026-04-12
---

# Phase 03 Plan 13: Mypy Snapshot Return Types Summary

**Gap closure for UAT#3: replaced `# type: ignore[return-value]` on `GraphPersistence.save_snapshot` with `typing.cast(int, …)`, cast the two `KnowledgeGraph` snapshot call sites through the `Any`-typed `_persistence` attribute, and added a pytest regression guard that shells out to mypy — `uv run mypy src/token_world/graph/` now reports "Success: no issues found in 8 source files".**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-12 (executor session)
- **Completed:** 2026-04-12
- **Tasks:** 2
- **Files modified:** 2 (plus 1 created)

## Accomplishments

- `uv run mypy src/token_world/graph/` exits 0 with `Success: no issues found in 8 source files` (previously 2 `no-any-return` errors on knowledge_graph.py:450 and :479).
- `GraphPersistence.save_snapshot` body returns `cast(int, cursor.lastrowid)` — no more `# type: ignore[return-value]` silencing the checker.
- `KnowledgeGraph.snapshot` and `KnowledgeGraph.list_snapshots` now narrow their return values through `typing.cast` so the public API types (`int`, `list[SnapshotInfo]`) survive the `self._persistence: Any` lazy-init attribute.
- Regression test `tests/test_graph/test_mypy_clean.py` added — future Any-leaks in the graph module fail pytest rather than UAT.
- Graph test count 84 → 85; full suite (292 tests) still green; ruff check and `ruff format --check` both clean.

## Task Commits

Each task was committed atomically:

1. **Task 13.1: Annotate GraphPersistence snapshot methods so their return types are concrete** — `e4bd871` (fix)
2. **Task 13.2: Add regression guard: mypy-clean contract for graph module is test-enforced** — `1981f12` (test)

## Files Created/Modified

- `src/token_world/graph/persistence.py` — Added `from typing import cast`; `save_snapshot` now returns `cast(int, cursor.lastrowid)` in place of the prior `# type: ignore[return-value]`.
- `src/token_world/graph/knowledge_graph.py` — Added `cast` to typing imports; wrapped the two `_persistence.save_snapshot(...)` and `_persistence.list_snapshots()` call sites in `typing.cast(int, …)` / `typing.cast(list[SnapshotInfo], …)` so mypy narrows through the `Any`-typed `_persistence` attribute.
- `tests/test_graph/test_mypy_clean.py` — New regression test; shells out to `mypy src/token_world/graph/` and asserts exit 0; skips cleanly when mypy is not on PATH.

## Decisions Made

- **Cast at the knowledge_graph.py call sites rather than retyping `self._persistence`.** The plan's acceptance criteria explicitly allowed "typed `cast(...)` call(s)" in knowledge_graph.py. Retyping `self._persistence: GraphPersistence | None` would have been cleaner architecturally but expanded the blast radius to every other method that touches `_persistence` (5 additional lines inside `save`, `load`, `restore`, etc., some of which would have needed their own `if self._persistence is None` reshuffles). Minimal surface fix chosen to honour the plan's "no behaviour change" constraint.
- **Replaced `# type: ignore[return-value]` with `typing.cast(int, cursor.lastrowid)` inside `save_snapshot`.** Plan forbade `# type: ignore[no-any-return]` specifically, but the spirit is the same: tighten, don't silence. `cast` keeps the annotation honest while acknowledging that sqlite3's Cursor.lastrowid stubs return `Any`.
- **Subprocess-based mypy test, not `mypy.api.run`.** Keeps mypy out of the test runtime import graph and lets the test skip cleanly when mypy isn't installed — consistent with the plan's "skips if mypy not importable" guidance.

## Deviations from Plan

None - plan executed exactly as written.

The plan's `<action>` block suggested the fix would live in `persistence.py`; in practice the `# type: ignore[return-value]` on line 209 of persistence.py was real and got replaced with `cast`, but the *propagating* `Any` actually originated from `self._persistence: Any` in knowledge_graph.py line 61. The plan's acceptance criteria anticipated this ("`git diff knowledge_graph.py` contains 0 lines OR contains only typed `cast(...)` call(s)") — the `cast(...)`-call-site branch was taken. No auto-fixes outside the two files the plan scoped to.

## Issues Encountered

- Initial fix to `persistence.py` alone (replacing `# type: ignore` with `cast`) did not clear the mypy errors on knowledge_graph.py:450/479 — diagnosed by inspecting line 61 (`self._persistence: Any = None`), which broadcast `Any` to every `_persistence.*` call. Resolved by adding `cast` at the two knowledge_graph.py call sites the plan called out.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 03 UAT Test 3 gap is closed: `uv run mypy src/token_world/graph/` exits 0, satisfying the "type-check green" criterion that Phase 04 assumes when consuming the graph module's snapshot API.
- Regression guard in place so new Any-leaks in the graph module will fail pytest rather than surfacing at the next UAT.

## Self-Check: PASSED

- FOUND: `src/token_world/graph/persistence.py` (modified; contains `from typing import cast` and `cast(int, cursor.lastrowid)`)
- FOUND: `src/token_world/graph/knowledge_graph.py` (modified; contains `cast(int, self._persistence.save_snapshot(...))` and `cast(list[SnapshotInfo], self._persistence.list_snapshots())`)
- FOUND: `tests/test_graph/test_mypy_clean.py` (created; contains `def test_graph_module_is_mypy_clean`)
- FOUND commit `e4bd871` (fix(03-13): tighten snapshot method return types for mypy no-any-return)
- FOUND commit `1981f12` (test(03-13): add mypy-clean regression guard for graph module)
- `uv run mypy src/token_world/graph/` → `Success: no issues found in 8 source files`
- `uv run pytest tests/test_graph/ -q` → 85 passed (prior 84 + 1 new)
- `uv run pytest tests/ -q` → 292 passed
- `uv run ruff check src/` → All checks passed
- `uv run ruff format --check src/` → 39 files already formatted
- `git diff HEAD~2 HEAD -- src/token_world/graph/` grep for added `# type: ignore` → 0 additions (only the prior `# type: ignore[return-value]` was removed)

---
*Phase: 03-design-validation*
*Completed: 2026-04-12*
