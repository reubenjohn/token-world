---
phase: "06-resident-agent-end-to-end-loop"
plan: "03"
title: "Use-case regression suite: 35 Phase-3 UC manifests as E2E integration tests"
subsystem: "testing"
tags: ["regression", "use-cases", "DVAL-03", "fake-llm", "parametrize"]
dependency_graph:
  requires:
    - "03-use-case-library (35 UC manifests)"
    - "05-simulation-engine (SimulationEngine.run_tick, seed mechanics)"
    - "token_world.use_cases.loader.load_use_case"
  provides:
    - "tests/test_regression/ package"
    - "35 parametrized regression tests (DVAL-03)"
    - "@pytest.mark.regression gate"
  affects:
    - "pyproject.toml (new marker + addopts exclusion)"
    - "future plans that close mechanic gaps will improve the 0/35 baseline"
tech_stack:
  added:
    - "pytest parametrize over pathlib.Path objects"
    - "restricted exec() namespace for graph_builder code"
    - "shutil.copy2 for seed mechanic deployment into test universe"
  patterns:
    - "FakeClassifier / FakeObserver bypass LLM cost in CI"
    - "TDD RED (test_conftest.py fails) -> GREEN (conftest.py written)"
    - "exec_graph_builder restricted namespace (mirrors test_integration/ pattern)"
key_files:
  created:
    - "tests/test_regression/__init__.py"
    - "tests/test_regression/conftest.py"
    - "tests/test_regression/test_conftest.py"
    - "tests/test_regression/test_use_cases.py"
    - "tests/test_regression/README.md"
  modified:
    - "pyproject.toml (regression marker + addopts exclusion)"
decisions:
  - "D-16: 35 Phase-3 UC manifests reused as E2E regression tests (zero duplication)"
  - "D-25: FakeClassifier + FakeObserver avoid 35 x 2 LLM calls per CI run"
  - "Rule 1 fix: plan used kg.query_node() which does not exist; changed to kg.query()"
  - "Seed mechanics copied into test universe via shutil.copy2 (rglob preserves subdirs)"
  - "Regression excluded from default addopts so normal dev cycles stay fast"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-13T16:17:23Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 1
---

# Phase 06 Plan 03: Use-case regression suite — 35 Phase-3 UC manifests as E2E integration tests

**One-liner:** Parametrized pytest suite over all 35 Phase-3 UC manifests using FakeClassifier + FakeObserver; baseline 0/35 pass (all yield — no seed mechanic has VerbMatcher watches()).

## What Was Built

### `tests/test_regression/` package

A pytest package with four files:

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `conftest.py` | FakeClassifier, FakeObserver, exec_graph_builder, build_engine fixture |
| `test_conftest.py` | 6 scaffolding tests (TDD RED→GREEN for the fixtures) |
| `test_use_cases.py` | 35 parametrized regression tests (DVAL-03) |
| `README.md` | Suite docs, failure interpretation guide, extension instructions |

### Fake LLM Strategy (D-25)

**FakeClassifier** takes the manifest's `actions[0].classified` dict and returns
`VerdictOk(classified=ClassifiedAction(**classified_dict), confidence=0.99)`.
No Haiku call. Makes every test deterministic and free.

**FakeObserver** returns `"Action succeeded."` (or the refusal_narrative verbatim
when provided). No Sonnet call. Per 06-RESEARCH §Open Question 2: the regression
suite tests mechanic matching + graph assertions, not observer prose.

**Cost impact:** 35 × 2 LLM calls per CI run = ~$0.05–$0.50 and 60+ seconds.
Fake clients reduce this to ~5 seconds.

### exec() Namespace Restriction (06-RESEARCH Pitfall 2)

`exec_graph_builder(code, kg)` runs UC graph_builder code with:

```python
_EXEC_NS_BASE = {
    "__builtins__": {
        "range": range, "print": print, "len": len,
        "list": list, "dict": dict, "set": set, "tuple": tuple,
        "str": str, "int": int, "float": float, "bool": bool,
        "True": True, "False": False, "None": None,
    }
}
```

`__import__` is absent from the namespace. A test `test_conftest_exec_graph_builder_no_import`
confirms that `__import__("os").getcwd()` raises `NameError` or `AttributeError`.

### Seed Mechanics Deployment

The `build_engine` fixture copies all non-underscore `.py` files from
`src/token_world/mechanic/seeds/` (recursively, preserving subdirectory structure)
into the test universe's `mechanics/` dir. Without this, the engine's
`MechanicRegistry.scan()` finds no mechanics and every tick yields.

### pytest.mark.regression Gate

Registered in `pyproject.toml`:
```
"regression: use-case regression suite (DVAL-03); run with 'uv run pytest -m regression'"
```

Default `addopts = "-m 'not integration and not regression'"` excludes the 35-UC
suite from normal dev cycles. Opt-in: `uv run pytest -m regression`.

## Baseline Pass/Fail Count

**0/35 pass. 35/35 fail (all yield).**

Every UC fails with: `expected kind='ok', got kind='yielded'`

### Root Cause

No seed mechanic implements `watches()` with a `VerbMatcher`. The
`DeterministicMatcher` scores mechanics by +3 for a verb match in `watches()`.
Without `watches()`, all voluntary mechanics score 0, `NoMatchResult` is returned,
`decide()` emits `YieldDecision`, and the engine yields.

This is the expected state. The gaps are documented in each manifest's `gaps:`
block. These are Phase 5/7 mechanic improvements.

### Failure Breakdown by Category

| Category | UCs | Fail reason |
|----------|-----|-------------|
| spatial (UC-S01..S07) | 7/7 | yield — no VerbMatcher on movement/passage_move |
| social (UC-O01..O08) | 8/8 | yield — no VerbMatcher on trade/persuade/give/speak/teach/observe |
| resource (UC-R01..R07) | 7/7 | yield — no VerbMatcher on craft/consume/give/pickup/pay/degrade |
| environmental (UC-V01..V07) | 7/7 | yield — no VerbMatcher on involuntary mechanics |
| edge-case (UC-E01..E06) | 6/6 | yield — same root cause |

### Notable Edge Cases

- **UC-E04 (nonsense-input)**: `classified.verb = "none"` — no mechanic matches,
  yields instead of refusing. Expected "blocked". Correct signal: engine needs
  an explicit `no_viable_action` path from the classifier.
- **UC-R07 (conservation-violation-attempt)**: `verb = "invoke_mechanic"` — no
  mechanic. Correct signal: conservation checker never reached because matching fails.
- **UC-E06 (locked room)**: `expected_outcome = "pass"` — the `try_door` mechanic
  exists in seeds but has no `watches()`, so it yields. Correct signal: add
  VerbMatcher to try_door.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `kg.query_node()` does not exist**
- **Found during:** Task 2 implementation
- **Issue:** Plan code used `kg.query_node(node)` to get node properties. The actual
  `KnowledgeGraph` API has `kg.query(node_id, property=None) -> dict`.
- **Fix:** Changed all `kg.query_node(...)` calls to `kg.query(...)` in `_verify_assertion()`.
- **Files modified:** `tests/test_regression/test_use_cases.py`
- **Commit:** cc49832

## How Plan 06-05 Invokes This Suite

Plan 06-05 (prompt-hash-change detection) will invoke the regression suite
automatically when any system prompt hash changes:

```bash
uv run pytest -m regression --tb=short --json-report \
    --json-report-file universe/regression-history.jsonl
```

Results are appended to `universe/regression-history.jsonl` for trend analysis
(AUTO-07). The regression suite is the smoke test that fires on every
prompt-engineering change, closing the D-14/D-15 loop.

## How to Extend with New Assertion Kinds

1. Add the new kind string to `VALID_ASSERTION_KINDS` in
   `src/token_world/use_cases/loader.py`.
2. Add an `elif kind == "new_kind":` branch in `_verify_assertion()` in
   `tests/test_regression/test_use_cases.py`.
3. Use the new kind in a manifest's `graph_assertions:` block.

## Known Stubs

None. The suite is structurally complete. The 0/35 pass rate is a content
gap (missing `watches()` on seed mechanics), not a stub.

## Threat Flags

None. The test package adds no network endpoints, auth paths, or new
schema changes. `exec()` with restricted namespace is defence-in-depth.

## Self-Check: PASSED
