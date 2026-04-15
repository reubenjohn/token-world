---
phase: 05-simulation-engine
plan: 6
subsystem: engine
tags: [conservation, yaml, scaffold, mutation, verification]

# Dependency graph
requires:
  - phase: 05-simulation-engine
    provides: Mutation dataclass (graph/models.py), RefusalTemplate.render("conservation_violation") from Plan 05-03, scaffold.py idempotent guard pattern from Plan 05-01, universe_yaml.py template pattern from Plan 05-01

provides:
  - ConservationChecker.from_yaml(path) — soft-fail YAML loader returning enabled or disabled checker
  - ConservationChecker.verify(mutations) — O(1) no-op for empty config; net-delta scanner for configured universes
  - ConservationVerdict.ok() / ConservationVerdict.violation(deltas) — verdict shape for Plan 05-08 orchestrator
  - conservation_yaml.py template (CONSERVATION_YAML_TEMPLATE + render_conservation_yaml)
  - scaffold.py creates conservation.yaml idempotently in every new universe
  - token_world.engine exports ConservationChecker + ConservationVerdict

affects:
  - 05-08 (orchestrator wires checker into tick pipeline, calls graph.restore on violation)
  - future universes (conservation.yaml opt-in)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Soft-fail YAML loader: malformed/missing/non-mapping/non-list all yield disabled no-op — mirrors load_engine_config pattern"
    - "Opt-in conservation enforcement: empty conserved_properties = zero overhead (D-16)"
    - "Verdict + rollback split: checker only verifies, orchestrator handles rollback (Plan 05-08)"
    - "Idempotent scaffold: conservation.yaml created only if absent, never overwritten"

key-files:
  created:
    - src/token_world/engine/conservation.py
    - src/token_world/universe/templates/conservation_yaml.py
    - tests/test_engine/test_conservation.py
  modified:
    - src/token_world/engine/__init__.py
    - src/token_world/universe/templates/__init__.py
    - src/token_world/universe/scaffold.py

key-decisions:
  - "D-16: ConservationChecker runs after execute, before observation synthesis; empty config = no enforcement = O(1) opt-out"
  - "Checker never calls graph.restore() — rollback is the orchestrator's job (Plan 05-08)"
  - "T-05-CONS-CONFIG-INJECT mitigated: three explicit soft-fail paths (malformed YAML, non-mapping root, non-list conserved_properties)"
  - "T-05-CONS-BYPASS accepted: only set_property mutations checked; add_node/add_edge are graph-structural not value-changing"

patterns-established:
  - "conservation.py: from_yaml() soft-fail pattern mirrors engine/config.py load_engine_config"
  - "conservation_yaml.py: TEMPLATE constant + render_() function, exported from templates/__init__.py"

requirements-completed: [SIM-08]

# Metrics
duration: 62min
completed: 2026-04-13
---

# Phase 05 Plan 06: Conservation Checker YAML Summary

**Post-execute mutation scanner with YAML-configured conserved properties; disabled-by-default via `conserved_properties: []` for zero-cost opt-out (D-16, GAP-ENG06)**

## Performance

- **Duration:** ~62 min
- **Started:** 2026-04-13T13:44:56Z
- **Completed:** 2026-04-13T13:46:27Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- ConservationChecker + ConservationVerdict implemented with full TDD: 15 tests covering disabled checker (O(1) short-circuit), net-delta violation detection, balanced increment/decrement cancellation, all three soft-fail YAML loader paths, non-numeric property warnings, and RefusalTemplate integration shape
- conservation.yaml template module created mirroring universe_yaml.py pattern; exported from templates package
- scaffold.py extended to create conservation.yaml idempotently — every new universe gets the opt-in file; existing files are never overwritten

## Task Commits

1. **Task 1: ConservationChecker + ConservationVerdict (TDD)** - `49095bc` (feat)
2. **Task 2: conservation.yaml template + scaffold integration** - `7d46b5a` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/token_world/engine/conservation.py` — ConservationChecker (from_yaml, verify) + ConservationVerdict (ok, violation, is_violation)
- `src/token_world/engine/__init__.py` — Added ConservationChecker + ConservationVerdict to exports
- `src/token_world/universe/templates/conservation_yaml.py` — CONSERVATION_YAML_TEMPLATE + render_conservation_yaml()
- `src/token_world/universe/templates/__init__.py` — Added conservation_yaml exports
- `src/token_world/universe/scaffold.py` — Idempotent conservation.yaml creation block
- `tests/test_engine/test_conservation.py` — 15 tests (TDD: RED then GREEN)

## Decisions Made

- Verify-only design: checker never calls graph.restore() or mutates graph — rollback is the orchestrator's responsibility (Plan 05-08). Clean separation keeps the checker stateless and testable without a real graph.
- Accepted T-05-CONS-BYPASS: only `set_property` mutations are checked. `add_node`/`add_edge`/`remove_node`/`remove_edge` are structural, not value-changing. Documented in module docstring.
- T-05-CONS-CONFIG-INJECT fully mitigated via three separate soft-fail paths (malformed YAML, non-mapping root, non-list `conserved_properties`), each with a dedicated test.
- Used `warnings.warn(UserWarning)` (not logger.warning) for non-numeric property values to match the test's `pytest.warns(UserWarning)` pattern — ensures the caller can catch it programmatically.

## Deviations from Plan

None — plan executed exactly as written. The `warnings.warn` stacklevel was set to 2 (as specified in plan code block).

## Issues Encountered

- `ruff` flagged an unused `import warnings` in the test file (warnings.warn is not needed directly in tests — the module under test does the warning). Fixed by removing the import and running `ruff --fix`. No functional impact.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- ConservationChecker ready for Plan 05-08 (orchestrator) to wire into the tick pipeline
- Plan 05-08 call pattern: `checker = ConservationChecker.from_yaml(universe_path / "conservation.yaml")` at engine init; `verdict = checker.verify(mutations)` after each ChainExecutionEngine.execute; on violation: `graph.restore(pre_tick_snapshot_id)` + `RefusalTemplate.render("conservation_violation", {"violated_property": next(iter(verdict.violations))})`
- GAP-ENG06 closed

---
*Phase: 05-simulation-engine*
*Completed: 2026-04-13*
