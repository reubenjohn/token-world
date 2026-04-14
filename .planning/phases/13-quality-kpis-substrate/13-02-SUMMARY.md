---
phase: 13-quality-kpis-substrate
plan: "02"
subsystem: quality, dashboard, ci
tags: [quality, dashboard, kpi, ci-gate, nicegui]
dependency_graph:
  requires:
    - token_world.quality (score, QualityReport, DimensionResult) — Plan 13-01
    - token_world.dashboard.panels.stats (mirror pattern)
    - token_world.universe.manager (UniverseManager.load — path resolution)
    - XDG_DATA_HOME env var (universe path resolution for test isolation)
  provides:
    - token_world.dashboard.panels.quality (mount_quality_panel, load_quality, render_cells)
    - scripts/check_quality_thresholds.py (CI gate: exits 1 on FAIL dimension)
    - tests/test_dashboard/test_quality_panel.py (7 unit tests)
    - tests/test_meta/test_quality_thresholds.py (3 CI gate tests)
  affects:
    - src/token_world/dashboard/app.py (Quality panel mounted above stats strip)
    - CLAUDE.md Script Catalog (new entry)
tech_stack:
  added: []
  patterns:
    - Dashboard panel mirrors stats.py: load_* / render_cells / mount_* separation
    - Graceful degradation: exceptions swallowed, empty QualityReport returned
    - 10s timer (quality) vs 2s timer (stats) — slower-moving signal
    - XDG_DATA_HOME env var for test fixture universe isolation
    - CI gate exits 1 with named failing dimensions on stderr
key_files:
  created:
    - src/token_world/dashboard/panels/quality.py
    - scripts/check_quality_thresholds.py
    - tests/test_dashboard/test_quality_panel.py
    - tests/test_meta/test_quality_thresholds.py
  modified:
    - src/token_world/dashboard/app.py
    - CLAUDE.md
decisions:
  - "10s refresh timer for quality panel (stats uses 2s); quality is a slower-moving signal"
  - "XDG_DATA_HOME env override (not TOKEN_WORLD_UNIVERSES_DIR) for test isolation — matched actual path resolution in paths.py"
  - "Test fixtures use universe.db (SQLite init) not universe.json — manager.load() checks for universe.db existence"
  - "render_cells is framework-agnostic (returns list[dict]) so tests run without NiceGUI server"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-14"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
  tests_added: 10
---

# Phase 13 Plan 02: Dashboard Quality Panel + CI Gate Summary

**One-liner:** NiceGUI Quality scorecard panel (10s refresh, coloured cells, graceful degradation) wired into dashboard app.py + standalone CI gate script exiting 1 with named-dimension errors on FAIL verdict.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Dashboard Quality panel + app.py wiring | d9cb64a | quality.py panel, app.py, test_quality_panel.py |
| 2 | CI gate script + pytest wiring + CLAUDE.md | 44361da | check_quality_thresholds.py, test_quality_thresholds.py, CLAUDE.md |

## What Was Built

### `src/token_world/dashboard/panels/quality.py`

Mirrors `stats.py` exactly. Three public exports:

- `load_quality(universe_dir, slug, last=50) -> QualityReport` — calls `score()` from `token_world.quality`; swallows all exceptions and returns an empty `QualityReport(slug=slug)` on failure (no subprocess, no shell-out).
- `render_cells(report) -> list[dict]` — framework-agnostic; returns `[{label, value, status}]` for each dimension plus a Verdict cell. Testable without a NiceGUI server.
- `mount_quality_panel(universe_dir, slug) -> container` — mounts a NiceGUI row with coloured Tailwind cells; refreshes every 10 seconds via `ui.timer(10.0, _rebuild)`.

Colour mapping: OK → `bg-green-900 text-green-300`, WARN → `bg-yellow-900 text-yellow-300`, FAIL → `bg-red-900 text-red-300`, UNKNOWN → `bg-slate-800 text-slate-400`.

### `src/token_world/dashboard/app.py`

Two lines added in `index()` before the stats strip:

```python
from token_world.dashboard.panels.quality import mount_quality_panel
mount_quality_panel(universe_dir, slug)
```

No other logic changed.

### `scripts/check_quality_thresholds.py`

Standalone CI gate script (mirrors `check_requirements_traceability.py` pattern):

- Accepts `slug` positional arg and `--window N` (default 50).
- Resolves universe via `UniverseManager().load(slug)`.
- Calls `score()` from `token_world.quality`; prints `render_table()` to stdout.
- Exits 0 on HEALTHY, DEGRADED, or INSUFFICIENT_DATA verdicts.
- Exits 1 on FAILED verdict: prints failing dimension names to stderr with `[FAIL]` prefix.

### Tests

**`tests/test_dashboard/test_quality_panel.py`** (7 tests):
- `render_cells` with HEALTHY/FAILED/DEGRADED/INSUFFICIENT_DATA verdicts
- All 8 dimensions produce 9 cells (8 + verdict)
- `load_quality` degrades on missing universe dir and empty universe

**`tests/test_meta/test_quality_thresholds.py`** (3 tests):
- Healthy fixture (20 clean ticks) → exit 0
- Failing fixture (20 all-refused ticks) → exit 1, "action coherence" in stderr
- Missing universe → exit 1, "error" in stderr

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion used wrong case for dimension name**
- **Found during:** Task 2 first test run
- **Issue:** Plan template asserted `"action coherence" in result.stderr` but stderr contains `"Action coherence"` (capital A from `DimensionResult.name`)
- **Fix:** Changed assertion to compare against `result.stderr.lower()` (case-insensitive)
- **Files modified:** tests/test_meta/test_quality_thresholds.py
- **Commit:** 44361da (included after fix)

**2. [Rule 1 - Bug] Ruff import order fix**
- **Found during:** Task 1 commit (pre-commit hook)
- **Issue:** Import order in test file triggered ruff's isort rule
- **Fix:** ruff auto-reformatted import block
- **Files modified:** tests/test_dashboard/test_quality_panel.py
- **Commit:** d9cb64a

### Implementation Note: XDG_DATA_HOME vs TOKEN_WORLD_UNIVERSES_DIR

Plan template suggested using `TOKEN_WORLD_UNIVERSES_DIR` env var for test fixture isolation. After reading `src/token_world/universe/paths.py`, confirmed the actual path resolution uses `XDG_DATA_HOME` (not a custom env var). Test fixtures set `XDG_DATA_HOME=tmp_path/xdg_home` so `UniverseManager` resolves universes to `tmp_path/xdg_home/token_world/universes/<slug>/`.

### Implementation Note: universe.db Required

Plan template wrote `universe.json` in fixtures. After reading `manager.py`, confirmed `manager.load()` checks for `universe.db` (not `universe.json`). Test fixtures create a minimal SQLite `universe.db` via `sqlite3.connect`.

## Known Stubs

None. All cells render live data from `token_world.quality.score()`.

## Threat Flags

None. All new surface is local-only, read-only, Python import (no subprocess, no network).

## Self-Check

**Created files exist:**
- src/token_world/dashboard/panels/quality.py — FOUND
- scripts/check_quality_thresholds.py — FOUND
- tests/test_dashboard/test_quality_panel.py — FOUND
- tests/test_meta/test_quality_thresholds.py — FOUND

**Commits exist:**
- d9cb64a — FOUND
- 44361da — FOUND

**Tests:** 10/10 passing (7 dashboard panel + 3 CI gate)

**Full suite:** 1973 passed, 14 skipped (pre-existing traceability drift failure unrelated to this plan, documented in 13-01-SUMMARY.md)

**Lint/format:** ruff check and ruff format --check pass on all new files

**app.py wiring confirmed:** `grep -n mount_quality_panel src/token_world/dashboard/app.py` shows lines 76+78

## Self-Check: PASSED
