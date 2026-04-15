# Deferred Items — Phase 03 Design Validation

Items discovered during plan execution that were **out of scope** for the
plan in which they were found. Track here so a later phase or cleanup
plan can address them.

_All items resolved — see history below._

## Resolved

### Pre-existing type errors in `src/token_world/graph/knowledge_graph.py`

**Found during:** 03-02 (spatial-index) Task 2 mypy gate.
**Resolved by:** Plan 03-13 (commits e4bd871, 1981f12). `typing.cast` applied at
both call sites; `uv run mypy src/token_world/graph/` exits 0; regression guard
at `tests/test_graph/test_mypy_clean.py`.

### Pre-existing ruff errors in `tests/test_mechanic/`

**Found during:** 03-14 / 03-15 final ruff gates.
**Resolved during:** Phase 03 gap-closure cleanup. `ruff check --fix` resolved
3 of 4; `tests/test_mechanic/test_cli.py:73` simplified (the `or`-clause was a
self-referential dead branch — `result.output + (result.output or "")` cannot
contain "not found" without `result.output` already containing it). All 107
mechanic tests still pass; `uv run ruff check src/ tests/` clean.
