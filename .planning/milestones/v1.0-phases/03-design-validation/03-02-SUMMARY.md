---
phase: 03-design-validation
plan: 02
subsystem: graph
tags: [spatial, rtree, mechanic-context, lazy-accessor, tdd]

# Dependency graph
requires:
  - phase: 01-graph-foundation
    provides: KnowledgeGraph.nodes() / .query() — SpatialIndex reads via these
  - phase: 02-mechanic-framework
    provides: MechanicContext — spatial lazy accessor hangs off this
  - phase: 03-design-validation (plan 01)
    provides: rtree>=1.4 dependency + tests/test_graph/test_spatial_index.py stubs
provides:
  - src/token_world/graph/spatial.py — SpatialIndex with rebuild/nearest/within/intersects
  - MechanicContext.spatial lazy @property (unused mechanics pay zero rtree cost)
  - 12 passing SpatialIndex tests (6 Wave 0 stubs flipped + 6 Wave 1 edge cases)
  - 3 passing MechanicContext.spatial regression tests
  - malformed-position tolerance: loguru warning + skip, no crash (T-03-05 mitigation)
affects:
  - 03-03-temporal-index (sister primitive; same lazy-accessor pattern may be reused)
  - 03-06-authoring-spatial (UC-S* authoring; use cases will exercise ctx.spatial)
  - 04-mechanic-generation (generated mechanics can now call ctx.spatial.nearest)

# Tech tracking
tech-stack:
  added: []  # rtree was added in 03-01
  patterns:
    - "Lazy @property with deferred import — keeps optional native deps out of the base import graph"
    - "Rebuildable derived view — _rtree swapped wholesale on rebuild(); no per-id deletions"
    - "loguru.warning() + skip for malformed author data — robustness over strictness"
    - "Post-filter over-fetch — when node_type/subtype filters active, fetch 4*k from rtree then filter"

key-files:
  created:
    - src/token_world/graph/spatial.py
    - tests/test_mechanic/test_context_spatial.py
    - .planning/phases/03-design-validation/deferred-items.md
  modified:
    - src/token_world/mechanic/context.py
    - tests/test_graph/test_spatial_index.py

key-decisions:
  - "Full rtree replacement on rebuild() instead of per-id deletions — simpler code, faster for typical-scale rebuilds (<50ms @ 10k nodes per RESEARCH.md A1)"
  - "bbox cache (self._node_to_bbox) so intersects(node_id) skips revalidation of the source node's coords"
  - "Post-filter over-fetch factor of 4 for nearest() when filters active — balances 'cheap common case' (no filter) against 'don't miss matches' (filtered)"
  - "Deferred rtree import via TYPE_CHECKING + in-property import — mechanics that never touch ctx.spatial never import rtree"
  - "ValueError on intersects(positionless_node) instead of empty list — surfaces author bug loudly; positionless-self is a logic error, not a valid query"

patterns-established:
  - "Lazy optional-backend accessor on MechanicContext — template for future GRAPH-07 temporal index (ctx.temporal) and any other heavy-dep DSL extensions"
  - "Derived-view invariant documented in module docstring — 'rebuildable from graph state alone; never a source of truth'"

requirements-completed: [GRAPH-06]

# Metrics
duration: ~4min
completed: 2026-04-12
---

# Phase 3 Plan 02: Spatial Index Summary

**R-tree-backed SpatialIndex exposed via lazy `ctx.spatial` accessor — 2D nearest/within/intersects queries with node_type+subtype filters, malformed-position tolerance, and zero-cost-when-unused semantics.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-12T20:52:23Z
- **Completed:** 2026-04-12T20:56:11Z
- **Tasks:** 2 (both TDD: RED test → GREEN feat)
- **Commits:** 4 (2 test, 2 feat — one pair per task)
- **Files modified:** 4 (2 created, 2 modified)
- **Tests:** 238 passed / 7 skipped (was 223/8 — +15 tests, -1 skip)

## Accomplishments

- `SpatialIndex.rebuild/nearest/within/intersects` working on point (`position`) and bbox (`bbox`) nodes
- `bbox` wins over `position` when both present (per RESEARCH.md §Coordinate model)
- Nodes without position/bbox silently skipped — not an error, not indexed
- Malformed values (`position=["a", "b"]`, wrong-length lists, bools, etc.) logged via `loguru.warning` and skipped — T-03-05 mitigation shipped
- `node_type` and `subtype` kwargs filter results on all query methods
- `intersects(node_id)` excludes the source node from its result; raises `ValueError` if source is positionless
- `MechanicContext.spatial` is a lazy `@property` — first access imports+builds, subsequent accesses return cached instance
- `ctx._spatial is None` until first access — verified by regression test

## Task Commits

Each task shipped as TDD pair (RED then GREEN):

1. **Task 1 RED: Extend SpatialIndex test suite with edge cases** — `b47f002` (test)
2. **Task 1 GREEN: Implement SpatialIndex (GRAPH-06) with rtree backend** — `88310b2` (feat)
3. **Task 2 RED: Lazy-spatial regression tests for MechanicContext** — `bae0931` (test)
4. **Task 2 GREEN: Wire MechanicContext.spatial lazy property** — `d88c879` (feat)

**Plan metadata commit:** (this SUMMARY + STATE + ROADMAP + deferred-items) — hash TBD post-commit.

## Files Created/Modified

### Source

- `src/token_world/graph/spatial.py` (created, 225 lines) — `SpatialIndex` class, `_coerce_bbox` helper, module docstring explicitly calls out "derived view; never a source of truth; rebuildable from graph state alone"
- `src/token_world/mechanic/context.py` (modified, +27 lines) — added `self._spatial: SpatialIndex | None` in `__init__`, added `@property spatial`, `TYPE_CHECKING` import for `SpatialIndex`

### Tests

- `tests/test_graph/test_spatial_index.py` (modified, +101 lines) — added 6 edge-case tests (k > count, intersects-positionless, rebuild idempotency, invalid-position logging, node_type filter, subtype filter, intersects self-exclusion) on top of the 5 Wave 0 stubs
- `tests/test_mechanic/test_context_spatial.py` (created, 42 lines) — 3 tests covering laziness, caching, and no-build-on-non-spatial-DSL-access

### Planning

- `.planning/phases/03-design-validation/deferred-items.md` (created) — logs 2 pre-existing mypy `no-any-return` errors in `knowledge_graph.py` (out of plan scope)

## Decisions Made

- **Full rtree replacement on rebuild() over per-id deletions.** Library supports delete but a fresh `Index(...)` is simpler code and faster at the scales we care about (<50ms @ 10k nodes per RESEARCH.md A1). Per-id incremental invalidation can be bolted on in v2 if profiling shows a bottleneck.
- **bbox cache (`_node_to_bbox`) beside the rtree.** Lets `intersects(node_id)` fetch the source node's bbox in O(1) without re-entering `_coerce_bbox`. Cost: ~32 bytes per indexed node.
- **Post-filter over-fetch factor of 4× when `node_type`/`subtype` active.** Unfiltered `nearest(point, k)` passes `k` straight to rtree for minimum work. Filtered calls fetch `max(k*4, k)` then post-filter, preventing "returned 2 of 5 requested because the 3 closest were filtered out" surprises in the common case. `4×` is a heuristic; adjustable if authored use cases surface edge cases.
- **Deferred rtree import via `TYPE_CHECKING` + in-property import.** Mechanics that never touch `ctx.spatial` never import rtree. Confirmed by the `test_ctx_without_spatial_access_does_not_build` regression — touching `has_node` / `find_nodes` leaves `ctx._spatial is None`.
- **`ValueError` on `intersects(positionless_node)`, not empty list.** A query "what overlaps with nothing" is a logic error — returning `[]` silently would hide author bugs. Loud failure matches the spirit of graph-is-ground-truth.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff UP038 on `isinstance(v, (int, float))`**

- **Found during:** Task 1 pre-commit hook on GREEN commit.
- **Issue:** Pre-commit ruff rejected `isinstance(v, (int, float))` with UP038 — project rule prefers `int | float` PEP 604 syntax.
- **Fix:** Rewrote both calls as `isinstance(v, int | float)`. Re-ran ruff format (auto-applied minor line-length tweaks).
- **Files modified:** `src/token_world/graph/spatial.py`
- **Verification:** `uv run ruff check src/token_world/graph/spatial.py` → All checks passed.
- **Committed in:** `88310b2` (Task 1 GREEN — issue caught before the commit hash was final, so the final commit already contains the fix).

**2. [Rule 3 - Blocking] Ruff SIM103 on `_passes_filter` last condition**

- **Found during:** Task 1 ruff gate immediately after writing `spatial.py`.
- **Issue:** Two sequential `if X: return False` at function end; ruff SIM103 wants the second inlined as `return not X`.
- **Fix:** Collapsed last branch into `return not (subtype is not None and props.get("subtype") != subtype)`.
- **Files modified:** `src/token_world/graph/spatial.py`
- **Verification:** ruff clean; all 12 spatial tests still pass.
- **Committed in:** `88310b2` (Task 1 GREEN — applied before the commit).

---

**Total deviations:** 2 auto-fixed (both Rule 3 — linting gate blockers inside Task 1, both zero-semantic fixes).
**Impact on plan:** None. Both deviations were style-only adjustments to satisfy project lint rules before the Task 1 GREEN commit landed.

## Issues Encountered

- **Pre-existing mypy errors in `knowledge_graph.py`.** `uv run mypy src/token_world/graph/` reports 2 `no-any-return` errors on Phase 1 snapshot code. Confirmed pre-existing via `git stash → mypy → git stash pop` — not introduced by this plan. Logged to `.planning/phases/03-design-validation/deferred-items.md`. mypy on the in-scope files (`src/token_world/graph/spatial.py`, `src/token_world/mechanic/context.py`) exits 0.
- **loguru → caplog propagation.** By default loguru doesn't route through stdlib logging, so `pytest`'s `caplog` fixture sees nothing. Added a small `PropagateHandler` inside the one test that needs it (`test_invalid_position_logged_and_skipped`) — scoped to the test, removed on teardown. No project-wide logging config changes.

## User Setup Required

None — no env vars, no external services, no dashboard config. `rtree` was already installed in Plan 01.

## Next Phase Readiness

**Unblocked by this plan:**

- `03-03 temporal-index` — same lazy-accessor pattern applies; reuse `ctx._spatial` → `ctx._temporal` template. `TemporalIndex` will sit beside `SpatialIndex` under `src/token_world/graph/`.
- `03-06 authoring-spatial` — UC-S01..UC-S05 authors can now write `setup.graph_builder` graphs with `position=[x,y]` and action bodies that call `ctx.spatial.nearest(...)` expecting it to work.
- `04-mechanic-generation` — generated mechanics have a stable DSL extension (`ctx.spatial.*`) to target for spatial reasoning.

**No blockers.** All verification gates in the plan are green:

- `uv run pytest tests/test_graph/test_spatial_index.py tests/test_mechanic/test_context_spatial.py -v` → 15 passed
- `uv run pytest tests/ -q` → 238 passed, 7 skipped
- `uv run mypy src/token_world/graph/spatial.py src/token_world/mechanic/context.py` → 0 issues
- `uv run ruff check src/` → All checks passed
- `uv run ruff format --check src/` → 37 files already formatted

## Self-Check: PASSED

Verified artifacts exist and commits are in git history:

- FOUND: `src/token_world/graph/spatial.py`
- FOUND: `src/token_world/mechanic/context.py` (contains `def spatial` and `_spatial`)
- FOUND: `tests/test_mechanic/test_context_spatial.py`
- FOUND: `tests/test_graph/test_spatial_index.py` (extended with 6 new tests)
- FOUND: `.planning/phases/03-design-validation/deferred-items.md`
- FOUND commit `b47f002` (Task 1 RED — test)
- FOUND commit `88310b2` (Task 1 GREEN — feat)
- FOUND commit `bae0931` (Task 2 RED — test)
- FOUND commit `d88c879` (Task 2 GREEN — feat)

---

*Phase: 03-design-validation*
*Plan: 02*
*Completed: 2026-04-12*
