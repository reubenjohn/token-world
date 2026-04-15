---
phase: 17-operator-dev-ergonomics
verified: 2026-04-14T00:00:00Z
status: gaps_found
score: 3/5
overrides_applied: 0
gaps:
  - truth: "Dashboard registry panel shows First authored and Last invoked columns consuming mechanics --history --format json"
    status: failed
    reason: "No dashboard registry/mechanics panel exists in src/token_world/dashboard/panels/. The 17-02 PLAN must_haves listed this as required but the SUMMARY only changed stats.py and run_unattended.py. The CLI --history flag (SC-2a) was delivered; the dashboard SC-2b half was not."
    artifacts:
      - path: "src/token_world/dashboard/panels/registry.py"
        issue: "File does not exist — dashboard mechanics registry panel was never created"
    missing:
      - "Create a dashboard mechanics registry panel (e.g., panels/registry.py or panels/mechanics_registry.py) that loads token-world mechanics <slug> --history --format json and renders First authored + Last invoked columns"
      - "Wire the panel into dashboard/app.py"
  - truth: "Every yield-resolution event in operator-log.jsonl carries the authoring subagent's final JSON; overlap score computed against registry before authoring; subagent prompt includes overlap report"
    status: partial
    reason: "overlap.py exists with compute_overlap() and compute_overlap_report(). yield-handler.md has {OVERLAP_REPORT} placeholder + 0.7 threshold rule. subagent.py has append_decision_log() + overlap_report param in mechanic_author_prompt(). BUT: (1) compute_overlap/compute_overlap_report is never called from the operator harness — no call site exists outside the module itself; (2) append_decision_log is never called after yield resolution — SUMMARY 17-04 explicitly flagged this as 'not yet wired into the operator harness call site'. The functions exist and are tested in isolation but the SC-5 end-to-end requirement (operator-log.jsonl entries actually written, overlap report actually injected) is unmet."
    artifacts:
      - path: "src/token_world/operator/subagent.py"
        issue: "build_mechanic_author_agent() calls mechanic_author_prompt() without overlap_report= parameter, so the prompt section is always '(no overlap analysis available)'"
      - path: "src/token_world/operator/external.py"
        issue: "Yield resolution handler does not call append_decision_log() after authoring completes; operator-log.jsonl is never written in production flow"
    missing:
      - "Wire compute_overlap_report() call before build_mechanic_author_agent() in the operator harness; pass result as overlap_report= to mechanic_author_prompt()"
      - "Wire append_decision_log() call in the operator harness after yield resolution completes (resolved or rejected), passing the subagent outcome JSON"
---

# Phase 17: Operator & Dev Ergonomics Verification Report

**Phase Goal:** Every operator investigation the author reached for during sessions 4-6 becomes a one-liner on the CLI or a sticky surface on the dashboard.
**Verified:** 2026-04-14
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1: `token-world tick <slug> <id> --stage classification\|matcher\|observer [--raw]` works | VERIFIED | `load_stage_data()` in `inspect/tick.py` handles all 3 stages; `--stage` + `--raw` flags wired in `cli.py` lines 1498-1541; 8 tests pass |
| 2 | SC-2a: `token-world mechanics <slug> --history` shows first_authored_commit + timestamp | VERIFIED | `MechanicRow` has `first_authored_commit`/`first_authored_timestamp` fields; `aggregate(history=True)` calls `_git_first_commit()`; `render_table()` shows extra columns; 5 tests pass |
| 3 | SC-2b: Dashboard registry panel renders First authored/Last invoked columns | FAILED | No dashboard registry/mechanics panel file exists; `app.py` has no registry panel mount; 17-02 SUMMARY changed only `stats.py` and `run_unattended.py` |
| 4 | SC-3: `run_unattended.py` writes `.run-pid`, exits 2 on `.stop`; stats strip shows run-status dot | VERIFIED | `.stop` check at line 199 exits 2 with WARNING; PID file written at line 222; `try/finally` removes on exit; `load_run_status()` + colored dot in `stats.py`; 9 tests pass |
| 5 | SC-4: Clicking agent node opens inspector drawer with 6 sections | VERIFIED | `agent_inspector.py` has `render_agent_inspector_sections()` with exactly 6 sections; `graph_canvas.py` `_on_node_click` routes agent nodes to `_rebuild_agent_drawer`; 10 tests pass |
| 6 | SC-5: overlap.py `compute_overlap()`; yield-handler.md overlap report + 0.7 threshold; subagent.py appends to operator-log.jsonl | PARTIAL | `overlap.py` exists with `compute_overlap()` + `compute_overlap_report()`; `yield-handler.md` has `{OVERLAP_REPORT}` placeholder and 0.7 decision rule; `subagent.py` has `append_decision_log()` and accepts `overlap_report=` param — BUT `compute_overlap_report` is never called from any harness, `build_mechanic_author_agent()` does not pass `overlap_report=`, and `append_decision_log` is never called from any production call site |

**Score:** 3/5 truths fully verified (SC-1, SC-2a, SC-3, SC-4 pass; SC-2b and SC-5 have gaps)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/token_world/inspect/tick.py` | load_stage_data + --stage/--raw | VERIFIED | All 3 stages, path-traversal guard, render functions present |
| `src/token_world/inspect/mechanics.py` | MechanicRow git history fields | VERIFIED | `first_authored_commit`, `first_authored_timestamp`, `_git_first_commit()`, `aggregate(history=True)` all present |
| `scripts/run_unattended.py` | PID file + .stop check + SIGINT | VERIFIED | `.stop` check at startup exits 2; `.run-pid` written post-args; `try/finally` + SIGINT handler remove it |
| `src/token_world/dashboard/panels/stats.py` | load_run_status + run-status dot | VERIFIED | `load_run_status()`, `render_cells(run_status=)`, `mount_stats_strip()` with dot and tooltip present |
| `src/token_world/dashboard/panels/agent_inspector.py` | 6-section agent inspector | VERIFIED | `render_agent_inspector_sections()` returns exactly 6 sections; `mount_agent_inspector()` uses NiceGUI `ui.expansion()` |
| `src/token_world/dashboard/panels/graph_canvas.py` | Agent node routing to inspector | VERIFIED | `_on_node_click` checks `type == "agent"` and routes to `_rebuild_agent_drawer` |
| `src/token_world/dashboard/panels/registry.py` (or equivalent) | Dashboard mechanics registry with history columns | MISSING | File does not exist; no registry panel in `app.py` |
| `src/token_world/operator/overlap.py` | `compute_overlap()` function | VERIFIED | `compute_overlap()` + `compute_overlap_report()` with Jaccard similarity + top-3 report + 0.7 RECOMMENDATION |
| `src/token_world/operator/subagent.py` | `append_decision_log()` + overlap injection | PARTIAL | Function defined and in `__all__`; `mechanic_author_prompt()` accepts `overlap_report=` — but neither is called from production harness |
| `.planning/agent-prompts/yield-handler.md` | Overlap report + 0.7 threshold | VERIFIED | `{OVERLAP_REPORT}` placeholder present; "If overlap score >= 0.7, STRONGLY prefer editing" decision rule present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tick.py::load_stage_data` | `<universe>/diagnostics/tick_<id>/{stage}/` | Path read from diagnostics directory | WIRED | Reads `diagnostics/tick_<id>/classification/`, `matching.json`, `observation/` |
| `mechanics.py::aggregate` | `git log --follow --format=...` | subprocess when history=True | WIRED | `_git_first_commit()` uses subprocess, 5s timeout, graceful None on error |
| `stats.py::load_run_status` | `<universe>/.run-pid` | Path read + `os.kill(pid, 0)` | WIRED | Reads PID JSON, probes liveness via signal 0 |
| `run_unattended.py::main` | `<universe>/.run-pid` | write on start, remove in finally | WIRED | PID file written after args parsed; `try/finally` + SIGINT handler remove it |
| `graph_canvas.py::_on_node_click` | `agent_inspector.py::mount_agent_inspector` | `properties.get("type") == "agent"` branch | WIRED | Lazy import + call to `_rebuild_agent_drawer` which calls `mount_agent_inspector` |
| `subagent.py::build_mechanic_author_agent` | `overlap.py::compute_overlap_report` | `overlap_report=` param in prompt | NOT_WIRED | `build_mechanic_author_agent()` calls `mechanic_author_prompt()` WITHOUT `overlap_report=` param; overlap defaults to "(no overlap analysis available)" |
| Operator harness yield resolution | `subagent.py::append_decision_log` | call after resolution completes | NOT_WIRED | No production call site for `append_decision_log`; operator-log.jsonl never written |
| Dashboard app | Registry/mechanics panel | `mount_*` call in `app.py` | NOT_WIRED | No mechanics registry panel exists or is mounted |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 17 unit tests pass | `uv run pytest tests/test_inspect/ tests/test_scripts/test_run_unattended_stop.py tests/test_dashboard/test_run_status.py tests/test_dashboard/test_agent_inspector.py tests/test_operator/test_overlap.py tests/test_operator/test_decision_log.py -q --tb=no` | 160 passed | PASS |
| Full test suite (non-meta) | `uv run pytest tests/ -q --tb=no --ignore=tests/test_meta/` | 2059 passed, 14 skipped | PASS |
| Meta traceability test | `uv run pytest tests/test_meta/test_requirements_traceability.py` | 1 FAILED | NOTE: Pre-existing drift across phases 13-19; REQ-V12-* IDs referenced by ROADMAP are missing from REQUIREMENTS.md; not a Phase 17 implementation failure |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/token_world/operator/subagent.py` | 185 | `mechanic_author_prompt(universe=universe, yield_json=yield_signal.to_json())` — missing `overlap_report=` | Blocker | Overlap analysis never injected into production subagent prompts |
| No call site | — | `append_decision_log` exported but never called from harness | Blocker | operator-log.jsonl never populated in production |
| No file | — | Dashboard registry/mechanics panel missing | Blocker | SC-2b dashboard requirement unmet |

### Gaps Summary

**Gap 1 — Dashboard Registry Panel (SC-2b missing):**
The PLAN 17-02 must_haves include "Dashboard registry panel shows First authored and Last invoked columns" but this was never implemented. The 17-02 SUMMARY changed only `stats.py` and `run_unattended.py`. No `panels/registry.py` or equivalent exists; `app.py` has no registry panel mount. The CLI half of SC-2 (--history flag) is complete; the dashboard half is absent.

**Gap 2 — SC-5 overlap + decision log not wired into production (partial):**
The building blocks exist (`overlap.py`, `append_decision_log`, prompt parameter) and are unit-tested in isolation, but none are wired into the actual operator harness:
- `build_mechanic_author_agent()` never passes `overlap_report=` so the overlap section in every real subagent prompt is "(no overlap analysis available)"
- `append_decision_log` is never called after yield resolution so `operator-log.jsonl` is never written during actual runs
- The SUMMARY itself flagged this as a "known stub / separate integration step" — the functions are tested but not integrated

These two gaps prevent the phase from being marked passed. SC-1, SC-3, SC-4 are fully delivered with solid test coverage.

---

_Verified: 2026-04-14_
_Verifier: Claude (gsd-verifier)_
