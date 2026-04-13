---
phase: 07-attention-and-consciousness
plan: "01"
subsystem: engine
tags: [dataclasses, long-running-actions, thresholds, serialization, pure-python]

requires:
  - phase: 05-simulation-engine
    provides: VisibilityProjector projection dict shape (D-09 dot-notation evaluation target)
  - phase: 01-graph-foundation
    provides: ALLOWED_PROPERTY_TYPES constraint (list/dict/str/int/float/bool/None — no tuple)

provides:
  - ThresholdSpec frozen dataclass (property/op/value fields, D-19, D-23)
  - LongRunningAction frozen dataclass with to_dict/from_dict (D-02, D-16, D-23)
  - ThresholdEvaluator classmethod evaluator — 6 operators, D-09 safe defaults (D-03, D-09)
  - Public exports via token_world.engine __init__.py

affects:
  - 07-02 (LongRunningHook — consumes LongRunningAction and ThresholdEvaluator)
  - 07-03 (visibility.py attention extension — consumes LongRunningAction.payload)
  - 07-04 (engine.py hook integration — consumes all three primitives)
  - 07-05 through 07-07 (seed mechanics — return LongRunningAction from apply())

tech-stack:
  added: []
  patterns:
    - "Frozen dataclass with slots=True for engine contracts (consistent with YieldSignal, Mutation)"
    - "tuple in-memory / list[dict] on-graph serialization boundary for thresholds"
    - "Classmethod-only evaluator class for pure-function semantics with _OPS dispatch dict"
    - "D-09 safe-default: all error paths (missing node/prop, unknown op, type mismatch) return None not raise"

key-files:
  created:
    - src/token_world/engine/long_running.py
    - tests/test_engine/test_long_running.py
  modified:
    - src/token_world/engine/__init__.py

key-decisions:
  - "D-23: frozen dataclasses (not Pydantic) — consistent with YieldSignal, Mutation, SnapshotInfo"
  - "D-19: ThresholdSpec field names exactly property/op/value — op validation deferred to evaluator"
  - "D-16: turns_total=None signals indefinite duration (drunkenness/lingering states); JSON null roundtrips correctly"
  - "D-03: exactly 6 operators via _OPS dispatch dict — no lambda passed to graph, no DSL"
  - "D-09: all 4 error paths return None (missing node, missing prop, unknown op, type mismatch) — never raises"
  - "Serialization boundary: tuple[ThresholdSpec,...] in-memory; list[dict] in to_dict() for ALLOWED_PROPERTY_TYPES"

patterns-established:
  - "ThresholdSpec is a pure data carrier — no validation at construction; evaluator enforces op set"
  - "LongRunningAction.from_dict handles missing payload key by defaulting to {}"
  - "ThresholdEvaluator._OPS is a class-level dict — extend by adding entries, not subclassing"

requirements-completed:
  - SIM-09
  - SIM-10

duration: 18min
completed: 2026-04-13
---

# Phase 7 Plan 01: LongRunningAction + ThresholdSpec + ThresholdEvaluator — pure-dataclass foundation

**Frozen dataclasses ThresholdSpec/LongRunningAction + pure-function ThresholdEvaluator with 6-operator dispatch, tuple-to-list serialization boundary, and 41 deterministic tests.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-13T00:00:00Z
- **Completed:** 2026-04-13
- **Tasks:** 3 (Tasks 1 + 2 executed as a single TDD cycle; Task 3 export + lint)
- **Files modified:** 3

## Accomplishments

- `ThresholdSpec` frozen dataclass with slots=True and exactly three fields: `property`, `op`, `value` (D-19, D-23). Construction permits any op string — evaluator is the enforcement point per D-19.
- `LongRunningAction` frozen dataclass with `to_dict()`/`from_dict()` handling the critical serialization boundary: in-memory `thresholds` is a `tuple[ThresholdSpec, ...]` (frozen, hashable); serialized form is `list[dict]` satisfying ALLOWED_PROPERTY_TYPES. `turns_total=None` (indefinite, D-16) roundtrips through `json.dumps/loads` correctly as JSON `null`.
- `ThresholdEvaluator` classmethod evaluator: resolves `"<node_id>.<prop_name>"` dot-notation against VisibilityProjector output, dispatches via `_OPS` dict, returns first firing `ThresholdSpec` or `None`. All four D-09 safe-default error branches (missing node, missing prop, unknown op, type mismatch) return `None` and never raise.
- Three new symbols exported via `token_world.engine.__init__` public API: `LongRunningAction`, `ThresholdSpec`, `ThresholdEvaluator`.
- 41 new tests; full suite passes at 1410 (baseline 1369).

## Task Commits

1. **Tasks 1-3: dataclasses + evaluator + exports** - `2af4904` (feat)

## Files Created/Modified

- `src/token_world/engine/long_running.py` — Module docstring citing D-01/D-03/D-09/D-13/D-15/D-16/D-19/D-23. ThresholdSpec, LongRunningAction, ThresholdEvaluator. Zero imports from KnowledgeGraph, VisibilityProjector, Anthropic SDK, or any engine stage.
- `src/token_world/engine/__init__.py` — Added import block and three entries to `__all__`.
- `tests/test_engine/test_long_running.py` — 41 tests: all 6 operators parametrized, 4 D-09 safe-default branches, JSON roundtrip (turns_total=None, turns_total=int, empty thresholds, complex payload, 2-threshold list), ALLOWED_PROPERTY_TYPES structural check, first-firing order, mutation immutability, malformed spec skipping.

## Decisions Made

- Followed plan exactly. All decisions (D-03, D-09, D-16, D-19, D-23) implemented as specified.
- `from_dict()` defaults `payload` to `{}` when key is absent — defensive for graph entries written before payload was added.
- `_evaluate_one` checks `if prop_name not in props` explicitly (rather than `props.get(prop_name) is None`) to distinguish a genuinely missing property from a property whose stored value is `None`. Both return `False`; the distinction matters for future debugging.

## Deviations from Plan

None — plan executed exactly as written.

Minor lint fixes applied by ruff pre-commit hook during commit:
- `from typing import Callable` upgraded to `from collections.abc import Callable` (UP035)
- Quoted return annotation `-> "LongRunningAction"` removed (UP037, redundant with `from __future__ import annotations`)
- Two E501 lines in test docstrings shortened
These are style-conformance corrections, not logic deviations.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 07-02 (`LongRunningHook`) can consume `LongRunningAction` and `ThresholdEvaluator` immediately.
- Plan 07-03 (visibility.py attention extension) can read `LongRunningAction.payload["attention_state"]`.
- Plan 07-04 (engine.py integration) can import all three symbols from `token_world.engine`.
- Wave 1 parallel plans (07-02) have no blocking dependency on each other — scope discipline (zero modifications to engine.py, visibility.py, context.py) enables safe parallel execution.

---
*Phase: 07-attention-and-consciousness*
*Completed: 2026-04-13*
