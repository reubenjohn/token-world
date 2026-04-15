---
phase: 17-operator-dev-ergonomics
plan: "02"
subsystem: dashboard-ops
tags: [dashboard, pid-file, run-status, ops, tdd]
dependency_graph:
  requires: [17-01]
  provides: [load_run_status, run-status-dot, pid-file-lifecycle]
  affects: [dashboard.stats, scripts.run_unattended]
tech_stack:
  added: []
  patterns: [pid-file-NDJSON, SIGINT-handler, os.kill-liveness-probe]
key_files:
  created:
    - tests/test_dashboard/test_run_status.py
    - tests/test_scripts/test_run_unattended_stop.py
  modified:
    - scripts/run_unattended.py
    - src/token_world/dashboard/panels/stats.py
decisions:
  - ".stop startup check exits 2 with WARNING to stderr before any expensive setup"
  - "SIGINT handler exits with code 130 (conventional) and removes .run-pid"
  - "Colored dot uses static Tailwind classes: bg-green-500/bg-yellow-400/bg-slate-600 — no animation per CONTEXT.md"
  - "load_run_status degrades to idle on any JSON/OS error (T-17-02-02)"
metrics:
  duration: "~30 minutes"
  completed: "2026-04-14"
  tasks_completed: 2
  files_changed: 4
---

# Phase 17 Plan 02: PID File + .stop Check + Run-Status Dot Summary

Closes two operator pain points from sessions 4-6: stale .stop files silently halting runs, and no visibility into whether a run is live from the dashboard.

## What Was Built

**SC-3/OPS-01 — run_unattended.py hardening:**
- `.stop` check at startup: exits 2 with `WARNING: .stop file present at {path}; delete it before running.` to stderr
- PID file: writes `{"pid": int, "started_at": "ISO8601"}` to `<universe>/.run-pid` after args parsed
- `try/finally` wrapping runner.run() guarantees `.run-pid` removal on both clean exit and SystemExit halt
- SIGINT handler calls `_remove_pid_file()` then `sys.exit(130)`
- Removed duplicate `stop_path` assignment that existed lower in main()

**SC-3/DASHBOARD-07 — Dashboard stats strip:**
- `load_run_status(universe_dir)` reads `.run-pid`, validates PID via `os.kill(pid, 0)`, returns `{state, pid, started_at}`
- `render_cells()` gains `run_status=` parameter; prepends Run cell when provided
- `mount_stats_strip()` calls `load_run_status()` on every 2s poll and renders colored dot
- Dot classes: green=running, yellow=stale, grey=idle; tooltip shows PID + start time

## Tests

- `tests/test_scripts/test_run_unattended_stop.py` — 4 cases (.stop exits nonzero, stderr names path, PID file written+removed, JSON shape)
- `tests/test_dashboard/test_run_status.py` — 5 cases (running/stale/idle/render-cell/corrupted-json)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
- `tests/test_scripts/test_run_unattended_stop.py` — 4 passed
- `tests/test_dashboard/test_run_status.py` — 5 passed
- Commit: `c7c8345`
