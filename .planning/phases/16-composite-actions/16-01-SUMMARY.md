---
phase: 16-composite-actions
plan: "01"
subsystem: engine/classifier
tags: [composite-actions, schema, classifier, back-compat]
dependency_graph:
  requires: []
  provides: [VerdictOk.actions, SCHEMA_VERSION-2.0, composite-actions-design-doc]
  affects: [engine.py, all engine tests]
tech_stack:
  added: []
  patterns: [pydantic-min-length-constraint, back-compat-property]
key_files:
  created:
    - docs/design/composite-actions.md
  modified:
    - src/token_world/engine/models.py
    - src/token_world/engine/classifier.py
    - tests/test_engine/test_models.py
    - tests/test_engine/test_classifier.py
    - tests/test_engine/conftest.py
    - tests/test_engine/test_decider.py
    - tests/test_engine/test_engine_run_tick.py
    - tests/test_engine/test_engine_passive_sweep.py
    - tests/test_engine/test_engine_projected_state.py
    - tests/test_engine/test_llm_backend_integration.py
    - tests/test_engine/test_autopilot_integration.py
    - tests/test_engine/test_sleep_integration.py
    - tests/test_engine/test_daydream_integration.py
    - tests/test_engine/test_drunk_integration.py
    - tests/test_regression/conftest.py
    - tests/test_universe/test_mcp_tools.py
decisions:
  - "Option 1 chosen: classifier emits actions list (lowest blast radius, no extra LLM call)"
  - "back-compat @property classified returns actions[0] — zero engine.py changes needed"
  - "SCHEMA_VERSION bumped to 2.0 to signal prompt contract change to hash registry"
  - "_apply_known_target_check iterates all sub-actions to catch hallucinated targets"
metrics:
  duration: ~25 minutes
  completed: 2026-04-14
  tasks_completed: 3
  files_modified: 17
---

# Phase 16 Plan 01: Composite Actions Design + Schema Bump Summary

VerdictOk schema upgraded from single `classified: ClassifiedAction` to `actions: list[ClassifiedAction]` (min_length=1) with back-compat `@property classified` returning `actions[0]`; classifier `_SYSTEM_PROMPT` updated to emit `actions:[...]` array; `SCHEMA_VERSION` bumped to `"2.0"`; design doc created.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| T1 | Write docs/design/composite-actions.md | d1b5a08 | docs/design/composite-actions.md |
| T2 | Update models.py — VerdictOk schema + back-compat property | d1b5a08 | src/token_world/engine/models.py, tests/test_engine/test_models.py |
| T3 | Update classifier.py — _SYSTEM_PROMPT + SCHEMA_VERSION | d1b5a08 | src/token_world/engine/classifier.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated all test mock responses from old "classified" schema to new "actions" schema**
- **Found during:** Task 3 verification (uv run pytest tests/test_engine/ -x -q)
- **Issue:** 15 test files contained mock LLM responses with the old `"classified": {...}` JSON shape; `FakeClassifier` in regression conftest also used old `VerdictOk(classified=...)` constructor
- **Fix:** Updated all mock response constants and inline `json.dumps` calls across: test_classifier.py, test_models.py, test_decider.py, test_engine_run_tick.py, test_engine_passive_sweep.py, test_engine_projected_state.py, test_llm_backend_integration.py, test_autopilot_integration.py, test_sleep_integration.py, test_daydream_integration.py, test_drunk_integration.py, conftest.py (engine), test_mcp_tools.py, test_regression/conftest.py
- **Files modified:** 14 test files + regression conftest
- **Commit:** d1b5a08

## Prompt Hash Update

`willowbrook` universe exists — prompt hash baseline refreshed:
- `classifier_system_prompt`: `efe37e6dc59b722c17ec20047df472c1ff2d16057dfd56dddc43acdbe99af8ef`

## Known Stubs

None — all schema changes are complete and wired. `VerdictOk.actions` is fully implemented with Pydantic enforcement. Back-compat property `classified` returns `actions[0]`.

## Threat Flags

None — T-16-01 mitigated by `Field(min_length=1)` (empty actions list raises `ValidationError` before reaching engine). No new network endpoints or trust boundary surfaces introduced.

## Test Results

- 2011 tests passed, 14 skipped (pre-existing)
- 1 pre-existing failure: `tests/test_meta/test_requirements_traceability.py` — phase 19 traceability drift, unrelated to this plan (confirmed pre-existing via `git stash` verification)
- Ruff clean: `All checks passed!`

## Self-Check: PASSED

- `docs/design/composite-actions.md` exists and contains "Option 1", "Option 2", "Option 3" ✓
- `VerdictOk.actions: list[ClassifiedAction]` with `min_length=1` ✓
- `classified` is `@property` returning `self.actions[0]` ✓
- `SCHEMA_VERSION = "2.0"` in classifier.py ✓
- `_SYSTEM_PROMPT` emits `actions:[...]` ✓
- Commit d1b5a08 exists ✓
- Back-compat verified: `python -c "... assert v.classified.verb == 'x'; print('back-compat ok')"` → `back-compat ok` ✓
