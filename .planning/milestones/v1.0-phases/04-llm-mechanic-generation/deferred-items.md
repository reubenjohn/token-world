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

## 04-03 discoveries

### ruff E501 + format drift in `src/token_world/mechanic/validation.py`

**Found during:** 04-03 Task 3 (running `ruff check src/` + `ruff format --check src/`).

**Files:**
- `src/token_world/mechanic/validation.py` — 2 × E501 (lines 441, 544: function
  signature lines 110 chars); additional format diff reported by
  `ruff format --check`.

**Issue:** Both findings exist in commit `a6c1491` (04-02 Task 4 "phase-gate"),
verified by stashing 04-03 changes and re-running the checks. They predate
this plan's source edits.

**Why deferred:** Out of scope per CLAUDE.md §4 scope boundary
("Only auto-fix issues DIRECTLY caused by the current task's changes").
04-03 changes in `src/` are `diagnostics.py` (new file, clean)
and the `prune-diagnostics` command appended to `cli.py` (clean).

**Next action:** 04-12 cleanup plan (or a dedicated tooling plan) runs
`ruff format src/` and either shortens the `_stage_tests` / `_stage_smoke`
function signatures onto multiple lines or applies a `# noqa: E501` ack.

## 04-05 discoveries

### Continued pre-existing drift in `src/token_world/mechanic/validation.py`

**Found during:** 04-05 Task 2 phase-gate (running `ruff check src/`).

**Status:** still 2 × E501 on lines 441, 544 (unchanged from 04-03 finding).
04-05 does not touch `validation.py`; the phase-gate for this plan narrows
to `ruff check` on the three files it actually modifies
(`cli.py`, `universe/scaffold.py`, `universe/templates/claude_md.py`),
all of which are clean.

**Why deferred:** Out of scope per CLAUDE.md §4. Already logged above;
noted here for continuity.

**Next action:** As above — 04-12 cleanup plan.

## 04-07 discoveries

### ruff I001/F401/E501 drift in 04-06 test files

**Found during:** 04-07 Task 3 phase-gate (`ruff check
src/token_world/mechanic/seeds/ tests/test_mechanic/test_seeds/`).

**Files:**
- `tests/test_mechanic/test_seeds/test_passage_move.py` (I001 import order)
- `tests/test_mechanic/test_seeds/test_position_sync.py` (I001, F401 `pytest`
  imported but unused, E501 line 112)
- `tests/test_mechanic/test_seeds/test_terrain_move.py` (I001)

**Issue:** 5 ruff findings across three tests committed during 04-06. 04-06's
SUMMARY claims clean `ruff check src/token_world/mechanic/seeds/` but not the
test tree; `ruff check` over the full test tree now flags these. 04-07 does
not touch these files.

**Why deferred:** Out of scope per CLAUDE.md §4 scope boundary. 04-07's new
files (`test_look.py`, `test_find_nearest.py`, `test_aoe.py`, `test_speak.py`,
`test_try_door.py` + the 5 mechanic modules and `_helpers.py` addition) all
pass `ruff check` and `ruff format --check` cleanly after the plan's run.

**Next action:** A future plan (04-12 cleanup) runs `ruff check --fix
tests/test_mechanic/test_seeds/` and either reflows the E501 docstring or
adds a `# noqa: E501` ack. All four findings are `--fix`-automatable.

## 04-09 discoveries

### SIM102 in `tests/test_integration/test_use_cases.py` (predates 04-09)

**Found during:** 04-09 Task 3 phase-gate (`ruff check
tests/test_integration/`).

**File:**
- `tests/test_integration/test_use_cases.py` — one SIM102
  (`elif outcome == "pass":` containing nested `if not any_mechanic_fired`
  at lines ~500-503 of the post-D-38 file). Combine into a single
  `elif outcome == "pass" and not any_mechanic_fired:`.

**Issue:** Pre-existing finding in code committed by 04-04 (commit
`55cff4f`); 04-09 left the W5 explicit-outcome-branching block
unchanged structurally (the new D-38 stub-probe block sits earlier
in the function). Ruff continues to surface it under the broader
`ruff check tests/` lens.

**Why deferred:** Out of scope per CLAUDE.md scope-boundary — the
nested `if` is in a code region 04-09 did not modify. `ruff check`
on the 12 files this plan actually touched is clean.

**Next action:** A future plan (04-12 cleanup) runs `ruff check
--fix --select SIM102 tests/test_integration/test_use_cases.py`,
or — when the W5 branching grows additional cases — restructures
the outcome dispatch into a single match-statement.
