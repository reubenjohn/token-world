---
phase: 05-simulation-engine
plan: 7
subsystem: engine
tags: [pydantic, json, tick-summary, cost-accounting, atomic-write, diagnostics]

requires:
  - phase: 05-simulation-engine
    provides: TickSummary Pydantic schema in models.py (Plan 05-01), _atomic_write_json helper in mechanic/diagnostics.py (Phase 04), ExecutionTrace/Mutation types

provides:
  - TickSummaryWriter: atomic per-tick JSON writer to universe/tick_summaries/ticks/tick_<id>.json
  - build_tick_summary: factory converting raw orchestrator outputs (verdict, decision, trace, mutations, timing, tokens) to TickSummary
  - Per-stage USD cost computation from Haiku/Sonnet rate constants in summary_writer.py

affects:
  - 05-08-PLAN (orchestrator wires TickSummaryWriter.write + build_tick_summary into run_tick)
  - Phase 6 SIM-12 batch/epoch compressor (reads tick_summaries/ticks/*.json)
  - Operator tooling / CLI replay (consumes per-tick JSON)

tech-stack:
  added: []
  patterns:
    - "Pydantic model_dump_json + json.loads roundtrip for strict-JSON dict before _atomic_write_json"
    - "Dataclass(slots=True) stateless writer — instantiate once, write many times"
    - "_flatten_trace_mutations: iterative stack-based tree walk (avoids recursion depth)"
    - "Decision isinstance() dispatch (ExecuteDecision/YieldDecision/RefuseDecision) for path-specific field population"

key-files:
  created:
    - src/token_world/engine/summary_writer.py
    - tests/test_engine/test_summary_writer.py
  modified:
    - src/token_world/engine/__init__.py

key-decisions:
  - "D-20: One JSON file per tick at tick_summaries/ticks/tick_<id>.json; idempotent overwrite by tick_id"
  - "D-21: schema_version=1 Literal in every written file for Phase 6 forward-compatibility"
  - "D-24: Cost tracked via hardcoded Haiku/Sonnet rate constants in summary_writer.py; no circuit breakers in Phase 5"
  - "Used json.loads(model_dump_json()) not model_dump() to guarantee JSON-serialisable dict before _atomic_write_json"
  - "Reused Phase 4 _atomic_write_json (tempfile+os.replace) — T-05-SUMMARY-PARTIAL-WRITE mitigation"

patterns-established:
  - "build_tick_summary: all three decision paths (execute/yield/refuse) produce a complete TickSummary — orchestrator must call even on refuse/yield per D-20"
  - "Per-stage cost: classifier=Haiku rates, observer=Sonnet rates, unknown=0.0 (forward-compat)"
  - "tick_summaries/ticks/ subdir created on demand (mkdir parents=True, exist_ok=True)"

requirements-completed:
  - SIM-11

duration: 4min
completed: 2026-04-13
---

# Phase 05 Plan 07: Tick Summary Writer Summary

**Atomic per-tick JSON writer (D-20/SIM-11) with execute/yield/refuse path factory and Haiku/Sonnet cost accounting, reusing Phase 4 atomic-write infrastructure**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-13T13:49:01Z
- **Completed:** 2026-04-13T13:52:27Z
- **Tasks:** 1 (TDD: RED + GREEN + lint/type clean)
- **Files modified:** 3

## Accomplishments

- `TickSummaryWriter.write(summary, universe_dir)` — writes `tick_summaries/ticks/tick_<id>.json` atomically (tempfile + os.replace), creates subdir on demand, idempotent overwrite
- `build_tick_summary(...)` — factory for all three decision paths: execute (matched_mechanic_id + mutations flattened from trace tree), yield (yielded=True, everything else None), refuse (refused=True + reason_code)
- Per-stage USD cost computed from `_HAIKU_*` / `_SONNET_*` rate constants declared in module (auditable, operator-adjustable)
- 18 tests covering writer contract, JSON round-trip, Pydantic re-validation, atomic write (no .tmp leftovers), all three decision paths, trace tree flattening, 4-tuple mutation shape, cost rates, timestamp format
- `TickSummaryWriter` and `build_tick_summary` exported from `token_world.engine`

## Task Commits

1. **Task 1: TickSummaryWriter + build_tick_summary factory (TDD)** - `63f5e62` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/token_world/engine/summary_writer.py` — TickSummaryWriter, build_tick_summary, cost helpers, trace flattener
- `tests/test_engine/test_summary_writer.py` — 18 tests (TDD)
- `src/token_world/engine/__init__.py` — added TickSummaryWriter and build_tick_summary to exports and __all__

## Decisions Made

- Used `json.loads(summary.model_dump_json())` rather than `summary.model_dump()` to guarantee a strict-JSON dict is passed to `_atomic_write_json`. Pydantic v2's `model_dump()` can return Python-native types if model fields are extended later; the JSON roundtrip is the contract test #17 enforces.
- Reused `_atomic_write_json` from `mechanic/diagnostics.py` (Phase 4 proven) rather than writing a new atomic helper — T-05-SUMMARY-PARTIAL-WRITE mitigation with zero new code.
- Iterative stack traversal for `_flatten_trace_mutations` (not recursive) to avoid Python recursion depth issues on deep chain traces.

## Deviations from Plan

None — plan executed exactly as written. All 17+ tests specified in the plan were implemented (18 actual, covering all specified scenarios plus `test_tokens_by_stage_structure`).

## Issues Encountered

Minor ruff lint fixes: import block sort order (auto-fixed with `--fix`), line-length issues in test helper signatures, and a format reflow in `summary_writer.py`. All resolved before commit.

## Known Stubs

None. Writer is fully functional; no placeholder data flows to any consumer.

## Threat Flags

None. No new network endpoints, auth paths, or trust-boundary surface introduced. Writer is purely local filesystem I/O using engine-internal tick IDs (not agent-supplied text).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 05-08 (SimulationEngine orchestrator) can now call `build_tick_summary(...)` + `writer.write(summary, universe_dir)` at the end of `run_tick` to close D-20
- `TickSummaryWriter` and `build_tick_summary` are exported from `token_world.engine` and ready to import
- `tick_summaries/ticks/` subdir is created on first write; `tick_summaries/` parent already scaffolded by `tmp_universe` fixture and universe scaffolding

## Self-Check: PASSED

- `src/token_world/engine/summary_writer.py` exists: FOUND
- `tests/test_engine/test_summary_writer.py` exists: FOUND
- `63f5e62` commit exists: FOUND
- `uv run pytest -x -q`: 1162 passed, 14 skipped (no regressions)
- `token_world.engine.ConservationChecker` still importable: VERIFIED

---
*Phase: 05-simulation-engine*
*Completed: 2026-04-13*
