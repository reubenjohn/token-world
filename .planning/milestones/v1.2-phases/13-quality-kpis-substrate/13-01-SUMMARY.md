---
phase: 13-quality-kpis-substrate
plan: "01"
subsystem: quality
tags: [quality, kpi, scorer, cli, tdd]
dependency_graph:
  requires:
    - token_world.inspect._shared (iter_tick_files, read_json_file)
    - tick_summaries/ticks/*.json schema
    - universe.db graph_snapshots table
  provides:
    - token_world.quality (score, QualityReport, DimensionResult)
    - token-world quality CLI command
  affects:
    - src/token_world/cli.py (new command registered)
    - CLAUDE.md Script Catalog
tech_stack:
  added:
    - src/token_world/quality/ subpackage (4 files)
  patterns:
    - Single-pass tick scanner (mirrors stats.aggregate pattern)
    - Graceful degradation on missing dir/DB (never raises)
    - Canonical producer rule: compute once in quality/, read many
key_files:
  created:
    - src/token_world/quality/__init__.py
    - src/token_world/quality/report.py
    - src/token_world/quality/thresholds.py
    - src/token_world/quality/scorer.py
    - tests/test_cli/test_quality.py
  modified:
    - src/token_world/cli.py
    - CLAUDE.md
decisions:
  - "Groundedness uses Option A proxy (mutation-backed rate) per RESEARCH.md recommendation; true observer cross-check deferred"
  - "Novel subtype rate implemented as 8th dimension (WARN-only gate at zero for >=30 ticks, no FAIL)"
  - "Graph fan-out reads graph_snapshots table via sqlite3 direct; degrades gracefully if table missing"
  - "CLI exits 0 always; CI gate is separate scripts/check_quality_thresholds.py (Plan 02)"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-14"
  tasks_completed: 2
  files_created: 5
  files_modified: 2
  tests_added: 13
---

# Phase 13 Plan 01: Quality Subpackage + CLI Command Summary

**One-liner:** 8-dimension simulation quality scorer in `token_world.quality` with `render_table`/`render_json` renderers and `token-world quality <slug>` CLI command, TDD-built against 13 unit tests.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Quality subpackage — report, thresholds, scorer | 30f8058 | quality/__init__.py, report.py, thresholds.py, scorer.py, test_quality.py |
| 2 | Wire `token-world quality` CLI command | 5365a74 | cli.py, CLAUDE.md |

## What Was Built

### `src/token_world/quality/` subpackage

**`report.py`** — `DimensionResult(name, status, score, detail)` and `QualityReport(slug, window, tick_count, dimensions, verdict)` dataclasses. `render_table()` produces the rubric scorecard format; `render_json()` produces machine-readable JSON for CI/dashboard consumption.

**`thresholds.py`** — All GREEN/RED threshold constants matching `docs/quality/sim-quality-rubric.md` verbatim. `compute_verdict()` derives HEALTHY/DEGRADED/FAILED/INSUFFICIENT_DATA from dimension statuses.

**`scorer.py`** — `score(universe_dir, *, slug, last=50) -> QualityReport`. Single-pass scanner over tick JSON files using `iter_tick_files`/`read_json_file` from `token_world.inspect._shared`. All 8 dimension scorers:

1. **Groundedness** — mutation-backed execution rate proxy (not refused, not yielded, mutations.count > 0); GREEN >= 0.95, RED < 0.85
2. **Character stability** — marker substring scan on `action_text`; GREEN >= 0.98, RED < 0.90
3. **Action coherence** — longest non-refuse streak + refuse_rate per 10 ticks; combined verdict
4. **Refusal cluster** — max consecutive refuses; FAIL if >= 5
5. **Vocabulary growth** — novel mechanic IDs rate per 10 ticks; stagnation at 30+ ticks = RED
6. **Conservation drift** — refused ticks with "conservation" in refusal_reason; GREEN <= 0.02, RED >= 0.10
7. **Graph fan-out** — slope of edges/nodes ratio across last 5 graph_snapshots rows; degrades gracefully if DB missing
8. **Novel subtype rate** — distinct new subtype values from mutation lists; WARN-only if zero for >= 30 ticks

### `token-world quality` CLI command

Registered in `cli.py` after `stats_universe`. Accepts `--last N` (default 50) and `--format table|json`. Exits 0 always; CI gate is `scripts/check_quality_thresholds.py` (Plan 02).

## TDD Gate Compliance

- RED gate: tests written first, confirmed failing with `ModuleNotFoundError` (12/13 tests hit import error, CLI test hit exit code 2)
- GREEN gate: implementation made all 13 tests pass
- No REFACTOR gate needed (code was clean on first pass; ruff auto-fixed one SIM108 and one formatting issue via pre-commit hook)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff SIM108: ternary operator in `_score_novel_subtype_rate`**
- **Found during:** Task 1 commit (pre-commit hook)
- **Issue:** `if/else` block setting `status` triggered ruff SIM108 rule
- **Fix:** Converted to ternary `status = "WARN" if ... else "OK"`
- **Files modified:** src/token_world/quality/scorer.py
- **Commit:** 30f8058 (included in task commit after ruff fix)

**2. [Rule 1 - Bug] Ruff format: test file line length**
- **Found during:** Task 1 commit (pre-commit hook)
- **Issue:** One line in test file exceeded line length limit
- **Fix:** ruff-format auto-reformatted
- **Files modified:** tests/test_cli/test_quality.py
- **Commit:** 30f8058

### Pre-existing Issue (Out of Scope)

`tests/test_meta/test_requirements_traceability.py::test_no_traceability_drift[active-milestone]` was already failing before this plan (phases 18-19 planning drift). Confirmed pre-existing by `git stash` test. Not caused by Plan 13-01 changes.

## Self-Check

**Created files exist:**
- src/token_world/quality/__init__.py — FOUND
- src/token_world/quality/report.py — FOUND
- src/token_world/quality/thresholds.py — FOUND
- src/token_world/quality/scorer.py — FOUND
- tests/test_cli/test_quality.py — FOUND

**Commits exist:**
- 30f8058 — FOUND
- 5365a74 — FOUND

**Tests:** 13/13 passing

**CLI:** `token-world quality --help` shows slug, --last, --format

## Self-Check: PASSED
