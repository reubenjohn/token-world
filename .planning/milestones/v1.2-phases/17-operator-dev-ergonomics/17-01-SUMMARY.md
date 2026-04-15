---
phase: 17-operator-dev-ergonomics
plan: "01"
subsystem: inspect-cli
tags: [cli, inspect, tick, mechanics, git-history, tdd]
dependency_graph:
  requires: []
  provides: [load_stage_data, StageNotFoundError, MechanicRow.first_authored_commit, aggregate.history]
  affects: [cli.tick, cli.mechanics]
tech_stack:
  added: []
  patterns: [subprocess-git-log, path-traversal-guard]
key_files:
  created:
    - tests/test_inspect/__init__.py
    - tests/test_inspect/test_tick_stage.py
    - tests/test_inspect/test_mechanics_history.py
  modified:
    - src/token_world/inspect/tick.py
    - src/token_world/inspect/mechanics.py
    - src/token_world/cli.py
decisions:
  - "tick_id path-traversal guard via regex [A-Za-z0-9_.-]+ (T-17-01-01)"
  - "git --follow used for mechanic rename tracking; graceful None on timeout or missing repo"
  - "render_table shows history columns only when any row has data (backward compat)"
metrics:
  duration: "~35 minutes"
  completed: "2026-04-14"
  tasks_completed: 2
  files_changed: 6
---

# Phase 17 Plan 01: CLI Tick Stage Inspector + Mechanics Git History Summary

CLI inspection shortcuts operators reached for manually in sessions 4-6: `diagnostics/tick_N/classification/` and `git log mechanics/` are now one flag away.

## What Was Built

**SC-1 — Tick stage inspector:**
- `load_stage_data(universe_dir, tick_id, stage)` reads from `diagnostics/tick_<id>/classification|matching|observation/`
- `StageNotFoundError` raised when stage directory absent
- `render_stage_table(data, raw=False)` shows parsed JSON or raw prompt+response text
- `render_stage_json(data)` for `--format json` path
- tick_id path-traversal guard via `_SAFE_TICK_ID_RE` (T-17-01-01)
- `token-world tick <slug> <id> --stage classification|matcher|observer [--raw]` flags added to CLI

**SC-2a — Mechanics git history:**
- `MechanicRow` gains `first_authored_commit: str | None` and `first_authored_timestamp: str | None`
- `_git_first_commit()` helper runs `git log --follow --format=%H %aI` with 5s timeout, graceful `None` on any error
- `aggregate(..., history=True)` populates git fields; default `history=False` incurs zero subprocess overhead
- `render_table()` shows extra columns only when any row has history data
- `token-world mechanics <slug> --history` flag added to CLI

## Tests

- `tests/test_inspect/test_tick_stage.py` — 8 cases (all 3 stages, StageNotFoundError, ValueError, format json)
- `tests/test_inspect/test_mechanics_history.py` — 5 cases (git fields populated, no-subprocess when history=False, graceful degrade, table columns, json null fields)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
- `tests/test_inspect/test_tick_stage.py` — 8 passed
- `tests/test_inspect/test_mechanics_history.py` — 5 passed
- Commit: `2836fd2`
