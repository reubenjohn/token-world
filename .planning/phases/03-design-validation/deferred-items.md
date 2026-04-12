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
