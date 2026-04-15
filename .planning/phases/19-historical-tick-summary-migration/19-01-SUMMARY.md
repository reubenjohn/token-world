---
phase: 19
plan: "01"
subsystem: scripts
tags: [migration, tick-summaries, groundedness, ops]
dependency_graph:
  requires: [phase-13-quality-kpis]
  provides: [honest-willowbrook-archive]
  affects: [quality-scorer-groundedness]
tech_stack:
  added: []
  patterns: [atomic-tempfile-write, dry-run-apply-pattern]
key_files:
  created:
    - scripts/migrate_tick_summaries.py
    - tests/test_scripts/test_migrate_tick_summaries.py
    - .planning/phases/19-historical-tick-summary-migration/19-01-PLAN.md
  modified:
    - .planning/phases/19-historical-tick-summary-migration/19-VERIFICATION.md
decisions:
  - "Set refused=true + refusal_reason=mechanic_check_failed on false-EXECUTED ticks; scorer §E6 treats mechanic_check_failed as grounded (score 1.0 for match rate, 0.5 for mutation count)"
  - "Added universe_dir override param to run() for testability without UniverseManager"
metrics:
  duration: "~15 min"
  completed: "2026-04-14"
  tasks_completed: 3
  files_changed: 3
---

# Phase 19 Plan 01: Historical Tick Summary Migration Summary

Backfill pre-ENGINE-01 false-EXECUTED records in willowbrook with honest `refused=true, refusal_reason=mechanic_check_failed` so the quality scorer's Groundedness dimension no longer penalises them.

## What Was Built

`scripts/migrate_tick_summaries.py` — scans all tick files for the false-EXECUTED pattern (`refused=false, yielded=false, mutations.count=0`) and rewrites them atomically. Supports `--dry-run` (show table, no writes) and `--apply` (atomic temp-file rewrite). Idempotent: skips ticks already marked refused.

Applied to willowbrook: **14 ticks backfilled** (IDs 5, 6, 8, 9, 11, 13, 14, 19, 22, 29, 30, 34, 39, 42).

Post-migration `token-world quality willowbrook` Groundedness: **1.00 (50/50 grounded)**.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `scripts/migrate_tick_summaries.py` exists: FOUND
- `tests/test_scripts/test_migrate_tick_summaries.py` exists: FOUND (10 tests passing)
- Commit `956ff43` exists: FOUND
- Groundedness 1.00 post-migration: VERIFIED
