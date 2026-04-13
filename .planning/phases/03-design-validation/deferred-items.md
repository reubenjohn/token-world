# Deferred Items — Phase 03 Design Validation

Items discovered during plan execution that were **out of scope** for the
plan in which they were found. Track here so a later phase or cleanup
plan can address them.

## Pre-existing type errors in `src/token_world/graph/knowledge_graph.py`

**Found during:** 03-02 (spatial-index) Task 2 mypy gate.

```
src/token_world/graph/knowledge_graph.py:389: error: Returning Any from function declared to return "int"  [no-any-return]
src/token_world/graph/knowledge_graph.py:418: error: Returning Any from function declared to return "list[SnapshotInfo]"  [no-any-return]
```

**Status:** Pre-existing before this plan began (verified via `git stash` → mypy
reproduced both errors before any 03-02 changes were applied).

**Scope:** Phase 01 graph-foundation artifact. Not caused by and unrelated to
GRAPH-06 / SpatialIndex.

**Proposed fix:** Tighten the return-type cast at both call sites
(`snapshot()` returns `self._persistence.save_snapshot(...)`; `list_snapshots()`
returns `self._persistence.list_snapshots()`). Add explicit
`cast(int, ...)` / typed return from `GraphPersistence`, or annotate
`GraphPersistence.save_snapshot` and `.list_snapshots` with concrete return
types so the cast disappears.

**Impact if not fixed:** mypy on the `graph/` package exits non-zero. Does
not affect runtime behavior or test results.

## Pre-existing ruff errors in `tests/test_mechanic/`

**Found during:** 03-14 (escape_label angle-bracket gap closure) final
verification (`uv run ruff check src/ tests/`).

- `tests/test_mechanic/test_cli.py:73` — E501 line-too-long (117 > 100)
- `tests/test_mechanic/test_context.py:5` — F401 unused import `KnowledgeGraph`
- `tests/test_mechanic/test_engine.py:3` — I001 unsorted import block
- `tests/test_mechanic/test_registry.py:3` — I001 unsorted import block
  (also observed from 03-15 final ruff gate; pre-existing, same scope as above)

**Status:** Pre-existing. Reproduced against `HEAD~2` and earlier before
any plan-14 changes were applied.

**Scope:** Phase 02 (mechanic-framework tests) artifact. Plan 03-14 only
touches `src/token_world/viz/mermaid.py` and
`tests/test_viz/test_mermaid_escape.py`; fixing unrelated test files is
out of scope per the deviation-rules scope boundary.

**Proposed fix:** `uv run ruff check tests/test_mechanic/ --fix` resolves
three of the four automatically; the E501 line requires a manual split.

**Impact if not fixed:** `uv run ruff check src/ tests/` exits non-zero,
but only because of these pre-existing issues. `ruff check src/` and
`ruff check tests/test_viz/` both pass clean.
