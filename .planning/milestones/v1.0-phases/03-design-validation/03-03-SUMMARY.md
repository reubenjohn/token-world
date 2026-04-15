---
phase: 03-design-validation
plan: 03
subsystem: graph
tags: [temporal, event-sourcing, mechanic-context, lazy-accessor, sqlite-index, tdd]

# Dependency graph
requires:
  - phase: 01-graph-foundation
    provides: EventStore + graph_events SQLite table + graph_snapshots — TemporalIndex reads these
  - phase: 02-mechanic-framework
    provides: MechanicContext — temporal lazy accessor hangs off this
  - phase: 03-design-validation (plan 01)
    provides: tests/test_graph/test_temporal_index.py Wave 0 stubs
  - phase: 03-design-validation (plan 02)
    provides: lazy-accessor pattern on MechanicContext (ctx.spatial); this plan reuses the same pattern for ctx.temporal
provides:
  - src/token_world/graph/temporal.py — TemporalIndex read-only query facade
  - TemporalQueryOutOfRange exception for unreachable history
  - MechanicContext.temporal lazy @property
  - Two SQLite indexes on graph_events (target_id, property_name)
  - 11 passing TemporalIndex tests (5 Wave 0 stubs flipped + 6 new edge cases)
  - 4 passing MechanicContext.temporal regression tests
affects:
  - 03-06-authoring-spatial through 03-10 — use cases can now call ctx.temporal.query_history / last_change / find_state_at_tick
  - 04-mechanic-generation — generated mechanics have a second DSL extension (ctx.temporal.*) alongside ctx.spatial.*

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mem+disk merge on a derived view — session EventStore unions with persisted graph_events, deduped on (tick, type, target, property, new_value)"
    - "Static WHERE fragments + parameterized ? placeholders — zero f-string SQL"
    - "sqlite3.OperationalError caught as empty-disk — graceful on in-memory-only graphs where tables haven't been created yet"
    - "Lazy @property with deferred import — same template as plan 02's ctx.spatial"

key-files:
  created:
    - src/token_world/graph/temporal.py
    - tests/test_mechanic/test_context_temporal.py
  modified:
    - src/token_world/graph/persistence.py
    - src/token_world/mechanic/context.py
    - tests/test_graph/test_temporal_index.py

key-decisions:
  - "Mem+disk merge via union-with-dedup instead of sqlite-only reads. Session events haven't been flushed yet on first save() — reading from disk would miss them. Dedup key = (tick, type, target, property, new_value) covers the overlap window after a save/load cycle."
  - "sqlite3.OperationalError caught in _query_disk and _load_baseline. An in-memory-only graph (no save() ever called) has no tables; treating missing-table as empty-disk lets TemporalIndex work uniformly whether persistence has been exercised or not."
  - "Fixed test stub bug from plan 01: kg.advance_tick() does not exist on KnowledgeGraph — replaced with kg.set_tick(n) (the actual public API). Stub was uncallable; Wave 1 was always going to hit this."
  - "Accept _db_path internal-attribute access. Phase 1 has not exposed a public accessor; mirroring the plan 02 approach. Comment in temporal.py flags the coupling for Phase 1 to migrate later."
  - "Static WHERE fragments only. Every SQL string in temporal.py is built from string literals; only tuple params interpolated via ? placeholders. grep for f-string SQL returns nothing. T-03-03 mitigation shipped."

patterns-established:
  - "Composable lazy DSL extensions on MechanicContext — ctx.spatial and ctx.temporal are independently lazy, cached, and zero-cost-when-unused. Template ready for a third accessor (e.g., ctx.memory, ctx.goals) if Phase 4 wants it."
  - "Derived-view module docstring convention — 'Read-only. Derived view — never a source of truth.' Same language as SpatialIndex. Makes invariants explicit to anyone grepping the module."

requirements-completed: [GRAPH-07]

# Metrics
duration: ~4min
completed: 2026-04-12
---

# Phase 3 Plan 03: Temporal Index Summary

**Read-only `TemporalIndex` over EventStore + graph_events SQLite — query_history, query_changes, find_state_at_tick, last_change — exposed via lazy `ctx.temporal` accessor with zero-cost-when-unused and SQL-injection defense baked in.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-12T20:59:49Z
- **Completed:** 2026-04-12T21:03:36Z
- **Tasks:** 3 (Task 1 straight feat; Tasks 2 and 3 TDD — RED test → GREEN feat)
- **Commits:** 5 (1 feat, 2 test, 2 feat)
- **Files modified:** 5 (2 created, 3 modified)
- **Tests:** 253 passed / 6 skipped (was 238/7 — +15 tests, -1 skip)

## Accomplishments

- `TemporalIndex.query_history(node_id, tick_range=...)` returns all events targeting a node in tick order
- `TemporalIndex.query_changes(property, tick_range=..., node_id=...)` filters `set_property` events
- `TemporalIndex.find_state_at_tick(node_id, tick)` reconstructs node properties via snapshot baseline + event replay
- `TemporalIndex.last_change(node_id, property)` returns most recent `set_property` (or None)
- `TemporalQueryOutOfRange` raised for ticks before any reachable snapshot or add_node event
- Mem+disk merge: session EventStore unions with persisted graph_events, deduped on (tick, type, target, property, new_value), sorted by tick_id
- Two new SQLite indexes: `idx_events_target(target_id, tick_id)` and `idx_events_property(property_name, tick_id)` — make hot query paths O(log n) on large event logs (T-03-08 mitigation)
- Every SQL statement uses `?` placeholders with tuple params; WHERE fragments are static strings; no f-string SQL anywhere (T-03-03 mitigation shipped)
- `MechanicContext.temporal` is a lazy `@property` — first access imports + constructs, subsequent accesses return cached instance
- `ctx._temporal is None` until first access; non-temporal DSL calls don't trigger build
- `ctx.spatial` and `ctx.temporal` are independently lazy — each builds only when its own accessor is hit

## Task Commits

1. **Task 1: Add SQLite indexes on graph_events** — `c41cae2` (feat)
2. **Task 2 RED: expand TemporalIndex test suite** — `83617d0` (test)
3. **Task 2 GREEN: implement TemporalIndex (GRAPH-07)** — `6e443e5` (feat)
4. **Task 3 RED: lazy-temporal regression tests for MechanicContext** — `4c28808` (test)
5. **Task 3 GREEN: wire MechanicContext.temporal lazy property** — `0e93631` (feat)

**Plan metadata commit:** (this SUMMARY + STATE + ROADMAP) — hash TBD post-commit.

## Files Created/Modified

### Source

- `src/token_world/graph/temporal.py` (created, 264 lines) — `TemporalIndex` + `TemporalQueryOutOfRange`. Module docstring calls out "Read-only. Derived view — never a source of truth." and "No new storage."
- `src/token_world/graph/persistence.py` (modified, +2 lines) — two `CREATE INDEX IF NOT EXISTS` statements appended to `_ensure_tables` executescript
- `src/token_world/mechanic/context.py` (modified, +21 lines) — `TemporalIndex` TYPE_CHECKING import, `self._temporal` slot, `@property temporal`

### Tests

- `tests/test_graph/test_temporal_index.py` (modified, replaced) — 11 tests: 5 Wave 0 stubs flipped + 6 new (query_changes node filter, last_change absent, last_change recency, find_state_at_tick uses snapshot, mem+disk merge across save/load, SQL injection defense)
- `tests/test_mechanic/test_context_temporal.py` (created, 51 lines) — 4 tests: laziness, caching, non-temporal-DSL-no-build, spatial-and-temporal-independent

## Decisions Made

- **Mem+disk merge with dedup key = (tick, type, target, property, new_value).** Simpler than reasoning about "which events have been flushed." Works on fresh in-memory graphs (disk empty), on freshly loaded graphs (mem empty), and on mid-session graphs (overlap possible but dedup handles it). Sorted by tick_id post-merge so ordering guarantees hold even when mem events carry later ticks than disk.
- **sqlite3.OperationalError caught as empty-disk.** The Wave 0 `test_out_of_range_raises` test creates a KnowledgeGraph with a db_path but never calls `save()` — so `graph_events` and `graph_snapshots` tables don't exist yet. Rather than force a save inside TemporalIndex (which would be a write on a read path) or require explicit init, the module treats "no such table" as "no persisted events." Matches user intent: "if nothing is saved, there's nothing on disk."
- **Fixed the plan 01 stub bug.** `kg.advance_tick()` never existed — the real method is `kg.set_tick(n)`. Rewrote the three tests that used it. This is the kind of drift the Nyquist-gating pattern explicitly targets: Wave 0 stubs failing against real Wave 1 APIs are good signal.
- **Internal `_db_path` access mirrored from plan 02.** Phase 1 has not exposed a public `db_path` accessor. Rather than plumb one in now (out-of-scope architectural change per Rule 4), I accepted the same internal-attribute access plan 02 used. Documented in module docstring comment so the next migrator can find it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `kg.advance_tick()` doesn't exist**

- **Found during:** Task 2 RED (running the Wave 0 stubs in test_temporal_index.py).
- **Issue:** The existing stubs called `kg.advance_tick()`, but `KnowledgeGraph` has no such method. The actual API is `kg.set_tick(n)`. The stubs were structurally uncallable — they'd fail with `AttributeError` the moment the `importorskip` guard was lifted.
- **Fix:** Replaced `kg.advance_tick()` with `kg.set_tick(1)` (or the appropriate explicit tick) in the three affected tests.
- **Files modified:** `tests/test_graph/test_temporal_index.py`
- **Verification:** All 11 tests pass; no regressions elsewhere.
- **Committed in:** `83617d0` (Task 2 RED).

**2. [Rule 3 - Blocking] `graph_snapshots` table missing on unsaved DB**

- **Found during:** Task 2 GREEN first test run — `test_find_state_at_tick_reconstructs` crashed with `sqlite3.OperationalError: no such table: graph_snapshots`.
- **Issue:** The `kg` fixture opens a DB path but never calls `save()`, so tables don't exist. `_load_baseline` assumed the table was always present.
- **Fix:** Wrapped the snapshot SELECT in `try/except sqlite3.OperationalError` and fall through to the add-event fallback (treating missing table as "no snapshots"). Symmetric with the `_query_disk` handling of missing `graph_events`.
- **Files modified:** `src/token_world/graph/temporal.py`
- **Verification:** All 11 temporal tests pass.
- **Committed in:** `6e443e5` (Task 2 GREEN — fix landed before the commit).

**3. [Rule 3 - Blocking] ruff-format rewrite**

- **Found during:** Task 2 GREEN commit hook, and Task 2 RED commit hook.
- **Issue:** Pre-commit `ruff-format` hook rewrote minor formatting (f-string unwrap, long-line collapse) inside temporal.py and test_temporal_index.py.
- **Fix:** Accepted the reformat and re-added/re-committed. No semantic change.
- **Committed in:** `6e443e5` and `83617d0` (reformats landed inside those commits).

---

**Total deviations:** 3 auto-fixed (Rule 1 + 2× Rule 3). Zero architectural changes.
**Impact on plan:** Zero functional impact. The plan-01 stub bug (`advance_tick`) was already going to surface in this plan; catching it here is faster than bouncing back to plan 01.

## Issues Encountered

- **Wave 0 stub API drift.** Documented above under deviation 1. Two stubs from plan 01 referenced a method that never existed. Logged because Nyquist-gating depends on stubs being at least callable against the real surface.
- **Pre-existing mypy errors in `knowledge_graph.py`.** Still present from plan 02 (logged in `deferred-items.md`). mypy on this plan's scope (`temporal.py`, `persistence.py`, `context.py`) exits 0.

## User Setup Required

None — no env vars, no external services, no dashboard config.

## Next Phase Readiness

**Unblocked by this plan:**

- `03-06..10 authoring-*` — UC-*.md authors can now write setup/action bodies that call `ctx.temporal.query_history`, `ctx.temporal.find_state_at_tick`, etc.
- `04-mechanic-generation` — generated mechanics have two stable DSL extensions: `ctx.spatial.*` (plan 02) and `ctx.temporal.*` (this plan). Both lazy, both zero-cost when unused.

**No blockers.** Verification gates:

- `uv run pytest tests/test_graph/test_temporal_index.py tests/test_mechanic/test_context_temporal.py -v` → 15 passed
- `uv run pytest tests/ -q` → 253 passed, 6 skipped
- `uv run mypy src/token_world/graph/temporal.py src/token_world/graph/persistence.py src/token_world/mechanic/context.py` → 0 issues
- `uv run ruff check src/` → All checks passed
- `uv run ruff format --check src/` → 38 files already formatted
- `grep -E "f[\"'].*\{.*\}.*(SELECT|FROM)" src/token_world/graph/temporal.py` → no matches (injection defense holds)

## Self-Check: PASSED

Verified artifacts exist and commits are in git history:

- FOUND: `src/token_world/graph/temporal.py` (contains `class TemporalIndex` and `class TemporalQueryOutOfRange`)
- FOUND: `src/token_world/graph/persistence.py` (contains `idx_events_target`, `idx_events_property`)
- FOUND: `src/token_world/mechanic/context.py` (contains `def temporal` and `_temporal`)
- FOUND: `tests/test_graph/test_temporal_index.py` (11 tests, all passing)
- FOUND: `tests/test_mechanic/test_context_temporal.py` (4 tests, all passing)
- FOUND commit `c41cae2` (Task 1 — feat)
- FOUND commit `83617d0` (Task 2 RED — test)
- FOUND commit `6e443e5` (Task 2 GREEN — feat)
- FOUND commit `4c28808` (Task 3 RED — test)
- FOUND commit `0e93631` (Task 3 GREEN — feat)

---

*Phase: 03-design-validation*
*Plan: 03*
*Completed: 2026-04-12*
