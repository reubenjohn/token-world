# Phase 4 — Deferred Items

Discoveries made during execution that are out of scope for the current plan
but should be addressed opportunistically in a later plan or cleanup pass.

## 04-02 discoveries

### ruff format drift in 04-01 test files

**Found during:** 04-02 Task 3 (running `ruff format tests/` to normalize new
04-02 test files)

**Files:**
- `tests/test_design_validation/test_use_case_schema.py`
- `tests/test_mechanic/test_loader.py`
- `tests/test_universe/test_scaffold.py`

**Issue:** These files — committed during 04-01 — fail `ruff format --check tests/`
because of trivial style divergences (quote style in multi-line strings;
argument-wrapping threshold). Running `ruff format` on them is a pure
whitespace/quote change.

**Why deferred:** Out of scope per CLAUDE.md §4 scope boundary ("Only auto-fix
issues DIRECTLY caused by the current task's changes"). 04-02 only added
`validation.py`, `test_validation.py`, `test_validate_mechanic.py`, and touched
`registry.py`, `cli.py`, `test_registry.py` — all of which pass
`ruff format --check`. The phase-gate in 04-02 Task 4 only requires
`ruff format --check src/`, which is clean.

**Next action:** A future plan (04-12 cleanup or a dedicated tooling plan)
can run `ruff format tests/` and commit the result.
